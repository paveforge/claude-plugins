# claude-plugins

Claude Code plugins for paveforge.

Install Pave for Claude Code:

```
/plugin marketplace add paveforge/claude-plugins
/plugin install pave@paveforge
```

Install the separate Pave Installer when you want to use Pave on another
agentic coding platform (Codex or Kiro):

```
/plugin install pave-installer@paveforge
/pave-installer:install codex    # or: kiro
```

This installs one skill, `pave-setup`, for the current user. Run it in the
platform (`$pave-setup` in Codex, `/pave-setup` in Kiro): it explains Pave and
where its source is, and the platform builds its own Pave from it. The Pave
plugin itself stays Claude-specific. Remove the skill with
`/pave-installer:uninstall codex` (or `kiro`).

---

# Pave

**Specify a feature once, plan it across every service it touches, fix the
interfaces between them, then build in parallel.**

When a feature spans several services, the usual approach is to go service by
service, designing each in isolation. The cross-service picture — which
services are affected, what the interfaces between them are, what order things
ship in — never exists anywhere except in someone's head.

Pave inverts that. A **hub** folder sits beside your service repos and holds
the planning. A feature is specified and planned once, across all of it, with
every interface between services fixed field by field before any
implementation starts. That is what makes the next step safe: the services
stop depending on each other's in-flight code, so they can be built at the
same time by separate agents, each working from a self-contained task
document.

**Two files are the truth: `spec.md` (what) and `plan.md` (how).** Everything
else Pave writes for a feature - the task documents, the seal, the contract
copies, the reports - is rebuilt from those two and the code. A hub can keep
only those two files per feature and lose nothing that matters.

**The planner thinks; everything after it executes.** The planner decides
every place a change lives, every field of every interface and every
ordering, and writes it into task documents. Builders write code from their
one task and run nothing; reviewers check one task against the code. That is
why the planner gets the strongest model you have, and the rest stay cheap.

It is stack-agnostic. Build commands are discovered per repo — CI config
first, since that says how *your team* builds *this repo* — so nothing in the
plugin assumes a language, a framework or an architecture.

`build`, `test` and `lint` are slots meaning "does this work", not literal
compilation: a Terraform repo's are `validate`, `plan` and `tflint`, and a
Helm chart's are `template`, `test` and `lint`. Services, libraries, apps and
infrastructure are all first-class.

---

## Quick start

```bash
mkdir platform && cd platform          # the hub, beside your service repos
claude
```

```
/pave:init                             # create the hub here
/pave:add ../user-service           # register each service
/pave:add ../order-service
/pave:add ../pricing-service
/pave:analyse                          # work out what they are, and what they do
/pave:spec build checkout              # pick an id, then agree what it must do
/pave:plan                             # → one approval gate
/pave:build                            # fan out, every task that can run at once
/pave:review                           # did the agents follow the tasks, and does it build?
/pave:learn                            # record what the feature added
```

**Sharing the hub is optional.** Nothing in Pave depends on the hub being a
git repository — every hash, snapshot and staleness check works on plain
files, so a private hub that is never committed works exactly the same. To
share it with a team, commit `config.yaml`, `AGENTS.md`, `CLAUDE.md`,
`conventions/`, `.pave-hub` and `artifacts/knowledge/on-demand/`.
`workspace.yaml` stays local either way — it holds *your* repo paths, and a
teammate generates their own with `/pave:init`.

**So is git in the service repos.** Pave never reads a branch or a commit to
decide anything. The seal's task hashes record what each task was built
from, and knowledge records a hash of the source it read. In a repo
under git, builders work on a branch; in a repo without one, they build in
the folder as it is.

**Commits.** Builders never commit. At the end of `/pave:build`, with
`branch.autocommit: false`, the default, it asks whether to commit what it
built; with `true`, it makes one commit per repo without asking. Either way,
only a repo that had no uncommitted changes before the build is ever
committed, the commit comes before `/pave:review` has compiled or tested
anything, and nothing is merged or pushed. This is enforced by the agents'
instructions, not by a guard: a builder can run shell commands, so it is not
a hard boundary.

---

## How it flows

```
spec  →  plan  →  build  →  review  →  learn
what      how      do        check      remember
```

Every feature takes the same path, and each step answers exactly one
question:

| Step | Question | Owned by |
|---|---|---|
| **spec** | What must be true when this is done? | You — nothing is written without your yes |
| **plan** | What has to change, in which services, to make it true? | The planner — one gate, your approval |
| **build** | Write the code | Builders, every task whose dependencies are done, in parallel - they run nothing |
| **review** | Did the code do what each task said, and does it build? | Reviewers, one per task; then each service's build, test and lint |
| **learn** | What does the platform know now that it didn't before? | The knowledge base |

The philosophy is in how the steps relate:

- **Each step trusts only what the step before it wrote down.** The handoff
  is a file — `spec.md`, `plan.md`, a task document — never a conversation.
  So any step can run in a fresh session and reach the same result.
