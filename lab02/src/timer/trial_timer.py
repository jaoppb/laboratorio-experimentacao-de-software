from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import structlog

from src.runner.test_runner import TestRunner
from src.storage.csv_manager import CSVManager

logger = structlog.get_logger(__name__)


def normalize_treatment(treatment: str) -> str:
    """Normaliza a string do tratamento para os padrões do experimento ('ai' ou 'manual').

    Mapeia:
      'com_ia', 'com-ia', 'ia', 'ai' -> 'ai'
      'sem_ia', 'sem-ia', 'manual'   -> 'manual'
    """
    clean = treatment.strip().lower().replace("-", "_")
    if clean in ("com_ia", "ia", "ai"):
        return "ai"
    elif clean in ("sem_ia", "manual"):
        return "manual"
    return clean


@dataclass
class TrialResult:
    trial_id: str
    participant: str
    treatment: str
    kata: str
    file: str
    time_seconds: float
    censored: bool
    passed_tests: int
    total_tests: int
    failed_tests: int
    success_rate: float
    timestamp: str
    status: str
    actual_elapsed_seconds: float = 0.0

    def to_csv_dict(self) -> dict:
        d = asdict(self)
        return d


class TrialTimer:
    """Motor de cronometragem para os trials do Lab02.

    Mede o tempo desde o início do trial até que a solução passe em TODOS os testes
    de aceitação (time-to-green - RQ1), respeitando o time-box máximo (padrão de 35 min).
    Se o tempo esgotar sem que todos os testes passem, o trial é registrado como CENSURADO
    em 35 min (2100s) e retém a quantidade de testes passando (RQ2).
    """

    def __init__(
        self,
        trial_id: str,
        participant: str,
        treatment: str,
        kata: str,
        solution_path: Path | str,
        test_path: Optional[Path | str] = None,
        timebox_seconds: float = 35 * 60,  # 35 minutos = 2100 segundos
        poll_interval_seconds: float = 10.0,
        runner_type: str = "auto",
        csv_manager: Optional[CSVManager] = None,
        output_filename: str = "trials.csv",
        test_runner: Optional[TestRunner] = None,
        on_tick: Optional[Callable[[int, float, int, int], None]] = None,
    ):
        self.trial_id = trial_id.strip()
        self.participant = participant.strip().lower()
        self.treatment = normalize_treatment(treatment)
        self.kata = kata.strip()
        self.solution_path = Path(solution_path).resolve()
        self.test_path = Path(test_path).resolve() if test_path else None
        self.timebox_seconds = float(timebox_seconds)
        self.poll_interval_seconds = max(0.5, float(poll_interval_seconds))
        self.runner_type = runner_type
        self.output_filename = output_filename
        self.on_tick = on_tick

        self.test_runner = test_runner or TestRunner()

        if csv_manager is None:
            # Padrão: lab02/dados/
            default_dados_dir = self.test_runner.lab02_dir / "dados"
            self.csv_manager = CSVManager(default_dados_dir)
        else:
            self.csv_manager = csv_manager

    def run(self) -> TrialResult:
        """Executa a rotina de cronometragem em loop até o sucesso (time-to-green) ou timeout."""
        start_iso = datetime.now(timezone.utc).isoformat()
        log = logger.bind(
            trial_id=self.trial_id,
            participant=self.participant,
            treatment=self.treatment,
            kata=self.kata,
            timebox=self.timebox_seconds,
        )
        log.info("trial_started", start_time=start_iso)

        t0 = time.perf_counter()
        iteration = 0
        latest_passed = 0
        latest_total = 0
        latest_failed = 0

        censored = False
        status = "running"
        final_time_seconds = 0.0
        actual_elapsed = 0.0

        try:
            while True:
                iteration += 1
                elapsed = time.perf_counter() - t0
                actual_elapsed = elapsed

                # Verifica estouro do timebox
                if elapsed >= self.timebox_seconds:
                    log.warning(
                        "timebox_expired_censored",
                        elapsed_seconds=round(elapsed, 2),
                        timebox=self.timebox_seconds,
                    )
                    censored = True
                    status = "censored_timeout"
                    final_time_seconds = self.timebox_seconds
                    break

                # Executa a verificação dos testes de aceitação
                run_res = self.test_runner.run_tests(
                    kata_name_or_dir=self.kata,
                    solution_path=self.solution_path,
                    test_path=self.test_path,
                    runner_type=self.runner_type,
                )

                latest_passed = run_res.passed
                latest_total = run_res.total
                latest_failed = run_res.failed

                # Notifica callback para feedback visual no CLI
                if self.on_tick:
                    self.on_tick(iteration, elapsed, latest_passed, latest_total)

                log.debug(
                    "check_iteration",
                    iteration=iteration,
                    elapsed_seconds=round(elapsed, 2),
                    passed=latest_passed,
                    total=latest_total,
                )

                # Verifica condição de vitória: ALL PASS
                if run_res.all_passed:
                    time_to_green = round(elapsed, 2)
                    log.info(
                        "time_to_green_achieved",
                        time_to_green_seconds=time_to_green,
                        passed=latest_passed,
                        total=latest_total,
                    )
                    censored = False
                    status = "completed"
                    final_time_seconds = time_to_green
                    break

                # Aguarda o intervalo de polling sem ultrapassar o tempo limite
                remaining = self.timebox_seconds - (time.perf_counter() - t0)
                if remaining <= 0:
                    censored = True
                    status = "censored_timeout"
                    final_time_seconds = self.timebox_seconds
                    break

                sleep_duration = min(self.poll_interval_seconds, remaining)
                time.sleep(sleep_duration)

        except KeyboardInterrupt:
            elapsed = time.perf_counter() - t0
            actual_elapsed = elapsed
            log.warning("trial_interrupted_by_user", elapsed_seconds=round(elapsed, 2))
            censored = True
            status = "interrupted"
            final_time_seconds = round(elapsed, 2)

        # Se nunca conseguiu executar os testes para obter total (ex: arquivo não encontrado), default 0
        success_rate = (
            round(latest_passed / latest_total, 4) if latest_total > 0 else 0.0
        )

        result = TrialResult(
            trial_id=self.trial_id,
            participant=self.participant,
            treatment=self.treatment,
            kata=self.kata,
            file=str(self.solution_path),
            time_seconds=final_time_seconds,
            censored=censored,
            passed_tests=latest_passed,
            total_tests=latest_total,
            failed_tests=latest_failed,
            success_rate=success_rate,
            timestamp=start_iso,
            status=status,
            actual_elapsed_seconds=round(actual_elapsed, 2),
        )

        # Salva o resultado no CSV incrementalmente
        saved_path = self.csv_manager.append_record(
            result.to_csv_dict(), self.output_filename
        )
        log.info(
            "trial_recorded",
            destination=str(saved_path),
            censored=censored,
            time_seconds=final_time_seconds,
        )

        return result
