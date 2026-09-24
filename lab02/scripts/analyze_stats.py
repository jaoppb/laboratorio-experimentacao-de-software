#!/usr/bin/env python3
"""
analyze_stats.py — Análise Estatística dos Trials do Lab02 (Passo 4 / S03)

Lê lab02/dados/trials.csv + lab02/dados/metrics.csv, junta por trial_id e produz,
sempre recalculado a partir do estado atual dos CSVs (nunca de números fixos no
código):

1. Cobertura dos dados (quantos trials por participante/tratamento).
2. Descritivas por tratamento (mediana + IQR, preferidas a média/desvio-padrão
   dado o N reduzido, conforme lab02/docs/enunciado.md).
3. Detecção de outliers (regra de Tukey: fora de [Q1 - 1.5*IQR, Q3 + 1.5*IQR],
   calculada por tratamento).
4. Teste de Wilcoxon signed-rank (pareado por participante+kata, IA vs manual),
   consistente com o desenho within-subject — para RQ1 (tempo), RQ2 (defeitos)
   e RQ3 (métricas estáticas, com LOC como controle).

Uso:
    cd lab02
    uv run python scripts/analyze_stats.py
    uv run python scripts/analyze_stats.py --format json -o dados/analysis_summary.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from scipy import stats

lab02_dir = Path(__file__).resolve().parent.parent

# Métricas analisadas: (coluna, rótulo, RQ)
METRICS: list[tuple[str, str, str]] = [
    ("time_seconds", "Tempo até o verde (s)", "RQ1"),
    ("success_rate", "Taxa de sucesso", "RQ2"),
    ("failed_tests", "Defeitos (testes falhando)", "RQ2"),
    ("cc_avg", "Complexidade ciclomática média", "RQ3"),
    ("duplication_percentage", "% de duplicação", "RQ3"),
    ("mi", "Índice de manutenibilidade (MI)", "RQ3"),
    ("loc", "LOC (controle)", "RQ3"),
]


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Análise estatística (outliers + Wilcoxon pareado) dos trials do Lab02.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dados-dir",
        default=None,
        help="Diretório contendo trials.csv e metrics.csv (padrão: lab02/dados/).",
    )
    parser.add_argument(
        "--trials-csv",
        default="trials.csv",
        help="Nome do arquivo de trials dentro de --dados-dir (padrão: trials.csv).",
    )
    parser.add_argument(
        "--metrics-csv",
        default="metrics.csv",
        help="Nome do arquivo de métricas estáticas dentro de --dados-dir (padrão: metrics.csv).",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Formato de saída (padrão: table, legível no terminal).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Arquivo de destino para salvar o relatório (opcional, padrão: stdout).",
    )
    return parser.parse_args(args)


def iqr(s: pd.Series) -> float:
    return float(s.quantile(0.75) - s.quantile(0.25))


def load_data(dados_dir: Path, trials_name: str, metrics_name: str) -> pd.DataFrame:
    trials_path = dados_dir / trials_name
    metrics_path = dados_dir / metrics_name
    if not trials_path.exists():
        raise FileNotFoundError(f"Não encontrado: {trials_path}")
    if not metrics_path.exists():
        raise FileNotFoundError(f"Não encontrado: {metrics_path}")

    trials = pd.read_csv(trials_path)
    metrics = pd.read_csv(metrics_path)

    df = trials.merge(metrics, on="trial_id", suffixes=("", "_m"), how="left")
    df["treatment"] = df["treatment"].str.lower()
    return df


def build_coverage(df: pd.DataFrame) -> dict[str, Any]:
    counts = (
        df.groupby(["participant", "treatment"]).size().unstack(fill_value=0).to_dict(orient="index")
    )
    return {
        "por_participante": counts,
        "katas": sorted(df["kata"].dropna().unique().tolist()),
        "censurados": int((df["censored"] == True).sum()),  # noqa: E712
        "status_nao_completed": df.loc[df["status"] != "completed", "trial_id"].tolist(),
    }


def build_descriptives(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for col, label, rq in METRICS:
        if col not in df.columns:
            continue
        g = df.groupby("treatment")[col]
        rows.append(
            {
                "rq": rq,
                "metrica": label,
                "coluna": col,
                "ai_mediana": g.median().get("ai"),
                "ai_iqr": g.apply(iqr).get("ai"),
                "manual_mediana": g.median().get("manual"),
                "manual_iqr": g.apply(iqr).get("manual"),
            }
        )
    return rows


def find_outliers(df: pd.DataFrame) -> list[dict[str, Any]]:
    outliers = []
    for col, label, rq in METRICS:
        if col not in df.columns:
            continue
        for treatment, g in df.groupby("treatment"):
            s = g[col].dropna()
            if len(s) < 4:
                continue
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr_v = q3 - q1
            lo, hi = q1 - 1.5 * iqr_v, q3 + 1.5 * iqr_v
            out = g[(g[col] < lo) | (g[col] > hi)]
            for _, r in out.iterrows():
                outliers.append(
                    {
                        "rq": rq,
                        "metrica": label,
                        "tratamento": treatment,
                        "trial_id": r["trial_id"],
                        "kata": r["kata"],
                        "participant": r.get("participant", ""),
                        "valor": r[col],
                        "limite_inferior": round(lo, 2),
                        "limite_superior": round(hi, 2),
                    }
                )
    return outliers


def run_wilcoxon(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Wilcoxon signed-rank pareado por (participant, kata), AI vs manual."""
    results = []
    pivot_base = df.pivot_table(
        index=["participant", "kata"], columns="treatment", values=[c for c, _, _ in METRICS]
    )
    for col, label, rq in METRICS:
        if col not in pivot_base.columns.get_level_values(0):
            continue
        sub = pivot_base[col].dropna()
        n = len(sub)
        entry: dict[str, Any] = {"rq": rq, "metrica": label, "coluna": col, "n_pares": n}
        if n < 1 or "ai" not in sub.columns or "manual" not in sub.columns:
            entry["resultado"] = "N insuficiente / falta um dos tratamentos para parear."
            results.append(entry)
            continue
        diffs = sub["ai"] - sub["manual"]
        if (diffs == 0).all():
            entry["resultado"] = "Todas as diferenças são zero — Wilcoxon indefinido."
            results.append(entry)
            continue
        try:
            res = stats.wilcoxon(sub["ai"], sub["manual"], zero_method="wilcox")
            entry["statistic"] = round(float(res.statistic), 4)
            entry["p_value"] = round(float(res.pvalue), 4)
            entry["significativo_0.05"] = bool(res.pvalue < 0.05)
        except ValueError as e:
            entry["resultado"] = f"Wilcoxon não pôde ser calculado: {e}"
        results.append(entry)
    return results


