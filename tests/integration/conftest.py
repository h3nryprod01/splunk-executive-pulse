# tests/integration/conftest.py
"""Shared fixtures + setup for integration tests."""
import pytest
import asyncio
import subprocess
import os

@pytest.fixture(scope="session", autouse=True)
def ensure_stack_running():
    """Auto-boot the stack if not already up."""
    if os.getenv("SKIP_STACK_CHECK") == "1":
        yield; return
    try:
        out = subprocess.run(
            ["docker", "compose", "ps", "--services", "--filter", "status=running"],
            capture_output=True, text=True, check=True,
        )
        required = {"splunk", "postgres", "redis", "mcp"}
        running = set(out.stdout.strip().split())
        missing = required - running
        if missing:
            pytest.skip(f"required services not running: {missing} — run `make up`")
    except subprocess.CalledProcessError:
        pytest.skip("docker compose not available")
    yield


@pytest.fixture(scope="session")
def event_loop():
    """Module-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def seeded_data():
    """Ensure synthetic data is seeded before integration tests."""
    if os.getenv("SKIP_SEED") == "1":
        return
    from business_context.loader import load_seed_data, has_seed_data
    if not await has_seed_data():
        await load_seed_data()
