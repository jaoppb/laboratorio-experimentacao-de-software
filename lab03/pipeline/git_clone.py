"""Bare blobless/treeless Git clone and local commit log extraction for Lead Time.

Replaces REST compare API calls with local bare git clones (--filter=tree:0)
to achieve zero API quota consumption when computing commit lead time.
"""

from __future__ import annotations

import asyncio
import codecs
from contextlib import aclosing, asynccontextmanager
import logging
import os
import re
from pathlib import Path
import shutil
import time
from typing import TYPE_CHECKING, AsyncIterator

from metricas.schemas import Commit, Release, truncate_full_message
from pipeline.commits import ComparisonStatus, ReleaseCommits

if TYPE_CHECKING:
    from pipeline.http_client import TokenPool
    from pipeline.releases import WindowReleases

logger = logging.getLogger(__name__)


# Partial-clone filter. `tree:0` already omits trees AND blobs, so it is both
# "treeless" and "blobless" for our purposes; commit objects (SHA, author date,
# subject, full message) and tags are all we read. The group decided (Q19) on
# `combine:tree:0+blob:none`, but GitHub rejects `combine` filters on clone
# ("fatal: remote error: filter 'combine' not supported"; verified with git
# 2.54 against github.com), so it cannot be used there. Kept in one constant.
CLONE_FILTER = "--filter=tree:0"

# `git log` record layout: a record separator before each commit (so multi-line
# `%B` bodies need no newline heuristics) and a unit separator between fields.
_RECORD_START = "\x1e"
_FIELD_SEP = "\x1f"
# Split only at a separator followed by `<sha><unit separator>`, so a stray
# \x1e inside a commit body cannot cut a record.
_RECORD_SPLIT_RE = re.compile(r"\x1e(?=[0-9a-f]{40,64}\x1f)")


# `git log base..head` is streamed: a hard limit on the whole command (seconds)
# and the block size read from its stdout.
GIT_LOG_TIMEOUT = 900.0
GIT_LOG_BLOCK_BYTES = 1 << 20
# Longest `<sha><unit separator>` that follows a record separator (64 hex + 1)
# plus the separator itself: a block boundary inside it cannot be decided yet.
_RECORD_LOOKAHEAD = 66


class GitCloneError(Exception):
    """Raised when git clone fails."""


class GitCommandError(Exception):
    """A streamed git command exited with a non-zero status."""

    def __init__(self, returncode: int, stderr: str) -> None:
        super().__init__(f"git exited with {returncode}: {stderr.strip()}")
        self.returncode = returncode
        self.stderr = stderr


def safe_rmtree(path: Path | str) -> None:
    """Robustly remove directory tree, resetting read-only permissions if needed."""
    p = Path(path)
    if not p.exists():
        return
    import stat

    def _on_error(func, target_path, exc_info):
        try:
            os.chmod(target_path, stat.S_IWRITE | stat.S_IWUSR | stat.S_IRUSR)
            func(target_path)
        except Exception:
            pass

    try:
        shutil.rmtree(p, onerror=_on_error)
    except Exception:
        shutil.rmtree(p, ignore_errors=True)