- **Change flows one way.** A new requirement starts at spec, never in a task
  or a repo. A builder that finds a gap stops; a planner that meets a "what"
  question sends it back. Nothing downstream decides what upstream left open.
- **Drift is detected, not trusted away.** The plan records the spec it
  answers, and the seal the tasks it approved, by hash. Change either, and
  build and review refuse until the feature is re-planned.
- **Your choices are final.** A level you give `/pave:plan`, or any answer
  you give, is done as given. Pave recommends and warns, but never overrides
  you.
- **The loop closes.** What a feature added, and what a question dug out of
  the code, goes back into the knowledge base — so the next spec is written,
  and the next plan is made, against the platform as it now is.

---

## The workflow

| Command | When you run it |
|---|---|
| `/pave:init` | Once, to create the hub; again after upgrading Pave |
| `/pave:add <folder>` | Whenever a service joins the platform |
| `/pave:analyse` | After adding services, then as they drift |
| `/pave:spec` | Every feature — sets the session's feature, then what it must do |
| `/pave:plan` | Once the spec has no open questions |
| `/pave:build` | Once the plan is approved |
| `/pave:review` | On demand |
| `/pave:learn` | After a clean review — records the feature in the knowledge base |
| `/pave:help` | Any time you have a question about using Pave |
| `/pave:query` | Any time you have a question about your hub |
| `/pave:visualize` | Any time you want a picture instead of tables |
| `/pave:compact` | When the conversation is long — before you run `/compact` |

---

## `/pave:init` — create the hub

**What it does.** Creates the hub folder's scaffolding: `config.yaml`,
an empty `workspace.yaml`, `AGENTS.md` (plus a `CLAUDE.md` that imports it), `conventions/` and a `.pave-hub`
marker that lets every other command find the hub from anywhere.

It does not look for repos, guess what anything is, or scan. Each step does one
thing you can check before moving on.

**What it asks you.** Where the hub goes — this folder, or somewhere else. It
never guesses. If the folder isn't a git repository it offers `git init`, for
sharing the hub later - nothing in Pave needs it.

**After upgrading Pave, run it again.** On an existing hub it creates only
what is missing and leaves everything else. It runs `pave.sh config-check`,
which compares the hub's config with the template this version of Pave ships:

```
leftover  model_ranking = [haiku, sonnet, opus, fable]
leftover  agents.designer = { model: fable, effort: max }
missing   agents.planner = { model: opus, effort: high }
result: 3 to fix - run /pave:init
```

Init asks what to do - add the missing keys, remove the leftovers, both, or
nothing - and makes exactly those edits: missing keys are copied from the
template with its values, leftovers are removed, and every other line, comment
and value stays, in the file's own format (YAML or TOML). A removed key's value
is not carried over (`designer`'s model does not move to `planner` - edit the
config afterwards to keep it). The config
records no Pave version; the template is what Pave reads now, which is right
however old the hub is.

**Upgrading to 1.0.** 1.0 makes `spec.md` and `plan.md` a feature's only
sources of truth, and a hub from 0.x notices it in four places:

- **Task hashes move out of `plan.md`** into a disposable seal,
  `features/<id>/artifacts/seal.yaml`. A feature sealed under 0.x has no
  seal, so `pave.sh check` reports it `unverified` and build and review
  refuse. The next `/pave:plan` rebuilds its task documents from `plan.md` -
  updating `plan.md` first if it lacks something the tasks need, such as the
  new Interfaces table - and you approve once. Rebuilt tasks start `pending`;
  the next build finds what already holds in the code, and review checks
  everything again.
- **Contracts are no longer planned files.** `plan.md` holds the exact
  interfaces, and each task carries its side of them. The old
  `features/<id>/contracts/` folder is no longer read; delete it when you
  like. After a clean review, the built schema files are copied into
  `artifacts/contracts/` as a record.
- **Builders only write code.** They run no build, test, lint or codegen,
  and never commit. `/pave:review` runs the commands as a second gate, and
  `/pave:build` makes the commits. The `monorepo_strategy` setting under
  `execution` is gone: `/pave:init` reports it as a leftover and removes it.
- **`depends_on` is the only ordering.** Tasks in one service run in
  parallel unless the plan orders them. A plan from 0.x relied on one
  builder per service; its rebuild adds the `depends_on` that tasks sharing
  a file need.

**Upgrading from 0.6.** 0.7 adds `branch.autocommit`, and builders no longer
commit by default. `/pave:build` stops until the key is in the config: run
`/pave:init` to add it as `false`, or set it to `true` to have each builder
commit once, after its build passes.

**Upgrading from 0.5.** 0.6 stops using git to decide anything, and a hub
from 0.5 notices it in three places:

