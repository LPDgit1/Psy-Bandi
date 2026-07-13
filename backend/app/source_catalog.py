from __future__ import annotations

from app.central_health_catalog import CENTRAL_HEALTH_SOURCE_DEFINITIONS
from app.hospital_health_catalog import HOSPITAL_HEALTH_SOURCE_DEFINITIONS
from app.ministerial_catalog import MINISTERIAL_SOURCE_DEFINITIONS
from app.national_health_catalog import NATIONAL_HEALTH_SOURCE_DEFINITIONS
from app.northern_health_catalog import NORTHERN_HEALTH_SOURCE_DEFINITIONS
from app.puglia_aol_catalog import PUGLIA_AOL_SOURCE_DEFINITIONS
from app.target_health_catalog import TARGET_HEALTH_SOURCE_DEFINITIONS

PUBLIC_SOURCE_NOTE = (
    "Accesso pubblico istituzionale. Prima dell'adapter verificare robots.txt e "
    "termini d'uso; usare frequenza moderata e rimando al documento originale."
)
OPEN_SOCIAL_SOURCE_NOTE = (
    "Fonte pubblicamente consultabile, non necessariamente istituzionale. Prima "
    "dell'adapter verificare robots.txt, termini d'uso e opportunita di includere "
    "solo riferimenti essenziali con rimando alla pagina originale."
)


def _source(
    *,
    name: str,
    source_type: str,
    base_url: str,
    region: str | None,
    organization: str,
    import_method: str,
    technical_notes: str,
    access_note: str = PUBLIC_SOURCE_NOTE,
) -> dict[str, str | None]:
    return {
        "name": name,
        "source_type": source_type,
        "base_url": base_url,
        "region": region,
        "organization": organization,
        "import_method": import_method,
        "refresh_frequency": "daily",
        "technical_notes": f"{technical_notes} {access_note}",
    }


