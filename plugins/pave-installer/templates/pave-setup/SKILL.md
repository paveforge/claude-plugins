---
name: pave-setup
description: Build Pave for @@HOST_TITLE@@ from the Pave plugin written for Claude Code, or rebuild it. Explains Pave's principles and parts, finds its source, and converts it into native @@HOST_TITLE@@ skills and agents. Run after installing Pave Installer, after every update, and whenever you want to rebuild Pave.
---

# Pave setup for @@HOST_TITLE@@

Pave is written as a Claude Code plugin. This skill does not contain Pave. It
tells you, the @@HOST_TITLE@@ agent, what Pave is, where its source is, and what
must hold once you have turned it into skills and agents that work natively in
@@HOST_TITLE@@. How you convert it is yours to decide. Each run may produce
different files; Pave's principles, parts and behaviour must stay the same.

## 1. Find the source

```bash
bash "@@SCRIPT@@" locate
```

It prints `source=`, `version=` and `path=`. Read Pave from that `path` only:
never from memory, another copy or the web. If the script fails, stop and pass
its message on; do not look for Pave anywhere else.

When it prints `source=clone`, the folder is temporary. Delete it once
setup is finished, whether it succeeded or not:

```bash
bash "@@SCRIPT@@" cleanup <path>
```

## 2. Understand Pave before you change anything

Read every file under `skills/` and `agents/`, then `templates/` and
`reference/`, and skim `scripts/`. Pave is a mindset first; the files carry it
out.

### The mindset

- **Two sources of truth, both files.** `spec.md` says what a feature must do;
  the user owns it. `plan.md` and its task documents say how; the planner
  writes them. Nothing else is a source of truth: not a conversation, a
  report, a checkbox or a commit.
- **Hashes hold them together, never a VCS.** Each step checks the content
  hash of what it depends on and refuses when it does not match. A repo may
  use git, another VCS or none; Pave never relies on one to decide anything.
- **The planner knows the code.** Planning gets the strongest model. Before it
  writes a plan it reads what the code does today, so every task names real
  files, types and values.
- **The builder and reviewer are cheap and simple.** The builder does what its
  task document says, item by item, and stops and reports when the document
  does not say. The reviewer checks the task document item by item against
  the code. Neither decides, infers or searches beyond what it was told.
- **A gap is the planner's to fix.** Never compensate by giving the builder or
  reviewer more judgement, more modes or more to search.
- **The config template is the only source of truth for config.** Every
  setting comes from the hub's config file. Nothing else holds a default. A
  missing or empty setting stops the command and points to init; never guess.
- **No new concept when an existing one will do.**
- **The hub is independent of any coding platform.** It holds Pave's files;
  the only platform files it may hold are that platform's own settings, under
  its own folder.

### The parts

| Part | Where in the source | What it is |
|---|---|---|
| Skills | `skills/<name>/SKILL.md`, plus any other file in that folder | The commands a user runs. Flow: `init` → `add` → `analyse` → `spec` → `plan` → `build` → `review` → `learn`; `query`, `visualize`, `compact` and `help` at any time. |
| Agents | `agents/<role>.md` | The roles skills spawn: `explorer`, `analyst`, `planner`, `builder`, `reviewer`, `retriever`. The frontmatter `tools` line lists what the role may use; the body is its instructions. |
| Tools | `allowed-tools` and `tools` lines | Claude Code names: `Read` reads a file, `Glob` finds files by name, `Grep` searches inside files, `Write` creates a file, `Edit` changes part of a file, `Bash` runs a command, `Agent` spawns a subagent, `SendMessage` resumes one. |
| Scripts | `scripts/` | `pave.sh` and its helpers do the deterministic work: finding the hub, registering services, hashing, sealing and checking plans, looking up agents, checking config. |
| Templates, reference | `templates/`, `reference/` | Files the skills copy into a hub or read. `templates/config.yaml` lists every config key. |

## 3. Convert

