from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AttachmentRead(BaseModel):
    id: str
    title: str
    url: str
    file_type: str | None = None


class OpportunityListItem(BaseModel):
    id: str
    title: str
    organization: str
    entity_type: str
    region: str | None = None
    province: str | None = None
    municipality: str | None = None
    category: str
    areas: list[str]
    status: str
    deadline: datetime | None = None
    psychology_relevance: str
    relevance_score: int
    requirements: list[str]
    source_name: str | None = None
    official_url: str
    is_featured: bool = False
    summary: str | None = None
    updated_at: datetime


class OpportunityDetail(OpportunityListItem):
    short_description: str | None = None
    description: str | None = None
    published_at: datetime | None = None
    opens_at: datetime | None = None
    positions: int | None = None
    compensation_min: int | None = None
    compensation_max: int | None = None
    compensation_period: str | None = None
    duration: str | None = None
    contract_type: str | None = None
    application_mode: str | None = None
    organization_url: str | None = None
    attachments: list[AttachmentRead] = Field(default_factory=list)


class FacetValue(BaseModel):
    value: str
    count: int


class Facets(BaseModel):
    regions: list[FacetValue] = Field(default_factory=list)
    provinces: list[FacetValue] = Field(default_factory=list)
    categories: list[FacetValue] = Field(default_factory=list)
    entity_types: list[FacetValue] = Field(default_factory=list)
    areas: list[FacetValue] = Field(default_factory=list)
    statuses: list[FacetValue] = Field(default_factory=list)


class OpportunityListResponse(BaseModel):
    items: list[OpportunityListItem]
    total: int
    limit: int
    offset: int
    facets: Facets


class AlertCreate(BaseModel):
    email: EmailStr
    regions: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    frequency: Literal["daily", "weekly"] = "weekly"


class AlertResponse(BaseModel):
    id: str
    status: str
    message: str
    confirm_token: str | None = None


class AlertReportResponse(BaseModel):
    id: str
    status: str
    matched_count: int
    message: str
    email_log_id: str | None = None


class RefreshSourceResult(BaseModel):
    label: str
    status: str
    source_id: str | None = None
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error: str | None = None


class RefreshResponse(BaseModel):
    status: str
    message: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    retry_after_seconds: int | None = None
    sources: list[RefreshSourceResult] = Field(default_factory=list)


class ReportCreate(BaseModel):
    opportunity_id: str | None = None
    email: EmailStr | None = None
    message: str = Field(min_length=5, max_length=2000)


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OpportunityPatch(BaseModel):
    title: str | None = None
    summary: str | None = None
    category: str | None = None
    areas: list[str] | None = None
    organization: str | None = None
    entity_type: str | None = None
    region: str | None = None
    province: str | None = None
    municipality: str | None = None
    status: str | None = None
    deadline: datetime | None = None
    compensation_min: int | None = None
    compensation_max: int | None = None
    compensation_period: str | None = None
    duration: str | None = None
    contract_type: str | None = None
    requirements: list[str] | None = None
    editorial_status: str | None = None
    editorial_notes: str | None = None
    is_featured: bool | None = None


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    source_type: str
    base_url: str
    region: str | None = None
    organization: str | None = None
    import_method: str
    refresh_frequency: str
    status: str
    last_success_at: datetime | None = None
    last_error: str | None = None


class ImportRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    created_count: int
    updated_count: int
    skipped_count: int
    error_message: str | None = None