VERIFIED_SOURCE_CATALOG = [
    _source(
        name="Gazzetta Ufficiale - 4a Serie Speciale Concorsi ed Esami",
        source_type="html-pdf-index",
        base_url="https://www.gazzettaufficiale.it/30giorni/concorsi",
        region=None,
        organization="Istituto Poligrafico e Zecca dello Stato",
        import_method="html-pdf-index-pending-adapter",
        technical_notes=(
            "Indice ufficiale degli ultimi 30 giorni. Fonte di controllo nazionale "
            "e discovery, con estratti minimi e link alla pubblicazione."
        ),
    ),
    _source(
        name="INAIL - Avvisi",
        source_type="html-archive",
        base_url="https://www.inail.it/portale/it/inail-comunica/avvisi.html",
        region=None,
        organization="INAIL",
        import_method="html-archive-recent-pages",
        technical_notes=(
            "Adapter attivo sull'archivio pubblico generale degli avvisi. Legge "
            "soltanto poche pagine recenti e filtra i profili psicologici espliciti. "
            "Non usa le sezioni Amministrazione Trasparente escluse da robots.txt."
        ),
    ),
    _source(
        name="INPS - Concorsi e mobilita",
        source_type="public-json-api",
        base_url=(
            "https://www.inps.it/it/it/avvisi-bandi-e-fatturazione/"
            "fatturazione-concorsi.html"
        ),
        region=None,
        organization="INPS",
        import_method="public-json-api",
        technical_notes=(
            "Adapter attivo sull'endpoint JSON pubblico richiamato dalla lista "
            "ufficiale Concorsi e Mobilita. Interroga soltanto filtri professionali "
            "psicologici e conserva il link alla scheda INPS."
        ),
    ),
    _source(
        name="Regione Veneto - Concorsi in Veneto",
        source_type="html-index",
        base_url="https://concorsi.regione.veneto.it/",
        region="Veneto",
        organization="Regione del Veneto",
        import_method="html-index-pending-adapter",
        technical_notes=(
            "Indice pubblico curato dagli URP regionali e aggiornato settimanalmente. "
            "Utile per discovery di enti veneti; il portale dichiara copertura non esaustiva."
        ),
    ),
    _source(
        name="Regione Veneto - Bandi Avvisi Concorsi",
        source_type="html-index",
        base_url="https://bandi.regione.veneto.it/",
        region="Veneto",
        organization="Regione del Veneto",
        import_method="html-index-pending-adapter",
        technical_notes=(
            "Portale pubblico regionale con scadenzario e ricerca avanzata. "
            "Candidato per adapter dedicato e deduplicazione con inPA."
        ),
    ),
    _source(
        name="Regione Piemonte - Concorsi incarichi e stage",
        source_type="html-index",
        base_url="https://bandi.regione.piemonte.it/concorsi-incarichi-stage",
        region="Piemonte",
        organization="Regione Piemonte",
        import_method="html-index-pending-adapter",
        technical_notes="Portale pubblico regionale per concorsi, incarichi e stage.",
    ),
    _source(
        name="Regione Liguria - Bandi e avvisi",
        source_type="html-index",
        base_url="https://www.regione.liguria.it/homepage-bandi-e-avvisi.html",
        region="Liguria",
        organization="Regione Liguria",
        import_method="html-index-pending-adapter",
        technical_notes="Portale pubblico regionale bandi e avvisi.",
    ),
    _source(
        name="Regione Toscana - Concorsi",
        source_type="html-index",
        base_url="https://www.regione.toscana.it/-/concorsi",
        region="Toscana",
        organization="Regione Toscana",
        import_method="html-index-pending-adapter",
        technical_notes="Pagina pubblica regionale dei concorsi.",
    ),
    _source(
        name="Regione Marche - Concorsi",
        source_type="html-index",
        base_url="https://www.regione.marche.it/Entra-in-Regione/Concorsi",
        region="Marche",
        organization="Regione Marche",
        import_method="html-index-pending-adapter",
        technical_notes="Pagina pubblica regionale dei concorsi.",
    ),
    _source(
        name="Regione Abruzzo - Concorsi",
        source_type="html-index",
        base_url="https://www2.regione.abruzzo.it/content/concorsi",
        region="Abruzzo",
        organization="Regione Abruzzo",
        import_method="html-index-pending-adapter",
        technical_notes="Pagina pubblica regionale dei concorsi.",
    ),
    _source(
        name="Regione Puglia - Bandi e avvisi",
        source_type="html-index",
        base_url="https://www.regione.puglia.it/web/guest/bandi-e-avvisi",
        region="Puglia",
        organization="Regione Puglia",
        import_method="html-index-pending-adapter",
        technical_notes="Portale pubblico regionale bandi e avvisi.",
    ),
    _source(
        name="Regione Sardegna - Bandi",
        source_type="html-index",
        base_url=(
            "https://www.regione.sardegna.it/atti-bandi-archivi/"
            "atti-amministrativi/bandi"
        ),
        region="Sardegna",
        organization="Regione Autonoma della Sardegna",
        import_method="html-index-pending-adapter",
        technical_notes="Portale pubblico regionale atti, bandi e archivi.",
    ),
    _source(
        name="Regione Siciliana - Bandi",
        source_type="html-index",
        base_url="https://www.regione.sicilia.it/istituzioni/servizi-informativi/bandi",
        region="Sicilia",
        organization="Regione Siciliana",
        import_method="html-index-pending-adapter",
        technical_notes="Portale pubblico regionale dei bandi.",
    ),
    _source(
        name="Azienda Zero Veneto - Concorsi",
        source_type="public-json-api",
        base_url="https://www.azero.veneto.it/concorsi-e-avvisi",
        region="Veneto",
        organization="Azienda Zero - Regione del Veneto",
        import_method="public-json-api",
        technical_notes=(
            "Adapter attivo sull'endpoint JSON pubblico usato dall'interfaccia. "
            "Importa riferimenti essenziali agli allegati senza replicare i documenti."
        ),
    ),
    _source(
        name="ASL Roma 2 - Concorsi",
        source_type="html-table",
        base_url="https://www.aslroma2.it/external/concorsi/index.php",
        region="Lazio",
        organization="ASL Roma 2",
        import_method="html-table-post-filter",
        technical_notes=(
            "Adapter attivo sulla tabella pubblica con ricerca server-side. "
            "Importa riferimenti essenziali agli allegati senza replicare i documenti."
        ),
    ),
    _source(
        name="Comune di Venezia - Bandi di concorso",
        source_type="html-table",
        base_url="https://www.comune.venezia.it/node/6313",
        region="Veneto",
        organization="Comune di Venezia",
        import_method="html-table",
        technical_notes=(
            "Adapter attivo sulla tabella pubblica con procedure in scadenza, in "
            "corso e concluse. Molti bandi rimandano anche a inPA: deduplicazione "
            "obbligatoria."
        ),
    ),
    _source(
        name="Comune di Torino - Lavorare in Comune",
        source_type="html-hub",
        base_url="https://www.comune.torino.it/argomenti/comune/lavorare-comune",
        region="Piemonte",
        organization="Comune di Torino",
        import_method="html-hub-pending-adapter",
        technical_notes="Pagina pubblica del capoluogo regionale per concorsi e selezioni.",
    ),
    _source(
        name="Comune di Aosta - Bandi di concorso",
        source_type="html-list",
        base_url="https://trasparenza.partout.it/enti/AOSTA/bandi-concorso",
        region="Valle d'Aosta",
        organization="Comune di Aosta",
        import_method="html-list-pending-adapter",
        technical_notes="Pagina pubblica di Amministrazione Trasparente del capoluogo.",
    ),
    _source(
        name="Comune di Genova - Bandi di concorso",
        source_type="html-list",
        base_url="https://smart.comune.genova.it/contenuti/bandi-di-concorso",
        region="Liguria",
        organization="Comune di Genova",
        import_method="html-list-pending-adapter",
        technical_notes="Pagina pubblica con filtri, stati e schede dei concorsi.",
    ),
    _source(
        name="Comune di Trento - Concorsi in pubblicazione",
        source_type="html-list",
        base_url=(
            "https://www.comune.trento.it/Amministrazione-Trasparente/"
            "Bandi-di-concorso/Concorsi-in-pubblicazione2"
        ),
        region="Trentino-Alto Adige",
        organization="Comune di Trento",
        import_method="html-list-pending-adapter",
        technical_notes="Elenco pubblico dei concorsi in pubblicazione del capoluogo.",
    ),
    _source(
        name="Comune di Bolzano - Bandi di concorso",
        source_type="html-hub",
        base_url=(
            "https://www.comune.bolzano.bz.it/Amministrazione-Trasparente/"
            "Bandi-di-concorso"
        ),
        region="Trentino-Alto Adige",
        organization="Comune di Bolzano",
        import_method="html-hub-pending-adapter",
        technical_notes="Sezione pubblica di Amministrazione Trasparente del capoluogo.",
    ),
    _source(
        name="Comune di Firenze - Bandi di concorso",
        source_type="html-hub",
        base_url=(
            "https://amministrazionetrasparente.comune.firenze.it/pagina/"
            "amministrazione-trasparente/bandi-di-concorso"
        ),
        region="Toscana",
        organization="Comune di Firenze",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Hub pubblico con concorsi, selezioni esterne e graduatorie del "
            "capoluogo regionale."
        ),
    ),
    _source(
        name="Comune di Napoli - Bandi di concorso",
        source_type="html-list",
        base_url="https://trasparenza.comune.napoli.it/bandi-di-concorso",
        region="Campania",
        organization="Comune di Napoli",
        import_method="html-list-pending-adapter",
        technical_notes="Pagina pubblica di Amministrazione Trasparente del capoluogo.",
    ),
    _source(
        name="Comune di Bari - Bandi di concorso",
        source_type="html-list",
        base_url=(
            "https://trasparenza.comune.bari.it/comunebari/archivio/"
            "174894-bandi-di-concorso"
        ),
        region="Puglia",
        organization="Comune di Bari",
        import_method="html-list-pending-adapter",
        technical_notes="Archivio pubblico di Amministrazione Trasparente del capoluogo.",
    ),
    _source(
        name="Comune di Catanzaro - Concorsi attivi",
        source_type="html-list",
        base_url=(
            "https://old.comune.catanzaro.it/amm-trasparente/"
            "bandi-di-concorso/concorsi-attivi/"
        ),
        region="Calabria",
        organization="Comune di Catanzaro",
        import_method="html-list-pending-adapter",
        technical_notes="Pagina pubblica dei concorsi attivi del capoluogo regionale.",
    ),
    _source(
        name="Comune di Palermo - Bandi di concorso",
        source_type="html-list",
        base_url=(
            "https://repository.comune.palermo.it/"
            "amministrazione-trasparente.php?grp=3&id=5&lev=2"
        ),
        region="Sicilia",
        organization="Comune di Palermo",
        import_method="html-list-pending-adapter",
        technical_notes="Pagina pubblica di Amministrazione Trasparente del capoluogo.",
    ),
    _source(
        name="Comune di Belluno - Bandi di concorso",
        source_type="spa-external-link",
        base_url="https://www.comune.belluno.it/amministrazionetrasparente/_05_bandi_di_concorso",
        region="Veneto",
        organization="Comune di Belluno",
        import_method="external-page-pending-adapter",
        technical_notes=(
            "La sezione MyPortal pubblica rinvia alla pagina storica "
            "https://www.comune.belluno.it/amministrazione/attipubblicazioni/concorsi. "
            "Richiede un adapter separato della pagina collegata."
        ),
    ),
    _source(
        name="Comune di Padova - Bandi di concorso",
        source_type="html-hub",
        base_url="https://www.comune.padova.it/amministrazione-trasparente/bandi-di-concorso",
        region="Veneto",
        organization="Comune di Padova",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Hub pubblico con concorsi, mobilita e selezioni a tempo determinato. "
            "Richiede visita delle sottosezioni e deduplicazione con inPA."
        ),
    ),
    _source(
        name="Comune di Rovigo - Bandi di concorso",
        source_type="spa-external-link",
        base_url="https://www.comune.rovigo.it/amministrazionetrasparente/bandi-di-concorso",
        region="Veneto",
        organization="Comune di Rovigo",
        import_method="external-transparency-pending-adapter",
        technical_notes=(
            "La sezione MyPortal pubblica rinvia al portale trasparenza Liferay "
            "rovigo.trasparenza-valutazione-merito.it. Richiede un adapter separato."
        ),
    ),
    _source(
        name="Comune di Treviso - Bandi di concorso",
        source_type="public-json-api",
        base_url="https://www.comune.treviso.it/amministrazionetrasparente/_05_bandi_di_concorso",
        region="Veneto",
        organization="Comune di Treviso",
        import_method="myportal-public-json-api",
        technical_notes=(
            "Adapter attivo sul catalogo JSON pubblico MyPortal usato dalla SPA. "
            "Importa soltanto i riferimenti essenziali agli allegati."
        ),
    ),
    _source(
        name="Comune di Verona - Bandi di concorso",
        source_type="html-hub",
        base_url=(
            "https://www.comune.verona.it/"
            "Amministrazione-Trasparente/Bandi-di-concorso"
        ),
        region="Veneto",
        organization="Comune di Verona",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Sezione pubblica di Amministrazione Trasparente con categorie e "
            "schede di dettaglio. Preferire le pagine documento correnti."
        ),
    ),
    _source(
        name="Comune di Vicenza - Bandi di concorso",
        source_type="html-hub",
        base_url=(
            "https://servizi2.comune.vicenza.it/amministrazione/trasparente/"
            "cmsammtrasparente.php/bandi_di_concorso"
        ),
        region="Veneto",
        organization="Comune di Vicenza",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Pagina pubblica di Amministrazione Trasparente che rimanda all'elenco "
            "dei concorsi in corso. Richiede adapter della pagina collegata."
        ),
    ),
    _source(
        name="Roma Capitale - Bandi di concorso",
        source_type="html-hub",
        base_url=(
            "https://www.comune.roma.it/web/it/"
            "amministrazione-trasparente-bandi-di-concorso.page"
        ),
        region="Lazio",
        organization="Roma Capitale",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Pagina pubblica di Amministrazione Trasparente. Per i concorsi correnti "
            "rimanda anche al Portale del Reclutamento inPA; verificare deduplicazione."
        ),
    ),
    _source(
        name="Comune di Cagliari - Bandi di concorso",
        source_type="html-list",
        base_url="https://www.comune.cagliari.it/portale/page/it/bandi_di_concorso",
        region="Sardegna",
        organization="Comune di Cagliari",
        import_method="html-list-pending-adapter",
        technical_notes="Pagina pubblica del capoluogo regionale per bandi di concorso.",
    ),
    _source(
        name="ATS Sardegna - Amministrazione Trasparente archivio",
        source_type="html-hub",
        base_url="https://www.atssardegna.it/amministrazionetrasparente/",
        region="Sardegna",
        organization="ATS Sardegna",
        import_method="html-hub-archive-pending-adapter",
        technical_notes=(
            "Archivio pubblico ATS precedente alla riorganizzazione del servizio "
            "sanitario regionale; utile come fonte storica e di controllo."
        ),
    ),
    _source(
        name="Ministero Lavoro - Terzo settore",
        source_type="html-hub",
        base_url=(
            "https://www.lavoro.gov.it/temi-e-priorita/"
            "terzo-settore-e-responsabilita-sociale-imprese/Pagine/default.aspx"
        ),
        region=None,
        organization="Ministero del Lavoro e delle Politiche Sociali",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Hub istituzionale su terzo settore, avvisi e misure nazionali. "
            "Da usare come discovery pubblica, con filtro psicologico molto stretto."
        ),
    ),
    _source(
        name="Forum Terzo Settore - Bandi di interesse",
        source_type="third-sector-hub",
        base_url=(
            "https://www.forumterzosettore.it/2023/10/11/"
            "bandi-di-interesse-per-il-terzo-settore/"
        ),
        region=None,
        organization="Forum Nazionale Terzo Settore",
        import_method="third-sector-hub-pending-adapter",
        technical_notes=(
            "Pagina pubblica di segnalazione bandi per enti del terzo settore. "
            "Da trattare come aggregatore e non come fonte primaria del bando."
        ),
        access_note=OPEN_SOCIAL_SOURCE_NOTE,
    ),
    _source(
        name="Fondazione CON IL SUD - Bandi",
        source_type="third-sector-hub",
        base_url="https://www.fondazioneconilsud.it/bandi/",
        region=None,
        organization="Fondazione CON IL SUD",
        import_method="third-sector-hub-pending-adapter",
        technical_notes=(
            "Pagina pubblica dei bandi filantropici e sociali, rilevante per "
            "servizi sociali, salute di comunita e interventi educativi."
        ),
        access_note=OPEN_SOCIAL_SOURCE_NOTE,
    ),
    _source(
        name="Con i Bambini - Bandi e iniziative",
        source_type="third-sector-hub",
        base_url="https://www.conibambini.org/bandi-e-iniziative/",
        region=None,
        organization="Con i Bambini",
        import_method="third-sector-hub-pending-adapter",
        technical_notes=(
            "Pagina pubblica dei bandi e iniziative contro la poverta educativa "
            "minorile, potenzialmente rilevante per psicologia dello sviluppo."
        ),
        access_note=OPEN_SOCIAL_SOURCE_NOTE,
    ),
    _source(
        name="CSV Lombardia - Bandi per organizzazioni",
        source_type="third-sector-hub",
        base_url="https://www.csvlombardia.it/milano/milano-organizzazioni/#bandi",
        region="Lombardia",
        organization="CSV Lombardia",
        import_method="third-sector-hub-pending-adapter",
        technical_notes=(
            "Hub pubblico dei Centri di Servizio per il Volontariato lombardi, "
            "utile per bandi e progettazione sociale territoriale."
        ),
        access_note=OPEN_SOCIAL_SOURCE_NOTE,
    ),
    _source(
        name="Coopselios - Lavora con noi",
        source_type="private-social-jobs",
        base_url="https://www.coopselios.com/lavora-con-noi/",
        region=None,
        organization="Coopselios",
        import_method="private-social-jobs-pending-adapter",
        technical_notes=(
            "Pagina pubblica lavoro di cooperativa sociale. Catalogata come "
            "possibile fonte privata, da non importare senza adapter dedicato."
        ),
        access_note=OPEN_SOCIAL_SOURCE_NOTE,
    ),
    _source(
        name="Codess Sociale - Lavora con noi",
        source_type="private-social-jobs",
        base_url="https://www.codess.org/lavora-con-noi/",
        region=None,
        organization="Codess Sociale",
        import_method="private-social-jobs-pending-adapter",
        technical_notes=(
            "Pagina pubblica lavoro di cooperativa sociale nazionale. Catalogata "
            "come possibile fonte privata, da non importare senza adapter dedicato."
        ),
        access_note=OPEN_SOCIAL_SOURCE_NOTE,
    ),
    _source(
        name="Universita della Valle d'Aosta - Bandi di concorso",
        source_type="html-archive",
        base_url="https://www.univda.it/trasparenza/bandi-di-concorso/",
        region="Valle d'Aosta",
        organization="Universita della Valle d'Aosta",
        import_method="html-archive-pending-adapter",
        technical_notes="Archivio pubblico annuale di Amministrazione Trasparente.",
    ),
    _source(
        name="Universita di Torino - Concorsi e selezioni",
        source_type="html-hub",
        base_url="https://www.unito.it/ateneo/concorsi-e-selezioni",
        region="Piemonte",
        organization="Universita degli Studi di Torino",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Hub pubblico per personale, ricerca, docenza e opportunita per laureati. "
            "Richiede adapter delle sottosezioni."
        ),
    ),
    _source(
        name="Universita del Piemonte Orientale - Concorsi",
        source_type="html-hub",
        base_url="https://www.uniupo.it/it/concorsi",
        region="Piemonte",
        organization="Universita del Piemonte Orientale",
        import_method="html-hub-pending-adapter",
        technical_notes="Hub pubblico con categorie di concorsi e opportunita di Ateneo.",
    ),
    _source(
        name="Politecnico di Torino - Concorsi e selezioni",
        source_type="html-hub",
        base_url=(
            "https://www.polito.it/ateneo/lavora-e-collabora-con-noi/"
            "concorsi-e-selezioni"
        ),
        region="Piemonte",
        organization="Politecnico di Torino",
        import_method="html-hub-pending-adapter",
        technical_notes="Hub pubblico con categorie per personale, ricerca e incarichi.",
    ),
    _source(
        name="Universita di Genova - Concorsi e reclutamento",
        source_type="html-hub",
        base_url="https://unige.it/concorsi",
        region="Liguria",
        organization="Universita degli Studi di Genova",
        import_method="html-hub-pending-adapter",
        technical_notes="Hub pubblico con sottosezioni per personale e ricerca.",
    ),
    _source(
        name="Universita di Milano - Tutti i concorsi",
        source_type="html-list",
        base_url="https://www.unimi.it/it/ateneo/lavora-con-noi/tutti-i-concorsi",
        region="Lombardia",
        organization="Universita degli Studi di Milano",
        import_method="html-list-pending-adapter",
        technical_notes="Elenco pubblico filtrabile di bandi aperti e procedure in corso.",
    ),
    _source(
        name="Universita di Milano-Bicocca - Concorsi",
        source_type="html-hub",
        base_url="https://www.unimib.it/concorsi",
        region="Lombardia",
        organization="Universita degli Studi di Milano-Bicocca",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Hub pubblico per personale, ricerca, collaborazioni e docenza. "
            "Alta utilita potenziale per opportunita psicologiche."
        ),
    ),
    _source(
        name="Universita di Pavia - Bandi e concorsi",
        source_type="html-hub",
        base_url="https://portale.unipv.it/it/ateneo/organizzazione/bandi-e-concorsi",
        region="Lombardia",
        organization="Universita degli Studi di Pavia",
        import_method="html-hub-pending-adapter",
        technical_notes="Hub pubblico con collegamenti alle categorie di bandi di Ateneo.",
    ),
    _source(
        name="Universita dell'Insubria - Bandi attivi",
        source_type="html-list",
        base_url="https://www.uninsubria.it/bandi-e-concorsi",
        region="Lombardia",
        organization="Universita degli Studi dell'Insubria",
        import_method="html-list-pending-adapter",
        technical_notes=(
            "Elenco pubblico filtrabile con bandi attivi, procedure in espletamento "
            "e dettagli completi."
        ),
    ),
    _source(
        name="Universita di Bergamo - Concorsi e selezioni",
        source_type="html-hub",
        base_url="https://www.unibg.it/ateneo/amministrazione/concorsi-e-selezioni",
        region="Lombardia",
        organization="Universita degli Studi di Bergamo",
        import_method="html-hub-pending-adapter",
        technical_notes="Hub pubblico con categorie per personale, ricerca e collaborazioni.",
    ),
    _source(
        name="Universita di Brescia - Concorsi",
        source_type="html-hub",
        base_url="https://www.unibs.it/it/ateneo/amministrazione/concorsi",
        region="Lombardia",
        organization="Universita degli Studi di Brescia",
        import_method="html-hub-pending-adapter",
        technical_notes="Hub pubblico con sottosezioni per personale e ricerca.",
    ),
    _source(
        name="Politecnico di Milano - Bandi e concorsi",
        source_type="html-list",
        base_url="https://dynamicpoli.polimi.it/staff/lavora-con-noi/bandi-e-concorsi",
        region="Lombardia",
        organization="Politecnico di Milano",
        import_method="html-list-pending-adapter",
        technical_notes="Elenco pubblico filtrabile per personale tecnico-amministrativo.",
    ),
    _source(
        name="Universita di Trento - Lavora con noi",
        source_type="html-hub",
        base_url="https://lavoraconnoi.unitn.it/pta-cel",
        region="Trentino-Alto Adige",
        organization="Universita degli Studi di Trento",
        import_method="html-hub-pending-adapter",
        technical_notes="Portale pubblico dedicato a posizioni e procedimenti di selezione.",
    ),
    _source(
        name="Universita di Verona - Concorsi",
        source_type="html-list",
        base_url="https://www.univr.it/it/concorsi",
        region="Veneto",
        organization="Universita degli Studi di Verona",
        import_method="html-list-pending-adapter",
        technical_notes="Elenco pubblico di Ateneo con schede di dettaglio.",
    ),
    _source(
        name="Universita di Padova - Concorsi e selezioni",
        source_type="html-hub",
        base_url="https://www.unipd.it/concorsi",
        region="Veneto",
        organization="Universita degli Studi di Padova",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Hub pubblico istituzionale con categorie di concorsi, incarichi e bandi "
            "delle strutture di Ateneo. Richiede adapter per le sottosezioni."
        ),
    ),
    _source(
        name="Universita Ca' Foscari Venezia - Lavora con noi",
        source_type="html-hub",
        base_url="https://www.unive.it/lavoraconnoi",
        region="Veneto",
        organization="Universita Ca' Foscari Venezia",
        import_method="html-hub-pending-adapter",
        technical_notes="Hub pubblico per personale, ricerca, docenza e collaborazioni.",
    ),
    _source(
        name="Universita Iuav di Venezia - Bandi e concorsi",
        source_type="html-list",
        base_url="https://www.iuav.it/it/ateneo/bandi-concorsi",
        region="Veneto",
        organization="Universita Iuav di Venezia",
        import_method="html-list-pending-adapter",
        technical_notes="Elenco pubblico filtrabile con bandi correnti e materiali allegati.",
    ),
    _source(
        name="Universita di Trieste - Concorsi selezioni e consulenze",
        source_type="html-hub",
        base_url="https://www.units.it/en/node/44",
        region="Friuli-Venezia Giulia",
        organization="Universita degli Studi di Trieste",
        import_method="html-hub-pending-adapter",
        technical_notes="Hub pubblico con categorie per personale, ricerca e consulenze.",
    ),
    _source(
        name="Universita di Udine - Concorsi e bandi",
        source_type="html-hub",
        base_url="https://www.uniud.it/it/ateneo-uniud/concorsi-bandi-uniud",
        region="Friuli-Venezia Giulia",
        organization="Universita degli Studi di Udine",
        import_method="html-hub-pending-adapter",
        technical_notes="Hub pubblico con categorie per concorsi e collaborazioni.",
    ),
    _source(
        name="Universita di Bologna - Bandi di concorso",
        source_type="html-hub",
        base_url="https://www.unibo.it/it/ateneo/amministrazione-trasparente/bandi-di-concorso",
        region="Emilia-Romagna",
        organization="Alma Mater Studiorum - Universita di Bologna",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Sezione pubblica di Amministrazione Trasparente con rimandi alle "
            "categorie e alle schede dei bandi."
        ),
    ),
    _source(
        name="Universita di Parma - Concorsi e mobilita",
        source_type="html-hub",
        base_url="https://www.unipr.it/concorsi-e-mobilita",
        region="Emilia-Romagna",
        organization="Universita degli Studi di Parma",
        import_method="html-hub-pending-adapter",
        technical_notes="Archivio pubblico con categorie per personale e ricerca.",
    ),
    _source(
        name="Universita di Modena e Reggio Emilia - Bandi di concorso",
        source_type="pat-html",
        base_url=(
            "https://amministrazionetrasparente.unimore.it/"
            "pagina639_bandi-di-concorso.html"
        ),
        region="Emilia-Romagna",
        organization="Universita degli Studi di Modena e Reggio Emilia",
        import_method="pat-html-pending-adapter",
        technical_notes=(
            "Portale pubblico PAT di Amministrazione Trasparente. Valutare adapter "
            "riusabile anche per altri enti basati sulla stessa piattaforma."
        ),
    ),
    _source(
        name="Universita di Ferrara - Bandi di concorso",
        source_type="html-hub",
        base_url="https://www2.unife.it/at/bandi-di-concorso",
        region="Emilia-Romagna",
        organization="Universita degli Studi di Ferrara",
        import_method="html-hub-pending-adapter",
        technical_notes=(
            "Sezione pubblica di Amministrazione Trasparente con bandi centrali "
            "e collegamenti ai Dipartimenti."
        ),
    ),
]

