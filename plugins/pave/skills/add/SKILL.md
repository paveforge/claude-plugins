---
name: add
description: Register service folders with the Pave hub. Records each absolute path in workspace.yaml and grants Claude access to it. Use after /pave:init, and whenever a service joins the platform.
argument-hint: "<folder> [more folders...]"
allowed-tools: Bash
---

# Pave — add

Run the deterministic registration script, then the Claude adapter that grants
this session access to every folder the script successfully registered:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh add $ARGUMENTS
python3 "${CLAUDE_PLUGIN_ROOT}"/adapters/claude/grant.py $ARGUMENTS
```

Registering a folder is entirely deterministic — validate, resolve to an
absolute path and append to `workspace.yaml`. The adapter separately merges
registered paths into `additionalDirectories`.
A script does that faster and more reliably than a model editing YAML and JSON
by hand, and it costs no context.

Run it from the hub, or anywhere below it; it walks up for `.pave-hub`.

## Then relay what it reports

Each line is one folder:

| Prefix | Meaning | What to say |
|---|---|---|
| `added` | Registered | Nothing more. If it notes the folder is not a git repository, pass that on as information only: builders will work there without a branch or commits, and nothing else changes |
| `skip` | Already registered, missing, or inside the hub | Say which and why |
| `CLASH` | Name taken by a different path | **Stop and ask.** Two services with one name make task documents ambiguous about which repo they target, and a builder has no way to tell. Offer to add it under a different name — the script takes the folder name, so renaming means moving or symlinking, or editing `workspace.yaml` by hand |
| adapter error | Claude access could not be updated | Pass the error on. **This is not cosmetic** — without it agents cannot read or write that repo, however correctly `workspace.yaml` describes it |

If anything was added, point at `/pave:analyse`: Pave now knows where these
services are and nothing else about them.

Do not edit `workspace.yaml` or `settings.json` yourself. If the script cannot
do something, say so — a hand edit here and a script edit next time is how the
two drift apart.
