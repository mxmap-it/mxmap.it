#!/usr/bin/env bash
# Server-side autonomous wrapper. Designed to keep running even when the
# user's laptop (running Claude Desktop) disconnects mid-flight.
#
# Chain:
#   1. wait for any in-flight `uv run preprocess IT` to finish
#   2. recover_it_unknowns
#   3. probe_it_provincial_backends
#   4. reclassify_it_provincial
#   5. finalize_it_unknowns
#   6. report_it_per_province
#   7. report_it_by_category
#   8. build_frontend
#   9. commit + push (push is best-effort; needs SSH deploy-key on
#      git@github.com:fpietrosanti/mxmap.it for write access)
#
# Logs to ~/server_autorun.log (append). Always safe to re-run.
#
# Invoke detached on the server:
#   nohup ./scripts/server_autorun_full_pipeline.sh > ~/server_autorun.log 2>&1 &

set -uo pipefail
cd "$(dirname "$0")/.."

LOG="${LOG:-$HOME/server_autorun.log}"
log() { echo "[$(date -u +%FT%TZ)] $*" >> "$LOG"; }

export PATH="$HOME/.local/bin:$PATH"

log "=== server_autorun started ==="

# 1) Wait for any preprocess in flight (user-launched). This survives.
while pgrep -af "uv run preprocess IT" > /dev/null 2>&1; do
  log "waiting for preprocess to finish..."
  sleep 60
done
log "preprocess finished (or never running). Continuing chain."

run_step() {
  local name="$1"; shift
  log "step: $name -> running: $*"
  if "$@" >> "$LOG" 2>&1; then
    log "step: $name OK"
  else
    log "step: $name FAILED (rc=$?) — continuing"
  fi
}

run_step "recover_it_unknowns"          uv run python3 scripts/recover_it_unknowns.py
run_step "probe_it_provincial_backends" uv run python3 scripts/probe_it_provincial_backends.py
run_step "reclassify_it_provincial"     uv run python3 scripts/reclassify_it_provincial.py
run_step "finalize_it_unknowns"         uv run python3 scripts/finalize_it_unknowns.py
run_step "report_it_per_province"       uv run python3 scripts/report_it_per_province.py
run_step "report_it_by_category"        uv run python3 scripts/report_it_by_category.py
run_step "build_frontend"               uv run python3 scripts/build_frontend.py

log "=== chain complete; committing artifacts ==="
git add data.json data/dns_cache/ data/municipalities_it.json data/it_provincial_backends.json data/reports/ data-summary.json data-detail.json data-regions.json data/summary/ 2>>"$LOG" || true

if git diff --cached --quiet; then
  log "no new changes to commit"
else
  git -c user.email="mxmap.it@51.158.36.151" \
      -c user.name="mxmap.it pipeline" \
      commit -m "data(it): autorun full-pipeline (incl. tier2/3 IndicePA categories)" >> "$LOG" 2>&1 \
    && log "commit OK" || log "commit FAILED"
fi

log "=== attempting push to origin ==="
if git push origin main >> "$LOG" 2>&1; then
  log "push OK"
else
  log "push FAILED (likely no deploy key with write access on the GitHub repo)"
  log "to grant: add ~/.ssh/id_ed25519.pub as a deploy key WITH write access"
  log "  https://github.com/fpietrosanti/mxmap.it/settings/keys/new"
  log "and switch the remote to SSH: git remote set-url origin git@github.com:fpietrosanti/mxmap.it.git"
fi

log "=== server_autorun done ==="
