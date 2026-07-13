from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.base import ImportResult
from app.importers.institutional import direct_psychology_match, is_manually_hidden
from app.models import ImportRun, Opportunity, Source
from app.services.classifier import build_search_text, classify_text, normalize_text
from app.services.dates import infer_status, parse_date
from app.services.dedupe import content_hash

INPA_SOURCE_NAME = "inPA - Portale del Reclutamento"
INPA_PUBLIC_BASE_URL = "https://www.inpa.gov.it"
INPA_API_BASE_URL = "https://portale.inpa.gov.it"
INPA_SEARCH_PATH = "/concorsi-smart/api/concorso-public-area/search-better"
DIRECT_DESCRIPTION_ROLE_PATTERN = re.compile(
    r"\bn\.\s*\d+[^.;]{0,100}\bpsicolog(?:o|a|i|he|e)\b|"
    r"\bprofil[io][^.]{0,120}\bpsicolog(?:o|a|i|he|e)\b|"
    r"\bfigure professionali ricercate[^.]{0,350}\bpsicolog(?:o|a|i|he|e)\b|"
    r"\bespert[oaie]\s+psicolog(?:o|a|i|he|e)\b|"
    r"\bpsicolog(?:o|a|i|he|e)\s+con\b"
)
REVOKED_PROCEDURE_PATTERN = re.compile(
    r"\brevoca(?:\s+del(?:la)?|\s+della)?\s+"
    r"(?:concorso|avviso|bando|procedura|selezione)\b"
)
AUTO_HIDE_DUPLICATE_NOTE = (
    "Escluso automaticamente: duplicato inPA con stesso identificativo ufficiale."
)
AUTO_HIDE_NOT_OPEN_NOTE = (
    "Escluso automaticamente: procedura non piu presente tra i bandi aperti inPA."
)
ITALIAN_REGIONS = {
    "Abruzzo",
    "Basilicata",
    "Calabria",
    "Campania",
    "Emilia-Romagna",
    "Friuli-Venezia Giulia",
    "Lazio",
    "Liguria",
    "Lombardia",
    "Marche",
    "Molise",
    "Piemonte",
    "Puglia",
    "Sardegna",
    "Sicilia",
    "Toscana",
    "Trentino-Alto Adige",
    "Umbria",
    "Valle d'Aosta",
    "Veneto",
}


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    return BeautifulSoup(value, "html.parser").get_text(" ", strip=True)


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == INPA_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=INPA_SOURCE_NAME,
        source_type="api",
        base_url=f"{INPA_PUBLIC_BASE_URL}/bandi-e-avvisi/",
        organization="Dipartimento della Funzione Pubblica",
        import_method="public-json-api",
        refresh_frequency="daily",
        status="active",
        technical_notes=(
            "Endpoint pubblico usato dalla pagina inPA: "
            f"{INPA_API_BASE_URL}{INPA_SEARCH_PATH}"
        ),
    )
    db.add(source)
    db.flush()
    return source


def remove_demo_source(db: Session) -> int:
    demo_source = db.scalar(select(Source).where(Source.name == "Fonte demo aggregata"))
    if demo_source is None:
        return 0

    deleted_count = len(
        list(db.scalars(select(Opportunity.id).where(Opportunity.source_id == demo_source.id)))
    )
    db.execute(delete(Opportunity).where(Opportunity.source_id == demo_source.id))
    demo_source.status = "retired"
    demo_source.technical_notes = (
        "Fonte fixture archiviata dopo il primo import reale. "
        "Conservata per mantenere lo storico import."
    )
    return deleted_count


def _search_body(term: str) -> dict[str, Any]:
    return {
        "text": term,
        "categoriaId": None,
        "regioneId": None,
        "status": ["OPEN"],
        "settoreId": None,
        "provinciaCodice": None,
        "dateFrom": None,
        "dateTo": None,
        "livelliAnzianitaIds": None,
        "tipoImpiegoId": None,
        "salaryMin": None,
        "salaryMax": None,
        "enteRiferimentoName": "",
    }


