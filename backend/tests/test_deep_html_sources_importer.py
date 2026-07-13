from app.importers.deep_html_sources import collect_deep_links


def test_collect_deep_links_prioritizes_relevant_details_and_pagination() -> None:
    html = """
    <a href="/privacy">Privacy</a>
    <a href="/servizi/centro-ascolto">Centro ascolto</a>
    <a href="/competition/avviso-psicologo">Avviso psicologo</a>
    <a href="/amministrazione-trasparente/bandi-di-concorso/">Bandi di concorso</a>
    <a href="/concorsi/?page=2" rel="next">Pagina successiva</a>
    <a href="https://other.test/concorsi/psicologo">Altro sito</a>
    """

    links = collect_deep_links(html, "https://example.test/concorsi/", limit=4)

    assert links == [
        "https://example.test/competition/avviso-psicologo",
        "https://example.test/amministrazione-trasparente/bandi-di-concorso/",
        "https://example.test/concorsi/?page=2",
    ]


def test_collect_deep_links_skips_binary_and_social_links() -> None:
    html = """
    <a href="/bando-psicologo.pdf">Bando psicologo PDF</a>
    <a href="mailto:test@example.test">Email</a>
    <a href="/concorsi/avviso-psicologo">Scheda avviso psicologo</a>
    <a href="/facebook/concorsi">Facebook</a>
    """

    links = collect_deep_links(html, "https://example.test/", limit=10)

    assert links == ["https://example.test/concorsi/avviso-psicologo"]


def test_collect_deep_links_respects_zero_limit() -> None:
    html = '<a href="/competition/avviso-psicologo">Avviso psicologo</a>'

    assert collect_deep_links(html, "https://example.test/", limit=0) == []


def test_collect_deep_links_includes_broader_psychology_terms() -> None:
    html = """
    <a href="/avvisi/riabilitazione-cognitiva">Avviso riabilitazione cognitiva</a>
    <a href="/bandi/interventi-psicoeducativi">Bando interventi psicoeducativi</a>
    <a href="/servizi/salute-mentale">Servizio salute mentale</a>
    """

    links = collect_deep_links(html, "https://example.test/", limit=5)

    assert "https://example.test/avvisi/riabilitazione-cognitiva" in links
    assert "https://example.test/bandi/interventi-psicoeducativi" in links
