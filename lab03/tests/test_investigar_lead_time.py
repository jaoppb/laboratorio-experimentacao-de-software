"""Tests for the lead time diagnosis script (analises.investigar_lead_time)."""

from collections import Counter

import pytest

from analises.investigar_lead_time import MOTIVO_SEM_ARQUIVO, diagnose, motivo_nulo
from metricas.schemas import Commit, Release
from pipeline.commits import ComparisonStatus, ReleaseCommits
from pipeline.releases import save_releases_to_parquet


def _save(tmp_path, name, items):
    owner, repo = name.split("/")
    save_releases_to_parquet(items, owner, repo, tmp_path / f"{owner}__{repo}.parquet")


def _rel(tag, date):
    return Release(tag_name=tag, published_at=date)


def test_motivo_nulo_combines_reasons():
    assert motivo_nulo(Counter(not_found=3)) == "tag não encontrada (equivalente a 404)"
    assert motivo_nulo(Counter(first_release=1, empty=2)) == (
        "primeira release da história + release sem commits novos"
    )
    assert motivo_nulo(Counter()) == "sem releases na janela"


def test_missing_file_is_collection_failure(tmp_path):
    d = diagnose("org/missing", tmp_path)
    assert d.lead_time_a_hours is None
    assert d.motivo_nulo == MOTIVO_SEM_ARQUIVO


def test_all_not_found_gives_null_lead_time(tmp_path):
    r1, r2 = _rel("v1", "2024-01-01T00:00:00Z"), _rel("v2", "2024-02-01T00:00:00Z")
    _save(tmp_path, "org/nf", [ReleaseCommits(r2, r1, ComparisonStatus.NOT_FOUND)])
    d = diagnose("org/nf", tmp_path)
    assert d.not_found == 1
    assert d.motivo_nulo == "tag não encontrada (equivalente a 404)"


def test_one_big_release_inverts_medians_without_invariant_violation(tmp_path):
    """Two small fast releases and one with 5 slow commits: b > a legitimately."""
    day = "T00:00:00Z"
    r0 = _rel("v0", "2024-01-01" + day)
    r1 = _rel("v1", "2024-01-10" + day)
    r2 = _rel("v2", "2024-01-20" + day)
    r3 = _rel("v3", "2024-03-01" + day)
    big = [Commit(sha=f"b{i}", committed_at="2024-01-21" + day) for i in range(5)]
    _save(
        tmp_path,
        "org/inv",
        [
            ReleaseCommits(r1, r0, ComparisonStatus.OK, [Commit("a", "2024-01-09" + day)]),
            ReleaseCommits(r2, r1, ComparisonStatus.OK, [Commit("b", "2024-01-19" + day)]),
            ReleaseCommits(r3, r2, ComparisonStatus.OK, big),
        ],
    )
    d = diagnose("org/inv", tmp_path)
    assert d.lead_time_a_hours == pytest.approx(24.0)
    assert d.lead_time_b_hours == pytest.approx(40 * 24.0)
    assert d.b_maior_que_a
    assert d.violacoes_invariante == 0
    assert d.maior_release == "v3"
    assert d.fracao_commits_maior_release == pytest.approx(5 / 7)


def test_is_out_of_line():
    from analises.investigar_lead_time import is_out_of_line

    assert is_out_of_line("v19.2.0", "v19.0.1")
    assert not is_out_of_line("v19.0.0", "v19.0.1")
    assert not is_out_of_line(None, "v1.0.0")
    assert not is_out_of_line("nightly", "v1.0.0")
