# agents/signal_collector/tests/test_agent.py
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from agents.signal_collector.agent import SignalCollectorAgent
from agents.signal_collector.models import CollectorConfig, SignalCategory
from agents.signal_collector.detectors.error_spike import ErrorSpikeDetector


@pytest.fixture
def config():
    return CollectorConfig(
        time_window_start=datetime(2026,5,21,0,0,tzinfo=timezone.utc),
        time_window_end=datetime(2026,5,21,23,59,tzinfo=timezone.utc),
        enabled_detectors=[SignalCategory.ERROR_SPIKE],
    )


@pytest.fixture
def mock_splunk():
    client = AsyncMock()
    client.searches_executed = 0
    # Fake Splunk response for error_spike: 3 contiguous 1-min buckets at 02:47
    client.search.return_value = [
        {"_time": "2026-05-21T02:47:00Z", "service": "payment-api",
         "error_count": 18, "baseline_avg": 2.3, "sigma_deviation": 8.1},
        {"_time": "2026-05-21T02:48:00Z", "service": "payment-api",
         "error_count": 16, "baseline_avg": 2.3, "sigma_deviation": 7.6},
        {"_time": "2026-05-21T02:49:00Z", "service": "payment-api",
         "error_count": 13, "baseline_avg": 2.3, "sigma_deviation": 6.2},
    ]
    return client


@pytest.mark.asyncio
async def test_error_spike_collapses_contiguous_buckets(mock_splunk, config):
    agent = SignalCollectorAgent(splunk=mock_splunk, config=config)
    out = await agent.run()

    assert len(out.signals) == 1, "3 contiguous buckets → 1 signal"
    sig = out.signals[0]
    assert sig.service == "payment-api"
    assert sig.category == SignalCategory.ERROR_SPIKE
    assert sig.magnitude.value == 47  # 18+16+13
    assert sig.magnitude.deviation_sigma == 8.1  # max
    assert sig.started_at.hour == 2 and sig.started_at.minute == 47


@pytest.mark.asyncio
async def test_detector_failure_does_not_crash_pipeline(config):
    bad_splunk = AsyncMock()
    bad_splunk.searches_executed = 0
    bad_splunk.search.side_effect = RuntimeError("Splunk down")

    agent = SignalCollectorAgent(splunk=bad_splunk, config=config)
    out = await agent.run()

    assert len(out.signals) == 0
    assert len(out.detectors_failed) == 1
    assert out.detectors_failed[0]["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_max_signals_cap_enforced(mock_splunk):
    # Generate 100 non-contiguous spike buckets (spaced 5 min apart, distinct services)
    base = datetime(2026, 5, 21, tzinfo=timezone.utc)
    mock_splunk.search.return_value = [
        {"_time": (base + timedelta(minutes=h * 5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
         "service": f"svc-{h}",
         "error_count": 50 - (h % 40), "baseline_avg": 2, "sigma_deviation": 5 + h * 0.1}
        for h in range(100)
    ]
    config = CollectorConfig(
        time_window_start=datetime(2026,5,21,tzinfo=timezone.utc),
        time_window_end=datetime(2026,5,22,tzinfo=timezone.utc),
        enabled_detectors=[SignalCategory.ERROR_SPIKE],
        max_signals_returned=20,
    )
    agent = SignalCollectorAgent(splunk=mock_splunk, config=config)
    out = await agent.run()
    assert len(out.signals) == 20
    # Highest sigma first
    assert out.signals[0].magnitude.deviation_sigma > out.signals[-1].magnitude.deviation_sigma
