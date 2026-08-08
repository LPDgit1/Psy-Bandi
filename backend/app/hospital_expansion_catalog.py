from __future__ import annotations


def _hospital_source(
    name: str,
    organization: str,
    base_url: str,
    region: str,
    note: str,
) -> dict[str, str]:
    return {
        "name": name,
        "source_type": "hospital-html-hub",
        "base_url": base_url,
        "region": region,
        "organization": organization,
        "import_method": "hospital-html-hub-deep",
        "technical_notes": note,
    }


LOMBARDY_ASST_NOTE = (
    "Fonte ufficiale aziendale verificata ad agosto 2026. Adapter profondo "
    "notturno; Gazzetta Ufficiale e inPA restano fonti nazionali di sicurezza."
)

LOMBARDY_ASST_SOURCE_DEFINITIONS = [
    _hospital_source(name, organization, url, "Lombardia", LOMBARDY_ASST_NOTE)
    for name, organization, url in (
        (
            "ASST Niguarda - Concorsi",
            "ASST Grande Ospedale Metropolitano Niguarda",
            "https://www.ospedaleniguarda.it/professionisti-e-aziende/lavora-con-noi-concorsi",
        ),
        (
            "ASST Santi Paolo e Carlo - Concorsi",
            "ASST Santi Paolo e Carlo",
            "https://www.asst-santipaolocarlo.it/concorsi",
        ),
        (
            "ASST Fatebenefratelli Sacco - Concorsi",
            "ASST Fatebenefratelli Sacco",
            "https://www.asst-fbf-sacco.it/concorsi",
        ),
        (
            "ASST Gaetano Pini CTO - Concorsi",
            "ASST Gaetano Pini CTO",
            "https://www.asst-pini-cto.it/it/concorsi",
        ),
        (
            "ASST Ovest Milanese - Concorsi",
            "ASST Ovest Milanese",
            "https://www.asst-ovestmi.it/concorsi-graduatorie",
        ),
        (
            "ASST Rhodense - Portale istituzionale",
            "ASST Rhodense",
            "https://www.asst-rhodense.it/",
        ),
        (
            "ASST Nord Milano - Lavora con noi",
            "ASST Nord Milano",
            "https://www.asst-nordmilano.it/lavora-con-noi",
        ),
        (
            "ASST Melegnano Martesana - Concorsi",
            "ASST Melegnano e della Martesana",
            "https://www.asst-melegnano-martesana.it/concorsi",
        ),
        (
            "ASST Lodi - Bandi e concorsi",
            "ASST di Lodi",
            "https://www.asst-lodi.it/bandi-e-concorsi",
        ),
        (
            "ASST Sette Laghi - Lavora con noi",
            "ASST dei Sette Laghi",
            "https://www.asst-settelaghi.it/lavora-con-noi1",
        ),
        (
            "ASST Valle Olona - Lavora con noi",
            "ASST della Valle Olona",
            "https://www.asst-valleolona.it/lavora-con-noi/",
        ),
        (
            "ASST Lariana - Concorsi",
            "ASST Lariana",
            "https://www.asst-lariana.it/asl-comunica/concorsi/",
        ),
        (
            "ASST Valtellina Alto Lario - Concorsi",
            "ASST della Valtellina e dell'Alto Lario",
            "https://www.asst-val.it/asst-comunica/concorsi/",
        ),
        (
            "ASST Valcamonica - Portale istituzionale",
            "ASST della Valcamonica",
            "https://www.asst-valcamonica.it/",
        ),
        (
            "ASST Lecco - Concorsi",
            "ASST di Lecco",
            "https://www.asst-lecco.it/amministrazione-trasparente/bandi-di-concorso/concorsi/",
        ),
        (
            "ASST Brianza - Portale istituzionale",
            "ASST della Brianza",
            "https://www.asst-brianza.it/",
        ),
        (
            "IRCCS San Gerardo - Lavora con noi",
            "Fondazione IRCCS San Gerardo dei Tintori",
            "https://www.irccs-sangerardo.it/lavora-con-noi",
        ),
        (
            "ASST Papa Giovanni XXIII - Concorsi",
            "ASST Papa Giovanni XXIII",
            "https://www.asst-pg23.it/concorsi",
        ),
        (
            "ASST Bergamo Est - Concorsi e avvisi",
            "ASST Bergamo Est",
            "https://www.asst-bergamoest.it/it/concorsi-avvisi-manifestazioni-d-interesse-e-lettere-d-invito?filter=4218#listing",
        ),
        (
            "ASST Bergamo Ovest - Portale istituzionale",
            "ASST Bergamo Ovest",
            "https://www.asst-bgovest.it/",
        ),
        (
            "ASST Spedali Civili - Albo concorsi",
            "ASST degli Spedali Civili di Brescia",
            "https://www.asst-spedalicivili.it/albo-pretorio-concorsi",
        ),
        (
            "ASST Franciacorta - Bandi di concorso",
            "ASST della Franciacorta",
            "https://www.asst-franciacorta.it/amministrazione-trasparente/bandi-di-concorso/",
        ),
        (
            "ASST Garda - Bandi e concorsi",
            "ASST del Garda",
            "https://www.asst-garda.it/bandi-di-gara-e-concorsi/",
        ),
        (
            "ASST Cremona - Concorsi",
            "ASST di Cremona",
            "https://www.asst-cremona.it/concorsi",
        ),
        (
            "ASST Crema - Lavora con noi",
            "ASST di Crema",
            "https://www.asst-crema.it/lavora-noi",
        ),
        (
            "ASST Mantova - Concorsi",
            "ASST di Mantova",
            "https://www.asst-mantova.it/concorsi",
        ),
        (
            "ASST Pavia - Lavora con noi",
            "ASST di Pavia",
            "https://asst-pavia.it/lavora-con-noi/",
        ),
    )
]


