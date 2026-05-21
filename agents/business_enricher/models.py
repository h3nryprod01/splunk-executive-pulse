"""
Pydantic models for the Business Context Enricher agent.
All inter-agent data flows through these typed schemas.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# INPUT: signals coming from Signal Collector
# ============================================================
class SignalCategory(str, Enum):
    ERROR_SPIKE = "error_spike"
    LATENCY = "latency"
    SECURITY = "security"
    AVAILABILITY = "availability"
    CAPACITY = "capacity"
    DEPLOY = "deploy"
    COST = "cost"


class SignalMagnitude(BaseModel):
    metric: str
    value: float
    baseline: float
    deviation_sigma: float
    unit: Optional[str] = None


class RawSignal(BaseModel):
    """Input from Signal Collector."""
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    category: SignalCategory
    service: str = Field(..., description="service_id matching catalog")
    started_at: datetime
    ended_at: datetime
    magnitude: SignalMagnitude
    splunk_query: str
    correlation_ids: list[str] = Field(default_factory=list)
    raw_sample_size: int = 0

    @property
    def duration_minutes(self) -> float:
        return (self.ended_at - self.started_at).total_seconds() / 60.0


# ============================================================
# ENRICHMENT SUB-MODELS
# ============================================================
class RevenueContext(BaseModel):
    service_tier: Literal["tier-0", "tier-1", "tier-2", "tier-3", "unknown"]
    revenue_per_minute_usd: Optional[float] = None
    revenue_critical: bool = False
    business_function: Optional[str] = None


class CustomerTierBreakdown(BaseModel):
    enterprise: int = 0
    mid_market: int = 0
    smb: int = 0
    free: int = 0


class CustomerContext(BaseModel):
    total_affected: int = 0
    by_tier: CustomerTierBreakdown = Field(default_factory=CustomerTierBreakdown)
    named_accounts: list[str] = Field(default_factory=list)
    customer_facing: bool = False


class SLAContext(BaseModel):
    breached: bool = False
    contracts_affected: int = 0
    estimated_credit_liability_usd: float = 0.0
    breached_customer_ids: list[str] = Field(default_factory=list)


class ComplianceContext(BaseModel):
    regulated_data_touched: list[str] = Field(default_factory=list)
    reportable_to_regulator: bool = False
    reputation_risk_score: int = Field(default=1, ge=1, le=5)


class HistoryContext(BaseModel):
    occurrences_last_30d: int = 0
    trend: Literal["improving", "stable", "worsening", "unknown"] = "unknown"
    last_occurrence: Optional[datetime] = None


class BusinessContext(BaseModel):
    revenue: RevenueContext
    customer: CustomerContext
    sla: SLAContext
    compliance: ComplianceContext
    history: HistoryContext
    enrichment_confidence: float = Field(ge=0.0, le=1.0)
    missing_data_flags: list[str] = Field(default_factory=list)


# ============================================================
# OUTPUT: enriched signal passed to Impact Quantifier
# ============================================================
class EnrichedSignal(BaseModel):
    signal_id: str
    raw_signal: RawSignal
    business_context: BusinessContext
    needs_manual_review: bool = False
    enrichment_timestamp: datetime = Field(default_factory=datetime.utcnow)


class EnricherOutput(BaseModel):
    """Final output of the agent."""
    enriched_signals: list[EnrichedSignal]
    skipped_signals: list[dict] = Field(default_factory=list)
    enrichment_duration_ms: int
    mcp_calls_made: int
