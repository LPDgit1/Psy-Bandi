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
      [data-testid="stAppViewContainer"] {
        background:
          radial-gradient(circle at 86% 3%, rgba(41, 111, 85, .13), transparent 26rem),
          linear-gradient(180deg, #f4f8f6 0%, #eaf1ed 100%);
      }
      [data-testid="stHeader"] {background: rgba(244, 248, 246, .9);}
      [data-testid="stSidebar"] {
        background: #e5eee9;
        border-right: 1px solid #c3d5cb;
      }
      .block-container {max-width: 1180px; padding-top: 1.6rem; padding-bottom: 3rem;}
      [data-testid="stMetricValue"] {font-size: 1.15rem;}
      [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border-color: #cbdad2 !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 24px rgba(24, 58, 45, .09);
      }
      .hero-panel {
        min-height: 11rem;
        padding: 1.7rem 1.9rem;
        border: 1px solid #1d5845;
        border-radius: 20px;
        background: linear-gradient(135deg, #123d31 0%, #246a52 100%);
        box-shadow: 0 12px 30px rgba(18, 61, 49, .18);
      }
      .hero-eyebrow, .toggle-eyebrow, .result-summary-label {
        color: #1d6b4d;
        font-size: .72rem;
        font-weight: 750;
        letter-spacing: .09em;
        text-transform: uppercase;
      }
      .hero-eyebrow {color: #9fe0c1;}
      .hero-title {
        color: #ffffff;
        font-size: clamp(2rem, 4vw, 3rem);
        font-weight: 780;
        letter-spacing: -.035em;
        line-height: 1.05;
        margin: .35rem 0 .7rem;
      }
      .hero-copy {color: #e2eee8; font-size: 1.02rem; line-height: 1.55; max-width: 44rem;}
      .source-note {color: #bcd7cb; font-size: .84rem; margin-top: .8rem;}
      .summary-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .8rem;
        margin: 1.25rem 0 1.45rem;
      }
      .summary-item {
        padding: .9rem 1rem;
        border: 1px solid #cfded6;
        border-radius: 13px;
        background: #ffffff;
        box-shadow: 0 4px 14px rgba(24, 58, 45, .055);
      }
      .summary-item:nth-child(1) {border-top: 3px solid #287a57;}
      .summary-item:nth-child(2) {border-top: 3px solid #c18428;}
      .summary-item:nth-child(3) {border-top: 3px solid #4f718d;}
      .summary-label {
        color: #6a7972;
        font-size: .74rem;
        font-weight: 650;
        text-transform: uppercase;
      }
      .summary-value {color: #183f30; font-size: 1.05rem; font-weight: 750; margin-top: .16rem;}
      .result-heading {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        border-left: 4px solid #2c7b59;
        padding-left: .85rem;
      }
      .result-kicker {color: #61736a; font-size: .82rem; font-weight: 600; margin-bottom: .28rem;}
      .result-title {color: #183f30; font-size: 1.16rem; font-weight: 750; line-height: 1.35;}
      .status-badge {
        display: inline-flex;
        flex: 0 0 auto;
        align-items: center;
        padding: .32rem .62rem;
        border-radius: 999px;
        font-size: .75rem;
        font-weight: 700;
        white-space: nowrap;
      }
      .status-open {color: #0d5936; background: #ccebd9; border: 1px solid #a8d8bc;}
      .status-closing {color: #744400; background: #ffe4ad; border: 1px solid #eac879;}
      .status-review {color: #694600; background: #fff0c7; border: 1px solid #e7c66f;}
      .status-closed {color: #713737; background: #f3d8d8; border: 1px solid #ddb7b7;}
      .status-neutral {color: #53635c; background: #edf1ef;}
      .result-meta-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .65rem;
        margin: 1rem 0;
      }
      .result-meta {
        padding: .68rem .78rem;
        border-radius: 11px;
        background: #edf3f0;
        border: 1px solid #d8e4de;
      }
      .result-meta span {
        display: block;
        color: #6d7b75;
        font-size: .7rem;
        text-transform: uppercase;
      }
      .result-meta strong {display: block; color: #294a3d; font-size: .9rem; margin-top: .14rem;}
      .result-summary-label {margin-top: .1rem;}
      .result-summary {color: #455c52; line-height: 1.52; margin: .2rem 0 .75rem;}
      .area-chip {
        display: inline-block;
        color: #365178;
        background: #e5ecf6;
        border-radius: 999px;
        font-size: .75rem;
        margin: 0 .32rem .55rem 0;
        padding: .24rem .55rem;
      }
      .stButton > button, .stLinkButton > a {border-radius: 10px;}
      @media (max-width: 700px) {
        .hero-panel {min-height: auto; padding: 1.35rem;}
        .summary-strip, .result-meta-grid {grid-template-columns: 1fr;}
        .result-heading {display: block;}
        .status-badge {margin-top: .65rem;}
      }
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
    "include_review",
)
FILTER_DEFAULTS: dict[str, Any] = {
    "search_query": "",
    "filter_region": "",
    "filter_province": "",
    "filter_category": "",
    "filter_entity_type": "",
    "filter_area": "",
    "filter_status": "",
    "filter_deadline": "",
    "filter_featured": False,
    "filter_sort": "deadline",
    "page_size": 20,
    "include_review": False,
}


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
    for key, value in FILTER_DEFAULTS.items():
        st.session_state[key] = value
    st.session_state.page = 0
    st.session_state.pop("filter_signature", None)
    st.session_state.pop("selected_opportunity", None)


def _initialize_filter_state() -> None:
    for key, value in FILTER_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def _reset_province() -> None:
    st.session_state.filter_province = ""
    st.session_state.page = 0
    st.session_state.pop("selected_opportunity", None)


def _reset_status_for_review_toggle() -> None:
    st.session_state.filter_status = ""
    st.session_state.page = 0
    st.session_state.pop("selected_opportunity", None)


def _context_filter_state() -> dict[str, Any]:
    return {
        "q": str(st.session_state.get("search_query", "")).strip() or None,
        "region": st.session_state.get("filter_region") or None,
        "province": st.session_state.get("filter_province") or None,
        "category": st.session_state.get("filter_category") or None,
        "entity_type": st.session_state.get("filter_entity_type") or None,
        "area": st.session_state.get("filter_area") or None,
        "status_filter": st.session_state.get("filter_status") or None,
        "deadline": st.session_state.get("filter_deadline") or None,
        "featured": True if st.session_state.get("filter_featured") else None,
        "include_review": bool(st.session_state.get("include_review")),
    }


def _facet_count(facets: Any, value: str) -> int:
    return next((facet.count for facet in facets.statuses if facet.value == value), 0)


def _render_page_header(facets: Any, generated_at: datetime, source_count: int) -> None:
    introduction, visibility = st.columns([3.3, 1.25], gap="large")
    with introduction:
        st.markdown(
            f"""
            <div class="hero-panel">
              <div class="hero-eyebrow">Opportunità professionali per la psicologia</div>
              <div class="hero-title">Bandi Psicologia</div>
              <div class="hero-copy">
                Bandi, concorsi, avvisi e incarichi raccolti da fonti pubbliche,
                in una vista semplice da consultare e filtrare.
              </div>
              <div class="source-note">
                Dati aggiornati al {html.escape(format_datetime(generated_at))} ·
                {source_count} fonti con risultati pubblicati
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with visibility:
        with st.container(border=True):
            st.markdown('<div class="toggle-eyebrow">Visualizzazione</div>', unsafe_allow_html=True)
            review_count = _facet_count(facets, "review")
            st.toggle(
                f"Mostra anche “Da verificare” ({review_count})",
                key="include_review",
                help=(
                    "Aggiunge ai bandi aperti quelli per cui stato o scadenza "
                    "richiedono un controllo sulla fonte ufficiale."
                ),
                on_change=_reset_status_for_review_toggle,
            )
            st.caption("La vista iniziale mostra soltanto aperti e in scadenza.")


def _render_sidebar(facets: Any) -> dict[str, Any]:
    st.sidebar.header("Ricerca e filtri")
    st.sidebar.caption("Affina i risultati per territorio, ambito e scadenza.")
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
        on_change=_reset_province,
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
            empty_label=(
                "Aperte, in scadenza e da verificare"
                if st.session_state.include_review
                else "Aperte e in scadenza"
            ),
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
        "include_review": bool(st.session_state.include_review),
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
        safe_organization = html.escape(item.organization)
        location = (
            " · ".join(value for value in (item.region, item.province) if value)
            or "Territorio non indicato"
        )
        status_class = {
            "open": "status-open",
            "closing_soon": "status-closing",
            "review": "status-review",
            "closed": "status-closed",
        }.get(item.status, "status-neutral")
        st.markdown(
            f"""
            <div class="result-heading">
              <div>
                <div class="result-kicker">{safe_organization} · {html.escape(location)}</div>
                <div class="result-title">{safe_title}</div>
              </div>
              <span class="status-badge {status_class}">{html.escape(label_for(item.status))}</span>
            </div>
            <div class="result-meta-grid">
              <div class="result-meta">
                <span>Scadenza</span>
                <strong>{html.escape(format_date(item.deadline))}</strong>
              </div>
              <div class="result-meta">
                <span>Tipologia</span>
                <strong>{html.escape(label_for(item.category))}</strong>
              </div>
              <div class="result-meta">
                <span>Pertinenza</span>
                <strong>{html.escape(label_for(item.psychology_relevance))}</strong>
              </div>
            </div>
            <div class="result-summary-label">In breve</div>
            <div class="result-summary">
              {html.escape(item.summary or "Riepilogo non disponibile.")}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if item.areas:
            chips = "".join(
                f'<span class="area-chip">{html.escape(label_for(area))}</span>'
                for area in item.areas[:4]
            )
            st.markdown(chips, unsafe_allow_html=True)

        actions = st.columns([1.2, 1.6, 4])
        if actions[0].button(
            "Vedi dettagli",
            key=f"detail_{item.id}",
            type="primary",
            use_container_width=True,
        ):
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
    _initialize_filter_state()

    path = str(snapshot_path().resolve())
    catalog: StaticCatalog | None = None
    try:
        catalog = StaticCatalog(Path(path))
        facets = catalog.search(
            **_context_filter_state(),
            limit=1,
            offset=0,
        ).facets
    except SnapshotValidationError as exc:
        if catalog is not None:
            catalog.close()
        logger.warning("Public snapshot unavailable: %s", exc)
        st.title("Bandi Psicologia")
        st.error(
            "L'archivio pubblico non è ancora disponibile. Nel repository apri "
            "Actions → Aggiorna archivio bandi → Run workflow, quindi attendi il redeploy."
        )
        st.stop()
    except Exception:
        if catalog is not None:
            catalog.close()
        logger.exception("Unable to open the public snapshot")
        st.title("Bandi Psicologia")
        st.error("L'archivio pubblico non è leggibile in questo momento.")
        st.stop()

    assert catalog is not None

    generated_at = datetime.fromisoformat(catalog.snapshot.generated_at)
    _render_page_header(facets, generated_at, catalog.snapshot.source_count)

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
    if filters["status_filter"]:
        view_label = f"Stato: {label_for(filters['status_filter'])}"
    elif filters["include_review"]:
        view_label = "Aperti + da verificare"
    else:
        view_label = "Solo aperti e in scadenza"
    st.markdown(
        f"""
        <div class="summary-strip">
          <div class="summary-item">
            <div class="summary-label">Risultati</div>
            <div class="summary-value">{response.total} {result_label}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">Fonti pubblicate</div>
            <div class="summary-value">{catalog.snapshot.source_count}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">Vista attiva</div>
            <div class="summary-value">{html.escape(view_label)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("Bandi trovati")
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
