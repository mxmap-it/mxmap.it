# Sintesi finale — Sovranità digitale della posta elettronica della PA italiana

**Dataset:** 22.987 enti pubblici italiani classificati via DNS (MX/SPF/DKIM/autodiscover)
**Edizione:** giugno 2026 (build 2026-06-15 → report 2026-06-16)
**Fonte primaria:** MxMap.it — `data.json`, `kpi.json`, `report.json`
**Licenza:** CC BY-SA 4.0
**URL pubblico:** `https://mxmap.it/` — Osservatorio: `https://osservatorio.mxmap.it/`

---

## 1. Executive Summary

### 1.1 Numeri di testata (edizione giugno 2026)

| KPI | Valore | Denominatore | Note |
|---|---|---|---|
| Enti monitorati | **22.987** | — | popolazione IndicePA bonificata |
| Enti con MX (coverage) | **22.328** (97,26 %) | 22.987 | confidenza media 0,85; 91,4 % ad alta confidenza |
| Enti classificati (no `unknown`) | **22.358** | — | base per ISD / CLOUD Act |
| **ISD — Indice di Sovranità Digitale** | **52,65 %** | classificati | provider sotto giurisdizione IT (3 bucket Italia) |
| **Quota CLOUD Act (USA)** | **47,34 %** | classificati | Microsoft 365 + Google Workspace + AWS + tenant MIM |
| HHI di mercato | **1.879** | — | concentrazione moderata (sotto soglia antitrust EU 2.500, sopra 1.500) |
| Top-3 concentrazione | **66,83 %** | classificati | hyperscaler + leader IT |

