---
name: install
description: Install or update Pave for another supported coding-agent host. Use `/pave:install codex` for a user installation or `/pave:install codex project` for the current project.
argument-hint: "codex [user|project]"
allowed-tools: Bash
---

# Pave — install a host adapter

Install the Pave adapter for the named coding-agent host. This manages agent
integration only; it never creates or changes a Pave hub.

Accept exactly:

- `codex` or `codex user` — install for the current user
- `codex project` — install for the current project

For anything else, stop and show those choices. Do not guess a host or scope.

Set `scope` from the argument, defaulting to `user`. First show the complete
plan:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/pave-host.py plan-install codex --scope <scope>
```

Pass its output on. A `conflict` means an existing file was not written by the
previous Pave installation, or was edited afterwards. The installer preserves
it. Then run the installation without asking another question — invoking this
skill is the user's instruction to install:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}"/scripts/pave-host.py install codex --scope <scope>
```

Exit 2 means the compatible files were installed but one or more conflicts
were preserved. Name those paths. Any other non-zero exit is a failure; pass
the error on and do not claim installation succeeded.

On success, say that Codex detects skill changes automatically, but a new
session may be needed if the skills do not appear. The explicit Codex commands
are `$pave-init`, `$pave-add`, `$pave-analyse`, `$pave-spec`, `$pave-plan`,
`$pave-build`, `$pave-review`, `$pave-learn`, `$pave-query`, `$pave-visualize`
and `$pave-help`. In each existing hub, run `$pave-init` once to create that
host's separate `config.codex.yaml` (or `.yml` / `.toml`) before using the
workflow there.
