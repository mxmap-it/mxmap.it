# Add Italy to MX Map (mxmap.it)

You are extending the multi-country MX Map upstream to add a complete Italian dataset, deployed at `mxmap.it`.
Read `CLAUDE.md` first for project architecture and the "Adding a New Country" guide.

## Scope decision: territorial Phase A only (Regioni / Province / Comuni)

mxmap.it focuses exclusively on Italian **territorial public administrations** — the three levels of government with native polygon representation:

| Level | IndicePA `Codice_categoria` | Approx final count |
|---|---|---:|
| **Regioni** | `L4` (filtered) | ~22 (20 regioni + 2 province autonome) |
| **Province** | `L5` + `L45` | ~107 (~93 province + 14 città metropolitane) |
| **Comuni** | `L6` (filtered) | ~7,900 |

Treating **città metropolitane** as province-equivalent (post-Delrio 2014, they replaced the old province in 14 metro areas).

**Out of scope for v1** (revisit in dedicated sessions, see `Future Work` below):
- Schools, healthcare, ministries, ordini professionali, gestori pubblici servizi, stazioni appaltanti, partecipate, consorzi, unioni di comuni, comunità montane.
- **PEC (legal email)** — never used to derive the MX target. Italian PEC infrastructure is dominated by 5–6 providers (Aruba PEC, Poste, InfoCert, Register.it, Namirial, LegalMail) and does not represent the office email infrastructure we want to classify.

## Frontend scope: Italy-only

mxmap.it shows only Italy, in **Italian primary / English secondary**. The codebase remains multi-country compatible upstream — the Italy-only behaviour is a build-time configuration of `index.html`, not a fork of the engine.

## Repo
- Origin: `https://github.com/fpietrosanti/mxmap.it`
- Upstream reference: `https://github.com/livenson/mxmap` (Baltic fork, used as starting point)
- Branch strategy: work on `italy` branch initially.

## Phase 1: Seed data

### Source: IndicePA (CKAN JSON API, NOT XLSX)

AgID's daily-updated registry of Italian public administrations. CC-BY 4.0. 23,683 entities total; we filter to ~8,000.

**Use the CKAN datastore JSON API**, not the XLSX file:

```
GET https://indicepa.gov.it/ipa-dati/api/3/action/datastore_search
    ?resource_id=d09adf99-dc10-4349-8c53-27b1e5aa97b6
    &filters={"Codice_Categoria":"L6"}
    &limit=10000
    &offset=0
```

Paginate via `offset` until the response's `result.records` is shorter than `limit`. Repeat for `L4`, `L5`, `L45`.

The dataset resource ID `d09adf99-dc10-4349-8c53-27b1e5aa97b6` is stable; if it changes, look it up via `package_show?id=enti`.

### Per-row fields used

From each IndicePA record we keep:

| Field | Use |
|---|---|
| `Codice_IPA` | Stable internal identifier (audit / debug only) |
| `Denominazione_ente` | Display name |
| `Codice_Categoria` | Level routing (L4/L5/L45/L6) |
| `Codice_ISTAT` | Region or province ISTAT code (depending on level) |
| `Codice_comune_ISTAT` | Comune ISTAT code (6-digit) |
| `Sito_istituzionale` | **Sole source of the email domain** |
| `Ente_in_liquidazione` | If `"S"`, drop the row |

PEC fields (`Mail{n}` where `Tipo_Mail{n} = "pec"`) are **explicitly never used**.

### Domain extraction

From `Sito_istituzionale` only:

1. `urlparse(value).hostname.lower()`
2. Strip leading `www.`
3. Validate hostname syntax (regex)
4. **Accept any TLD verbatim.** Do NOT filter by `.it`. Italian PAs can and do use other TLDs (`.gov.it`, `.eu`, `.org`, `.com`, `.net`, custom domains under non-Italian registries). The IndicePA `Sito_istituzionale` field is authoritative — whatever TLD it reports is the domain we MX-classify.
5. **If empty/invalid: drop the entity.** Do NOT fall back to PEC, do NOT name-guess. Italian PA name-to-domain mapping is too irregular for reliable guessing — silent guessing pollutes the dataset with corporate namesakes.

