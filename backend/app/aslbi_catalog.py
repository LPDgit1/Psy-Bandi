from __future__ import annotations


ASL_BI_SOURCE_DEFINITIONS = [
    {
        "name": "ASL BI - Bandi concorso reclutamento personale",
        "source_type": "aslbi-csv",
        "base_url": (
            "https://trasparenza.aslbi.piemonte.it/"
            "bandi-concorso-reclutamento-personale?sf=102"
        ),
        "region": "Piemonte",
        "organization": "ASL BI",
        "import_method": "aslbi-csv-export",
        "technical_notes": (
            "Adapter dedicato ai due export CSV ufficiali della pagina di "
            "trasparenza (bandi espletati e procedure selettive). Prima di ogni "
            "richiesta verifica robots.txt; in caso di divieto o risposta non "
            "testuale la fonte resta registrata e l'errore viene tracciato senza "
            "aggirare le regole del sito."
        ),
    },
]
