#!/usr/bin/env python3
"""One-shot backfill: write `mx_discovery_method` + `mx_discovery_evidence`
on every IT entry in data.json by inferring from existing audit fields
(domain_correction_source, miur_tenant_dependency, scraped_email, etc.).

Idempotent: re-running re-derives the same values.

Usage: uv run python3 scripts/backfill_mx_discovery.py
"""
from __future__ import annotations
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))
from mail_sovereignty.mx_discovery import infer_method_from_entry, set_discovery

DATAJSON = ROOT / "data.json"

def main() -> int:
    data = json.loads(DATAJSON.read_text(encoding="utf-8"))
    muns = data.get("municipalities") or data
    n = 0
    stats: Counter[str] = Counter()
    for k, m in muns.items():
        if (m.get("country") or "").upper() != "IT":
            continue
        method, evidence = infer_method_from_entry(m)
        set_discovery(m, method, evidence)
        stats[method] += 1
        n += 1
    DATAJSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Backfilled {n} IT entries.\n")
    print("Distribuzione per metodo di scoperta:")
    for m, c in stats.most_common():
        print(f"  {m:<28} {c}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
