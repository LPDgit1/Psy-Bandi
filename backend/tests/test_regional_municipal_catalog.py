from app.models import Source
from app.importers.regional_municipal import (
    collect_regional_municipal_detail_links,
    parse_regional_municipal_records,
)
from app.regional_municipal_catalog import (
    MUNICIPAL_CAPITAL_SOURCE_DEFINITIONS,
    REGIONAL_MUNICIPAL_SOURCE_DEFINITIONS,
    REGIONAL_MUNICIPAL_SOURCE_NAMES,
    REGIONAL_SOURCE_DEFINITIONS,
)
from app.source_catalog import VERIFIED_SOURCE_CATALOG
from app.scripts.audit_sources import adapter_family


def test_regional_municipal_catalog_is_unique_and_https() -> None:
    assert len(REGIONAL_SOURCE_DEFINITIONS) == 9
    assert len(MUNICIPAL_CAPITAL_SOURCE_DEFINITIONS) == 46
    assert len(REGIONAL_MUNICIPAL_SOURCE_NAMES) == 55
    assert len(
        {source["name"] for source in REGIONAL_MUNICIPAL_SOURCE_DEFINITIONS}
    ) == 55
    assert all(
        source["base_url"].startswith("https://")
        for source in REGIONAL_MUNICIPAL_SOURCE_DEFINITIONS
    )


def test_regional_municipal_sources_use_the_dedicated_adapter() -> None:
    existing_names = {source["name"] for source in VERIFIED_SOURCE_CATALOG}
    assert not REGIONAL_MUNICIPAL_SOURCE_NAMES & (
        existing_names - REGIONAL_MUNICIPAL_SOURCE_NAMES
    )
    assert all(
        adapter_family(Source(**source, status="catalogued")) == "dedicated"
        for source in REGIONAL_MUNICIPAL_SOURCE_DEFINITIONS
    )


def test_regional_municipal_adapter_discovers_and_parses_a_recruitment_card() -> None:
    source = Source(
        id="src_regional_test",
        **REGIONAL_SOURCE_DEFINITIONS[0],
        status="catalogued",
    )
    html = (
        "<article><h2>Concorso psicologo dirigente</h2>"
        "<p>Avviso pubblico per psicologo con scadenza 30/09/2026.</p>"
        "<a href='/concorsi/psicologo-2026'>Dettagli</a></article>"
    )

    detail_links = collect_regional_municipal_detail_links(html, source.base_url)
    records = parse_regional_municipal_records(source, html, source.base_url)

    assert detail_links == [
        "https://www.regione.calabria.it/concorsi/psicologo-2026"
    ]
    assert records and records[0].official_url == detail_links[0]
