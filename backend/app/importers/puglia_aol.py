from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.base import ImportResult
from app.importers.institutional import (
    AUTO_EXCLUSION_PREFIX,
    direct_psychology_match,
    editorial_visibility,
    find_probable_duplicate,
    upsert_opportunity,
)
from app.models import ImportRun, Opportunity, Source
from app.services.classifier import build_search_text, classify_text, normalize_text
from app.services.dates import infer_status, parse_date
from app.services.dedupe import content_hash
from app.services.source_probe import _probe_error_status, ensure_source_catalog
from app.services.source_telemetry import track_source_attempt

API_BASE_URL = "https://sanita.puglia.it/AlboOnline/ao/"
APP_BASE_URL = "https://sanita.puglia.it/aol/"
SEARCH_TERMS = ("psicolog", "psicoterap", "neuropsicolog")
PAGE_SIZE = 25
MAX_PAGES_PER_TERM = 2
SOURCE_TYPE = "puglia-aol-api"

FOLLOW_UP_TERMS = (
    "ammissione",
    "ammessi",
    "calendario",
    "commissione",
    "convocazione",
    "data colloquio",
    "data prova",
    "diario",
    "elenco candidati",
    "esclusione",
    "esito",
    "graduatoria",
    "nomina",
    "presa d'atto",
    "prova colloquio",
    "prova orale",
    "prova pratica",
    "prova scritta",
    "sorteggio",
)
PRIMARY_TERMS = (
    "avviso pubblico",
    "bando di concorso",
    "concorso pubblico",
    "incarico",
    "manifestazione di interesse",
    "selezione pubblica",
)


def _source_code(source: Source) -> str:
    query = parse_qs(urlparse(source.base_url).query)
    return query.get("aziendaParam", [""])[0]


def _official_url(source: Source, item_id: int | str) -> str:
    query = urlencode(
        {
            "path": f"dettaglioConcorso/{item_id}",
            "aziendaParam": _source_code(source),
        }
    )
    return f"{APP_BASE_URL}?{query}"


def _attachment_url(source: Source, attachment_id: int | str) -> str:
    query = urlencode(
        {
            "path": f"downloadAllegato/{attachment_id}",
            "aziendaParam": _source_code(source),
        }
    )
    return f"{APP_BASE_URL}?{query}"


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("\ufffd", " ")).strip()


def _is_primary_opportunity(text: str) -> bool:
    normalized = normalize_text(text)
    if not direct_psychology_match(text) and "neuropsicolog" not in normalized:
        return False
    if not any(term in normalized for term in PRIMARY_TERMS):
        return False
    if any(term in normalized for term in FOLLOW_UP_TERMS):
        return False
    return True


def _request_payload(source: Source, term: str, page: int) -> dict[str, Any]:
    return {
        "azienda": source.organization,
        "tipoItem": "concorso",
        "page": page,
        "numElementi": PAGE_SIZE,
        "dataAdozioneDal": None,
        "dataAdozioneAl": None,
        "dataScadenzaDal": None,
        "dataScadenzaAl": None,
        "estensioneNum": None,
        "numero": None,
        "oggetto": term,
        "proponenteSelezionato": None,
        "numeroRepertorio": None,
        "annoRepertorio": None,
        "tipoDocumentazione": None,
        "statoAtto": None,
        "logged": False,
    }


def _attachments(source: Source, item: dict[str, Any]) -> list[dict[str, str | None]]:
    attachments: list[dict[str, str | None]] = []
    for attachment in item.get("listaAllegati") or []:
        attachment_id = attachment.get("id")
        title = _clean_text(attachment.get("nomeFile")) or "Allegato ufficiale"
        if attachment_id is None:
            continue
        attachments.append(
            {
                "title": title[:255],
                "url": _attachment_url(source, attachment_id),
                "file_type": "pdf" if ".pdf" in title.lower() else None,
            }
        )
    return attachments[:6]