Put everything you produce under `@@HOST_HOME@@` or `@@SKILLS_DIR@@`:

- one skill per source skill, named `pave-<name>`, in `@@SKILLS_DIR@@`
- one agent per source agent, named `pave-<role>`, where @@HOST_TITLE@@ keeps
  user-wide agents
- everything the skills need at run time (scripts, templates, reference and
  any other file they read) under `@@HOST_HOME@@/pave/`

Pave is installed user-wide only. Never write into a hub or a service repo
during setup, into `@@HOST_HOME@@/pave-installer/`, or into this `pave-setup`
skill.

The result must hold all of this. Check each point before you report.

1. **Self-contained.** Nothing you produce refers to the source `path`. It may be a
   temporary clone, or belong to Claude Code and change with its next update.
2. **Every skill** follows its source step by step and keeps every refusal,
   stop, approval gate and hash check.
3. **Every agent's** instructions are its source body, unchanged in meaning,
   with the tools its `tools` line allows. `explorer`, `retriever` and
   `reviewer` read only: they must not be able to write files or run
   commands. Use @@HOST_TITLE@@'s own tool restrictions to enforce that
   wherever it has them.
4. **The scripts decide.** Skills call Pave's scripts wherever the source
   does. Never restate a script's logic in prose. Change a script only where
   it touches Claude Code itself.
5. **The orchestrator picks the model, never the agent.** Before every spawn,
   the skill reads that role's `model` and `effort` from the hub's
   `config.@@HOST@@.yaml` (or `.yml` or `.toml`; exactly one) and passes both to
   the spawn. That file has exactly the keys of `templates/config.yaml`, with
   model names @@HOST_TITLE@@ accepts. The source reads `config.yaml` through
   `pave.sh agent` and `pave.sh config-check`; make those read
   `config.@@HOST@@.*` without changing what they decide. Stop and tell the
   user, never guess, inherit the parent's model or use a default, when:
   - the file is missing, or there is more than one
   - the role has no entry, or its model or effort is empty
   - @@HOST_TITLE@@ cannot set the model for a spawn

   If only the effort cannot be set, say that the session's effort applies.
6. **Init writes the host config.** The converted `init` creates
   `config.@@HOST@@.yaml`, not `config.yaml`. It uses a template with the same
   keys as `templates/config.yaml` and every agent's `model` and `effort`
   empty, with a comment saying Pave will not run a role until the user fills
   them in. An existing `config.@@HOST@@.*` is left as it is, as the source
   does for `config.yaml`.
7. **Replace what only Claude Code has; never silently drop it.** If
   @@HOST_TITLE@@ has no equivalent, the skill tells the user exactly what to do
   by hand.
   - `${CLAUDE_PLUGIN_ROOT}` → your run-time folder
   - `/pave:<name>` → how @@HOST_TITLE@@ invokes `pave-<name>`
   - `$ARGUMENTS` → how @@HOST_TITLE@@ passes arguments
   - the `Agent` and `SendMessage` tools → @@HOST_TITLE@@'s way to spawn and
     resume, or the fallback the source describes when resuming is not
     possible
   - Claude's Artifact tool → the local HTML file the source falls back to
   - `.claude/settings.json` (`additionalDirectories`) and `CLAUDE.md` →
     @@HOST_TITLE@@'s own mechanism for folder access and hub instructions,
     written under the hub's `.@@HOST@@/` folder if anywhere
8. **Re-runs replace the previous run.** Replace what an earlier setup created:
   - every `pave-*` skill except `pave-setup`
   - every `pave-*` agent
   - `@@HOST_HOME@@/pave/`

   Ask the user before replacing a file they edited.

## 4. Report

Say:

- which Pave version you built and from which source
- what you created, and where
- anything you could not carry over, and why
- what the user does next: start a new session if the skills do not appear,
  then run `pave-init` once in each hub and fill in the models and efforts
  in `config.@@HOST@@.yaml`
