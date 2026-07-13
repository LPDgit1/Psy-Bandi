from __future__ import annotations

# Territorial health organizations only. Hospital trusts can be added later.
CENTRAL_HEALTH_SOURCE_DEFINITIONS = [
    {
        "name": "AUSL Romagna - Bandi di concorso e avvisi",
        "source_type": "public-json-api",
        "base_url": (
            "https://www.auslromagna.it/pubblicita-legale/"
            "selezioni-del-personale/concorsi-selezioni-romagna"
        ),
        "region": "Emilia-Romagna",
        "organization": "AUSL Romagna",
        "import_method": "public-json-api-recent-pages",
        "technical_notes": (
            "Adapter attivo sui feed JSON pubblici delle categorie di selezione. "
            "Scansiona pagine recenti e apre solo dettagli psicologici espliciti."
        ),
    },
    {
        "name": "AST Pesaro Urbino - Concorsi",
        "source_type": "nextjs-public-list",
        "base_url": "https://www.astpu.marche.it/ast-comunica/concorsi",
        "region": "Marche",
        "organization": "AST Pesaro Urbino",
        "import_method": "nextjs-public-list-pending-adapter",
        "technical_notes": "Nuovo sito AST ufficiale attivo dal 18 settembre 2025.",
    },
    {
        "name": "AST Ancona - Concorsi",
        "source_type": "nextjs-public-list",
        "base_url": "https://www.astancona.marche.it/ast-comunica/concorsi",
        "region": "Marche",
        "organization": "AST Ancona",
        "import_method": "nextjs-public-list-pending-adapter",
        "technical_notes": "Nuovo sito AST ufficiale attivo dal 18 settembre 2025.",
    },
    {
        "name": "AST Macerata - Concorsi",
        "source_type": "nextjs-public-list",
        "base_url": "https://www.astmc.marche.it/ast-comunica/concorsi",
        "region": "Marche",
        "organization": "AST Macerata",
        "import_method": "nextjs-public-list-pending-adapter",
        "technical_notes": (
            "Nuovo sito AST ufficiale attivo dal 18 settembre 2025. La lista "
            "server-rendered include gia procedure psicologiche."
        ),
    },
    {
        "name": "AST Fermo - Concorsi",
        "source_type": "nextjs-public-list",
        "base_url": "https://www.astfm.marche.it/ast-comunica/concorsi",
        "region": "Marche",
        "organization": "AST Fermo",
        "import_method": "nextjs-public-list-pending-adapter",
        "technical_notes": "Nuovo sito AST ufficiale attivo dal 18 settembre 2025.",
    },
    {
        "name": "AST Ascoli Piceno - Concorsi",
        "source_type": "nextjs-public-list",
        "base_url": "https://www.astap.marche.it/ast-comunica/concorsi",
        "region": "Marche",
        "organization": "AST Ascoli Piceno",
        "import_method": "nextjs-public-list-pending-adapter",
        "technical_notes": "Nuovo sito AST ufficiale attivo dal 18 settembre 2025.",
    },
    {
        "name": "USL Umbria 1 - Bandi di concorso",
        "source_type": "wordpress-html-hub",
        "base_url": (
            "https://www.uslumbria1.it/per-gli-operatori-della-sanita/"
            "concorsi-e-mobilita/"
        ),
        "region": "Umbria",
        "organization": "USL Umbria 1",
        "import_method": "wordpress-html-hub-pending-adapter",
        "technical_notes": (
            "Hub pubblico raggiungibile e consentito da robots.txt. Collega le "
            "sottosezioni WordPress concorsi, avvisi e specialistica ambulatoriale."
        ),
    },
    {
        "name": "USL Umbria 2 - Bandi di concorso",
        "source_type": "html-table",
        "base_url": "https://www.uslumbria2.it/pagine/concorsi-001",
        "region": "Umbria",
        "organization": "USL Umbria 2",
        "import_method": "html-table-sections",
        "technical_notes": (
            "Adapter attivo sulle tabelle HTML pubbliche delle selezioni. Apre "
            "solo i dettagli dei profili psicologici espliciti."
        ),
    },
]
