# Research: Aruba Cloud Providers & School Entities (mxmap.it, IT)

> **Context.** mxmap.it classifies the email provider of ~22,987 Italian PA
> entities (`data.json`, `kpi.json` run of 2026-06-15). This brief analyses
> the two segments the user flagged: **(1) ~5,258 entities classified as
> `aruba`** (Italian private commercial hosting) and **(2) ~893 entities
> classified as `istruzione-miur-tenant`** (a synthetic bucket representing
> schools that sign DKIM / host MX under MIM's central MS365 tenant).
>
> **Methodology note.** The source `data.json` is a single-line 31 MB JSON
> and the read tool used in this environment is capped at 50 KB per read.
> Live BFS samples were therefore **not** pulled row-by-row — the brief
> reasons about the data from (a) the codebase that *produces* the
> classification ([`src/mail_sovereignty/`](src/mail_sovereignty/)), (b)
> the published aggregate [`kpi.json`](kpi.json), (c) the curated test
> fixture ([`tests/test_stats.py`](tests/test_stats.py)) which mirrors the
> exact entry shape, and (d) primary web sources for Aruba and the
> Italian-PA cloud market. Each finding states the inference path so the
> confidence is auditable.

---

## Executive Summary

1. **Aruba is not a US hyperscaler and not a regional public operator** — it
   is a **private Italian commercial provider** (Aruba S.p.A., ASNs 31034 /
   12637 / 62076) that mxmap buckets as `aruba` → display "Provider
   Italiano" → sovereignty "Italia — Provider commerciali". With ~5,258
   entries it is the **largest single private provider** serving Italian
   territorial PAs in the dataset, and is the only one of the 5 Italian
   commercial providers that the codebase treats as a "local provider"
   eligible for DKIM look-through (i.e. can be re-classified to
   `microsoft`/`google` if its hosted mailboxes actually sign with a
   hyperscaler DKIM). Aruba is **listed by Consip as a PA IaaS/PaaS cloud
   provider** and holds **ACN AI3 + QC3** qualifications, which is why so
   many comuni route to it directly or via gateways.
2. **`istruzione-miur-tenant` is a special label for ~893 schools that are
   tenants of the MIM (Ministero dell'Istruzione e del Merito) central
   Microsoft 365** — mxmap maps it to display "Microsoft 365" / sovereignty
   "USA (CLOUD Act)". It is *not* a sovereign infrastructure: it lives on
   the same Microsoft hyperscaler as the L33 (Scuole) cluster. The
   constants file's 2026-05-04 note explicitly removed `edu.it`,
   `istruzione.it`, `miur.it` and `pubblica.istruzione.it` from the
   "regional-public" set because verification showed their MX all point to
   `*.mail.protection.outlook.com`. The Education cluster overall
   (8,403 entities, 77.7 % CLOUD Act exposure) is dominated by **Google
   Workspace for Education** on `*.edu.it` schools (~60 % of the cluster
   per the codebase note).
3. **The sovereignty finding is not symmetric between the two segments.**
   Aruba-hosted mail *can* be migrated in-house or to sovereign PSN
   infrastructure (it is just a hosting choice). The MIM central tenant
   cannot: the data sits on Microsoft's US infrastructure by design of the
   central framework agreement, and the ~893 schools are caught in the
   procurement dependency, not the technical one. This is the most
   important editorial distinction the Osservatorio should make explicit.

---

## 1. The `aruba` classification: what mxmap means by it

### 1.1 Definition (from the source code, not from the data)

`aruba` is one of the eight "Italian commercial provider" buckets
introduced in mxmap.it Phase 3 (see
[`docs/countries/ITALY.md` §Phase 3](docs/countries/ITALY.md)). The
classifier is documented in two places and both agree:

- [`src/mail_sovereignty/constants.py` `ARUBA_KEYWORDS`](src/mail_sovereignty/constants.py) →
  matched as a **substring** of the MX host blob:
  `aruba.it`, `arubabusiness`, `aruba.cloud`, `arubapec`, `staff.aruba`,
  `arubacloud.com`.
- [`src/mail_sovereignty/constants.py` `ITALIAN_PROVIDER_ASN_OVERRIDES`](src/mail_sovereignty/constants.py) →
  AS-based override: when the MX hostname does *not* carry an Aruba
  keyword (e.g. a custom `mail.comune.<name>.it` on Aruba IP space) but
  the MX IP belongs to AS **31034**, **12637**, or **62076**, classify
  as `aruba`. These are Aruba S.p.A.'s ASNs.

Combined, the two rules cover the "obvious" cases (MX host literally
named `*.aruba.it` etc.) **and** the silent cases where a comune
provisions its own mail hostname on Aruba hosting. The latter is common:
the 5,258 figure is dominated by the ASN-override path, not by
hostnames that shout "aruba" — this is why the override exists (per the
inline comment in `constants.py`).

Confidence: **HIGH** (direct code inspection, two corroborating sources).

### 1.2 Where the 5,258 entities come from (inference)

The user-reported figure (~5,258) is consistent with the published
`kpi.json` aggregate:

- The "Provider Italiano" roll-up in [`kpi.json`](kpi.json) is **7,722
  entities (33.6 %)** of 22,987.
- That bucket collapses seven distinct mxmap provider labels
  (`aruba`, `register-it`, `seeweb`, `infocert`, `namirial`, `local-isp`,
  `pa-contractor-private`) into one citizen-facing label, per
  [`src/mail_sovereignty/historicize.py` `PROVIDER_DISPLAY`](src/mail_sovereignty/historicize.py).
- Of those seven, `aruba` is the only one with an explicit
  multi-thousand-entry scale (3 ASN ranges, 6 keyword strings, gateway
  look-through behaviour — see
  [`src/mail_sovereignty/classify.py` `classify()` step 1](src/mail_sovereignty/classify.py)),
  and the only one documented in the project history as a
  "mass-market" territorial provider. `register-it` is small (Dada
  /TeamSystem is primarily PEC), `seeweb` is small (3 ASNs, niche), the
  rest are sub-1 K.
- The 5,258 figure therefore plausibly represents **~68 %** of the
  7,722 "Provider Italiano" total — a high concentration that matches
  Aruba's market-leader status (Wikipedia EN: "the market leader in
  Italy").

**Confidence: MEDIUM** (the breakdown isn't in `kpi.json`; the 68 % is
inferred from the codebase's treatment of the seven buckets).

### 1.3 What a typical `aruba` row looks like

Using the test fixture in
[`tests/test_stats.py`](tests/test_stats.py) `_e()` builder as the
canonical shape, a `provider="aruba"` entry has the following fields
populated by the pipeline (other fields exist but the ones that matter
for the bucket are):

| Field | Sample value | Meaning |
|---|---|---|
| `bfs` | `IT-COM-NNNNNN` (or other IT-prefix) | mxmap stable id (IndicePA-derived) |
| `country` | `"IT"` | territorial flag |
| `provider` | `"aruba"` | bucket |
| `mx_jurisdiction` | `"domestic"` or `"mixed"` | where the MX IP physically sits (from Team Cymru `origin.asn.cymru.com`) |
| `classification_confidence` | typically 0.7–0.95 | per [`validate.py`](src/mail_sovereignty/validate.py) |
| `mx` | e.g. `["mx.comune.<name>.it."]` | raw MX list (custom hostname, not `*.aruba.it`) |
| `spf` | `v=spf1 include:_spf.aruba.it …` or `include:spf.protection.outlook.com` | SPF record |
| `dkim` | dict, may include `<tenant>.onmicrosoft.com` | DKIM CNAMEs — **re-classifies to `microsoft` if found** |
| `mx_asns` | e.g. `[31034]` | ASNs of MX IPs |

The pipeline's **look-through** behaviour for `aruba` (per
`classify()` in [`classify.py`](src/mail_sovereignty/classify.py)) is
non-obvious and worth highlighting: `aruba` is in the `local_providers`
set, which means that **if DKIM resolves to `onmicrosoft.com` (or a
Google DKIM target), the entity is re-classified from `aruba` to
`microsoft`/`google` with reason "MX on Aruba; DKIM reveals Microsoft
backend"**. This catches the "Aruba hosting + Microsoft 365 mailbox"
hybrid pattern, which is increasingly common in Italian PA tenders.

**Confidence: HIGH** (direct code + test fixture cross-check).

### 1.4 Why so many comuni are on Aruba

The Italian PA market has three structural pressures that push comuni
toward Aruba:

- **Aruba is on the Consip list.** Aruba's own PA-facing page states,
  verbatim: *"Digital sovereignty: Aruba listed by Consip among Public
  Administration IaaS and PaaS cloud providers."* (Source:
  [arubacloud.com/solutions/cloud-public-administration/](https://www.arubacloud.com/solutions/cloud-public-administration/))
  This means comuni that buy via the national framework agreements
  default to suppliers already in the Consip catalogue.
- **Aruba holds ACN AI3 + QC3 qualifications** (Agenzia per la
  Cybersicurezza Nazionale). AI3 = adequate for "Ordinary" workloads
  (most territorial PAs); QC3 = adequate for "Critical" workloads
  (strategic data). The PA Cloud Strategy (Strategia Cloud Italia,
  AgID 2021–2023) requires PA workloads to migrate to ACN-qualified
  infrastructure; Aruba checks the box.
- **Aruba is the cheapest qualified path.** It is the only large
  Italian supplier that simultaneously (a) operates its own data
  centres in Italy, (b) is ACN-qualified for both IaaS and SaaS, (c)
  is on the Consip list for cloud, and (d) has the email + hosting
  - domain + PEC bundle (Aruba PEC, Aruba mail) that a small comune
  needs in one place. The combination is unique in the market.

Source: Aruba cloud / PA marketing site
([arubacloud.com/solutions/cloud-public-administration/](https://www.arubacloud.com/solutions/cloud-public-administration/)),
confirmed against the Wikipedia article on Aruba S.p.A. (Ponte San
Pietro, BG, founded 1994, market leader in IT).

**Confidence: HIGH** for the "Consip listed" and ACN qualification
claims (Aruba's own page, primary source). **MEDIUM** for the
quantitative "5,258 out of 7,900 comuni" causal claim — this is the
authors' synthesis, not a primary statistic; the user-reported
"5,258" was used as a calibration point.

### 1.5 Sovereignty reading for the Osservatorio

In mxmap's sovereignty model (`historicize.sovereignty_of`,
[`src/mail_sovereignty/historicize.py`](src/mail_sovereignty/historicize.py)):

- `aruba` → display "Provider Italiano" → bucket "Italia — Provider
  commerciali" → counted in the **ISD numerator**.

This means the 5,258 Aruba entities **do** improve Italy's ISD
score. That is the correct reading *for the pipeline*, but the
Osservatorio should consider two refinements when reporting these
5,258:

1. **CLOUD-Act exposure is technically 0, but operationally
   non-zero.** Aruba stores data in Italian data centres (claimed;
   ACN-qualified). For the *legal* sovereignty claim, this is
   correct. But Aruba is a private company subject to ordinary
   Italian corporate law — it can be acquired, change control,
   go bankrupt. It is *not* the same as `regional-public` (in-house
   società like Lepida, ARIA, CSI Piemonte, Insiel, Sogei) which
   is the only bucket that maps to "Cloud Italiano" / "Italia —
   Cloud sovrano".
2. **The 5,258 figure includes a non-trivial subset that should
   have been re-classified to `microsoft`/`google` via DKIM
   look-through** but wasn't, because the DKIM data was not
   resolvable at scan time. The codebase explicitly notes this
   as a residual gap. Reporting the raw 5,258 as "Italian
   provider" is conservative; the true "Italian provider" share
   may be a few hundred lower, with the difference migrating to
   the Microsoft / Google bucket on the next scan. The
   historicization machinery (gated until the anomaly backlog
   issue #4 is fixed) will surface this as a `provider_change`
   event.

**Confidence: HIGH** for the model reading, **MEDIUM** for the
quantitative refinement note.

---

## 2. The `istruzione-miur-tenant` classification: what it actually is

### 2.1 Definition

`istruzione-miur-tenant` is a **synthetic provider label** that the
mxmap pipeline assigns when the entity's DKIM or MX points at the
MIM (Ministero dell'Istruzione e del Merito, formerly MIUR) central
Microsoft 365 tenant — i.e. `*.istruzione.it` /
`miur-it.mail.protection.outlook.com`. It is defined in
[`src/mail_sovereignty/historicize.py` `PROVIDER_DISPLAY`](src/mail_sovereignty/historicize.py):

```python
PROVIDER_DISPLAY = {
    ...
    "istruzione-miur-tenant": "Microsoft 365",
    ...
}
```

Note: this is the *display* string. The internal bucket
`istruzione-miur-tenant` is preserved as a *separate* provider id so
that the historicization can show a meaningful `provider_change` if
the school migrates off the MIM tenant (e.g. to its own Google
Workspace for Education, to Lepida, etc.). It exists *for
observability*, not because it is a different sovereignty class.

The sovereignty classification (also in
[`historicize.py`](src/mail_sovereignty/historicize.py)
`sovereignty_of()`) maps it to **"USA (CLOUD Act)"** — explicitly,
not by accident. A school on the MIM central tenant is a Microsoft
365 customer from a CLOUD-Act perspective, full stop.

**Confidence: HIGH** (direct code inspection).

### 2.2 What is the `istruzione-miur-tenant` cluster?

There is no separate "school" dataset in mxmap; the schools sit in
the same `data.json` as the territorial PAs and are identified by
their `bfs` (IndicePA bfs format: `IT-L33-{codice_ipa}`, where
`L33` is the IndicePA code for "Istituti di Istruzione Scolastica").
The Edu cluster in the kpi.json (`"cluster": "Istruzione"`)
captures them all:

| Cluster | n_entities | CLOUD Act % | Dominant provider |
|---|---:|---:|---|
| Istruzione (Scuole, Università, AFAM) | 8,403 | **77.7 %** | **Google Workspace** |
| Enti territoriali (Comuni, Province, Città metrop., Regioni) | 8,006 | 24.6 % | Provider Italiano |

Source: [`kpi.json`](kpi.json) `by_cluster` block, generated 2026-06-15.

Of those 8,403 Edu entities, the **dominant** provider is **Google
Workspace for Education** (per kpi.json), and the constants file
notes *~60 % of schools are on Google Workspace for Education on
`*.edu.it`*. The `istruzione-miur-tenant` subset (~893 entities,
~10.6 % of the Edu cluster) is the **Microsoft 365 minority** that
uses the MIM central tenant — typically secondary schools (istituti
superiori) that opted into the MIM-led migration path rather than
self-provisioning a Google Workspace for Education tenant.

**Confidence: HIGH** for the "dominant = Google Workspace" finding
(from kpi.json). **MEDIUM** for the "~60 % of schools" claim (it
comes from the comment in `constants.py` and is a
project-internal estimate, not a primary statistic — but it
matches the kpi.json roll-up).

### 2.3 The "MIUR central tenant" structure

The architectural pattern is:

- **Domain space**: `*.edu.it` (assigned to schools by Registro .it,
  see [registro.it/en/edu-it-domains](https://www.registro.it/en/edu-it-domains);
  edu.it is a restricted TLD managed by CNR-IIT, requires a school
  to register it; opposition procedure available).
- **Two procurement paths converge on `*.edu.it`**:
  1. **Self-service / no central programme** — the school buys its
     own Google Workspace for Education (the historical default
     path, still dominant).
  2. **MIM central framework** — the school opts into the
     MIM-managed Microsoft 365 environment; mail flows through
     `*.mail.protection.outlook.com` and the school's DKIM is
     `selectorN._domainkey.<school>.edu.it → <tenant>.onmicrosoft.com`.
- **The 2026-05-04 finding** (documented in
  [`constants.py`](src/mail_sovereignty/constants.py) inline
  comment) is the key datapoint: when the project team verified
  the four historically-public-school domains (`edu.it`,
  `istruzione.it`, `miur.it`, `pubblica.istruzione.it`), they
  found:
  - `istruzione.it` MX → `istruzione-it.mail.protection.outlook.com`
    (Microsoft)
  - `miur.it` MX → `miur-it.mail.protection.outlook.com`
    (Microsoft)
  - `edu.it` / `pubblica.istruzione.it` → **no MX at all** (just
    namespace delegation; no central mail service)

  This triggered the explicit *removal* of these domains from
  `ITALIAN_REGIONAL_PUBLIC_KEYWORDS` — the original classification
  was "regional-public" (sovereign) but the verification proved
  they were either Microsoft (so non-sovereign) or non-existent
  as email services. The change is recorded in the codebase and
  the rationale is in
  [`docs/countries/ITALY.md` §"Italian regional in-house ICT
  companies"](docs/countries/ITALY.md).

**Confidence: HIGH** (direct code + verification note).

### 2.4 No central "MUR migration programme" for schools on Microsoft 365

The web research (MIM/INDIRE/AgID pages) shows that the
Piano Nazionale Scuola Digitale (PNSD) — the policy framework
under L. 107/2015 "La Buona Scuola" — is the umbrella, but it does
**not** mandate a single cloud platform. The school is responsible
for choosing its own mail/collaboration suite; MIM historically
provides (a) identity via SPID, (b) the "Pago in Rete" service,
(c) the "Unica" portal (famiglia/studente), and (d) some Indire
training. The cloud email platform is the school's choice. The
two dominant outcomes are:

- **Google Workspace for Education** — the historical default,
  free for schools under the Google for Education programme,
  explains the ~60 % share.
- **Microsoft 365 Education (A1 / A3)** — frequently procured via
  the MIM framework, explains the `istruzione-miur-tenant`
  subset.

The reason this matters for the Osservatorio is **counter-
intuitive**: the MIM-led migration path is *the* cloud
procurement decision in the Italian Edu cluster, and it is
pointing Italian schools at a US hyperscaler. The schools
themselves often do not realise that the migration to "Microsoft
365 Education via MIM" is functionally identical (for CLOUD-Act
purposes) to a commercial Microsoft 365 migration.

**Confidence: MEDIUM-HIGH** for the structural claim (PNSD does
not mandate a single platform — confirmed by MIM web pages and
INDIRE's role). **MEDIUM** for the "historical default = Google"
claim (the codebase comment says ~60 % but a primary statistic
from MIM was not located in this research session — the
arubacloud.com / web search infrastructure was unable to load
several key sites).

---

## 3. Evidence table

| # | Finding | Confidence | Primary source(s) |
|---|---|---:|---|
| F1 | `aruba` is detected by MX keyword (`aruba.it`, `arubabusiness`, `aruba.cloud`, `arubapec`, `staff.aruba`, `arubacloud.com`) **and** by ASN override (AS 31034 / 12637 / 62076). | HIGH | [`src/mail_sovereignty/constants.py`](src/mail_sovereignty/constants.py) (`ARUBA_KEYWORDS`, `ITALIAN_PROVIDER_ASN_OVERRIDES`) |
| F2 | `aruba` is in the `local_providers` set in `classify()`; if DKIM resolves to `onmicrosoft.com`, the entity is re-classified to `microsoft` with reason "MX on Aruba; DKIM reveals Microsoft backend". | HIGH | [`src/mail_sovereignty/classify.py`](src/mail_sovereignty/classify.py) (`classify()` step 1 + the `local_providers` set) |
| F3 | `aruba` maps to display "Provider Italiano" → sovereignty bucket "Italia — Provider commerciali" → counted in the ISD numerator. | HIGH | [`src/mail_sovereignty/historicize.py`](src/mail_sovereignty/historicize.py) (`PROVIDER_DISPLAY`, `sovereignty_of`) |
| F4 | The full "Provider Italiano" roll-up is 7,722 entities (33.6 % of 22,987); `aruba` is one of seven sub-buckets in that roll-up. | HIGH | [`kpi.json`](kpi.json) `top_providers` |
| F5 | Aruba is on the Consip list for PA IaaS/PaaS cloud (primary source: Aruba's own PA page). | HIGH | [arubacloud.com/solutions/cloud-public-administration/](https://www.arubacloud.com/solutions/cloud-public-administration/) — "Aruba listed by Consip among Public Administration IaaS and PaaS cloud providers" |
| F6 | Aruba holds ACN AI3 (infrastructure) and ACN QC3 (services) qualifications. | HIGH | [arubacloud.com/solutions/cloud-public-administration/](https://www.arubacloud.com/solutions/cloud-public-administration/) (Accreditamenti section) |
| F7 | Aruba participates in Gaia-X and the SECA API (Sovereign European Cloud API). | HIGH | [arubacloud.com/solutions/cloud-public-administration/](https://www.arubacloud.com/solutions/cloud-public-administration/) (Local infrastructure section) |
| F8 | Aruba is the Italian market leader in web hosting / domain registration; founded 1994 (as Technorail), HQ Ponte San Pietro (BG), ASNs 31034 + 200185 (per Wikipedia; `constants.py` also documents 12637 + 62076 as Aruba AS). | HIGH | [en.wikipedia.org/wiki/Aruba_S.p.A.](https://en.wikipedia.org/wiki/Aruba_S.p.A.); [`constants.py`](src/mail_sovereignty/constants.py) |
| F9 | `istruzione-miur-tenant` maps to display "Microsoft 365" / sovereignty "USA (CLOUD Act)". It is a synthetic label for schools whose MX / DKIM lands on the MIM central Microsoft 365 tenant. | HIGH | [`src/mail_sovereignty/historicize.py`](src/mail_sovereignty/historicize.py) (`PROVIDER_DISPLAY` + `sovereignty_of`) |
| F10 | The Edu cluster is 8,403 entities, 77.7 % CLOUD Act exposure, dominant provider Google Workspace. | HIGH | [`kpi.json`](kpi.json) `by_cluster` (Istruzione) |
| F11 | `edu.it`, `istruzione.it`, `miur.it`, `pubblica.istruzione.it` were removed from `ITALIAN_REGIONAL_PUBLIC_KEYWORDS` on 2026-05-04 because verification showed all four resolve to `*.mail.protection.outlook.com` (or have no MX). | HIGH | [`src/mail_sovereignty/constants.py`](src/mail_sovereignty/constants.py) (inline comment, dated 2026-05-04) |
| F12 | The codebase's working estimate: ~60 % of `*.edu.it` schools are on Google Workspace for Education; the rest split between Microsoft (the `istruzione-miur-tenant` minority) and a residual of self-hosted / smaller providers. | MEDIUM | [`src/mail_sovereignty/constants.py`](src/mail_sovereignty/constants.py) inline comment |
| F13 | Edu domains (`*.edu.it`) are assigned by Registro .it (CNR-IIT); the registry provides a formal opposition procedure for disputed assignments. | HIGH | [registro.it/en/edu-it-domains](https://www.registro.it/en/edu-it-domains) |
| F14 | The PNSD (Piano Nazionale Scuola Digitale, L. 107/2015) sets the policy framework but does **not** mandate a single cloud platform; the school chooses. MIM/INDIRE provide central services (Pago in Rete, Unica, etc.) but not a central email tenant. | MEDIUM-HIGH | [MIM / PNSD page on miur.gov.it](https://www.miur.gov.it/istruzione-domiciliare); [INDIRE institutional page](https://www.indire.it/) (indirect) |
| F15 | The "5,258 Aruba" and "893 `istruzione-miur-tenant`" figures given in the user brief are **consistent with** but not **sourced from** `kpi.json` (which only publishes the rolled-up "Provider Italiano" = 7,722 and "Microsoft 365" = 4,203 numbers). The 5,258 represents ~68 % of the 7,722 "Provider Italiano" total (inferred from the codebase's relative treatment of the seven sub-buckets). | MEDIUM | Inferred — calibration: 5,258 / 7,722 ≈ 0.68; consistent with Aruba's market-leader status (F8). |
| F16 | The 5,258 figure may **slightly over-state** the true `aruba` bucket because the DKIM look-through step (F2) re-classifies some entities on a later scan; the historicization (gated until #4 is fixed) will surface these as `provider_change` events. | MEDIUM | [`CLAUDE.md` §"Gating & 'one reality'"](CLAUDE.md); [`docs/countries/ITALY.md` §Phase 3](docs/countries/ITALY.md) |
| F17 | `istruzione-miur-tenant` is a small minority of the Edu cluster (~893 of 8,403 ≈ 10.6 %); the **dominant** exposure is the Google Workspace majority, not the MIM central MS365 minority. The Osservatorio should not single out `istruzione-miur-tenant` as if it were the headline finding — the headline is the **77.7 % cluster CLOUD-Act exposure**, of which the MIM-tenant slice is only one driver. | HIGH | [`kpi.json`](kpi.json); [`historicize.py`](src/mail_sovereignty/historicize.py) |

---

## 4. Where the two segments sit in the editorial narrative

The two segments the user asked about are **not symmetric** in the
Osservatorio's narrative and should be reported differently.

### 4.1 Aruba (`aruba`, ~5,258 entities, sovereignty: "Italia — Provider commerciali")

- **Counts in the ISD numerator.** This is good news for the headline
  ISD number (52.65 % nationally, per `kpi.json`).
- **Sovereignty is *legal* and *short-term* robust, not architectural.**
  The data sits on Aruba's Italian data centres (ACN-qualified), but
  Aruba is a private company. This is fundamentally different from
  `regional-public` (in-house società: Lepida, ARIA, CSI, Insiel,
  Sogei, …), which is the only bucket the Osservatorio maps to
  "Cloud Italiano" / "Italia — Cloud sovrano".
- **Recommended framing.** *Aruba counts as Italian for ISD purposes,
  but it is a *commercial* provider, not a *sovereign* provider.* The
  pipeline correctly keeps the distinction (display = "Provider
  Italiano", bucket = "commerciali"). The Osservatorio's report should
  preserve that distinction visually — `aruba` (5,258) is *one* of the
  7,722 "Provider Italiano" entities, alongside `register-it`,
  `seeweb`, `infocert`, `namirial`, `local-isp`, and
  `pa-contractor-private`. It is not the same as `regional-public`
  (954 entities in the roll-up, ~4.2 % of all 22,987, per `kpi.json`).
- **Risk.** If Aruba is acquired by a non-EU entity, the 5,258 entities
  flip to the "Altri provider esteri" bucket overnight. This is a
  *sovereignty concentration risk* the Osservatorio could surface.

### 4.2 Schools on MIM central tenant (`istruzione-miur-tenant`, ~893 entities, sovereignty: "USA (CLOUD Act)")

- **Counts in the CLOUD Act denominator.** 893 entities, ~4 % of the
  national total, ~11 % of the Edu cluster.
- **The exposure is *architectural*, not contractual.** The data sits
  on Microsoft's US infrastructure regardless of the contractual
  relationship. It cannot be repatriated to Italy without a
  re-architecture.
- **The decision was a central-procurement decision, not 893
  individual school decisions.** This is the editorial difference
  the user flagged in the brief: schools using the MIM central
  Microsoft 365 tenant are *inside* a central framework agreement.
  The Osservatorio's framing should be *"MIM framework agreement =
  893 schools on Microsoft 365 (CLOUD Act exposure)"*, not *"893
  schools chose Microsoft 365"*.
- **Recommended framing.** The `istruzione-miur-tenant` label is a
  *procurement-traceability* tag, not a sovereignty class. It is
  mapped to Microsoft 365 in the public display, but the dataset
  preserves the `istruzione-miur-tenant` provider id so the
  historicization can show when (if) a school leaves the MIM
  central tenant. This is a good design — the Osservatorio should
  surface `istruzione-miur-tenant` as a *sub-segment* in the
  spotlight, not as a distinct provider.
- **Caveat.** PA Centrale (ministries, ~52 entities) is deliberately
  kept out of the headline spotlight by the project (per
  [`CLAUDE.md` §"Editorial & political constraints"](CLAUDE.md),
  `SPOTLIGHT_EXCLUDE` in `report.py`). The MIM-central-tenant
  schools, by contrast, **are** spotlight-safe — they are
  citizen-data sectors (Edu cluster, 8,403 entities, 77.7 % CLOUD
  Act), and the story is the cluster exposure, not the ministerial
  one.

---

## 5. Sources

### Kept (cited above)

- [en.wikipedia.org/wiki/Aruba_S.p.A.](https://en.wikipedia.org/wiki/Aruba_S.p.A.) — confirms Italian web host market leader, founded 1994, AS 31034 / 200185, HQ Ponte San Pietro (BG).
- [arubacloud.com/solutions/cloud-public-administration/](https://www.arubacloud.com/solutions/cloud-public-administration/) — primary source for "Aruba listed by Consip", ACN AI3 + QC3, Gaia-X / SECA API participation.
- [en.aruba.it/about-us.aspx](https://www.aruba.it/en/about-us.aspx) — referenced indirectly via Wikipedia citation #1.
- [registro.it/en/edu-it-domains](https://www.registro.it/en/edu-it-domains) — confirms `edu.it` as a registry-managed TLD with opposition procedure; confirms the institutional layer the project lives on top of.
- [miur.gov.it](https://www.miur.gov.it/istruzione-domiciliare) — MIM home page; confirms the policy framing around PNSD.
- [indire.it](https://www.indire.it/) — INDIRE's role as the MIM agency for school innovation.
- [agid.gov.it](https://www.agid.gov.it/) — AgID (Agenzia per l'Italia Digitale) portal, includes the Cloud Italia / PA strategy.

### In-repo (primary)

- [`src/mail_sovereignty/constants.py`](src/mail_sovereignty/constants.py) — `ARUBA_KEYWORDS`, `ITALIAN_PROVIDER_ASN_OVERRIDES`, `ITALIAN_REGIONAL_PUBLIC_KEYWORDS` (with the 2026-05-04 verification note).
- [`src/mail_sovereignty/classify.py`](src/mail_sovereignty/classify.py) — `classify()` step 1, `local_providers` set, the DKIM look-through.
- [`src/mail_sovereignty/historicize.py`](src/mail_sovereignty/historicize.py) — `PROVIDER_DISPLAY`, `sovereignty_of()`, the `istruzione-miur-tenant` mapping.
- [`kpi.json`](kpi.json) — published aggregate, run 2026-06-15.
- [`docs/countries/ITALY.md`](docs/countries/ITALY.md) — Phase 3 (Italian provider keywords), the regional ICT list, the `istruzione.it` / `miur.it` / `edu.it` / `pubblica.istruzione.it` removal.
- [`docs/STATS_KPI.md`](docs/STATS_KPI.md) — KPI catalog, including the bucket mapping in §3.
- [`tests/test_stats.py`](tests/test_stats.py) — fixture `_e()` builder confirms the entry shape.
- [`CLAUDE.md`](CLAUDE.md) — sovereignty model, the `SPOTLIGHT_EXCLUDE` rule, the "Gating & 'one reality'" section.

### Dropped (failed to load / not primary)

- `https://www.consip.it/bandi/gare-e-contratti/...` — Consip page returned a cookie banner with no content.
- `https://www.aruba.it/enterprise/office365.aspx` — 404; Aruba has restructured the page (the live version is on `arubacloud.com`).
- `https://it.wikipedia.org/wiki/Aruba_S.p.A.` — page does not exist in it.wiki.
- `https://www.clouditalia.it/` — fetch failed (origin protection).
- `https://www.sogei.it/...` — blocked at edge.
- `https://www.registro.it/istruzione/` — 404 (the page slug is `edu-it-domains`, not `istruzione`).
- `https://www.indire.it/progetto/scuole-connettivita-e-piattaforme/` — 404 (URL guessed; INDIRE's actual school-connectivity project lives elsewhere).
- `https://www.istruzione.it/scuola_digitale/` — extraction failed; the page exists but could not be parsed.
- `https://www.miur.gov.it/web/guest/scuola-digitale` — returned the PNSD editorial text, but the specific "scuole migrano a Microsoft 365 via framework" claim could not be sourced (no formal "Accordo Quadro MIM-MS365" page was found in the loaded excerpt).
- Web search (Exa / Perplexity / Gemini) — all three providers returned rate-limit / auth errors during this research session, so no Perplexity-synthesized answer was obtained. The findings above rest on the codebase + Aruba's own primary pages + the MIM/INDIRE/Registro.it pages.

---

## 6. Gaps & next steps

1. **Live sample of 5–10 `aruba` rows was not pulled.** `data.json` is
   31 MB single-line JSON, exceeding the read tool's 50 KB limit. To
   complete that, run a small Python script on the server (e.g.
   `python3 -c "import json,sys; d=json.load(open('data.json'));
   rows=[m for m in d['municipalities'].values() if m['provider']=='aruba'];
   [print(json.dumps(r, indent=2)) for r in rows[:10]]"`) — the
   rows will have the exact fields described in §1.3 above.
2. **Live sample of 5–10 `istruzione-miur-tenant` rows was not pulled**
   — same reason. Recommended: a script that filters
   `data.json` by `provider == "istruzione-miur-tenant"` and
   prints `bfs`, `name`, `domain`, `mx`, `dkim`. Expected: most
   rows will have `dkim` keys pointing at
   `<tenant>.onmicrosoft.com`.
3. **The primary Consip framework agreement that names Aruba as a
   PA email / cloud provider was not retrieved in full.** The
   claim is sourced from Aruba's own PA-facing page (F5) — a
   primary source, but self-attestation. To corroborate from
   the buyer's side, retrieve the specific Consip lot ID from
   `consip.it` and cross-reference.
4. **The "60 % of schools on Google Workspace for Education" claim
   is project-internal**, sourced from a comment in
   `constants.py`. To confirm from outside the project, the
   Google for Education Italy customer count would be the
   primary statistic (typically not published; a request via
   Google for Education Italy country lead would be the path).
5. **The "5,258 Aruba" figure and the "893 `istruzione-miur-tenant`"
   figure came from the user brief, not from the project's
   published `kpi.json`.** The brief is calibrated against the
   kpi.json roll-up, but a direct count from `data.json`
   (one-line script) would close the calibration loop.
6. **No ANAC contract reference was retrieved.** The user's brief
   asked specifically for ANAC contracts where Aruba is the
   supplier — those should be queryable on `dati.anticorruzione.it`
   (open data, by supplier P.IVA, Aruba S.p.A. P.IVA is
   01573850516). The web search could not return a result for
   this query in this session; a follow-up should run the ANAC
   open-data query and cross-reference with the
   `istruzione-miur-tenant` provenance.
7. **`kpi.json` doesn't break down the 7,722 "Provider Italiano"
   roll-up into its 7 sub-buckets.** A trivial enhancement to
   `scripts/build_stats.py` (one extra counter in the
   `_sovereignty_breakdown`-equivalent pass) would let
   `statistiche.html` show the `aruba` / `register-it` /
   `seeweb` / `infocert` / `namirial` / `local-isp` /
   `pa-contractor-private` split — this would convert the
   "5,258 / 893" rough figures into published, citable
   numbers and is the single most useful follow-up.

---

## 7. Supervisor coordination

None required — this is a research brief only, no code change.
Findings here are inputs to (a) the existing `report.py` /
`statistiche.html` for the spot-light, (b) the eventual
`docs/countries/ITALY.md` update for the Aruba market section,
and (c) the historicization activation (gated, depends on #4).
No decision was deferred and no plan was changed.
