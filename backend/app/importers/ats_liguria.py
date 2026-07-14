from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

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
from app.models import ImportRun, Opportunity, Source
from app.services.classifier import build_search_text, classify_text, normalize_text
from app.services.dates import infer_status, parse_date
from app.services.dedupe import content_hash
from app.services.source_probe import _probe_error_status, ensure_source_catalog

ATS_LIGURIA_SOURCE_NAME = "ATS Liguria - Bandi di concorso"
ATS_LIGURIA_FALLBACK_URLS = (
    "https://www.asl3.liguria.it/amministrazione-trasparente/bandi-di-concorso/concorsi-aperti/",
    "https://www.asl3.liguria.it/amministrazione-trasparente/bandi-di-concorso/avvisi-pubblici/publiccompetitions/",
    "https://www.asl1.liguria.it/amministrazione-trasparente/bandi-di-concorso/concorsi/concorsi-dirigenza/publiccompetitions/",
    "https://www.asl1.liguria.it/amministrazione-trasparente/bandi-di-concorso/contratti-dilavoro-autonomo/publiccompetitions/",
    "https://www.asl4.liguria.it/amministrazione-trasparente/concorsi/sottocategorie-bandi-di-concorso/",
    "https://www.asl5.liguria.it/Istituzionali/ConcorsieMobilita/Concorsi.aspx",
)
MAX_LIST_PAGES = 12
MAX_DETAIL_PAGES = 80
MULTI_PROFILE_TITLE_TERMS = (
    "figure professionali",
    "profili professionali",
    "profili vari",
    "vari profili",
)
AUTO_HIDE_UNFOCUSED_NOTE = (
    "Escluso automaticamente: la singola scheda ATS Liguria non riguarda "
    "un profilo psicologico."
)
VERIFIED_ACTIVE_URL_MARKERS = (
    "/concorsi-aperti/",
    "/avvisi-pubblici/",
    "/concorsi-dirigenza/",
    "/contratti-dilavoro-autonomo/",
)


@dataclass(frozen=True)
class LiguriaRecord:
    external_id: str
    title: str
    description: str
    official_url: str
    deadline: datetime | None
    attachments: tuple[dict[str, str | None], ...]


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _same_host(left: str, right: str) -> bool:
    left_host = urlparse(left).netloc
    right_host = urlparse(right).netloc
    return not right_host or left_host == right_host


def _external_id(official_url: str) -> str:
    return hashlib.sha256(official_url.encode()).hexdigest()[:24]


def _verified_active_detail(official_url: str) -> bool:
    normalized = official_url.lower()
    return any(marker in normalized for marker in VERIFIED_ACTIVE_URL_MARKERS)


