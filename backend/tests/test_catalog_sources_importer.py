from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.importers import catalog_sources
from app.importers.catalog_sources import (
    CATALOG_SOURCE_TYPES,
    _entity_type,
    _source_search_urls,
    align_existing_catalog_record,
    collect_catalog_links,
    parse_catalog_records,
)
from app.models import Base, Opportunity, Source


def test_parse_catalog_records_extracts_html_psychology_opportunity() -> None:
    source = Source(
        id="src_test",
        name="Comune Test - Bandi di concorso",
        source_type="html-list",
        base_url="https://example.test/bandi",
        organization="Comune Test",
        region="Veneto",
    )
    html = """
    <html>
      <body>
        <article>
          <h2>Avviso pubblico per incarico di psicologo scolastico</h2>
          <p>Procedura comparativa per psicologo. Scadenza domande 20/09/2026.</p>
          <a href="/bandi/psicologo-scolastico">Scheda ufficiale</a>
        </article>
        <article>
          <h2>Concorso per istruttore amministrativo</h2>
          <p>Procedura non pertinente.</p>
        </article>
      </body>
    </html>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert len(records) == 1
    assert records[0].title == "Avviso pubblico per incarico di psicologo scolastico"
    assert records[0].deadline is not None
    assert records[0].official_url == "https://example.test/bandi/psicologo-scolastico"


def test_parse_catalog_records_extracts_broader_psychology_opportunity() -> None:
    source = Source(
        id="src_test",
        name="ASL Test - Bandi",
        source_type="hospital-html-hub",
        base_url="https://example.test/concorsi",
        organization="ASL Test",
        region="Lazio",
    )
    html = """
    <article>
      <h2>Avviso pubblico per riabilitazione cognitiva</h2>
      <p>Procedura comparativa per test neuropsicologici. Scadenza 20/09/2026.</p>
      <a href="/concorsi/riabilitazione-cognitiva">Scheda ufficiale</a>
    </article>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert len(records) == 1
    assert records[0].title == "Avviso pubblico per riabilitazione cognitiva"


def test_parse_catalog_records_accepts_explicit_role_without_generic_bando_word() -> None:
    source = Source(
        id="src_role",
        name="ASL Test - Concorsi",
        source_type="html-list",
        base_url="https://example.test/concorsi",
        organization="ASL Test",
        region="Lazio",
    )
    html = """
    <tr>
      <td><a href="/concorsi/dirigente-psicologo">Dirigente Psicologo</a></td>
      <td>Scadenza 30/09/2026</td>
    </tr>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert len(records) == 1


def test_catalog_record_identity_survives_deadline_extension() -> None:
    source = Source(
        id="src_extension",
        name="ASL Test - Concorsi",
        source_type="html-list",
        base_url="https://example.test/concorsi",
        organization="ASL Test",
        region="Lazio",
    )
    first = parse_catalog_records(
        source,
        """<article><h2>Avviso per psicologo</h2><p>Scadenza 20/09/2026</p>
        <a href="/item/1">Scheda</a></article>""",
        source.base_url,
    )[0]
    extended = parse_catalog_records(
        source,
        """<article><h2>Avviso per psicologo</h2><p>Scadenza 30/09/2026</p>
        <a href="/item/1">Scheda</a></article>""",
        source.base_url,
    )[0]

    assert first.external_id == extended.external_id


def test_catalog_record_identity_uses_detail_url_across_title_variants() -> None:
    source = Source(
        id="src_detail",
        name="Ente Test - Bandi",
        source_type="html-list",
        base_url="https://example.test/bandi",
    )
    listing = parse_catalog_records(
        source,
        """<article><h2>Ricerca di Psicologo per...</h2>
        <a href="/item/1">Scheda</a></article>""",
        source.base_url,
    )[0]
    detail = parse_catalog_records(
        source,
        """<article><h1>Ricerca di Psicologo per attivita riabilitativa</h1>
        <p>Scadenza 30/09/2026.</p></article>""",
        "https://example.test/item/1",
    )[0]

    assert listing.external_id == detail.external_id


def test_align_existing_catalog_record_hides_same_url_duplicate() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        source = Source(
            id="src_duplicates",
            name="Ente Test - Bandi",
            source_type="html-list",
            base_url="https://example.test/bandi",
        )
        first = Opportunity(
            source=source,
            external_id="legacy-list",
            title="Ricerca di Psicologo per...",
            normalized_title="ricerca di psicologo per",
            organization="Ente Test",
            status="review",
            official_url="https://example.test/item/1",
            search_text="ricerca psicologo",
            editorial_status="approved",
        )
        second = Opportunity(
            source=source,
            external_id="legacy-detail",
            title="Ricerca di Psicologo per attivita riabilitativa",
            normalized_title="ricerca di psicologo per attivita riabilitativa",
            organization="Ente Test",
            status="open",
            official_url="https://example.test/item/1",
            search_text="ricerca psicologo attivita riabilitativa",
            editorial_status="approved",
        )
        db.add_all([first, second])
        db.commit()
        record = parse_catalog_records(
            source,
            """<article><h1>Ricerca di Psicologo per attivita riabilitativa</h1>
            <p>Scadenza 30/09/2026.</p></article>""",
            "https://example.test/item/1",
        )[0]

        align_existing_catalog_record(db, source, record)

        assert second.external_id == record.external_id
        assert first.editorial_status == "hidden"


def test_catalog_source_types_cover_hospital_and_private_social_jobs() -> None:
    assert "hospital-html-hub" in CATALOG_SOURCE_TYPES
    assert "private-social-jobs" in CATALOG_SOURCE_TYPES


def test_source_search_urls_adds_wordpress_search_terms_only_for_wordpress_hubs() -> None:
    wordpress = Source(
        source_type="wordpress-html-hub",
        base_url="https://example.test/lavora-con-noi/",
    )
    generic = Source(
        source_type="html-hub",
        base_url="https://example.test/lavora-con-noi/",
    )

    wordpress_urls = _source_search_urls(wordpress)

    assert wordpress_urls[0] == wordpress.base_url
    assert any("?s=psicolog" in url for url in wordpress_urls)
    assert _source_search_urls(generic) == [generic.base_url]


def test_parse_catalog_records_uses_labeled_deadline_before_other_dates() -> None:
    source = Source(
        id="src_test",
        name="ASM Test - Bandi",
        source_type="html-list",
        base_url="https://example.test/bandi",
        organization="ASM Test",
        region="Basilicata",
    )
    html = """
    <article>
      <h2>Avviso pubblico per psicologo del lavoro</h2>
      <p>
        Data del documento: 16-10-2025 00:00.
        Data scadenza: 20-11-2025 00:00.
      </p>
      <a href="/concorsi-avvisi/psicologo-lavoro">Scheda</a>
    </article>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert len(records) == 1
    assert records[0].deadline is not None
    assert records[0].deadline.date().isoformat() == "2025-11-20"


