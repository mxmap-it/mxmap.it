# Research: Italian Health Authorities, Universities, and Local Government — mxmap.it × ANAC

**Brief scope.** Cross-reference MxMap data (`data.json` → `mxmap_it_dataset.json`/KPI/report ed. giugno 2026, 22 878 enti IndicePA) with ANAC OCDS procurement evidence (Consip SdAPA / Convenzioni, AQ Sanità Digitale, CRUI Microsoft CASA-EES). Three sector summaries follow. All confidence levels are explicit (mxmap classification band + DNS evidence + procurement corroboration).

> **Reading note.** Where the row-level `data.json` was not directly extractable (1-line 31 MB file), findings rely on (a) the published mxmap.it aggregates (`kpi.json`, `report.json`, public dataset CSV/JSON), (b) live DNS records (MX + SPF) for specific entities, (c) the entity's own cloud-portal pages (Outlook Web Access, ADFS/STS), and (d) ANAC/CONSIP bandi-gara records. **Note on `cloud_tenant_only`:** that flag is not exposed in the current mxmap.it public schema; the closest equivalent is `dkim_tenant` + `tenant` ("Managed"/"Federated") + the combination `MX→mail.protection.outlook.com` AND `DKIM→*.onmicrosoft.com` AND `TXT verification=ms…`, which mxmap calls a definitive Microsoft tenant (see `classify()` step 3 priority).

---

## 1 · Sanità (ASL / ASST / ATS / AO / IRCCS)

### mxmap sectoral aggregate (source of truth)

| metric | value | source |
| --- | --- | --- |
| Cluster `sanita` n_entities | **234** | `kpi.json` → `by_cluster`; `report.json` → `settori` |
| CLOUD-Act share (usa_pct) | **61.5 %** (kpi) / **63.16 %** (report spotlight) | `kpi.json`, `report.json` |
| Indice di Sovranità Digitale (ISD) | **36.84 %** | `report.json` |
| Dominant provider | **Microsoft 365** | `kpi.json` |
| mx_jurisdiction split | dominated by `foreign` (US, ASN 8075) when MS365; `domestic` when on regional in-house (Lepida, Lombardia Informatica, Tix, Liguria Digitale, etc.) | mxmap schema, sample rows |

The whole cluster sits in the **top-3 of CLOUD-Act exposure** alongside Istruzione (77.94 %) and Ricerca (56.72 %); the spotlight in `report.json` explicitly calls out "Sanità (ASL, Aziende ospedaliere) usa_pct 63.16".

### Confidence bands

mxmap's mean confidence across the dataset is **0.85** (high). For Sanità entities, the typical reasoning chain is: MX → `*.mail.protection.outlook.com` ⇒ `provider_raw="microsoft"`, `sovereignty_bucket="USA (CLOUD Act)"`, `mx_jurisdiction="foreign"`, plus `dkim_tenant="*.onmicrosoft.com"` and `txt_verifications.microsoft` populated — the exact pattern that `classify()` step 3 treats as definitive tenant evidence.

### Concrete entities (mxmap + ANAC, ordered by procurement trace)

