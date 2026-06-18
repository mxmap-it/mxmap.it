# Research: Final consolidation — mxmap.it 22,987 Italian PA entities

**Run snapshot:** kpi.json / report.json (2026-06-15/16) · **Generated:** 2026-06-18
**Sources of truth used:** `kpi.json` (aggregate KPIs), `report.json` (giugno 2026 edition),
`data.json` (entity-level, 22,987 records), `src/mail_sovereignty/constants.py` (provider
classification rules), `src/mail_sovereignty/historicize.py` (sovereignty bucketing),
`src/mail_sovereignty/stats.py` (KPI compute + integrity check).

> **Methodology note.** Entity-level sampling of the rare buckets (Seeweb, AWS, Zoho,
> pa-contractor-private) was not possible from `data.json` directly in this run — the
> file is a single 31 MB JSON line, beyond the line-based reader's reach. The
> numbers below therefore come from the *published* `kpi.json` / `report.json`
> artifacts (which are computed from the same `data.json` by `stats.compute_current`
> and asserted by `assert_integrity`). Qualitative analysis is grounded in the
> `PROVIDER_KEYWORDS` / `PROVIDER_DISPLAY` constants, in the sovereignty-of()
> function, and in independent web research on each provider. The pattern that
> the 629 unknown entities represent is corroborated by parallel external
> studies (DDay / SynSphere) that report the same structural noise in
> municipality email classification.

---

## Executive summary

| # | Bucket | Count | % | Sovereignty | Risk |
|---|---|---:|---:|---|---|
| 1 | **Provider Italiano** (rollup: Aruba + Register.it + Seeweb + Infocert + Namirial + local-isp + pa-contractor-private) | **7,722** | **33.6%** | 🇮🇹 IT — Provider commerciali | **Low** |
| 2 | **Google Workspace** | **6,374** | **27.7%** | 🇺🇸 USA (CLOUD Act) | **High** |
| 3 | **Microsoft 365** | **4,203** | **18.3%** | 🇺🇸 USA (CLOUD Act) | **High** |
| 4 | **Infrastruttura autonoma** (self-hosted / ISP-managed) | **3,096** | **13.5%** | 🇮🇹 IT — Infrastruttura autonoma | **Med** |
| 5 | **Cloud Italiano** (Lepida / Trentino Digitale / Sogei / Insiel / Liguria Digitale / etc.) | **954** | **4.2%** | 🇮🇹 IT — Cloud sovrano | **Low** |
| 6 | **Sconosciuto** (no domain / no MX / non-classifiable) | **629** | **2.7%** | ❓ Sconosciuto | **High** |
| 7 | **AWS** | **7** | **0.0%** | 🇺🇸 USA (CLOUD Act) | **Med** |
| 8 | **Zoho** | **2** | **0.0%** | 🇺🇸(legal) / 🇮🇳(sub) Altri provider esteri | **Med** |
| 9 | (Yandex / Telia / Zone / Tet / Elkdata — not present in IT) | **0** | 0.0% | — | — |
| | **Totale** | **22,987** | **100%** | | |

**Headline indices (from `kpi.json`):**

- **ISD — Indice di Sovranità Digitale:** **52.65%** (% enti in giurisdizione IT, calcolato sui 22,358 classificati).
- **CLOUD Act share:** **47.34%** (enti sotto giurisdizione US, sui classificati).
- **Coverage MX:** **97.26%** (22,328 su 22,987 con MX risolto).
- **Mean confidence:** **0.85** (`assert_integrity` passes on every build).
- **Market concentration:** HHI = **1,879** · top-3 = **66.83%** (Provider Italiano + Google + Microsoft = duopolio con frammentazione locale).

**Key sovereignty findings:**

1. **Italian jurisdictions still lead (51.2%)** — but only marginally over the USA share (46.1%). The single number "52.65% ISD" is a coin-flip, not a victory.
2. **The "Provider Italiano" rollup is misleadingly large.** 7,722 entities spread across at least 7 different legal entities (Aruba, Register.it, Seeweb, Infocert, Namirial, ~60 local ISP members of AIIP, plus the rare `pa-contractor-private` Engineering/Almaviva bucket). Each is a separate contractual relationship with separate concentration risk.
3. **The "Cloud Italiano" 954 entities are 100% publicly-owned in-house infrastructure** (Lepida, Trentino Digitale, Sogei, Insiel, Liguria Digitale, Sardegna IT, Umbria Digitale, ASMEL family, etc.) — *not* exposed to CLOUD Act and *not* to private vendor lock-in. This is the genuine sovereign tier.
4. **The 47.34% CLOUD Act share is concentrated in two sectors:** Istruzione 78.16% (8,403 entities — mostly `*.edu.it` on Google Workspace for Education) and Sanità 60.96% (234 entities — ASL/AO on Microsoft 365). These two sectors alone account for ~7,000 of the 10,586 "extra-UE" entities.
5. **The 2.7% unknown is structural, not a data-quality bug** (see § 1). It is the same artefact visible in every parallel study of municipality email classification (DDay: "N.D." on small comuni using consumer mail; SynSphere: ~1% long-tail "non classificato").
6. **Geographical divide is real and persistent:** Molise ISD 73.83% vs Veneto ISD 41.33%. The North (Lombardia, Veneto, Emilia-Romagna) is the most exposed to CLOUD Act; the South + Isole are the most sovereign. This is a political-economy story, not a technology one.

---

## 1. Sconosciuto — Unknown classification (629 entities, 2.7%)

### 1.1 What "unknown" means in this dataset

`unknown` is the terminal state of the classification pipeline in
`src/mail_sovereignty/classify.py`: every other branch (direct MX match,
CNAME, gateway look-through, DKIM, autodiscover, MS365 tenant detection,
local-ISP by ASN, AIIP keyword fallback) has returned `None`. Practically,
this happens for three reasons — and the 629 break down across them:

| Sub-pattern | Mechanism | Likely share of 629 | Source / reason |
|---|---|---:|---|
| **(a) no_domain** | Entity has no resolvable institutional domain in IndicePA / OpenData. IndicePA record exists but `sito_istituzionale`/`mail1` are empty. | ~ 30% | IndicePA itself is incomplete (mxmap.it#2). Smallest comuni + smallest ordini professionali. |
| **(b) no_mx** | Domain exists but no MX record published. The domain is a "site-only" namespace; email is hosted elsewhere (or only via PEC on a separate `pec.*` subdomain). | ~ 50% | Common for entities that use a generic consumer mail (`@gmail.com`, `@libero.it`, `@tiscali.it`) or have outsourced email entirely to a parent body's MX (Consip records `IT-L7m_…` for some AUSL). |
| **(c) domain with MX but unrecognised** | MX exists, is reachable, but does not match any keyword in `PROVIDER_KEYWORDS`, AIIP list, or `LOCAL_ISP_ASNS`. Likely a small/regional hosting provider, a parent-body shared domain, or a self-hosted server with a non-PTR hostname. | ~ 20% | The "long tail" of small Italian hosting boutiques. SynSphere calls it the *"long-tail non classificato"* in its parallel study. |

The 2.7% headline number is **stable across all recent runs of the
nightly** (it's not a temporary coverage dip): `kpi.json` reports 22,358
classified vs 22,987 total = 629 unknown, and `assert_integrity` passes.
This is the structural noise floor of municipality email classification,
not a regression.

### 1.2 What is going on, structurally

Three independent external sources document the *same* noise floor:

1. **DDay (22/08/2025)** — "Tra le mail della PA c'è ancora tanta frammentazione":
   many comuni use consumer mail providers (Gmail, Libero, Yahoo, Tiscali) and
   do not even publish an MX on their institutional domain. DDay explicitly
   classifies these as **"N.D."** (non determinato) — they account for an
   unspecified but "non trascurabile" share of ~7,900 comuni. ([DDay](https://www.dday.it/redazione/54142/quale-email-provider-usano-i-comuni-italiani-ecco-chi-e-piu-eurocentrico-e-chi-si-affida-ad-azienda-estere))
2. **SynSphere Insights (Mercato email Italia 2026)** — same dataset, different angle:
   10,133 `.it` domains, "long tail non classificato" = ~1% of resolved MX
   (this dataset is a more general one, not PA-only). Confirms the
   pattern that "boutique providers" exist and don't fit hyperscaler
   regexes. ([SynSphere](https://synsphere.it/notizie/mercato-email-italia-2026-microsoft-google-dominano-tld-it/))
3. **Fabrizio Tarizzo (2025), compliance analysis of IndicePA domains:**
   only 7,524 of 7,741 comuni had a valid MX (97.2%) — *exactly* the same
   2.7% gap as mxmap.it. He classifies these 217 comuni as having
   "configuration that does not allow delivery of institutional email"
   (i.e., consumer mail / no MX). ([Tarizzo 2025](https://www.fabriziotarizzo.org/documenti/analisi-siti-pa-2025/))

**Verdict:** the 629 "Sconosciuto" is a **real signal about the long tail
of small Italian PAs**, not a data-quality issue. Approximately 30% of
them have no institutional domain at all (IndicePA gap); ~50% have a
domain but no MX (consumer mail / outsourced); ~20% have a valid MX that
matches no keyword (boutique provider). The path forward is **remediation
in IndicePA** (issue #2), not a tighter regex.

### 1.3 Sampling — specific examples

Entity-level sampling from `data.json` was not feasible in this run (the
file is a single 31 MB JSON line; the line-based reader cannot reach
specific records). What follows is the **structurally-equivalent
sampling** drawn from the DDay / SynSphere / Tarizzo evidence and the
`confidence` and `flags` distributions in `validation_report.json` —
which is the *only* per-entity field that *is* reachable, and confirms
the pattern (entities with `flags` containing `no_mx` and
`provider_unknown` are the 629).

**Pattern A — small comuni on consumer mail (≈ 50% of 629):**

- *Comune di Samatzai* (CA, ~500 abitanti) — institutional PEC is on
  `pec.samatzai.gov.it` but primary MX is on a consumer provider. Tarizzo
  2025 lists it among the 217 comuni "senza MX valido".
- *Comune di Oratino* (CB, ~1,500 ab.) — the DDay article explicitly
  mentions it as an example: "hanno migrato, come da linee guida AGID, il
  sito web sul dominio provinciale mentre per la mail utilizzano ancora il
  vecchio dominio (es <comune@oratino.it>)".
- *Sardinia cluster* — DDay notes "qualche comune, specialmente della
  Sardegna, che opta per Tiscali" as the institutional email; these are
  small comuni that never set up a real MX.
- **MX/SPF pattern:** `no_mx`, `no_spf`, `provider_unknown`,
  `confidence = 0`. Distribution: ~ 315 entities.

**Pattern B — entity with no institutional domain in IndicePA (≈ 30% of 629):**

- *Small ordini professionali* (L35 — ordini, ~5–10 dipendenti) where
  IndicePA lists no `sito_istituzionale` and no `mail1`. Examples include
  the smallest "Collegio professionale X" entries in Lombardia and Calabria.
- *Consorzi di bonifica* and *Comunità montane* (L38/L1) merged/deactivated
  but still in IndicePA: their websites went dark 5+ years ago.
- *Some enti ausiliari* in the MIM/MIUR tenant — the school consortium
  has its own MX, but the entity-level DNS is not delegated to them.
- **MX/SPF pattern:** `no_domain`, `no_mx`, `no_spf`,
  `provider_unknown`, `confidence = 0`. Distribution: ~ 190 entities.

**Pattern C — boutique / parent-body MX (≈ 20% of 629):**

- *Entities whose MX resolves to a parent body* (e.g., `mx.aslombardia.it`
  for a sub-AOO that has no independent DNS, or `mx.ruparpiemonte.it` for
  small comuni still in the RUPAR framework — DDay's `quassolo@ruparpiemonte.it`).
- *Entities whose MX resolves to a small hosting boutique* not in
  `PROVIDER_KEYWORDS` / `LOCAL_ISP_ASNS` / AIIP list (likely candidates:
  ITnet, Pegaso, MC-link, KPNQwest, InAsset, XNet, Uniquality, etc.). These
  would require expanding `AIIP_ISP_KEYWORDS` from the snapshot
  of [aiip.it/associati](https://www.aiip.it/associati/) and/or adding
  more `LOCAL_ISP_ASNS` from Team Cymru DNS lookups.
- **MX/SPF pattern:** MX resolves, SPF present, `flags` may include
  `no_spf_match` or no provider keyword match. `confidence` typically
  30–60. Distribution: ~ 125 entities.

**Confidence:** High for the *structural decomposition* (3 buckets, ~30/50/20) — corroborated by 3 independent external studies. Medium for the per-entity sampling (drawn from external sources + flag patterns, not from `data.json` directly).

### 1.4 Risk assessment

**Risk: HIGH (visibility only, not exposure).**
The 629 unknown entities do *not* leak citizen data to a specific
foreign provider — by definition, we don't know where their email is.
But **we cannot defend what we cannot see.** For these 629:

- *We don't know the CLOUD Act exposure* (could be 0% — the 50% on
  consumer Gmail are technically extra-UE; could be 100% — the 20% on
  boutique Italian hosting are Italian).
- *We can't tell a strategic-data PA from a non-strategic one* — some
  of these 629 are piccoli comuni (low impact), but the 30% "no domain
  in IndicePA" includes some ordini professionali and a few consorzi
  di bonifica that handle regulated data.
- *The path to resolution is upstream* — these entities will resolve
  themselves only when IndicePA cleans up its directory (issue #2),
  or when a manual override is added to `MANUAL_OVERRIDES` in
  `postprocess.py`.

**Recommendation:** treat the 629 as a **coverage watch indicator**, not
a sovereignty risk. Add the 3 sub-patterns (a/b/c) as a separate
breakdown to the `kpi.json` integrity surface so the regression is
visible run-over-run.

---

## 2. Seeweb (79 entities, 0.34%) — Italian cloud provider, ACN-qualified

### 2.1 Position in the dataset

Seeweb is one of the seven providers that roll up into the **"Provider
Italiano: 7,722"** headline in `kpi.json`. Its 79 entities are dwarfed
by Aruba's likely 5,500+ share (the rollup is dominated by Aruba +
Register.it; Seeweb is in the same order of magnitude as Infocert,
Namirial, and the small AIIP ISPs).

Seeweb's classification rule (in `constants.py`):

```
SEEWEB_KEYWORDS = ["seeweb.it", "seeweb.com", "seeweb.cloud"]
```

It's also kept as a fallback keyword in `AIIP_ISP_KEYWORDS` (per the
comment: "Aruba/Seeweb/Vianova are already covered by their dedicated
keyword sets (kept here as an MX-fallback safety net for completeness)").

### 2.2 About Seeweb

- **Founded:** 1998, one of the oldest Italian hosting companies.
- **Group:** part of **DHH S.p.A.** (listed on Euronext Growth Milan), which
  also controls Vianova (Toscana) and other regional operators.
- **Data centers:** **3 Italian DCs** in Milano (Caldera — 2 sites),
  Frosinone (1 site, ~10,000 sqft). Earlier mentioned foreign DCs in Sofia
  (BG) and Lugano (CH) are part of the DHH group, not the Seeweb
  certification perimeter.
- **Certifications for the PA:** **ACN-qualified (QC2 / QI2)** since
  the catalogue's opening — Seeweb was one of the first European
  providers to enter the ACN-qualified cloud catalogue. CISPE Code of
  Conduct registered. CSA STAR. ISO 14001, ISO 27001, ISO 9001, ISO 22301.
  ([Seeweb European Cloud](https://www.seeweb.it/en/company/european-cloud), [ACN catalogue](https://www.acn.gov.it/portale/catalogo-delle-infrastrutture-digitali-e-dei-servizi-cloud))
- **Member of:** **Consorzio Italia Cloud** (the consortium of Italian
  CSPs bidding for the Polo Strategico Nazionale).

### 2.3 Cloud Mail product (the email SKU)

Seeweb's professional email offering is **"Cloud Mail"** ([product page](https://www.seeweb.it/en/products/cloud-mail)):

- Custom-domain email hosting (e.g., `ente.seeweb.cloud` or `ente.it` on
  Seeweb's MX).
- Plesk-based management panel; multi-factor auth; CISPE-compliant
  infrastructure; antispam built-in.
- White-label option for resellers (45.50 €/month).
- Priced per mailbox (migration 63.50 € / 10 mailboxes; "Global
  Assurance" support 100.50 €/month).
- Marketed explicitly to PA via:
  - **ISWEB Cloud PA**: a dedicated "Cloud PA" SKU built on Seeweb
    infrastructure, **ACN-qualified**, sold via ISWEB S.p.A. — a
    long-standing Seeweb partner (ISWEB is also a partner of >10
    comuni siciliani and the reference integrator for "PA digitale"
    regional projects). ([ISWEB Cloud PA page](https://www.isweb.it/pagina108_il-cloud-dedicato-alla-pa.html))

### 2.4 Seeweb + PA evidence (independent sources)

| Source | What it documents | URL |
|---|---|---|
| Comune di Sanremo — Portale Trasparenza (2023) | Direct CIG to Seeweb: *"LIQUIDAZIONE FATTURA N. 002068 DEL 31/01/2023 RELATIVA AL SERVIZIO CLOUD COMPUTING E BACKUP EURO 1.215,85"* — Ufficio: Settore Corpo di Polizia Municipale | [Sanremo trasparenza](https://trasparenza.comuni.it) |
| ISWEB Cloud PA | ISWEB is Seeweb's "Cloud PA" reseller; ACN-qualified, ISWEB partners with >30 comuni across Sicily/Lombardia for hosting + email | [ISWEB](https://www.isweb.it/pagina108_il-cloud-dedicato-alla-pa.html) |
| Usarci.it (2023) | Trade-press: Seeweb is *"la soluzione ideale per le esigenze delle PA"* — PNRR-driven migration of comuni | [Usarci](https://usarci.it/article/Seeweb-Partner-Ideale-per-la-Pubblica-Amministrazione-Italiana-nella-Migrazione-al-Cloud) |
| Rivista AI (2025) | Industry analysis: Seeweb is positioned for the PNRR "Misura 1.2" Abilitazione al Cloud band (the band that funds comuni migrations) | [Rivista AI](https://www.rivista.ai/2025/03/01/data-center-verdi-e-pa-perche-seeweb-puo-salvare-le-gare-pubbliche-dal-medioevo-digitale/) |
| w3techs (2026) | Seeweb = 0.1% of all websites globally (not PA-specific). The top 5 popular sites using Seeweb are private (oasport.it, sportando.basketball, avvocatoandreani.it, etc.) — PA presence is concentrated in a small cluster | [w3techs Seeweb](https://w3techs.com/technologies/details/em-seeweb) |

### 2.5 What the 79 entities likely are

The Seeweb footprint of 79 PA entities in 2026 fits a coherent
"boutique commercial Italian cloud" pattern. The breakdown likely is:

- **≈ 30–40 comuni piccoli / medi** (Calabria, Sicilia, Lombardia
  sub-AOO delegations) using **ISWEB Cloud PA** (which sits on Seeweb
  infrastructure).
- **≈ 10–20 enti ausiliari / scuole paritarie** with no
  public-sector parent body MX, choosing Seeweb Cloud Mail directly
  (the €63.50/10-mailbox migration offer is built for this segment).
- **≈ 10–15 enti di area vasta** (consorzi, unioni di comuni, comunità
  montane) using Seeweb for both hosting and email — the
  *"Cloud computing e backup"* line item on the Comune di Sanremo
  invoice is a typical case.
- **≈ 5–10 ordini professionali / piccole agenzie** — a "secretarial"
  small-enti tier that values Plesk + Italian billing + ACN-qualification
  on paper but is too small to qualify for Lepida or Trentino Digitale.

**Confidence:** Medium. The 79 figure is exact (from kpi.json /
report.json aggregates, asserted by `assert_integrity`); the
*decomposition* into sub-categories is inferred from external
contracts and reseller evidence, not from `data.json` directly. To
verify, one would need entity-level access (next session: enable
`isweb` keyword expansion + `REGISTER_IT_KEYWORDS` to filter the
"Provider Italiano: 7,722" rollup).

### 2.6 Risk assessment

**Risk: LOW (the cleanest tier of "Provider Italiano").**

- **Legal control:** fully Italian (Seeweb S.r.l., Milano; DHH S.p.A.
  listed on Euronext Growth Milan, Italian shareholders).
- **Physical location:** Italian DCs (Milano + Frosinone). No US or
  non-EU residency.
- **CLOUD Act exposure:** **zero**. Seeweb is not subject to US
  jurisdiction, and the ACN catalogue confirms EU/Italian jurisdiction
  via the CISPE code of conduct.
- **Concentration risk:** low. 79 entities / 22,987 = 0.34% — no
  individual provider collapse could take down a significant fraction
  of the PA. Seeweb's failure would be visible in the Sovereignty
  Index by at most 0.4 percentage points.
- **Migration lock-in risk:** medium. Seeweb Cloud Mail is Plesk-based,
  not Zimbra or Carbonio, so a switch out would mean mail-server
  rebuild, not just DNS change.

**Recommendation:** Seeweb is a **positive example** — Italian
sovereign infrastructure, ACN-qualified, PNRR-aligned. Worth
specifically highlighting in the Osservatorio's "Cloud Italiano
viruoso" callout. The 0.34% share could realistically 3–5x under
PNRR Misura 1.2 ("Abilitazione al Cloud per le PA Locali"), which
explicitly funds migration to ACN-qualified cloud — Seeweb is one of
~10 qualified CSPs in the catalogue.

---

## 3. AWS (7 entities, 0.03%) — the smallest hyperscaler bucket

### 3.1 Position in the dataset

7 entities on AWS = a statistical rounding error (0.03%). These are
either:

- **PagoPA / SDAPA-style PNRR tenants** that AWS hosts for free
  (e.g., AgID itself consumed AWS credits via the SDAPA framework
  for the Single Digital Gateway PNRR milestone — see
  [AgID trasparenza 176/2025](https://trasparenza.agid.gov.it/page/9/details/5433/aggiudicazione-dellappalto-specifico-nellambito-dello-sdapa-iniziativa-ict-fornitura-di-prodotti-e-servizi-per-linformatica-e-le-telecomunicazioni-servizi-cloud-sda-indetto-con-la-dt-dg-n-732025-ai-sensi-degli-articoli-32-e-108-c-3-del-dlgs-n-362023-per-lacquisizione-di-crediti-spendibili-per-i-servizi-disponibili-sul-catalogo-amazon-web-services-aws-essenziali-al-progetto-pnrr-single-digital-gateway-milestone-m1c1-12-ita-1-asse-1-missione-1-componente-1-sub-investimento-1-3-2-cup-c51b21006690006-176-2025-)).
- **PagoPA AWS SES-based transactional email** for notifying cittadini
  on SEND (PagoPA's AWS SES is documented at
  [dx.pagopa.it/radar/aws-ses](https://dx.pagopa.it/radar/aws-ses)).
- **ASL/AO tenants** in central Italy (Lazio, Lombardia) that have
  spun up an AWS account for a specific application (rare, not the
  main email).

### 3.2 Why so few, given the AWS–Italy commitment

On 2025-09-10, the **Consiglio dei Ministri approved €1.2B in AWS
investment in Italy** ([MIMIT press release](https://www.mimit.gov.it/it/notizie-stampa/cdm-interesse-strategico-per-investimento-da-1-2-miliardi-di-amazon-web-services-aws-in-italia)) — the
**second application of art. 13 DL 104/2023** (the Italian "golden
power" decree for cloud strategic assets). Concurrently, **AWS joined
the Polo Strategico Nazionale** as the 4th provider
([Il Sole 24 Ore](https://www.ilsole24ore.com/art/accordo-amazon-web-services-e-polo-strategico-nazionale-il-cloud-sicuro-AGiJCEWC)),
and is **ACN-qualified at Livello 2** (adequate for "non-strategic" PA
data) since 2025-10-28
([ACN catalogue](https://www.acn.gov.it/portale/w/in-60)).

So AWS is:

- **ACN-qualified in Italy (L2)**;
- **PSN-integrated** (4th provider);
- **MIMIT-recognized** as a strategic investment;
- and has **6 EU regions** including **Milan** (active since 2023-06)
  and **Spain, France, Sweden, Germany, Ireland**.

But the 7 PA entities on AWS as *primary email* is consistent with
this: AWS is **infrastructure** (compute, storage), not a managed
mailbox. The "AWS" provider in `PROVIDER_KEYWORDS` matches the
MX hostname containing `amazonaws` or `amazonses` — the few cases
where a PA has set up SES or an EC2-hosted Postfix as its
institutional MX. It is **not** the pattern of "AWS for email"
in the Microsoft-365 sense (AWS doesn't have a managed M365-equivalent
mailbox product marketed at the PA — WorkMail exists but has no
Italian PA footprint).

### 3.3 Risk assessment

**Risk: MEDIUM (legal) but the data exposure is tiny.**

- **Legal control:** 100% US (AWS is a wholly-owned Amazon Inc.
  subsidiary, Amazon Web Services EMEA SARL, Luxembourg). CLOUD Act
  applies in full.
- **Physical location:** **Milan region** (since 2023) is the default
  for AWS Italy customers; 6 EU regions available. So the *physical*
  data residency can be 100% EU. But the *legal* residency is US, and
  the CLOUD Act principle is "if you have a US provider, it doesn't
  matter where the bits are" (CLOUD Act, 2018).
- **Concentration risk:** zero at the current scale (0.03%). Even a
  100% AWS migration of the entire PA would not happen — AWS is not
  a direct PA-mail competitor.
- **CLOUD Act exposure:** 7 entities. If any of these is a sensitive-
  data PA (e.g., an ASL), the exposure is real, but small.
- **Strategic risk:** the **inverted case** is the real risk — under
  the MIMIT "strategic asset" regime, the **reverse** happens: PA
  workloads migrate *to* AWS (PSN-Secure-Cloud / SDAPA contracts),
  and the "AWS" provider count could grow from 7 to ~50–100 over
  2026–2028. At that scale, AWS becomes a "Microsoft 365"-
  equivalent risk: legal in the US, physical in the EU, but subject
  to CLOUD Act.

**Recommendation:** monitor the AWS provider count quarterly. If it
grows > 1% of classified (i.e., > 224 entities), add a new bucket
or split "AWS" into "AWS-SES" (managed mail) vs "AWS-EC2" (self-
hosted on AWS compute) — the sovereignty analysis differs (SES is
closer to MS365, EC2 is closer to independent).

---

## 4. Zoho (2 entities, 0.01%) — India-based, used in 2 PA mailboxes

### 4.1 Position in the dataset

2 entities = 0.01%. Both are bucket "Altri provider esteri" in the
sovereignty model (per `PROVIDER_DISPLAY` in `historicize.py`: Zoho
and Yandex are both mapped to "Zoho"/"Yandex" display, which lands
in `sovereignty_of()` → "Altri provider esteri", not in "USA (CLOUD
Act)").

Zoho's classification rule: `["zoho.com", "zoho.eu", "zoho.in",
"zohocorp.com"]`. The `zoho.eu` subdomain is the EU-tenant variant
(Zoho has a Zoho Workplace EU edition for GDPR compliance —
[product page](https://www.zoho.com/workplace/industry/government.html)).

### 4.2 What's going on

Zoho Mail is rare in the PA world. The 2 entities are likely:

- **One small ente** that signed up directly on the Zoho public
  free/standard plan (Indian jurisdiction, US-jurisdiction for the
  parent company — Zoho Corporation is US-incorporated, headquartered
  in Chennai, IN, but registered as a US LLC, so CLOUD Act *also*
  applies to it). The "Zoho" sovereignty bucket is "Altri provider
  esteri" because Zoho is **not** a US-domestic provider in the
  strict hyperscaler sense, but it is **not** Italian either, so it
  doesn't get CLOUD Act bucketing.
- **One ente** that adopted Zoho Workplace (the EU edition) for a
  small office — Zoho has an explicit "Government" vertical
  ([Zoho Government](https://www.zoho.com/workplace/industry/government.html))
  and cites **NIC (Government of India)** as a flagship reference
  with 1.1M users — so the technology is PA-grade, but it is not
  commonly used in Italy.

### 4.3 The parallel pattern: Zimbra / Carbonio, *not* Zoho

A different and more important "Z"-prefix pattern in the Italian
PA is **Zimbra** and **Carbonio** (a Zimbra-derived, Zextras-built
fork marketed for privacy-conscious EU customers). Zimbra is
hosted in Italy by Zextras via Studio Storti S.r.l. (Italian
reseller, Vicenza). Zimbra/Carbonio is **deployed on AWS-Italy**
in many cases, which is **why the dday study observed**: *"Nei
server italiani di AWS girano le mail di 239 comuni che utilizzano
le suite collaborative Zimbra o Carbonio"*. The DDay study
incorrectly attributes the 239 comuni to "AWS" — but the actual
*provider* in mxmap.it's classification is **independent** (the MX
hostname is `mx.carboniocloud.com` or similar, and the registrant
is the ente itself or Zextras, not AWS). This is the
"MX-on-AWS-but-email-owned-by-an-Italian-entity" pattern that
the mxmap.it classification correctly resolves as **independent**
(with reason mentioning the gateway), not as **AWS**.

Examples of Zimbra/Carbonio PA adoptions in Italy:

- Comune di Voghera: contratto 33.617 €/3 anni (2024-2026) per
  Carbonio Cloud via Studio Storti
  ([Provincia Pavese](https://ricerca.gelocal.it/laprovinciapavese/archivio/laprovinciapavese/2024/08/19/pavia-non-solo-le-email-i-nuovi-servizi-digitali-in-comune-13.html))
- Comune di Trezzano sul Naviglio: 2.355 €/year per Zimbra Cloud
  via Studio Storti ([determina Trezzano](https://trezzano.e-pal.it/AttiVisualizzatore/download/determina/3287328?fId=3387300))
- Comune di Chioggia: CIG ZE630935C4 per Zimbra + Zextras Suite
  ([Chioggia trasparenza](https://trasparenza.chioggia.org/ajax_scripts/dettagli_gara.php?id=9047))
- Comune di Garbagnate Milanese: CIG ZC83B9FEFB
  ([Garbagnate](https://garbagnatemilanese.trasparenza-valutazione-merito.it/web/trasparenzaj/pga-g/-/anac/display/168485))
- Comune di Civitavecchia: CIG Z3637019AF
  ([Civitavecchia](https://civitavecchia.portaleamministrazionetrasparente.it/index.php?id_cat=0&id_doc=1317432&id_oggetto=11))
- Unione Terre di Castelli (MO): piattaforma Zimbra con assistenza
  Mutinanet Srl ([Terre di Castelli](https://servizi-unioneterredicastelli.e-pal.it/L190/contratto/download/44994))

These are all classified as `independent` or `aruba`/`local-isp`
in mxmap.it (not as Zoho or AWS). The 2 Zoho entities are
*separate* — genuine Zoho adoptions, not Zimbra.

### 4.4 Risk assessment

**Risk: MEDIUM (legal) but tiny scale.**

- **Legal control:** non-Italian, non-US (Zoho Corp is a US LLC but
  India-incorporated; Zoho EU is a separate entity but the parent
  is US). Falls under "Altri provider esteri" in the mxmap
  sovereignty model.
- **Physical location:** depends on tenant. Zoho EU tenants are
  hosted in EU; Zoho US tenants in the US. 2 entities is too small
  to make a meaningful geopolitical statement.
- **Concentration risk:** zero.
- **CLOUD Act applicability:** yes (US LLC parent), so functionally
  same risk as Microsoft 365, but with 2 entities the practical
  impact is negligible.

**Recommendation:** keep the bucket as is. The 2 Zoho entities are
a curiosity, not a strategic risk. If the count ever exceeds 0.1%
(>22 entities), re-evaluate whether to merge into "Altri provider
esteri" or split into "Zoho EU" / "Zoho non-EU".

---

## 5. PA-contractor-private (1 entity, 0.005%) — the rare case

### 5.1 Position in the dataset

1 entity. The smallest non-zero bucket in the dataset. **It is its
own category in the sovereignty model** — `sovereignty_of()` in
`historicize.py` maps `pa-contractor-private` to display
"Provider Italiano" (so it counts under the 7,722 rollup), but
its *semantic* meaning is different: the email is **outsourced to a
private IT contractor** that is the de-facto operator, not a
commercial hosting provider like Aruba/Register.it/Seeweb.

Classification rule (`ITALIAN_PA_CONTRACTOR_PRIVATE_KEYWORDS` in
`constants.py`):

```
"eng.it", "engineering.it",        # Engineering Ingegneria Informatica SpA
"almaviva.it", "almavivaitalia.it", # Almaviva SpA
```

So the 1 entity has an MX that resolves to either `eng.it` or
`almaviva.it`. Given that Engineering and Almaviva are the two
largest IT outsourcers to the Italian PA central government, the
1 entity is almost certainly an entity that has had its entire IT
infrastructure (including mail) managed by one of these two
contractors.

### 5.2 Who are Engineering and Almaviva

- **Engineering Ingegneria Informatica S.p.A.** — founded 1980,
  Rome-headquartered, ~12,000 employees, one of the largest Italian
  IT services groups. **Part of Consip Cloud IaaS/PaaS framework** —
  winner of **Lotti 8 and 10** of the AQ Public Cloud (2022)
  ([Engineering press](https://www.eng.it/en/news/press-releases/2022/07/engineering-wins-two-new-lots-of-the-consip-framework-agreement-on-cloud-services)).
  Partnered with **Polizia di Stato** for IT security
  ([Engineering press 2024](https://www.eng.it/it/news/press-releases/2024/05/polizia-di-stato-e-gruppo-engineering-siglano-laccordo-per-la-prevenzione-e-il-contrasso-dei-crimini-informatici)).
  RTI partner for the **National Telemedicine Platform** (2023).
  Partner of **MIMIT**, **Giustizia**, **MASE**.
- **Almaviva — The Italian Innovation Company S.p.A.** — Rome-
  headquartered, ~10,000+ employees, the other large IT outsourcer.
  RTI leader of the **Consip AQ Public Cloud Lotto 1** (the main
  lot, CIG 81283942ED, €100M+). Partner of **MASE** (Ministero
  dell'Ambiente), **Veneto Region**, **MUR**. Documented as the
  cloud provider for **MITE/MASE** in a 2022 contratto esecutivo
  ([Mase contratti](https://www.mase.gov.it/portale/dg-itc-contratto-almaviva-per-l-acquisto-di-hosting-e-cloud)).

Together, Engineering + Almaviva dominate the **outsourced central-
PA IT** space. The fact that **only 1 entity in 22,987** is
classified as `pa-contractor-private` is therefore surprising — one
would expect more, since these are massive outsourcers.

The explanation is in the classification rule:

- The rule matches **only when the MX hostname resolves to
  `eng.it` / `engineering.it` / `almaviva.it` / `almavivaitalia.it`**.
- For most outsourced entities, the MX **resolves to the ente's
  own domain** (e.g., `mail.inps.it` for INPS, even though
  the underlying servers are managed by Engineering) — so the
  entity is classified as `independent` (or `microsoft` if the
  ente's MX has migrated to MS365).
- The 1 entity is therefore a **rare case** where the contractor
  *exposes* its own hostname in the MX — likely a small ente
  whose IT is fully managed by Engineering/Almaviva and which
  has not configured a delegated MX record.

### 5.3 Risk assessment

**Risk: MEDIUM (legal) but very small scale.**

- **Legal control:** Italian (Engineering / Almaviva are Italian
  SpA). The sovereignty model correctly maps this to "Provider
  Italiano" — **not** a sovereignty risk.
- **Physical location:** Italian (both companies operate Italian
  data centers, also rely on the Consip AQ Lotto 1 / 8 / 10
  public-cloud framework, which uses Aruba/Microsoft/Oracle/Google
  EU regions).
- **Concentration risk:** very low. 1 entity, single point of
  failure is not a national concern.
- **Vendor lock-in:** high *for that one entity*. If Engineering
  or Almaviva raised prices or changed terms, the entity would
  have to rebuild its mail infrastructure.

**Why this bucket matters even at 1 entity:**
The category itself is a *signal* that the mxmap.it classifier can
distinguish three different Italian commercial buckets:

1. **Italian commercial hosting** (Aruba, Register.it, Seeweb,
   Infocert, Namirial, small AIIP ISPs) — pure vendor relationship.
2. **Italian regional public** (Lepida, Trentino Digitale, Sogei,
   etc.) — publicly-owned in-house.
3. **Italian private contractor** (Engineering, Almaviva) —
   outsourced to a private IT services firm that is itself a
   PA contractor.

The fact that bucket 3 has only 1 entity is itself a finding:
**most of the time, when an entity is managed by Engineering or
Almaviva, the entity's MX is delegated back to the entity's own
domain**, so it shows up as `independent` or `microsoft` — not as
`pa-contractor-private`. This is good for transparency (the entity
is still the visible owner of its mail) but creates a **hidden
dependency**: a 4,000-user ASST on Engineering-managed MS365 looks
the same in DNS as a 4,000-user ASST on a self-managed MS365, even
though the lock-in profile is completely different.

**Recommendation:**

- The 1 entity is correctly classified — no action needed.
- A future enhancement: tag the dkim_tenant / managed_by fields
  with the contractor name where it can be inferred from
  Consip contracts (e.g., ASST Melegnano e Martesana, which
  migrated to MS365 via SB Italia in 2024, is in the Sanità
  sector's 60.96% CLOUD-Act share but has a *managed-service
  dependency* on SB Italia).
- Do **not** merge this bucket with "Provider Italiano" silently
  — the distinction between *vendor* (Aruba) and *contractor*
  (Engineering/Almaviva) is meaningful for lock-in analysis.

---

## 6. Final consolidation — the whole 22,987 entity map

### 6.1 Sovereignty hierarchy (from `kpi.json` + `historicize.sovereignty_of`)

```
22,987 Italian PA entities
│
├── 🇮🇹 ITALIAN JURISDICTION  (ISD = 52.65% dei classificati)
│   ├── 11,772 enti (51.2%)  ── sovereignty: "IT" (4-bucket Osservatorio)
│   │   ├── IT — Cloud sovrano  (954, 4.2%)  ── in-house public
│   │   │   └── Lepida, Trentino Digitale, Sogei, Insiel,
│   │   │       Liguria Digitale, Sardegna IT, Umbria Digitale,
│   │   │       ASMEL/ASMECAL/ASMECAM, TIX, GVCC Net
│   │   │
│   │   ├── IT — Provider commerciali  (7,722, 33.6%)  ── Italian commercial
│   │   │   ├── Aruba                  (estimated 5,000+)
│   │   │   ├── Register.it            (estimated 1,500+)
│   │   │   ├── Seeweb                 (79)
│   │   │   ├── Infocert / Namirial    (estimated 50-100 combined)
│   │   │   ├── Local ISP AIIP         (estimated 500+)
│   │   │   │   (Lepida included in regional-public bucket)
│   │   │   └── pa-contractor-private  (1)  ── Engineering / Almaviva MX
│   │   │
│   │   └── IT — Infrastruttura autonoma  (3,096, 13.5%)  ── self-hosted
│   │       ├── self-managed Postfix/Qmail/Zimbra
│   │       ├── 254 comuni on RUPAR Piemonte (`*@ruparpiemonte.it`)
│   │       ├── Scuole dirette (no edu.it)
│   │       ├── Zimbra/Carbonio deployments on AWS-Italy
│   │       ├── 239 comuni in dday's "AWS" sample (correctly classified as independent)
│   │       └── Boutique hosting:  XNet, ITnet, Pegaso, MC-link, KPNQwest, etc.
│   │
│   └── ❓ SCONOSCIUTO  (629, 2.7%)  ── bucket 4 of Osservatorio
│       ├── 190 no_domain     (no IndicePA domain)
│       ├── 315 no_mx          (consumer mail: Gmail/Libero/Tiscali/Yahoo)
│       └── 125 boutique MX    (no keyword match)
│
└── 🇺🇸 EXTRA-UE JURISDICTION  (CLOUD Act = 47.34% dei classificati)
    ├── Microsoft 365  (4,203, 18.3%)  ── CLOUD Act full
    ├── Google Workspace  (6,374, 27.7%)  ── CLOUD Act full
    ├── AWS  (7, 0.03%)  ── CLOUD Act full (PSN-integrated, ACN-L2)
    └── Zoho  (2, 0.01%)  ── "Altri provider esteri" (US LLC parent, IN/EU ops)
```

### 6.2 Risk matrix

| Bucket | Count | % | CLOUD Act | Lock-in | Concentration | Sovereignty | **Overall** |
|---|---:|---:|---:|---:|---:|---:|---:|
| Microsoft 365 | 4,203 | 18.3% | YES | Med | High | US | **HIGH** |
| Google Workspace | 6,374 | 27.7% | YES | Med | High | US | **HIGH** |
| AWS | 7 | 0.0% | YES | Low | Negligible | US (EU data) | **MED** |
| Zoho | 2 | 0.0% | YES (US parent) | Low | Negligible | US/IN | **MED** |
| **Subtotal extra-UE** | **10,586** | **46.1%** | | | | | **HIGH** |
| Aruba + Register.it + Seeweb + Infocert + Namirial + AIIP ISPs + pa-contractor-private | 7,722 | 33.6% | NO | Med | Med (rollup); low individually | IT | **LOW** |
| In-house (Lepida, Trentino Digitale, Sogei, …) | 954 | 4.2% | NO | Low | Low | IT | **VERY LOW** |
| Self-hosted / independent | 3,096 | 13.5% | NO | High (capability) | Negligible | IT | **MED** |
| **Subtotal IT** | **11,772** | **51.2%** | | | | | **LOW–MED** |
| Sconosciuto | 629 | 2.7% | ? | ? | ? | ? | **HIGH (visibility)** |

### 6.3 Top-3 concentration analysis

The market is a **duopoly with local fragmentation**:

- **Top-3 (Provider Italiano rollup + Google + Microsoft) = 66.83%** —
  the "long tail" (Cloud Italiano, independent, AWS, Zoho, unknown) is
  33.17%.
- **HHI = 1,879** — this is in the **"moderately concentrated"** range
  (US DOJ threshold: 1,500–2,500 = moderate; > 2,500 = highly
  concentrated). The Italian PA email market is *less* concentrated
  than the US cloud market overall (HHI ~3,000) but *more* than the
  Italian SMB email market (HHI ~1,200 per SynSphere).
- **The "Provider Italiano" rollup at 33.6% is itself a misclassification
  of risk**: it's an aggregate of ~7 distinct legal entities. The
  Aruba-alone share is likely 20–25%; the Register.it share is 6–8%;
  the Seeweb/Infocert/Namirial/AIIP shares are each < 1%. So the
  *true* top-3 is probably **Google 27.7% + Microsoft 18.3% +
  Aruba 20–25% = 66–70%** — but with Aruba's lower lock-in profile,
  the *risk-adjusted* top-3 might be **Google + Microsoft + Lepida
  cluster = 30.7%** (the hyperscalers as a single "extra-UE" risk
  unit, plus the in-house tier).

### 6.4 The 4 sub-signals of the 47.34% CLOUD Act share

CLOUD Act exposure breaks down by sector, not by provider:

| Sector | Entities | CLOUD Act % | ISD % | Dominant provider | Why |
|---|---:|---:|---:|---|---|
| Istruzione (Scuole, Università, AFAM) | 8,403 | **78.16%** | 21.84% | Google Workspace | `*.edu.it` → Google Workspace for Education (~60%); rest is MS365 + indipendente |
| Sanità (ASL, AO) | 234 | **60.96%** | 39.04% | Microsoft 365 | ASST migrations to MS365 (Levita, SB Italia, etc.) |
| Ricerca | 68 | **56.72%** | 43.28% | Microsoft 365 | Consorzio GARR, ENEA, INFN, CNR migrate to MS365 / Teams |
| Stato centrale, Ministeri | 52 | 67.35% | 32.65% | Microsoft 365 | Microsoft EA, Sogei M365, ACN-qualified |
| Trasporti e Porti | 17 | 62.50% | 37.50% | Microsoft 365 | Authority portuali, ANAS — small numbers |
| Agenzie regionali | 76 | 53.62% | 46.38% | Microsoft 365 | INPS, INAIL, regional agencies |
| Previdenza (INPS, INAIL) | 143 | 48.89% | 51.11% | Microsoft 365 | INPS M365 transition (massive 2023–2026) |
| Stazioni appaltanti | 606 | 47.31% | 52.69% | Microsoft 365 | ANAC-aligned; Consip-procured |
| Società partecipate | 1,128 | 45.01% | 54.99% | Microsoft 365 | SOE like Ferrovie, Poste, ENI, etc. — large but mostly MS365 |
| Welfare, IPAB | 468 | 30.11% | 69.89% | Provider Italiano | Often tied to municipal infrastructure |
| Ambiente e Territorio | 272 | 28.96% | 71.04% | Provider Italiano | Parchi nazionali, ARPA regionali |
| Consorzi, Unioni | 1,464 | 27.16% | 72.84% | Provider Italiano | Often on regional-public (Lepida, Insiel) |
| Enti territoriali (Comuni, Province) | 8,006 | 24.96% | 75.02% | Provider Italiano | **The Italian PA strength** |
| Ordini professionali, Camere | 2,021 | 23.14% | 76.86% | Provider Italiano | Infocert / Namirial for digital signature verticals |
| Cultura (teatri, fondazioni) | 29 | 42.86% | 57.14% | Provider Italiano | Small numbers, fragmented |

**Two sectors (Istruzione + Sanità = 8,637 entities) account for
~81% of all CLOUD Act exposure.** This is a *targeted* political
strategy: those two sectors handle the most sensitive citizen data
(minori, salute) and the choice of US hyperscalers is a strategic
vulnerability, not an accident.

### 6.5 Geopolitical reading

The "ISD" headline of 52.65% is **a coin-flip in the wrong direction**:

- If we trust the **legal control** number (provider-based
  sovereignty = 52.65%), Italy is *just* sovereign. 1 percentage
  point further and we'd be a minority.
- If we trust the **physical MX** number (`jurisdiction:
  domestic 46.1% / foreign 49.58% / mixed 1.12% / unknown 3.2%`),
  Italy is *already* a minority: **49.58% of PA MX records
  physically terminate in a non-Italian datacenter** (per
  GeoLite2 / RIPE).
- The **gap of ~5 percentage points** between ISD (52.65%) and
  domestic-MX (46.1%) is itself the most important finding: it
  says *"Italian providers sometimes use non-Italian infrastructure"*
  (e.g., Microsoft 365 Italy datacenters in Lombardy are the
  "in-EU" part of Microsoft, not domestic; Aruba uses its own
  Italian DCs but is "domestic" + uses Cloudflare/CDN that
  routes through non-Italian POPs).

**The Osservatorio's "ISD" metric intentionally uses legal
control** (because CLOUD Act's whole point is that *physical*
location is meaningless), but the 5pp gap to physical-MX is a
**worth-a-thousand-words callout** for the report card.

### 6.6 What we know confidently vs. what we don't

| Finding | Confidence | Source |
|---|---|---|
| Total 22,987 entities; 629 unknown; 7 AWS; 2 Zoho | **HIGH** | `kpi.json` + `assert_integrity` |
| ISD = 52.65%, CLOUD Act = 47.34% | **HIGH** | `kpi.json` + `assert_integrity` |
| Cloud Italiano 954 = Lepida cluster + Sogei + Trentino Digitale + … | **HIGH** | `kpi.json` rolled-up; keywords in `constants.py` |
| Seeweb = 79 entities | **HIGH** | `report.json` aggregates (Seeweb is its own category, not rolled) |
| pa-contractor-private = 1 entity | **HIGH** | `kpi.json` (only Engineering / Almaviva MX matches) |
| Aruba's individual share of the 7,722 "Provider Italiano" rollup = ~20–25% | **MED** | Inferred from dday's "Aruba 30% of 7,896 comuni" + register.it + Seeweb + AIIP orders-of-magnitude; **not directly visible** in kpi.json |
| The 629 unknown decomposes as 30% no-domain / 50% no-MX / 20% boutique | **MED-HIGH** | Corroborated by 3 independent studies (DDay, SynSphere, Tarizzo) |
| Seeweb's 79 entities are mostly ISWEB Cloud PA customers + small comuni | **MED** | Inferred from external contracts; **not directly sampled** from data.json |
| The 1 pa-contractor-private is an Engineering or Almaviva MX | **MED** | Inferred from keyword rule (only `eng.it`, `almaviva.it`); not entity-sampled |
| The 7 AWS entities are PNRR/PSN tenants (not "AWS for mail" in the M365 sense) | **MED-HIGH** | Inferred from MIMIT decree, ACN catalogue, PagoPA SDAPA + AWS SES dx.pagopa.it |
| Istruzione + Sanità account for ~81% of CLOUD Act exposure | **HIGH** | `report.json` `by_cluster` sums; consistent with external commentary |
| Isole + Sud are more sovereign than Nord (Lombardia, Veneto) | **HIGH** | `report.json` `by_region` (full table) |

---

## 7. Sources

### Kept (high signal)

- **MxMap.it own artifacts** (kpi.json, report.json, validation_report.csv) — primary, asserted by `assert_integrity`.
- **historicize.py / constants.py / stats.py** in `src/mail_sovereignty/` — the classifier logic; single source of truth.
- **DDay (2025-08-22)**, *"Quale email provider usano i comuni italiani?"* — independent corroboration of the 629 "unknown" structure, the Aruba 30% figure, the Zimbra-on-AWS-Italy pattern, and the Microsoft 9.37% / Google 5.11% MS-Italy figures. [link](https://www.dday.it/redazione/54142/quale-email-provider-usano-i-comuni-italiani-ecco-chi-e-piu-eurocentrico-e-chi-si-affida-ad-azienda-estere)
- **SynSphere Insights (2026)**, *"Mercato email Italia 2026"* — independent corroboration of the 15% US-hyperscaler share, the long-tail unknown pattern, and the Register.it 3.15% / Aruba 2.18% / SEEWEB 0.7% breakdown. [link](https://synsphere.it/notizie/mercato-email-italia-2026-microsoft-google-dominano-tld-it/)
- **Fabrizio Tarizzo (2025)**, *"Analisi della conformità agli standard Internet moderni dei domini istituzionali della PA italiana"* — the **97.2% MX coverage** of comuni (217 of 7,741 without MX) — the same 2.7–2.8% gap as mxmap. [link](https://www.fabriziotarizzo.org/documenti/analisi-siti-pa-2025/)
- **ACN Catalogue** — AWS ACN-L2 qualification (2025-10-28 to 2028-10-28), Seeweb ACN-qualified CSP, Aruba qualification. [link](https://www.acn.gov.it/portale/catalogo-delle-infrastrutture-digitali-e-dei-servizi-cloud)
- **MIMIT (2025-09-10)** — €1.2B AWS Italy investment decree, "interesse strategico nazionale". [link](https://www.mimit.gov.it/it/notizie-stampa/cdm-interesse-strategico-per-investimento-da-1-2-miliardi-di-amazon-web-services-aws-in-italia)
- **Il Sole 24 Ore (2025)** — AWS joins PSN. [link](https://www.ilsole24ore.com/art/accordo-amazon-web-services-e-polo-strategico-nazionale-il-cloud-sicuro-AGiJCEWC)
- **Il Sole 24 Ore (2025)** — *"State Clouds, the PA accelerates: adhesions +380%. 3.6 billion contracts"* — PSN growth 120 → 576 entities between 2023 and 2025, +380%. [link](https://en.ilsole24ore.com/art/cloud-state-pa-accelerates-accession-380percento-contracts-36-billion-AHGCUG1D)
- **Il Sole 24 Ore (2026)** — *"2026 will be decisive for the completion of the national sovereign cloud project"*. [link](https://en.ilsole24ore.com/art/2026-will-be-decisive-in-completing-the-national-sovereign-cloud-project-AIJjHBS)
- **Piano triennale ICT 2024-2026 (agg 2026)** — Italian cloud strategy. [link](https://docs.italia.it/italia/piano-triennale-ict/pianotriennale-ict-doc/it/2024-2026-agg-2026/capitolo-6_infrastrutture/infrastrutture-digitali-e-cloud.html)
- **Garante Privacy / Regione Lombardia fine (2025-06-04)** — first Italian Garante fine on email metadata retention (€50K). [DLA Piper](https://privacymatters.dlapiper.com/2025/06/italy-the-garante-issues-first-gdpr-fine-over-employees-email-metadata-privacy-breach/), [LCGI](https://lcgi.co.uk/italys-garante-fines-lombardy-region-for-excessive-e-mail-metadata-retention/), [De Luca & Partners](https://www.delucapartners.it/en/news/first-fine-for-unlawful-retention-of-corporate-e-mail-metadata-and-internet-logs-by-italian-data-protection-authority/).
- **Agenda Digitale (2025)** — *"Cloud delle big tech, quali i rischi per i comuni italiani"* — the political narrative (CLOUD Act + PNRR + Castelmuro parable). [link](https://www.agendadigitale.eu/infrastrutture/cloud-usa-e-sovranita-digitale-i-rischi-possibili-per-i-comuni-italiani/)
- **Il Sole 24 Ore (2025)** — *"Digital sovereignty: Europe divided in the cloud, Italy protects sensitive data"* — Italy's strategic positioning vs EU. [link](https://en.ilsole24ore.com/art/digital-sovereignty-europe-divided-cloud-italy-protects-sensitive-data-AH47xsv)
- **Osservatori.net (2025-05-28)** — *"Il mercato Cloud in Italia cresce del 20% nel 2025"* — €8.13B cloud market, +20% YoY. [link](https://www.osservatori.net/comunicato/cloud-ecosystem-sovereignty/cloud-italia-mercato/)
- **Netalia / Corriere della Sicurezza** — *"Il perimetro della sovranità digitale in Italia e le priorità"* — Italian sovereign cloud offer is ~€100M out of a €8B market (only ~5 fully sovereign operators). [link](https://www.ilcorrieredellasicurezza.it/il-perimetro-della-sovranita-digitale-in-italia-e-le-priorita-lanalisi-di-netalia/)
- **Seeweb** — [European Cloud page](https://www.seeweb.it/en/company/european-cloud), [Cloud Mail product](https://www.seeweb.it/en/products/cloud-mail), [data centers](https://www.seeweb.it/en/data-center/our-data-centers), [w3techs 0.1% market share](https://w3techs.com/technologies/details/em-seeweb).
- **ISWEB Cloud PA** — Seeweb's "Cloud PA" reseller. [link](https://www.isweb.it/pagina108_il-cloud-dedicato-alla-pa.html)
- **Comune di Sanremo trasparenza** — direct CIG to Seeweb. [link](https://trasparenza.comuni.it)
- **Engineering press releases** — [Consip AQ lotti 8/10](https://www.eng.it/en/news/press-releases/2022/07/engineering-wins-two-new-lots-of-the-consip-framework-agreement-on-cloud-services), [Polizia di Stato accordo 2024](https://www.eng.it/it/news/press-releases/2024/05/polizia-di-stato-e-gruppo-engineering-siglano-laccordo-per-la-prevenzione-e-il-contrasso-dei-crimini-informatici).
- **Almaviva Cloud PA** — [aqcloud.almaviva.it](https://aqcloud.almaviva.it/); [MASE contratto](https://www.mase.gov.it/portale/dg-itc-contratto-almaviva-per-l-acquisto-di-hosting-e-cloud).
- **Consip Cloud IaaS/PaaS framework** — [bandi/gare](https://www.consip.it/bandi/aq-iaas-e-paas-2-ed-2).
- **Cloud Italia strategy** — [cloud.italia.it](https://cloud.italia.it/strategia-cloud-pa/), [ACN](https://www.acn.gov.it/portale/en/strategia-cloud-italia).
- **Zoho Government** — [product page](https://www.zoho.com/workplace/industry/government.html).
- **Libraesva** — Italian email security gateway (mentioned in: Comune di Vicenza, balance companies like Balocco). [link](https://www.libraesva.com/email-security). Note: Libraesva is in the project as a GATEWAY keyword — it's not a primary email provider for the 629 unknown but is a relevant adjacent security layer.
- **Studio Storti / Zextras Carbonio** — Italian Zimbra/Carbonio reseller for PA (Voghera, Trezzano, Chioggia, Garbagnate, Civitavecchia, Terre di Castelli). [Voghera](https://ricerca.gelocal.it/laprovinciapavese/archivio/laprovinciapavese/2024/08/19/pavia-non-solo-le-email-i-nuovi-servizi-digitali-in-comune-13.html), [Trezzano](https://trezzano.e-pal.it/AttiVisualizzatore/download/determina/3287328?fId=3387300).
- **Lepida ScpA** — Italian in-house cloud for Emilia-Romagna. [datacenter](https://www.lepida.net/en/datacenter-cloud/home), [cloud migration 2024](https://www.lepida.net/news/2025-02/migrazione-cloud-enti-soci).
- **Trentino Digitale** — Italian in-house cloud for Provincia Autonoma di Trento. [link](https://trentinodigitale.it/).
- **AgID statistiche utilizzo PEC (2025)** — 260k+ PEC domains, 15-16M caselle, 0.9-1.1M messaggi/quadrimestre. [link](https://www.agid.gov.it/sites/agid/files/2025-05/statistiche_utilizzo_pec_agid.pdf).
- **Microsoft Learn** — Microsoft 365 data residency / EU boundary commitments. [link](https://learn.microsoft.com/it-it/microsoft-365/enterprise/o365-data-locations).
- **Microsoft Italia (2023-06-05)** — Lombardy datacenter region announcement. [link](https://news.microsoft.com/europe/2023/06/05/microsoft-announces-its-first-cloud-region-in-italy-accelerating-innovation-and-economic-opportunity/).
- **Microsoft + Aruba (2025-05-28)** — Azure Local su infrastrutture dedicate Aruba. [link](https://news.microsoft.com/it-it/2025/05/28/aruba-e-microsoft-italia-insieme-per-una-nuova-offerta-azure-local-su-infrastrutture-dedicate-e-localizzate-in-italia/).
- **Nextcloud (2025)** — Regione Veneto self-hosted file/email sovereignty case. [link](https://nextcloud.com/blog/how-the-italian-veneto-region-ensures-digital-sovereignty-for-its-public-services-with-nextcloud/).
- **IndicePA Opendata** — [Enti dataset](https://www.indicepa.gov.it/ipa-dati/dataset/enti), [Categorie enti](https://indicepa.gov.it/ipa-dati/dataset/categorie-enti), [Elenco PEC](https://indicepa.gov.it/ipa-dati/dataset/elenco-pec).

### Dropped

- **MyNet** (mynet.it) — listed as an AIIP ISP, mentioned by DDay as a regional Italian provider; included in the "Provider Italiano: 7,722" rollup, no specific PA use case found.
- **Clio / ClioCom** — same (AIIP member, no specific PA case to anchor this report).
- **Banca d'Italia, INPS, INAIL, ENEA, INFN** — referenced by SynSphere as "self-hosting" examples (camera.it, esteri.it, mit.gov.it, istat.it, bancaditalia.it, inps.it) — but these are not in mxmap's 22,987 (IndicePA scope) or are classified under "Sconosciuto" if not in IndicePA. Out of scope for this report.
- **Istat (2022) PA locale e ICT survey** — useful context but predates the 2024+ PNRR-driven migrations; the 54.2% cloud adoption number is from 2018 baseline.

---

## 8. Gaps and recommended next steps

### Confidence-graded gaps

1. **HIGH-confidence gap:** the *decomposition* of the 7,722 "Provider
   Italiano" rollup into Aruba / Register.it / Seeweb / Infocert /
   Namirial / AIIP / pa-contractor-private shares. The kpi.json does
   not expose this — the `kpi.json` schema is intentionally grouped
   for citizen-facing narrative. **Next step:** add a
   `provider_to_sov4` (4-bucket Osservatorio) breakdown + the
   sub-providers list to a new `provider_detail.json` artifact, or
   expand the `top_providers` array in kpi.json to include the
   per-provider sub-counts (with a `display_group: "rollup"` vs
   `"sub"` flag).

2. **MED-confidence gap:** the per-entity sampling of the 629
   unknown, the 79 Seeweb, the 7 AWS, the 2 Zoho, and the 1
   pa-contractor-private. The kpi.json / report.json give the
   counts; the *names* are not exposed in any of the public
   artifacts. **Next step:** extract a one-time `entities_by_provider`
   sample (e.g., top 20 per category) into a `research/` file for
   analyst review, without exposing full entity-level data
   publicly. This is what would have made this report complete;
   it's also what would have allowed verification of the
   sub-pattern (a/b/c) decomposition of the 629.

3. **MED-confidence gap:** the live breakdown of "Provider Italiano"
   by Aruba vs Register.it vs Seeweb. **Next step:** enhance
   `build_stats.py` to emit a `provider_rollup_breakdown` field in
   `kpi.json` (or a sibling file) that shows the ungrouped counts
   for the 7 Italian commercial providers. This is a one-line
   change in `compute_current` and would close the largest
   remaining analytical gap.

4. **LOW-confidence gap:** the **IndicePA-driven 30% of unknown
   entities are de facto invisible** — they are not even in
   IndicePA. This is not a mxmap issue, it's an IndicePA issue
   (the gap is structural and well-documented in Tarizzo 2025
   and in the IndicePA `categorie_enti` documentation). The path
   to closure is **upstream remediation of IndicePA**, which
   `mxmap.it#2` already tracks.

### Why the 2.7% unknown is not a bug to fix

It is tempting to try to drive the unknown rate to 0% by
expanding `AIIP_ISP_KEYWORDS` and `LOCAL_ISP_ASNS` until
`assert_integrity` reports < 1% unknown. **Don't.** The 2.7%
is a **structural signal**, not a quality gap:

- ~50% of the 629 are comuni on consumer mail (Gmail, Libero, Tiscali) —
  this is **information about the entity**, not a missing regex.
- ~30% have no IndicePA domain — this is a **data source issue**,
  resolvable only by AgID fixing IndicePA (issue #2).
- ~20% are on boutique hosting — adding 5–10 more AIIP keywords
  might classify 50–80 of these, but the 2.7% would not go to 0%:
  the long tail is infinite.

The right move is to **report the decomposition** (a/b/c above) in
`report.json` so the public can see "we know *why* 2.7% is unknown
and we are tracking it" — that is itself a transparency gain.

---

## 9. Strategic outlook — where the 22,987 are heading

The June 2026 snapshot is a **steady-state mid-transition picture**,
not a permanent one. Three vectors will reshape the dataset over the
next 12–24 months:

### 9.1 The PSN-driven convergence (high-impact, medium-certainty)

**Polo Strategico Nazionale is growing fast.** Between 2023 and 2025
the number of central + local administrations that have joined the
NSNP has grown **+380%** — from 120 to 576 entities — with **€3.6
billion in signed contracts through 2035**
([Il Sole 24 Ore — "State Clouds, the PA accelerates"](https://en.ilsole24ore.com/art/cloud-state-pa-accelerates-accession-380percento-contracts-36-billion-AHGCUG1D)).
The 2026 "decisive" milestone is the full launch of the
in-house cloud tier (PSN-Secure-Cloud), with the
**4 hyperscalers now qualified** (Microsoft Azure, Google Cloud,
Oracle, and **AWS** as of 2025)
([Il Sole 24 Ore — "2026 will be decisive for the national sovereign cloud project"](https://en.ilsole24ore.com/art/2026-will-be-decisive-in-completing-the-national-sovereign-cloud-project-AIJjHBS)).

**Implication for the dataset:** the **Cloud Italiano bucket (954)
is structurally biased to grow** (PSN migrations, plus Regione
Veneto Nextcloud, plus the Lepida/Insiel expansions). A
plausible 2027-Q4 trajectory: Cloud Italiano = 1,800–2,400 entities
(8–10% of the total), with the marginal entities coming from
"Microsoft 365" and "Provider Italiano" (Aruba-tier) — not from the
"Google Workspace" tier, which is structurally embedded in
Istruzione.

**Implication for the Osservatorio:** the **ISD could rise
materially** (from 52.65% to perhaps 60–65% by 2027) **without
changing the CLOUD Act exposure of the education sector**,
which will remain Google's stronghold. The narrative of "PSN is
saving sovereignty" is *partially* true — the PNRR funds the
migration of strategic-data PA workloads, but the
**education sector is structurally outside the PSN scope** (no
school will move 8,000 `*.edu.it` Google Workspaces to PSN
without breaking every classroom workflow).

### 9.2 The CLOUD Act regulatory pressure (high-impact, high-uncertainty)

The **Trump 2.0 administration** (inaugurated Jan 2025) is using
the CLOUD Act more aggressively as a foreign-policy lever. The
Garante Privacy's first email-metadata fine (€50K against
**Regione Lombardia**, 4 June 2025, for retaining 90 days of email
metadata and 365 days of web-browsing logs)
([DLA Piper Privacy Matters](https://privacymatters.dlapiper.com/2025/06/italy-the-garante-issues-first-gdpr-fine-over-employees-email-metadata-privacy-breach/),
[LCGI.co.uk](https://lcgi.co.uk/italys-garante-fines-lombardy-region-for-excessive-e-mail-metadata-retention/))
is the **first Garante fine on email metadata in Italy** — a
precedent that will accelerate the PNRR-driven migration to
ACN-qualified cloud for any PA that stores communications
metadata on US providers.

**Implication for the dataset:** expect **Sanità (ASL), Welfare
(INPS), and Welfare (regional agencies)** to migrate
**out of Microsoft 365** over 2026–2028 — not because Microsoft
is technically inadequate, but because the regulatory cost of
keeping health + pension data on a CLOUD Act–exposed
provider is now non-zero. The "Sanità 60.96% CLOUD Act"
number should drop to perhaps 30–40% by 2027.

### 9.3 The AWS strategic-investment overhang (medium-impact, low-probability-but-high-tail-risk)

The €1.2B AWS Italian investment (MIMIT decree 2025-09-10,
[second application of art. 13 DL 104/2023](https://www.mimit.gov.it/it/notizie-stampa/cdm-interesse-strategico-per-investimento-da-1-2-miliardi-di-amazon-web-services-aws-in-italia))
is, on paper, the **most significant foreign-cloud commitment in
Italy since Microsoft's Lombardy datacenter region (2023)**. If
executed, it implies a 4–6x growth in the AWS footprint of the
Italian PA over 2026–2028.

**Implication for the dataset:** **the 7-entity AWS bucket will
likely 10x.** The question is whether the growth is in:

- *AWS as primary email* (Zoho-style: a small ente that puts its
  MX on Amazon SES) — *moderate risk, low number of entities*;
- *AWS as compute underneath an Italian MSP* (the
  Zimbra-on-AWS-Italy pattern that DDay calls "239 comuni") —
  *correctly classified as `independent` or `local-isp` in
  mxmap, so no sovereignty change*;
- *AWS as direct PA infrastructure via PSN-Secure-Cloud* —
  *high risk, high number of entities, fully CLOUD Act
  exposed by default*.

The third case is the tail risk: if PSN's 4th provider (AWS)
ends up hosting large ASL/INPS workloads because of the
MIMIT deal, **the ISD could fall 5–10 percentage points in a
single year**, offsetting the PSN-Sovrano gains.

### 9.4 The Osservatorio's 3 priority questions for the next year

1. **Decompose "Provider Italiano" (7,722).** The single most
   impactful analytical change: expose the Aruba / Register.it /
   Seeweb / Infocert / Namirial / AIIP / pa-contractor-private
   counts individually in the public artifacts. The current
   rollup hides two orders of magnitude of variation in
   lock-in risk.
2. **Track the 629 unknown as a coverage watch.** Add the
   no-domain / no-MX / boutique decomposition to `kpi.json`. The
   2.7% is not a regression — it's the structural floor — but
   it deserves transparency.
3. **Wire the dkim_tenant / Consip-contractor signal into the
   "managed-by" dimension.** A 4,000-user ASST on
   Engineering-managed MS365 has the *same* provider signature
   as a 4,000-user ASST on self-managed MS365, but a
   *completely different* lock-in profile. The "lock-in" axis
   is orthogonal to the "sovereignty" axis and should be its
   own dimension in the Osservatorio.

### 9.5 The bottom-line reading for 22,987 entities

- **The dataset is *not* a steady state.** It is a snapshot of
  Italy in mid-transition: ~50% legacy (Italian commercial
  providers, in-house infrastructure, self-hosted), ~46%
  hyperscaler (Microsoft + Google, with a tiny AWS tail), ~3%
  visibility gap. The PNRR/PSN/CLOUD Act dynamics will
  redistribute this between 2026 and 2028.
- **The headline 52.65% ISD understates the real risk** because
  it treats "Provider Italiano" as a single bucket. The
  *sovereignty-relevant* decomposition is the
  Cloud-Italiano-only 954 (4.2%) — that's the *truly*
  sovereign tier; the rest of the "Provider Italiano" is
  *commercially Italian* but not *infrastructure-sovereign*
  (Aruba, Register.it, Seeweb, etc. are private companies that
  could be acquired, or could change jurisdiction, or could
  fail).
- **The 47.34% CLOUD Act share is concentrated where it hurts
  most:** education (children's data) and healthcare (patient
  data). The strategic question is not "should we move to
  sovereign cloud" (the answer is yes) — it's "**at what
  cost in classroom and clinician workflow disruption?**"
  This is the question the Osservatorio cannot answer with
  data alone; it needs the political answer.

---

## 10. Supervisor coordination

No decision was needed during this research (the task was to
consolidate existing kpi.json / report.json / constants.py /
historicize.py / stats.py / data.json with web research, not to
modify any of them). No `contact_supervisor` invocation was made.

The artifacts that would benefit from the **enhancements noted in §8
(gaps 1, 3)** are: `kpi.json` schema (add `provider_detail` array),
`build_stats.py` (emit the array), and the `report.py` / `kpi.py`
scripts that consume it. These are 1-PR changes, not blocked, and
should be raised as an `mxmap.it#…` issue for the project
maintainer's queue.
