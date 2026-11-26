# ADR 0056: /archive-session archives a session from within it through Vibe's own flag

- **Status:** accepted
- **Date:** 2026-11-26

## Context

Archiving a conversation is a Vibe sessions-list action, out of reach from
inside the session: the desktop app offers it only from the list, and the
agent-facing API refuses to archive the session that calls it (only other
sessions). Users asked for a way to archive the conversation they are in
without leaving it.

Vibe keeps each session under `~/.vibe/logs/session/unified/<id>/` with a
`meta.json` whose `archived_at` timestamp is the archive state: setting it
archives the session (the sessions list picks it up live, verified on Vibe
Desktop); clearing it restores the session. The field is undocumented; a
session's shell environment carries no session id (`VIBE_SESSION=1` is only a
flag), and the app server rewrites `meta.json` often, preserving the flag.

Within a turn, a tool call's output lands in the session's own live journal
(`journal/<n>.jsonl`, appended in seconds) — `chunks/*.json` appears only at
turn boundaries.

## Decision
- **`/archive-session` flips `archived_at` itself.** The command's script
  (`plugin/scripts/archive-session.py`) sets or clears the field in the
  current session's `meta.json`; no Vibe API is involved. Worst case, if the
  storage format changes, the command fails loudly and changes nothing.
- **A token round trip identifies the session.** The first script call
  prints a unique token; its tool result is journalled into this session's
  live journal seconds later. The second call greps all journals (live
  first) for the token: the one that holds it is this session. Rejected:
  picking the session whose journal was written last, which guesses wrong
  whenever two sessions are live at once.
- **Restore needs no token** (it runs in a different session than it
  targets): without a selector the script lists recently archived sessions
  and the command asks the user which to restore.
- **The kit says it is the session's last act.** A session the user keeps
  using after archiving can lose the flag again (an interaction with the
  archived session was observed to clear it), so the command tells the user
  to archive as the last thing they do in the conversation.

## Consequences
- The command depends on an undocumented field; a Vibe update that changes
  it breaks the command until the kit adapts.
- One bash round trip (two commands) per archive — kept to one on purpose;
  the token cannot be found until it has been journalled.
- Claude Code has no session archive; the script exits with an explanation
  there, and the command reports it as unsupported.