def _description(item: dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    parts = [
        _clean_text(item.get("oggetto")),
        _clean_text(metadata.get("oggettoDettaglio")),
        _clean_text(metadata.get("incarichi")),
        _clean_text(metadata.get("requisiti")),
        _clean_text(metadata.get("note")),
    ]
    return "\n".join(part for part in parts if part)[:2400]


def _deadline(item: dict[str, Any]) -> datetime | None:
    metadata = item.get("metadata") or {}
    return (
        parse_date(metadata.get("dataScadenzaDomande"))
        or parse_date(metadata.get("dataScadenzaOfferte"))
        or parse_date(item.get("dataScadenza"))
    )


def _payload(db: Session, source: Source, item: dict[str, Any]) -> dict[str, Any]:
    title = _clean_text(item.get("oggetto"))[:500]
    description = _description(item) or title
    deadline = _deadline(item)
    status = infer_status(deadline)
    classification = classify_text(title, description)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization=source.organization or source.name,
        deadline=deadline,
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    official_url = _official_url(source, item["id"])
    payload: dict[str, Any] = {
        "external_id": f"puglia-aol:{source.id}:{item['id']}",
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
        "organization": source.organization or source.name,
        "entity_type": "azienda-sanitaria",
        "region": source.region,
        "original_location": source.region,
        "status": status,
        "published_at": parse_date(item.get("dataPubblicazione")),
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": None,
        "requirements": classification.requirements,
        "application_mode": f"Consultare la scheda ufficiale Albo Online: {source.name}.",
        "official_url": official_url,
        "organization_url": source.base_url,
        "content_hash": content_hash(title, description, official_url),
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


def _sources(db: Session) -> list[Source]:
    ensure_source_catalog(db)
    return list(
        db.scalars(
            select(Source).where(Source.source_type == SOURCE_TYPE).order_by(Source.organization)
        )
    )


def _hide_non_primary_existing(db: Session, source: Source) -> int:
    hidden = 0
    opportunities = db.scalars(
        select(Opportunity).where(
            Opportunity.source_id == source.id,
            Opportunity.external_id.like("puglia-aol:%"),
            Opportunity.editorial_status != "hidden",
        )
    ).all()
    for opportunity in opportunities:
        if _is_primary_opportunity(opportunity.title):
            continue
        opportunity.editorial_status = "hidden"
        opportunity.editorial_notes = (
            f"{AUTO_EXCLUSION_PREFIX} aggiornamento procedurale, non nuovo bando."
        )
        hidden += 1
    return hidden


def _fetch_items(client: httpx.Client, source: Source) -> list[dict[str, Any]]:
    items_by_id: dict[int, dict[str, Any]] = {}
    for term in SEARCH_TERMS:
        for page in range(MAX_PAGES_PER_TERM):
            response = client.post(
                "atti/getListaAttiPaginata",
                json=_request_payload(source, term, page),
            )
            response.raise_for_status()
            data = response.json()
            for item in data.get("content") or []:
                item_id = item.get("id")
                title = _clean_text(item.get("oggetto"))
                if item_id is None or not _is_primary_opportunity(title):
                    continue
                items_by_id[int(item_id)] = item
            if data.get("last") is True:
                break
    return list(items_by_id.values())


def run_puglia_aol_import(db: Session) -> ImportResult:
    run = ImportRun(source_id=None, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=API_BASE_URL,
            timeout=httpx.Timeout(20, connect=6),
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)",
            },
        ) as client:
            for source in _sources(db):
                with track_source_attempt(db, source) as attempt:
                    try:
                        hidden_count = _hide_non_primary_existing(db, source)
                        skipped += hidden_count
                        attempt.skipped(hidden_count)
                        for item in _fetch_items(client, source):
                            if upsert_opportunity(
                                db,
                                payload=_payload(db, source, item),
                                attachments=_attachments(source, item),
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
                        source.status = _probe_error_status(exc)
                        source.last_error = str(exc)
                        skipped += 1
                        attempt.skipped()
                        attempt.fail(exc)
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