- **Every service is re-analysed once.** Knowledge from 0.5 records a git
  commit, not a hash of the source it read, so `pave.sh stale` reports every
  service `missing` and the next `/pave:analyse` reads them all again. Plan
  for the cost of one full scan.
- **Every source finding is stale.** A finding from 0.5 records a commit
  too. Each is answered again, from the code, the next time `/pave:query` or
  `/pave:plan` needs it; until then it is not used.
- **Reports lose their commits.** Build and review reports record the spec
  and task hashes they ran against, not a branch head or a commit sha, and
  feature records list tasks per service instead of commits. Anything outside
  Pave that reads `commit:` from them must change.

Plans and tasks carry over to 0.6 as they are: a feature sealed and built
under 0.5 still passes `pave.sh check` there, and its `done` tasks stay done.

---

## `/pave:add` — register a service

```
/pave:add ../order-service
/pave:add ../storefront/packages/events     # a monorepo package
```

**What it does.** Records the folder's absolute path in `workspace.yaml` and
adds it to `additionalDirectories` in `.claude/settings.json` — that second
part is what actually grants Claude access to the repo.

It runs `scripts/pave.sh`, because none of that needs a model: validate,
absolutise, append, merge. The script is idempotent, so adding the same folder
twice is a no-op, and you can run it directly if you prefer:

```
"$(...)/plugins/pave/scripts/pave.sh" add ../order-service
```

That's all it records: name and path. Not the language, not the build commands.
`/pave:analyse` finds those, and having two commands discover the same things
would mean two answers.

**What it asks you.** Nothing, unless something is wrong — the folder doesn't
exist, is inside the hub, or collides with a name already registered. A
folder that isn't a git repository is registered like any other, with a note
that builders will not branch or commit there.

---

## `/pave:analyse` — work out what they are

**What it does.** Two passes over the registered services.

**Discovery** reads CI config first, then a task runner, then the manifest,
then the README, and records the language, build/test/lint commands, contracts
and repository root. That order is deliberate: a manifest tells you a repo is Go; CI
tells you how *your team* builds *this repo*, which is the question that
matters.

**Analysis** then reads each service's domain model, business flows,
integrations and data ownership, and writes an indexed knowledge base.

**Why the second pass exists.** Discovery records how to *build* a repo. It
says nothing about what a service *means*. Without that, planning writes
confident, concrete tasks that contradict code which already exists — a
`Reservation` entity in a service that has had `StockHold` for two years.
Concrete and wrong is worse than vague, because an agent will faithfully build
it.

**It never overwrites your edits.** `workspace.yaml` is yours to correct. If
you fix a test command by hand, analyse fills empty fields around it and leaves
yours alone, reporting the disagreement instead of silently winning.

**Staleness is path-scoped, not age-based.** Each service records the source
directories its analysis rested on, and `pave.sh stamp` records a hash of
their content. A month of changes to CI config invalidates nothing; a change
under `internal/domain` invalidates exactly one service. It compares file
content, not history, so it works the same with git, another VCS or none.

That check runs in `scripts/pave.sh`, which you can also run directly:

```
pave.sh stale

undiscovered svc-d       no language in workspace.yaml
missing      svc-c       no knowledge folder
stale        svc-b       files changed under internal/domain
orphan       old-svc     knowledge folder, no such service in workspace.yaml
current      svc-a       unchanged since 3f9a1c2
```

**It is the scan, nothing else.** `/pave:analyse` or `/pave:analyse
<service>`. A question is not a scan — ask it with `/pave:query`, which reads
the code only for what the question needs. A scan never rewrites or deletes
on-demand knowledge (below); it only rebuilds the index that lists it.

**You rarely run it by hand after the first time.** `/pave:plan` spawns analysts
itself for any service whose knowledge is missing, and refreshes stale
knowledge on a `full` plan. Before a `quick` re-plan that you want planned
against fresh knowledge, run `/pave:analyse <service>` first.

---

## `/pave:spec` — agree what the feature must do

```
/pave:spec FEAT-8888 build checkout      →  features/FEAT-8888/
/pave:spec let's build checkout page    →  asks: feat-3 | build-checkout-page | other
/pave:spec FEAT-8888                     →  resume an existing feature
```

**One feature per session, and this is the command that sets it.**
`/pave:plan`, `/pave:build` and `/pave:review` take no feature argument —
they act on the feature `/pave:spec` last set in the conversation. Picking a
feature back up in a fresh session is `/pave:spec <id>`: it loads the spec,
summarises it, and asks nothing unless something needs clarifying.

A leading ticket reference becomes the id. For a description, it proposes the
next `feat-N` and a short slug and lets you choose; nothing is created until
you do. The description becomes the feature's **title**.

**What it does.** It is an assistant for *your* job — deciding what the
feature is — not an agent producing something. It works through the why, the
behaviour, the acceptance criteria (each with a permanent id like `AC-3`), the
guardrails, what's out of scope, and what's still open. It asks when something
is unclear rather than filling the gap, and points out what is weak: an
untestable criterion, a "fast" with no number, a behaviour with no failure case.

