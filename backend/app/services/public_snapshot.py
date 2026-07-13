from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload

from app.models import Attachment, Base, Opportunity, Source

SNAPSHOT_SCHEMA_VERSION = "1"
PUBLIC_TABLE_NAMES = {
    "attachments",
    "opportunities",
    "snapshot_metadata",
    "sources",
}
FORBIDDEN_TABLE_NAMES = {
    "alert_subscriptions",
    "editorial_actions",
    "email_logs",
    "import_runs",
}
SENSITIVE_NULL_COLUMNS = {
    "attachments": ("content_hash", "extracted_text"),
    "opportunities": ("editorial_notes",),
    "sources": ("last_error", "technical_notes"),
}
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")


class SnapshotValidationError(ValueError):
    """Raised when a public snapshot is missing, corrupt, or contains private data."""


@dataclass(frozen=True)
class SnapshotReport:
    path: Path
    generated_at: str
    opportunity_count: int
    source_count: int
    attachment_count: int
    content_digest: str


def _sqlite_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.resolve().as_posix()}"


def _column_values(instance: Any) -> dict[str, Any]:
    return {
        column.name: copy.deepcopy(getattr(instance, column.name))
        for column in instance.__table__.columns
    }


def _is_demo(opportunity: Opportunity) -> bool:
    source = opportunity.source
    if source and source.source_type == "fixture":
        return True
    if source and "demo" in source.name.casefold():
        return True

    urls = [opportunity.official_url]
    if source:
        urls.append(source.base_url)
    for value in urls:
        hostname = urlparse(value or "").hostname or ""
        if hostname == "example.test" or hostname.endswith(".example.test"):
            return True
    return False


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).isoformat()
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _content_digest(
    opportunities: list[Opportunity],
    sources: dict[str, Source],
) -> str:
    source_fields = (
        "id",
        "name",
        "source_type",
        "base_url",
        "region",
        "organization",
        "import_method",
        "refresh_frequency",
    )
    opportunity_fields = (
        "id",
        "external_id",
        "source_id",
        "title",
        "normalized_title",
        "short_description",
        "description",
        "summary",
        "category",
        "areas",
        "psychology_relevance",
        "relevance_score",
        "organization",
        "entity_type",
        "region",
        "province",
        "municipality",
        "original_location",
        "status",
        "published_at",
        "opens_at",
        "deadline",
        "positions",
        "compensation_min",
        "compensation_max",
        "compensation_period",
        "duration",
        "contract_type",
        "requirements",
        "application_mode",
        "official_url",
        "organization_url",
        "search_text",
        "is_featured",
    )
    payload = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "sources": [
            {field: _json_value(getattr(source, field)) for field in source_fields}
            for source in sorted(sources.values(), key=lambda item: item.id)
        ],
        "opportunities": [
            {
                **{
                    field: _json_value(getattr(opportunity, field))
                    for field in opportunity_fields
                },
                "attachments": [
                    {
                        "id": attachment.id,
                        "title": attachment.title,
                        "url": attachment.url,
                        "file_type": attachment.file_type,
                        "file_size": attachment.file_size,
                    }
                    for attachment in sorted(
                        opportunity.attachments,
                        key=lambda item: item.id,
                    )
                ],
            }
            for opportunity in opportunities
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def export_public_snapshot(
    source_session: Session,
    destination: Path,
    *,
    generated_at: datetime | None = None,
) -> SnapshotReport:
    """Export approved public records into a new, privacy-minimized SQLite file."""
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)

    opportunities = list(
        source_session.scalars(
            select(Opportunity)
            .where(Opportunity.editorial_status == "approved")
            .options(
                selectinload(Opportunity.source),
                selectinload(Opportunity.attachments),
            )
            .order_by(Opportunity.id)
        ).all()
    )
    opportunities = [item for item in opportunities if not _is_demo(item)]
    sources = {
        item.source.id: item.source
        for item in opportunities
        if item.source is not None
    }
    digest = _content_digest(opportunities, sources)
    timestamp = (generated_at or datetime.now(UTC)).astimezone(UTC).isoformat()

    public_engine = create_engine(_sqlite_url(destination))
    Base.metadata.create_all(
        bind=public_engine,
        tables=[Source.__table__, Opportunity.__table__, Attachment.__table__],
    )
    with Session(public_engine) as public_session:
        for source in sorted(sources.values(), key=lambda item: item.id):
            values = _column_values(source)
            values["status"] = "active"
            values["last_success_at"] = None
            values["last_error"] = None
            values["technical_notes"] = None
            public_session.add(Source(**values))

        for opportunity in opportunities:
            values = _column_values(opportunity)
            values["content_hash"] = None
            values["editorial_status"] = "approved"
            values["editorial_notes"] = None
            public_session.add(Opportunity(**values))
            for attachment in sorted(opportunity.attachments, key=lambda item: item.id):
                attachment_values = _column_values(attachment)
                attachment_values["content_hash"] = None
                attachment_values["extracted_text"] = None
                attachment_values["indexed_at"] = None
                public_session.add(Attachment(**attachment_values))
        public_session.commit()
    public_engine.dispose()

    metadata = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_at": timestamp,
        "opportunity_count": str(len(opportunities)),
        "source_count": str(len(sources)),
        "attachment_count": str(
            sum(len(opportunity.attachments) for opportunity in opportunities)
        ),
        "content_digest": digest,
    }
    with sqlite3.connect(destination) as connection:
        connection.execute(
            "CREATE TABLE snapshot_metadata "
            "(key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO snapshot_metadata (key, value) VALUES (?, ?)",
            sorted(metadata.items()),
        )
        connection.commit()
        connection.execute("VACUUM")

    return validate_public_snapshot(destination)


