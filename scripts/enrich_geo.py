#!/usr/bin/env python3
"""Arricchimento geografico di data.json: regione / provincia / comune / macroarea.

Passo strutturale della pipeline: per ogni ente IT risolve la chiave-sede pulita
`ipa_codice_comune_istat` (dal seed, presente al 100%) sul crosswalk ufficiale
ISTAT (data/istat_comuni.json) tramite mail_sovereignty.geo, e scrive i campi
geografici su data.json. Sostituisce il dato territoriale **sporco** di IndicePA
(il campo `region` del seed è incompleto e a volte è il nome dell'ente) con quello
ufficiale ISTAT. Idempotente e ri-eseguibile. Vedi mxmap.it#2.

Uso: uv run python3 scripts/enrich_geo.py [--country IT]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from mail_sovereignty.geo import (  # noqa: E402
    SCONOSCIUTA,
    build_istat_index,
    resolve_geo,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--seed", type=Path, default=ROOT / "data" / "municipalities_it.json")
    ap.add_argument("--istat", type=Path, default=ROOT / "data" / "istat_comuni.json")
    ap.add_argument("--country", default="IT")
    args = ap.parse_args()

    istat = json.loads(args.istat.read_text(encoding="utf-8"))
    index = build_istat_index(istat.get("comuni", []))
    print(f"ISTAT: {len(index)} codici (con alias storici)")

    seed = json.loads(args.seed.read_text(encoding="utf-8"))
    seed_istat = {
        e.get("id"): e.get("ipa_codice_comune_istat")
        for e in seed
        if e.get("id")
    }

    d = json.loads(args.data.read_text(encoding="utf-8"))
    muns = d.get("municipalities") or d
    cc = args.country.upper()

    n = resolved = 0
    regioni: Counter = Counter()
    for key, entity in muns.items():
        if (entity.get("country") or "").upper() != cc:
            continue
        ent_id = entity.get("bfs") or entity.get("id") or key
        geo = resolve_geo(seed_istat.get(ent_id), index)
        entity.update(geo)
        n += 1
        regioni[geo["regione"]] += 1
        if geo["regione"] != SCONOSCIUTA:
            resolved += 1

    args.data.write_text(
        json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    pct = round(100 * resolved / n, 1) if n else 0.0
    print(f"=== enrich_geo ({cc}): {n} enti · regione risolta {resolved} ({pct}%) ===")
    for reg, c in regioni.most_common():
        print(f"  {reg:24} {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
