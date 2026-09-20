---
name: design
description: Plan a feature across every service it touches. Finds the blast radius, writes the spec and architecture, freezes the contracts, and produces one self-contained task document per unit of work. Use before building any feature that spans more than one service.
effort: high
argument-hint: "<feature description>"
---

# Pave — design

Design the feature once, across all services, with contracts defined first.

This is the phase the whole plugin exists for, and the one the feature lives or
dies on. Everything downstream executes what is decided here; nothing
downstream is allowed to redesign it. Spend the effort here.

## Before starting

Locate the hub by walking up for `.pave-hub`. Read `config.yaml` and
`workspace.yaml`. If either is missing, stop and tell the user to run
`/pave:init`.

Check the session model against `phases.design.model`. If the session is on a
weaker model, say so and ask whether to continue:

```
config.yaml sets phases.design.model: opus, this session is on sonnet.
Planning quality decides the whole feature. Continue anyway? [y/N]
```

Say it once and respect the answer. Do not switch models — that decision is
the user's.

## 1. Blast radius

Before writing anything, work out which services the feature touches. This is
the step that justifies planning centrally: the answer is usually wider than
the person asking expects.

Use `consumes` edges in `workspace.yaml`, then dispatch `explorer` agents
against the candidate repos to confirm. Use `agents.explorer.model`.

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
