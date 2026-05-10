#!/usr/bin/env python3
"""Purge cross-tenant MX misattributions left in data.json by ANY of
the recovery paths that pre-dated the is_legit_email_domain gate:

  1. recover_it_unknowns (consumes seed `domain_fallbacks` from IndicePA
     non-PEC Mail* fields) — the dominant source for the istruzione.it
     hijack of ~895 schools (a school's IndicePA record exposes the
     dirigente's @istruzione.it inbox, which the recover script blindly
     turned into the school's own MX).
  2. postprocess.process_unknown (homepage scrape).
  3. finalize_it_unknowns S3/S4 (homepage scrape + DDG search).
  4. Any future ingest path that writes mx/provider/domain_used.

For each IT entity in data.json:
  1. Determine the "claimed" email domain that produced the MX:
     - prefer audit fields `domain_used` or `scraped_email`
     - else current `m["domain"]` (which may have been overwritten)
  2. Compare against seed `domain` via is_legit_email_domain
  3. If reject → strip mx/spf/provider/cnames/asns/countries/autodiscover/
     dkim/tenant/gateway/domain_used/scraped_email and force the entry
     back to provider="unknown" with reason recording the rejection.

Output:
  data.json mutated in-place (backup at data.json.cleanup_backup)
  data/reports/cleanup_invalid_mx_attributions.json — full audit
  (id / name / seed_domain / claimed_domain / reject_reason / old_mx /
  old_provider). User-visible "rejection table" for manual review.

Idempotent: a second run finds nothing to purge.

Usage: uv run python3 scripts/cleanup_invalid_mx_attributions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))
from mail_sovereignty.scrape_validator import is_legit_email_domain  # noqa

DATA = ROOT / "data"
DATAJSON = ROOT / "data.json"
SEED = DATA / "municipalities_it.json"
REPORT = DATA / "reports" / "cleanup_invalid_mx_attributions.json"

# Fields that were set by the (now-gated) scrape paths and must be
# stripped when we revert the entity to "unknown".
SCRAPE_DERIVED_FIELDS = (
    "mx", "spf", "spf_resolved", "mx_cnames", "mx_asns", "mx_countries",
    "autodiscover", "dkim", "tenant", "txt_verifications", "gateway",
    "scraped_email", "scrape_tried_hosts", "domain_correction_source",
    "domain_used",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="don't write changes, only report")
    args = ap.parse_args()

    data = json.loads(DATAJSON.read_text(encoding="utf-8"))
    muns = data.get("municipalities") or data  # tolerate either shape
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    seed_by_id = {e["id"]: e for e in seed}

    purged: list[dict] = []
    n_it = 0
    n_with_mx = 0

    for bid, m in muns.items():
        if (m.get("country") or "").upper() != "IT":
            continue
        n_it += 1
        if not (m.get("mx") or []):
            continue
        n_with_mx += 1

        seed_entry = seed_by_id.get(bid) or {}
        seed_dom = (seed_entry.get("domain") or "").strip().lower()
        codice_ipa = (seed_entry.get("ipa_codice_ipa")
                      or m.get("ipa_codice_ipa") or "").strip().lower()

        # The claimed email domain — prefer audit-trail fields; otherwise
        # the entry's current domain (which may have been silently
        # overwritten by the old process_unknown).
        claimed = (m.get("domain_used")
                   or m.get("scraped_email", "").rsplit("@", 1)[-1]
                   or m.get("domain") or "").strip().lower()

        if not claimed or not seed_dom:
            continue
        if claimed == seed_dom:
            continue   # never scrape-derived

        ok, reason = is_legit_email_domain(claimed, seed_dom,
                                           codice_ipa=codice_ipa or None)
        if ok:
            continue   # legit — leave alone

        # PURGE
        purged.append({
            "id": bid,
            "name": m.get("name", ""),
            "codice_ipa": codice_ipa or None,
            "seed_domain": seed_dom,
            "claimed_domain": claimed,
            "reject_reason": reason,
            "old_mx": (m.get("mx") or [None])[0],
            "old_provider": m.get("provider"),
            "old_reason": (m.get("reason") or "")[:120],
        })
        for fld in SCRAPE_DERIVED_FIELDS:
            m.pop(fld, None)
        # Restore the seed domain so the next pipeline run re-attempts
        # the legitimate domain rather than the contaminated one.
        m["domain"] = seed_dom
        m["provider"] = "unknown"
        m["reason"] = f"cleared by is_legit gate: {reason}"

    print(f"IT enti scanned:           {n_it}")
    print(f"  with MX before cleanup:  {n_with_mx}")
    print(f"  PURGED (cross-tenant):   {len(purged)}")
    if purged:
        from collections import Counter
        by_reason = Counter(p["reject_reason"].split(":", 1)[0]
                            for p in purged)
        print("  rejections grouped by family:")
        for r, n in by_reason.most_common():
            print(f"    {r:<28} {n}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "n_purged": len(purged),
        "items": purged,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nFull rejection table: {REPORT}")

    if args.dry_run:
        print("\nDry-run — data.json NOT modified.")
        return 0

    backup = DATAJSON.with_suffix(".json.cleanup_backup")
    if not backup.exists():
        shutil.copy2(DATAJSON, backup)
        print(f"Backup written: {backup}")
    DATAJSON.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"data.json updated in-place ({len(purged)} enti reverted to unknown).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
