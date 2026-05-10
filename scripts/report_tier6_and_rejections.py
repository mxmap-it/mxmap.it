#!/usr/bin/env python3
"""Final audit reports after the is_legit_email_domain rollout:
  REPORT 1 — Tier-6 reconciliation table (enti recovered via AOO/UO)
  REPORT 2 — Manual-review rejection table (cross-tenant purges)

Reads only existing artifacts (no network):
  - data/indicepa_extended_emails.json (from enrich_from_aoo_uo.py)
  - data/reports/cleanup_scraped_mx_bug.json (from cleanup_scraped_mx_bug.py)
  - data/municipalities_it.json (seed)
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ext = json.loads((ROOT / "data/indicepa_extended_emails.json").read_text(encoding="utf-8"))
seed = json.loads((ROOT / "data/municipalities_it.json").read_text(encoding="utf-8"))
seed_by_ipa = {(e.get("ipa_codice_ipa") or "").lower(): e for e in seed}
clean = json.loads((ROOT / "data/reports/cleanup_scraped_mx_bug.json").read_text(encoding="utf-8"))

# ---------- REPORT 1 ----------
print("=" * 110)
print("REPORT 1 — TIER-6 RECONCILIATIONS (non-PEC domains harvested from IndicePA AOO/UO, is_legit-validated)")
print("=" * 110)
items = []
for ipa, info in ext.get("by_ipa", {}).items():
    doms = info.get("non_pec_domains") or []
    if not doms:
        continue
    se = seed_by_ipa.get(ipa)
    if not se:
        continue
    items.append((ipa, se.get("name", ""), se.get("domain", ""), doms,
                  info.get("source_record_count", 0)))

items.sort(key=lambda x: -x[4])
print(f"{'codice_ipa':<14}{'ente':<46}{'seed_domain':<32}{'AOO/UO domain(s)'}")
print("-" * 110)
for ipa, name, sd, doms, n in items[:40]:
    extra = f" (+{len(doms)-2})" if len(doms) > 2 else ""
    show = ",".join(doms[:2]) + extra
    print(f"{ipa:<14}{name[:44]:<46}{(sd or '-')[:30]:<32}{show}")
print(f"\nTOTAL: {len(items)} enti enriched, {sum(len(d) for _,_,_,d,_ in items)} distinct domains")
fam = Counter()
for _, _, _, doms, _ in items:
    for d in doms:
        fam[d.split('.')[-2] if d.count('.') >= 1 else d] += 1
print("\nMost common Tier-6 domains (top 10):")
for d, n in Counter(d for _, _, _, doms, _ in items for d in doms).most_common(10):
    print(f"  {n:>5}x  {d}")

# ---------- REPORT 2 ----------
print()
print("=" * 110)
print("REPORT 2 — MANUAL-REVIEW REJECTION TABLE (purged from data.json by cleanup_scraped_mx_bug)")
print("=" * 110)
print(f"{'id':<24}{'ente':<32}{'seed_domain':<24}{'claimed_domain':<24}{'reason'}")
print("-" * 110)
for it in clean["items"][:40]:
    print(f"{it['id'][:23]:<24}{(it['name'] or '')[:30]:<32}"
          f"{(it['seed_domain'] or '')[:22]:<24}"
          f"{(it['claimed_domain'] or '')[:22]:<24}"
          f"{it['reject_reason'][:30]}")
print(f"\nTOTAL purged: {clean['n_purged']}")
print("\nTop hijacking 'claimed_domain' values:")
for d, n in Counter(it["claimed_domain"] for it in clean["items"]).most_common(15):
    print(f"  {n:>5}x  {d}")
print("\nReason distribution:")
for r, n in Counter(it["reject_reason"].split(":", 1)[0] for it in clean["items"]).most_common():
    print(f"  {n:>5}x  {r}")