def test_parse_catalog_records_does_not_use_graduation_deadline() -> None:
    source = Source(
        id="src_estar",
        name="ESTAR Test - Ricerca",
        source_type="html-list",
        base_url="https://example.test/estar",
        organization="ESTAR Test",
        region="Toscana",
    )
    html = """
    <article>
      <h2>
        Concorso pubblico per Ricercatore Sanitario Neuropsicologo -
        Scadenza graduatoria 26/06/2027
      </h2>
      <p>Data: 5 Luglio 2024. Graduatorie vigenti.</p>
      <a href="/graduatoria-neuropsicologo">Scheda</a>
    </article>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert len(records) == 1
    assert records[0].deadline is None


def test_parse_catalog_records_ignores_search_result_page_as_record() -> None:
    source = Source(
        id="src_search",
        name="ASM Test - Ricerca",
        source_type="html-list",
        base_url="https://example.test/?s=lm-51",
        organization="ASM Test",
        region="Basilicata",
    )
    html = """
    <main>
      <h1>Risultati della ricerca per LM-51</h1>
      <p>Risultati relativi a psicologo, concorsi e avvisi.</p>
    </main>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert records == []


def test_parse_catalog_records_ignores_listing_page_mixed_context() -> None:
    source = Source(
        id="src_listing",
        name="ASL Test - Bandi di concorso",
        source_type="html-list",
        base_url="https://example.test/BandiConcorsi.jsp",
        organization="ASL Test",
        region="Abruzzo",
    )
    html = """
    <html>
      <head><title>Bandi di concorso - Azienda USL Test</title></head>
      <body>
        <main>
          <h1>Bandi di concorso</h1>
          <p>Informazioni reclutamento Psicologo di Base: tel. 000.</p>
          <h2>Avviso pubblico per tecnico sanitario</h2>
          <p>Scadenza domande: 20/07/2026.</p>
        </main>
      </body>
    </html>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert records == []


def test_parse_catalog_records_ignores_service_detail_page_without_opportunity_title() -> None:
    source = Source(
        id="src_service",
        name="AO Test - Concorsi",
        source_type="hospital-html-hub",
        base_url="https://example.test/concorsi/",
        organization="AO Test",
        region="Umbria",
    )
    html = """
    <html>
      <head><title>Centro di ascolto psicologico</title></head>
      <body>
        <main>
          <h1>Centro di ascolto psicologico</h1>
          <p>In tutti i casi in cui si ravvisi un disagio psicologico.</p>
          <p>La pagina e' collegata alla sezione concorsi del sito.</p>
        </main>
      </body>
    </html>
    """

    records = parse_catalog_records(
        source,
        html,
        "https://example.test/servizi/centro-di-ascolto-psicologico/",
    )

    assert records == []


def test_parse_catalog_records_ignores_awarded_consultant_profile() -> None:
    source = Source(
        id="src_consultants",
        name="Comune Test - Amministrazione Trasparente",
        source_type="external-transparency",
        base_url="https://example.test/trasparenza",
        organization="Comune Test",
        region="Puglia",
    )
    html = """
    <article>
      <h2>Dott. Mario Rossi</h2>
      <p>Scheda documento. Conferimento incarico al Dott. Mario Rossi per
      consulenza psicologica relativa a un concorso. Data fine 31/12/2027.</p>
      <a href="/consulenti/mario-rossi">Scheda</a>
    </article>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert records == []


