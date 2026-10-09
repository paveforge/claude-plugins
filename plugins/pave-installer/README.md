# Pave Installer

Pave Installer brings Pave to other agentic coding platforms without changing
`plugins/pave`. It does not convert Pave itself. It installs one skill,
`pave-setup`, and the platform builds its own Pave from it.

Supported hosts, installed for the current user only:

- Codex: `~/.agents/skills/pave-setup/`
- Kiro: `~/.kiro/skills/pave-setup/`

Claude Code commands:

```text
/pave-installer:install codex
/pave-installer:install kiro
/pave-installer:uninstall codex
/pave-installer:uninstall kiro
```

## What pave-setup does

Run it in the host: `$pave-setup` in Codex, `/pave-setup` in Kiro. It explains
Pave's principles and its parts (skills, agents, flow, tools, scripts and
config), then has the host convert the Pave source into its own skills and
agents. The conversion is the host's to decide; `pave-setup` states what must
hold afterwards, for example:

- every skill and agent is carried over
- read-only roles cannot write
- the orchestrator starts each agent with the model and effort from the hub's
  `config.<host>.yaml`, and stops rather than guess when they are missing
- the hub stays independent of the platform
- in Kiro, every agent is written twice: a JSON file for Kiro CLI and a
  Markdown file for the Kiro IDE, which cannot spawn an agent from JSON

The result lives under the host's own folder (`~/.codex`, `~/.kiro`) and does
not depend on the source after setup. Run `pave-setup` again after every
update, or whenever you want to rebuild Pave.

## Where the source comes from

`pave-setup/pave-installer.sh locate` prints the folder to read Pave from:

1. The Pave plugin in the same marketplace download as this installer, if it
   is still there and holds the installed version.
2. Otherwise a shallow HTTPS clone of the repository, at the commit that was
   installed, in a temporary folder. `pave-installer.sh cleanup <path>`
   deletes it afterwards, and refuses any folder it did not clone.

Both are fixed when you install: the local path, the Pave version, the
repository's HTTPS URL (from the git remote, or from `plugin.json`) and the
commit. After a Claude Code plugin update, run `/pave-installer:install
<host>` again.

## Updates and removal

Every installed file is recorded by hash in `<host home>/pave-installer/install.json`.
An update replaces only files that are unchanged since they were installed;
uninstall removes only those, and keeps any the user edited. Uninstall removes
`pave-setup` only. The Pave the host built belongs to the host.

Pave Installer 0.1 generated Codex skills, agents and a runtime itself. The
next `install codex` or `uninstall codex` removes those files, keeping any the
user edited.
