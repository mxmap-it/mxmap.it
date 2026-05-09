#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "data" / "reports" / "scraped_mx_bug_audit.json").read_text(encoding="utf-8"))
print(f"Total IT enti: {d['total_it']}")
print(f"  with MX:     {d['total_with_mx']}")
print(f"  SUSPICIOUS:  {d['suspicious_count']} ({d['suspicious_count']/d['total_with_mx']*100:.2f}%)")
print()
print("=== Top 15 most-shared spurious MX (BUG signature: same wrong MX on N enti) ===")
for k, v in list(d["shared_mx"].items())[:15]:
    print(f"  {v:>4}x  {k}")
print()
cats = Counter()
for it in d["items"]:
    if it.get("tenant_slug"):
        cats["microsoft_tenant_mismatch"] += 1
    elif it.get("category") == "non_tenant_mismatch":
        cats["non_tenant_mismatch"] += 1
    else:
        cats["other"] += 1
print("=== Breakdown by mismatch type ===")
for k, v in cats.most_common():
    print(f"  {k:<35} {v:>5}")
