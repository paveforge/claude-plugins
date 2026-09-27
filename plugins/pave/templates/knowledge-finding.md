---
kind: source-finding
question: <the question, as the user asked it>
answered_at: <date>
# One line per service whose code the answer rests on: the directories read.
# `pave.sh stamp` adds `hash:` to each line - the hash of their content - and
# `pave.sh stale` marks the finding stale the moment it changes. Keep this
# exact one-line form - the script parses it.
services:
  - { service: <service>, paths: [<dir>, <dir>] }
terms: [<platform terms the answer uses>]
uncertain:
  - "<what the code did not settle>"
---

<!-- Written by the analyst when /pave:query could not answer from the
     knowledge base. On-demand knowledge: /pave:analyse never rewrites or
     deletes it. 80 lines maximum. Cite file and line; never transcribe code. -->

# <The question, as a heading>

## Answer
<Direct answer, in the platform's vocabulary. Two to five sentences.>

## How it works
<Step by step, in the order it happens, across services. Each step names the
file (and line) it lives in, what triggers it, what it changes, what it emits.>

1. **<service>** — <what happens> (`path/to/file.go:42`)

## When it fails
<What each step does on failure, retry or boundary, as far as the code shows.>

## Not covered
<What the question touched but this finding did not read, so nobody reads
more into it than it says.>
