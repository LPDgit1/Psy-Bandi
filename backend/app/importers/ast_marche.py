from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
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
from app.services.source_probe import _probe_error_status, ensure_source_catalog

AST_MARCHE_SOURCE_NAMES = {
    "AST Ancona - Concorsi",
    "AST Ascoli Piceno - Concorsi",
    "AST Fermo - Concorsi",
    "AST Macerata - Concorsi",
    "AST Pesaro Urbino - Concorsi",
}


@dataclass(frozen=True)
class AstRecord:
    external_id: str
    title: str
    description: str
    official_url: str
    published_at: datetime | None
    deadline: datetime | None
    attachments: tuple[dict[str, str | None], ...]


def _clean_html(value: str | None) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def _decode_next_payload(html: str) -> str:
    return (
        html.replace('\\"', '"')
        .replace("\\u003c", "<")
        .replace("\\u003e", ">")
        .replace("\\u0026", "&")
    )


def _json_array_after(decoded: str, marker: str) -> list[dict[str, Any]]:
    start = decoded.find(marker)
    if start < 0:
        return []
    start += len(marker) - 1
    depth = 0
    in_string = False
    escaped = False
    end: int | None = None
    for offset, char in enumerate(decoded[start:]):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                end = start + offset + 1
                break
    if end is None:
        return []
    try:
        parsed = json.loads(decoded[start:end])
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _attachment_from_document(document: dict[str, Any]) -> dict[str, str | None] | None:
    file_info = document.get("file")
    if file_info is None and "full" in document:
        file_info = document
    if not isinstance(file_info, dict):
        return None
    url = file_info.get("full")
    if not isinstance(url, str) or not url.startswith("http"):
        return None
    additional = file_info.get("additionalInfo")
    title = "Documento ufficiale"
    file_type = None
    if isinstance(additional, dict):
        title = str(additional.get("fullName") or additional.get("name") or title)
        file_type = str(additional.get("format") or "") or None
    return {"title": title[:255], "url": url, "file_type": file_type}


def _attachments(item: dict[str, Any]) -> tuple[dict[str, str | None], ...]:
    attachments: list[dict[str, str | None]] = []
    for value in item.values():
        if isinstance(value, dict):
            attachment = _attachment_from_document(value)
            if attachment:
                attachments.append(attachment)
        elif isinstance(value, list):
            for nested in value:
                if isinstance(nested, dict):
                    attachment = _attachment_from_document(nested)
                    if attachment:
                        attachments.append(attachment)
    unique: dict[str, dict[str, str | None]] = {}
    for attachment in attachments:
        unique[str(attachment["url"])] = attachment
    return tuple(unique.values())[:6]


def _parse_iso_or_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return parse_date(value)


def _record_external_id(source: Source, item: dict[str, Any], official_url: str) -> str:
    raw = "|".join(
        [
            source.id,
            str(item.get("_id") or ""),
            normalize_text(str(item.get("object") or "")),
            normalize_text(official_url),
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def parse_ast_marche_records(source: Source, html: str, page_url: str) -> list[AstRecord]:
    decoded = _decode_next_payload(html)
    records: list[AstRecord] = []
    for item in _json_array_after(decoded, '"announcements":['):
        title = str(item.get("object") or "").strip()
        description = " ".join(
            part
            for part in (
                title,
                _clean_html(str(item.get("whatIs") or "")),
                _clean_html(str(item.get("targetDescription") or "")),
                _clean_html(str(item.get("howToParticipate") or "")),
                _clean_html(str(item.get("selectionModality") or "")),
            )
            if part
        )
        if not direct_psychology_match(title, description):
            continue
        page_slug = str(item.get("pageUrl") or "").strip()
        official_url = urljoin(page_url.rstrip("/") + "/", page_slug) if page_slug else page_url
        records.append(
            AstRecord(
                external_id=_record_external_id(source, item, official_url),
                title=title[:500],
                description=description[:2400],
                official_url=official_url,
                published_at=_parse_iso_or_date(str(item.get("publishedDate") or "")),
                deadline=_parse_iso_or_date(str(item.get("expirationDate") or "")),
                attachments=_attachments(item),
            )
        )
    return records


def _sources(db: Session) -> list[Source]:
    ensure_source_catalog(db)
    return list(
        db.scalars(select(Source).where(Source.name.in_(AST_MARCHE_SOURCE_NAMES)).order_by(Source.name))
    )


def _payload(db: Session, source: Source, record: AstRecord) -> dict[str, Any]:
    status = infer_status(record.deadline)
    classification = classify_text(record.title, record.description)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=record.title,
        organization=source.organization or source.name,
        deadline=record.deadline,
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    payload: dict[str, Any] = {
        "external_id": record.external_id,
        "source_id": source.id,
        "title": record.title,
        "normalized_title": normalize_text(record.title),
        "short_description": record.description[:900],
        "description": record.description,
        "summary": record.description[:420],
        "category": classification.category,
        "areas": classification.areas,
        "psychology_relevance": classification.psychology_relevance,
        "relevance_score": classification.relevance_score,
        "organization": source.organization or source.name,
        "entity_type": "azienda-sanitaria",
        "region": "Marche",
        "original_location": "Marche",
        "status": status,
        "published_at": record.published_at,
        "deadline": record.deadline,
        "last_seen_at": datetime.now(UTC),
        "requirements": classification.requirements,
        "application_mode": f"Consultare la scheda ufficiale: {source.name}.",
        "official_url": record.official_url,
        "organization_url": source.base_url,
        "content_hash": content_hash(record.title, record.description, record.official_url),
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


def run_ast_marche_import(db: Session) -> ImportResult:
    run = ImportRun(source_id=None, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            timeout=httpx.Timeout(15, connect=5),
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            for source in _sources(db):
                try:
                    response = client.get(source.base_url)
                    response.raise_for_status()
                    records = parse_ast_marche_records(source, response.text, str(response.url))
                    for record in records:
                        if upsert_opportunity(
                            db,
                            payload=_payload(db, source, record),
                            attachments=list(record.attachments),
                        ):
                            created += 1
                        else:
                            updated += 1
                    source.status = "active"
                    source.last_success_at = datetime.now(UTC)
                    source.last_error = None
                    db.flush()
                except Exception as exc:
                    source.status = _probe_error_status(exc)
                    source.last_error = str(exc)
                    skipped += 1
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
