#!/usr/bin/env bash
# Pave helper. Deterministic hub operations that need no model.
#
#   pave.sh add <folder>...    register service folders with the hub
#   pave.sh stale [service]     report what needs discovery or analysis, and stale findings
#   pave.sh feature propose <args...>   classify a feature argument, create nothing
#   pave.sh feature create <id> [title] create a confirmed feature's folder
#   pave.sh seal                        record spec and task hashes at the plan gate
#   pave.sh check                       is the plan still the one approved for this spec?
#   pave.sh prune-obsoleted-tasks       remove reverted obsolete tasks
#
# seal, check and prune-obsoleted-tasks act on the session's feature, given
# only as SESSION_FEATURE_ID=<id> - never as an argument:
#   SESSION_FEATURE_ID=FEAT-8888 pave.sh check
#
#   pave.sh agent <name>        model and effort to spawn an agent with
#   pave.sh config-check        compare the hub's config with what Pave reads
#   pave.sh config-check --fix  apply those fixes (only /pave:init, on "yes")
#
# Run from anywhere inside or beside the hub; it walks up for .pave-hub.
set -uo pipefail

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

find_hub() {
  local d="${PAVE_HUB:-$PWD}"
  d="$(cd "$d" 2>/dev/null && pwd)" || die "cannot resolve $d"
  while [ "$d" != "/" ]; do
    [ -e "$d/.pave-hub" ] && { printf '%s' "$d"; return 0; }
    d="$(dirname "$d")"
  done
  die "no .pave-hub found. Run /pave:init first, or set PAVE_HUB."
}

have_python() { command -v python3 >/dev/null 2>&1; }

SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# add <folder>...
cmd_add() {
  [ $# -ge 1 ] || die "usage: pave.sh add <folder>..."
  local hub; hub="$(find_hub)"
  local ws="$hub/workspace.yaml"
  local settings="$hub/.claude/settings.json"
  [ -f "$ws" ] || die "no workspace.yaml in $hub. Run /pave:init first."

  local added=0
  for raw in "$@"; do
    if [ ! -d "$raw" ]; then
      printf 'skip   %s — not a directory\n' "$raw"; continue
    fi
    local path name
    path="$(cd "$raw" && pwd)"
    name="$(basename "$path")"

    case "$path" in
      "$hub"|"$hub"/*)
        printf 'skip   %s — inside the hub. The hub holds planning, not code.\n' "$name"
        continue ;;
    esac

    if grep -qE "^[[:space:]]*path:[[:space:]]*${path}[[:space:]]*$" "$ws"; then
      printf 'skip   %s — already registered\n' "$name"; continue
    fi
    if grep -qE "^[[:space:]]*-[[:space:]]*name:[[:space:]]*${name}[[:space:]]*$" "$ws"; then
      printf 'CLASH  %s — that name is registered at a different path. Rename one.\n' "$name"
      continue
    fi

    local note=""
    git -C "$path" rev-parse --git-dir >/dev/null 2>&1 || note="  (not a git repository — builders cannot branch here)"

    printf '\n  - name: %s\n    path: %s\n' "$name" "$path" >> "$ws"
    printf 'added  %s → %s%s\n' "$name" "$path" "$note"
    added=$((added+1))

    if have_python; then
      PAVE_DIR="$path" PAVE_SETTINGS="$settings" python3 - <<'PY'
import json, os, pathlib
p = pathlib.Path(os.environ["PAVE_SETTINGS"]); d = os.environ["PAVE_DIR"]
p.parent.mkdir(parents=True, exist_ok=True)
try:
    cfg = json.loads(p.read_text()) if p.exists() and p.read_text().strip() else {}
except json.JSONDecodeError:
    raise SystemExit("settings.json is not valid JSON — left alone")
dirs = cfg.setdefault("additionalDirectories", [])
if d not in dirs:
    dirs.append(d)
    p.write_text(json.dumps(cfg, indent=2) + "\n")
PY
      [ $? -eq 0 ] || printf 'WARN   could not update settings.json — add %s to additionalDirectories by hand\n' "$path"
    else
      printf 'WARN   python3 not found — add %s to additionalDirectories in %s by hand\n' "$path" "$settings"
    fi
  done

  printf '\nhub: %s\n' "$hub"
  printf 'registered services: %s\n' "$(grep -cE '^[[:space:]]*-[[:space:]]*name:' "$ws" || echo 0)"
  [ "$added" -gt 0 ] && printf 'next: /pave:analyse\n'
  return 0
}

# stale [service]
# Reports per-service state. Decides nothing - /pave:analyse reads this and
# chooses what to spawn.
cmd_stale() {
  local hub; hub="$(find_hub)"
  have_python || die "python3 is required for 'stale'"
  python3 "$SCRIPTS/pave-stale.py" "$hub" "$@"
}

# feature propose <ticket-id|feature-id|description...>
# Classifies the argument and reports candidates. Creates nothing: the id is
# confirmed by the user first, so a rejected proposal leaves no folder behind.
cmd_feature_propose() {
  [ $# -ge 1 ] || die "usage: pave.sh feature propose <ticket-id|feature-id|description...>"
  local hub; hub="$(find_hub)"
  local fdir="$hub/features"

  if [ $# -eq 1 ] && [ -d "$fdir/$1" ]; then
    printf 'kind: existing\nid: %s\ntitle: %s\npath: %s\n' "$1" "$(spec_title "$fdir/$1")" "$fdir/$1"
    return 0
  fi
  # A ticket reference: letters, hyphen, digits. Case preserved as typed.
  if printf '%s' "$1" | grep -qE '^[A-Za-z][A-Za-z0-9_]*-[0-9]+$'; then
    local id="$1"; shift
    printf 'kind: ticket\nid: %s\ntitle: %s\n' "$id" "$*"
    [ -d "$fdir/$id" ] && printf 'note: exists - %s\n' "$fdir/$id"
    return 0
  fi
  printf 'kind: description\nnext: %s\ntitle: %s\n' "$(next_feat "$fdir")" "$*"
  printf 'note: propose feat-N or a short slug (kebab-case, at most 30 characters), and let the user choose\n'
}

# feature create <id> [title...]
# Creates the folder skeleton for a confirmed id. Idempotent.
cmd_feature_create() {
  [ $# -ge 1 ] || die "usage: pave.sh feature create <id> [title...]"
  local id="$1"; shift
  printf '%s' "$id" | grep -qE '^[A-Za-z0-9][A-Za-z0-9_-]*$' \
    || die "invalid id '$id': letters, digits, - and _ only"
  [ "${#id}" -le 30 ] || die "id '$id' is longer than 30 characters - shorten it"
  local hub; hub="$(find_hub)"
  local path="$hub/features/$id" status="new"
  [ -d "$path" ] && status="exists"
  mkdir -p "$path/contracts" "$path/tasks" "$path/artifacts"
  local title="$*"
  [ -z "$title" ] && title="$(spec_title "$path")"
  printf 'id: %s\ntitle: %s\nstatus: %s\npath: %s\n' "$id" "$title" "$status" "$path"
}

spec_title() { [ -f "$1/spec.md" ] && grep -m1 '^# ' "$1/spec.md" | sed 's/^# //'; }

next_feat() {
  local n=0 m d
  for d in "$1"/feat-*; do
    [ -d "$d" ] || continue
    m="${d##*/feat-}"
    case "$m" in (*[!0-9]*|"") continue ;; esac
    [ "$m" -gt "$n" ] && n="$m"
  done
  printf 'feat-%s' "$((n+1))"
}

# seal | check | prune-obsoleted-tasks
# Plan integrity for the session's feature. See pave-plan.py. The feature is
# taken only from SESSION_FEATURE_ID, set by the caller from the feature
# /pave:spec chose for its session - each session passes its own, so parallel
# sessions on different features never share state.
cmd_plan() {
  local op="$1" py="$2"; shift 2
  [ $# -eq 0 ] || die "$op takes no arguments. Pass the feature as SESSION_FEATURE_ID=<id> pave.sh $op"
  local id="${SESSION_FEATURE_ID:-}"
  [ -n "$id" ] || die "SESSION_FEATURE_ID is not set. Run /pave:spec <feature-id> to choose this session's feature."
  have_python || die "python3 is required for '$op'"
  local hub; hub="$(find_hub)"
  [ -d "$hub/features/$id" ] || die "SESSION_FEATURE_ID=$id: no such feature in $hub/features"
  printf 'feature: %s\n' "$id"
  python3 "$SCRIPTS/pave-plan.py" "$py" "$hub/features/$id"
}

# agent <name>
# Prints the model and effort to spawn an agent with. config.yaml wins; the
# defaults below cover hubs whose config predates an agent. Agent definitions
# carry no model or effort, so this is the only place either is decided.
# When the config has drifted from what Pave reads, a drift= line says so.
AGENTS="analyst builder explorer reviewer retriever planner"

agent_default() {
  case "$1" in
    analyst)   echo "sonnet medium" ;;
    builder)   echo "sonnet medium" ;;
    explorer)  echo "haiku low" ;;
    reviewer)  echo "sonnet low" ;;
    retriever) echo "sonnet low" ;;
    planner)   echo "opus high" ;;
    *) return 1 ;;
  esac
}

