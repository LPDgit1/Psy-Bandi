from __future__ import annotations


"""Official public-institution sources outside the existing health catalog.

The regional school offices are taken from the Ministry of Education's official
directory.  Valle d'Aosta and Trentino-Alto Adige are not listed as USRs in that
directory because their school administration is autonomous, so they are not
invented here.
"""


PUBLIC_INSTITUTION_SOURCE_DEFINITIONS = [
    {
        "name": "Ministero della Salute - Bandi di concorso",
        "source_type": "public-institution-html",
        "base_url": (
            "https://www.salute.gov.it/new/it/amministrazione-trasparente/"
            "bandi-di-concorso/"
        ),
        "region": None,
        "organization": "Ministero della Salute",
        "import_method": "public-institution-detail",
        "technical_notes": (
            "Sezione ufficiale Amministrazione Trasparente. L'adapter segue le "
            "schede e gli allegati pubblici, mantenendo il link originale."
        ),
    },
    {
        "name": "Istituto Superiore di Sanita - Bandi di concorso",
        "source_type": "public-institution-html",
        "base_url": (
            "https://amministrazionetrasparente.iss.it/index.html%3Ftipologie%3D"
            "bandi-di-concorso.html"
        ),
        "region": None,
        "organization": "Istituto Superiore di Sanita",
        "import_method": "public-institution-detail",
        "technical_notes": (
            "Indice ufficiale di Amministrazione Trasparente usato come percorso "
            "pubblico stabile; il portale selezioni principale puo presentare "
            "protezioni automatiche e non viene aggirato."
        ),
    },
    {
        "name": "CNR - Selezioni online",
        "source_type": "public-institution-html",
        "base_url": "https://selezionionline.cnr.it/jconon/",
        "region": None,
        "organization": "Consiglio Nazionale delle Ricerche",
        "import_method": "public-institution-detail",
        "technical_notes": (
            "Portale ufficiale delle selezioni CNR. L'adapter conserva la scheda "
            "e il link alla procedura, con filtro sui profili psicologici."
        ),
    },
    {
        "name": "Istituto Italiano di Tecnologia - Openings",
        "source_type": "public-institution-html",
        "base_url": "https://www.iit.it/it-IT/openings",
        "region": None,
        "organization": "Istituto Italiano di Tecnologia",
        "import_method": "public-institution-detail",
        "technical_notes": (
            "Pagina ufficiale delle posizioni aperte IIT, incluse ricerca e "
            "collaborazioni. Importa solo contenuti con segnali psicologici o "
            "neuro-scientifici riconoscibili."
        ),
    },
    {
        "name": "Dipartimento della Protezione Civile - Bandi di concorso",
        "source_type": "public-institution-html",
        "base_url": (
            "https://www.protezionecivile.gov.it/it/dipartimento/"
            "amministrazione-trasparente/bandi-di-concorso/"
        ),
        "region": None,
        "organization": "Dipartimento della Protezione Civile",
        "import_method": "public-institution-detail",
        "technical_notes": (
            "Sezione ufficiale dei bandi di concorso e delle selezioni. Sono "
            "esclusi gli atti privi di contenuto professionale pertinente."
        ),
    },
    {
        "name": "Ministero della Giustizia - Concorsi, esami, selezioni e assunzioni",
        "source_type": "public-institution-html",
        "base_url": (
            "https://www.giustizia.it/giustizia/page/it/"
            "concorsi_esami_selezioni_assunzioni?all=true&viewcat=csce_tipologia1"
        ),
        "region": None,
        "organization": "Ministero della Giustizia",
        "import_method": "public-institution-detail",
        "technical_notes": (
            "Indice nazionale ufficiale del Ministero della Giustizia. Non include "
            "il portale del Dipartimento dell'Amministrazione Penitenziaria, "
            "escluso dal perimetro della fonte."
        ),
    },
    {
        "name": "Ministero per la Famiglia - Avvisi e opportunita",
        "source_type": "public-institution-html",
        "base_url": "https://www.famiglia.governo.it/it/",
        "region": None,
        "organization": "Ministero per la Famiglia",
        "import_method": "public-institution-detail",
        "technical_notes": (
            "Sito ufficiale del Ministero per la Famiglia; l'adapter cerca avvisi, "
            "selezioni e opportunita professionali pertinenti."
        ),
    },
    {
        "name": "Ministero dell'Universita e della Ricerca - Concorsi e avvisi",
        "source_type": "public-institution-html",
        "base_url": "https://www.mur.gov.it/it/ministero/concorsi-e-avvisi",
        "region": None,
        "organization": "Ministero dell'Universita e della Ricerca",
        "import_method": "public-institution-detail",
        "technical_notes": (
            "Pagina ufficiale MUR per concorsi e avvisi, con rimando alle schede "
            "e ai documenti originali."
        ),
    },
    {
        "name": "Ministero dell'Universita e della Ricerca - CONCORSIMUR",
        "source_type": "public-institution-html",
        "base_url": "https://concorsi.mur.gov.it/",
        "region": None,
        "organization": "Ministero dell'Universita e della Ricerca",
        "import_method": "public-institution-detail",
        "technical_notes": (
            "Portale ufficiale CONCORSIMUR per le procedure concorsuali del MUR."
        ),
    },
]


