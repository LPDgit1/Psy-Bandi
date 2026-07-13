# Fonti sanitarie territoriali: Emilia-Romagna, Marche e Umbria

Verifica eseguita il 31 maggio 2026 su pagine istituzionali pubbliche, con
validazione TLS attiva e frequenza di lettura moderata.

## Fonti automatizzate

| Regione | Fonte | URL | Stato |
| --- | --- | --- | --- |
| Emilia-Romagna | AUSL Romagna | `https://www.auslromagna.it/pubblicita-legale/selezioni-del-personale/concorsi-selezioni-romagna` | Adapter JSON attivo |
| Umbria | USL Umbria 2 | `https://www.uslumbria2.it/pagine/concorsi-001` | Adapter HTML attivo |

AUSL Romagna pubblica feed JSON Plone per le categorie di selezione. L'adapter
legge solo poche pagine recenti, filtra i profili psicologici prima di aprire il
dettaglio e conserva soltanto i documenti iniziali essenziali.

USL Umbria 2 pubblica tabelle HTML per concorsi, assunzioni, mobilita e incarichi
libero-professionali. L'adapter apre solo le schede psicologiche e non importa
graduatorie, commissioni, esiti o elenchi candidati.

Verifica reale del 31 maggio 2026:

- AUSL Romagna ha importato 4 procedure psicologiche storiche;
- USL Umbria 2 ha importato 1 procedura psicologica storica;
- tutte le 5 procedure sono scadute e restano correttamente nascoste dalla
  ricerca corrente;
- il refresh pubblico completo ha verificato 13 fonti attive senza errori.

## Marche

Il precedente portale ASUR dichiara che dal 18 settembre 2025 sono attivi i nuovi
siti delle Aziende Sanitarie Territoriali. Le cinque liste ufficiali sono
raggiungibili via HTTPS e condividono una struttura pubblica Next.js:

| Fonte | URL |
| --- | --- |
| AST Pesaro Urbino | `https://www.astpu.marche.it/ast-comunica/concorsi` |
| AST Ancona | `https://www.astancona.marche.it/ast-comunica/concorsi` |
| AST Macerata | `https://www.astmc.marche.it/ast-comunica/concorsi` |
| AST Fermo | `https://www.astfm.marche.it/ast-comunica/concorsi` |
| AST Ascoli Piceno | `https://www.astap.marche.it/ast-comunica/concorsi` |

Le fonti sono catalogate e pronte per un adapter condiviso. Prima
dell'automazione conviene isolare il contratto dati pubblico usato dal frontend,
anziche dipendere dal formato serializzato interno delle pagine Next.js.

## Umbria

| Fonte | URL | Stato |
| --- | --- | --- |
| USL Umbria 1 | `https://www.uslumbria1.it/per-gli-operatori-della-sanita/concorsi-e-mobilita/` | Catalogata, adapter WordPress da sviluppare |
| USL Umbria 2 | `https://www.uslumbria2.it/pagine/concorsi-001` | Adapter HTML attivo |

Il `robots.txt` di USL Umbria 1 consente la consultazione pubblica. USL Umbria 2
non espone un file `robots.txt` dedicato, quindi l'adapter resta volutamente
limitato alle cinque sezioni di selezione e ai soli dettagli pertinenti.
