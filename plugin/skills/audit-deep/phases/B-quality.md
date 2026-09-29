# Phase B: code quality and production readiness

Audit code quality and production readiness against the production bar.

Cover:

- **Testing:** what exists; coverage (measure it only if a harness exists and
  runs without installs or writes outside a temp dir; otherwise estimate from
  the test-to-source ratio and say so); and test quality. For the five largest
  test files, check whether they assert on behaviour or only exercise code
  without meaningful assertions. Flag mocked-until-meaningless tests, missing
  integration tests, and skipped or commented-out tests.
- **CI/CD:** pipeline config, what gates a merge and what does not. Whether
  the pipeline is green by default or habitually red: check recent runs with
  `gh run list -L 20` if `gh` is installed and authenticated, otherwise say it
  was not checked.
- **Error handling:** swallowed exceptions, bare catches, missing retry logic,
  missing idempotency on anything that retries, unbounded retries, missing
  timeouts.
- **Observability:** structured logging or print statements, log levels,
  tracing (especially across async or multi-step operations), metrics,
  alerting hooks.
- **Dependencies:** lockfile present and committed, unpinned versions,
  packages unmaintained or last released over two years ago, known CVEs if you
  can check without network access, license compatibility. Mark anything you
  could not check offline as inferred or unchecked.
- **Configuration and secrets:** hardcoded credentials, keys or tokens in the
  repo or its git history (search `git log -p` output, saved to a scratch
  file, for key, token, secret and password patterns), env var handling,
  per-environment config, and what happens when a required config value is
  missing.
- **Developer experience:** can a new developer go from clone to running
  using only the README? Walk the steps literally and flag every one that
  would fail. Check whether the repo's CLAUDE.md agrees with the README and
  with the code.
- **Git hygiene:** commit message quality, branching, PR template,
  CODEOWNERS, large binaries or secrets in history.

End with `## What is missing` and `## Top 10`, ranked by severity then effort
(high severity with low effort first).
