#!/usr/bin/env python3
"""Storicizzazione di un run dell'Osservatorio (Task #15 — PROTOTIPO F1).

Vedi docs/HISTORICIZATION_DESIGN.md per il design completo.

Dato il `data.json` corrente (e opzionalmente lo snapshot del run
precedente), produce:
  - history/snapshots/{run_id}.jsonl.gz   snapshot compatto (campi materiali)
  - history/changelog/{YYYY-MM}.jsonl     eventi di cambiamento (append)
  - history/runs.jsonl                    manifest dei run (append/update)
  - history/timeseries/provider_national.json
  - history/timeseries/sovereignty.json
  - history/timeseries/coverage.json
  - history/CHANGELOG-{run_id}.md         changelog leggibile

Idempotente sul run_id: ri-eseguire sovrascrive lo snapshot e l'entry
di runs.jsonl, e rimuove eventuali eventi changelog già scritti per
quel run_id prima di riscriverli.

Uso:
  uv run python3 scripts/historicize.py --run-id 2026-05-30 \
       --git-sha 29ea8ecd --pipeline-version 1.3.0
  # confronto esplicito di due file (per backfill / test):
  uv run python3 scripts/historicize.py --run-id R --data data.json \
       --prev-snapshot history/snapshots/2026-05-29.jsonl.gz
"""
from __future__ import annotations

import argparse
import gzip
import json
import time
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "history"
SNAP_DIR = HISTORY / "snapshots"
CHANGELOG_DIR = HISTORY / "changelog"
TS_DIR = HISTORY / "timeseries"

# Campi materiali: la loro variazione È un cambiamento. Tutto il resto
# (spf raw, cnames, ttl, ordine MX non-primario) è rumore e va ignorato.
MATERIAL_FIELDS = ("provider", "method", "domain_used", "mx0", "has_mx",
                   "sovereignty", "dkim_tenant", "gateway")

PROVIDER_DISPLAY = {
    "microsoft": "Microsoft 365", "google": "Google Workspace", "aws": "AWS",
    "aruba": "Provider Italiano", "register-it": "Provider Italiano",
    "seeweb": "Provider Italiano", "infocert": "Provider Italiano",
    "namirial": "Provider Italiano", "local-isp": "Provider Italiano",
    "telia": "Provider Italiano", "tet": "Provider Italiano",
    "zone": "Provider Italiano", "elkdata": "Provider Italiano",
    "pa-contractor-private": "Provider Italiano",
    "regional-public": "Cloud Italiano",
    "independent": "Infrastruttura autonoma",
    "provincial-shared": "Mail provinciale condivisa",
    "istruzione-miur-tenant": "Microsoft 365",  # tenant centrale MIM = MS365
    "zoho": "Zoho", "yandex": "Yandex", "unknown": "Sconosciuto",
}


def sovereignty_of(provider: str) -> str:
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
    dkim = entry.get("dkim") or {}
    if isinstance(dkim, dict):
        for v in dkim.values():
            if isinstance(v, str) and "onmicrosoft.com" in v:
                # estrai <tenant>.onmicrosoft.com
                for tok in v.replace(",", " ").split():
                    if tok.endswith("onmicrosoft.com"):
                        return tok.split("._domainkey.")[-1]
    return None


def material_row(entry: dict) -> dict:
    """Estrae la riga compatta materiale da un'entità data.json."""
    provider = entry.get("provider") or "unknown"
    mx = entry.get("mx") or []
    return {
        "id": entry.get("bfs") or entry.get("id"),
        "ipa": entry.get("ipa_codice_ipa") or "",
        "cat": entry.get("ipa_codice_categoria") or "",
        "name": (entry.get("name") or "")[:120],
        "provider": provider,
        "sovereignty": sovereignty_of(provider),
        "method": entry.get("mx_discovery_method") or "unknown",
        "domain_used": (entry.get("domain_used") or entry.get("domain") or "").lower(),
        "mx0": (mx[0].lower().rstrip(".") if mx else None),
        "has_mx": bool(mx),
        "dkim_tenant": dkim_tenant_of(entry),
        "gateway": entry.get("gateway"),
    }


def load_data_json(path: Path, country: str = "IT") -> dict[str, dict]:
    """Carica data.json e ritorna {id: material_row} per il paese dato."""
    d = json.loads(path.read_text(encoding="utf-8"))
    muns = d.get("municipalities") or d
    out = {}
    for v in muns.values():
        if country and (v.get("country") or "").upper() != country:
            continue
        row = material_row(v)
        if row["id"]:
            out[row["id"]] = row
    return out


def load_snapshot(path: Path) -> dict[str, dict]:
    """Carica uno snapshot compatto .jsonl.gz → {id: row}."""
    out = {}
    if not path.exists():
        return out
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            out[row["id"]] = row
    return out


