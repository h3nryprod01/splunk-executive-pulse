# agents/signal_collector/detectors/base.py
"""
Detector base class. Each detector knows:
  - which SPL query to run
  - how to parse results into RawSignal[]
"""
from __future__ import annotations
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..models import RawSignal, SignalCategory, SignalMagnitude, CollectorConfig
from ..splunk_mcp import SplunkMCPSearchClient

logger = logging.getLogger(__name__)

QUERIES_DIR = Path(__file__).parent.parent / "queries"


class BaseDetector(ABC):
    """One detector = one signal category."""

    category: SignalCategory
    query_file: str          # filename in queries/ dir

    def __init__(self, splunk: SplunkMCPSearchClient, config: CollectorConfig):
        self.splunk = splunk
        self.config = config

    # ---------- public ----------
    async def detect(self) -> list[RawSignal]:
        try:
            spl = self._build_query()
            results = await self.splunk.search(
                spl=spl,
                earliest=self.config.time_window_start,
                latest=self.config.time_window_end,
                max_count=10000,
            )
            signals = self._parse_results(results, spl)
            logger.info(f"{self.__class__.__name__}: {len(signals)} signals")
            return signals
        except Exception as e:
            logger.exception(f"{self.__class__.__name__} failed: {e}")
            raise

    # ---------- subclass overrides ----------
    @abstractmethod
    def _parse_results(self, rows: list[dict], spl: str) -> list[RawSignal]:
        """Convert Splunk JSON rows into RawSignal objects."""

    # ---------- helpers ----------
    def _build_query(self) -> str:
        """
        Build the SPL this detector will run. Default: load the static .spl
        file and fill template vars. Detectors that generate SPL programmatically
        (e.g. via the Splunk AI Toolkit) override this.
        """
        return self._render_query(self._load_query())

    def _load_query(self) -> str:
        return (QUERIES_DIR / self.query_file).read_text()

    def _render_query(self, spl: str) -> str:
        """Fill in template variables ##VAR##."""
        return (spl
            .replace("##BASELINE_DAYS##", str(self.config.baseline_days))
            .replace("##ERROR_SIGMA##", str(self.config.error_sigma_threshold))
            .replace("##LATENCY_SIGMA##", str(self.config.latency_sigma_threshold))
            .replace("##MIN_COUNT##", str(self.config.min_event_count))
        )

    @staticmethod
    def _new_signal_id() -> str:
        return f"sig_{uuid.uuid4().hex[:10]}"

    @staticmethod
    def _parse_dt(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        # Splunk returns ISO8601 in _time
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