> **Definizioni (canoniche, in `src/mail_sovereignty/historicize.py` e `stats.py`):**
>
> - **ISD** = provider sotto giurisdizione IT (3 bucket "Italia —") / classificati.
> - **mx_jurisdiction** è una dimensione complementare (dove atterra l'MX), non usata nell'ISD.
> - **Copertura** = enti classificati / enti monitorati. L'ISD esclude gli `unknown` (2,7 %).

### 1.2 Headline (dal report, "Sintesi per i decisori")

> **Quasi una pubblica amministrazione su due affida la posta a provider extra-UE soggetti al CLOUD Act statunitense.**
>
> I provider italiani restano la prima scelta (52,65 %), ma frammentati. Lo scarto tra controllo legale (52,65 %) e collocazione tecnica dell'MX (46,1 % domestico) è esso stesso un segnale. I settori più esposti al CLOUD Act sono **Istruzione 78,16 %**, **Sanità 60,96 %**, **Ricerca 56,72 %**. Il divario territoriale è marcato: il Molise guida la sovranità (ISD 73,83 %), il Veneto è il più esposto (58,67 % CLOUD Act).

### 1.3 I 5 principali rischi per la sovranità

1. **Esposizione al CLOUD Act (47,34 % degli enti).** Provider USA (Microsoft 365, Google Workspace, AWS) sono soggetti alla norma americana 2018 (CLOUD Act, 18 U.S.C. § 2713) che consente l'accesso autoritativo a dati di clienti extraterritoriali — la sentenza *Microsoft Corp. v. United States* (2018, 2nd Cir.) ha solo parzialmente limitato l'extraterritorialità. Fonte: `kpi.json`, `report.json` §sintesi.
2. **Concentrazione in due hyperscaler.** Google Workspace (27,7 %) + Microsoft 365 (18,3 %, *display*; 14,4 % raw + 3,9 % tenant MIM) = **46,0 %** del totale — il resto del mercato è un lungo code. Top-3 a 66,83 %. HHI 1.879. Fonte: `kpi.json` `top_providers`, `market`.
3. **Settori a dati sensibili sopra soglia critica.** Istruzione 78,16 %, Sanità 60,96 %, PA Centrale 67,35 %, Trasporti 62,5 %, Ricerca 56,72 % — tutti sopra la soglia di esposizione "critica" definita dalla Strategia Cloud Italia. Fonte: `report.json` §settori, `kpi.json` `by_cluster`.
4. **Frammentazione del "Provider Italiano".** Il 33,6 % "italiano" è una aggregazione di 6+ brand (Aruba, Register.it, Seeweb, local-isp, …): leaderismo fragile, nessun singolo attore > 23 % del totale. Rischio di sostituzione progressiva da parte di hyperscaler.
5. **Debolezza del dato "unknown" + anomalie residue.** 629 enti (2,7 %) senza classificazione; ~700 anomalie aperte (mxmap.it#4) da risolvere prima di attivare la storicizzazione e la serie temporale. Fonte: `report.json` §metodologia, mxmap.it#2 e #4.

### 1.4 Cosa raccomanda l'edizione giugno 2026 (dal report, "Sintesi per i decisori")

| # | Raccomandazione | Owner |
|---|---|---|
| 1 | Censire i servizi email della PA in IndicePA e renderli monitorabili | AgID · Dip. Trasformazione Digitale |
| 2 | Inserire requisiti di sovranità nelle convenzioni quadro per la PA | Consip · MEF |
| 3 | Avviare un piano di migrazione prioritario per i settori a dati sensibili | MIM · Ministero della Salute |

---

## 2. Distribuzione completa per provider (22.987 enti)

### 2.1 Provider *grezzi* (chiavi di classificazione, da `data.json`)

| Provider | Enti | % | Giurisdizione legale | Bucket MXMap (6) | Bucket Osservatorio (4) |
|---|---:|---:|---|---|---|
| **google** | 6.374 | 27,7 % | USA (CLOUD Act) | USA (CLOUD Act) | `extra_eu` |
| **aruba** | 5.258 | 22,9 % | Italia | Italia — Provider commerciali | `it` |
| **microsoft** | 3.310 | 14,4 % | USA (CLOUD Act) | USA (CLOUD Act) | `extra_eu` |
| **independent** | 3.096 | 13,5 % | Italia (self-hosted) | Italia — Infrastruttura autonoma | `it` |
| **local-isp** | 1.717 | 7,5 % | Italia | Italia — Provider commerciali | `it` |
| **regional-public** | 954 | 4,2 % | Italia (cloud PSN/regionale) | Italia — Cloud sovrano | `it` |
| **istruzione-miur-tenant** | 893 | 3,9 % | USA (tenant `*.onmicrosoft.com` del MIM) | USA (CLOUD Act) | `extra_eu` |
| **register-it** | 667 | 2,9 % | Italia | Italia — Provider commerciali | `it` |
| **unknown** | 629 | 2,7 % | n/d | Sconosciuto | `unknown` |
| **seeweb** | 79 | 0,3 % | Italia | Italia — Provider commerciali | `it` |
| **aws** | 7 | 0,0 % | USA (CLOUD Act) | USA (CLOUD Act) | `extra_eu` |
| **zoho** | 2 | 0,0 % | India (estero non-UE) | Altri provider esteri | `extra_eu` |
| **pa-contractor-private** | 1 | 0,0 % | Italia (commerciale) | Italia — Provider commerciali | `it` |
| **TOTALE** | **22.987** | **100,0 %** | | | |

> *Riga "istruzione-miur-tenant"*: 893 enti (scuole) sono ospitati sul tenant centralizzato del Ministero dell'Istruzione (`*.onmicrosoft.com`); classificati nel bucket "Microsoft 365" lato display (è la *medesima* tecnologia) e nel bucket "USA (CLOUD Act)" lato sovranità. Fonte: `kpi.py` `PROVIDER_DISPLAY`, `sovereignty_of`.

### 2.2 Provider *aggregati per display name* (come la mappa e il KPI)

`kpi.json` `top_providers` raggruppa per "nome visibile" sommando i bucket che condividono giurisdizione:

| Display | Enti | % | Sovranità |
|---|---:|---:|---|
| **Provider Italiano** (aruba + register-it + seeweb + local-isp + pa-contractor-private + altri minori) | 7.722 | 33,6 % | `it` |
| **Google Workspace** | 6.374 | 27,7 % | `extra_eu` |
| **Microsoft 365** (microsoft + istruzione-miur-tenant) | 4.203 | 18,3 % | `extra_eu` |
| **Infrastruttura autonoma** (independent) | 3.096 | 13,5 % | `it` |
| **Cloud Italiano** (regional-public) | 954 | 4,2 % | `it` |
| **Sconosciuto** | 629 | 2,7 % | `unknown` |
| **AWS** | 7 | 0,0 % | `extra_eu` |
| **Zoho** | 2 | 0,0 % | `extra_eu` |

### 2.3 Composizione della sovranità a 4 bucket (kpi.json `sovereignty`)

| Bucket | Etichetta | Enti | % sul totale | % sui classificati |
|---|---|---:|---:|---:|
| `it` | Italiano | 11.772 | **51,2 %** | **52,65 %** (= ISD) |
| `extra_eu` | Extra-UE (CLOUD Act) | 10.586 | **46,1 %** | **47,34 %** |
| `eu_non_it` | UE (non italiano) | 0 | 0,0 % | 0,0 % |
| `unknown` | Sconosciuto | 629 | 2,7 % | (escluso) |

> **Attenzione al denominatore** (chiarito in `docs/STATS_KPI.md` §9): la *testata* usa `indices.isd` (52,65 %, sui **classificati**); la *torta* usa `sovereignty.it.pct` (51,2 %, sul **totale**, perché include l'`unknown`). Sono la stessa realtà su due basi diverse — non van-no mostrati come "numeri diversi".

### 2.4 Giurisdizione *tecnica* dell'MX (complementare)

| `mx_jurisdiction` | Enti | % | Cosa misura |
|---|---:|---:|---|
| `domestic` | 10.597 | 46,1 % | MX fisicamente in Italia |
| `foreign` | 11.397 | 49,6 % | MX fisicamente all'estero |
| `mixed` | 257 | 1,1 % | catena MX mista |
| `unknown` | 736 | 3,2 % | non determinabile |

> **Scarto ISD (52,65 %) ↔ MX-domestic (46,1 %)** = 6,5 punti. È esso stesso un finding: provider nominalmente italiani (Aruba, Register, Seeweb) hanno una quota di MX fisicamente in cloud estero; il "controllo legale" non coincide con la "collocazione fisica".

---

## 3. Valutazione di sovranità per categoria

### 3.1 Controllati esteri (USA, esposti al CLOUD Act) — rischio **ALTO**

| Provider raw | Provider display | Enti | % | Sede legale | Esposizione CLOUD Act |
|---|---|---:|---:|---|---|
| google | Google Workspace | 6.374 | 27,7 % | Mountain View, CA (USA) | **Sì** — assoggettato a 18 U.S.C. § 2713 e FISA 702 |
| microsoft | Microsoft 365 | 3.310 | 14,4 % | Redmond, WA (USA) | **Sì** |
| istruzione-miur-tenant | Microsoft 365 (tenant MIM) | 893 | 3,9 % | Tenant `*.onmicrosoft.com` gestito da Microsoft; controllo MIM nominale | **Sì** (il controllo del dato è di fatto del vendor USA) |
| aws | AWS | 7 | 0,0 % | Seattle, WA (USA) | **Sì** |
| zoho | Zoho | 2 | 0,0 % | Chennai (India) | Rischio limitrofo, ma extra-UE → estero |
| **Subtotale esteri (CLOUD Act + altri esteri)** | | **10.586** | **46,1 %** | | |

> **CLOUD Act (Clarifying Lawful Overseas Use of Data, 2018).** Impone ai "provider di servizio di comunicazione elettronica" USA di produrre dati anche se custoditi all'estero su richiesta delle autorità federali, *previo* ordine di un tribunale o warrant. Combinato con FISA 702, espone direttamente la PA italiana che usa hyperscaler USA. Per AWS la *sovereign cloud* europea di AWS (Francoforte/Brandeburgo) è annunciata ma non ancora pienamente operativa; Microsoft ha avviato "Microsoft Cloud for Sovereignty" ma con limiti analoghi. Fonte: `kpi.json` `top_providers`, `report.json` §sintesi.

### 3.2 Italiani / UE — rischio **BASSO** (operativo) / **MEDIO** (di mercato)

| Provider | Enti | % | Tipo | Rischio |
|---|---:|---:|---|---|
| **aruba** | 5.258 | 22,9 % | Provider commerciale IT leader, DC a Ponte San Pietro (BG) — 9,8 M caselle e-mail + 9 M PEC (autorità AgID) | **Basso** giuridico / **medio** di concentrazione (leader singolo) |
| **register-it** | 667 | 2,9 % | Provider IT, brand del gruppo DADA–Register (ora parte di team.blue) | **Basso** giuridico / **medio** (è di proprietà estera UE) |
| **seeweb** | 79 | 0,3 % | Provider IT, DC in Italia | **Basso** |
| **local-isp** | 1.717 | 7,5 % | ISP/IT locali (Lepida, Insiel, IKT, …) | **Basso** ma **frammentato** — qualità variabile |
| **pa-contractor-private** | 1 | 0,0 % | Outsourcer PA | **Basso** ma *n* trascurabile |
| **independent** | 3.096 | 13,5 % | Self-hosted (on-prem) della PA | **Basso** giuridico / **alto** operativo (capacità, competenze, NIS 2) |
| **Subtotale italiano** | | **~10.819 (47,1 %)** | | |

> **Nota su Register.it**: acquisito da DADA (IT) → fuse in Register (2020) → venduto a team.blue (Olanda, 2024). La sede legale resta IT, ma la *proprietà* è ora UE non-italiana; ai fini del CLOUD Act il rischio è nullo, ai fini del bucket Osservatorio resta `it`. Fonte: `kpi.json` `top_providers`, sezione "Provider Italiano".

### 3.3 Cloud pubblico italiano — rischio **BASSO** (alto valore strategico)

| Provider | Enti | % | Tipo |
|---|---:|---:|---|
| **regional-public** (Cloud Italiano) | 954 | 4,2 % | Poli regionali (Lepida in ER, Trentino Network, Insiel FVG, Lombardia Informatica /ARIA, Toscana — *esempi*) |

> Il bucket "Cloud Italiano" è il *target* della Strategia Cloud Italia. Piccolo come quota (4,2 %) ma di rilevanza strategica enorme: include molti servizi regionali, Lepida, e in prospettiva dovrebbe accrescersi con il PSN.

### 3.4 Settore pubblico / infrastruttura autonoma — rischio **MOLTO BASSO** (alto costo di gestione)

| Provider | Enti | % | Tipo |
|---|---:|---:|---|
| **independent** (Infrastruttura autonoma) | 3.096 | 13,5 % | Server di posta self-hosted della PA (comuni piccoli, ordini, piccoli enti) |
| **local-isp** (subset pubblico) | parte di 1.717 | parte | Servizi di consorzi pubblici / IKT regionali |

> Il 13,5 % di Infrastruttura autonoma è un dato **positivo dal lato della sovranità** (il dato non esce dalla PA), ma **negativo dal lato della resilienza**: NIS 2 (D.Lgs. 138/2024) classifica la PA come settore "altamente critico" e impone misure di sicurezza stringenti che un server self-hosted raramente può garantire da solo. È il "Sovrano fragile" — controllo legale sì, ma elevato rischio di sicurezza.

### 3.5 Sintesi del livello di rischio

| Categoria | Enti | % | Rischio CLOUD Act | Rischio operativo | Rischio NIS 2 | Giudizio |
|---|---:|---:|---|---|---|---|
| USA hyperscaler (Google, Microsoft, AWS) + tenant MIM | 10.584 | 46,1 % | **ALTO** | medio (lock-in) | basso (delega) | **CRITICO** |
| Provider IT commerciali (Aruba, Register, Seeweb, ISP) | 7.722 | 33,6 % | nullo | basso | basso | **BUONO** (frammentato) |
| Cloud regionale (PSN-equivalent, poli regionali) | 954 | 4,2 % | nullo | medio (in rollout) | basso | **STRATEGICO** |
| Self-hosted (independent) | 3.096 | 13,5 % | nullo | **alto** | **alto** | **SOVRANO MA FRAGILE** |
| Sconosciuto | 629 | 2,7 % | n/d | n/d | n/d | **DA MISURARE** |
| India (Zoho) | 2 | 0,0 % | limitrofo | basso | basso | **MARGINALE** |

---

## 4. Key findings — il quadro che emerge

### 4.1 I due mercati che si sovrappongono

Il dataset mostra **due mercati paralleli** con driver completamente diversi:

- **Mercato "A" — PA locale/territoriale (Enti territoriali + Ordini + Welfare + Ambiente, ~10.230 enti = 44,5 %)**: dominato da provider IT commerciali (Aruba, Register, ISP locali). **ISD 75 %**; **CLOUD Act ~25 %**. Driver: convenzioni locali, costo, abitudine, scarsa competenza tecnica.
- **Mercato "B" — PA centrale e settori specializzati (Istruzione, Sanità, Ricerca, PA Centrale, Gestori pubblici, Stazioni appaltanti, ~10.305 enti = 44,8 %)**: dominato da hyperscaler USA. **ISD 22 %** (Istruzione), 39 % (Sanità), 43 % (Ricerca). Driver: compliance a requisiti UE/globali, suite integrate (Teams, Classroom), gare Consip, PNRR.

> *Il numero che conta* (edizione giugno 2026): **47,34 % CLOUD Act**, ma il *pattern* è bimodale, non uniforme. Una politica di migrazione non può essere unica: deve differenziare per cluster.

### 4.2 Settori a dati sensibili sopra soglia critica

Dalla sezione "Analisi per gruppi" del report (kpi.json `by_cluster`, report.json §settori):

| Cluster | Enti | CLOUD Act | ISD | Provider dominante | Stato |
|---|---:|---:|---:|---|---|
| **Istruzione** (scuole, università, AFAM) | 8.403 | **78,16 %** | 21,84 % | Google Workspace | **CRITICO** |
| **Sanità** (ASL, AO) | 234 | 60,96 % | 39,04 % | Microsoft 365 | **CRITICO** |
| **Ricerca** (CNR, ENEA, …) | 68 | 56,72 % | 43,28 % | Microsoft 365 | **CRITICO** |
| **PA Centrale** (ministeri, autorità) | 52 | 67,35 % | 32,65 % | Microsoft 365 | **CRITICO** (piccolo N — *non* in spotlight) |
| **Trasporti e porti** | 17 | 62,50 % | 37,50 % | Microsoft 365 | **CRITICO** |
| **Agenzie regionali** | 76 | 53,62 % | 46,38 % | Microsoft 365 | **ATTENZIONE** |
| **Stazioni appaltanti** | 606 | 47,31 % | 52,69 % | Microsoft 365 | **ATTENZIONE** |
| **Gestori di pubblici servizi** | 1.128 | 45,01 % | 54,99 % | Microsoft 365 | **ATTENZIONE** |
| Previdenza e casse | 143 | 48,89 % | 51,11 % | Microsoft 365 | **ATTENZIONE** |
| Welfare/ASP/IPAB | 468 | 30,11 % | 69,89 % | Provider Italiano | buono |
| Enti territoriali (comuni, province, regioni) | 8.006 | 24,96 % | **75,02 %** | Provider Italiano | buono |
| Ordini/Camere/ACI | 2.021 | 23,14 % | 76,86 % | Provider Italiano | buono |
| Consorzi/Unioni | 1.464 | 27,16 % | 72,84 % | Provider Italiano | buono |
| Ambiente/Parchi | 272 | 28,96 % | 71,04 % | Provider Italiano | buono |
| Cultura | 29 | 42,86 % | 57,14 % | Provider Italiano | attenzione |

> *Insight* — Istruzione da sola vale 8.403 enti (36,5 % del totale) ed è per il 78,16 % su provider CLOUD Act. Migrare Istruzione è il singolo intervento con il maggiore impatto sull'ISD nazionale: spostare solo 2.000 scuole su cloud italiano equivarrebbe a un salto dell'ISD di circa **+8,7 punti percentuali** (da 52,65 % a ~61 %).

### 4.3 Il divario territoriale (analisi per aree)

Fonte: `report.json` §aree, costruita su `regione`/`provincia` ricavate da `ipa_codice_comune_istat` (crosswalk ISTAT, copertura 100 %).

**Top 5 regioni per sovranità (ISD):**

| Regione | Enti | ISD | CLOUD Act |
|---|---:|---:|---:|
| Molise | 275 | **73,83 %** | 26,17 % |
| Basilicata | 342 | 70,24 % | 29,76 % |
| Piemonte | 2.272 | 67,00 % | 32,96 % |
| Abruzzo | 709 | 66,32 % | 33,68 % |
| Calabria | 928 | 65,52 % | 34,48 % |

**Bottom 5 regioni (più esposte al CLOUD Act):**

| Regione | Enti | ISD | CLOUD Act |
|---|---:|---:|---:|
| Veneto | 1.667 | **41,33 %** | **58,67 %** |
| Lombardia | 3.348 | 41,92 % | 58,08 % |
| Emilia-Romagna | 1.313 | 43,40 % | 56,60 % |
| Puglia | 1.223 | 45,77 % | 54,23 % |
| Trentino-Alto Adige | 904 | 45,79 % | 54,21 % |

**Macroaree:**

| Macroarea | Enti | ISD | CLOUD Act |
|---|---:|---:|---:|
| Isole | 2.699 | **59,09 %** | 40,91 % |
| Sud | 5.405 | 57,53 % | 42,47 % |
| Centro | 4.035 | 51,25 % | 48,73 % |
| Nord | 10.848 | **49,19 %** | 50,80 % |

> **Pattern chiaro**: il Nord è più esposto al CLOUD Act (regioni con tessuto economico denso, università, grandi ASL); il Sud è più sovrano (peso di piccoli comuni su provider IT locali). Il Molise, regione più piccola, è paradossalmente la più sovrana. Veneto e Lombardia, motori economici, sono i più esposti. **Una politica di migrazione regionale potrebbe partire proprio da Nord-ovest**, dove il delta rispetto alla media nazionale è più alto.

### 4.4 Mercato: HHI e concentrazione

Dati da `report.json` `fotografia.market`:

- **Top-3 concentrazione: 66,83 %** (Provider Italiano + Google + Microsoft)
- **HHI (Herfindahl-Hirschman Index): 1.879**

> L'HHI è in "zona di concentrazione moderata" (1.500–2.500). Le linee-guida antitrust EU (DOJ/FTC USA) considerano concentrazione:
>
> - HHI < 1.500: bassa
> - 1.500–2.500: moderata
> - \> 2.500: alta (soglia di allarme)
>
> Il mercato è quindi *moderatamente* concentrato, non a rischio di monopolio imminente. **Ma** il dato aggregato nasconde la bimodalità: il sotto-mercato "PA locale/territoriale" è guidato da Aruba (22,9 %), quello "PA centrale" da Microsoft+Google (46 %). Combinati, i due hyperscaler USA hanno un potere contrattuale asimmetrico enorme *anche se* la quota aggregata non è dominante.

### 4.5 Il "sovrano fragile": il 13,5 % self-hosted

I 3.096 enti "Infrastruttura autonoma" sono nominalmente i più "sovrani" (il dato non esce), ma:

- **NIS 2 (D.Lgs. 138/2024)** classifica la PA tra i settori "altamente critici" e impone 10+ misure di sicurezza (gestione del rischio, gestione incidenti, continuità operativa, crittografia, …). Compliance onerosa per un server self-hosted di un piccolo comune.
- La copertura di competenze IT nei piccoli enti è spesso insufficiente: il modello "lo gestisce il figlio del segretario" è reale.
- ENISA Threat Landscape 2025 (4.875 incidenti analizzati) identifica la *supply chain* come minaccia primaria: i piccoli enti sono quelli con supply chain software meno controllata.

> **Insight strategico**: lo "Sovrano fragile" è un *serbatoio di migrazione*. Senza un'offerta "Cloud Italiano" accessibile (PSN, cloud qualificato QC1/QC2) e conveniente, questi enti migreranno per default verso l'iper-scalatore più accessibile (Google Workspace Education per le scuole, MS365 per i comuni medi).

### 4.6 Indice di fiducia del dataset

- **Copertura 97,26 %** (22.328 enti su 22.987 con MX). Solo il 2,7 % `unknown`.
- **Confidenza media 0,85** (su 0–1).
- **Alta confidenza (≥0,8): 91,4 %**.
- **Limite strutturale noto**: IndicePA non è una base dati pulita (mxmap.it#2). La bonifica continua è una dipendenza funzionale core. ~700 anomalie residue (mxmap.it#4) prima dell'attivazione della storicizzazione.

> Il dataset è *production-ready* per la fotografia attuale; la serie temporale partirà al run #1 (post-fix #4).

---

## 5. Procurement trends — il contesto PNRR e Consip

### 5.1 Il quadro PNRR-Missione 1 / Componente 1

Il PNRR ha stanziato ingenti risorse per la trasformazione digitale della PA, con focus specifico sul cloud:

- **Investimento 1.2 "Abilitazione al Cloud per le PA Locali"**: avvisi per Comuni (15/04/2022, 25/07/2022) e Scuole (22/04/2022, 27/06/2022), più un avviso multimisura per ASL/AO (marzo 2023). Bando più recente: **luglio 2025 (Avviso 12 — Comuni)**. Fonte: `innovazione.gov.it` (Attuazione misure PNRR) — `https://innovazione.gov.it/italia-digitale-2026/attuazione-misure-pnrr/`.
- **Investimento 1.3.1 "Piattaforma Digitale Nazionale Dati"** (PDND): contratto esecutivo attivato da AgID (CIG derivato B432ABCCD2) in adesione all'Accordo Quadro Consip "servizi applicativi in ottica Cloud" Lotto 1 (master 91918889EE), ottobre 2024.
- **Investimento 1.3.2 "Single Digital Gateway"**: AgID ha riallocato (Det. 56/2024) i servizi del Lotto 1 dell'AQ Consip IaaS/PaaS Public Cloud (master 81283942ED) e acquisito (Det. 55/2024) ulteriori servizi **Cloud PaaS AWS** tramite RDO su MePA. *Notare l'acquisto esplicito di AWS per un progetto PNRR*: la centralizzazione passa anche da hyperscaler.

> *Riferimenti puntuali*:
>
> - Determinazione AgID n. 56/2024 (rimodulazione IaaS/PaaS) — `https://trasparenza.agid.gov.it/page/103/details/3151/...`
> - Determinazione AgID n. 55/2024 (acquisizione AWS PaaS) — `https://trasparenza.agid.gov.it/page/103/details/3152/...`
> - Contratto esecutivo B432ABCCD2 (PDND) — `https://trasparenza.agid.gov.it/page/103/details/5266/...`

### 5.2 Il Polo Strategico Nazionale (PSN) — il "Cloud sovrano" italiano

- **Natura**: infrastruttura cloud ad alta affidabilità, gestita da PSN S.p.A. (partecipata da TIM, Leonardo, CDP Equity e Poste Italiane). Convenzione con il Dipartimento per la Trasformazione Digitale.
- **Adesioni 2023 → 2025**: da 120 a **576 PA** (+380 %); contratti firmati per **3,6 miliardi €** (Il Sole 24 Ore, 2025). Al 2026: **oltre 600 PA** (`polostrategiconazionale.it`).
- **Estensione deadline adesioni**: dal 24/08/2025 al **23/02/2027** (`innovazione.gov.it`).
- **Modello "italiano con tecnologia USA"**: il PSN noleggia *tecnologia* dai big tech (in particolare Oracle, VMware, Dell, IBM, …) ma con *controllo del dato* e *gestione operativa* in capo allo Stato italiano. Lettura del Sole 24 Ore: "Italy has taken the lead in launching initiatives centered on a European sovereign cloud"; lettura di Decode39: "the government's decision to use U.S. big tech only as technology suppliers — not data custodians — may discourage the very investments Europe needs".

> *Riferimenti*:
>
> - Il Sole 24 Ore, "State Clouds, the Pa accelerates" — `https://en.ilsole24ore.com/art/cloud-state-pa-accelerates-accession-380percento-contracts-36-billion-AHGCUG1D`
> - PSN — `https://innovazione.gov.it/dipartimento/focus/polo-strategico-nazionale/`
> - Decode39 — `https://decode39.com/12657/italys-cloud-strategy-hits-a-limit/`
> - Convenzione PSN — `https://www.polostrategiconazionale.it/app/uploads/2023/03/PSN-Concessione-Convenzione.pdf`

### 5.3 Gare Consip e presenza di Microsoft / Google

Le gare Consip recenti mostrano la **dipendenza strutturale** dai hyperscaler USA nella PA centrale:

- **Gara Public Cloud SaaS — CRM (ed. 2)** (ID 2700): aggiudicazione efficace del lotto 4, gara aperta SaaS per la PA. Fonte: `consip.it/bandi/gara-public-cloud-saas-crm-ed-2`.
- **AQ Public Cloud SaaS "Business intelligence" + "Produttività individuale/collaboration"**: 380 mln € attivati, due accordi quadro. Fonte: `consip.it/notizie-e-comunicati/disponibili-i-nuovi-contratti-consip-per-i-servizi-public-cloud-saas-business-intelligence-e-produttivita-individualecollaboration`.
- **Procedura negoziata Google Cloud Platform per Sogei** (ID Sigef 2607) — gara specifica per Sogei (infrastruttura critica MEF).
- **Appalto specifico Microsoft Azure per Sogei** (ID Sigef 2772, 18/07/2024): 36 mesi di sottoscrizioni.
- **Appalto specifico Microsoft Azure per INAIL** (ID Sigef 2645).
- **Microsoft Enterprise Agreement ID 2871** (bando pubblicato 28/11/2025 dal MEF, CIG Lotto 1 B9416D42F2): gara centralizzata per licenze Microsoft EA e servizi connessi per le PA.

> **Pattern**: Sogei, INAIL, MEF (licenze Enterprise Agreement), AdE (cloud SaaS) — tutta la PA centrale strategica compra da Microsoft/Google direttamente o tramite Consip. Il dataset MxMap lo riflette: 67,35 % CLOUD Act in PA Centrale, 60,96 % in Sanità.

### 5.4 La spesa ICT della PA (contesto)

- **Osservatorio FinPA 2025**: spesa ICT PA italiana (panel) **~4,6 mld €** nel 2023, >90 % del perimetro (statale + enti previdenziali/ricerca + Regioni/PA locali). Fonte: `osservatorio-finpa.it`.
- **Mercato cloud IT in crescita** (Mordor Intelligence, outlook 2030): trend di adozione spinto dal PNRR e dalla Strategia Cloud Italia.
- **Cio Survey PA 2025** (NetConsulting cube / inno3.it): digitalizzazione in slancio, ma con "nodi irrisolti" — competenze, lock-in, frammentazione.

> *Riferimenti*:
>
> - `https://www.osservatorio-finpa.it/wp-content/uploads/2026/02/Rapporto_La_spesa_ICT_nella_PA_2025.pdf`
> - `https://inno3.it/2025/05/29/cio-survey-pa-2025-slancio-digitale-e-nodi-irrisolti/`
> - `https://www.mordorintelligence.com/industry-reports/italy-cloud-computing-market`

### 5.5 Andamento dei tre pilastri della Strategia Cloud Italia

La Strategia Cloud Italia (sett. 2021, Dip. Trasformazione Digitale + ACN) si basa su **tre pilastri**:

1. **Classificazione di dati e servizi** → tre livelli: *Ordinario*, *Critico*, *Strategico*. Determina dove può andare il dato.
2. **Qualificazione dei servizi cloud** → catalogo ACN con 4 livelli (QC1 minimo → QC4 massimo), in vigore dal 1° agosto 2024 (regime ordinario dopo transitorio al 31/07/2024). Dal 19/01/2023 la qualificazione è in capo ad ACN (trasferita da AgID).
3. **Polo Strategico Nazionale (PSN)** → per dati Critici/Strategici; in rollout.

**Stato al giugno 2026**:

- **Classificazione**: AgID ha completato il censimento di banche dati e servizi; tutte le PA devono classificare i propri dati.
- **Qualificazione**: catalogo ACN pubblico e attivo; centinaia di servizi qualificati su tutti e 4 i livelli (`https://www.acn.gov.it/portale/catalogo-delle-infrastrutture-digitali-e-dei-servizi-cloud`).
- **PSN**: 576+ PA, 3,6 mld € in contratti, deadline prorogata al 23/02/2027.

> *Riferimenti*:
>
> - `https://cloud.italia.it/strategia-cloud-pa/`
> - `https://www.acn.gov.it/portale/cloud`
> - `https://www.acn.gov.it/portale/cloud/regolamento-cloud-per-la-pa`
> - `https://docs.italia.it/italia/cloud-italia/italian-cloud-strategy-docs/it/stabile/4_cloud_strategy_for_the_public_administration.html`

---

## 6. Analisi del rischio

### 6.1 Rischio vendor lock-in

Il 47,34 % degli enti è su hyperscaler USA. Il lock-in si manifesta a più livelli:

- **Tecnologico**: identità (Entra ID / Google Identity), dati (Exchange Online / Google Drive), formati proprietari (.msg, .ost, Google Docs), automazioni (Power Automate, Apps Script).
- **Contrattuale**: licenze a canone con commit pluriennale (es. Microsoft Enterprise Agreement ID 2871, MEF 2025).
- **Competenze**: formazione del personale PA sul vendor specifico; costo di re-skilling se si migra.
- **Migrazione dati**: egress fee, assenza di standard aperti per la posta (RFC 5321 + IMAP; ma calendar/contacts/identity non sono standard).

> *Stima* (Agenda Digitale, inno3, Italian Cyber Team 2025–2026): "Quando un ministero, una forza di polizia o un ospedale pubblico è in lock-in con un vendor privato extraeuropeo, la dipendenza non è solo economica: è operativa, strategica e — come vedremo — legale." ENISA Threat Landscape 2025 (4.875 incidenti) identifica la *supply chain* come minaccia primaria per le organizzazioni europee. Fonte: `italiancyberteam.it/2026/04/16/...`, `agendadigitale.eu/.../sovranita-digitale-perche-il-lock-in...`.

### 6.2 Conformità a PSN / ACN / Strategia Cloud Italia

| Categoria enti | % CLOUD Act | Compatibilità con dati *Ordinari* | Compatibilità con dati *Critici* | Compatibilità con dati *Strategici* |
|---|---:|---|---|---|
| USA hyperscaler (10.584 enti) | 100 % | ✅ sì, se qualificati ACN (sono nel catalogo) | ⚠️ sì solo con garanzie aggiuntive (UE data boundary, encryption con chiavi PA) | ❌ vietato dalla strategia |
| Provider IT commerciali (7.722 enti) | 0 % | ✅ sì | ✅ sì (qualificati) | ⚠️ parziale (dipende da ubicazione e controllo) |
| Cloud regionale (954 enti) | 0 % | ✅ sì | ✅ sì (full) | ✅ sì (PSN-aligned) |
| Self-hosted (3.096 enti) | 0 % | ✅ sì (in house) | ✅ sì (in house) | ✅ sì |

> **Conclusione**: i 10.584 enti CLOUD Act **non possono** ospitare dati Strategici secondo la normativa italiana. La quota effettiva di "non conformi potenziali" dipende dalla classificazione dei dati di ciascun ente — non misurabile dal solo MX.

### 6.3 NIS 2 e D.Lgs. 138/2024

La **Direttiva NIS 2 (UE) 2022/2555**, recepita in Italia con **D.Lgs. 138/2024**, include esplicitamente la **PA** tra i settori "altamente critici" (Allegato I). Obblighi per gli enti:

- Registrazione al portale ACN `portale.acn.gov.it` entro la scadenza (febbraio 2025 per i soggetti già identificati).
- Implementazione di misure in **almeno 10 ambiti** di gestione del rischio (art. 21).
- Notifica incidenti entro tempistiche strette (early warning 24h, notifica 72h, relazione finale 1 mese).
- Governance: obbligo di formazione degli organi direttivi, responsabilità personale.

**Implicazione per i 3.096 enti "self-hosted"**: la compliance NIS 2 è strutturalmente onerosa per chi fa da sé. Il PSN e i provider qualificati QC1–QC4 forniscono parte della compliance "as a service" — *è un driver indiretto di consolidamento verso hyperscaler o PSN*.

> *Riferimenti*:
>
> - `https://www.acn.gov.it/portale/strategia-cloud-italia`
> - `https://www.lexology.com/library/detail.aspx?g=c1595840-1211-413e-a196-7d4a130b8c9a`
> - `https://www.mimit.gov.it/it/comunicazioni/internet-e-connettivita/sicurezza-informatica/autorita-di-settore`

### 6.4 Data residency

L'Italia (Strategia Cloud) richiede che:

- Dati **Ordinari** → cloud qualificato (anche hyperscaler, se nel catalogo ACN).
- Dati **Critici** → PSN o cloud qualificato con garanzie (crittografia, localizzazione UE).
- Dati **Strategici** → **solo** PSN (o Polo Strategico Nazionale *Potenziato* in roadmap).

Realtà fisica: 49,6 % degli enti ha l'MX all'estero (anche Aruba ha una quota di server in cloud estero). Il gap tra *sovranità legale* (52,65 %) e *collocazione fisica* (46,1 %) è di 6,5 punti. Il PSN mira a chiuderlo.

### 6.5 Rischio GDPR + D.Lgs. 196/2003 (Codice Privacy)

L'uso di hyperscaler USA per dati di cittadini europei è sotto scrutinio dopo *Schrems II* (2020) e l'EU-US Data Privacy Framework (DPF, 2023). Il DPF ha riaperto i trasferimenti, ma è contestato e incerto. L'Italia richiede, nella prassi AgID, **garanzie contrattuali + tecniche** (SCC, crittografia, pseudonimizzazione) che non sempre sono implementate nei contratti standard. Rischio: sanzioni GDPR fino al 4 % del fatturato per violazione.

> *Riferimenti*: `https://cms.law/en/int/expert-guides/cms-expert-guide-to-data-protection-and-cyber-security-laws/italy`.

### 6.6 Matrice di rischio

| Rischio | Probabilità | Impatto | Enti esposti | Driver |
|---|---|---|---|---|
| Accesso autoritativo US (CLOUD Act / FISA 702) | medio-basso (richiede trigger) | **altissimo** (intercettazione) | 10.584 (46,1 %) | iperscaler USA |
| Vendor lock-in (costi, flessibilità) | **alto** | medio-alto (costi, switching) | 10.584 + parte del "italiano" | assenza di standard aperti |
| Inadempienza NIS 2 (self-hosted) | **alto** | medio (sanzioni, attacchi) | 3.096 (13,5 %) | mancanza competenze IT |
| Vendor failure (disservizio prolungato) | basso | medio (continuità operativa) | tutti | dipendenza da singolo CSP |
| Perdita di know-how tecnologico nazionale | **alto** (cumulativo) | **alto** (strategico) | tutti i cluster sopra soglia 50 % CLOUD Act | assenza di mercato IT cloud |
| Class action GDPR su trasferimenti extra-UE | medio (Schrems II-style) | **alto** (sanzioni) | 10.584 | contratti non aggiornati |

---

## 7. Raccomandazioni per la strategia di sovranità digitale della PA

> *Le raccomandazioni che seguono derivano dall'analisi del dataset (mxmap.it, kpi.json, report.json) e dal contesto regolatorio (Strategia Cloud Italia, ACN, PNRR, NIS 2).* Non sono *la* politica ufficiale (quella sta nella Strategia Cloud Italia e nel Piano Triennale), ma un'interpretazione basata sull'evidenza misurata.

### 7.1 Tre direttrici strategiche

**A. Migrazione mirata dei cluster a dati sensibili (impatto alto, costo gestibile).**

Priorità (sulla base di CLOUD Act % × n_entità × sensibilità dei dati):

1. **Istruzione** (8.403 enti, 78,16 % CLOUD Act) — il *biggest bang for the buck*. Il tenant MIM (`istruzione-miur-tenant`, 893 enti) è il *cuore* del problema: 893 scuole "ufficialmente" PA italiana ma di fatto su Microsoft 365. Una rinegoziazione MIM/Microsoft che (a) mantenga il servizio (b) ma *tolga* il dato dalla giurisdizione FISA è la singola iniziativa con il ROI più alto. Alternativa: migrazione al PSN o a cloud qualificato QC2+ con localizzazione UE esclusiva.
2. **Sanità** (234 enti, 60,96 % CLOUD Act) — ASL/AO su dati clinici. Driver: gara centralizzata Consip dedicata a Sanità su cloud qualificato con localizzazione UE *e* con requisiti di HDS (Hospital Data System). Modello possibile: estensione del modello Emilia-Romagna (Lepida + cloud sovrano regionale).
3. **PA Centrale** (52 enti, 67,35 % CLOUD Act) — *non* nello spotlight (cluster piccolo), ma politicamente e giuridicamente il più esposto. Audit mirato + migrazione al PSN per i dati classificati come Strategici.
4. **Ricerca** (68 enti, 56,72 % CLOUD Act) — anche qui cluster piccolo ma dati Strategici. Cloud qualificato con garanzia di non-trasferimento extra-UE.

**B. Consolidamento dell'offerta "Cloud Italiano" (impatto strutturale, costo politico).**

- **Crescere il bucket "Cloud Italiano" (4,2 %)** significa fare *marketing* e *convenzione* del PSN e dei poli regionali (Lepida, Trentino Network, Insiel, ARIA, …) per intercettare i **3.096 enti self-hosted** ("Sovrano fragile") *prima* che migrino verso Google/Microsoft.
- **Gare Consip dedicate a cloud sovrano QC1/QC2**: replicare il modello della Gara CRM (ed. 2) ma per *posta e collaborazione*, con vincoli di localizzazione.
- **Estensione convenzione PSN**: la proroga al 23/02/2027 è l'occasione. Target: 1.000 PA entro fine 2026 (riprendendo il trend 380 % di crescita).

**C. Differenziazione geografica (impatto mirato, costo basso).**

- Le 5 regioni più esposte (Veneto, Lombardia, ER, Puglia, TAA) hanno > 8.500 enti totali. Un programma regionale di migrazione (assistenza tecnica, fondi PNRR residui, coordinamento AgID) porterebbe +5/+6 punti di ISD a costi limitati.
- Le 5 regioni più sovrane (Molise, Basilicata, Piemonte, Abruzzo, Calabria) hanno meno di 4.500 enti: buoni *esempi* ma piccoli. Trasferire *know-how* dalle più virtuose (es. modello Lepida ER, modello Trentino) a quelle più esposte.

### 7.2 Cinque azioni operative (con owner)

| # | Azione | Owner suggerito | Orizzonte | KPI di impatto |
|---|---|---|---|---|
| 1 | **Audit mirato tenant MIM** + rinegoziazione con Microsoft per uscita dalla giurisdizione FISA sui dati delle scuole (o migrazione) | MIM + AgID + ACN | 12 mesi | -893 enti da CLOUD Act; ISD +4,0 % |
| 2 | **Convenzione quadro cloud qualificato QC1/QC2** "Posta e collaborazione PA" (con localizzazione UE garantita) | Consip + ACN | 18 mesi | -2.000 enti da CLOUD Act nei cluster Sanità / Welfare / Piccoli enti |
| 3 | **Programma "Sovrano fragile → Cloud Italiano"** per i 3.096 enti self-hosted (incentivi PSN, Lepida, poli regionali; assessment NIS 2 incluso) | Dip. Trasformazione Digitale + Regioni | 24 mesi | -1.500 enti da "independent" a "Cloud Italiano" o qualificato IT |
| 4 | **Migrazione geografica mirata** delle 5 regioni più esposte (Veneto, Lombardia, ER, Puglia, TAA) con fondi PNRR residui | Dip. Trasformazione Digitale + 5 Regioni | 18 mesi | ISD regionale minimo 50 % in tutte le 20 regioni |
| 5 | **Requisiti di sovranità nelle gare Consip esistenti** (MEF EA ID 2871, gare Azure/GCP esistenti): clausola "localizzazione UE" + "audit del dato" obbligatoria per dati *Critici* | MEF + Consip | 6 mesi (revisione bandi) | Tutte le nuove gare Consip conformi |

### 7.3 Tre azioni *abilitanti* (trasversali)

- **Misurazione continua**: il dataset MxMap va mantenuto e *reso pubblico* (CC BY-SA 4.0, già), con attivazione della storicizzazione (post-fix #4) per monitorare i trend di migrazione. KPI: ISD in crescita anno-su-anno, CLOUD Act in calo.
- **Trasparenza nelle gare**: obbligo per la PA di pubblicare (in BDNCP) il provider di posta elettronica acquistato e il livello di qualificazione (QC1–QC4). L'Anac già raccoglie i CIG, basta aggiungere il campo.
- **Formazione**: il "Sovrano fragile" è anche un problema di competenze. Investire in formazione IT di base per il personale PA (in linea con il *Piano Nazionale Scuola Digitale* e i *Competence Center* del MIMIT).

### 7.4 Tre cose da *non* fare

1. **Non vietare gli hyperscaler USA frontalmente**: la Strategia Cloud Italia non lo fa (e non lo può fare per ragioni di mercato UE). Farebbe solo danno alle PA che usano Google Classroom o Teams *legittimamente* per dati Ordinari.
2. **Non imporre la migrazione al PSN per dati Ordinari**: il PSN non ha la capacità (né probabilmente l'intenzione) di ospitare 22.987 enti. È la soluzione per dati Critici/Strategici. Per gli Ordinari bastano i qualificati QC2+.
3. **Non sottovalutare il "Sovrano fragile"**: i 3.096 enti self-hosted *oggi* sono un asset di sovranità, *domani* saranno il problema (se non si mettono in sicurezza NIS 2). Servono policy *prima* che migrino per default.

### 7.5 KPI di monitoraggio (proposta per il cruscotto pubblico)

Da aggiungere al catalogo in `docs/STATS_KPI.md` (Cat. 7–8) e alimentare dalla pipeline di storicizzazione:

| KPI | Definizione | Target |
|---|---|---|
| ISD anno-su-anno | `isd(t) - isd(t-1)` | > +2 p.p./anno |
| CLOUD Act anno-su-anno | `cloud_act_pct(t) - cloud_act_pct(t-1)` | < -2 p.p./anno |
| Cluster critici sopra soglia | % enti in Istruzione/Sanità/Ricerca/PA Centrale con CLOUD Act > 50 % | < 50 % entro 2027 |
| Regioni sotto ISD 50 % | n regioni con ISD < 50 % | 0 entro 2027 |
| Sovrano fragile | n enti in `independent` non-NIS2-compliant | < 500 entro 2027 |
| Adesioni PSN | n PA su PSN | > 1.000 entro 2026 |
| Migrazioni di sovranità | saldo eventi `sov_change: EST→ITA` − `ITA→EST` per run | > 0 (crescita netta) |

---

## 8. Limitazioni del dataset e del report

- **IndicePA non è una fonte pulita** (mxmap.it#2). Il dataset richiede bonifica continua. ~700 anomalie residue (mxmap.it#4) prima di attivare la storicizzazione.
- **Confini del dato "italiano"**: la proprietà di Register.it (team.blue, Olanda) è estera UE; ai fini del CLOUD Act è irrilevante, ma tecnicamente Register non è più "italiano" al 100 %.
- **Il "self-hosted" non è tutto sovrano in pratica**: spesso il server è in housing presso un provider estero (es. Hetzner DE) o usa antispam USA (es. Proofpoint, Mimecast). La copertura DNS non distingue questi casi.
- **Il bucket `unknown` (2,7 %)** potrebbe contenere sia falsi negativi (enti che non hanno un MX record pubblico) sia residui di dominio errato.
- **L'ISD non distingue** *dato* per *dato*: un ente su hyperscaler USA che ospita solo dati *Ordinari* è tecnicamente conforme; uno che ospita dati *Strategici* non lo è. Il dataset misura la *giurisdizione del provider*, non la *classificazione del dato* ospitato.
- **Storicizzazione non attiva**: la serie temporale parte da questa edizione (`status: "just_started"`); i trend di migrazione saranno misurabili dal run #1 in poi.

---

## 9. Conclusioni

Il quadro che emerge da 22.987 enti PA italiana è un **bilancio sfumato**, non un verdetto netto:

- **La PA italiana è oggi per il 47,34 % "esposta" al CLOUD Act** — poco meno di una su due. Non è la maggioranza, ma è una quota enorme e concentrata nei settori più delicati (Istruzione, Sanità, Ricerca, PA Centrale).
- **La sovranità "italiana" è reale al 52,65 %** ma **frammentata**: nessun singolo provider IT supera il 23 % del totale, e il *self-hosted* (13,5 %) è nominalmente sovrano ma fragile su NIS 2.
- **Il PSN sta crescendo** (576+ PA, 3,6 mld €, proroga al 2027) ma è ancora *l'eccezione*, non la regola. La Strategia Cloud Italia c'è, ha gambe (catalogo ACN, qualificazione QC1–QC4, classificazione dati), ma i **bandi Consip** continuano a comprare Microsoft e Google per la PA centrale.
- **Il pattern bimodale** (PA locale sovrana / PA centrale esposta) suggerisce che una *politica unica* non funziona: servono **mirate priorità di cluster** (Istruzione, Sanità) + **consolidamento dell'offerta italiana** (PSN, poli regionali) + **programmi regionali** (Nord-ovest).

> *La posta elettronica è solo l'inizio.* Lo stesso dataset MxMap può essere esteso ad altri servizi (PEC, DNS, DNS secondario, DNS-over-HTTPS, identità digitale, eIDAS, firme remote) per misurare la sovranità digitale complessiva della PA. È il *data engine* su cui l'Osservatorio Nazionale Sovranità Digitale costruisce la sua analisi.

---

## 10. Fonti

### Primarie (MxMap, edizione giugno 2026)

- `kpi.json` — KPI aggregati (22.987 enti, ISD 52,65 %, CLOUD Act 47,34 %, HHI 1.879, top-3 66,83 %) — generato il 2026-06-15.
- `report.json` — Report strutturato (sezioni: sintesi, fotografia, settori, aree, andamento, metodologia) — generato il 2026-06-16.
- `src/mail_sovereignty/historicize.py` — `sovereignty_of()`, `material_row()`, mappatura 6→4 bucket (fonte canonica della definizione di sovranità).
- `src/mail_sovereignty/kpi.py` — `build_kpi()`, `assert_kpi_integrity()`, mappatura provider→`SOV4`.
- `src/mail_sovereignty/stats.py` — `compute_current()`, `assert_integrity()`, definizione di ISD sui classificati.
- `docs/STATS_KPI.md` — Catalogo KPI, definizioni canoniche (denominatore ISD, gap testata/torta, mappatura cluster).

### Regulatori e normativi

- Strategia Cloud Italia (2021) — `https://cloud.italia.it/strategia-cloud-pa/`, `https://assets.innovazione.gov.it/1634299755-strategiacloudit.pdf`, `https://docs.italia.it/italia/cloud-italia/italian-cloud-strategy-docs/it/stabile/4_cloud_strategy_for_la_pubblica_amministrazione.html`
- ACN — Cloud: `https://www.acn.gov.it/portale/cloud`; Regolamento: `https://www.acn.gov.it/portale/cloud/regolamento-cloud-per-la-pa`; Catalogo: `https://www.acn.gov.it/portale/catalogo-delle-infrastrutture-digitali-e-dei-servizi-cloud`; Qualificazione (passaggio da AgID ad ACN il 19/01/2023): `https://www.acn.gov.it/portale/w/qualificazione-del-cloud-della-pa-dal-19-gennaio-passa-ad-acn`
- AgID — Cloud della PA: `https://www.agid.gov.it/it/infrastrutture/cloud-pa`; Qualificazione CSP: `https://www.agid.gov.it/it/infrastrutture/cloud-pa/qualificazione-csp`; Migrazione AgID su PSN: `https://www.agid.gov.it/it/notizie/agid-migra-sul-polo-strategico-nazionale-prosegue-lattuazione-della-strategia-cloud-italia`
- PSN — `https://innovazione.gov.it/dipartimento/focus/polo-strategico-nazionale/`; Convenzione: `https://www.polostrategiconazionale.it/app/uploads/2023/03/PSN-Concessione-Convenzione.pdf`; Risultati 2026: `https://www.polostrategiconazionale.it/media/stampa/il-cloud-sovrano-italiano-missioni-e-risultati-di-psn/`; Proroga: `https://innovazione.gov.it/notizie/articoli/polo-strategico-nazionale-prorogato-il-termine-di-adesione-alla-convenzione/`
- PNRR — Attuazione misure: `https://innovazione.gov.it/italia-digitale-2026/attuazione-misure-pnrr/`; Bando 1.2 Comuni luglio 2025: `https://presidenza.governo.it/AmministrazioneTrasparente/Sovvenzioni/CriteriModalita/PNRR_Avviso_1-2_Comuni/Luglio_2025/Avviso%2012%20-%20Comuni%20luglio%202025.pdf`
- Piano Triennale 2024-2026 (agg. 2025): `https://www.agid.gov.it/sites/agid/files/2025-02/Piano_Triennale_2024-2026_Aggiornamento2025acc_0.pdf`; capitolo Cloud: `https://docs.italia.it/italia/piano-triennale-ict/pianotriennale-ict-doc/it/2024-2026-agg-2026/capitolo-6_infrastrutture/infrastrutture-digitali-e-cloud.html`
- NIS 2 / D.Lgs. 138/2024 — `https://www.lexology.com/library/detail.aspx?g=c1595840-1211-413e-a196-7d4a130b8c9a`; `https://www.mimit.gov.it/it/comunicazioni/internet-e-connettivita/sicurezza-informatica/autorita-di-settore`; ACN adempimenti: `https://www.diritto.it/direttiva-nis-2-acn-pubblica-adempimenti-materia/`
- GDPR / D.Lgs. 196/2003 — `https://cms.law/en/int/expert-guides/cms-expert-guide-to-data-protection-and-cyber-security-laws/italy`

### Gare e procurement

- Consip — Gare Public Cloud SaaS: `https://www.consip.it/bandi/gara-public-cloud-saas-crm-ed-2`; Comunicato Business intelligence + Collaboration (380 mln €): `https://www.consip.it/notizie-e-comunicati/disponibili-i-nuovi-contratti-consip-per-i-servizi-public-cloud-saas-business-intelligence-e-produttivita-individualecollaboration`; Microsoft Azure Sogei (ID 2772): `https://www.consip.it/bandi/as-acquisizione-microsoft-azure-per-sogei`; Azure INAIL (ID 2645): `https://www.consip.it/bandi/as-fornitura-servizi-cloud-microsoft-azure-per-inail`; Google Cloud Sogei: `https://www.consip.it/bandi/procedura-negoziata-acquisizione-di-servizi-hybrid-cloud-google-cloud-platform-per-sogei`
- MEF — Microsoft Enterprise Agreement (ID 2871, bando 28/11/2025): `https://www.mef.gov.it/bandi/bandi-di-gara/2025/Gara-per-la-Fornitura-di-Licenze-duso-Microsoft-Enterprise-Agreement-e-dei-servizi-connessi-per-le-Pubbliche-Amministrazioni-ID-2871-CIG-Lotto1-B9416D42F2/`
- AgID Det. 56/2024 (rimodulazione IaaS/PaaS): `https://trasparenza.agid.gov.it/page/103/details/3151/...`; Det. 55/2024 (acquisizione AWS PaaS): `https://trasparenza.agid.gov.it/page/103/details/3152/...`; Det. 314/2024 (PDND): `https://trasparenza.agid.gov.it/page/103/details/5266/...`

### Contesto di mercato

- Osservatorio FinPA 2025 (spesa ICT PA): `https://www.osservatorio-finpa.it/wp-content/uploads/2026/02/Rapporto_La_spesa_ICT_nella_PA_2025.pdf`
- Mordor Intelligence (cloud IT mercato IT 2030): `https://www.mordorintelligence.com/industry-reports/italy-cloud-computing-market`
- Cio Survey PA 2025 (inno3): `https://inno3.it/2025/05/29/cio-survey-pa-2025-slancio-digitale-e-nodi-irrisolti/`
- Il Sole 24 Ore — Cloud di Stato +380 %, 3,6 mld €: `https://en.ilsole24ore.com/art/cloud-state-pa-accelerates-accession-380percento-contracts-36-billion-AHGCUG1D`; "Digital sovereignty: Europe divided": `https://en.ilsole24ore.com/art/digital-sovereignty-europe-divided-cloud-italy-protects-sensitive-data-AH47xsv`; "2026 will be decisive for the national sovereign cloud": `https://en.ilsole24ore.com/art/2026-will-be-decisive-in-completing-the-national-sovereign-cloud-project-AIJjHBS`
- Decode39 — Italy's cloud strategy hits a limit: `https://decode39.com/12657/italys-cloud-strategy-hits-a-limit/`
- Aruba — chi siamo: `https://www.aruba.it/chisiamo.aspx`; Wired — gestori PEC: `https://www.wired.it/internet/web/2018/12/05/gestori-pec-posta-elettronica-certificata-italia/`
- Interoperable Europe — Italy 2025 country intelligence: `https://interoperable-europe.ec.europa.eu/sites/default/files/inline-files/italy-2025-country-intelligence-report.pdf`
- Agenda Digitale — Lock-in problema strategico: `https://www.agendadigitale.eu/infrastrutture/sovranita-digitale-perche-il-lock-in-e-diventato-un-problema-strategico/`; Fornitori insostituibili: `https://www.agendadigitale.eu/cittadinanza-digitale/il-fardello-dei-fornitori-pa-insostituibili-come-liberarsene/`
- Italian Cyber Team 2026 — Vendor lock-in e sicurezza nazionale: `https://italiancyberteam.it/2026/04/16/vendor-lock-in-sovranita-digitale-e-le-raccomandazioni-europee-perche-la-dipendenza-tecnologica-e-un-problema-di-sicurezza-nazionale/`
- ZeroUno — Cloud sovrano italiano, risposta a lock-in ed egress fee: `https://www.zerounoweb.it/cloud-computing/cloud-sovrano-italiano-la-risposta-a-vendor-lock-in-ed-egress-fee/`
- inno3 — Transizione cloud e lock-in: `https://inno3.it/2025/05/06/transizione-cloud-gestire-opportunita-e-rischio-lock-in/`

---

*Report generato il 2026-06-18 — Edizione giugno 2026 di MxMap (build kpi 2026-06-15, report 2026-06-16). Dataset: 22.987 enti PA italiana, copertura DNS 97,26 %, confidenza media 0,85. Licenza CC BY-SA 4.0.*
