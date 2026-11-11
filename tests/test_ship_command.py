import re

from helpers import PLUGIN, command_text

SHIP = command_text("ship")


def _step(n):
    match = re.search(rf"^{n}\. (.*?)(?=^\d+\. |\Z)", SHIP, re.M | re.S)
    assert match, n
    return " ".join(match.group(1).split())


def test_feature_branch_is_cut_from_origin_main():
    assert re.search(r"feat/<slug>.{0,40}origin/main", _step(2), re.S)


def test_unclean_local_main_is_not_a_stop_rule():
    stops = SHIP.split("## Stop rules", 1)[1].split("## Steps", 1)[0]
    assert "pre-flight" not in stops.lower()
    assert "clean tree" not in _step(1)


def test_uncommitted_spec_moves_into_the_worktree():
    step = _step(2)
    assert "untracked" in step and "identical" in step


def test_main_is_verified_in_a_temporary_worktree_not_the_main_checkout():
    assert "git worktree add --detach" in _step(10)
    assert "git pull" not in SHIP


def test_cleanup_does_not_run_inside_the_main_checkout():
    step = _step(11)
    assert "git -C" in step
    assert "From the main checkout" not in step
    # Local main moves only by a guarded fast-forward, after leaving the worktree.
    assert "merge --ff-only origin/main" in step and "clean tree" in step
    assert step.index("ExitWorktree") < step.index("merge --ff-only")


def test_step_zero_requires_a_valid_gate_record():
    step = _step(0)
    assert "spec-lint.py" in step and "--verify-record" in step
    assert "claude-kit:spec-gate" in step


def test_failed_gate_is_a_stop_rule():
    stops = SHIP.split("## Stop rules", 1)[1].split("## Steps", 1)[0]
    assert "gate fails" in stops.lower()


def test_gate_record_moves_into_the_worktree_with_the_spec():
    assert "docs/superpowers/gates/" in _step(2)


def test_gated_spec_is_marked_approved_even_when_the_record_is_valid():
    step = _step(0)
    ok_branch = step.split("Otherwise", 1)[0]
    assert "approved" in ok_branch


def _stops():
    return SHIP.split("## Stop rules", 1)[1].split("## Steps", 1)[0]


def test_step_three_gates_the_plan():
    step = _step(3)
    assert "claude-kit:plan-gate" in step
    assert "docs/superpowers/gates/plans/" in step


def test_step_three_resumes_an_existing_plan_by_its_spec_line():
    step = _step(3)
    assert "**Spec:**" in step
    assert "decisions not approved" in step
    assert "never approval" not in step


def test_step_four_verifies_the_plan_record():
    step = _step(4)
    assert "--verify-record" in step and "plan" in step


def test_plan_gate_is_a_stop_rule():
    stops = _stops().lower()
    assert "plan gate" in stops
    assert "`fail`" in stops
    assert "decisions approved" in stops


def test_stop_rule_fires_on_irreversible_decisions():
    stops = " ".join(_stops().lower().split())  # phrases may wrap across lines
    assert "irreversible" in stops
    assert "decisions not approved" in stops
    assert "only irreversible plan-introduced decisions need the user" in stops
    assert "returns `pass-with-decisions` or `fail`" not in stops
    assert "approves the spec, not decisions a plan adds later" not in stops


def test_step_three_auto_approves_decisions():
    step = _step(3)
    assert "- **Decisions approved:** <today>" in step
    assert "- **Approved by:** /ship (auto)" in step
    assert "Ruling:" in step
    assert "irreversible" in step


def test_step_three_does_not_edit_the_plan_for_adrs():
    step = _step(3)
    assert "MUST trigger" in step
    assert "Do not edit the plan" in step


def test_step_three_sub_steps_stay_inside_step_three():
    step = _step(3)
    for label in ("(3a)", "(3b)", "(3c)", "(3d)", "(3e)"):
        assert label in step
    assert "**Plan gate:**" in step and "**Implement.**" not in step


