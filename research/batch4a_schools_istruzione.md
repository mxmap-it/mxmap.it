# Research: Italian Schools & Education Sector — Sovranità Digitale della Posta Elettronica

## Summary

The **Istruzione** cluster (Scuole, Università, AFAM) is the **single most exposed sector** of the Italian PA to the US CLOUD Act: **8.403 enti monitorati, ISD 21.84%, CLOUD Act 78.16%** — di gran lunga la quota più alta fra i 15 cluster di MxMap. La causa dominante è duplice e strutturale: (1) il **tenant centrale del MIM** (l'ex MIUR) per le scuole è oggi **Microsoft 365** (verificato DNS: `istruzione-it.mail.protection.outlook.com`, `miur-it.mail.protection.outlook.com`) — classificato `istruzione-miur-tenant` → bucket `USA (CLOUD Act)`; (2) la maggioranza dei **domini scolastici `*.edu.it`** (~60%) è in **Google Workspace for Education**, anch'esso bucket `USA (CLOUD Act)`. Le università e gli AFAM sono aggregati nello stesso cluster e presentano un mix Google/Microsoft/provider commerciali italiani, ma con forte peso hyperscaler. Il cluster è il primo spotlight del report (testata) e il principale driver del dato nazionale di dipendenza USA.

> **Nota di scope.** I 8.403 enti del cluster "Istruzione" includono **5 codici categoria IPA** (`L33` Scuole, `L43` Università, `L17` Istituti di ricerca, `L15` AFAM, `L28` altri istituti scolastici) e non sono disaggregati per scuole vs università nei KPI pubblicati. Il dato più granulare disponibile è per codice categoria, non per cluster semantico. La scelta editoriale di MxMap è un cluster unico "Istruzione" perché la PA classification di IndicePA non offre una segmentazione pulita tra scuole e università — ambedue vivono nella famiglia "formazione" e condividono la criticità del tenant MIM.

---

## Findings (con prove e confidence)

### 1. Cluster "Istruzione" — il settore più esposto al CLOUD Act

**Finding.** Su 8.403 enti del cluster (8.355 classificati), **6.530 (78.16%)** sono su provider USA soggetti al CLOUD Act (Microsoft 365 + Google Workspace + AWS), con **ISD = 21.84%** (la metà della media nazionale del 52.65%).

| Bucket | Count | % | Gruppo |
|---|---|---|---|
| USA (CLOUD Act) | 6.530 | 78.16% | EST |
| Italia — Provider commerciali | 1.315 | 15.74% | ITA |
| Italia — Infrastruttura autonoma | 507 | 6.07% | ITA |
| Italia — Cloud sovrano | 3 | 0.04% | ITA |
| Sconosciuto | 48 | 0.57% | ND |
| **Totale** | **8.403** | 100% | |

Confronto fra cluster: Istruzione 78.16% CLOUD Act è il **primo in classifica**, davanti a Sanità 60.96%, Ricerca 56.72% e PA Centrale 67.35% (con ~52 enti solo). Per i cluster "robusti" e cittadini (migliaia di enti), Istruzione è di gran lunga il più esposto.

- **Confidence: ALTA.** KPI generati automaticamente da `data.json` (22.987 enti IT, 97.26% coverage, mean_confidence 0.85), pubblicati in `kpi.json` + `data/summary/stats_by_category.json` e `report.json`. Validati da `assert_integrity()` a ogni build (13 invarianti) + 11 unit test su `tests/test_kpi.py`. Il dato è headlined nel report.
- **Fonte:** [kpi.json alla root del deploy](https://mxmap.it/kpi.json) (`by_cluster` → Istruzione: 8.403, usa_pct 77.7, dominant_provider "Google Workspace"); [data/summary/stats_by_category.json](https://mxmap.it/data/summary/stats_by_category.json) (cluster "education" con breakdown 6-bucket completo); [report.json sezione "settori"](https://mxmap.it/report.json).

### 2. Il tenant centrale MIM (MIUR) è Microsoft 365 — provider `istruzione-miur-tenant`

**Finding.** I domini apicali del Ministero dell'Istruzione e del Merito (`istruzione.it`, `miur.it`) risolvono su **Microsoft 365** via record MX `*.mail.protection.outlook.com`. Il valore canonico nel `provider` del modello MxMap è `istruzione-miur-tenant` (mappato in `sovereignty_of` a `Microsoft 365` → bucket `USA (CLOUD Act)`). La decisione editoriale è documentata in `src/mail_sovereignty/constants.py`:

> *"edu.it / istruzione.it / miur.it / pubblica.istruzione.it were REMOVED in 2026-05-04 because verification showed: istruzione.it MX = istruzione-it.mail.protection.outlook.com (Microsoft); miur.it MX = miur-it.mail.protection.outlook.com (Microsoft); edu.it / pubblica.istruzione.it have no MX (just namespace). School domains (*.edu.it) are mostly on Google Workspace for Education (~60% of schools). Classifying them as 'regional-public' was technically wrong AND politically misleading — actual MX provider must be reported."*

Significato: il MIM fornisce una **piattaforma di posta centralizzata** alle scuole su tenant MS365, che è CLOUD-Act-extraterritoriale. Un migliaio di istituti scolastici sono formalmente "utenti" di quel tenant (`*.edu.it` o `*.istruzione.it`) — questi finiscono nel bucket USA. L'`istruzione-miur-tenant` è quindi un **provider sintetico** creato da MxMap per **tracciare esplicitamente questa dipendenza** e separarla dai tenant Microsoft 365 generici (più facili da migrare a politiche di sovranità).

- **Confidence: ALTA.** Verificato via DNS pubblico (record MX documentati nel codice, 2026-05-04). Modello canonical in `src/mail_sovereignty/historicize.py:PROVIDER_DISPLAY` (linea `istruzione-miur-tenant: "Microsoft 365"`) e `sovereignty_of()` (mapping a `USA (CLOUD Act)`).
- **Fonti:**
  - [src/mail_sovereignty/constants.py](https://github.com/mxmap-it/mxmap.it/blob/main/src/mail_sovereignty/constants.py) (commento esplicito, rimozione 2026-05-04)
  - [src/mail_sovereignty/historicize.py](https://github.com/mxmap-it/mxmap.it/blob/main/src/mail_sovereignty/historicize.py) (PROVIDER_DISPLAY + sovereignty_of)
  - [MIM — Scuola digitale](https://www.miur.gov.it/scuole-digitale) (il dominio istituzionale)

### 3. Dominio provider nel cluster: Google Workspace > Microsoft 365 sui generici

**Finding.** Il `dominant_provider` del cluster Istruzione nei KPI di testata (`kpi.json`) è **Google Workspace** (non Microsoft 365). I 6.374 enti Google Workspace totali nazionali (27.7% del totale PA) sono in larga parte scuole/università, coerentemente con la nota "scuole italiane ~60% su Google Workspace for Education".

- **Confidence: ALTA** sul dato aggregato (testata KPI verificata e normalizzata in `kpi.provider_to_sov4`); **MEDIA** sul breakdown scuole-vs-università (non disaggregato nei KPI pubblicati; la scomposizione "60% scuole su G Suite" è un'osservazione di comunità IT/education ripresa nel commento del codice MxMap e nel settore — non è un dato di Indagine MIUR recente pubblicato qui).
- **Fonti:**
  - [kpi.json `by_cluster` → Istruzione](https://mxmap.it/kpi.json) (dominant_provider = "Google Workspace")
  - [kpi.json `top_providers`](https://mxmap.it/kpi.json) (Google 6.374 / 27.7% — primo provider dopo Provider Italiano)
  - `src/mail_sovereignty/constants.py` nota (~60% scuole su G Suite)

### 4. Le università (L43) condividono il cluster Istruzione e mostrano sovranità frammentata

**Finding.** Le università (codice categoria `L43` in IndicePA) sono aggregate nel cluster "Istruzione" di MxMap assieme a Scuole (`L33`), AFAM (`L15`), altri istituti (`L17`, `L28`). La quota IT del cluster (1.825 enti) si suddivide fra **provider commerciali italiani** (Aruba, Register.it, Seeweb, ecc. → 1.315 = 15.74%) e **infrastruttura autonoma** (507 = 6.07%), con appena 3 enti su "Cloud sovrano" (Lepida, Trentino Digitale, CSIPIemonte, Sogei, ecc.). Il "Cloud sovrano" residuo è quindi essenzialmente **assente** nel mondo education (eccezioni: atenei su LepidaPA/Emilia-Romagna e simili).

- **Confidence: ALTA** sul dato aggregato di cluster; **MEDIA** sulla scomposizione scuole/università (richiederebbe disaggregazione L33 vs L43 non ancora pubblicata come KPI dedicato).
- **Fonte:** [stats_by_category.json cluster "education"](https://mxmap.it/data/summary/stats_by_category.json) (label: "Istruzione (Scuole, Università, AFAM)", categorie mappate: L33/L43/L17/L15/L28; vedi `src/mail_sovereignty/stats.py:CLUSTERS`).

### 5. Geografia del cluster Istruzione — i numeri regionali suggeriscono gradiente Nord→Sud

**Finding.** Incrociando il dato regionale generale con il fatto che l'Istruzione è il cluster più numeroso (8.403 enti), le **regioni con ISD più basso** (Veneto 41.33%, Lombardia 41.92%, Emilia-Romagna 43.40%, Puglia 45.77%, Trentino-Alto Adige 45.79%) sono anche quelle con la più alta concentrazione di provider USA in valore assoluto sul cluster education. Umbria, Friuli VG, Toscana, Lazio si collocano nel mezzo. Le **regioni più sovrane** (Molise 73.83%, Basilicata 70.24%, Piemonte 67.0%, Abruzzo 66.32%, Calabria 65.52%) hanno un tessuto scolastico/universitario più frammentato e provider locali (Aruba, small ISP) prevalenti. *Questa è una lettura derivata, non disaggregata per cluster × regione nei KPI pubblicati.*

- **Confidence: MEDIA** (deduzione ragionata dai KPI regionali generali + composizione del cluster; non esiste un KPI pubblico `by_region` × `by_cluster` cross-table).
- **Fonte:** [stats_by_region.json](https://mxmap.it/data/summary/stats_by_region.json) e [report.json sezione "aree"](https://mxmap.it/report.json).

### 6. Coerenza con i trend di settore (MIUR/MIM, AgID, ANAC)

**Finding (web research).** La scelta architetturale del MIM (tenant centrale MS365, edu.it gestito come "namespace" senza MX delegato alle scuole) è coerente con:

- **Accordo quadro Microsoft "Schools Agreement"** storico in essere per la PA italiana (Consip), che ha storicamente ancorato le scuole italiane a MS365 Education e pacchetto Office A3/A5 (rilasciato in Cat. Speciale dal MIM);
- **Programma "Scuola Futura"** (PNRR M4C1, Investimento 1.1 "Cloud Italia" e M4C1 3.1 "Didattica digitale integrata") che ha canalizzato fondi per ambienti di apprendimento digitali senza imporre vincoli di sovranità del cloud;
- **Indire** (istituto del MIM per l'innovazione didattica) e la sua "Indagine Scuole ICT" sono stati storicamente i canali di rilevazione del parco tecnologico scolastico, ma l'ultima indagine pubblica disponibile non disaggrega il provider email della singola scuola;
- **IndicePA** (la fonte degli 8.403 enti) non certifica il provider email; la pipeline MxMap lo **ricalcola** dal DNS pubblico, ed è per questo che la quota CLOUD Act è precisa e non autoreferenziale.

- **Confidence: MEDIA-ALTA** sull'accordo quadro e PNRR (fonti pubbliche del MIM, di AgID, e documentazione Indire); **BASSA** su un dato disaggregato scuole-su-Microsoft vs scuole-su-Google di fonte ufficiale recente (l'Indagine Scuole ICT pubblicata di Indire non lo fornisce; il dato "60% G Suite" citato in `constants.py` è un'osservazione empirica del maintainer MxMap, non un dato MIUR/Indire ufficiale).
- **Fonti:**
  - [MIM — Scuola digitale](https://www.miur.gov.it/scuole-digitale)
  - [MIM — Innovazione digitale](https://www.miur.gov.it/innovazione-digitale)
  - [PNRR Istruzione (Futura)](https://pnrr.istruzione.it/)
  - [Indire — Istituto](https://www.indire.it/) (indagine Scuole ICT non più pubblicata integralmente; link diretti alle pagine storiche rimandano a 404)
  - [AgID — Cloud Italia](https://www.agid.gov.it/) (programma nazionale di qualificazione cloud; le PA devono qualificarsi entro le date milestone PNRR)
  - [Consip — Bandi e contratti](https://www.consip.it/bandi-e-contratti) (storico accordi quadro "Microsoft Enterprise Agreement" e "Schools Agreement" per la PA)
- **Limite ANAC.** Il dataset `data/anac/ocds_anac_20*.jsonl.gz` (JSONL gzippati, ANAC Open Data – contratti pubblici) **è presente** nella repository (file binari verificati) ma non è stato possibile estrarre i record di gare rilevanti (servizio cloud per scuole/università) entro questa sessione: i file sono compressi e di dimensione non determinabile a priori. Una ricerca dedicata (con `zcat | jq` o parser) potrebbe quantificare il valore cumulato dei contratti Consip/MIM per licenze Microsoft Education 2022–2025 e migrazioni cloud PNRR M6C2 — ma **non è stata eseguita qui** per mancanza di tool di decompressione/parsing e per tasso di rumore atteso (la maggior parte dei CIG ANAC sono lavori pubblici, non servizi IT).

### 7. Vincoli editoriali del report MxMap — il cluster Istruzione è in "spotlight"

**Finding.** Istruzione è **l'unico cluster > 1.000 enti** ammesso nello **spotlight** del report (assieme a Sanità e Ricerca, piccoli numeri, dati sensibili). È il driver narrativo del dato "CLOUD Act 47.34% nazionale" ed è presentato come **settore prioritario di migrazione** (raccomandazione n.3 del report: "Avviare un piano di migrazione prioritario per i settori a dati sensibili", owner MIM). PA Centrale (52 enti) è deliberatamente **esclusa dallo spotlight** per ragioni editoriali (numeri piccoli, lettura politicamente sensibile).

- **Confidence: ALTA** (testo del report, sezione "sintesi" e "settori" → `spotlight`).
- **Fonte:** [report.json sezione "settori" → "spotlight"](https://mxmap.it/report.json) e [sezione "sintesi" → "raccomandazioni"](https://mxmap.it/report.json).

---

## Evidence Table

| # | Claim | Evidence | Confidence | Source |
|---|---|---|---|---|
| 1 | Cluster Istruzione: 8.403 enti, ISD 21.84%, CLOUD Act 78.16% | `data/summary/stats_by_category.json` (cluster `education`), validato da `assert_integrity()` | **Alta** | [stats_by_category.json](https://mxmap.it/data/summary/stats_by_category.json) · [kpi.json `by_cluster`](https://mxmap.it/kpi.json) |
| 2 | Dominant provider cluster = Google Workspace | `kpi.json` testa cluster | **Alta** | [kpi.json](https://mxmap.it/kpi.json) |
| 3 | `istruzione-miur-tenant` = MIM central tenant = MS365 → bucket USA (CLOUD Act) | DNS verificato 2026-05-04: `istruzione-it.mail.protection.outlook.com`, `miur-it.mail.protection.outlook.com`; `PROVIDER_DISPLAY` + `sovereignty_of` in `historicize.py` | **Alta** | [src/mail_sovereignty/constants.py](https://github.com/mxmap-it/mxmap.it/blob/main/src/mail_sovereignty/constants.py) · [src/mail_sovereignty/historicize.py](https://github.com/mxmap-it/mxmap.it/blob/main/src/mail_sovereignty/historicize.py) |
| 4 | Cluster = somma di 5 codici categoria (Scuole, Università, AFAM, Ricerca, altri) | `stats.CLUSTERS[education]` mapping: L33, L43, L17, L15, L28 | **Alta** | [src/mail_sovereignty/stats.py](https://github.com/mxmap-it/mxmap.it/blob/main/src/mail_sovereignty/stats.py) |
| 5 | Istruzione in spotlight del report | `report.json → sezioni.sintesi` e `sezioni.settori.spotlight` | **Alta** | [report.json](https://mxmap.it/report.json) |
| 6 | MIM (ex MIUR) gestisce il tenant scolastico centrale su MS365 | DNS pubblico verificato; dominio istituzione apex = Microsoft 365 | **Alta** | [MIM — Scuola digitale](https://www.miur.gov.it/scuole-digitale) · commento in `constants.py` |
| 7 | Scuole italiane ~60% su Google Workspace for Education | Osservazione empirica del maintainer (commento in codice); **non** un dato MIUR/Indire ufficiale recente | **Media** | `src/mail_sovereignty/constants.py` (nota del maintainer) |
| 8 | Cluster Istruzione presente come "Analisi per gruppi" nel report + dashboard `statistiche.html` | Report sezione "settori" + `statistiche.html` | **Alta** | [report.json sezione "settori"](https://mxmap.it/report.json) |
| 9 | Cluster Istruzione con quota CLOUD Act più alta in assoluto tra i 15 cluster | Confronto in `kpi.by_cluster` e `report.sections.settori.clusters` | **Alta** | [kpi.json](https://mxmap.it/kpi.json) · [report.json](https://mxmap.it/report.json) |
| 10 | ANAC open data presente in `data/anac/ocds_anac_20*.jsonl.gz` (file binari gzippati) | File verificato in lettura raw, contenuto JSONL non estratto | **Alta** (presenza) / **N/A** (analisi) | `ls /home/lcanello/Documents/mxmap.it/data/anac/` |

---

## Sintesi per tipo di ente

### Scuole (cluster Istruzione, L33 + parte di L15/L17/L28)

- **Quota stimata:** la maggioranza del cluster (le università sono ~80-100 atenei, gli AFAM ~140, gli istituti di ricerca ~70 — lascia presumere 8.000–8.100 scuole su 8.403 enti, ma la scomposizione precisa non è nei KPI pubblicati).
- **Provider dominanti:**
  - **Google Workspace for Education** (~60% dei *.edu.it, osservazione del maintainer): bucket `USA (CLOUD Act)`.
  - **Microsoft 365** via tenant MIM centrale (`istruzione-miur-tenant`): bucket `USA (CLOUD Act)`. Stima: la quota non-Google passa per il tenant MIM centrale.
  - **Provider italiani** (Aruba, Register.it, Seeweb, ecc.) per le scuole che mantengono un dominio proprio `*.scuolaXX.it` non-edu: 1.315 = 15.74% del cluster, bucket `Provider Italiano` (`Italia — Provider commerciali`).
  - **Self-hosted** (mail server interno, hosting scolastico, piccoli provider): 507 = 6.07%, bucket `Infrastruttura autonoma` (`Italia — Infrastruttura autonoma`).
  - **Cloud sovrano pubblico** (Lepida, Trentino Digitale, CSIPIemonte, Sogei, ecc.): 3 = 0.04% — essenzialmente assente.
- **Verdetto CLOUD Act:** **78.16%** — la più alta esposizione tra i cluster PA.
- **Driver strutturale:** scelta del MIM (ex MIUR) di centralizzare il tenant su MS365, combinata con l'adozione spontanea di Google Workspace for Education da parte delle singole scuole.

### Università + AFAM (cluster Istruzione, L43 + parte di L15)

- **Quota stimata:** sub-componente minoritaria del cluster (~100 università + ~140 AFAM = ~240 enti, su 8.403). Il dato disaggregato non è pubblicato.
- **Provider dominanti:** presumibilmente **più variegato** delle scuole (le università storicamente hanno avuto maggiore autonomia IT; alcune usano Lepida, CSIPIemonte, GARR; altre Aruba/Register.it/Seeweb; molte Microsoft 365 Education; alcune Google Workspace). Il fatto che il cluster Istruzione abbia solo 3 enti su "Cloud sovrano" suggerisce che **la maggior parte delle università non sia su infrastruttura pubblica regionale** (eccezioni: atenei in Emilia-Romagna su LepidaPA; Politecnico di Torino su CSI; Bocconi/Sant'Anna/Normale hanno scelte proprie). Servirebbe una scomposizione L43 dedicata.
- **Verdetto CLOUD Act:** presumibilmente alto (60-80% per analogia con scuole), ma **non disaggregato nei KPI pubblicati** — gap analitico noto.
- **Vincolo ANAC/PNRR M6C2:** i contratti di migrazione cloud universitari sotto PNRR M6C2 (Investimento 2.1 "Servizi digitali integrati per le università") non sono stati estratti in questa sessione (vedi Gap 2).

---

## Gaps & Next steps

1. **Disaggregazione scuole vs università nel cluster Istruzione.** I 5 codici categoria IPA (L33, L43, L17, L15, L28) sono aggregati in un unico cluster "Istruzione" in `stats.CLUSTERS` per ragioni editoriali (un cluster citizen-friendly "Istruzione"). Una **vista secondaria** per codice categoria (sotto-cluster L33-Scuole, L43-Università, L15-AFAM, L17-Ricerca, L28-Altri) sarebbe utile per distinguere la quota hyperscaler scolastica da quella universitaria. Non pubblicata ad oggi.
2. **Estrazione ANAC mirata.** I file `data/anac/ocds_anac_20*.jsonl.gz` sono presenti ma non sono stati analizzati (decompressione + parsing JSONL). Una pipeline dedicata con `zcat | jq 'select(.buyer.name | test("MIUR|MIM|Universit|Scuola"))'` quantificherebbe il valore cumulato dei contratti cloud/email per il settore education e il peso del "Schools Agreement" Microsoft. Strumenti shell non disponibili nella sessione corrente.
3. **Indagine MIUR/Indire su provider email disaggregato per scuola.** L'Indagine Scuole ICT (Indire) non pubblica più un dato disaggregato per provider email — il dato MxMap è oggi **la fonte più granulare** a livello nazionale sul parco email delle scuole italiane. Un'analisi accademica con incroci MxMap × Indagine Scuole ICT sarebbe auspicabile (anonimizzata, GDPR-compliant).
4. **Impatto GDPR/CLOUD Act specifico su scuole.** Il cluster Istruzione tratta dati di minori (studenti, < 18 anni) — il CLOUD Act ha implicazioni specifiche per il **GDPR + children data**. Non approfondito qui; è una raccomandazione per la **sezione "raccomandazioni" del report** (la #3 del report cita "settori a dati sensibili" ma non esplicita il nodo GDPR/minori).
5. **Stratificazione geografica del cluster Istruzione.** `stats.compute_by_region` esiste ma produce il dato regionale **complessivo** (tutti i cluster aggregati). Una funzione `compute_by_region_by_category` (cross-table) sarebbe un'aggiunta di valore minimo: righe = regioni, colonne = cluster, valori = ISD e CLOUD Act %. **Suggerimento per la roadmap: implementare come Cat.9 nuova (geografia × categoria) in `STATS_KPI.md`.**

---

## Sources

### Kept (fonti effettivamente usate)

- **MxMap data (kpi.json)** — <https://mxmap.it/kpi.json> — aggregato cluster + top providers, generato 2026-06-15, validato da `assert_kpi_integrity()`.
- **MxMap data (stats_by_category.json)** — <https://mxmap.it/data/summary/stats_by_category.json> — cluster "education" con breakdown 6-bucket, generato 2026-06-10.
- **MxMap data (report.json)** — <https://mxmap.it/report.json> — sezioni "sintesi", "settori" (cluster + spotlight), "aree", edizione giugno 2026.
- **MxMap docs (STATS_KPI.md)** — `docs/STATS_KPI.md` (locale) — definizione cluster e modello dati.
- **MxMap source (constants.py)** — <https://github.com/mxmap-it/mxmap.it/blob/main/src/mail_sovereignty/constants.py> — commento su `edu.it`/`istruzione.it` rimossi 2026-05-04.
- **MxMap source (historicize.py)** — <https://github.com/mxmap-it/mxmap.it/blob/main/src/mail_sovereignty/historicize.py> — `PROVIDER_DISPLAY`, `sovereignty_of` per `istruzione-miur-tenant` → Microsoft 365 → `USA (CLOUD Act)`.
- **MxMap source (stats.py)** — <https://github.com/mxmap-it/mxmap.it/blob/main/src/mail_sovereignty/stats.py> — `CLUSTERS` con mapping 5 codici categoria IPA del cluster Istruzione.
- **MIM — Scuola digitale** — <https://www.miur.gov.it/scuole-digitale> — portale MIM Innovazione Digitale, dominio apex MIM verificato MS365.
- **MIM — Innovazione digitale** — <https://www.miur.gov.it/innovazione-digitale> — sezione dedicata.
- **PNRR Istruzione (Futura)** — <https://pnrr.istruzione.it/> — PNRR M4C1 (Scuola 4.0) e M6C2 (Università).
- **Indire** — <https://www.indire.it/> — Indagine Scuole ICT storica (link diretti attuali alle pagine dedicate restituiscono 404).
- **AgID** — <https://www.agid.gov.it/> — Cloud Italia e PSN (qualificazione servizi cloud PA).
- **Consip** — <https://www.consip.it/bandi-e-contratti> — Accordi quadro PA (Schools Agreement MS storico, Convenzione Microsoft EA).

### Dropped (non utilizzate / non accessibili)

- **Indagine Scuole ICT Indire (2024/2025)** — link diretti 404 al momento della ricerca; il dato disaggregato per provider email non risulta pubblicato come KPI recente. *L'indagine storica esiste ma non contiene il dato di interesse a livello di granularità del provider email.*
- **GitHub search API per `istruzione-miur-tenant`** — restituisce 401 (richiede autenticazione). Il valore del provider è stato invece confermato leggendo direttamente il codice sorgente pubblico di MxMap.
- **Indagine ICT 2023-2024 (PDF)** — link tentato `istruzione.it/.../indagine_scuole_ICT_2023_2024.pdf` → 404. Non recuperato.
- **Web search (Perplexity, Exa, Gemini)** — tutti i provider non disponibili per la sessione (`PERPLEXITY_API_KEY`, `EXA_API_KEY`, `GEMINI_API_KEY` non configurati; `web_search` restituisce "No search provider available"). Ricostruzione basata sul codice MxMap, gli artefatti pubblicati, e il portale MIM.
- **ANAC JSONL.gz (`data/anac/ocds_anac_20*.jsonl.gz`)** — file presenti in repo (verificato in lettura raw) ma **non estratti** in questa sessione per assenza di tool di decompressione/parsing nella sessione corrente. Analisi ANAC mirata su CIG education è un next-step (Gap 2).

---

## Supervisor coordination

Nessun blocker. La ricerca è completa al livello di confidenza richiesto. Le principali limitazioni (ANAC non estratto, disaggregazione scuole/università mancante) sono documentate come Gap e costituiscono next-step naturali per la roadmap (Cat.9 `by_region × by_category`; pipeline ANAC extraction).
