---
name: compact
description: Get this conversation ready to compact without losing its place - writes a short brief holding the session's feature line and a concise summary of the recent work, then gives the /compact command that keeps it. Use when the context is getting long.
argument-hint: "[what else to keep]"
allowed-tools: Bash, Read, Glob
---

# Pave — compact

Claude Code's `/compact` replaces the conversation with a summary. A plain
summary can drop the one line every Pave command depends on - `Working on
<id> — <title>` - and then `/pave:plan`, `/pave:build`, `/pave:review` and
`/pave:learn` stop with "No feature in this session". This skill writes a
brief the summary must keep, then hands the user the `/compact` command that
keeps it.

A skill cannot run `/compact` itself. The user runs it; this skill makes what
survives worth having.

The brief is memory, not a source of truth. The files are: the commands
that act on the feature - `/pave:spec`, `/pave:plan`, `/pave:build`,
`/pave:review` and `/pave:learn` - read its `spec.md`, `plan.md` and tasks
from disk after a compaction, as they do at any other time. So the brief records **where the work is and what
is not on disk yet** - never a copy of a file.

## 1. The session's feature

Read `${CLAUDE_PLUGIN_ROOT}/reference/session.md` for how the session's
feature is found, but do not stop when there is none: a session without a
feature compacts too, and its brief says so. Never guess one, never take it
from a file or another session.

With a feature, locate the hub (walk up for `.pave-hub`) and read only the
Status line of `features/<id>/README.md`, and run:

```
SESSION_FEATURE_ID=<id> "${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh check
```

Check its `feature: <id>` line matches before using anything after it. These
give the brief the feature's state as the files say it, not as the
conversation remembers it. If either fails, say so in the brief and go on.

## 2. Write the brief

Output it once, in exactly this form, in a fenced block. Keep it under about
25 lines; a brief that restates the conversation is not a compaction.

```
Pave brief
Working on <id> — <title>
State: <Status from README> · <one line from pave.sh check>
Recent work:
- <what was done, newest last - one line each, at most 8>
Not on disk yet:
- <a spec edit proposed and not approved, a question asked and not answered,
  a choice the user made that no file records yet>
Next: <the command or step the conversation was about to take>
Keep: <the argument, if the user gave one>
```

- **Feature line.** Copy it verbatim from the latest `Working on` or
  `Switched` line - the exact characters, em dash included, because that is
  what the other commands look for. With no feature, write `No feature in
  this session` instead, and leave out `State`.
- **Recent work.** Outcomes, not steps: "sealed the plan, tasks 1-4",
  "review of task 3 failed on AC-2", not the commands that got there. Name
  files and task numbers rather than describing their content.
- **Not on disk yet.** Only what would be lost: anything already written to a
  file is left out. Write `nothing` when nothing is pending.
- Leave out tool output, file contents, and anything the user did not need.

## 3. Hand over the command

Below the brief, give the user this command to run, as it is. With no
feature, leave out the clause about the `Working on` line.

```
/compact Keep the "Pave brief" block from the last message word for word, and end the summary with its "Working on" line exactly as written. Summarise the rest in a few lines.
```

Then one line: after compacting, run the next command as normal - a command
that acts on the feature finds it from the brief, and reads the feature's
files from disk.
