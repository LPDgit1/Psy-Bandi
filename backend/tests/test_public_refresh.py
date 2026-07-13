from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Base, ImportRun
from app.services import public_refresh
from app.services.import_pipeline import SourceImportSummary


def test_public_refresh_runs_pipeline_and_enforces_cooldown(monkeypatch) -> None:
    monkeypatch.setattr(public_refresh, "_last_refresh_finished_at", None)
    monkeypatch.setattr(
        public_refresh,
        "run_active_source_imports",
        lambda db, remove_demo: [
            SourceImportSummary(
                label="inPA",
                status="success",
                source_id="src_inpa",
                created_count=2,
                updated_count=3,
                skipped_count=4,
            )
        ],
    )
    monkeypatch.setattr(public_refresh, "refresh_deadline_statuses", lambda db: 0)
    monkeypatch.setattr(public_refresh, "mark_stale_import_runs_failed", lambda db, now: 0)

    completed = public_refresh.run_public_refresh(object())
    cooldown = public_refresh.run_public_refresh(object())

    assert completed["status"] == "completed"
    assert completed["created_count"] == 2
    assert completed["updated_count"] == 3
    assert completed["skipped_count"] == 4
    assert cooldown["status"] == "cooldown"
    assert cooldown["retry_after_seconds"] > 0


def test_mark_stale_import_runs_failed_closes_old_running_rows() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)

    with Session(engine) as db:
        stale = ImportRun(
            status="running",
            started_at=now - timedelta(hours=1),
        )
        recent = ImportRun(
            status="running",
            started_at=now - timedelta(minutes=5),
        )
        db.add_all([stale, recent])
        db.commit()

        changed = public_refresh.mark_stale_import_runs_failed(db, now=now)

        assert changed == 1
        rows = list(db.scalars(select(ImportRun).order_by(ImportRun.started_at)))
        assert rows[0].status == "failed"
        assert rows[0].finished_at == now.replace(tzinfo=None)
        assert "interrotto" in (rows[0].error_message or "")
        assert rows[1].status == "running"
        assert rows[1].finished_at is None


def test_queued_refresh_returns_immediately_and_exposes_final_status(monkeypatch) -> None:
    class FakeSession:
        def __enter__(self):
            return object()

        def __exit__(self, *_args) -> None:
            return None

    class ImmediateThread:
        def __init__(self, *, target, **_kwargs) -> None:
            self.target = target

        def start(self) -> None:
            self.target()

    monkeypatch.setattr(public_refresh, "SessionLocal", FakeSession)
    monkeypatch.setattr(public_refresh, "Thread", ImmediateThread)
    monkeypatch.setattr(
        public_refresh,
        "run_public_refresh",
        lambda _db, **_kwargs: {
            "status": "completed",
            "message": "Fatto",
            "created_count": 1,
            "sources": [],
        },
    )
    public_refresh._refresh_state.clear()
    public_refresh._refresh_state.update({"status": "idle", "sources": []})

    queued = public_refresh.queue_public_refresh()
    final = public_refresh.get_public_refresh_status()

    assert queued["status"] == "running"
    assert final["status"] == "completed"
    assert final["created_count"] == 1
