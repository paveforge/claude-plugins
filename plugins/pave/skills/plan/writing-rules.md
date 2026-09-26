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

### The sufficiency test

**Could someone write every task document from `plan.md` and the contracts
alone, without asking you a question?**

That is a correctness bar, not a stylistic one. The tasks may be written by a
planner that remembers none of your reasoning - a fresh one, spawned because
yours could not be resumed. Anything you decided but did not write down is
gone, and the task-writer invents a replacement that looks reasonable and is
not what you meant. So: **write down the reasoning, not only the conclusion.**

### What it must contain

**Named sections with stable anchors.** Tasks cite `plan.md#<section>` in
`derives_from`. An uncitable decision cannot be checked.

**The service map.** Every service the feature was considered against, in one
of three states. This is what makes parallel building safe, so be exact:

| State | Means | Consequence |
|---|---|---|
| `modify` | Its code changes | It gets tasks, and a builder |
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
| Kind | `build` or `revert` |
| Priority | `low` for build, `high` for revert. `critical` is reserved - do not use it |
| Size | `S` (≤3 items), `M` (≤8), `L`. **An `L` must be split before the gate** |
| Satisfies | Criteria ids. A build task with none is invented work |
| Depends on | Only real cross-service ordering (see §5) |
| Change | What this revision does: `new`, `rewritten`, `reopened`, `obsolete`, `reverts NN`, `unchanged` |

**Always split into tasks, however small the feature.** One change is still
task `01`. A task is the unit that is built, rebuilt, reviewed and reverted on
its own, so the history of every change is a set of tasks.

**Build order.** Derive the waves from the table. Tasks in different services
run in parallel; tasks in the same service run one after another inside one
builder, highest priority first, then by number. More than one wave means a
real `depends_on` edge - say why each exists.

## 3. Contracts — frozen, and generated

Write the contracts into `features/<feature-id>/contracts/`.

Every contract states: exactly one producer, its named consumers, a
compatibility stance (additive-only, versioned path, new topic), and whether
stubs are generated or hand-written.

The format is whatever the services already use - protobuf, OpenAPI,
GraphQL, JSON Schema, Avro. If a team has no IDL, a markdown table of fields
and semantics is a valid contract.

**The freeze is what buys the parallelism.** Once the interface is fixed and
its stubs exist, services stop depending on each other's in-flight code and
can be built at the same time. If contracts are still soft when the builders
spawn, they diverge and reconciling costs more than the fan-out saved.

Contracts are approved at the gate with the plan, because an interface
between two services is a design decision, and "this should be an event, not
a synchronous call" has to be raised before any task is derived from it.

## 4. Re-planning

A re-plan starts from what changed, not from nothing.

**Find the difference.** Compare `spec.md` with `artifacts/spec.approved.md`
(the spec the current plan was approved against) and list every criterion,
guardrail and exclusion that was added, changed or removed. Follow
`plan.md` from those to the decisions they touch, and from the decisions to
the tasks (`satisfies:`, `derives_from:`). Re-read knowledge only for the
services those tasks touch.

**If nothing moved**, return `verdict: unaffected` and write nothing. That
means no criterion, guardrail, out-of-scope line or described behaviour
changed - only wording that no decision or task depends on. List the spec
differences you compared, so the user can check your judgement. When in
doubt, it moved: a changed word in a criterion is a changed criterion.

**Then classify every affected task.** A task document always describes the
**end state**, never a change: when the spec changes, you rewrite the document
in place to say what must be true now. Nothing in it records what it said
before - a builder reading it, or rebuilding it from scratch after a reset,
must reach the same result.

| The task is… | …and the spec | Do |
|---|---|---|
| not built (`pending`, never started) | still needs it, differently | Rewrite it in place. Stays `pending` |
| not built | no longer needs it | **Drop it** - list it under Delete for the orchestrator to remove. Nothing was built, so nothing needs reverting |
| built or started (`done`, `in-progress`, `failed`, `blocked`, `reopened`) | still needs it, differently | Rewrite it in place. Set `status: reopened`. **Untick only the items the change affects** |
| built or started | no longer needs it | Set `status: obsolete`. Add a **revert task** |
| any | is unaffected | Leave it untouched - its hash must not change |

**Unticking is how a reopened rebuild stays cheap.** A checkbox records
progress, not history: an unticked item says "this is not satisfied yet", never
"this used to say 15". The builder reconciles the existing code to the
document, working the unticked items; it discovers what differs by reading
the code.

**A revert task** removes the work of one or more obsolete tasks:

- `kind: revert`, `priority: high`, `reverts: [NN, …]`, a new number
- Each item names exactly what is removed - files, routes, handlers, config,
  flags - and the migration that reverses a schema change
