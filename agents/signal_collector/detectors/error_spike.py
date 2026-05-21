# agents/signal_collector/detectors/error_spike.py
from __future__ import annotations
from datetime import timedelta
from typing import Any

from .base import BaseDetector
from ..models import RawSignal, SignalCategory, SignalMagnitude


class ErrorSpikeDetector(BaseDetector):
    """
    Detects time windows where a service's 5xx rate deviates
    > N sigma from rolling baseline.
    Output: one RawSignal per (service, contiguous-window).
    """
    category = SignalCategory.ERROR_SPIKE
    query_file = "error_spike.spl"

    def _parse_results(self, rows: list[dict], spl: str) -> list[RawSignal]:
        signals: list[RawSignal] = []
        # group by service, identify contiguous spike windows
        by_service: dict[str, list[dict]] = {}
        for row in rows:
            by_service.setdefault(row["service"], []).append(row)

        for service, windows in by_service.items():
            windows.sort(key=lambda r: r["_time"])
            # collapse adjacent buckets into one signal
            current_start, current_end = None, None
            current_count, current_baseline, current_sigma = 0, 0.0, 0.0

            def emit():
                if current_start is None:
                    return
                signals.append(RawSignal(
                    signal_id=self._new_signal_id(),
                    category=self.category,
                    service=service,
                    started_at=current_start,
                    ended_at=current_end,
                    magnitude=SignalMagnitude(
                        metric="http_5xx_count",
                        value=float(current_count),
                        baseline=float(current_baseline),
                        deviation_sigma=float(current_sigma),
                    ),
                    splunk_query=spl,
                    raw_sample_size=int(current_count),
                ))

            for w in windows:
                ts = self._parse_dt(w["_time"])
                count = int(w["error_count"])
                baseline = float(w["baseline_avg"])
                sigma = float(w["sigma_deviation"])
                if current_start is None:
                    current_start = ts
                    current_end = ts + timedelta(minutes=1)
                    current_count, current_baseline, current_sigma = count, baseline, sigma
                elif ts <= current_end + timedelta(minutes=2):
                    # extend
                    current_end = ts + timedelta(minutes=1)
                    current_count += count
                    current_sigma = max(current_sigma, sigma)
                else:
                    emit()
                    current_start = ts
                    current_end = ts + timedelta(minutes=1)
                    current_count, current_baseline, current_sigma = count, baseline, sigma
            emit()
        return signals
