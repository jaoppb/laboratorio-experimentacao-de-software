"""Unit tests for selection funnel tracking and configuration loader (Issue #31 & #28)."""

from pathlib import Path

import pytest
from pipeline.__main__ import load_config
from pipeline.funnel import FunnelTracker


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


class TestConfigLoader:
    def test_load_valid_config(self, tmp_path: Path):
        cfg_file = tmp_path / "test_config.yaml"
        cfg_file.write_text("janela:\n  inicio: '2025-01-01'\n", encoding="utf-8")
        cfg = load_config(cfg_file)
        assert cfg["janela"]["inicio"] == "2025-01-01"

    def test_load_missing_config_raises_filenotfound(self):
        with pytest.raises(FileNotFoundError):
            load_config("non_existent_config.yaml")