def test_parse_catalog_records_does_not_infer_deadline_from_unlabeled_law_date() -> None:
    source = Source(
        id="src_dates",
        name="ASL Test - Avvisi",
        source_type="html-list",
        base_url="https://example.test/avvisi",
        organization="ASL Test",
        region="Basilicata",
    )
    html = """
    <article>
      <h2>Avviso pubblico per dirigente psicologo</h2>
      <p>Progetto disciplinato dal DM 30 dicembre 2026.</p>
      <a href="/avvisi/psicologo">Scheda</a>
    </article>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert len(records) == 1
    assert records[0].deadline is None


def test_parse_catalog_records_ignores_undated_records_from_search_pages() -> None:
    source = Source(
        id="src_search",
        name="ASM Test - Ricerca",
        source_type="html-list",
        base_url="https://example.test/?s=psicolog",
        organization="ASM Test",
        region="Basilicata",
    )
    html = """
    <article>
      <h2>Avviso pubblico di selezione. Dirigente Psicologo del lavoro</h2>
      <p>Procedura comparativa per psicologo.</p>
      <a href="/concorsi-avvisi/psicologo-lavoro">Scheda</a>
    </article>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert records == []


def test_parse_catalog_records_ignores_followup_title() -> None:
    source = Source(
        id="src_followup",
        name="ASM Test - Bandi",
        source_type="html-list",
        base_url="https://example.test/bandi",
        organization="ASM Test",
        region="Basilicata",
    )
    html = """
    <article>
      <h2>
        AMMISSIONE CANDIDATI E NOMINA COMMISSIONE - Avviso Pubblico
        per Psicologo Specialista in Psicoterapia
      </h2>
      <p>Procedura comparativa per psicologo con scadenza 20/11/2025.</p>
      <a href="/ammissione-candidati">Scheda</a>
    </article>
    """

    records = parse_catalog_records(source, html, source.base_url)

    assert records == []


def test_parse_catalog_records_extracts_xml_atto() -> None:
    source = Source(
        id="src_xml",
        name="ASL Test - XML concorsi",
        source_type="xml-index",
        base_url="https://example.test/concorsi.xml",
        organization="ASL Test",
        region="Piemonte",
    )
    xml = """
    <atti>
      <atto>
        <oggetto>Avviso pubblico per dirigente psicologo</oggetto>
        <nota>Selezione pubblica. Scadenza domande: 30/09/2026</nota>
        <allegati><allegato><web>/atti/dirigente-psicologo.pdf</web></allegato></allegati>
      </atto>
      <atto>
        <oggetto>Avviso pubblico per dirigente medico</oggetto>
        <nota>Scadenza domande: 30/09/2026</nota>
      </atto>
    </atti>
    """

    records = parse_catalog_records(source, xml, source.base_url)

    assert len(records) == 1
    assert records[0].title == "Avviso pubblico per dirigente psicologo"
    assert records[0].deadline is not None


def test_collect_catalog_links_keeps_relevant_same_site_links(monkeypatch) -> None:
    monkeypatch.setattr(catalog_sources, "MAX_DETAIL_LINKS_PER_SOURCE", 4)
    html = """
    <a href="/privacy">Privacy</a>
    <a href="/amministrazione-trasparente">Amministrazione trasparente</a>
    <a href="/concorsi">Concorsi</a>
    <a href="https://other.test/bandi">Bandi esterni</a>
    <a href="/lavora-con-noi">Lavora con noi</a>
    <a href="/concorsi/289-2026">Scheda</a>
    <a href="/ap/deliberazione-123">Deliberazione</a>
    """

    links = collect_catalog_links(html, "https://example.test/")

    assert links == [
        "https://example.test/concorsi/289-2026",
        "https://example.test/ap/deliberazione-123",
        "https://example.test/concorsi",
        "https://example.test/lavora-con-noi",
    ]


def test_entity_type_distinguishes_social_sources() -> None:
    assert (
        _entity_type(
            Source(
                source_type="third-sector-hub",
                organization="Fondazione Test",
            )
        )
        == "terzo-settore"
    )
    assert (
        _entity_type(
            Source(
                source_type="private-social-jobs",
                organization="Cooperativa Sociale Test",
            )
        )
        == "privato-sociale"
    )
