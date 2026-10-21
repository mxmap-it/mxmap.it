# STATE — riprendere il progetto da qualunque computer

> Regola di progetto (globale, 2026): **resumable by design** — un `git clone`
> di questo repo deve bastare per riprendere il lavoro. Questo file è
> l'entrypoint: cosa leggere, come fare bootstrap, cosa NON è nel clone,
> dove vive lo stato vivo. Va aggiornato quando cambia lo stato DURABILE del
> progetto (decisioni, pendenze, architettura) — non per i numeri quotidiani,
> che vivono nei dati committati dalla nightly e nelle issue.

## 1. Cosa leggere, in ordine

1. **`CLAUDE.md`** — il cervello operativo: pipeline, regole CRITICAL
   (nightly-never-break, KPI testati, basemap keyless, format-before-commit),
   architettura, comandi.
2. **`docs/countries/ITALY.md`** — piano di riferimento del progetto italiano
   (IndicePA, tier di recupero, server, roadmap).
3. **Issue aperte** (`gh issue list`) — lo stato vivo delle pendenze; le
   failure notturne si auto-documentano lì (label `nightly-failure`,
   `nightly-commit`, `basemap`, `quality-gate`).
4. `docs/ROADMAP.md` e gli altri design doc in `docs/` per i singoli temi.

## 2. Bootstrap da zero (macchina nuova)

Prerequisiti: `git`, [`uv`](https://docs.astral.sh/uv/), `gh` (autenticato:
`gh auth login`, serve lo scope `workflow` per toccare i file in
`.github/workflows/`). Su Windows: sempre `PYTHONUTF8=1` e Git Bash per i
comandi (mai PowerShell).

```bash
git clone https://github.com/mxmap-it/mxmap.it.git
cd mxmap.it
uv sync --group dev
uv run ruff check src tests && uv run ruff format src tests --check
uv run pytest            # suite completa (coverage gate 90%)
```

Senza nemmeno `uv` (solo python3 + pytest) funzionano già: i test puri
(`PYTHONPATH=src pytest tests/test_geo.py tests/test_basemap.py
tests/test_data_invariants.py tests/test_pages.py`) e gli script stdlib
della pipeline sui dati committati (`python scripts/build_kpi.py --country IT`,
`build_stats.py`, `report_it_by_cluster.py`, `indexnow_submit.py --dry-run`).

**La prova che il clone basta è la CI stessa**: ogni push esegue su un runner
vergine clone → `uv sync` → ruff → pytest → coda deterministica della
pipeline sui dati committati (job `smoke` di `ci.yml`). Verificato anche a
mano il 2026-10-21 (34 test + build_kpi/build_stats verdi da un clone nudo).

## 3. Cosa NON è nel clone (e dove serve)

Il repo non contiene segreti. Per le operazioni che li richiedono:

| Cosa | Serve per | Dove si ottiene |
|---|---|---|
| `gh auth` (scope `workflow`) | push ai workflow, issue, dispatch dei run | `gh auth login` con l'account GitHub |
| Chiave SSH per `mxmap.it@51.158.36.151` | one-off lunghi sul server (vedi §5) | portachiavi di Fabio |
| `config/bounce.toml` | bounce-verifier (design doc, non in produzione) | da ricreare secondo `docs/BOUNCE_VERIFIER_DESIGN.md` |
| Accesso TopDNS | DNS di mxmap.it (apex → GitHub Pages; MAI Cloudflare) | account di Fabio |
| Google Search Console / Bing WT | monitoraggio indicizzazione | account di Fabio |

La chiave IndexNow NON è un segreto (pubblica by design, file `<key>.txt`
alla root). Niente API key di terze parti: il basemap è keyless per policy
(vedi CLAUDE.md §Basemap).

## 4. Dove gira cosa (nessun processo locale da ricostruire)

Tutta l'operatività quotidiana è su **GitHub Actions** — un PC nuovo non deve
avviare niente:

