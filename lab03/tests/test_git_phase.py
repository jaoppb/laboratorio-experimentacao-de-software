"""Git phase of one repository: equivalence with the old in-memory path, memory bound, child process.

Offline: the commits come from synthetic Git repositories built with `git`.
"""

from __future__ import annotations

import asyncio
import gc
import json
import os
import sys
import tracemalloc
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from metricas.cfr_b import DEFAULT_HEURISTIC
from metricas.lead_time import calculate_lead_time
from metricas.schemas import Commit, Release, WorkflowRun, truncate_full_message, window_length
from metricas.dora import calculate_deployment_frequency, evaluate_repository_dora
from metricas.stability import calculate_cfr_a, calculate_recovery_time
from pipeline import git_phase
from pipeline.commit_store import load_commit_store, load_release_commits, load_tag_commits
from pipeline.commits import collect_release_commits
from pipeline.git_clone import (
    _FIELD_SEP,
    _RECORD_SPLIT_RE,
    _RECORD_START,
    collect_release_commits_from_git,
    extract_tags_from_git,
    run_git_command,
)
from pipeline.git_phase import GitPhaseError, GitPhaseSpec, run_git_phase, run_git_phase_in_child
from pipeline.orchestrator import (
    C2C3Units,
    collect_c2_c3_units,
    compose_metric_columns,
    compute_c2_c3_columns,
    compute_cfr_b_columns,
    compute_metric_columns,
    compute_run_columns,
)
from pipeline.releases import WindowReleases, filter_window
from tests.git_helpers import make_divergent_repo
from tests.test_git_clone import _record, fake_git_stream
from tests.test_regenerar import ALPHA, _make_bare_clone, _runs

WINDOW_START = datetime(2025, 10, 1, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 9, 30, 23, 59, 59, 999999, tzinfo=timezone.utc)
WINDOW_WEEKS = window_length(WINDOW_START, WINDOW_END) / timedelta(weeks=1)


# ------------------------------------------------------- the old (reference) path


async def reference_get_commits(git_dir, base_tag, head_tag, **_):
    """`get_commits_between_tags` as it was before streaming: whole output, no table."""
    git_path = Path(git_dir)
    target = git_path / ".git" if (git_path / ".git").is_dir() else git_path
    fmt = f"{_RECORD_START}%H{_FIELD_SEP}%aI{_FIELD_SEP}%s{_FIELD_SEP}%B"
    code, stdout, _ = await run_git_command(
        [f"--git-dir={target}", "log", f"{base_tag}..{head_tag}", f"--format={fmt}"]
    )
    if code != 0:
        raise KeyError(f"Tags not resolvable: {base_tag}..{head_tag}")
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


def frozen_compute_metric_columns(
    *, releases, window_releases, runs, valid_runs_count, release_commits_c1, units,
    window_start, window_end, window_weeks, cfr_b_heuristic=DEFAULT_HEURISTIC,
) -> dict:  # fmt: skip
    """`compute_metric_columns` exactly as it was before the split (frozen reference)."""
    lead_time_c1 = calculate_lead_time(
        [(rc.release, rc.commits_or_none) for rc in release_commits_c1]
    )
    dep_freq = calculate_deployment_frequency(
        releases=releases, window_weeks=window_weeks, start_date=window_start, end_date=window_end
    )
    cfr_a = calculate_cfr_a(runs)
    recovery_result = calculate_recovery_time(runs)
    lead_time_a = lead_time_c1.median_a_hours
    lead_time_days = (lead_time_a / 24.0) if lead_time_a is not None else None
    dora_eval = evaluate_repository_dora(
        deployment_frequency=dep_freq,
        lead_time_days=lead_time_days,
        cfr=cfr_a,
        recovery_hours=recovery_result.median_hours,
        failure_episodes=recovery_result.total_episodes,
    )
    return {
        "releases_count_window": window_releases.count,
        "total_releases": len(releases),
        "workflow_runs_count_window": valid_runs_count,
        "total_workflow_runs": len(runs),
        "deployment_frequency": dep_freq,
        "deployment_tier": dora_eval.deployment_tier.value,
        "lead_time_a_hours": lead_time_a,
        "lead_time_b_hours": lead_time_c1.median_b_hours,
        "lead_time_tier": (
            dora_eval.lead_time_tier.value if dora_eval.lead_time_tier is not None else None
        ),
        "cfr_a": cfr_a,
        "cfr_tier": dora_eval.cfr_tier.value,
        "recovery_hours": recovery_result.median_hours,
        "recovery_tier": dora_eval.recovery_tier.value,
        "censored_episodes_ratio": recovery_result.censored_ratio,
        "overall_dora_score": dora_eval.overall_score,
        "overall_dora_tier": dora_eval.overall_tier.value,
        **compute_c2_c3_columns(
            units.release_commits_c2,
            units.tag_commits_c3,
            total_prereleases=len([r for r in releases if r.prerelease]),
            total_tags=len(units.all_tags),
            window_weeks=window_weeks,
        ),
        **compute_cfr_b_columns(
            release_commits_c1, window_end=window_end, heuristic=cfr_b_heuristic
        ),
        **compute_cfr_b_columns(
            units.release_commits_c2,
            window_end=window_end,
            heuristic=cfr_b_heuristic,
            prefix="c2_",
        ),
    }