def _read_metadata(connection: sqlite3.Connection) -> dict[str, str]:
    return dict(connection.execute("SELECT key, value FROM snapshot_metadata").fetchall())


def _validated_count(metadata: dict[str, str], key: str) -> int:
    try:
        value = int(metadata[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise SnapshotValidationError(f"Metadato non valido: {key}") from exc
    if value < 0:
        raise SnapshotValidationError(f"Metadato negativo: {key}")
    return value


def validate_public_snapshot(path: Path) -> SnapshotReport:
    """Verify integrity, table allowlist, counts, sanitized fields, and URL safety."""
    path = path.resolve()
    if not path.is_file():
        raise SnapshotValidationError(f"Snapshot non trovato: {path}")

    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        with connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            if integrity != ("ok",):
                raise SnapshotValidationError("Controllo di integrita SQLite fallito")

            table_names = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
                if not row[0].startswith("sqlite_")
            }
            if table_names != PUBLIC_TABLE_NAMES:
                raise SnapshotValidationError(
                    "Tabelle pubbliche inattese: "
                    f"attese={sorted(PUBLIC_TABLE_NAMES)}, trovate={sorted(table_names)}"
                )
            if table_names & FORBIDDEN_TABLE_NAMES:
                raise SnapshotValidationError("Lo snapshot contiene tabelle riservate")

            metadata = _read_metadata(connection)
            if metadata.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
                raise SnapshotValidationError("Versione dello snapshot non supportata")
            digest = metadata.get("content_digest", "")
            if not _DIGEST_PATTERN.fullmatch(digest):
                raise SnapshotValidationError("Digest dello snapshot non valido")

            expected_counts = {
                "opportunities": _validated_count(metadata, "opportunity_count"),
                "sources": _validated_count(metadata, "source_count"),
                "attachments": _validated_count(metadata, "attachment_count"),
            }
            for table_name, expected in expected_counts.items():
                actual = connection.execute(
                    f'SELECT COUNT(*) FROM "{table_name}"'
                ).fetchone()[0]
                if actual != expected:
                    raise SnapshotValidationError(
                        f"Conteggio incoerente per {table_name}: {actual} != {expected}"
                    )

            non_public = connection.execute(
                "SELECT COUNT(*) FROM opportunities WHERE editorial_status != 'approved'"
            ).fetchone()[0]
            if non_public:
                raise SnapshotValidationError("Sono presenti opportunita non approvate")

            for table_name, columns in SENSITIVE_NULL_COLUMNS.items():
                condition = " OR ".join(f'"{column}" IS NOT NULL' for column in columns)
                exposed = connection.execute(
                    f'SELECT COUNT(*) FROM "{table_name}" WHERE {condition}'
                ).fetchone()[0]
                if exposed:
                    raise SnapshotValidationError(
                        f"Campi riservati valorizzati nella tabella {table_name}"
                    )

            url_queries = (
                "SELECT base_url FROM sources",
                "SELECT official_url FROM opportunities",
                "SELECT organization_url FROM opportunities WHERE organization_url IS NOT NULL",
                "SELECT url FROM attachments",
            )
            for query in url_queries:
                for (url,) in connection.execute(query):
                    parsed = urlparse(url or "")
                    if parsed.username is not None or parsed.password is not None:
                        raise SnapshotValidationError("Una URL pubblica contiene credenziali")
    except sqlite3.Error as exc:
        raise SnapshotValidationError(f"Snapshot SQLite non leggibile: {exc}") from exc
    finally:
        if "connection" in locals():
            connection.close()

    generated_at = metadata.get("generated_at", "")
    try:
        datetime.fromisoformat(generated_at)
    except ValueError as exc:
        raise SnapshotValidationError("Data di generazione non valida") from exc

    return SnapshotReport(
        path=path,
        generated_at=generated_at,
        opportunity_count=expected_counts["opportunities"],
        source_count=expected_counts["sources"],
        attachment_count=expected_counts["attachments"],
        content_digest=digest,
    )


def publish_snapshot(candidate: Path, destination: Path) -> tuple[SnapshotReport, bool]:
    """Atomically publish a valid candidate only when its public content changed."""
    candidate_report = validate_public_snapshot(candidate)
    destination = destination.resolve()
    if destination.exists():
        try:
            current_report = validate_public_snapshot(destination)
        except SnapshotValidationError:
            current_report = None
        if (
            current_report is not None
            and current_report.content_digest == candidate_report.content_digest
        ):
            return current_report, False

    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(candidate, destination)
    return validate_public_snapshot(destination), True