96.5% of the IndicePA dataset has `Sito_istituzionale` populated, so coverage will be high.

### Filtering "consorzi e associazioni" out

The IPA categories `L4` and `L6` include consorzi/associazioni alongside the true entities. These don't have a polygon and shouldn't appear on the map. Detection heuristics, in order:

1. **Whitelist by ISTAT code** — the official ISTAT region/comune lists are the source of truth. An entity whose `Codice_ISTAT` is not in the official ISTAT list is a consorzio/associazione → drop.
2. **Name regex fallback** — drop entities whose `Denominazione_ente` matches `(?i)consorzio|associazione|unione|comunità\s+montana`.
3. **Drop `Ente_in_liquidazione = "S"`** unconditionally.

Implementation: download the official ISTAT territorial codes list once (`https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv`) and use it as the canonical ID set.

### OSM relation IDs (cross-reference build)

mxmap requires `osm_relation_id` to join seed rows to TopoJSON polygons. IndicePA does not include OSM IDs, so we build a one-time crosswalk:

**Regioni** (~22): hand-curated map of ISTAT region code (`01..20`, plus `21`/`22` for Trento and Bolzano) → OSM relation ID. Verify each against current OSM data.

**Province + Città Metropolitane** (~107): Wikidata SPARQL joining provinces (`Q16110`) and città metropolitane (`Q22863014`) with their OSM relation IDs (`P402`) and ISTAT province codes. Cross-reference by ISTAT.

**Comuni** (~7,900): Wikidata SPARQL on `wdt:P31 wd:Q747074` (comune italiano) with `wdt:P402` (OSM) and `wdt:P935` or equivalent ISTAT code property. Verify completeness — fall back to Overpass query for `admin_level=8` relations in Italy with `ref:ISTAT` tag for any missing IDs.

The crosswalk lives in `data/it_istat_to_osm.json` and is rebuilt only when OSM relation IDs change (rare).

### IDs and seed format

ID convention with level prefix:

| Level | Format | Example |
|---|---|---|
| Regione | `IT-REG-{NN}` | `IT-REG-12` (Lazio) |
| Provincia | `IT-PRO-{NNN}` | `IT-PRO-058` (Roma) |
| Città Metropolitana | `IT-CMM-{NNN}` | `IT-CMM-258` |
| Comune | `IT-COM-{NNNNNN}` | `IT-COM-058091` (Roma) |

Seed file `data/municipalities_it.json`:

```json
[
  {
    "id": "IT-COM-058091",
    "name": "Roma",
    "country": "IT",
    "region": "Lazio",
    "domain": "comune.roma.it",
    "osm_relation_id": 41485
  },
  {
    "id": "IT-PRO-058",
    "name": "Provincia di Roma",
    "country": "IT",
    "region": "Lazio",
    "domain": "cittametropolitanaroma.it",
    "osm_relation_id": 40784
  }
]
```

