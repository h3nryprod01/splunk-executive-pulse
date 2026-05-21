# agents/signal_collector/models.py
"""
Schemas for Signal Collector.
Output (RawSignal) must match the Business Enricher's input contract.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SignalCategory(str, Enum):
    ERROR_SPIKE = "error_spike"
    LATENCY = "latency"
    SECURITY = "security"
    AVAILABILITY = "availability"
    CAPACITY = "capacity"
    DEPLOY = "deploy"
    COST = "cost"


class CollectorConfig(BaseModel):
    """Runtime config for one collection run."""
    model_config = ConfigDict(extra="forbid")

    time_window_start: datetime
    time_window_end: datetime
    baseline_days: int = 7

    indexes: list[str] = Field(default_factory=lambda: ["prod", "security", "cicd", "finance", "perf"])

    # Thresholds — tune per environment
    error_sigma_threshold: float = 2.0
    latency_sigma_threshold: float = 2.5
    min_event_count: int = 10               # filter noise
    max_signals_returned: int = 50          # protect downstream

    enabled_detectors: list[SignalCategory] = Field(
        default_factory=lambda: list(SignalCategory)
    )


class SignalMagnitude(BaseModel):
    metric: str
    value: float
    baseline: float
    deviation_sigma: float
    unit: Optional[str] = None


class RawSignal(BaseModel):
    """
    The atomic unit passed to the Business Enricher.
    CONTRACT: this schema must remain compatible with
    agents.business_enricher.models.RawSignal.
    """
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    category: SignalCategory
    service: str
    started_at: datetime
    ended_at: datetime
    magnitude: SignalMagnitude
    splunk_query: str
    correlation_ids: list[str] = Field(default_factory=list)
    raw_sample_size: int = 0


class CollectorOutput(BaseModel):
    run_id: str
    config: CollectorConfig
    signals: list[RawSignal]
    detectors_run: list[str]
    detectors_failed: list[dict] = Field(default_factory=list)
    splunk_searches_executed: int = 0
    total_duration_ms: int
    collected_at: datetime = Field(default_factory=datetime.utcnow)
