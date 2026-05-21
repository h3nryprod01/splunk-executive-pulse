"""
Deterministically generate customers.csv for the demo night.
34 enterprise + 210 mid-market + 1003 SMB = 1247 affected accounts.

    python business_context/seed_data/generate_customers.py
"""
from __future__ import annotations
import csv
import random
from pathlib import Path

OUT = Path(__file__).parent / "customers.csv"
SEED = 20260521

NAMED = [
    ("cust-001", "Acme Corp", 480000, 0.04),
    ("cust-002", "Globex Inc", 720000, 0.03),
    ("cust-003", "Initech", 310000, 0.05),
    ("cust-004", "Umbrella Co", 410000, 0.04),
    ("cust-005", "Soylent Industries", 365000, 0.06),
]

HEADER = [
    "customer_id", "customer_name", "tier", "acv_usd", "churn_risk_base",
    "named_account", "region", "industry", "csm_owner", "contract_start", "contract_end",
]
REGIONS = ["NA", "EMEA", "APAC", "LATAM"]
INDUSTRIES = ["retail", "finance", "tech", "healthcare", "manufacturing"]
CSMS = ["sarah.k", "marcus.l", "priya.n", "tom.b"]


def main() -> None:
    rng = random.Random(SEED)
    rows: list[list] = []
    idx = 1

    def add(name, tier, acv, churn, named):
        nonlocal idx
        cid = f"cust-{idx:04d}"
        rows.append([
            cid, name, tier, acv, churn, str(named).lower(),
            rng.choice(REGIONS), rng.choice(INDUSTRIES), rng.choice(CSMS),
            "2024-01-15", "2027-01-15",
        ])
        idx += 1

    for cid, name, acv, churn in NAMED:
        add(name, "enterprise", acv, churn, True)
    for _ in range(34 - len(NAMED)):
        add(f"Enterprise {idx}", "enterprise", rng.randint(250_000, 800_000),
            round(rng.uniform(0.03, 0.08), 3), False)
    for _ in range(210):
        add(f"MidMarket {idx}", "mid-market", rng.randint(40_000, 150_000),
            round(rng.uniform(0.05, 0.12), 3), False)
    for _ in range(1003):
        add(f"SMB {idx}", "smb", rng.randint(5_000, 30_000),
            round(rng.uniform(0.08, 0.20), 3), False)

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
    print(f"Wrote {len(rows)} customers -> {OUT}")


if __name__ == "__main__":
    main()
