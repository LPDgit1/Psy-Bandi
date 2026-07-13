from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from threading import Lock, Thread
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import ImportRun
from app.services.deadline_status import refresh_deadline_statuses
from app.services.import_pipeline import run_active_source_imports

_refresh_lock = Lock()
_refresh_state_lock = Lock()
_last_refresh_finished_at: datetime | None = None
_refresh_state: dict[str, Any] = {
    "status": "idle",
    "message": "Nessun aggiornamento avviato in questa sessione.",
    "sources": [],
}
STALE_IMPORT_RUN_AFTER = timedelta(minutes=30)


def mark_stale_import_runs_failed(
    db: Session,
    *,
    now: datetime | None = None,
    stale_after: timedelta = STALE_IMPORT_RUN_AFTER,
) -> int:
    current = now or datetime.now(UTC)
    cutoff = current - stale_after
    stale_runs = list(
        db.scalars(
            select(ImportRun)
            .where(ImportRun.status == "running", ImportRun.started_at < cutoff)
            .order_by(ImportRun.started_at)
        )
    )
    for run in stale_runs:
        run.status = "failed"
        run.finished_at = current
        run.error_message = (
            "Import interrotto o non completato: marcato automaticamente come "
            "fallito prima di un nuovo refresh."
        )
    if stale_runs:
        db.commit()
    return len(stale_runs)


def acquire_import_lock(*, blocking: bool = False) -> bool:
    return _refresh_lock.acquire(blocking=blocking)


def release_import_lock() -> None:
    _refresh_lock.release()


def run_public_refresh(
    db: Session,
    *,
    wait_for_lock: bool = False,
) -> dict[str, Any]:
    global _last_refresh_finished_at

    started_at = datetime.now(UTC)
    if not acquire_import_lock(blocking=wait_for_lock):
        return {
            "status": "running",
            "message": "Aggiornamento gia in corso. I risultati appariranno tra poco.",
            "retry_after_seconds": 15,
            "sources": [],
        }

    try:
        if _last_refresh_finished_at is not None:
            elapsed = int((started_at - _last_refresh_finished_at).total_seconds())
            retry_after = max(settings.public_refresh_cooldown_seconds - elapsed, 0)
            if retry_after:
                return {
                    "status": "cooldown",
                    "message": (
                        "Fonti aggiornate di recente. "
                        f"Nuovo controllo disponibile tra {retry_after} secondi."
                    ),
                    "retry_after_seconds": retry_after,
                    "sources": [],
                }

        mark_stale_import_runs_failed(db, now=started_at)
        results = run_active_source_imports(db, remove_demo=True)
        refresh_deadline_statuses(db)
        finished_at = datetime.now(UTC)
        _last_refresh_finished_at = finished_at
        failed_count = sum(result.status == "failed" for result in results)
        completed_count = len(results) - failed_count
        status = "completed" if failed_count == 0 else "partial"
        message = (
            f"Aggiornamento completato: {completed_count} fonti verificate."
            if failed_count == 0
            else (
                f"Aggiornamento completato: {completed_count} fonti verificate, "
                f"{failed_count} da ricontrollare."
            )
        )
        return {
            "status": status,
            "message": message,
            "started_at": started_at,
            "finished_at": finished_at,
            "created_count": sum(result.created_count for result in results),
            "updated_count": sum(result.updated_count for result in results),
            "skipped_count": sum(result.skipped_count for result in results),
            "retry_after_seconds": settings.public_refresh_cooldown_seconds,
            "sources": [asdict(result) for result in results],
        }
    finally:
        release_import_lock()


def get_public_refresh_status() -> dict[str, Any]:
    with _refresh_state_lock:
        return dict(_refresh_state)


def _run_queued_public_refresh() -> None:
    try:
        with SessionLocal() as db:
            result = run_public_refresh(db, wait_for_lock=True)
    except Exception as exc:
        result = {
            "status": "failed",
            "message": "Aggiornamento non completato per un errore tecnico.",
            "finished_at": datetime.now(UTC),
            "sources": [],
            "error": str(exc),
        }
    with _refresh_state_lock:
        _refresh_state.clear()
        _refresh_state.update(result)


def queue_public_refresh() -> dict[str, Any]:
    started_at = datetime.now(UTC)
    with _refresh_state_lock:
        if _refresh_state.get("status") == "running":
            return dict(_refresh_state)
        _refresh_state.clear()
        _refresh_state.update(
            {
                "status": "running",
                "message": "Aggiornamento delle fonti avviato. Puoi continuare a usare la ricerca.",
                "started_at": started_at,
                "retry_after_seconds": 3,
                "sources": [],
            }
        )
        response = dict(_refresh_state)
    Thread(
        target=_run_queued_public_refresh,
        name="public-source-refresh",
        daemon=True,
    ).start()
    return response