**It writes only when you say yes.** Whenever the conversation changes scope,
a criterion or a guardrail, it stops and proposes the exact edit to `spec.md`.
Every approved write bumps the spec's version. If a plan exists, it then asks
whether to re-plan.

**What it asks you.** Everything about *what*. Nothing about *how*.

---

## `/pave:plan` — plan it across services

```
/pave:plan                   # plan; on a re-plan, asks the level once
/pave:plan quick             # re-plan at this level, no question
```

Always runs the `planner` agent, on the model `config.yaml` names for it. The
planner is the only agent that thinks - every place a change lives, every
interface field, every ordering is decided here - so the strongest model you
have is recommended for it.

**Is a plan needed?** It first compares the spec's hash with the one recorded
in the approved plan. Same → the plan is current, and it says so. Different →
it re-plans, starting from what changed. It refuses while the spec still has
open questions.

**What it does, in order:**

1. **Services** — which services does this touch? Usually more than the
   person asking expects. You confirm the candidates.
2. **plan.md** — the approach, a **service map** (every service as `modify`,
   `read-only` or `untouched`), each decision with the criteria it serves and
   the alternative it rejected, the flow, failure behaviour, state ownership,
   the **interfaces** between services field by field, and every task in one
   line: service, priority, size, the criteria it satisfies, what it depends
   on, and the obsolete tasks it reverts.

   **→ The gate.** You approve `plan.md`. **Interfaces freeze here.**

3. **Task documents** — one per task, each naming a single service and
   carrying everything its builder needs, interface fields included, then a
   readiness check - with `pave.sh overlaps` making sure no two tasks that can
   run at once name the same file. The plan is then **sealed**: the spec's
   hash goes into `plan.md`, each task's hash into the seal.

**`spec.md` and `plan.md` are the truth; tasks are projections.** Every
change goes into `plan.md` first, and the tasks are written from it. Lose
the task documents - or keep only the two truth files in git - and the next
`/pave:plan` writes them again from the plan.

**It never decides what the spec leaves open.** A question about *how* — an
event or a call, which service owns the state — it settles or asks you. A
question whose answer changes what the feature does goes back to you as a spec
decision: settle it with `/pave:spec`, then re-plan.

**Always tasks, even for one change.** A task is the unit that is built,
rebuilt, reviewed and reverted on its own. Task numbers only ever increase.

**The planner owns every ordering.** Build runs every task whose `depends_on`
are done at the same time - two tasks in one service as readily as two in
different services. So the plan gives a `depends_on` to any two tasks that
name the same file, or where one needs the other's result, and none to the
rest.

**Re-planning, at the level you choose.** A small change should not cost a
full plan. `pave.sh diff` works out, for free, which acceptance criteria
changed since the approved spec and which tasks and services they reach -
the Why and What prose never count. Then the re-plan runs at one of three
levels:

| Level | For a change that… | Knowledge | Passes | Readiness checks |
|---|---|---|---|---|
| `quick` | stays within the plan sections behind the tasks it reaches | stale kept; the planner checks the code | one: plan and tasks together, one gate | the re-projected tasks |
| `scoped` | changes decisions, interfaces or the task set | stale kept; the planner checks the code | plan, gate, tasks | changed tasks and their interface partners |
| `full` | does anything else | stale refreshed | plan, gate, tasks | every task |

Give the level as the argument and it is used as given. Give none, and the
planner traces the change first and recommends one; you are asked once,
offered only the levels the change fits. **Your choice is final**: the
planner may say at the gate that it would have chosen differently, but it
plans at your level. The one exception: with no approved spec to compare
against - a fresh clone of the hub, say - nothing can tell what changed, so
the re-plan is `full`, and it says why.

Whatever the level, tasks describe the end state, never a change from a
previous version:

| The task is… | …and the spec | The plan |
|---|---|---|
| not built | still needs it, differently | rewrites it in place |
| not built | no longer needs it | drops it |
| built | still needs it, differently | rewrites it and **reopens** it, naming every place in the code the change reaches |
| built | no longer needs it | marks it **obsolete** and adds a new task that removes its work |

**The planner reads the code.** Knowledge tells it where to look; the code
tells it what is true. It looks up precise things itself — every place a value
lives, what a handler does on failure — and hands back what it needs
explained: the skill has a cheaper `analyst` read the code and save the answer
as an on-demand finding, then resumes the planner with it. A task can only
name every place a behaviour lives if someone read the code, and that is the
planner's job, not the builder's.

**A change that affects nothing.** If the spec changed only in wording — a
typo, a clarified sentence — the planner says so and lists what it compared,
and you can **re-seal** instead of re-planning: the new spec hash is recorded,
no task is touched, and the feature goes back to the status its tasks say.
It's always your call; a changed word in a criterion counts as a change.

