# ADR 0057: Vibe users install the kit with a one-line remote bootstrap

- **Status:** accepted
- **Date:** 2026-11-25

## Context
[ADR 0054](0054-vibe-native-plugin.md) installs the kit in Mistral Vibe by
running `plugin/install.py --agent vibe` **from a checkout** of this repo.
Vibe has no plugin marketplace and no `vibe plugin install`: plugins are
discovered only from `~/.vibe/plugins/` and `.vibe/plugins/` on disk, and Vibe
adapts a Claude Code plugin found there to skills and MCP servers only — no
hooks, so the adapted copy is not the kit. A Vibe user without a checkout had
no documented way in; the contributor flow was the only entry point.

## Decision
- **A self-contained bootstrap (`plugin/install-vibe.py`), not a marketplace
  (D1).** The script downloads the repo tarball from
  `codeload.github.com` (no git needed), unpacks it into the persistent cache
  `&lt;home&gt;/.vibe/.agent-kit-src/agent-kit`, and runs `install.py
  --agent vibe` from it, so the existing native build, the `hooks.toml`
  cleanup and the `AGENTS.md` fallback all stay in one place. The README and
  the setup guide carry it as one line: `python -c "import
  urllib.request; exec(urllib.request.urlopen('...').read())"`.
  Rejected: shipping the built `agent-kit` and `superpowers` folders as an
  artifact to drop into `~/.vibe/plugins/` — every subfolder there is a plugin
  root, so two folders cannot come from one download, and the drop-in would
  skip the installer's `hooks.toml` and `AGENTS.md` steps. Also rejected:
  waiting for a Mistral marketplace, which does not exist.
- **The cache belongs to the bootstrap (D2).** A folder it did not write
  (no `.agent-kit-src` marker) is refused, never replaced, like the plugin
  folders in ADR 0054. The cache refreshes through a staging swap with a way
  back, and the tarball is extracted behind an explicit escape check rather
  than trusting the tarfile data filter.
- **The hooks default to the running interpreter's path (D3).** The
  bootstrap passes `--python &lt;sys.executable&gt;`, so session hooks run
  even when the bare `python` on PATH is the Windows store stub or Python 2;
  `--python python` restores the plain command.

## Consequences
- The one-liner installs the version on `main`; re-running it is also the
  upgrade path (the Vibe plugins are a copy, so a cached checkout upgrades
  the same way).
- `--ref <tag-or-sha>` pins an install; `--tarball <file>` installs offline
  or from a test; `--repo` points at a fork.
- ADR 0050's contributor flow stays as it is: Codex and Cursor still need a
  checkout of the repo.
