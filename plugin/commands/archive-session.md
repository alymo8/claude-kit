---
description: Archive this conversation from within it (it leaves the Vibe sessions list; reversible), or restore an archived one
disable-model-invocation: true
---

Archive the conversation you are in, so it leaves the sessions list in
Mistral Vibe without deleting it, or restore one that was archived.

If Vibe's session storage (`~/.vibe/logs/session/unified/`) is missing
(the script reports it), say the command works only in Mistral Vibe and
stop. Where `${CLAUDE_PLUGIN_ROOT}` is not expanded, use the plugin root
stated in the kit map in its place.

## Archive this session

1. Run and show the token it prints:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/archive-session.py" token
   ```

2. Immediately (the token is only matched in journals written within a
   quarter hour) run, with the token from step 1 in place of `TOKEN`:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/archive-session.py" archive --token TOKEN
   ```

   Neither call waits on the user; run them back to back.

3. Show the second command's output verbatim, then tell the user:
   - The conversation now shows as archived in the sessions list; the
     open window stays usable, but once they close it, it is only
     reachable again after a restore.
   - Nothing was deleted: the full transcript stays on disk and a
     restore brings the conversation back exactly as it was.
   - Archiving sticks best as the last thing they do in the
     conversation: using it again can bring it back to the list.
   - To restore it later, run this command with `restore` (below) from
     any session in the same project.

## Restore an archived session

1. Run:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/archive-session.py" restore
   ```

2. When it lists candidate sessions, show the id, archived-at and title
   lines verbatim and ask the user which to restore. Do not guess.
3. With their choice, run:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/archive-session.py" restore --session-id ID
   ```

   Show its output verbatim. A line `already active` or
   `no archived sessions` means nothing to do; say so and stop.

Status of the current session (one round trip, like archive):

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/archive-session.py" status --token TOKEN
```
