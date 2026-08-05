from app.importers.ministerial_sources import (
    collect_ministerial_detail_links,
    parse_ministerial_records,
)
from app.models import Source


def _source() -> Source:
    return Source(
        id="src_ministerial",
        name="Ministero dell'Interno - Bandi di concorso",
        source_type="ministerial-html-hub",
        base_url="https://www.interno.gov.it/concorsi",
        organization="Ministero dell'Interno",
        region=None,
    )


def test_parse_ministerial_records_extracts_psychology_opportunity() -> None:
    html = """
    <article>
      <h2>Concorso pubblico per commissari tecnici psicologi</h2>
      <p>Domande entro il 30/09/2026. Profilo psicologo.</p>
      <a href="/concorsi/psicologi">Scheda ufficiale</a>
    </article>
    <article>
      <h2>Concorso pubblico per funzionari amministrativi</h2>
      <a href="/concorsi/amministrativi">Scheda</a>
    </article>
    """

    records = parse_ministerial_records(_source(), html, _source().base_url)

    assert len(records) == 1
    assert records[0].title == "Concorso pubblico per commissari tecnici psicologi"
    assert records[0].official_url == "https://www.interno.gov.it/concorsi/psicologi"
    assert records[0].deadline is not None


def test_collect_ministerial_detail_links_prioritizes_official_concourse_links() -> None:
    html = """
    <nav><a href="/privacy">Privacy</a></nav>
    <main>
      <a href="/concorsi/psicologo">Concorso psicologi</a>
      <a href="/servizi">Servizi</a>
      <a href="/concorsi/amministrativi">Concorso amministrativi</a>
    </main>
    """

    links = collect_ministerial_detail_links(html, _source().base_url)

    assert links[0] == "https://www.interno.gov.it/concorsi/psicologo"
    assert "https://www.interno.gov.it/privacy" not in links