IRCCS_DIRECT_NOTE = (
    "Fonte ufficiale diretta ad alta rilevanza per psicologia, neuroscienze o "
    "riabilitazione, verificata ad agosto 2026 e letta dall'adapter profondo."
)

STRATEGIC_IRCCS_SOURCE_DEFINITIONS = [
    _hospital_source(name, organization, url, region, IRCCS_DIRECT_NOTE)
    for name, organization, url, region in (
        (
            "Fondazione Santa Lucia IRCCS - Lavora con noi",
            "Fondazione Santa Lucia IRCCS",
            "https://www.hsantalucia.it/lavora-con-noi",
            "Lazio",
        ),
        (
            "IRCCS Ospedale San Raffaele - Lavora con noi",
            "IRCCS Ospedale San Raffaele",
            "https://www.hsr.it/lavora-con-noi",
            "Lombardia",
        ),
        (
            "IRCCS Humanitas - Opportunita professionali",
            "IRCCS Humanitas Research Hospital",
            "https://jobs.humanitas.it/",
            "Lombardia",
        ),
        (
            "Fondazione Don Gnocchi IRCCS - Lavora con noi",
            "Fondazione Don Gnocchi IRCCS",
            "https://www.dongnocchi.it/lavora-con-noi",
            "Lombardia",
        ),
        (
            "ICS Maugeri IRCCS - Carriere",
            "ICS Maugeri IRCCS",
            "https://carriere.icsmaugeri.it/",
            "Lombardia",
        ),
        (
            "IRCCS Auxologico - Lavora con noi",
            "IRCCS Istituto Auxologico Italiano",
            "https://www.auxologico.it/lavora-con-noi",
            "Lombardia",
        ),
        (
            "Fondazione Mondino IRCCS - Lavora con noi",
            "Fondazione Mondino IRCCS",
            "https://www.mondino.it/lavora-con-noi/",
            "Lombardia",
        ),
        (
            "IRCCS Carlo Besta - Concorsi",
            "Fondazione IRCCS Istituto Neurologico Carlo Besta",
            "https://www.istituto-besta.it/concorsi",
            "Lombardia",
        ),
        (
            "IRCCS Ca Granda Policlinico - Lavora con noi",
            "Fondazione IRCCS Ca' Granda Ospedale Maggiore Policlinico",
            "https://www.policlinico.mi.it/lavora-con-noi",
            "Lombardia",
        ),
        (
            "IRCCS Istituto Nazionale Tumori Milano - Concorsi",
            "Fondazione IRCCS Istituto Nazionale dei Tumori",
            "https://www.istitutotumori.mi.it/concorsi",
            "Lombardia",
        ),
        (
            "Fondazione Policlinico Gemelli IRCCS - Lavora con noi",
            "Fondazione Policlinico Universitario Agostino Gemelli IRCCS",
            "https://www.policlinicogemelli.it/lavora-con-noi/",
            "Lazio",
        ),
        (
            "IDI IRCCS - Lavora con noi",
            "Istituto Dermopatico dell'Immacolata IRCCS",
            "https://www.idi.it/lavora-con-noi",
            "Lazio",
        ),
    )
]


