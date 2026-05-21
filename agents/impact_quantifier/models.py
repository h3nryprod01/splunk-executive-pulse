# agents/impact_quantifier/models.py
from __future__ import annotations
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict

# Import the upstream type — single source of truth
from agents.business_enricher.models import EnrichedSignal


class CalculationStep(BaseModel):
    """
    A single, transparent calculation step.
    Used to render 'methodology' tooltips in the UI.
    """
    label: str                            # e.g., "Direct revenue loss"
    formula: str                          # human-readable formula
    inputs: dict[str, float]              # name → value
    result_usd: float
    confidence: float = Field(ge=0.0, le=1.0)
    notes: Optional[str] = None


class FinancialImpact(BaseModel):
    """All financial impacts for one signal, fully cited."""
    direct_revenue_loss_usd: float = 0.0
    indirect_exposure_usd: float = 0.0
    sla_credit_liability_usd: float = 0.0
    incident_response_cost_usd: float = 0.0
    cost_overrun_usd: float = 0.0
    total_exposure_usd: float = 0.0

    calculations: list[CalculationStep] = Field(default_factory=list)
    aggregated_confidence: float = Field(ge=0.0, le=1.0)


class CustomerImpactScore(BaseModel):
    affected_count: int = 0
    tier_weighted_score: float = 0.0
    named_accounts_affected: list[str] = Field(default_factory=list)


class QuantifiedSignal(BaseModel):
    """Output of the Impact Quantifier — one per enriched signal."""
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    enriched: EnrichedSignal
    financial_impact: FinancialImpact
    customer_impact: CustomerImpactScore

    priority_score: float = Field(ge=0.0, le=100.0)
    executive_attention_required: bool
    qualitative_only: bool = False        # true when confidence too low for $

    quantified_at: datetime = Field(default_factory=datetime.utcnow)


class QuantifierOutput(BaseModel):
    quantified_signals: list[QuantifiedSignal]
    total_exposure_usd: float
    highest_priority_score: float
    failed_quantifications: list[dict] = Field(default_factory=list)
    duration_ms: int
