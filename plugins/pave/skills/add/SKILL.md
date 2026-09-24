---
name: add
description: Register service folders with the Pave hub. Records each absolute path in workspace.yaml and grants Claude access to it. Use after /pave:init, and whenever a service joins the platform.
argument-hint: "<folder> [more folders...]"
allowed-tools: Bash
---

# Pave — add

Run the script. It does the whole job:

```
"${CLAUDE_PLUGIN_ROOT}"/scripts/pave.sh add $ARGUMENTS
```

Registering a folder is entirely deterministic — validate, resolve to an
absolute path, append to `workspace.yaml`, merge into `additionalDirectories`.
A script does that faster and more reliably than a model editing YAML and JSON
by hand, and it costs no context.

Run it from the hub, or anywhere below it; it walks up for `.pave-hub`.

## Then relay what it reports

Each line is one folder:

| Prefix | Meaning | What to say |
|---|---|---|
| `added` | Registered | Nothing more, unless it carries a git warning — a folder without git cannot take a branch, so builders will not be able to commit there |
| `skip` | Already registered, missing, or inside the hub | Say which and why |
| `CLASH` | Name taken by a different path | **Stop and ask.** Two services with one name make task documents ambiguous about which repo they target, and a builder has no way to tell. Offer to add it under a different name — the script takes the folder name, so renaming means moving or symlinking, or editing `workspace.yaml` by hand |
| `WARN` | `settings.json` could not be updated | Tell them to add the path to `additionalDirectories` themselves. **This is not cosmetic** — without it agents cannot read or write that repo, however correctly `workspace.yaml` describes it |

If anything was added, point at `/pave:analyse`: Pave now knows where these
services are and nothing else about them.

Do not edit `workspace.yaml` or `settings.json` yourself. If the script cannot
do something, say so — a hand edit here and a script edit next time is how the
two drift apart.
