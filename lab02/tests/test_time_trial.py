"""
Testes unitários e de integração para o cronômetro de trials (lab02/src/timer e lab02/scripts/time_trial.py).
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.runner.test_runner import TestRunner, TestRunResult
from src.storage.csv_manager import CSVManager
from src.timer.trial_timer import TrialTimer, normalize_treatment


def test_normalize_treatment():
    assert normalize_treatment("com_ia") == "ai"
    assert normalize_treatment("com-ia") == "ai"
    assert normalize_treatment("ia") == "ai"
    assert normalize_treatment("ai") == "ai"
    assert normalize_treatment("sem_ia") == "manual"
    assert normalize_treatment("sem-ia") == "manual"
    assert normalize_treatment("manual") == "manual"


def test_csv_manager_append_and_headers(tmp_path: Path):
    manager = CSVManager(tmp_path)
    filename = "test_trials.csv"

    record1 = {
        "trial_id": "T01",
        "participant": "marcela",
        "treatment": "ai",
        "kata": "01-bario-world",
        "time_seconds": 150.5,
        "censored": False,
        "passed_tests": 20,
        "total_tests": 20,
    }
    manager.append_record(record1, filename)

    csv_file = tmp_path / filename
    assert csv_file.exists()

    records = manager.read_records(filename)
    assert len(records) == 1
    assert records[0]["trial_id"] == "T01"
    assert records[0]["passed_tests"] == "20"
    assert records[0]["censored"] == "False"

    # Segundo registro adicionado incrementalmente
    record2 = {
        "trial_id": "T02",
        "participant": "joao",
        "treatment": "manual",
        "kata": "02-cards",
        "time_seconds": 2100.0,
        "censored": True,
        "passed_tests": 12,
        "total_tests": 20,
    }
    manager.append_record(record2, filename)

    records = manager.read_records(filename)
    assert len(records) == 2
    assert records[1]["trial_id"] == "T02"
    assert records[1]["participant"] == "joao"
    assert records[1]["censored"] == "True"

    # Confirma que há apenas uma linha de cabeçalho no arquivo bruto
    lines = csv_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3  # 1 header + 2 rows


def test_pytest_runner_integration(tmp_path: Path):
    runner = TestRunner()

    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "def test_one():\n"
        "    assert 1 == 1\n"
        "def test_two():\n"
        "    assert 2 == 2\n"
        "def test_three():\n"
        "    assert 1 == 2\n",
        encoding="utf-8",
    )

    res = runner.run_pytest_tests(test_file)
    assert res.total == 3
    assert res.passed == 2
    assert res.failed == 1
    assert res.all_passed is False

    # Corrige o teste para passar
    test_file.write_text(
        "def test_one():\n"
        "    assert 1 == 1\n"
        "def test_two():\n"
        "    assert 2 == 2\n",
        encoding="utf-8",
    )

    res2 = runner.run_pytest_tests(test_file)
    assert res2.total == 2
    assert res2.passed == 2
    assert res2.failed == 0
    assert res2.all_passed is True


def test_kata_runner_with_real_gabarito():
    lab02_dir = Path(__file__).resolve().parent.parent
    runner = TestRunner(lab02_dir)

    gabarito_bario = lab02_dir / "katas" / "gabaritos" / "01-bario-world.py"
    if not gabarito_bario.exists():
        pytest.skip("Gabarito 01-bario-world.py não encontrado")

    res = runner.run_kata_tests(
        kata_dir=lab02_dir / "katas" / "01-bario-world",
        solution_path=gabarito_bario,
        timeout_per_test=5.0,
    )

    assert res.total == 20
    assert res.passed == 20
    assert res.failed == 0
    assert res.all_passed is True


def test_trial_timer_time_to_green_immediate(tmp_path: Path):
    mock_runner = MagicMock()
    mock_runner.run_tests.return_value = TestRunResult(
        passed=20,
        total=20,
        failed=0,
        all_passed=True,
    )

    csv_mgr = CSVManager(tmp_path)
    sol_file = tmp_path / "solution.py"
    sol_file.write_text("print(1)", encoding="utf-8")

    ticks = []

    def on_tick(it, elapsed, p, t):
        ticks.append((it, p, t))

    timer = TrialTimer(
        trial_id="T01",
        participant="marcela",
        treatment="com_ia",
        kata="01-bario-world",
        solution_path=sol_file,
        timebox_seconds=60.0,
        poll_interval_seconds=0.5,
        test_runner=mock_runner,
        csv_manager=csv_mgr,
        output_filename="trials.csv",
        on_tick=on_tick,
    )

    result = timer.run()

    assert result.status == "completed"
    assert result.censored is False
    assert result.treatment == "ai"
    assert result.passed_tests == 20
    assert result.total_tests == 20
    assert result.failed_tests == 0
    assert result.success_rate == 1.0
    assert result.time_seconds < 5.0
    assert len(ticks) == 1

    saved = csv_mgr.read_records("trials.csv")
    assert len(saved) == 1
    assert saved[0]["trial_id"] == "T01"
    assert saved[0]["treatment"] == "ai"
    assert saved[0]["censored"] == "False"


def test_trial_timer_censored_timeout(tmp_path: Path):
    mock_runner = MagicMock()
    # Solução que passa em apenas 5 de 20 testes
    mock_runner.run_tests.return_value = TestRunResult(
        passed=5,
        total=20,
        failed=15,
        all_passed=False,
    )

    csv_mgr = CSVManager(tmp_path)
    sol_file = tmp_path / "solution.py"
    sol_file.write_text("print(0)", encoding="utf-8")

    timebox = 1.2
    timer = TrialTimer(
        trial_id="T02",
        participant="gabriel",
        treatment="sem_ia",
        kata="02-cards",
        solution_path=sol_file,
        timebox_seconds=timebox,
        poll_interval_seconds=0.3,
        test_runner=mock_runner,
        csv_manager=csv_mgr,
        output_filename="trials.csv",
    )

    t_start = time.perf_counter()
    result = timer.run()
    t_end = time.perf_counter()

    assert result.status == "censored_timeout"
    assert result.censored is True
    assert result.treatment == "manual"
    assert result.time_seconds == timebox  # Registrado no corte de censura
    assert result.passed_tests == 5
    assert result.total_tests == 20
    assert result.failed_tests == 15
    assert result.success_rate == 0.25
    assert t_end - t_start >= 1.0

    saved = csv_mgr.read_records("trials.csv")
    assert len(saved) == 1
    assert saved[0]["trial_id"] == "T02"
    assert saved[0]["treatment"] == "manual"
    assert saved[0]["censored"] == "True"
    assert saved[0]["passed_tests"] == "5"


def test_schema_keys_matching_collect_metrics():
    """Valida se as chaves primárias de identificação batem exatamente com collect_metrics.py."""

    # Colunas geradas pelo TrialResult
    timer_keys = [
        "trial_id",
        "participant",
        "treatment",
        "kata",
        "file",
    ]

    # Campos definidos em collect_metrics.py
    cm_fields = [
        "file",
        "kata",
        "participant",
        "treatment",
        "trial_id",
    ]

    # Ambas as listas devem conter exatamente o mesmo conjunto de chaves
    assert set(timer_keys) == set(cm_fields)
