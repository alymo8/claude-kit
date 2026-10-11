"""Tests for review-threads.py: filtering open review items and main()."""

from __future__ import annotations

import copy
import json

import pytest
from helpers import PLUGIN, REPO, load_module

SCRIPT = PLUGIN / "scripts" / "review-threads.py"
FIXTURE = REPO / "tests" / "fixtures" / "review_threads" / "pr.json"

rt = load_module(SCRIPT, "review_threads")


@pytest.fixture
def pr():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def by_kind(items, kind):
    return [i for i in items if i["kind"] == kind]


def test_resolved_thread_dropped(pr):
    ids = [i["thread_id"] for i in by_kind(rt.open_items(pr, "me"), "thread")]
    assert "T1" not in ids


def test_thread_last_answered_by_viewer_dropped(pr):
    ids = [i["thread_id"] for i in by_kind(rt.open_items(pr, "me"), "thread")]
    assert "T2" not in ids


def test_thread_with_reviewer_reply_after_viewer_kept(pr):
    threads = {i["thread_id"]: i for i in by_kind(rt.open_items(pr, "me"), "thread")}
    t3 = threads["T3"]
    assert t3["reply_to"] == 31
    assert t3["path"] == "a.py" and t3["line"] == 3
    assert [c["author"] for c in t3["comments"]] == ["bob", "me", "bob"]
    assert t3["comments"][-1] == {
        "author": "bob",
        "body": "not yet",
        "url": "u33",
        "at": "2026-10-01T02:00:00Z",
    }


def test_outdated_carried_through(pr):
    threads = {i["thread_id"]: i for i in by_kind(rt.open_items(pr, "me"), "thread")}
    assert threads["T4"]["outdated"] is True
    assert threads["T3"]["outdated"] is False


def test_deleted_author_is_ghost_and_kept(pr):
    threads = {i["thread_id"]: i for i in by_kind(rt.open_items(pr, "me"), "thread")}
    assert threads["T5"]["comments"][0]["author"] == "ghost"


def test_empty_or_whitespace_review_dropped(pr):
    ids = [i["id"] for i in by_kind(rt.open_items(pr, "me"), "review")]
    assert 61 not in ids and 62 not in ids


def test_reviews_and_comments_older_than_viewer_latest_dropped(pr):
    items = rt.open_items(pr, "me")
    assert [i["id"] for i in by_kind(items, "review")] == [64]
    assert [i["id"] for i in by_kind(items, "comment")] == [73]
    review = by_kind(items, "review")[0]
    assert review == {
        "kind": "review",
        "id": 64,
        "author": "bob",
        "state": "CHANGES_REQUESTED",
        "body": "new review",
        "url": "u64",
        "at": "2026-10-03T00:00:00Z",
    }


def test_viewer_without_comments_keeps_older_items(pr):
    items = rt.open_items(pr, "carol")
    assert [i["id"] for i in by_kind(items, "review")] == [63, 64, 65]
    assert [i["id"] for i in by_kind(items, "comment")] == [70, 71, 72, 73]


def test_viewer_own_reviews_and_comments_dropped(pr):
    items = rt.open_items(pr, "me")
    ids = [i["id"] for i in items if i["kind"] != "thread"]
    assert 65 not in ids and 70 not in ids and 72 not in ids


def test_items_order_threads_reviews_comments(pr):
    kinds = [i["kind"] for i in rt.open_items(pr, "me")]
    assert kinds == ["thread", "thread", "thread", "review", "comment"]


def stub_gh(pr, calls=None, fail=False):
    def run_gh(args):
        if calls is not None:
            calls.append(args)
        if fail:
            raise rt.GhError("gh: boom\n")
        if args[:2] == ["pr", "view"]:
            return "42\n"
        if args[:2] == ["repo", "view"]:
            return json.dumps({"owner": {"login": "o"}, "name": "r"})
        if args[:2] == ["api", "user"]:
            return "me\n"
        if args[:2] == ["api", "graphql"]:
            return json.dumps({"data": {"repository": {"pullRequest": pr}}})
        raise AssertionError(args)

    return run_gh


def test_main_prints_items(pr, monkeypatch, capsys):
    monkeypatch.setattr(rt, "run_gh", stub_gh(pr))
    assert rt.main(["42"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["pr"] == 42
    assert out["url"] == "https://github.com/o/r/pull/42"
    assert out["state"] == "OPEN"
    assert out["head"] == "feat/x"
    assert out["author"] == "me"
    assert out["viewer"] == "me"
    assert len(out["items"]) == 5


def test_main_without_pr_uses_current_branch(pr, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(rt, "run_gh", stub_gh(pr, calls))
    assert rt.main([]) == 0
    assert calls[0][:2] == ["pr", "view"]
    graphql = next(c for c in calls if c[:2] == ["api", "graphql"])
    assert "number=42" in graphql
    assert json.loads(capsys.readouterr().out)["pr"] == 42


def test_main_warns_on_next_page(pr, monkeypatch, capsys):
    paged = copy.deepcopy(pr)
    paged["reviewThreads"]["pageInfo"]["hasNextPage"] = True
    paged["reviewThreads"]["nodes"][2]["comments"]["pageInfo"]["hasNextPage"] = True
    monkeypatch.setattr(rt, "run_gh", stub_gh(paged))
    assert rt.main(["42"]) == 0
    err = capsys.readouterr().err
    assert "warning: more than 100 review threads; only the first 100 were read" in err
    assert (
        "warning: more than 100 comments in review thread T3; "
        "only the first 100 were read" in err
    )


def test_main_gh_failure_exits_1(pr, monkeypatch, capsys):
    monkeypatch.setattr(rt, "run_gh", stub_gh(pr, fail=True))
    assert rt.main(["42"]) == 1
    assert "gh: boom" in capsys.readouterr().err


def test_main_usage_error_exits_2(capsys):
    assert rt.main(["abc"]) == 2
    assert rt.main(["1", "2"]) == 2
    assert "usage" in capsys.readouterr().err


def test_main_pr_not_found_exits_1(pr, monkeypatch, capsys):
    run_gh = stub_gh(pr)

    def missing(args):
        if args[:2] == ["api", "graphql"]:
            return json.dumps({"data": {"repository": {"pullRequest": None}}})
        return run_gh(args)

    monkeypatch.setattr(rt, "run_gh", missing)
    assert rt.main(["42"]) == 1
    assert "PR #42 not found" in capsys.readouterr().err


def test_thread_without_comments_dropped(pr):
    pr["reviewThreads"]["nodes"][2]["comments"]["nodes"] = []
    ids = [i["thread_id"] for i in by_kind(rt.open_items(pr, "me"), "thread")]
    assert "T3" not in ids


def test_review_without_submitted_at_dropped(pr):
    pr["reviews"]["nodes"][3]["submittedAt"] = None
    ids = [i["id"] for i in by_kind(rt.open_items(pr, "carol"), "review")]
    assert 64 not in ids


def test_main_warns_on_reviews_and_comments_next_page(pr, monkeypatch, capsys):
    pr["reviews"]["pageInfo"]["hasNextPage"] = True
    pr["comments"]["pageInfo"]["hasNextPage"] = True
    monkeypatch.setattr(rt, "run_gh", stub_gh(pr))
    assert rt.main(["42"]) == 0
    err = capsys.readouterr().err
    assert "warning: more than 100 reviews; only the first 100 were read" in err
    assert (
        "warning: more than 100 conversation comments; only the first 100 were read"
        in err
    )