def run_wilcoxon_per_participant(df: pd.DataFrame, col: str = "time_seconds") -> list[dict[str, Any]]:
    """Wilcoxon de RQ1 separado por participante (evita psuedo-replicação ao poolar)."""
    results = []
    for participant, g in df.groupby("participant"):
        piv = g.pivot_table(index="kata", columns="treatment", values=col).dropna()
        entry: dict[str, Any] = {"participant": participant, "n_pares": len(piv)}
        if len(piv) < 1 or "ai" not in piv.columns or "manual" not in piv.columns:
            entry["resultado"] = "N insuficiente / falta um dos tratamentos."
            results.append(entry)
            continue
        try:
            res = stats.wilcoxon(piv["ai"], piv["manual"], zero_method="wilcox")
            entry["statistic"] = round(float(res.statistic), 4)
            entry["p_value"] = round(float(res.pvalue), 4)
        except ValueError as e:
            entry["resultado"] = f"Wilcoxon não pôde ser calculado: {e}"
        results.append(entry)
    return results


def render_table(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("LAB02 — ANÁLISE ESTATÍSTICA (gerado a partir de trials.csv + metrics.csv)")
    lines.append("=" * 78)

    cov = report["cobertura"]
    lines.append("\n## 0. Cobertura dos dados\n")
    for participant, counts in cov["por_participante"].items():
        lines.append(f"  {participant}: {counts}")
    lines.append(f"  Katas: {cov['katas']}")
    lines.append(f"  Trials censuradas: {cov['censurados']}")
    if cov["status_nao_completed"]:
        lines.append(f"  Trials com status != completed: {cov['status_nao_completed']}")

    lines.append("\n## 1. Descritivas por tratamento (mediana / IQR)\n")
    desc_df = pd.DataFrame(report["descritivas"]).drop(columns=["coluna"]).round(3)
    lines.append(desc_df.to_string(index=False))

    lines.append("\n## 2. Outliers (regra de Tukey, 1.5x IQR por tratamento)\n")
    if report["outliers"]:
        for o in report["outliers"]:
            lines.append(
                f"  [{o['rq']} | {o['metrica']} | {o['tratamento']}] {o['trial_id']} "
                f"({o['kata']}, {o['participant']}): valor={o['valor']} "
                f"fora de [{o['limite_inferior']}, {o['limite_superior']}]"
            )
    else:
        lines.append("  Nenhum outlier encontrado.")

    lines.append("\n## 3. Wilcoxon signed-rank (pareado por participante+kata, IA vs manual)\n")
    for w in report["wilcoxon"]:
        base = f"  [{w['rq']}] {w['metrica']} (N pares={w['n_pares']})"
        if "resultado" in w:
            lines.append(f"{base}: {w['resultado']}")
        else:
            sig = "significativo" if w["significativo_0.05"] else "não significativo"
            lines.append(f"{base}: W={w['statistic']} | p={w['p_value']} ({sig} a alpha=0.05)")

    lines.append("\n## 4. Wilcoxon de RQ1 por participante (evita poolar observações não independentes)\n")
    for w in report["wilcoxon_rq1_por_participante"]:
        if "resultado" in w:
            lines.append(f"  {w['participant']}: {w['resultado']}")
        else:
            lines.append(
                f"  {w['participant']}: N={w['n_pares']} pares | W={w['statistic']} | p={w['p_value']}"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    dados_dir = Path(args.dados_dir).resolve() if args.dados_dir else lab02_dir / "dados"

    try:
        df = load_data(dados_dir, args.trials_csv, args.metrics_csv)
    except FileNotFoundError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1

    report = {
        "cobertura": build_coverage(df),
        "descritivas": build_descriptives(df),
        "outliers": find_outliers(df),
        "wilcoxon": run_wilcoxon(df),
        "wilcoxon_rq1_por_participante": run_wilcoxon_per_participant(df),
    }

    if args.format == "json":
        output = json.dumps(report, indent=2, ensure_ascii=False, default=str)
    else:
        output = render_table(report)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
        print(f"Relatório salvo em: {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
