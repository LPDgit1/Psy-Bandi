from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.central_health_catalog import CENTRAL_HEALTH_SOURCE_DEFINITIONS
from app.hospital_health_catalog import HOSPITAL_HEALTH_SOURCE_DEFINITIONS
from app.importers.arcs_fvg import ARCS_FVG_SOURCE_NAME
from app.importers.asdaa_alto_adige import ASDAA_SOURCE_NAME
from app.importers.asl_piemonte import ASL_PIEMONTE_SOURCE_NAMES
from app.importers.asl_roma2 import ASL_ROMA2_SOURCE_NAME
from app.importers.ast_marche import AST_MARCHE_SOURCE_NAMES
from app.importers.asuit_trentino import ASUIT_SOURCE_NAME
from app.importers.ats_liguria import ATS_LIGURIA_SOURCE_NAME
from app.importers.ausl_romagna import AUSL_ROMAGNA_SOURCE_NAME
from app.importers.azienda_zero import AZIENDA_ZERO_SOURCE_NAME
from app.importers.azienda_zero_piemonte import AZIENDA_ZERO_PIEMONTE_SOURCE_NAME
from app.importers.catalog_sources import SPECIFIC_ADAPTER_SOURCE_NAMES, _entity_type
from app.importers.comune_venezia import COMUNE_VENEZIA_SOURCE_NAME
from app.importers.inail import INAIL_SOURCE_NAME
from app.importers.inpa import INPA_SOURCE_NAME
from app.importers.inps import INPS_SOURCE_NAME
from app.importers.myportal_veneto import TREVISO
from app.importers.target_health_html import TARGET_HEALTH_SOURCE_NAMES
from app.importers.usl_umbria1 import USL_UMBRIA1_SOURCE_NAME
from app.importers.usl_umbria2 import USL_UMBRIA2_SOURCE_NAME
from app.ministerial_catalog import MINISTERIAL_SOURCE_DEFINITIONS
from app.models import Base, Source
from app.national_health_catalog import (
    NATIONAL_HEALTH_SOURCE_DEFINITIONS,
    NON_AUTOMATED_HEALTH_SOURCE_DEFINITIONS,
)
from app.northern_health_catalog import NORTHERN_HEALTH_SOURCE_DEFINITIONS
from app.puglia_aol_catalog import PUGLIA_AOL_SOURCE_DEFINITIONS
from app.scripts.audit_sources import adapter_family
from app.services.import_pipeline import PUBLIC_REFRESH_IMPORTERS
from app.services.source_probe import (
    _probe_failure_status,
    _probe_success_status,
    ensure_source_catalog,
    source_refresh_order,
)
from app.source_catalog import VERIFIED_SOURCE_CATALOG
from app.target_health_catalog import TARGET_HEALTH_SOURCE_DEFINITIONS


def test_catalog_includes_all_veneto_provincial_capitals() -> None:
    organizations = {source["organization"] for source in VERIFIED_SOURCE_CATALOG}

    assert {
        "Comune di Belluno",
        "Comune di Padova",
        "Comune di Rovigo",
        "Comune di Treviso",
        "Comune di Venezia",
        "Comune di Verona",
        "Comune di Vicenza",
    } <= organizations


def test_catalog_includes_northern_university_network() -> None:
    university_sources = [
        source
        for source in VERIFIED_SOURCE_CATALOG
        if "Universita" in source["organization"]
        or source["organization"].startswith("Politecnico")
        or source["organization"].startswith("Alma Mater")
    ]

    assert len(university_sources) >= 20
    assert all(source["base_url"].startswith("https://") for source in university_sources)


def test_catalog_includes_open_inail_and_inps_sources() -> None:
    organizations = {source["organization"]: source for source in VERIFIED_SOURCE_CATALOG}

    assert organizations["INAIL"]["base_url"] == (
        "https://www.inail.it/portale/it/inail-comunica/avvisi.html"
    )
    assert organizations["INPS"]["base_url"] == (
        "https://www.inps.it/it/it/avvisi-bandi-e-fatturazione/"
        "fatturazione-concorsi.html"
    )


