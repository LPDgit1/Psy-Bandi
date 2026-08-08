from datetime import datetime

from app.importers.gazzetta_concorsi import collect_issue_urls, parse_issue_records


INDEX_HTML = """
<html><body>
  <a href="/gazzetta/concorsi/caricaDettaglio?dataPubblicazioneGazzetta=2026-07-31&amp;numeroGazzetta=58">58</a>
  <a href="/gazzetta/concorsi/caricaDettaglio?dataPubblicazioneGazzetta=2026-08-04&amp;numeroGazzetta=59">59</a>
</body></html>
"""

ISSUE_HTML = """
<html><body>
  <span class="emettitore">AZIENDA TERRITORIALE SANITARIA DI BERGAMO</span>
  <span class="risultato">
    <a href="/atto/concorsi/caricaDettaglioAtto/originario?atto.dataPubblicazioneGazzetta=2026-08-04&amp;atto.codiceRedazionale=26E04234">
      CONCORSO (scadenza 3 settembre 2026)
    </a>
    <a href="/atto/concorsi/caricaDettaglioAtto/originario?atto.dataPubblicazioneGazzetta=2026-08-04&amp;atto.codiceRedazionale=26E04234">
      Concorso pubblico per un posto di dirigente psicologo, disciplina psicoterapia
    </a>
  </span>
  <span class="emettitore">ESTAR TOSCANA</span>
  <span class="risultato">
    <a href="/atto/concorsi/caricaDettaglioAtto/originario?atto.dataPubblicazioneGazzetta=2026-08-04&amp;atto.codiceRedazionale=26E04202">
      CONCORSO (scadenza 3 settembre 2026)
    </a>
    <a href="/atto/concorsi/caricaDettaglioAtto/originario?atto.dataPubblicazioneGazzetta=2026-08-04&amp;atto.codiceRedazionale=26E04202">
      Concorso pubblico per dirigente psicologo per l'AUSL Toscana Nord Ovest
    </a>
  </span>
  <span class="emettitore">COMUNE DI ESEMPIO</span>
  <span class="risultato">
    <a href="/atto/concorsi/caricaDettaglioAtto/originario?atto.dataPubblicazioneGazzetta=2026-08-04&amp;atto.codiceRedazionale=26E09999">
      CONCORSO (scadenza 10 settembre 2026)
    </a>
    <a href="/atto/concorsi/caricaDettaglioAtto/originario?atto.dataPubblicazioneGazzetta=2026-08-04&amp;atto.codiceRedazionale=26E09999">
      Concorso pubblico per istruttore amministrativo
    </a>
  </span>
</body></html>
"""


def test_collect_issue_urls_reads_official_index() -> None:
    urls = collect_issue_urls(INDEX_HTML)

    assert len(urls) == 2
    assert urls[-1].endswith("numeroGazzetta=59")


def test_parse_issue_records_extracts_relevant_acts_and_counts_all_rows() -> None:
    issue_url = (
        "https://www.gazzettaufficiale.it/gazzetta/concorsi/caricaDettaglio"
        "?dataPubblicazioneGazzetta=2026-08-04&numeroGazzetta=59"
    )

    records, act_count = parse_issue_records(ISSUE_HTML, issue_url)

    assert act_count == 3
    assert [record.external_id for record in records] == [
        "gazzetta-concorsi:26E04234",
        "gazzetta-concorsi:26E04202",
    ]
    assert records[0].organization == "AZIENDA TERRITORIALE SANITARIA DI BERGAMO"
    assert records[0].deadline == datetime.fromisoformat("2026-09-03T23:59:00+02:00")
    assert records[0].published_at == datetime.fromisoformat("2026-08-04T23:59:00+02:00")
    assert "atto.codiceRedazionale=26E04234" in records[0].official_url


def test_parse_issue_records_detects_structural_failure() -> None:
    assert parse_issue_records("<html><body>pagina vuota</body></html>", "https://example.test") == (
        [],
        0,
    )