def _fetch_pages(
    client: httpx.Client,
    *,
    term: str,
    max_pages: int,
    require_complete: bool = False,
) -> dict[str, dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for page in range(max_pages):
        response = client.post(
            INPA_SEARCH_PATH,
            params={"page": page, "size": settings.inpa_page_size},
            json=_search_body(term),
        )
        response.raise_for_status()
        payload = response.json()
        for item in payload.get("content", []):
            external_id = item.get("id")
            if external_id:
                records_by_id[external_id] = item

        total_pages = int(payload.get("totalPages", 0))
        if require_complete and total_pages > max_pages:
            raise RuntimeError(
                "Scansione inPA incompleta: "
                f"{total_pages} pagine OPEN disponibili, limite configurato {max_pages}. "
                "Aumentare INPA_OPEN_SCAN_MAX_PAGES."
            )
        if page + 1 >= min(total_pages, max_pages):
            break
    return records_by_id


def _fetch_records(client: httpx.Client) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    if settings.inpa_open_scan_enabled:
        records_by_id.update(
            _fetch_pages(
                client,
                term="",
                max_pages=settings.inpa_open_scan_max_pages,
                require_complete=True,
            )
        )
    for term in settings.inpa_search_terms:
        records_by_id.update(
            _fetch_pages(
                client,
                term=term,
                max_pages=settings.inpa_max_pages,
            )
        )
    return list(records_by_id.values())


def _professional_match(raw: dict[str, Any]) -> str | None:
    title = normalize_text(raw.get("titolo"))
    figure = normalize_text(raw.get("figuraRicercata"))
    description = normalize_text(
        " ".join(
            [
                strip_html(raw.get("descrizione")),
                strip_html(raw.get("descrizioneBreve")),
            ]
        )
    )

    if REVOKED_PROCEDURE_PATTERN.search(title):
        return None

    individual_profession = re.compile(r"\bpsicolog[oaie]\b|\bpsicoterapeut[aei]\b")
    title_without_order_name = title.replace("ordine degli psicologi", "")

    if individual_profession.search(figure):
        return "direct"
    if individual_profession.search(title_without_order_name):
        return "direct"
    if direct_psychology_match(figure):
        return "direct"
    if direct_psychology_match(title_without_order_name):
        return "direct"
    if "laureat" in title and "psicologia" in title:
        return "direct"
    if "laurea" in title and "psicologia" in title:
        return "direct"

    has_psychology_degree = "laurea in psicologia" in description or "lm 51" in description
    has_professional_requirement = "albo" in description or "abilitazione" in description
    if has_psychology_degree and has_professional_requirement:
        return "eligible"
    if DIRECT_DESCRIPTION_ROLE_PATTERN.search(description):
        return "direct"
    if direct_psychology_match(description):
        return "eligible"
    if (
        "scienze comportamentali" in description
        and "salute mentale" in description
    ):
        return "eligible"
    return None


def _professionally_relevant(raw: dict[str, Any]) -> bool:
    return _professional_match(raw) is not None


def _notes_with_duplicate_auto_hide(existing: str | None) -> str:
    if not existing:
        return AUTO_HIDE_DUPLICATE_NOTE
    if AUTO_HIDE_DUPLICATE_NOTE in existing:
        return existing
    return f"{existing}\n{AUTO_HIDE_DUPLICATE_NOTE}"


def _hide_duplicate_inpa_opportunities(db: Session, source: Source) -> int:
    opportunities = list(
        db.scalars(
            select(Opportunity)
            .where(
                Opportunity.source_id == source.id,
                Opportunity.external_id.is_not(None),
            )
            .order_by(Opportunity.external_id, Opportunity.created_at)
        )
    )
    by_external_id: dict[str, list[Opportunity]] = {}
    for opportunity in opportunities:
        if opportunity.external_id:
            by_external_id.setdefault(opportunity.external_id, []).append(opportunity)

    hidden_count = 0
    rank = {"approved": 0, "pending": 1, "hidden": 2}
    for duplicates in by_external_id.values():
        if len(duplicates) <= 1:
            continue
        keep = sorted(
            duplicates,
            key=lambda item: (
                rank.get(item.editorial_status, 3),
                item.created_at,
            ),
        )[0]
        for duplicate in duplicates:
            if duplicate.id == keep.id:
                continue
            if duplicate.editorial_status != "hidden":
                duplicate.editorial_status = "hidden"
                hidden_count += 1
            duplicate.editorial_notes = _notes_with_duplicate_auto_hide(
                duplicate.editorial_notes
            )
    return hidden_count


def _hide_inpa_records_no_longer_open(
    db: Session,
    source: Source,
    seen_external_ids: set[str],
) -> int:
    hidden_count = 0
    opportunities = db.scalars(
        select(Opportunity).where(
            Opportunity.source_id == source.id,
            Opportunity.external_id.is_not(None),
            Opportunity.status != "closed",
        )
    ).all()
    for opportunity in opportunities:
        if opportunity.external_id in seen_external_ids:
            continue
        opportunity.status = "closed"
        if not is_manually_hidden(opportunity):
            opportunity.editorial_status = "hidden"
            opportunity.editorial_notes = AUTO_HIDE_NOT_OPEN_NOTE
        hidden_count += 1
    return hidden_count


def _category(raw: dict[str, Any], fallback: str) -> str:
    categories = " ".join(raw.get("categorie") or [])
    normalized = normalize_text(categories)
    if "concorso" in normalized:
        return "concorso-pubblico"
    if "mobilita" in normalized:
        return "mobilita"
    if "incarico" in normalized:
        return "incarico-libero-professionale"
    return fallback


def _status(raw: dict[str, Any], deadline: datetime | None) -> str:
    if raw.get("calculatedStatus") == "CLOSED":
        return "closed"
    return infer_status(deadline)


def _first(items: list[str] | None, index: int) -> str | None:
    if not items or len(items) <= index:
        return None
    return items[index]


def _location_parts(locations: list[str]) -> tuple[str | None, str | None, str | None]:
    region = _first(locations, 0)
    province = _first(locations, 1)
    municipality = _first(locations, 2)
    if region and province and region not in ITALIAN_REGIONS and province in ITALIAN_REGIONS:
        return province, region, municipality
    return region, province, municipality


def _organization(raw: dict[str, Any]) -> str:
    organizations = raw.get("entiRiferimento") or []
    return organizations[0] if organizations else "Ente non specificato"


def _payload(source: Source, raw: dict[str, Any]) -> dict[str, Any]:
    description = strip_html(raw.get("descrizione"))
    short_description = strip_html(raw.get("descrizioneBreve"))
    title = raw.get("titolo") or "Bando inPA senza titolo"
    organization = _organization(raw)
    locations = raw.get("sedi") or []
    region, province, municipality = _location_parts(locations)
    deadline = parse_date(raw.get("dataScadenza"))
    published_at = parse_date(raw.get("dataPubblicazione"))
    classification = classify_text(
        title,
        raw.get("figuraRicercata"),
        description,
        short_description,
    )
    external_id = raw["id"]
    match = _professional_match(raw)
    official_url = (
        f"{INPA_PUBLIC_BASE_URL}/bandi-e-avvisi/dettaglio-bando-avviso/"
        f"?concorso_id={external_id}"
    )

    payload: dict[str, Any] = {
        "external_id": external_id,
        "source_id": source.id,
        "title": title,
        "normalized_title": normalize_text(title),
        "short_description": short_description[:900] or description[:900],
        "description": description,
        "summary": short_description[:420] or description[:420],
        "category": _category(raw, classification.category),
        "areas": classification.areas,
        "psychology_relevance": classification.psychology_relevance,
        "relevance_score": classification.relevance_score,
        "organization": organization,
        "entity_type": "altro-ente-pubblico",
        "region": region,
        "province": province,
        "municipality": municipality,
        "original_location": ", ".join(locations),
        "status": _status(raw, deadline),
        "published_at": published_at,
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": raw.get("numPosti"),
        "compensation_min": raw.get("salaryMin"),
        "compensation_max": raw.get("salaryMax"),
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale inPA.",
        "official_url": official_url,
        "organization_url": raw.get("linkReindirizzamento"),
        "content_hash": content_hash(title, description, short_description),
        "editorial_status": "approved" if match == "direct" else "pending",
    }
    payload["search_text"] = build_search_text(
        payload["title"],
        payload["description"],
        payload["short_description"],
        payload["organization"],
        payload["region"],
        payload["province"],
        payload["category"],
        payload["areas"],
        payload["requirements"],
    )
    return payload


def run_inpa_import(db: Session, remove_demo: bool = False) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()

    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=INPA_API_BASE_URL,
            timeout=30,
            verify=settings.inpa_verify_tls,
            headers={
                "Accept": "application/json",
                "User-Agent": "BandiPsicologiaMVP/0.1 (+consultazione fonti pubbliche)",
                "Referer": f"{INPA_PUBLIC_BASE_URL}/bandi-e-avvisi/",
            },
        ) as client:
            records = _fetch_records(client)

        if settings.inpa_open_scan_enabled and not records:
            raise RuntimeError("Scansione inPA OPEN vuota: aggiornamento annullato per sicurezza.")

        seen_external_ids = {str(raw["id"]) for raw in records if raw.get("id")}

        for raw in records:
            existing = db.scalar(
                select(Opportunity).where(
                    Opportunity.source_id == source.id,
                    Opportunity.external_id == raw["id"],
                )
            )
            if not _professionally_relevant(raw):
                if existing:
                    existing.editorial_status = "hidden"
                    existing.editorial_notes = (
                        "Escluso automaticamente: nessun profilo professionale "
                        "psicologico identificato."
                    )
                skipped += 1
                continue

            payload = _payload(source, raw)

            if existing:
                manually_hidden = is_manually_hidden(existing)
                previous_notes = existing.editorial_notes
                for key, value in payload.items():
                    setattr(existing, key, value)
                if manually_hidden:
                    existing.editorial_status = "hidden"
                    existing.editorial_notes = previous_notes
                updated += 1
            else:
                db.add(Opportunity(**payload))
                created += 1

        if remove_demo and created + updated > 0:
            remove_demo_source(db)

        if settings.inpa_open_scan_enabled:
            _hide_inpa_records_no_longer_open(db, source, seen_external_ids)
        _hide_duplicate_inpa_opportunities(db, source)
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
