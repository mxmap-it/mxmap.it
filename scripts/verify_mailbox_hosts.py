"""Verifica attiva della coorte mailbox-host (farm Zimbra/Carbonio) — #31.

Per ogni ente IT il cui MX è su una farm Zimbra/Carbonio (o matcha
zimbra|carbonio|zextras), sonda via HTTPS i frontend candidati (autodiscover,
webmail convenzionali, MX stesso) e assegna un verdetto di evidenza:

  mailbox_host_confirmed | farm_autodiscover | farm_mx_confirmed |
  hybrid_cloud | unverified

Scrive il report in data/reports/mailbox_host_verification.{json,md}
(evidenza committata: regola "restore, don't regenerate"). Ripartibile:
la cache per-host nel JSON viene riusata nei rerun (--refresh per rifare).

Uso:
    python scripts/verify_mailbox_hosts.py [--limit N] [--refresh]
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mail_sovereignty.constants import MAILBOX_HOST_GATEWAYS  # noqa: E402
from mail_sovereignty.mailbox_hosts import (  # noqa: E402
    FARM_DOMAINS,
    candidate_hosts,
    classify_login_page,
    entity_verdict,
    farm_of,
)

PAT = re.compile(r"zimbra|carbonio|zextras", re.I)
UA = "mxmap-mailbox-verifier/1.0 (+https://mxmap.it; issue #31)"
PROBE_PATHS = ("/", "/static/login/")


def probe_host(host: str, timeout: float) -> dict:
    """GET HTTPS sull'host: ritorna {software, title, final, error}."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # fingerprinting, non fiducia
    last_err = ""
    for path in PROBE_PATHS:
        try:
            req = urllib.request.Request(
                f"https://{host}{path}", headers={"User-Agent": UA}
            )
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                final = r.geturl()
                body = r.read(60000).decode("utf-8", "replace")
            title = ""
            low = body.lower()
            if "<title>" in low:
                title = low.split("<title>", 1)[1].split("</title>", 1)[0][:80]
            sw = classify_login_page(body, title)
            if sw or path == PROBE_PATHS[-1]:
                return {"software": sw, "title": title, "final": final, "error": ""}
        except Exception as e:  # rete/SSL/HTTP: registra e prova il prossimo path
            last_err = f"{type(e).__name__}: {e}"[:90]
    return {"software": None, "title": "", "final": "", "error": last_err}


def select_cohort(munis: dict) -> dict[str, dict]:
    out = {}
    for bid, e in munis.items():
        if not bid.startswith("IT-"):
            continue
        mx = e.get("mx") or []
        if (e.get("gateway") in MAILBOX_HOST_GATEWAYS) or any(
            PAT.search(h or "") for h in mx
        ):
            out[bid] = e
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data.json"))
    ap.add_argument(
        "--out",
        default=str(ROOT / "data" / "reports" / "mailbox_host_verification"),
        help="prefisso output (.json/.md)",
    )
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refresh", action="store_true", help="ignora la cache host")
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        d = json.load(f)
    munis = d["municipalities"] if "municipalities" in d else d
    cohort = select_cohort(munis)
    if args.limit:
        cohort = dict(list(cohort.items())[: args.limit])
    print(f"coorte mailbox-host: {len(cohort)} enti")

    out_json = Path(args.out + ".json")
    host_cache: dict[str, dict] = {}
    if out_json.exists() and not args.refresh:
        try:
            prev = json.loads(out_json.read_text(encoding="utf-8"))
            host_cache = prev.get("hosts", {})
            print(f"cache host riusata: {len(host_cache)} host già sondati")
        except Exception as e:
            print(f"cache precedente illeggibile ({e}): riparto da zero")

    # host unici da sondare: candidati degli enti + frontend noti delle farm
    wanted: list[str] = []
    for e in cohort.values():
        for h in candidate_hosts(e):
            if h not in wanted:
                wanted.append(h)
    for farm in FARM_DOMAINS:
        for pfx in ("proxy", "webmail", "mail"):
            h = f"{pfx}.{farm}"
            if h not in wanted:
                wanted.append(h)
    todo = [h for h in wanted if h not in host_cache]
    print(f"host unici: {len(wanted)}, da sondare ora: {len(todo)}")

    if todo:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for host, res in zip(
                todo, ex.map(lambda h: probe_host(h, args.timeout), todo)
            ):
                host_cache[host] = res
                tag = res["software"] or (res["error"][:40] if res["error"] else "-")
                print(f"  {host}: {tag}")

    probed = {h: r.get("software") for h, r in host_cache.items()}
    confirmed_farms = {
        farm_of(h) for h, sw in probed.items() if sw and farm_of(h)
    } - {None}
    print(f"farm confermate via login: {sorted(confirmed_farms)}")

    entities = {}
    counts: dict[str, int] = {}
    for bid, e in sorted(cohort.items()):
        verdict, ev = entity_verdict(e, probed, confirmed_farms)
        counts[verdict] = counts.get(verdict, 0) + 1
        entities[bid] = {
            "name": e.get("name"),
            "domain": e.get("domain"),
            "mx": e.get("mx"),
            "gateway": e.get("gateway"),
            "provider_attuale": e.get("provider"),
            "confidence_attuale": e.get("classification_confidence"),
            "verdict": verdict,
            "evidence": ev,
        }

    generated = datetime.now(UTC).isoformat(timespec="seconds")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(
            {
                "generated_at": generated,
                "cohort": len(cohort),
                "counts": counts,
                "confirmed_farms": sorted(confirmed_farms),
                "hosts": host_cache,
                "entities": entities,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    # report leggibile
    lines = [
        "# Verifica mailbox host (farm Zimbra/Carbonio) — issue #31",
        "",
        f"Generato: {generated} · coorte: {len(cohort)} enti · "
        f"host sondati: {len(host_cache)}",
        "",
        "| Verdetto | Enti |",
        "|---|---:|",
    ]
    for v, n in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {v} | {n} |")
    lines += ["", f"Farm confermate via pagina di login: {sorted(confirmed_farms)}", ""]
    for section, verdicts in (
        ("## Ibridi cloud genuini (il fix non li tocca)", {"hybrid_cloud"}),
        ("## Da verificare a mano (nessuna evidenza attiva)", {"unverified"}),
    ):
        rows = [
            (bid, r) for bid, r in entities.items() if r["verdict"] in verdicts
        ]
        lines.append(section)
        if not rows:
            lines.append("(nessuno)")
        for bid, r in rows:
            lines.append(
                f"- `{bid}` {r['domain']} — {r['provider_attuale']}; {r['evidence']}"
            )
        lines.append("")
    Path(args.out + ".md").write_text("\n".join(lines), encoding="utf-8")

    print(f"\nverdetti: {counts}")
    print(f"report: {out_json} + .md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
