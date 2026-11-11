# /ship-fast: steps 7 to 9

Part of `commands/ship-fast.md`, which reads this file when it reaches it. That command's Stop rules and Git lock retry apply here.

7. **PR.** First run the `claude-kit:capture-learnings` skill, then
   `git push -u origin poc/<slug>` (it carries any learnings commit, which
   changes no app code and needs no restart). (Each CI fix commit restarts
   the app, as in step 5.) The PR title is the spec's title: the first
   line outside code fences that starts with `# `, with the
   `# ` prefix and trailing whitespace removed. Run, with the Bash tool (not
   PowerShell), `gh pr create --title '<title>' --body-file <file>`, with
   the title written out literally inside single quotes and each `'` in it
   written as `'\''`. The body has: Summary; Acceptance criteria, each with
   its evidence (the test name or the smoke-run output); Decisions (every
   question the user answered, then the product choices "assumed (not
   asked)"); Assumptions (engineering choices taken without asking); Cut
   (what the POC leaves out); links to the spec and the task list;
   Verification (the exact commands and their results); and the
   attribution line the session requires. Then
   compare `gh pr view --json title` with the title; on a mismatch run
   `gh pr edit --title '<title>'` once. Whether the repository has CI is
   decided only by whether `.github/workflows/*.yml` exists on the branch.
   If it does, run `gh pr checks` every 15 seconds until checks appear
   (they start a few seconds after the PR is created), then
   `gh pr checks --watch --fail-fast`. On red: `gh run view <id> --log-failed`, fix with
   `superpowers:systematic-debugging`, commit, push, count one attempt. If
   there is no workflow file, skip the watch and say so in the report.
8. **Hand over.** No cleanup runs here: the user tests and presents the
   POC from this workspace first. Keep the feature worktree, the local
   branch `poc/<slug>` and any Docker objects. The app launched in step 5
   is already running: confirm it serves the branch's final commit
   (restart it if not, or relaunch it with the `run` skill if it has
   stopped) and leave it running; note its URL or entry command, the
   command to stop it, and the command to start it again (a background
   process ends with the session; containers keep running). Stop any other
   process the smoke run left behind.
9. **Report.** One message: the PR link; each acceptance criterion with its
   evidence; Decisions (answered, then assumed) and Assumptions; the review
   fixes; the Learnings summary from step 7; the CI result (and, for a new
   repository, that its first `main` run was red because it had no tests
   yet); the wall-clock minutes of steps 2 to 7 (each, and in total); and
   **Try it**: the running app's URL or entry command, how to stop and
   restart it, and the worktree path.
   Do not suggest cleaning up in the report. Once the user says they have
   tested the app or finished presenting it, suggest the Cleanup below in
   one line, and run it when they agree.