async def run_git_command(
    args: list[str],
    cwd: Path | str | None = None,
    timeout: float = 120.0,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Execute a git command asynchronously with timeout."""
    cmd_env = dict(os.environ)
    cmd_env["GIT_TERMINAL_PROMPT"] = "0"
    if env:
        cmd_env.update(env)

    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=cmd_env,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return (
            proc.returncode or 0,
            stdout_bytes.decode("utf-8", errors="replace"),
            stderr_bytes.decode("utf-8", errors="replace"),
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        raise TimeoutError(f"Git command timed out after {timeout}s: git {' '.join(args)}")


async def stream_git_stdout(
    args: list[str],
    cwd: Path | str | None = None,
    timeout: float = GIT_LOG_TIMEOUT,
    block_size: int = GIT_LOG_BLOCK_BYTES,
    env: dict[str, str] | None = None,
) -> AsyncIterator[str]:
    """Run a git command and yield its stdout as decoded text, block by block.

    The whole output is never held: the child's stdout is read in blocks of
    `block_size` bytes and decoded incrementally (UTF-8, undecodable bytes
    replaced, like `run_git_command`). `timeout` is a deadline for the whole
    command; the child is killed when it expires or when the consumer stops
    early. Raises `TimeoutError` on timeout and `GitCommandError` (with the
    stderr) if git exits with a non-zero status after the output was read.
    """
    cmd_env = dict(os.environ)
    cmd_env["GIT_TERMINAL_PROMPT"] = "0"
    if env:
        cmd_env.update(env)

    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=cmd_env,
    )
    assert proc.stdout is not None and proc.stderr is not None
    stderr_chunks: list[bytes] = []

    async def drain_stderr() -> None:
        # Keep only the head: it is enough to explain a failure and it cannot fill the pipe
        kept = 0
        while chunk := await proc.stderr.read(65536):  # type: ignore[union-attr]
            if kept < 65536:
                stderr_chunks.append(chunk)
                kept += len(chunk)

    stderr_task = asyncio.create_task(drain_stderr())
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    deadline = time.monotonic() + timeout
    finished = False
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError
            block = await asyncio.wait_for(proc.stdout.read(block_size), timeout=remaining)
            if not block:
                break
            text = decoder.decode(block)
            if text:
                yield text
        tail = decoder.decode(b"", final=True)
        if tail:
            yield tail
        remaining = max(deadline - time.monotonic(), 0.001)
        await asyncio.wait_for(proc.wait(), timeout=remaining)
        await stderr_task
        finished = True
        if proc.returncode:
            raise GitCommandError(
                proc.returncode, b"".join(stderr_chunks).decode("utf-8", errors="replace")
            )
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"Git command timed out after {timeout}s: git {' '.join(args)}"
        ) from None
    finally:
        if not finished:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
            stderr_task.cancel()
            try:
                await stderr_task
            except (asyncio.CancelledError, Exception):
                pass


async def fetch_all_tags(git_dir: Path | str, auth_args: list[str] | None = None) -> bool:
    """Fetch every tag into a single-branch clone, keeping the partial-clone filter.

    `--single-branch` only brings tags reachable from the default branch, so
    releases tagged on maintenance branches (e.g. `v19.0.x` backports) would be
    missing and their lead time would be skipped as not found. Fetching
    `refs/tags/*` adds the commits of those branches without trees or blobs.
    Returns False (and keeps the clone usable) if the fetch fails.
    """
    args = [
        *(auth_args or []),
        f"--git-dir={git_dir}",
        "fetch",
        "--quiet",
        CLONE_FILTER,
        "origin",
        "+refs/tags/*:refs/tags/*",
    ]
    retcode, _, stderr = await run_git_command(args, timeout=600.0)
    if retcode != 0:
        logger.warning("git fetch of all tags failed in %s: %s", git_dir, stderr.strip())
        return False
    return True


async def clone_repository(
    owner: str,
    repo: str,
    target_dir: Path | str,
    token_pool: TokenPool | None = None,
) -> Path:
    """Clone repository superficially (--bare --filter=tree:0 --single-branch).

    First attempts anonymous clone. If rate-limited or authentication is required,
    retries by injecting a GitHub token from the TokenPool via HTTP header.
    """
    target = Path(target_dir)
    if (target / "HEAD").is_file():
        logger.debug("Existing git clone found at %s, skipping clone.", target)
        return target

    if target.exists():
        safe_rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    url = f"https://github.com/{owner}/{repo}.git"
    clone_args = [
        "clone",
        "--bare",
        CLONE_FILTER,
        "--single-branch",
        url,
        str(target),
    ]

    logger.info("Starting anonymous git clone for %s/%s...", owner, repo)
    retcode, stdout, stderr = await run_git_command(clone_args)

    if retcode == 0:
        logger.info("Successfully cloned %s/%s anonymously.", owner, repo)
        await fetch_all_tags(target)
        return target

    # Check for authentication / rate-limit failures
    is_auth_or_ratelimit = any(
        err_pattern in stderr.lower()
        for err_pattern in ("403", "429", "authentication", "rate limit", "username")
    )

    if is_auth_or_ratelimit and token_pool and token_pool.has_tokens:
        token = await token_pool.get_next_token()
        if token:
            logger.warning(
                "Anonymous clone failed for %s/%s. Retrying with token from pool...",
                owner,
                repo,
            )
            if target.exists():
                safe_rmtree(target)
            auth_header = ["-c", f"http.extraHeader=Authorization: Bearer {token}"]
            auth_args = [
                *auth_header,
                "clone",
                "--bare",
                CLONE_FILTER,
                "--single-branch",
                url,
                str(target),
            ]
            retcode, stdout, stderr = await run_git_command(auth_args)
            if retcode == 0:
                logger.info("Successfully cloned %s/%s with token.", owner, repo)
                await fetch_all_tags(target, auth_header)
                return target

    # Clean up incomplete clone
    if target.exists():
        safe_rmtree(target)
    raise GitCloneError(f"git clone failed for {owner}/{repo} (exit {retcode}): {stderr.strip()}")


async def _iter_log_records(chunks: AsyncIterator[str]) -> AsyncIterator[str]:
    """Split a stream of `git log` text into records, one at a time.

    Same boundaries as `_RECORD_SPLIT_RE.split` over the whole output: a record
    separator only cuts when it is followed by `<sha><unit separator>`, so a
    stray one inside a body does not. A block boundary can fall inside the
    lookahead; the pending tail then stays in the buffer until the next block.
    """
    buffer = ""
    scanned = 0  # no unresolved separator before this offset of `buffer`
    async for chunk in chunks:
        buffer += chunk
        start = 0
        for match in _RECORD_SPLIT_RE.finditer(buffer, scanned):
            yield buffer[start : match.start()]
            start = match.end()
        buffer = buffer[start:]
        scanned = max(0, len(buffer) - _RECORD_LOOKAHEAD)
    yield buffer


def _parse_log_record(
    record: str,
    commit_cache: dict[str, Commit] | None,
    fresh: dict[str, Commit],
) -> Commit | None:
    """Parse one `git log` record; reuse the commit of a SHA already seen.

    The SHA is read first: when it is in `commit_cache` (or already parsed in
    this range) nothing else is built. New commits go to `fresh`.
    """
    record = record.strip()
    if not record:
        return None
    sep = record.find(_FIELD_SEP)
    if sep < 0:
        return None
    sha = record[:sep]
    if commit_cache is not None:
        known = commit_cache.get(sha)
        if known is not None:
            return known
    parts = record.split(_FIELD_SEP, 3)
    if len(parts) >= 3:
        commit = Commit(
            sha=parts[0],
            committed_at=parts[1],
            message=parts[2].strip(),
            full_message=truncate_full_message(parts[3]) if len(parts) == 4 else None,
        )
    else:
        commit = Commit(sha=parts[0], committed_at=parts[1], message="")
    fresh[sha] = commit
    return commit


async def get_commits_between_tags(
    git_dir: Path | str,
    base_tag: str,
    head_tag: str,
    commit_cache: dict[str, Commit] | None = None,
    timeout: float = GIT_LOG_TIMEOUT,
    block_size: int = GIT_LOG_BLOCK_BYTES,
) -> list[Commit]:
    """Retrieve commits between base_tag and head_tag using git log in bare repository.

    The log is streamed and parsed one record at a time (the output is never
    held whole). With `commit_cache` (SHA -> `Commit`, one table per
    repository) a commit already in the table is reused instead of built
    again, and the new ones are added to it when the range succeeds, so the
    ranges of a repository share one `Commit` object per SHA.
    """
    git_path = Path(git_dir)
    target_git_dir = git_path / ".git" if (git_path / ".git").is_dir() else git_path
    fmt = f"{_RECORD_START}%H{_FIELD_SEP}%aI{_FIELD_SEP}%s{_FIELD_SEP}%B"
    args = [
        f"--git-dir={target_git_dir}",
        "log",
        f"{base_tag}..{head_tag}",
        f"--format={fmt}",
    ]

    commits: list[Commit] = []
    fresh: dict[str, Commit] = {}
    try:
        async with (
            aclosing(stream_git_stdout(args, timeout=timeout, block_size=block_size)) as stream,
            aclosing(_iter_log_records(stream)) as records,
        ):
            async for record in records:
                commit = _parse_log_record(record, commit_cache, fresh)
                if commit is not None:
                    commits.append(commit)
    except GitCommandError as exc:
        logger.debug(
            "git log failed for %s..%s in %s: %s", base_tag, head_tag, git_path, exc.stderr.strip()
        )
        raise KeyError(f"Tags not resolvable: {base_tag}..{head_tag}") from None
    if commit_cache is not None:
        commit_cache.update(fresh)
    return commits


async def collect_release_commits_from_git(
    git_dir: Path | str,
    window: WindowReleases,
    commit_cache: dict[str, Commit] | None = None,
) -> list[ReleaseCommits]:
    """Collect commits of in-window releases using local git log.

    `commit_cache` is the per-repository SHA table (see `get_commits_between_tags`).
    """
    ordered = window.with_anchor()
    offset = 1 if window.anchor is not None else 0
    results: list[ReleaseCommits] = []

    for i in range(offset, len(ordered)):
        previous = ordered[i - 1] if i > 0 else None
        release = ordered[i]

        if previous is None:
            results.append(ReleaseCommits(release, None, ComparisonStatus.FIRST_RELEASE))
            continue

        try:
            commits = await get_commits_between_tags(
                git_dir=git_dir,
                base_tag=previous.tag_name,
                head_tag=release.tag_name,
                **({"commit_cache": commit_cache} if commit_cache is not None else {}),
            )
            results.append(ReleaseCommits(release, previous, ComparisonStatus.OK, commits))
        except KeyError:
            logger.debug(
                "Tags %s..%s not found in git repo %s; release marked NOT_FOUND",
                previous.tag_name,
                release.tag_name,
                git_dir,
            )
            results.append(ReleaseCommits(release, previous, ComparisonStatus.NOT_FOUND))

    return results


async def extract_tags_from_git(git_dir: Path | str) -> list[Release]:
    """Extract all git tags from a bare clone, dated by commit author date (oldest first)."""
    git_path = Path(git_dir)
    if not git_path.exists():
        raise GitCloneError(f"Git directory not found: {git_path}")

    target_git_dir = git_path / ".git" if (git_path / ".git").is_dir() else git_path

    sep = "\t"
    fmt = (
        f"%(refname:short){sep}"
        f"%(if)%(*authordate:iso-strict)%(then)%(*authordate:iso-strict)%(else)%(authordate:iso-strict)%(end){sep}"
        f"%(if)%(*objectname)%(then)%(*objectname)%(else)%(objectname)%(end)"
    )
    args = [
        f"--git-dir={target_git_dir}",
        "for-each-ref",
        f"--format={fmt}",
        "refs/tags",
    ]

    retcode, stdout, stderr = await run_git_command(args)
    if retcode != 0:
        raise GitCloneError(f"git for-each-ref failed in {git_path}: {stderr.strip()}")

    tags: list[Release] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(sep, 2)
        if len(parts) >= 2:
            tag_name = parts[0]
            date_str = parts[1].strip()
            sha = parts[2].strip() if len(parts) > 2 else None
            if not date_str:
                continue
            tags.append(
                Release(
                    tag_name=tag_name,
                    published_at=date_str,
                    draft=False,
                    prerelease=False,
                    commit_sha=sha or None,
                )
            )

    return sorted(tags, key=lambda t: t.published_at)


@asynccontextmanager
async def temporary_git_clone(
    owner: str,
    repo: str,
    cache_dir: Path | str = "cache/git_repos",
    auto_cleanup: bool = True,
    token_pool: TokenPool | None = None,
) -> AsyncIterator[Path]:
    """Async context manager to provide a local bare clone with optional auto-cleanup."""
    clone_path = Path(cache_dir) / f"{owner}__{repo}.git"
    await clone_repository(owner, repo, clone_path, token_pool=token_pool)
    try:
        yield clone_path
    finally:
        if auto_cleanup and clone_path.exists():
            safe_rmtree(clone_path)
