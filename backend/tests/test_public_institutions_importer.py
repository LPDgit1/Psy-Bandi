from app.importers.public_institutions import (
    collect_public_detail_links,
    parse_public_institution_records,
)
from app.models import Source


def test_public_institution_adapter_extracts_psychology_detail() -> None:
    source = Source(
        id="src_public",
        name="Ministero della Salute - Bandi di concorso",
        source_type="public-institution-html",
        base_url="https://example.gov.it/concorsi",
        organization="Ministero della Salute",
    )
    html = """
    <main>
      <div class="opening">
        <h2>Avviso pubblico per psicologo dirigente</h2>
        <p>Selezione pubblica. Scadenza domande 30/09/2026.</p>
        <a href="/concorsi/psicologo">Scheda ufficiale</a>
      </div>
    </main>
    """

    records = parse_public_institution_records(source, html, source.base_url + "/scheda")

    assert len(records) == 1
    assert "psicologo" in records[0].title.casefold()
    assert records[0].deadline is not None
    assert records[0].official_url == "https://example.gov.it/concorsi/psicologo"


def test_public_detail_link_adapter_prioritizes_official_opportunity_pages() -> None:
    html = """
    <a href="/privacy">Privacy</a>
    <a href="/concorsi/psicologo">Avviso psicologo</a>
    <a href="/files/bando.pdf">Bando PDF</a>
    <a href="/lavora-con-noi">Lavora con noi</a>
    """

    links = collect_public_detail_links(html, "https://example.gov.it/", limit=2)

    assert links[0] == "https://example.gov.it/concorsi/psicologo"
    assert "privacy" not in " ".join(links)
    assert not any(link.endswith(".pdf") for link in links)
