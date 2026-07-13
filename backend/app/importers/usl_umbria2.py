from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

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
from app.services.dates import infer_status, parse_date
from app.services.dedupe import content_hash

USL_UMBRIA2_SOURCE_NAME = "USL Umbria 2 - Bandi di concorso"
USL_UMBRIA2_BASE_URL = "https://www.uslumbria2.it"
USL_UMBRIA2_HUB_PATH = "/pagine/concorsi-001"
USL_UMBRIA2_LIST_PATHS = (
    "/amministrazione-trasparente/concorsi-pubblici-per-direzione-struttura-compless",
    "/amministrazione-trasparente/assunzioni-a-tempo-indeterminato",
    "/amministrazione-trasparente/assunzioni-a-tempo-determinato",
    "/amministrazione-trasparente/avvisi-di-mobilita",
    "/amministrazione-trasparente/avvisi-per-attivazione-incarichi-libero-profession",
)
EXCLUDED_ATTACHMENT_TERMS = (
    "ammess",
    "candidat",
    "commission",
    "compens",
    "convocaz",
    "esito",
    "graduator",
    "preferenza",
    "rinvio",
    "sorteggio",
)
ESSENTIAL_ATTACHMENT_TERMS = (
    "avviso",
    "bando",
    "domanda",
    "istruzion",
    "modello",
    "schema",
)


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == USL_UMBRIA2_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=USL_UMBRIA2_SOURCE_NAME,
        source_type="html-table",
        base_url=f"{USL_UMBRIA2_BASE_URL}{USL_UMBRIA2_HUB_PATH}",
        region="Umbria",
        organization="USL Umbria 2",
        import_method="html-table-sections",
        refresh_frequency="daily",
        status="active",
        technical_notes=(
            "Adapter sulle tabelle pubbliche delle selezioni. Apre il dettaglio "
            "solo per profili psicologici espliciti."
        ),
    )
    db.add(source)
    db.flush()
    return source


def _external_id(detail_url: str) -> str:
    return hashlib.sha256(detail_url.encode()).hexdigest()[:24]


def _positions(title: str) -> int | None:
    searchable_title = title.replace(".", "").replace(",", "")
    match = re.search(
        r"\bn\s*(\d+)\s+(?:post[oi]|incarich[io]|unita|bors[ae])\b",
        searchable_title,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def parse_listing(html: str, list_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for row in soup.select("table.table-atti tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        link = row.select_one("a[href]")
        title = cells[0].get_text(" ", strip=True)
        if link is None or not title:
            continue
        detail_url = urljoin(list_url, str(link["href"]))
        records.append(
            {
                "external_id": _external_id(detail_url),
                "title": title,
                "description": title,
                "detail_url": detail_url,
                "deadline": parse_date(cells[1].get_text(" ", strip=True).replace(".", "/")),
                "source_category": cells[2].get_text(" ", strip=True),
            }
        )
    return records


def _attachment_file_type(title: str) -> str | None:
    normalized_title = title.lower()
    for extension in ("pdf", "docx", "doc", "odt", "zip"):
        if f".{extension}" in normalized_title:
            return extension
    return None


def parse_detail(html: str, detail_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    attachments: list[dict[str, str | None]] = []
    for link in soup.select("a[href]"):
        url = urljoin(detail_url, str(link["href"]))
        if "streamattributomediaoriginale.ashx" not in url.lower():
            continue
        title = link.get_text(" ", strip=True) or "Documento ufficiale"
        normalized_title = normalize_text(title)
        if any(term in normalized_title for term in EXCLUDED_ATTACHMENT_TERMS):
            continue
        if not any(term in normalized_title for term in ESSENTIAL_ATTACHMENT_TERMS):
            continue
        attachments.append(
            {
                "title": title,
                "url": url,
                "file_type": _attachment_file_type(title),
            }
        )
    return {"attachments": attachments[:6]}


def _fetch_records(client: httpx.Client) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for list_path in USL_UMBRIA2_LIST_PATHS:
        response = client.get(list_path)
        response.raise_for_status()
        for record in parse_listing(response.text, str(response.url)):
            records_by_id[record["external_id"]] = record

    for record in records_by_id.values():
        if not direct_psychology_match(record["title"]):
            continue
        response = client.get(record["detail_url"])
        response.raise_for_status()
        record.update(parse_detail(response.text, str(response.url)))
    return list(records_by_id.values())


def _payload(db: Session, source: Source, raw: dict[str, Any]) -> dict[str, Any]:
    title = raw["title"]
    description = raw.get("description") or title
    deadline = raw.get("deadline")
    status = infer_status(deadline)
    classification = classify_text(title, description, raw["source_category"])
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="USL Umbria 2",
        deadline=deadline,
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    payload: dict[str, Any] = {
        "external_id": raw["external_id"],
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
        "organization": "USL Umbria 2",
        "entity_type": "azienda-sanitaria",
        "region": "Umbria",
        "original_location": "Umbria",
        "status": status,
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": _positions(title),
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale USL Umbria 2.",
        "official_url": raw["detail_url"],
        "organization_url": f"{USL_UMBRIA2_BASE_URL}{USL_UMBRIA2_HUB_PATH}",
        "content_hash": content_hash(title, description, raw["source_category"]),
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


def run_usl_umbria2_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=USL_UMBRIA2_BASE_URL,
            timeout=30,
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            records = _fetch_records(client)
        for raw in records:
            if not direct_psychology_match(raw["title"]):
                skipped += 1
                continue
            if upsert_opportunity(
                db,
                payload=_payload(db, source, raw),
                attachments=raw.get("attachments", []),
            ):
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
