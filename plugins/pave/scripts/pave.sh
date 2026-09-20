#!/usr/bin/env bash
# Pave helper. Deterministic hub operations that need no model.
#
#   pave.sh add <folder>...    register service folders with the hub
#   pave.sh stale [service]     report what needs discovery or analysis
#   pave.sh feature <args...>   resolve a feature id and create its folder
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
  local here; here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  python3 "$here/pave-stale.py" "$hub" "$@"
}

# feature <ticket-id|description...>
# Resolves the feature id, creates the folder skeleton, reports both.
# The id is a handle, never a summary: a ticket reference if one was given,
# otherwise feat-N. A kebab-cased sentence is not something anyone types twice.
cmd_feature() {
  [ $# -ge 1 ] || die "usage: pave.sh feature <ticket-id|description...>"
  local hub; hub="$(find_hub)"
  local fdir="$hub/features"
  mkdir -p "$fdir"

  local id title
  # A ticket reference: letters, hyphen, digits. Case preserved as typed.
  if printf '%s' "$1" | grep -qE '^[A-Za-z][A-Za-z0-9_]*-[0-9]+$'; then
    id="$1"; shift; title="$*"
  else
    local n=0 m
    for d in "$fdir"/feat-*; do
      [ -d "$d" ] || continue
      m="${d##*/feat-}"
      case "$m" in (*[!0-9]*|"") continue ;; esac
      [ "$m" -gt "$n" ] && n="$m"
    done
    id="feat-$((n+1))"; title="$*"
  fi

  local path="$fdir/$id" status="new"
  [ -d "$path" ] && status="exists"

  # Re-design: recover the title from the existing spec rather than losing it.
  if [ "$status" = "exists" ] && [ -z "$title" ] && [ -f "$path/spec.md" ]; then
    title="$(grep -m1 '^# ' "$path/spec.md" 2>/dev/null | sed 's/^# //')"
  fi

  mkdir -p "$path/contracts" "$path/tasks" "$path/artifacts"

  printf 'id: %s\n' "$id"
  printf 'title: %s\n' "$title"
  printf 'status: %s\n' "$status"
  printf 'path: %s\n' "$path"
  [ -z "$title" ] && printf 'note: no description given - ask what this feature is\n'
  [ "$status" = "exists" ] && printf 'note: re-design - say so before re-deriving\n'
  return 0
}

case "${1:-}" in
  add) shift; cmd_add "$@" ;;
  stale) shift; cmd_stale "$@" ;;
  feature) shift; cmd_feature "$@" ;;
  ""|-h|--help) printf 'usage: pave.sh add <folder>...\n       pave.sh stale [service]\n       pave.sh feature <ticket-id|description...>\n' ;;
  *) die "unknown command: $1" ;;
esac
