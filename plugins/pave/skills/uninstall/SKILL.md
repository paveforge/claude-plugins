---
name: uninstall
description: Remove a Pave adapter previously installed for another coding-agent host without touching any Pave hub. Use `/pave:uninstall codex` or `/pave:uninstall codex project`.
argument-hint: "codex [user|project]"
allowed-tools: Bash
---

# Pave — uninstall a host adapter

Remove only files recorded in Pave's installation manifest. Never remove a
Pave hub, its feature files, knowledge, reports or any service repository.

Accept exactly:

- `codex` or `codex user` — uninstall the current user's adapter
- `codex project` — uninstall the adapter from the current project

For anything else, stop and show those choices. Do not guess a host or scope.

Set `scope` from the argument, defaulting to `user`. First show the complete
plan:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/pave-host.py plan-uninstall codex --scope <scope>
```

Pass its output on. `preserve` means the file changed after Pave installed it
and will remain. Then run the uninstall without asking another question —
invoking this skill is the user's instruction to uninstall:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/pave-host.py uninstall codex --scope <scope>
```

Exit 2 is a partial uninstall: name every preserved path and say the manifest
was retained so a later uninstall can finish. Any other non-zero exit is a
failure; pass the error on. On success, say the adapter was removed. Never
suggest deleting preserved files automatically.
