from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class StepStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ERROR = "error"


class InvestigationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class SkippedCore(BaseModel):
    core: str
    reason: str


class Interpretation(BaseModel):
    source: Literal["ai"] = "ai"
    need: str
    searchQueries: dict[str, str]
    skippedCores: list[SkippedCore] = Field(default_factory=list)


class StepState(BaseModel):
    id: str
    label: str
    status: StepStatus = StepStatus.QUEUED
    detail: str | None = None
    tool: str | None = None
    query: str | None = None


class Organization(BaseModel):
    name: str
    sourceField: str
    sourceRecordIds: list[str]


class CoreEvidence(BaseModel):
    core: str
    tool: str
    arguments: dict[str, Any]
    records: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class Investigation(BaseModel):
    id: str
    query: str
    status: InvestigationStatus = InvestigationStatus.RUNNING
    interpretation: Interpretation
    steps: list[StepState]
    evidence: dict[str, CoreEvidence] = Field(default_factory=dict)
    organizations: list[Organization] = Field(default_factory=list)


class CreateInvestigationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class CoreIngestRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    records: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
