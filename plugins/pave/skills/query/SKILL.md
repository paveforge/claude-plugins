---
name: query
description: Ask a question about this hub - how something works across services, a convention, why a feature is stuck. Answers from the knowledge base first; when that cannot answer a question about how the code behaves, reads the source, answers, and saves the answer as an on-demand finding that /pave:analyse never erases. Use any time.
argument-hint: "<question>"
allowed-tools: Bash, Read, Write, Glob, Grep, Agent
---

# Pave — query

Answer one question about this hub, as cheaply as the question allows.

| Step | Reads | When |
|---|---|---|
| 1. Retrieve | The knowledge base, on-demand knowledge, conventions, hub docs | Always |
| 2. Read the source | Only the code the question needs | Only when step 1 cannot answer a question about how the code behaves |
| 3. Save | One on-demand finding | Only after step 2 |

So a question the knowledge base already answers costs one small agent, and a
question it cannot answer is paid for once: the next person to ask gets the
saved finding.

This skill orchestrates. The reading and answering happen in agents, keeping
this session's context free for whatever you do next.

For questions about Pave itself - "what does `/pave:build` do" - use
`/pave:help` instead; it needs no hub and no agent.

## Before starting

Locate the hub (walk up for `.pave-hub`). If none is found, stop and say to
run `/pave:init` first. Read the hub's config file (`config.yaml`,
`config.yml` or `config.toml`) and `workspace.yaml` if they exist.

## 1. Retrieve

### Gather paths, not content

Do not read these yourself - you are collecting what to hand the retriever.
Note which exist:

- `artifacts/knowledge/README.md` — the index, including its On-demand section
- `artifacts/knowledge/on-demand/` — source findings and feature records
- `conventions/README.md`, and any per-language or per-service file under
  `conventions/`
- the hub's `AGENTS.md`
- `workspace.yaml`
- if the question names a feature, `/pave:spec` set one in this session, or
  the hub has exactly one, that feature's `spec.md`, `plan.md` and `README.md`

Then run `"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh stale` and keep its
`finding-stale` and `stale` lines. The retriever must know which findings and
which service analyses no longer match the code; it cannot run the check
itself.

### Spawn the retriever

One `retriever`, with the `model` and `effort` printed by
`"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh agent retriever`, given: the question
verbatim, every path gathered above labelled with what it is, and the stale
lines. Nothing else.

It returns an answer with citations, and - if it could not answer all of it -
the gap, classified:

| Gap | Means | Next |
|---|---|---|
| none | Answered | Relay it (§4) |
| `source` | A question about how the code behaves that knowledge does not cover, or covers only with something stale. Names the services it concerns | §2 |
| `other` | Not about the code - a decision nobody recorded, a feature that does not exist, a convention nobody wrote | Relay it, and what would resolve it. Never read source for it |

## 2. Read the source

Only for a `source` gap. The question decides what is read, not the
service: the analyst follows the question through the code and stops when it
can answer.

For each service the gap names (add any the index shows at the seam - an
event the flow emits, a service that consumes it):

- its repo path and `path` from `workspace.yaml`
- **its current commit**: `git -C <repo> rev-parse HEAD`. The analyst has no
  Bash, and without the commit the finding can never be checked for staleness
- its knowledge files, if it has any that are not stale - as a map of where to
  start, not as the answer

Choose the finding's file: `artifacts/knowledge/on-demand/source/<slug>.md`,
a short kebab-case slug of the question. If a stale finding answers the same
question, reuse its file - the new answer replaces it.

Spawn one `analyst` in **question mode**, with the `model` and `effort`
printed by `pave.sh agent analyst`, given: the question verbatim, the services
above, the finding's path, `templates/knowledge-finding.md`, and the hub's
`AGENTS.md` if it exists. It reads the code, writes the finding, and returns
the answer.

If it returns nothing, or says it could not answer, no finding is written and
nothing is saved - say what it could not determine. A guessed finding in the
knowledge base is worse than none: the planner will trust it.

## 3. Rebuild the index's On-demand section

After a finding is written, rebuild **only** the On-demand section of
`artifacts/knowledge/README.md`, from the frontmatter of every file under
`on-demand/source/` and `on-demand/features/`, with each finding's state from
`pave.sh stale`. Leave every other section as it is - those are
`/pave:analyse`'s. If there is no index yet, write one from
`templates/knowledge-README.md` with only the On-demand section filled.

## 4. Relay the answer

Pass it through as the agent wrote it - it already cites its sources.
Softening or re-deriving it here reintroduces the mistake delegation exists to
avoid. If a finding was saved, say where, in one line. If part of the
question could not be answered, say which part plainly, and what would resolve
it.
