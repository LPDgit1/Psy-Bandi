from __future__ import annotations

# Territorial health organizations only. Hospital trusts and research hospitals
# can be added in a later pass without changing this catalog boundary.
NORTHERN_HEALTH_SOURCE_DEFINITIONS = [
    {
        "name": "Azienda Zero Piemonte - Concorsi pubblici",
        "source_type": "html-list",
        "base_url": (
            "https://www.aziendazero.piemonte.it/concorsiaz0/concorsi-pubblici/"
        ),
        "region": "Piemonte",
        "organization": "Azienda Sanitaria Zero Piemonte",
        "import_method": "html-list-paginated",
        "technical_notes": (
            "Adapter attivo sulle sezioni pubbliche WordPress e sulla paginazione. "
            "Filtra i profili psicologici e deduplica con inPA."
        ),
    },
    {
        "name": "ASL AL - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.aslal.it/bandi-di-concorso",
        "region": "Piemonte",
        "organization": "ASL AL",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Elenco pubblico diretto dell'azienda sanitaria.",
    },
    {
        "name": "ASL AT - Concorsi in vigore",
        "source_type": "xml-index",
        "base_url": "https://trasparenza.asl.at.it/DL33/concorsiinvigore.xml",
        "region": "Piemonte",
        "organization": "ASL AT",
        "import_method": "xml-index-pending-adapter",
        "technical_notes": (
            "Indice XML pubblico di Amministrazione Trasparente. Valutare un "
            "adapter riusabile per portali DL33."
        ),
    },
    {
        "name": "ASL CN1 - Concorsi pubblici e avvisi",
        "source_type": "html-list",
        "base_url": (
            "https://www.aslcn1.it/amministrazione-trasparente/"
            "bandi-di-concorso/concorsi-pubblici-e-avvisi"
        ),
        "region": "Piemonte",
        "organization": "ASL CN1",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Elenco pubblico diretto dell'azienda sanitaria.",
    },
    {
        "name": "ASL CN2 - Bandi di concorso",
        "source_type": "html-hub",
        "base_url": (
            "https://www.aslcn2.it/azienda-asl-cn2/amministrazione-trasparente/"
            "bandi-di-concorso/"
        ),
        "region": "Piemonte",
        "organization": "ASL CN2",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Hub pubblico diretto dell'azienda sanitaria.",
    },
    {
        "name": "ASL NO - Portale concorsi",
        "source_type": "html-list",
        "base_url": "https://concorsi.asl.novara.it/",
        "region": "Piemonte",
        "organization": "ASL NO",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Portale pubblico dedicato ai concorsi dell'azienda sanitaria.",
    },
    {
        "name": "ASL Citta di Torino - Concorsi pubblici",
        "source_type": "html-list",
        "base_url": "https://www.aslcittaditorino.it/concorsi-pubblici/",
        "region": "Piemonte",
        "organization": "ASL Citta di Torino",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Elenco pubblico diretto dell'azienda sanitaria.",
    },
    {
        "name": "ASL TO3 - Portale trasparenza",
        "source_type": "external-transparency",
        "base_url": (
            "https://trasparenzaap.aslto3.piemonte.it/web/trasparenza/trasparenza"
        ),
        "region": "Piemonte",
        "organization": "ASL TO3",
        "import_method": "external-transparency-pending-tls-review",
        "technical_notes": (
            "Portale pubblico collegato dal sito aziendale. Dal container la "
            "catena TLS remota risulta incompleta: mantenere lo stato tls-review "
            "senza disabilitare la verifica dei certificati."
        ),
    },
    {
        "name": "ASL TO4 - Concorsi",
        "source_type": "html-list",
        "base_url": "https://www.aslto4.piemonte.it/concorsi/",
        "region": "Piemonte",
        "organization": "ASL TO4",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Elenco pubblico diretto dell'azienda sanitaria.",
    },
    {
        "name": "ASL TO5 - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.aslto5.piemonte.it/it/trasparenza/bandi-concorso",
        "region": "Piemonte",
        "organization": "ASL TO5",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Elenco pubblico diretto dell'azienda sanitaria.",
    },
    {
        "name": "ASL VC - Concorsi",
        "source_type": "html-list",
        "base_url": "https://aslvc.piemonte.it/albo-pretorio/concorsi/",
        "region": "Piemonte",
        "organization": "ASL VC",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Elenco pubblico diretto dell'azienda sanitaria.",
    },
    {
        "name": "ASL VCO - Concorsi e selezioni",
        "source_type": "html-list",
        "base_url": "https://www.aslvco.it/lasl-informa/concorsi-e-selezioni/",
        "region": "Piemonte",
        "organization": "ASL VCO",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Elenco pubblico diretto dell'azienda sanitaria.",
    },
    {
        "name": "ATS Liguria - Bandi di concorso",
        "source_type": "regional-html-hub",
        "base_url": (
            "https://www.atsliguria.it/amministrazione-trasparente-ats/"
            "amministrazione-trasparente/bandi-di-concorso.html"
        ),
        "region": "Liguria",
        "organization": "ATS Liguria",
        "import_method": "regional-html-hub-pending-adapter",
        "technical_notes": (
            "Hub corrente dell'azienda regionale nata il 1 gennaio 2026 dalla "
            "fusione delle cinque ASL liguri e Liguria Salute. Durante la verifica "
            "il DNS del container ha avuto una anomalia transitoria, poi risolta: "
            "mantenere il monitoraggio prima di sviluppare l'adapter."
        ),
    },
    {
        "name": "Regione Lombardia - Concorsi e avvisi enti sanitari",
        "source_type": "regional-html-hub",
        "base_url": (
            "https://www.regione.lombardia.it/sanita/"
            "personale-sanitario-e-sociosanitario/"
            "concorsi-e-avvisi-presso-enti-sanitari/"
            "concorsi-e-avvisi-presso-enti-sanitari"
        ),
        "region": "Lombardia",
        "organization": "Regione Lombardia",
        "import_method": "regional-html-hub-pending-adapter",
        "technical_notes": (
            "Pagina SSR pubblica con riepiloghi periodici di concorsi, avvisi, "
            "mobilita, incarichi e supplenze degli enti sanitari lombardi."
        ),
    },
    {
        "name": "ATS Milano - Concorsi e avvisi",
        "source_type": "html-list",
        "base_url": "https://www.ats-milano.it/ats/concorsi-avvisi",
        "region": "Lombardia",
        "organization": "ATS Milano",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica Lavora con noi con concorsi e avvisi.",
    },
    {
        "name": "ATS Insubria - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.ats-insubria.it/amministrazione-trasparente/bandi-di-concorso",
        "region": "Lombardia",
        "organization": "ATS Insubria",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Sezione pubblica Amministrazione Trasparente.",
    },
    {
        "name": "ATS Brianza - Concorsi",
        "source_type": "html-list",
        "base_url": (
            "https://www.ats-brianza.it/concorsi?template=-1&mnuitem=0&"
            "itmlayout=default&umnulist=1331&umnuedit=2078&umnuitem=2077"
        ),
        "region": "Lombardia",
        "organization": "ATS Brianza",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica concorsi del sito ATS.",
    },
    {
        "name": "ATS Brescia - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.ats-brescia.it/concorsi",
        "region": "Lombardia",
        "organization": "ATS Brescia",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica bandi di concorso.",
    },
    {
        "name": "ATS Bergamo - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.ats-bg.it/concorsi",
        "region": "Lombardia",
        "organization": "ATS Bergamo",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica bandi di concorso.",
    },
    {
        "name": "ATS Montagna - Concorsi e avvisi pubblici",
        "source_type": "external-transparency",
        "base_url": (
            "https://albopretorio.ats-montagna.it/web/trasparenza/"
            "dettaglio-trasparenza?p_p_id="
            "jcitygovmenutrasversaleleftcolumn_WAR_jcitygovalbiportlet&"
            "p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&p_p_col_id=column-2&"
            "p_p_col_count=1&_jcitygovmenutrasversaleleftcolumn_WAR_"
            "jcitygovalbiportlet_current-page-parent=0&"
            "_jcitygovmenutrasversaleleftcolumn_WAR_"
            "jcitygovalbiportlet_current-page=224"
        ),
        "region": "Lombardia",
        "organization": "ATS Montagna",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Portale pubblico Amministrazione Trasparente.",
    },
    {
        "name": "ATS Val Padana - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.ats-valpadana.it/concorsi",
        "region": "Lombardia",
        "organization": "ATS Val Padana",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica bandi di concorso.",
    },
    {
        "name": "ATS Pavia - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.ats-pavia.it/amministrazione-trasparente/bandi-di-concorso",
        "region": "Lombardia",
        "organization": "ATS Pavia",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Sezione pubblica Amministrazione Trasparente.",
    },
    {
        "name": "Regione Emilia-Romagna - Bandi concorsi e avvisi sanita",
        "source_type": "regional-html-hub",
        "base_url": (
            "https://salute.regione.emilia-romagna.it/trasparenza/"
            "bandi-concorsi-e-avvisi"
        ),
        "region": "Emilia-Romagna",
        "organization": "Regione Emilia-Romagna",
        "import_method": "regional-html-hub-pending-adapter",
        "technical_notes": (
            "Hub sanitario regionale pubblico con collegamenti alle aziende Usl "
            "territoriali e alle altre aziende del servizio sanitario."
        ),
    },
    {
        "name": "ARCS FVG - Concorsi avvisi incarichi",
        "source_type": "regional-html-hub",
        "base_url": (
            "https://arcs.sanita.fvg.it/it/professionisti-e-fornitori/"
            "concorsi-avvisi-incarichi/concorsi-e-avvisi"
        ),
        "region": "Friuli-Venezia Giulia",
        "organization": "ARCS Friuli-Venezia Giulia",
        "import_method": "html-list-detail",
        "technical_notes": (
            "Adapter attivo sulla lista pubblica Drupal. Apre il dettaglio solo "
            "per profili psicologici espliciti; copre anche ASUFC, ASUGI e ASFO."
        ),
    },
    {
        "name": "ASUIT Trentino - Lavora con noi",
        "source_type": "html-list-detail",
        "base_url": "https://www.asuit.tn.it/bandi-concorsi?combine=psicolog",
        "region": "Trentino-Alto Adige",
        "organization": "ASUIT Trentino",
        "import_method": "html-list-detail-filtered",
        "technical_notes": (
            "Adapter attivo sulla lista Drupal pubblica filtrata per psicolog. "
            "Apre il dettaglio solo per profili psicologici espliciti."
        ),
    },
    {
        "name": "ASDAA Alto Adige - Bandi di concorso",
        "source_type": "html-list",
        "base_url": (
            "https://home.asdaa.it/it/amministrazione-trasparente/"
            "info-concorsi.asp"
        ),
        "region": "Trentino-Alto Adige",
        "organization": "Azienda Sanitaria dell'Alto Adige",
        "import_method": "html-table-metadata-only",
        "technical_notes": (
            "Adapter attivo sulla tabella consentita da robots.txt. Importa solo "
            "metadati e non visita i documenti dell'area /cv/ esclusa."
        ),
    },
    {
        "name": "USL Valle d'Aosta - Concorsi e selezioni",
        "source_type": "html-list",
        "base_url": (
            "https://www.ausl.vda.it/concorsi-e-selezioni/concorsi-e-selezioni"
        ),
        "region": "Valle d'Aosta",
        "organization": "Azienda USL Valle d'Aosta",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Elenco pubblico diretto dell'azienda sanitaria regionale.",
    },
]
