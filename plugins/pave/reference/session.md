# The session's feature

`/pave:spec` sets the feature for this conversation. Use the latest
`Working on <id> — <title>` or `Switched: … → <id>` line. If there is none,
or you cannot find it, stop:

```
No feature in this session. Run /pave:spec <feature-id> first.
```

Never guess the feature or take it from a file or another session. Say
`Working on <id> — <title>` before continuing. These commands take no
feature argument; `/pave:build` may take task numbers.

**Every feature-scoped `pave.sh` call names the session's feature in its
environment**, never as an argument: `SESSION_FEATURE_ID=<id> pave.sh …`.
The script refuses without it and prints `feature: <id>` first. Check that
line matches the feature you announced before trusting anything after it.
Another session may be working on a different feature in the same hub at
the same moment; the variable keeps each call on this session's feature.
