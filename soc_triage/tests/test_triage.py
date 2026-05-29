from soc_triage.copilot import SOCTriageCopilot
from soc_triage.models import Alert

ALERT = Alert(
    alert_id="ALERT-TEST", title="blocked auth spike",
    alert_type="credential_stuffing", index="security", sourcetype="auth-svc",
)


def test_detects_account_takeover():
    report = SOCTriageCopilot().triage(ALERT)
    assert report.verdict.severity == "CRITICAL"
    assert "takeover" in report.verdict.classification.lower()
    assert "alice" in " ".join(report.verdict.recommended_actions)


def test_investigation_pivots_through_three_steps():
    report = SOCTriageCopilot().triage(ALERT)
    steps = {f.step for f in report.findings}
    assert steps == {1, 2, 3}
    assert report.searches_run >= 3  # burst + per-IP success check + data access


def test_timeline_is_ordered_and_includes_success():
    report = SOCTriageCopilot().triage(ALERT)
    times = [t.time for t in report.timeline]
    assert times == sorted(times)
    assert any("allowed" in t.action for t in report.timeline)
    assert any(t.action == "export" for t in report.timeline)


def test_step1_uses_mltk_anomalydetection():
    report = SOCTriageCopilot().triage(ALERT)
    step1 = next(f for f in report.findings if f.step == 1)
    assert "anomalydetection" in step1.spl
    assert "MLTK" in step1.summary


def test_incident_has_offline_narrative_keyless():
    report = SOCTriageCopilot().triage(ALERT)
    assert report.narrative_source == "offline"
    assert "CRITICAL" in report.narrative
    assert "alice" in report.narrative


def test_no_compromise_when_no_successful_login():
    # Searcher that never returns a successful login or data access.
    def only_blocked(spl: str):
        if "result=blocked" in spl:
            return [{"index": "security", "sourcetype": "auth-svc", "_time": "06:00:01",
                     "result": "blocked", "src_ip": "9.9.9.9", "asn": "AS1", "username": "x"}]
        return []

    report = SOCTriageCopilot(searcher=only_blocked).triage(ALERT)
    assert report.verdict.severity == "HIGH"
    assert "no confirmed compromise" in report.verdict.classification.lower()
