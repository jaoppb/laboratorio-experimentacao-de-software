#!/usr/bin/env python3
"""Executa os testes de aceitacao de um kata contra uma solucao qualquer.

Uso:
    python3 run_tests.py <kata_dir> -- <comando da solucao>

Exemplos:
    python3 run_tests.py ../01-bario-world -- python3 solution.py
    python3 run_tests.py ../06-n-checkers  -- java -cp out Main
    python3 run_tests.py ../05-dish-rack   -- ./a.out

Cada kata tem um diretorio tests/ com pares <nome>.in / <nome>.out. A saida da
solucao e comparada com o .out esperado, ignorando espacos no fim das linhas e
linhas em branco no fim do arquivo. Katas com mais de uma resposta valida tem um
checker.py proprio na raiz do kata, que e chamado no lugar da comparacao direta.

Codigo de saida: 0 se todos os testes passaram, 1 caso contrario -- e o que o
script de cronometragem usa para detectar o "time-to-green".
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def normalize(text):
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def run_checker(checker, in_file, expected_file, actual_text):
    with tempfile.NamedTemporaryFile("w", suffix=".out", delete=False) as tmp:
        tmp.write(actual_text)
        actual_file = tmp.name
    try:
        proc = subprocess.run(
            [sys.executable, str(checker), str(in_file), str(expected_file), actual_file],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr).strip()
    finally:
        Path(actual_file).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kata_dir", help="diretorio do kata (contem tests/)")
    parser.add_argument("--timeout", type=float, default=10.0, help="timeout por teste, em segundos")
    parser.add_argument("--json", dest="json_path", help="grava o resumo em JSON neste caminho")
    parser.add_argument("--quiet", action="store_true", help="imprime apenas o resumo final")

    argv = sys.argv[1:]
    if "--" not in argv:
        parser.error("informe o comando da solucao depois de --")
    split = argv.index("--")
    args = parser.parse_args(argv[:split])
    command = argv[split + 1 :]
    if not command:
        parser.error("informe o comando da solucao depois de --")

    kata_dir = Path(args.kata_dir).resolve()
    tests = sorted((kata_dir / "tests").glob("*.in"))
    if not tests:
        parser.error(f"nenhum teste encontrado em {kata_dir / 'tests'}")

    checker = kata_dir / "checker.py"
    results = []

    for in_file in tests:
        expected_file = in_file.with_suffix(".out")
        name = in_file.stem
        try:
            proc = subprocess.run(
                command,
                stdin=in_file.open(),
                capture_output=True,
                text=True,
                timeout=args.timeout,
            )
        except subprocess.TimeoutExpired:
            results.append({"test": name, "passed": False, "reason": f"timeout ({args.timeout}s)"})
            continue
        except FileNotFoundError:
            parser.error(f"comando nao encontrado: {command[0]}")

        if proc.returncode != 0:
            reason = f"exit code {proc.returncode}: {proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else ''}"
            results.append({"test": name, "passed": False, "reason": reason})
            continue

        if checker.exists():
            passed, reason = run_checker(checker, in_file, expected_file, proc.stdout)
        else:
            passed = normalize(proc.stdout) == normalize(expected_file.read_text())
            reason = "" if passed else "saida diferente da esperada"
        results.append({"test": name, "passed": passed, "reason": reason})

    passed = sum(r["passed"] for r in results)
    total = len(results)

    if not args.quiet:
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            detail = f"  ({r['reason']})" if r["reason"] else ""
            print(f"[{status}] {r['test']}{detail}")

    print(f"{passed}/{total} testes de aceitacao passaram")

    if args.json_path:
        Path(args.json_path).write_text(
            json.dumps(
                {"kata": kata_dir.name, "passed": passed, "total": total, "tests": results},
                indent=2,
            )
        )

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
