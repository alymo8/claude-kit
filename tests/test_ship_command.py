import re

from helpers import PLUGIN

SHIP = (PLUGIN / "commands" / "ship.md").read_text(encoding="utf-8")


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
    assert "never approval" in step


def test_step_four_verifies_the_plan_record():
    step = _step(4)
    assert "--verify-record" in step and "plan" in step


def test_plan_gate_is_a_stop_rule():
    stops = _stops().lower()
    assert "plan gate" in stops
    assert "pass-with-decisions" in stops
    assert "decisions approved" in stops


def test_pr_links_the_plan_gate_record():
    assert "docs/superpowers/gates/plans/" in _step(7)
