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
  `/pave:spec`. Its acceptance criteria are the contract; the prose around
  them is for people.
- `plan.md` - how. The planner writes it with `/pave:plan`.

Nothing else is a source of truth: not a conversation, not a report, not a
checkbox, not a commit - and not the task documents, the contracts, the
approved-spec snapshot, the seal or the knowledge base either. Those are
disposable: each can be rebuilt from `spec.md`, `plan.md` and the code. A
hub could keep only those two files per feature under version control and
lose nothing that matters.

So:

- **Every change goes into `plan.md` first.** A task is a projection of the
  plan. A change written only into a task is lost the next time the tasks are
  rebuilt, and is a defect.
- **`plan.md` is sufficient on its own.** Everything a task needs - including
  the exact interfaces between services - is in it, so the tasks can be
  written again from it alone.
- **Losing a disposable file costs time, never correctness.** The remedy is to
  rebuild it from the truth: never ask anyone to vouch for it, and never add
  machinery to work around its absence. Without the approved-spec snapshot a
  re-plan cannot know what changed, so it re-plans in full.

### Hashes hold them together, never a VCS

`plan.md` records the hash of the spec it was approved against; that binds
the two truths. A disposable seal records the hash of every task the plan was
projected into. Build and review refuse a plan out of sync with its spec, or a
task that differs from its seal. A task that cannot be vouched for is
rebuilt from the plan, never trusted.

Whether a repo uses git, another VCS or nothing at all is the user's choice.
Pave must work without one and must never rely on one to decide anything.

### The planner is the mastermind

Every decision that needs thinking is the planner's, so a precise plan is
what makes everything downstream work. Nothing after planning can rescue a
poor plan: build and review only execute and check it. That is why the
strongest model is recommended for the planner - recommended, because the
model is the user's choice in the hub's config.

- **It knows the code.** Before it writes a plan, the planner must know what
  the code does **today** - the knowledge base tells it where to look, the
  code tells it what is true. A task is concrete because the planner looked:
  its items name real files, real types and current values. A re-plan is a
  plan: the spec and the current code are all it needs, never what a task
  used to say.
- **It owns every ordering.** `depends_on` is the planner's tool to keep two
  tasks that touch the same place, or need each other's result, from running
  together. It is not a relation between services: tasks in one service with
  nothing between them run in parallel, and tasks in two services wait for
  each other when the planner says so. Build runs the graph it is given and
  decides nothing.
- **It puts everything a task needs into the task.** Builder and reviewer
  never read `plan.md`. An interface, a failure case, a place the behaviour
  lives: if a task does not say it, nobody downstream will.

### The builder and reviewer are cheap and simple

Each reads only its task document - never the plan, the spec or another task.

- **The builder writes code.** For each item it checks the code the item
  names, acts only if the item does not hold yet, and ticks it. It runs
  nothing - no build, test, lint or codegen - so builders never collide in a
  shared repo. It does not decide, infer or search beyond what it was told.
  If the document does not say, the builder stops and reports.
- **Review checks the result, in two gates.** First, each task's items
  against the code. Then the services' own build, test and lint. A failure in
  a file one task names sends that task back to the builder; a failure the
  tasks do not explain is a gap in the plan, and review says so.

Neither needs to know why a task exists, what it replaced, or what kind of
work it is.

### A gap is the planner's to fix

When something is missed - a leftover, an underspecified item, a behaviour in
a place no task names - the fix goes in the planner. Never compensate
downstream by giving the builder or reviewer more judgement, more modes or
more to search. Cheap agents doing expensive thinking is the failure this
design exists to avoid.

### The caller's choice is final

Pave's commands are tools. When the user chooses - an argument such as
`/pave:plan quick`, or an answer to a question - Pave does exactly that. It
recommends, warns and explains, but it never overrides, escalates or
second-guesses the choice. A user who chose wrong learns from the result.

The only exception is a choice that needs information which does not exist -
a quick re-plan with no approved spec to compare against. Then Pave says
plainly what is missing and what it does instead.

### The config template is the only source of truth for config

`plugins/pave/templates/config.yaml` lists every key Pave reads, with the
value a new hub starts with. Adding, renaming or removing an agent or a
setting changes the template in the same change as the code that reads it.
Nothing else holds a default: not `pave.sh`, not a skill, not an agent. A
command that needs a key the hub's config lacks stops and points to
`/pave:init`, which compares the config with the template (`pave.sh
config-check`) and brings it up to date. A key missing from the template is
a key Pave cannot read.

Name a config key in a prompt in full, as `` `section.key` `` -
`` `execution.max_parallel` ``, never `` `max_parallel` `` or "the parallel limit".
A test checks every key written that way against the template; a key written
any other way is invisible to it.

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
