"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class CreateAnalysisRequest(BaseModel):
    repo_url: HttpUrl


class CreateAnalysisResponse(BaseModel):
    id: str
    slug: str


class AnalysisResult(BaseModel):
    id: str
    slug: str
    status: str
    error: str | None = None
    facts_summary: dict | None = None
    services: list | None = None
    zerops_yaml: str | None = None
    yaml_valid: bool = False
    checklist: list | None = None
    timings: dict | None = None
    created_at: datetime
    completed_at: datetime | None = None
