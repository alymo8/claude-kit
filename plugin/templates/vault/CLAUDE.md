# Vault rules

This folder is a personal knowledge vault: raw material in `raw/`, a wiki built
from it in `wiki/`, and tasks in `tasks/`.

- **Read `wiki/index.md` first.** It lists every person, topic, source and task
  page.
- **One home per fact.** Each fact lives on one person or topic page. Source
  pages in `wiki/sources/` hold only what that source said.
- **Link every fact to its source.** Every fact added to a person or topic page
  links to the source page it came from, as a wiki-link such as
  `[[2026-11-03-example-call]]`.
- **Never invent people, owners, dates or facts.** Leave a field empty rather
  than guess.
- **Conflicts.** When sources disagree, a newer primary document beats a recap,
  and the conflict is noted on the page under Open questions.
- **`raw/` is never edited.** Files there are the originals; their sha256 is
  recorded on their source pages.
- **To add material,** drop the file into `raw/<kind>/` and run the
  `claude-kit:ingest` skill.
