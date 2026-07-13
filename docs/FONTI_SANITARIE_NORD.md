# Fonti sanitarie territoriali del Nord Italia

Verifica eseguita il 31 maggio 2026 sulle fonti ufficiali aperte delle aziende
sanitarie territoriali del Nord Italia. Il perimetro include AULSS, ASL, ASST e
denominazioni regionali equivalenti. Aziende ospedaliere, AOU e IRCCS potranno
essere aggiunti in una estensione successiva.

## Copertura regionale

| Regione | Perimetro territoriale | Fonte collegata | Stato |
| --- | --- | --- | --- |
| Valle d'Aosta | Azienda USL regionale | USL Valle d'Aosta | Pagina diretta catalogata |
| Piemonte | 12 ASL | Azienda Zero Piemonte e pagine dirette ASL | Adapter Azienda Zero attivo; ASL BI manuale |
| Liguria | ATS Liguria con aree 1-5 | ATS Liguria - Bandi di concorso | Hub corrente catalogato e raggiungibile |
| Lombardia | Rete ASST | Pagina riepilogativa SSR Lombardia | Hub regionale catalogato |
| Trentino | ASUIT | ASUIT - Bandi e concorsi | Adapter HTML filtrato attivo |
| Alto Adige | Azienda sanitaria provinciale | ASDAA - Concorsi in atto | Adapter tabellare sui soli metadati attivo |
| Veneto | 9 AULSS | Azienda Zero Veneto | Adapter JSON gia attivo |
| Friuli-Venezia Giulia | ASUFC, ASUGI e ASFO | ARCS FVG | Adapter HTML attivo |
| Emilia-Romagna | 8 Aziende Usl | Portale Salute Emilia-Romagna | Hub regionale catalogato |

Il catalogo preferisce una fonte regionale centralizzata quando esiste ed e
aperta. Questo evita richieste duplicate, conserva un punto di controllo chiaro
e facilita la deduplicazione con inPA.

## Inventario degli hub regionali

### Veneto

L'[elenco ufficiale regionale](https://salute.regione.veneto.it/aziende-sanitarie-del-veneto)
comprende 9 aziende territoriali: ULSS 1 Dolomiti, ULSS 2 Marca Trevigiana,
ULSS 3 Serenissima, ULSS 4 Veneto Orientale, ULSS 5 Polesana, ULSS 6 Euganea,
ULSS 7 Pedemontana, ULSS 8 Berica e ULSS 9 Scaligera. I concorsi sono coperti
dall'adapter gia attivo di Azienda Zero Veneto.

### Lombardia