**Token cost.** Within a session the planner is resumed rather than
respawned, so a re-plan costs only the difference. Across sessions it
recovers from small files: `plan.md` as the index from criteria to decisions
to tasks, a snapshot of the spec it was approved against, and the list of
knowledge files and findings it relied on. A `quick` re-plan reads the plan
and the code behind the tasks it reaches, and nothing else.

**What it asks you.** To confirm the services, the level on a re-plan, any
*how* questions, and the one gate.

---

## `/pave:build` — execute the plan

```
/pave:build                  # every outstanding task
/pave:build 03,07            # only these (spaces also work)
```

**It refuses to build a stale plan.** Before anything else it checks the
spec's hash and every task's hash against the sealed plan. A spec changed
since, or a task edited by hand, stops it: run `/pave:plan`.

**What it does.** Runs the plan's `depends_on` graph and decides nothing
else: every task whose dependencies are done is built at once, in one service
or many, up to `execution.max_parallel`. Tasks linked by `depends_on` in one
service form a chain that one builder works through, keeping its context.
Priority only picks which ready chain starts first when the limit holds
others back.

**Builders only write code.** A builder reads its task document and makes
each item hold in the code - nothing else. It runs no build, test, lint or
codegen, and never commits: several builders can share a repo, and none of
them runs anything that could collide with another or read another's
half-written files. `/pave:review` compiles and tests once everything is
built. The cost is honest: a cheap builder that cannot compile will
sometimes slip - a typo, a missing import - and review sends that task back.
The plan's precision is what keeps those slips rare.

**One way of building.** Every task is built the same way, whatever its
status: for each item, the builder reads the code the item names, leaves it
alone if the item already holds, and makes it hold if not. A new task, a
reopened one, one that failed review and one that removes obsolete work are
all just items to make true.

A `done` task is frozen and never rebuilt, even when named — a task changes
only by re-planning. A done task was built from the text sealed for it, so
if a re-plan rewrites a done task without reopening it, `pave.sh seal` sees
its hash differ from the previous seal's and reopens it.

**Pave writes in the hub; builders write in the repos.** The skill itself never
edits a service repository — it reads the hub, spawns agents, and writes
reports back. Builders write the code, in a repo under git on the feature's
branch.

**Commits.** Made by `/pave:build` itself, once every builder has returned -
never by a builder. With `branch.autocommit: true`, each repo that had no
uncommitted changes before the build and whose tasks are all done gets one
commit, without asking. With `false`, the default, it offers those repos and
commits only on an explicit yes. Either way the commit comes before review
has compiled anything.

**What it asks you.** Ideally nothing. The build report is triaged by *who must
act*: an in-scope judgement an agent made goes under **Decisions taken**, where
you can skim it; only what genuinely cannot be resolved without you reaches
**Needs you**, and each of those carries the decision and the exact command.

**Escalation.** An agent that finds an interface wrong stops rather than
fixing it locally — the other side is being built from the same fields, and a
local fix turns one error into several divergent guesses. That becomes a
decision for you, usually a re-plan.

---

## `/pave:review` — check what was built, in two gates

**Gate 1 - did each builder do what its task said?** Spawns one reviewer per
task. Each takes a single task document and one repo, and finds every ticked
item in the code — not in the agent's report, in the code.

**Gate 2 - does it build?** For every service whose tasks are all done and
passed gate 1, it runs the service's own `codegen`, `build`, `test` and
`lint` - one service at a time within a repo. A failure is sorted, not
judged: `pave.sh attribute` says which tasks name each failing file.

| The failure is in… | Means | Next |
|---|---|---|
| a file exactly one task names | that builder's slip | the task is marked `failed`, with the error in its Build notes → `/pave:build` |
| a file no task names, or several do | a gap in the plan - a place it did not name, two tasks it did not order | reported as a plan gap → `/pave:plan`, your call |
| no file at all | the environment | reported → fix it, review again |

**What it does not do.** It does not ask whether the plan was right. If the
plan said A, B and C and the agents did A, B and C, gate 1 passes — even if
the feature needs D. When the gap shows up in gate 2, it is reported as the
plan's, never as a task's, and you decide.

That restraint is the point: it makes the phase cheap, and it keeps your
approval at the plan gate meaningful. Like build, it refuses to run against a
plan that no longer matches the spec.

**When something deviates**, review unticks the specific items that were not
real, writes what the reviewer found for each - where it looked and what was
there instead - into that task's Build notes, marks the task `failed`, and
writes a report for you. `/pave:build` then re-runs only the failed tasks;
each builder sees only its task document, where the failed items are unticked
and the findings sit in its Build notes.

**Contracts, as a record.** After a clean review of a finished feature,
`pave.sh contracts` copies every `producer` contract file `workspace.yaml`
records for the services the plan modified - the schemas as actually built
and verified - into `features/<id>/artifacts/contracts/`. Nothing is built
against the copy; run it again and it is rebuilt.

