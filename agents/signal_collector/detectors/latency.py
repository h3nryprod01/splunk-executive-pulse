# agents/signal_collector/detectors/latency.py
from __future__ import annotations
from datetime import timedelta

from .base import BaseDetector
from ..models import RawSignal, SignalCategory, SignalMagnitude


class LatencyDetector(BaseDetector):
    category = SignalCategory.LATENCY
    query_file = "latency_anomaly.spl"

    def _parse_results(self, rows, spl):
        signals = []
        for row in rows:
            ts = self._parse_dt(row["_time"])
            signals.append(RawSignal(
                signal_id=self._new_signal_id(),
                category=self.category,
                service=row["service"],
                started_at=ts,
                ended_at=ts + timedelta(minutes=int(row.get("window_min", 60))),
                magnitude=SignalMagnitude(
                    metric=row["latency_metric"],   # p95_ms or p99_ms
                    value=float(row["latency_value"]),
                    baseline=float(row["baseline_value"]),
                    deviation_sigma=float(row.get("sigma", 0)),
                    unit="ms",
                ),
                splunk_query=spl,
                raw_sample_size=int(row.get("request_count", 0)),
            ))
        return signals