ADDITIONAL_SOCIAL_JOB_SOURCE_DEFINITIONS = [
    {
        "name": "Telefono Azzurro - Lavora con noi",
        "source_type": "private-social-jobs",
        "base_url": "https://telefonoazzurro.altamiraweb.com",
        "region": None,
        "organization": "Telefono Azzurro",
        "import_method": "private-social-jobs-pending-adapter",
        "technical_notes": (
            "Portale pubblico Altamira collegato dal sito Telefono Azzurro. "
            "Fonte privata/sociale da usare con adapter dedicato e filtri stretti."
        ),
        "access_note": OPEN_SOCIAL_SOURCE_NOTE,
    },
    {
        "name": "Emergency - Lavora con noi",
        "source_type": "private-social-jobs",
        "base_url": "https://www.emergency.it/lavora-con-noi/",
        "region": None,
        "organization": "Emergency",
        "import_method": "private-social-jobs-pending-adapter",
        "technical_notes": (
            "Pagina pubblica lavoro di organizzazione umanitaria. Catalogata come "
            "fonte sociale potenziale, non come concorso pubblico."
        ),
        "access_note": OPEN_SOCIAL_SOURCE_NOTE,
    },
    {
        "name": "CUAMM Medici con l'Africa - Lavora con noi",
        "source_type": "private-social-jobs",
        "base_url": "https://mediciconlafrica.org/lavora-con-noi/",
        "region": None,
        "organization": "CUAMM Medici con l'Africa",
        "import_method": "private-social-jobs-pending-adapter",
        "technical_notes": (
            "Pagina pubblica lavoro e collaborazione di organizzazione sanitaria "
            "non profit; richiede adapter dedicato."
        ),
        "access_note": OPEN_SOCIAL_SOURCE_NOTE,
    },
    {
        "name": "Croce Rossa Italiana - Lavora con noi",
        "source_type": "private-social-jobs",
        "base_url": "https://cri.it/lavora-con-noi-2/",
        "region": None,
        "organization": "Croce Rossa Italiana",
        "import_method": "private-social-jobs-pending-adapter",
        "technical_notes": (
            "Pagina pubblica lavoro della Croce Rossa Italiana. Da trattare come "
            "fonte sociale nazionale e verificare prima dello scraping."
        ),
        "access_note": OPEN_SOCIAL_SOURCE_NOTE,
    },
    {
        "name": "La Nostra Famiglia - Lavora con noi",
        "source_type": "private-social-jobs",
        "base_url": "https://lanostrafamiglia.it/lavora-con-noi/",
        "region": None,
        "organization": "La Nostra Famiglia",
        "import_method": "private-social-jobs-pending-adapter",
        "technical_notes": (
            "Pagina pubblica lavoro di ente sociosanitario e riabilitativo; "
            "potenzialmente rilevante per profili psicologici e neuropsicologici."
        ),
        "access_note": OPEN_SOCIAL_SOURCE_NOTE,
    },
]

