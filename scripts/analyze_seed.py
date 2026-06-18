#!/usr/bin/env python3
"""Analyze seed data quality in data.json.

Prints statistics about:
- entries with a domain but no MX records
- entries with a name but no domain
- breakdown of unknown-provider entries
- potentially wrong subdomain patterns
- independent provider analysis
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    data_path = repo_root / "data.json"

    with open(data_path) as f:
        data = json.load(f)

    muni = data["municipalities"]
    print(f"Total entries: {len(muni)}")

    # Category 1: Domain set but mx empty/null
    # (dirty seed - domain in IndicePA but no MX resolved)
    domain_no_mx = []
    for bfs, m in muni.items():
        d = m.get("domain") or ""
        mx = m.get("mx", [])
        if d and len(mx) == 0:
            domain_no_mx.append(
                (
                    bfs[:40],
                    m.get("name", "")[:50],
                    m.get("country", ""),
                    m.get("provider", "unknown"),
                    d,
                )
            )

    print(f"\n=== Category 1: Domain set but MX empty/null - {len(domain_no_mx)} ===")
    for e in domain_no_mx[:25]:
        print(f"  {e[0]} | {e[1]} | provider={e[3]} | country={e[2]} | domain={e[4]}")

    # Category 2: Name set but domain null/empty (missing from IndicePA)
    name_no_domain = []
    for bfs, m in muni.items():
        n = m.get("name") or ""
        d = m.get("domain") or ""
        if n and not d:
            name_no_domain.append(
                (
                    bfs[:40],
                    m.get("name", "")[:50],
                    m.get("country", ""),
                    m.get("provider", "unknown"),
                )
            )

    print(
        f"\n=== Category 2: Name set but domain null/empty - {len(name_no_domain)} ==="
    )
    for e in name_no_domain[:15]:
        print(f"  {e[0]} | {e[1]} | provider={e[3]} | country={e[2]}")

    # Unknowns breakdown
    unk_counts: dict[str, int] = {}
    unk_examples = []
    for bfs, m in muni.items():
        if m.get("provider") == "unknown":
            d = m.get("domain") or ""
            mx_list = m.get("mx", [])

            if not d and not mx_list:
                key = "no_domain_and_no_mx"
            elif d and not mx_list:
                key = "has_domain_but_no_mx"
            else:
                key = "has_some_dns_data"

            unk_counts[key] = unk_counts.get(key, 0) + 1

            if len(unk_examples) < 5:
                unk_examples.append(
                    (bfs[:40], m.get("name", "")[:50], d or "", mx_list)
                )

    print("\n=== Category 3: Unknowns breakdown ===")
    for k, v in sorted(unk_counts.items()):
        print(f"  {k}: {v}")

    print("\n  Sample unknowns:")
    for e in unk_examples:
        print(f"    {e[0]} | {e[1]} | domain='{e[2]}' | mx={e[3][:3]}")

    # Wrong domain patterns (subdomain like dominio.provincia.it)
    wrong_patterns = []
    for bfs, m in muni.items():
        d = m.get("domain") or ""
        if not d:
            continue

        dparts = d.split(".")
        if len(dparts) >= 3:
            parent = ".".join(dparts[1:])
            wrong_patterns.append(
                (
                    bfs[:40],
                    m.get("name", "")[:50],
                    d,
                    ".".join(dparts[-2:]),
                    m.get("provider", "unknown"),
                )
            )

    print(
        "\n=== Category 4: Subdomain patterns (3+ levels) - potential wrong domains ==="
    )
    subdomain_counts: Counter = Counter()
    for e in wrong_patterns:
        subdomain_counts[e[3]] += 1

    print("  Top parent domains (likely wrong seed data):")
    for d, c in subdomain_counts.most_common(15):
        print(f"    {d}: {c} entries")

    # Category 5: Independent provider analysis
    independent_with_domain = []
    for bfs, m in muni.items():
        p = m.get("provider", "unknown")
        if p == "independent":
            d = m.get("domain") or ""
            mx = m.get("mx", [])

            independent_with_domain.append(
                {
                    "bfs": bfs[:40],
                    "name": m.get("name", "")[:50],
                    "country": m.get("country"),
                    "domain": d,
                    "has_mx": len(mx) > 0,
                    "gateway": m.get("gateway"),
                }
            )

    print("\n=== Category 5: Independent provider analysis ===")
    ind_with_domain = sum(1 for e in independent_with_domain if e["domain"])
    ind_with_mx = sum(1 for e in independent_with_domain if e["has_mx"])

    print(f"  Total independent: {len(independent_with_domain)}")
    print(f"  With domain: {ind_with_domain}")
    print(f"  With MX: {ind_with_mx}")
    print(f"  No domain/nomx: {len(independent_with_domain) - ind_with_domain}")

    # Top 30 worst domain issues
    dirty_findings = []

    for e in wrong_patterns[:50]:
        bfs, name, domain, parent, provider = e[0], e[1], e[2], e[3], e[4]
        severity = "HIGH" if len(domain.split(".")) >= 4 else "MEDIUM"
        dirty_findings.append(
            {
                "bfs": bfs[:50],
                "name": name[:60],
                "domain": domain,
                "provider": provider,
                "parent_domain": parent,
                "severity": severity,
            }
        )

    for e in domain_no_mx[:30]:
        bfs, name, provider, domain = e[0], e[1], e[3], e[4]
        dirty_findings.append(
            {
                "bfs": bfs[:50],
                "name": name[:60],
                "domain": domain,
                "provider": provider,
                "parent_domain": "",
                "severity": "CRITICAL",
            }
        )

    sev_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    dirty_findings.sort(key=lambda x: -sev_order.get(x["severity"], 0))
    top30 = dirty_findings[:30]

    print("\n=== Top 30 worst domain issues ===")
    for i, item in enumerate(top30, 1):
        print(
            f"  {i:2d}. [{item['severity']}] BFS={item['bfs']} "
            f"name={item['name']} domain='{item['domain']}' provider={item['provider']}"
        )

    print("\n=== SUMMARY FOR REPORT ===")
    print(f"Total entries: {len(muni)}")
    print(
        f"Italian entities: {sum(1 for m in muni.values() if m.get('country') == 'IT')}"
    )
    print(f"Unknown providers: {unk_counts}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
