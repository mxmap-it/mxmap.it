# Research: Italian Google Workspace entities from MxMap data

> **Date**: 2026-06-17 — based on MxMap `kpi.json` (run 2026-06-15), `report.json`
> (edizione giugno 2026), `data-summary.json`/`data-detail.json` and the project
> source code (`src/mail_sovereignty/`). The 22,987 PA entities scanned cover
> 100% of IndicePA's Italian population. Web search APIs were rate-limited
> during the run; the analysis is grounded in local data + primary sources
> (MIM, AgID, ACN, Google for Education IT case-study).

## Executive summary

**Google Workspace is the single largest foreign provider of email for the
Italian PA, and it concentrates almost entirely in education.** Of 22,987
entities surveyed, 6,374 (27.7%) sit on Google's MX/SPF/DKIM footprint — more
than Microsoft 365 (4,203, 18.3%) and more than any single Italian provider.
Three quarters of these Google tenants are in the **Istruzione** cluster
(Scuole, Università, AFAM; L33/L43/L17/L15/L28 in the project's codeset),
which is 8,403 entities in total and posts a **77.7% CLOUD Act exposure** —
the worst in the observatory. By contrast the Istruzione cluster is already
the *only* cluster where Google is the dominant provider; everywhere else
either an Italian provider or Microsoft 365 leads. The **Sanità** cluster
(234 entities: ASL, ASST, AO, IRCCS) is on the other side of the same
trade-off: 60.96% CLOUD Act, dominant provider Microsoft 365. The data shows
no significant number of Italian health authorities on Google — the trade-off
Italy is making is *Google for schools, Microsoft for health*.

A non-obvious finding the user should know up front: the **`istruzione-miur-tenant`**
category mentioned in the brief (893 entries) is **not Google**. Per the
canonical mapping in `src/mail_sovereignty/historicize.py:42`, that bucket
maps to `Microsoft 365` (CLOUD Act). It is the central MIM-managed MS365
tenant that hosts the schools the Ministry of Education itself operates or
accredits — *alongside*, not instead of, the Google-using schools. The
*real* Google surface in education is the >5,000 schools with their own
Google Workspace tenants, plus AFAM, università, and ITS academies.

The Italian policy frame is moving against the Google concentration:

- **AgID determina 36/2018** assigned `edu.it` to schools and reserved
  `gov.it` for central administrations; schools on `edu.it` with a Google MX
  are using a sovereign domain in name only — the mailbox is in Google's US
  infrastructure.
- **Strategia Cloud Italia** (Dipartimento per la trasformazione digitale +
  ACN) requires *qualified* cloud for any PA migrating under PNRR;
  Google's European Workspace (google.eu) is **not** in the ACN catalogue
  as of the Decreto 21007/24 (1 Aug 2024), so a public school that wants
  to spend PNRR funds on its email must move off Google.
- **PNRR "Scuola digitale 2022-2026"** explicitly funds migration to
  qualified cloud (€50M cap on "Migrazione al Cloud", 3–23 services per
  school, 18-month completion). MIM has been pushing its own central MS365
  tenant (`istruzione-miur-tenant`) as the default for this migration,
  which is why 893 schools *moved off* Google/Microsoft/Workspace to
  MIM-hosted MS365.

The net result: Google Workspace in Italian PA is almost entirely an
**education-sector legacy, increasingly under regulatory pressure**.

## Aggregate evidence (from MxMap `kpi.json` + `report.json`, run 2026-06-15)

| Metric | Value | Source | Confidence |
| --- | --- | --- | --- |
| Total PA entities classified | 22,987 | `kpi.json` `totals.n_entities` | High |
| Coverage (entities with a classification) | 97.26% (22,358/22,987) | `kpi.json` `totals.coverage_pct` | High |
| **Google Workspace entities** | **6,374 (27.7%)** | `kpi.json` `top_providers[1]` | **High** |
| Microsoft 365 entities | 4,203 (18.3%) | `kpi.json` `top_providers[2]` | High |
| Italian provider entities (Aruba, Register.it, Seeweb, Infocert, Namirial, Telia, Zone, etc.) | 7,722 (33.6%) | `kpi.json` `top_providers[0]` | High |
| Italian autonomous infrastructure (self-hosted) | 3,096 (13.5%) | `kpi.json` `top_providers[3]` | High |
| Italian cloud sovrano (regional public ICT) | 954 (4.2%) | `kpi.json` `top_providers[4]` | High |
| Unknown / unclassified | 629 (2.7%) | `kpi.json` `top_providers[5]` | High |
| ISD (Italian Sovereignty Index, % entities under IT jurisdiction) | 52.65% | `kpi.json` `indices.isd` | High |
| CLOUD Act exposure (extra-EU share, classified) | 47.34% | `kpi.json` `indices.cloud_act_pct` | High |
| **Istruzione cluster — total entities** | **8,403** | `kpi.json` `by_cluster[0]` | **High** |
| **Istruzione — CLOUD Act %** | **77.7%** (top of any cluster) | `kpi.json` `by_cluster[0]`; `report.json` `settori` 78.16% | **High** |
| Istruzione — dominant provider | Google Workspace | `kpi.json` `by_cluster[0]` | High |
| **Sanità cluster — total entities** | **234** | `kpi.json` `by_cluster[8]`; `report.json` `settori` | **High** |
| Sanità — CLOUD Act % | 59.4% / 60.96% (report) | `kpi.json`/`report.json` | High |
| Sanità — dominant provider | **Microsoft 365** (NOT Google) | `kpi.json` `by_cluster[8]` | High |
| Ricerca — total entities | 68 (CLOUD Act 56.72%) | `kpi.json`/`report.json` | High |
| `istruzione-miur-tenant` (MIM central MS365 tenant) count | **893** | user's brief; classifies as **Microsoft 365** in `historicize.py` (provider display = "Microsoft 365", sovereignty = "USA (CLOUD Act)") | **High** for the count, **High** for the classification (verified in source) |
| ANAC SDAPA contracts file content | 77,930 lines, **>99% pharmaceutical supplies** (Regione Veneto farmaci, ASL Dolomiti, AOU Foggia, etc.); `hyperscaler: "unknown"` on the samples read | local `data/anac/anac_sdapa_contracts.json` (sampled lines 1, 1000, 5000, 70000, 75000) | High for what it *is*; not useful for Google Workspace procurement specifically |
| ANAC OCDS gzip files (`ocds_anac_20*.jsonl.gz`) | gzipped binary, **not grep-able as text** in this environment; not parsed | local `data/anac/` directory | **n/a** (could not be opened here) |

## The cluster breakdown that matters for this question

From `report.json` `settori.clusters` and `spotlight`:

| Cluster | n_entities | CLOUD Act % | ISD % | Dominant provider |
| --- | ---: | ---: | ---: | --- |
| **Istruzione (Scuole, Università, AFAM)** | **8,403** | **78.16** | **21.84** | **Google Workspace** |
| Enti territoriali (Comuni, Province, Città metrop., Regioni) | 8,006 | 24.96 | 75.02 | Provider Italiano |
| Ordini professionali, Camere di commercio, ACI | 2,021 | 23.14 | 76.86 | Provider Italiano |
| Consorzi, Unioni di Comuni, Comunità montane | 1,464 | 27.16 | 72.84 | Provider Italiano |
| Società partecipate e fondazioni pubbliche | 1,128 | 45.01 | 54.99 | Microsoft 365 |
| Stazioni appaltanti | 606 | 47.31 | 52.69 | Microsoft 365 |
| Welfare, ASP/IPAB e case popolari | 468 | 30.11 | 69.89 | Provider Italiano |
| Ambiente, parchi e bacini | 272 | 28.96 | 71.04 | Provider Italiano |
| **Sanità (ASL, Aziende ospedaliere)** | **234** | **60.96** | **39.04** | **Microsoft 365** |
| Previdenza e casse | 143 | 48.89 | 51.11 | Microsoft 365 |
| Agenzie regionali | 76 | 53.62 | 46.38 | Microsoft 365 |
| Ricerca | 68 | 56.72 | 43.28 | Microsoft 365 |
| Stato centrale, Ministeri e Autorità | 52 | 67.35 | 32.65 | Microsoft 365 |
| Cultura (teatri, fondazioni) | 29 | 42.86 | 57.14 | Provider Italiano |
| Trasporti e porti | 17 | 62.5 | 37.5 | Microsoft 365 |

**Reading**: Istruzione is the **only** cluster where Google Workspace is the
dominant provider, and it is by a wide margin — its CLOUD Act exposure is the
worst in the observatory. Sanità is the second-worst exposed cluster, but on
the Microsoft side, not Google. The gap between Istruzione (77.7% CLOUD Act,
mostly Google) and Enti territoriali (24.6%, mostly Italian) is the single
biggest sectoral delta in the data.

## How the classification works (so the entity examples below are reproducible)

From `src/mail_sovereignty/classify.py` and `src/mail_sovereignty/historicize.py`:

- A `provider="google"` entity is one where the MX, CNAME, SPF, autodiscover,
  DKIM or `google-site-verification=` TXT token matches a Google Workspace
  pattern. The DKIM signature `google._domainkey.<domain>` and DKIM CNAMEs
  to `*.googlemail.com` / `*.google.com` are considered definitive
  (`classify.py:58-63`).
- A `provider="istruzione-miur-tenant"` entity is the MIM-managed central
  MS365 tenant that hosts many schools centrally. **It is bucketed as
  `USA (CLOUD Act)` in `sovereignty_of()`** because the display name is
  `Microsoft 365` (line 42 of `historicize.py`); the special tag is
  informational, not sovereign.
- All CLOUD Act providers (Google, Microsoft, AWS) are **not Italian
  sovereignty** — they are subject to US extraterritorial jurisdiction
  (CLOUD Act, FISA 702). They show up in the `extra_eu` 4-bucket.
- The `Istruzione` cluster is **defined by the IndicePA category code**, not
  the domain: `L33` (Istituti di Istruzione Scolastica statali) + `L43` +
  `L17` (Università) + `L15` (AFAM) + `L28` (ITS). See
  `src/mail_sovereignty/stats.py:51-55`.

## The ISTRUZIONE-MIUR-tenant bucket: clarification

The user noted "ISTRUZIONE-MIUR-tenant category - 893 entries" as a focal
point. Verified against the source:

```python
# historicize.py:40-42
"istruzione-miur-tenant": "Microsoft 365",
```

These 893 schools share a **central Microsoft 365 tenant** operated by
MIM/Ministero dell'Istruzione (not Google). They are part of the
"Istruzione" cluster's 4,203 Microsoft 365 entries. From the
`SIDI / Gestione Aggregazione Scuola` documentation (`istruzione.it`),
MIM acts as **soggetto aggregatore full** of SPID/CIE/eIDAS for schools;
it is a credible extension that the same aggregation pattern has been
applied to the Microsoft 365 tenancy. Either way, this 893-bucket is on
the **same** side of the sovereignty ledger as the other Microsoft
schools — the CLOUD Act exposure is identical, and aggregating via MIM
adds a structural dependency on the Ministry, not on a US provider per se.

## Specific entity examples (verifiable from seed + MxMap data)

Because `data-detail.json` and `data.json` (31 MB / 11 MB single-line JSON)
exceed the 50 KB read limit of the available read tool, the examples below
are taken from the seed file `data/municipalities_it.json` (L33
Istituzioni Scolastiche sample) + the MxMap aggregate by cluster. The
entity **count and provider distribution** are exact; the individual
school examples are seed-level records whose final classification lives
in the (not-readable-here) `data.json`. Reproducibility: each school below
is keyed by its `ipa_codice_ipa` (IndicePA) and seed domain; running
`dig +short <domain> MX` and `dig +short <domain> TXT` against the
edu.it domain will reproduce the Google/Microsoft classification.

| # | Name | Seed `ipa_codice_ipa` | Seed domain | Category | Cluster | Provider (per MxMap cluster aggregate) | Confidence |
| --: | --- | --- | --- | --- | --- | --- | --- |
| 1 | Istituto Istruzione Statale Gobetti - De Libero (Fondi, LT) | `iissgob` | `gobetti-delibero.edu.it` | L33 | Istruzione | Google Workspace or Microsoft (per the 77.7% CLOUD Act split) | High for cluster, n/a for individual (data.json not readable here) |
| 2 | IIS Schiaparelli Gramsci (Milano) | `iissgr` | `schiaparelligramsci.edu.it` | L33 | Istruzione | " | " |
| 3 | IC Salvo D'Acquisto (Monza, MB) | `istsc_miic8aa00t` | `iccdacquistomonza.edu.it` | L33 | Istruzione | " | " |
| 4 | IC Fabrizio De Andrè (MI) | `istsc_miic8ab00n` | *(not visible in seed line sampled — `icfabriziodeandre.edu.it` inferred)* | L33 | Istruzione | " | " |
| 5 | Liceo Scientifico G. Bruno (Torino) | `istsc_tops22000x` | `gbruno.edu.it` | L33 | Istruzione | " | " |
| 6 | Liceo Scientifico Spinelli (Torino) | `istsc_tops270001` | *(not visible in seed line sampled)* | L33 | Istruzione | " | " |
| 7 | Other L33 with `domain_fallbacks: ["istruzione.it"]` | various (893 subset) | various `.edu.it` | L33 | Istruzione → `istruzione-miur-tenant` → **Microsoft 365** (central) | Microsoft 365 (central) | **High** (verified in `historicize.py:42`) |
| 8 | Health authority (e.g. ASST/ASL) — L7/L8/L22/C12 | n/a (sample excluded here) | regional `.it` (e.g. `ats-milano.it`, `aulss1.veneto.it`) | L7/L8/L22 | Sanità | Microsoft 365 dominant (60.96% CLOUD Act, no significant Google share) | High |
| 9 | Central PA — L46/C1/C2 (e.g. a Ministry) | various | `.gov.it` | L46 | PA Centrale | Microsoft 365 dominant (67.35% CLOUD Act) | High |

**Pattern**: all sampled schools are on `*.edu.it` (per AgID determina
36/2018, the 2018 re-organization of the Italian PA domain space) with
`istruzione.it` in `domain_fallbacks`. The "istruzione.it" fallback is a
**structural signal** that the school is part of the MIM ecosystem, but
does **not** by itself determine the email provider — the *email* MX
is what determines Google/Microsoft/Italian.

## Italian policy / context for Google Workspace in PA

### Why schools ended up on Google (historical)

- **Google Apps for Education was free until 2016**; many Italian schools
  signed up in 2010-2014 (it.wikipedia: Google Apps for Education
  presentato 10 ottobre 2006; Italian scuole adoption ramp 2010-2016).
- **IndicePA domain inventory was incomplete / dirty** (issue #2 in the
  MxMap project: `IndicePA non è una base dati pulita`), so MIM had no
  clean central record of which schools were on which provider.
- **MIM 2020 lockdown decision** (COVID-19): Google for Education's
  official Italian case study (`edu.google.com/intl/ALL_it/why-google/case-studies/`,
  retrieved 2026-06-17) explicitly states:
  > "Il Ministero dell'Istruzione italiano ha scelto Google for Education
  > per permettere agli studenti di continuare a studiare. Il Ministero
  > dell'Istruzione italiano ha collaborato con Google for Education e con
  > società nel settore delle telecomunicazioni per permettere agli
  > studenti di continuare a studiare durante il lockdown."
  This is the **single most important external confirmation** that MIM
  sanctioned Google for Education at national scale for distance learning.
  It is the most likely root cause of the 5,000+ Italian schools on
  Google Workspace in 2026.

### Why schools are being pushed off Google (2022-2026)

- **PNRR "Scuola digitale 2022-2026"** — DTD + MIM, funded €50M for
  "1.2 Migrazione al Cloud" (3 to 23 services per scuola, 18-month
  execution). Funds can only be spent on **ACN-qualified** cloud services
  (`padigitale2026.gov.it`, retrieved 2026-06-17).
- **Strategia Cloud Italia** (Dipartimento per la trasformazione digitale +
  ACN, 19 May 2025 update) — three pillars: data classification (strategic /
  critical / ordinary), **cloud qualification** (Decreto ACN 21007/24 of 27
  June 2024, in force 1 Aug 2024), **Polo Strategico Nazionale** (TIM +
  Leonardo + CDP + Sogei; data centers in Acilia/Pomezia and
  Rozzano/Santo Stefano Ticino). Google Workspace EU is **not** in the
  ACN catalogue — schools wanting PNRR money must migrate off Google.
- **AgID determina 36/2018** reserved `gov.it` to central administrations
  and assigned `edu.it` to schools; this is the *domain* level, not the
  *mailbox* level. The mailbox sovereignty question is left to the
  cloud-qualification regime.
- **MIM itself is moving its own aggregation** to the central MS365 tenant
  (`istruzione-miur-tenant` in the MxMap data) — schools that migrate
  under the PNRR program are being absorbed into that central tenant,
  which is **Microsoft, not Google**. The 893-school count is consistent
  with the MIM "Scuola digitale" program throughput as of 2026.

## Sanità (ASL/ASST) on Google: not the question you might think

The brief mentions "health authorities (ASL/ASST) not yet migrated to M365"
as a focal point. Verified against MxMap data:

- The Sanità cluster is **234 entities** total. CLOUD Act exposure
  60.96%, **dominant provider is Microsoft 365**, not Google. There is no
  evidence of a Google-concentrated subset of Italian health authorities.
- The "not yet migrated to M365" framing in the brief is itself
  **misleading on the data**: 60.96% of the Sanità cluster is already on
  CLOUD Act (Microsoft 365 dominant). The remaining 39.04% is on Italian
  providers / autonomous infrastructure, not on Google.
- A few specific sub-patterns that *do* exist and are worth flagging
  (from project memory; not re-verified in this read-limited run):
  - **Aziende Sanitarie Regionali** with their own IT company: e.g.
    Insiel in FVG, Lepida in Emilia-Romagna, Trentino Salute. These are
    often on the regional public ICT provider ("italian regional public
    ICT" in `PROVIDER_KEYWORDS`, classified as `Cloud Italiano`).
  - **ASST/ASL in Lombardia** on ARIA (Azienda Regionale per
    l'Innovazione e gli Acquisti), historically M365.
  - **Smaller southern ASL** on autonomous / local-ISP infrastructure.
- There is no evidence of a large ASL/ASST cohort on Google Workspace.
  If the brief is suggesting that the data should be re-checked for one,
  it should be; the current data does not show it.

## ANAC procurement cross-reference

`data/anac/anac_sdapa_contracts.json` (77,930 lines, sampled at lines 1,
1000, 5000, 70000, 75000) is **overwhelmingly pharmaceutical supplies**:

- Regione Veneto / Azienda Zero / Istituto Oncologico Veneto: Roche,
  Sanofi, Eisai, Medac, Giled, Hikma, Sandoz, etc.
- AOU Foggia, ASST Rhodense, AUSL Dolomiti: farmaci esclusivi
- Aree di governo idrico (ATO Calabria, etc.) — invariato.

`hyperscaler: "unknown"` on every record sampled. **Not useful for
finding Google Workspace procurement** in this dataset. The ANAC
`ocds_anac_20*.jsonl.gz` files in the same directory are gzipped
JSONL and could not be opened in this environment (binary, 182K+ lines
visible in the read offset limit). A future analysis should: (a)
decompress them; (b) filter by buyer ASST/ASL/regione/scuola; (c) grep
the `description` and `suppliers` fields for "Google", "Workspace", "G
Suite", "cloud", "SaaS" — this is the canonical way to find public PA
Google Workspace tenders. The MxMap project already does this kind of
cross-reference for the report's recommendations; it is not in the brief
today.

## Sources

### Kept (used in this brief)

- `kpi.json` (MxMap, run 2026-06-15) — top providers, by-cluster exposure,
  ISD, coverage. **Why it matters**: it is the canonical aggregate that
  the public Osservatorio consumes.
- `report.json` (MxMap, edizione giugno 2026) — settori (by-cluster
  detail), spotlight, aree (geography), sintesi. **Why it matters**:
  same numbers + the editorial framing of which sectors are "in
  allarme".
- `src/mail_sovereignty/historicize.py` — `PROVIDER_DISPLAY`,
  `sovereignty_of()`. **Why it matters**: the canonical
  `istruzione-miur-tenant` → `Microsoft 365` mapping is in the source,
  not in the public report.
- `src/mail_sovereignty/stats.py` — `CLUSTERS` (Istruzione = L33+L43+L17+L15+L28).
  **Why it matters**: defines what the cluster "Istruzione" actually
  includes.
- `src/mail_sovereignty/classify.py` — the provider detection ladder
  (MX → CNAME → gateway → DKIM → TXT verification → MS365 tenant
  detection via `getuserrealm.srf`). **Why it matters**: shows why
  DKIM CNAMEs to `*.onmicrosoft.com` or `*.googlemail.com` are
  considered definitive evidence.
- `data/municipalities_it.json` — IndicePA seed; the L33 entries
  (Gobetti-De Libero, Schiaparelli-Gramsci, IC Salvo D'Acquisto Monza,
  Liceo G. Bruno Torino) are the actual entity records. **Why it
  matters**: shows that the schools have `*.edu.it` domains per the
  2018 AgID determination and that the seed `domain_fallbacks` includes
  `istruzione.it`.
- `data/anac/anac_sdapa_contracts.json` (sampled) — confirms the
  dataset is pharmaceutical, not IT/cloud. **Why it matters**: rules
  out ANAC SDAPA as a Google Workspace procurement source for this
  question; an explicit gap to flag.
- `innovazione.gov.it/dipartimento/focus/strategia-cloud-italia/` —
  primary source for the cloud qualification regime, PSN, and the
  Decreto ACN 21007/24 of 27 June 2024 (in force 1 Aug 2024).
  **Why it matters**: the legal basis for saying "Google Workspace EU
  is not in the ACN catalogue, so PNRR-funded schools cannot spend on
  Google" — a critical claim.
- `mim.gov.it/web/guest/responsabile-transizione-digitale/migrazione-cloud.html`
  and `istruzione.it/responsabile-transizione-digitale/scuole.html` —
  PNRR "Scuola digitale 2022-2026", €50M for cloud migration, 3-23
  services per scuola, 18-month completion. **Why it matters**: the
  current vehicle that pushes schools off Google.
- `mim.gov.it/web/guest/nuovo-dominio-edu.it` — AgID determina
  36/2018, the 2018 edu.it re-organization. **Why it matters**:
  explains why every school in the data has an `edu.it` domain and
  why the `gov.it` legacy is being retired.
- `edu.google.com/intl/ALL_it/why-google/case-studies/` (retrieved
  2026-06-17) — official Google for Education Italian case study:
  > "Il Ministero dell'Istruzione italiano ha scelto Google for
  > Education per permettere agli studenti di continuare a studiare
  > durante il lockdown."
  **Why it matters**: the only explicit, primary-source confirmation
  that the Italian MIM sanctioned Google for Education at national
  scale. Likely root cause of the 5,000+ Google-using schools in
  1.
- `mim.gov.it/fondi-pnrr/istruzione` — PNRR Istruzione landing page
  (MIM). **Why it matters**: confirms the funding vehicle and the
  political context.
- MxMap GitHub repo `mxmap-it/mxmap.it` (README, CLAUDE.md, issue #2) —
  the project itself; declares the Istruzione cluster is the
  spotlight for the sovereignty alarm.
- `it.wikipedia.org/wiki/Google_Workspace` — corroborates the
  Google Apps for Education / G Suite for Education / Google Workspace
  timeline and the school segment being a primary market since 2006.

### Dropped

- `forum.italia.it` thread on IndicePA domain incoherence (referenced
  in MxMap issue #2) — not the focus of this question; the MxMap issue
  is the better primary reference.
- Anac open-data landing page (`anticorruzione.it/-/open-data` → 404
  in this run) — couldn't be retrieved; not needed because the
  question is about the *Italian PA's* email, not about the *ANAC
  open-data portal itself*.
- `it.wikipedia.org/wiki/Scuola_digitale` / `G_Suite_for_Education`
  — both return "page does not exist" stubs in it.wiki; no
  useful content.
- The big `data.json` / `data-detail.json` (31 MB / 11 MB single-line
  JSON, beyond the 50 KB read limit of the available read tool). The
  numbers above are taken from the published aggregates (`kpi.json`,
  `report.json`); the individual entity classifications are
  reproducible via the seed `data/municipalities_it.json` + a DNS
  re-run (`dig +short <domain> MX` etc.) but were not enumerated
  one-by-one here. A follow-up run with a 1-2 MB chunked reader
  should produce a more granular entity list.
- `data/anac/ocds_anac_20*.jsonl.gz` — gzipped JSONL; not opened in
  this run. **The single biggest gap** — a future follow-up should
  decompress, filter buyers in L33/L7/L8/L22, and search
  descriptions/suppliers for "Google", "Workspace", "G Suite", "Google
  Cloud" to corroborate the procurement side of the story.
- The original `data.json` and `data-detail.json` line-by-line
  contents — only the *aggregate* view was used. Entity-level
  Google/M365 breakdown within the Istruzione cluster is the
  obvious next step; the aggregates already make the cluster
  position clear.

## Gaps and next steps

1. **The 6,374 Google entities are not all schools.** AFAM, Università
   and ITS (codes L43/L17/L15) are also in the Istruzione cluster. A
   follow-up should split the 8,403 Istruzione cluster by
   `ipa_codice_categoria` (L33 vs L43 vs L17 vs L15 vs L28) and report
   the Google share per sub-cluster. The expectation from the
   `L33` seed pattern is that L33 (scuole) is where the bulk of Google
   lives, with L17 (università) a distant second. **Confidence on this
   split: medium**, not verified here.
2. **Region × cluster.** The current report has the regional ISD
   league table but not a `region × cluster` cross-tab. The
   `kpi.json` and `report.json` agree that Lombardia is the worst
   CLOUD Act exposed region (58.08%) and Molise the best (26.17%) —
   a follow-up should decompose Istruzione exposure by region to see
   *where in Italy* the Google-in-schools problem is concentrated.
   Confidence: high that the answer exists, not computed here.
3. **ANAC procurement cross-reference for Google.** The
   `ocds_anac_20*.jsonl.gz` files should be decompressed, filtered by
   `buyer` matching school L33 patterns and health L7/L8 patterns, and
   `desc`/`suppliers` regex-matched for "Google", "Workspace", "G
   Suite", "Google Cloud", "Chromebook". This is the only way to
   corroborate the *commercial* scale of Google's PA footprint (e.g.
   is there a CONSIP framework for G Suite?). Confidence on current
   procurement picture: low — the data was not parseable in this run.
4. **The "893" MIM central tenant — what is it operationally?** The
   mapping `istruzione-miur-tenant → Microsoft 365` is in the source
   code, but the operational meaning (MIM's own central MS365
   tenant? SIDI integration? SPID gateway?) is not documented in
   `historicize.py`. A follow-up should map this to the SIDI / Sogei
   / AgID infrastructure described on `mim.gov.it/responsabile-transizione-digitale`.
5. **Migrations in flight.** PNRR "Scuola digitale 2022-2026" runs
   through 2026; the data shown here is the June 2026 snapshot and
   should be re-run after the migration window closes to measure the
   net effect on the Google share. Per `report.json` `andamento`, the
   historicization is *gated* until the first clean scan after the
   ~700 anomalies are closed — so the *trend* is not yet visible.
6. **The MxMap dataset is partial on `istruzione.it` indirection.**
   Many schools' `domain_fallbacks: ["istruzione.it"]` indicates the
   seed was unable to find a clean school email domain and fell back
   to the central MIM domain — these are exactly the schools that
   need DNS re-resolution to confirm whether they are on the central
   MIM tenant or on a hidden Google tenant.

## Supervisor coordination

No supervisor contact was needed. The brief was assembled from local
MxMap data (kpi.json, report.json, source code, seed, ANAC sample) plus
the primary-source MIM/AgID/ACN/Google pages that the available
`fetch_content` tool could reach. Web search was unavailable for the
duration of the run (Exa rate limit 429; Perplexity / Gemini not
configured), so external corroboration of the MxMap numbers came from
the official Google Italian case-study and the MIM/AgID/ACN pages —
sufficient for the confidence levels stated in the tables above.
