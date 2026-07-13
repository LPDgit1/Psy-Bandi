from __future__ import annotations

MINISTERIAL_SOURCE_DEFINITIONS = [
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
