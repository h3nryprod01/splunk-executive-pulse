# agents/signal_collector/detectors/deploy.py
from __future__ import annotations
from datetime import timedelta

from .base import BaseDetector
from ..models import RawSignal, SignalCategory, SignalMagnitude


class DeployDetector(BaseDetector):
    """
    Captures recent deploy events. Provides correlation_ids
    that other agents (especially Editor) use to link cause→effect.
    """
    category = SignalCategory.DEPLOY
    query_file = "deploy_events.spl"

    def _parse_results(self, rows, spl):
        signals = []
        for row in rows:
            ts = self._parse_dt(row["_time"])
            signals.append(RawSignal(
                signal_id=self._new_signal_id(),
                category=self.category,
                service=row["service"],
                started_at=ts,
                ended_at=ts + timedelta(minutes=5),
                magnitude=SignalMagnitude(
                    metric="deploy",
                    value=1,
                    baseline=0,
                    deviation_sigma=0,
                ),
                splunk_query=spl,
                correlation_ids=[
                    f"version:{row.get('version','?')}",
                    f"gate_passed:{row.get('gate_passed','?')}",
                    f"rolled_back:{bool(row.get('rollback_at'))}",
                ],
                raw_sample_size=1,
            ))
        return signals
