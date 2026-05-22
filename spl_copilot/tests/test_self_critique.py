import asyncio

from spl_copilot.copilot import SPLCopilot
from spl_copilot.critique import fix_unknown_fields
from spl_copilot.mock_index import MockExecutor


class _FakeAssistant:
    """Returns a fixed SPL so tests don't depend on the phrasebook."""

    def __init__(self, spl: str, source: str = "test"):
        self._spl = spl
        self._source = source

    async def generate_spl(self, nl_intent: str):
        from agents.common.splunk_ai.spl_assistant import SPLSuggestion

        return SPLSuggestion(
            intent=nl_intent, spl=self._spl, explanation="",
            source=self._source, confidence=0.9,
        )


def test_self_fix_bad_field_then_returns_rows():
    # `status` is not in the payment-svc schema; `http_status` is.
    bad = "search index=prod sourcetype=payment-svc status>=500 | timechart span=1m count"
    copilot = SPLCopilot(assistant=_FakeAssistant(bad), executor=MockExecutor())
    result = asyncio.run(copilot.run("payment errors"))

    assert len(result.steps) == 1
    assert "http_status>=500" in result.final_spl
    assert " status>=500" not in result.final_spl  # bare `status` field is gone
    assert result.row_count > 0


def test_clean_query_needs_no_fix():
    good = "search index=security sourcetype=auth-svc result=blocked | stats count by src_ip"
    copilot = SPLCopilot(assistant=_FakeAssistant(good), executor=MockExecutor())
    result = asyncio.run(copilot.run("blocked logins"))

    assert result.steps == ()
    assert result.row_count == 2


def test_unfixable_field_stops_gracefully():
    weird = "search index=prod sourcetype=payment-svc zzz_nonsense=1"
    copilot = SPLCopilot(assistant=_FakeAssistant(weird), executor=MockExecutor())
    result = asyncio.run(copilot.run("nonsense"))

    assert result.row_count == 0
    assert len(result.steps) <= copilot.max_fixes


def test_fix_unknown_fields_alias():
    available = {"_time", "http_status", "response_ms"}
    out = fix_unknown_fields("search status>=500", ("status",), available)
    assert out is not None
    new_spl, reason = out
    assert "http_status>=500" in new_spl
    assert "http_status" in reason


def test_real_phrasebook_payment_self_fixes():
    # End-to-end through the real shared assistant phrasebook (keyless).
    copilot = SPLCopilot(executor=MockExecutor())
    result = asyncio.run(copilot.run("show me payment errors"))
    assert "http_status" in result.final_spl
    assert result.row_count > 0
