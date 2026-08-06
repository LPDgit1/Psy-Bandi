from __future__ import annotations

import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.base import ImportResult
from app.importers.catalog_sources import (
    CatalogRecord,
    _fetch_text,
    _payload,
    align_existing_catalog_record,
)
from app.importers.institutional import upsert_opportunity
from app.importers.public_institutions import (
    collect_public_detail_links,
    parse_public_institution_records,
)
from app.models import ImportRun, Source
from app.regional_municipal_catalog import (
    REGIONAL_MUNICIPAL_SOURCE_NAMES,
)
from app.services.source_probe import _probe_error_status, ensure_source_catalog
from app.services.source_telemetry import start_source_attempt


MAX_DETAIL_LINKS_PER_SOURCE = 12
MAX_RECORDS_PER_SOURCE = 25


def collect_regional_municipal_detail_links(
    html: str,
    base_url: str,
    *,
    limit: int = MAX_DETAIL_LINKS_PER_SOURCE,
) -> list[str]:
    """Discover same-domain recruitment pages for regional/municipal portals."""

    return collect_public_detail_links(html, base_url, limit=limit)


def parse_regional_municipal_records(
    source: Source,
    html: str,
    page_url: str,
) -> list[CatalogRecord]:
    """Use the shared heterogeneous HTML parser for local-government layouts."""

    return parse_public_institution_records(source, html, page_url)[:MAX_RECORDS_PER_SOURCE]


def _sources_for_regional_municipal(db: Session) -> list[Source]:
    ensure_source_catalog(db)
    return list(
        db.scalars(
            select(Source)
            .where(Source.name.in_(REGIONAL_MUNICIPAL_SOURCE_NAMES))
            .order_by(Source.name)
        )
    )


def run_regional_municipal_sources_import(db: Session) -> ImportResult:
    """Refresh the eight missing regions and the missing provincial-capital portals."""

    run = ImportRun(source_id=None, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        import_deadline = time.monotonic() + settings.deep_adapter_budget_seconds
        with httpx.Client(
            timeout=httpx.Timeout(10, connect=5),
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={
                "User-Agent": "BandiPsicologiaMVP/0.1 (+adapter regioni e capoluoghi)"
            },
        ) as client:
            for source in _sources_for_regional_municipal(db):
                if time.monotonic() > import_deadline:
                    skipped += 1
                    continue
                attempt = start_source_attempt(db, source)
                try:
                    html = _fetch_text(client, source.base_url)
                    if html is None:
                        skipped += 1
                        attempt.skipped()
                        continue

                    records_by_id = {
                        record.external_id: record
                        for record in parse_regional_municipal_records(
                            source, html, source.base_url
                        )
                    }
                    for detail_url in collect_regional_municipal_detail_links(
                        html, source.base_url
                    ):
                        if time.monotonic() > import_deadline:
                            break
                        detail_html = _fetch_text(client, detail_url)
                        if detail_html is None:
                            skipped += 1
                            attempt.skipped()
                            continue
                        records_by_id.update(
                            {
                                record.external_id: record
                                for record in parse_regional_municipal_records(
                                    source, detail_html, detail_url
                                )
                            }
                        )
                        if len(records_by_id) >= MAX_RECORDS_PER_SOURCE:
                            break

                    if not records_by_id:
                        attempt.skipped()
                    for record in list(records_by_id.values())[:MAX_RECORDS_PER_SOURCE]:
                        align_existing_catalog_record(db, source, record)
                        if upsert_opportunity(
                            db,
                            payload=_payload(db, source, record),
                            attachments=[],
                        ):
                            created += 1
                            attempt.created()
                        else:
                            updated += 1
                            attempt.updated()
                    source.status = "active"
                    source.last_success_at = datetime.now(UTC)
                    source.last_error = None
                    db.flush()
                except Exception as exc:
                    skipped += 1
                    source.status = _probe_error_status(exc)
                    source.last_error = str(exc)
                    attempt.skipped()
                    attempt.fail(exc)
                finally:
                    attempt.finish()
        run.status = "success"
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        raise
    finally:
        run.finished_at = datetime.now(UTC)
        run.created_count = created
        run.updated_count = updated
        run.skipped_count = skipped
        db.commit()

    return ImportResult(
        source_id=None,
        created_count=created,
        updated_count=updated,
        skipped_count=skipped,
    )