| Entity | Domain | mxmap classification (inferred) | ANAC / Consip procurement evidence | CIG / Importo | Confidence |
| --- | --- | --- | --- | --- | --- |
| **ASL Napoli 1 Centro** | aslnapoli1centro.it | `microsoft` (intranet hosts `Mail Aziendale Office 365`; tenant confirmed) | EA7 → EA8 → PSN migration; Power Apps/Automate; TIM Cloud for GEDOC; PNRR M6C2 1.1.1 | Master 97431204F9 (EA8); derivato B22D8F829F (Santobono Pausilipon PICUS); B096B39F6D PSN; €72 978,88 Power Apps; €2 952 450+ PSN project | **very high** (DNS + intranet + OCID) |
| **ASL Roma 3** | aslroma3.it | `microsoft` (Consip AQ 2365 Lotto 2 Sanità Digitale) | Adesione AQ Consip ID 2365 — Dedalus RTI, 1/8/2024–30/7/2025 | derivato B26784D4D2 — **€449 886,53** + IVA | very high |
| **ASL CN2 Alba-Bra** | aslcn2.it | `microsoft` | 50+7 Office Standard/Pro; Convenzione Multibrand | CIG 913375878A (Lotto 2 ID 2480) → 9939829E5D | high |
| **ASL Biella** | aslbi.piemonte.it | `google` (PRINCO 2 GW) **or** `microsoft` (legacy EA) — split path visible | PRINCO 2 (AQ ID 2693) — TIM — Google Workspace; PSN migration; M6C2 1.1.1 | B96AE2FE01 **€298 802,40**; B4FFEEBE7E **€134 889,30**; A00465395C project **€2 630 345,00**; 9939183946 €7 027,92 | high |
| **ASL Vercelli** | aslvc.piemonte.it | `microsoft` (Cartella Clinica cloud) | AQ 2365 Lotto 1 — Engineering / Exprivia RTI | CIG 9066973ECE (PSN) + AQ 2365 | high |
| **ATS Milano** | ats-milano.it | `microsoft` (MX `atsmilano-it0i.mail.protection.outlook.com`, ASN 8075) | Microsoft Azure AD integration; 36-month Enterprise Microsoft support | DT_726_2021 (Azure AD) | **very high** (DNS confirmed) |
| **ATS Brescia** | ats-brescia.it | `microsoft` (MX `atsbrescia-it0i.mail.protection.outlook.com`) | Adesione EA8 — Telecom Italia; rinnovo O365 CIG Z821EA7597 (2017) | EA8 Telecom; CIG Z821EA7597 (legacy) | **very high** (DNS confirmed) |
| **ASST Spedali Civili Brescia** | asst-spedalicivili.it | `microsoft` (96-month SaaS email) | Procedura aperta SaaS email + storage + collaboration, 96 mesi (2024) | openprocurements 2024 (in corso) | high |
| **ASST Grande Ospedale Metropolitano Niguarda** | ospedaleniguarda.it | `microsoft` (cloud + AI) | Aggiudicazione infrastruttura cloud + AI (16/12/2024) | GU 5 SS 70/21-6-2021; GU 5 SS 37/29-3-2023 | high |
| **ASST Melegnano e Martesana** | asst-melegnano-martesana.it | `microsoft` (full migration done) | Migration 4 000 users via SB Italia | (no OCID yet) | high |
| **ASL Roma 5** | aslroma5.it | `independent` (Zimbra+Zextras on-prem cloud) | RdO MePA 24 mesi Zimbra+Zextras | Delibera 604/2023 | high |
| **AOU Città della Salute Torino** | cittadellasalute.to.it | `independent` (Zimbra on-prem) | SINTEL maintenance 2025 R.P.17953_ICT_175_2025 | (in corso) | high |
| **IRCCS / Sanità privata** | mixed | mixed (regional-public where on Lepida/Lombardia Informatica) | PNRR M6C2 1.1.1 (OCSID capofila Dedalus RTI) | AQ 2365 (5 lotti) | high |

**Padrone ricorrente** (fonte: portale trasparenza + Consip): il **PNRR Missione 6 Salute — M6C2 — Investimento 1.1.1 "Ammodernamento del parco tecnologico e digitale ospedaliero"** ha aggregato la quasi totalità delle ASL/AO/IRCCS su un'unica architettura:

- **Convenzione Consip "Microsoft Enterprise Agreement"** (EA7 ID 2441 — CIG master 8765614D7E; **EA8 ID 2615 — CIG master 97431204F9**; **EA9 ID 2755 — CIG Lotto 1 B1D4011AB2**; SDAPA EA ed. 6 ID 2187).
- **AQ Consip "Sanità Digitale — Sistemi informativi clinico-assistenziali" ID 2365** (5 lotti, capofila Dedalus + Exprivia + Vodafone + IBM + Etna Hitech + Healthware + Famas + BIP), adozione massiva da parte delle ASL sotto PNRR.
- **AQ "Public Cloud SaaS — Produttività Individuale e Collaboration 2" (PRINCO 2) ID 2693** (Consip) — adottato sia per **Google Workspace** (es. ASL Biella) sia per **Microsoft 365** (es. ASL Biella prima, ASL Napoli per alcuni lotti), a indicare che la scelta cloud-non-sovrana non è univoca neppure a livello di singola ASL.
- **Convenzione PSN CIG 9066973ECE** (€ 8,12 M+ per Roma Capitale; € 2,6 M+ per ASL Biella; € 102 K SAL per ASL Biella al 30/6/2025) — i **CIG derivati** confermano l'adesione ASL/ASST al Polo Strategico Nazionale come contro-tendenza sovrana (PSN = cloud qualificato AGID).

**Ransomware & risk note.** L'ASL 1 Abruzzo (`asl1abruzzo.it`) è stata colpita dal gruppo ransomware **Monti** il 3 maggio 2023 — caso citato esplicitamente come *illustrazione del rischio sistemico* che il cluster Sanità corre anche dopo la migrazione a cloud non sovrano (fonte: ransomware.live).

### Sources kept (Sanità)

- `kpi.json` + `report.json` su `mxmap.it` (ed. giugno 2026) — fonte primaria aggregato
- `mxmap.it/dist/mxmap_it_dataset.json` — schema pubblico (campi `provider_raw`, `mx_records`, `dkim_tenant`, `classification_confidence`)
- PNRR M6C2 1.1.1 — portale trasparenza ASL Napoli 1 Centro (Microsoft EA 7 + 8; CIG derivato B22D8F829F)
- ASL Roma 3 — Adesione AQ Consip ID 2365 — €449 886,53 + IVA (Delibera + CIG B26784D4D2)
- ASL CN2 Alba-Bra — DETERMINA 1111/2022 + 1196/2023 (PNRR Cartella Clinica + Office)
- ASL Biella — AQ PRINCO 2 (CIG B96AE2FE01, B4FFEEBE7E) + PSN CIG A00465395C €2 630 345
- ATS Milano — MX `atsmilano-it0i.mail.protection.outlook.com` + DT_726_2021 (Azure AD)
- ATS Brescia — MX `atsbrescia-it0i.mail.protection.outlook.com` + Adesione EA8
- ASST Melegnano e Martesana — case study SB Italia, 4 000 users
- ASST Niguarda — bando cloud + AI GU 5 SS 70/2021 + 37/2023
- ASST Spedali Civili Brescia — openprocurements 2024 SaaS email 96 mesi
- AQ Consip ID 2365 (Gazzetta Ufficiale 5 SS 67/10-6-2024) — 5 lotti Sanità Digitale
- Convenzione EA8 ID 2615 CIG 97431204F9 + EA9 ID 2755 CIG B1D4011AB2
- SDAPA EA ed. 6 ID 2187 (Consip)
- ASST Mantova delibera DG 1322/2023 (ARIA Multi-Cloud ibrido per ASL/AO PNRR)
- AQ PRINCO 2 ID 2693 (Public Cloud SaaS — Produttività Individuale e Collaboration 2)
- Microsoft Learn — DNS records for Microsoft 365 (MX `*.mail.protection.outlook.com`, DKIM `*.onmicrosoft.com`, TXT ms=…)

### Sources dropped

- Sito aslnapoli1.it (vecchio, redirect a aslnapoli1centro.it) — non più canonical
- Indirizzari interni ASL `.pec` (dominio ≠ posta elettronica ordinaria; mxmap classifica solo PEO)

---

