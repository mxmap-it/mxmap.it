# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MX Map is a DNS-based email provider classifier for European municipalities (92 countries, ~20,000 municipalities). It runs a 3-stage async pipeline that produces `data.json`, which powers an interactive Leaflet.js map showing where municipalities host their official email. Forked from [mxmap.ch](https://mxmap.ch) (Swiss municipalities). Covers all 27 EU member states plus 20 non-EU European countries.

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

GitHub Actions nightly workflow (`.github/workflows/nightly.yml`) runs preprocess → postprocess → validate → commit data.json → deploy to GitHub Pages. Quality gate failure creates a GitHub issue. Default branch is `baltic`.

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
