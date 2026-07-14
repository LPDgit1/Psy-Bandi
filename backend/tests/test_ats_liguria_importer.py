from app.importers.ats_liguria import (
    _verified_active_detail,
    collect_ats_liguria_list_urls,
    parse_ats_liguria_detail_urls,
    parse_ats_liguria_record,
)


def test_collect_ats_liguria_list_urls_finds_publiccompetition_sections() -> None:
    html = """
    <a href="/bandi/concorsi.html">Concorsi</a>
    <a href="/bandi/concorsi/dirigenza/publiccompetitions/">Dirigenza</a>
    <a href="https://external.test/publiccompetitions/">Esterno</a>
    """

    urls = collect_ats_liguria_list_urls(html, "https://www.atsliguria.it/bandi/")

    assert urls == ["https://www.atsliguria.it/bandi/concorsi/dirigenza/publiccompetitions/"]


def test_parse_ats_liguria_detail_urls_extracts_competition_links() -> None:
    html = """
    <a href="/bandi/publiccompetition/123:avviso-psicologo.html">Avviso psicologo</a>
    <a href="/bandi/publiccompetitions/">Lista</a>
    """

    urls = parse_ats_liguria_detail_urls(html, "https://www.atsliguria.it/bandi/lista/")

    assert urls == ["https://www.atsliguria.it/bandi/publiccompetition/123:avviso-psicologo.html"]


def test_parse_ats_liguria_record_filters_and_extracts_attachment() -> None:
    html = """
    <main>
      <h1>Avviso pubblico per dirigente psicologo</h1>
      <p>Scadenza domande: 30/09/2026.</p>
      <a href="/components/com_publiccompetitions/includes/download.php?id=1:bando.pdf">
        pdf (120 Kb)
      </a>
    </main>
    """

    record = parse_ats_liguria_record(
        html,
        "https://www.atsliguria.it/bandi/publiccompetition/123:avviso-psicologo.html",
    )

    assert record is not None
    assert record.deadline is not None
    assert len(record.attachments) == 1


def test_parse_ats_liguria_record_extracts_textual_closing_date() -> None:
    html = """
    <main>
      <h1>Concorso pubblico per dirigente psicologo</h1>
      <p>Data pubblicazione: 13 Marzo 2024</p>
      <p>Data chiusura: 11 Aprile 2024</p>
    </main>
    """

    record = parse_ats_liguria_record(
        html,
        "https://www.asl3.liguria.it/bandi/concorsi-aperti/publiccompetition/psicologo.html",
    )

    assert record is not None
    assert record.deadline is not None
    assert record.deadline.date().isoformat() == "2024-04-11"


def test_parse_ats_liguria_record_ignores_non_psychology_detail() -> None:
    html = "<main><h1>Avviso pubblico per dirigente medico</h1></main>"

    assert parse_ats_liguria_record(html, "https://example.test/detail") is None


def test_parse_ats_liguria_record_ignores_related_psychology_page_text() -> None:
    html = """
    <main>
      <h1>Concorso pubblico per dirigente medico in cardiologia</h1>
      <p>Dettaglio del concorso di cardiologia.</p>
      <aside>Altri concorsi: dirigente psicologo, disciplina psicoterapia.</aside>
    </main>
    """

    assert parse_ats_liguria_record(html, "https://example.test/cardiologia") is None


def test_active_liguria_listing_can_publish_record_without_deadline() -> None:
    assert _verified_active_detail(
        "https://www.asl3.liguria.it/bandi/concorsi-aperti/publiccompetition/psicologo.html"
    )
    assert not _verified_active_detail(
        "https://www.asl3.liguria.it/bandi/archivio/publiccompetition/psicologo.html"
    )
