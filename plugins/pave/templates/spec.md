---
feature: <feature-id>
version: 1            # bumped by /pave:spec on every approved change
---

<!-- The heading is the feature's title. When the folder is a ticket id it
     is the only human-readable name the feature has.

     This file is the user's. /pave:spec writes it only when the user approves
     a change. Everything downstream - plan, tasks, build, review - answers to
     it, so it states what must be true, never how to make it true. -->

# <Feature Name>

## Why
<The problem. What is broken or missing today, and for whom.>

## What
<User-visible behaviour. What changes for someone using the system. In the
platform's own vocabulary, not in services or code.>

## Acceptance criteria

<!-- For the feature as a whole. Every service can pass its own checks while
     the seams are broken - this is the only place that is caught.

     Each criterion has a stable id. Tasks cite them in `satisfies:`, so an id
     is never renumbered or reused: a removed criterion leaves a gap. Each one
     is observable and testable - no "fast", "robust" or "should probably". -->

- **AC-1** <end-to-end, observable outcome>
- **AC-2** <what happens when it fails, repeats, or hits a limit>

## Guardrails

<!-- What must not change or break while this is built: compatibility,
     performance budgets, security, data that must survive. Concrete enough to
     check. -->

- <e.g. existing v1 checkout clients keep working unchanged>

## Out of scope
<What this feature explicitly does not do.>

## Open questions

<!-- Anything not yet decided. /pave:plan refuses to plan while this list is
     not empty - a planner that meets an open question would have to answer
     it, and answering "what" is the user's job. Write "None." when empty. -->

- <question>
