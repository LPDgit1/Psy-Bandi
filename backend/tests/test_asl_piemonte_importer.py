from app.importers.asl_piemonte import parse_piemonte_records
from app.models import Source


def test_parse_piemonte_xml_records_extracts_psychology_atto() -> None:
    source = Source(
        id="src_aslat",
        name="ASL AT - Concorsi in vigore",
        source_type="xml-index",
        base_url="https://example.test/concorsiinvigore.xml",
        organization="ASL AT",
        region="Piemonte",
    )
    xml = """
    <atti>
      <atto>
        <oggetto>AVVISO PER INCARICO LIBERO PROFESSIONALE A PSICOLOGO</oggetto>
        <nota>Scadenza domande: 20/09/2026</nota>
        <pubblicatodal>01/09/2026</pubblicatodal>
        <allegati><allegato><web>/atti/psicologo.pdf</web></allegato></allegati>
      </atto>
      <atto>
        <oggetto>AVVISO PER DIRIGENTE MEDICO</oggetto>
        <nota>Scadenza domande: 20/09/2026</nota>
      </atto>
    </atti>
    """

    records = parse_piemonte_records(source, xml, source.base_url)

    assert len(records) == 1
    assert records[0].title == "AVVISO PER INCARICO LIBERO PROFESSIONALE A PSICOLOGO"
    assert records[0].deadline is not None
    assert records[0].official_url == "https://example.test/atti/psicologo.pdf"


def test_parse_piemonte_html_records_uses_parent_context_for_pdf_links() -> None:
    source = Source(
        id="src_aslcn1",
        name="ASL CN1 - Concorsi pubblici e avvisi",
        source_type="html-list",
        base_url="https://example.test/concorsi",
        organization="ASL CN1",
        region="Piemonte",
    )
    html = """
    <table>
      <tr>
        <td>Concorso pubblico per dirigente psicologo SERD. Scadenza 30/09/2026.</td>
        <td><a href="/docs/bando_conc__PSICOL_x_serd.pdf">bando concorso</a></td>
      </tr>
      <tr>
        <td>Concorso pubblico per infermiere.</td>
        <td><a href="/docs/bando_infermiere.pdf">bando concorso</a></td>
      </tr>
    </table>
    """

    records = parse_piemonte_records(source, html, source.base_url)

    assert len(records) == 1
    assert "dirigente psicologo" in records[0].title.lower()
    assert records[0].official_url == "https://example.test/docs/bando_conc__PSICOL_x_serd.pdf"


def test_parse_piemonte_html_records_ignores_contact_links() -> None:
    source = Source(
        id="src_aslno",
        name="ASL NO - Portale concorsi",
        source_type="html-list",
        base_url="https://example.test/concorsi",
        organization="ASL NO",
        region="Piemonte",
    )
    html = """
    <article>
      <p>Concorso per dirigente psicologo disciplina psicoterapia.</p>
      <a href="tel:0321374593">tel:0321 374593</a>
      <a href="mailto:concorsi@example.test">concorsi@example.test</a>
    </article>
    """

    records = parse_piemonte_records(source, html, source.base_url)

    assert records == []


def test_parse_piemonte_html_records_ignores_pagination_and_unrelated_roles() -> None:
    source = Source(
        id="src_aslno",
        name="ASL NO - Portale concorsi",
        source_type="html-list",
        base_url="https://example.test/concorsi",
        organization="ASL NO",
        region="Piemonte",
    )
    html = """
    <nav class="pagination">
      <a href="?page=1">Pagina successiva</a>
      <a href="https://www.regione.piemonte.it/">Regione Piemonte</a>
    </nav>
    <article>
      <h2>Avviso pubblico per dirigente psicologo</h2>
      <p>Scadenza domande 30/09/2026.</p>
      <a href="/concorso/psicologo">Scheda</a>
    </article>
    <article>
      <h2>Avviso di selezione interna per Dietista</h2>
      <p>Scadenza domande 30/09/2026.</p>
      <a href="/concorso/dietista">Scheda</a>
    </article>
    """

    records = parse_piemonte_records(source, html, source.base_url)

    assert len(records) == 1
    assert "psicologo" in records[0].title.lower()