def test_catalog_includes_northern_territorial_health_network() -> None:
    organizations = {
        source["organization"] for source in NORTHERN_HEALTH_SOURCE_DEFINITIONS
    }

    assert {
        "Azienda Sanitaria Zero Piemonte",
        "ASL AL",
        "ASL AT",
        "ASL CN1",
        "ASL CN2",
        "ASL NO",
        "ASL Citta di Torino",
        "ASL TO3",
        "ASL TO4",
        "ASL TO5",
        "ASL VC",
        "ASL VCO",
        "ATS Liguria",
        "ATS Milano",
        "ATS Insubria",
        "ATS Brianza",
        "ATS Brescia",
        "ATS Bergamo",
        "ATS Montagna",
        "ATS Val Padana",
        "ATS Pavia",
        "Regione Lombardia",
        "Regione Emilia-Romagna",
        "ARCS Friuli-Venezia Giulia",
        "ASUIT Trentino",
        "Azienda Sanitaria dell'Alto Adige",
        "Azienda USL Valle d'Aosta",
    } <= organizations


def test_every_catalogued_source_has_an_adapter_or_explicit_access_review() -> None:
    unassigned = [
        candidate["name"]
        for candidate in VERIFIED_SOURCE_CATALOG
        if adapter_family(Source(**candidate, status="catalogued")) == "unassigned"
    ]

    assert unassigned == []


def test_access_blocked_sources_are_explicitly_routed_to_review() -> None:
    review_sources = {
        candidate["name"]
        for candidate in VERIFIED_SOURCE_CATALOG
        if adapter_family(Source(**candidate, status="catalogued")) == "access-review"
    }

    assert review_sources == {
        "ASL TO3 - Portale trasparenza",
        "Comune di Milano - Bandi di concorso",
        "Comune di Viterbo - Bandi di concorso",
        "MAECI - Lavora con noi e opportunita",
    }


def test_specific_adapter_registry_matches_implemented_connectors() -> None:
    implemented_connector_sources = {
        ARCS_FVG_SOURCE_NAME,
        ASDAA_SOURCE_NAME,
        ASL_ROMA2_SOURCE_NAME,
        ASUIT_SOURCE_NAME,
        ATS_LIGURIA_SOURCE_NAME,
        AUSL_ROMAGNA_SOURCE_NAME,
        AZIENDA_ZERO_SOURCE_NAME,
        AZIENDA_ZERO_PIEMONTE_SOURCE_NAME,
        COMUNE_VENEZIA_SOURCE_NAME,
        INAIL_SOURCE_NAME,
        INPA_SOURCE_NAME,
        INPS_SOURCE_NAME,
        TREVISO.source_name,
        USL_UMBRIA1_SOURCE_NAME,
        USL_UMBRIA2_SOURCE_NAME,
        *ASL_PIEMONTE_SOURCE_NAMES,
        *AST_MARCHE_SOURCE_NAMES,
        *TARGET_HEALTH_SOURCE_NAMES,
    }

    assert SPECIFIC_ADAPTER_SOURCE_NAMES == implemented_connector_sources


def test_every_adapter_family_is_scheduled_for_public_refresh() -> None:
    scheduled_importers = {
        importer.__name__ for _label, importer in PUBLIC_REFRESH_IMPORTERS
    }

    assert {
        "run_arcs_fvg_import",
        "run_asdaa_alto_adige_import",
        "run_asl_piemonte_import",
        "run_asl_roma2_import",
        "run_ast_marche_import",
        "run_asuit_trentino_import",
        "run_ats_liguria_import",
        "run_ausl_romagna_import",
        "run_azienda_zero_import",
        "run_azienda_zero_piemonte_import",
        "run_catalog_sources_import",
        "run_comune_venezia_import",
        "run_deep_html_sources_import",
        "run_inail_import",
        "run_inps_import",
        "run_myportal_treviso_import",
        "run_puglia_aol_import",
        "run_target_health_html_import",
        "run_usl_umbria1_import",
        "run_usl_umbria2_import",
    } == scheduled_importers


