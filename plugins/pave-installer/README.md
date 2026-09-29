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