async def reference_record(git_dir, releases, runs, heuristic) -> dict:
    """Old path: one `Commit` per range, everything in memory, the frozen metric function."""
    window_releases = filter_window(releases, WINDOW_START, WINDOW_END)
    with patch("pipeline.git_clone.get_commits_between_tags", reference_get_commits):
        c1 = await collect_release_commits(None, "o", "r", window_releases, git_dir=git_dir)
        units = await collect_c2_c3_units(git_dir, releases, WINDOW_START, WINDOW_END)
    return frozen_compute_metric_columns(
        releases=releases,
        window_releases=window_releases,
        runs=runs,
        valid_runs_count=len(runs),
        release_commits_c1=c1,
        units=units,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        window_weeks=WINDOW_WEEKS,
        cfr_b_heuristic=heuristic,
    )


def new_record(result: dict, releases, runs) -> dict:
    """New path: the git phase result composed with the run-derived columns."""
    commit_columns = result["columns"]
    run_columns = compute_run_columns(
        releases=releases,
        window_releases=filter_window(releases, WINDOW_START, WINDOW_END),
        runs=runs,
        valid_runs_count=len(runs),
        lead_time_a_hours=commit_columns["lead_time_a_hours"],
        lead_time_b_hours=commit_columns["lead_time_b_hours"],
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        window_weeks=WINDOW_WEEKS,
    )
    return compose_metric_columns(run_columns, commit_columns)


def make_spec(git_dir, dados, releases, heuristic=DEFAULT_HEURISTIC) -> GitPhaseSpec:
    return GitPhaseSpec.build(
        owner="o", repo="r", git_dir=git_dir, dados_dir=dados, releases=releases,
        window_start=WINDOW_START, window_end=WINDOW_END, window_weeks=WINDOW_WEEKS,
        heuristic=heuristic,
    )  # fmt: skip


@pytest.fixture
def alpha(tmp_path):
    git_cache = tmp_path / "git"
    _make_bare_clone(tmp_path, git_cache, "acme/alpha")
    releases = [Release(tag_name=t, published_at=d, prerelease=p) for t, d, _, p in ALPHA]
    return git_cache / "acme__alpha.git", releases


@pytest.fixture
def divergent(tmp_path):
    git_dir = make_divergent_repo(tmp_path, per_line=25, n_tags=40)
    tags = asyncio.run(extract_tags_from_git(git_dir))
    # every third tag is a release, every ninth a pre-release; all the tags are C3
    releases = [
        Release(tag_name=t.tag_name, published_at=t.published_at, prerelease=i % 9 == 0)
        for i, t in enumerate(tags)
        if i % 3 == 0
    ]
    return git_dir, releases


# ------------------------------------------------------------------ golden test


