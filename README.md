# Bandi Psicologia

Scaffold tecnico MVP per un servizio embedded di ricerca bandi, concorsi, avvisi e incarichi rilevanti per psicologhe e psicologi in Italia.

La configurazione Docker importa automaticamente bandi aperti reali da inPA e rimuove i
dati demo quando l'import ha successo.

Il progetto segue la specifica funzionale in:

- `../docs/progetto-bandi-psicologia/SPECIFICA_FUNZIONALE_MVP.md`

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL/SQLite in sviluppo
- Frontend: Streamlit per Community Cloud; React + Vite per embed iframe
- Import: pipeline Python modulare con classificazione rule-based
- Search MVP: filtro full-text su database, predisposto per motore dedicato
- DevOps: Docker Compose con backend, frontend e PostgreSQL

## Struttura

```text
bandi-psicologia/
  .github/         aggiornamento automatico dell'archivio pubblico
  .streamlit/      tema e configurazione dell'interfaccia pubblica
  backend/        API, modelli, importers, classificazione, test
  data/           snapshot SQLite pubblico generato automaticamente
  frontend/       widget React/Vite embeddabile
  docs/           note tecniche e contratto API
  scripts/        comandi PowerShell di supporto
```

## Deploy su Streamlit Community Cloud

L'interfaccia Streamlit legge in sola lettura `data/bandi.sqlite`: non richiede
FastAPI, React, Docker, PostgreSQL, account aggiuntivi o Secrets. GitHub Actions
interroga le fonti pubbliche due volte al giorno, genera uno snapshot SQLite
minimizzato e lo salva nel repository soltanto quando i dati cambiano. Il nuovo
commit provoca automaticamente il redeploy di Streamlit Community Cloud.

Le fonti con adapter specifici vengono controllate a ogni esecuzione. I cataloghi
più ampi usano invece lotti deterministici che cambiano ogni 12 ore: 50 fonti
generiche, 15 fonti sanitarie mirate e 12 adapter profondi. La configurazione
garantisce la copertura teorica completa rispettivamente entro 36, 36 e 48 ore,
salvo timeout o indisponibilità dei siti remoti. Il riepilogo di ogni esecuzione
Actions mostra sia il lotto pianificato sia le fonti effettivamente interrogate.

Configurazione dell'app in <https://share.streamlit.io>:

```text
Repository: LPDgit1/Psy-Bandi
Branch: main
Main file path: backend/streamlit_app.py
Python: 3.12
```

Non inserire valori in `Advanced settings > Secrets`: questa configurazione non ne
usa. Al primo push delle modifiche il workflow parte automaticamente. Per avviarlo
a mano: apri il repository su GitHub, scegli `Actions`, poi
`Aggiorna archivio bandi`, `Run workflow` e conferma su `main`.

Lo snapshot pubblicato contiene solo le tabelle pubbliche di fonti, opportunità e
allegati. Alert, email, log di import, audit, note redazionali, errori tecnici e testo
estratto dagli allegati non vengono esportati.

Per provare Streamlit in locale:

```powershell
cd bandi-psicologia
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python -m app.scripts.build_public_snapshot --output data\bandi.sqlite
.\.venv\Scripts\python -m streamlit run backend\streamlit_app.py
```

Il comando di generazione richiede accesso Internet alle sole fonti pubbliche. Per
provare l'interfaccia con uno snapshot in un percorso diverso si può impostare la
variabile locale `PUBLIC_SNAPSHOT_PATH`; non è una credenziale.

## Avvio con Docker

Richiede Docker con accesso a registry pubblici.

```powershell
cd bandi-psicologia
Copy-Item .env.example .env
docker compose up --build
```

Servizi:

- Backend API: http://localhost:8000
- Documentazione OpenAPI: http://localhost:8000/docs
- Frontend widget: http://localhost:5173
- Embed demo: http://localhost:5173/?tenant=ordine-demo&region=Lazio&defaultStatus=open

## Avvio locale backend

```powershell
cd bandi-psicologia\backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python -m app.scripts.seed
.\.venv\Scripts\uvicorn app.main:app --reload
```

Se `DATABASE_URL` non e' definito, il backend usa SQLite locale (`bandi_dev.db`) per prototipazione.

## Avvio locale frontend

```powershell
cd bandi-psicologia\frontend
npm install
Copy-Item .env.example .env
npm run dev
```

## Aggiornare una installazione Docker esistente

Da PowerShell:

```powershell
cd C:\percorso\Psy-Bandi
docker compose down
docker compose up --build
```

Il backend aggiorna inPA, Azienda Zero Veneto, Azienda Zero Piemonte, ARCS FVG,
ASUIT Trentino, ASDAA Alto Adige, AUSL Romagna, USL Umbria 2, ASL Roma 2,
Comune di Venezia, MyPortal Comune di Treviso, INAIL e INPS all'avvio.

Nel widget il pulsante con icona di aggiornamento rilancia tutte le fonti attive
e ricarica automaticamente l'elenco. Il backend applica un intervallo minimo di
5 minuti tra due richieste pubbliche. Per rilanciare manualmente l'aggiornamento
completo, incluso il probe del catalogo:

```powershell
docker compose exec backend python -m app.scripts.import_real --remove-demo --probe-local-sources
```

## Alert ed email

In locale gli alert usano una consegna email sicura in modalita file:

- quando un utente crea un alert, il backend genera una email di conferma;
- le email vengono salvate in `tmp/email_outbox` dentro il container backend;
- ogni invio viene tracciato nella tabella `email_logs`;
- il report alert include titolo, ente, regione, scadenza e link alla fonte.

