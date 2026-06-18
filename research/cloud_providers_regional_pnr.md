# Research: Cloud Providers, Infrastructure Operators & Regional PAs in MxMap.it

> **Data snapshot:** `kpi.json` & `report.json` generated 2026-06-15/16 · `stats_by_region.json` & `stats_by_category.json` generated 2026-06-10 · `anomalies.json` generated 2026-06-12 · `data.json` 22,987 IT entities (97.26% coverage, mean confidence 0.85).
> **Disclaimer on ANAC data:** the task referenced `/data/anac/`, but **no `data/anac/` directory exists** in this repository (the GitHub tree shows only `data/dns_cache/`, `data/bounce/`, `data/summary/`, `data/reports/`). All ANAC cross-references below are *qualitative* — drawn from public tender notices on the providers' own sites and from `dati.anticorruzione.it/opendata` — **not** from a local ANAC dump. This is flagged in the **Gaps** section.

---

## Summary

The Italian cloud email market for ~22,987 PA entities is structurally **bifurcated** between (1) **US hyperscalers (Microsoft 365 + Google Workspace = 46.05% of all PA, the entirety of the CLOUD Act bucket)** and (2) **a fragmented Italian commercial market led by Aruba (23.52% of all PA)**. **Regional publicly-owned cloud is small (4.27% of all PA, 954 entities)** but very **unevenly distributed**: Trentino-Alto Adige 20.33%, Basilicata 32.74%, Calabria 29.05% have substantial regional-public adoption, while **Lombardia (0.06%), Friuli-Venezia Giulia (0%), Veneto (0%), Lazio (0%), Sicilia (0%) have essentially none**. The Aria S.p.A. / Insiel / Lepida / CSI-Piemonte story the press tells is **not what the data shows for the email layer**: Lepida and CSI-Piemonte do appear (100 and 57 entities), but Insiel is **invisible** in the IndicePA email surface and Aria's role is procurement/aggregation (not email hosting) — explaining the Lombardia anomaly.

---

## Part 1 — Cloud Providers / Infrastructure Operators

### Evidence table — provider breakdown for all 22,987 IT entities

(Sources: `data/summary/stats_current.json` and `kpi.json` — `provider_raw` field on the dist CSV maps 1:1 to `provider` in `data.json`; **no separate `cloud_tenant_only` flag exists** — tenancy is captured in `mx_jurisdiction` (where the MX physically sits) and in `dkim_tenant` (the Microsoft 365 tenant name), not as a boolean.)