def test_catalog_uses_current_official_source_urls() -> None:
    sources_by_name = {
        source["name"]: source["base_url"] for source in VERIFIED_SOURCE_CATALOG
    }

    assert sources_by_name["Policlinico San Martino - Concorsi"] == (
        "https://www.ospedalesanmartino.it/it/bandi"
    )
    assert sources_by_name["AOU Siena - Concorsi"] == (
        "https://www.ao-siena.toscana.it/avvisi-e-bandi/"
    )
    assert sources_by_name["INRCA - Concorsi"] == (
        "https://www.inrca.it/INRCA/MODTRASP52/"
        "?Pag=tra_Isti_Concorsi_EspletatiX&mnu=78"
    )
    assert sources_by_name["AO Cosenza - Bandi di concorso"] == (
        "https://aocosenza.it/bandi/concorsi/"
    )
    assert sources_by_name["AOU Renato Dulbecco - Bandi di concorso"] == (
        "https://www.aourenatodulbecco.it/bandi-e-concorsi/"
    )
    assert sources_by_name["GOM Reggio Calabria - Bandi di concorso"] == (
        "https://www.gomrc.it/doc/amministrazione-trasparente/"
        "bandi-di-concorso.html"
    )
    assert sources_by_name["Comune di Milano - Bandi di concorso"] == (
        "https://www.comune.milano.it/amministrazione/"
        "amministrazione-trasparente/bandi-di-concorso"
    )
    assert sources_by_name["Comune di Rieti - Bandi di concorso"] == (
        "https://lnx.comune.rieti.it/amministrazione-trasparente/"
        "content/bandi-di-concorso"
    )
    assert sources_by_name["Comune di Viterbo - Bandi di concorso"] == (
        "https://comune.viterbo.it/argomento/concorsi/"
    )
    assert sources_by_name["Comune di Barletta - Amministrazione Trasparente"] == (
        "https://trasparenza.comune.barletta.bt.it/"
        "pagina639_bandi-di-concorso.html"
    )


def test_catalog_excludes_robots_blocked_asl_bi_from_automatic_probe() -> None:
    organizations = {
        source["organization"] for source in NORTHERN_HEALTH_SOURCE_DEFINITIONS
    }

    assert "ASL BI" not in organizations
    assert len(NORTHERN_HEALTH_SOURCE_DEFINITIONS) == 27


def test_catalog_includes_verified_central_health_network() -> None:
    organizations = {
        source["organization"] for source in CENTRAL_HEALTH_SOURCE_DEFINITIONS
    }

    assert {
        "AUSL Romagna",
        "AST Pesaro Urbino",
        "AST Ancona",
        "AST Macerata",
        "AST Fermo",
        "AST Ascoli Piceno",
        "USL Umbria 1",
        "USL Umbria 2",
    } <= organizations


def test_catalog_includes_target_regional_health_and_social_network() -> None:
    regions = {source["region"] for source in TARGET_HEALTH_SOURCE_DEFINITIONS}
    organizations = {
        source["organization"] for source in TARGET_HEALTH_SOURCE_DEFINITIONS
    }

    assert {
        "Toscana",
        "Emilia-Romagna",
        "Lazio",
        "Campania",
        "Puglia",
        "Basilicata",
        "Abruzzo",
        "Molise",
        "Calabria",
        "Sicilia",
        "Sardegna",
    } <= regions
    assert {
        "ESTAR Toscana",
        "ASL Roma 1",
        "ASL Roma 4",
        "ASL Roma 5",
        "ASL Roma 6",
        "ASL Napoli 3 Sud",
        "ASL Napoli 1 Centro",
        "ASL Avellino",
        "ASL Bari",
        "ASL Lecce",
        "ASP Basilicata",
        "ASL Teramo",
        "ASReM Molise",
        "ASP Crotone",
        "ASP Messina",
        "ASP Enna",
        "ASP Siracusa",
        "ASP Caltanissetta",
        "AREUS Sardegna",
        "ARES Sardegna",
    } <= organizations
    counts_by_region = {
        region: sum(
            1
            for source in TARGET_HEALTH_SOURCE_DEFINITIONS
            if source["region"] == region
        )
        for region in {"Lazio", "Campania", "Emilia-Romagna", "Sicilia"}
    }
    assert counts_by_region["Lazio"] >= 8
    assert counts_by_region["Campania"] >= 6
    assert counts_by_region["Emilia-Romagna"] >= 7
    assert counts_by_region["Sicilia"] >= 5


