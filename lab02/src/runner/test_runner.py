from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TestRunResult:
    __test__ = False
    passed: int
    total: int
    failed: int
    all_passed: bool
    output: str = ""
    error_message: str = ""


class TestRunner:
    """Adaptador de execução de testes de aceitação para o Lab02.

    Suporta:
    1. Executor oficial dos katas da Maratona Mineira (katas/common/run_tests.py) com I/O stdin/stdout.
    2. Testes baseados em Pytest (com extração estruturada via JUnit XML).
    """

    __test__ = False

    def __init__(self, repo_lab02_dir: Optional[Path] = None):
        if repo_lab02_dir is not None:
            self.lab02_dir = Path(repo_lab02_dir).resolve()
        else:
            # Tenta encontrar a pasta lab02 subindo a partir do arquivo atual
            current = Path(__file__).resolve()
            # current: lab02/src/runner/test_runner.py -> parent.parent.parent = lab02
            self.lab02_dir = current.parent.parent.parent

        self.kata_runner_script = self.lab02_dir / "katas" / "common" / "run_tests.py"

    def resolve_kata_dir(self, kata_name_or_path: str) -> Path:
        """Resolve o caminho do diretório do kata."""
        path = Path(kata_name_or_path)
        if path.is_dir() and (path / "tests").exists():
            return path.resolve()

        # Procura dentro de lab02/katas/
        candidate = self.lab02_dir / "katas" / kata_name_or_path
        if candidate.is_dir() and (candidate / "tests").exists():
            return candidate.resolve()

        # Tenta match parcial (ex: "01" ou "bario" -> "01-bario-world")
        katas_dir = self.lab02_dir / "katas"
        if katas_dir.exists():
            for d in katas_dir.iterdir():
                if d.is_dir() and kata_name_or_path.lower() in d.name.lower():
                    if (d / "tests").exists():
                        return d.resolve()

        raise FileNotFoundError(
            f"Diretório do kata '{kata_name_or_path}' contendo 'tests/' não foi encontrado em {katas_dir}."
        )

    def run_kata_tests(
        self,
        kata_dir: Path,
        solution_path: Path,
        timeout_per_test: float = 10.0,
    ) -> TestRunResult:
        """Executa os testes de aceitação de um kata usando katas/common/run_tests.py."""
        if not self.kata_runner_script.exists():
            raise FileNotFoundError(
                f"Script runner dos katas não encontrado em: {self.kata_runner_script}"
            )

        solution_file = Path(solution_path).resolve()
        if not solution_file.exists():
            return TestRunResult(
                passed=0,
                total=0,
                failed=0,
                all_passed=False,
                error_message=f"Arquivo de solução não encontrado: {solution_file}",
            )

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp_json:
            tmp_json_path = Path(tmp_json.name)

        try:
            cmd = [
                sys.executable,
                str(self.kata_runner_script),
                str(kata_dir),
                "--timeout",
                str(timeout_per_test),
                "--json",
                str(tmp_json_path),
                "--quiet",
                "--",
                sys.executable,
                str(solution_file),
            ]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            passed = 0
            total = 0

            if tmp_json_path.exists() and tmp_json_path.stat().st_size > 0:
                try:
                    data = json.loads(tmp_json_path.read_text(encoding="utf-8"))
                    passed = int(data.get("passed", 0))
                    total = int(data.get("total", 0))
                except Exception as e:
                    logger.warning("failed_to_parse_kata_json", error=str(e))

            failed = max(0, total - passed)
            all_passed = (proc.returncode == 0) and (total > 0) and (passed == total)

            return TestRunResult(
                passed=passed,
                total=total,
                failed=failed,
                all_passed=all_passed,
                output=(proc.stdout + proc.stderr).strip(),
            )
        except Exception as e:
            return TestRunResult(
                passed=0,
                total=0,
                failed=0,
                all_passed=False,
                error_message=str(e),
            )
        finally:
            tmp_json_path.unlink(missing_ok=True)

    def run_pytest_tests(
        self,
        test_path: Path,
        solution_path: Optional[Path] = None,
        timeout: float = 30.0,
    ) -> TestRunResult:
        """Executa testes com pytest e extrai a contagem de testes via JUnit XML."""
        test_file = Path(test_path).resolve()
        if not test_file.exists():
            return TestRunResult(
                passed=0,
                total=0,
                failed=0,
                all_passed=False,
                error_message=f"Arquivo de testes pytest não encontrado: {test_file}",
            )

        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False) as tmp_xml:
            tmp_xml_path = Path(tmp_xml.name)

        # Prepara ambiente para encontrar a solução se fornecida
        env = os.environ.copy()
        if solution_path:
            sol_dir = str(Path(solution_path).resolve().parent)
            existing_pp = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{sol_dir}{os.pathsep}{existing_pp}" if existing_pp else sol_dir

        try:
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(test_file),
                f"--junitxml={tmp_xml_path}",
                "-q",
                "--tb=no",
            ]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )

            passed = 0
            total = 0
            failed = 0

            if tmp_xml_path.exists() and tmp_xml_path.stat().st_size > 0:
                try:
                    tree = ET.parse(tmp_xml_path)
                    root = tree.getroot()
                    # root pode ser <testsuites> ou <testsuite>
                    if root.tag == "testsuites":
                        found_suite = root.find("testsuite")
                        suite = found_suite if found_suite is not None else root
                    else:
                        suite = root

                    total = int(suite.attrib.get("tests", 0))
                    failures = int(suite.attrib.get("failures", 0))
                    errors = int(suite.attrib.get("errors", 0))
                    failed = failures + errors
                    passed = max(0, total - failed)
                except Exception as e:
                    logger.warning("failed_to_parse_pytest_xml", error=str(e))

            all_passed = (proc.returncode == 0) and (total > 0) and (failed == 0)

            return TestRunResult(
                passed=passed,
                total=total,
                failed=failed,
                all_passed=all_passed,
                output=(proc.stdout + proc.stderr).strip(),
            )
        except subprocess.TimeoutExpired:
            return TestRunResult(
                passed=0,
                total=0,
                failed=0,
                all_passed=False,
                error_message=f"Timeout ({timeout}s) ao executar pytest.",
            )
        except Exception as e:
            return TestRunResult(
                passed=0,
                total=0,
                failed=0,
                all_passed=False,
                error_message=str(e),
            )
        finally:
            tmp_xml_path.unlink(missing_ok=True)

    def run_tests(
        self,
        kata_name_or_dir: Optional[str] = None,
        solution_path: Optional[Path] = None,
        test_path: Optional[Path] = None,
        runner_type: str = "auto",
        timeout_per_test: float = 10.0,
    ) -> TestRunResult:
        """Executa a suíte de testes apropriada conforme a configuração."""
        if runner_type == "pytest" or (test_path and test_path.suffix == ".py" and not kata_name_or_dir):
            if test_path is None:
                raise ValueError("Para o runner pytest, 'test_path' deve ser informado.")
            return self.run_pytest_tests(test_path, solution_path=solution_path)

        # Caso padrão: Kata runner
        if not kata_name_or_dir:
            raise ValueError("Informe o nome do kata ou diretório do kata para executar os testes.")

        kata_dir = self.resolve_kata_dir(kata_name_or_dir)
        if not solution_path:
            raise ValueError("Caminho do arquivo de solução não informado.")

        return self.run_kata_tests(
            kata_dir=kata_dir,
            solution_path=solution_path,
            timeout_per_test=timeout_per_test,
        )