ADDITIONAL_MUNICIPAL_SOURCE_DEFINITIONS = [
    {
        "name": "Comune di Bologna - Bandi e concorsi",
        "source_type": "html-hub",
        "base_url": "https://www.comune.bologna.it/amministrazione/concorsi",
        "region": "Emilia-Romagna",
        "organization": "Comune di Bologna",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica concorsi del capoluogo regionale.",
    },
    {
        "name": "Comune di Trieste - Bandi di concorso",
        "source_type": "spa-external-link",
        "base_url": (
            "https://www.comune.trieste.it/it/amministrazione-trasparente-5200/"
            "bandi-di-concorso-5222"
        ),
        "region": "Friuli-Venezia Giulia",
        "organization": "Comune di Trieste",
        "import_method": "spa-external-link-pending-adapter",
        "technical_notes": "Sezione pubblica SPA di Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Ancona - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.comuneancona.it/ankonline/ammtrasp/bandi-di-concorso/",
        "region": "Marche",
        "organization": "Comune di Ancona",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica di Amministrazione Trasparente del capoluogo.",
    },
    {
        "name": "Comune di Perugia - Concorsi",
        "source_type": "html-list",
        "base_url": "https://www.comune.perugia.it/argomento/concorsi/",
        "region": "Umbria",
        "organization": "Comune di Perugia",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica argomento concorsi del capoluogo regionale.",
    },
    {
        "name": "Comune di Milano - Bandi di concorso",
        "source_type": "municipal-access-review",
        "base_url": (
            "https://www.comune.milano.it/amministrazione/amministrazione-trasparente/"
            "bandi-di-concorso"
        ),
        "region": "Lombardia",
        "organization": "Comune di Milano",
        "import_method": "municipal-access-review",
        "technical_notes": (
            "Pagina pubblica aggiornata, ma il portale risponde 403 agli accessi "
            "automatici. Fonte mantenuta per revisione di un endpoint compatibile."
        ),
    },
    {
        "name": "Comune dell'Aquila - Bandi di concorso",
        "source_type": "spa-external-link",
        "base_url": "https://www.comune.laquila.it/amministrazione-trasparente/bandi-di-concorso",
        "region": "Abruzzo",
        "organization": "Comune dell'Aquila",
        "import_method": "spa-external-link-pending-adapter",
        "technical_notes": "Pagina SPA pubblica del capoluogo regionale.",
    },
    {
        "name": "Comune di Campobasso - Bandi di concorso",
        "source_type": "spa-external-link",
        "base_url": (
            "https://www.comune.campobasso.it/sito/amministrazione-trasparente/"
            "bandi-di-concorso"
        ),
        "region": "Molise",
        "organization": "Comune di Campobasso",
        "import_method": "spa-external-link-pending-adapter",
        "technical_notes": "Pagina SPA pubblica del capoluogo regionale.",
    },
    {
        "name": "Comune di Frosinone - Bandi di concorso",
        "source_type": "external-transparency",
        "base_url": "https://servizi.comune.frosinone.it/openweb/trasparenza/categoria.php?id=8",
        "region": "Lazio",
        "organization": "Comune di Frosinone",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Sezione OpenWeb Trasparenza verificata dal sito comunale.",
    },
    {
        "name": "Comune di Latina - Concorsi",
        "source_type": "html-hub",
        "base_url": "https://www.comune.latina.it/home/info/argomenti/015.html",
        "region": "Lazio",
        "organization": "Comune di Latina",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica argomento concorsi e lavoro.",
    },
    {
        "name": "Comune di Rieti - Bandi di concorso",
        "source_type": "external-transparency",
        "base_url": (
            "https://lnx.comune.rieti.it/amministrazione-trasparente/content/"
            "bandi-di-concorso"
        ),
        "region": "Lazio",
        "organization": "Comune di Rieti",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Pagina pubblica Amministrazione Trasparente del Comune.",
    },
    {
        "name": "Comune di Viterbo - Bandi di concorso",
        "source_type": "municipal-access-review",
        "base_url": "https://comune.viterbo.it/argomento/concorsi/",
        "region": "Lazio",
        "organization": "Comune di Viterbo",
        "import_method": "municipal-access-review",
        "technical_notes": (
            "Pagina pubblica concorsi protetta da una verifica anti-bot. Fonte "
            "mantenuta per revisione di un endpoint o adapter compatibile."
        ),
    },
    {
        "name": "Comune di Avellino - Bandi di concorso",
        "source_type": "spa-external-link",
        "base_url": (
            "https://www.comune.avellino.it/sito/amministrazione-trasparente/"
            "bandi-di-concorso"
        ),
        "region": "Campania",
        "organization": "Comune di Avellino",
        "import_method": "spa-external-link-pending-adapter",
        "technical_notes": "Pagina SPA pubblica del capoluogo provinciale.",
    },
    {
        "name": "Comune di Benevento - Amministrazione Trasparente",
        "source_type": "html-list",
        "base_url": "https://comune.benevento.it/concorsi/",
        "region": "Campania",
        "organization": "Comune di Benevento",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica concorsi del Comune.",
    },
    {
        "name": "Comune di Caserta - Amministrazione Trasparente",
        "source_type": "external-transparency",
        "base_url": "https://trasparenza.comune.caserta.it/",
        "region": "Campania",
        "organization": "Comune di Caserta",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Portale pubblico Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Salerno - Amministrazione Trasparente",
        "source_type": "external-transparency",
        "base_url": "https://amministrazionetrasparente.comune.salerno.it/amministrazioneTrasparente",
        "region": "Campania",
        "organization": "Comune di Salerno",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Portale pubblico Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Brindisi - Amministrazione Trasparente",
        "source_type": "external-transparency",
        "base_url": "https://servizi.comune.brindisi.it/openweb/trasparenza/",
        "region": "Puglia",
        "organization": "Comune di Brindisi",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Portale pubblico OpenWeb Trasparenza.",
    },
    {
        "name": "Comune di Foggia - Amministrazione Trasparente",
        "source_type": "external-transparency",
        "base_url": (
            "https://portalehypersic.comune.foggia.it/cmsfoggia/portale/"
            "trasparenza/trasparenzaamministrativa.aspx?P=6700"
        ),
        "region": "Puglia",
        "organization": "Comune di Foggia",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Portale Hypersic pubblico Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Lecce - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.comune.lecce.it/amministrazione-trasparente/bandi-di-concorso",
        "region": "Puglia",
        "organization": "Comune di Lecce",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica di Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Taranto - Vita lavorativa",
        "source_type": "html-hub",
        "base_url": "https://www.comune.taranto.it/it/page/113238?fromService=1",
        "region": "Puglia",
        "organization": "Comune di Taranto",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica servizi vita lavorativa collegata ai concorsi.",
    },
    {
        "name": "Comune di Andria - Amministrazione Trasparente",
        "source_type": "external-transparency",
        "base_url": "https://andria.trasparenza-valutazione-merito.it/",
        "region": "Puglia",
        "organization": "Comune di Andria",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Portale pubblico Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Barletta - Amministrazione Trasparente",
        "source_type": "external-transparency",
        "base_url": (
            "https://trasparenza.comune.barletta.bt.it/"
            "pagina639_bandi-di-concorso.html"
        ),
        "region": "Puglia",
        "organization": "Comune di Barletta",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": (
            "Pagina pubblica aggiornata di Amministrazione Trasparente, gestita "
            "dall'adapter HTML profondo."
        ),
    },
    {
        "name": "Comune di Trani - Amministrazione Trasparente",
        "source_type": "external-transparency",
        "base_url": "https://trani.trasparenza-valutazione-merito.it/",
        "region": "Puglia",
        "organization": "Comune di Trani",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Portale pubblico Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Potenza - Bandi di concorso",
        "source_type": "spa-external-link",
        "base_url": (
            "https://www.comune.potenza.it/sito/amministrazione-trasparente/"
            "bandi-di-concorso"
        ),
        "region": "Basilicata",
        "organization": "Comune di Potenza",
        "import_method": "spa-external-link-pending-adapter",
        "technical_notes": "Pagina SPA pubblica del capoluogo regionale.",
    },
    {
        "name": "Comune di Matera - Vita lavorativa",
        "source_type": "html-hub",
        "base_url": "https://comune.matera.it/servizi-categoria/vita-lavorativa/",
        "region": "Basilicata",
        "organization": "Comune di Matera",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica servizi vita lavorativa collegata ai concorsi.",
    },
    {
        "name": "Comune di Chieti - Amministrazione Trasparente",
        "source_type": "html-list",
        "base_url": "https://comune.chieti.it/concorsi/",
        "region": "Abruzzo",
        "organization": "Comune di Chieti",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica concorsi del Comune.",
    },
    {
        "name": "Comune di Pescara - Bandi di selezione del personale",
        "source_type": "html-list",
        "base_url": "https://www.comune.pescara.it/bandi-di-selezione-del-personale/",
        "region": "Abruzzo",
        "organization": "Comune di Pescara",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica dei bandi di selezione del personale.",
    },
    {
        "name": "Comune di Teramo - Amministrazione Trasparente",
        "source_type": "external-transparency",
        "base_url": "https://trasparenza.tinnvision.cloud/traspamm/00174750679/2/home.html",
        "region": "Abruzzo",
        "organization": "Comune di Teramo",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Portale Tinnvision pubblico di Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Alessandria - Amministrazione Trasparente",
        "source_type": "external-transparency",
        "base_url": (
            "https://servizionline.comune.alessandria.it/cmsalessandria/"
            "portale/trasparenza/trasparenzaamministrativadocs.aspx?R=1&CP=5"
        ),
        "region": "Piemonte",
        "organization": "Comune di Alessandria",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Portale pubblico Hypersic di Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Asti - Bandi e concorsi",
        "source_type": "html-list",
        "base_url": (
            "https://www.comune.asti.it/amministrazione/documenti-dati/documenti"
            "?f%5B0%5D=tipo_doc%3A136&f%5B1%5D=tipo_doc%3A136"
        ),
        "region": "Piemonte",
        "organization": "Comune di Asti",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Lista pubblica documenti filtrata sui concorsi.",
    },
    {
        "name": "Comune di Biella - Concorsi",
        "source_type": "html-list",
        "base_url": "https://comune.biella.it/amm_trasp/bandi-di-concorso/",
        "region": "Piemonte",
        "organization": "Comune di Biella",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica argomento concorsi.",
    },
    {
        "name": "Comune di Cuneo - Concorsi",
        "source_type": "html-list",
        "base_url": "https://www.comune.cuneo.it/argomento/concorsi/",
        "region": "Piemonte",
        "organization": "Comune di Cuneo",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica argomento concorsi.",
    },
    {
        "name": "Comune di Novara - Vita lavorativa",
        "source_type": "html-hub",
        "base_url": "https://www.comune.novara.it/servizi/vita-lavorativa",
        "region": "Piemonte",
        "organization": "Comune di Novara",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica servizi vita lavorativa.",
    },
    {
        "name": "Comune di Verbania - Concorsi",
        "source_type": "html-list",
        "base_url": "https://www.comune.verbania.it/Amministrazione-Trasparente/Bandi-di-concorso",
        "region": "Piemonte",
        "organization": "Comune di Verbania",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica argomento concorsi.",
    },
    {
        "name": "Comune di Vercelli - Vita lavorativa",
        "source_type": "html-hub",
        "base_url": "https://www.comune.vercelli.it/servizi/vita-lavorativa",
        "region": "Piemonte",
        "organization": "Comune di Vercelli",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica servizi vita lavorativa.",
    },
    {
        "name": "Comune di Bergamo - Avvisi e bandi",
        "source_type": "html-list",
        "base_url": "https://www.comune.bergamo.it/avvisi-bandi",
        "region": "Lombardia",
        "organization": "Comune di Bergamo",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica avvisi e bandi del Comune.",
    },
    {
        "name": "Comune di Brescia - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://trasparenza.comune.brescia.it/amministrazione-trasparente/bandi-di-concorso/",
        "region": "Lombardia",
        "organization": "Comune di Brescia",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica di Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Como - Concorsi",
        "source_type": "html-list",
        "base_url": "https://www.comune.como.it/amministrazione-trasparente/bandi-di-concorso",
        "region": "Lombardia",
        "organization": "Comune di Como",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica argomento concorsi.",
    },
    {
        "name": "Comune di Cremona - Concorsi e selezioni",
        "source_type": "html-list",
        "base_url": "https://www.comune.cremona.it/schede-informative/concorsi-selezioni",
        "region": "Lombardia",
        "organization": "Comune di Cremona",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica concorsi e selezioni.",
    },
    {
        "name": "Comune di Lecco - Lavora con noi",
        "source_type": "html-hub",
        "base_url": "https://www.comune.lecco.it/Novita/Notizie/Lavora-con-noi",
        "region": "Lombardia",
        "organization": "Comune di Lecco",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica lavoro e concorsi del Comune.",
    },
    {
        "name": "Comune di Lodi - Bandi di concorso",
        "source_type": "external-transparency",
        "base_url": "https://lodi.e-pal.it/L190/?idSezione=167875&id=&sort=&activePage=&search=",
        "region": "Lombardia",
        "organization": "Comune di Lodi",
        "import_method": "external-transparency-pending-adapter",
        "technical_notes": "Portale pubblico L190 di Amministrazione Trasparente.",
    },
    {
        "name": "Comune di Mantova - Concorsi",
        "source_type": "html-list",
        "base_url": "https://www.comune.mantova.it/it/topics/15",
        "region": "Lombardia",
        "organization": "Comune di Mantova",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica tema concorsi.",
    },
    {
        "name": "Comune di Monza - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://www.comune.monza.it/it/page/412919",
        "region": "Lombardia",
        "organization": "Comune di Monza",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica concorsi e selezioni.",
    },
    {
        "name": "Comune di Pavia - Vita lavorativa",
        "source_type": "html-list",
        "base_url": "https://www.comune.pavia.it/amministrazione/documenti-dati/dataset/bandi-concorso",
        "region": "Lombardia",
        "organization": "Comune di Pavia",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Dataset pubblico bandi concorso.",
    },
    {
        "name": "Comune di Sondrio - Bandi concorso",
        "source_type": "html-list",
        "base_url": "https://comune.sondrio.it/novita/bandi-di-concorso/",
        "region": "Lombardia",
        "organization": "Comune di Sondrio",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica bandi concorso.",
    },
    {
        "name": "Comune di Varese - Ufficio concorsi",
        "source_type": "html-hub",
        "base_url": "https://www.comune.varese.it/amministrazione/uffici/ufficio_66.html#info",
        "region": "Lombardia",
        "organization": "Comune di Varese",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica ufficio concorsi e selezioni.",
    },
    {
        "name": "Comune di Agrigento - Bandi di concorso",
        "source_type": "html-list",
        "base_url": "https://comune.agrigento.it/amm_trasp/bandi-di-concorso/",
        "region": "Sicilia",
        "organization": "Comune di Agrigento",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica bandi di concorso.",
    },
    {
        "name": "Comune di Caltanissetta - Concorsi",
        "source_type": "html-list",
        "base_url": "https://www.comune.caltanissetta.it/it/topics/56",
        "region": "Sicilia",
        "organization": "Comune di Caltanissetta",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica tema concorsi.",
    },
    {
        "name": "Comune di Catania - Vita lavorativa",
        "source_type": "html-hub",
        "base_url": "https://www.comune.catania.it/servizi/default.aspx?category=3",
        "region": "Sicilia",
        "organization": "Comune di Catania",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica servizi vita lavorativa.",
    },
    {
        "name": "Comune di Enna - Vita lavorativa",
        "source_type": "html-list",
        "base_url": "https://www.comune.enna.it/amministrazione-trasparente/bandi-di-concorso",
        "region": "Sicilia",
        "organization": "Comune di Enna",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica bandi di concorso.",
    },
    {
        "name": "Comune di Messina - Vita lavorativa",
        "source_type": "html-hub",
        "base_url": "https://www.comune.messina.it/it/page/vita-lavorativa-200?fromService=1",
        "region": "Sicilia",
        "organization": "Comune di Messina",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica servizi vita lavorativa.",
    },
    {
        "name": "Comune di Ragusa - Vita lavorativa",
        "source_type": "html-hub",
        "base_url": "https://www.comune.ragusa.it/it/page/123601?fromService=1",
        "region": "Sicilia",
        "organization": "Comune di Ragusa",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica servizi vita lavorativa.",
    },
    {
        "name": "Comune di Siracusa - Concorsi",
        "source_type": "html-list",
        "base_url": "https://www.comune.siracusa.it/area_tematica/bandi-di-concorso-del-comune-di-siracusa",
        "region": "Sicilia",
        "organization": "Comune di Siracusa",
        "import_method": "html-list-pending-adapter",
        "technical_notes": "Pagina pubblica argomento concorsi.",
    },
    {
        "name": "Comune di Trapani - Vita lavorativa",
        "source_type": "html-hub",
        "base_url": "https://comune.trapani.it/tipo_servizio/vita-lavorativa/",
        "region": "Sicilia",
        "organization": "Comune di Trapani",
        "import_method": "html-hub-pending-adapter",
        "technical_notes": "Pagina pubblica servizi vita lavorativa.",
    },
]