**Cleaning up.** After a successful review, if any obsolete tasks have been
reverted, it asks whether to remove them. On yes, `pave.sh
prune-obsoleted-tasks` deletes each obsolete task together with the task that
reverted it (from the `Reverts` column of `plan.md`) and drops their hashes
from the seal, leaving the spec hash and every other task untouched.

---

## `/pave:help` — how do I use Pave

Not part of the sequence above. Run it any time, from anywhere — it needs no
hub.

```
/pave:help
/pave:help plan
/pave:help how does /pave:review decide a task failed?
```

**What it does.** Explains a command, or the workflow as a whole, straight
from the plugin's own skill files — no hub, no agent, just a handful of
small local files. With no argument it lists every command and what it does
in one line. Given a command name, it explains that phase in plain language.

Ask it something about *your* hub instead — a service, a feature, a
convention — and it declines and points you at `/pave:query`, rather than
guessing at an answer it has no way to check.

**What it asks you.** Nothing.

---

## `/pave:query` — ask about your hub

Not part of the sequence. Run it any time, once you have a hub.

```
/pave:query what happens after an order is submitted?
/pave:query why did build-checkout end up blocked?
```

**What it does.** Answers as cheaply as the question allows:

1. A `retriever` answers from the knowledge base — service analyses, earlier
   on-demand findings, feature records — plus `conventions/` and the hub's
   `AGENTS.md`, citing the file each fact came from.
2. If that can't answer a question about **how the code behaves**, an
   `analyst` reads only the code the question needs, across services, and
   answers with file and line references.
3. That answer is saved as a **source finding** in
   `artifacts/knowledge/on-demand/source/`, so the next person to ask gets it
   from knowledge.

A finding records the directories it read and a hash of their content, and
`pave.sh stale` marks it stale as soon as that code changes. A stale finding is never used as
an answer; the next query that needs it reads the code again and replaces it.

A gap reading code can't settle — a decision nobody recorded, a convention
nobody wrote — is reported as such, never guessed.

**What it asks you.** Nothing.

---

## `/pave:learn` — record a finished feature

```
/pave:learn
```

**What it does.** Acts on the session's feature. Once it has been built and
passed review against its current plan — the plan matches the spec, every task
is done, every acceptance criterion is satisfied by a done task, and the review
is of this build — it writes a **feature record** to
`artifacts/knowledge/on-demand/features/<feature-id>.md`: what the feature
added, per service with the tasks built there, its interfaces, the decisions a
later feature will bump into, and links back to `features/<feature-id>/`.

Its capabilities join the knowledge index, so the next spec in the same area is
planned against what this one added.

The record stores the spec hash it was made against. Once the feature's
`spec.md` changes, `pave.sh stale` marks the record stale and it stops being
used as an answer or planned against, until the feature is re-planned,
rebuilt, reviewed and learned again. If the feature isn't finished, it refuses
and lists what's missing and which command fixes it.

**What it asks you.** Nothing.

---

## `/pave:visualize` — draw a picture

Also not part of the sequence. Run it any time.

```
/pave:visualize                            # the session feature's blast radius
/pave:visualize build-checkout             # another feature's
/pave:visualize how does pricing talk to checkout?   # freeform
```

**What it does.** Given a feature id, or none when the session has one,
draws that feature's blast radius — services from its `plan.md` service map as
nodes, its Flow steps and Interfaces as edges. Given anything else, treats it as a description and pulls what's
relevant from the knowledge index.

It draws only from files other phases already wrote — never from scanning a
service repo — and says plainly when something needed is missing or stale
rather than filling the gap.

Where Claude's Artifact tool is available it publishes an interactive
diagram and gives you the link; otherwise it writes a self-contained
`diagram.html` you open locally.

**What it asks you.** What to draw, if you ran it with no argument.

---

## `/pave:compact` — compact without losing your place

Also not part of the sequence. Run it when the conversation gets long.

```
/pave:compact
/pave:compact keep the two options we discussed for retries
```

**Why it exists.** The session's feature lives in the conversation — the
`Working on <id> — <title>` line `/pave:spec` printed. A plain `/compact`
can summarise that line away, and then `/pave:plan`, `/pave:build` and
`/pave:review` stop with "No feature in this session".

