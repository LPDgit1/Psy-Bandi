from __future__ import annotations

import hashlib
import re
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
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

ASL_PIEMONTE_SOURCE_NAMES = {
    "ASL AL - Bandi di concorso",
    "ASL AT - Concorsi in vigore",
    "ASL CN1 - Concorsi pubblici e avvisi",
    "ASL CN2 - Bandi di concorso",
    "ASL Citta di Torino - Concorsi pubblici",
    "ASL NO - Portale concorsi",
    "ASL TO3 - Portale trasparenza",
    "ASL TO4 - Concorsi",
    "ASL TO5 - Bandi di concorso",
    "ASL VC - Concorsi",
    "ASL VCO - Concorsi e selezioni",
}

DOCUMENT_TERMS = (
    "avviso",
    "bando",
    "concorso",
    "incarico",
    "mobilita",
    "selezione",
)
SKIP_DOCUMENT_TERMS = (
    "ammess",
    "commission",
    "convoc",
    "criteri",
    "diario",
    "esito",
    "graduator",
    "prova",
)
SKIP_HREF_PREFIXES = ("#", "javascript:", "mailto:", "tel:")
MULTI_PROFILE_TITLE_TERMS = (
    "figure professionali",
    "incarichi individuali",
    "profili professionali",
    "profili vari",
    "vari profili",
)


@dataclass(frozen=True)
class PiemonteRecord:
    external_id: str
    title: str
    description: str
    official_url: str
    published_at: datetime | None
    deadline: datetime | None


def _safe_text(node: Any) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def _is_psychology_document(text: str, href: str = "") -> bool:
    combined = f"{text} {href}"
    normalized = normalize_text(combined)
    return (
        (direct_psychology_match(combined) or "neuropsicolog" in normalized)
        and any(term in normalized for term in DOCUMENT_TERMS)
        and not any(term in normalized for term in SKIP_DOCUMENT_TERMS)
    )


def _is_usable_href(href: str) -> bool:
    normalized = href.strip().lower()
    return bool(normalized) and not normalized.startswith(SKIP_HREF_PREFIXES)


