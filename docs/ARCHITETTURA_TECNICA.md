# Architettura tecnica MVP

## Obiettivo

Questo scaffold implementa una prima base eseguibile per il servizio di consultazione bandi psicologici:

- backend API;
- modello dati persistente;
- importer modulare;
- classificazione rule-based;
- widget embedded React;
- seed demo;
- test di dominio.

## Componenti

### Backend

Percorso: `backend/app`

Responsabilita:

- espone API pubbliche e admin;
- gestisce opportunita, fonti, alert e audit;
- esegue seed/import demo;
- classifica pertinenza, ambiti e requisiti;
- prepara il contratto per importer reali.

Moduli principali:

- `models.py`: modello SQLAlchemy;
- `api/public.py`: consultazione pubblica e alert;
- `api/admin.py`: revisione minima e import manuale demo;
- `importers/base.py`: contratto importer;
- `importers/sample_fixture.py`: importer fixture;
- `importers/inpa.py`: importer reale inPA;
- `services/source_probe.py`: verifica raggiungibilita fonti istituzionali catalogate;
- `services/classifier.py`: tassonomia rule-based;
- `services/dates.py`: parsing date e stato;
- `services/dedupe.py`: fingerprint e duplicati.

### Frontend

Percorso: `frontend/src`

Responsabilita:

- widget embeddabile in iframe;
- ricerca e filtri;
- lista risultati;
- scheda dettaglio;
- form alert;
- fallback demo quando il backend non e' raggiungibile.

Parametri URL supportati:

- `region`
- `q`
- `category`
- `entity_type`
- `area`
- `status`
- `defaultStatus=open`

Esempio:

```text
http://localhost:5173/?tenant=ordine-demo&region=Lazio&defaultStatus=open
```

### Database

Il backend supporta:

- SQLite locale se `DATABASE_URL` non e' impostato;
- PostgreSQL tramite Docker Compose.

Tabelle principali:

- `opportunities`;
- `sources`;
- `attachments`;
- `alert_subscriptions`;
- `editorial_actions`;
- `import_runs`.

Per MVP lo schema viene creato con `Base.metadata.create_all`. Prima di produzione va introdotto Alembic.

## Flusso import

1. Importer recupera record grezzi.
2. Parsing e normalizzazione campi.
3. Classificazione rule-based.
4. Deduplicazione su `source_id + external_id`.
5. Upsert opportunita.
6. Aggiornamento `search_text`.
7. Log in `import_runs`.

Per aggiungere una fonte reale:

1. creare un nuovo file in `backend/app/importers`;
2. implementare una funzione `run_x_import(db: Session)`;
3. creare/aggiornare la `Source`;
4. trasformare i record esterni in payload `Opportunity`;
5. aggiungere endpoint admin o job scheduler.

## Catalogo sorgenti

`backend/app/source_catalog.py` contiene le pagine istituzionali pubbliche da
monitorare. Il probe HTTP non importa contenuti: aggiorna soltanto lo stato
operativo della fonte.

Stati principali:

- `catalogued`: fonte registrata ma non ancora verificata;
- `reachable`: pagina raggiungibile dal container;
- `tls-review`: pagina pubblica da riesaminare per la catena certificati;
- `timeout-review`: pagina da riesaminare per tempi di risposta;
- `unreachable`: errore non riconducibile ai casi precedenti.

Il catalogo sincronizza URL, tipo di fonte e note tecniche senza azzerare lo
stato operativo gia registrato.

## Import inPA

L'importer usa l'endpoint JSON pubblico richiamato dalla pagina ufficiale inPA:

```text
https://portale.inpa.gov.it/concorsi-smart/api/concorso-public-area/search-better
```

Il backend:

- cerca bandi aperti con termini professionali;
- deduplica per ID inPA;
- conserva il link ufficiale alla scheda inPA;
- ripulisce HTML descrittivo;
- applica classificazione e tagging;
- esclude risultati con sole citazioni generiche a competenze psicologiche.

Comando manuale:

```powershell
python -m app.scripts.import_real --remove-demo --probe-local-sources
```

## Import istituzionali attivi

Il comando manuale aggiorna anche sei adapter:

- `importers/azienda_zero.py`: usa l'endpoint JSON pubblico richiamato dalla pagina
  ufficiale `https://www.azero.veneto.it/concorsi-e-avvisi`;
- `importers/asl_roma2.py`: usa la ricerca server-side della tabella pubblica
  `https://www.aslroma2.it/external/concorsi/index.php`.
- `importers/comune_venezia.py`: legge la tabella HTML pubblica
  `https://www.comune.venezia.it/node/6313`.
- `importers/myportal_veneto.py`: usa il catalogo JSON pubblico MyPortal di
  Amministrazione Trasparente ed e attivo per il Comune di Treviso.
- `importers/inail.py`: legge soltanto poche pagine recenti dell'archivio pubblico
  `https://www.inail.it/portale/it/inail-comunica/avvisi.html`.
- `importers/inps.py`: interroga con termini psicologici l'endpoint JSON pubblico
  richiamato dalla lista `https://www.inps.it/it/it/avvisi-bandi-e-fatturazione/fatturazione-concorsi.html`.

Gli adapter:

- selezionano soltanto profili professionali psicologici espliciti;
- conservano riferimenti agli allegati essenziali senza scaricare o replicare i PDF;
- escludono dagli allegati elenchi candidati e altri documenti non necessari;
- mantengono nascoste le procedure scadute;
- marcano come nascoste le probabili duplicazioni gia presenti da altre fonti;
- registrano il risultato in `import_runs`.

Per INAIL l'ambito e intenzionalmente limitato: `robots.txt` esclude le sezioni
di Amministrazione Trasparente, quindi l'adapter usa soltanto l'archivio generale
degli avvisi, non escluso dalla policy pubblicata. La connessione INAIL usa un
contesto dedicato TLS 1.2 con `AES256-GCM-SHA384`, richiesto dal server, senza
disattivare verifica CA o hostname. INPS consente l'accesso alla lista e
l'interfaccia ufficiale usa direttamente un endpoint JSON pubblico.

`https://concorsi.regione.veneto.it/` resta una fonte di discovery: le tabelle
pubbliche sono incorporate tramite Google Apps Script, ma non espongono un formato
dati stabile documentato adatto a un adapter server-side prudente.

La famiglia MyPortal va attivata tenant per tenant. Treviso pubblica i record nel
catalogo JSON MyPortal. Belluno e Rovigo usano MyPortal come porta d'ingresso ma
rinviano rispettivamente a una sezione storica separata e a un portale trasparenza
Liferay esterno.

## Strategia search

La ricerca MVP usa `search_text` normalizzato e filtri in memoria dopo lettura da database. E' accettabile per dataset pilota.

Step successivo:

- introdurre Meilisearch/Typesense/OpenSearch;
- indicizzare title, description, organization, areas, requirements, extracted attachment text;
- usare faccette native del motore search.

## Sicurezza MVP

Admin protetto da bearer token statico:

```text
Authorization: Bearer <ADMIN_API_TOKEN>
```

Prima di produzione:

- password hashing;
- sessioni o JWT con scadenza;
- rotazione token;
- rate limit;
- CSRF se si usano cookie;
- audit piu completo.

## Decisioni tecniche da chiudere

- regioni pilota;
- fonti reali prioritarie;
- provider email transazionale di produzione;
- dominio servizio;
- policy privacy e retention;
- scelta motore search;
- deploy target.