@pytest.mark.parametrize(
    ("repo", "heuristic"),
    [("alpha", "v1"), ("alpha", "v1_full_message"), ("divergent", "v1_full_message")],
)
async def test_new_path_equals_the_old_in_memory_path_on_every_column(
    repo, heuristic, alpha, divergent, tmp_path
):
    git_dir, releases = alpha if repo == "alpha" else divergent
    runs = _runs()

    expected = await reference_record(git_dir, releases, runs, heuristic)
    result = await run_git_phase(make_spec(git_dir, tmp_path / "dados", releases, heuristic))
    actual = new_record(result, releases, runs)

    assert list(actual) == list(expected)  # same columns, same order
    assert actual == expected  # same values, floats included (exact ==)
    assert actual["tags_count_window"] > 0 and actual["total_tags"] > 0
    # and the composed in-process function of the pipeline is the frozen one too
    window_releases = filter_window(releases, WINDOW_START, WINDOW_END)
    with patch("pipeline.git_clone.get_commits_between_tags", reference_get_commits):
        c1 = await collect_release_commits(None, "o", "r", window_releases, git_dir=git_dir)
        units = await collect_c2_c3_units(git_dir, releases, WINDOW_START, WINDOW_END)
    kwargs = dict(
        releases=releases, window_releases=window_releases, runs=runs, valid_runs_count=len(runs),
        release_commits_c1=c1, units=units, window_start=WINDOW_START, window_end=WINDOW_END,
        window_weeks=WINDOW_WEEKS, cfr_b_heuristic=heuristic,
    )  # fmt: skip
    assert compute_metric_columns(**kwargs) == frozen_compute_metric_columns(**kwargs)


async def test_files_written_by_the_phase_read_back_as_the_old_objects(divergent, tmp_path):
    git_dir, releases = divergent
    dados = tmp_path / "dados"
    await run_git_phase(make_spec(git_dir, dados, releases))

    window_releases = filter_window(releases, WINDOW_START, WINDOW_END)
    with patch("pipeline.git_clone.get_commits_between_tags", reference_get_commits):
        c1 = await collect_release_commits(None, "o", "r", window_releases, git_dir=git_dir)
        units = await collect_c2_c3_units(git_dir, releases, WINDOW_START, WINDOW_END)

    store = load_commit_store(dados / "commits" / "o__r.parquet")
    assert {c.sha for rc in c1 + units.release_commits_c2 + units.tag_commits_c3 for c in rc.commits} == set(store)
    for folder, expected in (("releases", c1), ("releases_c2", units.release_commits_c2)):
        loaded = load_release_commits(dados / folder / "o__r.parquet", store)
        assert [(u.release, u.status, u.commits) for u in loaded] == [
            (u.release, u.status, u.commits) for u in expected
        ]
    loaded_tags = load_tag_commits(dados / "tags" / "o__r.parquet", store)
    assert [(u.release.tag_name, u.commits) for u in loaded_tags][1:] == [
        (u.release.tag_name, u.commits) for u in units.tag_commits_c3
    ][1:]
    # the three definitions share the commit objects once loaded
    assert len({id(c) for u in loaded_tags for c in u.commits}) <= len(store)


async def test_phase_result_is_json_serialisable_and_round_trips(alpha, tmp_path):
    git_dir, releases = alpha
    result = await run_git_phase(make_spec(git_dir, tmp_path / "dados", releases))
    assert json.loads(json.dumps(result)) == result
    assert set(result) == {"columns", "distinct_commits", "peak_rss_mb"}
    assert result["distinct_commits"] == len(ALPHA) - 1  # the first tag has no range


# ---------------------------------------------------------------- memory bound


def _synthetic_log(distinct: int):
    """`git log` text of a commit pool: the records, each with a short body."""
    return [
        _record(
            f"{i:040x}",
            f"2026-03-{(i % 27) + 1:02d}T10:00:00Z",
            f"fix: change number {i}",
            f"Longer description of change {i}.\n\nFixes #{i}",
        )
        for i in range(distinct)
    ]


