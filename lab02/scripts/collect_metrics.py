#!/usr/bin/env python3
"""
collect_metrics.py — Coletor de Métricas Estáticas de Código (Lab02)

Coleta as métricas estáticas necessárias para a RQ3 do Lab02:
1. Complexidade Ciclomática média (McCabe) por função/método (Radon CC)
2. % de linhas duplicadas (jscpd com fallback nativo em Python)
3. LOC (Linhas de Código) como métrica de controle (Radon raw: loc, sloc, lloc, comments)
4. Índice de Manutenibilidade (Radon MI)

Suporta saídas em formato Tabela (terminal), JSON e CSV (para análise estatística na S03).
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import radon.complexity as radon_cc
import radon.metrics as radon_mi
import radon.raw as radon_raw

# ---------------------------------------------------------------------------
# Estruturas de Dados das Métricas
# ---------------------------------------------------------------------------


@dataclass
class FunctionCC:
    name: str
    kind: str  # 'function' ou 'method'
    lineno: int
    complexity: int
    rank: str


@dataclass
class CloneBlock:
    start_line_a: int
    end_line_a: int
    start_line_b: int
    end_line_b: int
    lines_count: int


@dataclass
class TrialMetrics:
    file: str
    kata: str = ""
    participant: str = ""
    treatment: str = ""  # 'ai' ou 'manual'
    trial_id: str = ""
    # LOC (Métrica de Controle)
    loc: int = 0
    sloc: int = 0
    lloc: int = 0
    comments: int = 0
    blank: int = 0
    # Complexidade Ciclomática (McCabe)
    functions_count: int = 0
    cc_avg: float = 0.0
    cc_max: int = 0
    cc_min: int = 0
    cc_total: int = 0
    cc_rank: str = "A"
    functions: list[FunctionCC] = field(default_factory=list)
    # Duplicação de Código
    duplicated_lines: int = 0
    duplication_percentage: float = 0.0
    clones_count: int = 0
    duplication_tool: str = ""
    clones: list[CloneBlock] = field(default_factory=list)
    # Índice de Manutenibilidade
    mi: float = 0.0
    mi_rank: str = "A"
    # Status
    status: str = "ok"
    error_message: str = ""


# ---------------------------------------------------------------------------
# Complexidade Ciclomática (McCabe)
# ---------------------------------------------------------------------------


class _ModuleComplexityVisitor(ast.NodeVisitor):
    """Calcula a complexidade ciclomática de código top-level (sem funções)."""

    def __init__(self) -> None:
        self.complexity = 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.complexity += 1
        if node.ifs:
            self.complexity += len(node.ifs)
        self.generic_visit(node)

    def visit_Match(self, node: Any) -> None:
        # Suporte a Python 3.10+ match/case se presente no AST
        cases = getattr(node, "cases", [])
        if cases:
            self.complexity += max(0, len(cases) - 1)
        self.generic_visit(node)


def compute_cyclomatic_complexity(
    code: str,
) -> tuple[int, float, int, int, int, str, list[FunctionCC]]:
    """
    Calcula métricas de CC usando Radon e AST.
    Retorna: (functions_count, cc_avg, cc_max, cc_min, cc_total, cc_rank, functions)
    """
    blocks = radon_cc.cc_visit(code)
    # Filtra funções e métodos (ignora blocos de classe, mantendo seus métodos)
    funcs: list[FunctionCC] = []
    for b in blocks:
        if type(b).__name__ == "Function" or getattr(b, "letter", "") in ("F", "M"):
            kind = "method" if getattr(b, "is_method", False) else "function"
            funcs.append(
                FunctionCC(
                    name=b.name,
                    kind=kind,
                    lineno=b.lineno,
                    complexity=b.complexity,
                    rank=radon_cc.cc_rank(b.complexity),
                )
            )

    if funcs:
        total_cc = sum(f.complexity for f in funcs)
        count = len(funcs)
        cc_avg = round(total_cc / count, 2)
        cc_max = max(f.complexity for f in funcs)
        cc_min = min(f.complexity for f in funcs)
        rank = radon_cc.cc_rank(round(cc_avg))
        return count, cc_avg, cc_max, cc_min, total_cc, rank, funcs

    # Caso especial: script sem funções declaradas (ex: solução procedural/competitiva)
    try:
        tree = ast.parse(code)
        visitor = _ModuleComplexityVisitor()
        visitor.visit(tree)
        module_cc = visitor.complexity
    except Exception:
        module_cc = 1

    rank = radon_cc.cc_rank(module_cc)
    return 0, float(module_cc), module_cc, module_cc, module_cc, rank, []


# ---------------------------------------------------------------------------
# Duplicação de Código (jscpd + Fallback Python CPD)
# ---------------------------------------------------------------------------


def detect_duplicates_python(
    code: str, min_lines: int = 4
) -> tuple[int, float, int, list[CloneBlock]]:
    """
    Detector nativo em Python de linhas duplicadas (CPD equivalente).
    Identifica blocos de linhas normalizadas contíguas de tamanho >= min_lines
    que ocorrem em mais de uma posição do mesmo arquivo.
    Retorna: (duplicated_lines_count, duplication_percentage, clones_count, clones)
    """
    raw_lines = code.splitlines()
    total_lines = len(raw_lines)
    if total_lines < min_lines:
        return 0, 0.0, 0, []

    # Normaliza linhas ignorando espaços em branco e comentários puros para detecção de padrões
    norm_lines = [line.strip() for line in raw_lines]

    # Mapeia janelas de tamanho min_lines para suas posições de início (0-indexed)
    windows: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for i in range(total_lines - min_lines + 1):
        window = tuple(norm_lines[i : i + min_lines])
        # Ignora blocos compostos unicamente por linhas em branco ou comentários
        if any(bool(line and not line.startswith("#")) for line in window):
            windows[window].append(i)

    # Identifica duplicatas e expande para encontrar clones máximos
    found_clones: list[CloneBlock] = []
    duplicated_line_indices: set[int] = set()

    for _window, positions in windows.items():
        if len(positions) < 2:
            continue
        for idx1 in range(len(positions)):
            for idx2 in range(idx1 + 1, len(positions)):
                p1, p2 = positions[idx1], positions[idx2]
                # Verifica se não são janelas sobrepostas
                if abs(p1 - p2) >= min_lines:
                    # Expande para frente o máximo possível
                    match_len = 0
                    while (
                        p1 + match_len < total_lines
                        and p2 + match_len < total_lines
                        and norm_lines[p1 + match_len] == norm_lines[p2 + match_len]
                    ):
                        match_len += 1

                    if match_len >= min_lines:
                        # Marca apenas as linhas clonadas adicionais (instância 2 em diante),
                        # alinhando com a convenção do CPD/jscpd
                        for offset in range(match_len):
                            duplicated_line_indices.add(p2 + offset)

                        found_clones.append(
                            CloneBlock(
                                start_line_a=p1 + 1,
                                end_line_a=p1 + match_len,
                                start_line_b=p2 + 1,
                                end_line_b=p2 + match_len,
                                lines_count=match_len,
                            )
                        )

    # Agrupa e remove sobreposições nos clones encontrados
    dup_lines_count = len(duplicated_line_indices)
    percentage = (
        round((dup_lines_count / total_lines) * 100.0, 2) if total_lines > 0 else 0.0
    )
    return dup_lines_count, percentage, len(found_clones), found_clones


def detect_duplicates_jscpd(
    filepath: Path, min_lines: int = 4, min_tokens: int = 15
) -> tuple[int, float, int, list[CloneBlock]] | None:
    """
    Executa o jscpd via CLI se disponível no ambiente.
    Retorna None se o jscpd não puder ser executado.
    """
    # Procura jscpd ou npx
    bin_jscpd = shutil.which("jscpd")
    bin_npx = shutil.which("npx")

    if bin_jscpd:
        cmd_prefix = [bin_jscpd]
    elif bin_npx:
        cmd_prefix = [bin_npx, "--yes", "jscpd"]
    else:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = cmd_prefix + [
            "--min-lines",
            str(min_lines),
            "--min-tokens",
            str(min_tokens),
            "--reporters",
            "json",
            "--output",
            tmpdir,
            str(filepath),
        ]
        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=30,
            )
            report_file = Path(tmpdir) / "jscpd-report.json"
            if report_file.exists():
                with open(report_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                total_stats = data.get("statistics", {}).get("total", {})
                dup_lines = int(total_stats.get("duplicatedLines", 0))
                pct = float(total_stats.get("percentage", 0.0))
                clones_cnt = int(total_stats.get("clones", 0))
                clones: list[CloneBlock] = []
                for d in data.get("duplicates", []):
                    clones.append(
                        CloneBlock(
                            start_line_a=d["firstFile"]["start"],
                            end_line_a=d["firstFile"]["end"],
                            start_line_b=d["secondFile"]["start"],
                            end_line_b=d["secondFile"]["end"],
                            lines_count=d.get("lines", 0),
                        )
                    )
                return dup_lines, round(pct, 2), clones_cnt, clones
        except Exception:
            return None

    return None


def detect_duplicates(
    filepath: Path,
    code: str,
    engine: str = "auto",
    min_lines: int = 4,
    min_tokens: int = 15,
) -> tuple[int, float, int, str, list[CloneBlock]]:
    """
    Executa a ferramenta de duplicação conforme a opção:
    'auto': tenta jscpd; se falhar ou indisponível, usa fallback python nativo.
    'jscpd': força jscpd.
    'python': força detector nativo python.
    """
    if engine in ("auto", "jscpd"):
        jscpd_res = detect_duplicates_jscpd(
            filepath, min_lines=min_lines, min_tokens=min_tokens
        )
        if jscpd_res is not None:
            dup_lines, pct, clones_cnt, clones = jscpd_res
            return dup_lines, pct, clones_cnt, "jscpd", clones
        if engine == "jscpd":
            raise RuntimeError(
                "jscpd solicitado mas não encontrado/falhou na execução."
            )

    # Fallback / Python engine
    dup_lines, pct, clones_cnt, clones = detect_duplicates_python(
        code, min_lines=min_lines
    )
    return dup_lines, pct, clones_cnt, "python-cpd", clones


# ---------------------------------------------------------------------------
# Análise Completa de um Arquivo
# ---------------------------------------------------------------------------


def analyze_file(
    filepath: str | Path,
    kata: str = "",
    participant: str = "",
    treatment: str = "",
    trial_id: str = "",
    engine: str = "auto",
    min_lines: int = 4,
    min_tokens: int = 15,
) -> TrialMetrics:
    """Coleta todas as métricas estáticas para um arquivo de solução de trial."""
    path = Path(filepath).resolve()
    result = TrialMetrics(
        file=str(path),
        kata=kata or path.stem,
        participant=participant,
        treatment=treatment,
        trial_id=trial_id,
    )

    if not path.exists():
        result.status = "error"
        result.error_message = f"Arquivo não encontrado: {path}"
        return result

    try:
        code = path.read_text(encoding="utf-8")
    except Exception as exc:
        result.status = "error"
        result.error_message = f"Erro ao ler arquivo: {exc}"
        return result

    # 1. LOC Metrics (Radon raw)
    try:
        raw_data = radon_raw.analyze(code)
        result.loc = raw_data.loc
        result.sloc = raw_data.sloc
        result.lloc = raw_data.lloc
        result.comments = raw_data.comments
        result.blank = raw_data.blank
    except Exception as exc:
        result.status = "error"
        result.error_message = f"Erro na análise de LOC: {exc}"
        return result

    # 2. McCabe Cyclomatic Complexity
    try:
        (
            result.functions_count,
            result.cc_avg,
            result.cc_max,
            result.cc_min,
            result.cc_total,
            result.cc_rank,
            result.functions,
        ) = compute_cyclomatic_complexity(code)
    except Exception as exc:
        result.status = "error"
        result.error_message = f"Erro na análise de complexidade ciclomática: {exc}"
        return result

    # 3. Duplicação de Código
    try:
        (
            result.duplicated_lines,
            result.duplication_percentage,
            result.clones_count,
            result.duplication_tool,
            result.clones,
        ) = detect_duplicates(
            path,
            code,
            engine=engine,
            min_lines=min_lines,
            min_tokens=min_tokens,
        )
    except Exception as exc:
        result.status = "error"
        result.error_message = f"Erro na análise de duplicação: {exc}"
        return result

    # 4. Maintainability Index (Radon MI)
    try:
        mi_val = radon_mi.mi_visit(code, multi=True)
        result.mi = round(mi_val, 2)
        result.mi_rank = radon_mi.mi_rank(mi_val)
    except Exception as exc:
        result.status = "error"
        result.error_message = f"Erro na análise de manutenibilidade: {exc}"
        return result

    return result


# ---------------------------------------------------------------------------
# Formatação de Saída (Tabela, JSON, CSV)
# ---------------------------------------------------------------------------


def format_table(results: list[TrialMetrics]) -> str:
    """Formata os resultados como uma tabela legível em ASCII/Markdown."""
    out = io.StringIO()
    out.write("\n=== Relatório de Métricas Estáticas (Lab02 — RQ3) ===\n\n")

    headers = [
        "Arquivo / Kata",
        "LOC",
        "SLOC",
        "CC Médio",
        "CC Max",
        "Funções",
        "% Duplicada",
        "MI",
        "Rank MI",
        "Tool Dupl.",
    ]
    col_widths = [max(len(h), 22) for h in headers]
    col_widths[0] = 32

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    out.write(header_line + "\n")
    out.write(separator + "\n")

    for r in results:
        if r.status != "ok":
            row = [
                Path(r.file).name[:30],
                "ERRO",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                r.error_message[:15],
            ]
        else:
            name_display = r.kata if r.kata else Path(r.file).name
            row = [
                name_display[:30],
                str(r.loc),
                str(r.sloc),
                f"{r.cc_avg:.2f}",
                str(r.cc_max),
                str(r.functions_count),
                f"{r.duplication_percentage:.1f}%",
                f"{r.mi:.1f}",
                r.mi_rank,
                r.duplication_tool,
            ]
        out.write(
            " | ".join(row[i].ljust(col_widths[i]) for i in range(len(headers))) + "\n"
        )

    out.write("\n")
    return out.getvalue()


def format_json(results: list[TrialMetrics]) -> str:
    """Formata os resultados como JSON estruturado."""
    data = []
    for r in results:
        d = asdict(r)
        # Converte Path para str se necessário
        data.append(d)
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_csv(results: list[TrialMetrics]) -> str:
    """Formata os resultados como CSV para uso com Pandas / Wilcoxon na S03."""
    out = io.StringIO()
    fields = [
        "file",
        "kata",
        "participant",
        "treatment",
        "trial_id",
        "loc",
        "sloc",
        "lloc",
        "comments",
        "blank",
        "functions_count",
        "cc_avg",
        "cc_max",
        "cc_min",
        "cc_total",
        "cc_rank",
        "duplicated_lines",
        "duplication_percentage",
        "clones_count",
        "duplication_tool",
        "mi",
        "mi_rank",
        "status",
        "error_message",
    ]
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for r in results:
        row = {f: getattr(r, f) for f in fields}
        writer.writerow(row)
    return out.getvalue()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Coletor de Métricas Estáticas de Código para o Lab02 (Radon CC/LOC/MI + jscpd)."
    )
    parser.add_argument(
        "targets",
        nargs="+",
        help="Arquivos .py ou diretórios contendo soluções de trials a analisar.",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Formato de saída (padrão: table).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Arquivo de destino para salvar o relatório (opcional, padrão: stdout).",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "jscpd", "python"],
        default="auto",
        help="Ferramenta para detecção de duplicação (padrão: auto - tenta jscpd, fallback em python).",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=4,
        help="Mínimo de linhas para considerar bloco duplicado (padrão: 4).",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=15,
        help="Mínimo de tokens para o jscpd (padrão: 15).",
    )
    # Metadados opcionais para o trial
    parser.add_argument(
        "--participant",
        default="",
        help="Nome do participante do trial (ex: joao, marcela, gabriel).",
    )
    parser.add_argument(
        "--treatment",
        choices=["", "ai", "manual"],
        default="",
        help="Tratamento do trial: 'ai' (com Gemini 3.8 Flash) ou 'manual' (sem IA).",
    )
    parser.add_argument(
        "--kata",
        default="",
        help="Identificador do kata (ex: 01-bario-world).",
    )
    parser.add_argument(
        "--trial-id",
        default="",
        help="Identificador do trial (ex: trial-01).",
    )

    return parser.parse_args(args)


def find_python_files(targets: list[str]) -> list[Path]:
    """Coleta recursivamente todos os arquivos .py a partir dos alvos informados."""
    files: list[Path] = []
    for target in targets:
        p = Path(target)
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            for root, _, filenames in os.walk(p):
                for f in sorted(filenames):
                    if f.endswith(".py"):
                        files.append(Path(root) / f)
        else:
            # Tenta resolver glob se o shell não expandiu
            matched = list(Path(".").glob(target))
            for m in matched:
                if m.is_file() and m.suffix == ".py":
                    files.append(m)
    return sorted(dict.fromkeys(files))


def main() -> int:
    args = parse_args()
    files = find_python_files(args.targets)

    if not files:
        print(
            f"Erro: nenhum arquivo Python encontrado em: {args.targets}",
            file=sys.stderr,
        )
        return 1

    results: list[TrialMetrics] = []
    for f in files:
        res = analyze_file(
            f,
            kata=args.kata,
            participant=args.participant,
            treatment=args.treatment,
            trial_id=args.trial_id,
            engine=args.engine,
            min_lines=args.min_lines,
            min_tokens=args.min_tokens,
        )
        results.append(res)

    if args.format == "json":
        output_text = format_json(results)
    elif args.format == "csv":
        output_text = format_csv(results)
    else:
        output_text = format_table(results)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"Relatório gravado com sucesso em: {out_path}")
    else:
        print(output_text)

    # Retorna 0 se todas as análises foram ok
    return 0 if all(r.status == "ok" for r in results) else 2


if __name__ == "__main__":
    sys.exit(main())
