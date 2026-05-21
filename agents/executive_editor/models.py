from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, ConfigDict

from agents.impact_quantifier.models import QuantifiedSignal


class Persona(str, Enum):
    CEO  = "CEO"
    CFO  = "CFO"
    CISO = "CISO"
    CTO  = "CTO"
    COO  = "COO"


class StoryTheme(str, Enum):
    REVENUE_INCIDENT     = "revenue_incident"
    SECURITY_THREAT      = "security_threat"
    PERFORMANCE_DEGRAD   = "performance_degradation"
    COST_OVERRUN         = "cost_overrun"
    COMPLIANCE_RISK      = "compliance_risk"
    CAPACITY_RISK        = "capacity_risk"
    DEPLOY_INCIDENT      = "deploy_incident"
    POSITIVE_MILESTONE   = "positive_milestone"
    UNKNOWN              = "unknown"


class StoryCluster(BaseModel):
    """A coherent narrative made from one or more related signals."""
    model_config = ConfigDict(extra="forbid")

    cluster_id: str
    theme: StoryTheme
    headline_hint: str               # short, used by writer as scaffolding
    signal_ids: list[str]
    primary_signal_id: str           # the "lead" signal
    aggregate_priority: float        # 0-100
    aggregate_exposure_usd: float
    persona_relevance: dict[str, float]  # Persona → 0..1


class DecisionAsk(BaseModel):
    decision_id: str
    title: str
    context_one_liner: str
    options: list[dict]              # [{label, cost_usd?, benefit?, risk?}]
    cost_usd: Optional[float] = None
    deadline: Optional[datetime] = None
    owner: str                       # role: "CISO","CFO",...
    supporting_cluster_ids: list[str]


class EditorOutput(BaseModel):
    persona: Persona
    briefing_date: datetime
    headline_cluster_id: str
    clusters: list[StoryCluster]     # already ranked, capped, ordered
    decisions_required: list[DecisionAsk]
    good_news_cluster_id: Optional[str] = None
    skipped_clusters_count: int = 0
    total_exposure_usd_shown: float
