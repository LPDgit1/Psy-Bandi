# Fonti sanitarie territoriali nazionali

Verifica tecnica aggiornata al 10 luglio 2026. Il perimetro copre le aziende
sanitarie territoriali o equivalenti regionali: ASL, AUSL, AULSS, ASP, ATS, AST,
USL, ASReM, aziende sanitarie provinciali e hub regionali tipo Azienda Zero,
ARES, ESTAR e ARCS.

## Stato sintetico

- Fonti sanitarie automatizzabili o refreshabili in catalogo: 117.
- Fonti sanitarie documentate ma non automatizzate: 2.
- Fonti ospedaliere, AOU e IRCCS catalogate per adapter/revisione: 30.
- Test automatici di copertura nazionale: attivi in `test_source_catalog.py`.
- Adapter profondi gia attivi: inPA, Azienda Zero Veneto, Azienda Zero Piemonte,
  ARCS FVG, ASUIT Trentino, ASDAA Alto Adige, AUSL Romagna, USL Umbria 1,
  USL Umbria 2, ASL Roma 2, PugliaSalute AOL, target health HTML e catalogo
  generico.

## Copertura regionale

| Regione | Copertura |
| --- | --- |
| Valle d'Aosta | Azienda USL Valle d'Aosta |
| Piemonte | Azienda Zero Piemonte; ASL AL, AT, BI, CN1, CN2, Citta di Torino, NO, TO3, TO4, TO5, VC, VCO |
| Liguria | ATS Liguria, equivalente regionale dal 2026 |
| Lombardia | ATS Bergamo, Brescia, Brianza, Insubria, Milano, Montagna, Pavia, Val Padana; hub Regione Lombardia |
| Trentino-Alto Adige | ASUIT Trentino; Azienda Sanitaria dell'Alto Adige |
| Veneto | Azienda Zero Veneto; AULSS 1-9 |
| Friuli-Venezia Giulia | ARCS FVG, hub operativo per ASUFC, ASUGI e ASFO |
| Emilia-Romagna | AUSL Piacenza, Parma, Reggio Emilia, Modena, Bologna, Imola, Ferrara, Romagna |
| Toscana | ESTAR; AUSL Toscana Centro, Nord Ovest, Sud Est |
| Umbria | USL Umbria 1 e USL Umbria 2 |
| Marche | AST Pesaro Urbino, Ancona, Macerata, Fermo, Ascoli Piceno |
| Lazio | ASL Roma 1-6, Frosinone, Latina, Rieti, Viterbo |
| Abruzzo | ASL Avezzano Sulmona L'Aquila, Lanciano Vasto Chieti, Pescara, Teramo |
| Molise | ASReM |
| Campania | ASL Avellino, Benevento, Caserta, Napoli 1 Centro, Napoli 2 Nord, Napoli 3 Sud, Salerno |
| Puglia | ASL Bari, Foggia, BT, Taranto, Brindisi, Lecce; PugliaSalute AOL |
| Basilicata | ASP Basilicata; ASM Matera |
| Calabria | ASP Catanzaro, Cosenza, Crotone, Reggio Calabria, Vibo Valentia |
| Sicilia | ASP Agrigento, Caltanissetta, Catania, Enna, Messina, Palermo, Ragusa, Siracusa, Trapani |
| Sardegna | ARES, AREUS; ASL Sassari, Gallura, Nuoro, Ogliastra, Oristano, Medio Campidano, Sulcis, Cagliari |

## Eccezioni non automatizzate

- ASL BI: fonte documentata, ma non inserita nel refresh automatico perche la
  verifica precedente del `robots.txt` vietava il crawl delle procedure.
- Azienda Zero Calabria: equivalente regionale individuato, ma non e stata
  confermata una fonte concorsi pubblica stabile e risolvibile per import
  automatico. La copertura operativa rimane sulle cinque ASP calabresi.

## Note tecniche

Le fonti centralizzate regionali restano preferite quando sono la via
istituzionale piu affidabile per i concorsi sanitari: Azienda Zero Veneto,
Azienda Zero Piemonte, ESTAR Toscana, ARES Sardegna, ARCS FVG e PugliaSalute AOL.
Le pagine aziendali territoriali sono comunque catalogate quando pubbliche e
ragionevolmente consultabili, per aumentare discovery e ridondanza.

Le fonti aggiunte nel catalogo nazionale usano l'import generico `html-list` o
`html-hub`, salvo adapter dedicati gia esistenti. Il parser generico riconosce
ora anche `AULSS`, `ASP`, `ASReM`, `ARES`, `AREUS`, `ESTAR`, `ARCS`, `ASDAA`,
`ASUIT` e `Azienda Zero` come `azienda-sanitaria`.

## Estensione ospedaliera, AOU e IRCCS

Il catalogo include anche un primo blocco nazionale di aziende ospedaliere,
aziende ospedaliero-universitarie e IRCCS, tra cui AO Alessandria, Gaslini,
San Martino, AO Padova, AOUI Verona, IOV, Burlo, CRO Aviano, Careggi, Meyer,
AOUP Pisa, AOU Siena, AOU Perugia, AO Terni, AOU Marche, INRCA, San Camillo,
IFO, AORN Moscati, AOU Federico II, AOR San Carlo, AO Cosenza, AOU Dulbecco,
GOM Reggio Calabria, Cannizzaro, ARNAS Garibaldi, Papardo, Brotzu, AOU Cagliari
e AOU Sassari.

Queste fonti sono intenzionalmente classificate come `hospital-html-hub` con
`pending-adapter`: sono pubbliche e catalogate, ma non entrano nel refresh
generico finche non viene verificata una struttura stabile per ciascun sito e
non viene definita la deduplicazione con hub regionali come ESTAR, Azienda Zero
o ARES.