def test_pr_lists_auto_approved_decisions():
    step = _step(7)
    assert "Plan decisions (auto-approved)" in step
    assert "- **Approved by:** /ship (auto)" in step
    assert "`Plan decisions` otherwise" in step


def test_rerun_does_not_reapprove_a_stopped_record():
    step = _step(3)
    stops = " ".join(_stops().split())
    assert "- **Stopped on irreversible:** <today>" in step
    assert "Stopped on irreversible" in stops
    assert "rerunning `/ship` is not an answer" in stops


def test_user_approval_still_writes_adrs():
    stops = " ".join(_stops().split())
    assert "on approval, do (3c) and (3d)" in stops


def test_adr_trigger_list_uses_the_kit_map():
    step = _step(3)
    assert "../conventions/decision-log.md" not in step
    assert "kit map" in step


def test_report_lists_auto_approved_decisions():
    assert "Plan decisions (auto-approved)" in _step(12)


def test_pr_links_the_plan_gate_record():
    assert "docs/superpowers/gates/plans/" in _step(7)


def test_step_3_adds_depends_on_lines():
    assert "**Depends on:**" in _step(3)


def test_step_4_picks_waves_and_falls_back():
    step = _step(4)
    assert "parallel-plan.py" in step and "waves" in step
    assert "claude-kit:parallel-tasks" in step
    assert "non-zero" in step and "not a stop rule" in step


def test_git_lock_retry_rule():
    rule = SHIP.split("## Git lock retry", 1)[1].split("## Steps", 1)[0]
    assert "Unable to create '...lock': File exists" in rule
    assert "cannot lock ref" in rule


def test_step_7_titles_the_pr_with_a_single_quoted_title():
    step = _step(7)
    assert "--title '<title>'" in step and "'\\''" in step
    assert "$(" not in step  # no command substitution: worktree guards refuse it
    assert "gh pr view --json title" in step and "gh pr edit" in step
    assert "first line outside code fences" in step


def test_title_mismatch_is_a_stop_rule():
    stops = SHIP.split("## Stop rules", 1)[1].split("## Git lock retry", 1)[0]
    assert "PR title does not match the spec's title" in stops


def test_step_9_regenerates_the_spec_index():
    step = _step(9)
    assert "spec-index.py" in step
    assert "git add docs/superpowers/README.md" in step


def test_step_7_uses_the_bash_tool():
    assert "Bash tool" in _step(7)


def test_plan_writer_answers_the_spec_records_plan_questions():
    step = _step(3)
    assert "## Plan questions" in step
    assert "docs/superpowers/gates/<spec file name>" in step


def test_learnings_are_captured_before_the_pr():
    step = _step(7)
    assert "claude-kit:capture-learnings" in step
    assert step.index("claude-kit:capture-learnings") < step.index("gh pr create")


def test_learnings_commit_is_tested_before_push():
    step = _step(7)
    learn = step.index("claude-kit:capture-learnings")
    assert learn < step.index("full test suite") < step.index("git push")
    assert step.index("git push") < step.index("gh pr create")


def test_report_lists_learnings():
    assert "Learnings summary from step 7" in _step(12)


def test_rebase_dedupes_learnings_and_renumbers_adrs():
    step = _step(9)
    assert "Capture learnings" in step
    assert "duplicate" in step and "renumber" in step


def _raw_step(n):
    match = re.search(rf"^{n}\. (.*?)(?=^\d+\. |\Z)", SHIP, re.M | re.S)
    assert match, n
    return match.group(1)


def _quoted(n):
    lines = [line.strip() for line in _raw_step(n).splitlines()]
    return " ".join(" ".join(x[1:] for x in lines if x.startswith(">")).split())


def _unquoted(n):
    lines = [line.strip() for line in _raw_step(n).splitlines()]
    return " ".join(" ".join(x for x in lines if not x.startswith(">")).split())