_USR_SOURCES = (
    ("Abruzzo", "https://www.mim.gov.it/web/abruzzo"),
    ("Basilicata", "https://www.mim.gov.it/web/basilicata"),
    ("Calabria", "https://www.istruzione.calabria.it/"),
    ("Campania", "https://www.miur.gov.it/web/miur-usr-campania"),
    ("Emilia-Romagna", "https://www.istruzioneer.gov.it/"),
    ("Friuli-Venezia Giulia", "https://usrfvg.gov.it/it/home/index.html"),
    ("Lazio", "https://www.ufficioscolasticoregionalelazio.it/"),
    ("Liguria", "https://www.istruzioneliguria.it/"),
    ("Lombardia", "https://www.mim.gov.it/web/usr-lombardia/home"),
    ("Marche", "https://www.miur.gov.it/web/miur-usr-marche/"),
    ("Molise", "https://www.mim.gov.it/web/molise"),
    ("Piemonte", "https://www.istruzionepiemonte.it/"),
    ("Puglia", "https://www.pugliausr.gov.it/"),
    ("Sardegna", "https://www.mim.gov.it/web/usr-sardegna"),
    ("Sicilia", "https://www.usr.sicilia.it/"),
    ("Toscana", "https://www.miur.gov.it/web/miur-usr-toscana"),
    ("Umbria", "https://istruzione.umbria.it/"),
    ("Veneto", "https://istruzioneveneto.gov.it/"),
)

PUBLIC_INSTITUTION_SOURCE_DEFINITIONS.extend(
    {
        "name": f"Ufficio Scolastico Regionale {region}",
        "source_type": "public-institution-html",
        "base_url": base_url,
        "region": region,
        "organization": f"Ministero dell'Istruzione e del Merito - USR {region}",
        "import_method": "usr-public-list-detail",
        "technical_notes": (
            "Fonte ufficiale dell'Ufficio Scolastico Regionale, ricavata dalla "
            "directory MIM. L'adapter segue le pagine di concorsi, incarichi e "
            "selezioni e mantiene il collegamento alla scheda originale."
        ),
    }
    for region, base_url in _USR_SOURCES
)


PUBLIC_INSTITUTION_SOURCE_NAMES = {
    definition["name"] for definition in PUBLIC_INSTITUTION_SOURCE_DEFINITIONS
}

USR_SOURCE_NAMES = {
    definition["name"]
    for definition in PUBLIC_INSTITUTION_SOURCE_DEFINITIONS
    if definition["name"].startswith("Ufficio Scolastico Regionale ")
}
