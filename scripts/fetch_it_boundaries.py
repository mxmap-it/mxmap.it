#!/usr/bin/env python3
"""Fetch Italian admin boundaries at all 3 levels from Overpass.

Resilient by design — public Overpass instances frequently return 504/429:
  * Mirror rotation: tries multiple Overpass endpoints in order
  * Exponential backoff retries per mirror
  * Per-region splitting for admin_level=8 (~7,900 comuni — too big for a
    single country-scope query) and as fallback for admin_level=6
  * Element deduplication when merging per-region responses

Generates:
  topo/it_region.topo.json       (admin_level=4, ~22 regioni + prov. autonome)
  topo/it_province.topo.json     (admin_level=6, ~107 province + CM)
  topo/it_municipality.topo.json (admin_level=8, ~7,900 comuni)

Run on the deployment server (faster network):
  uv run python3 scripts/fetch_it_boundaries.py

Requires mapshaper + osmtogeojson on PATH.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_boundaries import (  # noqa: E402
    DATA_DIR,
    TOPO_DIR,
    annotate_geojson,
    osm_to_geojson,
)
# We do NOT use upstream's overpass_query (single mirror, no retry) or
# create_topojson (joins format= and quantization= into one buggy arg).

# Public Overpass mirrors. Order matters — first-listed is tried first per
# query. Falls forward through the list when one returns 5xx / connection
# errors. Add or reorder to match infrastructure availability.
OVERPASS_MIRRORS: list[str] = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

USER_AGENT = "mxmap.it-topo-fetcher/0.2 (+https://github.com/fpietrosanti/mxmap.it)"

# Italy mainland + islands bounding box (Pantelleria/Lampedusa to South Tyrol).
IT_BBOX = [6.6, 35.4, 18.6, 47.1]

# admin_level -> mxmap level slot (matching the frontend's region/district/
# municipality 3-button toggle). Province goes in "district" slot for the
# manifest; the frontend translation layer renames it to "Province" in the UI.
LEVELS = [
    (4, "region",       "it_region.topo.json"),
    (6, "district",     "it_province.topo.json"),
    (8, "municipality", "it_municipality.topo.json"),
]

# Per-level mapshaper config
MAPSHAPER_CONFIG = {
    4: {"simplify": "8%",  "quantization": "5000"},
    6: {"simplify": "10%", "quantization": "5000"},
    8: {"simplify": "15%", "quantization": None},   # no quantization for muni
}

CROSSWALK_PATH = DATA_DIR / "it_istat_osm_crosswalk.json"


def overpass_post(mirror: str, query: str, *, timeout: int = 300) -> dict:
    """POST a query to a single Overpass mirror. Raises on HTTP error."""
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        mirror,
        data=data,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class OverpassError(RuntimeError):
    pass


def overpass_with_failover(query: str, *, label: str = "", per_mirror_attempts: int = 2,
                           timeout: int = 300) -> dict:
    """Try each Overpass mirror with exponential backoff. First successful
    response wins. Raises OverpassError if all mirrors exhausted."""
    last_err: Exception | None = None
    for mirror in OVERPASS_MIRRORS:
        for attempt in range(1, per_mirror_attempts + 1):
            try:
                print(f"    [{label}] {mirror} attempt {attempt}/{per_mirror_attempts}...")
                start = time.monotonic()
                data = overpass_post(mirror, query, timeout=timeout)
                elapsed = time.monotonic() - start
                n_elements = len(data.get("elements", []))
                print(f"      ok ({elapsed:.1f}s, {n_elements} elements)")
                return data
            except urllib.error.HTTPError as e:
                last_err = e
                # 504 / 429 / 503 are retryable; 4xx (other) is usually fatal
                # for this mirror — break and try the next one.
                if e.code in (429, 502, 503, 504):
                    backoff = 30 * (2 ** (attempt - 1))
                    print(f"      HTTP {e.code} — sleep {backoff}s before next attempt")
                    time.sleep(backoff)
                    continue
                print(f"      HTTP {e.code} (non-retryable) — moving to next mirror")
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last_err = e
                backoff = 30 * (2 ** (attempt - 1))
                print(f"      {type(e).__name__}: {e} — sleep {backoff}s")
                time.sleep(backoff)
                continue
            except Exception as e:
                last_err = e
                print(f"      unexpected {type(e).__name__}: {e}")
                break
        # End of attempts for this mirror — try the next.
        time.sleep(5)
    raise OverpassError(f"all Overpass mirrors exhausted for {label}: {last_err!r}")


def country_scope_query(admin_level: int, *, query_timeout: int = 600) -> str:
    """Single-shot Italy-wide query at the given admin_level."""
    return f"""
