from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("src"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), default="html")
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    import_method: Mapped[str] = mapped_column(String(80), default="manual")
    refresh_frequency: Mapped[str] = mapped_column(String(80), default="daily")
    status: Mapped[str] = mapped_column(String(40), default="active")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    opportunities: Mapped[list[Opportunity]] = relationship(back_populates="source")


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("opp"))
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), nullable=True)

    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[str] = mapped_column(String(80), default="altro", index=True)
    areas: Mapped[list[str]] = mapped_column(JSON, default=list)
    psychology_relevance: Mapped[str] = mapped_column(String(40), default="media", index=True)
    relevance_score: Mapped[int] = mapped_column(Integer, default=0)

    organization: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(120), default="altro-ente-pubblico")
    region: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    province: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    municipality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    original_location: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    positions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compensation_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compensation_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compensation_period: Mapped[str | None] = mapped_column(String(40), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contract_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    requirements: Mapped[list[str]] = mapped_column(JSON, default=list)
    application_mode: Mapped[str | None] = mapped_column(Text, nullable=True)

    official_url: Mapped[str] = mapped_column(Text, nullable=False)
    organization_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    search_text: Mapped[str] = mapped_column(Text, default="")

    editorial_status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    editorial_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    source: Mapped[Source | None] = relationship(back_populates="opportunities")
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="opportunity",
        cascade="all, delete-orphan",
    )


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("att"))
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    opportunity: Mapped[Opportunity] = relationship(back_populates="attachments")


class AlertSubscription(Base, TimestampMixin):
    __tablename__ = "alert_subscriptions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sub"))
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending")
    confirm_token: Mapped[str] = mapped_column(String(120), default=lambda: uuid.uuid4().hex)
    regions: Mapped[list[str]] = mapped_column(JSON, default=list)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    areas: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    frequency: Mapped[str] = mapped_column(String(40), default="weekly")
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmailLog(Base, TimestampMixin):
    __tablename__ = "email_logs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("eml"))
    alert_subscription_id: Mapped[str | None] = mapped_column(
        ForeignKey("alert_subscriptions.id"),
        nullable=True,
    )
    recipient: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    delivery_mode: Mapped[str] = mapped_column(String(40), default="file")
    provider_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EditorialAction(Base):
    __tablename__ = "editorial_actions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("act"))
    admin_user: Mapped[str] = mapped_column(String(255), nullable=False)
    opportunity_id: Mapped[str | None] = mapped_column(
        ForeignKey("opportunities.id"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("run"))
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
