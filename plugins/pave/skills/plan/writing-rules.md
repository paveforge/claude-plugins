# Pave — plan: writing the plan and its tasks

Read by the `planner` agent. Where this file says "present" at the gate, the
planner returns its summary instead; `/pave:plan` presents it.

## 1. The spec is the only source of "what"

`spec.md` says what must be true. The plan says what must change to make it
true. Nothing in the plan may decide what the spec did not.

**Every decision serves the spec.** Each decision in `plan.md` names the
acceptance criteria or guardrails it serves. Each task names, in
`satisfies:`, the criteria it delivers. A decision that serves nothing in the
spec is invented scope - drop it.

**Sort every question before answering it.**

| Kind | The answer changes… | Who answers |
|---|---|---|
| how | only how the spec is met: a protocol, an owner, an ordering | You, from the knowledge; or the user, via the orchestrator. Record it as a decision |
| what | behaviour, scope, a criterion or a guardrail | **Only the user, through `/pave:spec`.** Return it as a "what" question and stop planning around it |

The line is sometimes thin. "Should an expired hold be released
immediately or at the next sweep?" sounds like mechanism, but if a user can
observe the difference, it is "what". If in doubt, it is "what".

**Never plan around an open question.** If the spec's Open questions section
is not empty, you should not have been started; say so and return.

## 2. plan.md

Write `features/<feature-id>/plan.md` from `templates/plan.md`.

`spec.md` and `plan.md` are the feature's only sources of truth. Everything
else - the task documents, the seal, the approved-spec snapshot, contract
copies - is disposable and is rebuilt from them. So **every change goes into
`plan.md` first**, and the tasks are projected from it. A change you write
only into a task is lost the next time the tasks are rebuilt.

### The sufficiency test

**Could someone write every task document from `plan.md` alone, and the
code, without asking you a question?**

That is a correctness bar, not a stylistic one. The tasks may be written by a
planner that remembers none of your reasoning - a fresh one, spawned because
yours could not be resumed, or because the task documents were lost. Anything
you decided but did not write down is gone, and the task-writer invents a
replacement that looks reasonable and is not what you meant. So: **write down
the reasoning, not only the conclusion.**

### What it must contain

**Named sections with stable anchors.** Tasks cite `plan.md#<section>` in
`derives_from`. An uncitable decision cannot be checked.

**The service map.** Every service the feature was considered against, in one
of three states. This is what makes parallel building safe, so be exact:

| State | Means | Consequence |
|---|---|---|
| `modify` | Its code changes | It gets tasks |
| `read-only` | It is called or read as it is | No tasks; every task that touches it says so in Out of scope |
| `untouched` | Considered and ruled out, with the reason | Named in every task's Out of scope |

Recording `untouched` is deliberate. It says the service was ruled out, not
forgotten, and it is the line that keeps a helpful builder out of it.

**Each decision, with its rationale** - what was decided, which criteria it
serves, why, and what was rejected. The rejected alternative matters most:
without it, a task-writer may quietly re-derive the option you ruled out.

**The flow, step by step** - which service does what, in order, and what it
emits.

**The unhappy paths, at the cross-service level.** What happens when each step
fails: what retries, what compensates, what is left inconsistent and for how
long, what the caller sees. §5 projects this into per-item failure behaviour.
If it is not here, four builders each invent something sensible and none of
them agree. Every failure case in the spec's criteria must appear here.

**State ownership** - which service owns which piece of state, and who may
read it.

**Assumptions** about the system as it is. An assumption about what the user
wants is not an assumption; it is a "what" question.

### The task table

Every task in one line - the whole plan is approved from this table before
any task document is written. So the table has to be complete and honest:

| Column | Rule |
|---|---|
| `#` | From `next_task` in the frontmatter, increasing. **Never reuse a number**, even of a deleted task |
| Service | Exactly one. A task never spans two services |
| Priority | `low`, or `high` for a task that reverts others. `critical` is reserved - do not use it |
| Size | `S` (≤3 items), `M` (≤8), `L`. **An `L` must be split before the gate** |
| Satisfies | Criteria ids. A task with none that reverts nothing is invented work |
| Depends on | Every task it must not run at the same time as, or whose result it needs - in its own service or another (see §5) |
| Reverts | The obsolete tasks whose work this one removes, e.g. `05`, or `-` |
| Change | What this revision does: `new`, `rewritten`, `reopened`, `obsolete`, `unchanged` |

