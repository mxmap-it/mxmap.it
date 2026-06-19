# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MX Map is a DNS-based email provider classifier for European municipalities (92 countries, ~20,000 municipalities). It runs a 3-stage async pipeline that produces `data.json`, which powers an interactive Leaflet.js map showing where municipalities host their official email. Forked from [mxmap.ch](https://mxmap.ch) (Swiss municipalities). Covers all 27 EU member states plus 20 non-EU European countries.

## Project context (2026): the Italian digital-sovereignty observatory

The classifier above (92 countries) is the inherited infrastructure; **since 2026 the active focus is Italy**, as the data engine behind the **Osservatorio Nazionale Sovranità Digitale**. Read this section before touching any public-facing or KPI logic — it captures the framing, the analytical model, and the decisions/assumptions/constraints accumulated so far, so a new contributor can pick up the project.

### Two-project ecosystem (keep the boundary)
- **MxMap (this repo) = the *data engine*.** Classifies the email provider of ~22,987 Italian PA entities (from IndicePA) → `data.json` + **public static artifacts at the deploy root**: `kpi.json` (aggregate KPIs) and `report.json` (the structured report), plus the pages `statistiche.html`, `report.html`, `storia.html` (gated), `anomalie.html`, `methodology.html`.
- **Osservatorio Nazionale Sovranità Digitale = the *presentation/advocacy* layer.** A *separate* Hugo repo (`fpietrosanti/osservatorio-nazionale-sovranita-digitale`; local `C:\Users\admin\osservatorio-nazionale-sovranita-digitale`). Stakeholder-oriented; it **fetches** our artifacts (a `update-kpi.yml` Action downloads `kpi.json`; same pattern planned for `report.json`) and renders them with its own styling.
- **Contract:** MxMap *produces*, the Osservatorio *consumes*. Artifacts are static files at the deploy root — no API, no auth, CC BY-SA 4.0. **Measurement belongs here; editorial/presentation belongs to the Osservatorio.** If you change an artifact's schema, update `docs/STATS_KPI.md` and tell the Osservatorio side.
- **Custom domain:** `mxmap.it` (CNAME). Canonical URLs are `https://mxmap.it/...`; old `fpietrosanti.github.io/mxmap.it/...` redirect there.

