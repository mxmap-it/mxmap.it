#!/usr/bin/env python3
"""Final audit reports after the is_legit_email_domain rollout.

Writes machine-readable CSVs covering EVERY entry, plus a top-N
human-readable summary printed to stdout.

Inputs (no network):
  - data/indicepa_extended_emails.json (from enrich_from_aoo_uo.py)
  - data/reports/cleanup_invalid_mx_attributions.json (from cleanup_invalid_mx_attributions.py)
  - data/municipalities_it.json (seed)
  - data.json (current pipeline state, for ente category lookup)

Outputs:
  - data/reports/tier6_reconciliation_full.csv  — every Tier-6 enti accepted
  - data/reports/manual_review_rejections_full.csv — every purged misattribution
"""
from __future__ import annotations
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "data" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

ext = json.loads((ROOT / "data/indicepa_extended_emails.json").read_text(encoding="utf-8"))
seed = json.loads((ROOT / "data/municipalities_it.json").read_text(encoding="utf-8"))
seed_by_ipa = {(e.get("ipa_codice_ipa") or "").lower(): e for e in seed}
_clean_path = REPORTS / "cleanup_invalid_mx_attributions.json"
if not _clean_path.exists():
    _clean_path = REPORTS / "cleanup_scraped_mx_bug.json"  # legacy filename
clean = json.loads(_clean_path.read_text(encoding="utf-8"))

# ---------------- REPORT 1: Tier-6 reconciliations (full CSV) ----------------
items = []
for ipa, info in ext.get("by_ipa", {}).items():
    doms = info.get("non_pec_domains") or []
    if not doms:
        continue
    se = seed_by_ipa.get(ipa) or {}
    items.append({
        "codice_ipa": ipa,
        "name": se.get("name", ""),
        "categoria": se.get("ipa_codice_categoria", ""),
        "id": se.get("id", ""),
        "seed_domain": se.get("domain", ""),
        "aoo_uo_domains": ";".join(doms),
        "n_domains": len(doms),
        "source_records": info.get("source_record_count", 0),
        "n_filtered_out": len(info.get("filtered_out") or []),
    })
items.sort(key=lambda x: -x["source_records"])

csv_path = REPORTS / "tier6_reconciliation_full.csv"
with open(csv_path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(items[0].keys()) if items else [
        "codice_ipa", "name", "categoria", "id", "seed_domain",
        "aoo_uo_domains", "n_domains", "source_records", "n_filtered_out"])
    w.writeheader()
    w.writerows(items)

print("=" * 110)
print("REPORT 1 — TIER-6 RECONCILIATIONS  (full CSV: data/reports/tier6_reconciliation_full.csv)")
print("=" * 110)
print(f"Enti enriched:                 {len(items)}")
print(f"Total accepted domains (sum):  {sum(i['n_domains'] for i in items)}")
print(f"Total filtered-out (rejected): {sum(i['n_filtered_out'] for i in items)}")
print()
print(f"{'codice_ipa':<14}{'ente':<46}{'seed':<32}{'AOO/UO domain(s)'}")
print("-" * 110)
for it in items[:50]:
    doms = it["aoo_uo_domains"].split(";")
    extra = f" (+{len(doms)-2})" if len(doms) > 2 else ""
    show = ",".join(doms[:2]) + extra
    print(f"{it['codice_ipa']:<14}{it['name'][:44]:<46}"
          f"{(it['seed_domain'] or '-')[:30]:<32}{show}")
print(f"... +{max(0, len(items)-50)} more in CSV")

print("\nMost common Tier-6 domains (top 15):")
all_doms = [d for it in items for d in it["aoo_uo_domains"].split(";")]
for d, n in Counter(all_doms).most_common(15):
    print(f"  {n:>5}x  {d}")

# ---------------- REPORT 2: Manual-review rejections (full CSV) ----------------
rej_path = REPORTS / "manual_review_rejections_full.csv"
with open(rej_path, "w", encoding="utf-8", newline="") as f:
    fields = ["id", "name", "codice_ipa", "seed_domain", "claimed_domain",
              "reject_reason", "old_mx", "old_provider", "old_reason"]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for it in clean["items"]:
        w.writerow({k: it.get(k, "") for k in fields})

print()
print("=" * 110)
print("REPORT 2 — MANUAL-REVIEW REJECTIONS  (full CSV: data/reports/manual_review_rejections_full.csv)")
print("=" * 110)
print(f"Total purged: {clean['n_purged']}")
print()
print(f"{'id':<24}{'ente':<32}{'seed':<24}{'claimed':<24}{'reason'}")
print("-" * 110)
for it in clean["items"][:50]:
    print(f"{it['id'][:23]:<24}{(it['name'] or '')[:30]:<32}"
          f"{(it['seed_domain'] or '')[:22]:<24}"
          f"{(it['claimed_domain'] or '')[:22]:<24}"
          f"{it['reject_reason'][:30]}")
print(f"... +{max(0, clean['n_purged']-50)} more in CSV")

print("\nTop 15 hijacking 'claimed_domain' values:")
for d, n in Counter(it["claimed_domain"] for it in clean["items"]).most_common(15):
    print(f"  {n:>5}x  {d}")

print("\nReason distribution:")
for r, n in Counter(it["reject_reason"].split(":", 1)[0] for it in clean["items"]).most_common():
    print(f"  {n:>5}x  {r}")

print()
print("CSVs written:")
print(f"  {csv_path}")
print(f"  {rej_path}")