**Always split into tasks, however small the feature.** One change is still
task `01`. A task is the unit that is built, rebuilt, reviewed and reverted on
its own, so the history of every change is a set of tasks.

**Build order.** You own every ordering; build decides none. It runs every
task whose `depends_on` are done at the same time - two tasks in one service
as readily as two in different services. So `depends_on` is the only thing
that keeps two tasks apart. Derive the waves from the table, and say why each
edge exists.

## 3. Interfaces — exact, and projected

Every interface between services this feature adds or changes goes into
`plan.md`'s Interfaces table: for each element, every field with its type,
its wire name or number, its producer, its consumers and a compatibility
stance (additive-only, versioned path, new topic). Only what this feature
defines - not the whole API. If a team has no IDL, the table is the
interface.

**Exact is what buys the parallelism.** Producer and consumers are built at
the same time, from the same values, by builders that cannot see each other.
If a field is soft in the plan, they diverge, and reconciling costs more than
the parallel build saved.

**You project it; nobody else reads it.** Builders and reviewers never read
`plan.md`. Each task carries, in its Interfaces table and its items, exactly
the fields it provides or consumes:

- The **producer** task has an item for the schema file itself - its path as
  `workspace.yaml` records it, and the field as it must appear there
- A **consumer** task has items for what it reads - its own copy of the
  schema if it keeps one, and the code that uses the field
- Builders run no codegen. Where code uses generated identifiers, name them
  exactly - `resp.GetTrackingUrl()`, not "the new getter" - so code written
  before the stubs exist compiles once review generates them
- A consumer that needs the producer's built work first - a client library
  that must be published, a migration it reads - waits for it with
  `depends_on`

No contract file is written at planning. After a clean review, the
producers' schema files are copied into `artifacts/contracts/` as a record of
what was built.

Interfaces are approved at the gate with the plan, because an interface
between two services is a design decision, and "this should be an event, not
a synchronous call" has to be raised before any task is derived from it.

## 4. Re-planning

A re-plan starts from what changed, not from nothing.

**Find the difference.** The brief carries the output of `pave.sh diff`: the
acceptance criteria added, changed or removed since `artifacts/spec.approved.md`
(the spec the current plan was approved against), whether the guardrails or
the out-of-scope lines changed, and the tasks and services those criteria
reach through the task table's `Satisfies` column. Start there. Follow
`plan.md` from those criteria and lines to the decisions they touch, and from
the decisions to the tasks (`Satisfies`, `derives_from`). Read knowledge and
code only for the services those tasks touch.

**The acceptance criteria are the spec's contract.** Why and What are prose
for people: a change there, with no criterion changed, moves nothing.
Guardrails and out-of-scope lines carry no ids; when they change, decide from
their text what they reach.

**If nothing moved**, return `verdict: unaffected` and write nothing. That
means no criterion, guardrail or out-of-scope line changed in a way any
decision or task depends on. List the spec differences you compared, so the
user can check your judgement. When in doubt, it moved: a changed word in a
criterion is a changed criterion.

### The level

A re-plan runs at one of three levels. The level decides how much process
runs - what is refreshed, how many passes, what readiness covers - never what
the plan may contain. Whatever the level, the plan says everything the change
needs.

| Level | Fits a change that… | You |
|---|---|---|
| `quick` | stays within the plan sections behind the tasks it reaches: no decision, interface, service-map row or task is added or removed | Edit those `plan.md` sections and re-project the tasks they reach - **in one pass**, plan and task documents together, then return for one gate |
| `scoped` | changes decisions, interfaces or the task set, within services the plan already has | Stage 1, gate, stage 2, as for any plan, reading only what the change reaches |
| `full` | does anything else: a new service, a guardrail or exclusion with wide reach | Plan as though from the start, against refreshed knowledge |

