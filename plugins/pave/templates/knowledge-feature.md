---
kind: feature-record
feature: <feature-id>          # features/<feature-id>/ - the full spec, plan and tasks
title: <feature title>
spec_version: <n>
spec_hash: <sha256>          # copied from plan.md at recording. `pave.sh stale` marks this
                             # record stale the moment features/<feature-id>/spec.md changes
recorded_at: <date>
reviewed_at: <review-report timestamp>
# Per service: the tasks built there. The system as the feature left it.
# Later changes to the same code by other work are found in the service
# analysis and in newer source findings.
services:
  - { service: <service>, tasks: [<NN>, <NN>] }
capabilities: [<business phrases the feature added, the way people ask for them>]
terms: [<terms the feature introduced or changed>]
emits: [<events added>]
consumes: [<events newly consumed>]
---

<!-- Written by /pave:learn once a feature was built and passed review against
     its current plan. On-demand knowledge: /pave:analyse never rewrites or
     deletes it. It describes one version of the spec: when the spec changes,
     the record is stale until the feature is re-planned, rebuilt, reviewed and
     learned again. 100 lines maximum. Summarise and link; the feature folder
     holds the detail. -->

# <Feature title> (`<feature-id>`)

## What it does
<From spec.md: why and what, in two to four sentences.>

## Acceptance criteria, as delivered
| AC | Criterion | Tasks |
|---|---|---|
| AC-1 | <criterion> | 01, 03 |

## What changed, per service
| Service | Change | Tasks |
|---|---|---|
| <service> | <one line per task outcome> | <NN, NN> |

## Interfaces
| Interface | Producer | Consumers | Built schema |
|---|---|---|---|
| `features/<feature-id>/plan.md#interfaces` - <element> | <service> | <services> | `features/<feature-id>/artifacts/contracts/<service>/<path>` |

## Decisions worth knowing
<The plan decisions a later feature is most likely to bump into - state
ownership, sync versus async, what was rejected - each linked to
`features/<feature-id>/plan.md#<anchor>`.>
