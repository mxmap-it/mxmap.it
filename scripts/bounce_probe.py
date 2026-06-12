#!/usr/bin/env python3
"""Bounce-verifier — SETUP + DRY-RUN (non invia email).

Imposta la verifica attiva dei casi a bassa confidenza (vedi
docs/LOW_CONFIDENCE_CASES.md): seleziona gli enti `frgn_mx_only` (conf 0,50,
MX presente ma backend ignoto), genera per ciascuno un indirizzo-target
inesistente e mostra cosa *verrebbe* inviato. NON spedisce nulla.

L'invio reale (lettura NDR via IMAP + parsing) è volutamente NON implementato
qui: è un'azione esterna che richiede il setup e l'autorizzazione esplicita
dell'utente (account Google Workspace dedicato). `--send` solleva un errore.

Uso:
  python3 scripts/bounce_probe.py --export      # scrive data/bounce/candidates.{csv,json}
  python3 scripts/bounce_probe.py --dry-run     # stampa i probe pianificati (default)
  python3 scripts/bounce_probe.py --send        # bloccato: non implementato
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "data" / "bounce"

# Local-part inesistente e riconoscibile: deve generare un NDR (no such user)
# ed essere ovviamente un probe, non un tentativo di raggiungere una persona.
PROBE_LOCALPART = "mxmap-probe-no-such-mailbox"

# Coorte target: bassa confidenza CON MX (bounce-testabile). Vedi doc.
TARGET_RULES = {"frgn_mx_only"}
CONF_MAX = 0.60


def select_candidates(data_path: Path) -> list[dict]:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    muns = data.get("municipalities", data)
    out = []
    for v in muns.values():
        if (v.get("country") or "").upper() != "IT":
            continue
        conf = v.get("classification_confidence") or 0.0
        rule = v.get("classification_rule")
        mx = v.get("mx") or []
        if rule in TARGET_RULES and 0.0 < conf < CONF_MAX and mx:
            out.append(
                {
                    "bfs": v.get("bfs", ""),
                    "name": v.get("name", ""),
                    "domain": v.get("domain", ""),
                    "mx": ";".join(mx),
                    "mx_jurisdiction": v.get("mx_jurisdiction", ""),
                    "confidence": conf,
                    "rule": rule,
                    "reason": (v.get("reason") or "")[:160],
                    "target_address": f"{PROBE_LOCALPART}@{v.get('domain', '')}",
                }
            )
    out.sort(key=lambda r: r["domain"])
    return out


def export(cands: list[dict]) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "candidates.json").write_text(
        json.dumps(cands, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    cols = [
        "bfs",
        "name",
        "domain",
        "mx",
        "mx_jurisdiction",
        "confidence",
        "rule",
        "target_address",
        "reason",
    ]
    with open(OUTDIR / "candidates.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for c in cands:
            w.writerow({k: c.get(k, "") for k in cols})
    print(f"Scritti {len(cands)} candidati in {OUTDIR}/candidates.{{csv,json}}")


def dry_run(cands: list[dict]) -> None:
    domains = sorted({c["domain"] for c in cands})
    print(
        f"DRY-RUN: {len(cands)} enti su {len(domains)} domini distinti "
        f"(NESSUN invio; si invia 1 probe per dominio).\n"
    )
    for c in cands[:15]:
        mx0 = c["mx"].split(";")[0]
        name = c["name"].encode("ascii", "replace").decode()[:30]
        print(f"  -> {c['target_address']:48}  via MX {mx0[:40]:40}  [{name}]")
    if len(cands) > 15:
        print(f"  ... e altri {len(cands) - 15}. Lista completa: data/bounce/candidates.csv")
    print(
        "\nNessuna email inviata. L'invio reale richiede il tuo setup Workspace "
        "e va abilitato esplicitamente (vedi --send)."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--export", action="store_true", help="scrive candidates.{csv,json}")
    ap.add_argument("--dry-run", action="store_true", help="stampa i probe (default)")
    ap.add_argument("--send", action="store_true", help="BLOCCATO: invio non implementato")
    args = ap.parse_args()

    if args.send:
        print(
            "ERRORE: l'invio reale non è implementato in questo scaffold.\n"
            "È un'azione esterna: richiede account Google Workspace dedicato, "
            "lettura NDR via IMAP e parser, e la tua autorizzazione esplicita.\n"
            "Per ora usa --export e --dry-run.",
            file=sys.stderr,
        )
        return 2

    cands = select_candidates(args.data)
    if args.export:
        export(cands)
    if args.dry_run or not args.export:
        dry_run(cands)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