def test_catalog_includes_full_national_territorial_health_network() -> None:
    automated_organizations = {source["organization"] for source in VERIFIED_SOURCE_CATALOG}
    non_automated_organizations = {
        source["organization"] for source in NON_AUTOMATED_HEALTH_SOURCE_DEFINITIONS
    }
    documented_organizations = automated_organizations | non_automated_organizations

    expected_territorial_or_central = {
        "Azienda USL Valle d'Aosta",
        "Azienda Sanitaria Zero Piemonte",
        "ASL AL",
        "ASL AT",
        "ASL BI",
        "ASL CN1",
        "ASL CN2",
        "ASL Citta di Torino",
        "ASL NO",
        "ASL TO3",
        "ASL TO4",
        "ASL TO5",
        "ASL VC",
        "ASL VCO",
        "ATS Liguria",
        "ATS Bergamo",
        "ATS Brescia",
        "ATS Brianza",
        "ATS Insubria",
        "ATS Milano",
        "ATS Montagna",
        "ATS Pavia",
        "ATS Val Padana",
        "ASUIT Trentino",
        "Azienda Sanitaria dell'Alto Adige",
        "Azienda Zero - Regione del Veneto",
        "AULSS 1 Dolomiti",
        "AULSS 2 Marca Trevigiana",
        "AULSS 3 Serenissima",
        "AULSS 4 Veneto Orientale",
        "AULSS 5 Polesana",
        "AULSS 6 Euganea",
        "AULSS 7 Pedemontana",
        "AULSS 8 Berica",
        "AULSS 9 Scaligera",
        "ARCS Friuli-Venezia Giulia",
        "AUSL Piacenza",
        "AUSL Parma",
        "AUSL Reggio Emilia",
        "AUSL Modena",
        "AUSL Bologna",
        "AUSL Imola",
        "AUSL Ferrara",
        "AUSL Romagna",
        "ESTAR Toscana",
        "AUSL Toscana Centro",
        "AUSL Toscana Nord Ovest",
        "AUSL Toscana Sud Est",
        "USL Umbria 1",
        "USL Umbria 2",
        "AST Pesaro Urbino",
        "AST Ancona",
        "AST Macerata",
        "AST Fermo",
        "AST Ascoli Piceno",
        "ASL Roma 1",
        "ASL Roma 2",
        "ASL Roma 3",
        "ASL Roma 4",
        "ASL Roma 5",
        "ASL Roma 6",
        "ASL Frosinone",
        "ASL Latina",
        "ASL Rieti",
        "ASL Viterbo",
        "ASL Avezzano Sulmona L'Aquila",
        "ASL Lanciano Vasto Chieti",
        "ASL Pescara",
        "ASL Teramo",
        "ASReM Molise",
        "ASL Avellino",
        "ASL Benevento",
        "ASL Caserta",
        "ASL Napoli 1 Centro",
        "ASL Napoli 2 Nord",
        "ASL Napoli 3 Sud",
        "ASL Salerno",
        "ASL Bari",
        "ASL Foggia",
        "ASL BT",
        "ASL Taranto",
        "ASL Brindisi",
        "ASL Lecce",
        "ASP Basilicata",
        "ASM Matera",
        "ASP Catanzaro",
        "ASP Cosenza",
        "ASP Crotone",
        "ASP Reggio Calabria",
        "ASP Vibo Valentia",
        "Azienda Zero Calabria",
        "ASP Agrigento",
        "ASP Caltanissetta",
        "ASP Catania",
        "ASP Enna",
        "ASP Messina",
        "ASP Palermo",
        "ASP Ragusa",
        "ASP Siracusa",
        "ASP Trapani",
        "ARES Sardegna",
        "AREUS Sardegna",
        "ASL Sassari",
        "ASL Gallura",
        "ASL Nuoro",
        "ASL Ogliastra",
        "ASL Oristano",
        "ASL Medio Campidano",
        "ASL Sulcis",
        "ASL Cagliari",
    }

    assert sorted(expected_territorial_or_central - documented_organizations) == []


def test_non_automated_health_sources_do_not_enter_refresh_catalog() -> None:
    automated_organizations = {source["organization"] for source in VERIFIED_SOURCE_CATALOG}
    non_automated_organizations = {
        source["organization"] for source in NON_AUTOMATED_HEALTH_SOURCE_DEFINITIONS
    }

    assert {
        "ASL BI",
        "ASP Vibo Valentia",
        "Azienda Zero Calabria",
    } <= non_automated_organizations
    assert automated_organizations.isdisjoint(non_automated_organizations)


def test_national_health_extension_has_importable_public_sources() -> None:
    assert len(NATIONAL_HEALTH_SOURCE_DEFINITIONS) >= 35
    assert all(
        source["base_url"].startswith("https://")
        for source in NATIONAL_HEALTH_SOURCE_DEFINITIONS
    )
    assert all(
        source["source_type"] in {"html-list", "html-hub"}
        for source in NATIONAL_HEALTH_SOURCE_DEFINITIONS
    )


