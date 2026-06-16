#!/usr/bin/env python3
"""For each remaining IT unknown, query Wikidata (P856 = official website)
and present a wrong-vs-corrected diff. The user wanted to fix unknowns
manually but suspects the IndicePA-listed domain is stale; this script
auto-suggests the current canonical website by ISTAT-code-keyed Wikidata
lookup.

Output: data/reports/it_unknowns_corrected.txt + .json
Usage: uv run python3 scripts/discover_correct_it_unknowns.py
"""

from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from mail_sovereignty.dns import lookup_mx

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = DATA / "reports"

SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "mxmap.it-correct-discovery/0.1 (+https://github.com/mxmap-it/mxmap.it)"


def sparql_query(query: str) -> list[dict]:
    url = f"{SPARQL_URL}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8")).get("results", {}).get("bindings", [])


def hostname_of(url: str) -> str:
    if not url:
        return ""
    try:
        h = urlparse(url if "://" in url else f"https://{url}").hostname or ""
    except Exception:
        return ""
    return h.lower().lstrip("www.").rstrip(".")


def fetch_wikidata_websites(istat_codes: list[str]) -> dict[str, dict]:
    """Return {istat_code: {name, website, qid}} for the given ISTAT codes.

    Uses VALUES to inject all codes in one SPARQL query — Wikidata handles
    this for hundreds of entries fine.
    """
    values_block = " ".join(f'"{c}"' for c in istat_codes)
    query = f"""
SELECT ?item ?itemLabel ?istat ?website WHERE {{
  VALUES ?istat {{ {values_block} }}
  ?item wdt:P635 ?istat ;
        wdt:P17 wd:Q38 .
  OPTIONAL {{ ?item wdt:P856 ?website }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "it,en" }}
}}
"""
    rows = sparql_query(query)
    out: dict[str, dict] = {}
    for r in rows:
        istat = r["istat"]["value"]
        # If multiple entries per istat (rare — historical), prefer one with website
        existing = out.get(istat)
        website = r.get("website", {}).get("value", "")
        if existing and not website and existing.get("website"):
            continue
        out[istat] = {
            "qid": r["item"]["value"].rsplit("/", 1)[-1],
            "name": r.get("itemLabel", {}).get("value", ""),
            "website": website,
        }
    return out


async def mx_check(domain: str) -> tuple[bool, list[str]]:
    if not domain:
        return False, []
    try:
        mx = await lookup_mx(domain)
    except Exception:
        return False, []
    return bool(mx), mx


