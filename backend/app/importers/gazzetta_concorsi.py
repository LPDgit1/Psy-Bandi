from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

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

GAZZETTA_SOURCE_NAME = "Gazzetta Ufficiale - 4a Serie Speciale Concorsi ed Esami"
GAZZETTA_BASE_URL = "https://www.gazzettaufficiale.it"
GAZZETTA_INDEX_PATH = "/30giorni/concorsi"
ISSUE_PATH_MARKER = "/gazzetta/concorsi/caricaDettaglio"
ACT_PATH_MARKER = "/atto/concorsi/caricaDettaglioAtto/"
REDACTION_CODE_PATTERN = re.compile(r"\b\d{2}[A-Z]\d{5}\b")


@dataclass(frozen=True)
class GazzettaRecord:
    external_id: str
    title: str
    description: str
    official_url: str
    organization: str
    published_at: datetime | None
    deadline: datetime | None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def collect_issue_urls(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        if ISSUE_PATH_MARKER not in href:
            continue
        absolute = urljoin(GAZZETTA_BASE_URL, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        urls.append(absolute)
    return urls[-settings.gazzetta_concorsi_max_issues :]


def _query_value(url: str, key: str) -> str | None:
    values = parse_qs(urlparse(url).query).get(key)
    return values[0] if values else None


def _publication_date(issue_url: str, act_url: str) -> datetime | None:
    raw = _query_value(act_url, "atto.dataPubblicazioneGazzetta") or _query_value(
        issue_url,
        "dataPubblicazioneGazzetta",
    )
    return parse_date(raw)


def _redaction_code(url: str, text: str) -> str | None:
    value = _query_value(url, "atto.codiceRedazionale")
    if value:
        return value
    match = REDACTION_CODE_PATTERN.search(text)
    return match.group(0) if match else None


def parse_issue_records(html: str, issue_url: str) -> tuple[list[GazzettaRecord], int]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[GazzettaRecord] = []
    act_count = 0
    for container in soup.select("span.risultato"):
        links = [
            link
            for link in container.find_all("a", href=True)
            if ACT_PATH_MARKER in str(link["href"])
        ]
        if not links:
            continue
        act_count += 1
        detail_link = max(links, key=lambda link: len(_clean_text(link.get_text(" ", strip=True))))
        title = _clean_text(detail_link.get_text(" ", strip=True))
        if not title or not direct_psychology_match(title):
            continue

        official_url = urljoin(GAZZETTA_BASE_URL, str(detail_link["href"]))
        code = _redaction_code(official_url, title)
        if not code:
            continue
        issuer_node = container.find_previous("span", class_="emettitore")
        organization = _clean_text(issuer_node.get_text(" ", strip=True)) if issuer_node else ""
        type_link = links[0]
        deadline = parse_date(_clean_text(type_link.get_text(" ", strip=True)))
        description = _clean_text(f"{organization}. {title}")
        records.append(
            GazzettaRecord(
                external_id=f"gazzetta-concorsi:{code}",
                title=title,
                description=description,
                official_url=official_url,
                organization=organization or "Gazzetta Ufficiale",
                published_at=_publication_date(issue_url, official_url),
                deadline=deadline,
            )
        )
    return records, act_count


def _source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == GAZZETTA_SOURCE_NAME))
    if source is None:
        raise RuntimeError("Fonte Gazzetta Concorsi assente dal catalogo.")
    return source


def _region_for_issuer(db: Session, issuer: str) -> str | None:
    normalized_issuer = normalize_text(issuer)
    if not normalized_issuer:
        return None
    best: tuple[int, str] | None = None
    for organization, region in db.execute(
        select(Source.organization, Source.region).where(Source.region.is_not(None))
    ):
        normalized_organization = normalize_text(organization)
        if not normalized_organization:
            continue
        if (
            normalized_organization in normalized_issuer
            or normalized_issuer in normalized_organization
        ):
            candidate = (min(len(normalized_organization), len(normalized_issuer)), region)
            if best is None or candidate[0] > best[0]:
                best = candidate
    return best[1] if best else None


def _entity_type(organization: str) -> str:
    normalized = normalize_text(organization)
    if any(
        token in normalized
        for token in (
            "azienda ospedal",
            "azienda sanit",
            "azienda socio sanit",
            "asl ",
            "asst ",
            "ausl ",
            "aou ",
            "irccs",
            "policlinico",
        )
    ):
        return "azienda-sanitaria"
    if "universita" in normalized:
        return "universita"
    if normalized.startswith("comune "):
        return "comune"
    if normalized.startswith("regione "):
        return "regione"
    return "ente-pubblico"


def _payload(db: Session, source: Source, record: GazzettaRecord) -> dict[str, Any]:
    status = infer_status(record.deadline)
    classification = classify_text(record.title, record.description)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=record.title,
        organization=record.organization,
        deadline=record.deadline,
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    region = _region_for_issuer(db, record.organization)
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
        "organization": record.organization,
        "entity_type": _entity_type(record.organization),
        "region": region,
        "original_location": region,
        "status": status,
        "published_at": record.published_at,
        "deadline": record.deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": None,
        "requirements": classification.requirements,
        "application_mode": "Consultare l'atto ufficiale della 4a Serie Speciale.",
        "official_url": record.official_url,
        "organization_url": source.base_url,
        "content_hash": content_hash(
            record.title,
            record.description,
            record.official_url,
        ),
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


def run_gazzetta_concorsi_import(db: Session) -> ImportResult:
    source = _source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=GAZZETTA_BASE_URL,
            timeout=httpx.Timeout(30, connect=8),
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            index = client.get(GAZZETTA_INDEX_PATH)
            index.raise_for_status()
            issue_urls = collect_issue_urls(index.text)
            if not issue_urls:
                raise RuntimeError("Indice Gazzetta Concorsi senza edizioni leggibili.")

            records_by_id: dict[str, GazzettaRecord] = {}
            parsed_act_count = 0
            for issue_url in issue_urls:
                response = client.get(issue_url)
                response.raise_for_status()
                records, act_count = parse_issue_records(response.text, str(response.url))
                parsed_act_count += act_count
                for record in records:
                    records_by_id[record.external_id] = record

        if parsed_act_count == 0:
            raise RuntimeError(
                "Edizioni Gazzetta raggiunte ma nessun atto interpretabile: adapter non valido."
            )

        skipped = max(parsed_act_count - len(records_by_id), 0)

        for record in records_by_id.values():
            if upsert_opportunity(
                db,
                payload=_payload(db, source, record),
                attachments=[],
            ):
                created += 1
            else:
                updated += 1

        source.status = "active"
        source.last_success_at = datetime.now(UTC)
        source.last_error = None
        run.status = "success"
    except Exception as exc:
        source.status = "error"
        source.last_error = str(exc)
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