Per inviare email reali basta configurare `EMAIL_DELIVERY_MODE=smtp` e le
variabili `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` e
`SMTP_USE_TLS` nel file `.env`.

Se la rete locale intercetta HTTPS e l'import segnala un errore certificato,
installare nel container la CA attendibile della propria rete. Non disabilitare
globalmente la verifica TLS: le fonti con catene remote incomplete o transitorie
restano visibili nel probe come `tls-review`.

## Funzioni gia scaffoldate

- API pubbliche per lista, dettaglio, faccette e alert
- API admin minime con token bearer
- modello dati SQLAlchemy per opportunita, fonti, allegati, alert e audit
- importer reale inPA tramite endpoint pubblico usato dalla pagina ufficiale
- importer Azienda Zero Veneto tramite endpoint JSON pubblico
- importer Azienda Zero Piemonte tramite sezioni HTML pubbliche paginate
- importer ARCS Friuli-Venezia Giulia tramite lista e dettaglio HTML pubblici
- importer ASUIT Trentino tramite lista Drupal filtrata e dettaglio HTML pubblico
- importer ASDAA Alto Adige sui soli metadati della tabella pubblica consentita
- importer AUSL Romagna tramite feed JSON pubblici Plone delle selezioni
- importer USL Umbria 2 tramite tabelle HTML pubbliche delle selezioni
- importer ASL Roma 2 tramite tabella HTML pubblica con ricerca server-side
- importer Comune di Venezia tramite tabella HTML pubblica
- importer MyPortal Veneto riusabile, attivo sul catalogo JSON pubblico di Treviso
- importer INAIL limitato alle pagine recenti dell'archivio pubblico degli avvisi
- importer INPS tramite endpoint JSON pubblico richiamato dalla lista ufficiale
- catalogo ministeriale per Ministero del Lavoro, Ministero dell'Istruzione e
  MAECI; MAECI resta in revisione tecnica per protezione anti-bot
- catalogo e probe per fonti istituzionali pubbliche aperte
- seed/importer dimostrativo opzionale con bandi realistici
- classificatore rule-based per pertinenza, ambiti, requisiti e tipologia
- frontend Streamlit con ricerca, filtri e collegamento diretto alle fonti ufficiali
- test unitari per classificazione, date e deduplicazione

## Fonti collegate

- inPA: importer attivo
- Azienda Zero Veneto: importer sanitario attivo
- Azienda Zero Piemonte: importer HTML sanitario attivo
- ARCS Friuli-Venezia Giulia: importer HTML sanitario attivo
- ASUIT Trentino: importer HTML sanitario attivo
- ASDAA Alto Adige: importer tabellare sanitario attivo sui soli metadati
- AUSL Romagna: importer JSON sanitario attivo sulle pagine recenti
- USL Umbria 2: importer HTML sanitario attivo sulle sezioni pubbliche
- ASL Roma 2: importer HTML attivo
- Comune di Venezia: importer HTML attivo
- Comune di Treviso: importer MyPortal JSON attivo
- INAIL: importer HTML prudente sulle pagine recenti degli avvisi attivo
- INPS: importer JSON filtrato sui concorsi e mobilita attivo
- Ministero del Lavoro e Ministero dell'Istruzione: fonti pubbliche catalogate
  per concorsi, avvisi e bandi
- Ministero degli Esteri: fonte ufficiale catalogata, ma non ancora refreshata
  automaticamente per protezione anti-bot osservata in verifica
- Gazzetta Ufficiale e Regione Veneto: fonti pubbliche catalogate
- Universita del Nord Italia: rete iniziale di hub pubblici catalogati e verificabili
- aziende sanitarie territoriali del Nord Italia: rete regionale catalogata con
  pagine ASL dirette e hub centralizzati compatibili con le policy pubbliche
- aziende ospedaliere, AOU e IRCCS: 30 fonti pubbliche catalogate per adapter
  dedicati o revisione tecnica, senza refresh automatico generico finche non si
  conferma una struttura stabile
- aziende sanitarie territoriali di Marche e Umbria: ingressi ufficiali
  catalogati; AUSL Romagna e USL Umbria 2 sono gia automatizzate
- capoluoghi di provincia del Veneto: Belluno, Padova, Rovigo, Treviso, Venezia, Verona e Vicenza
- Roma Capitale: pagina pubblica verificata, con possibile sovrapposizione inPA

Il portale "Concorsi in Veneto" rimane una fonte di discovery: pubblica tabelle
incorporate tramite Google Apps Script, senza un'interfaccia dati stabile documentata.

Belluno e Rovigo usano MyPortal come porta d'ingresso, ma delegano i bandi a
piattaforme collegate distinte. Restano catalogati per i prossimi adapter dedicati.

INAIL richiede un profilo TLS dedicato: il backend limita quella singola
connessione a TLS 1.2 con la suite accettata dal server, mantenendo verifica CA e
hostname attive.

L'elenco tecnico completo, le priorita di sviluppo e i criteri per un riuso prudente
sono descritti in `docs/FONTI_PILOTA.md`. Le matrici sanitarie regionali e le
eccezioni `robots.txt` sono riportate in `docs/FONTI_SANITARIE_NORD.md` e
`docs/FONTI_SANITARIE_CENTRO.md`.

## Credenziali admin locali

Definire nel file `.env` locale, non versionato:

- email: `<ADMIN_EMAIL>`
- password: `<ADMIN_PASSWORD>`
- token bearer: `<ADMIN_API_TOKEN>`

Il backend rifiuta l'accesso amministrativo se una variabile non è configurata.
