"""Storicizzazione di un run dell'Osservatorio — logica pura (testabile).

Vedi docs/HISTORICIZATION_DESIGN.md. Estrae da ogni entità i **campi
materiali** (la cui variazione È un cambiamento reale), confronta due run
(prev vs curr) e produce gli eventi di changelog con **causa attribuita**
(reality = la PA è migrata / methodology = abbiamo migliorato il rilevamento /
source = cambiamento a monte / uncertain = da rivedere).

Forward-only: lo storico parte dal primo scan ufficiale, non dal backfill dei
commit git (decisione utente). Scope: IT. Lo snapshot compatto diventa il
record storico canonico; `data.json` resta un build-artifact transitorio.

L'I/O (gzip, file) sta nella CLI scripts/historicize.py; qui solo logica pura.
"""

from __future__ import annotations

from collections import Counter

# Campi materiali tracciati nel diff (la loro variazione genera un evento).
# confidence è nello snapshot per i trend ma NON nel diff (micro-variazioni =
# rumore). jurisdiction (mx_jurisdiction ESORICS) è materiale: dove risiede
# fisicamente l'MX è sovranità.
DIFFED_FIELDS = ("provider", "sovereignty", "jurisdiction", "domain_used", "mx0")

PROVIDER_DISPLAY = {
    "microsoft": "Microsoft 365",
    "google": "Google Workspace",
    "aws": "AWS",
    "aruba": "Provider Italiano",
    "register-it": "Provider Italiano",
    "seeweb": "Provider Italiano",
    "infocert": "Provider Italiano",
    "namirial": "Provider Italiano",
    "local-isp": "Provider Italiano",
    "telia": "Provider Italiano",
    "tet": "Provider Italiano",
    "zone": "Provider Italiano",
    "elkdata": "Provider Italiano",
    "pa-contractor-private": "Provider Italiano",
    "regional-public": "Cloud Italiano",
    "independent": "Infrastruttura autonoma",
    "provincial-shared": "Mail provinciale condivisa",
    # tenant centrale MIM = MS365 (CLOUD Act)
    "istruzione-miur-tenant": "Microsoft 365",
    "zoho": "Zoho",
    "yandex": "Yandex",
    "unknown": "Sconosciuto",
}


def sovereignty_of(provider: str) -> str:
    """Bucket di sovranità (narrazione CLOUD Act), derivato dal provider."""
    disp = PROVIDER_DISPLAY.get(provider, "Sconosciuto")
    if disp in {"Microsoft 365", "Google Workspace", "AWS"}:
        return "USA (CLOUD Act)"
    if disp == "Cloud Italiano":
        return "Italia — Cloud sovrano"
    if disp in {"Provider Italiano", "Mail provinciale condivisa"}:
        return "Italia — Provider commerciali"
    if disp == "Infrastruttura autonoma":
        return "Italia — Infrastruttura autonoma"
    if disp in {"Zoho", "Yandex"}:
        return "Altri provider esteri"
    return "Sconosciuto"


def dkim_tenant_of(entry: dict) -> str | None:
    """Estrae <tenant>.onmicrosoft.com dal DKIM, se presente."""
    dkim = entry.get("dkim") or {}
    if isinstance(dkim, dict):
        for v in dkim.values():
            if isinstance(v, str) and "onmicrosoft.com" in v:
                for tok in v.replace(",", " ").split():
                    if tok.endswith("onmicrosoft.com"):
                        return tok.split("._domainkey.")[-1]
    return None


def parse_bfs(bfs: str | None) -> tuple[str, str]:
    """`IT-C1-m_it` → (cat='C1', ipa='m_it'). L'ipa può contenere '-'."""
    parts = (bfs or "").split("-")
    if len(parts) >= 3:
        return parts[1], "-".join(parts[2:])
    return "", ""


def material_row(entry: dict) -> dict:
    """Riga compatta materiale da un'entità data.json (solo campi materiali)."""
    provider = entry.get("provider") or "unknown"
    mx = entry.get("mx") or []
    cat, ipa = parse_bfs(entry.get("bfs"))
    conf = entry.get("classification_confidence")
    return {
        "id": entry.get("bfs") or entry.get("id"),
        "ipa": ipa,
        "cat": cat,
        "name": (entry.get("name") or "")[:120],
        "provider": provider,
        "sovereignty": sovereignty_of(provider),
        "jurisdiction": entry.get("mx_jurisdiction") or "unknown",
        "method": entry.get("mx_discovery_method") or "unknown",
        "domain_used": (entry.get("domain_used") or entry.get("domain") or "").lower(),
        "mx0": (mx[0].lower().rstrip(".") if mx else None),
        "has_mx": bool(mx),
        "confidence": round(conf, 2) if isinstance(conf, int | float) else None,
        "dkim_tenant": dkim_tenant_of(entry),
        "gateway": entry.get("gateway"),
    }


def _change_type(field: str, prev: dict, curr: dict) -> str:
    if field == "provider":
        if prev["provider"] == "unknown" and curr["provider"] != "unknown":
            return "resolved"
        if prev["provider"] != "unknown" and curr["provider"] == "unknown":
            return "regressed"
        return "provider_change"
    return {
        "sovereignty": "sovereignty_change",
        "jurisdiction": "jurisdiction_change",
        "domain_used": "domain_change",
        "mx0": "mx_change",
    }[field]


def _attribute_cause(method_changed: bool, git_changed: bool) -> str:
    """reality (la PA è migrata) vs methodology (abbiamo migliorato il
    rilevamento) vs uncertain (la logica è cambiata → da rivedere)."""
    if method_changed:
        return "methodology"
    if git_changed:
        return "uncertain"
    return "reality"


