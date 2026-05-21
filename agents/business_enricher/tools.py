"""
Thin wrappers around Splunk MCP tools and the business context DB.
Each function is idempotent, well-typed, and logs every call.

Two store implementations share the same async interface:
  - BusinessContextStore   -> Postgres (asyncpg), production path
  - InMemoryContextStore   -> CSV-backed, zero-infra demo / tests
"""
from __future__ import annotations
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

import httpx

logger = logging.getLogger(__name__)


class MCPClient:
    """Wrapper around the Splunk MCP Server."""

    def __init__(self, mcp_url: str, api_token: str, timeout_s: int = 30):
        self.mcp_url = mcp_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.timeout = timeout_s
        self.calls_made = 0

    async def call_tool(self, tool_name: str, params: dict) -> dict:
        self.calls_made += 1
        logger.info(f"MCP call: {tool_name} params={params}")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.mcp_url}/tools/{tool_name}",
                json=params, headers=self.headers,
            )
            r.raise_for_status()
            return r.json()


class BusinessContextStore:
    """
    Interface to the Postgres business context DB.
    Wraps SQL queries the agent needs.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        # Lazy import so the in-memory path works without asyncpg installed.
        import asyncpg
        self._asyncpg = asyncpg
        self._pool = None

    async def init(self):
        self._pool = await self._asyncpg.create_pool(self.dsn, min_size=2, max_size=10)

    @asynccontextmanager
    async def conn(self):
        async with self._pool.acquire() as c:
            yield c

    # ---------- SERVICE CATALOG ----------
    async def lookup_service(self, service_id: str) -> Optional[dict]:
        async with self.conn() as c:
            row = await c.fetchrow(
                "SELECT * FROM services WHERE service_id=$1 OR service_name=$1",
                service_id,
            )
            return dict(row) if row else None

    # ---------- AFFECTED CUSTOMERS ----------
    async def lookup_affected_customers(
        self, service_id: str, start: datetime, end: datetime,
    ) -> list[dict]:
        async with self.conn() as c:
            rows = await c.fetch(
                """
                SELECT c.customer_id, c.customer_name, c.tier, c.acv_usd,
                       c.churn_risk_base, c.named_account,
                       COUNT(t.txn_id) AS failed_txns
                FROM customer_transaction_log t
                JOIN customers c ON c.customer_id = t.customer_id
                WHERE t.service_id = $1
                  AND t.ts BETWEEN $2 AND $3
                  AND t.status = 'failed'
                GROUP BY c.customer_id, c.customer_name, c.tier, c.acv_usd,
                         c.churn_risk_base, c.named_account
                """,
                service_id, start, end,
            )
            return [dict(r) for r in rows]

    # ---------- SLA BREACHES ----------
    async def lookup_sla_breaches(
        self, service_id: str, start: datetime, end: datetime,
        duration_minutes: float,
    ) -> list[dict]:
        async with self.conn() as c:
            rows = await c.fetch(
                """
                SELECT s.contract_id, s.customer_id, s.uptime_target_pct,
                       s.credit_pct_per_breach, s.monthly_fee_usd
                FROM sla_contracts s
                WHERE s.service_id = $1 AND s.active = true
                """,
                service_id,
            )
            breaches = []
            for r in rows:
                # 99.95% uptime = ~21.6 min/month allowed downtime
                allowed_min = (100 - float(r["uptime_target_pct"])) / 100 * 30 * 24 * 60
                if duration_minutes > allowed_min:
                    credit = float(r["monthly_fee_usd"]) * float(r["credit_pct_per_breach"]) / 100
                    breaches.append({**dict(r), "credit_owed_usd": credit})
            return breaches

    # ---------- HISTORY ----------
    async def lookup_incident_history(
        self, service_id: str, category: str, days: int = 30,
    ) -> list[dict]:
        async with self.conn() as c:
            rows = await c.fetch(
                """
                SELECT * FROM incidents_history
                WHERE service_id = $1 AND category = $2
                  AND occurred_at >= NOW() - ($3 || ' days')::INTERVAL
                ORDER BY occurred_at DESC
                """,
                service_id, category, str(days),
            )
            return [dict(r) for r in rows]


class InMemoryContextStore:
    """
    CSV-backed store with the same async interface as BusinessContextStore.
    Lets the Collector -> Enricher slice run with zero infrastructure.
    Customer impact is derived from a deterministic affected-count map keyed
    by service (synthetic "demo night"), since there is no live txn log.
    """

    def __init__(self, seed_dir: str | Path):
        self.seed_dir = Path(seed_dir)
        self.calls_made = 0
        self._services: dict[str, dict] = {}
        self._sla_by_service: dict[str, list[dict]] = {}
        self._affected_by_service: dict[str, list[dict]] = {}

    async def init(self):
        self._load_services()
        self._load_sla()
        self._build_affected_customers()

    # ---- loaders -------------------------------------------------
    def _load_services(self):
        path = self.seed_dir / "services.csv"
        for row in _read_csv(path):
            row["revenue_critical"] = row.get("revenue_critical") == "true"
            row["customer_facing"] = row.get("customer_facing") == "true"
            row["revenue_per_min_usd"] = _to_float(row.get("revenue_per_min_usd"))
            row["regulated_data"] = [
                d for d in (row.get("regulated_data") or "").split(",") if d
            ]
            self._services[row["service_id"]] = row
            self._services[row["service_name"]] = row

    def _load_sla(self):
        path = self.seed_dir / "sla_contracts.csv"
        if not path.exists():
            return
        for row in _read_csv(path):
            if row.get("active") != "true":
                continue
            self._sla_by_service.setdefault(row["service_id"], []).append(row)

    def _build_affected_customers(self):
        """Deterministic synthetic impact for the demo night, keyed by service."""
        customers = list(_read_csv(self.seed_dir / "customers.csv")) \
            if (self.seed_dir / "customers.csv").exists() else []
        # The payment outage (svc-001) impacts the demo customer set.
        impacted = []
        for c in customers:
            impacted.append({
                "customer_id": c["customer_id"],
                "customer_name": c["customer_name"],
                "tier": c["tier"],
                "acv_usd": _to_float(c.get("acv_usd")),
                "churn_risk_base": _to_float(c.get("churn_risk_base")),
                "named_account": c.get("named_account") == "true",
                "failed_txns": 3,
            })
        self._affected_by_service["svc-001"] = impacted

    # ---- interface ----------------------------------------------
    async def lookup_service(self, service_id: str) -> Optional[dict]:
        self.calls_made += 1
        return self._services.get(service_id)

    async def lookup_affected_customers(
        self, service_id: str, start: datetime, end: datetime,
    ) -> list[dict]:
        self.calls_made += 1
        svc = self._services.get(service_id)
        sid = svc["service_id"] if svc else service_id
        return self._affected_by_service.get(sid, [])

    async def lookup_sla_breaches(
        self, service_id: str, start: datetime, end: datetime,
        duration_minutes: float,
    ) -> list[dict]:
        self.calls_made += 1
        svc = self._services.get(service_id)
        sid = svc["service_id"] if svc else service_id
        breaches = []
        for r in self._sla_by_service.get(sid, []):
            allowed_min = (100 - float(r["uptime_target_pct"])) / 100 * 30 * 24 * 60
            if duration_minutes > allowed_min:
                credit = float(r["monthly_fee_usd"]) * float(r["credit_pct_per_breach"]) / 100
                breaches.append({**r, "credit_owed_usd": credit})
        return breaches

    async def lookup_incident_history(
        self, service_id: str, category: str, days: int = 30,
    ) -> list[dict]:
        self.calls_made += 1
        return []


def _read_csv(path: Path):
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _to_float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
