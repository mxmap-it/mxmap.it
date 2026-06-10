#!/usr/bin/env python3
"""Backfill dello storico dai commit git esistenti di data.json (PROTOTIPO).

Estrae ogni versione storica di data.json committata in git e la passa a
historicize.py in ordine cronologico, ricostruendo runs.jsonl + changelog
+ timeseries da dati REALI già presenti nella history git.

Dimostra la tesi del design §10: i 160 commit esistenti danno ~1 mese di
storia al day-one, senza aspettare nuovi run.

Uso:
  uv run python3 scripts/backfill_history.py [--max N] [--country IT]
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, check=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="max commit (0=tutti)")
    ap.add_argument("--country", default="IT")
    args = ap.parse_args()

    # commit che toccano data.json, dal più vecchio al più recente
    log = git("log", "--reverse", "--format=%H|%cI|%s", "--", "data.json")
    commits = []
    for line in log.splitlines():
        if not line.strip():
            continue
        sha, iso, subj = line.split("|", 2)
        date = iso[:10]
        commits.append((sha, date, subj))
    if args.max:
        # campiona uniformemente max commit per coprire tutto il periodo
        if len(commits) > args.max:
            step = len(commits) / args.max
            commits = [commits[int(i * step)] for i in range(args.max)]

    print(f"Backfill di {len(commits)} commit storici di data.json\n")
    seen_dates = set()
    for i, (sha, date, subj) in enumerate(commits, 1):
        # run_id unico: se più commit nello stesso giorno, suffissa
        run_id = date
        n = 2
        while run_id in seen_dates:
            run_id = f"{date}.{n}"
            n += 1
        seen_dates.add(run_id)

        print(f"[{i}/{len(commits)}] {run_id}  {sha[:8]}  {subj[:50]}")
        # estrai quella versione di data.json in un file temporaneo
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                          encoding="utf-8") as tf:
            try:
                blob = git("show", f"{sha}:data.json")
            except subprocess.CalledProcessError:
                print("    (data.json assente in questo commit, skip)")
                continue
            tf.write(blob)
            tmp_path = tf.name

        try:
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "historicize.py"),
                 "--run-id", run_id, "--data", tmp_path,
                 "--git-sha", sha[:8], "--country", args.country],
                check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"    ERRORE historicize: {e.stderr[-300:]}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # stampa il riassunto del time-series risultante
    ts = ROOT / "history" / "timeseries" / "sovereignty.json"
    if ts.exists():
        data = json.loads(ts.read_text(encoding="utf-8"))
        print(f"\n=== Time-series sovranità ricostruita ({len(data)} run) ===")
        for row in data:
            usa = row.get("USA (CLOUD Act)", 0)
            sov = row.get("Italia — Cloud sovrano", 0)
            unk = row.get("Sconosciuto", 0)
            print(f"  {row['date']:<12} USA-CloudAct={usa:<6} "
                  f"CloudSovrano={sov:<5} Sconosciuto={unk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