**What it does.** Writes a short *Pave brief*: the feature line, verbatim;
the feature's state as its files say it (`README.md` status and `pave.sh
check`); a few lines of recent work; and whatever is not on disk yet — a spec
edit you have not approved, a question still open. Then it gives you the
`/compact` command that keeps the brief word for word. A skill cannot run
`/compact` itself, so you run it.

The brief is memory, not a source of truth. After compacting, the commands
that act on the feature — `/pave:spec`, `/pave:plan`, `/pave:build`,
`/pave:review` and `/pave:learn` — still read its spec, plan and tasks from
disk; the brief only tells them which feature, and you where you were.

**What it asks you.** Nothing. An argument is anything else you want kept.

---

## The hub

```
platform/
├── config.yaml              team policy — commit this
├── workspace.yaml           your services — gitignored, local to you
├── AGENTS.md                your rules — every agent is given this
├── CLAUDE.md                @AGENTS.md — so Claude Code loads it too
├── conventions/             how code is written, by language and service
│   ├── README.md
│   └── go.md
├── artifacts/               disposable, except knowledge/on-demand/
│   ├── knowledge/           what each service does, indexed
│   │   └── on-demand/       kept by every scan — cannot be regenerated
│   │       ├── source/      answers /pave:query read from the code
│   │       └── features/    what each finished feature added, from /pave:learn
│   ├── diagram.html         written by /pave:visualize when freeform
│   └── platform.code-workspace
└── features/
    ├── README.md            portfolio: one row per feature
    └── build-checkout/
        ├── README.md        one row per task
        ├── spec.md          what it must do — yours
        ├── plan.md          how, with its interfaces and the spec's hash — the truth, with spec.md
        ├── tasks/           one self-contained document per unit of work, projected from plan.md
        └── artifacts/       disposable: the seal, spec snapshot, planner context,
                             reports, built contracts, diagram.html
```

`config.yaml` holds nothing machine-specific, so it commits and the team shares
it. `workspace.yaml` holds absolute paths, which differ per developer — a
teammate clones the hub and builds their own with `/pave:add`. That split is
what lets everyone share one policy with their own local layout.

---

## Status

```mermaid
flowchart LR
    newfeat(("new feature")) -->|/pave:spec| specifying(["specifying"])
    specifying -->|/pave:plan| planning(["planning"])
    planning -->|gate passes, plan sealed| ready(["ready"])
    ready -->|/pave:build| building(["building"])
    building -->|every task done| done(["done"])
    building -->|agent escalated| blocked(["blocked"])
    blocked -->|blocker resolved, /pave:build| building
    blocked -->|plan must change, /pave:plan| planning
    done -->|/pave:review finds gaps| failed(["failed"])
    failed -->|/pave:build| building
    any(["any status"]) -.->|/pave:spec changes the spec| specifying

    classDef step fill:#54aeff26,stroke:#54aeff,stroke-width:1px
    classDef good fill:#2da44e26,stroke:#2da44e,stroke-width:1px
    classDef warn fill:#bf871926,stroke:#bf8719,stroke-width:1px
    classDef bad  fill:#cf222e26,stroke:#cf222e,stroke-width:1px
    classDef muted fill:none,stroke:#8c959f,stroke-dasharray:3 3
    class specifying,planning,ready,building step
    class any,newfeat muted
    class done good
    class blocked warn
    class failed bad
```

| Status | Means | What to do |
|---|---|---|
| `specifying` | The spec is being written, or changed since it was last planned | `/pave:plan` once it has no open questions |
| `planning` | Planning in progress | — |
| `ready` | Plan approved and sealed, not built | `/pave:build` |
| `building` | Being built, or a run left work | `/pave:build` resumes |
| `done` | Every task built | `/pave:review` if you want it checked |
| `failed` | Review found claims that were not real | `/pave:build` re-runs those tasks |
| `blocked` | An agent escalated | Read the build report. `/pave:build` once the blocker is fixed; `/pave:plan` if the plan must change; `/pave:spec` first if what the feature does must change |

A spec change sends the feature back to `specifying` from any status: build
and review refuse until it is re-planned. `/pave:learn` does not change the
status; it records a `done`, reviewed feature in the knowledge base.

Tasks have their own status: `pending`, `in-progress`, `done`, `reopened`
(re-planned after it was built), `failed`, `blocked`, and `obsolete` (no longer
wanted; a new, high-priority task removes its work).

---

## Configuration

`config.yaml` — team policy, committed:

```yaml
agents:
  analyst:   { model: sonnet, effort: medium }   # reads business logic
  builder:   { model: sonnet, effort: medium }   # writes the code of one task document
  explorer:  { model: haiku,  effort: low    }   # mechanical repo scanning
  reviewer:  { model: sonnet, effort: low    }   # one per task: task vs code
  planner:   { model: opus,   effort: high   }   # planning decides the feature - strongest recommended
  retriever: { model: sonnet, effort: low    }   # answers hub questions

execution:
  mode: parallel                 # parallel | sequential
  max_parallel: 4

branch:
  pattern: feature/{feature-id}  # the branch in every service repo under git
  autocommit: false              # true: /pave:build commits each repo once, at the end
