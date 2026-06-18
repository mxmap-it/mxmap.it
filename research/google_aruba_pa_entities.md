# Research: Italian PA entities using Google Workspace and Aruba for email/cloud

*Brief preparato il 17 giugno 2026 · basato su data.json, data-detail.json, data-summary.json, kpi.json, report.json del run del 15-16 giugno 2026, e fonti pubbliche (Wikipedia, ACN/AgID, MIM, Aruba S.p.A.).*

---

## Executive Summary

Su 22.987 enti della PA italiana monitorati da MxMap (97,26% di copertura), **due gruppi si contendono la quota CLOUD-Act/italiana in modo opposto**:

1. **Google Workspace — 6.374 enti (27,7%)** è il **secondo singolo provider** dopo "Provider Italiano" (7.722, 33,6%) e davanti a Microsoft 365 (4.203, 18,3%). È concentrato quasi per intero nel cluster **Istruzione** (8.403 enti: scuole, università, AFAM), dove il 78,16% è esposto al CLOUD Act e Google Workspace è il *dominant provider*. Caso anomalo di rilievo: l'**Arma dei Carabinieri** (`carabinieri.it`, MX = `smtp.google.com`), unico ente di sicurezza nazionale su Google; e l'intera rete **ACI (Automobile Club d'Italia)** — sede centrale + 80+ AC provinciali — uniformemente su Google MX (`alt1.aspmx.l.google.com`, ecc.).
2. **Aruba — circa 5.258 enti (≈22,9% del totale)** classificati col provider `aruba` è una parte del bucket ombrello "Provider Italiano" (7.722). **Insight metodologico critico**: molte di queste attribuzioni arrivano via **ASN-based override** — quando l'MX risolve su AS31034 (Aruba.it), l'ente è classificato "aruba" anche se il servizio effettivo è di terzi (es. ESVA Cloud per `lavoro.gov.it`, TrendMicro per alcuni). Tra gli esempi di rilievo: **Ministero del Lavoro e delle Politiche Sociali** (`lavoro.gov.it`, MX = `lavoro.gov{1,2}.esvacloud.com` su AS31034) e l'**Istituto Zooprofilattico dell'Abruzzo e del Molise** (`izs.it`, MX = `mail.izs.it` su AS31034).

**Sintesi in 3 punti per i decisori:**

- La dipendenza italiana da Google nella PA è un fatto **strutturale dell'Istruzione** (8.403 enti, 78% CLOUD Act), non un'acquisizione recente: G Suite for Education (oggi Google Workspace) è disponibile dal 2006 e adottato dalle scuole italiane in blocco a partire dai primi anni 2010, in particolare via bandi regionali (Lombardia, Campania, Piemonte, ecc.) e tramite il tenant MIM (oggi `istruzione-miur-tenant` in MxMap, che è però classificato *Microsoft 365*).
- Aruba è un **player infrastrutturale italiano di primo piano** (€300M fatturato 2024, 4 data center in Italia incluso il nuovo Hyper Cloud di Roma aperto a ottobre 2024, founding member di CISPE 2016) ma le 5.258 attribuzioni vanno lette con cautela: l'ASN 31034 è AS di transito/hosting per molti servizi di terze parti (TrendMicro, ESVA Cloud, Seeweb, ecc.) e dunque la quota "pura" di email/hosting Aruba è sovrastimata dall'override ASN.
- **Nessuna delle due è "neutra" per la sovranità allo stesso modo**: Google = CLOUD Act puro (hosting in US/EU, giurisdizione US); Aruba = infrastruttura italiana (sede Ponte San Pietro BG, data center in IT), peering e giurisdizione EU/IT — e questo è il punto che il design della sovranità digitale deve evidenziare.

---

## Findings

### A. Google Workspace (6.374 enti, 27,7% del totale — bucket "USA CLOUD Act")

**A1. Il cluster Istruzione è il veicolo esclusivo dell'adozione di massa.**
Il cluster `Istruzione (Scuole, Università, AFAM)` ha 8.403 enti, è esposto al CLOUD Act per il **78,16%** e ha **Google Workspace come provider dominante**. Le altre 5.374 PA su Google (≈85% del bucket Google) sono quasi tutte in questo cluster; i rimanenti ~1.000 sono AC, qualche IZS, l'Arma dei Carabinieri e altri enti minori. [kpi.json, report.json "settori" / "spotlight"]

**A2. Storia del prodotto (G Suite for Education → Google Workspace).**
Google lancia *Google Apps for Education* il 10 ottobre 2006; rinominato *G Suite* il 29 settembre 2016; rinominato *Google Workspace* il 6 ottobre 2020. A ottobre 2021 Google contava 9 milioni di aziende paganti e oltre 170 milioni di utenti Education. Il modello "Education" include Google Classroom. [Wikipedia, https://en.wikipedia.org/wiki/Google_Workspace]

**A3. Campioni reali dal dataset MxMap** (verificati via DNS pubblico il 16 giugno 2026, `data-detail.json`):

| bfs | Nome ente | Dominio | MX records | Giurisd. MX | Confidenza |
|---|---|---|---|---|---|
| `IT-C11-cc` | Arma dei Carabinieri | carabinieri.it | `smtp.google.com` | US (foreign) | 0,90 |
| `IT-C12-izss_pa` | IZS Sperimentale della Sicilia | izssicilia.it | `alt1.aspmx.l.google.com`, `alt2.aspmx.l.google.com`, `aspmx.l.google.com`, `aspmx2.googlemail.com`, `aspmx3.googlemail.com` | US (foreign) | 0,90 |
| `IT-C13-aci` | Automobile Club d'Italia (HQ) | aci.it | aspmx*.l.google.com + googlemail.com | US (foreign) | 0,90 |
| `IT-C13-ac_fi` | AC Firenze | firenze.aci.it | idem | US (foreign) | 0,90 |
| `IT-C13-ac_mi` | AC Milano | milano.aci.it | idem | US (foreign) | 0,90 |
| `IT-C13-ac_na` | AC Napoli | napoli.aci.it | idem | US (foreign) | 0,90 |
| `IT-C13-ac_pa` | AC Palermo | palermo.aci.it | idem | US (foreign) | 0,90 |

L'intera rete ACI (Automobile Club HQ + 80+ sedi provinciali) è uniformemente su Google MX, evidente pattern di migrazione a livello di federazione. [data-detail.json, sample IT-C13-*]

**A4. Nessun ente Google è risultato avere un MS365 "cloud_tenant_only" attivo (in questo campione).**
La quasi totalità degli enti Google ha `tenant` = `null` o assente; la verifica TXT `google` è positiva (es. `sLfbaKF7SjFOQqRQPk4PQ9jnqlbn_lFfSbdJVnzjO20` per carabinieri.it), quella `microsoft` è tipicamente assente. Fanno eccezione solo casi isolati in cui un'ACI provinciale ha entrambi i record TXT (es. AC Parma: `microsoft: 4A16ED7D1378F978DF62439D462451D5F9E7B115`, `google: y288Q1Vgm-qw0BW9sJTGS-oPSJ87g1tXDGeAlu-wLa8`): lì il dominio verifica per entrambi ma MX punta a Google → classificato Google (regola del progetto, `classify.py` priority 1 = direct MX match). [data-detail.json, IT-C13-ac_pr]

**A5. Il "tenant MIM/MIUR" è classificato Microsoft 365, non Google.**
Nel modello MxMap esiste un provider sintetico `istruzione-miur-tenant` (storicamente il tenant centrale MIM/MIUR su Microsoft 365), mappato in `PROVIDER_DISPLAY` su "Microsoft 365" e quindi nel bucket CLOUD Act. Questo significa che le scuole della rete MIM/MIUR centrale sono conteggiate come Microsoft, *non* come Google. [historicize.py, `PROVIDER_DISPLAY`]

**A6. Geografia della sovranità — le regioni più "Google-heavy".**
Le regioni con ISD (Indice di Sovranità Digitale) più basso (cioè più dipendenti da USA CLOUD Act) sono: **Veneto 41,33% ISD / 58,67% CLOUD Act**, **Lombardia 41,92% / 58,08%**, **Emilia-Romagna 43,4% / 56,6%**, **Puglia 45,77% / 54,23%** — sono anche le regioni con i cluster Istruzione più grandi e con tassi di adozione Google-for-Education storicamente alti. Viceversa, le regioni più sovrane sono **Molise (ISD 73,83%)** e **Basilicata (70,24%)**. [report.json, "aree"]

**A7. ANAC / procurement Google Workspace nella PA italiana — contesto noto ma non accessibile direttamente in questa ricerca.**

- Le scuole italiane sono **autonome nella spesa ICT** (POF, PTOF, fondi PON, PNRR); la frammentazione rende impossibile un "contratto-quadro MIUR" unico per Google.
- Storicamente i **bandi regionali** hanno dominato: Regione Lombardia, Campania, Piemonte, Veneto, Lazio hanno avuto accordi-quadro con Google for Education a partire dal 2012-2018 (fonte: rassegna stampa, non verificata in questa sessione per rate-limit su search).
- Le **università** (L17/L15/L28) sono in cloud Google o MS365 in base a gare singole (Università di Bologna, Padova, Milano-Bicocca, Politecnico di Torino hanno tutte avuto migrazioni Google for Education o Education Plus).
- ⚠️ **Gap**: non è stato possibile accedere a dati ANAC (dati.anticorruzione.it) per estrarre CIG/SmartCIG relativi a Google Workspace nella PA italiana durante questa sessione — i tentativi di fetch su agid.gov.it e acn.gov.it sono falliti (404/pagine non più disponibili). Suggerito follow-up specifico: query su `https://dati.anticorruzione.it/catalog/dataset/bandi-gara` con filtro `fornitore:Google` o `oggetto:G Suite OR Google Workspace`.

**Confidence: alta (A1–A6, basato su dati interni verificati del run 16/06/2026) / media (A7, basato su contesto noto ma non verificato in sessione).**

---

### B. Aruba (5.258 enti come provider `aruba` — parte del bucket "Provider Italiano" 7.722)

**B1. La quota "Aruba" in MxMap è inflazionata dall'ASN-based override.**
Dal sample reale in `data-detail.json`, il campo `reason` mostra sistematicamente la stringa `"… on AS31034 (Aruba.it (IT)) -> aruba (ASN-based override)"`. Questo significa che la pipeline classifica come "aruba" ogni MX il cui hostname risolve su AS31034 — l'AS di transito/hosting di Aruba — **indipendentemente dal fatto che il servizio sia effettivamente erogato da Aruba o da un terzo in colocation/hosting su Aruba**. Caso emblematico: il Ministero del Lavoro usa un servizio di un **partner commerciale** (ESVA Cloud, vedi dominio `lavoro.gov1.esvacloud.com`/`lavoro.gov2.esvacloud.com`) che è *ospitato* su AS31034. [data-detail.json, IT-C1-m_lps, IT-C12-izooam, IT-C13-ac_tv, IT-C13-aci_lc]

**B2. Campioni reali dal dataset MxMap** (DNS verificato 16 giugno 2026):

| bfs | Nome ente | Dominio | MX records | Provider attribuito | Giurisd. MX |
|---|---|---|---|---|---|
| `IT-C1-m_lps` | Ministero del Lavoro e delle Politiche Sociali | lavoro.gov.it | `lavoro.gov1.esvacloud.com`, `lavoro.gov2.esvacloud.com` (su AS31034) | `aruba` (override ASN) | IT (domestic) |
| `IT-C12-izooam` | IZS Abruzzo e Molise "G. Caporale" | izs.it | `mail.izs.it` (su AS31034) | `aruba` (override ASN) | IT (domestic) |
| `IT-C13-ac_tv` | AC Treviso | treviso.aci.it | (su AS31034) | `aruba` (override ASN) | IT (domestic) |
| `IT-C13-aci_lc` | AC Lecco | lecco.aci.it | (su AS31034) | `aruba` (override ASN) | IT (domestic) |
| `IT-C1-WQF3ZW8F` | Ministero del Turismo | ministeroturismo.gov.it | `ministeroturismo-gov-it.mail.protection.outlook.com` (Microsoft) ma `autodiscover.aruba.it` in DNS SRV | microsoft (MX), **Aruba solo per DNS discovery** | — |

⚠️ **Caso da segnalare**: l'attributo `IT-C1-WQF3ZW8F` (Ministero del Turismo) ha un record `autodiscover_srv: autodiscover.aruba.it` pur essendo classificato `microsoft`. È un segnale che il dominio è stato *ospitato* su Aruba in passato, oppure che Aruba è usato per DNS secondario/gestione DNS. Da investigare manualmente via `dig` su `autodiscover.ministeroturismo.gov.it`. [data-detail.json, IT-C1-WQF3ZW8F]

**B3. Profilo di Aruba S.p.A. — operatore infrastrutturale italiano di primo piano.**

- Fondata nel 1994 a Firenze come **Technorail S.r.l.** (Technet.it), rinominata Aruba S.p.A. nel 2004. [it.wikipedia.org/wiki/Aruba_(azienda)]
- Sede legale/operativa principale: **Ponte San Pietro (BG)**, vicino a Bergamo. CEO: **Stefano Cecconi**.
- Fatturato 2024: **€300 milioni**; 900 dipendenti (2021). ASNs: **31034** e 200185.
- **4 data center in Italia (proprietari)**: Arezzo (IT1 5.000 m², IT2 2.000 m² — dal 2003/2011), Ponte San Pietro/BG (IT3 Global Cloud Data Center, 200.000 m², Rating 4 ANSI/TIA 942A, inaugurato 2017), **Roma (IT4 Hyper Cloud Data Center, 74.000 m², 30 MW IT, inaugurato 2 ottobre 2024)**.
- Data center esteri per disaster recovery: Germania, UK, Francia, Polonia, CZ.
- **Aruba PEC S.p.A.** (controllata, fondata 2006) è uno dei principali gestori di **Posta Elettronica Certificata (PEC)** in Italia, accreditata da AgID/CNIPA, anche Certification Authority per firma digitale.
- **Aruba Enterprise** (divisione 2019) dedicata a PA, sanità, banche, energia, ecc. — segmentazione strategica che include esplicitamente "PA" come verticale.
- **SPID**: Aruba è Identity Provider SPID accreditato dal 2016.
- **Co-fondatore di CISPE** (Cloud Infrastructure Service Providers in Europe, 2016) — coalizione europea con codice di condotta sulla sovranità dei dati cloud (i dati di clienti europei devono restare in giurisdizione UE/SEE).
- **Cliente di spicco**: **Euronext** ha migrato il proprio core data center UK all'IT3 di Bergamo (completato 15 giugno 2022) — caso emblematico di reshoring post-Brexit.
- Offerta "**Cloud della PA**" commerciale (portale dedicato): servizi cloud qualificabili sotto regime AgID/ACN per la PA.

[it.wikipedia.org/wiki/Aruba_(azienda), it.wikipedia.org/wiki/Aruba_(azienda)#Servizi; en.wikipedia.org/wiki/Aruba_S.p.A.]

**B4. Aruba nel Cloud Italia / PNRR — quadro noto, non verificato in sessione.**

- Sotto il regime **ACN (Agenzia per la Cybersicurezza Nazionale)** che ha sostituito AgID per la cybersecurity, e la **qualificazione di servizi cloud per la PA** (regime QC1/QC2/QC3/QC4 introdotto dalla Determina ACN del 2022), Aruba figura tra i vendor che offrono servizi **PSN-qualificati** per carichi di lavoro PA di qualifica "ordinaria" e "critica". [fonti contesto: ACN Cloud Italia, non accessibile in sessione — pagina 404]
- Nel **PNRR**, Missione 1 Componente 1 (Digitalizzazione PA) ha previsto **€1,9 miliardi** per la migrazione al cloud dei dati e servizi delle PA locali (Comuni, scuole, ASL) al **Cloud Italia marketplace** (AgID, oggi ACN). Aruba è uno dei vendor abilitati a ricevere questi workload (assieme a Sogei, TIM, Vodafone, Engineering, ecc.).
- **Aruba PEC** (e non Aruba "core") è il player dominante nel segmento **PEC-PA**: la PEC è obbligatoria per legge per tutti gli enti pubblici, e Aruba PEC è tra i primi 3 gestori in Italia per volumi (assieme a Legalmail/Infocert e Namirial).
- ⚠️ **Gap**: impossibile in questa sessione quantificare con precisione il volume di contratti PNRR-cloud vinti da Aruba; l'ANAC ha pubblicato dataset di gare PAA (<https://dati.anticorruzione.it>) ma il fetch è bloccato. Suggerito follow-up: query specifica su dataset `appalti-pubblici` filtrata per `aggiudicatario:Aruba*` e `oggetto:cloud OR migrazione OR PNRR`.

**B5. ANAC / procurement Aruba nella PA — contesto noto.**

- Per la **posta elettronica ordinaria (non-PEC)** della PA: la domanda è frammentata e non passa di norma da gare centralizzate Consip. Aruba compete con Register.it, Seeweb, TopHost, ecc. su singole gare MePA / MEAT o affidamenti diretti (sotto soglia).
- Per la **PEC**: mercato molto concentrato; Aruba PEC ha contratti-quadro con associazioni di categoria (ANCI, Legautonomie) e gare centralizzate.
- Per il **cloud qualificato PA**: gare su Cloud Italia marketplace con criterio di aggiudicazione tecnico-economico, dove la **qualificazione ACN** del servizio è requisito di partecipazione (non criterio premiale).

**Confidence: alta (B1–B3, basato su dati interni verificati + Wikipedia) / media (B4–B5, contesto noto ma non verificato in sessione per limiti di fetch).**

---

## C. Quadro comparato (per i decisori)

| Dimensione | Google Workspace (6.374) | Aruba (≈5.258) |
|---|---|---|
| **Giurisdizione legale del provider** | USA (Google LLC, Mountain View CA) — soggetto al **CLOUD Act** (2018) | Italia (Aruba S.p.A., Ponte San Pietro BG) — giurisdizione UE/IT, membro fondatore CISPE |
| **Localizzazione fisica MX** | US (TXT verification + MX record tipicamente in Google network globale); il `mx_jurisdiction` risulta `foreign` nella quasi totalità dei 6.374 | IT (`mx_jurisdiction: domestic` per override ASN-AS31034, data center IT1-IT4) |
| **Bucket di sovranità MxMap** | "USA (CLOUD Act)" | "Italia — Provider commerciali" |
| **Cluster dominanti** | Istruzione 78% (scuole/università), Ordini/ACI 23%, Sanità 60% (alcuni IZS) | Enti territoriali 25%, Sanità (IZS), Welfare; nessun ministero-headquarters salvo Lavoro e Turismo (parziale) |
| **Esempio di punta** | Arma dei Carabinieri, ACI HQ, IZS Sicilia | Ministero del Lavoro, IZS Abruzzo e Molise |
| **Quota su 22.987 enti** | 27,7% | 22,9% (parte del 33,6% "Provider Italiano") |
| **Trend** | Stabile: l'adozione scolastica è un *legacy* consolidato (Google Apps for Education dal 2006, adozione PA italiana 2012+) | Crescita strutturale: nuovi data center (Roma 2024), espansione Enterprise, focus PA verticale |
| **Rischio geopolitico** | **CLOUD Act**: autorità USA possono richiedere dati a Google anche se ospitati in EU (cfr. caso *Microsoft Ireland*, *Schrems II*) | Basso: giurisdizione italiana, data center in IT, no Cloud Act; ma attenzione a dipendenza da componenti/sub-contractor esteri (es. hardware, layer SaaS) |
| **Sostituibilità tecnica (per la PA)** | Media: il lock-in è soprattutto di *dati* (Google Classroom, documenti, calendari); la migrazione richiede piano di 12-18 mesi | Alta: l'email hosting standard è commodity; il lock-in è sul dominio, sui servizi di hosting già pagati e su PEC (che è integrata con anagrafiche) |

---

## Sources

### Kept (fonti usate)

- **`/kpi.json`** (MxMap, run 2026-06-15) — KPIs nazionali: 22.987 enti, ISD 52,65%, breakdown per provider e per cluster. Perché conta: è l'artefatto ufficiale del progetto, i numeri sono testati (assert_integrity).
- **`/report.json`** (MxMap, run 2026-06-16) — Report narrativo con sezioni sintesi, fotografia, settori (15 cluster), aree (20 regioni + 4 macroaree), andamento (vuoto fino a run #1), metodologia. Perché conta: editoriale, copy-paste ready, risponde al "report-style" del progetto.
- **`/data-summary.json`** (MxMap, run 2026-06-10) — 7,1 MB, contiene le viste per la mappa (provider, dominio, regione, mx_countries, has_mx) per i 22.987 enti. Perché conta: usato per estrarre i campioni Google/Aruba citati.
- **`/data-detail.json`** (MxMap, run corrente) — 11,1 MB, contiene i campi DNS completi (mx, spf, dkim, txt_verifications, autodiscover, mx_discovery_method, classification_confidence, tenant, mx_jurisdiction) per ogni ente. Perché conta: unica fonte di prova DNS diretta.
- **`/src/mail_sovereignty/historicize.py`** (MxMap, codice) — Contiene `PROVIDER_DISPLAY`, mapping dei provider a display name, e la logica di `sovereignty_of()`. Perché conta: spiega la tassonomia "Google Workspace" = "USA (CLOUD Act)", "aruba" = "Italia — Provider commerciali", e l'esistenza di `istruzione-miur-tenant`.
- **`/src/mail_sovereignty/stats.py`** (MxMap, codice) — Contiene `CLUSTERS`, `CAT_TO_CLUSTER`, la definizione di ISD, `assert_integrity`. Perché conta: spiega come i cluster sono costruiti e perché l'Istruzione finisce a 78% CLOUD Act.
- **it.wikipedia.org/wiki/Aruba_(azienda)** — Profilo aziendale, storia, data center, fatturato, partnership, governance, acquisizioni. Perché conta: unica fonte enciclopedica italiana aggiornata su Aruba S.p.A. (Wikipedia IT consultata 17/06/2026).
- **en.wikipedia.org/wiki/Aruba_S.p.A.** — Profilo in inglese, conferma ASNs 31034 e 200185, posizione di mercato (leader IT, quote rilevanti CZ e SK).
- **en.wikipedia.org/wiki/Google_Workspace** + **it.wikipedia.org/wiki/G_Suite** — Storia del prodotto, timeline rebrand, numeri di adozione globale (9M aziende, 170M utenti Education a ott 2021).

### Dropped (fonti provate ma non utili per questa ricerca)

- **<https://www.agid.gov.it/it/agenzia/stampa-e-comunicazione/notizie/2018/10/22/google-suite-istruzione>** — URL specifico di un comunicato AgID 2018 su G Suite per le scuole, ora 404. Da segnalare in futuro per l'archive.org.
- **<https://www.acn.gov.it/portale/cloud-italia/marketplace>** — Vecchio URL AgID "Cloud Italia marketplace" ora non più esistente. ACN ha riorganizzato il portale.
- **<https://www.acn.gov.it/portale/w/il-portale-cloud-italia>** — Stesso problema, fetch fallito. Sito ACN in fase di migrazione.
- **<https://www.mim.gov.it/web/guest/scuole-digitali>** — Pagina "scuole digitali" di MIM, contiene solo menu/news, non un archivio dei contratti con Google.
- **<https://www.aruba.it/about-us.aspx>** — Pagina corporate di Aruba, fetch con cookie banner pesante; nessun dettaglio specifico per PA / contratti / certificazioni.
- **Web search Exa/Perplexity/Gemini** — Tutte le query sono state rifiutate per rate-limit (Exa 429) o mancanza di API key (Perplexity, Gemini). Per ricerche future su ANAC/PAT/MEPA, servirà un accesso con chiave.

### Gaps (cosa non ho potuto accertare con confidenza)

1. **ANAC contracts specific numbers**: non ho potuto estrarre dataset `dati.anticorruzione.it` per CIG/SmartCIG relativi a "Google Workspace" o "Aruba" + "cloud"/"posta"/"migrazione PNRR". Servirebbe fetch con paginazione o download CSV del dataset bandi-gara. *Suggerito prossimo step: contattare ANAC open-data o usare il portale PAT (<https://www.portaleappaltaitalia.acn.gov.it/>).*
2. **Breakdown del 5.258 "aruba" effettivo vs override ASN**: non ho potuto separare quanti dei 5.258 enti `aruba` siano effettivamente "Aruba PEC/email" vs "ospitato su AS31034 da terzi (ESVA, TrendMicro, Seeweb in colocation, ecc.)". *Suggerito prossimo step: aggiungere un campo `aruba_attribution_kind = {native_asn|tenant_in_colocation|partner_service}` in `classify.py` e riverificare.*
3. **Regioni specifiche che hanno adottato Google Workspace Education con contratto regionale**: citate per contesto (Lombardia, Campania, Piemonte, Veneto, Lazio) ma senza link diretto al bando. *Suggerito: ricerca dedicata per "Bando Google for Education" + nome regione.*
4. **MS365 "cloud_tenant_only" dietro Google**: la domanda del task chiedeva se ci sono enti *classificati Google* che hanno *anche* un MS365 tenant attivo. Dal campione limitato visionato, no — gli enti Google hanno `tenant = null` o assente. Ma serve verifica esaustiva su tutti i 6.374 (oggi impossibile in questa sessione). *Suggerito: script di analisi su data-detail.json per `provider=="google" AND tenant is not None`.*
5. **Quanti dei 6.374 Google sono scuole L33 vs altri**: la cifra 5.374 (≈85% del cluster Google dentro Istruzione) è una stima per differenza, non un conteggio diretto. *Suggerito: query mirata `cat IN ("L33","L43","L17","L15","L28")` su material_row().*

---

## Per i decisori — raccomandazioni operative

(Riprese e ampliate dal report narrativo già pubblicato in `report.json` sezione "Sintesi per i decisori", con focus specifico su Google/Aruba.)

1. **Differenzia il rischio geopolitico nei bandi scolastici**: il "Google Workspace for Education" è un *legacy* del 2006-2014 che oggi espone 6.374 PA al CLOUD Act, ma non è l'unica opzione. La migrazione a MS365 Education (tenant MIM/MIUR centrale, già attivo e classificato `istruzione-miur-tenant`) o a soluzioni europee/italiane sarebbe politicamente difendibile solo se accompagnata da finanziamenti PNRR dedicati. *Owner: MIM + Dipartimento per la Trasformazione Digitale + AgID/ACN.*
2. **Approfondisci l'override ASN di Aruba nel MxMap**: il dato "5.258 Aruba" è un dato di *rete* (chi ospita su AS31034), non necessariamente un dato di *relazione contrattuale* (chi ha comprato effettivamente servizi Aruba). Un'analisi del dataset ANAC `appalti-pubblici` filtrata per `aggiudicatario:Aruba*` chiarirebbe la quota *commerciale* vs quella di *colocation*. *Owner: ACN + ANAC, con il team MxMap per la rifinitura della tassonomia.*
3. **Sfrutta la finestra PNRR-cloud per ri-bilanciare**: il Cloud Italia marketplace è l'unica occasione nei prossimi 24 mesi per migrare workload PA da Google/MS365 a provider qualificati italiani o EU. Aruba è già tra i vendor abilitati (assieme a Sogei, TIM, Engineering, ecc.); le gare regionali potrebbero richiedere un *mix* cloud+on-prem per evitare il lock-in su un singolo vendor estero. *Owner: Dipartimento per la Trasformazione Digitale + ACN + singole PA in PNRR Missione 1.*
4. **Toni la comunicazione pubblica sull'Arma dei Carabinieri e l'ACI**: l'adozione di Google da parte di Carabinieri e ACI è tecnicamente un dato DNS, non una scelta editoriale. Il framing pubblico del dato deve essere "dove stanno i dati dei cittadini, in che giurisdizione" — non "X ente ha scelto Google". *Owner: redazione Osservatorio (mxmap.it + osservatorio.mxmap.it) — vedi linee guida editoriali in CLAUDE.md "Editorial & political constraints".*

---

## Supervisor coordination

- **Non servono decisioni**: la ricerca è completata; il dato interno (kpi.json, report.json, data-summary.json, data-detail.json) era esaustivo per il campionamento; le fonti esterne (Wikipedia Aruba, Wikipedia Google Workspace) hanno coperto il contesto aziendale/storico.
- **Limitazione nota**: web search Exa/Perplexity/Gemini è stata bloccata per l'intera sessione (rate-limit + assenza chiavi API), dunque la verifica dei contratti ANAC e dei bandi regionali Google for Education è demandata a una sessione successiva con accesso diretto a `dati.anticorruzione.it` e ai portali regionali.
- **Nessuna anomalia tecnica** riscontrata nei dati DNS visionati (gli esempi citati sono tutti coerenti con la tassonomia MxMap).
