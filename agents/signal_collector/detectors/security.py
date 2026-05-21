# agents/signal_collector/detectors/security.py
from __future__ import annotations
from datetime import timedelta

from .base import BaseDetector
from ..models import RawSignal, SignalCategory, SignalMagnitude


class SecurityDetector(BaseDetector):
    """
    Detects auth-failure storms, geo/ASN clustering attacks,
    WAF block spikes.
    """
    category = SignalCategory.SECURITY
    query_file = "auth_failures.spl"

    def _parse_results(self, rows, spl):
        signals = []
        for row in rows:
            start = self._parse_dt(row["window_start"])
            end = self._parse_dt(row["window_end"])
            signals.append(RawSignal(
                signal_id=self._new_signal_id(),
                category=self.category,
                service="auth-api",
                started_at=start,
                ended_at=end,
                magnitude=SignalMagnitude(
                    metric="auth_failures_blocked",
                    value=float(row["total_attempts"]),
                    baseline=float(row.get("baseline_attempts", 0)),
                    deviation_sigma=float(row.get("sigma", 0)),
                ),
                splunk_query=spl,
                correlation_ids=[
                    f"asn:{row.get('top_asn','?')}",
                    f"unique_ips:{row.get('unique_ips','?')}",
                ],
                raw_sample_size=int(row["total_attempts"]),
            ))
        return signals