### The sovereignty model (single source of truth)
- `sovereignty_of(provider)` + `material_row(entity)` in [`historicize.py`](src/mail_sovereignty/historicize.py) are **canonical** — `stats`, `kpi`, `report` all reuse them. **Never re-derive sovereignty elsewhere.**
- **6 MxMap buckets:** `USA (CLOUD Act)`, `Altri provider esteri`, `Italia — Cloud sovrano`, `Italia — Provider commerciali`, `Italia — Infrastruttura autonoma`, `Sconosciuto`.
- **4 Osservatorio buckets** (`kpi.provider_to_sov4`): `extra_eu` (USA + non-European foreign, e.g. Zoho/Yandex), `eu_non_it` (European non-IT providers — OVH, Hetzner, IONOS, Scaleway, Gandi, Infomaniak; CH/UK counted as European for simplicity — via `EU_NON_IT_PROVIDERS`, [#21](https://github.com/mxmap-it/mxmap.it/issues/21)), `it` (the 3 Italian buckets), `unknown`. In the 6-bucket model these European providers sit in `Altri provider esteri`; the `eu_non_it`/`extra_eu` split happens only in the 4-bucket.
- **ISD — Indice di Sovranità Digitale:** % entities under Italian jurisdiction, computed **over classified** (unknowns excluded), on **provider sovereignty** (legal control). `mx_jurisdiction` (where the MX physically sits) is a **complementary technical** indicator — the gap between the two is itself a finding.

### Two segmentation axes
- **By GROUP (works):** 15 citizen-friendly clusters keyed on the `bfs` category code. NB: the `bfs` uses the project's **own** codes (`COM`=Comuni, `PRO`=Province, `CMM`, `REG`), **not** IndicePA `L6`/`L5` — the 54 real codes are mapped in `stats.CLUSTERS` (full coverage, no `other`).
- **By AREA (active):** every IT entity now carries `regione`/`provincia`/`comune`/`macroarea`, injected by [`scripts/enrich_geo.py`](scripts/enrich_geo.py) via the **structural geographic enrichment** — it resolves the seed's clean `ipa_codice_comune_istat` (the comune-sede, present 100%) against the official ISTAT crosswalk (`data/istat_comuni.json`) in [`geo.py`](src/mail_sovereignty/geo.py). **Coverage 20/20 regions, 100%** (Sardegna uses pre-2016 legacy province prefixes 112–119, mapped to current provinces; see `geo.SARDEGNA_LEGACY_PROV`). This **bypasses** IndicePA's dirty `region` field, not derived from it. Consumed by `stats.compute_by_region` → `stats_by_region.json` + the report **"Analisi per aree"** section (regional ISD league table + macroarea summary + most-sovereign/most-exposed extremes) + the **Statistiche** page (regional stacked bars).
- **GOTCHA — the map's region/province grouping uses `regione`/`provincia`, NOT the legacy seed fields.** The interactive map (`index.html`) historically grouped the *Regioni* level by `canton` and the *Province* level by `district` — both stale seed fields that the geo work left only **~33–34%** populated (and `canton` is full of garbage like assembly/entity names). Reading them directly silently broke both choropleths (72 fake "regions", mostly-empty provinces). `build_frontend.py` now keys IT regions by `regione` (20) and provinces by the `provincia` car-plate sigla (107); `index.html`'s `getGroupKey` reads the clean fields and `matchGroupFeature` matches the topo polygons by `name:it` (bilingual regions: Sardegna/Valle d'Aosta/Trentino) and by sigla (`ISO3166-2`/`short_name`) for provinces. **Guard:** `build_frontend._assert_it_geo_coverage` exits non-zero if `regione`/`provincia` coverage isn't 100% (CI-smoke + nightly catch a regression before deploy). Known topo gap: the province TopoJSON lacks `AO` (Aosta) and `SU` (Sud Sardegna) polygons (pre-2016 naming) — those 2 provinces render uncolored though their entities are still counted. Note: enrich_geo gives region/province but **not** building-level geometry, so this powers analytics, not *new* polygons.

### The IndicePA constraint ([#2](https://github.com/mxmap-it/mxmap.it/issues/2))
IndicePA is **not** a clean source: email domains are incoherent/incomplete. The whole pipeline exists to *reprocess* it; our data is **not** a direct read. Continuous remediation is a **core functional dependency** (issue #2), disclosed in the methodology. The same dirtiness affected the territorial field — now **worked around structurally**: instead of IndicePA's incomplete/wrong `region`, the geo enrichment resolves the clean `ipa_codice_comune_istat` against the ISTAT crosswalk (see the AREA axis above).

### Gating & "one reality"
- **Historicization is gated:** the `historicize`/`build_dcat` steps in `nightly.yml` are commented out and `storia.html`/per-entity timelines are empty **until run #1** — the first clean scan after the ~700 anomalies ([#4](https://github.com/mxmap-it/mxmap.it/issues/4)) are fixed. Do not activate before then.
- **One reality:** no "reality vs methodology" distinction. Methodology freezes at run #1; everything after is real change.
- **Fotografia anticipata:** the *current* snapshot KPIs (`kpi.json`, `report.json`, `stats_current`) are **live now** (non-gated); only the *time-series* wait for run #1.

### Editorial & political constraints (public-facing)
- Lead with **segmented extremes**, not the national average (citable/actionable findings).
- Report style = **management consulting**: answer-first titles, exhibits (pie charts), recommendations with owners, **methodology in calce**, both site links. The "andamento" section is pre-built but shows **"just started"** until historicization is live.
- **Tone down politically-sensitive, small-N segments.** PA Centrale (ministries, ~52 entities) is deliberately **kept out of the headline spotlight** (`SPOTLIGHT_EXCLUDE` in `report.py`): small numbers + a charged "attack-the-state" reading. The spotlight features robust, citizen-data sectors (Istruzione, Sanità, Ricerca). Security/defense segments, if surfaced, go via **policy framing**, not loud percentages. Frame as *protecting citizens*, not *accusing institutions*.

### Per-entity & geographic SEO pages ([#15](https://github.com/mxmap-it/mxmap.it/issues/15))
- [`scripts/build_entity_pages.py`](scripts/build_entity_pages.py) emits, every nightly, **~53k static pages**: one per entity (`/ente/{provincia-sigla}/{nome-ente}/`) with full scan data + sovereignty verdict (6/4-bucket, **reusing** `sovereignty_of`/`provider_to_sov4` — never re-derive) + reliability + **nearby entities** (reputational nudge) + a "Riporta un errore" link that becomes an emphasised **"Aiutaci a risolvere l'anomalia"** CTA for anomalous/low-confidence entities; plus geographic hubs (`/aree/{regione}/{sigla}/{comune}/`), category facets (`/categoria/{cluster}/`) and lightweight domain aliases (`/dominio/{dominio}/`, canonical → entity).
- **Pure URL/slug logic in [`src/mail_sovereignty/pages.py`](src/mail_sovereignty/pages.py)** (ruff-gated, unit-tested in `tests/test_pages.py`): deterministic, **collision-free** slugs (full entity name, province namespace, stable per-bfs token on the rare namesake; 0 collisions on the real 22,987). Generator runs an integrity assert (`#entity-pages == #entities`, unique URLs, ISD in range).
- **`build_entity_pages.py` is the single sitemap authority**: writes `sitemap.xml` (a **sitemap index**) + `sitemap-core/aree/categorie` + `sitemap-enti-{regione}.xml` (×20). It replaced the standalone `build_sitemap.py` step in the nightly (the latter is kept only as an importable lib for the core page list). `<lastmod>` = `kpi.json:generated_at`.
- **Artifact-only, never committed.** The generated `/ente /aree /categoria /dominio` + `sitemap*.xml` are **git-ignored**; they ship inside the Pages artifact (deploy is decoupled from git). Covered by the `smoke` job (subset via `--limit`/`--solo-regione`). ~53k files build in ~50s.

### Build conventions & dev machine
- Logic in `src/mail_sovereignty/` (importable, ruff-gated, coverage `fail_under=84`); thin CLI in `scripts/`; viewer HTML + public artifacts at root. Every KPI generator follows the **numbers-tested** rule (below).
- Driven from a Windows laptop **without `uv`**: for `stats`-style logic (stdlib + `mail_sovereignty` only), `pip install ruff==0.15.5 pytest` into the system Python to format/lint/test locally; else round-trip via the server. **Push from the laptop** (server deploy key is read-only); PowerShell for `git push` (HTTPS creds), Bash tool for commits.
- See **`docs/ROADMAP.md`** for the issue-driven roadmap.
- **Keep the docs in sync (mandatory).** On **every feature commit or significant change**, update the relevant sections of **`README.md`** (Italian, contributor-facing: how it works, corner cases, artifacts) and **`docs/ROADMAP.md`** (phases/issues). Treat docs drift as a bug. The README A-to-Z + roadmap are how a new contributor (or Claude) onboards.

## Important: Always use `uv run`

**Never use system `python3` directly.** Always use `uv run python3` or `uv run` for all Python commands. The system Python may be an older version (e.g., 3.9) that doesn't support the type annotations and features used in this codebase.

## CRITICAL: Format Python before every commit

CI (`.github/workflows/ci.yml`) runs `uv run ruff format src tests --check` and **fails the entire CI (exit 1, pytest skipped)** if any file under `src/` or `tests/` is not ruff-formatted. Hand-written Python is almost never compliant (string wrapping, `@parametrize` layout, trailing commas), so it breaks CI every time.

**Mandatory before committing any change to `src/` or `tests/` Python:**

```bash
uv run ruff format src tests      # auto-format (mutates files)
uv run ruff check src tests       # lint (separate CI gate, also blocks)
```

Then `git add` the reformatted files. There is a committed `.pre-commit-config.yaml` (ruff hooks) — run `pre-commit install` once to enforce this automatically on `git commit`.

**Dev-machine note:** if the working machine has no `uv` (e.g. a Windows laptop driving a remote server), run the format on the server, then copy the formatted files back before committing. CI checks only `src tests`, **not** `scripts/` — do not bulk-commit a repo-wide reformat of `scripts/`.

## CRITICAL: Nightly must never break

The nightly (`.github/workflows/nightly.yml`) broke twice on the data commit/push and stopped the public site from updating. The fix is **structural** and must be preserved — never patch around it:

1. **The deploy NEVER depends on a git commit/push.** `update-data` builds the data and publishes it with `actions/upload-pages-artifact` (path `.`); the `deploy` job only runs `actions/deploy-pages` on that artifact. **Do not** re-introduce `actions/checkout` + `ref: main` in the `deploy` job — that re-couples the site to a successful push and is exactly the bug that recurred. The site must update from the in-run artifact regardless of git.

2. **Data commits are best-effort and non-blocking.** The "Commit and push data" step in `update-data` is `continue-on-error: true` with `id: commit`. A commit/push failure must **never** fail the job or block the deploy. Keep the git history of data as a side-effect, never on the critical path.

3. **Every script invoked by `nightly.yml` MUST be covered by the `smoke` job in `ci.yml`.** The `smoke` job `py_compile`s every nightly script (catches import/syntax breakage, including the network-only ones) and runs the deterministic pipeline tail (`compute_confidence`, `report_confidence`, `report_anomalies`, `validate`, `build_frontend`, `build_public_dataset`, `historicize`, `build_dcat`) on the committed `data.json`. **If you add or rename a step in `nightly.yml`, add/update it in the `smoke` job in the SAME PR.** This is what guarantees a code change can never silently break the 04:00 run — it goes red in CI first.

4. **Failures auto-open a GitHub issue (auto-detection).** A commit failure opens/updates an issue labeled `nightly-commit`; any hard step failure (build/pipeline) opens/updates one labeled `nightly-failure` via a final `if: failure()` step. Do not remove these and do not let the labels go missing (the steps create them idempotently).

5. **Before merging any change that touches the nightly or its scripts:** confirm `ci.yml`'s `smoke` job is green. Locally/on the server you can dry-run the tail with the same commands the smoke job uses (see `ci.yml`). Network steps (`fetch_indicepa`, `preprocess`, `postprocess`, `recover/finalize`, `enrich`) can't run in CI — they are only `py_compile`d; their runtime failures are transient (network) and surface via the `nightly-failure` issue, never by silently dropping the site.

## CRITICAL: KPIs & statistics — numbers must always be tested and verified

Any statistic or KPI we publish (Indice di Sovranità Digitale, CLOUD Act share, per-category breakdowns, coverage, market concentration, …) **MUST be both unit-tested and self-verified at build time**. A wrong public number is worse than a missing one — this is a transparency observatory; the figures are the product.

**Two mandatory layers for every KPI/statistics generator:**

1. **Unit tests with hand-computed expected values.** The compute logic lives in `src/mail_sovereignty/` (importable, coverage-gated by `fail_under`), **not** only in `scripts/`. A `tests/test_*.py` exercises it on a small synthetic fixture whose totals are worked out by hand, asserting **exact** values (counts, shares, index, segmentation). Reference: [`src/mail_sovereignty/stats.py`](src/mail_sovereignty/stats.py) + [`tests/test_stats.py`](tests/test_stats.py).

2. **Runtime integrity assertions on real data.** The module exposes an `assert_integrity()` that checks internal consistency — counts sum to the population, shares sum to ~100%, the headline index equals its definition, the segmentation covers everything with no oversized `other`, no `NaN`/out-of-range — and the build script calls it on **every** run, exiting non-zero on any violation. Reference: `stats.assert_integrity()`, called by [`scripts/build_stats.py`](scripts/build_stats.py). Each invariant has a test proving it actually fires on corrupted input.

**Wiring (so it runs automatically):** unit tests run in the `test` CI job (`pytest --cov`); the build script *with its integrity check* runs in the nightly **and** in the `smoke` CI job (see the rule above). A KPI that isn't covered by **both** a unit test and a runtime invariant must not ship.

**Dev-machine note:** `src/` + `tests/` are ruff-gated. The Windows laptop has no `uv`, but `ruff==0.15.5` and `pytest` can be `pip install`ed into the system Python to format/lint/test `stats`-style modules locally (logic that only imports stdlib + `mail_sovereignty`), avoiding the server round-trip. Match the pinned ruff version (see `uv.lock`).

## Commands

```bash
uv sync                # Install dependencies
uv sync --group dev    # Install with dev dependencies

# Pipeline (run in order, each reads/writes data.json)
uv run preprocess      # DNS lookups + classification (~30s for small countries)
uv run preprocess DE   # Single country
uv run preprocess DE:BY  # Single Bundesland (Bavaria)
uv run postprocess     # Overrides, SMTP banners, scraping (~5 min)
uv run validate        # Confidence scoring + quality gate

# TopoJSON split (requires mapshaper: npm install -g mapshaper)
uv run python3 scripts/split_topo.py             # Splits monolithic TopoJSON -> topo/

# Seed data fetching
uv run python3 scripts/fetch_wikidata.py DE      # Fetch Gemeinden from Wikidata
uv run python3 scripts/fetch_boundaries.py DE    # Fetch boundaries from Overpass

# Tests
uv run pytest                                    # All tests
uv run pytest tests/test_classify.py             # Single file
uv run pytest tests/test_classify.py::test_name  # Single test
uv run pytest --cov --cov-report=term-missing    # With coverage (90% threshold)

# Lint
uv run ruff check src tests
uv run ruff format src tests

# Local frontend
python -m http.server
```

## Architecture

### Pipeline Stages

All three stages operate on `data.json` at the repo root:

1. **Preprocess** (`preprocess.py`) — Loads municipalities from `data/municipalities_{cc}.json` seed files (92 countries) + `data/overrides.json`. For each municipality: extracts domain (or guesses from name with diacritics transliteration), performs async MX/SPF/CNAME/ASN/autodiscover/DKIM/TXT-verification/tenant DNS lookups via 3 resolvers (system, Google, Cloudflare) with shared cache, classifies provider, detects gateways. Concurrency: 20. Supports sub-country filtering (`DE:BY` scans only Bavaria).

2. **Postprocess** (`postprocess.py`) — Four sub-steps: (a) apply `MANUAL_OVERRIDES` dict with DNS re-lookup for domain-only overrides, (b) retry DNS for unknowns that have a domain, (c) SMTP banner check on primary MX of independent/unknown entries (deduplicated, concurrency 5), (d) scrape municipality websites for email addresses on remaining unknowns (concurrency 10). Includes TYPO3 Caesar cipher decryption for obfuscated mailto: links.

3. **Validate** (`validate.py`) — Scores each entry 0–100 based on DNS data quality (has domain, MX, SPF, provider match, etc.). Quality gate: average score ≥ 70 and ≥ 80% of entries above 80 confidence. Writes `validation_report.json` and `validation_report.csv`. Exits 1 on failure.

### Classification Hierarchy (`classify.py`)

`classify()` returns `tuple[str, str]` — `(provider, reason)`.

Priority order:
1. **Direct MX match** — MX hostname contains provider keyword
2. **CNAME resolution** — MX host's CNAME target matches a provider
3. **Known gateway look-through** — MX matches a `GATEWAY_KEYWORDS` entry (SeppMail, Barracuda, FortiMail, SecMail, D-Fence, Cisco IronPort, MailAnyone, Comendo, Heimdal, StaySecure, edelkey, ippnet, garmtech, etc.) → check SPF (only if exactly one main provider found) → autodiscover → DKIM → TXT verification → MS365 tenant (via `getuserrealm.srf`) for the actual backend provider. If no backend identified, returns "independent" with reason mentioning the gateway.
4. **Self-hosted gateway detection** — MX exists but doesn't match any provider or gateway → check DKIM for a hidden backend provider (e.g., `mail.muhu.ee` on Radicenter but DKIM → `*.onmicrosoft.com` = Microsoft)
5. **Local ISP** — MX ASN matches known ISP ASNs (`LOCAL_ISP_ASNS` in constants.py)
6. **Independent** — MX exists but doesn't match any known provider and no DKIM backend found
7. **Unknown** — No MX records found

**SPF vs DKIM for backend detection:**
- **SPF** is only used in step 3 (known gateways), and **only when exactly one main provider is found** in SPF. If multiple providers appear (e.g., Microsoft + Google), SPF is ambiguous — municipalities often include `spf.protection.outlook.com` for shared calendars or hybrid sending without hosting mailboxes on Microsoft. In ambiguous cases, fall through to autodiscover/DKIM.
- **DKIM** is used in both steps 3 and 4. DKIM CNAMEs (`selector1._domainkey.domain → *.onmicrosoft.com`) prove a Microsoft 365 tenant is configured to sign mail for that domain — this is definitive proof of mail hosting. DKIM is the most reliable signal for identifying the actual backend provider.

Provider values: `microsoft`, `google`, `aws`, `zone`, `telia`, `tet`, `elkdata`, `local-isp`, `independent`, `unknown`.

### Provider Keywords (`constants.py`)

All provider detection is keyword-based. To add a new provider:
1. Add `*_KEYWORDS` list to `constants.py`
2. Add to `PROVIDER_KEYWORDS` dict
3. Add to `SMTP_BANNER_KEYWORDS` if applicable
4. Add to the two provider-matching loops in `classify()` (steps 1 and 2)
5. Add display name mapping + color in `index.html`

### DNS Cache (`dns_cache.py`)

Per-country file-based DNS cache in `data/dns_cache/`. Domain-scoped: all DNS queries for a domain stored together. TTL: 7 days.

**Partitioned caches** for large countries: `DnsCache("DE", partition="09")` → `de_09.json`. Configured via `PARTITIONED_COUNTRIES` in `constants.py`. Currently only Germany is partitioned (16 files, one per Bundesland).

### Sub-Country Filtering

The preprocess CLI supports `CC:STATE` syntax for scanning subsets of large countries:

```bash
uv run preprocess DE:BY      # Bavaria only (abbreviation)
uv run preprocess DE:09      # Bavaria only (state code)
uv run preprocess DE:BY,NW   # Bavaria + Nordrhein-Westfalen
uv run preprocess DE:BY IT   # Bavaria + all of Italy
```

State codes are in `DE_STATES` dict in `constants.py`. When filtering, only the scanned entries are replaced in data.json — other states/countries are preserved.

### Frontend (`index.html`)

Single-page app with three admin-level views (Region/District/Municipality) and per-country lazy-loaded TopoJSON.

**Data loading:** Fetches `data-summary.json` + `topo/manifest.json` on startup. `data-detail.json` loaded in background. The manifest maps each country × level to a TopoJSON file (or an object of per-state files with bboxes for viewport loading). Files are fetched on demand and cached in memory (`topoCache`). Default view is "Districts".

**Multi-level toggle:** Three-button segmented control (top-left) switches between Region, District, and Municipality views. Each level loads different TopoJSON files per country.

**Viewport-based loading:** For countries with many municipalities (currently DE), the manifest municipality entry is an object mapping filenames to bboxes. Only files whose bbox intersects the visible viewport are fetched. On `moveend`, new files are loaded as needed.

**Per-country layers:** Each country has its own `L.geoJSON` layer stored in `countryLayers` Map. Country filter buttons add/remove layers and restyle them (active = provider-colored, inactive = gray).

**Aggregation:** At Region/District levels, multiple municipalities map to one polygon. `computeAggregation()` groups municipalities by region name or district key (AT: first 6 chars of ID, BE: first 5, DE: first 8). `matchGroupFeature()` matches dissolved TopoJSON features to groups by `name`, `name_en`, or `name:en` property.

**Popups:** Municipality level shows individual DNS data (MX, SPF, DKIM, autodiscover, TXT verifications, MS365 tenant status). Region/District level shows aggregated view: dominant provider badge, stacked provider bar chart, scrollable municipality list with provider dots.

**Statistics panel:** Always shows municipality-level data — unaffected by the level toggle.

**Gateway markers:** Shield icons only shown at municipality level.

### TopoJSON Split (`scripts/split_topo.py`)

Splits `baltic-municipalities.topo.json` (monolithic source) into per-country per-level files in `topo/`. Some countries have standalone TopoJSON files generated by `scripts/fetch_boundaries.py`.

```
topo/
  manifest.json                  # { CC: { levels, files, sizes } }
  {cc}_municipality.topo.json    # Per-country municipality boundaries (simplified 15%)
  {cc}_region.topo.json          # Dissolved by region field (simplified 8%, quantization 5k)
  {cc}_district.topo.json        # Dissolved by district key (AT, BE, DE)
  de_municipality_XX.topo.json   # Per-Bundesland DE files (16 files, viewport-loaded)
```

**Manifest format:** For most countries, `files.municipality` is a string filename. For DE, it's an object mapping filenames to bounding boxes:
```json
"municipality": {
  "de_municipality_01.topo.json": [8.3, 53.3, 11.3, 55.0],
  "de_municipality_09.topo.json": [8.9, 47.3, 13.8, 50.6]
}
```

**District key extraction:** AT → first 6 chars of ID (`AT-101`), BE → first 5 (`BE-11`), DE → first 8 (`DE-01001`).

Run: `uv run python3 scripts/split_topo.py` (requires mapshaper CLI).

### Frontend Data Split (`scripts/build_frontend.py`)

Splits `data.json` into two files for faster initial page load:

- **`data-summary.json`** — Loaded immediately. Contains fields needed for map rendering, legend, and stats.
- **`data-detail.json`** — Loaded in background after map renders. Contains popup-only fields: `mx`, `spf`, `reason`, `autodiscover`, `dkim`, `txt_verifications`, `tenant`, `smtp_software`.

Run: `uv run python3 scripts/build_frontend.py`

### DNS Module (`dns.py`)

All lookups use 3 resolvers (system, Google, Cloudflare) sharing a single `dns.resolver.Cache` to avoid redundant queries. The core function `resolve_robust(qname, rdtype)` provides universal multi-resolver fallback — all higher-level functions delegate to it. Key functions: `lookup_mx()`, `lookup_txt()` (returns SPF + TXT verification tokens in one query), `lookup_spf()`, `resolve_spf_includes()` (recursive BFS with loop detection), `resolve_mx_cnames()`, `resolve_mx_asns()`, `resolve_mx_countries()` (both via Team Cymru DNS — ASN + country code from same query), `lookup_autodiscover()`, `lookup_dkim()` (checks `selector1/selector2/google._domainkey` CNAMEs — definitive proof of mail hosting, e.g. CNAME to `*.onmicrosoft.com` = Microsoft 365), `lookup_tenant()` (queries Microsoft's `getuserrealm.srf` endpoint to detect MS365 tenants — returns `Managed` or `Federated`).

## Testing

Tests use `pytest-asyncio` (auto mode) and `respx` for HTTP mocking. DNS is mocked via `AsyncMock` on resolver objects. Fixtures in `conftest.py` provide `sample_municipality`, `sovereign_municipality`, `sample_data_json`. Coverage threshold is 90%.

## Deployment

GitHub Actions nightly workflow (`.github/workflows/nightly.yml`) runs preprocess → postprocess → validate → build (frontend, public dataset, stats, kpi, report) → **upload Pages artifact → deploy**, with a separate **best-effort** data commit. The deploy is **decoupled from the git commit** (see "CRITICAL: Nightly must never break"). Default branch is **`main`**. The custom domain is `mxmap.it` (CNAME at repo root — keep it in the deploy artifact).

**DE nightly rotation:** Germany's 11K Gemeinden are too many to scan every night. The workflow rotates 3 Bundesländer per night (6-day cycle), while all other countries are scanned every night.

## Adding a New Country

### 1. Seed data (`data/municipalities_XX.json`)

Create a JSON array of municipalities:
```json
[{"id": "XX-001", "name": "City Name", "country": "XX", "region": "Region", "domain": "city.xx", "osm_relation_id": 12345}]
```
Sources: national statistics office API for official list, Wikidata SPARQL for OSM relation IDs + domains (`P856` website, `P402` OSM relation), Nominatim as fallback for OSM IDs.

### 2. Pipeline changes

- **`preprocess.py`**: Add `"XX": "municipalities_xx.json"` to `SEED_FILES`. Add diacritics transliteration pairs. Add `"XX": [".xx"]` to `tld_map` in `guess_domains()`. Add name suffixes to strip (e.g., " kommun", " kunta").
- **`constants.py`**: Add country-specific ISP ASNs to `LOCAL_ISP_ASNS`. Use Team Cymru DNS (`origin.asn.cymru.com`) to identify ASNs of municipalities classified as "independent" — many will be local ISPs. Add gateway keywords if the country uses local email security appliances (FortiMail, SecMail, etc.). Municipal IT cooperatives (e.g., Norwegian IKT companies like Hedmark IKT, Lofoten IKT) often act as gateways — add them to `GATEWAY_KEYWORDS` or `LOCAL_ISP_ASNS` as appropriate.
- **`constants.py`**: Add `"example.xx"` to `SKIP_DOMAINS`. Add country-specific contact page paths to `SUBPAGES` if different from existing ones.

### 3. TopoJSON boundaries

**Preferred: `scripts/fetch_boundaries.py`** — Fetches from Overpass API, converts via Python GeoJSON converter, annotates with region/country, creates TopoJSON via mapshaper.
- Add country to `COUNTRY_CONFIG` with admin_level and ISO code
- Run: `uv run python3 scripts/fetch_boundaries.py XX`

**Alternative: monolithic file** — For countries in `baltic-municipalities.topo.json`, run `scripts/split_topo.py`.

Feature IDs must be `relation/XXXXX` matching `osm_relation_id` in seed data.

### 4. Frontend (`index.html`)

- Add country code to `COUNTRY_LIST` and `FLAGS` map
- Add country button in `.country-filters` div
- Add country name to `countryNames` and color to `countryColors` in stats

### 4b. Build scripts

- Add country to `COUNTRIES` and `LEVEL_MAP` in `scripts/split_topo.py`
- Re-run `uv run python3 scripts/build_frontend.py` to rebuild data-summary.json and data-detail.json

### 5. Tests

- Update `test_loads_all_countries` expected countries set
- Update `test_no_country_generates_all_tlds` expected TLDs
- Add diacritics test case in `TestGuessDomains`

### 6. Verify

Run preprocess → check "independent" municipalities → look up their MX ASNs → add missing local ISPs to `LOCAL_ISP_ASNS` → re-run. Typical pattern: first run has too many "independent", iteratively adding ISP ASNs and gateway keywords brings it down to a handful of genuinely self-hosted servers. Also check for gateway patterns in MX hostnames (e.g., `iphmx.com` = Cisco IronPort, `comendosystems.com` = Comendo) and add to `GATEWAY_KEYWORDS`.

## Scaling to Large Countries

For countries with >2,000 municipalities (currently DE with ~11K):

1. **Partitioned DNS cache** — Add to `PARTITIONED_COUNTRIES` in `constants.py` with a lambda extracting the partition key from the municipality ID.
2. **Sub-country filtering** — `uv run preprocess CC:STATE` to scan subsets.
3. **Per-state TopoJSON** — Manifest uses object format `{filename: [bbox]}` for viewport-based loading.
4. **Nightly rotation** — Scan N states per night instead of all at once.
5. **Dissolved district topo** — Generate `{cc}_district.topo.json` by dissolving municipality features by district key prefix.

### Overpass API Pitfalls

When fetching boundaries from Overpass:
- **Area ID format**: `3600000000 + relation_id` (not string concatenation `3600{id}`)
- **Rate limiting**: Overpass returns 429 after rapid queries. Use 10-15s delays between states, 90s backoff on 429.
- **Timeouts (504)**: Large states may timeout. Retry up to 3 times with 30s waits.
- **City-states**: Berlin, Hamburg, Bremen use different admin levels (4/6/9 instead of 8). Try multiple levels for states with ≤5 expected municipalities.
- **osmtogeojson strips properties**: The npm `osmtogeojson` tool doesn't preserve OSM tags as flat GeoJSON properties. Use the Python `convert_osm_to_geojson_simple()` fallback for boundary fetching.
- **osm_id format**: Feature IDs must be `relation/XXXXX` (with prefix), not bare integers. The `convert_osm_to_geojson_simple` function sets this correctly, but verify after mapshaper processing.

## Common Domain Pitfalls

Municipality domains are the most error-prone part of the data. Always verify domains via web search — do not trust automated guessing alone.

### Domain ≠ municipality name
Many municipality domains do NOT match the municipality name:
- **Corporate namesakes**: `nokia.fi` (phone company), `outokumpu.fi` (mining company), `noo.ee` (meat factory). Cities use `nokiankaupunki.fi`, `outokummunkaupunki.fi`, `nvv.ee`.
- **Tourism/portal sites**: `hiiumaa.ee` (tourism portal, municipality is at `vald.hiiumaa.ee`), `peipsi.ee` (tourism NGO, municipality is `peipsivald.ee`), `rouge.ee` (community portal, municipality is `rougevald.ee`).
- **Gaming/unrelated sites**: `siauliu.lt` was a Counter-Strike gaming site; the actual municipality domain is `siauliuraj.lt`.

### Bilingual municipalities use the minority-language domain
Swedish-speaking Finnish municipalities consistently use their **Swedish name** for domains: Kruunupyy→`kronoby.fi`, Luoto→`larsmo.fi`, Maalahti→`malax.fi`, Vöyri→`vora.fi`, Kristiinankaupunki→`krs.fi`.

### Latvian novads vs city domains
After Latvia's 2021 municipal reform, many novads (counties) have their own domains distinct from the main city: `bauskasnovads.lv` (not `bauska.lv`), `valmierasnovads.lv` (not `valmiera.lv`), `ventspilsnd.lv` (not `ventspils.lv` which is the city). The seed data domain with no MX causes the pipeline to guess the city domain instead — always set the correct novads domain in seed data.

### Norwegian municipality domains
Norwegian municipalities mostly use `name.kommune.no`, but exceptions exist: `ha.no` (Hå), `sarpsborg.com` (Sarpsborg), `voss.herad.no` (Voss herad), `mgk.no` (Midtre Gauldal), `ahk.no` (Aurskog-Høland). Sami-language municipalities may use `.suohkan.no` for their website but `.kommune.no` for email (e.g., Kautokeino). Post-merger municipalities sometimes retain stale "nye" (new) domains — always verify the current domain has MX records.

### Website domain ≠ email domain
Some municipalities use different domains for their website and email. When the seed data domain has no MX records, the pipeline falls back to guessing from the municipality name, which may find a wrong domain. Always check MX records for the seed data domain; if empty, search for the actual email domain.

### Verification approach
For each country, web-search every municipality to verify domains. Use `dig +short domain MX` to confirm MX records exist. The `MANUAL_OVERRIDES` dict in `postprocess.py` handles cases where the guessed domain is wrong but the seed data domain is correct for the website (overrides trigger DNS re-lookup on the corrected domain).

## Gateway Detection Patterns

Municipalities often use local email security gateways (FortiMail, SecMail, D-Fence, Barracuda, etc.) that relay to cloud providers. The pipeline detects these via `GATEWAY_KEYWORDS` in `constants.py`. When a gateway is detected, the pipeline checks SPF → autodiscover → DKIM to identify the backend provider.

Small local IT companies can also act as gateways (e.g., `edelkey.net` for Helsinki, `ippnet.fi` for Parkano, `garmtech.com` for Saulkrasti). Add these to `GATEWAY_KEYWORDS` when discovered — otherwise they get classified as "independent" instead of the actual backend provider.

**Gateway SPF ambiguity:** When looking through a gateway, SPF is only trusted if exactly one main provider keyword is found. Many municipalities have multiple providers in SPF (e.g., Microsoft for mailboxes + Google for transactional email), making SPF ambiguous. In those cases, the pipeline falls through to autodiscover, DKIM, TXT verification, and MS365 tenant detection for a definitive answer. If none identify a backend, the municipality is classified as "independent" with a reason mentioning the gateway name.

**MS365 tenant detection:** `lookup_tenant()` queries Microsoft's `login.microsoftonline.com/getuserrealm.srf` endpoint. A `Managed` or `Federated` response proves an MS365 tenant exists for that domain. Used as a last-resort signal in gateway look-through (after DKIM and TXT verification) — not used for self-hosted MX since having a tenant doesn't prove mailboxes are hosted there.

**DKIM is the most reliable signal** for identifying the backend provider. A CNAME at `selector1._domainkey.domain` pointing to `*.onmicrosoft.com` is definitive proof of Microsoft 365, even when MX and SPF point elsewhere.

**Norwegian IKT cooperatives:** Many Norwegian municipalities share IT infrastructure via regional IKT companies (Hedmark IKT, Lofoten IKT, IKT Sunnmøre, etc.). These appear as shared MX hosts or DKIM tenants (e.g., `lofotenikt.onmicrosoft.com`). They typically relay to Microsoft 365.

## Country-Specific Notes

Per-country implementation guides are in `docs/countries/`. These were used during initial setup and may be outdated, but contain useful context about domain pitfalls, ISP discovery, and admin level choices. Available: Andorra, Australia, Austria, Belgium, Czechia, Denmark, Germany, Luxembourg, New Zealand, Norway, Sweden. Use these as examples when adding new countries.