cmd_agent() {
  [ $# -eq 1 ] || die "usage: pave.sh agent <name>"
  local def; def="$(agent_default "$1")" || die "unknown agent: $1"
  local dmodel="${def% *}" deffort="${def#* }"
  local hub; hub="$(find_hub)"
  local model="" effort="" source=default

  find_config "$hub"
  if [ -n "$CONFIG" ]; then
    have_python || die "python3 is required to read $CONFIG"
    local out rc
    out="$("$SCRIPTS/$CONFIG_READER" "$CONFIG" "agents.$1")"; rc=$?
    case $rc in
      0) model="$(printf '%s\n' "$out" | sed -n 's/^model=//p')"
         effort="$(printf '%s\n' "$out" | sed -n 's/^effort=//p')" ;;
      3) ;;
      *) die "cannot read $CONFIG" ;;
    esac
  fi

  [ -n "$model" ] && source=config || model="$dmodel"
  [ -n "$effort" ] || effort="$deffort"
  printf 'model=%s\neffort=%s\nsource=%s\n' "$model" "$effort" "$source"

  local n=0
  if [ -z "$CONFIG" ]; then
    printf 'drift=no config file - run /pave:init\n'
  elif n="$(pave_config count "$CONFIG" 2>/dev/null)" && [ "${n:-0}" -gt 0 ]; then
    printf 'drift=%s config fixes pending - run /pave:init\n' "$n"
  fi
}

# config-check [--fix]
# Compares the hub's config with what this version of Pave reads: keys it no
# longer reads, agents with no entry, values it will not accept. --fix edits
# only the lines involved; /pave:init runs it, and only on "yes".
cmd_config_check() {
  local mode=check
  [ "${1:-}" = "--fix" ] && { mode=fix; shift; }
  [ $# -eq 0 ] || die "usage: pave.sh config-check [--fix]"
  local hub; hub="$(find_hub)"
  find_config "$hub"
  if [ -z "$CONFIG" ]; then
    printf 'config: none\nresult: no config file - /pave:init writes one\n'
    return 0
  fi
  have_python || die "python3 is required to read $CONFIG"
  pave_config "$mode" "$CONFIG"
}

pave_config() {
  local a defaults=""
  for a in $AGENTS; do
    defaults="$defaults $a=$(agent_default "$a" | tr ' ' :)"
  done
  PAVE_AGENT_DEFAULTS="$defaults" python3 "$SCRIPTS/pave-config.py" "$@"
}

# find_config <hub>
# Sets CONFIG to the hub's config file and CONFIG_READER to the script that
# reads it; both empty when there is none. At most one may exist.
find_config() {
  local f n=0
  CONFIG="" CONFIG_READER=""
  for f in config.toml config.yaml config.yml; do
    [ -f "$1/$f" ] || continue
    n=$((n+1)); CONFIG="$1/$f"
    case "$f" in
      *.toml) CONFIG_READER=toml-reader ;;
      *)      CONFIG_READER=yaml-reader ;;
    esac
  done
  [ "$n" -le 1 ] || die "more than one config file in $1. Keep exactly one of config.toml, config.yaml, config.yml."
}

case "${1:-}" in
  add) shift; cmd_add "$@" ;;
  stale) shift; cmd_stale "$@" ;;
  feature)
    case "${2:-}" in
      propose) shift 2; cmd_feature_propose "$@" ;;
      create)  shift 2; cmd_feature_create "$@" ;;
      *) die "usage: pave.sh feature <propose|create> ..." ;;
    esac ;;
  seal)  shift; cmd_plan seal seal "$@" ;;
  check) shift; cmd_plan check check "$@" ;;
  prune-obsoleted-tasks) shift; cmd_plan prune-obsoleted-tasks prune "$@" ;;
  agent) shift; cmd_agent "$@" ;;
  config-check) shift; cmd_config_check "$@" ;;
  ""|-h|--help) sed -n '4,20p' "${BASH_SOURCE[0]}" | sed 's/^# *//' ;;
  *) die "unknown command: $1" ;;
esac
