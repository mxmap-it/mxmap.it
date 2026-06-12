#!/usr/bin/env python3
"""Bounce-verifier — CLI di orchestrazione (vedi docs/BOUNCE_VERIFIER_DESIGN.md).

Sottocomandi:
  --export       scrive data/bounce/candidates.{csv,json} (69 enti frgn_mx_only)
  --dry-run      anteprima dei probe (default; NON invia)
  --send         esegue il flusso (richiede config/bounce.toml con dry_run=false)
  --collect-ndr  legge gli NDR via IMAP e li accoda al log
  --report       genera report_summary.{json,md} + report_detail.csv dal log

Logica e I/O nel modulo src/mail_sovereignty/bounce.py (testato). L'invio reale
passa per lo smarthost autenticato (Workspace) e va abilitato esplicitamente;
di default tutto è in dry-run. Gli esiti si leggono poi dagli NDR (--collect-ndr).
"""

from __future__ import annotations

import argparse
import csv
import json
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str((ROOT / "src").as_posix()))
OUTDIR = ROOT / "data" / "bounce"
CONFIG = ROOT / "config" / "bounce.toml"
LOG = OUTDIR / "probe_log.jsonl"

from mail_sovereignty import bounce  # noqa: E402

TARGET_RULES = {"frgn_mx_only"}
CONF_MAX = 0.60


def select_candidates(data_path: Path) -> list[dict]:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    muns = data.get("municipalities", data)
    out = []
    for v in muns.values():
        if (v.get("country") or "").upper() != "IT":
            continue
        conf = v.get("classification_confidence") or 0.0
        if v.get("classification_rule") in TARGET_RULES and 0.0 < conf < CONF_MAX and v.get("mx"):
            out.append(
                {
                    "bfs": v.get("bfs", ""),
                    "name": v.get("name", ""),
                    "domain": v.get("domain", ""),
                    "mx": list(v.get("mx") or []),
                    "mx_jurisdiction": v.get("mx_jurisdiction", ""),
                    "confidence": conf,
                    "rule": v.get("classification_rule"),
                    "reason": (v.get("reason") or "")[:160],
                }
            )
    out.sort(key=lambda r: r["domain"])
    return out


def dedupe_domains(cands: list[dict]) -> list[dict]:
    seen, out = set(), []
    for c in cands:
        if c["domain"] in seen:
            continue
        seen.add(c["domain"])
        out.append(c)
    return out


