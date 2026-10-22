#!/usr/bin/env bash
# Supervisor of the final regeneration (Issue #56), meant to run on jao-pc without anyone attached.
#
# Deployed as ~/regen-lab03/supervisor.sh (REGEN_HOME below). It keeps ONE instance (flock), runs
#   python -m pipeline.regenerar --resume --runs-modo reconciliar ...
# and restarts it whenever it exits non-zero (crash, OOM kill, transient API failure) or ends
# without the bundle. Waits 60 s between attempts, doubling up to 10 min, reset after progress
# (the checkpoint grew). When the run completes it writes the bundle (done by the pipeline),
# a local, unpushed commit and the DONE marker. Tokens are never printed: the pipeline reads them
# from lab03/.env and the log is filtered.
#
# The machine is shared with its owner: the unit runs with a memory budget and low priority, and the
# pipeline itself pauses new repositories while the system has < 3 GiB of RAM available.
#
# Launch (once):
#   systemd-run --user --unit=regen-sup --collect -p Restart=on-failure -p RestartSec=60 \
#     -p MemoryHigh=5G -p MemoryMax=7G -p Nice=15 -p IOSchedulingClass=idle -p CPUWeight=20 \
#     systemd-inhibit --what=sleep:idle --who=regen --why="dataset regeneration" \
#     bash ~/regen-lab03/supervisor.sh
#
# Check:  cat ~/regen-lab03/status.json ; tail ~/regen-lab03/supervisor.log ; ls ~/regen-lab03/DONE

set -u
REGEN_HOME="${REGEN_HOME:-$HOME/regen-lab03}"
LAB="$REGEN_HOME/lab03"
SUP_LOG="$REGEN_HOME/supervisor.log"
RUN_LOG="$REGEN_HOME/regen.log"
DONE="$REGEN_HOME/DONE"
CHECKPOINT="$LAB/dados/.regenerar/checkpoint.jsonl"
WORKERS="${REGEN_WORKERS:-2}"
MIN_AVAILABLE_MB="${REGEN_MIN_AVAILABLE_MB:-3072}"
MIN_WAIT="${REGEN_MIN_WAIT:-60}"
MAX_WAIT="${REGEN_MAX_WAIT:-600}"

log() { printf '%s [supervisor] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$SUP_LOG"; }

# One instance only
exec 9>"$REGEN_HOME/.supervisor.lock"
if ! flock -n 9; then
  log "another supervisor holds the lock; exiting"
  exit 0
fi

if [ -e "$DONE" ] && [ -z "${REGEN_FORCE:-}" ]; then
  log "DONE marker exists ($(head -n1 "$DONE")); nothing to do"
  exit 0
fi

# uv comes from mise (not on the PATH of a systemd user service)
UV="${REGEN_UV:-$(bash -lc 'mise which uv' 2>/dev/null | tail -n1)}"
if [ -z "$UV" ] || [ ! -x "$UV" ]; then
  UV="$(ls -1 "$HOME"/.local/share/mise/installs/uv/*/.mise-bins/uv 2>/dev/null | tail -n1)"
fi
if [ -z "$UV" ] || [ ! -x "$UV" ]; then
  log "uv not found"
  exit 1
fi
export UV_DEFAULT_INDEX="${UV_DEFAULT_INDEX:-https://pypi.org/simple}"
export PYTHONUNBUFFERED=1

checkpoint_lines() { [ -f "$CHECKPOINT" ] && wc -l <"$CHECKPOINT" || echo 0; }

cd "$LAB" || exit 1
wait_s=$MIN_WAIT
attempt=0
log "started (pid $$, uv=$UV, workers=$WORKERS)"

while true; do
  attempt=$((attempt + 1))
  before=$(checkpoint_lines)
  log "attempt $attempt: running pipeline.regenerar --resume (checkpoint lines: $before)"
  # filter anything that looks like a token prefix before it reaches the log
  nice -n 10 "$UV" run --frozen python -m pipeline.regenerar --config config.yaml \
      --resume --runs-modo reconciliar --workers "$WORKERS" \
      --mem-min-disponivel-mb "$MIN_AVAILABLE_MB" \
      --status "$REGEN_HOME/status.json" --bundle-dir "$REGEN_HOME" 2>&1 \
    | sed -u -E 's/(gh[pousr]_|github_pat_)[A-Za-z0-9_]+/\1***/g; s/Token [A-Za-z0-9_]{8}/Token ********/g' \
    >>"$RUN_LOG"
  rc=${PIPESTATUS[0]}
  after=$(checkpoint_lines)

  bundle="$(ls -1t "$REGEN_HOME"/outputs-*.tar.gz 2>/dev/null | head -n1)"
  if [ "$rc" -eq 0 ] && [ -n "$bundle" ]; then
    log "pipeline finished (rc=0), bundle $(basename "$bundle")"
    # Local commit so the work is not lost; never pushed from here.
    (
      cd "$REGEN_HOME" &&
      git add -A lab03/dados/repositorios.csv lab03/dados/repositorios.parquet lab03/dados/runs \
          lab03/docs/regeneracao_final.md lab03/config.yaml 2>>"$SUP_LOG" &&
      git -c user.name="regen-supervisor" -c user.email="regen@localhost" \
          commit -q -m "#56 regenerated dataset (local commit on jao-pc, not pushed)" 2>>"$SUP_LOG"
    ) && log "local commit created" || log "local commit skipped"
    # A temporary extra token may have been appended to GITHUB_TOKENS in lab03/.env. When the
    # operator sets REGEN_DROP_LAST_TOKEN_IF_COUNT=N, the last entry is removed here (only if the
    # list has exactly N entries). Nothing from the file is ever printed or logged.
    if [ -n "${REGEN_DROP_LAST_TOKEN_IF_COUNT:-}" ] && [ -f "$LAB/.env" ]; then
      python3 - "$LAB/.env" "$REGEN_DROP_LAST_TOKEN_IF_COUNT" >>"$SUP_LOG" 2>&1 <<'PY' || log "token cleanup failed"
import os, re, sys
path, expected = sys.argv[1], int(sys.argv[2])
lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
for i, line in enumerate(lines):
    m = re.match(r"^(\s*(?:export\s+)?GITHUB_TOKENS\s*=\s*)(['\"]?)(.*?)(['\"]?)(\s*)$", line.rstrip("\n"))
    if not m:
        continue
    entries = [e for e in m.group(3).split(",") if e.strip()]
    if len(entries) != expected:
        print("token cleanup skipped: unexpected number of entries")
        sys.exit(0)
    lines[i] = m.group(1) + m.group(2) + ",".join(entries[:-1]) + m.group(4) + "\n"
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    print("token cleanup: last GITHUB_TOKENS entry removed")
    sys.exit(0)
print("token cleanup skipped: GITHUB_TOKENS not found")
PY
    fi
    {
      date -u +%Y-%m-%dT%H:%M:%SZ
      basename "$bundle"
      cat "$bundle.sha256" 2>/dev/null
    } >"$DONE"
    log "DONE written"
    exit 0
  fi

  if [ "$after" -gt "$before" ]; then
    wait_s=$MIN_WAIT   # progress: reset the backoff
  fi
  log "attempt $attempt ended rc=$rc without completion (checkpoint $before -> $after); retrying in ${wait_s}s"
  sleep "$wait_s"
  wait_s=$((wait_s * 2))
  [ "$wait_s" -gt "$MAX_WAIT" ] && wait_s=$MAX_WAIT
done
