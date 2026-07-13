from __future__ import annotations

import hashlib
import re
import time
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.base import ImportResult
from app.importers.institutional import (
    PSYCHOLOGY_QUERY_TERMS,
    PSYCHOLOGY_SEARCH_TERMS,
    direct_psychology_match,
    editorial_visibility,
    find_probable_duplicate,
    is_manually_hidden,
    professional_role_match,
    upsert_opportunity,
)
from app.models import ImportRun, Opportunity, Source
from app.services.classifier import build_search_text, classify_text, normalize_text
from app.services.dates import infer_status, parse_date
from app.services.dedupe import content_hash
from app.services.source_probe import (
    _probe_error_status,
    ensure_source_catalog,
    source_refresh_order,
)
from app.target_health_catalog import TARGET_HEALTH_SOURCE_DEFINITIONS

AUTO_HIDE_SAME_URL_NOTE = (
    "Escluso automaticamente: duplicato della stessa scheda ufficiale nella fonte."
)

SPECIFIC_ADAPTER_SOURCE_NAMES = {
    "inPA - Portale del Reclutamento",
    "Azienda Zero Veneto - Concorsi",
    "Azienda Zero Piemonte - Concorsi pubblici",
    "ARCS FVG - Concorsi avvisi incarichi",
    "ASUIT Trentino - Lavora con noi",
    "ASDAA Alto Adige - Bandi di concorso",
    "AUSL Romagna - Bandi di concorso e avvisi",
    "ATS Liguria - Bandi di concorso",
    "USL Umbria 1 - Bandi di concorso",
    "USL Umbria 2 - Bandi di concorso",
    "ASL Roma 2 - Concorsi",
    "Comune di Venezia - Bandi di concorso",
    "Comune di Treviso - Bandi di concorso",
    "INAIL - Avvisi",
    "INPS - Concorsi e mobilita",
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
    "AST Ancona - Concorsi",
    "AST Ascoli Piceno - Concorsi",
    "AST Fermo - Concorsi",
    "AST Macerata - Concorsi",
    "AST Pesaro Urbino - Concorsi",
    *(definition["name"] for definition in TARGET_HEALTH_SOURCE_DEFINITIONS),
}

CATALOG_SOURCE_TYPES = {
    "external-transparency",
    "hospital-html-hub",
    "html-archive",
    "html-hub",
    "html-index",
    "html-list",
    "html-list-detail",
    "html-pdf-index",
    "html-table",
    "nextjs-public-list",
    "pat-html",
    "regional-html-hub",
    "spa-external-link",
    "private-social-jobs",
    "third-sector-hub",
    "wordpress-html-hub",
    "xml-index",
}

BLOCK_STATUSES = {"retired"}
MAX_DETAIL_LINKS_PER_SOURCE = settings.catalog_max_detail_links_per_source
MAX_RECORDS_PER_SOURCE = 30
MAX_RECORD_TEXT = 2400
TOTAL_BUDGET_SECONDS = 90
SEARCH_QUERY_KEYS = {"combine", "q", "s", "search", "text"}
SEARCHABLE_HUB_SOURCE_TYPES = {"wordpress-html-hub"}
DEEP_ADAPTER_SOURCE_TYPES = {"external-transparency", "hospital-html-hub", "pat-html"}