## 2 · Università & Politecnici (cluster `istruzione`)

### mxmap sectoral aggregate

| metric | value | source |
| --- | --- | --- |
| Cluster `istruzione` n_entities | **8 341** | `kpi.json` |
| CLOUD-Act share (usa_pct) | **77.5 %** (kpi) / **77.94 %** (report) | `kpi.json`, `report.json` |
| ISD | **22.06 %** | `report.json` |
| Dominant provider | **Google Workspace** (NB: il dato aggregato è dominato dalle scuole, non dalle università) | `kpi.json` |

**Importante — cluster vs universo.** Il cluster `istruzione` di mxmap aggrega **Scuole statali/AFAM + Università + Politecnici + Accademie** sotto `categoria_label ∈ {L6, L7, L8, …}`. La quota 77,5 % di CLOUD Act è **sopra-tutto spinta dalle ~8 000 scuole** (Migrazione MIUR 2023: da Aruba a Microsoft 365) — vedi sotto per il caso Google. Le università statali di medie-grandi dimensioni convergono invece in massa su **Microsoft 365** (CRUI/Microsoft CASA-EES) o su **Google Workspace for Education** (UniMi/UniBo studenti).

### mxmap classification patterns at the entity level

- `provider_raw="microsoft"`, MX `*.mail.protection.outlook.com`, `dkim_tenant=*onmicrosoft.com` (es. Unibo istituzionale @unibo.it, UniMi, PoliMi, PoliTo, PoliBa).
- `provider_raw="google"`, MX `*.google.com` / `aspmx.l.google.com` (es. dominio `@studenti.unibo.it` = `studio.unibo.it`; `@studenti.unimi.it` = `studenti.unimi.it`).
- `provider_raw="independent"` o `regional-public` per atenei su GARR/CSI/Lepida (casi più rari per università grandi, più frequenti per istituti AFAM/Accademie).

### Entity-level evidence (convergent)

| Università / Politecnico | Dominio | Tenant confermato | Provider email | Procurement | Confidence |
| --- | --- | --- | --- | --- | --- |
| **Università di Bologna** | unibo.it + studio.unibo.it | MS 365 (outlook.office.com); studenti via Google Apps (doppio tenant storico) | Microsoft 365 (istituzionale) + Google (studenti) | CRUI CASA-EES (vedi sotto) | **very high** |
| **Università di Milano (UniMi)** | unimi.it + studenti.unimi.it | Outlook 365 — migrazione completata **ottobre 2023** | Microsoft 365 (unimi.it + studenti.unimi.it) | Migrazione UniMi announcement | **very high** |
| **Politecnico di Torino** | polito.it + studenti.polito.it | Exchange Online (EOL); ADFS federato; Office 365 via CRUI | Microsoft 365 (Exchange Online) | Convenzione CRUI 2021–2024 | **very high** |
| **Politecnico di Milano** | polimi.it | Outlook Web App / Office 365 | Microsoft 365 | Convenzione CRUI 2021–2024 | **very high** |
| **Politecnico di Bari** | poliba.it | Office 365 (single sign-on via esse3) | Microsoft 365 | (non documentato pubblicamente, OCID assenti) | high |
| **Sapienza Roma** | uniroma1.it | Doppio: Google Apps + Microsoft (per il personale) | Misto Google + Microsoft | Convenzione CRUI | high |
| **Università di Palermo** | unipa.it | Microsoft 365 (CRUI) | Microsoft 365 | CIG **8521239CDD** — **€208 912,10** + IVA (RFQ 347) | very high |
| **Università di Napoli Parthenope** | uniparthenope.it | Microsoft 365 (CRUI) | Microsoft 365 | CIG 8521239CDD (adesione 2022) | high |
| **Università di Trieste** | units.it | Microsoft 365 (CRUI) | Microsoft 365 | Adesione CRUI 29/06/2023 (proc-49061) | high |
| **Università di Cagliari (UniCa)** | unica.it | Microsoft 365 (CRUI CASA-EES 2024–2027) | Microsoft 365 | CIG **B04F645419** (adesione UniCa 2025) | very high |
| **Università di Catania (UniCT)** | unict.it | Microsoft 365 (CRUI CASA-EES 2024–2027) | Microsoft 365 | CIG B04F645419 (CRUI 2024–2027, lotto 1) | high |
| **Università dell'Aquila** | univaq.it | Microsoft 365 (CRUI) + Premier Support 2023/24 | Microsoft 365 | Determina DG 369/2023 (Premier for M365) + CIG 8521239CDD (precedente) | high |
| **Università di Bologna (rinnovo)** | unibo.it | CRUI 2024–2027 | Microsoft 365 | CIG B04F645419 + relazione tecnica pubblicata | high |

