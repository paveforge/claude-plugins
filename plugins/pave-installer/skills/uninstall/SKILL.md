---
name: uninstall
description: Remove a Pave adapter installed by Pave Installer without touching any Pave hub. Use `/pave-installer:uninstall codex` or `/pave-installer:uninstall codex project`.
argument-hint: "codex [user|project]"
allowed-tools: Bash
---

# Pave Installer — uninstall a host adapter

Remove only files recorded in Pave's installation manifest. Never remove a
Pave hub, its feature files, knowledge, reports or any service repository.

Accept exactly:

- `codex` or `codex user` — uninstall the current user's adapter
- `codex project` — uninstall the adapter from the current project

For anything else, stop and show those choices. Do not guess a host or scope.

Set `scope` from the argument, defaulting to `user`. First show the complete
plan. Resolve the marketplace and `--plugin-dir` layouts:

```bash
installer="${CLAUDE_PLUGIN_ROOT}/plugins/pave-installer/scripts/pave-host.py"
[ -f "$installer" ] || installer="${CLAUDE_PLUGIN_ROOT}/scripts/pave-host.py"
python3 "$installer" plan-uninstall codex --scope <scope>
```

Pass its output on. `preserve` means the file changed after Pave installed it
and will remain. Then run the uninstall without asking another question —
invoking this skill is the user's instruction to uninstall:

```bash
python3 "$installer" uninstall codex --scope <scope>
```

Exit 2 is a partial uninstall: name every preserved path and say the manifest
was retained so a later uninstall can finish. Any other non-zero exit is a
failure; pass the error on. On success, say the adapter was removed. Never
suggest deleting preserved files automatically.
