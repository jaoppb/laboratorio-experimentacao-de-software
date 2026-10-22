"""Builders of synthetic Git repositories for the streaming/memory tests (no network)."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def git(cwd: Path | None, *args: str, stdin: bytes | None = None) -> str:
    out = subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, env=GIT_ENV, input=stdin
    )
    return out.stdout.decode("utf-8", errors="replace")


def make_divergent_repo(path: Path, per_line: int, n_tags: int) -> Path:
    """Bare repository whose date-ordered tags alternate between two diverging lines.

    Both lines fork from one root commit and their commits are dated alternately
    (`main` takes the even days, `side` the odd ones). The `n_tags` tags
    (`v0000`...) sit on the commits of the two lines in turn, so the
    chronological predecessor of a tag is on the *other* line and
    `git log previous..tag` returns about the whole history of the tag's line:
    ranges overlap heavily, like the CI tags of a real repository. Distinct
    commits: `2 * per_line + 1`.
    """
    git_dir = path / "divergent.git"
    git(None, "init", "-q", "--bare", "-b", "main", str(git_dir))
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def stamp(index: int) -> int:
        return int((start + timedelta(minutes=index)).timestamp())

    lines: list[str] = []

    def commit(ref: str, mark: int, when: int, message: str, parent: int | None) -> None:
        body = message.encode()
        lines.append(f"commit {ref}")
        lines.append(f"mark :{mark}")
        lines.append(f"author t <t@example.com> {when} +0000")
        lines.append(f"committer t <t@example.com> {when} +0000")
        lines.append(f"data {len(body)}")
        lines.append(message)
        if parent is not None:
            lines.append(f"from :{parent}")
        lines.append("")

    commit("refs/heads/main", 1, stamp(0), "root", None)
    marks: dict[str, list[int]] = {"main": [1], "side": [1]}
    next_mark = 2
    for i in range(per_line):
        for line in ("main", "side"):
            offset = 2 * i + (1 if line == "main" else 2)
            ref = "refs/heads/main" if line == "main" else "refs/heads/side"
            commit(ref, next_mark, stamp(offset), f"fix: {line} change {i}\n\nbody of {line} {i}", marks[line][-1])
            marks[line].append(next_mark)
            next_mark += 1

    # tag k goes on the commit `k // 2`-th of line (main if k is even, else side)
    for k in range(n_tags):
        line = "main" if k % 2 == 0 else "side"
        commits = marks[line]
        target = commits[min(len(commits) - 1, 1 + (k * (len(commits) - 1)) // max(n_tags, 1))]
        lines.append(f"reset refs/tags/v{k:04d}")
        lines.append(f"from :{target}")
        lines.append("")

    git(git_dir, "fast-import", "--quiet", stdin=("\n".join(lines) + "\n").encode())
    return git_dir