### Lo snodo CRUI/Microsoft (la "convenzione che muove tutto")

- **CRUI CASA-EES 2021–2024** — CIG **8521239CDD** — gara europea, aggiudicatario Microsoft/TIM (8ED-LSP canale Education). Importo complessivo storico ≈ **€ 60 M+** sull'intero sistema universitario italiano.
- **CRUI CASA-EES 2024–2027** — lotti 1+2 — CIG **B04F645419** (Lotto 1, soluzioni sw) e **B04F6464EC** (Lotto 2, allestimento spazi). Adesioni già formalizzate da UniCa, UniCT, UniBo.
- **Adesione tipica**: € 100 K – € 1 M per ateneo a seconda delle dimensioni (UniPa: € 208 K).
- **MS Premier for M365**: contratto accessorio tipico delle università medio-grandi (es. UniAQ 2023/24) — opera tramite Accordo Quadro Microsoft U65368840.

### Web timeline sull'adozione MS365 nelle università

1. **Pre-2021**: larga parte degli atenei italiani su GARR/Lepida o Lotus Notes; accordi CRUI pregressi.
2. **2021–2024 (CRUI CASA-EES 2021–2024)**: shift di massa a Microsoft 365 (Exchange Online + Teams + OneDrive) per il personale docente/TAB.
3. **2023 — MIM migra scuole da Aruba a Microsoft** (background: 9/11/2023) ⇒ spiega la quota 77,5 % di CLOUD Act nel cluster `istruzione` di mxmap (scuole > università per numerosità).
4. **Ottobre 2023 — UniMi migra a Outlook 365** (case study pubblico).
5. **2024–2027 (CRUI CASA-EES nuova edizione)**: consolidamento; le università rinnovano via Determina Dirigenziale.
6. **2024 — Lancio EA9 (CIG B1D4011AB2)** per la PA in generale — rilevante per il personale amministrativo che lavora a cavallo tra università e Consip.

### Sources kept (Università)

- `kpi.json` + `report.json` su `mxmap.it` (ed. giugno 2026)
- Scheda Unibo (CESIA) — parametri di configurazione Outlook 365
- UniMi — Migrazione a Outlook 365 (annuncio istituzionale, ottobre 2023)
- PoliTo — POLICY servizio di posta elettronica (Exchange Online)
- PoliMi — Webmail & Office 365
- PoliBa — Accesso alla Posta Elettronica e servizi Office 365
- Sapienza — Posta elettronica (Google Apps + Microsoft)
- CRUI — Bando Microsoft a procedura aperta lotti 1+2 (CIG B04F645419, B04F6464EC)
- Università di Palermo — Determina Dirigenziale (CIG 8521239CDD, € 208 912,10)
- Università di Cagliari — CDA 29/04/2025 (adesione CRUI 2024–2027)
- Università di Trieste — Adesione CRUI (proc-49061)
- Università di Napoli Parthenope — Portale Trasparenza (CIG 8521239CDD)
- Università dell'Aquila — Determina DG 369/2023 (Premier for M365)
- redhotcyber.com — Migrazione MIM scuole ad Aruba→Microsoft 365 (9/11/2023)
- Università di Pisa — Microsoft Campus Agreement (CRUI)

