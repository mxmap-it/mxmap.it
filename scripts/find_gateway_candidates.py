#!/usr/bin/env python3
"""Censimento dei gateway email NON mappati — candidati per GATEWAY_KEYWORDS.

Trova gli MX che con ogni probabilità sono **gateway di posta di terzi**
(antispam/antivirus/relay) che mascherano il backend reale, e che NON sono ancora
in `GATEWAY_KEYWORDS`. È il metodo che ha smascherato Libraesva (issue #14): da
girare dopo ogni run per far emergere automaticamente i nuovi gateway.

Segnale (in ordine di forza):
  1. l'MX è di un soggetto TERZO (dominio diverso da quello dell'ente);
  2. l'ente è classificato NON-cloud (independent/local-isp/provider IT/aruba…);
  3. lo SPF rivela un backend cloud estero:
       - Microsoft : include:spf.protection.outlook.com   (forte: hosting caselle)
       - Google    : include:_spf.google.com              (forte: hosting caselle)
       - AWS/SES   : amazonses.com / amazonaws            (DEBOLE: spesso solo invio
                     transazionale del gateway, non hosting → da validare a mano).

Conferma definitiva del backend (fuori da questo script, manuale):
  - Microsoft : login.microsoftonline.com/getuserrealm.srf → NameSpaceType=Managed/Federated
  - Google    : record TXT `google._domainkey.<dominio>`  → chiave DKIM Google

Uso:
  uv run python3 scripts/find_gateway_candidates.py [--min-entities 2] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))

try:  # console Windows (cp1252)
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from mail_sovereignty.constants import (  # noqa: E402
    GATEWAY_KEYWORDS,
    PROVIDER_KEYWORDS,
)

CLOUD_PROVIDERS = {"microsoft", "google", "aws"}


def _known_keywords() -> set[str]:
    known: set[str] = set()
    for d in (GATEWAY_KEYWORDS, PROVIDER_KEYWORDS):
        for kws in d.values():
            known.update(k.lower() for k in kws)
    return known


def backend_from_spf(spf: str | None) -> str | None:
    """Backend cloud rivelato dallo SPF (None se nessuno)."""
    s = (spf or "").lower()
    if "protection.outlook" in s or "sharepointonline" in s:
        return "microsoft"
    if "_spf.google" in s or "google.com" in s:
        return "google"
    if "amazonses" in s or "amazonaws" in s:
        return "aws"
    return None


def registrable(host: str) -> str:
    """Approssimazione del dominio registrabile: ultime due label."""
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def find_candidates(entities: list[dict], min_entities: int = 2) -> list[dict]:
    known = _known_keywords()
    by_vendor: dict[str, dict] = defaultdict(
        lambda: {
            "entities": set(),
            "backends": Counter(),
            "providers": Counter(),
            "hosts": set(),
        }
    )
    for e in entities:
        mx = e.get("mx") or []
        if not mx:
            continue
        host = mx[0].lower().rstrip(".")
        dom = (e.get("domain") or "").lower()
        # MX sul dominio dell'ente → self-hosting, non un gateway di terzi
        if host == dom or (dom and host.endswith("." + dom)):
            continue
        provider = e.get("provider")
        if provider in CLOUD_PROVIDERS:  # già classificato cloud → nessun mascheramento
            continue
        backend = backend_from_spf(e.get("spf"))
        if not backend:
            continue
        # MX già mappato? Il match va fatto sull'HOST completo (come detect_gateway):
        # es. "esva" matcha esva.labassaromagna.it ma non il dominio labassaromagna.it.
        # Esclude sia i gateway noti sia i provider noti (lì lo SPF cloud è rumore).
        if any(k in host for k in known):
            continue
        vend = registrable(host)
        rec = by_vendor[vend]
        rec["entities"].add(dom)
        rec["backends"][backend] += 1
        rec["providers"][provider] += 1
        rec["hosts"].add(host)

    out = []
    for vend, rec in by_vendor.items():
        n = len(rec["entities"])
        if n < min_entities:
            continue
        # confidenza: MS/Google = hosting caselle (forte); AWS-only = debole
        strong = rec["backends"].get("microsoft", 0) + rec["backends"].get("google", 0)
        out.append(
            {
                "vendor": vend,
                "n_entities": n,
                "backends": dict(rec["backends"]),
                "current_providers": dict(rec["providers"]),
                "sample_hosts": sorted(rec["hosts"])[:3],
                "sample_entities": sorted(rec["entities"])[:3],
                "confidence": "strong" if strong >= n else "weak (AWS-only)",
            }
        )
    out.sort(key=lambda c: (-c["n_entities"], c["vendor"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--country", default="IT")
    ap.add_argument("--min-entities", type=int, default=2)
    ap.add_argument("--json", type=Path, help="scrive anche l'elenco in JSON")
    args = ap.parse_args()

    d = json.loads(args.data.read_text(encoding="utf-8"))
    muns = d.get("municipalities") or d
    entities = [
        v
        for v in muns.values()
        if (v.get("country") or "").upper() == args.country.upper()
    ]
    cands = find_candidates(entities, args.min_entities)

    print(f"=== Candidati gateway non mappati ({args.country}): {len(cands)} ===")
    print(f"{'vendor (dominio MX)':26} {'#enti':>5}  {'backend':18} {'conf.':14} host")
    for c in cands:
        be = ",".join(f"{k}:{v}" for k, v in sorted(c["backends"].items()))
        print(
            f"{c['vendor']:26} {c['n_entities']:>5}  {be:18} {c['confidence']:14} "
            f"{c['sample_hosts'][0]}"
        )
    print(
        "\nNota: backend Microsoft/Google = hosting caselle (forte). AWS-only è "
        "debole (spesso solo invio del gateway). Conferma prima di mappare: "
        "getuserrealm (MS) / google._domainkey (Google)."
    )

    if args.json:
        args.json.write_text(
            json.dumps(cands, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nScritto: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
