"""Full commit messages through a real partial clone (local file:// repo).

Checks that the partial-clone filter used by the pipeline (CLONE_FILTER) keeps
SHAs, author dates, subjects, full messages and tags identical to a plain clone.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from metricas.cfr_b import is_corrective_release
from pipeline.git_clone import (
    CLONE_FILTER,
    extract_tags_from_git,
    get_commits_between_tags,
    run_git_command,
)

_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def _git(repo: Path, *args: str, date: str | None = None, stdin: bytes | None = None) -> None:
    env = dict(_ENV)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=env, input=stdin)


def _commit(repo: Path, name: str, message: bytes, date: str) -> None:
    (repo / name).write_text(name)
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-F", "-", date=date, stdin=message)


@pytest.fixture
def source_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "src"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "uploadpack.allowFilter", "true")
    _commit(repo, "a", b"feat: first\n", "2026-01-01T10:00:00+00:00")
    _git(repo, "tag", "v1.0.0")
    _commit(repo, "b", b"chore: tidy\n\nLonger body.\nFixes #123\n", "2026-01-02T10:00:00-03:00")
    _commit(repo, "c", b'Revert "feat: first"\n\nThis reverts commit abc.\n', "2026-01-03T10:00:00+00:00")
    _commit(
        repo,
        "d",
        "docs: café ✓ 日本\r\n\r\nCRLF body\r\nhotfix in body\r\n".encode(),
        "2026-01-04T10:00:00+00:00",
    )
    _git(repo, "tag", "v1.0.1")
    _git(repo, "checkout", "-q", "-b", "side")
    _commit(repo, "e", b"feat: side\n", "2026-01-05T10:00:00+00:00")
    _git(repo, "checkout", "-q", "main")
    _commit(repo, "f", b"feat: main\n", "2026-01-06T10:00:00+00:00")
    _git(
        repo, "merge", "-q", "--no-ff", "side", "-m", "Merge branch 'side'", "-m", "merge body",
        date="2026-01-07T10:00:00+00:00",
    )
    _git(repo, "tag", "-a", "v1.1.0", "-m", "annotated")
    return repo


async def _clone(source: Path, dest: Path, *filters: str) -> Path:
    args = ["clone", "--bare", "--quiet", *filters, "--single-branch", source.as_uri(), str(dest)]
    code, _, err = await run_git_command(args)
    assert code == 0, err
    return dest


async def _snapshot(git_dir: Path):
    tags = await extract_tags_from_git(git_dir)
    names = [t.tag_name for t in tags]
    commits = {
        f"{a}..{b}": await get_commits_between_tags(git_dir, a, b)
        for a, b in zip(names, names[1:])
    }
    return [(t.tag_name, t.published_at, t.commit_sha) for t in tags], commits


@pytest.mark.parametrize(
    "partial_filter",
    [CLONE_FILTER, "--filter=combine:tree:0+blob:none"],
    ids=["pipeline-filter", "combined-filter"],
)
async def test_partial_clone_matches_plain_clone(source_repo, tmp_path, partial_filter):
    # The combined filter is only accepted by file:// remotes and by git itself,
    # not by github.com (see CLONE_FILTER), so it is checked here against git only.
    plain = await _snapshot(await _clone(source_repo, tmp_path / "plain.git"))
    partial = await _snapshot(await _clone(source_repo, tmp_path / "partial.git", partial_filter))

    assert partial == plain  # SHAs, author dates, subjects, full messages and tags
    tags, commits = partial
    assert [t[0] for t in tags] == ["v1.0.0", "v1.0.1", "v1.1.0"]
    assert len(commits["v1.0.0..v1.0.1"]) == 3


async def test_real_log_gives_subject_and_full_message(source_repo, tmp_path):
    git_dir = await _clone(source_repo, tmp_path / "partial.git", CLONE_FILTER)
    by_subject = {
        c.message: c for c in await get_commits_between_tags(git_dir, "v1.0.0", "v1.0.1")
    }

    body = by_subject["chore: tidy"]
    assert body.full_message == "chore: tidy\n\nLonger body.\nFixes #123"
    crlf = by_subject["docs: café ✓ 日本"]
    assert crlf.full_message == "docs: café ✓ 日本\n\nCRLF body\nhotfix in body"
    assert by_subject['Revert "feat: first"'].full_message.endswith("This reverts commit abc.")

    merge = (await get_commits_between_tags(git_dir, "v1.0.1", "v1.1.0"))
    assert any(c.message == "Merge branch 'side'" and "merge body" in c.full_message for c in merge)


async def test_v1_vs_full_message_on_real_log(source_repo, tmp_path):
    git_dir = await _clone(source_repo, tmp_path / "partial.git", CLONE_FILTER)
    commits = [
        c for c in await get_commits_between_tags(git_dir, "v1.0.0", "v1.0.1")
        if c.message == "chore: tidy"
    ]
    # subject has no keyword; only the body ("Fixes #123") does
    assert is_corrective_release("v1.0.0", "v1.0.1", commits, version="v1") is False
    assert is_corrective_release("v1.0.0", "v1.0.1", commits, version="v1_full_message") is True