VERIFIED_SOURCE_CATALOG.extend(
    _source(**definition) for definition in ADDITIONAL_SOCIAL_JOB_SOURCE_DEFINITIONS
)
VERIFIED_SOURCE_CATALOG.extend(
    _source(**definition) for definition in ADDITIONAL_MUNICIPAL_SOURCE_DEFINITIONS
)

VERIFIED_SOURCE_CATALOG.extend(
    _source(**definition) for definition in NORTHERN_HEALTH_SOURCE_DEFINITIONS
)
VERIFIED_SOURCE_CATALOG.extend(
    _source(**definition) for definition in CENTRAL_HEALTH_SOURCE_DEFINITIONS
)
VERIFIED_SOURCE_CATALOG.extend(
    _source(**definition) for definition in TARGET_HEALTH_SOURCE_DEFINITIONS
)
VERIFIED_SOURCE_CATALOG.extend(
    _source(**definition) for definition in NATIONAL_HEALTH_SOURCE_DEFINITIONS
)
VERIFIED_SOURCE_CATALOG.extend(
    _source(**definition) for definition in PUGLIA_AOL_SOURCE_DEFINITIONS
)
VERIFIED_SOURCE_CATALOG.extend(
    _source(**definition) for definition in HOSPITAL_HEALTH_SOURCE_DEFINITIONS
)
VERIFIED_SOURCE_CATALOG.extend(
    _source(**definition) for definition in MINISTERIAL_SOURCE_DEFINITIONS
)
