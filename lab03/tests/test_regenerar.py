"""Tests for the final regeneration command (pipeline.regenerar, Issue #56).

Everything is offline: GitHub calls are replaced by synthetic releases and
workflow runs, and the commits come from real local bare clones built with git.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pyarrow.parquet as pq
import pytest
import yaml

from metricas.schemas import Release, WorkflowRun
from pipeline import regenerar
from pipeline.orchestrator import (
    SCHEMA_REPOSITORIOS,
    load_repositories_dataset,
    save_repositories_dataset,
)
from pipeline.regeneracao_relatorio import (
    METADATA_COLUMNS,
    SCHEMA_COLUMNS,
    check_invariants,
    check_written_files,
    compare_datasets,
    render_report,
)
from pipeline.regenerar import (
    RegenerationError,
    RegenSettings,
    load_checkpoint,
    redact,
    remove_orphan_runs,
    run_regeneration,
)
from pipeline.workflow_runs import WorkflowRunsCollectionResult

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}

# (tag, date, commit message, prerelease)
ALPHA = [
    ("v1.0.0", "2026-01-10T10:00:00+00:00", "feat: first", False),
    ("v1.0.1", "2026-01-12T10:00:00+00:00", "fix: crash on start", False),
    ("v1.1.0", "2026-03-01T10:00:00+00:00", "feat: more", False),
    ("v1.2.0", "2026-04-01T10:00:00+00:00", "feat: even more", False),
    ("v1.3.0", "2026-05-01T10:00:00+00:00", "feat: again", False),
    ("v2.0.0-rc.1", "2026-06-01T10:00:00+00:00", "feat: rc", True),
    # last day of the window, after 00:00Z: only inside with the end-of-day bound
    ("v1.4.0", "2026-09-30T20:00:00+00:00", "feat: last day", False),
]
BETA = [
    (f"v1.{i}.0", f"2026-0{i + 1}-15T12:00:00+00:00", f"feat: step {i}", False)
    for i in range(5)
]
REPOS = {"acme/alpha": ALPHA, "acme/beta": BETA}


def _git(cwd: Path, *args: str, date: str | None = None) -> None:
    env = dict(_GIT_ENV)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=env)


def _make_bare_clone(tmp_path: Path, git_cache: Path, full_name: str) -> None:
    """Bare clone in the cache location, so the pipeline reuses it without any network."""
    owner, repo = full_name.split("/")
    src = tmp_path / f"src-{owner}-{repo}"
    src.mkdir()
    _git(src, "init", "-q", "-b", "main")
    for i, (tag, date, message, _) in enumerate(REPOS[full_name]):
        (src / f"f{i}").write_text(tag)
        _git(src, "add", f"f{i}")
        _git(src, "commit", "-q", "-m", message, date=date)
        _git(src, "tag", tag)
    git_cache.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(src), str(git_cache / f"{owner}__{repo}.git")],
        check=True,
        capture_output=True,
        env=_GIT_ENV,
    )


def _old_record(full_name: str, stars: int) -> dict[str, Any]:
    owner, name = full_name.split("/")
    record: dict[str, Any] = dict.fromkeys(SCHEMA_COLUMNS)
    record.update(
        owner=owner,
        name=name,
        full_name=full_name,
        stars=stars,
        language="Python",
        default_branch="main",
        created_at="2020-01-01T00:00:00+00:00",
        contributors_count=42,
        releases_count_window=3,
        total_releases=3,
        workflow_runs_count_window=10,
        total_workflow_runs=10,
        deployment_frequency=0.05,
        deployment_tier="Low",
        cfr_a=0.5,
        cfr_tier="Low",
        recovery_tier="Low",
        overall_dora_score=0,
        overall_dora_tier="Low",
    )
    return record


def _runs() -> list[WorkflowRun]:
    def run(i: int, conclusion: str, started: str, updated: str) -> WorkflowRun:
        return WorkflowRun(
            workflow_id=1,
            conclusion=conclusion,
            run_started_at=started,
            updated_at=updated,
            id=i,
            name="ci",
            event="push",
            branch="main",
        )

    return [
        run(1, "success", "2026-02-01T10:00:00Z", "2026-02-01T10:05:00Z"),
        run(2, "failure", "2026-02-02T10:00:00Z", "2026-02-02T10:05:00Z"),
        run(3, "success", "2026-02-02T12:00:00Z", "2026-02-02T12:05:00Z"),
        run(4, "success", "2026-02-03T10:00:00Z", "2026-02-03T10:05:00Z"),
    ]


class Fakes:
    """Replacements for the GitHub calls, with call counters per repository."""

    def __init__(self) -> None:
        self.release_calls: dict[str, int] = {}
        self.run_calls: dict[str, int] = {}
        self.fail: set[str] = set()

    async def fetch_releases(self, client, owner, repo, window_start=None, use_graphql=False):
        name = f"{owner}/{repo}"
        self.release_calls[name] = self.release_calls.get(name, 0) + 1
        if name in self.fail:
            raise RuntimeError(f"boom for {name} with ghp_{'a' * 30}")
        return [
            Release(tag_name=tag, published_at=date, prerelease=pre)
            for tag, date, _, pre in REPOS[name]
        ]

    async def collect_workflow_runs(self, owner, repo, client=None, **kwargs):
        name = f"{owner}/{repo}"
        self.run_calls[name] = self.run_calls.get(name, 0) + 1
        assert kwargs["branch"] == "main"
        assert kwargs["save_to_parquet"] is False
        runs = _runs()
        return WorkflowRunsCollectionResult(
            owner=owner,
            repo=repo,
            branch="main",
            runs=runs,
            total_runs=len(runs),
            valid_runs_count=len(runs),
            passed_t4=False,
            api_requests=7,
            unsplittable_intervals=[{"start": "x"}] if name == "acme/beta" else [],
        )


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> Fakes:
    f = Fakes()
    monkeypatch.setattr(regenerar, "fetch_releases", f.fetch_releases)
    monkeypatch.setattr(regenerar, "collect_workflow_runs", f.collect_workflow_runs)
    return f


@pytest.fixture
def client() -> Any:
    return SimpleNamespace(token_pool=None)


@pytest.fixture
def env(tmp_path: Path) -> RegenSettings:
    """A `dados/` with the 'old' dataset of two repositories, clones and an orphan run."""
    dados = tmp_path / "dados"
    config = {
        "janela": {"inicio": "2025-10-01", "fim": "2026-09-30"},
        "amostra": {"tamanho_final": 2, "min_releases": 5, "min_workflow_runs": 50},
        "cfr_b": {"heuristica": "v1"},
        "diretorios": {
            "dados": str(dados),
            "cache": str(tmp_path / "cache"),
            "git_cache": str(tmp_path / "cache" / "git_repos"),
        },
    }
    settings = RegenSettings.from_config(config, report_path=tmp_path / "docs" / "relatorio.md")
    old = [_old_record("acme/alpha", 111), _old_record("acme/beta", 222)]
    save_repositories_dataset(old, settings.dataset_parquet, settings.dataset_csv)
    (dados / "funil.csv").write_text("etapa,quantidade\nx,1\n", encoding="utf-8")
    (dados / "runs").mkdir()
    for name in ("acme__alpha", "acme__beta", "elastic__elasticsearch"):
        (dados / "runs" / f"{name}.parquet").write_bytes(b"old " + name.encode())
    for name in REPOS:
        _make_bare_clone(tmp_path, settings.git_cache_dir, name)
    return settings


def _run(settings, client, **kwargs):
    import asyncio

    return asyncio.run(run_regeneration(settings, client=client, generated_on="2026-10-22", **kwargs))


# ------------------------------------------------------------- full run


def test_full_regeneration_publishes_everything(env, fakes, client):
    funil_before = (env.dados_dir / "funil.csv").read_bytes()
    summary = _run(env, client)

    assert summary.ok and summary.finalized
    assert len(summary.collected) == 2

    records = load_repositories_dataset(env.dataset_parquet)
    assert [r["full_name"] for r in records] == ["acme/alpha", "acme/beta"]
    alpha = records[0]

    # metadata untouched, metrics recomputed
    assert (alpha["stars"], alpha["language"], alpha["contributors_count"]) == (111, "Python", 42)
    assert alpha["created_at"] == "2020-01-01T00:00:00+00:00"
    # C1: 6 releases (the one on 2026-09-30T20:00Z is inside: end of day), no pre-release
    assert alpha["releases_count_window"] == 6
    assert alpha["total_releases"] == 7
    assert alpha["deployment_frequency"] == pytest.approx(6 / (365 / 7))
    assert alpha["workflow_runs_count_window"] == 4
    # CFR (b) C1: v1.0.0 failed (patch + fix), v1.4.0 censored -> 1 / 5
    assert alpha["cfr_b"] == pytest.approx(0.2)
    assert alpha["cfr_b_censored_releases"] == 1
    # CFR (b) C2 includes the pre-release: 1 / 6
    assert alpha["c2_cfr_b"] == pytest.approx(1 / 6)
    assert alpha["c2_cfr_b_evaluated_releases"] == 6
    assert alpha["c2_cfr_b_tier"] is not None
    assert alpha["prereleases_count_window"] == 1
    assert alpha["total_prereleases"] == 1
    assert alpha["c2_deployment_frequency"] == pytest.approx(7 / (365 / 7))
    assert alpha["tags_count_window"] == 7 and alpha["total_tags"] == 7
    # one failure episode (02-02 10:00) recovered by the success finished at 12:05
    assert alpha["recovery_hours"] == pytest.approx(125 / 60)

    # CSV and Parquet carry the identical, complete schema
    with open(env.dataset_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == list(SCHEMA_COLUMNS)
    assert pq.read_schema(env.dataset_parquet).names == list(SCHEMA_COLUMNS)
    assert [r["full_name"] for r in rows] == ["acme/alpha", "acme/beta"]

    # runs: regenerated for the 2 repos, the orphan is gone
    assert sorted(p.name for p in env.runs_dir.glob("*.parquet")) == [
        "acme__alpha.parquet",
        "acme__beta.parquet",
    ]
    assert pq.read_table(env.runs_dir / "acme__alpha.parquet").num_rows == 4
    assert summary.removed_orphans == ["elastic__elasticsearch.parquet"]

    # untouched artifacts
    assert (env.dados_dir / "funil.csv").read_bytes() == funil_before
    # report written
    report = env.report_path.read_text(encoding="utf-8")
    assert "# Regeneração final do dataset (Issue #56)" in report
    assert "`c2_cfr_b`" in report and "Intervalos não divisíveis" in report
    assert "acme/beta | 1 |" in report


def test_regeneration_is_idempotent(env, fakes, client):
    _run(env, client)
    first = (env.dataset_csv.read_bytes(), env.dataset_parquet.read_bytes()[:0])
    _run(env, client, resume=True)
    assert env.dataset_csv.read_bytes() == first[0]
    _run(env, client, fresh=True)
    assert env.dataset_csv.read_bytes() == first[0]


def test_limit_collects_but_does_not_publish(env, fakes, client):
    csv_before = env.dataset_csv.read_bytes()
    summary = _run(env, client, limit=1)

    assert summary.collected == ["acme/alpha"]
    assert not summary.finalized and summary.ok
    assert env.dataset_csv.read_bytes() == csv_before
    assert (env.runs_dir / "elastic__elasticsearch.parquet").exists()
    assert fakes.release_calls == {"acme/alpha": 1}


# ---------------------------------------------------------------- resume


def test_resume_skips_finished_repositories(env, fakes, client):
    fakes.fail.add("acme/beta")
    csv_before = env.dataset_csv.read_bytes()
    summary = _run(env, client)

    assert list(summary.failed) == ["acme/beta"]
    assert "ghp_" not in summary.failed["acme/beta"]  # token-like text is redacted
    assert not summary.finalized
    assert env.dataset_csv.read_bytes() == csv_before  # nothing published on failure
    done = load_checkpoint(env.checkpoint_path, env.fingerprint())
    assert list(done) == ["acme/alpha"]

    fakes.fail.clear()
    summary = _run(env, client, resume=True)
    assert summary.finalized and summary.ok
    assert summary.reused == 1 and summary.collected == ["acme/beta"]
    assert fakes.release_calls == {"acme/alpha": 1, "acme/beta": 2}  # alpha not collected again
    assert len(load_repositories_dataset(env.dataset_parquet)) == 2


def test_existing_checkpoint_requires_resume_or_fresh(env, fakes, client):
    _run(env, client, limit=1)
    with pytest.raises(RegenerationError, match="--resume"):
        _run(env, client)
    summary = _run(env, client, fresh=True)
    assert summary.finalized and summary.reused == 0
    assert fakes.release_calls["acme/alpha"] == 2


def test_checkpoint_ignores_stale_and_truncated_lines(env, fakes, client):
    _run(env, client, limit=1)
    # another window/heuristic: ignored
    lines = env.checkpoint_path.read_text(encoding="utf-8").splitlines()
    stale = json.loads(lines[0])
    stale["fingerprint"] = "other"
    stale["record"]["full_name"] = "acme/beta"
    with open(env.checkpoint_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(stale) + "\n")
        f.write('{"fingerprint": "' + env.fingerprint() + '", "record": {"full_na')  # cut write
    done = load_checkpoint(env.checkpoint_path, env.fingerprint())
    assert list(done) == ["acme/alpha"]

    summary = _run(env, client, resume=True)
    assert summary.finalized
    assert fakes.release_calls["acme/beta"] == 1


def test_checkpoint_of_a_different_window_is_not_reused(env, fakes, client):
    _run(env, client, limit=2)
    other = RegenSettings.from_config(
        {
            "janela": {"inicio": "2025-10-01", "fim": "2026-09-29"},
            "amostra": {"tamanho_final": 2},
            "diretorios": {"dados": str(env.dados_dir), "cache": str(env.cache_dir),
                           "git_cache": str(env.git_cache_dir)},
        },
        report_path=env.report_path,
    )
    assert other.fingerprint() != env.fingerprint()
    assert load_checkpoint(env.checkpoint_path, other.fingerprint()) == {}


def test_tampered_checkpoint_metadata_blocks_publication(env, fakes, client):
    _run(env, client, limit=2)
    lines = [json.loads(line) for line in env.checkpoint_path.read_text().splitlines()]
    lines[0]["record"]["stars"] = 999_999
    env.checkpoint_path.write_text("".join(json.dumps(e) + "\n" for e in lines), encoding="utf-8")
    csv_before = env.dataset_csv.read_bytes()

    summary = _run(env, client, resume=True)

    assert not summary.finalized and not summary.ok
    assert any("stars" in p for p in summary.problems)
    assert env.dataset_csv.read_bytes() == csv_before
    assert (env.runs_dir / "elastic__elasticsearch.parquet").exists()


def test_baseline_is_kept_across_runs(env, fakes, client):
    old_csv = env.dataset_csv.read_bytes()
    _run(env, client)
    assert env.baseline_csv.read_bytes() == old_csv
    _run(env, client, fresh=True)  # a second run still compares against the original
    assert env.baseline_csv.read_bytes() == old_csv


# --------------------------------------------------------------- orphans


def test_remove_orphan_runs_uses_git_rm_for_tracked_files(tmp_path):
    repo = tmp_path / "repo"
    runs = repo / "dados" / "runs"
    runs.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    for name in ("a__a", "orphan__x"):
        (runs / f"{name}.parquet").write_bytes(b"x")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "runs")
    (runs / "untracked__y.parquet").write_bytes(b"y")

    removed = remove_orphan_runs(runs, {"a__a.parquet"})

    assert removed == ["orphan__x.parquet", "untracked__y.parquet"]
    assert [p.name for p in runs.glob("*.parquet")] == ["a__a.parquet"]
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout
    assert "D  dados/runs/orphan__x.parquet" in status  # staged removal


def test_remove_orphan_runs_missing_dir(tmp_path):
    assert remove_orphan_runs(tmp_path / "nope", set()) == []


# ------------------------------------------------------------ invariants


def _ok_records():
    base = {
        c: 1 for c in SCHEMA_COLUMNS
    }
    base.update({"deployment_tier": "Low", "cfr_tier": "Low", "recovery_tier": "Low",
                 "overall_dora_tier": "Low"})
    a = {**base, "full_name": "a/a", "owner": "a", "name": "a"}
    b = {**base, "full_name": "b/b", "owner": "b", "name": "b"}
    return [a, b]


def test_check_invariants_accepts_a_faithful_regeneration():
    old = _ok_records()
    new = [dict(r) for r in old]
    new[0]["deployment_frequency"] = 9.9  # metrics may change
    assert check_invariants(old, new, expected_rows=2) == []


def test_check_invariants_detects_violations():
    old = _ok_records()

    assert any("esperado 3" in p for p in check_invariants(old, [dict(r) for r in old], 3))
    assert any("ordem" in p for p in check_invariants(old, [dict(r) for r in reversed(old)]))
    assert any("conjunto de repositórios" in p for p in check_invariants(old, [old[0]]))
    renamed = [dict(old[0]), {**old[1], "full_name": "c/c"}]
    assert any("conjunto de repositórios mudou" in p for p in check_invariants(old, renamed))
    dup = [dict(old[0]), dict(old[0])]
    assert any("duplicados" in p for p in check_invariants(old, dup))

    meta = [dict(r) for r in old]
    meta[1]["language"] = "Go"
    assert any("language" in p for p in check_invariants(old, meta))

    missing = [dict(r) for r in old]
    del missing[0]["c2_cfr_b"]
    assert any("esquema incompleto" in p for p in check_invariants(old, missing))

    nulls = [dict(r) for r in old]
    nulls[0]["overall_dora_tier"] = None
    assert any("overall_dora_tier nulo" in p for p in check_invariants(old, nulls))


def test_check_written_files_detects_metadata_text_drift(tmp_path):
    old = [_old_record("a/a", 5)]
    new = [{**_old_record("a/a", 5), "deployment_frequency": 1.5}]
    base_pq, base_csv = tmp_path / "b.parquet", tmp_path / "b.csv"
    out_pq, out_csv = tmp_path / "o.parquet", tmp_path / "o.csv"
    save_repositories_dataset(old, base_pq, base_csv)
    save_repositories_dataset(new, out_pq, out_csv)
    assert check_written_files(base_csv, out_csv, out_pq) == []

    drifted = [{**new[0], "stars": 6}]
    save_repositories_dataset(drifted, out_pq, out_csv)
    assert any("stars" in p for p in check_written_files(base_csv, out_csv, out_pq))


def test_committed_dataset_round_trips_with_identical_metadata(tmp_path):
    """Rewriting the committed dataset through the real writer keeps the metadata text."""
    dados = Path(__file__).resolve().parents[1] / "dados"
    if not (dados / "repositorios.parquet").is_file():
        pytest.skip("dataset not available")
    records = load_repositories_dataset(dados / "repositorios.parquet")
    out_pq, out_csv = tmp_path / "o.parquet", tmp_path / "o.csv"
    save_repositories_dataset(records, out_pq, out_csv)
    assert check_written_files(dados / "repositorios.csv", out_csv, out_pq) == []
    assert len(records) == 330


# ---------------------------------------------------------------- report


def test_compare_datasets_counts_changes_and_transitions():
    old = _ok_records()
    old[0].update(deployment_tier="Low", overall_dora_tier="Low", overall_dora_score=1,
                  recovery_hours=None, cfr_b=None)
    old[1].update(overall_dora_tier="High", overall_dora_score=3, recovery_hours=2.0)
    new = [dict(r) for r in old]
    new[0].update(deployment_tier="High", overall_dora_tier="Medium", overall_dora_score=2,
                  recovery_hours=3.0, cfr_b=0.5,
                  releases_count_window=6, workflow_runs_count_window=60)
    new[1].update(recovery_hours=None, releases_count_window=3, workflow_runs_count_window=10)

    cmp = compare_datasets(
        old, new, baseline_columns=[c for c in SCHEMA_COLUMNS if not c.startswith("c2_cfr_b")],
        unsplittable={"b/b": 2},
    )
    cols = {c.column: c for c in cmp.columns}

    assert cols["deployment_tier"].changed_rows == 1
    assert cmp.tier_transitions["deployment_tier"][("Low", "High")] == 1
    assert cols["recovery_hours"].changed_rows == 2
    assert (cols["recovery_hours"].nulls_before, cols["recovery_hours"].nulls_after) == (1, 1)
    assert (cols["recovery_hours"].became_null, cols["recovery_hours"].became_filled) == (1, 1)
    assert cols["cfr_b"].became_filled == 1
    assert cols["stars"].changed_rows == 0
    assert cmp.overall_changes == [("a/a", "Low", "Medium", 1, 2)]
    assert cmp.new_columns == [c for c in SCHEMA_COLUMNS if c.startswith("c2_cfr_b")]
    assert cols["c2_cfr_b"].is_new
    assert [n for n, *_ in cmp.below_selection_criteria] == ["b/b"]
    assert cmp.unsplittable == {"b/b": 2}


def test_render_report_is_pt_br_and_lists_violations():
    old = _ok_records()
    new = [dict(r) for r in old]
    new[0]["overall_dora_tier"] = "Elite"
    cmp = compare_datasets(old, new)

    text = render_report(
        cmp, [], generated_on="2026-10-22", window=("2025-10-01", "2026-09-30"), heuristic="v1",
        expected_rows=2,
    )
    for section in (
        "## Resumo", "## Invariantes", "## Colunas: antes × depois", "## Transições de faixa",
        "## Repositórios com a faixa geral alterada", "## Repositórios fora dos critérios",
    ):
        assert section in text
    assert "| a/a | Low | Elite |" in text
    assert "2 linhas, mesmos repositórios na mesma ordem: OK" in text

    bad = render_report(
        cmp, ["a/a: language mudou"], generated_on="x", window=("a", "b"), heuristic="v1"
    )
    assert "**Violadas:**" in bad and "a/a: language mudou" in bad


# ------------------------------------------------------------------- CLI


def test_redact_removes_tokens():
    text = f"401 for ghp_{'x' * 36} and github_pat_{'y' * 40} and Bearer {'z' * 30} done"
    out = redact(text)
    assert "ghp_" not in out and "github_pat_" not in out and "z" * 30 not in out
    assert out.count("***") == 3


def test_cli_refuses_leftover_checkpoint_and_builds_report(env, fakes, client, tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "janela": {"inicio": "2025-10-01", "fim": "2026-09-30"},
                "amostra": {"tamanho_final": 2},
                "diretorios": {
                    "dados": str(env.dados_dir),
                    "cache": str(env.cache_dir),
                    "git_cache": str(env.git_cache_dir),
                },
            }
        ),
        encoding="utf-8",
    )
    _run(env, client)  # complete run: baseline + new dataset exist

    report = tmp_path / "out" / "r.md"
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_" + "s" * 36)
    code = regenerar.main(
        ["--config", str(config_path), "--somente-relatorio", "--relatorio", str(report)]
    )
    assert code == 0
    assert report.is_file() and "Resumo" in report.read_text(encoding="utf-8")

    code = regenerar.main(["--config", str(config_path), "--relatorio", str(report)])
    assert code == 2  # checkpoint left by the run above, no --resume
    captured = capsys.readouterr()
    assert "--resume" in captured.err
    assert "ghp_" not in captured.out + captured.err  # the token is never printed
    assert "Tokens configurados: 1" in captured.out


def test_settings_validate_the_heuristic():
    with pytest.raises(ValueError, match="Unknown CFR"):
        RegenSettings.from_config({"cfr_b": {"heuristica": "nope"}})


def test_schema_has_cfr_b_columns_for_c2():
    names = [f.name for f in SCHEMA_REPOSITORIOS]
    for suffix in ("", "_tier", "_failed_releases", "_evaluated_releases",
                   "_censored_releases", "_skipped_releases"):
        assert f"c2_cfr_b{suffix}" in names
    assert set(METADATA_COLUMNS) <= set(names)


# ------------------------------------------------- unavailable repositories


def test_unavailable_repository_keeps_previous_values(env, fakes, client):
    import dataclasses

    fakes.fail.add("acme/beta")
    old_beta = [r for r in load_repositories_dataset(env.dataset_parquet) if r["name"] == "beta"][0]
    old_run = (env.runs_dir / "acme__beta.parquet").read_bytes()
    settings = dataclasses.replace(env, keep_previous=frozenset({"acme/beta"}))

    summary = _run(settings, client)

    assert summary.ok and summary.finalized
    assert list(summary.kept) == ["acme/beta"] and "RuntimeError" in summary.kept["acme/beta"]
    assert "ghp_" not in summary.kept["acme/beta"]
    records = {r["name"]: r for r in load_repositories_dataset(env.dataset_parquet)}
    # previous values untouched (including nulls the new schema cannot fill), the other one regenerated
    assert records["beta"] == old_beta
    assert records["alpha"]["c2_cfr_b_evaluated_releases"] == 6
    assert (env.runs_dir / "acme__beta.parquet").read_bytes() == old_run
    report = env.report_path.read_text(encoding="utf-8")
    assert "## Repositórios mantidos com os valores anteriores" in report
    assert "| acme/beta | RuntimeError" in report


def test_unavailable_repository_outside_the_keep_list_still_fails(env, fakes, client):
    fakes.fail.add("acme/beta")
    summary = _run(env, client)
    assert list(summary.failed) == ["acme/beta"] and not summary.kept


def test_keep_list_comes_from_config_and_cli_flag():
    settings = RegenSettings.from_config(
        {"regeneracao": {"manter_valores_anteriores": ["a/a"]}}, keep_previous=["b/b"]
    )
    assert settings.keep_previous == frozenset({"a/a", "b/b"})


def test_check_invariants_exempts_kept_repositories_from_the_null_check():
    old = _ok_records()
    new = [dict(r) for r in old]
    new[1]["c2_cfr_b_evaluated_releases"] = None
    assert check_invariants(old, new)
    assert check_invariants(old, new, kept={"b/b"}) == []


# ------------------------------------------- reconcile mode, status, bundle


def _reconcile_settings(env, tmp_path, **extra):
    import dataclasses

    from pipeline.workflow_runs import save_runs_to_parquet

    # real "previous" runs for the reconciliation (the fixture's files are placeholders)
    for name in ("alpha", "beta"):
        save_runs_to_parquet(_runs()[:3], "acme", name, env.runs_dir / f"acme__{name}.parquet")
    from datetime import datetime, timezone

    return dataclasses.replace(
        env,
        runs_mode="reconciliar",
        previous_window_start=datetime(2025, 10, 1, tzinfo=timezone.utc),
        previous_window_end=datetime(2026, 9, 30, tzinfo=timezone.utc),
        status_path=tmp_path / "status.json",
        bundle_dir=tmp_path / "bundle",
        **extra,
    )


@pytest.fixture
def reconciling(monkeypatch: pytest.MonkeyPatch, fakes: Fakes):
    seen: dict[str, Any] = {}

    async def fake_reconcile(owner, repo, previous_runs, client, start_date, previous_end_date,
                             end_date, branch, **kw):
        name = f"{owner}/{repo}"
        seen[name] = {"previous": len(previous_runs), "previous_end": previous_end_date, "branch": branch}
        runs = _runs()
        beta = name == "acme/beta"
        entries = [
            {"start": "2025-10-01T00:00:00Z", "end": "2025-10-31T23:59:59Z", "action": "kept",
             "previous_count": 2, "api_count": 2},
            {"start": "2025-11-01T00:00:00Z", "end": "2025-11-30T23:59:59Z",
             "action": "refetched" if beta else "kept", "previous_count": 1000, "api_count": 1300,
             "fetched_count": 1300},
            {"start": "2026-09-30T00:00:01Z", "end": "2026-09-30T23:59:59Z", "action": "tail",
             "fetched_count": 0},
        ]
        return WorkflowRunsCollectionResult(
            owner=owner, repo=repo, branch=branch, runs=runs, total_runs=len(runs),
            valid_runs_count=len(runs), passed_t4=False, api_requests=3 + (5 if beta else 0),
            reconciliation=entries,
        )

    monkeypatch.setattr(regenerar, "reconcile_workflow_runs", fake_reconcile)
    return seen


def test_reconcile_mode_uses_the_baseline_runs_and_reports_refetched_intervals(env, fakes, client, tmp_path, reconciling):
    settings = _reconcile_settings(env, tmp_path)
    summary = _run(settings, client)

    assert summary.ok and summary.finalized
    # the previous runs come from the snapshot taken before anything was published
    assert reconciling["acme/alpha"]["previous"] == 3 and reconciling["acme/beta"]["previous"] == 3
    assert reconciling["acme/alpha"]["previous_end"].isoformat() == "2026-09-30T00:00:00+00:00"
    assert fakes.run_calls == {}  # the full collector was never used
    assert (env.state_dir / "baseline_runs" / "acme__alpha.parquet").is_file()

    done = load_checkpoint(env.checkpoint_path, env.fingerprint())
    diag = done["acme/beta"]["diagnostics"]
    assert diag["runs_mode"] == "reconciliar"
    assert diag["reconciled"] == {"kept": 1, "refetched": 1, "tail": 1}
    assert diag["refetched_intervals"][0]["api_count"] == 1300

    report = settings.report_path.read_text(encoding="utf-8")
    assert "## Coleta dos runs: reconciliação com a API" in report
    assert "| acme/beta | 2025-11-01T00:00:00Z .. 2025-11-30T23:59:59Z | 1000 | 1300 | intervalo truncado" in report
    assert "reconciliar: 2" in report
    assert "## Execução desacoplada" in report and "status.json" in report


def test_reconcile_mode_requires_the_previous_window_and_files(env, fakes, client, tmp_path, reconciling):
    import dataclasses

    settings = dataclasses.replace(_reconcile_settings(env, tmp_path), previous_window_end=None)
    summary = _run(settings, client)
    assert set(summary.failed) == {"acme/alpha", "acme/beta"}
    assert all("janela_anterior" in v for v in summary.failed.values())


def test_a_checkpoint_from_the_full_mode_is_reused_in_reconcile_mode(env, fakes, client, tmp_path, reconciling):
    settings = _reconcile_settings(env, tmp_path)  # also writes the previous runs
    _run(env, client, limit=1)  # alpha collected in full mode
    summary = _run(settings, client, resume=True)

    assert summary.reused == 1 and summary.collected == ["acme/beta"]
    assert list(reconciling) == ["acme/beta"]
    assert summary.finalized


def test_status_json_is_written_and_has_no_secrets(env, fakes, client, tmp_path, reconciling):
    settings = _reconcile_settings(env, tmp_path)
    client.token_pool = SimpleNamespace(
        tokens=[SimpleNamespace(token="ghp_" + "s" * 36, remaining=4200, reset_ts=1_800_000_000.0,
                                cooldown_until=0.0),
                SimpleNamespace(token="ghp_" + "t" * 36, remaining=None, reset_ts=None,
                                cooldown_until=float("inf"))]
    )
    _run(settings, client)

    text = settings.status_path.read_text(encoding="utf-8")
    status = json.loads(text)
    assert "ghp_" not in text
    assert status["state"] == "finished"
    assert (status["done"], status["total"], status["runs_mode"]) == (2, 2, "reconciliar")
    assert status["requests_this_run"] == 3 + 8
    assert status["quota"][0]["remaining"] == 4200 and status["quota"][0]["reset_at"]
    assert status["quota"][1]["disabled"] is True
    assert (status["tokens_total"], status["tokens_usable"]) == (2, 1)
    assert status["current"] == [] and status["last_error"] is None and status["pid"] > 0


def test_status_json_records_failures_and_partial_state(env, fakes, client, tmp_path):
    import dataclasses

    fakes.fail.add("acme/beta")
    settings = dataclasses.replace(env, status_path=tmp_path / "status.json")
    _run(settings, client)

    status = json.loads(settings.status_path.read_text(encoding="utf-8"))
    assert status["state"] == "failed" and status["failed_this_run"] == 1
    assert status["done"] == 1 and "acme/beta" in status["last_error"]
    assert "ghp_" not in status["last_error"]


def test_bundle_has_everything_and_verifiable_checksums(env, fakes, client, tmp_path):
    import dataclasses
    import hashlib
    import tarfile

    settings = dataclasses.replace(env, bundle_dir=tmp_path / "bundle")
    summary = _run(settings, client)

    archive = summary.bundle
    assert archive is not None and archive.name.startswith("outputs-") and archive.name.endswith(".tar.gz")
    digest = (archive.parent / f"{archive.name}.sha256").read_text().split()[0]
    assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()

    with tarfile.open(archive) as tar:
        names = tar.getnames()
        for expected in (
            "outputs/dados/repositorios.csv",
            "outputs/dados/repositorios.parquet",
            "outputs/dados/runs/acme__alpha.parquet",
            "outputs/dados/runs/acme__beta.parquet",
            "outputs/docs/regeneracao_final.md",
            "outputs/INVARIANTES.txt",
            "outputs/DIFF_STAT.txt",
            "outputs/SHA256SUMS",
        ):
            assert expected in names
        assert not any("elastic" in n for n in names)  # the orphan is not part of the result
        assert not any(".env" in n for n in names)  # secrets never go into the bundle
        assert tar.extractfile("outputs/INVARIANTES.txt").read().decode().startswith("OK")
        sums = tar.extractfile("outputs/SHA256SUMS").read().decode().splitlines()
        for line in sums:
            sha, member = line.split("  ", 1)
            assert hashlib.sha256(tar.extractfile(f"outputs/{member}").read()).hexdigest() == sha
    assert "Pacote de saídas" in regenerar.format_summary(summary)


def test_settings_reject_unknown_runs_mode_and_parse_previous_window():
    with pytest.raises(ValueError, match="runs_mode"):
        RegenSettings.from_config({}, runs_mode="nope")
    settings = RegenSettings.from_config(
        {"regeneracao": {"janela_anterior": {"inicio": "2025-10-01", "fim": "2026-09-30"}}},
        runs_mode="reconciliar",
    )
    assert settings.previous_window_end.isoformat() == "2026-09-30T00:00:00+00:00"  # literal, not end of day
    assert settings.previous_window_start.isoformat() == "2025-10-01T00:00:00+00:00"


def test_validate_reconciliation_compares_ids_and_derived_metrics(env, fakes, client, tmp_path, monkeypatch):
    import dataclasses

    from pipeline.regenerar import format_validation, validate_reconciliation

    settings = _reconcile_settings(env, tmp_path)
    _run(dataclasses.replace(env, runs_mode="completo"), client, limit=1)  # alpha: full result staged
    from pipeline.regenerar import prepare_baseline

    prepare_baseline(settings)

    async def fake_reconcile(owner, repo, previous_runs, client, start_date, previous_end_date,
                             end_date, branch, **kw):
        runs = _runs() if repo == "alpha" else _runs()[:3]  # beta: the reconciliation lost a run
        return WorkflowRunsCollectionResult(
            owner=owner, repo=repo, branch=branch, runs=runs, total_runs=len(runs),
            valid_runs_count=len(runs), passed_t4=False, api_requests=2,
            reconciliation=[{"start": "a", "end": "b", "action": "kept"}],
        )

    monkeypatch.setattr(regenerar, "reconcile_workflow_runs", fake_reconcile)
    import asyncio

    results = asyncio.run(validate_reconciliation(settings, client, ["acme/alpha", "acme/beta"]))

    alpha, beta = results
    assert alpha["full_source"] == "checkpoint" and alpha["same_ids"] and alpha["same_metrics"]
    assert beta["full_source"] == "coleta completa" and not beta["same_ids"]
    assert beta["only_in_full"] == 1
    assert alpha["requests_full"] == 7 and alpha["requests_reconciled"] == 2
    assert (settings.state_dir / "validacao_reconciliacao.json").is_file()
    assert "acme/beta" in format_validation(results)


# ------------------------------------------------------- memory budget


def test_wait_for_memory_pauses_until_enough_ram_is_available():
    import asyncio

    readings = iter([1000, 1500, 4000])
    calls = []

    def reader():
        value = next(readings)
        calls.append(value)
        return {"rss": 1, "peak_rss": 1, "available": value}

    waited = asyncio.run(regenerar.wait_for_memory(3072, poll_seconds=0.01, reader=reader))
    assert calls == [1000, 1500, 4000] and waited == pytest.approx(0.02)
    # unknown memory (not Linux) never blocks
    assert asyncio.run(
        regenerar.wait_for_memory(3072, 0.01, reader=lambda: {"available": None})
    ) == 0.0


def test_read_memory_has_the_expected_keys():
    mem = regenerar.read_memory()
    assert set(mem) == {"rss", "peak_rss", "available"}
    if Path("/proc/self/status").exists():
        assert mem["rss"] > 0 and mem["peak_rss"] >= mem["rss"] and mem["available"] > 0


def test_is_heavy_by_runs_releases_or_tags():
    assert regenerar.is_heavy({"total_workflow_runs": 50_000})
    # tag-heavy repositories (CI tags) are heavy too, even with few runs and releases
    assert regenerar.is_heavy({"total_workflow_runs": 93, "releases_count_window": 70, "tags_count_window": 1000})
    assert regenerar.is_heavy({"tags_count_window": 9_458})
    assert not regenerar.is_heavy({"tags_count_window": 999})
    assert not regenerar.is_heavy({"tags_count_window": None})
    assert regenerar.is_heavy({"total_workflow_runs": 10, "releases_count_window": 2576})
    assert not regenerar.is_heavy({"total_workflow_runs": 4_000, "releases_count_window": 28})
    assert not regenerar.is_heavy({})


def test_only_one_heavy_repository_at_a_time(env, fakes, client, monkeypatch):
    import asyncio

    # both repositories are heavy; four workers must still serialise them
    old = load_repositories_dataset(env.dataset_parquet)
    for r in old:
        r["total_workflow_runs"] = 99_999
    save_repositories_dataset(old, env.dataset_parquet, env.dataset_csv)
    env.baseline_parquet.unlink(missing_ok=True)
    env.baseline_csv.unlink(missing_ok=True)

    active = {"now": 0, "max": 0}
    original = fakes.fetch_releases

    async def tracking(*a, **kw):
        active["now"] += 1
        active["max"] = max(active["max"], active["now"])
        await asyncio.sleep(0.05)
        try:
            return await original(*a, **kw)
        finally:
            active["now"] -= 1

    monkeypatch.setattr(regenerar, "fetch_releases", tracking)
    summary = _run(env, client, num_workers=4)
    assert summary.ok and summary.finalized
    assert active["max"] == 1


def test_light_repositories_run_in_parallel(env, fakes, client, monkeypatch):
    import asyncio

    active = {"now": 0, "max": 0}
    original = fakes.fetch_releases

    async def tracking(*a, **kw):
        active["now"] += 1
        active["max"] = max(active["max"], active["now"])
        await asyncio.sleep(0.05)
        try:
            return await original(*a, **kw)
        finally:
            active["now"] -= 1

    monkeypatch.setattr(regenerar, "fetch_releases", tracking)
    assert _run(env, client, num_workers=2).ok
    assert active["max"] == 2


def test_status_reports_memory_and_the_peak_per_repository(env, fakes, client, tmp_path):
    import dataclasses

    settings = dataclasses.replace(env, status_path=tmp_path / "status.json")
    _run(settings, client)
    status = json.loads(settings.status_path.read_text(encoding="utf-8"))
    assert set(status["memory_mb"]) == {"rss", "peak_rss", "available"}
    done = load_checkpoint(env.checkpoint_path, env.fingerprint())
    assert all("peak_rss_mb" in e["diagnostics"] for e in done.values())
    if Path("/proc/self/status").exists():
        assert status["memory_mb"]["rss"] > 0 and status["peak_rss_mb_per_repo"]


def test_only_restricts_the_scope_and_publishes_nothing(env, fakes, client):
    csv_before = env.dataset_csv.read_bytes()
    summary = _run(env, client, only=["acme/beta"])
    assert summary.collected == ["acme/beta"] and not summary.finalized
    assert env.dataset_csv.read_bytes() == csv_before
    with pytest.raises(RegenerationError, match="fora do dataset"):
        _run(env, client, only=["nope/nope"], resume=True)


# ------------------------------------------------- git phase in a child process


def _records_by_name(settings):
    return {r["full_name"]: r for r in load_repositories_dataset(settings.dataset_parquet)}


def test_child_process_record_equals_the_in_process_record(env, fakes, client, tmp_path):
    import dataclasses
    import shutil

    in_process = _run(env, client)
    assert in_process.ok and in_process.finalized
    expected = _records_by_name(env)
    expected_csv = env.dataset_csv.read_bytes()
    expected_files = {
        p.relative_to(env.dados_dir).as_posix(): p.read_bytes()
        for folder in ("commits", "releases", "releases_c2", "tags")
        for p in (env.dados_dir / folder).glob("*.parquet")
    }
    assert set(expected_files) == {
        f"{folder}/acme__{repo}.parquet"
        for folder in ("commits", "releases", "releases_c2", "tags")
        for repo in ("alpha", "beta")
    }

    # again from scratch, now with the git phase in a child per repository
    shutil.rmtree(env.state_dir)
    for folder in ("commits", "releases", "releases_c2", "tags"):
        shutil.rmtree(env.dados_dir / folder)
    old = [r for r in load_repositories_dataset(env.dataset_parquet)]
    # start again from the dataset that existed before the first run
    baseline = [_old_record("acme/alpha", 111), _old_record("acme/beta", 222)]
    save_repositories_dataset(baseline, env.dataset_parquet, env.dataset_csv)
    child_settings = dataclasses.replace(env, git_subprocess=True)
    summary = _run(child_settings, client)

    assert summary.ok and summary.finalized and old
    assert _records_by_name(env) == expected  # same columns, same floats
    assert env.dataset_csv.read_bytes() == expected_csv  # byte for byte
    for name, content in expected_files.items():
        assert (env.dados_dir / name).read_bytes() == content, name
    done = load_checkpoint(env.checkpoint_path, env.fingerprint())
    peaks = [e["diagnostics"]["peak_rss_mb"] for e in done.values()]
    assert all(isinstance(p, int) and p > 0 for p in peaks)  # the child's own peak


def test_child_peak_goes_to_status_json(env, fakes, client, tmp_path):
    import dataclasses

    settings = dataclasses.replace(env, git_subprocess=True, status_path=tmp_path / "status.json")
    _run(settings, client)
    status = json.loads(settings.status_path.read_text(encoding="utf-8"))
    done = load_checkpoint(env.checkpoint_path, env.fingerprint())
    assert status["peak_rss_mb_per_repo"] == {
        name: e["diagnostics"]["peak_rss_mb"] for name, e in done.items()
    }


def test_a_failing_child_is_a_repository_failure_and_is_retried_on_resume(
    env, fakes, client, monkeypatch
):
    import dataclasses

    child_settings = dataclasses.replace(env, git_subprocess=True)
    real = regenerar.run_git_phase_in_child
    attempts = []

    async def flaky(spec, timeout):
        attempts.append(spec.repo)
        if spec.repo == "beta" and attempts.count("beta") == 1:  # only its first attempt fails
            raise regenerar.GitPhaseError(
                f"git phase of acme/beta failed (exit -9): killed ghp_{'z' * 30}"
            )
        return await real(spec, timeout=timeout)

    monkeypatch.setattr(regenerar, "run_git_phase_in_child", flaky)
    csv_before = env.dataset_csv.read_bytes()
    summary = _run(child_settings, client)

    assert list(summary.failed) == ["acme/beta"]
    assert "exit -9" in summary.failed["acme/beta"] and "ghp_" not in summary.failed["acme/beta"]
    assert not summary.finalized and env.dataset_csv.read_bytes() == csv_before
    done = load_checkpoint(env.checkpoint_path, env.fingerprint())
    assert list(done) == ["acme/alpha"]

    summary = _run(child_settings, client, resume=True)  # beta is retried; alpha is not
    assert summary.ok and summary.finalized and summary.collected == ["acme/beta"]
    assert attempts.count("alpha") == 1 and attempts.count("beta") == 2
    assert not list(env.dados_dir.rglob("*.tmp"))


def test_a_timing_out_child_keeps_previous_values_when_listed(env, fakes, client, monkeypatch):
    import dataclasses

    (env.dados_dir / "runs").joinpath("acme__beta.parquet").write_bytes(b"old beta")
    child_settings = dataclasses.replace(
        env, git_subprocess=True, keep_previous=frozenset({"acme/beta"})
    )

    real = regenerar.run_git_phase_in_child

    async def dispatch(spec, timeout):
        if spec.repo == "beta":
            raise regenerar.GitPhaseError("git phase of acme/beta timed out after 3600s")
        return await real(spec, timeout=timeout)

    monkeypatch.setattr(regenerar, "run_git_phase_in_child", dispatch)
    summary = _run(child_settings, client)

    assert summary.ok and summary.finalized
    assert "timed out" in summary.kept["acme/beta"]


def test_child_timeout_comes_from_the_settings(env, fakes, client, monkeypatch):
    import dataclasses

    seen = []

    async def spy(spec, timeout):
        seen.append(timeout)
        raise regenerar.GitPhaseError("stop")

    monkeypatch.setattr(regenerar, "run_git_phase_in_child", spy)
    _run(dataclasses.replace(env, git_subprocess=True, child_timeout=123.0), client, limit=1)
    assert seen == [123.0]


def test_cli_runs_the_git_phase_in_a_child_unless_told_otherwise(env, fakes, tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "janela": {"inicio": "2025-10-01", "fim": "2026-09-30"},
                "amostra": {"tamanho_final": 2},
                "diretorios": {
                    "dados": str(env.dados_dir),
                    "cache": str(env.cache_dir),
                    "git_cache": str(env.git_cache_dir),
                },
            }
        ),
        encoding="utf-8",
    )
    captured = []

    async def fake_run(settings, **kwargs):
        captured.append(settings.git_subprocess)
        return regenerar.RegenSummary()

    monkeypatch.setattr(regenerar, "run_regeneration", fake_run)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_" + "s" * 36)
    base = ["--config", str(config_path), "--relatorio", str(tmp_path / "r.md")]
    regenerar.main(base)
    regenerar.main([*base, "--sem-subprocesso"])
    assert captured == [True, False]
    assert RegenSettings.from_config({"janela": {"inicio": "2025-10-01", "fim": "2026-09-30"}}).git_subprocess is False
