# AGENTS.md

Rules for any agent changing this repository. Read this before you propose or
write a change to Pave. It says what Pave believes; the README says how it
behaves. Where the code and this file disagree, this file is the intent and
the code is the bug.

Not to be confused with `plugins/pave/templates/hub-AGENTS.md`, which is the
rulebook a Pave user keeps in their own hub.

## Pave's principles

### Two sources of truth, both files

- `spec.md` - what the feature must do. The user owns it and writes it with
  `/pave:spec`.
- `plan.md` and its task documents - how. The planner writes them with
  `/pave:plan`.

Nothing else is a source of truth: not a conversation, not a report, not a
checkbox, not a commit.

### Hashes hold them together, never a VCS

Each step checks the content hash of what it depends on and refuses when it
does not match: build and review refuse a plan that is out of sync with the
spec, or a task edited outside the plan. Whether a repo uses git, another VCS
or nothing at all is the user's choice. Pave must work without one and must
never rely on one to decide anything.

### The planner knows the code

Planning is the most important step and gets the strongest model. Before it
writes a plan, the planner must know what the code does **today** - the
knowledge base tells it where to look, the code tells it what is true. A task
is concrete because the planner looked: its items name real files, real types
and current values. A re-plan is a plan: the spec and the current code are all
it needs, never what a task used to say.

### The builder and reviewer are cheap and simple

- **The builder does what the task document says.** For each item it checks
  the code the item names, acts only if the item does not hold yet, and ticks
  it. It does not decide, infer or search beyond what it was told. If the
  document does not say, the builder stops and reports.
- **The reviewer checks what the task document says**, item by item, against
  the code.

Neither needs to know why a task exists, what it replaced, or what kind of
work it is.

### A gap is the planner's to fix

When something is missed - a leftover, an underspecified item, a behaviour in
a place no task names - the fix goes in the planner. Never compensate
downstream by giving the builder or reviewer more judgement, more modes or
more to search. Cheap agents doing expensive thinking is the failure this
design exists to avoid.

### No new concept when an existing one will do

A revert is a task. A removal is an item. Before adding a status, a mode, a
kind, a field or a file, show that nothing existing can carry it. Every
concept a builder must understand makes it less reliable.

## Working in this repo

- Pave lives in `plugins/pave/`: `skills/` (the commands), `agents/` (the
  subagents they spawn), `templates/`, `scripts/`, `tests/`.
- Tests: `python3 -m pytest plugins/pave/tests`. Shell: `bash -n` and
  `shellcheck --severity=warning` on `plugins/pave/scripts/pave.sh`. CI runs
  both on Python 3.9 and 3.12, with and without PyYAML.
- Skills, agents and templates are prompts. Change them with the same care as
  code: one rule in one place, and every file that restates it updated
  together.
