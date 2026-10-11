#!/usr/bin/env python3
"""List the open review items on a pull request, as JSON.

Usage: review-threads.py [PR]

PR is a number; without it, the current branch's PR is used. One GraphQL
query reads the PR's review threads, reviews and conversation comments (the
first 100 of each, and the first 100 comments per thread). Kept: unresolved
threads whose last comment is not the viewer's, and non-empty reviews and
conversation comments by others that are newer than the viewer's latest
conversation comment. Exits 0 on success (also when nothing is open), 1 when
gh fails, 2 on a usage error. A connection with more than 100 entries gets a
warning on stderr.
"""

from __future__ import annotations

import json
import subprocess
import sys

QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number url state headRefName author { login }
      reviewThreads(first: 100) {
        pageInfo { hasNextPage }
        nodes {
          id isResolved isOutdated path line
          comments(first: 100) {
            pageInfo { hasNextPage }
            nodes { databaseId author { login } body url createdAt }
          }
        }
      }
      reviews(first: 100) {
        pageInfo { hasNextPage }
        nodes { databaseId author { login } state body url submittedAt }
      }
      comments(first: 100) {
        pageInfo { hasNextPage }
        nodes { databaseId author { login } body url createdAt }
      }
    }
  }
}
"""

CONNECTIONS = (
    ("reviewThreads", "review threads"),
    ("reviews", "reviews"),
    ("comments", "conversation comments"),
)


class GhError(Exception):
    """A gh command failed; the message is its stderr."""


def run_gh(args: list[str]) -> str:
    """Run gh and return its stdout; raise GhError on failure."""
    try:
        proc = subprocess.run(
            ["gh", *args], capture_output=True, text=True, encoding="utf-8"
        )
    except FileNotFoundError as err:
        raise GhError(f"gh not found: {err}\n") from err
    if proc.returncode != 0:
        raise GhError(proc.stderr)
    return proc.stdout


def login(node: dict) -> str:
    """The author's login; a deleted account (null author) is ``ghost``."""
    return (node.get("author") or {}).get("login") or "ghost"


def open_items(pr: dict, viewer: str) -> list[dict]:
    """The review items on ``pr`` still waiting for ``viewer``'s answer."""
    items = []
    for thread in pr["reviewThreads"]["nodes"]:
        comments = thread["comments"]["nodes"]
        if thread["isResolved"] or not comments or login(comments[-1]) == viewer:
            continue
        items.append(
            {
                "kind": "thread",
                "thread_id": thread["id"],
                "reply_to": comments[0]["databaseId"],
                "path": thread["path"],
                "line": thread["line"],
                "outdated": thread["isOutdated"],
                "comments": [
                    {
                        "author": login(c),
                        "body": c["body"],
                        "url": c["url"],
                        "at": c["createdAt"],
                    }
                    for c in comments
                ],
            }
        )
    conversation = pr["comments"]["nodes"]
    since = max(
        (c["createdAt"] for c in conversation if login(c) == viewer), default=""
    )
    for review in pr["reviews"]["nodes"]:
        at = review.get("submittedAt") or ""
        if not review["body"].strip() or login(review) == viewer or at <= since:
            continue
        items.append(
            {
                "kind": "review",
                "id": review["databaseId"],
                "author": login(review),
                "state": review["state"],
                "body": review["body"],
                "url": review["url"],
                "at": at,
            }
        )
    for comment in conversation:
        if login(comment) == viewer or comment["createdAt"] <= since:
            continue
        items.append(
            {
                "kind": "comment",
                "id": comment["databaseId"],
                "author": login(comment),
                "body": comment["body"],
                "url": comment["url"],
                "at": comment["createdAt"],
            }
        )
    return items


def warnings(pr: dict) -> list[str]:
    """One line per connection that has more than the 100 entries read."""
    tail = "only the first 100 were read"
    out = [
        f"warning: more than 100 {label}; {tail}"
        for key, label in CONNECTIONS
        if pr[key]["pageInfo"]["hasNextPage"]
    ]
    out += [
        f"warning: more than 100 comments in review thread {t['id']}; {tail}"
        for t in pr["reviewThreads"]["nodes"]
        if t["comments"]["pageInfo"]["hasNextPage"]
    ]
    return out


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1 or (args and not args[0].isdigit()):
        print("usage: review-threads.py [PR]", file=sys.stderr)
        return 2
    try:
        if args:
            number = int(args[0])
        else:
            number = int(run_gh(["pr", "view", "--json", "number", "--jq", ".number"]))
        repo = json.loads(run_gh(["repo", "view", "--json", "owner,name"]))
        viewer = run_gh(["api", "user", "--jq", ".login"]).strip()
        data = json.loads(
            run_gh(
                [
                    "api",
                    "graphql",
                    "-f",
                    f"query={QUERY}",
                    "-f",
                    f"owner={repo['owner']['login']}",
                    "-f",
                    f"name={repo['name']}",
                    "-F",
                    f"number={number}",
                ]
            )
        )
    except GhError as err:
        sys.stderr.write(str(err))
        return 1
    pr = data["data"]["repository"]["pullRequest"]
    if pr is None:
        print(f"error: PR #{number} not found", file=sys.stderr)
        return 1
    for line in warnings(pr):
        print(line, file=sys.stderr)
    print(
        json.dumps(
            {
                "pr": pr["number"],
                "url": pr["url"],
                "state": pr["state"],
                "head": pr["headRefName"],
                "author": login(pr),
                "viewer": viewer,
                "items": open_items(pr, viewer),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
