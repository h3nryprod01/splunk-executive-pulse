# agents/narrative_writer/models.py
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    claim_text: str               # the exact substring in script
    source_signal_id: str
    methodology: str              # e.g., "$3,916/min × 12 min"
    confidence: float = Field(ge=0.0, le=1.0)
    splunk_query: Optional[str] = None
    splunk_dashboard_url: Optional[str] = None


class DrillDownLink(BaseModel):
    cluster_id: str
    headline: str
    splunk_dashboard_url: str


class NarrativeScript(BaseModel):
    """The audio-ready output of the writer."""
    model_config = ConfigDict(extra="forbid")

    script_text: str
    ssml_version: str
    persona: str
    briefing_date: datetime

    estimated_duration_sec: int
    word_count: int

    citations: list[Citation]
    drill_down_links: list[DrillDownLink]

    # Provenance for debugging / auditing
    llm_model_used: str
    llm_passes: int               # how many revision passes
    self_critique_score: float = Field(ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class WriterValidationError(Exception):
    """Raised when a script cannot be validated even after retries."""