(Schema is mxmap's existing seed format — do not introduce new fields. Level is encoded in the `id` prefix.)

### Italian domain conventions

Italian PA domains follow several patterns under ANCI / Codice Amministrazione Digitale guidance, **but no naming convention is mandatory** — an Italian PA can use any TLD and any structure. Common patterns observed:

| Pattern | Example | Notes |
|---|---|---|
| `comune.{name}.it` | `comune.roma.it`, `comune.milano.it` | Most common at comune level |
| `comune.{name}.{prov}.it` | `comune.firenze.fi.it` | Smaller comuni, two-letter province code |
| `cittametropolitana{name}.it` | `cittametropolitanaroma.it` | Città metropolitane, modern |
| `provincia.{name}.it` | `provincia.tn.it`, `provincia.fi.it` | Province (often two-letter PA code, not full name) |
| `regione.{name}.it` | `regione.lazio.it`, `regione.toscana.it` | Regioni (full name) |
| `{name}.it` | `bologna.it`, `napoli.it` | A few large cities — verify ownership |
| `*.gov.it` | `agid.gov.it`, `governo.it` | Central-government second-level domain (rare for territorial PA) |
| Other TLDs | `.eu`, `.org`, `.com`, `.net`, custom branded | Occur for some PAs — accept whatever IndicePA reports |

**Do not assume `.it`** — the Italian PA naming patterns are conventions, not rules. The `Sito_istituzionale` field is the single source of truth: parse the hostname and use it as-is, regardless of TLD.

**Avoid name-guessing**: corporate namesakes are common (`milano.it`, `bologna.it`, `verona.it` are all corporate). Always source from `Sito_istituzionale`.

**Diacritics**: Italian uses `à è é ì ò ù`. Domain transliteration drops diacritics (`L'Aquila → laquila`, `Forlì → forli`), but with `Sito_istituzionale` as the source we never need to guess from name.

## Phase 2: Pipeline changes

### preprocess.py

- Verify `"IT": "municipalities_it.json"` is in `SEED_FILES` (currently present from Wikidata-seeded baseline; we replace its content, not its key).
- Italian diacritics in transliteration table: `("à","a"), ("è","e"), ("é","e"), ("ì","i"), ("ò","o"), ("ù","u"), ("'","")`. Avoid pairs that conflict with other languages already in the table.
- `tld_map` has `"IT": [".it"]` — irrelevant for our path because we **disable name-based domain guessing for IT entries entirely** (Italian PA domains are not constrained to `.it`, so guessing-by-TLD-suffix would be incorrect).
- **Disable name-based domain guessing for IT entries** if `domain` is null in the seed: emit `unknown` rather than guessing. This is a safer default for Italy than the existing TLD-guessing path.

### constants.py

- Add to `SKIP_DOMAINS`: `"esempio.it"`, `"example.it"`, `"www.gov.it"`.
- Add Italian contact-page paths to `SUBPAGES`: `"/contatti"`, `"/urp"`, `"/contattaci"`, `"/amministrazione-trasparente/organizzazione/articolazione-degli-uffici"`.
- Add Italian provider keywords (see Phase 3).

### tests

- Update `test_loads_all_countries` to ensure `"IT"` is in expected set.
- Update `test_no_country_generates_all_tlds` to include `"it"`.
- Add an Italian diacritic test (e.g., `"L'Aquila" → "laquila"`).

## Phase 3: ISP and provider discovery (iterative)

### Italian email/IT landscape

| Provider category | Players | mxmap label |
|---|---|---|
| Italian hosting/cloud | Aruba, Seeweb, Register.it, Namirial, InfoCert | new keywords (see below) |
| Italian ISPs (TLC) | TIM, Vodafone, Wind Tre / Fastweb, Tiscali, Iliad | `LOCAL_ISP_ASNS` |
| Cloud hyperscalers | Microsoft 365, Google Workspace, AWS | existing `microsoft`, `google`, `aws` |
| Email security gateways (IT-specific) | Libraesva (Pisa), DataLab, Iconto | `GATEWAY_KEYWORDS` |

### Italian provider keywords (initial seed)

Add to `constants.py`:

```python
ARUBA_KEYWORDS = ["aruba.it", "arubabusiness.it", "staff.aruba.it"]
REGISTER_IT_KEYWORDS = ["register.it", "register-it"]
SEEWEB_KEYWORDS = ["seeweb.it", "seeweb.com"]
INFOCERT_KEYWORDS = ["infocert.it", "infocert.eu"]
NAMIRIAL_KEYWORDS = ["namirial.com", "namirial.it"]
```

Wire each into `PROVIDER_KEYWORDS` and the two provider-matching loops in `classify()`. Display labels (Italian-first) in `index.html`:
- `aruba` → "Aruba"
- `register-it` → "Register.it"
- `seeweb` → "Seeweb"
- `infocert` → "InfoCert"
- `namirial` → "Namirial"

### Italian ISP ASNs (initial seed list)

Add to `LOCAL_ISP_ASNS` in `constants.py`:

| ISP | ASN | Notes |
|---|---|---|
| TIM / Telecom Italia | 3269, 6664 | Largest Italian ISP, hosts many PA |
| Vodafone Italia | 30722 | |
| Wind Tre | 1267 | |
| Fastweb | 12874 | (Wind Tre group post-2025 merger) |
| Tiscali | 8612 | |
| Iliad Italia | 50318 | |
| Aruba | 31034, 62076 | Hosting/PEC |
| Seeweb | 35369 | |
| Register.it (Dada/TeamSystem) | 39729 | |
| InfoCert | 39257 | |
| Namirial | (lookup at discovery time) | |

These are starting points — coverage is incomplete. The discovery loop (below) will identify more.

### Italian regional in-house ICT companies (società in-house pubbliche)

Italy has a network of **publicly-owned regional ICT companies** that host IT infrastructure (including email) for the regione and many of its comuni. Analogous to Germany's Vitako-affiliated providers (Dataport, AKDB, ekom21). These do **not** appear in AIIP or AGCOM registries — they are public-sector entities, not commercial ISPs — so they need to be seeded explicitly.

Add the following to `LOCAL_ISP_ASNS` (ASN to be confirmed via PeeringDB at discovery time) **and** add their hostname patterns to `GATEWAY_KEYWORDS` so MX hosts owned by these companies are correctly attributed to the regional public infrastructure rather than classified as `independent`:

| Company | Coverage | Hostname patterns |
|---|---|---|
| **Lepida ScpA** | Emilia-Romagna | `lepida.it`, `lepida.network`, `lepida.net` |
| **ARIA SpA** | Lombardia | `ariaspa.it`, `aria.lombardia.it` |
| **CSI Piemonte** | Piemonte, Valle d'Aosta | `csi.it`, `csipiemonte.it` |
| **Insiel SpA** | Friuli Venezia Giulia | `insiel.it` |
| **Liguria Digitale ScpA** | Liguria | `liguriadigitale.it` |
| **PuntoZero ScarL** (merger of Umbria Digitale + Umbria Salute, eff. 2022-01-01) | Umbria | `puntozeroscarl.it`, `umbriadigitale.it` (legacy) |
| **Sardegna IT Srl** | Sardegna | `sardegnait.it` |
| **Trentino Digitale** | Provincia Autonoma Trento | `trentinodigitale.it` |
| **PA Digitale Alto Adige (SIAG)** | Provincia Autonoma Bolzano | `siag.it`, `provinz.bz.it` (DKIM signs many comuni) |
| **Pasubio Tecnologia Srl** | Veneto (Vicenza, Verona, Padova) — 40+ comuni-soci | `pasubiotecnologia.it` |
| **Sogei SpA** | nazionale (Ministero Economia, Agenzia Entrate, MEF perimeter) | `sogei.it` |

These companies typically operate as **gateways with cloud backends** (M365 or self-hosted) rather than as the email backend itself. Treat them like the Norwegian IKT cooperatives in `CLAUDE.md` — when a regional in-house MX is detected, the pipeline should look through to the actual backend (M365 tenant, DKIM signature, etc.) and surface the regional company in the entry's `reason` field. Display label suggestion: `regional-public` (e.g., "ICT regionale pubblico — Lepida").

Add to `constants.py`:

```python
ITALIAN_PUBLIC_ICT_KEYWORDS = [
    "lepida.it", "lepida.network", "lepida.net",
    "ariaspa.it",
    "csi.it", "csipiemonte.it",
    "insiel.it",
    "liguriadigitale.it",
    "puntozeroscarl.it", "umbriadigitale.it",
    "sardegnait.it",
    "trentinodigitale.it",
    "siag.it", "provinz.bz.it",
    "pasubiotecnologia.it",
    "sogei.it",
]
```

Wire into `GATEWAY_KEYWORDS` so look-through resolves the actual backend provider. ASNs for each — confirm via PeeringDB / RIPE in the discovery loop and add to `LOCAL_ISP_ASNS` then.

### Italian private PA IT contractors (separate category)

A handful of **private** Italian IT companies host email for many Italian PAs through outsourcing/managed-services contracts. They are NOT publicly owned — keep them analytically distinct from the in-house regional companies above. They will surface in the discovery loop and are worth seeding so they're attributed correctly rather than as `independent`:

| Company | Ownership | Hostname patterns |
|---|---|---|
| **Engineering Ingegneria Informatica SpA** | Listed (Bain Capital / NB Renaissance owned, post-2020 delisting) | `eng.it`, `engineering.it`, `eng.engineering.it` |
| **Almaviva SpA** | Privately held (Tripi family) | `almaviva.it`, `almavivaitalia.it` |

Display label suggestion: `pa-contractor-private` (e.g., "Contractor PA privato — Engineering"). Distinct from `regional-public` so the map can visually differentiate "public sovereign infrastructure" from "private outsourcer".

Add to `constants.py` as a separate keyword list:

```python
ITALIAN_PRIVATE_PA_CONTRACTOR_KEYWORDS = [
    "eng.it", "engineering.it",
    "almaviva.it", "almavivaitalia.it",
]
```

Wire into `GATEWAY_KEYWORDS` (same look-through behaviour as the public ICT companies — find the actual backend provider). The classification *label* is what differs.

The discovery loop is likely to surface other private PA outsourcers — add them here as they appear, with a brief ownership note.

### Italian gateway keywords (initial)

Add to `GATEWAY_KEYWORDS`:
- `libraesva` — Italian email security appliance, Pisa-based, common in Italian PAs
- `datalab` — Italian email security
- `iconto` — Italian gateway (less common)

### Discovery loop

1. Run `uv run preprocess IT`
2. Count `independent` and `unknown` — first-run estimate: 40–60%
3. For each `independent` entry, lookup MX ASN via Team Cymru (`origin.asn.cymru.com`)
4. Group by ASN; identify Italian-specific providers; add ASN to `LOCAL_ISP_ASNS` or hostname pattern to `GATEWAY_KEYWORDS`
5. Inspect MX hostnames for gateway patterns (e.g., `*.aruba.it`, `*.libraesva.com`, `*.seeweb.it`)
6. Re-run; repeat until `independent` count stabilizes

### Future Work — comprehensive ISP scrape (separate session)

The ASN seed list above is heuristic. To improve coverage materially, a follow-up dedicated session should:

1. **Scrape AIIP members** — `https://aiip.it/` (Italian Internet Service Providers Association) — extract every member's company name, then resolve each to AS numbers via PeeringDB / RIPE.
2. **Scrape AGCOM TLC operator registry** — `https://www.agcom.it/operatori-di-comunicazioni-elettroniche` — full list of authorised electronic-communications operators.
3. **Cross-reference with PeeringDB** — for each operator, fetch all announced ASNs.
4. Expand `LOCAL_ISP_ASNS` with the full set; produce a separate PR with the changes for review.

Treat as a self-contained data-gathering subproject — DO NOT bundle into the initial Italy launch.

## Phase 4: Domain verification

After ISP discovery stabilizes:

1. List remaining `independent` and `unknown` entries
2. Spot-check ~30 random entries by visiting `Sito_istituzionale`
3. Compare `dig +short {domain} MX` to the actual website
4. Fix seed data or add `MANUAL_OVERRIDES` for known mismatches in `postprocess.py`

## Phase 5: Postprocess + validate

```bash
uv run preprocess IT
uv run postprocess IT
uv run validate
```

Italian quality-gate target: average score ≥ 70, ≥ 80% above 80 confidence — same as upstream.

## Phase 6: TopoJSON boundaries

Italy already has partial TopoJSON in the repo:
- `topo/it_municipality.topo.json` — verify completeness vs ~7,900 comuni
- `topo/it_region.topo.json` — verify completeness vs 22 regioni (20 + 2 prov. autonome)

**Need to fetch**: `topo/it_province.topo.json` (~107 features, includes città metropolitane).

```python
# scripts/fetch_boundaries.py — add to COUNTRY_CONFIG
"IT": {
    "admin_level": 6,  # province / città metropolitana
    "iso_code": "IT",
}
```

```bash
uv run python3 scripts/fetch_boundaries.py IT
```

Verify feature IDs are `relation/{N}` matching `osm_relation_id` in seed data. Mind the Overpass pitfalls listed in `CLAUDE.md`:
- Area ID format: `3600000000 + relation_id`
- Rate limiting: 10–15s between states, 90s on 429
- Italy is moderately sized → expect 3–5 minute fetch per level

Update `topo/manifest.json` to reference all three Italian files.

## Phase 7: Frontend (Italy-only build)

mxmap.it is Italy-only. The codebase remains multi-country — this is a build-time configuration:

### `index.html` config flag

Introduce a build-time flag (e.g., a `<script>` block at the top of `index.html` that's swapped at deploy time, or a JSON config loaded first):

```js
const COUNTRY_LIST = ["IT"];        // Italy-only
const DEFAULT_LEVEL = "municipality"; // Comuni view by default
const DEFAULT_CENTER = [42.5, 12.5];
const DEFAULT_ZOOM = 6;
const UI_LANGUAGES = ["it", "en"];
const DEFAULT_LANGUAGE = "it";
```

### UI translations

| English (upstream) | Italian (mxmap.it) |
|---|---|
| Region | Regioni |
| District | Province |
| Municipality | Comuni |
| Provider | Provider |
| independent | Indipendente / Self-hosted |
| local-isp | ISP italiano |
| unknown | Sconosciuto |
| What is this? | Cos'è questa mappa? |
| Statistics | Statistiche |

Implement as a `translations` object keyed by `lang` + DOM-attribute swap on toggle. A single floating IT/EN toggle in the corner of the map.

### Hide multi-country UI

- Remove or hide the country-filter buttons (Italy-only)
- Stats panel shows Italian-only breakdown
- Map default-frame on Italy bbox

## Phase 8: Final verification

1. Build: `uv run python3 scripts/build_frontend.py`
2. Local server: `python -m http.server 8000`
3. Verify in browser:
   - Map loads centered on Italy at zoom 6
   - Three-level toggle works (Regioni / Province / Comuni)
   - Italian/English language toggle works
   - Spot-check 10 random popups (mix of provider colours): provider classification looks plausible
   - Stats panel shows Italian-only data
   - No console errors / missing TopoJSON files
4. Tests: `uv run pytest`

## Phase 9: Deployment

### Server
- Host: `51.158.36.151` (Scaleway baremetal, fr-par-2 — same as `selective-copy-trader`)
- SSH user: `mxmap.it` (uid 1001, home `/home/mxmap.it`, SSH key already deployed)
- HTTP server: existing `mini_httpd` on port 80 (running as `nobody`)
- Initial deployment: serve at the bare IP `http://51.158.36.151/` (or `http://51.158.36.151/mxmap/`)
- Domain `mxmap.it` is **deferred to a later step**

### One-time setup (as ubuntu, sudo NOPASSWD)

1. Install `uv` for the `mxmap.it` user:
   ```
   sudo -u mxmap.it bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'
   ```
2. Clone the repo into `/home/mxmap.it/mxmap`:
   ```
   sudo -u mxmap.it git clone https://github.com/fpietrosanti/mxmap.it.git /home/mxmap.it/mxmap
   ```
3. `uv sync` once to populate `.venv`:
   ```
   sudo -u mxmap.it bash -lc 'cd /home/mxmap.it/mxmap && ~/.local/bin/uv sync'
   ```
4. Configure mini_httpd to serve `/home/mxmap.it/public_html` at the IP. Inspect `/etc/mini-httpd.conf`; either:
   - Change `dir` to `/home/mxmap.it/public_html`, or
   - Add a virtual-host directory mapping using mini_httpd's `-v` host-dir feature later when DNS is in place.
   - Ensure `nobody` has read permissions on `/home/mxmap.it/public_html`.

### Deploy workflow (after each pipeline run)

Static artifacts to publish:
- `index.html`
- `data-summary.json`, `data-detail.json`
- `topo/manifest.json`, `topo/it_region.topo.json`, `topo/it_province.topo.json`, `topo/it_municipality.topo.json`
- Translations JSON (if extracted from `index.html`)

Sequence:
```bash
# On dev machine
uv run python3 scripts/build_frontend.py
rsync -av --delete \
    index.html data-summary.json data-detail.json \
    topo/manifest.json topo/it_*.topo.json \
    mxmap.it@51.158.36.151:~/public_html/
```

### Pipeline on the server

The pipeline runs on the server, not locally, so DNS results reflect the server's vantage point.

```bash
ssh mxmap.it@51.158.36.151
cd ~/mxmap
~/.local/bin/uv run preprocess IT
~/.local/bin/uv run postprocess IT
~/.local/bin/uv run validate
~/.local/bin/uv run python3 scripts/build_frontend.py
cp index.html data-*.json public_html/
cp topo/manifest.json topo/it_*.topo.json public_html/topo/
```

### Scheduling (Phase 9b — set up only after manual run is green)

Weekly cadence (decided in this proposal). Cron under `mxmap.it`:

```cron
# Sunday 03:00 Europe/Rome — preprocess + postprocess + validate + publish
0 3 * * 0 cd /home/mxmap.it/mxmap && /home/mxmap.it/.local/bin/uv run preprocess IT && /home/mxmap.it/.local/bin/uv run postprocess IT && /home/mxmap.it/.local/bin/uv run validate && /home/mxmap.it/.local/bin/uv run python3 scripts/build_frontend.py && cp index.html data-*.json /home/mxmap.it/public_html/ && cp topo/manifest.json topo/it_*.topo.json /home/mxmap.it/public_html/topo/ >> /home/mxmap.it/cron.log 2>&1
```

Set `TZ=Europe/Rome` in the crontab.

### Domain + TLS (deferred)

When `mxmap.it` DNS is pointed at `51.158.36.151`:
- Option A: front mini_httpd with **Caddy** as reverse proxy on 443 (auto Let's Encrypt). mini_httpd stays on 80 for the trader / other content.
- Option B: drop mini_httpd, run Caddy as the sole web server.
- Decide in a separate session; do not block the IP-based launch.

## Do NOT
- Push without review
- Push to `main` (use `italy` branch first)
- Include PEC domains in MX classification
- Include schools, hospitals, ministries, ordini, gestori, partecipate, consorzi, unioni, comunità montane in v1
- Drop the codebase's multi-country support — only the deployed frontend is Italy-only
- Run the AIIP / AGCOM scrape in this session — it's a separate, dedicated task
- Configure DNS or TLS for `mxmap.it` in this session — deferred to a follow-up

## Future Work (parking lot)

1. **AIIP + AGCOM ISP scrape** — comprehensive Italian ISP/telco ASN list (Phase 3 enhancement)
2. **`mxmap.it` DNS + TLS** — switch from bare-IP to domain-served with Let's Encrypt
3. **Tier 2 expansion** — Sanità, Stato centrale, Università, Camere/Ordini, Ambiente, Welfare, Cultura, Ricerca, Trasporti (point-marker frontend feature required)
4. **Schools (L33)** — only after MIUR-domain monoculture risk is investigated; likely behind a default-OFF toggle
5. **Tier 3** — Gestori, Stazioni Appaltanti, Partecipate — review value vs. noise after Tier 1+2 is live
