from __future__ import annotations

import html
import logging
import os
import sys
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Any

import streamlit as st

st.set_page_config(
    page_title="Bandi Psicologia",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.public_snapshot import SnapshotValidationError  # noqa: E402
from app.services.static_catalog import StaticCatalog  # noqa: E402
from app.streamlit_support import (  # noqa: E402
    format_compensation,
    format_date,
    format_datetime,
    label_for,
    safe_http_url,
)

logger = logging.getLogger(__name__)

st.markdown(
    """
    <style>
      .block-container {max-width: 1180px; padding-top: 2rem;}
      [data-testid="stMetricValue"] {font-size: 1.15rem;}
      .source-note {color: #5f6b66; font-size: .88rem;}
      .result-title {font-size: 1.15rem; font-weight: 700; line-height: 1.35;}
    </style>
    """,
    unsafe_allow_html=True,
)

FILTER_WIDGET_KEYS = (
    "search_query",
    "filter_region",
    "filter_province",
    "filter_category",
    "filter_entity_type",
    "filter_area",
    "filter_status",
    "filter_deadline",
    "filter_featured",
    "filter_sort",
    "page_size",
)


def snapshot_path() -> Path:
    configured = os.getenv("PUBLIC_SNAPSHOT_PATH")
    if not configured:
        return REPOSITORY_ROOT / "data" / "bandi.sqlite"
    path = Path(configured)
    return path if path.is_absolute() else REPOSITORY_ROOT / path


def _facet_options(values: list[Any]) -> list[str]:
    return ["", *(facet.value for facet in values)]


def _facet_label(value: str, values: list[Any], empty_label: str = "Tutte") -> str:
    if not value:
        return empty_label
    counts = {facet.value: facet.count for facet in values}
    count = counts.get(value)
    suffix = f" ({count})" if count is not None else ""
    return f"{label_for(value)}{suffix}"


def _reset_filters() -> None:
    for key in FILTER_WIDGET_KEYS:
        st.session_state.pop(key, None)
    st.session_state.page = 0
    st.session_state.pop("selected_opportunity", None)


def _render_sidebar(facets: Any) -> dict[str, Any]:
    st.sidebar.header("Ricerca e filtri")
    query = st.sidebar.text_input(
        "Parole chiave",
        placeholder="es. psicoterapia, neuropsicologia…",
        key="search_query",
    )

    region = st.sidebar.selectbox(
        "Regione",
        _facet_options(facets.regions),
        format_func=lambda value: _facet_label(value, facets.regions),
        key="filter_region",
    )
    province = st.sidebar.selectbox(
        "Provincia",
        _facet_options(facets.provinces),
        format_func=lambda value: _facet_label(value, facets.provinces),
        key="filter_province",
    )
    category = st.sidebar.selectbox(
        "Tipologia",
        _facet_options(facets.categories),
        format_func=lambda value: _facet_label(value, facets.categories),
        key="filter_category",
    )
    entity_type = st.sidebar.selectbox(
        "Tipo di ente",
        _facet_options(facets.entity_types),
        format_func=lambda value: _facet_label(value, facets.entity_types),
        key="filter_entity_type",
    )
    area = st.sidebar.selectbox(
        "Ambito",
        _facet_options(facets.areas),
        format_func=lambda value: _facet_label(value, facets.areas),
        key="filter_area",
    )

    status_values = ["", *(facet.value for facet in facets.statuses)]
    status_filter = st.sidebar.selectbox(
        "Stato",
        list(dict.fromkeys(status_values)),
        format_func=lambda value: _facet_label(
            value,
            facets.statuses,
            empty_label="Aperte e in scadenza",
        ),
        key="filter_status",
    )

    deadline_labels = {
        "": "Qualsiasi scadenza",
        "7d": "Entro 7 giorni",
        "30d": "Entro 30 giorni",
        "future": "Solo future",
        "missing": "Data da verificare",
    }
    deadline = st.sidebar.selectbox(
        "Scadenza",
        list(deadline_labels),
        format_func=deadline_labels.get,
        key="filter_deadline",
    )
    featured = st.sidebar.checkbox("Solo in evidenza", key="filter_featured")

    sort_labels = {
        "deadline": "Scadenza più vicina",
        "recent": "Più recenti",
        "relevance": "Pertinenza",
        "organization": "Ente A–Z",
        "region": "Regione A–Z",
    }
    sort = st.sidebar.selectbox(
        "Ordina per",
        list(sort_labels),
        format_func=sort_labels.get,
        key="filter_sort",
    )
    page_size = st.sidebar.select_slider(
        "Risultati per pagina",
        options=[10, 20, 50],
        value=20,
        key="page_size",
    )

    st.sidebar.button("Azzera filtri", use_container_width=True, on_click=_reset_filters)
    return {
        "q": query.strip() or None,
        "region": region or None,
        "province": province or None,
        "category": category or None,
        "entity_type": entity_type or None,
        "area": area or None,
        "status_filter": status_filter or None,
        "deadline": deadline or None,
        "featured": True if featured else None,
        "sort": sort,
        "limit": page_size,
    }


def _render_detail(detail: Any | None) -> None:
    if detail is None:
        st.warning("Il bando selezionato non è più presente nell'archivio pubblico.")
        return

    header, close = st.columns([8, 1])
    with header:
        st.subheader(detail.title)
        st.caption(f"{detail.organization} · {label_for(detail.status)}")
    with close:
        if st.button("Chiudi", key="close_detail"):
            st.session_state.pop("selected_opportunity", None)
            st.rerun()

    st.info(
        "Le informazioni sono riassunte per facilitare la consultazione. "
        "Prima di candidarti verifica sempre il testo pubblicato dall'ente."
    )

    columns = st.columns(4)
    columns[0].metric("Scadenza", format_date(detail.deadline))
    columns[1].metric("Regione", detail.region or "Non indicata")
    columns[2].metric("Posti", detail.positions or "Non indicati")
    columns[3].metric(
        "Compenso",
        format_compensation(
            detail.compensation_min,
            detail.compensation_max,
            detail.compensation_period,
        ),
    )

    left, right = st.columns(2)
    with left:
        st.write("**Tipologia:**", label_for(detail.category))
        st.write("**Tipo ente:**", label_for(detail.entity_type))
        st.write("**Pubblicazione:**", format_date(detail.published_at))
        st.write("**Contratto:**", detail.contract_type or "Non indicato")
    with right:
        st.write("**Provincia:**", detail.province or "Non indicata")
        st.write("**Comune:**", detail.municipality or "Non indicato")
        st.write("**Durata:**", detail.duration or "Non indicata")
        st.write("**Candidatura:**", detail.application_mode or "Verificare sulla fonte")

    if detail.areas:
        st.write("**Ambiti:**", " · ".join(label_for(area) for area in detail.areas))
    if detail.requirements:
        st.write(
            "**Requisiti estratti:**",
            " · ".join(label_for(value) for value in detail.requirements),
        )
    description = detail.description or detail.short_description or detail.summary
    if description:
        st.markdown("#### Riepilogo")
        st.write(description)

    official_url = safe_http_url(detail.official_url)
    if official_url:
        st.link_button("Apri la fonte ufficiale", official_url, type="primary")

    valid_attachments = [
        (attachment.title, safe_http_url(attachment.url)) for attachment in detail.attachments
    ]
    valid_attachments = [(title, url) for title, url in valid_attachments if url]
    if valid_attachments:
        st.markdown("#### Allegati")
        for title, url in valid_attachments:
            st.link_button(title, url)

    st.caption(
        f"Fonte: {detail.source_name or 'non indicata'} · "
        f"Ultimo aggiornamento: {format_datetime(detail.updated_at)}"
    )
    st.divider()


def _render_result(item: Any) -> None:
    with st.container(border=True):
        safe_title = html.escape(item.title)
        st.markdown(f"<div class='result-title'>{safe_title}</div>", unsafe_allow_html=True)
        st.caption(
            f"{item.organization} · {item.region or 'Regione non indicata'} · "
            f"{label_for(item.status)}"
        )
        cols = st.columns([2, 2, 2, 3])
        cols[0].metric("Scadenza", format_date(item.deadline))
        cols[1].metric("Tipologia", label_for(item.category))
        cols[2].metric("Pertinenza", label_for(item.psychology_relevance))
        cols[3].write(item.summary or "Riepilogo non disponibile.")

        actions = st.columns([1, 1, 3])
        if actions[0].button("Dettagli", key=f"detail_{item.id}", use_container_width=True):
            st.session_state.selected_opportunity = item.id
            st.rerun()
        official_url = safe_http_url(item.official_url)
        if official_url:
            actions[1].link_button(
                "Fonte ufficiale",
                official_url,
                use_container_width=True,
            )


def main() -> None:
    st.title("Bandi Psicologia")
    st.caption(
        "Bandi, concorsi, avvisi e incarichi rilevanti per psicologhe e psicologi."
    )

    path = str(snapshot_path().resolve())
    catalog: StaticCatalog | None = None
    try:
        catalog = StaticCatalog(Path(path))
        facets = catalog.facets()
    except SnapshotValidationError as exc:
        if catalog is not None:
            catalog.close()
        logger.warning("Public snapshot unavailable: %s", exc)
        st.error(
            "L'archivio pubblico non è ancora disponibile. Nel repository apri "
            "Actions → Aggiorna archivio bandi → Run workflow, quindi attendi il redeploy."
        )
        st.stop()
    except Exception:
        if catalog is not None:
            catalog.close()
        logger.exception("Unable to open the public snapshot")
        st.error("L'archivio pubblico non è leggibile in questo momento.")
        st.stop()

    assert catalog is not None

    generated_at = datetime.fromisoformat(catalog.snapshot.generated_at)
    st.caption(
        f"Dati aggiornati al {format_datetime(generated_at)} · "
        f"{catalog.snapshot.source_count} fonti con risultati pubblicati"
    )

    filters = _render_sidebar(facets)

    signature = tuple(filters.items())
    if st.session_state.get("filter_signature") != signature:
        st.session_state.filter_signature = signature
        st.session_state.page = 0
        st.session_state.pop("selected_opportunity", None)
    page = int(st.session_state.get("page", 0))

    try:
        response = catalog.search(
            **filters,
            offset=page * filters["limit"],
        )
        selected_id = st.session_state.get("selected_opportunity")
        detail = catalog.detail(selected_id) if selected_id else None
    except Exception:
        logger.exception("Streamlit opportunity search failed")
        st.error("La ricerca non è disponibile in questo momento. Riprova tra poco.")
        st.stop()
    finally:
        catalog.close()

    if selected_id:
        _render_detail(detail)

    result_label = "risultato" if response.total == 1 else "risultati"
    st.subheader(f"{response.total} {result_label}")
    if response.total == 0:
        st.info(
            "Nessun bando corrisponde ai filtri selezionati. Prova a rimuovere uno o "
            "più filtri o a usare parole chiave diverse."
        )
        return

    total_pages = max(ceil(response.total / response.limit), 1)
    navigation = st.columns([1, 2, 1])
    if navigation[0].button("← Precedente", disabled=page == 0, use_container_width=True):
        st.session_state.page = page - 1
        st.rerun()
    navigation[1].markdown(
        f"<p style='text-align:center'>Pagina {page + 1} di {total_pages}</p>",
        unsafe_allow_html=True,
    )
    if navigation[2].button(
        "Successiva →",
        disabled=page + 1 >= total_pages,
        use_container_width=True,
    ):
        st.session_state.page = page + 1
        st.rerun()

    for item in response.items:
        _render_result(item)


if __name__ == "__main__":
    main()
