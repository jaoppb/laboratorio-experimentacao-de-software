#!/usr/bin/env python3
"""
time_trial.py — Cronômetro de Trials para o Lab02 (RQ1 / RQ2)

Mede o tempo desde o início do trial até que o participante faça o kata
passar em TODOS os testes de aceitação ("time-to-green" - RQ1), com time-box
fixo de 35 minutos.

Se o tempo esgotar, o trial é registrado como CENSURADO em 35 min (2100 segundos),
preservando a quantidade de testes passando para a RQ2 (defeitos).
A verificação é 100% automática a cada N segundos (padrão: 10s).

Os dados são salvos incrementalmente no CSV lab02/dados/trials.csv, com chaves
compatíveis com collect_metrics.py para a análise estatística (Wilcoxon) da Sprint 3.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Adiciona o diretório lab02 ao PYTHONPATH para importar src
lab02_dir = Path(__file__).resolve().parent.parent
if str(lab02_dir) not in sys.path:
    sys.path.insert(0, str(lab02_dir))

import structlog  # noqa: E402

from src.storage.csv_manager import CSVManager  # noqa: E402
from src.timer.trial_timer import TrialTimer, normalize_treatment  # noqa: E402

# Configuração de logging estruturado (seguindo padrão do Lab01)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger("time_trial")


def format_duration(seconds: float) -> str:
    """Formata segundos em formato legível mm:ss."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cronômetro automatizado de trials para o Lab02 (Time-to-green e Defeitos).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--trial-id",
        required=True,
        help="Identificador do trial (ex: trial-01, T01, etc.).",
    )
    parser.add_argument(
        "--participant",
        required=True,
        help="Nome do participante (ex: marcela, joao, gabriel).",
    )
    parser.add_argument(
        "--treatment",
        required=True,
        choices=["com_ia", "sem_ia", "ai", "manual"],
        help="Tratamento experimental: 'com_ia' (ou 'ai') vs 'sem_ia' (ou 'manual').",
    )
    parser.add_argument(
        "--kata",
        required=True,
        help="Nome ou pasta do kata (ex: 01-bario-world, 02-cards, 03-exploring-terrain, etc.).",
    )
    parser.add_argument(
        "--solution",
        required=True,
        help="Caminho do arquivo de solução que está sendo editado (ex: solution.py).",
    )
    parser.add_argument(
        "--test-path",
        default=None,
        help="Caminho opcional para arquivo de teste específico (pytest ou suite alternativa).",
    )
    parser.add_argument(
        "--runner",
        choices=["auto", "kata", "pytest"],
        default="auto",
        help="Tipo de executor de testes (padrão: auto - usa run_tests.py dos katas ou pytest).",
    )
    parser.add_argument(
        "--timebox",
        type=float,
        default=35.0,
        help="Tempo limite máximo do trial em minutos (padrão: 35.0).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=10.0,
        help="Intervalo de verificação automática em segundos (padrão: 10.0).",
    )
    parser.add_argument(
        "--output-csv",
        default="trials.csv",
        help="Nome do arquivo CSV de saída dentro da pasta de dados (padrão: trials.csv).",
    )
    parser.add_argument(
        "--dados-dir",
        default=None,
        help="Diretório onde os CSVs serão salvos (padrão: lab02/dados/).",
    )

    return parser.parse_args(args)


def main() -> int:
    args = parse_args()

    solution_file = Path(args.solution).resolve()
    if not solution_file.exists():
        # Se o arquivo ainda não existe, cria um arquivo inicial vazio para o participante
        solution_file.parent.mkdir(parents=True, exist_ok=True)
        solution_file.write_text("# Solução do Kata - Inicie sua implementação aqui\n", encoding="utf-8")
        print(f"[INFO] Arquivo de solucao inicial criado em: {solution_file}")

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    dados_dir = Path(args.dados_dir).resolve() if args.dados_dir else lab02_dir / "dados"
    csv_manager = CSVManager(dados_dir)

    norm_treatment = normalize_treatment(args.treatment)
    timebox_sec = args.timebox * 60.0

    print("=" * 70)
    print(" [CRONOMETRO] LAB02 - CRONOMETRO DE TRIAL EXPERIMENTAL")
    print("=" * 70)
    print(f" * Trial ID:       {args.trial_id}")
    print(f" * Participante:   {args.participant.capitalize()}")
    print(f" * Tratamento:     {norm_treatment.upper()} ({args.treatment})")
    print(f" * Kata:           {args.kata}")
    print(f" * Arquivo:        {solution_file}")
    print(f" * Time-box:       {args.timebox:.1f} minutos ({int(timebox_sec)}s)")
    print(f" * Checagem:       A cada {args.interval:.1f}s automaticamente")
    print(f" * Saida CSV:      {dados_dir / args.output_csv}")
    print("=" * 70)
    print(" Dica: Programacao normal na IDE. Os testes rodam sozinhos em segundo plano.")
    print("=" * 70)
    print()

    # Callback para atualização visual amigável no terminal
    def on_tick(iteration: int, elapsed: float, passed: int, total: int):
        remaining = max(0.0, timebox_sec - elapsed)
        passed_str = f"{passed}/{total}" if total > 0 else "0/?"
        sys.stdout.write(
            f"\r[Checagem #{iteration:03d} | Decorrido: {format_duration(elapsed)} | Restam: {format_duration(remaining)}] Testes passando: {passed_str}  "
        )
        sys.stdout.flush()

    timer = TrialTimer(
        trial_id=args.trial_id,
        participant=args.participant,
        treatment=args.treatment,
        kata=args.kata,
        solution_path=solution_file,
        test_path=args.test_path,
        timebox_seconds=timebox_sec,
        poll_interval_seconds=args.interval,
        runner_type=args.runner,
        csv_manager=csv_manager,
        output_filename=args.output_csv,
        on_tick=on_tick,
    )

    result = timer.run()
    print("\n")

    print("-" * 70)
    if result.status == "completed":
        print(" [SUCESSO] TIME-TO-GREEN ALCANCADO!")
        print(f" * Tempo ate o verde (RQ1): {result.time_seconds:.2f}s ({format_duration(result.time_seconds)})")
        print(f" * Testes de aceitacao:     {result.passed_tests}/{result.total_tests} (100% passando)")
        print(f" * Censurado:               {result.censored}")
    elif result.status == "censored_timeout":
        print(" [TIMEOUT] TIME-BOX ESGOTADO!")
        print(f" * Tempo registrado:        {result.time_seconds:.2f}s (CENSURADO em {args.timebox:.0f} min)")
        print(f" * Testes passando (RQ2):   {result.passed_tests}/{result.total_tests} (Taxa: {result.success_rate * 100:.1f}%)")
        print(f" * Defeitos restantes:      {result.failed_tests}")
        print(f" * Censurado:               {result.censored} (Dado preservado para analise)")
    elif result.status == "interrupted":
        print(" [INTERROMPIDO] TRIAL INTERROMPIDO PELO USUARIO!")
        print(f" * Tempo decorrido:         {result.time_seconds:.2f}s")
        print(f" * Testes passando:         {result.passed_tests}/{result.total_tests}")
        print(f" * Censurado:               {result.censored}")
    print("-" * 70)
    print(f" [OK] Resultado gravado em: {dados_dir / args.output_csv}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