PUBLIC_AO_AOU_NOTE = (
    "Fonte ufficiale AO, AOU o IRCCS pubblico verificata ad agosto 2026. "
    "Adapter profondo notturno con deduplicazione rispetto alle fonti nazionali."
)

PUBLIC_AO_AOU_SOURCE_DEFINITIONS = [
    _hospital_source(name, organization, url, region, PUBLIC_AO_AOU_NOTE)
    for name, organization, url, region in (
        (
            "AOU Maggiore della Carita Novara - Concorsi e selezioni",
            "AOU Maggiore della Carita di Novara",
            "https://www.maggioreosp.novara.it/lospedale-maggiore/personale/concorsi-e-selezioni/",
            "Piemonte",
        ),
        (
            "AO Mauriziano Torino - Concorsi",
            "Azienda Ospedaliera Ordine Mauriziano di Torino",
            "https://www.mauriziano.it/flex/cm/pages/ServeBLOB.php/L/IT/IDPagina/31",
            "Piemonte",
        ),
        (
            "AOU Ferrara - Bandi di concorso",
            "Azienda Ospedaliero-Universitaria di Ferrara",
            "https://at.ospfe.it/bandi-di-concorso",
            "Emilia-Romagna",
        ),
        (
            "Policlinico Umberto I - Portale istituzionale",
            "AOU Policlinico Umberto I",
            "https://www.policlinicoumberto1.it/",
            "Lazio",
        ),
        (
            "AORN Santobono Pausilipon - Portale istituzionale",
            "AORN Santobono Pausilipon",
            "https://www.santobonopausilipon.it/",
            "Campania",
        ),
        (
            "Azienda Ospedaliera dei Colli - Bandi di concorso",
            "Azienda Ospedaliera dei Colli",
            "https://www.ospedalideicolli.it/amministrazione-trasparente/bandi-di-concorso/",
            "Campania",
        ),
        (
            "AO Sant'Anna e San Sebastiano Caserta - Concorsi",
            "AORN Sant'Anna e San Sebastiano di Caserta",
            "https://www.ospedale.caserta.it/concorsi/",
            "Campania",
        ),
        (
            "AOU Vanvitelli - Bandi di concorso",
            "AOU Luigi Vanvitelli",
            "https://www.policliniconapoli.it/bandi-di-concorso/",
            "Campania",
        ),
        (
            "AOU Policlinico Messina - Bandi di concorso",
            "AOU Policlinico Gaetano Martino di Messina",
            "https://www.polime.it/Amministrazione-Trasparente/Bandi-di-concorso",
            "Sicilia",
        ),
        (
            "IRCCS Bonino Pulejo - Concorsi",
            "IRCCS Centro Neurolesi Bonino Pulejo",
            "https://www.irccsme.it/concorsi/",
            "Sicilia",
        ),
    )
]


HOSPITAL_EXPANSION_SOURCE_DEFINITIONS = [
    *LOMBARDY_ASST_SOURCE_DEFINITIONS,
    *STRATEGIC_IRCCS_SOURCE_DEFINITIONS,
    *PUBLIC_AO_AOU_SOURCE_DEFINITIONS,
]