def test_catalog_includes_hospital_health_sources_for_adapter_review() -> None:
    organizations = {
        source["organization"] for source in HOSPITAL_HEALTH_SOURCE_DEFINITIONS
    }

    assert {
        "Azienda Ospedale Universita Padova",
        "Azienda Ospedaliera Universitaria Integrata Verona",
        "Istituto Oncologico Veneto IRCCS",
        "AOU Careggi",
        "Azienda Ospedaliero Universitaria Pisana",
        "Azienda Ospedaliera San Camillo Forlanini",
        "AOU Federico II",
        "AOU Renato Dulbecco",
        "Azienda Ospedaliera Cannizzaro",
        "ARNAS G. Brotzu",
    } <= organizations
    assert all(
        source["source_type"] == "hospital-html-hub"
        for source in HOSPITAL_HEALTH_SOURCE_DEFINITIONS
    )
    assert all(
        "pending-adapter" in source["import_method"]
        for source in HOSPITAL_HEALTH_SOURCE_DEFINITIONS
    )


def test_catalog_includes_ministerial_sources_and_marks_maeci_for_review() -> None:
    sources_by_org = {
        source["organization"]: source for source in MINISTERIAL_SOURCE_DEFINITIONS
    }

    assert {
        "Ministero del Lavoro e delle Politiche Sociali",
        "Ministero dell'Istruzione e del Merito",
        "Ministero degli Affari Esteri e della Cooperazione Internazionale",
    } <= set(sources_by_org)
    assert sources_by_org[
        "Ministero degli Affari Esteri e della Cooperazione Internazionale"
    ]["source_type"] == "ministerial-access-review"


def test_catalog_entity_type_recognizes_health_acronyms() -> None:
    aulss = Source(organization="AULSS 6 Euganea", base_url="https://example.test")
    asp = Source(organization="ASP Palermo", base_url="https://example.test")
    estar = Source(organization="ESTAR Toscana", base_url="https://example.test")
    hospital = Source(
        organization="Azienda Ospedaliera Universitaria Integrata Verona",
        base_url="https://example.test",
    )

    assert _entity_type(aulss) == "azienda-sanitaria"
    assert _entity_type(asp) == "azienda-sanitaria"
    assert _entity_type(estar) == "azienda-sanitaria"
    assert _entity_type(hospital) == "azienda-sanitaria"


def test_catalog_includes_verified_regional_and_capital_sources() -> None:
    organizations = {source["organization"] for source in VERIFIED_SOURCE_CATALOG}

    assert {
        "Regione Piemonte",
        "Regione Liguria",
        "Regione Toscana",
        "Regione Marche",
        "Regione Abruzzo",
        "Regione Puglia",
        "Regione Autonoma della Sardegna",
        "Regione Siciliana",
        "Comune di Torino",
        "Comune di Aosta",
        "Comune di Genova",
        "Comune di Bologna",
        "Comune di Trieste",
        "Comune di Ancona",
        "Comune di Perugia",
        "Comune di Milano",
        "Comune di Trento",
        "Comune di Bolzano",
        "Comune di Firenze",
        "Comune di Napoli",
        "Comune di Bari",
        "Comune di Catanzaro",
        "Comune dell'Aquila",
        "Comune di Campobasso",
        "Comune di Potenza",
        "Comune di Palermo",
        "Comune di Cagliari",
        "ATS Sardegna",
    } <= organizations


def test_catalog_includes_requested_provincial_capitals() -> None:
    organizations = {source["organization"] for source in VERIFIED_SOURCE_CATALOG}

    assert {
        "Comune di Frosinone",
        "Comune di Latina",
        "Comune di Rieti",
        "Comune di Viterbo",
        "Comune di Avellino",
        "Comune di Benevento",
        "Comune di Caserta",
        "Comune di Salerno",
        "Comune di Brindisi",
        "Comune di Foggia",
        "Comune di Lecce",
        "Comune di Taranto",
        "Comune di Andria",
        "Comune di Barletta",
        "Comune di Trani",
        "Comune di Matera",
        "Comune di Chieti",
        "Comune di Pescara",
        "Comune di Teramo",
        "Comune di Alessandria",
        "Comune di Asti",
        "Comune di Biella",
        "Comune di Cuneo",
        "Comune di Novara",
        "Comune di Verbania",
        "Comune di Vercelli",
        "Comune di Bergamo",
        "Comune di Brescia",
        "Comune di Como",
        "Comune di Cremona",
        "Comune di Lecco",
        "Comune di Lodi",
        "Comune di Mantova",
        "Comune di Monza",
        "Comune di Pavia",
        "Comune di Sondrio",
        "Comune di Varese",
        "Comune di Agrigento",
        "Comune di Caltanissetta",
        "Comune di Catania",
        "Comune di Enna",
        "Comune di Messina",
        "Comune di Ragusa",
        "Comune di Siracusa",
        "Comune di Trapani",
    } <= organizations