- `nightly.yml` (04:00 UTC): refresh IndicePA + crosswalk ISTAT + scan DNS +
  recovery + build + **deploy via artifact** (disaccoppiato dal commit git) +
  commit dati best-effort + job `basemap-battery` + auto-issue sulle failure.
- `ci.yml`: test + smoke della nightly su ogni push/PR.
- `deploy.yml`: pubblica su GitHub Pages (modalità **workflow**, mai branch).
- `indexnow.yml` (12:30 UTC): fetta rotante quotidiana a IndexNow.
- `upstream-watch.yml` (settimanale): digest dei commit di
  `mxmap/secassure2026` in issue `upstream-watch`.

Il **server** (`mxmap.it@51.158.36.151`, già documentato in ITALY.md) serve
solo per one-off lunghi che non devono morire col laptop (es. il re-geocoding
Nominatim 2026-09-29, in tmux). Non ospita servizi di mxmap.it: se
irraggiungibile, il sito e la pipeline non ne risentono.

## 5. Regole operative da non riscoprire a proprie spese

- **Restore, don't regenerate**: gli artefatti costosi (es.
  `data/it_istruzione_points.json`, geocoding Nominatim) sono committati;
  se un input manca, si RIPRISTINA dalla storia git o dalle copie sul
  server, mai si rigenera da zero. Guardie anti-shrink in
  `aggregate_istruzione_per_comune.py` e `geocode_istruzione.py` +
  pavimenti in `tests/test_data_invariants.py`.
- **Batteria basemap** (`tests/test_basemap.py`): il basemap è OSM keyless
  con riserva Esri e failover runtime; la batteria gira in CI e ogni notte.
  Mai reintrodurre provider con API key.
- Ogni nuovo step della nightly va replicato nello smoke di `ci.yml`
  (regola in CLAUDE.md) e ogni suo output nel commit-list tollerante.
- Dati e deploy sono accoppiati al COMMIT (il sito serve dati committati
  rigenerati nel run): vedi CLAUDE.md §Deployment.

## 6. Stato durabile e pendenze (agg. 2026-10-21)

- **Sito**: live su https://mxmap.it (GitHub Pages, DNS TopDNS). ~22.9k enti,
  ~31k pagine SEO per-ente/area/categoria generate nel deploy (#15).
- **Upstream** (`mxmap/secassure2026`, policy follow-never-merge): PR aperte
  in attesa dei maintainer — [#34](https://github.com/mxmap/secassure2026/pull/34)
  (DKIM TXT fallback Google) e [#37](https://github.com/mxmap/secassure2026/pull/37)
  (basemap OSM keyless al posto di CARTO_KEY).
- **Indicizzazione Google**: leve attive (sitemap a 3 livelli con lastmod
  onesti, IndexNow quotidiano, backlink regionali dall'Osservatorio);
  monitoraggio in Search Console lato Fabio.
- **Incidenti risolti di recente** (post-mortem nelle issue chiuse):
  CARTO→OSM (2026-09-29, #26), scuole/geocoding ripristinato dal server
  (2026-09-29), fusioni di comuni → fallback prefisso-provincia
  (2026-10-19, #27).
- **TODO noti**: issue aperte sul repo (#2–#25: bounce verifier #5, PSN #12,
  bottone segnalazione #16, PEC-ordinaria #20, fingerprinting #22/#23, …) +
  `docs/ROADMAP.md`; rimozione "ISD" dalla headline (memoria 2026-06-16).

## 7. Contesto Claude (memoria tra macchine)

Il repo è PUBBLICO: la memoria personale di Claude non viene specchiata qui
(a differenza dei repo privati). Tutto il contesto operativo necessario è
però già curato in questo file + `CLAUDE.md` + le issue: una sessione Claude
nuova su un altro PC riparte leggendo quelli. Le regole trasversali
dell'utente (Bash-non-PowerShell, UTF-8, commit continui, rendiconto batterie
+ conferma, restore-not-regenerate) sono riassunte in CLAUDE.md §Working
rules così da valere anche senza la memoria locale.
