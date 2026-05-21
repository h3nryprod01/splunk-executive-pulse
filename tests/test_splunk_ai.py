import pytest

from agents.common.splunk_ai.spl_assistant import SplunkSPLAssistant
from agents.common.splunk_ai.mltk import anomaly_detection_spl, forecast_spl


@pytest.fixture
def assistant():
    # No endpoint/token configured -> deterministic offline phrasebook.
    return SplunkSPLAssistant(endpoint=None, token=None)


async def test_offline_matches_payment_errors(assistant):
    s = await assistant.generate_spl("show me last night's payment errors")
    assert "payment-svc" in s.spl and "status>=500" in s.spl
    assert s.source == "offline-fallback"


async def test_offline_matches_credential_stuffing(assistant):
    s = await assistant.generate_spl("was there a credential stuffing attack?")
    assert "index=security" in s.spl and "unique_ips" in s.spl


async def test_generic_fallback_low_confidence(assistant):
    s = await assistant.generate_spl("tell me about quarterly widget velocity")
    assert s.source == "offline-fallback"
    assert s.confidence < 0.5
    assert s.spl.startswith("search index=*")


def test_mltk_anomaly_spl_density():
    spl = anomaly_detection_spl("prod", "payment-svc", method="density")
    assert "| fit DensityFunction" in spl and "| apply" in spl


def test_mltk_forecast_spl():
    spl = forecast_spl("prod", "checkout-svc")
    assert "| predict" in spl and "upper95(forecast)" in spl