def test_catalog_includes_third_sector_and_private_social_sources() -> None:
    sources_by_org = {
        source["organization"]: source for source in VERIFIED_SOURCE_CATALOG
    }

    assert {
        "Ministero del Lavoro e delle Politiche Sociali",
        "Forum Nazionale Terzo Settore",
        "Fondazione CON IL SUD",
        "Con i Bambini",
        "CSV Lombardia",
        "Coopselios",
        "Codess Sociale",
        "Telefono Azzurro",
        "Emergency",
        "CUAMM Medici con l'Africa",
        "Croce Rossa Italiana",
        "La Nostra Famiglia",
    } <= set(sources_by_org)
    assert sources_by_org["Fondazione CON IL SUD"]["source_type"] == "third-sector-hub"
    assert sources_by_org["Coopselios"]["source_type"] == "private-social-jobs"
    assert sources_by_org["Telefono Azzurro"]["source_type"] == "private-social-jobs"


def test_catalog_includes_puglia_aol_health_network() -> None:
    organizations = {
        source["organization"] for source in PUGLIA_AOL_SOURCE_DEFINITIONS
    }

    assert {
        "ASL Bari",
        "ASL Foggia",
        "ASL BT",
        "ASL Taranto",
        "ASL Brindisi",
        "ASL Lecce",
        "Azienda Ospedaliera Ospedali Riuniti - Foggia",
        "Azienda Ospedaliero Universitaria Consorziale Policlinico",
    } <= organizations
    assert all(
        source["source_type"] == "puglia-aol-api"
        for source in PUGLIA_AOL_SOURCE_DEFINITIONS
    )


def test_ensure_source_catalog_refreshes_metadata_without_resetting_status() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    candidate = VERIFIED_SOURCE_CATALOG[0]

    with Session(engine) as db:
        source = Source(
            name=candidate["name"],
            source_type="old",
            base_url="https://example.test/old",
            status="reachable",
        )
        db.add(source)
        db.commit()

        ensure_source_catalog(db)
        refreshed = db.scalar(select(Source).where(Source.name == candidate["name"]))

        assert refreshed is not None
        assert refreshed.base_url == candidate["base_url"]
        assert refreshed.source_type == candidate["source_type"]
        assert refreshed.status == "reachable"


def test_probe_error_status_distinguishes_tls_and_timeout_reviews() -> None:
    tls_error = httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] test")

    source = Source(name="Catalogata", base_url="https://example.test")

    assert _probe_failure_status(source, tls_error) == "tls-review"
    assert (
        _probe_failure_status(source, httpx.ConnectError("[SSL] handshake failure"))
        == "tls-review"
    )
    assert _probe_failure_status(source, httpx.ReadTimeout("timed out")) == "timeout-review"
    assert _probe_failure_status(source, RuntimeError("other")) == "unreachable"


def test_probe_reports_current_failure_for_previously_active_sources() -> None:
    active_source = Source(
        name="Fonte con adapter",
        base_url="https://example.test",
        status="active",
    )
    catalogued_source = Source(
        name="Fonte catalogata",
        base_url="https://example.test",
        status="catalogued",
    )

    assert _probe_success_status(active_source) == "active"
    assert _probe_failure_status(active_source, RuntimeError("network")) == "unreachable"
    assert _probe_success_status(catalogued_source) == "reachable"


def test_source_refresh_order_prioritizes_never_checked_then_oldest() -> None:
    now = datetime(2026, 7, 13, tzinfo=UTC)
    never = Source(name="Mai verificata", base_url="https://never.test")
    older = Source(
        name="Verificata prima",
        base_url="https://older.test",
        last_success_at=now - timedelta(days=2),
    )
    recent = Source(
        name="Verificata ora",
        base_url="https://recent.test",
        last_success_at=now,
    )

    assert source_refresh_order([recent, older, never]) == [never, older, recent]