**The verdict.** When the brief gives no level, trace the change first and
return a verdict - `unaffected`, `quick`, `scoped` or `full` - with one line
on why, before writing anything. The orchestrator asks the user and resumes
you with the level they chose. When the brief gives a level, it is the user's
choice and it is final: plan at that level. If the change goes beyond it,
plan it all the same and say so in one line at the gate - "this changes
interface `OrderResponse`; planned as quick, as chosen". Never move to
another level yourself.

**Stale knowledge.** At `quick` and `scoped` the brief may name services
whose knowledge is stale and was left so. Treat their knowledge files as a
map of where to look, and confirm everything you rely on in the code.

**Then classify every affected task.** A task document always describes the
**end state**, never a change: when the spec changes, you rewrite the document
in place to say what must be true now. Nothing in it records what it said
before - a builder reading it, or rebuilding it from scratch after a reset,
must reach the same result.

| The task is… | …and the spec | Do |
|---|---|---|
| not built (`pending`, never started) | still needs it, differently | Rewrite it in place. Stays `pending` |
| not built | no longer needs it | **Drop it** - list it under Delete for the orchestrator to remove. Nothing was built, so nothing needs reverting |
| built or started (`done`, `in-progress`, `failed`, `blocked`, `reopened`) | still needs it, differently | Rewrite it in place. Set `status: reopened`. **Untick every item you rewrote or added** |
| built or started | no longer needs it | Set `status: obsolete`. Add a task that **reverts** it |
| any | is unaffected | Leave it untouched - its hash must not change |

**A tick means "checked against this wording".** An item you rewrote or
added has not been checked by anyone, so it is unticked. That is a fact about
the document, never a record of what it said before. The builder checks every
item against the code, ticked or not, so an untick is where it starts, not a
limit on what it checks.

**Read the code before you rewrite a built task.** It holds the earlier
build. A changed behaviour usually lives in more than one place - a constant,
a migration, a schedule, a fixture, a config default. Find every one and
write an item for each. A builder makes its items hold and nothing more; a
place you leave out keeps the old behaviour, and review will not catch it,
because the task never asked.

**What must go is an item too.** When a reopened task stops doing something,
say what must be true instead - "no email is sent when a hold expires",
"`internal/hold/notify.go` does not exist". Deleting the old item removes it
from the document, not from the code.

**Reverting obsolete work is an ordinary task.** It is a new number with
`priority: high`, and nothing else sets it apart:

- Record which obsolete tasks it removes in the task table's `Reverts`
  column. That link is yours and the orchestrator's; the builder never sees
  it and does not need to
- Each item states what must be true once the work is gone - "no route
  `/holds/sweep` exists", "table `hold_sweeps` does not exist; migration
  `0051_drop_hold_sweeps` drops it" - naming every file, route, handler,
  config and flag the obsolete work left in the code
- It states what must still work afterwards, and names the test that proves it
- **Anything that cannot be reversed automatically** - data that would be
  dropped, a published event schema, a migration that has already run in an
  environment - is not decided by you. List it at the gate for the user; write
  the agreed handling into the task afterwards

`priority: high` only means it starts first when several tasks are ready
and `execution.max_parallel` limits how many run. It never orders anything. A
revert that must land before other work - in the place that work also
changes, or in another service that must first stop calling what it removes
- needs a `depends_on`. Priority never replaces `depends_on`.

**An interface change is re-projected on both sides.** Every task that
provides or consumes a changed field is rewritten - and reopened if built -
and the gate says so.

**Tasks edited outside the plan.** If `pave.sh check` reported a task edited
by hand, decide from the plan and the spec what the document must say, write
that, and report at the gate what the hand edit was and whether you kept it.
Never adopt a hand edit silently: a change worth keeping goes into `plan.md`
first.

**Tasks the seal cannot vouch for.** If `pave.sh check` reported the seal
missing, every task document is rebuilt from `plan.md` in stage 2: write each
one again as a projection of the plan and the current code. Status and ticks
are not carried over - a rebuilt task starts `pending`, and the builder finds
what already holds in the code. If `plan.md` fails the sufficiency test, fix
`plan.md` first; that is a plan change and goes through the gate.

