# Pave Installer

Pave Installer adapts the Claude-native Pave plugin for other agentic coding
platforms without changing `plugins/pave`.

Supported host:

- Codex, at user or project scope

Claude Code commands:

```text
/pave-installer:install codex
/pave-installer:install codex project
/pave-installer:uninstall codex
/pave-installer:uninstall codex project
```

The installer reads the Pave source bundled in the same marketplace checkout,
generates host-native skills and agents, and records every installed file by
hash. Updates replace only unchanged managed files; uninstall preserves files
the user edited after installation.

Host-specific templates and transformations live only in this plugin. Pave
remains the authoritative workflow source and stays Claude-specific.

Generated Codex skills read each role's model and effort from the hub's
`config.codex.*` immediately before a spawn and require both as explicit
spawn settings. If the active client cannot set them, the skill instructs
Codex to stop instead of using the parent model.
The installed custom agent TOMLs intentionally contain no model defaults,
so changing the hub config takes effect on the next spawn.

`$pave-add` records service directories in `workspace.yaml` but cannot grant
Codex permission to write to them. It prints a
`codex --cd <hub> --add-dir <service-root>` command for a new CLI session and the paths to add to writable
roots in the app or IDE. `$pave-build` requires the agent to confirm access
before it starts builders.
Subagents inherit the parent session's permissions.
In a hosted environment, the service repos must also exist in that environment;
`--add-dir` does not transfer local files into it.
