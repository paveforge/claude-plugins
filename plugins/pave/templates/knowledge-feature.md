---
kind: feature-record
feature: <feature-id>          # features/<feature-id>/ - the full spec, plan and tasks
title: <feature title>
spec_version: <n>
recorded_at: <date>
reviewed_at: <review-report timestamp>
# Per service: the commit its last task landed at. This is the system as the
# feature left it - history, not a live description. Later changes to the same
# code are found in the service analysis and in newer source findings.
services:
  - { service: <service>, commit: <sha> }
capabilities: [<business phrases the feature added, the way people ask for them>]
terms: [<terms the feature introduced or changed>]
emits: [<events added>]
consumes: [<events newly consumed>]
---

<!-- Written by /pave:learn once a feature was built and passed review against
     its current plan. On-demand knowledge: /pave:analyse never rewrites or
     deletes it. 100 lines maximum. Summarise and link; the feature folder
     holds the detail. -->

# <Feature title> (`<feature-id>`)

## What it does
<From spec.md: why and what, in two to four sentences.>

## Acceptance criteria, as delivered
| AC | Criterion | Tasks |
|---|---|---|
| AC-1 | <criterion> | 01, 03 |

## What changed, per service
| Service | Change | Commit |
|---|---|---|
| <service> | <one line per task outcome> | `<sha>` |

## Contracts
| Contract | Producer | Consumers |
|---|---|---|
| `features/<feature-id>/contracts/<file>` | <service> | <services> |

## Decisions worth knowing
<The plan decisions a later feature is most likely to bump into - state
ownership, sync versus async, what was rejected - each linked to
`features/<feature-id>/plan.md#<anchor>`.>
