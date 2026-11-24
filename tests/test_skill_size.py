"""Size limits for skills and commands, and the reference files commands point to.

After a compaction Claude Code re-attaches each invoked skill or command cut at
20,000 characters, so anything past that point silently drops out of a long run.
Long commands keep their late steps in plugin/references/ and read them when
they reach them.
"""

from __future__ import annotations

import pytest
from helpers import PLUGIN, REFERENCE_RE

LIMIT = 20_000

FILES = sorted(PLUGIN.glob("skills/*/SKILL.md")) + sorted(PLUGIN.glob("commands/*.md"))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.relative_to(PLUGIN).as_posix())
def test_under_compaction_limit(path):
    size = len(path.read_bytes())
    assert size < LIMIT, f"{size} bytes; move late sections to plugin/references/"


FALLBACK_RULE = (
    "Where `${CLAUDE_PLUGIN_ROOT}` is not expanded, "
    "use the plugin root stated in the kit map, "
    "else `~/.claude/skills/agent-kit`, in its place."
)
ROOT_NOTE = (
    "`<plugin root>` is the plugin root stated in the kit map, "
    "else `~/.claude/skills/agent-kit`."
)


def test_every_reference_pointer_resolves_and_has_a_fallback():
    # A file either states the fallback once (FALLBACK_RULE) or per pointer.
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        for ref in REFERENCE_RE.findall(text):
            assert (PLUGIN / "references" / ref).is_file(), (path.name, ref)
            fallback = f"<plugin root>/references/{ref}"
            assert FALLBACK_RULE in text or (fallback in text and ROOT_NOTE in text), (
                ref
            )


def test_every_reference_file_is_read_by_a_command():
    # A reference read by a hook (such as hooks/run.py) counts too.
    sources = FILES + sorted(PLUGIN.glob("hooks/*.py"))
    texts = "".join(p.read_text(encoding="utf-8") for p in sources)
    for ref in (PLUGIN / "references").glob("*.md"):
        assert f"references/{ref.name}" in texts, ref.name
