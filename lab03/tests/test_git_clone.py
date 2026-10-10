"""Tests for bare git clone and git log commit extraction (pipeline.git_clone)."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from metricas.schemas import Release
from pipeline.commits import ComparisonStatus
from pipeline.git_clone import (
    GitCloneError,
    clone_repository,
    collect_release_commits_from_git,
    get_commits_between_tags,
    run_git_command,
    temporary_git_clone,
)
from pipeline.http_client import TokenPool
from pipeline.releases import WindowReleases


async def test_get_commits_between_tags_parsing():
    """Verify parsing of git log unit-separated output (%H%x1f%aI%x1f%s)."""
    fake_stdout = (
        "aaa111\x1f2026-02-18T19:41:55Z\x1frelease 1.0\n"
        "bbb222\x1f2026-02-18T18:00:00Z\x1ffix: resolve bug (#123)\n"
    )

    with patch("pipeline.git_clone.run_git_command", new_callable=AsyncMock) as mock_cmd:
        mock_cmd.return_value = (0, fake_stdout, "")
        commits = await get_commits_between_tags(
            git_dir="/tmp/repo.git",
            base_tag="v1.0.0",
            head_tag="v1.1.0",
        )

    assert len(commits) == 2
    assert commits[0].sha == "aaa111"
    assert commits[0].committed_at == datetime(2026, 2, 18, 19, 41, 55, tzinfo=timezone.utc)
    assert commits[0].message == "release 1.0"
    assert commits[1].sha == "bbb222"


async def test_get_commits_between_tags_not_found():
    """Verify KeyError is raised when tags cannot be resolved in git."""
    with patch("pipeline.git_clone.run_git_command", new_callable=AsyncMock) as mock_cmd:
        mock_cmd.return_value = (128, "", "fatal: ambiguous argument 'v1..v2': unknown revision")
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

    async def fake_get_commits(git_dir, base_tag, head_tag):
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

    assert len(calls) == 2
    assert "Authorization: Bearer secret-token" in " ".join(calls[1])


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