def _source_external_id(source: Source, title: str, official_url: str) -> str:
    raw = "|".join([source.id, normalize_text(title), normalize_text(official_url)])
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _deadline_from_text(text: str) -> datetime | None:
    patterns = (
        r"scadenza(?:\s+domande)?[:\s]+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        r"entro\s+il\s+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        r"termine.*?([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_date(match.group(1))
    return None


def _is_structural_link(label: str, href: str) -> bool:
    normalized = normalize_text(f"{label} {href}")
    query_keys = {key.lower() for key, _value in parse_qsl(urlparse(href).query)}
    if query_keys.intersection({"page", "p", "pagina"}):
        return True
    if re.search(r"/page/\d+/?$", urlparse(href).path.lower()):
        return True
    if not normalize_text(label) or normalize_text(label).isdigit():
        return True
    return any(
        term in normalized
        for term in (
            "pagina attuale",
            "pagina successiva",
            "regione piemonte",
            "seguente",
            "ultima pagina",
        )
    )


def _has_focused_relevance(title: str, description: str) -> bool:
    if direct_psychology_match(title):
        return True
    normalized_title = normalize_text(title)
    return any(term in normalized_title for term in MULTI_PROFILE_TITLE_TERMS) and (
        _is_psychology_document(description)
    )


def _ancestor_description(link: Any) -> str:
    best = _safe_text(link)
    parent = link.parent
    depth = 0
    while parent is not None and depth < 5:
        if getattr(parent, "name", "") in {
            "[document]",
            "table",
            "tbody",
            "body",
            "html",
        }:
            break
        text = _safe_text(parent)
        if 20 <= len(text) <= 1400:
            best = text
        if _is_psychology_document(text, str(link.get("href", ""))) and len(text) >= 40:
            return text
        parent = parent.parent
        depth += 1
    return best


def _document_title(link: Any, description: str, official_url: str) -> str:
    parent = link.parent
    depth = 0
    while parent is not None and depth < 4:
        if getattr(parent, "name", "") in {"[document]", "body", "html"}:
            break
        heading = parent.find(["h1", "h2", "h3", "h4", "strong"])
        heading_text = _safe_text(heading) if heading else ""
        if len(heading_text) >= 16:
            return heading_text
        parent = parent.parent
        depth += 1

    label = _safe_text(link)
    if len(label) >= 16:
        return label
    if len(description) >= 16:
        return description[:240]
    return official_url.rsplit("/", 1)[-1].replace("_", " ").replace("-", " ")


def _record_from_document_link(source: Source, link: Any, page_url: str) -> PiemonteRecord | None:
    href = str(link.get("href", ""))
    if not _is_usable_href(href):
        return None
    label = _safe_text(link)
    if _is_structural_link(label, href):
        return None
    description = _ancestor_description(link)
    if not _is_psychology_document(f"{label} {description}", href):
        return None
    official_url = urljoin(page_url, href)
    title = _document_title(link, description, official_url)
    if not _has_focused_relevance(title, description):
        return None
    deadline = _deadline_from_text(description)
    return PiemonteRecord(
        external_id=_source_external_id(source, title, official_url),
        title=title[:500],
        description=description[:2400],
        official_url=official_url,
        published_at=None,
        deadline=deadline,
    )


def _records_from_html(source: Source, html: str, page_url: str) -> list[PiemonteRecord]:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("header, nav, footer, .pagination, .pager"):
        node.decompose()
    records_by_id: dict[str, PiemonteRecord] = {}
    seen_urls: set[str] = set()
    for link in soup.find_all("a", href=True):
        record = _record_from_document_link(source, link, page_url)
        if record is not None:
            records_by_id[record.external_id] = record
            seen_urls.add(record.official_url)

    for container in soup.select("tr, article, li, .card, .views-row, .item"):
        text = _safe_text(container)
        if not 24 <= len(text) <= 3000:
            continue
        if not _is_psychology_document(text):
            continue
        all_links = container.find_all("a", href=True)
        link = next(
            (
                candidate
                for candidate in all_links
                if _is_usable_href(str(candidate["href"]))
            ),
            None,
        )
        if all_links and link is None:
            continue
        official_url = urljoin(page_url, str(link["href"])) if link else page_url
        if official_url in seen_urls:
            continue
        title_node = container.find(["h1", "h2", "h3", "h4", "strong", "a"])
        title = _safe_text(title_node) if title_node else text[:240]
        if len(title) < 20:
            title = text[:240]
        if not _has_focused_relevance(title, text):
            continue
        record = PiemonteRecord(
            external_id=_source_external_id(source, title, official_url),
            title=title[:500],
            description=text[:2400],
            official_url=official_url,
            published_at=None,
            deadline=_deadline_from_text(text),
        )
        records_by_id[record.external_id] = record
        seen_urls.add(record.official_url)
    return list(records_by_id.values())


def _records_from_xml(source: Source, xml: str, page_url: str) -> list[PiemonteRecord]:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(xml, "html.parser")
    records: list[PiemonteRecord] = []
    for atto in soup.find_all("atto"):
        text = _safe_text(atto)
        if not _is_psychology_document(text):
            continue
        title_node = atto.find("oggetto")
        title = _safe_text(title_node) if title_node else text[:240]
        link_node = atto.find("web")
        official_url = (
            urljoin(page_url, _safe_text(link_node))
            if link_node and _safe_text(link_node)
            else page_url
        )
        published_node = atto.find("pubblicatodal")
        records.append(
            PiemonteRecord(
                external_id=_source_external_id(source, title, official_url),
                title=title[:500],
                description=text[:2400],
                official_url=official_url,
                published_at=parse_date(_safe_text(published_node)) if published_node else None,
                deadline=_deadline_from_text(text),
            )
        )
    return records


def parse_piemonte_records(source: Source, text: str, page_url: str) -> list[PiemonteRecord]:
    if source.source_type == "xml-index" or "<atto" in text[:5000].lower():
        return _records_from_xml(source, text, page_url)
    return _records_from_html(source, text, page_url)


def _payload(db: Session, source: Source, record: PiemonteRecord) -> dict[str, Any]:
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
        "region": "Piemonte",
        "original_location": "Piemonte",
        "status": status,
        "published_at": record.published_at,
        "deadline": record.deadline,
        "last_seen_at": datetime.now(UTC),
        "requirements": classification.requirements,
        "application_mode": f"Consultare la fonte ufficiale: {source.name}.",
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


def _source_links(source: Source, html: str) -> list[str]:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "html.parser")
    urls = [source.base_url]
    for link in soup.find_all("a", href=True):
        label = normalize_text(f"{link.get_text(' ', strip=True)} {link['href']}")
        if "concorsiinvigore xml" in label or "concorsi pubblici" in label:
            url = urljoin(source.base_url, str(link["href"]))
            if url not in urls:
                urls.append(url)
    return urls[:4]


def _sources(db: Session) -> list[Source]:
    ensure_source_catalog(db)
    return list(
        db.scalars(select(Source).where(Source.name.in_(ASL_PIEMONTE_SOURCE_NAMES)).order_by(Source.name))
    )


def _hide_parser_artifacts(db: Session, source: Source) -> None:
    opportunities = db.scalars(
        select(Opportunity).where(
            Opportunity.source_id == source.id,
            Opportunity.editorial_status == "approved",
        )
    ).all()
    for opportunity in opportunities:
        title = normalize_text(opportunity.title)
        official_url = (opportunity.official_url or "").strip().lower()
        if (
            official_url.startswith(("mailto:", "tel:"))
            or title.startswith(("tel:", "telefono", "email", "e-mail"))
            or "@" in title
            or _is_structural_link(opportunity.title, opportunity.official_url)
            or not _has_focused_relevance(
                opportunity.title,
                opportunity.description or "",
            )
        ):
            opportunity.editorial_status = "hidden"
            opportunity.editorial_notes = (
                "Nascosto automaticamente: link di contatto non interpretabile come bando."
            )


def run_asl_piemonte_import(db: Session) -> ImportResult:
    run = ImportRun(source_id=None, status="running")
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
            for source in _sources(db):
                records_by_id: dict[str, PiemonteRecord] = {}
                try:
                    response = client.get(source.base_url)
                    response.raise_for_status()
                    urls = _source_links(source, response.text)
                    for url in urls:
                        page = response.text if url == source.base_url else client.get(url).text
                        for record in parse_piemonte_records(source, page, url):
                            records_by_id[record.external_id] = record
                    for record in records_by_id.values():
                        if upsert_opportunity(
                            db,
                            payload=_payload(db, source, record),
                            attachments=[],
                        ):
                            created += 1
                        else:
                            updated += 1
                    _hide_parser_artifacts(db, source)
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
