"""Streaming `git log`, SHA dedupe and the streaming timeout (pipeline.git_clone, Issue #56)."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from metricas.schemas import MAX_FULL_MESSAGE_CHARS, Commit, Release, truncate_full_message
from pipeline.commits import ComparisonStatus
from pipeline.git_clone import (
    _FIELD_SEP,
    _RECORD_SPLIT_RE,
    GitCommandError,
    _iter_log_records,
    collect_release_commits_from_git,
    extract_tags_from_git,
    get_commits_between_tags,
    run_git_command,
    stream_git_stdout,
)
from pipeline.releases import WindowReleases
from tests.git_helpers import make_divergent_repo
from tests.test_git_clone import _record, fake_git_stream


async def _blocks(text: str, size: int):
    for i in range(0, len(text), size):
        yield text[i : i + size]


async def _records(text: str, size: int) -> list[str]:
    return [r async for r in _iter_log_records(_blocks(text, size))]


async def _commits(stdout: str, block: int, cache=None) -> list[Commit]:
    with patch("pipeline.git_clone.stream_git_stdout", fake_git_stream(stdout, block=block)):
        return await get_commits_between_tags("/tmp/repo.git", "v1", "v2", commit_cache=cache)


def _reference_parse(stdout: str) -> list[Commit]:
    """The parser as it was before streaming: split the whole output, parse every record."""
    commits = []
    for record in _RECORD_SPLIT_RE.split(stdout):
        record = record.strip()
        if not record:
            continue
        parts = record.split(_FIELD_SEP, 3)
        if len(parts) >= 3:
            commits.append(
                Commit(
                    sha=parts[0],
                    committed_at=parts[1],
                    message=parts[2].strip(),
                    full_message=truncate_full_message(parts[3]) if len(parts) == 4 else None,
                )
            )
        elif len(parts) == 2:
            commits.append(Commit(sha=parts[0], committed_at=parts[1], message=""))
    return commits


def _sha(n: int) -> str:
    return f"{n:040x}"


# ----------------------------------------------------------------- the splitter


@pytest.mark.parametrize("size", [1, 2, 3, 5, 41, 65, 66, 67, 100, 10_000])
async def test_record_boundaries_may_fall_anywhere_in_a_record(size):
    out = "".join(
        _record(_sha(i), "2026-02-18T19:41:55Z", f"feat: {i}", "body\nline\n" * (i % 4))
        for i in range(1, 12)
    )
    assert await _records(out, size) == _RECORD_SPLIT_RE.split(out)


@pytest.mark.parametrize("size", [1, 7, 40, 41, 42, 66, 1000])
async def test_stray_record_separator_never_splits_at_any_block_size(size):
    stray = [
        "weird \x1e body",
        "\x1e" + "a" * 39 + "\x1f",  # one hex digit short of a SHA
        "\x1e" + "g" * 40 + "\x1f",  # not hex
        "\x1e" + "a" * 40,  # no unit separator after it
        "ends with \x1e",
    ]
    out = "".join(
        _record(_sha(i), "2026-02-18T19:41:55Z", "feat: a", body) for i, body in enumerate(stray, 1)
    )
    commits = await _commits(out, size)
    assert [c.sha for c in commits] == [_sha(i) for i in range(1, len(stray) + 1)]
    for commit, body in zip(commits, stray):
        assert body.strip() in commit.full_message


@pytest.mark.parametrize("size", [1, 3, 64, 1000])
async def test_a_record_separator_followed_by_a_sha_still_splits(size):
    # `\x1e<sha>\x1f` is a record start even inside a body: same as the whole-output split
    body = "x \x1e" + "b" * 40 + "\x1f tail"
    out = _record(_sha(1), "2026-02-18T19:41:55Z", "feat: a", body)
    assert await _records(out, size) == _RECORD_SPLIT_RE.split(out)


@pytest.mark.parametrize("seed", range(5))
async def test_random_outputs_split_like_the_whole_output(seed):
    rng = random.Random(seed)
    alphabet = ["a", "f", "0", "\x1e", "\x1f", "\n", " ", "é", "x"]
    out = ""
    for i in range(30):
        body = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 120)))
        out += _record(_sha(i + 1), "2026-02-18T19:41:55Z", f"s{i}", body)
    for size in (1, 13, 66, 500):
        assert await _records(out, size) == _RECORD_SPLIT_RE.split(out)


async def test_empty_output_has_no_commit():
    assert await _commits("", 5) == []
    assert await _commits("\n\n", 5) == []


# ------------------------------------------------------------ parsing semantics


@pytest.mark.parametrize("size", [1, 9, 64, 5000])
async def test_streaming_parse_equals_the_whole_output_parse(size):
    out = _record(_sha(1), "2026-02-18T19:41:55Z", "Revert \"feat: x\"", "This reverts commit abc.")
    out += _record(_sha(2), "2026-02-18T18:00:00-03:00", "docs: café ✓ 日本")
    out += "\x1e" + _sha(3) + "\x1f2026-02-18T17:00:00Z\x1ffix: crlf\x1ffix: crlf\r\n\r\nbody\r\nhotfix\r\n\n"
    out += "\x1e" + _sha(4) + "\x1f2026-02-18T16:00:00Z"  # short record: only SHA and date
    out += _record(_sha(5), "2026-02-18T15:00:00Z", "feat: empty body", "")
    out += _record(_sha(6), "2026-02-18T14:00:00Z", "feat: big", "y" * (MAX_FULL_MESSAGE_CHARS * 3))
    commits = await _commits(out, size)
    assert commits == _reference_parse(out)
    assert commits[2].full_message == "fix: crlf\n\nbody\nhotfix"
    assert commits[3].message == "" and commits[3].full_message is None
    assert len(commits[5].full_message) == MAX_FULL_MESSAGE_CHARS


async def test_a_record_without_field_separator_is_skipped():
    commits = await _commits("\x1e" + "c" * 40 + "\n", 4)
    assert commits == _reference_parse("\x1e" + "c" * 40 + "\n") == []


# ------------------------------------------------------------------------ dedupe


def _overlapping_output() -> tuple[str, str]:
    first = "".join(_record(_sha(i), f"2026-02-0{i}T10:00:00Z", f"feat: {i}", "b") for i in (1, 2, 3))
    second = "".join(_record(_sha(i), f"2026-02-0{i}T10:00:00Z", f"feat: {i}", "b") for i in (2, 3, 4))
    return first, second


async def test_cache_gives_one_commit_object_per_sha():
    first, second = _overlapping_output()
    cache: dict[str, Commit] = {}
    a = await _commits(first, 11, cache)
    b = await _commits(second, 11, cache)

    assert len(cache) == 4
    assert [c.sha for c in b] == [_sha(2), _sha(3), _sha(4)]
    assert b[0] is a[1] and b[1] is a[2]  # shared, not copied
    assert b[2] is cache[_sha(4)]
    # same fields with and without the cache
    assert a == await _commits(first, 11) and b == await _commits(second, 11)


async def test_cached_commits_are_not_rebuilt():
    first, second = _overlapping_output()
    cache = {c.sha: c for c in await _commits(first, 11)}
    built = []
    real_init = Commit.__post_init__

    def counting(self):
        built.append(self.sha)
        real_init(self)

    with patch.object(Commit, "__post_init__", counting):
        await _commits(second, 11, cache)
    assert built == [_sha(4)]  # only the new one was built


async def test_a_failed_range_does_not_pollute_the_cache():
    first, _ = _overlapping_output()
    stream = fake_git_stream(first, error=GitCommandError(128, "fatal: bad"))
    cache: dict[str, Commit] = {}
    with patch("pipeline.git_clone.stream_git_stdout", stream):
        with pytest.raises(KeyError):
            await get_commits_between_tags("/tmp/repo.git", "v1", "v2", commit_cache=cache)
    assert cache == {}


async def test_collect_release_commits_passes_the_cache_to_every_range():
    first, second = _overlapping_output()
    outputs = {"v2": first, "v3": second}
    releases = [
        Release(tag_name=f"v{i}", published_at=datetime(2026, i, 1, tzinfo=timezone.utc))
        for i in (1, 2, 3)
    ]

    async def fake_stream(args, *_, **__):
        head = args[2].split("..")[1]
        for i in range(0, len(outputs[head]), 20):
            yield outputs[head][i : i + 20]

    cache: dict[str, Commit] = {}
    with patch("pipeline.git_clone.stream_git_stdout", fake_stream):
        shared = await collect_release_commits_from_git(
            "/tmp/repo.git", WindowReleases(in_window=releases), commit_cache=cache
        )
        plain = await collect_release_commits_from_git(
            "/tmp/repo.git", WindowReleases(in_window=releases)
        )
    assert shared == plain  # same releases, statuses and commits, same order
    assert [r.status for r in shared] == [ComparisonStatus.FIRST_RELEASE] + [ComparisonStatus.OK] * 2
    assert len(cache) == 4
    assert shared[2].commits[0] is shared[1].commits[1]
    assert len({id(c) for rc in shared for c in rc.commits}) == 4
    assert len({id(c) for rc in plain for c in rc.commits}) == 6


# ------------------------------------------------------------ real git (stream)


@pytest.fixture(scope="module")
def divergent(tmp_path_factory) -> Path:
    return make_divergent_repo(tmp_path_factory.mktemp("divergent"), per_line=30, n_tags=12)


async def test_stream_matches_run_git_command_with_tiny_blocks(divergent):
    args = [f"--git-dir={divergent}", "log", "--format=%H%x1f%B%x1e", "main"]
    code, whole, _ = await run_git_command(args)
    assert code == 0
    streamed = "".join([c async for c in stream_git_stdout(args, block_size=64)])
    assert streamed == whole and len(whole) > 64 * 10


async def test_stream_reports_a_failure_after_the_output(tmp_path):
    with pytest.raises(GitCommandError) as exc:
        async for _ in stream_git_stdout([f"--git-dir={tmp_path}", "log", "nope..nada"]):
            pass
    assert exc.value.returncode != 0 and exc.value.stderr


async def test_unresolvable_tags_still_raise_key_error(divergent):
    with pytest.raises(KeyError):
        await get_commits_between_tags(divergent, "no-such-tag", "v0001")


async def test_stream_timeout_kills_the_child():
    # `git slow` is an alias for a shell `sleep`: the child never closes stdout in time
    args = ["-c", "alias.slow=!sleep 5", "slow"]
    loop = asyncio.get_running_loop()
    start = loop.time()
    with pytest.raises(TimeoutError):
        async for _ in stream_git_stdout(args, timeout=0.3):
            pass
    assert loop.time() - start < 3


async def test_stopping_early_does_not_leave_the_stream_running(divergent):
    args = [f"--git-dir={divergent}", "log", "--format=%H%n%B", "main"]
    stream = stream_git_stdout(args, block_size=16)
    first = await stream.__anext__()
    assert first
    await stream.aclose()  # kills the child; must not hang or raise


async def test_real_log_with_tiny_blocks_equals_the_default(divergent):
    tags = await extract_tags_from_git(divergent)
    names = [t.tag_name for t in tags]
    for base, head in zip(names, names[1:]):
        tiny = await get_commits_between_tags(divergent, base, head, block_size=37)
        default = await get_commits_between_tags(divergent, base, head)
        assert tiny == default