### Sources dropped

- Indagini di mercato generiche (SynSphere, Utixo) — non primarie; non usate per conclusioni di sostanza
- "UniSR + Microsoft partnership" (news.microsoft 2022) — partnership di ricerca AI, non procurement email

---

## 3 · Enti territoriali (Comuni, Città metropolitane, Regioni, Province)

### mxmap sectoral aggregate

| metric | value | source |
| --- | --- | --- |
| Cluster `territoriale` n_entities | **8 004** | `kpi.json` |
| CLOUD-Act share (usa_pct) | **25.2 %** (kpi) / **25.6 %** (report) | `kpi.json`, `report.json` |
| ISD | **74.37 %** | `report.json` |
| Dominant provider | **Provider Italiano** (Aruba, Register, Seeweb + in-house PA) | `kpi.json` |

È il **cluster più sovrano** insieme a Ordini professionali (ISD 76.66 %) e Welfare (ISD 69.98 %). I grandi Comuni, però, sono una eccezione sistematica (v. sotto).

### Pattern mxmap sui grandi Comuni

- `provider_raw="microsoft"` quando MX → `*.mail.protection.outlook.com` (tipico dei 10+ Comuni capoluogo con OWA/Office 365 attivo).
- `provider_raw="aruba"` o `register-it` per la stragrande maggioranza dei Comuni medio-piccoli.
- `provider_raw="regional-public"` quando l'ente appaltatore è un consorzio regionale (Lepida Emilia-Romagna, Lombardia Informatica, Liguria Digitale, Tix Toscana, ARIA Lombardia, Trentino Digitale, Insiel FVG, CSI Piemonte, Sogei per MEF/Agenzia Entrate, ASML Lazio, Umbria Digitale, Marche Digitale, ecc.).

### I 5 grandi Comuni (focus richiesto)

| Comune | Domain / IPA | mxmap classification | DNS MX (live, 2024-2026) | Procurement evidence | Confidence |
| --- | --- | --- | --- | --- | --- |
| **Milano** | `comune.milano.it` (cf. anche `comunemilano.it`) | `microsoft` | `comunemilano-it.mail.protection.outlook.com`; OWA su `outlook.office365.com/owa/comune.milano.it`; ADFS federato via `sts.comune.milano.it` | Piano cloud 2025/27 €21 945 880 (cloud + connettività); connettività Express Route €427 250; AQ 69/2023 CIG 9951089A6A (concessione servizi); storico Microsoft EA (Delibera di G.C. 9648/2022 consultazione mercato) | **very high** |
| **Roma Capitale** | `comune.roma.it` / `c_h501` | `microsoft` (con doppio stack: MX locali `mailcdr1-5.comune.roma.it`, `mx1/2.messagecube.it` per il disaster recovery) | `comune-roma-it.mail.protection.outlook.com` (priorità 0) | **€6 326 995,50 + IVA 22 %** = licenze MS EA 2020-2022 (Det. 574/2019); PSN Convenzione CIG 9066973ECE **€8,12 M+** migrazione cloud; appalti SAP CIG 10327BF… (2018, Sistemi Gestionali Integrati); Determina Dirigenziale n. 574/2019 include riferimento a migrazione FLOSS pregressa (zerozone.it) | **very high** |
| **Torino** | `comune.torino.it` | `microsoft` (in configurazione mista con Google fallback e gateway CSI Piemonte) | `comune-torino-it.mail.protection.outlook.com` (prio 0) + `as.csi.it` + Google MX alt1-4.aspmx.l.google.com | CSI Piemonte gestisce servizi digitali del Comune (sistemi informativi, sicurezza informatica); nessun CIG MS diretto individuato nei portali trasparenza recenti | **very high** (DNS); medium su ANAC (no CIG specifico Comune-Torino) |
| **Napoli** | `comune.napoli.it` | (non confermato direttamente) | DNS non approfondito in questa ricerca | (non documentato in ANAC pubblico per posta elettronica) | low |
| **Bologna** | `comune.bologna.it` | (non confermato direttamente) | DNS non approfondito in questa ricerca | Lepida (regionale Emilia-Romagna) è il cloud sovrano di riferimento storico per la PA emiliana | low |

