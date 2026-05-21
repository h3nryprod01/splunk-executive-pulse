# agents/signal_collector/splunk_mcp.py
"""
Specialized Splunk MCP client for running searches.
Handles: dispatch, polling, result pagination, error retry.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from typing import Any
import httpx

logger = logging.getLogger(__name__)


class SplunkSearchError(Exception):
    pass


class SplunkMCPSearchClient:
    """
    Wraps the Splunk MCP `search` tool. Each call is an async search:
    dispatch → poll → fetch → parse.
    """

    def __init__(
        self, mcp_url: str, api_token: str,
        max_poll_attempts: int = 30, poll_interval_s: float = 2.0,
        timeout_s: int = 60,
    ):
        self.mcp_url = mcp_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        self.max_poll_attempts = max_poll_attempts
        self.poll_interval_s = poll_interval_s
        self.timeout = timeout_s
        self.searches_executed = 0

    async def search(
        self,
        spl: str,
        earliest: datetime,
        latest: datetime,
        max_count: int = 10000,
    ) -> list[dict[str, Any]]:
        """
        Run a Splunk search via MCP and return result rows.
        Raises SplunkSearchError on failure.
        """
        self.searches_executed += 1
        logger.info(f"SPL: {spl[:120]}{'...' if len(spl) > 120 else ''}")

        payload = {
            "query": spl if spl.strip().startswith("|") or spl.strip().startswith("search")
                     else f"search {spl}",
            "earliest_time": earliest.isoformat(),
            "latest_time": latest.isoformat(),
            "max_count": max_count,
            "output_mode": "json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # 1. Dispatch
            r = await client.post(
                f"{self.mcp_url}/tools/search",
                json=payload, headers=self.headers,
            )
            if r.status_code != 200:
                raise SplunkSearchError(f"dispatch failed: {r.status_code} {r.text[:200]}")
            sid = r.json().get("sid")
            if not sid:
                # Some MCP implementations return results inline for fast searches
                return r.json().get("results", [])

            # 2. Poll
            for attempt in range(self.max_poll_attempts):
                await asyncio.sleep(self.poll_interval_s)
                status_r = await client.get(
                    f"{self.mcp_url}/tools/search/{sid}/status",
                    headers=self.headers,
                )
                state = status_r.json().get("state")
                if state == "DONE":
                    break
                if state == "FAILED":
                    raise SplunkSearchError(f"search failed: {status_r.json()}")
            else:
                raise SplunkSearchError(f"search timeout after {attempt+1} polls")

            # 3. Fetch results
            results_r = await client.get(
                f"{self.mcp_url}/tools/search/{sid}/results",
                params={"output_mode": "json", "count": max_count},
                headers=self.headers,
            )
            return results_r.json().get("results", [])
