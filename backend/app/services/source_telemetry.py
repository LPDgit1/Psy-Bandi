from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ImportRun, Source


class SourceAttempt:
    """Mutable counter facade backed by one per-source ImportRun row."""

    def __init__(self, run: ImportRun) -> None:
        self.run = run

    def created(self, count: int = 1) -> None:
        self.run.created_count += count

    def updated(self, count: int = 1) -> None:
        self.run.updated_count += count

    def skipped(self, count: int = 1) -> None:
        self.run.skipped_count += count

    def fail(self, exc: Exception) -> None:
        self.run.status = "failed"
        self.run.error_message = str(exc)

    def finish(self) -> None:
        if self.run.status == "running":
            self.run.status = "success"
        self.run.finished_at = datetime.now(UTC)


def start_source_attempt(db: Session, source: Source) -> SourceAttempt:
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    return SourceAttempt(run)


@contextmanager
def track_source_attempt(db: Session, source: Source) -> Iterator[SourceAttempt]:
    """Record one actual source attempt, excluding sources skipped before entry."""

    attempt = start_source_attempt(db, source)
    try:
        yield attempt
    except Exception as exc:
        attempt.fail(exc)
        raise
    finally:
        attempt.finish()


@dataclass(frozen=True)
class SourceAttemptSummary:
    source_id: str
    source_name: str
    source_type: str
    import_method: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    created_count: int
    updated_count: int
    skipped_count: int
    error: str | None


@dataclass(frozen=True)
class SourceTelemetryReport:
    catalogued_count: int
    attempted_source_count: int
    successful_source_count: int
    failed_source_count: int
    not_attempted_source_count: int
    attempts: list[SourceAttemptSummary]


def collect_source_telemetry(
    db: Session,
    *,
    since: datetime,
) -> SourceTelemetryReport:
    rows = db.execute(
        select(ImportRun, Source)
        .join(Source, ImportRun.source_id == Source.id)
        .where(ImportRun.source_id.is_not(None), ImportRun.started_at >= since)
        .order_by(ImportRun.started_at, Source.name)
    ).all()
    attempts = [
        SourceAttemptSummary(
            source_id=source.id,
            source_name=source.name,
            source_type=source.source_type,
            import_method=source.import_method,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            created_count=run.created_count,
            updated_count=run.updated_count,
            skipped_count=run.skipped_count,
            error=run.error_message,
        )
        for run, source in rows
    ]
    catalogued_count = db.scalar(select(func.count()).select_from(Source)) or 0
    attempted_source_ids = {attempt.source_id for attempt in attempts}
    failed_source_ids = {attempt.source_id for attempt in attempts if attempt.status == "failed"}
    successful_source_ids = attempted_source_ids - failed_source_ids
    return SourceTelemetryReport(
        catalogued_count=catalogued_count,
        attempted_source_count=len(attempted_source_ids),
        successful_source_count=len(successful_source_ids),
        failed_source_count=len(failed_source_ids),
        not_attempted_source_count=max(catalogued_count - len(attempted_source_ids), 0),
        attempts=attempts,
    )


def _single_line(value: str | None, *, limit: int = 240) -> str | None:
    if not value:
        return None
    return " ".join(value.split())[:limit]


def print_source_telemetry(report: SourceTelemetryReport) -> None:
    print(
        "Telemetria fonti: "
        f"{report.attempted_source_count}/{report.catalogued_count} interrogate; "
        f"{report.successful_source_count} riuscite; "
        f"{report.failed_source_count} fallite; "
        f"{report.not_attempted_source_count} non interrogate."
    )
    for attempt in report.attempts:
        payload = asdict(attempt)
        payload["started_at"] = attempt.started_at.isoformat()
        payload["finished_at"] = attempt.finished_at.isoformat() if attempt.finished_at else None
        payload["error"] = _single_line(attempt.error)
        print("SOURCE_TELEMETRY " + json.dumps(payload, ensure_ascii=False, sort_keys=True))


def append_github_step_summary(report: SourceTelemetryReport) -> None:
    configured = os.getenv("GITHUB_STEP_SUMMARY")
    if not configured:
        return
    path = Path(configured)
    lines = [
        "## Telemetria fonti",
        "",
        (
            f"Interrogate **{report.attempted_source_count}** su "
            f"**{report.catalogued_count}**: "
            f"{report.successful_source_count} riuscite, "
            f"{report.failed_source_count} fallite, "
            f"{report.not_attempted_source_count} non interrogate."
        ),
        "",
        "| Fonte | Adapter | Stato | Creati | Aggiornati | Scartati |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for attempt in report.attempts:
        name = attempt.source_name.replace("|", "\\|")
        method = attempt.import_method.replace("|", "\\|")
        lines.append(
            f"| {name} | {method} | {attempt.status} | "
            f"{attempt.created_count} | {attempt.updated_count} | "
            f"{attempt.skipped_count} |"
        )
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