- It states what must still work afterwards, and names the test that proves it
- **Anything that cannot be reversed automatically** - data that would be
  dropped, a published event schema, a migration that has already run in an
  environment - is not decided by you. List it at the gate for the user; write
  the agreed handling into the task afterwards

`priority: high` puts it first in its service's queue. If a revert must land
before work in **another** service - removing an endpoint another service must
first stop calling - that is a real ordering: write it as `depends_on`.
Priority never replaces `depends_on`.

**A contract change is a re-freeze.** Every built task that provides or
consumes a changed contract is reopened, and the gate says so.

**Tasks edited outside the plan.** If `pave.sh check` reported a task edited
by hand, decide from the spec what the document must say, write that, and
report at the gate what the hand edit was and whether you kept it. Never
adopt a hand edit silently.

### → The gate

Present the plan as a gate summary: each file's path with one line on what it
covers, the service map, the per-task changes on a re-plan, the decisions the
user must rule on, the "how" questions you could not settle, and anything
that cannot be reverted automatically. Stop. Do not write task documents yet.

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
that executes it never saw the plan and cannot read its sibling documents.

**Everything above `## Build notes` is yours and is hashed at the gate.**
Builders change only the status, the commit, checkboxes and the Build notes
section. Anything you want a builder to know goes above the line.

### Derivation is the whole job

The tasks are a **projection** of `plan.md` and the contracts into
per-service briefs. They are not a second act of design, and nothing in them
should be true for the first time.

Write them in one pass, seeing the whole feature, so the set is consistent:
what one service emits, another handles; what one stops sending, another
stops expecting.

**Cite the source.** Every task names the plan sections and contracts it
comes from, and the criteria it satisfies:

```yaml
satisfies: [AC-2, AC-4]
derives_from:
  - plan.md#reservation-expiry
  - plan.md#state-ownership
  - contracts/stock.v1.proto
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
decision and every contract field by field, and find the task that implements
each. A criterion with no task will not be built, and review will pass the
feature - because review asks whether the plan was followed, and the plan
never asked.

### How many tasks

One task is **one coherent unit of work in one service that could be
committed on its own**. Split where the work has a natural seam - the API and
the background sweeper that expires its rows are two tasks.

Never split by architectural layer. "Domain", then "repository", then
"handlers" is three tasks that cannot be committed or reviewed independently.

### What an item looks like

An item is **one focused change you can state in a single sentence without
using "and"**. If the sentence needs an "and", it is two items.

Each item must be:

- **Concrete** — names the file, type, endpoint or migration
- **Independently checkable** — review ticks and verifies items one at a time
- **Grounded** — names the existing code it extends, from the knowledge files

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

`/pave:review` reads code and runs nothing, so "done when" has to be visible
in the repository or in the verification commands.

### Carry the mechanics

Pull `build`, `test` and `lint` for the target service out of
`workspace.yaml` into the Verification section.

Mark a `depends_on` only where one genuinely exists - a library that must
publish before consumers bump it, a migration others read, infra that must
exist first, a revert another service must wait for. With contracts frozen
these should be rare. **A plan full of `depends_on` is a signal, not a
schedule**: it means the contracts were not really frozen.

## 6. Readiness check — hard gate

The fan-out is only as safe as its weakest brief. For **every** task document
that is not `done` or `obsolete`:

| Check | Fails when |
|---|---|
| Has tasks | A `modify` service in the service map has no task |
| Contract slice | Any contract it consumes or provides is missing |
| Verification | No build/test command carried over from `workspace.yaml` |
| Acceptance | No "done when" |
| Out of scope | Does not name the `read-only` and `untouched` services |
| Self-contained | Refers to another task document, to a previous version of itself, or to the plan discussion |
| End state | Describes a change from before ("change 15 to 30") instead of what must be true |
| Grounded | Touches existing behaviour without naming the code it extends |
| Traceable | No `derives_from`, or an item with no plan decision behind it |
| Satisfies | A build task with no criterion in `satisfies` |
| Complete | A criterion, a plan decision or a contract field with no task implementing it |
| Sized | An item needing "and" to state, a task split by layer, or size `L` |
| Unhappy paths | A behavioural item states no failure, replay or boundary behaviour |
| Tested | A behavioural item names no test expectation |
| Reverts | A revert task that does not name what it removes, or an obsolete task no revert names |
| Numbering | A number reused, or not from `next_task` |

On failure, name the gap and fix it. A failure you can fix from the approved
plan is yours to fix. A failure that needs a decision goes back to the user,
and the change goes through the gate again. Never let `/pave:build` proceed
and fix it later - that is the builder making plan decisions.
