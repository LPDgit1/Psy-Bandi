from app.importers.usl_umbria1 import parse_usl_umbria1_detail, parse_usl_umbria1_listing


def test_parse_usl_umbria1_listing_extracts_cards_and_deadline() -> None:
    html = """
    <div class="scheda-sito">
      <a href="/bando_concorso/dirigente-psicologo/">
        AVVISO PUBBLICO PER DIRIGENTE PSICOLOGO
      </a>
      DATA PUBBLICAZIONE: 01/06/2026 DATA SCADENZA: 30/09/2026
    </div>
    """

    records = parse_usl_umbria1_listing(html, "https://www.uslumbria1.it/cat/")

    assert len(records) == 1
    assert records[0].official_url == "https://www.uslumbria1.it/bando_concorso/dirigente-psicologo/"
    assert records[0].deadline is not None
    assert records[0].deadline.month == 9


def test_parse_usl_umbria1_detail_extracts_relevant_attachments() -> None:
    listing_record = parse_usl_umbria1_listing(
        """
        <div class="scheda-sito">
          <a href="/bando_concorso/dirigente-psicologo/">Avviso psicologo</a>
          DATA SCADENZA: 30/09/2026
        </div>
        """,
        "https://www.uslumbria1.it/cat/",
    )[0]
    html = """
    <main>
      <h1>Avviso psicologo</h1>
      <p>Scadenza domande: 30/09/2026.</p>
      <a href="/wp-content/uploads/bando-psicologo.pdf">Download</a>
      <a href="/wp-content/uploads/graduatoria.pdf">Graduatoria</a>
    </main>
    """

    record = parse_usl_umbria1_detail(
        listing_record,
        html,
        "https://www.uslumbria1.it/bando_concorso/dirigente-psicologo/",
    )

    assert record.deadline is not None
    assert len(record.attachments) == 1
    assert record.attachments[0]["url"] == "https://www.uslumbria1.it/wp-content/uploads/bando-psicologo.pdf"
