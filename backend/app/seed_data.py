from __future__ import annotations

SAMPLE_SOURCE = {
    "name": "Fonte demo aggregata",
    "source_type": "fixture",
    "base_url": "https://example.test/fonti/demo",
    "region": None,
    "organization": "Demo",
    "import_method": "fixture",
    "refresh_frequency": "manual",
}

SAMPLE_OPPORTUNITIES = [
    {
        "external_id": "demo-001",
        "title": "Avviso pubblico per psicologo nei servizi tutela minori",
        "description": (
            "Procedura comparativa per incarico libero professionale di psicologo "
            "a supporto del servizio tutela minori e famiglia. Richiesta iscrizione "
            "all'albo degli psicologi ed esperienza almeno biennale con minori."
        ),
        "organization": "Comune di Frosinone",
        "entity_type": "comune",
        "region": "Lazio",
        "province": "FR",
        "municipality": "Frosinone",
        "published_at": "2026-05-20",
        "deadline": "2026-06-18",
        "positions": 1,
        "compensation_max": 18000,
        "compensation_period": "forfait",
        "duration": "12 mesi",
        "contract_type": "incarico libero-professionale",
        "official_url": "https://example.test/comune-frosinone/avviso-psicologo-minori",
    },
    {
        "external_id": "demo-002",
        "title": "Concorso pubblico per dirigente psicologo disciplina psicoterapia",
        "description": (
            "Concorso pubblico per titoli ed esami per dirigente psicologo. "
            "Sono richieste laurea in psicologia, abilitazione, iscrizione all'albo "
            "e specializzazione in psicoterapia."
        ),
        "organization": "Azienda Sanitaria Locale Roma 2",
        "entity_type": "azienda-sanitaria-ospedaliera",
        "region": "Lazio",
        "province": "RM",
        "municipality": "Roma",
        "published_at": "2026-05-16",
        "deadline": "2026-06-28",
        "positions": 2,
        "contract_type": "tempo indeterminato",
        "official_url": "https://example.test/asl-roma-2/concorso-dirigente-psicologo",
    },
    {
        "external_id": "demo-003",
        "title": "Borsa di ricerca in neuropsicologia dell'invecchiamento",
        "description": (
            "Selezione per borsa di ricerca su disturbi cognitivi, demenza e "
            "riabilitazione cognitiva. Titolo preferenziale: esperienza in "
            "valutazione neuropsicologica."
        ),
        "organization": "Universita degli Studi di Padova",
        "entity_type": "universita",
        "region": "Veneto",
        "province": "PD",
        "municipality": "Padova",
        "published_at": "2026-05-21",
        "deadline": "2026-06-12",
        "positions": 1,
        "compensation_max": 12000,
        "compensation_period": "forfait",
        "duration": "10 mesi",
        "contract_type": "borsa di ricerca",
        "official_url": "https://example.test/unipd/borsa-neuropsicologia",
    },
    {
        "external_id": "demo-004",
        "title": "Manifestazione di interesse per sportello ascolto scolastico",
        "description": (
            "Manifestazione di interesse per esperti esterni psicologi da impiegare "
            "in sportello ascolto scolastico rivolto a studenti, famiglie e docenti. "
            "Richiesta iscrizione all'albo professionale degli psicologi."
        ),
        "organization": "Istituto Comprensivo Statale Galileo",
        "entity_type": "scuola-istituto-scolastico",
        "region": "Lombardia",
        "province": "MI",
        "municipality": "Milano",
        "published_at": "2026-05-18",
        "deadline": "2026-06-06",
        "positions": 1,
        "compensation_max": 3200,
        "compensation_period": "forfait",
        "duration": "anno scolastico 2026/2027",
        "contract_type": "collaborazione",
        "official_url": "https://example.test/ic-galileo/sportello-ascolto",
    },
    {
        "external_id": "demo-005",
        "title": "Avviso per psicologo esperto in dipendenze presso SERD",
        "description": (
            "Avviso pubblico per il conferimento di incarico a psicologo con "
            "esperienza nel trattamento delle dipendenze patologiche presso SERD. "
            "Richiesta laurea in psicologia e iscrizione albo."
        ),
        "organization": "ASP Palermo",
        "entity_type": "azienda-sanitaria-ospedaliera",
        "region": "Sicilia",
        "province": "PA",
        "municipality": "Palermo",
        "published_at": "2026-05-24",
        "deadline": "2026-07-02",
        "positions": 1,
        "duration": "24 mesi",
        "contract_type": "incarico libero-professionale",
        "official_url": "https://example.test/asp-palermo/psicologo-serd",
    },
    {
        "external_id": "demo-006",
        "title": "Selezione consulente orientamento e bilancio competenze",
        "description": (
            "Procedura comparativa per consulente esperto in orientamento, bilancio "
            "competenze e supporto psicologico per percorsi di inclusione lavorativa."
        ),
        "organization": "Agenzia Regionale Lavoro Emilia-Romagna",
        "entity_type": "regione-ente-regionale",
        "region": "Emilia-Romagna",
        "province": "BO",
        "municipality": "Bologna",
        "published_at": "2026-05-25",
        "deadline": "2026-06-25",
        "positions": 3,
        "contract_type": "collaborazione-consulenza",
        "official_url": "https://example.test/arl-er/orientamento-psicologico",
    },
]