def write_snapshot(path: Path, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for row in rows.values():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def classify_change(prev: dict | None, curr: dict | None,
                    git_changed: bool) -> list[dict]:
    """Confronta due righe materiali → lista di eventi changelog."""
    events = []
    if prev is None and curr is not None:
        events.append({"change": "new", "field": None,
                       "from": None, "to": curr["provider"],
                       "cause": "source"})
        return events
    if curr is None and prev is not None:
        events.append({"change": "removed", "field": None,
                       "from": prev["provider"], "to": None,
                       "cause": "source"})
        return events

    # entrambi presenti: diff sui campi materiali
    method_changed = prev["method"] != curr["method"]
    for field in ("provider", "sovereignty", "domain_used", "mx0"):
        if prev.get(field) == curr.get(field):
            continue
        # determina il tipo
        if field == "provider":
            if prev["provider"] == "unknown" and curr["provider"] != "unknown":
                ctype = "resolved"
            elif prev["provider"] != "unknown" and curr["provider"] == "unknown":
                ctype = "regressed"
            else:
                ctype = "provider_change"
        elif field == "sovereignty":
            ctype = "sovereignty_change"
        elif field == "domain_used":
            ctype = "domain_change"
        else:
            ctype = "mx_change"

        # attribuzione causa
        if method_changed:
            cause = "methodology"
        elif git_changed:
            cause = "uncertain"   # la logica è cambiata, potrebbe essere un fix
        else:
            cause = "reality"     # stessa logica, dato diverso → la PA è migrata

        events.append({"change": ctype, "field": field,
                       "from": prev.get(field), "to": curr.get(field),
                       "from_method": prev["method"], "to_method": curr["method"],
                       "cause": cause})

    # cambio di solo metodo (stessa classificazione)
    if method_changed and not any(e["field"] == "provider" for e in events):
        events.append({"change": "method_change", "field": "method",
                       "from": prev["method"], "to": curr["method"],
                       "cause": "methodology"})
    return events


def provider_counts(rows: dict[str, dict]) -> dict:
    return dict(Counter(r["provider"] for r in rows.values()).most_common())


def sovereignty_counts(rows: dict[str, dict]) -> dict:
    return dict(Counter(r["sovereignty"] for r in rows.values()).most_common())


def append_jsonl(path: Path, obj: dict, dedup_key: str | None = None,
                 dedup_val=None) -> None:
    """Append una riga; se dedup_key dato, rimuove prima le righe con
    quel valore (idempotenza sul run_id)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if dedup_key and row.get(dedup_key) == dedup_val:
                continue
            existing.append(row)
    existing.append(obj)
    with open(path, "w", encoding="utf-8") as f:
        for row in existing:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def remove_run_from_jsonl(path: Path, run_id: str) -> list[dict]:
    """Rimuove tutte le righe con run_id dato; ritorna le rimanenti."""
    if not path.exists():
        return []
    kept = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("run_id") == run_id:
            continue
        kept.append(row)
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--prev-snapshot", type=Path, default=None,
                    help="snapshot del run precedente (.jsonl.gz)")
    ap.add_argument("--git-sha", default="")
    ap.add_argument("--pipeline-version", default="")
    ap.add_argument("--country", default="IT")
    args = ap.parse_args()

    print(f"=== Historicize run {args.run_id} ===")
    curr = load_data_json(args.data, country=args.country)
    print(f"  entità correnti ({args.country}): {len(curr)}")

    # snapshot precedente: esplicito o l'ultimo in snapshots/
    prev_path = args.prev_snapshot
    if prev_path is None:
        snaps = sorted(SNAP_DIR.glob("*.jsonl.gz")) if SNAP_DIR.exists() else []
        prev_path = snaps[-1] if snaps else None
    prev = load_snapshot(prev_path) if prev_path else {}
    print(f"  snapshot precedente: {prev_path.name if prev_path else '(nessuno)'} "
          f"({len(prev)} entità)")

    # git_changed: il codice è cambiato dall'ultima run? (euristica: se
    # abbiamo un git-sha e differisce da quello dell'ultima run nel manifest)
    git_changed = False
    runs_path = HISTORY / "runs.jsonl"
    last_sha = None
    if runs_path.exists():
        rows = [json.loads(l) for l in runs_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        prev_runs = [r for r in rows if r.get("run_id") != args.run_id]
        if prev_runs:
            last_sha = prev_runs[-1].get("git_sha")
    if args.git_sha and last_sha and args.git_sha != last_sha:
        git_changed = True

    # diff
    all_ids = set(prev) | set(curr)
    events = []
    counts = Counter()
    for eid in sorted(all_ids):
        evs = classify_change(prev.get(eid), curr.get(eid), git_changed)
        for ev in evs:
            row = curr.get(eid) or prev.get(eid)
            ev.update({"run_id": args.run_id, "id": eid,
                       "ipa": row.get("ipa", ""), "name": row.get("name", ""),
                       "cat": row.get("cat", ""), "git_sha": args.git_sha})
            events.append(ev)
            counts[ev["change"]] += 1

    print(f"  eventi di cambiamento: {len(events)}")
    for k, v in counts.most_common():
        print(f"    {k:<18} {v}")

    # --- scrittura artefatti ---
    # 1. snapshot
    snap_out = SNAP_DIR / f"{args.run_id}.jsonl.gz"
    write_snapshot(snap_out, curr)

    # 2. changelog (idempotente sul run_id)
    month = args.run_id[:7]  # YYYY-MM
    cl_path = CHANGELOG_DIR / f"{month}.jsonl"
    kept = remove_run_from_jsonl(cl_path, args.run_id)
    CHANGELOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(cl_path, "w", encoding="utf-8") as f:
        for row in kept:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        for ev in events:
            ev["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # 3. runs.jsonl
    pc = provider_counts(curr)
    sv = sovereignty_counts(curr)
    manifest = {
        "run_id": args.run_id, "git_sha": args.git_sha,
        "pipeline_version": args.pipeline_version,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_entities": len(curr), "n_changed": len(events),
        "n_new": counts.get("new", 0), "n_removed": counts.get("removed", 0),
        "n_resolved": counts.get("resolved", 0),
        "n_regressed": counts.get("regressed", 0),
        "n_provider_change": counts.get("provider_change", 0),
        "provider_counts": pc, "sovereignty": sv,
        "snapshot": f"snapshots/{args.run_id}.jsonl.gz",
    }
    append_jsonl(runs_path, manifest, dedup_key="run_id", dedup_val=args.run_id)

    # 4. time-series (ricostruiti da runs.jsonl per coerenza)
    TS_DIR.mkdir(parents=True, exist_ok=True)
    runs = sorted(
        [json.loads(l) for l in runs_path.read_text(encoding="utf-8").splitlines() if l.strip()],
        key=lambda r: r["run_id"])
    prov_ts = [{"date": r["run_id"], **r["provider_counts"]} for r in runs]
    sov_ts = [{"date": r["run_id"], **r["sovereignty"]} for r in runs]
    cov_ts = [{"date": r["run_id"],
               "resolved": r["n_entities"] - r["provider_counts"].get("unknown", 0),
               "unknown": r["provider_counts"].get("unknown", 0),
               "coverage_pct": round(100 * (r["n_entities"] - r["provider_counts"].get("unknown", 0))
                                     / r["n_entities"], 2) if r["n_entities"] else 0}
              for r in runs]
    (TS_DIR / "provider_national.json").write_text(
        json.dumps(prov_ts, ensure_ascii=False, indent=2), encoding="utf-8")
    (TS_DIR / "sovereignty.json").write_text(
        json.dumps(sov_ts, ensure_ascii=False, indent=2), encoding="utf-8")
    (TS_DIR / "coverage.json").write_text(
        json.dumps(cov_ts, ensure_ascii=False, indent=2), encoding="utf-8")

    # 5. CHANGELOG markdown leggibile
    md = [f"# Changelog run {args.run_id}", ""]
    md.append(f"- git: `{args.git_sha}`  pipeline: `{args.pipeline_version}`")
    md.append(f"- entità: {len(curr)}  cambiamenti: {len(events)}")
    md.append("")
    by_cause = Counter(e["cause"] for e in events)
    md.append(f"**Per causa**: " + ", ".join(f"{k}={v}" for k, v in by_cause.most_common()))
    md.append("")
    for ctype in ("resolved", "regressed", "provider_change",
                  "sovereignty_change", "new", "removed"):
        evs = [e for e in events if e["change"] == ctype]
        if not evs:
            continue
        md.append(f"## {ctype} ({len(evs)})")
        for e in evs[:50]:
            md.append(f"- **{e['name'][:50]}** ({e['ipa']}): "
                      f"`{e.get('from')}` → `{e.get('to')}` "
                      f"[{e['cause']}]")
        if len(evs) > 50:
            md.append(f"- … +{len(evs)-50} altri")
        md.append("")
    (HISTORY / f"CHANGELOG-{args.run_id}.md").write_text("\n".join(md), encoding="utf-8")

    print(f"\n  Scritti: {snap_out.name}, {cl_path.name}, runs.jsonl, "
          f"timeseries/*.json, CHANGELOG-{args.run_id}.md")
    print(f"  Snapshot: {snap_out.stat().st_size/1024:.0f} KB gz")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
