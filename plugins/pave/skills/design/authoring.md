# Pave — design: writing the design outputs

Read by whoever writes the design outputs: `/pave:design` itself when it designs
in-session, or the `designer` agent when it is spawned. Where this file says
"present" at a gate, a spawned designer returns its summary instead; the
orchestrator presents it.

## 2. Spec

Write `features/<feature-id>/spec.md` from `templates/spec.md`: what and why,
user-visible behaviour, acceptance criteria for the feature **as a whole**.

Feature-level acceptance matters and is easy to skip. In a per-service model
nobody owns "does checkout actually work end to end" — every service can pass
its own criteria while the seams are broken. Write it here or no one will.

## 3. Architecture

Write `features/<feature-id>/architecture.md` from `templates/architecture.md`. This
file is the source every task is derived from, so it has to be sufficient on
its own.

### The sufficiency test

**Could someone write every task document from this file alone, without asking
you a question?**

That is not a stylistic bar, it is a correctness one. You may write the tasks
in a fresh context that remembers none of your reasoning — the spawned path
does exactly that, stage 2 reading this file off disk with no memory of stage
1. Anything you decided but did not write down is gone, and the task-writer
will invent a replacement that looks reasonable and is not what you meant.

So the rule is: **write down the reasoning, not only the conclusion.** The two
modes must produce the same quality, and this file is the only thing that
guarantees it.

### What it must contain

**Named sections with stable anchors.** Tasks cite `architecture.md#<section>`
in `derives_from`. Prose without headings cannot be cited, and an uncitable
decision cannot be checked.

**Each decision, with its rationale.** What was decided, why, and what was
rejected. The rejected alternative matters most: without it, a task-writer
looking at the same problem may quietly re-derive the option you ruled out.

**The flow, step by step** — which service does what, in order, and what it
emits.

**The unhappy paths, at the cross-service level.** What happens when each step
fails: what retries, what compensates, what is left inconsistent and for how
long, what the caller sees. This section is what §5 projects into per-item
failure behaviour. If it is not here, tasks cannot state it, and builders will
invent it one repo at a time — four services each picking something sensible
and none of them agreeing.

**State ownership** — which service owns which piece of state, and who may
read it.

**Assumptions** you had to make, stated plainly, so gate 1 can challenge them.

## 4. Contracts — frozen, and generated

Write the contracts into `features/<feature-id>/contracts/`.

Every contract states: exactly one producer, its named consumers, a
compatibility stance (additive-only, versioned path, new topic), and whether
stubs are generated or hand-written.

The format is whatever the services already use — protobuf, OpenAPI, GraphQL,
JSON Schema, Avro. If a team has no IDL, a markdown table of fields and
semantics is a valid contract. What is required is the producer, the consumers
and the compatibility stance, not the syntax.

**The freeze is what buys the parallelism.** Once the interface is fixed and
its stubs exist, order-service and payment-service stop depending on each
other's in-flight code and can be built at the same time. If contracts are
still soft when the agents spawn, they will diverge and reconciling costs more
than the fan-out saved.

### → Gate 1

Present the spec, the architecture **and the contracts**. Stop and wait for
approval. Do not write task documents yet.

Contracts are approved here, with the architecture they belong to, because an
interface between two services is a design decision and not an implementation
detail. Deciding it at the same moment as the flow and the state ownership is
what lets them be judged together.

It also puts the objection where it is cheap. "This should be an event, not a
synchronous call" invalidates every task derived from that contract — so it
has to be asked before those tasks exist, not after you have read twenty of
them.

**On approval the contracts are frozen.** From here they change only by
re-running design, never by an agent in a repo.

## 5. Task documents

Write one document per unit of work into `features/<feature-id>/tasks/`, named
`NN-<feature-id>.md`, from `templates/task.md`.

This is the most important output of the phase. Everything downstream executes
these documents without question: a builder does what the document says, and
review checks only whether it did. Anything the document leaves open, an agent
invents — and nothing downstream will catch it, because the plan never asked
for it.

So the test for every line is: **could a competent stranger do this without
asking a question?**

**Each task names exactly one target service** and must stand alone. The agent
that executes it never saw this conversation and cannot read its sibling
documents.

### Derivation is the whole job

The tasks are a **projection** of `architecture.md` and the contracts into
per-service briefs. They are not a second act of design, and nothing in them
should be true for the first time.

Write them all in one pass, seeing the whole feature, so the set is
consistent: what one service emits, another handles; what one stops sending,
another stops expecting.

**Cite the source.** Every task names, in frontmatter, the design sections and
contracts it comes from:

```yaml
derives_from:
  - architecture.md#reservation-expiry
  - architecture.md#state-ownership
  - contracts/stock.v1.proto
```

This is not bookkeeping. A builder cannot see `architecture.md` — its task
document is its whole world — so it has no way to tell a designed decision
from something the task-writer invented. The citation is what lets a human at
gate 2 check, and it forces the question while you write: *where does this
come from?* **If you cannot cite a source for an item, you are inventing it.**
Either the design is incomplete — go back and fix it, then re-derive — or the
item does not belong.