async def test_memory_of_the_new_path_is_a_small_fraction_of_the_old_one():
    """2,000 tags whose consecutive ranges overlap almost completely (like CI tags)."""
    n_tags, distinct, per_range = 2000, 400, 60
    pool = _synthetic_log(distinct)
    tags = [
        Release(tag_name=f"t{i:04d}", published_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i))
        for i in range(n_tags)
    ]  # fmt: skip
    window = WindowReleases(in_window=tags)

    def range_text(head: str) -> str:
        start = (int(head[1:]) * 7) % (distinct - per_range)
        return "".join(pool[start : start + per_range])

    async def fake_stream(args, *_, **__):
        text = range_text(args[2].split("..")[1])
        for i in range(0, len(text), 4096):
            yield text[i : i + 4096]

    async def measure(commit_cache):
        gc.collect()
        tracemalloc.start()
        try:
            with patch("pipeline.git_clone.stream_git_stdout", fake_stream):
                result = await collect_release_commits_from_git(
                    "/fake.git", window, commit_cache=commit_cache
                )
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        gc.collect()
        live = sum(1 for o in gc.get_objects() if type(o) is Commit)
        return result, peak, live

    def signature(results):
        # fields only (no Commit objects), so a snapshot does not keep commits alive
        return [
            (rc.release.tag_name, rc.status, [(c.sha, c.committed_at, c.message, c.full_message) for c in rc.commits])
            for rc in results
        ]

    old, old_peak, old_live = await measure(None)
    old_snapshot = signature(old)
    instances = sum(len(rc.commits) for rc in old)
    old_ids = len({id(c) for rc in old for c in rc.commits})
    del old
    new, new_peak, new_live = await measure({})
    new_ids = len({id(c) for rc in new for c in rc.commits})
    distinct_shas = len({c.sha for rc in new for c in rc.commits})

    # identical results (tags, statuses, commits in the same order with the same fields)
    assert signature(new) == old_snapshot
    assert instances == (n_tags - 1) * per_range
    # one Commit object per distinct SHA ...
    assert new_ids == distinct_shas == new_live <= distinct
    # ... where the old path built one per range
    assert old_ids == instances and old_live >= instances
    print(
        f"\nmemory: {n_tags} tags, {instances} commit instances, {distinct_shas} distinct SHAs; "
        f"old peak {old_peak / 1e6:.1f} MB ({old_live} live Commit), "
        f"new peak {new_peak / 1e6:.2f} MB ({new_live} live Commit), "
        f"ratio {old_peak / new_peak:.0f}x"
    )
    assert new_peak < old_peak / 10


# ---------------------------------------------------------------- child process


async def test_child_process_result_equals_the_in_process_result(alpha, tmp_path):
    git_dir, releases = alpha
    in_process = await run_git_phase(make_spec(git_dir, tmp_path / "in", releases))
    child = await run_git_phase_in_child(make_spec(git_dir, tmp_path / "child", releases))

    assert child["columns"] == in_process["columns"]
    assert child["distinct_commits"] == in_process["distinct_commits"]
    assert isinstance(child["peak_rss_mb"], int) and child["peak_rss_mb"] > 0
    for folder in ("commits", "releases", "releases_c2", "tags"):
        a, b = tmp_path / "in" / folder / "o__r.parquet", tmp_path / "child" / folder / "o__r.parquet"
        assert a.read_bytes() == b.read_bytes(), folder


async def test_child_failure_is_an_error_without_partial_files(tmp_path):
    spec = make_spec(tmp_path / "no-such-clone.git", tmp_path / "dados", [])
    spec_bad = GitPhaseSpec(**{**spec.__dict__, "window_start": "not a date"})

    with pytest.raises(GitPhaseError, match="failed .*exit 1"):
        await run_git_phase_in_child(spec_bad)
    assert not list((tmp_path / "dados").rglob("*.parquet*"))


async def test_a_crashing_child_is_reported_with_its_stderr(tmp_path, monkeypatch):
    monkeypatch.setattr(git_phase.sys, "executable", sys.executable)
    original = asyncio.create_subprocess_exec

    async def crashing(*args, **kwargs):
        # same interpreter, but it dies by itself before answering
        return await original(sys.executable, "-c", "import sys; sys.stderr.write('segfault!'); sys.exit(139)", **kwargs)

    monkeypatch.setattr(git_phase.asyncio, "create_subprocess_exec", crashing)
    spec = make_spec(tmp_path / "x.git", tmp_path / "dados", [])
    with pytest.raises(GitPhaseError, match=r"exit 139.*segfault!"):
        await run_git_phase_in_child(spec)


