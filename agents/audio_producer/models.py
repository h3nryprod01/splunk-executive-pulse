from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ChapterMarker(BaseModel):
    start_sec: float
    title: str


class AudioOutput(BaseModel):
    audio_url: str
    local_path: str
    duration_sec: int
    waveform_url: Optional[str] = None
    chapters: list[ChapterMarker]
    voice_preset: str
    file_size_bytes: int
    expires_at: datetime
    generated_at: datetime = Field(default_factory=datetime.utcnow)
