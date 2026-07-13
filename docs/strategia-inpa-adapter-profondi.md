# Strategia INPA e adapter profondi

Aggiornato: 2026-07-10

## Obiettivi

1. Trattare INPA come fonte primaria nazionale, con massima copertura degli avvisi aperti.
2. Costruire adapter profondi per le altre fonti, raggruppandole per famiglia tecnica invece che per singolo ente.
3. Rendere ogni adapter verificabile: conteggi, paginazione, deduplica, scadenze e falsi positivi devono essere testati.

## INPA: standard di affidabilita

L'adapter INPA deve usare due livelli di acquisizione:

- scansione completa degli avvisi `OPEN` con `text=""`;
- ricerche per keyword psicologiche come ridondanza e controllo.

La scansione completa e' il meccanismo principale: evita di dipendere solo da keyword come `psicolog` o `lm-51`. Le keyword restano utili se l'API cambia comportamento o se serve intercettare record che il motore testuale indicizza diversamente.

Regole operative:

- se il numero di pagine `OPEN` supera `INPA_OPEN_SCAN_MAX_PAGES`, l'import deve fallire in modo esplicito;
- ogni record e' deduplicato per `concorso_id`;
- un record non chiaramente psicologico ma potenzialmente rilevante entra come `pending`;
- solo i record con profilo psicologico diretto sono `approved`;
- i record non professionali gia presenti vengono nascosti, non lasciati visibili.

## Tassonomia adapter profondi

### 1. API pubbliche JSON

Esempi: INPA, Puglia AOL, Azienda Zero, MyPortal.

Strategia:

- usare endpoint pubblici stabili osservati dalle pagine ufficiali;
- paginare fino a completamento dichiarato dall'API;
- fallire se la paginazione e' incompleta;
- testare parsing, deduplica, scadenza, status e link ufficiale.

Priorita: altissima.

### 2. Portali sanitari regionali centralizzati

Esempi: PugliaSalute, AST Marche, ASL Piemonte, target health regionali.

Strategia:

- creare adapter per famiglia regionale;
- separare pagina elenco, dettaglio, allegati e date;
- non importare graduatorie/revoche come bandi aperti;
- gestire gli avvisi multi-profilo con stato `pending` se non e' chiaro il profilo psicologo.

Priorita: altissima.

### 3. Amministrazione Trasparente / PAT

Esempi: comuni, ASL e aziende ospedaliere con sezioni "Bandi di concorso".

Strategia:

- riconoscere tabelle e griglie ricorrenti;
- seguire dettaglio e allegati;
- preferire la scadenza domanda rispetto a data pubblicazione, graduatoria o delibera;
- ignorare pagine hub generiche, privacy, servizio e contatti.

Priorita: alta.

### 4. WordPress / CMS tradizionali

Esempi: molte aziende sanitarie, ospedali, terzo settore.

Strategia:

- provare prima eventuale REST API WordPress (`/wp-json/wp/v2/search`, post, pages);
- usare query `?s=psicolog`, `?s=psicoterap`, `?s=lm-51` solo su fonti identificate come WordPress;
- attraversare un numero limitato di schede dettaglio;
- filtrare pagine servizio e news non candidabili.

Priorita: alta.

### 5. Portali ospedalieri custom

Esempi: AORN, AOU, IRCCS con sezioni concorsi proprietarie.

Strategia:

- campionare HTML e pattern URL;
- creare adapter per cluster tecnico, non uno per ogni ospedale quando il CMS e' uguale;
- se il portale ha storico lungo, importare solo aperti o ultimi record con scadenza futura;
- mantenere i record scaduti nascosti per audit, non pubblici.

Priorita: alta.

### 6. Terzo settore e privato sociale

Esempi: Telefono Azzurro, Emergency, CUAMM, CRI, cooperative sociali.

Strategia:

- distinguere "job board" da bandi/progetti;
- importare solo posizioni con testo professionale psicologico diretto;
- se richiede login, candidatura privata o sistema ATS non indicizzabile, catalogare ma non forzare scraping;
- indicare chiaramente `entity_type=privato-sociale`.

Priorita: media.

### 7. PDF / allegati

Strategia:

- scaricare solo allegati ufficiali leggeri e pertinenti;
- estrarre testo per scadenze e requisiti;
- se il PDF e' l'unica fonte della scadenza, segnare il record `pending` finche il parsing non e' testato;
- non usare date di firma, protocollo o pubblicazione come scadenza domanda.

Priorita: media.

## Pipeline di sviluppo adapter

Per ogni famiglia:

1. Inventario fonti: URL, tipo CMS, regione, ente, accessibilita, TLS, paginazione.
2. Sonda tecnica: HTML/API, pattern link dettaglio, presenza allegati, date.
3. Fixture reali minimizzate: un bando aperto, uno scaduto, una graduatoria, una pagina servizio.
4. Adapter dedicato o parser famiglia.
5. Test unitari su parsing e filtro professionale.
6. Test live controllato con conteggi creati/aggiornati/scartati.
7. Metriche: fonti con record, fonti zero, record pending, record nascosti per motivo.

## Metriche minime da esporre

- record acquisiti per fonte;
- record scartati per filtro non psicologico;
- record nascosti per scadenza;
- record nascosti per graduatoria/revoca;
- record pending aperti;
- fonti senza record dopo refresh;
- errori TLS/accesso/API.

## Priorita prossime

1. INPA completo: mantenere scansione OPEN e test di paginazione.
2. Sanita regionale con API o portali stabili: Puglia AOL, Piemonte, Marche, Veneto, Lazio.
3. Ospedalieri custom con molti risultati storici: AORN Moscati, AOUP Pisa, AO Terni, AOU/IRCCS.
4. PAT comuni e ASL: clusterizzare per piattaforma.
5. WordPress/CMS: REST API e ricerca controllata.
6. Privato sociale e terzo settore: solo dove le pagine sono pubbliche e senza login.
