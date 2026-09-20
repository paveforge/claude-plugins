---
service: <service-name>
feature: <feature-slug>
status: pending            # pending | in-progress | done | blocked
depends_on: []
branch: feature/<feature-slug>
---

# <What this task achieves>

## Objective & Context
**Goal:** <1-2 sentences on what we are building and why>
**Out of scope:** <services and areas not to touch. Name them explicitly -
agents are working in those repos in parallel.>

## Architecture & Data Contracts
**Data structures / schema:** <entities, migrations, DTOs>
**API contracts:** <path to the contract file>
**Contract status:** FROZEN at gate 2. Stubs generated and committed in <sha>.
Do not edit the contract or its generated files.

## Cross-Service Dependencies
| Direction | Service | Contract | Note |
|---|---|---|---|
| provides | <service> | <contract> | you own this |
| consumes | <service> | <contract> | stub landed; being built in parallel |

## Tasks
- [ ] <concrete, verifiable, one service - names the file, type, endpoint or migration>
- [ ] <not "add validation">

## Verification
Build `<command>` · Test `<command>` · Lint `<command>`
**Done when:** <criteria for this service>

## If the contract is wrong
Stop and report to the hub. Do not change the contract locally - other
services are building against it.
