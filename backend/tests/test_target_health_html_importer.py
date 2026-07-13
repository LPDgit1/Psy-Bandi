from app.importers.target_health_html import (
    collect_target_health_detail_urls,
    parse_target_health_detail,
    parse_target_health_records,
)
from app.models import Source


def _source() -> Source:
    return Source(
        id="src_target",
        name="ASL Test - Concorsi",
        source_type="target-health-html",
        base_url="https://example.test/concorsi",
        organization="ASL Test",
        region="Puglia",
    )


def test_parse_target_health_records_extracts_psychology_card() -> None:
    html = """
    <article>
      <h2>Avviso pubblico per dirigente psicologo</h2>
      <p>Data pubblicazione: 01/06/2026. Data scadenza: 30/09/2026.</p>
      <a href="/avviso-psicologo">Scheda</a>
    </article>
    <article>
      <h2>Avviso pubblico per dirigente medico</h2>
      <a href="/avviso-medico">Scheda</a>
    </article>
    """

    records = parse_target_health_records(_source(), html, "https://example.test/concorsi")

    assert len(records) == 1
    assert records[0].title == "Avviso pubblico per dirigente psicologo"
    assert records[0].official_url == "https://example.test/avviso-psicologo"
    assert records[0].deadline is not None
    assert records[0].deadline.month == 9


def test_parse_target_health_records_ignores_approval_and_final_ranking_page() -> None:
    html = """
    <article>
      <h2>Avviso pubblico per n. 3 dirigenti psicologi</h2>
      <p>Approvazione atti della Commissione Esaminatrice e graduatoria finale
      di merito. Riferimento al DM 30 dicembre 2026.</p>
      <a href="/avviso-psicologo">Scheda</a>
    </article>
    """

    records = parse_target_health_records(_source(), html, _source().base_url)

    assert records == []


def test_collect_target_health_detail_urls_uses_parent_context() -> None:
    html = """
    <div class="card">
      <h3>Concorso pubblico per psicologo consultoriale</h3>
      <a href="/detail">Leggi di piu</a>
    </div>
    <div class="card">
      <h3>Concorso pubblico per infermiere</h3>
      <a href="/other">Leggi di piu</a>
    </div>
    """

    urls = collect_target_health_detail_urls(html, "https://example.test/list")

    assert urls == ["https://example.test/detail"]


def test_parse_target_health_detail_extracts_attachments() -> None:
    html = """
    <main>
      <h1>Avviso pubblico per incarico libero professionale psicologo</h1>
      <p>Scadenza domande: 15/10/2026.</p>
      <a href="/docs/bando.pdf">Bando</a>
      <a href="/docs/graduatoria.pdf">Graduatoria</a>
    </main>
    """

    record = parse_target_health_detail(
        _source(),
        None,
        html,
        "https://example.test/detail",
    )

    assert record is not None
    assert record.deadline is not None
    assert len(record.attachments) == 1
    assert record.attachments[0]["url"] == "https://example.test/docs/bando.pdf"


def test_parse_target_health_detail_uses_ares_deadline_label() -> None:
    html = """
    <main>
      <h1>Indizione procedura comparativa profilo Psicologo</h1>
      <p>Data di pubblicazione 15.06.2026</p>
      <p>Data e ora di scadenza 30.06.2026 23:59:59</p>
      <section>
        Oggetto: incarico di collaborazione esterna nel profilo di Psicologo
        con specializzazione in Psicoterapia.
      </section>
      <a href="/docs/bando.pdf">bando</a>
    </main>
    """

    record = parse_target_health_detail(_source(), None, html, "https://example.test/ap/1")

    assert record is not None
    assert record.deadline is not None
    assert record.deadline.date().isoformat() == "2026-06-30"


def test_parse_target_health_detail_does_not_use_graduation_deadline() -> None:
    html = """
    <main>
      <h1>
        Concorso pubblico per Ricercatore Sanitario Neuropsicologo -
        Scadenza graduatoria 26/06/2027
      </h1>
      <p>Data: 5 Luglio 2024. Graduatorie vigenti.</p>
    </main>
    """

    record = parse_target_health_detail(_source(), None, html, "https://example.test/ap/3")

    assert record is not None
    assert record.deadline is None


def test_parse_target_health_detail_keeps_stabilization_with_followup_attachments() -> None:
    html = """
    <main>
      <h1>Procedura di stabilizzazione profilo di Psicologo ASL Gallura</h1>
      <p>Data di pubblicazione 09.10.2025</p>
      <p>Data e ora di scadenza 08.11.2025 23:59:59</p>
      <section>
        Procedura di stabilizzazione per il profilo di Psicologo.
        Documenti successivi: ammissione/esclusione candidati.
      </section>
      <a href="/docs/avviso.pdf">All: Avviso</a>
    </main>
    """

    record = parse_target_health_detail(_source(), None, html, "https://example.test/ap/2")

    assert record is not None
    assert record.deadline is not None
    assert record.deadline.date().isoformat() == "2025-11-08"


def test_parse_target_health_records_ignores_followup_notices() -> None:
    html = """
    <article>
      <h2>Convocazione Psicologi - preselezione</h2>
      <p>Esito della preselezione per profilo psicologo psicoterapeuta.</p>
      <a href="/convocazione">Scheda</a>
    </article>
    """

    records = parse_target_health_records(_source(), html, "https://example.test/concorsi")

    assert records == []


def test_parse_target_health_records_extracts_relevant_search_result_links() -> None:
    html = """
    <main>
      <a href="/bando-psicoterapia">
        Stabilizzazione Dirigente Psicologo disciplina Psicoterapia - scadenza 28/05/2026
      </a>
      <a href="/faq-concorsi">FAQ Concorsi</a>
    </main>
    """

    records = parse_target_health_records(_source(), html, "https://example.test/?s=psicolog")

    assert len(records) == 1
    assert records[0].title.startswith("Stabilizzazione Dirigente Psicologo")
    assert records[0].official_url == "https://example.test/bando-psicoterapia"


def test_parse_target_health_records_ignores_search_result_page_urls() -> None:
    html = """
    <main>
      <a href="https://example.test/?s=lm-51">
        Risultati della ricerca per LM-51 - psicologo
      </a>
    </main>
    """

    records = parse_target_health_records(_source(), html, "https://example.test/?s=lm-51")

    assert records == []


def test_parse_target_health_records_ignores_followup_titles_with_strong_terms() -> None:
    html = """
    <article>
      <h2>
        AMMISSIONE CANDIDATI E NOMINA COMMISSIONE - Avviso Pubblico
        per Psicologo Specialista in Psicoterapia
      </h2>
      <p>Avviso pubblico relativo al profilo di Psicologo Specialista.</p>
      <a href="/ammissione-candidati">Scheda</a>
    </article>
    """

    records = parse_target_health_records(_source(), html, "https://example.test/list")

    assert records == []


def test_parse_target_health_detail_ignores_followup_title() -> None:
    html = """
    <main>
      <h1>
        Approvazione atti della commissione e conferimento incarico -
        Avviso pubblico per psicologo
      </h1>
      <p>Data scadenza: 16-10-2025.</p>
    </main>
    """

    record = parse_target_health_detail(_source(), None, html, "https://example.test/detail")

    assert record is None


def test_parse_target_health_detail_strips_nul_bytes() -> None:
    html = """
    <main>
      <h1>Avviso pubblico per psicologo</h1>
      <p>Testo con byte nullo \x00 e scadenza 15/10/2026.</p>
    </main>
    """

    record = parse_target_health_detail(_source(), None, html, "https://example.test/detail")

    assert record is not None
    assert "\x00" not in record.description
