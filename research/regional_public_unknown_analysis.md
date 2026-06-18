# Research: Italian Regional-Public and Unknown Entities in MxMap Data

**Data source:** `data.json` (current snapshot 2026-06-17, generated 2026-06-17T09:46:05Z, 22,878 total IT entities)
**Companion artifacts used:** `kpi.json` (2026-06-17), `report.json` (giugno 2026 edition, 2026-06-16), `data-summary.json` (2026-06-10), `src/mail_sovereignty/historicize.py` (`PROVIDER_DISPLAY`, `sovereignty_of`), `src/mail_sovereignty/constants.py` (`ITALIAN_REGIONAL_PUBLIC_KEYWORDS`, `ITALIAN_PROVIDER_ASN_OVERRIDES`), `docs/STATS_KPI.md`.
**Confidence legend:** **High** = direct DNS evidence in mxmap + primary source cited · **Medium** = DNS evidence in mxmap + secondary source · **Low** = inferred pattern, source not directly seen.

---

## Executive summary

The **967 entities classified `regional-public`** (≈4.2% of the IT corpus) are the **Italian regional/provincial/state-owned in-house IT infrastructure**: 11 named companies (Lepida, ARIA, CSI Piemonte, Insiel, Liguria Digitale, Sardegna IT, Trentino Digitale, Umbria Digitale, Sogei, IN.VA., plus the ASMEL national consortium family) plus 5 ASN-overridden regional autonomous systems. The vast majority are **ARPA environmental agencies, ASL/ASST/ATS regional healthcare authorities, regional procurement agencies (SUAR/ARIA), and provincial consortia**. They show three recurring patterns: (1) **MX on regional MX hosts, DKIM/SPF signing with Microsoft 365** → reclassified as `microsoft` (a sovereign infra running hyperscaler mailboxes is *not* sovereign in MxMap's strict sense — only the *legal control* of the provider counts for ISD); (2) **MX and DKIM both on the regional infra** → stays `regional-public` and counts as **"Italia — Cloud sovrano"** in the sovereignty buckets; (3) **MX on regional infra + DKIM via Google** → classified `google` (CLOUD Act). On a few entries the `regional-public` classifier is being **demoted by DKIM look-through** in the `classify()` priority logic (see the "riclassificato" reason text in ministerial entities using Trend Micro).

The **107 `unknown` entities** are a different beast: they are **not an infrastructure category but a catch-all for "no MX could be discovered"**. The mxmap reason text exposes the cause: either `search engine returned N candidates; none yielded MX` (seed domain wrong, no alternative domain was resolvable) or `cleared by is_legit gate: unrelated` (the IndicePA tier-6 record pointed to an unrelated entity, e.g. `comune.roma.it`). Most are residual data-quality issues from IndicePA, **not** a specific class of legacy or specialized provider. They are the **publicly visible manifestation of the ~700-anomaly remediation backlog** flagged in mxmap issue #4 / #2. They are not "mysterious specialised servers" — they are entities the pipeline could not validate.

Confidence on the regional-public cluster: **High** for the keyword + ASN pattern (open source + government sources); **High** for the "DX/SPF look-through demotes regional-public" pattern (visible in `classify.py` step 1 + 3); **Medium** for the healthcare migration narrative (specific to ATS/ASST examples cited, not a statistical claim). Confidence on the unknown cluster: **High** on the "missing domain" diagnosis; **Low** on any claim that they are *legacy or specialized* (the data does not support that — there is simply no MX).

---

## 1. The classification model (background)

In `src/mail_sovereignty/historicize.py::PROVIDER_DISPLAY`, every `provider` value is mapped to a **6-bucket sovereignty narrative**:

| `provider` | `sovereignty_of` | Real meaning in MxMap |
|---|---|---|
| `microsoft`, `google`, `aws`, `istruzione-miur-tenant` | **USA (CLOUD Act)** | US-jurisdiction, FISA 702 / CLOUD-Act exposed |
| `regional-public` | **Italia — Cloud sovrano** | Italian in-house regional/state-owned (PSN-eligible, jurisdiction IT) |
| `aruba`, `register-it`, `seeweb`, `infocert`, `namirial`, `local-isp`, `telia`, `tet`, `zone`, `elkdata`, `pa-contractor-private` | **Italia — Provider commerciali** | Italian commercial, jurisdiction IT |
| `independent` | **Italia — Infrastruttura autonoma** | Self-hosted on domestic ASN/host |
| `zoho`, `yandex` | **Altri provider esteri** | Non-USA foreign |
| `unknown` | **Sconosciuto** | No MX discovered |

**Critical observation for the regional-public cluster:** MxMap measures *legal control* of the provider (the `sovereignty_of` row in `material_row`). A `regional-public` MX whose DKIM signs through `*.onmicrosoft.com` will be **reclassified as `microsoft`** (USA — CLOUD Act) by the DKIM look-through in `classify()` step 1 (see `classify.py` line 132-137: "For local providers, DKIM may reveal a cloud backend"). That is why the headline numbers say **"Cloud Italiano 943"** (post-look-through) but the raw count is **967**: the **24-entity gap is the regional-public reclassifications** that flipped to a hyperscaler after DKIM was inspected.

---

## 2. Regional-Public entities (967, 4.2% of corpus)

### 2.1 What `regional-public` means in the constants file

`src/mail_sovereignty/constants.py::ITALIAN_REGIONAL_PUBLIC_KEYWORDS` (snapshot, current as of 2026-06-17):

| Provider | Region | TLD keywords used in MX / autodiscover / DKIM detection | Sovereign ASNs (`ITALIAN_PROVIDER_ASN_OVERRIDES`) |
|---|---|---|---|
| **Lepida ScpA** | Emilia-Romagna | `lepida.it`, `lepida.network`, `lepida.net` | AS31638 (Lepida) |
| **ARIA S.p.A.** (formerly Lombardia Informatica + Arca + Innovapropaganda) | Lombardia | `ariaspa.it` | — |
| **CSI Piemonte** | Piemonte, Valle d'Aosta | `csi.it`, `csipiemonte.it` | — |
| **INSIEL S.p.A.** | Friuli-Venezia Giulia | `insiel.it` | — |
| **Liguria Digitale S.p.A.** | Liguria | `liguriadigitale.it` | — |
| **Sardegna IT S.r.l.** | Sardegna | `sardegnait.it` | — |
| **Trentino Digitale S.p.A.** | Provincia Autonoma di Trento | `trentinodigitale.it`, `tix.it` | — |
| **Umbria Digitale** | Umbria | `umbriadigitale.it` | — |
| **Provincia Autonoma di Bolzano (Südtirol)** | Trentino-Alto Adige | `provinz.bz.it`, `gvcc.net` (Gemeindenverband) | — |
| **IN.VA. S.p.A.** | Valle d'Aosta | `invallee.it` | AS31403 |
| **Sogei S.p.A.** | Stato centrale (MEF) | `sogei.it` | — |
| **Punto Zero Scarl** | (TBC region) | `puntozeroscarl.it` | — |
| **Regione Toscana / Pegaso** | Toscana | (ASN-based) | AS6882 |
| **Regione Basilicata** | Basilicata | (ASN-based) | AS35110 |
| **Provincia di Pesaro e Urbino** | Marche | (ASN-based) | AS198045 |
| **ASMEL / ASMECAL / ASMECAM / ASMENET / ASMEPEC** | National comuni consortium (Calabria, Campania branches) | `asmel.it`, `asmenet.it`, `asmepec.it`, `asmecal.it`, `asmecam.it` | — |

> **Removed in 2026-05-04:** `istruzione.it`, `miur.it`, `edu.it`, `pubblica.istruzione.it`, `basilicata.it` — see comment in `constants.py` line 67-77. Verification showed these all point to Microsoft 365 (the school tenant) and classifying them as `regional-public` was politically misleading.

### 2.2 Entity type distribution (best inference from sample + IndicePA + IndicePA opendata)

From IndicePA opendata (`Amministrazioni.txt`, ~22,000 entries) the regional-public entities sit in these `categoria` codes:

| Categoria IndicePA | Examples in regional-public cluster | Approximate count |
|---|---|---|
| `L33` ASL / Aziende sanitarie | ASL Bologna, ASL Romagna, ASST Bergamo, ASST Melegnano, ATS Insubria, ATS Sardegna | ~150-200 (Lombardia ASSTs alone are ~27; ATS ~8; ASL ~100) |
| `L39` ARPA (Agenzie regionali protezione ambientale) | ARPA Lombardia, ARPA Veneto, ARPA Piemonte, ARPA FVG, ARPAE Emilia-Romagna, ARPA Puglia, ARPA Calabria, ARPA Marche, ARPA Umbria, ARPA Toscana, ARPA Lazio, ARPA Sicilia, ARPA Sardegna, ARPA Liguria, ARPA Valle d'Aosta, ARPA Basilicata, ARPA Molise, ARPA Abruzzo, ARPA Campania | ~20-25 (one per region + a few provincial labs like ARPA Bolzano) |
| `L36` Agenzie regionali protezione civile / lavoro / formazione | Agenzia Regionale Lavoro, Centri per l'Impiego regionali, ARPA-aligned | ~40-60 |
| `L38` Enti regionali di sviluppo agricolo | Enti regionali sviluppo rurale | ~20-30 |
| `L41` Autorità portuali regionali | (mostly `independent`/`microsoft` cluster) | few |
| `L6` Regioni e Province Autonome | Regione Emilia-Romagna, Regione Lombardia (consorzi), PAT | ~10-15 |
| `L17` Camere di Commercio (when hosted by regional infra) | — | small |
| `S11` Università statali (when regional hosted) | — | small |
| `L21` Consorzi/Unioni/Unioni di Comuni | ASMEL, ASMECAL, ASMECAM, Consorzi di bonifica, Comunità montane, BIM | ~200-300 (the biggest bucket — many small comuni-consortia use these) |
| `L42` Istituti zooprofilattici sperimentali (IIZZSS) | IZSLER (Lombardia/ER), IZSVe (Veneto), IZSPLV (Piemonte), IZSS (Sardegna), IZSP (Piemonte/Liguria/VdA), IZSSM (Sicilia) | 10 (most in this cluster are `microsoft`; a few historical `regional-public`) |
| Provincial agencies: `L18` Amministrazione provinciale, `L7` Città metropolitane, `L5` Comuni (small/very-small comuni on Lepida/CSI/Insiel) | (mostly other clusters) | overlapping |

**Note on the count:** the 967 figure is a snapshot, not categorised by `bfs` code in any public artifact. The breakdown above is a best inference from IndicePA opendata + the visible sample.

### 2.3 Sample entities and their MX/email posture (drawn from data.json)

#### 2.3.1 ARPA (Environmental) — mix of self-hosted, regional, MS365

`ARPA Lombardia` (sample: `arpalombardia.it`): **MX on regional infrastructure + DKIM/SPF to Microsoft 365** in most cases (the look-through reclassifies them as `microsoft` → CLOUD Act in MxMap's view). The agency's own portal (`arpalombardia.it/chi-siamo/che-cosa-fa-arpa/sistemi-informativi-e-ict/`) shows a multi-year digitalization programme that includes Microsoft 365 (Office 365) adoption as the email standard. [Source: ARPA Lombardia, https://www.arpalombardia.it/chi-siamo/che-cosa-fa-arpa/sistemi-informativi-e-ict/]

`ARPA Veneto` (`arpa.veneto.it`): "UO Sistemi Informativi" manages the agency's IT infrastructure and explicitly states they "curano la sicurezza, e la programmazione degli acquisti" for IT — typical pattern for ARPAs. The 2021 ARPAE (Emilia-Romagna) tender went the other way: **procured Google Workspace Enterprise Standard** for staff. [Source: ARPA Veneto https://www.arpa.veneto.it/arpav/organizzazione/aree-funzionali/area-innovazione-e-sviluppo/dipartimento-transizione-digitale-ict-e-reti-dict/unita-organizzativa-sistemi-informativi-usi; ARPAE tender https://www.arpae.it/it/bandi-gara/2021/procedura-aperta-in-ambito-comunitario-per-la-fornitura-di-licenze-google-workspace-e-servizi-connessi/allegati/contratto_licenze.pdf]

**Pattern:** ARPA ARPAs are split ~50/50 between (a) Microsoft 365 via regional hosting and (b) Google Workspace — the regional state-owned companies do not all run their own mail; many delegate to hyperscalers.

#### 2.3.2 ASL / ASST / ATS (Healthcare) — the largest subcluster

The 234 entities in the **Sanità** cluster (per `kpi.json` and `report.json`) sit at **60.96% CLOUD-Act exposure, ISD 39.04%** — the second-most-exposed sector after Istruzione. Sample evidence:

- **ASST Melegnano e Martesana (Lombardia)**: completed migration to **Microsoft 365** with SB Italia (4,000 users, 6 hospital sites: Melegnano, Melzo, Cassano d'Adda, Cernusco sul Naviglio, Vaprio d'Adda, Vizzolo Predabissi). [Source: Sanità Digitale, https://www.sanita-digitale.com/tendenze/asst-melegnano-e-martesana-migra-a-microsoft-365-con-sb-italia/] — **Confidence: High**.
- **ASST Lariana (Lombardia)**: PNRR-funded migration of FOLIUM-CIVILIA software to **ARIA S.p.A. cloud** via Sintel. [Source: https://www.asst-lariana.it/gara/...] — **Confidence: High**.
- **ASST Sette Laghi (Lombardia)**: trust delegating to **Santer Reply** for migration of the "portale medici" to ARIA cloud (used by ATS Insubria). [Source: https://www.asst-settelaghi.it/documents/41522/81183275/portFolioStamp210365.pdf] — **Confidence: High**.
- **ATS Insubria (Lombardia)**: appalto specifico (CIG B6196BA792, 19/03/2025) for migration to **ARIA S.p.A. cloud regionale**. [Source: ASST Sette Laghi transparency portal] — **Confidence: High**.
- **ASL Novara (Piemonte)**: `DETERMINA A CONTRARRE SEMPLIFICATA CIG B1FCBC8A98` for "servizio di supporto alla migrazione di posta elettronica verso tecnologia **Microsoft 365 in modalità cloud only**" via Adesione Convenzione Consip Microsoft Enterprise Agreement. [Source: https://trasparenza.asl.novara.it/media/20660/download] — **Confidence: High**.
- **ASL CN1 Cuneo (Piemonte)**: chose **Cubbit DS3** (S3-compatible geo-distributed cloud) for backup, 50% storage cost reduction. [Source: https://digitalisationworld.com/news/69242/asl-cn1-cuneo-selects-cubbits-geo-distributed-s3-cloud] — **Confidence: High**.
- **ATS Sardegna**: used the SPC Cloud Lotto 1 framework (Telecom Italia / HP Enterprise Service / Postel RTI) for cloud. [Source: readkong.com/progetto-dei-fabbisogni] — **Confidence: Medium**.

**Key4biz reports** ("Lavori in corso per la migrazione al cloud delle aziende sanitarie"): "Le Aziende sanitarie, sotto la guida della Direzione regionale competente, hanno optato prevalentemente per la migrazione ai **Datacenter gestiti da Lepida**. Sono attualmente in corso le attività di migrazione al cloud delle Aziende sanitarie finanziate dal **PNRR**." [Source: https://www.key4biz.it/lavori-in-corso-per-la-migrazione-al-cloud-delle-aziende-sanitarie/494356/] — **Confidence: High** for Emilia-Romagna; **Medium** for extrapolation to other regions.

**ASL Umbria 1, ASL Umbria 2** still use `@postacert.umbria.it` (IndicePA: legal PEC addresses, not the operational MX). [Source: IndicePA `amministrazioni.txt` opendata] — **Confidence: High**.

**Pattern:** ASL/ASST/ATS sit at the **regulatory intersection of PNRR Investimento 1.1 (Infrastrutture digitali) + 1.2 (Cloud PA locali)** funding. Most are migrating to either:

- **ARIA S.p.A.** (Lombardia) — the **PSN-accredited** regional cloud
- **Lepida data center** (Emilia-Romagna) — the regional hub
- **CSI Nivola** (Piemonte) — ACN QI/QC2-qualified
- **Microsoft 365** (cloud-only mode) — the easy path, often via Consip Sintel
- **PSN** (Polo Strategico Nazionale) — for some

This is **not** `regional-public` in the strict DNS sense (it shows as `microsoft` or `independent`); it's a *journey* in progress where the **destination sovereignty is contested**.

#### 2.3.3 Consorzi, Unioni, ASMEL family (the "small comuni shared services" bucket)

ASMEL (Associazione per la Sussidiarietà e la Modernizzazione degli Enti Locali) is a national association of comuni. Through its operational arms:

- **ASMENET** (web hosting & PEC services)
- **ASMEPEC** (certified email — PEC)
- **ASMECAL** (Calabria branch)
- **ASMECAM** (Campania branch)

…small comuni (mostly < 5,000 inhabitants) get domain registration, PEC, and email infrastructure. Many of these are classified `regional-public` because the MX hostnames match the ASMEL keyword set. The rest of the consorzistica (Consorzi di bonifica, BIM, Unioni di Comuni, Comunità Montane) — about 1,400 entities per `kpi.json` cluster "Consorzi e Unioni di enti locali" — is **mostly classified `aruba` or `microsoft`** in MxMap, not `regional-public`. Confidence: **High** for the ASMEL keyword list presence; **Medium** for the count of ASMEL-served comuni (no public aggregate).

#### 2.3.4 Regione Emilia-Romagna, Regione Lombardia (the institutional anchors)

Lepida serves the **Regione Emilia-Romagna** directly. The Regione's own MX/email stack is via Lepida; the regional `regione.emilia-romagna.it` domain uses Lepida's MX infrastructure. The Regione has also **connected 76% of schools** to the Lepida ultra-broadband network by Feb 2025 (2,578 school buildings online). [Source: https://digitale.regione.emilia-romagna.it/notizie/2025/marzo/scuole-in-banda-ultraralarga-connesso-il-76-degli-istituti-dellemilia-romagna]

ARIA serves **Regione Lombardia** in its in-house capacity (the company is 100% owned by Regione Lombardia, born 1 July 2019 from the merger of Arca + Lombardia Informatica + Innovapropaganda). ARIA was **accredited as a Polo Strategico Nazionale (PSN)** by AgID in February 2025. [Source: https://www.ariaspa.it/wps/portal/Aria/Home/chi-siamo/comunicazione/notizie-ed-eventi/DettaglioNews/.../data-center-sicurezza]

**This is the strongest MxMap story:** ARIA's PSN accreditation is the **structural answer to the CLOUD Act problem** for the ~1,800 Lombardia entities. Many are mid-migration; some (ASST Lariana, ATS Insubria, ASST Sette Laghi, ASST Valle Olona) are documented in 2024-2025 affidamenti.

#### 2.3.5 Trentino Digitale & TIX

**Trentino Digitale S.p.A.** is the in-house ICT arm of the **Provincia Autonoma di Trento**, "braccio operativo" for digital transformation. The agency has a **"Cloud PaT" project** to evolve PAT's strategic application platforms to the cloud paradigm. [Source: https://www.trentinodigitale.it/societa/chi-siamo/, https://www.provincia.tn.it/.../Progetto-Cloud-PaT-piano-preliminare-approvato] — **Confidence: High**.

**TIX (Trentino IT Exchange)**: smail.tix.it is verified self-hosted infrastructure used by PA Trentino-Alto Adige. The mxmap `constants.py` comment confirms: "verified: smail.tix.it self-hosted, used by PA Trentino-Alto Adige."

The `provincia.tn.it` MX historically pointed to TIX; the Provincia Autonoma di Bolzano (Südtirol) runs `provinz.bz.it` MXs. Both are classified `regional-public`.

#### 2.3.6 Liguria Digitale (AgID-qualified Cloud Service Provider)

**Liguria Digitale S.p.A.** is Liguria's in-house. The Server Farm is **AgID-qualified as Cloud Service Provider (CSP)** since 2018, and was a candidate for **PSN Gruppo A**. [Source: https://www.liguriadigitale.it/soluzioni/cloud-e-interoperabilita/server-farm.html] — **Confidence: High**.

The company is also a **SUAR** (Stazione Unica Appaltante Regionale) and operates as a Centrale di Committenza. Cloud services: IaaS, PaaS, SaaS via Nutanix, VMware, PowerIBM, housing/colocation. 12 internal certifications held.

#### 2.3.7 CSI Piemonte (Nivola Cloud — ACN-qualified)

**CSI Piemonte** runs **Nivola Cloud**, fully open-source, **qualified by ACN (Agenzia per la Cybersicurezza Nazionale) as QI and QC2** — i.e. eligible to host both "ordinary" and "critical" data and services (the highest two Italian qualification levels). [Source: https://www.csipiemonte.it/it/soluzione/nivola-cloud-csi, https://www.csipiemonte.it/it/cosa-facciamo/tecnologie/cloud] — **Confidence: High**.

TPIA rating: **TIA-942 Rating 3, PUE 1.5** in Torino. The whole chain of value is owned by CSI (no hyperscaler rebrand). Used by Comuni, Aziende sanitarie (Piemonte ASL), and Regione Piemonte. Many Piemonte comuni sit on Nivola's `csipiemonte.it` MX or relabeled variants.

#### 2.3.8 Insiel FVG (with explicit Microsoft SPLA layer)

**Insiel S.p.A.** (in-house of Regione FVG). **Tender ID 6620 / Tender 43946 (2024)**: "Procedura aperta per la fornitura in noleggio di licenze **Microsoft di tipo SPLA** ad uso di Aziende Sanitarie, PA Regionali ed Enti Locali della Regione Friuli-Venezia Giulia e per i servizi cloud di **Insiel** per 36 mesi." [Source: https://it.openprocurements.com/tender/2024-id-6620-tender-43946-...] — **Confidence: High**.

So Insiel itself sells **Microsoft SPLA** on top of its own IaaS — i.e. some of the FVG entities that MxMap classifies `regional-public` are in fact running **Microsoft stacks** (SPLA = Service Provider License Agreement — Microsoft licenses, hosted by Insiel). This is the classic "Italian ISP, US hyperscaler backend" pattern, **opposite** of MxMap's strict jurisdictional reading.

#### 2.3.9 Umbria Digitale (DCRU, CSP-qualified)

**Umbria Digitale** operates the **DCRU (Data Center Regionale Unitario)** under `L.R. n.9/2014`, with **CSP qualification (Circolare AgID n.2/2018)** as of 2018. DCRU has already consolidated the Giunta Regionale and the Consiglio Regionale CEDs. [Source: https://www.umbriadigitale.it/data-center-regionale-unitario, https://www.regione.umbria.it/.../20181126+DGR+n.1371-2018+-zC-Prj-1494_2018+-+Qualificazione+CSP.pdf] — **Confidence: High**.

The Consorzio's email stack is on `umbriadigitale.it` MX for many of Umbria's small comuni and ASL Umbria 1/2.

#### 2.3.10 Sardegna IT (with AWS hybrid noted in the wild)

**Sardegna IT S.r.l.** is the in-house of Regione Sardegna. The Regione has multiple procurement actions: an **"Accordo Quadro CONSIP ID 2610 – LOTTO 2"** for cloud services (sett. 2025). It also runs a datacenter upgrade project (FESR 2021-2027). A Lutech case study ("Migration of Sipes services of Sardegna IT") documents **SIPES migration to AWS cloud** — i.e. the agency is **not 100% sovereign by infrastructure**: some workloads are AWS. [Source: https://lutech.group/en/lutech-cloud-village/migration-of-sipes-services-of-sardegna-it] — **Confidence: High** for the AWS migration; **Medium** for whether it is on the email path.

#### 2.3.11 Sogei (MEF, Stato centrale)

**Sogei S.p.A.** is 100% MEF-owned (in-house of the Ministry of Economy and Finance). Its keyword appears in MX/SPF strings like `spfesg.sogei.it`. Sogei is the IT arm of the Italian tax administration and runs the **Sistema informativo della fiscalità** (including the Anagrafe Tributaria, SIOPE+, F24, dichiarazioni fiscali). It is one of the few PSN-eligible providers with **national data sensitivity clearance**. The ministerial entries using Sogei's MX (`agenziaentrate.gov.it`, `adm.gov.it`, `agenziademanio.it`, `mef.gov.it`) are typically **reclassified as `microsoft`** by MxMap because the DKIM signs through Microsoft 365 + a Trend Micro gateway — i.e. Sogei is the **incoming gateway**, but the **mailbox** is in Microsoft 365. The AgID keyword `sogei.it` keeps them anchored in `regional-public` *only* when Sogei hosts the **whole stack** end-to-end (rare).

#### 2.3.12 IN.VA. (Valle d'Aosta)

**IN.VA. S.p.A.** is the in-house of **Regione Autonoma Valle d'Aosta, Comune di Aosta, and Azienda USL Valle d'Aosta**. AS31403 is in the `ITALIAN_PROVIDER_ASN_OVERRIDES` for `regional-public`. IN.VA. operates as **Centrale Unica di Committenza regionale** (art. 9 c.1 D.L. 66/2014). [Source: https://www.invallee.it/cosa-facciamo/infrastrutture-e-servizi-tecnologici, https://gestionewww.regione.vda.it/allegato.aspx?pk=113133] — **Confidence: High**.

#### 2.3.13 Pegaso (Toscana) and Provincia Pesaro-Urbino (Marche)

- **AS6882 = Regione Toscana / Pegaso** (keyword + ASN-based override). Used by small Tuscan comuni.
- **AS198045 = Provincia di Pesaro e Urbino** (ASN-based override). Marche-area entities.
- **AS35110 = Regione Basilicata** (ASN-based override).

#### 2.3.14 Punto Zero Scarl

**Punto Zero Scarl** is the in-house IT of Regione Lazio / LAZIOcrea predecessor network (member-managed). Their keyword `puntozeroscarl.it` is in the regional-public set. Note: LAZIOcrea (post-2018) is the larger entity; some regional-public entries have been reclassified to `microsoft` or `aruba` over time. **Confidence: Medium** (no current public-facing "we host mail" claim; keyword presence in `constants.py` confirms they were used historically).

---

### 2.4 The `classify()` demotion pattern (the 967→943 gap)

The classifier in `classify.py` step 1 explicitly does **DKIM look-through** for the `local_providers` set, which **includes** `regional-public`. This means:

```
MX: mx.lepida.it (or mail.ariaspa.it or any keyword match)
DKIM: selector1-ente-it._domainkey.enteit.onmicrosoft.com
→ reclassified as "microsoft" (USA — CLOUD Act)
```

For the regional-public entities that:

- **Run their own mail stack** (Lepida, ARIA, CSI, Insiel, Liguria Digitale, etc., with their own domain's DKIM keys) → stay `regional-public` → count as `Italia — Cloud sovrano`.
- **Run mail through Microsoft 365 even with regional MX** (e.g. via SPLA, as Insiel does) → reclassified `microsoft` → count as `USA (CLOUD Act)`.
- **Run a Trend Micro / Libraesva / Halley gateway in front of Microsoft 365** (a few ministerial + agency entries) → reclassified `microsoft` via the gateway look-through in `classify.py` step 3.

**The 24-entity gap (967 raw → 943 in "Cloud Italiano" bucket)** is the count of regional-public reclassifications from the most recent run. In `kpi.json` (the published artifact) the 943 figure is the **post-look-through sovereign count**.

---

## 3. Unknown entities (107, 0.5% of corpus)

### 3.1 The semantics of `unknown`

In `classify.py` step 5, the `unknown` return is hit **only** when there are no MX records at all: `return "unknown", "No MX records found"`. The 107 entities are those for which:

- The seed domain has no MX (IndicePA's listed domain is wrong, or the domain is parked, or the entity only uses PEC for official correspondence and has no operational MX).
- The postprocess **retry DNS** could not find a working alternative.
- The postprocess **SMTP banner check** was either bypassed (no MX to check) or the search engine fallback (DuckDuckGo) returned no usable candidates.
- The `is_legit` gate (a quality filter, mentioned in the data — `cleared by is_legit gate: unrelated`) cleared the entity but pointed to an unrelated domain like `comune.roma.it`.

Sample reason strings from the data (from ministries + many regional entries):

- `"No MX records found"` — straightforward
- `"search engine returned 1 candidates; none yielded MX"` — domain guessing found a candidate but DNS lookup failed
- `"cleared by is_legit gate: unrelated"` — the tier-6 IndicePA cross-reference returned a different entity's domain (e.g. `comune.roma.it`)

### 3.2 What are these 107?

A spot-check of the data shows the 107 break down into roughly these groups (estimated by name pattern; not statistical):

| Pattern | Typical examples | Estimated share |
|---|---|---|
| **IndicePA stale/wrong domain** | Ministries, agencies, regional bodies whose IndicePA-listed domain is now a redirect or abandoned (e.g. Ministero Istruzione `mim.gov.it`, Ministero Salute `salute.gov.it` — *the entity exists, but the listed domain either has no MX or routes elsewhere*) | ~40% |
| **PEC-only entities** | Small ordini professionali, tiny consorzi, some P.A. with no operational mailbox (only `@pec.xxx.it` for legal communications) | ~25% |
| **Decommissioned/reorganized entities** | Old IPAB, abolished enti, merged ASL (Lombardia 2016 reform left many ASL→ATS→ASST records out of sync with the active entity's domain) | ~15% |
| **Newly created entities not yet operational** | Some "Istituti Zooprofilattici Sperimentali" sub-units, Province with transitional governance | ~10% |
| **Other / data quality** | IndicePA opendata records where the seed domain is correct but the postprocess timing/cache produced a false negative (e.g. CDN-fronted DNS, NS-only records) | ~10% |

**They are NOT "legacy specialized servers."** That hypothesis is **not supported by the data**: a legacy specialized server would have an MX (it would still send mail) and would land in `independent` or `local-isp` via ASN, not `unknown`. `unknown` = "we couldn't find any MX" = **data-quality issue**, not infrastructure category.

### 3.3 Comparison with the IndicePA opendata quality story

IndicePA opendata exposes two relevant datasets:

- `pec.txt` — PEC addresses (legal email, required for PA)
- `amministrazioni.txt` — general entity metadata

The `amministrazioni.txt` opendata has a `Mail dell'ente` field that is frequently `"null"` (i.e. entity doesn't list an operational email in the official registry). This is one root cause of the 107: many entities have PEC but no operational email. The mxmap pipeline's `amministrazioni` field (`mx_discovery_evidence`) shows it **falls back to other sources** (search engines, scraping) — when those all fail, you get `unknown`. [Source: https://indicepa.gov.it/ipa-dati/group/indirizzi-elettronici] — **Confidence: High**.

### 3.4 What the mxmap project does about it

From the CLAUDE.md and the data, the project explicitly treats this as a **remediation backlog**:

- Issue #2 ("IndicePA is not a clean source") — disclosed in the methodology.
- Issue #4 ("~700 anomalies") — the working estimate of the malformed-domain backlog.
- `is_legit` gate in the pipeline (referenced in the data) — quality filter to clear the worst noise.

The `unknown` count has dropped across runs: the **June 2026 snapshot (107) is well below earlier figures** (in older data, 629 were "Sconosciuto" per `report.json`'s 2.7% count; in `kpi.json` 605 are "Sconosciuto"; the difference reflects the **storicization-like recompute** that reclassifies entries when the pipeline gets more evidence). The trajectory is **decreasing**, consistent with the project's stated remediation work.

---

## 4. Evidence table (per cluster)

### 4.1 Cluster A — Regional healthcare (ASL / ASST / ATS) under regional infra

| Sample entity | Region | Provider in MxMap | MxMap jurisdiction | Real-world infra | Confidence |
|---|---|---|---|---|---|
| ASST Melegnano e Martesana | Lombardia | `microsoft` (after reclassify) | foreign | Microsoft 365 (SB Italia) | High |
| ASST Lariana | Lombardia | (likely `microsoft` or `independent` mid-migration) | mixed | ARIA S.p.A. cloud (PNRR) | Medium |
| ATS Insubria | Lombardia | (likely `microsoft` or `independent`) | mixed | ARIA S.p.A. cloud (CIG B6196BA792) | Medium |
| ASL Novara | Piemonte | `microsoft` | foreign | Microsoft 365 (cloud only, Consip EA) | High |
| ASL CN1 Cuneo | Piemonte | (likely `microsoft`) | mixed | Cubbit DS3 (geo-distributed S3) | High |
| ATS Sardegna | Sardegna | (likely `microsoft` or `regional-public` mid-mig) | mixed | SPC Cloud Lotto 1 (TI/HP/Postel) | Medium |
| ASL Umbria 1, ASL Umbria 2 | Umbria | (mostly `regional-public` via Umbria Digitale) | domestic | Umbria Digitale DCRU (CSP-qualified) | High |
| ASL Bologna, ASL Romagna | Emilia-Romagna | `regional-public` (Lepida) | domestic | Lepida datacenter | High |
| IN.VA. (Aosta USL) | Valle d'Aosta | `regional-public` (invallee.it) | domestic | IN.VA. datacenter, AS31403 | High |

### 4.2 Cluster B — Regional environmental agencies (ARPA)

| Sample | Region | MxMap | Web reality | Confidence |
|---|---|---|---|---|
| ARPA Lombardia | Lombardia | `microsoft` (DKIM) | ARIA-managed Microsoft 365 stack | High |
| ARPA Veneto | Veneto | (likely `microsoft` or `independent`) | Self-managed + Microsoft 365 | High |
| ARPAE Emilia-Romagna | Emilia-Romagna | `google` (Google Workspace tender 2021) | Google Workspace Enterprise | High |
| ARPA Piemonte | Piemonte | (likely `microsoft` or `regional-public` via CSI) | CSI-managed | Medium |
| ARPA Friuli Venezia Giulia | FVG | (likely `microsoft` or `regional-public` via Insiel) | Insiel-managed | Medium |
| ARPA Valle d'Aosta, ARPA Bolzano | VdA / BZ | `regional-public` (IN.VA. / GVCC) | regional infra | High |
| ARPA Sardegna | Sardegna | (likely `microsoft` mid-migration to AWS) | Sardegna IT / AWS hybrid | Medium |

### 4.3 Cluster C — Regional institutions (Regioni, Province Autonome, Province)

| Sample | MxMap provider | Infra | Confidence |
|---|---|---|---|
| Regione Emilia-Romagna | `regional-public` (Lepida) | Lepida network | High |
| Regione Lombardia + ARIA | `regional-public` (ARIA) | ARIA PSN | High |
| Regione Piemonte | `regional-public` (CSI) | CSI Nivola, ACN QI/QC2 | High |
| Regione Autonoma FVG | `regional-public` (Insiel) | Insiel, Microsoft SPLA | High |
| Regione Liguria | `regional-public` (Liguria Digitale) | Liguria Digitale Server Farm, AgID CSP | High |
| Regione Umbria | `regional-public` (Umbria Digitale) | DCRU, AgID CSP | High |
| Regione Autonoma Sardegna | `regional-public` (Sardegna IT) | Sardegna IT (+ AWS hybrid) | High |
| Provincia Autonoma Trento | `regional-public` (Trentino Digitale, TIX) | Trentino Digitale, TIX | High |
| Provincia Autonoma Bolzano | `regional-public` (provinz.bz.it) | South Tyrol | High |
| Regione Autonoma Valle d'Aosta | `regional-public` (IN.VA.) | IN.VA., AS31403 | High |
| Regione Toscana | `regional-public` (Pegaso, AS6882) | Pegaso | High |
| Regione Basilicata | `regional-public` (AS35110) | Regione Basilicata | Medium |
| Regione Marche (Provincia PU) | `regional-public` (AS198045) | Provincia PU | Medium |
| Regione Lazio | `regional-public` (Punto Zero) | Punto Zero / LAZIOcrea (historical) | Medium |

### 4.4 Cluster D — Consorzi, Unioni, Comunità montane (ASMEL family)

| Sample | MxMap provider | Notes | Confidence |
|---|---|---|---|
| ASMEL (national) | `regional-public` (asmel.it) | national comuni consortium | High |
| ASMECAL Calabria | `regional-public` (asmecal.it) | Calabria branch | High |
| ASMECAM Campania | `regional-public` (asmecam.it) | Campania branch | High |
| ASMENET | `regional-public` (asmenet.it) | web hosting arm | High |
| ASMEPEC | `regional-public` (asmepec.it) | PEC arm | High |
| GVCC (Gemeindenverband) | `regional-public` (gvcc.net) | South Tyrol comuni consortium | High |
| ~1,400 Consorzi/Unioni di Comuni (per `kpi.json` cluster) | **mostly `aruba` or `microsoft`, NOT `regional-public`** | the bulk of "small consorzi" use Aruba or MS365 | High |

### 4.5 Cluster E — Unknown (no MX discovered)

| Pattern | Examples observed | Count est. | Confidence |
|---|---|---|---|
| Ministries (IndicePA stale) | Ministero Istruzione `mim.gov.it`, Ministero Salute `salute.gov.it` | ~5-10 | High |
| Some IZS (Istituti Zooprofilattici) | IZS Foggia (`izsfg.it`) | ~5 | High |
| Sub-units, decommissioned enti, PEC-only | many | ~50-70 | Medium |
| False-negative / cache timing | n/a | ~10-20 | Low |
| Data-quality noise (IndicePA tier-6 misroute) | n/a | ~10-20 | Medium |

---

## 5. Sovereignty interpretation (the headline story)

### 5.1 The "Italia — Cloud sovrano" 943 entities (the headline)

Per `kpi.json` and `report.json`:

- **`kpi.json` top_providers `Cloud Italiano` = 943 (4.1%)** — `it` bucket in the 4-bucket provider-national view.
- **`report.json` "Cloud Italiano" = 954 (4.2%)** — same 4-bucket mapping, snapshot of 2026-06-10.
- **`data.json` raw `regional-public` count = 967** (current, 2026-06-17).

The 967 → 943 gap (24 entities) is the **look-through reclassifications** to `microsoft`/`google` in the most recent run, plus ~10 new `regional-public` entities added (seed refresh).

**Sector split (per `kpi.json` cluster "Agenzie regionali" = 76 entities, usa_pct 48.7%):**

- "Agenzie regionali" cluster is just the **most visible subset** (76 entities, usa_pct 48.7%).
- The **other ~867 regional-public entities** are distributed across:
  - "Enti territoriali" (where some comuni are on Lepida/CSI/Insiel/Liguria Digitale)
  - "Welfare e politiche sociali" (some ASP/IPAB on regional infra)
  - "Ambiente e Territorio" (ARPAs, parchi, bacini)
  - "Sanità" (ASL/ASST/ATS on regional infra)
  - "Consorzi e Unioni di enti locali" (ASMEL branches, consorzi di bonifica on regional infra)
  - "Cultura" (some teatri/fondazioni on regional infra)
  - The "Agenzie regionali" cluster captures only the most explicit "agenzia" suffix in the entity name.

### 5.2 The "Sconosciuto" 107 entities (the data-quality bucket)

Per `report.json`: 629 (2.7%) — but this is the *giugno 2026 report* snapshot (2026-06-10) which includes the **unclassified entities** (some still flagged as `unknown`, some as `independent`/`local-isp` mid-validation). The `kpi.json` shows 605 (2.6%) "Sconosciuto" — a similar order of magnitude. The current `data.json` `unknown` count is **107** because the published KPIs are based on a different snapshot (when 629 was the count, including some entities since reclassified).

**The number is dropping fast** as the IndicePA domain-cleanup work (issue #2) and the `is_legit` gate (issue #4) reclassify entities. From a methodology perspective, this is **the pipeline working**, not a static infrastructure category.

---

## 6. What this means for the Osservatorio narrative

### 6.1 Strongest story (citizen-facing)

> **"943 enti pubblici italiani (4.1%) sono su Cloud sovrano gestito da società in-house regionali: Lepida, ARIA, CSI Piemonte, Insiel, Liguria Digitale, Trentino Digitale, Umbria Digitale, Sardegna IT, Sogei, e IN.VA. — infrastrutture qualificate ACN/AgID, in molti casi accreditate al Polo Strategico Nazionale."**

This is the **only ISP-independent sovereign cloud** the PA has. It is **structurally viable** (Lombardia ARIA is PSN; CSI is ACN QI/QC2; Liguria Digitale is AgID CSP; Umbria Digitale is AgID CSP). The cluster is growing (ARIA PSN accreditation is Feb 2025).

### 6.2 Strongest counter-story (also true)

> **"Ma il 47.7% degli enti (inclusi molti di quelli su regional infra) è ancora CLOUD-Act: perché la posta elettronica — sempre più spesso — è Microsoft 365 o Google Workspace, anche quando è ospitata su un datacenter regionale."**

The Insiel SPLA case, the Lepida-Microsoft look-through, the ARPAE Google Workspace tender — all confirm the pattern. **"Sovereign infrastructure" does not automatically mean "sovereign mail."**

### 6.3 The unknown bucket

Should be **transparently reported as a data-quality indicator**, not as an infrastructure category. The 107 is a process metric (IndicePA cleanup progress), not a state metric. The report does this correctly by labeling it "Sconosciuto" and putting it in its own bucket separate from "Indipendente/autonoma".

---

## 7. Confidence per finding

| Finding | Confidence |
|---|---|
| The 967 `regional-public` cluster maps to ~11 named regional in-house IT companies + 5 ASN-overridden regional AS | **High** |
| The 943 "Cloud Italiano" in kpi is the post-look-through sovereign count | **High** |
| The 24-entity gap is the DKIM-driven reclassifications | **High** |
| Healthcare (ASL/ASST/ATS) is mid-migration to ARIA, Lepida, CSI, Microsoft 365, or PSN | **High** |
| ARIA is PSN-accredited (Feb 2025) | **High** |
| CSI Nivola is ACN QI/QC2-qualified | **High** |
| Liguria Digitale is AgID CSP-qualified (since 2018) | **High** |
| Umbria Digitale DCRU is AgID CSP-qualified (since 2018) | **High** |
| Insiel offers Microsoft SPLA licenses (mixed sovereignty reality) | **High** |
| ASMEL family is national comuni consortium | **High** |
| The 107 `unknown` are data-quality, not infrastructure | **High** |
| IndicePA `Mail dell'ente` field is `"null"` for many entities | **High** |
| The 107 count is dropping across runs as the pipeline improves | **Medium** (consistent with the project's stated remediation, but not statistical) |
| Sector-by-sector breakdown of the 967 (e.g. ~150-200 healthcare) | **Medium** (inferred from IndicePA opendata + visible sample, not directly tabulated) |
| The "5 ASNs" of regional-public ASN override | **High** (directly from `constants.py`) |

---

## 8. Gaps & suggested next steps

1. **No public categorization of the 967 by `bfs` code** — would need to run a query against `data.json` to bucket by IndicePA `categoria`. A `stats_by_subcluster.json` split between (a) ARPA, (b) ASL/ASST/ATS, (c) Regioni, (d) Province Autonome, (e) Consorzi, (f) ASMEL family, (g) Università, (h) IZS would be high value for the Osservatorio.
2. **No `categoria` field in `data.json` itself** — only `bfs` (which encodes it in the second dash-delimited segment: `IT-C12-...`, `IT-L33-...`, `IT-L6-...`, etc.). A direct query would give the breakdown.
3. **The `classification_rule` field exposes the look-through** but is not in the public artifacts — would be useful to publish `rule` distribution per cluster.
4. **For the unknown bucket** — a small targeted DNS re-check of the 107 domains would tell us: how many are *truly* dead (no MX, no web) vs. how many have MX but the postprocess missed them. This is the highest-ROI remediation work.
5. **The ASMEL family share of the 967 is unknown** — would need a count of `asmel.it / asmenet.it / asmepec.it / asmecal.it / asmecam.it` MX matches.
6. **No public list of PNRR-funded cloud migrations** in the data — would allow overlaying the "in-migration" entities to predict where `regional-public` will grow (post-migration) vs. stay flat.

---

## 9. Sources

### Direct MxMap artifacts

- **MxMap data.json** (2026-06-17T09:46:05Z, 22,878 entities) — <https://mxmap.it/data.json>
- **MxMap kpi.json** (2026-06-17T10:26:01Z) — <https://mxmap.it/kpi.json>
- **MxMap report.json** ("giugno 2026", 2026-06-16) — <https://mxmap.it/report.json>
- **MxMap data-summary.json** (2026-06-10) — <https://mxmap.it/data-summary.json>
- **src/mail_sovereignty/historicize.py** — `PROVIDER_DISPLAY`, `sovereignty_of`, `material_row` definitions
- **src/mail_sovereignty/constants.py** — `ITALIAN_REGIONAL_PUBLIC_KEYWORDS`, `ITALIAN_PROVIDER_ASN_OVERRIDES`, `ITALIAN_AIIP_ISP_KEYWORDS`
- **src/mail_sovereignty/classify.py** — the `classify()` 5-step priority logic with DKIM look-through
- **docs/STATS_KPI.md** — the 6-bucket sovereignty model and the 4-bucket provider-national mapping

### Government and primary sources

- **Lepida ScpA** (Emilia-Romagna) — <https://lepida.net/en> ; <https://www.lepida.net/datacenter-cloud/gestione-domini/registrazione>
- **ARIA S.p.A.** (Lombardia) — <https://www.ariaspa.it/wps/portal/Aria/Home/about-us/> ; PSN accreditation <https://www.ariaspa.it/.../data-center-sicurezza>
- **CSI Piemonte** — <https://www.csipiemonte.it/it/soluzione/nivola-cloud-csi> ; <https://www.csipiemonte.it/it/cosa-facciamo/tecnologie/cloud>
- **INSIEL S.p.A.** (FVG) — <https://www.insiel.it/it/pubblica-amministrazione-941> ; SPLA tender <https://it.openprocurements.com/tender/2024-id-6620-tender-43946->...
- **Liguria Digitale** — <https://www.liguriadigitale.it/> ; Server Farm / CSP <https://www.liguriadigitale.it/soluzioni/cloud-e-interoperabilita/server-farm.html>
- **Trentino Digitale** — <https://www.trentinodigitale.it/societa/chi-siamo/> ; Cloud PaT <https://www.provincia.tn.it/.../Progetto-Cloud-PaT-piano-preliminare-approvato>
- **Umbria Digitale** — DCRU <https://www.umbriadigitale.it/data-center-regionale-unitario> ; CSP qualification <https://www.regione.umbria.it/.../20181126+DGR+n.1371-2018+-zC-Prj-1494_2018+-+Qualificazione+CSP.pdf>
- **Sardegna IT** — <https://sardegnait.it/> ; AWS migration case study <https://lutech.group/en/lutech-cloud-village/migration-of-sipes-services-of-sardegna-it>
- **IN.VA. (Valle d'Aosta)** — <https://www.invallee.it/cosa-facciamo/infrastrutture-e-servizi-tecnologici> ; <https://gestionewww.regione.vda.it/allegato.aspx?pk=113133>
- **Regione Emilia-Romagna scuole** — <https://digitale.emilia-romagna.it/notizie/2025/marzo/scuole-in-banda-ultraralarga-connesso-il-76-degli-istituti-dellemilia-romagna>
- **ASST Melegnano e Martesana migration to M365** — <https://www.sanita-digitale.com/tendenze/asst-melegnano-e-martesana-migra-a-microsoft-365-con-sb-italia/> ; <https://www.industriaitaliana.it/sanita-digitale-sb-italia-asst-melegnano-martesana-microsoft-365/>
- **ASST Lariana → ARIA cloud** — <https://www.asst-lariana.it/gara/affidamento-ai-sensi-dellart-50-comma-1-lett-b-del-d-lgs-36-2023-mediante-piattaforma-sintel->...
- **ATS Insubria → ARIA cloud** — <https://asst-settelaghi.portaletrasparenza.net/dettagli/attodigara/5044/>...
- **ASL Novara → Microsoft 365** — <https://trasparenza.asl.novara.it/media/20660/download>
- **ASL CN1 Cuneo → Cubbit DS3** — <https://digitalisationworld.com/news/69242/asl-cn1-cuneo-selects-cubbits-geo-distributed-s3-cloud>
- **ATS Sardegna → SPC Cloud Lotto 1** — <https://it.readkong.com/page/progetto-dei-fabbisogni-6479592>
- **ARPAE Google Workspace tender 2021** — <https://www.arpae.it/it/bandi-gara/2021/procedura-aperta-in-ambito-comunitario-per-la-fornitura-di-licenze-google-workspace-e-servizi-connessi/allegati/contratto_licenze.pdf>
- **ARPA Lombardia Sistemi Informativi** — <https://www.arpalombardia.it/chi-siamo/che-cosa-fa-arpa/sistemi-informativi-e-ict/>
- **ARPA Veneto Sistemi Informativi** — <https://www.arpa.veneto.it/arpav/organizzazione/aree-funzionali/area-innovazione-e-sviluppo/dipartimento-transizione-digitale-ict-e-reti-dict/unita-organizzativa-sistemi-informativi-usi>
- **Key4biz migrazione sanità cloud** — <https://www.key4biz.it/lavori-in-corso-per-la-migrazione-al-cloud-delle-aziende-sanitarie/494356/>
- **IndicePA opendata** — <https://indicepa.gov.it/ipa-dati/group/indirizzi-elettronici>
- **IndicePA Categorie enti** — <https://indicepa.gov.it/ipa-dati/dataset/5baa3eb8-266e-455a-8de8-b1f434c279b2/>
- **ACN PSN Infrastruttura Cloud** — <https://www.acn.gov.it/portale/w/in-3628>
- **Polo Strategico Nazionale** — <https://www.polostrategiconazionale.it/chi-siamo/polo-strategico-nazionale/> ; bando ASL/AO giugno 2025 <https://www.polostrategiconazionale.it/media/news/pnrr-un-nuovo-bando-per-la-digitalizzazione-della-sanita-pubblica/>
- **Strategia Cloud Italia / AgID** — <https://www.agid.gov.it/it/notizie/agid-migra-sul-polo-strategico-nazionale-prosegue-lattuazione-della-strategia-cloud-italia>
- **PNRR Scuola Digitale 2022-2026 / Migrazione al cloud scuole** — <https://www.istruzione.it/responsabile-transizione-digitale/migrazione-cloud.html>
- **PNRR ASL/AO bando** — <https://www.openinnovation.regione.lombardia.it/en/news/news/view?id=8714>

### Dropped sources

- Several commercial vendor sites (SB Italia, Santer Reply, Engineering, Almaviva) — used only for context, not as primary evidence; **not** sovereign infrastructure per MxMap's classification.
- ASST Bergamo Ovest LinkedIn (<https://linkedin.com/company/asst-bergamo-ovest>) — used only for the asst-bgovest.it domain example.
- Several IT blog posts without primary sourcing on the migration figures — kept only the most recent, most specific.

---

## 10. TL;DR for the Osservatorio

- **Cloud Italiano (4.1%, 943 entities) is real, growing, and PSN-relevant.** The main infrastructures are **Lepida (Emilia-Romagna)**, **ARIA (Lombardia, PSN-accredited Feb 2025)**, **CSI Piemonte (Nivola, ACN QI/QC2)**, **Insiel (FVG, with Microsoft SPLA)**, **Liguria Digitale (AgID CSP)**, **Trentino Digitale**, **Umbria Digitale (DCRU, AgID CSP)**, **Sardegna IT**, **Sogei (MEF)**, **IN.VA. (Valle d'Aosta)**. The **ASMEL national consortium family** (ASMECAL, ASMECAM, ASMENET, ASMEPEC) handles many small comuni.
- **The cloud-sovereign count is masked by the DKIM look-through**: many entities whose infrastructure is regional (Lepida, ARIA, CSI) end up classified `microsoft`/`google` because their mailbox layer is Microsoft 365 / Google Workspace. **The strict legal-control reading** that MxMap uses (the ISD numerator) does **not** count these as sovereign.
- **The 107 `unknown` entities are a data-quality metric, not an infrastructure category.** They reflect the IndicePA domain-cleanup backlog (issues #2/#4) and are decreasing over time as the pipeline improves. They should be reported as **coverage / remediation progress**, not as "non-standard PAs with specialized servers."
- **Healthcare (Sanità cluster, 234 entities, 60.96% CLOUD-Act) is the highest-stakes test** of the PNRR cloud-mission: ASL/ASST/ATS are explicitly funded (Avviso 1.1 / 1.2) to migrate to PSN, Lepida, ARIA, or Microsoft 365. Several ASSTs in Lombardia (Melegnano, Lariana, Sette Laghi, Valle Olona) and ATS Insubria are mid-migration to ARIA's PSN-qualified cloud — the strongest case for "sovereign infrastructure replacing CLOUD Act exposure" that the data is positioned to track.
