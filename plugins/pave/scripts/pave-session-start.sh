#!/usr/bin/env bash
# Pave's SessionStart hook. Exports the Claude session's id as
# PAVE_SESSION_ID for the Bash calls that follow, so pave.sh can record the
# session's feature in <hub>/.pave-sessions/<id> and find it again after a
# compaction. See resolve_feature in pave.sh.
#
# Claude Code passes the hook's input as JSON on stdin and the file to write
# `export` lines into as CLAUDE_ENV_FILE. When either is missing, or the id is
# not safe as a file name, it does nothing: a session never fails to start
# because of Pave, and pave.sh then works from SESSION_FEATURE_ID alone.
set -uo pipefail

[ -n "${CLAUDE_ENV_FILE:-}" ] || exit 0
input="$(cat)"

if command -v python3 >/dev/null 2>&1; then
  id="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    print(json.load(sys.stdin).get("session_id") or "")
except Exception:
    pass
' 2>/dev/null)"
else
  id="$(printf '%s' "$input" | tr -d '\n' \
    | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
fi

printf '%s' "$id" | grep -qE '^[A-Za-z0-9_-]+$' || exit 0
printf 'export PAVE_SESSION_ID=%s\n' "$id" >> "$CLAUDE_ENV_FILE"
exit 0
