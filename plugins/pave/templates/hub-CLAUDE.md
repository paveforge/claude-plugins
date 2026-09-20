# <Hub name>

This is a Pave hub: the central command folder for cross-service feature work.
Specs, designs, contracts and task documents live here. The service repos are
reachable through `additionalDirectories` and are modified only by build agents.

## Layout

- `config.yaml` - team policy. Committed, shared.
- `workspace.yaml` - your repos. Local, gitignored, source of truth.
- `conventions/` - how code is written, by language and service. Yours to edit.
- `features/` - the durable record of what was decided.
- `artifacts/` - disposable. Delete anything here and it regenerates.
- `artifacts/knowledge/` - what each service does, written by `/pave:analyse`.
  Derived from code, so it is disposable; its index is what lets design load
  selectively instead of scanning everything.

## Workflow

`/pave:init` → `/pave:analyse` → `/pave:design` → gate 1 → gate 2 →
`/pave:build` → `/pave:review`

`init` records how to build each repo. `analyse` records what each service
does. Design needs both: without the second it writes concrete tasks that
contradict code which already exists.

## Rules

**Contracts are frozen at gate 2.** They change by re-running `/pave:design`,
never by editing them in a service repo. The freeze is what lets services be
built in parallel; a local edit breaks every service building against it.

**Task documents are self-contained.** An agent executing one has not seen the
design discussion and cannot read the others.

**Escalate, do not improvise.** A gap in a task document is a design defect.
Report it rather than guessing - the hub can see every service, the agent
cannot.

**The roll-up READMEs are generated.** `features/README.md` and each feature's
`README.md` are rewritten from task frontmatter. Do not hand-edit them.

## Conventions

<Cross-cutting rules that apply to every repo. Language-specific rules belong
in `conventions/<language>.md`, which is loaded only when a task targets that
language.>