**Check coverage in both directions.** Grounding each task in the design is
only half of it:

| Direction | Question | Failure |
|---|---|---|
| Task → design | Does every item trace to a decision? | Invented work |
| Design → task | Does every decision have an item? | Silently dropped work |

The second is the one that gets missed, and it is the more expensive. After
the tasks are written, walk `architecture.md` decision by decision and every
contract message field by field, and find the task that implements each. A
decision with no task will not be built, nothing downstream will notice, and
review will pass the feature — because review asks whether the plan was
followed, and the plan never asked.

### How many tasks

One task is **one coherent unit of work in one service that could be committed
on its own**. Split where the work has a natural seam — the API and the
background sweeper that expires its rows are two tasks; they are reviewed
separately and could land separately.

Never split by architectural layer. "Domain", then "repository", then
"handlers" is three tasks that cannot be committed or reviewed independently,
and it reintroduces the phase scaffolding this design removed.

A service with thirty items in one task should have been two or three tasks.
A service with two items in three tasks should have been one.

### What an item looks like

An item is **one focused change you can state in a single sentence without
using "and"**. That is the sizing rule: if the sentence needs an "and", it is
two items.

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

Ordering is top to bottom. An agent that wants to write models before handlers
will do that anyway; it does not need to be told.

### Specify the unhappy paths

**This is where agents invent, and where review cannot save you.** If an item
describes behaviour, state what happens when it fails, repeats, or hits a
boundary. Put it as nested lines under the item:

```markdown
- [ ] `Reserve` is idempotent by checkout_session_id
      - replay with the same id returns the existing hold, does not decrement stock
      - insufficient stock → `ErrInsufficientStock`, no partial hold created
      - hold already expired → treat as a new reservation
```

The checkbox stays one sentence, so it is reviewable. The nested lines are the
specification the builder implements and the reviewer compares against — they
are what turns "it exists" into "it does what we said".

An item that changes behaviour and states no failure behaviour is not ready.
The agent will pick something reasonable, review will pass it because the plan
never said otherwise, and you will find out in production.

### Say what the tests must prove

A behavioural item names its test expectation, or has an explicit test item
next to it. Otherwise "done" is the agent's opinion, and review can only check
that *some* test exists.

```markdown
- [ ] Test: concurrent Reserve on the same SKU never oversells
```

### Bound the scope, including behaviour

"Out of scope" is not only about other services. Say what the agent must not
do inside its own repo — the most common autonomous failure is a correct
change wrapped in three unrequested ones.

```markdown
## Out of scope
- Do not modify order-service or payment-service. Agents are working there now.
- Do not refactor the existing allocation logic; it is used elsewhere.
- Do not upgrade dependencies or reformat files you did not otherwise change.
```

### Acceptance must be checkable from the repo

`/pave:review` reads code and runs nothing, so "done when" has to be visible in
the repository or in the verification commands. "Checkout completes in under
two seconds" cannot be reviewed; "the sweeper releases holds past expires_at,
covered by a test" can.

### Carry the mechanics

Pull `build`, `test` and `lint` for the target service out of `workspace.yaml`
into the Verification section. The agent must not have to rediscover how to
build the repo.

Mark a cross-service `depends_on` only where one genuinely exists — a library
that must publish before consumers bump it, a migration others read, infra that
must exist first. With contracts frozen these should be rare. **A plan full of
`depends_on` is a signal, not a schedule**: it means the contracts were not
really frozen. Say so at the gate rather than quietly producing a five-wave
rollout.

## 6. Readiness check — hard gate

The fan-out is only as safe as its weakest brief, so the weakest brief blocks
it. For **every** task document:

| Check | Fails when |
|---|---|
| Has tasks | Service in the blast radius with no tasks written |
| Contract slice | Any contract it consumes or provides is missing or still draft |
| Verification | No build/test command carried over from `workspace.yaml` |
| Acceptance | No "done when" |
| Out of scope | Not stated |
| Self-contained | Refers to another task document, or to this conversation |
| Grounded | Touches existing behaviour without naming the code it extends |
| Traceable | No `derives_from`, or an item with no design decision behind it |
| Complete | A decision in `architecture.md` or a contract with no task implementing it |
| Sized | An item needing "and" to state, or a task split by architectural layer |
| Unhappy paths | A behavioural item states no failure, replay or boundary behaviour |
| Tested | A behavioural item names no test expectation |
| Scope bounded | Out of scope does not cover behaviour inside the repo |
| Checkable | "Done when" cannot be verified by reading the repo |

On failure, name the gap and stop. Do not fan out. Do not let `/pave:build`
proceed and fix it later — that is the cheap model making design decisions,
which is the one thing the split is meant to prevent.

### → Gate 2

Present the task documents and the readiness result. Stop and wait for
approval.

The contracts were settled at gate 1, so this gate asks one question only:
**are these briefs executable without further decisions?**
