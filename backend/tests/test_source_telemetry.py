from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, ImportRun, Source
from app.services.source_telemetry import (
    collect_source_telemetry,
    track_source_attempt,
)


def test_tracks_each_attempted_source_and_excludes_unattempted_sources() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    since = datetime.now(UTC) - timedelta(seconds=1)

    with Session(engine) as db:
        successful = Source(
            name="Fonte riuscita",
            source_type="html-list",
            base_url="https://success.test",
            import_method="catalog-html",
        )
        failed = Source(
            name="Fonte fallita",
            source_type="html-list",
            base_url="https://failed.test",
            import_method="catalog-html",
        )
        untouched = Source(
            name="Fonte non interrogata",
            source_type="html-list",
            base_url="https://untouched.test",
            import_method="catalog-html",
        )
        db.add_all([successful, failed, untouched])
        db.flush()

        with track_source_attempt(db, successful) as attempt:
            attempt.created(2)
            attempt.updated()

        with track_source_attempt(db, failed) as attempt:
            attempt.skipped()
            attempt.fail(RuntimeError("timeout"))

        db.commit()
        report = collect_source_telemetry(db, since=since)

    assert report.catalogued_count == 3
    assert report.attempted_source_count == 2
    assert report.successful_source_count == 1
    assert report.failed_source_count == 1
    assert report.not_attempted_source_count == 1
    attempts_by_source = {item.source_name: item for item in report.attempts}
    assert {
        name: item.status for name, item in attempts_by_source.items()
    } == {
        "Fonte riuscita": "success",
        "Fonte fallita": "failed",
    }
    assert attempts_by_source["Fonte riuscita"].created_count == 2
    assert attempts_by_source["Fonte riuscita"].updated_count == 1


def test_unhandled_exception_marks_attempt_failed() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        source = Source(
            name="Fonte",
            source_type="html",
            base_url="https://example.test",
        )
        db.add(source)
        db.flush()
        try:
            with track_source_attempt(db, source):
                raise ValueError("risposta non valida")
        except ValueError:
            pass
        db.commit()
        run = db.query(ImportRun).filter(ImportRun.source_id == source.id).one()

    assert run.status == "failed"
    assert run.finished_at is not None
    assert run.error_message == "risposta non valida"