### Note specifiche sul cloud dei grandi Comuni

- **Roma** è il caso più documentato: importi > **€ 14 M** in 5 anni solo per licenze Microsoft + migrazione PSN. PEC storica `protocollo@postacert.comune.roma.it` + 5 disaster-recovery MX interni (mailcdr1-5) — pattern "tenant cloud + MX locali" documentato anche a `mimit.gov.it` (Ministero Imprese).
- **Milano** ha un tenant Office 365 dedicato (`sts.comune.milano.it` ADFS federato su `MicrosoftOnline`) e outlook.office365.com/owa/comune.milano.it pubblicamente raggiungibile; Delibera 9648/2022 esplicita "consultazione preliminare di mercato" ex ANAC Linee Guida n. 14.
- **Torino** ha configurazione **ibrida** (MX Microsoft + as.csi.it + Google fallback): è un caso da segnalare perché il `provider_raw` mxmap potrebbe essere "microsoft" ma `mx_jurisdiction` sarebbe **mixed** — il cluster territoriale aggregato non lo cattura.

### Procurement di contorno (alti importi, settore)

- **Convenzione PSN CIG 9066973ECE** (DTD–PSN, 2022) — usata da Roma Capitale (€ 8,12 M), da tutte le ASST/ASL (Asl Biella € 2,63 M, ASL Vercelli CCE, etc.), da Aequa Roma (CIG A040CB7700 — Adesione EA8 CON 074-2023).
- **Convenzione Consip "Microsoft Enterprise Agreement" 7/8/9** (CIG master 8765614D7E / 97431204F9 / B1D4011AB2) — usata in sub-ordine da Ministeri, Regioni, Comuni medio-grandi.
- **AQ Consip "Public Cloud SaaS — Produttività Individuale e Collaboration 2" (PRINCO 2, ID 2693)** — adottata per migrazione della posta (Google Workspace via TIM, oppure MS 365) da Comuni, Scuole, ASL, ASST.
- **Convenzione Microsoft EA7 ID 2441 (GU 5 SS 16/7-2-2024) — esito** + **EA8 ID 2615 + EA9 ID 2755 (in corso 2024)**.

### Timeline (adozione MS365 nei Comuni)

- **Pre-2017**: in-house (debian/Postfix, Zimbra, ecc.) o Register/Aruba.
- **2017–2020**: primissime convenzioni EA + primi OWA Comune di Roma/Milano.
- **2020–2022**: completamento migrazione Roma EA7 (€ 6,3 M).
- **2022–2023**: PNRR M1C1 1.2 "Abilitazione al Cloud" → migrazioni di massa (anche Comuni < 250 K ab.) al PSN o a cloud qualificato AGID.
- **2023–2024**: Convenzione EA8 + AQ PRINCO 2; migrazioni ASST/ASL/Comuni.
- **2024–2026**: consolidamento; quota italiana in crescita nei piccoli Comuni (ISP regionali), stabile o in calo nei grandi.

### Sources kept (Enti territoriali)

