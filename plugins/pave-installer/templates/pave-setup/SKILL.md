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
  the user owns it. `plan.md` says how; the planner writes it. Nothing else is
  a source of truth: not a conversation, a report, a checkbox, a commit - and
  not the task documents, the seal, the approved-spec snapshot or the
  contract copies either. Those are disposable and are rebuilt from
  `spec.md`, `plan.md` and the code; losing one costs time, never
  correctness.
- **Every change goes into `plan.md` first.** Task documents are projections
  of the plan. A change that lives only in a task is lost when the tasks are
  rebuilt.
- **Hashes hold them together, never a VCS.** `plan.md` records the hash of
  the spec it answers; a disposable seal records the hash of every task. Each
  step checks what it depends on and refuses when it does not match. A repo
  may use git, another VCS or none; Pave never relies on one to decide
  anything.
- **The planner is the mastermind.** It is the only role that thinks: before
  it writes a plan it reads what the code does today, and it decides every
  place a change lives, every field of every interface between services, and
  every ordering between tasks (`depends_on`). Nothing after it can rescue a
  poor plan, so the strongest model is recommended for it - recommended,
  because the model is the user's choice in the hub's config.
- **The builder and reviewer are cheap and simple.** Each reads only its one
  task document - never `plan.md`, the spec or another task. The builder
  writes code, item by item, and runs nothing: no build, test, lint, codegen
  or commit, so several builders can share one repo. The reviewer checks the
  task document item by item against the code. Neither decides, infers or
  searches beyond what it was told; each stops and reports when the document
  does not say.
- **Build executes the plan's ordering and review checks in two gates.**
  Build runs every task whose `depends_on` are done at once and decides
  nothing else, then commits at the end. Review first checks each task
  against the code, then runs each service's own build, test and lint, and
  sorts every failure to the task that names the file - or reports it as a
  gap in the plan.
- **A gap is the planner's to fix.** Never compensate by giving the builder or
  reviewer more judgement, more modes or more to search.
- **The caller's choice is final.** An argument the user gives a command, or
  an answer to a question, is done exactly. Pave recommends, warns and
  explains, but never overrides, escalates or second-guesses it. The only
  exception is a choice that needs information which does not exist, and
  then Pave says so.
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
| Scripts | `scripts/` | `pave.sh` and its helpers do the deterministic work: finding the hub, registering services, hashing knowledge, sealing and checking plans, finding which acceptance criteria changed (`diff`), finding tasks that share a file without an ordering (`overlaps`), sorting a failing file to its task (`attribute`), copying built contracts (`contracts`), looking up agents, checking config. |
| Templates, reference | `templates/`, `reference/` | Files the skills copy into a hub or read. `templates/config.yaml` lists every config key. |

## 3. Convert

Put everything you produce under `@@HOST_HOME@@` or `@@SKILLS_DIR@@`:

- one skill per source skill, named `pave-<name>`, in `@@SKILLS_DIR@@`
- one agent per source agent, named `pave-<role>`, where @@HOST_TITLE@@ keeps
  user-wide agents
- everything the skills need at run time (scripts, templates, reference and
  any other file they read) under `@@HOST_HOME@@/pave/`
@@HOST_NOTES@@
Pave is installed user-wide only. Never write into a hub or a service repo
during setup, into `@@HOST_HOME@@/pave-installer/`, or into this `pave-setup`
skill.

The result must hold all of this. Check each point before you report.

1. **Self-contained.** Nothing you produce refers to the source `path`. It may be a
   temporary clone, or belong to Claude Code and change with its next update.
2. **Every skill** follows its source step by step and keeps every refusal,
   stop, approval gate, hash check and question it asks the user. Where a
   source skill takes an argument (its `argument-hint` line), the converted
   skill accepts the same values and passes them on unchanged - `pave-plan`
   takes `quick`, `scoped` or `full`, and that level is final. Where the
   source pauses an agent to ask the user and then resumes it - `pave-plan`
   asks the level after the planner's verdict - keep the pause; if
   @@HOST_TITLE@@ cannot resume an agent, spawn a fresh one with the user's
   answer, as the source does when resuming is not possible.
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
   - Claude Code's `/compact` → @@HOST_TITLE@@'s own command that compacts
     or summarises the conversation, given the same instruction to keep the
     brief. If that command takes no instruction, `pave-compact` tells the
     user to run it as it is, then to run `pave-spec <id>` if the summary
     lost the `Working on` line. If it has none, `pave-compact` still writes
     the brief, then tells the user to start a new session and run
     `pave-spec <id>` there
   - `.claude/settings.json` (`additionalDirectories`) and `CLAUDE.md` →
     @@HOST_TITLE@@'s own mechanism for folder access and hub instructions,
     written under the hub's `.@@HOST@@/` folder if anywhere
8. **Re-runs replace the previous run.** Replace what an earlier setup created:
   - every `pave-*` skill except `pave-setup`
   - every `pave-*` agent, in every file @@HOST_TITLE@@ keeps it in
   - `@@HOST_HOME@@/pave/`

   Ask the user before replacing a file they edited.

## 4. Report

Say:

- which Pave version you built and from which source
- what you created, and where - for each agent, every file it was written to
- anything you could not carry over, and why
- what the user does next: start a new session if the skills do not appear,
  then run `pave-init` once in each hub and fill in the models and efforts
  in `config.@@HOST@@.yaml`
