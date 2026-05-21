import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from agents.signal_collector.agent import SignalCollectorAgent, DETECTOR_REGISTRY
from agents.signal_collector.models import CollectorConfig, SignalCategory


def test_capacity_detector_registered():
    assert SignalCategory.CAPACITY in DETECTOR_REGISTRY


@pytest.fixture
def config():
    return CollectorConfig(
        time_window_start=datetime(2026, 5, 21, 0, 0, tzinfo=timezone.utc),
        time_window_end=datetime(2026, 5, 21, 23, 59, tzinfo=timezone.utc),
        enabled_detectors=[SignalCategory.CAPACITY],
    )


@pytest.mark.asyncio
async def test_mltk_forecast_breach_emits_signal(config):
    splunk = AsyncMock()
    splunk.searches_executed = 0
    # MLTK | predict output: one point breaches the upper confidence band.
    splunk.search.return_value = [
        {"_time": "2026-05-21T03:00:00Z", "service": "checkout-api",
         "metric": "p99(response_ms)", "actual": 612, "forecast_upper": 430,
         "sigma": 3.1, "breach": 1, "window_min": 60, "request_count": 184000},
        {"_time": "2026-05-21T04:00:00Z", "service": "checkout-api",
         "metric": "p99(response_ms)", "actual": 401, "forecast_upper": 430,
         "sigma": 0.4, "breach": 0, "window_min": 60, "request_count": 170000},
    ]
    agent = SignalCollectorAgent(splunk=splunk, config=config)
    out = await agent.run()

    assert len(out.signals) == 1, "only the breaching point becomes a signal"
    sig = out.signals[0]
    assert sig.category == SignalCategory.CAPACITY
    assert sig.magnitude.value == 612
    assert sig.magnitude.baseline == 430
    assert "predict" in sig.splunk_query  # SPL came from the MLTK builder
