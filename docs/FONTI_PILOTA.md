# Fonti pilota

Il servizio usa inPA come prima fonte attiva e mantiene un catalogo di pagine
istituzionali pubbliche da trasformare progressivamente in adapter automatici.

## Fonte attiva

1. inPA
   - Endpoint pubblico identificato dalla pagina ufficiale e collegato.
   - Campi prioritari: titolo, ente, regione, stato, scadenza, descrizione,
     allegati e link ufficiale.
   - Deduplicazione basata sull'identificativo inPA.

## Fonti nazionali e regionali

| Fonte | URL | Uso previsto |
| --- | --- | --- |
| Gazzetta Ufficiale - 4a Serie Speciale | `https://www.gazzettaufficiale.it/30giorni/concorsi` | Controllo nazionale e discovery |
| INAIL - Avvisi | `https://www.inail.it/portale/it/inail-comunica/avvisi.html` | Adapter HTML attivo sulle sole pagine recenti |
| INPS - Concorsi e Mobilita | `https://www.inps.it/it/it/avvisi-bandi-e-fatturazione/fatturazione-concorsi.html` | Adapter JSON filtrato attivo |
| Regione Veneto - Concorsi in Veneto | `https://concorsi.regione.veneto.it/` | Discovery settimanale degli enti veneti |
| Regione Veneto - Bandi Avvisi Concorsi | `https://bandi.regione.veneto.it/` | Adapter regionale con scadenzario |
| Azienda Zero Veneto | `https://www.azero.veneto.it/concorsi-e-avvisi` | Adapter JSON sanitario attivo |

Il portale "Concorsi in Veneto" dichiara esplicitamente che il proprio elenco non
e esaustivo. Va quindi usato come fonte di discovery, non come unica sorgente. Le
tabelle pubbliche sono incorporate tramite Google Apps Script e non espongono un
formato dati stabile documentato: non vengono importate automaticamente.

Per INAIL viene usato soltanto l'archivio pubblico generale degli avvisi, con
scansione limitata alle pagine piu recenti. Il file `https://www.inail.it/robots.txt`
esclude le sezioni di Amministrazione Trasparente: l'adapter non le consulta.
Il server INAIL non accetta il ClientHello moderno predefinito di Python/OpenSSL:
il solo adapter INAIL usa TLS 1.2 con `AES256-GCM-SHA384`, mantenendo verifica CA
e hostname attive.
Per INPS il file `https://www.inps.it/robots.txt` consente la lista pubblica e la
pagina ufficiale richiama un endpoint JSON filtrabile.

## Capoluoghi di provincia del Veneto

| Ente | URL | Famiglia tecnica |
| --- | --- | --- |
| Comune di Belluno | `https://www.comune.belluno.it/amministrazionetrasparente/_05_bandi_di_concorso` | MyPortal Veneto con rinvio a pagina storica separata |
| Comune di Padova | `https://www.comune.padova.it/amministrazione-trasparente/bandi-di-concorso` | Hub HTML |
| Comune di Rovigo | `https://www.comune.rovigo.it/amministrazionetrasparente/bandi-di-concorso` | MyPortal Veneto con rinvio a portale trasparenza Liferay |
| Comune di Treviso | `https://www.comune.treviso.it/amministrazionetrasparente/_05_bandi_di_concorso` | MyPortal Veneto, adapter JSON attivo |
| Comune di Venezia | `https://www.comune.venezia.it/node/6313` | Tabella HTML, adapter attivo |
| Comune di Verona | `https://www.comune.verona.it/Amministrazione-Trasparente/Bandi-di-concorso` | Hub HTML |
| Comune di Vicenza | `https://servizi2.comune.vicenza.it/amministrazione/trasparente/cmsammtrasparente.php/bandi_di_concorso` | Hub HTML con elenco collegato |

Le installazioni MyPortal condividono la stessa famiglia tecnica, ma non la stessa
modalita di pubblicazione dei concorsi. L'adapter JSON riusabile e attivo per
Treviso. Belluno rinvia alla propria sezione storica
`https://www.comune.belluno.it/amministrazione/attipubblicazioni/concorsi`;
Rovigo rinvia a `https://rovigo.trasparenza-valutazione-merito.it/`.
Questi due casi richiedono adapter separati delle piattaforme collegate.

## Universita del Nord Italia

### Valle d'Aosta, Piemonte e Liguria

| Ateneo | URL |
| --- | --- |
| Universita della Valle d'Aosta | `https://www.univda.it/trasparenza/bandi-di-concorso/` |
| Universita di Torino | `https://www.unito.it/ateneo/concorsi-e-selezioni` |
| Universita del Piemonte Orientale | `https://www.uniupo.it/it/concorsi` |
| Politecnico di Torino | `https://www.polito.it/ateneo/lavora-e-collabora-con-noi/concorsi-e-selezioni` |
| Universita di Genova | `https://unige.it/concorsi` |

### Lombardia e Trentino-Alto Adige

| Ateneo | URL |
| --- | --- |
| Universita di Milano | `https://www.unimi.it/it/ateneo/lavora-con-noi/tutti-i-concorsi` |
| Universita di Milano-Bicocca | `https://www.unimib.it/concorsi` |
| Universita di Pavia | `https://portale.unipv.it/it/ateneo/organizzazione/bandi-e-concorsi` |
| Universita dell'Insubria | `https://www.uninsubria.it/bandi-e-concorsi` |
| Universita di Bergamo | `https://www.unibg.it/ateneo/amministrazione/concorsi-e-selezioni` |
| Universita di Brescia | `https://www.unibs.it/it/ateneo/amministrazione/concorsi` |
| Politecnico di Milano | `https://dynamicpoli.polimi.it/staff/lavora-con-noi/bandi-e-concorsi` |
| Universita di Trento | `https://lavoraconnoi.unitn.it/pta-cel` |

