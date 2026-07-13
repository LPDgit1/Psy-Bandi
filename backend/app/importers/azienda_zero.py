from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.base import ImportResult
from app.importers.institutional import (
    direct_psychology_match,
    editorial_visibility,
    find_probable_duplicate,
    upsert_opportunity,
)
from app.models import ImportRun, Source
from app.services.classifier import build_search_text, classify_text, normalize_text
from app.services.dates import infer_status
from app.services.dedupe import content_hash

AZIENDA_ZERO_SOURCE_NAME = "Azienda Zero Veneto - Concorsi"
AZIENDA_ZERO_BASE_URL = "https://www.azero.veneto.it"
AZIENDA_ZERO_PUBLIC_PATH = "/concorsi-e-avvisi"
AZIENDA_ZERO_RECORDS_PATH = "/api/jsonws/concorsi.concorsoentry/find-all"
AZIENDA_ZERO_ATTACHMENTS_PATH = "/api/jsonws/concorsi.concorsoattachment/find-by-concorso"
AZIENDA_ZERO_DETAIL_URL = (
    "https://www.aziendazero.concorsieavvisi.it/"
    "index.cfm?action=trasparenza.concorso&id={external_id}"
)


def _clean(value: str | None) -> str:
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)


def _datetime_from_millis(value: int | str | None) -> datetime | None:
    if value in {None, ""}:
        return None
    return datetime.fromtimestamp(int(value) / 1000, tz=UTC)


def _positions(title: str) -> int | None:
    match = re.search(r"\bn\.?\s*(\d+)\s+(?:posti|incarichi)\b", title, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == AZIENDA_ZERO_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=AZIENDA_ZERO_SOURCE_NAME,
        source_type="public-json-api",
        base_url=f"{AZIENDA_ZERO_BASE_URL}{AZIENDA_ZERO_PUBLIC_PATH}",
        region="Veneto",
        organization="Azienda Zero - Regione del Veneto",
        import_method="public-json-api",
        refresh_frequency="daily",
        status="active",
        technical_notes=(
            "Endpoint pubblico usato dall'interfaccia istituzionale: "
            f"{AZIENDA_ZERO_RECORDS_PATH}"
        ),
    )
    db.add(source)
    db.flush()
    return source


def _fetch_records(client: httpx.Client) -> list[dict[str, Any]]:
    response = client.post(AZIENDA_ZERO_RECORDS_PATH, data={"start": "-1", "end": "-1"})
    response.raise_for_status()
    return list(response.json())


def _fetch_attachments(client: httpx.Client, external_id: str) -> list[dict[str, Any]]:
    response = client.post(AZIENDA_ZERO_ATTACHMENTS_PATH, data={"concorsoId": external_id})
    response.raise_for_status()
    return list(response.json())


def _essential_attachments(records: list[dict[str, Any]]) -> list[dict[str, str | None]]:
    selected: list[dict[str, str | None]] = []
    for record in records:
        title = _clean(record.get("nomeFile")) or "Documento ufficiale"
        normalized = normalize_text(title)
        if not any(
            term in normalized
            for term in ("bando", "delibera di indizione", "istruzioni compilazione")
        ):
            continue
        selected.append(
            {
                "title": title,
                "url": record.get("link"),
                "file_type": record.get("estensione"),
            }
        )
    return selected[:6]


def _payload(
    db: Session,
    source: Source,
    raw: dict[str, Any],
) -> dict[str, Any]:
    external_id = str(raw["concorsoId"])
    title = _clean(raw.get("titolo")) or "Concorso Azienda Zero senza titolo"
    figure = _clean(raw.get("figura"))
    recruitment_type = _clean(raw.get("tipoReclutamento"))
    description = " - ".join(part for part in [title, figure, recruitment_type] if part)
    deadline = _datetime_from_millis(raw.get("scadenza"))
    status = infer_status(deadline)
    classification = classify_text(title, figure, recruitment_type)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="Azienda Zero - Regione del Veneto",
        deadline=deadline,
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    official_url = AZIENDA_ZERO_DETAIL_URL.format(external_id=external_id)

    payload: dict[str, Any] = {
        "external_id": external_id,
        "source_id": source.id,
        "title": title,
        "normalized_title": normalize_text(title),
        "short_description": description[:900],
        "description": description,
        "summary": description[:420],
        "category": classification.category,
        "areas": classification.areas,
        "psychology_relevance": classification.psychology_relevance,
        "relevance_score": classification.relevance_score,
        "organization": "Azienda Zero - Regione del Veneto",
        "entity_type": "azienda-sanitaria",
        "region": "Veneto",
        "original_location": "Veneto",
        "status": status,
        "published_at": _datetime_from_millis(raw.get("createDate")),
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": _positions(title),
        "contract_type": recruitment_type or None,
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale Azienda Zero.",
        "official_url": official_url,
        "organization_url": f"{AZIENDA_ZERO_BASE_URL}{AZIENDA_ZERO_PUBLIC_PATH}",
        "content_hash": content_hash(title, figure, recruitment_type),
        "editorial_status": editorial_status,
        "editorial_notes": editorial_notes,
    }
    payload["search_text"] = build_search_text(
        payload["title"],
        payload["description"],
        payload["organization"],
        payload["region"],
        payload["category"],
        payload["areas"],
        payload["requirements"],
    )
    return payload


def run_azienda_zero_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=AZIENDA_ZERO_BASE_URL,
            timeout=30,
            verify=settings.source_import_verify_tls,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            for raw in _fetch_records(client):
                if not direct_psychology_match(raw.get("titolo"), raw.get("figura")):
                    skipped += 1
                    continue
                attachments = _essential_attachments(
                    _fetch_attachments(client, str(raw["concorsoId"]))
                )
                payload = _payload(db, source, raw)
                if upsert_opportunity(db, payload=payload, attachments=attachments):
                    created += 1
                else:
                    updated += 1

        source.last_success_at = datetime.now(UTC)
        source.last_error = None
        source.status = "active"
        run.status = "success"
    except Exception as exc:
        source.last_error = str(exc)
        source.status = "error"
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
