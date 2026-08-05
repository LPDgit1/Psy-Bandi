from app.importers.asl_bi import parse_aslbi_csv
from app.models import Source


def test_parse_aslbi_csv_extracts_psychology_opportunity() -> None:
    source = Source(
        id="src_aslbi",
        name="ASL BI - Bandi concorso reclutamento personale",
        source_type="aslbi-csv",
        base_url=(
            "https://trasparenza.aslbi.piemonte.it/"
            "bandi-concorso-reclutamento-personale?sf=102"
        ),
        organization="ASL BI",
        region="Piemonte",
    )
    csv_text = (
        "Anno;Identificativo bando;Data scadenza\n"
        "2026;Pubblico concorso n. 1 posto di dirigente psicologo;30/09/2026\n"
        "2026;Pubblico concorso n. 2 posti di dirigente medico;30/09/2026\n"
    )

    records = parse_aslbi_csv(
        source,
        csv_text,
        endpoint_url="https://trasparenza.aslbi.piemonte.it/csv-download/test",
    )

    assert len(records) == 1
    assert "psicologo" in records[0].title.casefold()
    assert records[0].deadline is not None
    assert records[0].official_url.startswith("https://trasparenza.aslbi.piemonte.it/")
