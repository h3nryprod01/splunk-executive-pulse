# agents/signal_collector/__main__.py
"""
python -m agents.signal_collector
"""
import asyncio, json, os
from datetime import datetime, timezone, timedelta
from .agent import SignalCollectorAgent
from .models import CollectorConfig
from .splunk_mcp import SplunkMCPSearchClient


async def main():
    splunk = SplunkMCPSearchClient(
        mcp_url=os.getenv("SPLUNK_MCP_URL", "http://localhost:8089"),
        api_token=os.getenv("SPLUNK_MCP_TOKEN", "dev-token"),
    )
    end = datetime.now(tz=timezone.utc)
    config = CollectorConfig(
        time_window_start=end - timedelta(hours=24),
        time_window_end=end,
    )
    agent = SignalCollectorAgent(splunk=splunk, config=config)
    out = await agent.run()
    print(json.dumps(out.model_dump(mode="json"), indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())
