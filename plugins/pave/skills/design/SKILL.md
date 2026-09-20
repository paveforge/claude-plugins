---
name: design
description: Plan a feature across every service it touches. Finds the blast radius, writes the spec and architecture, freezes the contracts, and produces one self-contained task document per unit of work. Use before building any feature that spans more than one service.
effort: high
argument-hint: "<feature description> | <existing feature slug to re-design>"
---

# Pave — design

Design the feature once, across all services, with contracts defined first.

This is the phase the whole plugin exists for, and the one the feature lives or
dies on. Everything downstream executes what is decided here; nothing
downstream is allowed to redesign it. Spend the effort here.

## Re-designing an existing feature

Given an existing feature slug instead of a description, re-design that
feature. This is the route back when the **design** was wrong rather than the
execution — a missed case, a contract that cannot express what is needed.

**Re-design the whole feature. Do not patch it.**

The temptation is to find the one case that was missed, add a task for it and
leave everything else alone. Resist it: you cannot know that only one case was
missed. A patched design produces tasks that are each individually reasonable
and collectively inconsistent — a service handling a state its caller never
sends, an error path nobody raises — and that is the hardest kind of defect to
see, because every task looks fine on its own.

So run the whole phase again: re-read the knowledge, re-derive the blast
radius, re-examine the architecture, and rewrite every task from it. Keep what
still holds — this is re-deriving, not discarding — but derive it, do not
assume it.

Set the feature to `planning` while you work. Contracts are re-frozen at gate
2, so any task already built against a contract that changed goes back to
`pending`.

The user decides when this is the right move. Do not re-design because a build
agent found something awkward.

## Before starting

Locate the hub by walking up for `.pave-hub`. Read `config.yaml` and
`workspace.yaml`. If either is missing, stop and tell the user to run
`/pave:init`.

Check the session model against `agents.designer.model`. If the session is on a
weaker model, say so and ask whether to continue:

```
config.yaml sets agents.designer.model: opus, this session is on sonnet.
Planning quality decides the whole feature. Continue anyway? [y/N]
```

Say it once and respect the answer. Do not switch models — that decision is
the user's.

## 1. Blast radius — from the knowledge index

Work out which services the feature touches before writing anything. This is
the step that justifies planning centrally: the answer is usually wider than
the person asking expects.

Load knowledge in stages. Never scan every service, and never read a knowledge
file the index did not point you at.

| Stage | Load | Purpose |
|---|---|---|
| 1 | `artifacts/knowledge/README.md` — **only this** | Match the feature against capabilities, terms and events |
| 2 | `knowledge/services/<candidate>/README.md` | Confirm or drop each candidate. ~50 lines each |
| 3 | The files the index named | `domain.md` for services being modified, `integration.md` for services at the seam |

A four-service feature in a twelve-service platform reads one index, four
summaries and a handful of deep files. That is the whole point of the index
existing.

Read the Terms table carefully. The most expensive mistake this phase can make
is a vocabulary miss — designing a `Reservation` into a service that has named
that concept `StockHold` for two years. The task will be concrete, confident
and wrong, and an agent will build it.

Then confirm against `consumes` edges in `workspace.yaml` and the events table.
Topological coupling and domain coupling are different: an import graph will
not tell you that checkout touches stock because reservations expire.

### When knowledge is missing or stale

Never proceed blind, and never stop to send the user away. Check each
candidate for staleness the way `/pave:analyse` does — whether its
`source_paths` have changed since its recorded `commit` — then spawn `analyst`
agents for anything missing or stale, using `agents.analyst.model`, and
continue once they return.

Say what you are doing and why, in one line. Do not ask permission for it.

### Uncertainty is not knowledge

Every `uncertain:` entry on a service you are about to design against must be
resolved by reading the code yourself, not carried forward. The analyst
flagged it precisely because it could not tell. If it bears on the feature,
verify it; if you cannot, say so at gate 1 rather than designing over it.

Report the radius and ask before continuing:

```
"Build checkout" appears to touch:
  order-service     orchestrates the flow                  confident
  stock-service     must reserve inventory                 confident
  payment-service   must authorise payment                 confident
  notification-service  confirmation email                 likely
  web-checkout      new UI flow                            likely
  shared-events     new OrderCheckedOut schema             likely

Missing anything?
```

A service the user adds here is worth more than three you inferred.

## 2. Spec

Write `features/<slug>/spec.md`: what and why, user-visible behaviour,
acceptance criteria for the feature **as a whole**.

Feature-level acceptance matters and is easy to skip. In a per-service model
nobody owns "does checkout actually work end to end" — every service can pass
its own criteria while the seams are broken. Write it here or no one will.

## 3. Architecture

Write `features/<slug>/architecture.md`: the cross-service approach, the flow
through the services, the failure and rollback behaviour, and which service
owns which piece of state.

### → Gate 1

Present the spec and architecture. Stop and wait for approval. Do not write
contracts or tasks yet.

## 4. Contracts — frozen, and generated

Write the contracts into `features/<slug>/contracts/`.

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

## 5. Task documents

Write one document per unit of work into `features/<slug>/tasks/`, named
`NN-<slug>.md`, from `templates/task.md`.

**Each task names exactly one target service** and must stand alone. The agent
that executes it never saw this conversation and cannot read its sibling
documents. Everything it needs is in its own file or it will guess.

**Every task traces to the design.** The tasks are an output of `architecture.md`
and the contracts, not a separate act of invention. A task that does not follow
from the design is a defect — either the design is incomplete, in which case fix
the design and re-derive, or the task does not belong. Write them all in one
pass, seeing the whole feature, so the set is consistent: what one service
emits, another handles; what one stops sending, another stops expecting.

No phase scaffolding — no "Domain & Models" headings. List the actual tasks the
service must do. Without a scaffold to hide behind, each line has to be:

- **Concrete** — names the file, type, endpoint or migration, not "add validation"
- **Verifiable** — you can tell from the repo whether it is done
- **Owned by one service**

```markdown
- [ ] `Reservation` entity: SKU, qty, checkout_session_id, expires_at, Expired state
- [ ] Migration `reservations` + unique index on (checkout_session_id, sku)
- [ ] `Reserve` idempotent by checkout_session_id - returns existing on replay
```

not

```markdown
- [ ] Phase 1: Domain & Models
```

Ordering is top to bottom. An agent that wants to write models before handlers
will do that anyway; it does not need to be told.

**Ground every task in code that exists.** A task touching existing behaviour
names the type, file or flow it extends, taken from that service's knowledge
files. A task that is genuinely new says so. This is what separates specific
from specific-and-wrong, and it is the whole reason `/pave:analyse` runs.

```markdown
- [ ] Extend `StockHold` (internal/domain/hold.go) with expires_at + Expired state
```

not

```markdown
- [ ] Add a Reservation entity with a TTL
```

Pull `build`, `test` and `lint` for the target service out of `workspace.yaml`
into the document's Verification section. The agent must not have to rediscover
how to build the repo.

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

On failure, name the gap and stop. Do not fan out. Do not let `/pave:build`
proceed and fix it later — that is the cheap model making design decisions,
which is the one thing the split is meant to prevent.

## 7. Write the roll-ups

- `features/<slug>/README.md` — one row per task, from task frontmatter
- `features/README.md` — one row per feature, status `ready`

### → Gate 2

Present the contracts, the task documents and the readiness result. Stop and
wait for approval. On approval the contracts are frozen: from here they change
only by re-running design, never by an agent in a repo.