OPPORTUNITY_TERMS = (
    "avviso",
    "avvisi",
    "bando",
    "bandi",
    "collaborazione",
    "concorso",
    "concorsi",
    "graduatoria",
    "graduatorie",
    "incarico",
    "incarichi",
    "contratti libero professionali",
    "contratto libero professionale",
    "libero professionale",
    "manifestazione d interesse",
    "manifestazione di interesse",
    "mobilita",
    "procedura",
    "procedure",
    "selezione",
    "selezioni",
    "stabilizzazione",
    "lavora con noi",
    "offerta di lavoro",
    "offerte di lavoro",
    "opportunita di lavoro",
    "opportunita professionale",
    "posizione aperta",
    "posizioni aperte",
    "job",
    "career",
    "assegno di ricerca",
    "borsa di ricerca",
    "borsa di studio",
    "elenco idonei",
    "interpello",
    "short list",
)
LINK_DISCOVERY_TERMS = OPPORTUNITY_TERMS + (
    "lavora",
    "reclutamento",
)
LOW_SIGNAL_LINK_TERMS = (
    "amministrazione trasparente",
    "personale",
    "trasparenza",
)
DETAIL_PATH_PATTERNS = (
    r"/ap/",
    r"/avvisi?/",
    r"/bandi?/",
    r"/concorsi?/",
    r"/concorsi-avvisi/",
    r"/dettaglio",
    r"/procedure/",
)
SKIP_LINK_TERMS = (
    "accessibilita",
    "cookie",
    "facebook",
    "instagram",
    "login",
    "newsletter",
    "privacy",
    "rss",
    "twitter",
    "youtube",
)
FOLLOWUP_TITLE_TERMS = (
    "ammissione candidati",
    "approvazione atti",
    "approvazione graduatoria",
    "conferimento incarico",
    "convocazione",
    "diario prova",
    "esito colloquio",
    "graduatoria finale",
    "nomina commissione",
    "presa atto",
)
FOLLOWUP_CONTENT_TERMS = (
    "approvazione atti della commissione",
    "approvazione graduatoria",
    "graduatoria finale di merito",
    "presa atto dell esito",
)
MULTI_PROFILE_TITLE_TERMS = (
    "figure professionali",
    "incarichi individuali",
    "profili professionali",
    "profili vari",
    "vari profili",
)


@dataclass(frozen=True)
class CatalogRecord:
    external_id: str
    title: str
    description: str
    official_url: str
    published_at: datetime | None
    deadline: datetime | None


def _entity_type(source: Source) -> str:
    if source.source_type == "third-sector-hub":
        return "terzo-settore"
    if source.source_type == "private-social-jobs":
        return "privato-sociale"
    organization = normalize_text(source.organization or source.name)
    if organization.startswith("comune"):
        return "comune"
    if organization.startswith("regione"):
        return "regione"
    if organization.startswith("universita") or organization.startswith("politecnico"):
        return "universita"
    if "alma mater" in organization:
        return "universita"
    if any(
        token in organization
        for token in ("asl", "ast", "ats", "ausl", "usl", "azienda sanitaria")
    ):
        return "azienda-sanitaria"
    if any(
        token in organization
        for token in (
            "arcs",
            "ares",
            "areus",
            "asdaa",
            "asrem",
            "asuit",
            "asp",
            "aulss",
            "azienda ospedaliera",
            "azienda zero",
            "estar",
            "irccs",
            "pugliasalute",
        )
    ):
        return "azienda-sanitaria"
    return "altro-ente-pubblico"


def _has_opportunity_terms(text: str) -> bool:
    normalized = normalize_text(text)
    return any(term in normalized for term in OPPORTUNITY_TERMS)


def _has_psychology_terms(text: str) -> bool:
    normalized = normalize_text(text)
    return direct_psychology_match(text) or "neuropsicolog" in normalized


def _is_relevant_opportunity(text: str) -> bool:
    return _has_psychology_terms(text) and (
        _has_opportunity_terms(text) or professional_role_match(text)
    )


def _is_followup_content(text: str) -> bool:
    normalized = normalize_text(text)
    return any(term in normalized for term in FOLLOWUP_CONTENT_TERMS)


def _title_supports_relevance(title: str, context: str) -> bool:
    if _has_psychology_terms(title):
        return True
    normalized_title = normalize_text(title)
    return any(term in normalized_title for term in MULTI_PROFILE_TITLE_TERMS) and (
        _is_relevant_opportunity(context)
    )