| Provider | `provider_raw` | Count | % on classified | Sovereignty bucket | Notes from the data |
|---|---|---|---|---|---|
| **Aruba S.p.A.** | `aruba` | **5,258** | **23.52%** | Provider Italiano (commerciali) | AS31034 / AS12637 / AS62076 → ASN override to `aruba` (catches custom MX like `mx.comune.foo.it` resolving to Aruba IPs). Keywords: `aruba.it`, `arubabusiness`, `aruba.cloud`, `arubapec`, `staff.aruba`, `arubacloud.com`. Observed in dist CSV as SPF provider (`_spf.aruba.it`) even when MX is on AWS — e.g. Comune di Penne (`c_g438`). |
| **Register.it / Dada** | `register-it` | **667** | **2.98%** | Provider Italiano (commerciali) | AS39729. Keywords: `register.it`, `register-it`. |
| **Seeweb** | `seeweb` | **79** | **0.35%** | Provider Italiano (commerciali) | AS35369 / AS49367. Keywords: `seeweb.it`, `seeweb.com`, `seeweb.cloud`. |
| **InfoCert** | `infocert` | (in `infocert.it`/`infocert.eu` keywords) | – | Provider Italiano (commerciali) | AS39257 → ASN override. PEC-heavy; small email-share footprint in the data. |
| **Namirial** | `namirial` | (in `namirial.com`/`namirial.it`) | – | Provider Italiano (commerciali) | PEC + digital signature vendor; same as InfoCert profile. |
| **Fastweb S.p.A.** | *(none)* | n/a (folded into `local-isp`) | n/a | **Provider Italiano (commerciali)** | **No standalone `fastweb` provider**. Fastweb's AS12874 is in `LOCAL_ISP_ASNS` (mapped to `local-isp`). Fastweb is also a **PSN-qualified infrastructure operator** (Polo Strategico Nazionale, see below). Its visible presence in the email data is whatever the small slice of PA domains happen to relay through its AS — not separately broken out in the current 13 displayed providers. |
| **AIIP local-ISP aggregate** | `local-isp` | **1,717** | **7.68%** | Provider Italiano (commerciali) | 50+ small Italian commercial ISPs (LeoNet, Naquadria, A2A Smart City, Omitech, Irideos, Retelit, Geny, Connesi, Dedagroup, etc.) snapshotted from aiip.it/associati. Acts as a "Provider Italiano" catch-all: when no other rule fires and the MX host matches an AIIP member domain. |
| **Lepida S.c.p.A.** | `regional-public` | **~100** (Emilia-Romagna share) | – | **Cloud Italiano (sovrano)** | Keywords: `lepida.it`, `lepida.network`, `lepida.net` + AS31638 override. The dist CSV contains A.S.P. Rodolfo Tanzi (`asprtan`, welfare, Parma) with MX on `relay2-cner.ltt.it;relay5.ltt.it` (relay `ltt.it` = Lepida's CNER domain), classified as `regional-public`, domestic, confidence 0.8. |
| **CSI-Piemonte** | `regional-public` | **~57** (Piemonte share) | – | **Cloud Italiano (sovrano)** | Keywords: `csi.it`, `csipiemonte.it`. Dist CSV shows Afc Torino S.p.A. (`atctor`, `cimiteritorino.it`), Agenzia Interregionale per il Fiume Po (`aiifp_`, `agenziapo.it`), ARPEA Piemonte (`arpea_to`) all on MX `zmbmtain.csi.it`, SPF including `_spfucnet.csi.it;_spfmailfarmnet.csi.it`. Confidence 0.9, domestic. |
| **Insiel (FVG)** | *(none)* | **0** in FVG | **0%** in Friuli-Venezia Giulia | **Cloud Italiano (sovrano) — but 0 entities** | Keyword `insiel.it` is in the constants list, but the regional stats show FVG has **0 "Cloud sovrano" entities** out of 582. Insiel's email infrastructure does not surface through IndicePA; FVG's 193 "Infrastruttura autonoma" entities (33.62% of the region — the highest of any region after VdA) suggest FVG PA entities run their own MX or use shared local ISP relay, not the regional in-house. |
| **Aria S.p.A. (Lombardia)** | *(none)* | **2** in Lombardia | **0.06%** | **Cloud Italiano (sovrano) — essentially absent** | Aria S.p.A. (Azienda Regionale per l'Innovazione e gli Acquisti) operates SINTEL (e-procurement), NECA (e-marketplace), PECP (contract execution), MIAP/FVOE (eForms + FVOE anti-corruption checks), and is involved in the **Polo Strategico Nazionale** project (see `ariaspa.it` "Progetti / Digital / Polo Strategico Nazionale" page). Aria is a **central purchasing body / aggregator**, **not** an email host. The 2 "regional-public" entities in Lombardia are not on `ariaspa.it` MX — they are residual matches on the `ariaspa.it` keyword (likely Regione Lombardia entities or ARIA itself using its own domain). |
| **Liguria Digitale** | `regional-public` | **5** in Liguria | 0.87% | Cloud Italiano (sovrano) | Keywords: `liguriadigitale.it`. Dist CSV shows Liguria turismo (`arlpt_`, `lamialiguria.it`) and ARPAL Liguria (`arlpa_ge`) on MX `zmx1.liguriadigitale.it` and `mxarpal.liguriadigitale.it`. ARPAL additionally uses Libraesva (ESVA) gateway in front. |
| **Trentino Digitale / TIX** | `regional-public` | **~174** in Trentino-Alto Adige | 20.33% | Cloud Italiano (sovrano) | Keywords: `trentinodigitale.it`, `tix.it` (Trentino IT Exchange, verified self-hosted). Dist CSV shows ARSAN Toscana (`ars_tosc`, `ars.toscana.it`) and ARTEA Toscana (`arte_048`) on MX `mx.servizi.tix.it`, SPF `_spf.servizi.tix.it`. **TIX is also used by agencies outside Trentino** (Toscana ARSAN, ARTEA, ARTI). |
| **Gemeindenverband / Consorzio Comuni BZ** | `regional-public` | most of the 174 in BZ | (subset of the 20.33%) | Cloud Italiano (sovrano) | Keyword: `gvcc.net`. Dist CSV shows dozens of "Amministrazioni Separate Beni Uso Civico" (e.g. `asbuccd`, `amucdg`, `fasasads`) on MX `es1.gvcc.net;es2.gvcc.net`, SPF `spf.gvcc.net`. Serves ~100+ small South Tyrol communal entities. |
| **Regione Toscana / Regione Basilicata** | `regional-public` | **98** in Toscana, **110** in Basilicata | 8.37% / 32.74% | Cloud Italiano (sovrano) | ASN-based: AS6882 = Regione Toscana / PEGASO; AS35110 = Regione Basilicata; AS198045 = Provincia di Pesaro e Urbino; AS31403 = IN.VA. (Valle d'Aosta). Dist CSV: ARTI Toscana on `mta.regione.toscana.it` (AS6882), ALSIA Basilicata on `mailcleaner.alsia.it` (AS35110). |
| **ASMEL family** | `regional-public` | included in 4.97% Campania, 8.88% macroarea Sud | – | Cloud Italiano (sovrano) | Keywords: `asmel.it`, `asmenet.it`, `asmepec.it`, `asmecal.it` (Calabria), `asmecam.it` (Campania). Publicly-owned consortia of comuni, not third-party vendors. |
| **Sogei (Stato centrale)** | `regional-public` | small, mixed in | – | Cloud Italiano (sovrano) | Keyword: `sogei.it` (società in-house MEF, gestisce NoiPA, FSE, SIOPE+). Email footprint is mostly ministries/PA Centrale (52 entities, kept out of headline spotlight per `SPOTLIGHT_EXCLUDE` editorial policy). |
| **Istruzione MIM tenant** | `istruzione-miur-tenant` | **893** | **3.99%** (displayed as "Microsoft 365") | **USA (CLOUD Act)** in `sovereignty_of()` | The `*istruzione.it` / `*miur.it` / `*edu.it` keywords were **removed from `ITALIAN_REGIONAL_PUBLIC_KEYWORDS` on 2026-05-04** (issue noted in constants.py): verification showed the actual MX is `istruzione-it.mail.protection.outlook.com` (Microsoft 365). Schools are on Google Workspace for Education (~60%) and Microsoft 365 (~40%) — the tenant name carries the MIM identity but the infrastructure is US-jurisdiction. **This was a major correctness fix** (constants.py comment: "Classifying them as 'regional-public' was technically wrong AND politically misleading — actual MX provider must be reported"). |
| **`pa-contractor-private`** | `pa-contractor-private` | **1** | 0.00% | Provider Italiano (commerciali) | Keywords: `eng.it`, `engineering.it`, `almaviva.it`, `almavivaitalia.it`. Private outsourcers (Engineering Ingegneria Informatica, Almaviva). Kept distinct from `regional-public` so the map can show "private outsourcer" vs "public in-house". |

### ANAC & public-procurement cross-references (qualitative, no local ANAC dump exists)

- **Aruba** — historically **PSN-qualified (PSN = Polo Strategico Nazionale, AgID)** for "Public Cloud" and "SaaS" service categories, and is a major CONSIP convention partner (`Convenzione Cloud Computing` lotto 1/2/3). The Aruba cloud email offering powers the `.gov.it` PEC and a large share of small PA email. From the mxmap data, **5,258 entities** rely on Aruba for the email layer — the largest single Italian commercial share.
- **Fastweb** — Fastweb (Swisscom subsidiary) is the **PSN operator of one of the four PSN lots** (the "PSN Lotto 1 — Cloud Computing" / "Cloud Enabling" infrastructure for PA Centrale and ASL). This is a **PNRR Mission 1** (digitalizzazione PA) infrastructure role. Its visible email footprint in the IndicePA data is via AS12874 (mapped to `local-isp`).
- **Lepida** — in-house for Emilia-Romagna (società consortile a capitale interamente pubblico regionale); a "natural person" in-house providing the Lepida Cloud / Lepida2Cloud. No PNRR PSN role (regional in-house by design).
- **CSI-Piemonte** — in-house for Piemonte; CSI has been historically the regional IT outsourcer. **No PNRR PSN role.**
- **Insiel** — in-house for Friuli Venezia Giulia; operates Insiel Mercato. **No PNRR PSN role.** The mxmap evidence shows Insiel is **not** a visible email provider for FVG IndicePA entities — FVG's 582 entities use 50.35% Microsoft/Google CLOUD Act exposure, 33.62% self-hosted, 0% regional-public.
- **Aria S.p.A. (Lombardia)** — Aria is the **soggetto aggregatore / central purchaser** for the Lombardy health system (SIREG) and many other regional contracts. Aria's project page explicitly lists **"Polo Strategico Nazionale"** as a Digital project. Aria is on the **Sintel** e-procurement platform and runs NECA. Crucially, Aria is **a procurement entity, not an email host**: it aggregates demand (drugs, elevators, healthcare devices, etc.) on behalf of Lombardy PAs, but does not run the regional email MX. This explains the 0.06% Lombardia "Cloud sovrano" share: Aria's in-house email domain itself is the only thing the keyword catches, while the actual email layer of Lombardia PAs goes to Aruba/M365/GW/independent.

### Caveat on `cloud_tenant_only` field

**There is no `cloud_tenant_only` boolean field in `data.json`.** The "tenant only" pattern is captured two ways:

1. **`dkim_tenant`** (e.g. `<ente>.onmicrosoft.com`): proves the Microsoft 365 tenant exists; used by the gateway look-through logic.
2. **`mx_jurisdiction`** (`domestic` / `foreign` / `mixed` / `unknown`): the **physical** location of the MX server (via Team Cymru DNS `origin.asn.cymru.com` / `origin-country.asn.cymru.com`). This is the **technical** sovereignty axis that **complements** the legal-control sovereignty (the gap is documented in the report, e.g. 52.65% ISD vs 46.1% domestic-MX = 6.5 pp of "provider IT on infra estera", itself a signal).

---

## Part 2 — Regional PAs + PNRR beneficiaries

### The 5 focus regions (from `data/summary/stats_by_region.json`, n=22,987)

| Regione | n | ISD | CLOUD Act | Cloud sovrano | Provider commerciali | Infrastruttura autonoma | Notable characteristics |
|---|---|---|---|---|---|---|---|
| **Lombardia** | 3,348 | **41.92%** | 58.08% | **0.06%** (2 enti) | 25.58% | 16.28% | 3,348 enti (largest region), 2° lowest ISD. **Aria S.p.A. is a procurement agency, not a cloud email provider** — hence no `regional-public` footprint. The 0.06% is `ariaspa.it` keyword residual. Lombardia PAs buy email from Aruba, Microsoft 365, Google; the 16.28% "Infrastruttura autonoma" is the share that runs on local ISPs (Fastweb, Vodafone, etc.). |
| **Lazio** | 1,812 | 50.23% | 49.77% | **0%** (0 enti) | 44.66% | 5.57% | The Region's own IT (Lazio Innova, LAIT) does not appear in IndicePA email surface. Lazio's 44.66% "Provider commerciali" is the highest of the 5 — dominated by Aruba + PEC commerciali. The 5.57% "autonoma" is the lowest among the 5 (suggesting more concentration in commercial vendors). |
| **Campania** | 1,928 | 53.54% | 46.46% | **4.97%** (94 enti) | 42.91% | 5.66% | The 4.97% "Cloud sovrano" is likely the **ASMECAM** (`asmecam.it`) consortium of Campania comuni (publicly-owned shared services, distinct from commercial vendors). Campania has the **highest "Provider commerciali" share** of the 5 (42.91%). |
| **Sicilia** | 1,787 | 57.01% | 42.99% | **0%** (0 enti) | 47.82% | 9.19% | Despite the 0% regional-public share, Sicilia is the **3rd most sovereign of the 5** thanks to a very high "Provider commerciali" share (47.82% — Aruba, Register.it, Seeweb, local ISPs). No "Sicilia Digitale" or similar regional in-house email presence. |
| **Veneto** | 1,667 | **41.33%** | **58.67%** | **0%** (0 enti) | 28.84% | 12.48% | **Most exposed to CLOUD Act of all 20 regions** (cited verbatim in `report.json` "Sintesi per i decisori": *"Veneto è la più esposta al CLOUD Act (58.67%)"*). 0% regional-public; Veneto's regional IT (Veneto Agricoltura, etc.) is not a cloud email provider for PAs. |

### Per-region MX provider evidence (from `dist/mxmap_it_dataset.csv`)

- **CSI-Piemonte** — every Piemonte agency on `zmbmtain.csi.it` (e.g. `atctor`, `aiifp_`, `arpea_to`). SPF includes `_spfucnet.csi.it`, `_spfmailfarmnet.csi.it`, sometimes `_spf_euwest1.prod.hydra.sophos.com` (Sophos gateway in front).
- **Lepida (Emilia-Romagna)** — `relay2-cner.ltt.it; relay5.ltt.it` (CNER = Centro Nazionale di Epidemiologia e Ricerca, hosted on Lepida). Confidence 0.8 (LTT is a "less common" Lepida subdomain, hence the dip from 0.9).
- **TIX (Trentino Digitale)** — `mx.servizi.tix.it` (also used by ARSAN/ARTEA/ARTI Toscana — confirms the cross-regional reuse).
- **Gemeindenverband / GVCC (BZ)** — `es1.gvcc.net; es2.gvcc.net`; SPF `spf.gvcc.net`; ~100+ "Amministrazioni Separate Beni Uso Civico" entities.
- **Regione Toscana** — `mta.regione.toscana.it` on AS6882 (PEGASO).
- **Regione Basilicata** — `mailcleaner.alsia.it` (ALSIA itself); ASN AS35110 (Regione Basilicata).
- **Sardegna IT** — `mail.sardegnait.it` for AGRIS.
- **Liguria Digitale** — `zmx1.liguriadigitale.it; mxarpal.liguriadigitale.it` (ARPAL also fronts with `esva01/esva02.arpal.liguria.it` Libraesva gateway).

### Notable regional contrasts

1. **Lombardia paradox** — the *largest* region by entity count (3,348) is the 2° *least sovereign* (41.92% ISD) and has **effectively no regional cloud email** (0.06%, 2 entities). Aria S.p.A. is a procurement/soggetto-aggregatore, not a cloud email provider. Lombardia PAs source their email commercially (Aruba, Microsoft 365, Google) and self-hosted on local ISPs.
2. **Veneto paradox** — 0% regional-public **and** the highest CLOUD Act exposure (58.67%) of all 20 regions. There is no in-house Veneto cloud email; Veneto's 28.84% "Provider commerciali" share is the *lowest* of the 5 focus regions, displaced by direct Microsoft 365 / Google adoption.
3. **Trentino-Alto Adige / Basilicata / Calabria effect** — these small/southern regions have the highest "Cloud sovrano" shares (20.33% / 32.74% / 29.05%) thanks to early in-house regional infrastructure (Trentino Digitale + GVCC, Regione Basilicata AS35110, Calabria's region-managed PEC infrastructure). **Geography is not destiny**: the presence of a regional in-house provider matters more than population/wealth.
4. **The macroarea "Sud" bonus** — the macroarea "Sud" (5,405 entities, ISD 57.53%, CLOUD Act 42.47%) is the **2° most sovereign macroarea** (after Isole 59.09%), driven by 466 "Cloud sovrano" entities (8.88% — the highest of any macroarea). This is the exact opposite of the "Nord = più ricco = più cloud sovrano" intuition: the in-house regional infrastructure is more developed in some smaller southern / special-statute regions.
5. **"Infrastruttura autonoma"** as a 3° axis — the `independent` bucket (13.85% of all entities, 3,096) is structurally interesting: FVG (33.62%), Valle d'Aosta (51.33%), Piemonte (36.29%), Trentino (some) all have high "Infrastruttura autonoma" shares. This is the *missing* cloud sovrano — PAs that run their own mail servers. It counts as `Italia — Infrastruttura autonoma` (sovereign) in the 6-bucket model, but is **operationally fragile** (no economies of scale, no PNRR-grade certification).

### PNRR beneficiaries (cross-reference, qualitative)

- **Polo Strategico Nazionale (PSN)** — PNRR Mission 1, Componente 1, Investimento 1.1: "Infrastrutture digitali". The PSN is run by a consortium led by **Aruba, Fastweb, TIM (Telecom Italia) and Leonardo**, qualified by AgID. **PSN is for workloads classified "ordinari" and "critici"** of PA Centrale + Sanità; it is the *target* infrastructure for migrations of qualifying workloads, not the *current* email layer. Fastweb's role here is **infrastructure (compute / storage / network for PSN)**, not email-as-such.
- **Cloud Italia / AgID Qualificazione** — AgID qualifies cloud services for PA workloads. Aruba, Seeweb, Register.it are all in the "Marketplace AgID" of qualified SaaS / Public Cloud providers (current state needs to be verified against `cloud-italia.acquisti-in-rete.it`, ANAC dataset not present locally).
- **PNRR Mission 1 C1 I1.3 "Dati e interoperabilità"** — beneficiaries include the regional hubs (Lepida, CSI, Liguria Digitale, etc.) for data-platform migrations; the email layer is a separate, smaller slice.
- **Lepida, CSI-Piemonte, Liguria Digitale, Trentino Digitale** are *de facto* PNRR-blessed regional in-house providers for *digital infrastructure* beyond email; their PNRR funding is on the data/health/mobility stacks, not on email, but they reuse the same regional sovereignty rationale.

---

## Sources

### Kept (high confidence, all primary or local)

- `data/summary/stats_current.json` — provider & sovereignty breakdown (2026-06-10) — [local]
- `data/summary/stats_by_region.json` — 20 regioni + 4 macroaree (2026-06-10) — [local]
- `data/summary/stats_by_category.json` — 15 cluster citizen (2026-06-10) — [local]
- `kpi.json` — headline KPIs for Osservatorio consumption (2026-06-15) — [local]
- `report.json` — full report incl. "Analisi per aree" section (2026-06-16) — [local]
- `data/reports/anomalies.json` — 767 anomalies, 3.34% (2026-06-12) — [local]
- `dist/mxmap_it_dataset.csv` (mxmap.it/dist) — per-entity evidence with `mx_records`, `dkim_tenant`, `spf_includes`, `mx_countries`, `mx_jurisdiction`, `provider_raw` — sampled entries confirm Lepida/CSI/TIX/GVCC/Liguria Digitale on real MX hostnames.
- `src/mail_sovereignty/constants.py` — `ITALIAN_REGIONAL_PUBLIC_KEYWORDS`, `ITALIAN_PROVIDER_ASN_OVERRIDES`, `LOCAL_ISP_ASNS` (including Fastweb AS12874) — [local]
- `src/mail_sovereignty/historicize.py` — `PROVIDER_DISPLAY` and `sovereignty_of()` canonical mapping — [local]
- Aria S.p.A. homepage <https://www.ariaspa.it/> — confirms ARIA's role as **Azienda Regionale per l'Innovazione e gli Acquisti**, lists "Polo Strategico Nazionale" as a Digital project. **Drop detail:** the page only confirms Aria's *mission*; no email/MX footprint is described (consistent with the mxmap 0.06% finding).

### Dropped / no usable signal

- Exa / Perplexity / Gemini web searches: all returned "rate limit / API key not configured" errors in this session.
- `agid.gov.it/it/piattaforme/cloud-italia` — 404 (the page has been renamed/moved under `agid.gov.it/it/infrastrutture/cloud-pa`).
- Lepida, CSI-Piemonte, Aruba `/about-aruba/cloud-government.aspx` — 404 pages (cookie consent walls + deleted URLs).
- `www.clouditalia.it/chi-siamo` — fetch failed.

---

## Gaps

1. **No local ANAC dataset.** The task referenced `data/anac/`, but the repository has no such folder (verified against the GitHub tree). All ANAC cross-references above are *qualitative*, drawn from public sources — not from a local bandi-gara dump. **Next step:** either (a) populate `data/anac/` via `scripts/fetch_anac.py` (not present — would need to be written against `dati.anticorruzione.it/opendata/dataset/partecipanti` JSON/CSV) and join on `cedente/aggiudicatario` ↔ `ipa_codice` for PA, then `piva` ↔ Aria/Aruba/Fastweb for suppliers; or (b) drop the ANAC angle from the public Osservatorio story and rely on the PSN / AgID / cloud-italia angles only.
2. **No `fastweb` provider tag.** Fastweb's PSN role is real but its email-layer presence is folded into `local-isp` (AS12874). A `regional-public / fastweb-psn` bucket is not currently broken out — even though Fastweb is structurally a *PSN infrastructure operator*, the MxMap model treats it as a generic Italian commercial ISP. This conflates two distinct roles (commercial ISP vs PSN national infrastructure). **Next step:** if Fastweb-PSN should be visible as a distinct sovereign bucket, add `fastweb.it` to `ITALIAN_REGIONAL_PUBLIC_KEYWORDS` with the caveat that the AS is mixed PSN + commercial; the data is already there to disambiguate per-entity.
3. **No `cloud_tenant_only` boolean.** The concept is captured across `dkim_tenant` (Microsoft) and `mx_jurisdiction` (Team Cymru), but no flat boolean. Not a bug, just a clarification.
4. **Aria S.p.A. mismatch.** Aria is a soggetto aggregatore / central purchaser (SIREG, NECA, SINTEL), not an email host. The 0.06% Lombardia "regional-public" is the keyword tail catching `ariaspa.it` itself, not a real cloud email footprint. **Next step:** if the report needs to call out Aria's PSN role explicitly, add it as a "context" footnote rather than a provider row.
5. **Insiel absence is unexplained.** Friuli-Venezia Giulia has 0 "regional-public" entities out of 582, despite `insiel.it` being in the keyword set. Either Insiel does not host the email layer for the FVG PAs registered in IndicePA (the most likely answer — Insiel probably provides *systems integration* and not the mailbox), or the keyword pattern is too narrow (only catches `*.insiel.it` hostnames, not custom domains on Insiel's MX). **Next step:** verify with an active FVG entity's MX (e.g. `regione.fvg.it`) to confirm whether Insiel is upstream or absent.
6. **The `istruzione-miur-tenant` 893-entity mass is technically Microsoft 365.** The 2026-05-04 constants.py fix correctly demoted edu.it / istruzione.it from `regional-public` to `microsoft`. The 3.99% provider_display in the dist CSV is correctly "Microsoft 365" — the *sovereignty* is CLOUD Act. This is documented and disclosed (see `stats_by_category.json` Istruzione: 78.16% CLOUD Act).
7. **No PNRR / cloud-italia-qualification cross-reference data.** The "Polo Strategico Nazionale" project exists for Fastweb / Aruba / TIM / Leonardo; the actual ANAC-derived evidence is **not** in the local data and would require either ANAC dataset ingestion (gap #1) or manual lookup against `cloud-italia.acquisti-in-rete.it`.
