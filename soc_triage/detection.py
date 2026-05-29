"""MLTK-backed anomaly detection: decide whether the alert is a real spike.

Uses the Splunk AI Toolkit `| anomalydetection` SPL (built by the shared
agents.common.splunk_ai.mltk module) instead of assuming the alert is valid.
The keyless executor returns the underlying blocked-auth events; the anomaly
score is computed deterministically from per-IP attempt counts.
"""
from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.common.splunk_ai.mltk import count_anomaly_spl  # noqa: E402

# Expected blocked-auth attempts per source IP in a normal 1-minute window.
_BASELINE = 1


def detect_auth_anomaly(searcher: Callable[[str], list[dict]],
                        index: str, sourcetype: str) -> dict:
    spl = count_anomaly_spl(index, sourcetype, where="result=blocked", by_field="src_ip")
    rows = searcher(spl)
    by_ip = Counter(r["src_ip"] for r in rows if "src_ip" in r)
    peak = max(by_ip.values(), default=0)
    score = peak / _BASELINE if _BASELINE else float(peak)
    anomalous_ips = sorted(ip for ip, n in by_ip.items() if n > _BASELINE)
    return {
        "spl": spl,
        "rows": rows,
        "by_ip": dict(by_ip),
        "score": score,
        "is_anomaly": bool(anomalous_ips),
        "anomalous_ips": anomalous_ips,
    }
