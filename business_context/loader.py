"""
Business-context seed loader.

The demo's source of truth is the CSV seed under business_context/seed_data/.
In a full deployment `load_seed_data` would also push these rows into Postgres;
here it is CSV-first so integration fixtures and the zero-infra demo work without
a database. All functions are async to match the integration-test contract.
"""
from __future__ import annotations
import csv
from pathlib import Path
from typing import Optional

SEED_DIR = Path(__file__).resolve().parent / "seed_data"
CUSTOMERS_CSV = SEED_DIR / "customers.csv"


async def has_seed_data(seed_dir: Optional[str | Path] = None) -> bool:
    """True if the customer seed exists and is non-empty."""
    path = Path(seed_dir) / "customers.csv" if seed_dir else CUSTOMERS_CSV
    return path.exists() and path.stat().st_size > 0


async def load_seed_data(seed_dir: Optional[str | Path] = None) -> dict:
    """
    Ensure seed data is present. Generates the customer set if missing.
    Returns a summary of what is loaded (row counts per file).
    """
    base = Path(seed_dir) if seed_dir else SEED_DIR
    if not (base / "customers.csv").exists():
        # Generate the 1,247-customer demo set deterministically.
        from business_context.seed_data.generate_customers import main as gen
        gen()
    summary = {}
    for name in ("services", "customers", "sla_contracts", "executives"):
        path = base / f"{name}.csv"
        summary[name] = sum(1 for _ in open(path)) - 1 if path.exists() else 0
    return summary


async def all_customer_names(seed_dir: Optional[str | Path] = None) -> list[str]:
    """All customer display names — used to verify the briefing invents no accounts."""
    path = Path(seed_dir) / "customers.csv" if seed_dir else CUSTOMERS_CSV
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return [row["customer_name"] for row in csv.DictReader(f)]
