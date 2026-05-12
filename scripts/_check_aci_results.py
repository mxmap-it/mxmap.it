#!/usr/bin/env python3
"""Verifica risultati ACI dopo rule 6.6."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.load(open(ROOT / "data.json", encoding="utf-8"))
muns = d.get("municipalities") or d
aci = [(k, m) for k, m in muns.items() if k.startswith("IT-C13-")]
print(f"Totale ACI (C13): {len(aci)}")
print("Providers:", Counter(m.get("provider") for _, m in aci).most_common())
print()
print("--- ACI con domain_used (recuperati via fallback) ---")
for k, m in aci:
    if m.get("domain_used"):
        name = (m.get("name") or "")[:32]
        dom = m.get("domain") or ""
        used = m.get("domain_used") or ""
        prov = m.get("provider")
        rsn = (m.get("reason") or m.get("recovery_legit_reason") or "")[:90]
        print(f"  {k:<22} {name:<34} {dom} -> {used} ({prov})")
        print(f"    {rsn}")

print()
print("--- ACI ancora unknown ---")
for k, m in aci:
    if m.get("provider") == "unknown":
        name = (m.get("name") or "")[:32]
        dom = m.get("domain") or ""
        print(f"  {k:<22} {name:<34} seed={dom}")