def _sitecustomize_hanging_in_releases_c2(directory: Path, marker: Path) -> Path:
    """A `sitecustomize` that freezes the child while it writes `releases_c2/`."""
    directory.mkdir()
    (directory / "sitecustomize.py").write_text(
        "import os, time\n"
        "if os.environ.get('GIT_PHASE_TEST_HANG'):\n"
        "    import pyarrow.parquet as pq\n"
        "    original = pq.ParquetWriter.write_table\n"
        "    def write_table(self, table, *args, **kwargs):\n"
        "        original(self, table, *args, **kwargs)\n"
        "        if 'releases_c2' in str(self.where):\n"
        f"            open({str(marker)!r}, 'w').close()\n"
        "            time.sleep(600)\n"
        "    pq.ParquetWriter.write_table = write_table\n",
        encoding="utf-8",
    )
    return directory


async def test_killing_the_child_mid_write_leaves_no_partial_file(alpha, tmp_path, monkeypatch):
    """The parent gives up (cancellation) while the child is writing `releases_c2/`."""
    git_dir, releases = alpha
    dados = tmp_path / "dados"
    marker = tmp_path / "hanging"
    monkeypatch.setenv("GIT_PHASE_TEST_HANG", "1")
    monkeypatch.setenv("PYTHONPATH", str(_sitecustomize_hanging_in_releases_c2(tmp_path / "hang", marker)))

    task = asyncio.create_task(run_git_phase_in_child(make_spec(git_dir, dados, releases)))
    for _ in range(300):  # up to 30 s for the child to reach the write
        if marker.exists() or task.done():
            break
        await asyncio.sleep(0.1)
    assert marker.exists(), "the child never reached releases_c2/"
    # the temporary file of the interrupted write exists right now ...
    assert (dados / "releases_c2" / "o__r.parquet.tmp").exists()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # ... and is gone; what was completed before is whole; nothing after it was started
    leftovers = sorted(p.relative_to(dados).as_posix() for p in dados.rglob("*") if p.is_file())
    assert leftovers == ["commits/o__r.parquet", "releases/o__r.parquet"]

    # a retry (no hang) completes and replaces everything
    monkeypatch.delenv("GIT_PHASE_TEST_HANG")
    result = await run_git_phase_in_child(make_spec(git_dir, dados, releases))
    assert result["columns"]["tags_count_window"] == len(ALPHA)
    assert (dados / "releases_c2" / "o__r.parquet").is_file() and (dados / "tags" / "o__r.parquet").is_file()


async def test_child_timeout_kills_the_child(tmp_path, monkeypatch):
    original = asyncio.create_subprocess_exec
    started = []

    async def sleeping(*args, **kwargs):
        proc = await original(sys.executable, "-c", "import time; time.sleep(60)", **kwargs)
        started.append(proc)
        return proc

    monkeypatch.setattr(git_phase.asyncio, "create_subprocess_exec", sleeping)
    with pytest.raises(GitPhaseError, match="timed out after 1s"):
        await run_git_phase_in_child(make_spec(tmp_path / "x.git", tmp_path / "dados", []), timeout=1)
    assert started[0].returncode is not None  # killed and reaped


async def test_the_child_gets_no_token(alpha, tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_" + "t" * 36)
    monkeypatch.setenv("GITHUB_TOKENS", "ghp_" + "u" * 36)
    env = git_phase._child_env()
    assert not any(k in env for k in ("GITHUB_TOKEN", "GITHUB_TOKENS", "GH_TOKEN"))
    root = str(Path(git_phase.__file__).resolve().parent.parent)
    assert env["PYTHONPATH"].split(os.pathsep)[0] == root


def test_spec_round_trips_through_json_exactly(alpha, tmp_path):
    _, releases = alpha
    spec = make_spec("/x.git", tmp_path, releases)
    again = GitPhaseSpec.from_json(spec.to_json())
    assert again == spec and again.window_weeks == WINDOW_WEEKS  # exact float
    assert again.releases[5]["prerelease"] is True


def test_peak_rss_is_reported_in_mib():
    value = git_phase.peak_rss_mb()
    assert value is None or 10 < value < 100_000


async def test_phase_leaves_the_clone_alone(alpha, tmp_path):
    git_dir, releases = alpha
    before = sorted(p.name for p in git_dir.iterdir())
    await run_git_phase(make_spec(git_dir, tmp_path / "dados", releases))
    assert sorted(p.name for p in git_dir.iterdir()) == before
