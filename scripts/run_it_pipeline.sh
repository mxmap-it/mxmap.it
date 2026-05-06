#!/usr/bin/env bash
# End-to-end Italian PA email-sovereignty pipeline for mxmap.it.
# Idempotent — safe to re-run. Each step writes to repo files; reruns will
# pick up incremental changes.
#
# Prereqs:
#   - Python 3.13+ via uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
#   - mapshaper + osmtogeojson on PATH (only needed by topo steps)
#   - Network access to:
#       indicepa.gov.it/ipa-dati  (CKAN)
#       query.wikidata.org        (SPARQL)
#       overpass-api.de           (Overpass)
#       it.wikipedia.org          (Wikipedia API)
#       1.1.1.1 / 8.8.8.8         (DNS resolvers used by mxmap)
#       login.microsoftonline.com (MS365 tenant detection)
#
# Run from the repo root:
#   uv sync
#   ./scripts/run_it_pipeline.sh
#
# Output (all reproducibility-relevant files):
#   data/it_istat_osm_crosswalk.json  ISTAT/IPA->OSM relation crosswalk
#   data/municipalities_it.json       IT seed (~22.950 entries)
#   data/enrichment_pec_only.json     auto-discovered PEC-only domains
#   data/manual_llm_enrichment.json   hand-curated LLM enrichment (committed)
#   data/llm_prompt_unmapped.md       prompt for residual LLM-assisted lookup
#   data/it_istruzione_by_comune.json schools-per-comune choropleth data
#   data/it_pipeline_funnel.json      transparency funnel (validated/fixed/unmapped)
#   data.json                         full mxmap output (IT joined w/ rest)
#   data/dns_cache/it.json            DNS cache (incremental)
#   data/reports/                     per-province / per-category / per-cluster reports
#   topo/it_region.topo.json          OSM regioni (20 features)
#   topo/it_province.topo.json        OSM province + CM (107 features)
#   topo/it_municipality.topo.json    OSM comuni (~7,900 polygon features)

set -euo pipefail

SKIP_TOPO="${SKIP_TOPO:-0}"
SKIP_ENRICH="${SKIP_ENRICH:-0}"

cd "$(dirname "$0")/.."  # repo root

echo "=========================================="
echo " mxmap.it — Italian pipeline"
echo " repo: $(pwd)"
echo "=========================================="

echo ""
echo "[1/14] Build Wikidata crosswalk (ISTAT/IPA -> OSM relation)"
uv run python3 scripts/build_istat_osm_crosswalk.py

if [[ "$SKIP_ENRICH" != "1" ]]; then
  echo ""
  echo "[2a/14] Auto-enrich PEC-only enti (Wikidata + IT Wikipedia, ~620 candidates)"
  echo "        idempotent — uses existing data/enrichment_pec_only.json as cache"
  uv run python3 scripts/enrich_pec_only.py || echo "  enrich_pec_only failed; continuing"
fi

echo ""
echo "[2b/14] Fetch IndicePA seed — 22.950 enti (territorial + Tier-2/3 categories)"
echo "        loads data/manual_llm_enrichment.json + enrichment_pec_only.json overrides"
uv run python3 scripts/fetch_indicepa.py --include-others

echo ""
echo "[2c/14] Generate LLM enrichment prompt for residual unmapped enti"
echo "        output: data/llm_prompt_unmapped.md (paste into Claude Code session)"
uv run python3 scripts/generate_llm_enrichment_prompt.py || true

if [[ "$SKIP_TOPO" != "1" ]]; then
  echo ""
  echo "[3a/14] Fetch admin boundaries (Overpass admin_level 4/6/8)"
  echo "        set SKIP_TOPO=1 to skip (heavy: 10-20 min)"
  uv run python3 scripts/fetch_it_boundaries.py

  echo ""
  echo "[3b/14] Fetch missing comuni polygons (~311 entries dropped by per-province batching)"
  uv run python3 scripts/fetch_missing_comuni_polygons.py || echo "  missing-comuni failed; continuing"

  echo ""
  echo "[3c/14] Fetch extra IT province polygons (Valle d'Aosta + Sud Sardegna)"
  uv run python3 scripts/fetch_extra_it_provinces.py || echo "  extra-provinces failed; continuing"

  echo ""
  echo "[3d/14] Strip foreign cross-border features (Auvergne-Rhône-Alpes, Haute-Savoie, …)"
  uv run python3 scripts/strip_foreign_from_it_topo.py

  echo ""
  echo "[3e/14] Fix Sardegna 2016-reform legacy province polygons"
  uv run python3 scripts/fix_sardegna_legacy_provinces.py || echo "  fix-sardegna failed; continuing"
else
  echo ""
  echo "[3/14] Skipping topo fetch + cleanup (SKIP_TOPO=1)"
fi

echo ""
echo "[4/14] mxmap preprocess — DNS lookups + provider classification"
PYTHONUNBUFFERED=1 uv run preprocess IT

echo ""
echo "[5/14] Recover Unknown-MX entries via IndicePA non-PEC email fallbacks"
PYTHONUNBUFFERED=1 uv run python3 scripts/recover_it_unknowns.py

echo ""
echo "[6a/14] Probe each XX.it provincial domain for its actual mail backend"
PYTHONUNBUFFERED=1 uv run python3 scripts/probe_it_provincial_backends.py

echo ""
echo "[6b/14] Reclassify provincial-shared comuni using the probed backends"
PYTHONUNBUFFERED=1 uv run python3 scripts/reclassify_it_provincial.py

echo ""
echo "[7/14] Finalize unknowns: ruparpiemonte.it -> regional-public; homepage scrape; search engine"
PYTHONUNBUFFERED=1 uv run python3 scripts/finalize_it_unknowns.py

echo ""
echo "[8/14] mxmap postprocess (manual overrides + SMTP banner)"
PYTHONUNBUFFERED=1 uv run postprocess IT

echo ""
echo "[9/14] Validate (quality gate)"
uv run validate || echo "  validate exited non-zero — see validation_report.{json,csv}"

echo ""
echo "[10/14] Per-province report"
uv run python3 scripts/report_it_per_province.py

echo ""
echo "[11/14] Per-category + per-cluster reports"
uv run python3 scripts/report_it_by_category.py
uv run python3 scripts/report_it_by_cluster.py

echo ""
echo "[12/14] Aggregate scuole-per-comune for Sezione Istruzione choropleth"
uv run python3 scripts/aggregate_istruzione_per_comune.py

echo ""
echo "[13/14] Pipeline funnel transparency report"
uv run python3 scripts/report_pipeline_funnel.py

echo ""
echo "[14a/15] Build frontend data files (data-summary, data-detail, data-regions, per-country)"
uv run python3 scripts/build_frontend.py

echo ""
echo "[14b/15] Build public download dataset (CSV + JSON + XLSX) under dist/"
uv run python3 scripts/build_public_dataset.py

echo ""
echo "=========================================="
echo " Done — all artifacts regenerated"
echo "=========================================="
echo "Reports:"
echo "  data/reports/it_per_province.txt"
echo "  data/reports/it_by_cluster.txt"
echo "  data/it_pipeline_funnel.json     (transparency funnel)"
echo "  data/it_istruzione_by_comune.json (Sezione Scuole)"
echo "  validation_report.{json,csv}"
echo ""
echo "Quick stats:"
uv run python3 scripts/analyze_it_classification.py | head -25 || true
