"""Tests for git tag extraction from local bare clone (Issue #54)."""

import os
import subprocess
from pathlib import Path

import pytest
from pipeline.git_clone import GitCloneError, extract_tags_from_git


@pytest.fixture
def temp_git_repo_with_tags(tmp_path: Path) -> Path:
    repo_dir = tmp_path / "test_repo"
    # Create a git repo with commits and tags
    subprocess.run(["git", "init", str(repo_dir)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)

    base_env = dict(os.environ)

    # First commit + lightweight tag v0.1
    f1 = repo_dir / "file1.txt"
    f1.write_text("hello 1")
    subprocess.run(["git", "add", "file1.txt"], cwd=repo_dir, check=True)
    env1 = {
        **base_env,
        "GIT_AUTHOR_DATE": "2026-01-01T10:00:00Z",
        "GIT_COMMITTER_DATE": "2026-01-01T10:00:00Z",
    }
    subprocess.run(["git", "commit", "-m", "commit 1"], cwd=repo_dir, check=True, env=env1)
    subprocess.run(["git", "tag", "v0.1"], cwd=repo_dir, check=True)

    # Second commit + annotated tag v1.0
    f2 = repo_dir / "file2.txt"
    f2.write_text("hello 2")
    subprocess.run(["git", "add", "file2.txt"], cwd=repo_dir, check=True)
    env2 = {
        **base_env,
        "GIT_AUTHOR_DATE": "2026-02-01T12:00:00Z",
        "GIT_COMMITTER_DATE": "2026-02-01T12:00:00Z",
    }
    subprocess.run(["git", "commit", "-m", "commit 2"], cwd=repo_dir, check=True, env=env2)
    subprocess.run(
        ["git", "tag", "-a", "v1.0", "-m", "release 1.0"],
        cwd=repo_dir,
        check=True,
        env={**base_env, "GIT_COMMITTER_DATE": "2026-02-02T12:00:00Z"},
    )

    return repo_dir


async def test_extract_tags_from_git_success(temp_git_repo_with_tags: Path):
    tags = await extract_tags_from_git(temp_git_repo_with_tags)
    assert len(tags) == 2
    assert [t.tag_name for t in tags] == ["v0.1", "v1.0"]
    # Check author dates (lightweight uses commit author date; annotated dereferences to commit author date)
    assert tags[0].published_at.year == 2026
    assert tags[0].published_at.month == 1
    assert tags[1].published_at.year == 2026
    assert tags[1].published_at.month == 2
    # Check commit SHAs are present and peeled
    assert tags[0].commit_sha is not None
    assert tags[1].commit_sha is not None
    assert tags[0].commit_sha != tags[1].commit_sha


async def test_extract_tags_nonexistent_directory(tmp_path: Path):
    with pytest.raises(GitCloneError):
        await extract_tags_from_git(tmp_path / "nonexistent.git")
