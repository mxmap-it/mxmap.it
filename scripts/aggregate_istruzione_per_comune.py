#!/usr/bin/env python3
"""Aggregate Italian schools (IPA Codice_Categoria=L33) by their host comune
(via Codice_comune_ISTAT) and output a per-comune school-provider summary.

This powers the "Scuole" data-layer view in the frontend: the existing
it_municipality topo is reused, but each comune polygon is colored by the
dominant email provider of the SCHOOLS located in that comune (not by the
comune's own administration).

Output: data/it_istruzione_by_comune.json
{
  "generated": "2026-...",
  "total_schools": 8169,
  "comuni_with_schools": 7341,   # not all comuni have a state school
  "comuni": {
    "<istat6>": {
      "name": "Roma Capitale",
      "school_count": 142,
      "providers": {"Microsoft 365": 45, "Google Workspace": 80, "Provider Italiano": 17},
      "popProviders": {"Microsoft 365": 45, ...},  # same as count for schools (no pop weighting)
      "dominant": "Google Workspace",
      "blendedColor": "#aabbcc"
    },
    ...
  },
  "national_totals": {
    "providers": {...},   # rolled up across all 8169 schools
    "dominant": "Google Workspace"
  }
}

Run AFTER preprocess (so data.json has classified L33 entries):
  uv run python3 scripts/aggregate_istruzione_per_comune.py

Used by build_frontend.py downstream to inject `istruzione_districts`
into data-regions.json IT.* so the frontend can switch the choropleth
data source between "tutti gli enti" and "solo scuole".
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT_FILE = DATA / "it_istruzione_by_comune.json"

# Display-name mapping (mirrors scripts/build_frontend.py PROVIDER_DISPLAY)
PROVIDER_DISPLAY = {
    "microsoft": "Microsoft 365", "google": "Google Workspace", "aws": "AWS",
    "aruba": "Provider Italiano", "register-it": "Provider Italiano",
    "seeweb": "Provider Italiano", "infocert": "Provider Italiano",
    "namirial": "Provider Italiano", "local-isp": "Provider Italiano",
    "telia": "Provider Italiano", "tet": "Provider Italiano",
    "zone": "Provider Italiano", "elkdata": "Provider Italiano",
    "regional-public": "Cloud Italiano",
    "pa-contractor-private": "Provider Italiano",
    # Scuole statali sul tenant centrale MIM (istruzione.it). Distinto da
    # Microsoft 365 perché la scuola non controlla un proprio tenant.
    "istruzione-miur-tenant": "Tenant centrale MIM (istruzione.it)",
    "independent": "Infrastruttura autonoma",
    "provincial-shared": "Mail provinciale condivisa",
    "zoho": "Zoho", "yandex": "Yandex",
    "unknown": "Sconosciuto",
}

# Italian-flag-friendly palette (mirrors index.html COLORS)
COLORS = {
    "Microsoft 365": "#D42E2E", "Google Workspace": "#FF6B6B", "AWS": "#FF8C42",
    "Cloud Italiano": "#009246", "Provider Italiano": "#2E7D32",
    "Tenant centrale MIM (istruzione.it)": "#B85C5C",
    "Infrastruttura autonoma": "#558B2F",
    "Mail provinciale condivisa": "#7CB342",
    "Zoho": "#7C3AED", "Yandex": "#FFCC00",
    "Sconosciuto": "#bfbfbf",
}


def blend_color(providers: dict[str, int], total: int) -> str:
    """Compute a population-weighted blend of provider colors. Falls back to
    dominant color if total is zero."""
    if total == 0:
        return "#bfbfbf"
    r, g, b = 0.0, 0.0, 0.0
    for p, n in providers.items():
        c = COLORS.get(p, "#bfbfbf")
        try:
            cr = int(c[1:3], 16); cg = int(c[3:5], 16); cb = int(c[5:7], 16)
        except (ValueError, IndexError):
            cr = cg = cb = 191
        w = n / total
        r += cr * w; g += cg * w; b += cb * w
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def main() -> int:
    seed_path = DATA / "municipalities_it.json"
    data_path = ROOT / "data.json"
    if not seed_path.exists():
        print(f"FATAL: {seed_path} missing")
        return 1
    if not data_path.exists():
        print(f"FATAL: {data_path} missing — run preprocess first")
        return 1

    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    data = json.loads(data_path.read_text(encoding="utf-8"))
    muns = data.get("municipalities", {})

    # Index seed by id -> ipa metadata
    seed_by_id = {e["id"]: e for e in seed}

    # Build name-by-istat6 + istat6-to-osm_relation_id maps. The OSM map lets
    # the frontend join istruzione data to topo features (id="relation/<N>")
    # without needing to re-read the seed at render time.
    comune_name_by_istat: dict[str, str] = {}
    istat_to_osm: dict[str, int] = {}
    for e in seed:
        if e.get("ipa_codice_categoria") == "L6":
            istat = (e.get("ipa_codice_comune_istat") or "").zfill(6)
            if istat and len(istat) == 6:
                # Strip "Comune di " prefix
                n = (e.get("name") or "").strip()
                for prefix in ("Comune di ", "Comune del ", "Comune della ",
                               "Comune dell'", "Comune dei "):
                    if n.startswith(prefix):
                        n = n[len(prefix):]
                        break
                comune_name_by_istat[istat] = n
                osm = e.get("osm_relation_id")
                if osm:
                    istat_to_osm[istat] = int(osm)

    # Walk classified entries, keep schools (IPA L33) only
    by_comune: dict[str, Counter] = defaultdict(Counter)
    school_count = 0
    skipped_no_istat = 0
    for bid, m in muns.items():
        if not bid.startswith("IT-L33-"):
            continue
        sd = seed_by_id.get(bid)
        if not sd:
            continue
        istat = (sd.get("ipa_codice_comune_istat") or "").zfill(6)
        if not istat or len(istat) != 6:
            skipped_no_istat += 1
            continue
        raw_provider = (m.get("provider") or "unknown")
        display = PROVIDER_DISPLAY.get(raw_provider, raw_provider)
        by_comune[istat][display] += 1
        school_count += 1

    # Compose per-comune objects
    comuni_out: dict[str, dict] = {}
    by_osm: dict[str, dict] = {}  # secondary key: "relation/<N>" -> same dict
    national = Counter()
    for istat, providers in by_comune.items():
        total = sum(providers.values())
        dominant = providers.most_common(1)[0][0] if total else "Sconosciuto"
        entry = {
            "name": comune_name_by_istat.get(istat, ""),
            "istat": istat,
            "school_count": total,
            "providers": dict(providers),
            "popProviders": dict(providers),  # 1 school = 1 vote (no pop weighting)
            "dominant": dominant,
            "dominance": providers[dominant] / total if total else 0,
            "blendedColor": blend_color(providers, total),
        }
        comuni_out[istat] = entry
        osm = istat_to_osm.get(istat)
        if osm is not None:
            by_osm[f"relation/{osm}"] = entry
        for k, v in providers.items():
            national[k] += v

    # Per-school point markers (lat/lng + provider) when geocoding cache exists.
    # Built by scripts/geocode_istruzione.py. Falls back to empty list when
    # the cache file is missing, so this aggregation script remains runnable
    # without geocoding.
    geocode_path = DATA / "it_istruzione_points.json"
    points: list[dict] = []
    if geocode_path.exists():
        gd = json.loads(geocode_path.read_text(encoding="utf-8"))
        gp = gd.get("points", {})
        for bid, m in muns.items():
            if not bid.startswith("IT-"):
                continue
            sd = seed_by_id.get(bid)
            if not sd or sd.get("ipa_codice_categoria") not in ("L33", "L17", "L43", "L15", "L28"):
                continue
            ipa = (sd.get("ipa_codice_ipa") or "").strip()
            pt = gp.get(ipa)
            if not pt or "lat" not in pt or "lon" not in pt:
                continue
            raw = m.get("provider") or "unknown"
            points.append({
                "id": bid,
                "name": sd.get("name", "")[:80],
                "cat": sd.get("ipa_codice_categoria", ""),
                "lat": pt["lat"],
                "lon": pt["lon"],
                "p":   raw,                                                # raw provider
                "pd":  PROVIDER_DISPLAY.get(raw, raw),                     # display name
                "dom": pt.get("comune_name", ""),
            })

    out = {
        "generated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_schools": school_count,
        "comuni_with_schools": len(comuni_out),
        "skipped_no_istat": skipped_no_istat,
        "comuni": comuni_out,
        "by_osm": by_osm,
        "points": points,
        "national_totals": {
            "providers": dict(national),
            "dominant": national.most_common(1)[0][0] if national else "Sconosciuto",
            "blendedColor": blend_color(national, sum(national.values()) or 1),
        },
    }
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    print(f"  schools classified: {school_count}")
    print(f"  comuni with at least 1 school: {len(comuni_out)}")
    print(f"  schools skipped (no ISTAT): {skipped_no_istat}")
    print()
    print(f"  National school-provider distribution:")
    for k, v in national.most_common():
        print(f"    {k:<32} {v:>5}  ({v/school_count*100:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
