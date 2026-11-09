"""EU Security Map (#33 F2–F3): consolida la directory e scansiona i domini email.

Solo lookup DNS passivi su record pubblici (MX/SPF/DKIM/TXT/CNAME), gli stessi
che mxmap esegue per ogni PA italiana: nessuna connessione ai server degli enti.
Riusa preprocess.scan_municipality con cache dedicata; NON tocca data.json.

Output:
  data/eu_security/entities.json  directory consolidata
  data/eu_security/results.json   un record per (ente, dominio) + verdetto ente
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from mail_sovereignty.dns_cache import DnsCache
from mail_sovereignty.preprocess import scan_municipality

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "data" / "eu_security" / "research"
RESEARCH_EXT = ROOT / "data" / "eu_security" / "research_ext"  # wave 2
OUT_DIR = ROOT / "data" / "eu_security"
VALID_TYPES = {
    "police",
    "gendarmerie",
    "border_guard",
    "intelligence",
    "interior_ministry",
    "defence_ministry",
    "cybersecurity",
    "other_natsec",
    "armed_forces",
}
DOMAIN_RE = re.compile(r"^(?=.{3,253}$)([a-z0-9-]+\.)+[a-z]{2,}$")


def load_directory() -> tuple[list[dict], list[str]]:
    entities, problems, seen = [], [], set()
    for f in [*sorted(RESEARCH.glob("*.json")), *sorted(RESEARCH_EXT.glob("*.json"))]:
        doc = json.loads(f.read_text(encoding="utf-8"))
        cc = doc["country"].upper()
        for e in doc.get("entities", []):
            eid = e.get("id", "")
            if eid in seen:
                problems.append(f"{f.name}: id duplicato {eid}")
                continue
            seen.add(eid)
            if e.get("type") not in VALID_TYPES:
                problems.append(f"{eid}: type invalido {e.get('type')}")
                e["type"] = "other_natsec"
            doms = []
            for d in e.get("mail_domains") or []:
                d = d.strip().lower().rstrip(".")
                if DOMAIN_RE.match(d) and d not in doms:
                    doms.append(d)
                else:
                    problems.append(f"{eid}: dominio scartato {d!r}")
            entities.append(
                {
                    **e,
                    "country": cc,
                    "country_name_en": doc.get("country_name_en", cc),
                    "group": doc.get("group", ""),
                    "mail_domains": doms,
                }
            )
    return entities, problems


async def scan(entities: list[dict]) -> list[dict]:
    cache = DnsCache("EUSEC")
    sem = asyncio.Semaphore(10)
    domains = sorted({d for e in entities for d in e["mail_domains"]})

    async def one(d: str) -> tuple[str, dict]:
        m = {"bfs": d, "name": d, "country": "", "website": f"https://{d}"}
        try:
            r = await scan_municipality(m, sem, dns_cache=cache)
        except Exception as exc:  # resilienza: un dominio strano non ferma il run
            r = {"provider": "unknown", "reason": f"scan error: {exc}", "mx": []}
        return d, r

    print(f"Scanning {len(domains)} distinct mail domains…")
    res = dict(await asyncio.gather(*(one(d) for d in domains)))
    cache.save()

    keep = ("mx", "spf", "provider", "reason", "gateway", "mx_countries", "dkim")
    out = []
    for e in entities:
        scans = []
        for d in e["mail_domains"]:
            r = res.get(d, {})
            # il guessing per nome non deve mai sostituire il dominio esplicito
            if r.get("domain") and r["domain"] != d:
                r = {"provider": "unknown", "reason": "no MX on domain", "mx": []}
            scans.append({"domain": d, **{k: r.get(k) for k in keep if k in r}})
        primary = next((s for s in scans if s.get("mx")), scans[0] if scans else {})
        out.append(
            {
                **{k: e.get(k) for k in (
                    "id", "country", "country_name_en", "group", "type",
                    "name_native", "name_en", "acronym", "website", "confidence",
                )},
                "mail_domains": e["mail_domains"],
                "primary_domain": primary.get("domain"),
                "provider": primary.get("provider", "unknown"),
                "reason": primary.get("reason", "no mail domain"),
                "mx": primary.get("mx") or [],
                "mx_countries": primary.get("mx_countries") or [],
                "gateway": primary.get("gateway"),
                "scans": scans,
                "domain_evidence": next(
                    (
                        ev
                        for ev in e.get("evidence") or []
                        if (ev.get("domain") or "").lower() == primary.get("domain")
                    ),
                    None,
                ),
            }
        )
    return out


def main() -> int:
    entities, problems = load_directory()
    print(f"Directory: {len(entities)} entities, {len(problems)} problems")
    for p in problems:
        print("  -", p)
    (OUT_DIR / "entities.json").write_text(
        json.dumps(entities, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    results = asyncio.run(scan(entities))
    (OUT_DIR / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    from collections import Counter

    print(Counter(r["provider"] for r in results).most_common())
    return 0


if __name__ == "__main__":
    sys.exit(main())