```

Every model is enforced when its agent is spawned, planning included. Skills
look each one up with `pave.sh agent <name>` rather than parsing YAML.
`/pave:plan` always spawns the `planner` on its configured model, and resumes
the same agent for later stages and re-plans within a session.

Agent definitions carry no `model` or `effort`. The orchestrating skill always
passes both when it spawns, so `config.yaml` is the only place to change them.
There are no defaults anywhere else. If an agent has no entry, `pave.sh agent`
stops with an error, and a skill that needs a setting the config lacks stops
too; both point you to `/pave:init`, which brings the config up to date.
Commands never change the config themselves.

**What the platform can enforce.** Pave passes both values, but the agent
platform decides what it honours. In Claude Code the model is enforced when an
agent is spawned; whether `effort` is depends on your Claude Code version, and
where it is not supported the agent runs at the platform's default effort. Use
the model names your platform accepts for spawned agents - in Claude Code,
`haiku`, `sonnet`, `opus` or `fable` - rather than full model IDs.

The hub's config may be `config.yaml`, `config.yml` or `config.toml`, but only
one of them. `pave.sh` reads it with `scripts/yaml-reader` or
`scripts/toml-reader`, both Python 3. The YAML reader uses PyYAML when it is
installed, and otherwise a built-in parser that rejects any syntax it doesn't
support rather than guessing. The TOML reader uses Python 3.11's `tomllib`.
Either reader can be called directly:

```
scripts/yaml-reader config.yaml agents.explorer
model=haiku
effort=low
```

A config file that can't be parsed stops the command with an error rather than
falling back to defaults.

**Monorepos.** Several services - or several tasks of one service - may be
built in one repo at once. That is safe because the plan keeps them on
different files and builders run nothing. Review's second gate runs build,
test and lint one service at a time within a repo, and `/pave:build` commits
each repo once.

---

## Your own rules

The hub's `AGENTS.md` is yours. `/pave:init` creates it, and **every agent Pave
spawns is given it by path as required reading** — the builder writing code in
a service repo, the reviewer checking it, the analyst and explorer reading a
repo, the planner planning the feature. Write a rule there and it reaches the
agent doing the work, not only the session that spawned it.

The hub also gets a one-line `CLAUDE.md` — `@AGENTS.md` — because Claude
Code loads `CLAUDE.md` by itself and not `AGENTS.md`. Your rules go in
`AGENTS.md`; the `CLAUDE.md` only points at it. On a hub from an older
version, `/pave:init` offers to move rules from `CLAUDE.md` into `AGENTS.md`.

Skills read it explicitly rather than relying on it being loaded for them —
they run from inside service repos as well as from the hub, and a file loads by
itself only when you happen to be standing next to it.

| Where | What belongs there |
|---|---|
| hub `AGENTS.md` | Your rules — what agents should and should not do |
| `conventions/` | How code is written, by language and service |

The split is worth learning once: `conventions/` is **descriptive** — drafted
by `/pave:analyse` from your repos, narrowed to a language or a service. The
hub file is **prescriptive** — what you are telling the agents to do.

Nothing you write there relaxes the plugin's own doctrine. A rule cannot send a
builder outside its task's files, change a frozen interface, or let it fill a gap the
plan left open, and it cannot make a reviewer fail a task the plan never asked
for. Where one of your rules and a task document disagree, the document wins
and the agent says so in its summary rather than quietly picking.

---

## Why it holds together

**The user owns "what"; the plan owns "how".** The spec is written only with
your approval, and the planner sends back any question whose answer would
change what the feature does. So every plan decision traces to something you
wrote down.

**Two files are the truth.** `spec.md` and `plan.md` are all a feature needs
to be rebuilt; every other file is a projection of them or a record. Every
change goes into the plan first, so nothing true lives only in a task.

**Nothing is built against a stale plan.** The plan records the spec's hash,
and the seal every task's hash, at its gate; build and review check both
before doing anything. A spec change or a hand-edited task stops them until
the feature is re-planned.

**Planning is the expensive phase and is recommended the strong model.**
Build agents get a cheaper one — not because they do the same job with less
care, but because their job is genuinely smaller: interfaces are fixed field
by field, tasks name every file, orderings are decided, out-of-scope is
explicit, and anything ambiguous escalates instead of being improvised.

**Every task traces in both directions.** Tasks cite the plan sections they
come from and the acceptance criteria they satisfy, and the
planner checks coverage every way: no task without a decision behind it, no
decision without a task, no criterion without a task that satisfies it. The
missing ones are the expensive ones — a criterion with no task is never built,
and review will pass the feature, because review asks whether the plan was
followed and the plan never asked.

**Tasks describe the end state.** A re-planned task is rewritten, not
patched with a diff, so any builder — facing existing code or starting from
a reset — reaches the same result from the document alone.

**Unhappy paths are specified, not left open.** A task item that changes
behaviour states what happens on replay, on failure, and at boundaries. This is
where agents invent, and review is structurally unable to catch an invention
the plan never ruled out.

**Silence never means success.** An agent that returns nothing leaves its work
unfinished, not done — in build, in review, and in analyse alike.

If build agents routinely need to think their way out of gaps, that is a defect
in the plan, not a reason to raise the build model.
