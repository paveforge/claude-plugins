---
service: <service-name>
analysed_at: <date>
source_paths: [<dirs the analysis actually rests on - these decide staleness. Never build output, dependencies or generated code>]
# source_hash is added here by `pave.sh stamp` once the analysis is finished:
# the hash of the content under source_paths. Never write it by hand.
capabilities: [<business phrases, not function names>]
terms: [<domain vocabulary this service owns>]
emits: [<events>]
consumes: [<events>]
uncertain:
  - "<what could not be determined, and why it matters>"
---

# <service-name>

<What this service is for, in two or three lines.>

## Owns
<The state and decisions that belong to this service.>

## Does not
<What it deliberately leaves to others. This prevents planning putting work
in the wrong place.>

## Shape
<Entry points, layering, anything unusual about how it is organised.>

<!-- 50 lines maximum. Detail belongs in domain.md, flows.md,
     integration.md and data.md. -->
