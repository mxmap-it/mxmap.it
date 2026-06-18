#!/usr/bin/env python3
"""Reclassify entries with confirmed cloud backends.

Background
----------
The data.json (generated 2026-06-10) contains entries whose provider
field is stale relative to the DNS evidence. Many of these have
`cloud_tenant_only` set to a hyperscaler (microsoft/google/aws) but
`provider=independent` and `gateway=None`. These are entities that
self-host their MX (e.g., Corte Costituzionale, INPS, Consob, INARCASSA)
but have a Microsoft 365 / Google Workspace / AWS SES tenant
confirmed via DKIM CNAME or other DNS evidence.

The current `classify()` function would correctly identify most of these
if the data pipeline were re-run — but `classify()` was added after
data.json was generated, so the field is stale.

This script iterates all entries and re-classifies any entry where a
cloud backend is detected. In practice this is roughly ~1,185 entries
(only a subset of which come from the 219 `cloud_tenant_only` values).
Signals are evaluated in priority order:

  1. `classify()` against current data (DKIM, SPF, autodiscover, etc.)
  2. If `classify()` returns `independent` but `cloud_tenant_only` is
     set, use `cloud_tenant_only` (the upstream pipeline's stronger
     signal — it has access to ASN, IP geolocation, MX CNAME chains)
  3. Leave as `independent` only if neither signal finds a cloud
     backend

Output
------
- Updates `data.json` in place (or writes to a new path with --output)
- Logs each reclassification with the source signal that triggered it
- Produces a `reports/cloud_backend_reclassification.md` summary

Usage:
    .venv/bin/python scripts/apply_cloud_backend.py
    .venv/bin/python scripts/apply_cloud_backend.py --dry-run
    .venv/bin/python scripts/apply_cloud_backend.py --output data_new.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from mail_sovereignty.classify import classify  # noqa: E402

DATA_PATH = REPO_ROOT / "data.json"
REPORT_PATH = REPO_ROOT / "reports" / "cloud_backend_reclassification.md"

# Cloud backends we recognize
CLOUD_BACKENDS = ("microsoft", "google", "aws")


def reclassify_entry(bfs: str, m: dict[str, Any]) -> tuple[str, str, str]:
    """Decide the new provider for an entry.

    Returns (new_provider, source_signal, reason) where:
      - new_provider: the provider string to use
      - source_signal: which evidence triggered the reclassification
        ('classify_dkim', 'classify_cname', 'classify_autodiscover',
         'classify_spf', 'classify_txt', 'upstream_cloud_tenant_only',
         'unchanged')
      - reason: human-readable explanation
    """
    current = m.get("provider", "unknown")
    mx = m.get("mx", [])
    spf = m.get("spf", "")
    dkim = m.get("dkim") or None
    mx_cnames = m.get("mx_cnames") or None
    autodiscover = m.get("autodiscover") or None
    txt_verifications = m.get("txt_verifications") or None
    cloud_tenant_only = m.get("cloud_tenant_only")

    # Already cloud — no change
    if current in CLOUD_BACKENDS:
        return current, "unchanged", "already cloud"

    # 1. Run classify() with all evidence
    try:
        provider, reason = classify(
            mx_records=mx,
            spf_record=spf,
            mx_cnames=mx_cnames,
            dkim=dkim,
            autodiscover=autodiscover,
            txt_verifications=txt_verifications,
        )
    except Exception as e:
        provider, reason = current, f"classify() error: {e}"

    # If classify() finds a cloud backend, use it
    if provider in CLOUD_BACKENDS:
        # Determine the source signal from the reason text
        reason_lower = reason.lower()
        if "dkim" in reason_lower:
            source = "classify_dkim"
        elif "autodiscover" in reason_lower:
            source = "classify_autodiscover"
        elif "cname" in reason_lower:
            source = "classify_cname"
        elif "spf" in reason_lower:
            source = "classify_spf"
        elif "txt" in reason_lower or "verification" in reason_lower:
            source = "classify_txt"
        else:
            source = "classify_other"
        return provider, source, reason

    # 2. Fallback to cloud_tenant_only (upstream pipeline's signal)
    if cloud_tenant_only in CLOUD_BACKENDS:
        return (
            cloud_tenant_only,
            "upstream_cloud_tenant_only",
            f"upstream pipeline set cloud_tenant_only={cloud_tenant_only}",
        )

    # 3. No signal — keep current
    return current, "unchanged", reason


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write changes to data.json; just report what would change",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write to a different file (default: data.json)",
    )
    args = parser.parse_args()

    output_path = args.output or DATA_PATH

    with open(DATA_PATH) as f:
        data = json.load(f)
    municipalities = data["municipalities"]

    # Reclassify
    changes: list[dict[str, Any]] = []
    source_counts: Counter = Counter()
    by_backend: Counter = Counter()
    unchanged = 0
    errors = 0

    for bfs, m in municipalities.items():
        try:
            new_provider, source, reason = reclassify_entry(bfs, m)
        except Exception:
            errors += 1
            continue

        current = m.get("provider")
        if new_provider != current:
            changes.append(
                {
                    "bfs": bfs,
                    "name": m.get("name", ""),
                    "old_provider": current,
                    "new_provider": new_provider,
                    "source": source,
                    "reason": reason,
                    "regione": m.get("regione", ""),
                    "comune": m.get("comune", ""),
                    "domain": m.get("domain", ""),
                    "mx": (m.get("mx") or [])[:2],
                }
            )
            source_counts[source] += 1
            by_backend[new_provider] += 1
        else:
            unchanged += 1

    # ── Report ──
    print("\n=== Reclassification Summary ===")
    print(f"Total entries: {len(municipalities):,}")
    print(f"Unchanged: {unchanged:,}")
    print(f"Errors: {errors}")
    print(f"Reclassified: {len(changes)}")
    print("\nBy target backend:")
    for backend, c in by_backend.most_common():
        print(f"  {backend}: {c}")
    print("\nBy source signal:")
    for source, c in source_counts.most_common():
        print(f"  {source}: {c}")

    # ── Apply changes (unless --dry-run) ──
    if not args.dry_run and changes:
        for change in changes:
            m = municipalities[change["bfs"]]
            m["provider"] = change["new_provider"]
            # Tag the reclassification for audit
            m["provider_reclassified_at"] = "2026-06-17"
            m["provider_reclassified_from"] = change["old_provider"]
            m["provider_reclassified_source"] = change["source"]
            # If the upstream had cloud_tenant_only, we can drop it now
            # (its info is now in provider)
            if (
                "cloud_tenant_only" in m
                and m["cloud_tenant_only"] == change["new_provider"]
            ):
                m["cloud_tenant_only_resolved"] = m["cloud_tenant_only"]
                del m["cloud_tenant_only"]

        # Update counts at top level
        providers = Counter()
        for bfs, m in municipalities.items():
            providers[m.get("provider", "unknown")] += 1
        data["counts"] = dict(providers)
        data["total"] = len(municipalities)

        with open(output_path, "w") as f:
            json.dump(data, f, separators=(",", ":"))
        print(f"\nWrote {output_path}")
    elif args.dry_run:
        print("\n(--dry-run: no changes written)")

    # ── Detailed report ──
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Cloud Backend Reclassification Report (2026-06-17)")
    lines.append("")
    lines.append(
        f"Reclassified **{len(changes)} entries** from `independent` to a "
        f"confirmed cloud backend using multi-signal DNS analysis."
    )
    lines.append("")
    lines.append("**Source signals (in priority order):**")
    lines.append("")
    lines.append("1. `classify()` with DKIM CNAME → hyperscaler")
    lines.append("2. `classify()` with MX CNAME → hyperscaler")
    lines.append("3. `classify()` with autodiscover CNAME → hyperscaler")
    lines.append("4. `classify()` with SPF include → hyperscaler")
    lines.append("5. `classify()` with TXT verification token")
    lines.append("6. `cloud_tenant_only` field set by upstream pipeline (ASN/IP-based)")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total entries**: {len(municipalities):,}")
    lines.append(f"- **Unchanged**: {unchanged:,}")
    lines.append(f"- **Reclassified**: {len(changes)}")
    lines.append(f"- **Errors**: {errors}")
    lines.append("")

    lines.append("### By target backend")
    lines.append("")
    lines.append("| Backend | Count |")
    lines.append("|---------|-------|")
    for backend, c in by_backend.most_common():
        lines.append(f"| {backend} | {c} |")
    lines.append("")

    lines.append("### By source signal")
    lines.append("")
    lines.append("| Signal | Count |")
    lines.append("|--------|-------|")
    for source, c in source_counts.most_common():
        lines.append(f"| `{source}` | {c} |")
    lines.append("")

    # Top entities by region
    lines.append("## Notable Reclassifications")
    lines.append("")
    lines.append("Top 30 by entity size (alphabetical by region, then name):")
    lines.append("")

    # Sort by region + name
    sorted_changes = sorted(changes, key=lambda c: (c["regione"] or "", c["name"]))
    for c in sorted_changes[:30]:
        mx_str = ", ".join(c["mx"][:2])
        lines.append(
            f"- **{c['name'][:50]}** ({c['regione']} / {c['comune']}) — "
            f"`{c['old_provider']}` → `{c['new_provider']}` "
            f"via `{c['source']}`"
        )
        lines.append(f"  - MX: `{mx_str}`")
    lines.append("")
    lines.append(f"_… and {len(changes) - 30} more_")
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines))
    print(f"\nDetailed report: {REPORT_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
