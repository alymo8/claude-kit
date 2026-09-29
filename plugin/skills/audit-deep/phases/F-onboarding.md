# Phase F: onboarding guide

Produce an onboarding guide for a new contributor, using the audit files and
the source. Read-only with respect to source. Findings, if any, follow the
rules' format.

Include:

1. **Architecture mental model.** How the system actually works, in a form a
   newcomer can hold in their head. Name the five or six concepts that unlock
   everything else. Describe the main request or task lifecycle from entry to
   response, naming files and functions at each hop.
2. **Local setup.** Walk the README's setup steps literally. For each, state
   whether it works; where it fails, give the corrected step. Do not run
   installs: analyse the steps and flag what would break, marking each as
   verified or inferred. End with the shortest path from clone to a running
   local instance. Note anywhere the repo's CLAUDE.md contradicts the README.
3. **Codebase landmines.** From the audit findings, the areas where a naive
   change is most likely to break something non-obviously, and why.
4. **Safe first-change zones.** Where changes have a contained blast radius
   and existing test coverage.
5. **Three to five candidate first contributions,** ranked by value over risk.
   For each: what it is, which audit finding it addresses, the files involved,
   why it is low risk, roughly how long it takes, and how to verify it worked.
   Prefer contributions that are useful to the project over busywork, and ones
   that force reading important code.
6. **Conventions to follow:** naming, structure, testing and commit style as
   actually practised in this repo (cite examples), not as documented. Where
   CLAUDE.md states a convention the code does not follow, say which one to
   follow and why.