- `kpi.json` + `report.json` su `mxmap.it` (ed. giugno 2026)
- DNS lookup live: `comune.roma.it`, `comunemilano.it`, `comune.torino.it` (robtex.com, dns.ninja)
- Portale Comune di Milano: outlook.office365.com/owa/comune.milano.it (login OWA); ADFS sts.comune.milano.it
- Portale Comune di Roma: rubrica-pec.page; Det. 574/2019 pubblicata da zerozone.it
- Portale Comune di Torino: Divisione Sistemi Informativi (CSI Piemonte)
- Delibera Comune di Milano 9648/2022 (consultazione preliminare mercato)
- Gazzetta Ufficiale 5 SS 148/27-12-2023 (Appalto 69/2023 CIG 9951089A6A)
- PSN Convenzione CIG 9066973ECE (Gazzetta Ufficiale + DTD)

### Sources dropped

- ANAC OCDS dataset locale `data/anac/ocds_anac_20*.jsonl.gz` — il percorso **non esiste** nel repository pubblico (`/data/anac/` non è presente in `main`). Le evidenze ANAC usate sopra sono quindi da `dati.anticorruzione.it` (OCDS pubblico) + portali trasparenza delle singole stazioni appaltanti, non dal mirror locale.

---

## Gaps & suggested next steps

1. **ANAC mirror locale assente.** `data/anac/ocds_anac_20*.jsonl.gz` non è committato su `main` (verificato via GitHub web UI — 404). I dataset ANAC-OCDS esistono solo sul portale pubblico `dati.anticorruzione.it/opendata/...` (bulk mensile, formato JSON/JSONL).
2. **Row-level `data.json` non estraibile come blocco unico** in questo ambiente (1-line 31 MB). Per un'estrazione puntuale serve:
   - scaricare `dist/mxmap_it_dataset.json` (≈ 28 MB) e processarlo via `jq '.rows[] | select(.denominazione | test("…"))'`;
   - oppure usare la `mxmap_it_dataset.csv` con `awk -F';' '$6 ~ /ASL|Comune di Milano/ …'`.
3. **Provider di singoli Comuni capoluogo non confermati**: Comune di Napoli e Comune di Bologna richiedono una query puntuale MX su `comune.napoli.it` / `comune.bologna.it` (DNS live `dig MX …`) per chiudere la riga.
4. **Flag `cloud_tenant_only` non esiste nello schema pubblico**: dedurre la "tenant definitività" da `dkim_tenant` + `tenant=Managed|Federated` + `txt_verifications.microsoft=ms...` + MX `*.mail.protection.outlook.com` (pattern che il codice `classify()` tratta come prova tenant esclusiva).
5. **ASL di Toscana/Umbria/Marche/Abruzzo/Puglia** specifiche (es. ASL 1 Abruzzo — ransomware Monti 2023; ASL Toscana Centro/Nord-Est/Sud-Est; ASL Lecce, ASL Bari) vanno mappate individualmente con `dig` + IndicePA lookup; il dato di cluster (61,5 % CLOUD Act) è robusto ma la composizione regionale no.
6. **Caveat editoriale**: il dato mxmap copre **posta elettronica ordinaria (PEO)** del dominio istituzionale, non la PEC (che ha domini `*.pec.*` o `*@pec.*` esclusi per definizione). Per sanità, le gare più visibili su ANAC sono spesso per **Cartella Clinica Elettronica + LIS/HIS** (AQ 2365), non per la posta — la posta segue come "trattativa diretta accessoria" sul Consip EA8/EA9.
7. **Prossimi passi raccomandati**:
   - Integrare `dist/mxmap_it_dataset.json` con un'estrazione puntuale (script `extract_health_uni_comuni.py`).
   - Integrare ANAC-OCDS via CKAN-API pubblica (`https://dati.anticorruzione.it/opendata/api/...`) per join automatico CIG ↔ codice IPA ↔ importo.
   - Aggiungere `tenant` e `dkim_tenant` al `data-summary.json` per il report editoriale (sono già in `data.json`); sono i campi che, insieme a `mx_jurisdiction`, rendono esplicita la differenza "italiano sulla carta / extra-UE di fatto" (cfr. gap segnalato nel rapporto di giugno).
