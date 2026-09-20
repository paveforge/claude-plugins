#!/usr/bin/env bash
# Pave helper. Deterministic hub operations that need no model.
#
#   pave.sh add <folder>...    register service folders with the hub
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

case "${1:-}" in
  add) shift; cmd_add "$@" ;;
  ""|-h|--help) printf 'usage: pave.sh add <folder>...\n' ;;
  *) die "unknown command: $1" ;;
esac
