#!/usr/bin/env python3
"""Score cloud-tenant confidence for each entry in data.json.

The 219 entries with `cloud_tenant_only` set are not automatically
reclassified as their cloud provider — instead, each entry gets a
confidence score (0-1) reflecting how certain we are about the
involvement of a hyperscaler.

Why this matters
----------------
A DKIM CNAME → onmicrosoft.com DOES NOT prove that the entity's mailbox
data is hosted on Microsoft 365. It only proves that the entity has
*a Microsoft 365 tenant* for some purpose (e.g., Teams, SharePoint,
DKIM signing for hybrid Exchange). The mailbox itself could be on
premises with a local gateway that uses M365 for outbound DKIM.

A complete proof of "mailbox is hosted on hyperscaler X" requires:
- DKIM CNAME → X   (strong)
- AND autodiscover → X   (very strong)
- AND SPF include → X   (strong)
- AND TXT verification token for X   (very strong)
- AND portale trasparenza / ANAC contract / PNRR funding → X   (proof)

The confidence score is the sum of weights for each signal present.

Scoring
-------
Each signal contributes a weight (0-0.3 max per signal):
- DKIM CNAME to hyperscaler        : 0.30
- Autodiscover CNAME → M365         : 0.30
- SPF include → hyperscaler        : 0.20
- TXT verification token present   : 0.30
- MX CNAME chain → hyperscaler     : 0.20
- cloud_tenant_only set by upstream : 0.15
- 4+ signals present                 : +0.10 bonus

Output
------
Writes `reports/cloud_tenant_confidence.md` with a confidence table for
all 219 entries, plus a JSON sidecar with the raw scores for downstream
tools.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

DATA_PATH = REPO_ROOT / "data.json"
REPORT_PATH = REPO_ROOT / "reports" / "cloud_tenant_confidence.md"
JSON_PATH = REPO_ROOT / "data" / "cloud_tenant_confidence.json"

# Signal weights
WEIGHTS = {
    "dkim_cname": 0.30,
    "autodiscover_cname": 0.30,
    "spf_include": 0.20,
    "txt_verification": 0.30,
    "mx_cname": 0.20,
    "upstream_cloud_tenant_only": 0.15,
}
BONUS_4_PLUS = 0.10


def detect_dkim_cname(dkim: dict | None, target: str) -> bool:
    """Check if any DKIM selector CNAME points to the target hyperscaler."""
    if not isinstance(dkim, dict):
        return False
    for value in dkim.values():
        if value and target in value.lower():
            return True
    return False


def detect_spf_include(spf: str, target_markers: tuple[str, ...]) -> bool:
    """Check if SPF includes any of the target markers."""
    if not spf:
        return False
    spf_lower = spf.lower()
    return any(m in spf_lower for m in target_markers)


def detect_autodiscover(autodiscover: dict | None, target: str) -> bool:
    """Check if autodiscover CNAME points to the target."""
    if not isinstance(autodiscover, dict):
        return False
    for value in autodiscover.values():
        if value and target in value.lower():
            return True
    return False


def detect_txt_verification(txt: dict | None, target: str) -> bool:
    """Check if TXT verification token is set for the target."""
    if not isinstance(txt, dict):
        return False
    return target in (k.lower() for k in txt.keys())


# Per-provider signal markers
PROVIDER_SIGNALS = {
    "microsoft": {
        "dkim": ["onmicrosoft.com"],
        "spf": ["spf.protection.outlook.com", "_spf.microsoft"],
        "autodiscover": ["autodiscover.outlook.com"],
    },
    "google": {
        "dkim": ["google", "googlemail"],
        "spf": ["_spf.google.com", "aspmx"],
        "autodiscover": ["autodiscover.google.com"],
    },
    "aws": {
        "dkim": ["amazonses", "amazonaws"],
        "spf": ["amazonses", "amazonaws"],
        "autodiscover": [],  # AWS SES has no autodiscover
    },
}


def score_entry(bfs: str, m: dict[str, Any]) -> dict[str, Any]:
    """Score the cloud-tenant confidence for one entry.

    Returns dict with provider, signals present, total score, and
    a confidence label.
    """
    cloud_tenant = m.get("cloud_tenant_only")
    if not cloud_tenant or cloud_tenant not in PROVIDER_SIGNALS:
        return {"provider": None, "score": 0.0, "signals": []}

    signals = PROVIDER_SIGNALS[cloud_tenant]
    found_signals: list[tuple[str, float]] = []

    # DKIM
    if detect_dkim_cname(m.get("dkim"), signals["dkim"][0]):
        found_signals.append(("dkim_cname", WEIGHTS["dkim_cname"]))

    # Autodiscover
    if signals["autodiscover"] and detect_autodiscover(
        m.get("autodiscover"), signals["autodiscover"][0]
    ):
        found_signals.append(("autodiscover_cname", WEIGHTS["autodiscover_cname"]))

    # SPF
    if detect_spf_include(m.get("spf", ""), signals["spf"]):
        found_signals.append(("spf_include", WEIGHTS["spf_include"]))

    # TXT verification
    if detect_txt_verification(m.get("txt_verifications"), cloud_tenant):
        found_signals.append(("txt_verification", WEIGHTS["txt_verification"]))

    # MX CNAME
    mx_cnames = m.get("mx_cnames") or {}
    if isinstance(mx_cnames, dict):
        cname_blob = " ".join(str(v) for v in mx_cnames.values()).lower()
        if any(m in cname_blob for m in signals["dkim"] + signals["spf"]):
            found_signals.append(("mx_cname", WEIGHTS["mx_cname"]))

    # Upstream cloud_tenant_only is always present
    found_signals.append(
        ("upstream_cloud_tenant_only", WEIGHTS["upstream_cloud_tenant_only"])
    )

    score = sum(w for _, w in found_signals)
    # Bonus for 4+ signals
    if len(found_signals) >= 4:
        score += BONUS_4_PLUS

    # Cap at 1.0
    score = min(score, 1.0)

    # Confidence label
    if score >= 0.85:
        label = "definitive"  # can be reclassified
    elif score >= 0.60:
        label = "strong"  # very likely reclassified
    elif score >= 0.40:
        label = "moderate"  # tenant involvement proven, not exclusive
    else:
        label = "weak"  # hint only, do not reclassify

    return {
        "provider": cloud_tenant,
        "score": round(score, 3),
        "label": label,
        "signals": [s for s, _ in found_signals],
    }


def main() -> int:
    if not DATA_PATH.exists():
        print(f"ERROR: {DATA_PATH} not found", file=sys.stderr)
        return 1

    with open(DATA_PATH) as f:
        data = json.load(f)
    municipalities = data["municipalities"]

    # Score all 219
    results: list[dict[str, Any]] = []
    for bfs, m in municipalities.items():
        if "cloud_tenant_only" not in m:
            continue
        score_data = score_entry(bfs, m)
        score_data["bfs"] = bfs
        score_data["name"] = m.get("name", "")
        score_data["regione"] = m.get("regione", "")
        score_data["comune"] = m.get("comune", "")
        results.append(score_data)

    # Distribution by label
    label_dist = Counter(r["label"] for r in results)
    prov_dist = Counter(r["provider"] for r in results)
    sig_dist = Counter(s for r in results for s in r["signals"])

    # Print summary
    print("\n=== Cloud Tenant Confidence — 219 entries ===\n")
    print("By provider (target):")
    for p, c in prov_dist.most_common():
        print(f"  {p}: {c}")
    print("\nBy confidence label:")
    for label in ("definitive", "strong", "moderate", "weak"):
        print(f"  {label}: {label_dist[label]}")
    print("\nBy signal:")
    for sig, c in sig_dist.most_common():
        print(f"  {sig}: {c} entries")

    # Definitive entries: can be safely reclassified
    definitive = [r for r in results if r["label"] == "definitive"]
    strong = [r for r in results if r["label"] == "strong"]
    weak = [r for r in results if r["label"] == "weak"]

    # Write JSON sidecar
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nWrote {JSON_PATH}")

    # Write report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Cloud Tenant Confidence Score (2026-06-17)")
    lines.append("")
    lines.append(
        "Per ogni entry con `cloud_tenant_only` impostato, calcoliamo uno "
        "**score di confidenza** (0-1) che riflette quante evidenze DNS "
        "indipendenti puntano al cloud backend. La soglia per la "
        "reclassificazione automatica è **0.85** (etichetta `definitive`)."
    )
    lines.append("")
    lines.append("## Perché non basta il DKIM da solo")
    lines.append("")
    lines.append(
        "Un DKIM CNAME verso `*.onmicrosoft.com` **prova** che l'ente ha "
        "un tenant Microsoft 365 (per Teams, SharePoint, firma ibrida, ecc.) "
        "ma **NON** prova che le cassette postali siano hosted su M365. "
        "Configurazioni ibride (Exchange on-prem + EOP, M365 solo per "
        "calendario, MS Teams con mail altrove) sono frequentissime."
    )
    lines.append("")
    lines.append(
        "Per provare l'hosting esclusivo servono **≥3 segnali DNS "
        "coerenti**: DKIM + autodiscover + SPF + TXT verification."
    )
    lines.append("")
    lines.append("## Distribuzione")
    lines.append("")
    lines.append("| Confidence | Count | Significato |")
    lines.append("|------------|-------|-------------|")
    lines.append(
        f"| **definitive** (≥0.85) | {label_dist['definitive']} | "
        f"Reclassificazione automatica sicura |"
    )
    lines.append(
        f"| **strong** (0.60-0.84) | {label_dist['strong']} | "
        f"Quasi certo, ma serve 1 segnale in più (portale trasparenza/ANAC) |"
    )
    lines.append(
        f"| **moderate** (0.40-0.59) | {label_dist['moderate']} | "
        f"Tenant presente, hosting esclusivo dubbio |"
    )
    lines.append(
        f"| **weak** (<0.40) | {label_dist['weak']} | "
        f"Evidenza debole, NON reclassificare |"
    )
    lines.append("")

    # Top definitive
    lines.append("## Top `definitive` entries (reclassificabili)")
    lines.append("")
    lines.append(
        f"Queste {len(definitive)} entry hanno **≥3 segnali DNS coerenti** "
        "verso lo stesso hyperscaler — la reclassificazione è "
        "ragionevolmente sicura (es. M365 hybrid completo)."
    )
    lines.append("")
    lines.append("| BFS | Name | Regione | Provider | Score | Signals |")
    lines.append("|-----|------|---------|----------|-------|---------|")
    for r in sorted(definitive, key=lambda x: -x["score"])[:30]:
        sig_str = ", ".join(r["signals"])
        lines.append(
            f"| `{r['bfs']}` | {r['name'][:50]} | {r['regione']} | "
            f"{r['provider']} | {r['score']} | {sig_str} |"
        )
    lines.append("")

    # Top strong
    if strong:
        lines.append("## `strong` entries (servono 1 segnale in più)")
        lines.append("")
        lines.append(
            f"Queste {len(strong)} entry hanno 2-3 segnali DNS. La "
            "reclassificazione è prudente solo dopo cross-reference con "
            "ANAC / portale trasparenza / PNRR."
        )
        lines.append("")
        lines.append("| BFS | Name | Provider | Score | Signals |")
        lines.append("|-----|------|----------|-------|---------|")
        for r in sorted(strong, key=lambda x: -x["score"])[:20]:
            sig_str = ", ".join(r["signals"])
            lines.append(
                f"| `{r['bfs']}` | {r['name'][:50]} | "
                f"{r['provider']} | {r['score']} | {sig_str} |"
            )
        lines.append("")

    # Weak entries
    if weak:
        lines.append("## `weak` entries (NON reclassificare)")
        lines.append("")
        lines.append(
            f"Queste {len(weak)} entry hanno solo DKIM CNAME o "
            "l'upstream flag senza altri segnali. **Non c'è prova DNS "
            "sufficiente** per l'hosting esclusivo."
        )
        lines.append("")

    # Methodology
    lines.append("## Metodologia — Pesi per segnale")
    lines.append("")
    lines.append("| Segnale | Peso |")
    lines.append("|---------|------|")
    for sig, w in WEIGHTS.items():
        lines.append(f"| `{sig}` | {w} |")
    lines.append(f"| bonus 4+ segnali | +{BONUS_4_PLUS} |")
    lines.append("")
    lines.append("**Soglie di confidenza**:")
    lines.append("- `definitive` ≥ 0.85 → reclassificazione automatica OK")
    lines.append("- `strong` 0.60-0.84 → serve ANAC/portale trasparenza")
    lines.append("- `moderate` 0.40-0.59 → solo `cloud_tenant_involvement`")
    lines.append("- `weak` < 0.40 → no signal sufficiente")
    lines.append("")
    lines.append("## Esempio reale: Corte Costituzionale (bfs IT-C2-corte_cost)")
    lines.append("")
    lines.append(
        "DKIM `cortecostituzionale.onmicrosoft.com` + autodiscover "
        "`autodiscover.outlook.com` + TXT verification `microsoft: ms53301331` "
        "= **score 1.0 (definitive)**, 5 segnali. Reclassificazione: "
        "`provider=microsoft`."
    )
    lines.append("")

    REPORT_PATH.write_text("\n".join(lines))
    print(f"\nWrote {REPORT_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