La [pagina regionale sulle ASST](https://www.regione.lombardia.it/sanita/strutture-sanitarie-e-sociosanitarie/aziende-socio-sanitarie-territoriali-asst/aziende-socio-sanitarie-territoriali)
aggiornata il 5 maggio 2026 dichiara 27 ASST. L'elenco pubblicato contiene 26
voci ASST e la voce `IRCCS San Gerardo dei Tintori`, subentrata nel perimetro di
Monza. La discrepanza va mantenuta visibile durante lo sviluppo dell'adapter.

Le 26 ASST elencate sono: Papa Giovanni XXIII, Bergamo Ovest, Bergamo Est,
Spedali Civili di Brescia, Franciacorta, Garda, Lecco, Brianza, Grande Ospedale
Metropolitano Niguarda, Santi Paolo e Carlo, Fatebenefratelli Sacco, Gaetano
Pini-CTO, Ovest Milanese, Rhodense, Nord Milano, Melegnano e Martesana, Lodi,
Sette Laghi, Valle Olona, Lariana, Valtellina e Alto Lario, Valcamonica, Pavia,
Cremona, Mantova e Crema.

La fonte operativa selezionata e la [pagina regionale dei concorsi SSR](https://www.regione.lombardia.it/sanita/personale-sanitario-e-sociosanitario/concorsi-e-avvisi-presso-enti-sanitari/concorsi-e-avvisi-presso-enti-sanitari),
che pubblica un riepilogo periodico e rimanda ai siti aziendali per i dettagli.

### Friuli-Venezia Giulia

La [pagina regionale SSR](https://www.regione.fvg.it/rafvg/cms/RAFVG/salute-sociale/sistema-sociale-sanitario/)
elenca le tre aziende territoriali: ASUGI, ASUFC e ASFO. La fonte selezionata e
ARCS, che pubblica concorsi, avvisi e incarichi regionali.

### Emilia-Romagna

Il [portale regionale dei concorsi sanitari](https://salute.regione.emilia-romagna.it/trasparenza/bandi-concorsi-e-avvisi)
rimanda alle 8 AUSL territoriali: Piacenza, Parma, Reggio Emilia, Modena,
Bologna, Imola, Ferrara e Romagna.

## Piemonte

| Ente | URL | Nota |
| --- | --- | --- |
| Azienda Zero Piemonte | `https://www.aziendazero.piemonte.it/concorsiaz0/concorsi-pubblici/` | Adapter HTML paginato attivo |
| ASL AL | `https://www.aslal.it/bandi-di-concorso` | Pagina diretta aperta |
| ASL AT | `https://trasparenza.asl.at.it/DL33/concorsiinvigore.xml` | Indice XML pubblico |
| ASL BI | `https://trasparenza.aslbi.piemonte.it/bandi-concorso-reclutamento-personale?sf=102` | Solo verifica manuale: `robots.txt` vieta il crawl |
| ASL CN1 | `https://www.aslcn1.it/amministrazione-trasparente/bandi-di-concorso/concorsi-pubblici-e-avvisi` | Pagina diretta aperta |
| ASL CN2 | `https://www.aslcn2.it/azienda-asl-cn2/amministrazione-trasparente/bandi-di-concorso/` | Hub diretto aperto |
| ASL NO | `https://concorsi.asl.novara.it/` | Portale dedicato aperto |
| ASL Citta di Torino | `https://www.aslcittaditorino.it/concorsi-pubblici/` | Pagina diretta aperta |
| ASL TO3 | `https://trasparenzaap.aslto3.piemonte.it/web/trasparenza/trasparenza` | Catena TLS remota incompleta dal container |
| ASL TO4 | `https://www.aslto4.piemonte.it/concorsi/` | Pagina diretta aperta |
| ASL TO5 | `https://www.aslto5.piemonte.it/it/trasparenza/bandi-concorso` | Pagina diretta aperta |
| ASL VC | `https://aslvc.piemonte.it/albo-pretorio/concorsi/` | Pagina diretta aperta |
| ASL VCO | `https://www.aslvco.it/lasl-informa/concorsi-e-selezioni/` | Pagina diretta aperta |

`ASL BI` rimane documentata ma non entra nel probe automatico. Per `ASL TO3`
resta attiva la normale verifica dei certificati: non viene applicata alcuna
deroga TLS globale.

## Liguria

Dal 1 gennaio 2026 le cinque aziende sociosanitarie liguri e Liguria Salute sono
confluite in `ATS Liguria`. La fonte operativa corrente e:

`https://www.atsliguria.it/amministrazione-trasparente-ats/amministrazione-trasparente/bandi-di-concorso.html`

L'hub ufficiale espone le aree 1-5 e l'area Liguria Salute. Il dominio risulta
indicizzato e pubblicato dal sito istituzionale. Durante la verifica Windows lo
risolve correttamente, mentre il resolver interno del container Docker non
risolve in modo stabile la catena CNAME. Un probe intermedio ha raggiunto la
pagina, mentre il probe finale e tornato in stato `unreachable`: l'anomalia resta
annotata per monitoraggio.

I siti storici `asl1.liguria.it` - `asl5.liguria.it` possono essere utili per
procedure precedenti alla fusione, ma non sono trattati come fonti operative.
Anche il precedente portale ALISA resta escluso dagli adapter: il relativo
`robots.txt` vieta il crawl delle procedure.

## Hub delle altre regioni

| Regione | Fonte | URL |
| --- | --- | --- |
| Lombardia | Concorsi e avvisi presso enti sanitari | `https://www.regione.lombardia.it/sanita/personale-sanitario-e-sociosanitario/concorsi-e-avvisi-presso-enti-sanitari/concorsi-e-avvisi-presso-enti-sanitari` |
| Emilia-Romagna | Bandi, concorsi e avvisi | `https://salute.regione.emilia-romagna.it/trasparenza/bandi-concorsi-e-avvisi` |
| Friuli-Venezia Giulia | ARCS - Concorsi, avvisi e incarichi | `https://arcs.sanita.fvg.it/it/professionisti-e-fornitori/concorsi-avvisi-incarichi` |
| Trentino | ASUIT - Bandi e concorsi | `https://www.asuit.tn.it/bandi-concorsi?combine=psicolog` |
| Alto Adige | ASDAA - Concorsi in atto | `https://home.asdaa.it/it/amministrazione-trasparente/info-concorsi.asp` |
| Valle d'Aosta | USL - Concorsi e selezioni | `https://www.ausl.vda.it/concorsi-e-selezioni/concorsi-e-selezioni` |
| Veneto | Azienda Zero - Concorsi e avvisi | `https://www.azero.veneto.it/concorsi-e-avvisi` |

La pagina SSR della Lombardia pubblica riepiloghi periodici per gli enti del
sistema sociosanitario. Prima di creare adapter ASST singoli conviene verificare
quanto copre il riepilogo regionale e gestire separatamente l'evoluzione
organizzativa di IRCCS San Gerardo.

## Priorita adapter

Adapter completati:

1. Azienda Zero Piemonte, sulle cinque sezioni pubbliche paginate.
2. ARCS Friuli-Venezia Giulia, con filtro sulla lista e dettaglio richiesto solo
   per profili psicologici espliciti.
3. ASUIT Trentino, con filtro pubblico `psicolog`, lista paginata e dettaglio
   richiesto solo per profili professionali espliciti.
4. ASDAA Alto Adige, sulla tabella pubblica consentita: importa solo i metadati
   delle procedure pertinenti e non visita l'area documentale `/cv/`.

Verifica reale eseguita il 31 maggio 2026:

- Azienda Zero Piemonte ha restituito 4 procedure psicologiche storiche, tutte
  gia scadute e quindi importate come record nascosti;
- ARCS FVG ha restituito 4 procedure correnti, nessuna delle quali contiene un
  profilo psicologico esplicito;
- ASUIT Trentino ha restituito 16 schede filtrate, di cui 8 riferite a profili
  psicologici espliciti: sono procedure storiche concluse e restano nascoste
  dalla ricerca corrente;
- ASDAA Alto Adige ha restituito 28 procedure in atto, nessuna riferita a un
  profilo psicologico esplicito;
- il secondo import aggiorna i record esistenti senza crearne duplicati.

Prossimi adapter:

1. Altre AUSL Emilia-Romagna, trattate per famiglia tecnica a partire dai link
   dell'hub regionale. AUSL Romagna e' ora coperta da adapter JSON pubblico.
2. Famiglie piemontesi riusabili, iniziando dall'indice XML DL33 di ASL AT.
3. ATS Liguria, mantenendo il monitoraggio DNS del dominio ufficiale.
4. Riepiloghi SSR Lombardia, dopo verifica del formato degli allegati periodici.

Non sviluppare adapter automatici per `ASL BI` o per le procedure del precedente
portale `ALISA` senza una modifica esplicita delle rispettive policy pubbliche.
