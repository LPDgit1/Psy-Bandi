from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from threading import Event, Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, public
from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.importers.inpa import run_inpa_import
from app.importers.sample_fixture import run_sample_import
from app.models import Base
from app.services.alert_notifications import send_due_alert_reports
from app.services.deadline_status import refresh_deadline_statuses
from app.services.import_pipeline import INSTITUTIONAL_IMPORTERS
from app.services.public_refresh import acquire_import_lock, release_import_lock
from app.services.source_probe import ensure_source_catalog

logger = logging.getLogger(__name__)


def _run_startup_imports() -> None:
    if not acquire_import_lock():
        logger.info("Startup imports skipped: another refresh is already running")
        return
    try:
        with SessionLocal() as db:
            if settings.seed_on_startup:
                try:
                    run_sample_import(db)
                except Exception:
                    logger.exception("Startup sample import failed")
            if settings.inpa_import_on_startup:
                try:
                    run_inpa_import(db, remove_demo=settings.remove_demo_on_startup)
                except Exception:
                    logger.exception("Startup inPA import failed")
            if settings.institutional_import_on_startup:
                for label, importer in INSTITUTIONAL_IMPORTERS:
                    try:
                        importer(db)
                    except Exception:
                        logger.exception("Startup importer failed: %s", label)
            refresh_deadline_statuses(db)
    finally:
        release_import_lock()


def _run_alert_scheduler(stop_event: Event) -> None:
    if stop_event.wait(settings.alert_scheduler_initial_delay_seconds):
        return
    while not stop_event.is_set():
        try:
            with SessionLocal() as db:
                send_due_alert_reports(db)
        except Exception:
            logger.exception("Scheduled alert delivery failed")
        if stop_event.wait(settings.alert_scheduler_interval_seconds):
            return


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_source_catalog(db)
        db.commit()
        refresh_deadline_statuses(db)
    if (
        settings.seed_on_startup
        or settings.inpa_import_on_startup
        or settings.institutional_import_on_startup
    ):
        Thread(target=_run_startup_imports, name="startup-imports", daemon=True).start()
    alert_stop_event = Event()
    alert_thread: Thread | None = None
    if settings.alert_scheduler_enabled:
        alert_thread = Thread(
            target=_run_alert_scheduler,
            args=(alert_stop_event,),
            name="alert-scheduler",
            daemon=True,
        )
        alert_thread.start()
    try:
        yield
    finally:
        alert_stop_event.set()
        if alert_thread is not None:
            alert_thread.join(timeout=2)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(admin.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
