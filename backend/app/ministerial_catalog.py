from __future__ import annotations

MINISTERIAL_SOURCE_DEFINITIONS = [
    {
        "name": "Ministero dell'Interno - Bandi di concorso",
        "source_type": "ministerial-html-hub",
        "base_url": "https://www.interno.gov.it/it/amministrazione-trasparente/bandi-concorso",
        "region": None,
        "organization": "Ministero dell'Interno",
        "import_method": "ministerial-html-detail",
        "technical_notes": (
            "Hub ufficiale del Ministero dell'Interno. L'adapter segue le schede "
            "che richiamano profili psicologici e mantiene il rimando alla pagina "
            "originale; i bandi di Polizia e Vigili del Fuoco sono letti dai rispettivi "
            "portali dedicati."
        ),
    },
    {
        "name": "Polizia di Stato - Concorsi",
        "source_type": "ministerial-html-hub",
        "base_url": "https://www.poliziadistato.it/articolo/1129",
        "region": None,
        "organization": "Polizia di Stato",
        "import_method": "ministerial-html-detail",
        "technical_notes": (
            "Pagina ufficiale dei concorsi della Polizia di Stato, con filtro "
            "stretto sui profili psicologici. Se il portale presenta una sfida "
            "anti-bot l'adapter registra il mancato accesso senza aggirarla."
        ),
    },
    {
        "name": "Vigili del Fuoco - Concorsi pubblici",
        "source_type": "ministerial-html-hub",
        "base_url": "https://www.vigilfuoco.it/servizi-ai-cittadini/concorsi-pubblici",
        "region": None,
        "organization": "Corpo Nazionale dei Vigili del Fuoco",
        "import_method": "ministerial-html-detail",
        "technical_notes": (
            "Indice ufficiale dei concorsi pubblici dei Vigili del Fuoco; l'adapter "
            "segue anche le schede per vice direttore tecnico-scientifico psicologo."
        ),
    },
    {
        "name": "Ministero della Difesa - Concorsi Online",
        "source_type": "ministerial-html-hub",
        "base_url": "https://concorsi.difesa.it/default.aspx/ei/",
        "region": None,
        "organization": "Ministero della Difesa",
        "import_method": "ministerial-html-detail",
        "technical_notes": (
            "Portale ufficiale Concorsi Online della Difesa per Esercito, Marina e "
            "Aeronautica. Il portale e dinamico: l'adapter usa solo contenuti HTML "
            "pubblicamente esposti e conserva il link ufficiale."
        ),
    },
    {
        "name": "Ministero della Difesa - Concorsi per ufficiali (PERSOMIL)",
        "source_type": "ministerial-html-hub",
        "base_url": "https://www.difesa.it/amministrazione-trasparente/bandiconcorsopersomil/concorsi/uff/index.html",
        "region": None,
        "organization": "Ministero della Difesa - PERSOMIL",
        "import_method": "ministerial-html-detail",
        "technical_notes": (
            "Indice ufficiale PERSOMIL dei concorsi per ufficiali, inclusi i "
            "concorsi del Corpo sanitario e i profili psicologi."
        ),
    },
    {
        "name": "Ministero del Lavoro - Notizie concorsi e avvisi",
        "source_type": "html-list",
        "base_url": "https://www.lavoro.gov.it/notizie/Pagine/Notizie?search=concorsi",
        "region": None,
        "organization": "Ministero del Lavoro e delle Politiche Sociali",
        "import_method": "html-list-search",
        "technical_notes": (
            "Pagina ufficiale notizie filtrata sui concorsi. Da usare con filtro "
            "professionale psicologico stretto e deduplicazione con inPA."
        ),
    },
    {
        "name": "Ministero dell'Istruzione e del Merito - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.mim.gov.it/web/guest/bandi-di-concorso",
        "region": None,
        "organization": "Ministero dell'Istruzione e del Merito",
        "import_method": "html-list-search",
        "technical_notes": (
            "Pagina ufficiale MIM dei bandi di concorso. Rilevante per psicologi "
            "scolastici, orientamento, inclusione e supporto studenti."
        ),
    },
    {
        "name": "MAECI - Lavora con noi e opportunita",
        "source_type": "ministerial-access-review",
        "base_url": "https://www.esteri.it/it/trasparenza_comunicazioni_legali/bandi_di_concorso/",
        "region": None,
        "organization": "Ministero degli Affari Esteri e della Cooperazione Internazionale",
        "import_method": "ministerial-access-review",
        "technical_notes": (
            "Fonte ufficiale MAECI per bandi di concorso. Il dominio presenta "
            "protezione anti-bot Radware: resta catalogato per consultazione, mentre "
            "il recupero automatico usa la scansione completa dei bandi OPEN di inPA."
        ),
    },
]