def test_step_three_dispatches_a_plan_subagent():
    assert "general-purpose subagent" in _step(3)
    prompt = _quoted(3)
    for needle in (
        "superpowers:writing-plans",
        "claude-kit:plan-gate",
        "steps 1–6",
        "Verdict:",
        "Record:",
    ):
        assert needle in prompt, needle


def test_step_three_does_not_write_the_plan_itself():
    assert "superpowers:writing-plans" not in _unquoted(3)


def test_step_four_always_implements_in_subagents():
    step = _step(4)
    assert "superpowers:subagent-driven-development" in step
    assert "claude-kit:parallel-tasks" in step
    assert "non-zero" in step and "not a stop rule" in step
    assert "executing-plans" not in step
    assert "finishing-a-development-branch" in step and "not run" in step


def test_step_six_reuses_step_four_final_review():
    step = _step(6)
    assert "final whole-branch review" in step
    assert "superpowers:requesting-code-review" in step


def test_ship_never_names_executing_plans():
    assert "executing-plans" not in SHIP


def test_decision_findings_stop_even_inside_sdd():
    step = _step(4)
    assert "scope, product or behaviour decision" in step
    assert "stop rule" in step.split("scope, product or behaviour decision", 1)[1]


def test_rerunning_the_plan_gate_goes_through_step_three():
    assert "through step 3's subagent" in " ".join(_stops().split())


def test_cleanup_reports_docker_disk_line():
    step = _step(11)
    assert "scripts/docker-disk.py" in step
    assert step.index("docker buildx rm <slug>") < step.index("docker-disk.py")
    assert "its verdict is not a stop rule" in step
    assert "If the task used Docker, then run" in step
    assert "Never run a prune without a" in step
    assert "never remove anything in the baseline" in step
    assert "docker disk:" in _step(12)


def _frozen():
    rule = SHIP.split("## Frozen check", 1)[1].split("## Steps", 1)[0]
    return " ".join(rule.split())


def test_frozen_check_runs_before_every_push():
    rule = _frozen()
    for needle in (
        'frozen-check.py" <spec> <plan>',
        "~/.claude/skills/claude-kit/scripts/frozen-check.py",
        "superpowers:systematic-debugging",
        "not a stop rule",
        "step 8's fix loop",
    ):
        assert needle in rule, needle
    for n in (5, 6, 7, 9):
        assert "frozen check" in _step(n), n


def test_frozen_violation_is_a_stop_rule():
    stops = " ".join(_stops().split())
    for needle in (
        "`frozen-check.py` exits 1",
        "git commit --allow-empty",
        "Frozen-change-approved: <path>",
        "Implementers and subagents never write that trailer",
    ):
        assert needle in stops, needle


def test_plan_prompt_copies_the_frozen_bullet():
    assert "**Frozen:**" in _quoted(3)


def test_step_four_passes_the_frozen_constraint():
    step = _step(4)
    assert "Files under Frozen (`<list>`) that exist are read-only" in step
    assert "created once, exactly as the plan gives it" in step


def test_step_six_runs_the_two_axis_review_every_run():
    step = _step(6)
    assert "on every run, run the `claude-kit:review` skill" in step
    for needle in ("`hard`", "`judgement`", "scope creep"):
        assert needle in step, needle
    review = step.index("claude-kit:review")
    assert step.index("superpowers:requesting-code-review") < review


def test_pr_body_follows_the_reference():
    step = _step(7)
    for needle in (
        "references/pr-body.md",
        "~/.claude/skills/claude-kit/references/pr-body.md",
        "**Door:**",
        "**Blast radius:**",
        "Merge danger",
        "Hardening proposals",
    ):
        assert needle in step, needle


def test_capture_learnings_runs_in_auto_mode():
    needle = "`claude-kit:capture-learnings` skill with the argument `--auto`"
    assert needle in _step(7)


def test_report_lists_review_axes():
    step = _step(12)
    assert "claude-kit:review" in step
    assert "`judgement`" in step


def test_ship_md_stays_under_its_size_budget():
    assert len((PLUGIN / "commands" / "ship.md").read_bytes()) <= 18_500
