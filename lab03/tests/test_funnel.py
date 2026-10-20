"""Unit tests for selection funnel tracking and configuration loader (Issue #31 & #28)."""

import csv
from pathlib import Path

import pytest
from pipeline.__main__ import load_config
from pipeline.funnel import FunnelTracker
from pipeline.orchestrator import count_evaluated_candidates, export_funnel_summary

FUNIL_CSV = Path(__file__).resolve().parent.parent / "dados" / "funil.csv"


def _read_funnel(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def assert_funnel_consistent(rows: list[dict[str, str]]) -> None:
    """Each stage = previous - its discards; first row has no discards."""
    assert len(rows) >= 3
    assert int(rows[0]["descartados"]) == 0
    assert int(rows[-1]["descartados"]) == 0
    for prev, cur in zip(rows, rows[1:-1]):
        assert int(cur["quantidade_restante"]) == (
            int(prev["quantidade_restante"]) - int(cur["descartados"])
        ), cur["etapa"]
    discarded = sum(int(r["descartados"]) for r in rows)
    # Every evaluated candidate is either discarded or in the final sample
    assert int(rows[0]["quantidade_restante"]) == discarded + int(
        rows[-1]["quantidade_restante"]
    )
    # The last filter leaves exactly the final sample
    assert int(rows[-2]["quantidade_restante"]) == int(rows[-1]["quantidade_restante"])


class TestFunnelTracker:
    def test_record_stages_and_export_csv(self, tmp_path: Path):
        tracker = FunnelTracker()
        tracker.record_stage("Etapa 1", 1000, 0, "-")
        tracker.record_stage("Etapa 2", 800, 200, "Sem Actions")

        csv_path = tmp_path / "funil.csv"
        exported = tracker.export_csv(csv_path)

        assert exported.is_file()
        content = exported.read_text(encoding="utf-8")
        assert "Etapa 1,1000,0,-" in content
        assert "Etapa 2,800,200,Sem Actions" in content


class TestExportFunnelSummary:
    def test_first_row_counts_accepted_and_all_discards(self, tmp_path: Path):
        path = export_funnel_summary(
            tmp_path / "funil.csv",
            discarded_no_actions=56,
            discarded_low_releases=315,
            discarded_low_runs=50,
            accepted_count=330,
            discarded_git_errors=2,
        )
        rows = _read_funnel(path)
        assert [int(r["quantidade_restante"]) for r in rows] == [
            753, 697, 382, 332, 330, 330
        ]
        assert_funnel_consistent(rows)

    def test_without_git_errors_stage(self, tmp_path: Path):
        path = export_funnel_summary(
            tmp_path / "funil.csv",
            discarded_no_actions=1,
            discarded_low_releases=2,
            discarded_low_runs=3,
            accepted_count=4,
        )
        rows = _read_funnel(path)
        assert len(rows) == 5
        assert int(rows[0]["quantidade_restante"]) == 10
        assert_funnel_consistent(rows)

    def test_count_evaluated_candidates(self):
        assert count_evaluated_candidates(5, 1, 2, 3, 4) == 15
        assert count_evaluated_candidates(5, 0, 0, 0) == 5


def test_committed_funnel_is_arithmetically_consistent():
    assert_funnel_consistent(_read_funnel(FUNIL_CSV))


class TestConfigLoader:
    def test_load_valid_config(self, tmp_path: Path):
        cfg_file = tmp_path / "test_config.yaml"
        cfg_file.write_text("janela:\n  inicio: '2025-01-01'\n", encoding="utf-8")
        cfg = load_config(cfg_file)
        assert cfg["janela"]["inicio"] == "2025-01-01"

    def test_load_missing_config_raises_filenotfound(self):
        with pytest.raises(FileNotFoundError):
            load_config("non_existent_config.yaml")
