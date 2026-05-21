# agents/signal_collector/agent.py
"""
Signal Collector Agent.
Runs all enabled detectors in parallel, aggregates signals,
ranks by deviation_sigma, returns top-N.
"""
from __future__ import annotations
import asyncio
import logging
import time
import uuid
from typing import Type

from .models import CollectorConfig, CollectorOutput, RawSignal, SignalCategory
from .splunk_mcp import SplunkMCPSearchClient
from .detectors.base import BaseDetector
from .detectors.error_spike import ErrorSpikeDetector
from .detectors.latency import LatencyDetector
from .detectors.security import SecurityDetector
from .detectors.deploy import DeployDetector
from .detectors.forecast import CapacityForecastDetector

logger = logging.getLogger(__name__)


# Registry — add new detectors here
DETECTOR_REGISTRY: dict[SignalCategory, Type[BaseDetector]] = {
    SignalCategory.ERROR_SPIKE:  ErrorSpikeDetector,
    SignalCategory.LATENCY:      LatencyDetector,
    SignalCategory.SECURITY:     SecurityDetector,
    SignalCategory.DEPLOY:       DeployDetector,
    SignalCategory.CAPACITY:     CapacityForecastDetector,  # MLTK | predict
    # add: AvailabilityDetector, CostDetector
}


class SignalCollectorAgent:

    def __init__(self, splunk: SplunkMCPSearchClient, config: CollectorConfig):
        self.splunk = splunk
        self.config = config

    async def run(self) -> CollectorOutput:
        run_id = f"run_{uuid.uuid4().hex[:10]}"
        start = time.perf_counter()
        logger.info(f"[{run_id}] starting collection window="
                    f"{self.config.time_window_start} → {self.config.time_window_end}")

        detectors: list[BaseDetector] = [
            DETECTOR_REGISTRY[cat](self.splunk, self.config)
            for cat in self.config.enabled_detectors
            if cat in DETECTOR_REGISTRY
        ]

        # Fan out — each detector is independent
        results = await asyncio.gather(
            *[d.detect() for d in detectors],
            return_exceptions=True,
        )

        all_signals: list[RawSignal] = []
        detectors_run, detectors_failed = [], []

        for detector, result in zip(detectors, results):
            name = detector.__class__.__name__
            if isinstance(result, Exception):
                detectors_failed.append({
                    "detector": name,
                    "error": str(result),
                    "error_type": type(result).__name__,
                })
                logger.error(f"[{run_id}] {name} failed: {result}")
            else:
                detectors_run.append(name)
                all_signals.extend(result)

        # Rank + cap
        all_signals.sort(
            key=lambda s: s.magnitude.deviation_sigma, reverse=True,
        )
        capped = all_signals[: self.config.max_signals_returned]

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[{run_id}] done: {len(capped)} signals "
            f"({len(all_signals) - len(capped)} dropped by cap), "
            f"{self.splunk.searches_executed} SPL searches, {duration_ms}ms"
        )

        return CollectorOutput(
            run_id=run_id,
            config=self.config,
            signals=capped,
            detectors_run=detectors_run,
            detectors_failed=detectors_failed,
            splunk_searches_executed=self.splunk.searches_executed,
            total_duration_ms=duration_ms,
        )