### → The gate

Present the plan as a gate summary: each file's path with one line on what it
covers, the service map, the per-task changes on a re-plan, the decisions the
user must rule on, the "how" questions you could not settle, anything that
cannot be reverted automatically, and - when you were given a level the
change goes beyond - one line saying so. Stop. At `quick` the task documents
are already written with the plan; at any other level, do not write them
yet.

## 5. Task documents

Write one document per task in the approved table into
`features/<feature-id>/tasks/`, named `NN-<short-slug>.md`, from
`templates/task.md`.

This is the most important output of the phase. Everything downstream executes
these documents without question: a builder does what the document says, and
review checks only whether it did. Anything the document leaves open, an agent
invents - and nothing downstream will catch it, because the plan never asked
for it.

So the test for every line is: **could a competent stranger do this without
asking a question?**

**Each task names exactly one target service** and must stand alone. The agent
that executes it reads that document and nothing else - not `plan.md`, not
the spec, not its sibling documents.

**Everything above `## Build notes` is yours and is hashed into the seal at
the gate.** Builders change only the status, checkboxes and the Build notes
section. Anything you want a builder to know goes above the line.

### Derivation is the whole job

The tasks are a **projection** of `plan.md` into per-service briefs. They are
not a second act of design, and nothing in them should be true for the first
time - nor true only there: a task can be thrown away and written again from
the plan, and must come out the same.

Write them in one pass, seeing the whole feature, so the set is consistent:
what one service emits, another handles; what one stops sending, another
stops expecting.

**Cite the source.** Every task names the plan sections it comes from, and
the criteria it satisfies:

```yaml
satisfies: [AC-2, AC-4]
derives_from:
  - plan.md#reservation-expiry
  - plan.md#state-ownership
  - plan.md#interfaces
```

A builder cannot see `plan.md`, so it cannot tell a planned decision from one
the task-writer invented. The citation is what lets the user at the gate, and
review afterwards, check. **If you cannot cite a source for an item, you are
inventing it.**

**Check coverage in every direction:**

| Direction | Question | Failure |
|---|---|---|
| Task → plan | Does every item trace to a decision? | Invented work |
| Plan → task | Does every decision have an item? | Silently dropped work |
| Spec → task | Does every criterion have a task that satisfies it? | A requirement nobody builds |

The second and third are the ones that get missed, and they are the
expensive ones. Walk the spec criterion by criterion, `plan.md` decision by
decision and every interface field by field - once for its producer and once
for each consumer - and find the task that implements each. A criterion with no task will not be built, and review will pass the
feature - because review asks whether the plan was followed, and the plan
never asked.

### How many tasks

One task is **one coherent unit of work in one service that could be built
and reviewed on its own**. Split where the work has a natural seam - the API and
the background sweeper that expires its rows are two tasks.

Never split by architectural layer. "Domain", then "repository", then
"handlers" is three tasks that cannot be built or reviewed independently.

### What an item looks like

An item is **one focused change you can state in a single sentence without
using "and"**. If the sentence needs an "and", it is two items.

Each item must be:

- **Concrete** — names the file, type, endpoint or migration, with the file's
  path from the service's root. The path is also how parallel work is kept
  apart (below) and how a failing build is traced back to a task
- **Independently checkable** — review ticks and verifies items one at a time
- **Grounded** — names the existing code it extends, as you read it in the code

```markdown
- [ ] Extend `StockHold` (internal/domain/hold.go) with expires_at + Expired state
```

not

```markdown
- [ ] Add a Reservation entity with a TTL        # invents a concept that exists
- [ ] Phase 1: Domain & Models                   # scaffolding, not work
- [ ] Add validation                             # not checkable
- [ ] Add the entity and wire up the handler     # "and" - two items
```

### Specify the unhappy paths

**This is where agents invent, and where review cannot save you.** If an item
describes behaviour, state what happens when it fails, repeats, or hits a
boundary, as nested lines under the item:

```markdown
- [ ] `Reserve` is idempotent by checkout_session_id
      - replay with the same id returns the existing hold, does not decrement stock
      - insufficient stock → `ErrInsufficientStock`, no partial hold created
      - hold already expired → treat as a new reservation
```

