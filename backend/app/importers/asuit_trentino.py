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

ASUIT_SOURCE_NAME = "ASUIT Trentino - Lavora con noi"
ASUIT_BASE_URL = "https://www.asuit.tn.it"
ASUIT_LIST_PATH = "/bandi-concorsi"
ASUIT_SEARCH_TERMS = ("psicolog", "psicoterap", "neuropsicolog", "psicoterapia")
EXCLUDED_ATTACHMENT_TERMS = (
    "ammess",
    "assegnaz",
    "candidat",
    "commission",
    "convocaz",
    "esito",
    "graduator",
    "prov",
    "risultat",
)
ESSENTIAL_ATTACHMENT_TERMS = (
    "avviso",
    "bando",
    "domanda",
    "istruzion",
    "modello",
)


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == ASUIT_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=ASUIT_SOURCE_NAME,
        source_type="html-list-detail",
        base_url=f"{ASUIT_BASE_URL}{ASUIT_LIST_PATH}?combine={ASUIT_SEARCH_TERMS[0]}",
        region="Trentino-Alto Adige",
        organization="ASUIT Trentino",
        import_method="html-list-detail-filtered",
        refresh_frequency="daily",
        status="active",
        technical_notes=(
            "Adapter sulla lista pubblica Drupal filtrata per psicolog. "
            "Apre il dettaglio solo per profili psicologici e psicoterapeutici "
            "espliciti."
        ),
    )
    db.add(source)
    db.flush()
    return source


def _positions(title: str) -> int | None:
    searchable_title = title.replace(".", "").replace(",", "")
    match = re.search(
        r"\bn\s*(\d+)\s+(?:post[oi]|incarich[io]|unita|bors[ae])\b",
        searchable_title,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def _external_id(detail_url: str, history_node_id: str | None = None) -> str:
    if history_node_id:
        return history_node_id
    return hashlib.sha256(detail_url.encode()).hexdigest()[:24]


def parse_listing(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for card in soup.select("article.node--type-bando"):
        title_link = card.select_one(".card-title a[href]")
        if title_link is None:
            continue
        title = title_link.get_text(" ", strip=True)
        detail_url = urljoin(ASUIT_BASE_URL, str(title_link["href"]))
        description_node = card.select_one(".node--teaser-text-truncate")
        badges = [node.get_text(" ", strip=True) for node in card.select(".badge")]
        records.append(
            {
                "external_id": _external_id(
                    detail_url,
                    card.get("data-history-node-id"),
                ),
                "title": title,
                "description": (
                    description_node.get_text(" ", strip=True)
                    if description_node
                    else title
                ),
                "detail_url": detail_url,
                "list_status": badges[0] if badges else "",
                "source_category": badges[-1] if len(badges) > 1 else "",
            }
        )
    return records


def _has_next_page(html: str, current_page: int) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    marker = f"page={current_page + 1}"
    return any(marker in str(link.get("href", "")) for link in soup.find_all("a", href=True))


def _attachment_file_type(url: str) -> str | None:
    normalized_url = url.lower()
    for extension in ("pdf", "docx", "doc", "odt", "zip"):
        if f".{extension}" in normalized_url:
            return extension
    return None


def _detail_dates(soup: BeautifulSoup) -> dict[str, datetime | None]:
    dates: dict[str, datetime | None] = {}
    for box in soup.select("#date-scadenze .badge-meta-date-box"):
        label = box.select_one(".badge-meta-date-label")
        value = box.select_one(".badge-meta-date-time")
        if label is None or value is None:
            continue
        dates[normalize_text(label.get_text(" ", strip=True))] = parse_date(
            value.get_text(" ", strip=True)
        )
    return dates


def _safe_attachments(soup: BeautifulSoup) -> list[dict[str, str | None]]:
    attachments: list[dict[str, str | None]] = []
    seen_urls: set[str] = set()
    for link in soup.select("#documenti a[href]"):
        title = link.get_text(" ", strip=True) or "Documento ufficiale"
        normalized_title = normalize_text(title)
        url = urljoin(ASUIT_BASE_URL, str(link["href"]))
        if url in seen_urls or title.lower() == "download":
            continue
        if any(term in normalized_title for term in EXCLUDED_ATTACHMENT_TERMS):
            continue
        if not any(term in normalized_title for term in ESSENTIAL_ATTACHMENT_TERMS):
            continue
        seen_urls.add(url)
        attachments.append(
            {
                "title": title,
                "url": url,
                "file_type": _attachment_file_type(url),
            }
        )
    return attachments[:6]


def parse_detail(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    description_node = soup.select_one("#cosa-e")
    dates = _detail_dates(soup)
    return {
        "description": (
            description_node.get_text(" ", strip=True) if description_node else ""
        ),
        "published_at": next(
            (value for key, value in dates.items() if "pubblic" in key),
            None,
        ),
        "deadline": next(
            (value for key, value in dates.items() if "scaden" in key),
            None,
        ),
        "attachments": _safe_attachments(soup),
    }


def _fetch_records(client: httpx.Client) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for term in ASUIT_SEARCH_TERMS:
        for page in range(settings.asuit_max_pages):
            response = client.get(
                ASUIT_LIST_PATH,
                params={"combine": term, "page": page},
            )
            response.raise_for_status()
            for record in parse_listing(response.text):
                records_by_id[record["external_id"]] = record
            if not _has_next_page(response.text, page):
                break

    for record in records_by_id.values():
        if not direct_psychology_match(record["title"], record["description"]):
            continue
        detail_response = client.get(record["detail_url"])
        detail_response.raise_for_status()
        record.update(parse_detail(detail_response.text))
    return list(records_by_id.values())


def _status(raw: dict[str, Any]) -> str:
    if "conclus" in normalize_text(raw["list_status"]):
        return "closed"
    return infer_status(raw.get("deadline"))


def _payload(db: Session, source: Source, raw: dict[str, Any]) -> dict[str, Any]:
    title = raw["title"]
    description = raw.get("description") or title
    deadline = raw.get("deadline")
    status = _status(raw)
    classification = classify_text(title, description, raw["source_category"])
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="ASUIT Trentino",
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
        "organization": "ASUIT Trentino",
        "entity_type": "azienda-sanitaria",
        "region": "Trentino-Alto Adige",
        "original_location": "Trentino",
        "status": status,
        "published_at": raw.get("published_at"),
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": _positions(title),
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale ASUIT.",
        "official_url": raw["detail_url"],
        "organization_url": f"{ASUIT_BASE_URL}{ASUIT_LIST_PATH}?combine={ASUIT_SEARCH_TERMS[0]}",
        "content_hash": content_hash(title, description, raw["detail_url"]),
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


def run_asuit_trentino_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=ASUIT_BASE_URL,
            timeout=30,
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            records = _fetch_records(client)
        for raw in records:
            if not direct_psychology_match(raw["title"], raw["description"]):
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
