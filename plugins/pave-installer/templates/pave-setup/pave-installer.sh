#!/usr/bin/env bash
# pave-installer.sh - finds the Pave source that pave-setup converts.
#
#   pave-installer.sh locate          print where the Pave source is
#   pave-installer.sh cleanup <path>  delete a folder that locate cloned
#
# Written by Pave Installer. The values below were filled in when it was
# installed; reinstall rather than edit them.
set -euo pipefail

PAVE_LOCAL=@@LOCAL@@
PAVE_VERSION=@@VERSION@@
PAVE_REPOSITORY=@@REPOSITORY@@
PAVE_COMMIT=@@COMMIT@@
PAVE_REINSTALL=@@REINSTALL@@

# Left in every folder locate clones, so cleanup deletes nothing else.
MARKER=".pave-installer-clone"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

missing() {
  die "Pave $PAVE_VERSION is not at $PAVE_LOCAL and could not be cloned from $PAVE_REPOSITORY: $1. Run $PAVE_REINSTALL in Claude Code again."
}

# version_of <pave folder> - the version its plugin.json declares, or nothing.
version_of() {
  local manifest="$1/.claude-plugin/plugin.json"
  [ -f "$manifest" ] || return 0
  sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$manifest" | head -n 1
}

report() {
  printf 'source=%s\nversion=%s\npath=%s\n' "$1" "$PAVE_VERSION" "$2"
}

# fetch <folder> - clone the pinned commit, or the default branch without one.
fetch() {
  if [ -n "$PAVE_COMMIT" ]; then
    git init --quiet "$1" \
      && git -C "$1" fetch --quiet --depth 1 "$PAVE_REPOSITORY" "$PAVE_COMMIT" \
      && git -C "$1" -c advice.detachedHead=false checkout --quiet FETCH_HEAD
  else
    git clone --quiet --depth 1 "$PAVE_REPOSITORY" "$1"
  fi
}

cmd_locate() {
  [ $# -eq 0 ] || die "usage: pave-installer.sh locate"
  if [ "$(version_of "$PAVE_LOCAL")" = "$PAVE_VERSION" ]; then
    report local "$PAVE_LOCAL"
    return 0
  fi
  printf 'Pave %s is not at %s; cloning %s\n' "$PAVE_VERSION" "$PAVE_LOCAL" "$PAVE_REPOSITORY" >&2
  command -v git >/dev/null 2>&1 || missing "git is not installed"

  local root
  root="$(mktemp -d "${TMPDIR:-/tmp}/pave-source.XXXXXX")" || missing "no temporary folder"
  : > "$root/$MARKER"
  if ! fetch "$root/repo" >&2; then
    rm -rf "$root"
    missing "git could not fetch it"
  fi
  local found
  found="$(version_of "$root/repo/plugins/pave")"
  if [ "$found" != "$PAVE_VERSION" ]; then
    rm -rf "$root"
    missing "the clone holds version ${found:-unknown}"
  fi
  report clone "$root/repo/plugins/pave"
}

cmd_cleanup() {
  [ $# -eq 1 ] || die "usage: pave-installer.sh cleanup <path printed by locate>"
  local root="${1%/}"
  root="${root%/repo/plugins/pave}"
  [ -f "$root/$MARKER" ] || die "refusing to delete $1: locate did not clone it"
  rm -rf "$root"
  printf 'removed %s\n' "$root"
}

case "${1:-}" in
  locate) shift; cmd_locate "$@" ;;
  cleanup) shift; cmd_cleanup "$@" ;;
  *) die "usage: pave-installer.sh locate | cleanup <path>" ;;
esac