An item that changes behaviour and states no failure behaviour is not ready.

### Say what the tests must prove

A behavioural item names its test expectation, or has an explicit test item
next to it. Otherwise "done" is the agent's opinion.

```markdown
- [ ] Test: concurrent Reserve on the same SKU never oversells
```

### Bound the scope, including behaviour

"Out of scope" names every `read-only` and `untouched` service from the
service map, and says what the agent must not do inside its own repo - the
most common autonomous failure is a correct change wrapped in three
unrequested ones.

### Acceptance must be checkable from the repo

The builder runs nothing. `/pave:review` checks each item against the code,
then runs the service's `codegen`, `build`, `test` and `lint` once all its
tasks are built. So "done when" has to be visible in the repository or in the
output of those commands.

### Carry the mechanics

Pull `build`, `test` and `lint` for the target service out of
`workspace.yaml` into the Verification section. They are there for the
reader; the builder does not run them.

Write code the builder can get right without compiling it: exact
identifiers, exact signatures, the imports a new file needs. A slip the plan
could have prevented comes back from review as a failed task.

### Keep parallel work apart

Build runs every task whose `depends_on` are done at the same time, in the
same service as readily as in different ones. Nothing but your `depends_on`
keeps two tasks apart. Add one wherever:

- two tasks name the same place - the same file, or a folder and a file in it.
  Two builders writing one file at once overwrite each other's work
- one task needs another's result - a library that must publish before
  consumers bump it, a migration others read, infra that must exist first, a
  revert that must land before work in the same place or in a caller

Tasks that name different places, with no result between them, need none -
in one service or in two. Do not add an edge "to be safe": every one costs
parallelism, and `pave.sh overlaps` finds the ones you need.

## 6. Readiness check — hard gate

The fan-out is only as safe as its weakest brief. Which task documents are
checked depends on the level:

| Level | Checked |
|---|---|
| initial plan, `full` | every task document that is not `done` or `obsolete` |
| `scoped` | every task this revision wrote, rewrote or reopened, and every task that provides or consumes an interface it changed |
| `quick` | every task this revision re-projected |

Has tasks, Complete, Numbering and Separated are about the plan as a whole:
they always cover every task.

| Check | Fails when |
|---|---|
| Has tasks | A `modify` service in the service map has no task |
| Separated | Two tasks that are not `done` or `obsolete` name the same place and no `depends_on` path orders them. The orchestrator runs `pave.sh overlaps` and hands you what it finds |
| Interfaces | A field it provides or consumes is missing from its Interfaces table or items, or differs from `plan.md`'s Interfaces table |
| Verification | No build/test command carried over from `workspace.yaml` |
| Acceptance | No "done when" |
| Out of scope | Does not name the `read-only` and `untouched` services |
| Self-contained | Refers to another task document, to a previous version of itself, or to the plan discussion, or relies on the builder reading `plan.md` |
| Projected | Says something `plan.md` does not - a change that lives only in the task |
| End state | Describes a change from before ("change 15 to 30") instead of what must be true |
| Grounded | Touches existing behaviour without naming the code it extends |
| Located | Changes or removes a behaviour without an item for every place it lives in the code |
| Traceable | No `derives_from`, or an item with no plan decision behind it |
| Satisfies | No criterion in `satisfies`, and the task reverts nothing |
| Complete | A criterion, a plan decision, or an interface field on its producer or any consumer side, with no task implementing it |
| Sized | An item needing "and" to state, a task split by layer, or size `L` |
| Unhappy paths | A behavioural item states no failure, replay or boundary behaviour |
| Tested | A behavioural item names no test expectation |
| Reverts | An obsolete task no row's `Reverts` names, or a task that reverts others without stating what must be gone |
| Numbering | A number reused, or not from `next_task` |

On failure, name the gap and fix it. A failure you can fix from the approved
plan is yours to fix. A failure that needs a decision goes back to the user,
and the change goes through the gate again. Never let `/pave:build` proceed
and fix it later - that is the builder making plan decisions.