async def main_async() -> int:
    seed = json.loads((DATA / "municipalities_it.json").read_text(encoding="utf-8"))
    seed_by_id = {e["id"]: e for e in seed}
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    muns = data["municipalities"]

    # Pull the unknowns
    unknowns: list[tuple[str, dict, dict]] = []
    for k, v in muns.items():
        if v.get("country") != "IT":
            continue
        if v.get("provider") != "unknown":
            continue
        eid = v.get("id") or k
        s = seed_by_id.get(eid)
        if not s:
            continue
        unknowns.append((k, v, s))

    print(f"Found {len(unknowns)} IT entries still unknown")
    if not unknowns:
        return 0

    istat_codes = sorted(
        {(s.get("ipa_codice_comune_istat") or "").zfill(6) for _, _, s in unknowns if s.get("ipa_codice_comune_istat")}
    )
    print(f"Querying Wikidata for {len(istat_codes)} ISTAT codes...")
    wd = fetch_wikidata_websites(istat_codes)
    print(f"  Got {len(wd)} Wikidata matches (with or without website)")

    # MX-check the suggested websites in parallel
    print("MX-checking suggested websites...")
    rows: list[dict] = []
    for key, entry, s in unknowns:
        istat = (s.get("ipa_codice_comune_istat") or "").zfill(6)
        wd_entry = wd.get(istat) or {}
        suggested = hostname_of(wd_entry.get("website", ""))
        current = (s.get("domain") or "").lower()
        rows.append({
            "key": key,
            "id": s.get("id"),
            "name": s.get("name") or entry.get("name"),
            "istat": istat,
            "current_domain": current,
            "wd_qid": wd_entry.get("qid", ""),
            "wd_name": wd_entry.get("name", ""),
            "suggested_domain": suggested,
            "current_pipeline_reason": entry.get("reason", ""),
        })

    # Async MX checks (only for new suggested domains)
    suggested_domains = sorted({r["suggested_domain"] for r in rows if r["suggested_domain"] and r["suggested_domain"] != r["current_domain"]})
    print(f"  {len(suggested_domains)} unique suggested domains different from IndicePA")
    mx_status: dict[str, tuple[bool, list[str]]] = {}

    sem = asyncio.Semaphore(10)
    async def worker(d: str):
        async with sem:
            mx_status[d] = await mx_check(d)
    await asyncio.gather(*(worker(d) for d in suggested_domains))

    # Annotate rows with MX result
    for r in rows:
        d = r["suggested_domain"]
        if d and d != r["current_domain"]:
            ok, mx = mx_status.get(d, (False, []))
            r["mx_ok"] = ok
            r["mx_records"] = mx
        else:
            r["mx_ok"] = None
            r["mx_records"] = []

    # Categorise
    by_outcome = defaultdict(list)
    for r in rows:
        if not r["suggested_domain"]:
            cat = "no_wikidata_website"
        elif r["suggested_domain"] == r["current_domain"]:
            cat = "same_as_current"
        elif r["mx_ok"]:
            cat = "corrected_with_mx"
        else:
            cat = "suggested_no_mx"
        by_outcome[cat].append(r)

    # Build report
    lines: list[str] = []
    lines.append("=" * 110)
    lines.append(f"Wrong vs corrected websites — IT unknowns auto-suggestion via Wikidata P856 ({len(rows)} entries)")
    lines.append("=" * 110)
    lines.append("")
    lines.append("Outcome categories:")
    for cat, items in sorted(by_outcome.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"  {cat:<25} {len(items):>3}")
    lines.append("")

    for cat in ["corrected_with_mx", "suggested_no_mx", "same_as_current", "no_wikidata_website"]:
        items = by_outcome.get(cat, [])
        if not items:
            continue
        lines.append("=" * 110)
        lines.append(f"### {cat.upper()} ({len(items)} entries)")
        lines.append("=" * 110)
        lines.append("")
        if cat == "corrected_with_mx":
            lines.append("These have a different Wikidata-listed website AND that website has MX records.")
            lines.append("Strong candidates to overwrite the IndicePA domain in seed data.")
        elif cat == "suggested_no_mx":
            lines.append("Wikidata suggests a different website but it has no MX. May still be the correct site")
            lines.append("(no email there) or may itself be stale.")
        elif cat == "same_as_current":
            lines.append("Wikidata agrees with IndicePA's stale domain — Wikidata isn't more current here.")
        elif cat == "no_wikidata_website":
            lines.append("Wikidata has no P856 for this comune — manual web search needed.")
        lines.append("")
        for r in items:
            lines.append(f"  {r['id']}  {r['name']}  (ISTAT {r['istat']}, Wikidata {r['wd_qid']})")
            lines.append(f"    current (IndicePA)   : {r['current_domain']}")
            lines.append(f"    suggested (Wikidata) : {r['suggested_domain'] or '(none)'}")
            if r.get("mx_records"):
                lines.append(f"    MX on suggested      : {', '.join(r['mx_records'][:3])}")
            lines.append(f"    pipeline reason      : {r['current_pipeline_reason']}")
            lines.append("")

    out_txt = REPORTS / "it_unknowns_corrected.txt"
    out_txt.write_text("\n".join(lines), encoding="utf-8")
    out_json = REPORTS / "it_unknowns_corrected.json"
    out_json.write_text(json.dumps({
        "summary": {cat: len(by_outcome.get(cat, [])) for cat in
                     ["corrected_with_mx", "suggested_no_mx", "same_as_current", "no_wikidata_website"]},
        "rows": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"Wrote {out_txt}")
    print(f"Wrote {out_json}")
    print()
    print("Outcome:")
    for cat, items in sorted(by_outcome.items(), key=lambda kv: -len(kv[1])):
        print(f"  {cat:<25} {len(items):>3}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
