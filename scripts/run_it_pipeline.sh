#!/usr/bin/env bash
# End-to-end Italian PA email-sovereignty pipeline for mxmap.it.
# Idempotent — safe to re-run. Each step writes to repo files; reruns will
# pick up incremental changes.
#
# Prereqs:
#   - Python 3.13+ via uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
#   - mapshaper + osmtogeojson on PATH (only needed by step 5)
#   - Network access to:
#       indicepa.gov.it/ipa-dati  (CKAN)
#       query.wikidata.org        (SPARQL)
#       overpass-api.de           (Overpass)
#       1.1.1.1 / 8.8.8.8         (DNS resolvers used by mxmap)
#       login.microsoftonline.com (MS365 tenant detection)
#
# Run from the repo root:
#   uv sync
#   ./scripts/run_it_pipeline.sh
#
# Output:
#   data/it_istat_osm_crosswalk.json  ISTAT/IPA->OSM relation crosswalk
#   data/municipalities_it.json       IT seed (~8000 entries)
#   data.json                         mxmap output for IT (joined w/ existing)
#   data/dns_cache/it.json            DNS cache (incremental)
#   data/reports/it_per_province.txt  Per-provincia report
#   data/reports/it_per_province.json Per-province machine-readable report
#   topo/it_region.topo.json          OSM regioni boundaries
#   topo/it_province.topo.json        OSM province + CM boundaries
#   topo/it_municipality.topo.json    OSM comuni boundaries

set -euo pipefail

# Allow opting out of the heavy topo step (it takes 10–20 min; not strictly
# required to validate classification).
SKIP_TOPO="${SKIP_TOPO:-0}"

cd "$(dirname "$0")/.."  # repo root

echo "=========================================="
echo " mxmap.it — Italian pipeline"
echo " repo: $(pwd)"
echo "=========================================="

echo ""
echo "[1/8] Build Wikidata crosswalk (ISTAT/IPA -> OSM relation)"
uv run python3 scripts/build_istat_osm_crosswalk.py

echo ""
echo "[2/8] Fetch IndicePA seed (~8,000 territorial PAs, drops PEC)"
uv run python3 scripts/fetch_indicepa.py

echo ""
echo "[3/8] mxmap preprocess — DNS lookups + provider classification"
PYTHONUNBUFFERED=1 uv run preprocess IT

echo ""
echo "[4/8] Recover Unknown-MX entries via IndicePA non-PEC email fallbacks"
PYTHONUNBUFFERED=1 uv run python3 scripts/recover_it_unknowns.py

echo ""
echo "[5/9] Reclassify provincial-shared (XX.it) via comune look-through"
PYTHONUNBUFFERED=1 uv run python3 scripts/reclassify_it_provincial.py

echo ""
echo "[6/9] Finalize unknowns: ruparpiemonte.it -> regional-public; homepage scrape for the rest"
PYTHONUNBUFFERED=1 uv run python3 scripts/finalize_it_unknowns.py

echo ""
echo "[7/9] mxmap postprocess (manual overrides + SMTP banner)"
PYTHONUNBUFFERED=1 uv run postprocess IT

echo ""
echo "[8/9] Validate (quality gate)"
uv run validate || echo "  validate exited non-zero — see validation_report.{json,csv}"

echo ""
echo "[9/9] Per-province report"
uv run python3 scripts/report_it_per_province.py

if [[ "$SKIP_TOPO" != "1" ]]; then
  echo ""
  echo "[*] TopoJSON boundaries from Overpass (admin_level 4/6/8)"
  echo "    set SKIP_TOPO=1 to skip this step"
  uv run python3 scripts/fetch_it_boundaries.py
else
  echo ""
  echo "[*] Skipping TopoJSON fetch (SKIP_TOPO=1)"
fi

echo ""
echo "=========================================="
echo " Done."
echo "=========================================="
echo "Reports:"
echo "  data/reports/it_per_province.txt"
echo "  data/reports/it_per_province.json"
echo "  validation_report.{json,csv}"
echo ""
echo "Quick stats:"
uv run python3 scripts/analyze_it_classification.py | head -25 || true