def _deadline_from_text(text: str) -> datetime | None:
    date_value = (
        r"([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|"
        r"[0-9]{1,2}\s+[a-z]{3,12}\s+[0-9]{4})"
    )
    patterns = (
        rf"(?:data\s+)?(?:scadenza|chiusura)(?:\s+domande)?[:\s]+{date_value}",
        rf"entro\s+il\s+{date_value}",
        rf"termine.*?{date_value}",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_date(match.group(1))
    return None


def _file_type(url: str, label: str) -> str | None:
    normalized = f"{url} {label}".lower()
    for extension in ("pdf", "docx", "doc", "odt", "zip"):
        if extension in normalized:
            return extension
    return None


def collect_ats_liguria_list_urls(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = urljoin(base_url, str(link["href"]))
        if href in seen or not _same_host(base_url, href):
            continue
        normalized = normalize_text(f"{link.get_text(' ', strip=True)} {href}")
        if "publiccompetitions" in normalized or any(
            term in normalized
            for term in ("concorsi dirigenza", "avvisi pubblici dirigenza", "lavoro autonomo")
        ):
            seen.add(href)
            urls.append(href)
        if len(urls) >= MAX_LIST_PAGES:
            break
    return urls


def parse_ats_liguria_detail_urls(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = urljoin(page_url, str(link["href"]))
        if href in seen:
            continue
        if "/publiccompetition/" not in href:
            continue
        seen.add(href)
        urls.append(href)
    return urls


def _attachments_from_detail(
    soup: BeautifulSoup,
    detail_url: str,
) -> tuple[dict[str, str | None], ...]:
    attachments: list[dict[str, str | None]] = []
    for link in soup.find_all("a", href=True):
        href = urljoin(detail_url, str(link["href"]))
        label = _clean_text(link.get_text(" ", strip=True))
        normalized = normalize_text(f"{label} {href}")
        raw_combined = f"{label} {href}".lower()
        if "download.php" not in normalized and not any(
            extension in raw_combined
            for extension in (".pdf", ".doc", ".docx", ".odt", ".zip")
        ):
            continue
        if any(term in normalized for term in ("graduatoria", "commissione", "esito", "ammessi")):
            continue
        title = label or href.rsplit("/", 1)[-1]
        attachments.append(
            {
                "title": title[:255],
                "url": href,
                "file_type": _file_type(href, title),
            }
        )
    unique = {str(attachment["url"]): attachment for attachment in attachments}
    return tuple(unique.values())[:6]


def parse_ats_liguria_record(html: str, detail_url: str) -> LiguriaRecord | None:
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    for selector in ("h1", "h2", "title"):
        node = soup.select_one(selector)
        if node:
            title = _clean_text(node.get_text(" ", strip=True))
            break
    body = soup.select_one("main, article, .item-page, .com-content-article")
    description = _clean_text((body or soup).get_text(" ", strip=True))[:2400]
    if not title:
        title = description[:240]
    normalized_title = normalize_text(title)
    focused_match = direct_psychology_match(title, detail_url) or (
        any(term in normalized_title for term in MULTI_PROFILE_TITLE_TERMS)
        and direct_psychology_match(description)
    )
    if not focused_match:
        return None
    return LiguriaRecord(
        external_id=_external_id(detail_url),
        title=title[:500],
        description=description,
        official_url=detail_url,
        deadline=_deadline_from_text(description),
        attachments=_attachments_from_detail(soup, detail_url),
    )


def _hide_unfocused_records(db: Session, source: Source) -> int:
    hidden = 0
    opportunities = db.scalars(
        select(Opportunity).where(
            Opportunity.source_id == source.id,
            Opportunity.editorial_status == "approved",
        )
    ).all()
    for opportunity in opportunities:
        normalized_title = normalize_text(opportunity.title)
        focused_match = direct_psychology_match(
            opportunity.title,
            opportunity.official_url,
        ) or (
            any(term in normalized_title for term in MULTI_PROFILE_TITLE_TERMS)
            and direct_psychology_match(opportunity.description)
        )
        if focused_match:
            continue
        opportunity.editorial_status = "hidden"
        opportunity.editorial_notes = AUTO_HIDE_UNFOCUSED_NOTE
        hidden += 1
    return hidden


def _source(db: Session) -> Source:
    ensure_source_catalog(db)
    return db.scalar(select(Source).where(Source.name == ATS_LIGURIA_SOURCE_NAME))  # type: ignore[return-value]


def _payload(db: Session, source: Source, record: LiguriaRecord) -> dict[str, Any]:
    status = infer_status(record.deadline)
    if status == "review" and _verified_active_detail(record.official_url):
        status = "open"
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
        "region": "Liguria",
        "original_location": "Liguria",
        "status": status,
        "deadline": record.deadline,
        "last_seen_at": datetime.now(UTC),
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale ATS Liguria.",
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


def run_ats_liguria_import(db: Session) -> ImportResult:
    source = _source(db)
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
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            list_urls: list[str] = []
            seen_list_urls: set[str] = set()
            seed_errors: list[Exception] = []
            for seed_url in (source.base_url, *ATS_LIGURIA_FALLBACK_URLS):
                try:
                    hub = client.get(seed_url)
                    hub.raise_for_status()
                except Exception as exc:
                    seed_errors.append(exc)
                    skipped += 1
                    continue
                resolved_url = str(hub.url)
                for list_url in (
                    resolved_url,
                    *collect_ats_liguria_list_urls(hub.text, resolved_url),
                ):
                    if list_url not in seen_list_urls:
                        seen_list_urls.add(list_url)
                        list_urls.append(list_url)
            if not list_urls:
                raise seed_errors[-1] if seed_errors else RuntimeError(
                    "Nessuna pagina ATS Liguria disponibile."
                )

            detail_urls: list[str] = []
            seen_detail_urls: set[str] = set()
            for list_url in list_urls:
                try:
                    page = client.get(list_url)
                    page.raise_for_status()
                except Exception:
                    skipped += 1
                    continue
                for detail_url in parse_ats_liguria_detail_urls(page.text, str(page.url)):
                    if detail_url in seen_detail_urls:
                        continue
                    seen_detail_urls.add(detail_url)
                    detail_urls.append(detail_url)
                    if len(detail_urls) >= MAX_DETAIL_PAGES:
                        break
                if len(detail_urls) >= MAX_DETAIL_PAGES:
                    break

            for detail_url in detail_urls:
                try:
                    detail = client.get(detail_url)
                    detail.raise_for_status()
                except Exception:
                    skipped += 1
                    continue
                record = parse_ats_liguria_record(detail.text, str(detail.url))
                if record is None:
                    skipped += 1
                    continue
                if upsert_opportunity(
                    db,
                    payload=_payload(db, source, record),
                    attachments=list(record.attachments),
                ):
                    created += 1
                else:
                    updated += 1

            skipped += _hide_unfocused_records(db, source)

        source.status = "active"
        source.last_success_at = datetime.now(UTC)
        source.last_error = None
        run.status = "success"
    except Exception as exc:
        source.status = _probe_error_status(exc)
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
