#!/usr/bin/env python3
"""Storicizzazione di un run — CLI (I/O). Logica in src/mail_sovereignty/historicize.py.

Forward-only (niente backfill): produce per il run corrente
  history/snapshots/{run_id}.jsonl.gz   snapshot compatto canonico (campi materiali)
  history/changelog/{YYYY-MM}.jsonl     eventi di cambiamento (append, per-campo)
  history/runs.jsonl                    manifest dei run
  history/timeseries/{provider_national,sovereignty,jurisdiction,coverage}.json
  history/CHANGELOG-{run_id}.md         changelog leggibile

Idempotente sul run_id: ri-eseguire sovrascrive snapshot + entry runs.jsonl e
riscrive gli eventi changelog di quel run.

Uso:
  uv run python3 scripts/historicize.py --run-id 2026-06-12 \
       --git-sha "$GITHUB_SHA" --pipeline-version "$(cat VERSION)"
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))
HISTORY = ROOT / "history"
SNAP_DIR = HISTORY / "snapshots"
CHANGELOG_DIR = HISTORY / "changelog"
TS_DIR = HISTORY / "timeseries"

from mail_sovereignty import historicize as H  # noqa: E402


def load_data_json(path: Path, country: str = "IT") -> dict[str, dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    muns = d.get("municipalities") or d
    out = {}
    for v in muns.values():
        if country and (v.get("country") or "").upper() != country:
            continue
        row = H.material_row(v)
        if row["id"]:
            out[row["id"]] = row
    return out


def load_snapshot(path: Path | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not path or not path.exists():
        return out
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                row = json.loads(line)
                out[row["id"]] = row
    return out


def write_snapshot(path: Path, rows: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for row in rows.values():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--prev-snapshot", type=Path, default=None)
    ap.add_argument("--git-sha", default="")
    ap.add_argument("--pipeline-version", default="")
    ap.add_argument("--country", default="IT")
    args = ap.parse_args()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    print(f"=== Historicize run {args.run_id} ({args.country}) ===")
    curr = load_data_json(args.data, country=args.country)
    print(f"  entita correnti: {len(curr)}")

    prev_path = args.prev_snapshot
    if prev_path is None and SNAP_DIR.exists():
        snaps = sorted(SNAP_DIR.glob("*.jsonl.gz"))
        prev_path = snaps[-1] if snaps else None
    prev = load_snapshot(prev_path)
    print(f"  snapshot precedente: {prev_path.name if prev_path else '(nessuno)'} ({len(prev)})")

    runs_path = HISTORY / "runs.jsonl"
    events, counts = H.diff_runs(prev, curr)
    print(f"  eventi: {len(events)}  " + " ".join(f"{k}={v}" for k, v in counts.most_common()))

    # 1. snapshot canonico
    write_snapshot(SNAP_DIR / f"{args.run_id}.jsonl.gz", curr)

    # 2. changelog (idempotente sul run_id)
    cl_path = CHANGELOG_DIR / f"{args.run_id[:7]}.jsonl"
    kept = [e for e in read_jsonl(cl_path) if e.get("run_id") != args.run_id]
    for ev in events:
        ev["run_id"] = args.run_id
        ev["ts"] = now
        ev["git_sha"] = args.git_sha
    write_jsonl(cl_path, kept + events)

    # 3. runs.jsonl
    manifest = H.build_manifest(
        args.run_id, args.git_sha, args.pipeline_version, curr, counts, len(events), now
    )
    runs = [r for r in read_jsonl(runs_path) if r.get("run_id") != args.run_id]
    runs.append(manifest)
    write_jsonl(runs_path, runs)

    # 3b. F2: scheda storica per-ente (solo enti con eventi in questo run)
    entity_dir = HISTORY / "entity"
    by_ent: dict[str, list] = {}
    for ev in events:
        by_ent.setdefault(ev.get("ipa") or ev.get("id") or "", []).append(ev)
    for key, evs in by_ent.items():
        if not key:
            continue
        safe = "".join(c if (c.isalnum() or c in "_.-") else "_" for c in key)
        eid = evs[0]["id"]
        ef = entity_dir / f"{safe}.json"
        existing = json.loads(ef.read_text(encoding="utf-8")) if ef.exists() else None
        curr_row = curr.get(eid) or {
            "ipa": key,
            "name": evs[0].get("name", ""),
            "cat": evs[0].get("cat", ""),
        }
        updated = H.update_entity_timeline(existing, args.run_id, curr_row, evs)
        ef.parent.mkdir(parents=True, exist_ok=True)
        ef.write_text(json.dumps(updated, ensure_ascii=False, indent=1), encoding="utf-8")

    # 4. time-series (ricostruite da runs.jsonl per coerenza)
    TS_DIR.mkdir(parents=True, exist_ok=True)
    for name, series in H.build_timeseries(runs).items():
        (TS_DIR / f"{name}.json").write_text(
            json.dumps(series, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    # 5. CHANGELOG markdown leggibile
    md = [
        f"# Changelog run {args.run_id}",
        "",
        f"- git: `{args.git_sha}` - pipeline: `{args.pipeline_version}`",
        f"- entita: {len(curr)} - cambiamenti: {len(events)}",
        "",
    ]
    order = ("resolved", "regressed", "provider_change", "sovereignty_change", "jurisdiction_change", "new", "removed")
    for ctype in order:
        evs = [e for e in events if e["change"] == ctype]
        if not evs:
            continue
        md.append(f"## {ctype} ({len(evs)})")
        for e in evs[:50]:
            md.append(f"- **{e['name'][:50]}** ({e['ipa']}): `{e.get('from')}` -> `{e.get('to')}`")
        if len(evs) > 50:
            md.append(f"- ... +{len(evs) - 50} altri")
        md.append("")
    (HISTORY / f"CHANGELOG-{args.run_id}.md").write_text("\n".join(md), encoding="utf-8")

    snap_kb = (SNAP_DIR / f"{args.run_id}.jsonl.gz").stat().st_size / 1024
    print(f"  Scritti in history/: snapshot ({snap_kb:.0f} KB), changelog, runs.jsonl, timeseries/*, CHANGELOG.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