def export(cands: list[dict]) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for c in cands:
        c["target_address"] = f"mxmap-probe-no-such-mailbox@{c['domain']}"
    (OUTDIR / "candidates.json").write_text(
        json.dumps(cands, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    cols = ["bfs", "name", "domain", "mx", "mx_jurisdiction", "confidence", "rule", "target_address", "reason"]
    with open(OUTDIR / "candidates.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for c in cands:
            row = dict(c)
            row["mx"] = ";".join(c["mx"])
            w.writerow({k: row.get(k, "") for k in cols})
    print(f"Scritti {len(cands)} candidati in {OUTDIR}/candidates.{{csv,json}}")


def dry_run(cands: list[dict]) -> None:
    doms = dedupe_domains(cands)
    print(f"DRY-RUN: {len(cands)} enti su {len(doms)} domini distinti (NESSUN invio).\n")
    for c in doms[:15]:
        addr = f"mxmap-probe-no-such-mailbox@{c['domain']}"
        mx0 = (c["mx"][0] if c["mx"] else "?")
        print(f"  -> {addr:48}  via MX {mx0[:38]:38}  [{c['name'].encode('ascii', 'replace').decode()[:28]}]")
    if len(doms) > 15:
        print(f"  ... e altri {len(doms) - 15}. Lista completa: data/bounce/candidates.csv")
    print("\nNessuna email inviata. L'invio reale richiede config/bounce.toml (dry_run=false) e --send.")


def _resolve_ip(mx_host: str) -> str | None:
    try:
        return socket.getaddrinfo(mx_host, 25, proto=socket.IPPROTO_TCP)[0][4][0]
    except Exception:
        return None


def run_send(cfg: bounce.BounceConfig, cands: list[dict]) -> int:
    if cfg.dry_run:
        print(
            "RIFIUTO: config/bounce.toml ha dry_run=true. L'invio reale richiede "
            "dry_run=false (e la tua autorizzazione esplicita).",
            file=sys.stderr,
        )
        return 2
    doms = dedupe_domains(cands)
    plan = bounce.build_send_plan(
        [(c["domain"], _resolve_ip(c["mx"][0]) if c["mx"] else None) for c in doms],
        cfg.per_ip_min_interval_sec,
    )
    by_dom = {c["domain"]: c for c in doms}
    conn = bounce.open_smarthost(cfg)
    sends = []
    start = time.monotonic()
    print(f"INVIO via smarthost {cfg.smtp_host} su {len(plan)} domini...", file=sys.stderr)
    try:
        for step in plan:
            wait = step["offset_sec"] - (time.monotonic() - start)
            if wait > 0:
                time.sleep(wait)
            res = bounce.send_probe(cfg, by_dom[step["domain"]], smtp=conn)
            sends.append(res)
            bounce.write_jsonl(LOG, [{"type": "send", **bounce.asdict(res)}])
            print(f"  {res.domain:30} submitted={res.submitted} {res.error or ''}", file=sys.stderr)
    finally:
        try:
            conn.quit()
        except Exception:
            pass
    print("Invii completati. Attendi la finestra NDR, poi --collect-ndr e --report.", file=sys.stderr)
    _write_reports(sends, [])
    return 0


def run_collect(cfg: bounce.BounceConfig) -> int:
    ndrs = bounce.collect_ndrs(cfg)
    bounce.write_jsonl(LOG, [{"type": "ndr", **bounce.asdict(n)} for n in ndrs])
    print(f"Raccolti {len(ndrs)} NDR -> {LOG}")
    return 0


def _load_log() -> tuple[list[bounce.SendResult], list[bounce.NdrResult]]:
    sends, ndrs = [], []
    if not LOG.exists():
        return sends, ndrs
    for line in LOG.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        t = rec.pop("type", "send")
        if t == "send":
            sends.append(bounce.SendResult(**{k: rec.get(k) for k in bounce.SendResult.__dataclass_fields__ if k in rec}))
        else:
            ndrs.append(bounce.NdrResult(**{k: rec.get(k) for k in bounce.NdrResult.__dataclass_fields__ if k in rec}))
    return sends, ndrs


def _write_reports(sends, ndrs) -> None:
    summ = bounce.build_summary(sends, ndrs)
    detail = bounce.build_detail(sends, ndrs)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "report_summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# Bounce-verifier — rendiconto sintetico", ""]
    md.append(f"- inviati: **{summ['n_sent']}** · NDR raccolti: {summ['n_ndr']} · riclassificabili: **{summ['reclassifiable']}**")
    md.append(f"- per esito: {summ['by_outcome']}")
    md.append(f"- per origine NDR (hop): {summ.get('by_ndr_origin', {})}")
    md.append(f"- per backend identificato (da NDR): {summ['by_backend']}")
    (OUTDIR / "report_summary.md").write_text("\n".join(md), encoding="utf-8")
    cols = ["domain", "submitted", "outcome", "ndr_origin", "identified_backend", "reporting_mta", "ndr_status", "ndr_diagnostic", "remote_mta", "ndr_from", "error"]
    with open(OUTDIR / "report_detail.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in detail:
            w.writerow({k: r.get(k, "") for k in cols})
    print(f"Report -> {OUTDIR}/report_summary.{{json,md}} + report_detail.csv")


def run_report() -> int:
    results, ndrs = _load_log()
    _write_reports(results, ndrs)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data.json")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--collect-ndr", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    if args.send or args.collect_ndr:
        if not CONFIG.exists():
            print(f"ERRORE: manca {CONFIG}. Copia config/bounce.example.toml e compila.", file=sys.stderr)
            return 2
        cfg = bounce.load_config(CONFIG)
        cands = select_candidates(args.data)
        return run_send(cfg, cands) if args.send else run_collect(cfg)
    if args.report:
        return run_report()

    cands = select_candidates(args.data)
    if args.export:
        export(cands)
    if args.dry_run or not args.export:
        dry_run(cands)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