[out:json][timeout:{query_timeout}];
area["ISO3166-1"="IT"]->.country;
(relation["boundary"="administrative"]["admin_level"="{admin_level}"](area.country););
out body;
>;
out skel qt;
"""


def region_scope_query(region_osm_id: int, admin_level: int, *, query_timeout: int = 600) -> str:
    """Per-region query: scope by region's OSM area (relation_id + 3.6e9)."""
    area_id = 3_600_000_000 + region_osm_id
    return f"""
[out:json][timeout:{query_timeout}];
area({area_id})->.region;
(relation["boundary"="administrative"]["admin_level"="{admin_level}"](area.region););
out body;
>;
out skel qt;
"""


def merge_overpass_responses(responses: list[dict]) -> dict:
    """Combine multiple Overpass JSON responses, deduping elements by (type, id)."""
    by_key: dict[tuple[str, int], dict] = {}
    for resp in responses:
        for el in resp.get("elements", []):
            key = (el.get("type"), el.get("id"))
            if key in by_key:
                continue
            by_key[key] = el
    return {"elements": list(by_key.values())}


def _load_crosswalk() -> dict:
    if not CROSSWALK_PATH.exists():
        raise FileNotFoundError(
            f"{CROSSWALK_PATH} missing. Run scripts/build_istat_osm_crosswalk.py first."
        )
    with open(CROSSWALK_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_region_osm_ids() -> dict[str, int]:
    """ISTAT 2-digit region code -> OSM relation_id, from the crosswalk.

    Only includes the 20 standard regioni (no separate Bolzano/Trento entries
    because those are admin_level=6 in OSM and live inside region 04 area —
    a level=8 query scoped to region 04's area picks up their comuni too).
    """
    by_region = _load_crosswalk().get("by_istat_region") or {}
    if not by_region:
        raise RuntimeError(f"by_istat_region empty in {CROSSWALK_PATH}")
    return {istat: int(osm) for istat, osm in by_region.items()}


def load_province_osm_ids() -> dict[str, int]:
    """ISTAT 3-digit province code -> OSM relation_id, from the crosswalk.

    ~107 entries (province + città metropolitane). Used as the per-province
    splitting key for admin_level=8 (~7,900 comuni). Per-province produces
    smaller, more reliable Overpass queries (~70 comuni each vs ~400 per
    region) and load-balances better across mirrors.
    """
    by_province = _load_crosswalk().get("by_istat_province") or {}
    if not by_province:
        raise RuntimeError(f"by_istat_province empty in {CROSSWALK_PATH}")
    return {istat: int(osm) for istat, osm in by_province.items()}


def fetch_per_region(admin_level: int) -> dict:
    """Iterate Italian regions; accumulate Overpass responses; dedupe."""
    region_ids = load_region_osm_ids()
    print(f"  Per-region fetch for admin_level={admin_level}: "
          f"{len(region_ids)} regions")
    responses: list[dict] = []
    for istat, osm_id in sorted(region_ids.items()):
        label = f"reg{istat}/L{admin_level}"
        query = region_scope_query(osm_id, admin_level)
        try:
            data = overpass_with_failover(query, label=label, timeout=300)
        except OverpassError as e:
            print(f"    SKIP region {istat}: {e}")
            continue
        responses.append(data)
        time.sleep(8)  # politeness between regions
    return merge_overpass_responses(responses)


def fetch_per_province(admin_level: int) -> dict:
    """Iterate Italian province (admin_level=6 OSM areas); accumulate; dedupe.

    Used for admin_level=8 (comuni). Each province area contains ~70 comuni
    on average. ~107 queries total — slower than per-region but each query
    is small and unlikely to hit the public Overpass 504 timeout.
    """
    prov_ids = load_province_osm_ids()
    print(f"  Per-province fetch for admin_level={admin_level}: "
          f"{len(prov_ids)} province")
    responses: list[dict] = []
    n_done = 0
    for istat, osm_id in sorted(prov_ids.items()):
        n_done += 1
        label = f"prov{istat}/L{admin_level} ({n_done}/{len(prov_ids)})"
        query = region_scope_query(osm_id, admin_level)  # same query template
        try:
            data = overpass_with_failover(query, label=label, timeout=180)
        except OverpassError as e:
            print(f"    SKIP province {istat}: {e}")
            continue
        responses.append(data)
        time.sleep(5)  # politeness between province queries
    return merge_overpass_responses(responses)


def fetch_at_level(admin_level: int) -> dict | None:
    """Country-scope first; province-split for level 8 always; region-split
    fallback for levels 4/6 when the single-shot fails."""
    if admin_level == 8:
        # ~7,900 comuni — country-scope is impossible; per-region is borderline.
        # Per-province (107 chunks) is the most reliable split.
        return fetch_per_province(admin_level)
    try:
        query = country_scope_query(admin_level)
        return overpass_with_failover(query, label=f"country/L{admin_level}", timeout=300)
    except OverpassError as e:
        print(f"  Country-scope failed for level {admin_level}: {e}")
        print("  Falling back to per-region split...")
        return fetch_per_region(admin_level)


def make_topojson(annotated_geojson_path: str, out_path: str, admin_level: int) -> None:
    """Run mapshaper directly with separate args (avoids the upstream
    create_topojson bug that joined `format=topojson` + `quantization=5000`
    into one rejected arg)."""
    cfg = MAPSHAPER_CONFIG[admin_level]
    cmd = [
        "mapshaper", annotated_geojson_path,
        "-simplify", cfg["simplify"], "keep-shapes",
        "-o", out_path,
        "format=topojson",
    ]
    if cfg["quantization"]:
        cmd.append(f"quantization={cfg['quantization']}")
    print(f"  mapshaper: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.stderr.strip():
        print(f"  mapshaper note: {r.stderr.strip()}")
    if r.returncode != 0:
        raise RuntimeError(f"mapshaper failed (rc={r.returncode}): {r.stderr[:1500]}")


def update_manifest(sizes: dict[str, int]) -> None:
    """Write the IT entry into topo/manifest.json with all three levels."""
    manifest_path = TOPO_DIR / "manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    manifest["IT"] = {
        "levels": ["region", "district", "municipality"],
        "files": {
            "region":       "it_region.topo.json",
            "district":     "it_province.topo.json",
            "municipality": "it_municipality.topo.json",
        },
        "sizes": {k: v for k, v in sizes.items() if v > 0},
        "bbox":  IT_BBOX,
    }
    sorted_manifest = dict(sorted(manifest.items()))
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(sorted_manifest, f, indent=2)
    print(f"  Updated manifest: IT -> 3 levels, bbox {IT_BBOX}")


def main() -> int:
    seed_path = DATA_DIR / "municipalities_it.json"
    with open(seed_path, encoding="utf-8") as f:
        seed_data = json.load(f)
    print(f"Loaded {len(seed_data)} entries from {seed_path.name}")
    print(f"  with osm_relation_id: {sum(1 for e in seed_data if e.get('osm_relation_id'))}")
    print(f"Mirrors (in order): {', '.join(OVERPASS_MIRRORS)}")

    TOPO_DIR.mkdir(parents=True, exist_ok=True)
    sizes: dict[str, int] = {}

    for admin_level, _slot, out_filename in LEVELS:
        print(f"\n=== admin_level={admin_level} -> {out_filename} ===")
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                osm_data = fetch_at_level(admin_level)
            except Exception as e:
                print(f"  ABORT level={admin_level}: {e!r}")
                continue
            if not osm_data:
                print("  ERROR: Overpass returned no data — skipping level")
                continue
            relations = [e for e in osm_data.get("elements", []) if e["type"] == "relation"]
            print(f"  Overpass: {len(relations)} relations after merge/dedupe")
            if not relations:
                print("  ERROR: zero relations after merge")
                continue

            geo_path = osm_to_geojson(osm_data, tmpdir)
            with open(geo_path, encoding="utf-8") as f:
                geo = json.load(f)
            n_features = len(geo.get("features", []))
            print(f"  GeoJSON: {n_features} features")
            if n_features == 0:
                print("  ERROR: zero features after conversion")
                continue

            annotated_path = annotate_geojson(geo_path, "IT", seed_data)
            out_path = str(TOPO_DIR / out_filename)
            try:
                make_topojson(annotated_path, out_path, admin_level)
            except RuntimeError as e:
                print(f"  ERROR: {e}")
                continue

            size = Path(out_path).stat().st_size
            sizes[out_filename] = size
            print(f"  -> {Path(out_path).name} ({size:,} bytes)")

        time.sleep(15)  # politeness between levels

    update_manifest(sizes)

    print("\n=== Summary ===")
    for filename, size in sizes.items():
        print(f"  {filename:<35} {size:>12,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