### Veneto e Friuli-Venezia Giulia

| Ateneo | URL |
| --- | --- |
| Universita di Verona | `https://www.univr.it/it/concorsi` |
| Universita di Padova | `https://www.unipd.it/concorsi` |
| Universita Ca' Foscari Venezia | `https://www.unive.it/lavoraconnoi` |
| Universita Iuav di Venezia | `https://www.iuav.it/it/ateneo/bandi-concorsi` |
| Universita di Trieste | `https://www.units.it/en/node/44` |
| Universita di Udine | `https://www.uniud.it/it/ateneo-uniud/concorsi-bandi-uniud` |

### Emilia-Romagna

| Ateneo | URL |
| --- | --- |
| Universita di Bologna | `https://www.unibo.it/it/ateneo/amministrazione-trasparente/bandi-di-concorso` |
| Universita di Parma | `https://www.unipr.it/concorsi-e-mobilita` |
| Universita di Modena e Reggio Emilia | `https://amministrazionetrasparente.unimore.it/pagina639_bandi-di-concorso.html` |
| Universita di Ferrara | `https://www2.unife.it/at/bandi-di-concorso` |

La Libera Universita di Bolzano dispone di una pagina ufficiale pubblica, ma
richiede una verifica separata delle regole di crawling prima di essere inserita
nel probe automatico.

## Esito probe

Verifica eseguita il 31 maggio 2026:

- 65 fonti istituzionali catalogate;
- 61 fonti raggiungibili direttamente dal container Docker;
- 3 fonti in stato `tls-review`: Regione Veneto - Bandi Avvisi Concorsi,
  Universita Iuav di Venezia e ASL TO3 - Portale trasparenza;
- 1 fonte in stato `unreachable`: ATS Liguria - Bandi di concorso. Windows
  risolve il dominio ufficiale, mentre il resolver interno Docker non risolve
  stabilmente la catena CNAME;
- Regione Veneto invia una catena di transizione Actalis che termina sulla root
  `Actalis TLS Server RSA Root CA 2025`, non accettata dal bundle standard del
  container;
- IUAV invia il certificato foglia emesso da `Let's Encrypt R12`, ma non
  l'intermedio necessario alla verifica server-side;
- ASL TO3 espone una catena TLS incompleta dal proprio portale trasparenza
  collegato;
- nessuna fonte viene forzata disabilitando globalmente la verifica TLS.

## Altre fonti gia catalogate

| Fonte | URL |
| --- | --- |
| ASL Roma 2 | `https://www.aslroma2.it/external/concorsi/index.php` |
| Roma Capitale | `https://www.comune.roma.it/web/it/amministrazione-trasparente-bandi-di-concorso.page` |

Le aziende sanitarie territoriali del Nord Italia sono censite separatamente in
`docs/FONTI_SANITARIE_NORD.md`: il catalogo include hub regionali e pagine
dirette compatibili con le policy pubbliche, senza forzare i casi esclusi da
`robots.txt`.

## Confine di riuso

Il fatto che una pagina sia pubblica e istituzionale consente consultazione,
discovery e collegamento alla fonte. Non implica automaticamente la facolta di
ripubblicare integralmente ogni contenuto o allegato.

Per ogni nuovo adapter:

- verificare `robots.txt`, note legali e termini d'uso del dominio;
- applicare una frequenza moderata e cache locale;
- raccogliere solo i metadati necessari alla ricerca;
- mantenere sempre il link alla pagina ufficiale;
- non duplicare allegati se non strettamente necessario;
- evitare la ripubblicazione di dati personali non necessari;
- deduplicare i record rispetto a inPA.

## Priorita adapter

Adapter completati:

1. Azienda Zero Veneto, tramite endpoint JSON pubblico.
2. ASL Roma 2, tramite tabella HTML e ricerca server-side.
3. Comune di Venezia, tramite tabella HTML pubblica.
4. Comune di Treviso, tramite catalogo JSON pubblico MyPortal.
5. INAIL, tramite scansione limitata delle pagine recenti degli avvisi pubblici.
6. INPS, tramite endpoint JSON pubblico con filtri professionali.
7. Azienda Zero Piemonte, tramite sezioni HTML pubbliche paginate.
8. ARCS Friuli-Venezia Giulia, tramite lista e dettaglio HTML pubblici.
9. ASUIT Trentino, tramite lista Drupal pubblica filtrata e dettaglio HTML.
10. ASDAA Alto Adige, tramite tabella pubblica consentita e soli metadati.
11. AUSL Romagna, tramite feed JSON pubblici Plone delle selezioni.
12. USL Umbria 2, tramite tabelle HTML pubbliche delle selezioni.

Prossimi adapter:

1. AST Marche, riusando il formato pubblico Next.js dei cinque nuovi siti.
2. USL Umbria 1, con adapter WordPress dedicato.
3. Altre AUSL Emilia-Romagna, separando le famiglie tecniche collegate dall'hub.
4. Comune di Belluno, per la sezione storica collegata da MyPortal.
5. Comune di Rovigo, per il portale trasparenza Liferay collegato da MyPortal.
6. Universita con maggiore probabilita di opportunita psicologiche: Padova,
   Verona, Milano-Bicocca, Torino e Bologna.

## Checklist nuovo importer

- identificare URL sorgente;
- verificare policy di accesso;
- definire frequenza aggiornamento;
- implementare fetch lista;
- implementare fetch dettaglio;
- estrarre allegati solo se necessario;
- normalizzare date;
- calcolare `content_hash`;
- applicare classificazione;
- registrare import run;
- creare test fixture con HTML o PDF rappresentativo.
