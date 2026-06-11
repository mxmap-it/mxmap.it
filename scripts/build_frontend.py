#!/usr/bin/env python3
"""Build slim frontend data files from pipeline output.

Usage: python3 scripts/build_frontend.py

Reads:
  data.json  (full pipeline output, 6 MB)

Produces:
  data-summary.json  (map/stats fields only, ~60 KB gzipped)
  data-detail.json   (popup fields, keyed by bfs, ~130 KB gzipped)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Fields needed for map rendering, legend, stats, and aggregation
SUMMARY_FIELDS = {
    "bfs",
    "name",
    "name_en",
    "canton",
    "district",
    "country",
    "domain",
    "provider",
    "osm_relation_id",
    "mx_countries",
    "gateway",
    "isp_name",
    "population",
}

# Fields needed only for popups (loaded in background)
DETAIL_FIELDS = {
    "mx",
    "spf",
    "reason",
    "autodiscover",
    "dkim",
    "txt_verifications",
    "tenant",
    "smtp_software",
    # MX provenance — shown as badge in popup with link to methodology.html
    "mx_discovery_method",
    "mx_discovery_evidence",
    # Confidence ESORICS + sovranità (popup badge + filtro mappa)
    "classification_confidence",
    "classification_rule",
    "mx_jurisdiction",
    "cloud_tenant_only",
    "domestic_mx_override",
}

# Fields intentionally dropped (not used by frontend)
# spf_resolved, mx_asns, smtp_banner, mx_cnames


PROVIDER_DISPLAY = {
    "microsoft": "Microsoft 365",
    "google": "Google Workspace",
    "aws": "AWS",
    # Italian commercial — accorpati in 'Provider Italiano' (mxmap.it citizen UI)
    "aruba": "Provider Italiano",
    "register-it": "Provider Italiano",
    "seeweb": "Provider Italiano",
    "infocert": "Provider Italiano",
    "namirial": "Provider Italiano",
    "local-isp": "Provider Italiano",
    "telia": "Provider Italiano",
    "tet": "Provider Italiano",
    "zone": "Provider Italiano",
    "elkdata": "Provider Italiano",
    # Italian publicly-owned consortium / regional ICT
    "regional-public": "Cloud Italiano",
    # Italian PA private contractors (Engineering, Almaviva) — aggregated into
    # the citizen-facing "Provider Italiano" bucket because, from a CLOUD-Act
    # / digital-sovereignty perspective, they are Italian-jurisdiction private
    # companies just like Aruba/Register. The technical classification stays
    # distinct in data.json for auditing/reporting.
    "pa-contractor-private": "Provider Italiano",
    # Self-hosted (renamed)
    # Scuole statali sul tenant centrale MIM (istruzione.it). Distinto da
    # Microsoft 365 perché la scuola non controlla un proprio tenant.
    "istruzione-miur-tenant": "Tenant centrale MIM (istruzione.it)",
    "independent": "Infrastruttura autonoma",
    # Provincial-shared
    "provincial-shared": "Mail provinciale condivisa",
    # Foreign minor
    "zoho": "Zoho",
    "yandex": "Yandex",
    "unknown": "Sconosciuto",
}

COLORS = {
    # USA hyperscalers
    "Microsoft 365": "#D42E2E",
    "Google Workspace": "#FF6B6B",
    "AWS": "#FF8C42",
    # Italian palette — green family
    "Cloud Italiano": "#009246",         # Italian flag green (sovereign)
    "Provider Italiano": "#2E7D32",      # commercial Italian
    "Infrastruttura autonoma": "#558B2F",
    "Mail provinciale condivisa": "#7CB342",
    # Foreign minor
    "Zoho": "#7C3AED",
    "Yandex": "#FFCC00",
    # Backwards-compatible aliases
    "Microsoft": "#D42E2E",
    "Google": "#FF6B6B",
    "Local Provider": "#2E7D32",
    "Self-hosted": "#558B2F",
    "Sconosciuto": "#BFBFBF",
    "Unknown": "#BFBFBF",
}

US_PROVIDERS = {"Microsoft 365", "Google Workspace", "AWS", "Microsoft", "Google"}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def blend_provider_colors(providers: dict[str, int], total: int) -> str:
    r = g = b = 0.0
    for p, count in providers.items():
        color = COLORS.get(p, COLORS["Unknown"])
        cr, cg, cb = hex_to_rgb(color)
        w = count / total
        r += cr * w
        g += cg * w
        b += cb * w
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _ente_jurisdiction(m: dict) -> str:
    """Giurisdizione MX dell'ente: 'domestic'/'foreign'/'mixed'/'unknown'.

    Usa il valore precomputato da compute_confidence.py (classification_
    confidence) se presente; altrimenti deriva dai paesi degli MX rispetto
    al paese dell'ente. Identico al mirror JS mxJurisdiction() nel frontend.
    Serve a pre-aggregare le quote di sovranità per regione/provincia
    (data-regions.json) così il filtro mappa funziona ai livelli aggregati.
    """
    j = m.get("mx_jurisdiction")
    if j:
        return j
    countries = m.get("mx_countries") or []
    if not countries:
        return "unknown"
    target = (m.get("country") or "").upper()
    in_target = [c for c in countries if (c or "").upper() == target]
    if len(in_target) == len(countries):
        return "domestic"
    if not in_target:
        return "foreign"
    return "mixed"


def _bump_jurisdiction(d: dict, jur: str) -> None:
    """Incrementa il contatore di giurisdizione in d['jurisdictions']."""
    jd = d.setdefault("jurisdictions", {})
    jd[jur] = jd.get(jur, 0) + 1


def build_region_data(munis: dict, generated: str) -> dict:
    """Build pre-computed region-level aggregations with population weighting."""
    countries: dict[str, dict] = {}

    # First pass: collect per-country population stats for fallback estimation
    country_pops: dict[str, list[int]] = {}
    for bfs, m in munis.items():
        cc = m.get("country", "")
        pop = m.get("population", 0) or 0
        if pop > 0:
            country_pops.setdefault(cc, []).append(pop)

    # Compute median population per country for fallback
    country_median: dict[str, int] = {}
    for cc, pops in country_pops.items():
        sorted_pops = sorted(pops)
        mid = len(sorted_pops) // 2
        country_median[cc] = sorted_pops[mid] if sorted_pops else 0

    for bfs, m in munis.items():
        cc = m.get("country", "")
        region = m.get("canton", "") or ""
        district = m.get("district", "") or ""
        raw_provider = m.get("provider", "unknown")
        provider = PROVIDER_DISPLAY.get(raw_provider, raw_provider)
        pop = m.get("population", 0) or 0
        # Fallback: use country median if no population, or 1 if no data at all
        if pop <= 0:
            pop = country_median.get(cc, 0) or 1
        has_gateway = bool(
            m.get("gateway")
            and cc in (m.get("mx_countries") or [])
            and provider in US_PROVIDERS
        )
        jur = _ente_jurisdiction(m)

        if cc not in countries:
            countries[cc] = {
                "total": 0,
                "providers": {},
                "popProviders": {},
                "popTotal": 0,
                "gateway_count": 0,
                "jurisdictions": {},
                "regions": {},
                "districts": {},
            }
        cd = countries[cc]
        cd["total"] += 1
        cd["providers"][provider] = cd["providers"].get(provider, 0) + 1
        cd["popProviders"][provider] = cd["popProviders"].get(provider, 0) + pop
        cd["popTotal"] += pop
        if has_gateway:
            cd["gateway_count"] += 1
        _bump_jurisdiction(cd, jur)

        if region not in cd["regions"]:
            cd["regions"][region] = {
                "count": 0,
                "providers": {},
                "popProviders": {},
                "popTotal": 0,
                "gateway_count": 0,
                "jurisdictions": {},
            }
        rd = cd["regions"][region]
        rd["count"] += 1
        rd["providers"][provider] = rd["providers"].get(provider, 0) + 1
        rd["popProviders"][provider] = rd["popProviders"].get(provider, 0) + pop
        rd["popTotal"] += pop
        if has_gateway:
            rd["gateway_count"] += 1
        _bump_jurisdiction(rd, jur)

        # District-level aggregation (for IT province polygons / GB districts)
        if district:
            cd.setdefault("districts", {})
            if district not in cd["districts"]:
                cd["districts"][district] = {
                    "count": 0,
                    "providers": {},
                    "popProviders": {},
                    "popTotal": 0,
                    "gateway_count": 0,
                    "jurisdictions": {},
                }
            dd = cd["districts"][district]
            dd["count"] += 1
            dd["providers"][provider] = dd["providers"].get(provider, 0) + 1
            dd["popProviders"][provider] = dd["popProviders"].get(provider, 0) + pop
            dd["popTotal"] += pop
            if has_gateway:
                dd["gateway_count"] += 1
            _bump_jurisdiction(dd, jur)

    # Compute blended colors + dominant for each region & district
    for cc, cd in countries.items():
        for region_name, rd in cd.get("regions", {}).items():
            if rd["popTotal"] > rd["count"]:
                rd["blendedColor"] = blend_provider_colors(rd["popProviders"], rd["popTotal"])
            else:
                rd["blendedColor"] = blend_provider_colors(rd["providers"], rd["count"])
            top = sorted(rd["providers"].items(), key=lambda kv: -kv[1])
            rd["dominant"] = top[0][0] if top else "Unknown"
            rd["dominance"] = (top[0][1] / rd["count"]) if (top and rd["count"]) else 0.0
        for district_name, dd in cd.get("districts", {}).items():
            if dd["popTotal"] > dd["count"]:
                dd["blendedColor"] = blend_provider_colors(dd["popProviders"], dd["popTotal"])
            else:
                dd["blendedColor"] = blend_provider_colors(dd["providers"], dd["count"])
            top = sorted(dd["providers"].items(), key=lambda kv: -kv[1])
            dd["dominant"] = top[0][0] if top else "Unknown"
            dd["dominance"] = (top[0][1] / dd["count"]) if (top and dd["count"]) else 0.0
        # Country-level blended color
        if cd["popTotal"] > cd["total"]:
            cd["blendedColor"] = blend_provider_colors(cd["popProviders"], cd["popTotal"])
        else:
            cd["blendedColor"] = blend_provider_colors(cd["providers"], cd["total"])
        sorted_providers = sorted(cd["providers"].items(), key=lambda x: -x[1])
        cd["dominant"] = sorted_providers[0][0] if sorted_providers else "Unknown"

        for rname, rd in cd["regions"].items():
            sorted_providers = sorted(
                rd["providers"].items(), key=lambda x: -x[1]
            )
            rd["dominant"] = sorted_providers[0][0] if sorted_providers else "Unknown"
            rd["dominance"] = round(
                sorted_providers[0][1] / rd["count"], 3
            ) if sorted_providers else 0
            # Use population-weighted color if we have real population data
            if rd["popTotal"] > rd["count"]:
                rd["blendedColor"] = blend_provider_colors(rd["popProviders"], rd["popTotal"])
            else:
                rd["blendedColor"] = blend_provider_colors(rd["providers"], rd["count"])

    # IT-specific extras: schools-per-comune choropleth data layer.
    # Produced by scripts/aggregate_istruzione_per_comune.py — runs before
    # build_frontend in the chain. If the file isn't present (script wasn't
    # run yet) we silently skip; the frontend falls back to default views.
    it_istruzione = ROOT / "data" / "it_istruzione_by_comune.json"
    if "IT" in countries and it_istruzione.exists():
        try:
            ist = json.loads(it_istruzione.read_text(encoding="utf-8"))
            countries["IT"]["istruzione_by_osm"] = ist.get("by_osm", {})
            countries["IT"]["istruzione_total_schools"] = ist.get("total_schools", 0)
            countries["IT"]["istruzione_national"] = ist.get("national_totals", {})
            # Per-school point markers (when geocoded). Heavy when full
            # (~8K points = ~1MB) — kept inline because the user's intent
            # is to see them on the map, not lazy-load.
            countries["IT"]["istruzione_points"] = ist.get("points", [])
            print(f"  IT istruzione: {ist.get('total_schools')} schools across "
                  f"{ist.get('comuni_with_schools')} comuni")
        except Exception as e:
            print(f"  WARN: cannot load it_istruzione_by_comune.json: {e!r}")

    return {"generated": generated, "total": len(munis), "countries": countries}


def main():
    data_path = ROOT / "data.json"
    if not data_path.exists():
        print("Error: data.json not found")
        sys.exit(1)

    with open(data_path, encoding="utf-8") as f:
        raw = json.load(f)

    munis = raw.get("municipalities", {})
    if isinstance(munis, list):
        munis = {m["bfs"]: m for m in munis}

    generated = raw.get("generated", raw.get("generated_at", ""))

    summary_munis = {}
    detail_munis = {}

    for bfs, m in munis.items():
        # Summary: core fields + has_mx flag
        summary = {k: m[k] for k in SUMMARY_FIELDS if k in m}
        summary["has_mx"] = len(m.get("mx", [])) > 0
        summary_munis[bfs] = summary

        # Detail: popup-only fields
        detail = {k: m[k] for k in DETAIL_FIELDS if k in m}
        if detail:
            detail_munis[bfs] = detail

    # Emit mx_discovery_stats.json for methodology.html consumption.
    # Per-method counts across IT enti — also gets used in the methodology
    # page table. Keep alongside data/reports/ so it's served statically.
    from collections import Counter as _Counter
    _disc = _Counter()
    _disc_total = 0
    for _m in munis.values():
        if (_m.get("country") or "").upper() != "IT":
            continue
        _disc_total += 1
        _disc[_m.get("mx_discovery_method") or "unknown"] += 1
    _disc_out = ROOT / "data" / "reports" / "mx_discovery_stats.json"
    _disc_out.parent.mkdir(parents=True, exist_ok=True)
    with open(_disc_out, "w", encoding="utf-8") as f:
        json.dump({"total": _disc_total, "by_method": dict(_disc)}, f,
                  ensure_ascii=False, indent=2)
    print(f"  mx_discovery_stats.json: {_disc_total} enti, {len(_disc)} metodi")

    # Write region-level aggregations (lightweight, loaded first)
    regions_out = ROOT / "data-regions.json"
    regions_data = build_region_data(munis, generated)
    with open(regions_out, "w", encoding="utf-8") as f:
        json.dump(regions_data, f, separators=(",", ":"), ensure_ascii=False)
    print(f"  data-regions.json: {regions_out.stat().st_size:,} bytes")

    # Write per-country drill-down files (summary + key detail fields)
    summary_dir = ROOT / "data" / "summary"
    summary_dir.mkdir(exist_ok=True)
    by_country: dict[str, list] = {}
    for bfs, m in munis.items():
        cc = m.get("country", "")
        if not cc:
            continue
        # Merge summary + selected detail fields
        entry = {k: m[k] for k in SUMMARY_FIELDS if k in m}
        entry["has_mx"] = len(m.get("mx", [])) > 0
        # Add detail fields needed for drill-down
        for field in ("mx", "reason", "gateway", "spf", "autodiscover",
                      "dkim", "txt_verifications", "tenant", "smtp_software"):
            if m.get(field):
                entry[field] = m[field]
        by_country.setdefault(cc, []).append(entry)
    total_country_size = 0
    for cc, entries in by_country.items():
        cc_path = summary_dir / f"{cc.lower()}.json"
        with open(cc_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, separators=(",", ":"), ensure_ascii=False)
        total_country_size += cc_path.stat().st_size
    print(f"  data/summary/*.json: {len(by_country)} files, {total_country_size:,} bytes total")

    # Write summary
    summary_out = ROOT / "data-summary.json"
    summary_data = {
        "generated": generated,
        "municipalities": summary_munis,
    }
    with open(summary_out, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, separators=(",", ":"), ensure_ascii=False)
    print(f"  data-summary.json: {summary_out.stat().st_size:,} bytes")

    # Write detail
    detail_out = ROOT / "data-detail.json"
    with open(detail_out, "w", encoding="utf-8") as f:
        json.dump(detail_munis, f, separators=(",", ":"), ensure_ascii=False)
    print(f"  data-detail.json:  {detail_out.stat().st_size:,} bytes")

    # Compare with original
    orig_size = data_path.stat().st_size
    new_size = summary_out.stat().st_size + detail_out.stat().st_size
    print(
        f"  Original data.json: {orig_size:,} bytes"
        f" -> {new_size:,} bytes ({new_size * 100 // orig_size}%)"
    )


if __name__ == "__main__":
    main()
