"""Tests for bare git clone and git log commit extraction (pipeline.git_clone)."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from metricas.schemas import Release
from pipeline.commits import ComparisonStatus
from metricas.schemas import MAX_FULL_MESSAGE_CHARS
from pipeline.git_clone import (
    CLONE_FILTER,
    GitCloneError,
    GitCommandError,
    clone_repository,
    fetch_all_tags,
    collect_release_commits_from_git,
    get_commits_between_tags,
    run_git_command,
    temporary_git_clone,
)
from pipeline.http_client import TokenPool
from pipeline.releases import WindowReleases


def fake_git_stream(stdout, block=7, error=None):
    """Replacement of `stream_git_stdout`: yields `stdout` in blocks, optionally failing at the end."""
    calls = []

    async def stream(args, *_, **__):
        calls.append(args)
        for i in range(0, len(stdout), block):
            yield stdout[i : i + block]
        if error is not None:
            raise error

    stream.calls = calls
    return stream


async def test_get_commits_between_tags_parsing():
    """Verify parsing of git log output (subject kept as `message`)."""
    fake_stdout = (
        _record("a" * 40, "2026-02-18T19:41:55Z", "release 1.0")
        + _record("b" * 40, "2026-02-18T18:00:00Z", "fix: resolve bug (#123)")
    )

    with patch("pipeline.git_clone.stream_git_stdout", fake_git_stream(fake_stdout)):
        commits = await get_commits_between_tags(
            git_dir="/tmp/repo.git",
            base_tag="v1.0.0",
            head_tag="v1.1.0",
        )

    assert len(commits) == 2
    assert commits[0].sha == "a" * 40
    assert commits[0].committed_at == datetime(2026, 2, 18, 19, 41, 55, tzinfo=timezone.utc)
    assert commits[0].message == "release 1.0"
    assert commits[1].sha == "b" * 40


def _record(sha, date, subject, body=None):
    full = subject if body is None else f"{subject}\n\n{body}"
    return f"\x1e{sha}\x1f{date}\x1f{subject}\x1f{full}\n"


_SHA = "a" * 40


async def _parse(stdout):
    stream = fake_git_stream(stdout)
    with patch("pipeline.git_clone.stream_git_stdout", stream):
        return await get_commits_between_tags("/tmp/repo.git", "v1", "v2"), stream


async def test_get_commits_requests_subject_and_full_message():
    commits, stream = await _parse("")
    assert commits == []
    fmt = next(a for a in stream.calls[0] if a.startswith("--format="))
    assert fmt == "--format=\x1e%H\x1f%aI\x1f%s\x1f%B"


async def test_get_commits_multiline_body_keeps_subject_and_full_message():
    out = _record(_SHA, "2026-02-18T19:41:55Z", "chore: tidy", "Longer text.\n\nFixes #123\n")
    out += _record("b" * 40, "2026-02-17T10:00:00Z", "feat: x")
    commits, _ = await _parse(out)
    assert [c.message for c in commits] == ["chore: tidy", "feat: x"]
    assert commits[0].full_message == "chore: tidy\n\nLonger text.\n\nFixes #123"
    assert commits[1].full_message == "feat: x"


async def test_get_commits_revert_merge_unicode_and_crlf():
    out = _record(_SHA, "2026-02-18T19:41:55Z", 'Revert "feat: cache"', 'This reverts commit abc.')
    out += _record("b" * 40, "2026-02-18T19:00:00Z", "Merge branch 'side'", "merge body")
    out += _record("c" * 40, "2026-02-18T18:00:00-03:00", "docs: café ✓ 日本")
    out += "\x1e" + "d" * 40 + "\x1f2026-02-18T17:00:00Z\x1ffix: crlf\x1ffix: crlf\r\n\r\nbody line\r\nhotfix\r\n\n"
    commits, _ = await _parse(out)
    assert commits[0].full_message.startswith('Revert "feat: cache"')
    assert commits[1].message == "Merge branch 'side'"
    assert commits[2].message == "docs: café ✓ 日本"
    assert commits[2].committed_at.utcoffset().total_seconds() == -3 * 3600
    assert commits[3].message == "fix: crlf"
    assert commits[3].full_message == "fix: crlf\n\nbody line\nhotfix"


async def test_get_commits_stray_record_separator_in_body_does_not_split():
    out = _record(_SHA, "2026-02-18T19:41:55Z", "feat: a", "weird \x1e body")
    commits, _ = await _parse(out)
    assert len(commits) == 1
    assert "weird \x1e body" in commits[0].full_message


async def test_get_commits_truncates_huge_message():
    out = _record(_SHA, "2026-02-18T19:41:55Z", "feat: big", "x" * (MAX_FULL_MESSAGE_CHARS * 2))
    (commit,), _ = await _parse(out)
    assert len(commit.full_message) == MAX_FULL_MESSAGE_CHARS
    assert commit.message == "feat: big"


async def test_get_commits_between_tags_not_found():
    """Verify KeyError is raised when tags cannot be resolved in git."""
    error = GitCommandError(128, "fatal: ambiguous argument 'v1..v2': unknown revision")
    with patch("pipeline.git_clone.stream_git_stdout", fake_git_stream("", error=error)):
        with pytest.raises(KeyError):
            await get_commits_between_tags(
                git_dir="/tmp/repo.git",
                base_tag="v1",
                head_tag="v2",
            )


async def test_collect_release_commits_from_git():
    """Verify collect_release_commits_from_git handles anchor, first release, and not-found tags."""
    r1 = Release(tag_name="v1.0.0", published_at=datetime(2025, 10, 10))
    r2 = Release(tag_name="v1.1.0", published_at=datetime(2025, 11, 10))
    r3 = Release(tag_name="v1.2.0", published_at=datetime(2025, 12, 10))
    window = WindowReleases(in_window=[r1, r2, r3], anchor=None)

    async def fake_get_commits(git_dir, base_tag, head_tag, **kwargs):
        if head_tag == "v1.1.0":
            from metricas.schemas import Commit
            return [Commit(sha="abc", committed_at=datetime(2025, 11, 1), message="msg")]
        if head_tag == "v1.2.0":
            raise KeyError("Tag not found")
        return []

    with patch("pipeline.git_clone.get_commits_between_tags", side_effect=fake_get_commits):
        results = await collect_release_commits_from_git("/fake.git", window)

    assert len(results) == 3
    assert results[0].status == ComparisonStatus.FIRST_RELEASE
    assert results[1].status == ComparisonStatus.OK
    assert len(results[1].commits) == 1
    assert results[2].status == ComparisonStatus.NOT_FOUND


async def test_clone_repository_skip_existing(tmp_path):
    """Verify clone is skipped if bare repo HEAD already exists."""
    repo_dir = tmp_path / "existing.git"
    repo_dir.mkdir()
    (repo_dir / "HEAD").write_text("ref: refs/heads/main\n")

    res = await clone_repository("owner", "repo", repo_dir)
    assert res == repo_dir


async def test_clone_repository_anonymous_success(tmp_path):
    """Verify anonymous clone success."""
    target = tmp_path / "test.git"
    with patch("pipeline.git_clone.run_git_command", new_callable=AsyncMock) as mock_cmd:
        mock_cmd.return_value = (0, "Cloned", "")
        res = await clone_repository("owner", "repo", target)
        assert res == target


async def test_clone_repository_retry_with_token(tmp_path):
    """Verify clone retries with token when anonymous clone receives 403 / auth error."""
    target = tmp_path / "test.git"
    token_pool = TokenPool(["secret-token"])

    calls = []

    async def fake_run_git(args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            return (128, "", "fatal: unable to access: 403 Rate limit or authentication required")
        return (0, "Cloned with auth", "")

    with patch("pipeline.git_clone.run_git_command", side_effect=fake_run_git):
        res = await clone_repository("owner", "repo", target, token_pool=token_pool)
        assert res == target

    assert len(calls) == 3
    assert "Authorization: Bearer secret-token" in " ".join(calls[1])
    # Tag fetch after the clone reuses the token
    assert "+refs/tags/*:refs/tags/*" in calls[2]
    assert "Authorization: Bearer secret-token" in " ".join(calls[2])


async def test_clone_repository_fetches_tags_of_other_branches(tmp_path):
    """Single-branch clone misses tags of maintenance branches; they are fetched after."""
    target = tmp_path / "test.git"
    with patch("pipeline.git_clone.run_git_command", new_callable=AsyncMock) as mock_cmd:
        mock_cmd.return_value = (0, "", "")
        await clone_repository("owner", "repo", target)

    fetch_args = mock_cmd.call_args_list[1].args[0]
    assert "fetch" in fetch_args
    assert CLONE_FILTER in fetch_args
    assert "+refs/tags/*:refs/tags/*" in fetch_args


async def test_clone_and_tag_fetch_share_the_same_filter(tmp_path):
    """Clone and tag fetch (anonymous and with token) use CLONE_FILTER and stay bare."""
    target = tmp_path / "test.git"
    with patch("pipeline.git_clone.run_git_command", new_callable=AsyncMock) as mock_cmd:
        mock_cmd.return_value = (0, "", "")
        await clone_repository("owner", "repo", target)
    clone_args, fetch_args = (c.args[0] for c in mock_cmd.call_args_list[:2])
    assert "--bare" in clone_args and "--single-branch" in clone_args
    assert clone_args.count(CLONE_FILTER) == 1
    assert fetch_args.count(CLONE_FILTER) == 1
    # Exactly one filter flag per command (a second one would be combined by git)
    assert sum(a.startswith("--filter") for a in clone_args) == 1
    assert sum(a.startswith("--filter") for a in fetch_args) == 1


async def test_fetch_all_tags_failure_keeps_clone(tmp_path):
    """A failed tag fetch is logged and does not abort the clone."""
    with patch("pipeline.git_clone.run_git_command", new_callable=AsyncMock) as mock_cmd:
        mock_cmd.return_value = (128, "", "fatal: timeout")
        assert await fetch_all_tags(tmp_path) is False


async def test_clone_repository_failure_raises(tmp_path):
    """Verify GitCloneError is raised when clone fails permanently."""
    target = tmp_path / "test.git"
    with patch("pipeline.git_clone.run_git_command", new_callable=AsyncMock) as mock_cmd:
        mock_cmd.return_value = (128, "", "fatal: repository not found")
        with pytest.raises(GitCloneError):
            await clone_repository("owner", "repo", target)


async def test_temporary_git_clone_lifecycle(tmp_path):
    """Verify temporary_git_clone creates and removes directory with auto_cleanup=True."""
    target_dir = tmp_path / "clones" / "owner__repo.git"

    with patch("pipeline.git_clone.clone_repository", new_callable=AsyncMock) as mock_clone:
        async def fake_clone(owner, repo, target, **kwargs):
            Path(target).mkdir(parents=True, exist_ok=True)
            return Path(target)
        mock_clone.side_effect = fake_clone

        async with temporary_git_clone("owner", "repo", cache_dir=tmp_path / "clones", auto_cleanup=True) as path:
            assert path.exists()

        assert not target_dir.exists()