def classify_change(
    prev: dict | None, curr: dict | None, git_changed: bool
) -> list[dict]:
    """Confronta due righe materiali → lista di eventi changelog (per-campo)."""
    if prev is None and curr is not None:
        return [
            {
                "change": "new",
                "field": None,
                "from": None,
                "to": curr["provider"],
                "cause": "source",
            }
        ]
    if curr is None and prev is not None:
        return [
            {
                "change": "removed",
                "field": None,
                "from": prev["provider"],
                "to": None,
                "cause": "source",
            }
        ]

    events: list[dict] = []
    method_changed = prev["method"] != curr["method"]
    for field in DIFFED_FIELDS:
        if prev.get(field) == curr.get(field):
            continue
        events.append(
            {
                "change": _change_type(field, prev, curr),
                "field": field,
                "from": prev.get(field),
                "to": curr.get(field),
                "from_method": prev["method"],
                "to_method": curr["method"],
                "cause": _attribute_cause(method_changed, git_changed),
            }
        )
    # cambio di solo metodo (stessa classificazione su tutti i campi materiali)
    if method_changed and not events:
        events.append(
            {
                "change": "method_change",
                "field": "method",
                "from": prev["method"],
                "to": curr["method"],
                "cause": "methodology",
            }
        )
    return events


def diff_runs(
    prev: dict[str, dict], curr: dict[str, dict], git_changed: bool
) -> tuple[list[dict], Counter]:
    """Diff di tutti gli enti tra due run → (eventi arricchiti, conteggi)."""
    events: list[dict] = []
    counts: Counter = Counter()
    for eid in sorted(set(prev) | set(curr)):
        row = curr.get(eid) or prev.get(eid)
        for ev in classify_change(prev.get(eid), curr.get(eid), git_changed):
            ev.update(
                {
                    "id": eid,
                    "ipa": row.get("ipa", ""),
                    "name": row.get("name", ""),
                    "cat": row.get("cat", ""),
                }
            )
            events.append(ev)
            counts[ev["change"]] += 1
    return events, counts


def provider_counts(rows: dict[str, dict]) -> dict:
    return dict(Counter(r["provider"] for r in rows.values()).most_common())


def sovereignty_counts(rows: dict[str, dict]) -> dict:
    return dict(Counter(r["sovereignty"] for r in rows.values()).most_common())


def jurisdiction_counts(rows: dict[str, dict]) -> dict:
    return dict(Counter(r.get("jurisdiction", "unknown") for r in rows.values()))


def mean_confidence(rows: dict[str, dict]) -> float:
    vals = [
        r["confidence"]
        for r in rows.values()
        if isinstance(r.get("confidence"), int | float)
    ]
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def build_manifest(
    run_id: str,
    git_sha: str,
    pipeline_version: str,
    rows: dict[str, dict],
    counts: Counter,
    n_events: int,
    generated: str,
) -> dict:
    """Riga del manifest runs.jsonl per questo run."""
    n = len(rows)
    unknown = sum(1 for r in rows.values() if r["provider"] == "unknown")
    return {
        "run_id": run_id,
        "git_sha": git_sha,
        "pipeline_version": pipeline_version,
        "generated": generated,
        "n_entities": n,
        "n_changed": n_events,
        "n_new": counts.get("new", 0),
        "n_removed": counts.get("removed", 0),
        "n_resolved": counts.get("resolved", 0),
        "n_regressed": counts.get("regressed", 0),
        "n_provider_change": counts.get("provider_change", 0),
        "n_sovereignty_change": counts.get("sovereignty_change", 0),
        "n_jurisdiction_change": counts.get("jurisdiction_change", 0),
        "coverage_pct": round(100 * (n - unknown) / n, 2) if n else 0.0,
        "mean_confidence": mean_confidence(rows),
        "provider_counts": provider_counts(rows),
        "sovereignty": sovereignty_counts(rows),
        "jurisdiction": jurisdiction_counts(rows),
        "snapshot": f"snapshots/{run_id}.jsonl.gz",
    }


def build_timeseries(runs: list[dict]) -> dict[str, list]:
    """Da runs.jsonl (ordinato) → le serie temporali per la dashboard."""
    runs = sorted(runs, key=lambda r: r["run_id"])
    provider = [{"date": r["run_id"], **r.get("provider_counts", {})} for r in runs]
    sovereignty = [{"date": r["run_id"], **r.get("sovereignty", {})} for r in runs]
    jurisdiction = [{"date": r["run_id"], **r.get("jurisdiction", {})} for r in runs]
    coverage = [
        {
            "date": r["run_id"],
            "coverage_pct": r.get("coverage_pct", 0.0),
            "mean_confidence": r.get("mean_confidence", 0.0),
            "unknown": r.get("provider_counts", {}).get("unknown", 0),
        }
        for r in runs
    ]
    return {
        "provider_national": provider,
        "sovereignty": sovereignty,
        "jurisdiction": jurisdiction,
        "coverage": coverage,
    }


__all__ = [
    "PROVIDER_DISPLAY",
    "DIFFED_FIELDS",
    "sovereignty_of",
    "dkim_tenant_of",
    "parse_bfs",
    "material_row",
    "classify_change",
    "diff_runs",
    "provider_counts",
    "sovereignty_counts",
    "jurisdiction_counts",
    "mean_confidence",
    "build_manifest",
    "build_timeseries",
]
