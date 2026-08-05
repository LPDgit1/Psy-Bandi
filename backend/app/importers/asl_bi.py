from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import UTC, datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.base import ImportResult
from app.importers.catalog_sources import (
    CatalogRecord,
    _deadline_from_text,
    _is_relevant_opportunity,
    _payload,
    align_existing_catalog_record,
)
from app.importers.institutional import upsert_opportunity
from app.models import ImportRun, Source
from app.services.source_probe import _probe_error_status, ensure_source_catalog
from app.services.source_telemetry import start_source_attempt

ASL_BI_SOURCE_NAME = "ASL BI - Bandi concorso reclutamento personale"
ASL_BI_BASE_URL = (
    "https://trasparenza.aslbi.piemonte.it/"
    "bandi-concorso-reclutamento-personale?sf=102"
)
ASL_BI_ROBOTS_URL = "https://trasparenza.aslbi.piemonte.it/robots.txt"
ASL_BI_CSV_URLS = (
    "https://trasparenza.aslbi.piemonte.it/csv-download/2/elenco_bandi_espletati/CMi82PVQfGMemlc",
    "https://trasparenza.aslbi.piemonte.it/csv-download/2/dati_relativi_procedure_selettiv/2cVyzvs5wZdIopK",
)
USER_AGENT = "BandiPsicologiaMVP/0.1 (+adapter ASL BI; rispetto robots.txt)"
MAX_RECORDS_PER_SOURCE = 30
OPPORTUNITY_TERMS = (
    "avviso",
    "bando",
    "bandi",
    "concorso",
    "concorsi",
    "incarico",
    "incarichi",
    "mobilita",
    "procedura",
    "selezione",
)


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def _csv_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _row_title(row: dict[str, str], fallback: str) -> str:
    preferred = (
        "identificativo bando",
        "identificativo",
        "oggetto",
        "titolo",
        "descrizione",
        "bando",
    )
    normalized = {
        _clean(str(key)).casefold(): _clean(str(value))
        for key, value in row.items()
        if value is not None and _clean(str(value))
    }
    for key in preferred:
        for candidate_key, value in normalized.items():
            if key in candidate_key and len(value) >= 12:
                return value[:500]
    for value in normalized.values():
        if len(value) >= 12 and not value.isdigit():
            return value[:500]
    return fallback[:500]


def _row_url(row: dict[str, str], *, endpoint_url: str, title: str) -> str:
    for value in row.values():
        candidate = _clean(str(value or ""))
        if candidate.startswith(("https://", "http://")):
            parsed = urlparse(candidate)
            if parsed.netloc:
                return candidate
    digest = hashlib.sha256(f"{endpoint_url}|{title}".encode()).hexdigest()[:16]
    return f"{ASL_BI_BASE_URL}#csv-record-{digest}"


def _has_opportunity_terms(text: str) -> bool:
    normalized = _clean(text).casefold()
    return any(term in normalized for term in OPPORTUNITY_TERMS)


def parse_aslbi_csv(
    source: Source,
    raw: bytes | str,
    *,
    endpoint_url: str,
) -> list[CatalogRecord]:
    """Parse an official ASL BI CSV export without following document links."""
    text = _csv_text(raw) if isinstance(raw, bytes) else raw
    if not text.strip():
        return []
    try:
        dialect = csv.Sniffer().sniff(text[:8000], delimiters=";,\t|")
    except csv.Error:
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
    else:
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        return []

    records: dict[str, CatalogRecord] = {}
    for row in reader:
        cleaned_row = {
            _clean(str(key)): _clean(str(value or ""))
            for key, value in row.items()
            if key is not None
        }
        row_text = _clean(
            " ".join(
                f"{key}: {value}" for key, value in cleaned_row.items() if value
            )
        )
        if len(row_text) < 12 or not _is_relevant_opportunity(row_text):
            continue
        if not _has_opportunity_terms(row_text):
            continue
        title = _row_title(cleaned_row, source.name)
        official_url = _row_url(cleaned_row, endpoint_url=endpoint_url, title=title)
        external_id = hashlib.sha256(
            f"{source.id}|{official_url}|{title}".encode()
        ).hexdigest()[:24]
        records[external_id] = CatalogRecord(
            external_id=external_id,
            title=title,
            description=row_text[:2400],
            official_url=official_url,
            published_at=None,
            deadline=_deadline_from_text(row_text),
        )
        if len(records) >= MAX_RECORDS_PER_SOURCE:
            break
    return list(records.values())


def _robots_allows(client: httpx.Client) -> bool:
    response = client.get(ASL_BI_ROBOTS_URL)
    response.raise_for_status()
    parser = RobotFileParser()
    parser.set_url(ASL_BI_ROBOTS_URL)
    parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, ASL_BI_BASE_URL) and all(
        parser.can_fetch(USER_AGENT, url) for url in ASL_BI_CSV_URLS
    )


def run_asl_bi_import(db: Session) -> ImportResult:
    ensure_source_catalog(db)
    source = db.scalar(select(Source).where(Source.name == ASL_BI_SOURCE_NAME))
    if source is None:
        raise RuntimeError(f"Fonte non presente nel catalogo: {ASL_BI_SOURCE_NAME}")

    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0
    try:
        with httpx.Client(
            timeout=httpx.Timeout(12, connect=5),
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            attempt = start_source_attempt(db, source)
            try:
                if not _robots_allows(client):
                    raise PermissionError("robots.txt non consente il recupero automatico ASL BI")

                records: dict[str, CatalogRecord] = {}
                for endpoint_url in ASL_BI_CSV_URLS:
                    response = client.get(endpoint_url)
                    response.raise_for_status()
                    records.update(
                        {
                            record.external_id: record
                            for record in parse_aslbi_csv(
                                source,
                                response.content,
                                endpoint_url=endpoint_url,
                            )
                        }
                    )

                for record in records.values():
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
                source.status = (
                    "access-review"
                    if isinstance(exc, PermissionError)
                    else _probe_error_status(exc)
                )
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
        source_id=source.id,
        created_count=created,
        updated_count=updated,
        skipped_count=skipped,
    )