def _deadline_from_text(text: str) -> datetime | None:
    normalized = normalize_text(text)
    if "scadenza graduatoria" in normalized:
        return None
    date_expression = (
        r"(?:[0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|"
        r"[0-9]{1,2}\s+[a-z]{3,12}\s+[0-9]{4})"
    )
    patterns = (
        rf"data\s+(?:e\s+ora\s+di\s+)?scadenza.{{0,80}}?({date_expression})",
        rf"scadenza(?:\s+domande)?.{{0,80}}?({date_expression})",
        rf"entro\s+il\s+({date_expression})",
        rf"termine.{{0,120}}?({date_expression})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_date(match.group(1))
    return None


def _is_bad_official_url(url: str) -> bool:
    if _is_search_url(url):
        return True
    lower = url.lower()
    return any(token in lower for token in ("/page/", "/category/"))


def _is_search_url(url: str) -> bool:
    parsed = urlparse(url)
    return any(key in SEARCH_QUERY_KEYS for key, _value in parse_qsl(parsed.query))


def _same_normalized_url(left_url: str, right_url: str) -> bool:
    left = urlparse(left_url)
    right = urlparse(right_url)
    return (
        left.scheme,
        left.netloc.lower(),
        left.path.rstrip("/"),
        left.query,
    ) == (
        right.scheme,
        right.netloc.lower(),
        right.path.rstrip("/"),
        right.query,
    )


def _is_source_listing_page(source: Source, page_url: str) -> bool:
    return _same_normalized_url(source.base_url, page_url) or _is_search_url(page_url)


def _is_followup_title(title: str) -> bool:
    normalized = normalize_text(title)
    return any(term in normalized for term in FOLLOWUP_TITLE_TERMS)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _text_for(element: Any) -> str:
    return _clean_text(element.get_text(" ", strip=True))


def _title_from_container(container: Any, fallback: str) -> str:
    for selector in ("h1", "h2", "h3", "h4", "strong", "a[href]"):
        node = container.select_one(selector) if hasattr(container, "select_one") else None
        if node is None:
            continue
        title = _text_for(node)
        if len(title) >= 12 and not normalize_text(title).isdigit():
            return title[:500]
    first_sentence = re.split(r"(?<=[.!?])\s+", fallback, maxsplit=1)[0]
    return first_sentence[:500]


def _first_useful_link(container: Any, base_url: str) -> str:
    if hasattr(container, "find_all"):
        for link in container.find_all("a", href=True):
            href = str(link["href"])
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            return urljoin(base_url, href)
    return base_url


def _external_id(source: Source, title: str, official_url: str) -> str:
    identity_parts = [source.id, normalize_text(official_url)]
    if _is_source_listing_page(source, official_url):
        identity_parts.append(normalize_text(title))
    raw = "|".join(identity_parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _record_from_text(
    source: Source,
    *,
    title: str,
    text: str,
    official_url: str,
) -> CatalogRecord:
    deadline = _deadline_from_text(text)
    return CatalogRecord(
        external_id=_external_id(source, title, official_url),
        title=title,
        description=text[:MAX_RECORD_TEXT],
        official_url=official_url,
        published_at=None,
        deadline=deadline,
    )


def _records_from_xmlish(source: Source, html: str, page_url: str) -> list[CatalogRecord]:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "html.parser")

    records: list[CatalogRecord] = []
    for atto in soup.find_all("atto"):
        text = _text_for(atto)
        if not _is_relevant_opportunity(text):
            continue
        title_node = atto.find("oggetto")
        title = _text_for(title_node) if title_node else _title_from_container(atto, text)
        official_url = _first_useful_link(atto, page_url)
        records.append(
            _record_from_text(
                source,
                title=title,
                text=text,
                official_url=official_url,
            )
        )
    return records


def parse_catalog_records(source: Source, html: str, page_url: str) -> list[CatalogRecord]:
    if source.source_type == "xml-index" or "<atto" in html[:5000].lower():
        return _records_from_xmlish(source, html, page_url)

    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script, style, noscript, nav, footer"):
        node.decompose()

    selectors = (
        "tr",
        "article",
        "li",
        ".card",
        ".views-row",
        ".node",
        ".item",
        ".search-result",
        ".bando",
        ".concorso",
    )
    records_by_key: dict[str, CatalogRecord] = {}
    for selector in selectors:
        for container in soup.select(selector):
            text = _text_for(container)
            if not (24 <= len(text) <= MAX_RECORD_TEXT):
                continue
            if not _is_relevant_opportunity(text):
                continue
            title = _title_from_container(container, text)
            if (
                _is_followup_title(title)
                or _is_followup_content(text)
                or not _title_supports_relevance(title, text)
            ):
                continue
            official_url = _first_useful_link(container, page_url)
            if _is_bad_official_url(official_url):
                continue
            record = _record_from_text(
                source,
                title=title,
                text=text,
                official_url=official_url,
            )
            if _is_search_url(page_url) and record.deadline is None:
                continue
            records_by_key[record.external_id] = record

    page_text = _text_for(soup)
    if (
        not records_by_key
        and not _is_bad_official_url(page_url)
        and not _is_source_listing_page(source, page_url)
        and _is_relevant_opportunity(page_text)
        and len(page_text) <= 6000
    ):
        if _is_followup_title(page_text[:500]):
            return []
        title = soup.title.get_text(" ", strip=True) if soup.title else source.name
        if _is_followup_title(title):
            return []
        if _is_followup_content(page_text) or not _title_supports_relevance(
            title,
            page_text,
        ):
            return []
        if not (_has_opportunity_terms(title) or _has_opportunity_terms(page_url)):
            return []
        record = _record_from_text(
            source,
            title=title,
            text=page_text[:MAX_RECORD_TEXT],
            official_url=page_url,
        )
        records_by_key[record.external_id] = record

    return list(records_by_key.values())


def _same_site(left_url: str, right_url: str) -> bool:
    left = urlparse(left_url)
    right = urlparse(right_url)
    return not right.netloc or left.netloc == right.netloc


def _is_discovery_link(text: str, href: str) -> bool:
    return _discovery_link_score(text, href) > 0


def _discovery_link_score(text: str, href: str) -> int:
    normalized = normalize_text(f"{text} {href}")
    if not normalized or any(term in normalized for term in SKIP_LINK_TERMS):
        return 0

    href_lower = href.lower()
    score = 0
    if any(term in normalized for term in LINK_DISCOVERY_TERMS):
        score += 4
    if any(re.search(pattern, href_lower) for pattern in DETAIL_PATH_PATTERNS):
        score += 5
    if any(term in normalized for term in PSYCHOLOGY_SEARCH_TERMS):
        score += 5
    if any(term in normalized for term in ("dettaglio", "scheda", "visualizza")):
        score += 1

    has_low_signal_only = any(term in normalized for term in LOW_SIGNAL_LINK_TERMS)
    if has_low_signal_only and score == 0:
        return 0
    if has_low_signal_only:
        score -= 1
    return max(score, 0)


def collect_catalog_links(html: str, base_url: str) -> list[str]:
    if MAX_DETAIL_LINKS_PER_SOURCE <= 0:
        return []
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    candidates: list[tuple[int, int, str]] = []
    for index, link in enumerate(soup.find_all("a", href=True)):
        href = str(link["href"])
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen or not _same_site(base_url, absolute):
            continue
        label = link.get_text(" ", strip=True)
        score = _discovery_link_score(label, href)
        if score <= 0:
            continue
        seen.add(absolute)
        candidates.append((score, index, absolute))
    for _score, _index, absolute in sorted(candidates, key=lambda item: (-item[0], item[1])):
        links.append(absolute)
        if len(links) >= MAX_DETAIL_LINKS_PER_SOURCE:
            break
    return links


def _source_search_urls(source: Source) -> list[str]:
    parsed = urlparse(source.base_url)
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    search_indexes = [
        index
        for index, (key, value) in enumerate(query_items)
        if key in SEARCH_QUERY_KEYS and any(
            term in normalize_text(value) for term in ("psicolog", "psicoterap")
        )
    ]
    if not search_indexes:
        if source.source_type not in SEARCHABLE_HUB_SOURCE_TYPES:
            return [source.base_url]
        urls = [source.base_url]
        for term in PSYCHOLOGY_QUERY_TERMS:
            query = urlencode({"s": term})
            urls.append(urlunparse(parsed._replace(query=query)))
        return list(dict.fromkeys(urls))

    urls: list[str] = []
    for term in PSYCHOLOGY_QUERY_TERMS:
        next_items = [
            (key, term if index in search_indexes else value)
            for index, (key, value) in enumerate(query_items)
        ]
        urls.append(urlunparse(parsed._replace(query=urlencode(next_items))))
    return list(dict.fromkeys(urls))


def _payload(db: Session, source: Source, record: CatalogRecord) -> dict[str, Any]:
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
        "entity_type": _entity_type(source),
        "region": source.region,
        "original_location": source.region,
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


def align_existing_catalog_record(
    db: Session,
    source: Source,
    record: CatalogRecord,
) -> None:
    if _is_source_listing_page(source, record.official_url):
        return
    existing_records = list(
        db.scalars(
        select(Opportunity).where(
            Opportunity.source_id == source.id,
            Opportunity.official_url == record.official_url,
        )
        )
    )
    if not existing_records:
        return

    existing = next(
        (
            candidate
            for candidate in existing_records
            if candidate.external_id == record.external_id
        ),
        None,
    )
    if existing is None:
        existing = max(
            existing_records,
            key=lambda candidate: (
                candidate.editorial_status == "approved",
                candidate.status in {"open", "closing_soon"},
                candidate.deadline is not None,
                candidate.deadline or datetime.min.replace(tzinfo=UTC),
                len(candidate.description or ""),
            ),
        )
        existing.external_id = record.external_id

    for duplicate in existing_records:
        if duplicate.id == existing.id or is_manually_hidden(duplicate):
            continue
        duplicate.editorial_status = "hidden"
        duplicate.editorial_notes = AUTO_HIDE_SAME_URL_NOTE
    db.flush()


def _fetch_text(client: httpx.Client, url: str) -> str | None:
    response = client.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if not any(kind in content_type for kind in ("html", "xml", "text", "json")):
        return None
    return response.text


def _sources_for_generic_import(db: Session) -> list[Source]:
    ensure_source_catalog(db)
    sources = list(
        db.scalars(
            select(Source)
            .where(
                Source.source_type.in_(CATALOG_SOURCE_TYPES),
                Source.source_type.not_in(DEEP_ADAPTER_SOURCE_TYPES),
            )
        )
    )
    return source_refresh_order(sources)


def run_catalog_sources_import(db: Session) -> ImportResult:
    run = ImportRun(source_id=None, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            timeout=httpx.Timeout(6, connect=3),
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            import_deadline = time.monotonic() + TOTAL_BUDGET_SECONDS
            for source in _sources_for_generic_import(db):
                if source.name in SPECIFIC_ADAPTER_SOURCE_NAMES or source.status in BLOCK_STATUSES:
                    skipped += 1
                    continue
                if time.monotonic() > import_deadline:
                    skipped += 1
                    continue
                try:
                    records_by_id: dict[str, CatalogRecord] = {}
                    for source_url in _source_search_urls(source):
                        html = _fetch_text(client, source_url)
                        if html is None:
                            skipped += 1
                            continue

                        records_by_id.update(
                            {
                                record.external_id: record
                                for record in parse_catalog_records(source, html, source_url)
                            }
                        )
                        for url in collect_catalog_links(html, source_url):
                            if time.monotonic() > import_deadline:
                                break
                            try:
                                detail_html = _fetch_text(client, url)
                            except Exception:
                                continue
                            if detail_html is None:
                                continue
                            for record in parse_catalog_records(source, detail_html, url):
                                records_by_id[record.external_id] = record
                            if len(records_by_id) >= MAX_RECORDS_PER_SOURCE:
                                break
                        if len(records_by_id) >= MAX_RECORDS_PER_SOURCE:
                            break

                    for record in list(records_by_id.values())[:MAX_RECORDS_PER_SOURCE]:
                        if not _is_relevant_opportunity(
                            f"{record.title} {record.description}"
                        ):
                            skipped += 1
                            continue
                        align_existing_catalog_record(db, source, record)
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
