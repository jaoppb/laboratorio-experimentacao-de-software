"""Análise de Sensibilidade da Classificação DORA (RQ 07 - Sprint 03).

Escopo do Integrante C (João Pedro Peres):
- RQ 07: O quanto a classificação DORA depende da definição operacional escolhida?
  * Combinações metodológicas avaliadas:
    - C1 (Referência): Deploy = Release oficial, Lead Time = Variante (a), CFR = Variante (a) [CI].
    - C2: Deploy = Release + pré-release, Lead Time = Variante (b), CFR = Variante (b) [Entrega <= 7d].
    - C3: Deploy = Git Tag, Lead Time = Variante (b), CFR = Variante (a) [CI].
  * Métricas de concordância pareada (C1 x C2, C1 x C3, C2 x C3):
    - Percentual de repositórios que mudaram de categoria DORA.
    - Direção da mudança (quantos repositórios subiram vs desceram de tier).
    - Matriz de transição / confusão entre as quatro faixas (Elite, High, Medium, Low).
    - Coeficiente Kappa de Cohen ponderado linear (pesos lineares conforme guia).
    - Coeficiente Kappa de Cohen simples (não ponderado).
  * Análise de sensibilidade individual por métrica (Deployment Frequency, Lead Time e CFR).

Gera artefatos em JSON, tabelas em Markdown e LaTeX (booktabs para o Overleaf)
e figuras em alta resolução (PNG 300 DPI e PDF vetorial).

Execução (a partir de lab03/):
    uv run python -m analises.analise_rq07
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import confusion_matrix, cohen_kappa_score

from metricas.dora import (
    DORATier,
    TIER_POINTS,
    calculate_overall_dora_score,
    classify_change_failure_rate,
    classify_deployment_frequency,
    classify_lead_time,
)

logger = logging.getLogger(__name__)

# Configurações de plotagem adequadas para artigos científicos da SBC
sns.set_theme(style="ticks", palette="deep")
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.titlesize": 13,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    }
)

DATASET_PADRAO = "dados/repositorios.csv"
OUTPUT_DIR_PADRAO = "dados/analises"

TIERS_ORDEM = [DORATier.ELITE.value, DORATier.HIGH.value, DORATier.MEDIUM.value, DORATier.LOW.value]
TIERS_CORES = {
    "Elite": "#2ca02c",   # verde
    "High": "#1f77b4",    # azul
    "Medium": "#ff7f0e",  # laranja
    "Low": "#d62728",     # vermelho
}


@dataclass
class ResultadoSensibilidadePar:
    combinacao_1: str
    combinacao_2: str
    n_repositorios: int
    n_mudaram: int
    percentual_mudanca: float
    n_subiram: int
    percentual_subiram: float
    n_desceram: int
    percentual_desceram: float
    n_iguais: int
    percentual_iguais: float
    kappa_linear: float
    interpretacao_kappa_linear: str
    kappa_simples: float
    matriz_transicao: dict[str, dict[str, int]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def interpretar_kappa_fleiss_landis(kappa: float) -> str:
    """Interpretação do coeficiente Kappa segundo Landis & Koch (1977)."""
    if np.isnan(kappa) or kappa < 0:
        return "pobre / sem concordância"
    if kappa <= 0.20:
        return "leve"
    if kappa <= 0.40:
        return "razoável"
    if kappa <= 0.60:
        return "moderada"
    if kappa <= 0.80:
        return "substancial"
    return "quase perfeita"


def avaliar_combinacao_c1(df: pd.DataFrame) -> pd.DataFrame:
    """Avalia o tier geral e de cada métrica para C1 (Referência)."""
    c1_overall = []
    c1_dep = []
    c1_lt = []
    c1_cfr = []
    c1_rec = []

    for _, r in df.iterrows():
        dep_t = r["deployment_tier"]
        lt_t = r["lead_time_tier"] if pd.notna(r["lead_time_tier"]) else None
        cfr_t = r["cfr_tier"]
        rec_t = r["recovery_tier"]

        scores = [TIER_POINTS[t] for t in (dep_t, lt_t, cfr_t, rec_t) if t is not None]
        _, overall = calculate_overall_dora_score(scores)

        c1_dep.append(dep_t)
        c1_lt.append(lt_t if lt_t else "Sem dado")
        c1_cfr.append(cfr_t)
        c1_rec.append(rec_t)
        c1_overall.append(overall.value)

    res = pd.DataFrame(
        {
            "c1_dep_tier": c1_dep,
            "c1_lt_tier": c1_lt,
            "c1_cfr_tier": c1_cfr,
            "c1_rec_tier": c1_rec,
            "c1_overall_tier": c1_overall,
        },
        index=df.index,
    )
    return res


def avaliar_combinacao_c2(df: pd.DataFrame) -> pd.DataFrame:
    """Avalia o tier geral e de cada métrica para C2 (Releases + Pré-releases, LT b, CFR b)."""
    c2_overall = []
    c2_dep = []
    c2_lt = []
    c2_cfr = []
    c2_rec = []

    for _, r in df.iterrows():
        dep_t = classify_deployment_frequency(r["c2_deployment_frequency"]).value
        lt_val = r["c2_lead_time_b_hours"] / 24.0 if pd.notna(r["c2_lead_time_b_hours"]) else None
        lt_t_obj = classify_lead_time(lt_val)
        lt_t = lt_t_obj.value if lt_t_obj is not None else None

        cfr_val = r["c2_cfr_b"] if pd.notna(r["c2_cfr_b"]) else (r["cfr_b"] if pd.notna(r["cfr_b"]) else None)
        cfr_t = classify_change_failure_rate(cfr_val).value
        rec_t = r["recovery_tier"]

        scores = [TIER_POINTS[t] for t in (dep_t, lt_t, cfr_t, rec_t) if t is not None]
        _, overall = calculate_overall_dora_score(scores)

        c2_dep.append(dep_t)
        c2_lt.append(lt_t if lt_t else "Sem dado")
        c2_cfr.append(cfr_t)
        c2_rec.append(rec_t)
        c2_overall.append(overall.value)

    res = pd.DataFrame(
        {
            "c2_dep_tier": c2_dep,
            "c2_lt_tier": c2_lt,
            "c2_cfr_tier": c2_cfr,
            "c2_rec_tier": c2_rec,
            "c2_overall_tier": c2_overall,
        },
        index=df.index,
    )
    return res


def avaliar_combinacao_c3(df: pd.DataFrame) -> pd.DataFrame:
    """Avalia o tier geral e de cada métrica para C3 (Git Tags, LT b, CFR a)."""
    c3_overall = []
    c3_dep = []
    c3_lt = []
    c3_cfr = []
    c3_rec = []

    for _, r in df.iterrows():
        dep_t = classify_deployment_frequency(r["c3_deployment_frequency"]).value
        lt_val = r["c3_lead_time_b_hours"] / 24.0 if pd.notna(r["c3_lead_time_b_hours"]) else None
        lt_t_obj = classify_lead_time(lt_val)
        lt_t = lt_t_obj.value if lt_t_obj is not None else None

        cfr_t = r["cfr_tier"]
        rec_t = r["recovery_tier"]

        scores = [TIER_POINTS[t] for t in (dep_t, lt_t, cfr_t, rec_t) if t is not None]
        _, overall = calculate_overall_dora_score(scores)

        c3_dep.append(dep_t)
        c3_lt.append(lt_t if lt_t else "Sem dado")
        c3_cfr.append(cfr_t)
        c3_rec.append(rec_t)
        c3_overall.append(overall.value)

    res = pd.DataFrame(
        {
            "c3_dep_tier": c3_dep,
            "c3_lt_tier": c3_lt,
            "c3_cfr_tier": c3_cfr,
            "c3_rec_tier": c3_rec,
            "c3_overall_tier": c3_overall,
        },
        index=df.index,
    )
    return res


def calcular_sensibilidade_par(
    serie_1: pd.Series,
    serie_2: pd.Series,
    nome_1: str,
    nome_2: str,
) -> ResultadoSensibilidadePar:
    """Calcula a transição, discordância e Kappa ponderado linear entre duas classificações."""
    n_total = len(serie_1)
    if n_total == 0:
        raise ValueError("Séries vazias para comparação")

    # Contagens de transição
    n_mudaram = int((serie_1 != serie_2).sum())
    pct_mudanca = (n_mudaram / n_total) * 100.0

    n_iguais = n_total - n_mudaram
    pct_iguais = (n_iguais / n_total) * 100.0

    # Direção da transição (usando TIER_POINTS: Elite=4, High=3, Medium=2, Low=1)
    pts_1 = serie_1.map(TIER_POINTS).astype(int)
    pts_2 = serie_2.map(TIER_POINTS).astype(int)

    n_subiram = int((pts_2 > pts_1).sum())
    pct_subiram = (n_subiram / n_total) * 100.0

    n_desceram = int((pts_2 < pts_1).sum())
    pct_desceram = (n_desceram / n_total) * 100.0

    # Kappa de Cohen ponderado linear (categorias ordinais) e simples
    ordem_labels = [DORATier.LOW.value, DORATier.MEDIUM.value, DORATier.HIGH.value, DORATier.ELITE.value]
    kappa_linear = float(cohen_kappa_score(serie_1, serie_2, labels=ordem_labels, weights="linear"))
    kappa_simples = float(cohen_kappa_score(serie_1, serie_2, labels=ordem_labels))

    # Matriz de confusão / transição
    cm = confusion_matrix(serie_1, serie_2, labels=TIERS_ORDEM)
    matriz_dict: dict[str, dict[str, int]] = {}
    for i, linha_label in enumerate(TIERS_ORDEM):
        matriz_dict[linha_label] = {}
        for j, col_label in enumerate(TIERS_ORDEM):
            matriz_dict[linha_label][col_label] = int(cm[i, j])

    return ResultadoSensibilidadePar(
        combinacao_1=nome_1,
        combinacao_2=nome_2,
        n_repositorios=n_total,
        n_mudaram=n_mudaram,
        percentual_mudanca=pct_mudanca,
        n_subiram=n_subiram,
        percentual_subiram=pct_subiram,
        n_desceram=n_desceram,
        percentual_desceram=pct_desceram,
        n_iguais=n_iguais,
        percentual_iguais=pct_iguais,
        kappa_linear=kappa_linear,
        interpretacao_kappa_linear=interpretar_kappa_fleiss_landis(kappa_linear),
        kappa_simples=kappa_simples,
        matriz_transicao=matriz_dict,
    )


def gerar_figuras_rq07(
    df_sens: pd.DataFrame,
    res_c1_c2: ResultadoSensibilidadePar,
    res_c1_c3: ResultadoSensibilidadePar,
    res_c2_c3: ResultadoSensibilidadePar,
    output_dir: Path,
) -> list[str]:
    """Gera gráficos de barras de distribuição e matrizes de transição."""
    output_dir.mkdir(parents=True, exist_ok=True)
    arquivos_gerados: list[str] = []

    # ------------------------------------------------------------------ #
    # 1. Gráfico de Barras Agrupadas: Distribuição de Tiers em C1, C2 e C3
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(TIERS_ORDEM))
    w = 0.25

    cont_c1 = df_sens["c1_overall_tier"].value_counts().reindex(TIERS_ORDEM, fill_value=0)
    cont_c2 = df_sens["c2_overall_tier"].value_counts().reindex(TIERS_ORDEM, fill_value=0)
    cont_c3 = df_sens["c3_overall_tier"].value_counts().reindex(TIERS_ORDEM, fill_value=0)

    rects1 = ax.bar(x - w, cont_c1.values, width=w, label="C1 (Referência)", color="#1f77b4", edgecolor="black", linewidth=0.5)
    rects2 = ax.bar(x, cont_c2.values, width=w, label="C2 (Pré-rel. + LT b + CFR b)", color="#ff7f0e", edgecolor="black", linewidth=0.5)
    rects3 = ax.bar(x + w, cont_c3.values, width=w, label="C3 (Tags + LT b + CFR a)", color="#2ca02c", edgecolor="black", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(TIERS_ORDEM)
    ax.set_title("RQ 07: Distribuição das Faixas DORA sob Diferentes Proxies")
    ax.set_xlabel("Classificação DORA Consolidada")
    ax.set_ylabel("Quantidade de Repositórios")
    ax.legend()

    # Anotações nas barras
    total_n = len(df_sens)
    for rects in (rects1, rects2, rects3):
        for bar in rects:
            h = bar.get_height()
            pct = (h / total_n) * 100.0
            ax.annotate(
                f"{h}\n({pct:.0f}%)",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7.5,
            )

    plt.tight_layout()
    for ext in ("png", "pdf"):
        caminho = output_dir / f"rq07_distribuicao_c1_c2_c3.{ext}"
        fig.savefig(caminho)
        arquivos_gerados.append(str(caminho))
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # 2. Painel com as Três Matrizes de Transição / Confusão
    # ------------------------------------------------------------------ #
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    pares_plot = [
        (res_c1_c2, "C1 (Ref.) → C2", axes[0]),
        (res_c1_c3, "C1 (Ref.) → C3 (Tags)", axes[1]),
        (res_c2_c3, "C2 → C3 (Tags)", axes[2]),
    ]

    for res_par, titulo, ax_p in pares_plot:
        # Converter matriz em DataFrame
        mat_df = pd.DataFrame(res_par.matriz_transicao).T[TIERS_ORDEM]
        sns.heatmap(
            mat_df,
            annot=True,
            fmt="d",
            cmap="Blues",
            cbar=False,
            ax=ax_p,
            linewidths=0.5,
            linecolor="#ddd",
        )
        ax_p.set_title(f"{titulo}\n(Mudança: {res_par.percentual_mudanca:.1f}% | $\\kappa_{{lin}} = {res_par.kappa_linear:.3f}$)")
        ax_p.set_xlabel("Classificação Destino")
        ax_p.set_ylabel("Classificação Origem")

    plt.tight_layout()
    for ext in ("png", "pdf"):
        caminho = output_dir / f"rq07_painel_transicoes.{ext}"
        fig.savefig(caminho)
        arquivos_gerados.append(str(caminho))
    plt.close(fig)

    return arquivos_gerados


def exportar_tabelas_rq07(
    df_sens: pd.DataFrame,
    resultados_pares: list[ResultadoSensibilidadePar],
    output_dir: Path,
) -> tuple[Path, Path, Path, Path]:
    """Exporta tabelas formatadas de sensibilidade DORA em Markdown e LaTeX."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 1. Tabela de Concordância Pareada e Mudança (Markdown e LaTeX)
    # ------------------------------------------------------------------ #
    md_pares = [
        "# Tabela RQ 07: Análise de Sensibilidade DORA entre Combinações",
        "",
        "| Comparação | Repositórios | Mudaram de Tier | % Mudança | Subiram de Tier | Desceram de Tier | Kappa Linear | Interpretação |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for p in resultados_pares:
        md_pares.append(
            f"| {p.combinacao_1} × {p.combinacao_2} | {p.n_repositorios} | "
            f"{p.n_mudaram} | {p.percentual_mudanca:.1f}% | "
            f"{p.n_subiram} ({p.percentual_subiram:.1f}%) | "
            f"{p.n_desceram} ({p.percentual_desceram:.1f}%) | "
            f"{p.kappa_linear:.4f} | {p.interpretacao_kappa_linear} |"
        )
    md_path_pares = output_dir / "tabela_rq07_sensibilidade.md"
    md_path_pares.write_text("\n".join(md_pares), encoding="utf-8")

    tex_pares = [
        "% Tabela gerada automaticamente por analises/analise_rq07.py",
        "\\begin{table}[ht]",
        "\\centering",
        "\\caption{Sensibilidade da classificação DORA geral entre as combinações C1, C2 e C3 (RQ 07).}",
        "\\label{tab:rq07_sensibilidade}",
        "\\small",
        "\\begin{tabular}{lcccccc}",
        "\\toprule",
        "\\textbf{Par Comparado} & \\textbf{$n$} & \\textbf{Mudaram (\\%)} & \\textbf{Subiram} & \\textbf{Desceram} & \\textbf{Kappa Linear ($\\kappa$)} & \\textbf{Concordância} \\\\",
        "\\midrule",
    ]
    for p in resultados_pares:
        tex_pares.append(
            f"{p.combinacao_1} $\\times$ {p.combinacao_2} & {p.n_repositorios} & "
            f"{p.n_mudaram} ({p.percentual_mudanca:.1f}\\%) & "
            f"{p.n_subiram} & {p.n_desceram} & "
            f"{p.kappa_linear:.3f} & {p.interpretacao_kappa_linear} \\\\"
        )
    tex_pares.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    tex_path_pares = output_dir / "tabela_rq07_sensibilidade.tex"
    tex_path_pares.write_text("\n".join(tex_pares), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # 2. Tabela de Distribuição dos Tiers por Combinação
    # ------------------------------------------------------------------ #
    n_tot = len(df_sens)
    c1_c = df_sens["c1_overall_tier"].value_counts().reindex(TIERS_ORDEM, fill_value=0)
    c2_c = df_sens["c2_overall_tier"].value_counts().reindex(TIERS_ORDEM, fill_value=0)
    c3_c = df_sens["c3_overall_tier"].value_counts().reindex(TIERS_ORDEM, fill_value=0)

    md_dist = [
        "# Tabela RQ 07: Distribuição de Tiers DORA por Definição Operacional",
        "",
        "| Faixa DORA | C1 (Referência) | C2 (Releases + Pré) | C3 (Tags) |",
        "|---|---:|---:|---:|",
    ]
    for t in TIERS_ORDEM:
        md_dist.append(
            f"| **{t}** | {c1_c[t]} ({(c1_c[t]/n_tot)*100:.1f}%) | "
            f"{c2_c[t]} ({(c2_c[t]/n_tot)*100:.1f}%) | "
            f"{c3_c[t]} ({(c3_c[t]/n_tot)*100:.1f}%) |"
        )
    md_path_dist = output_dir / "tabela_rq07_distribuicao_tiers.md"
    md_path_dist.write_text("\n".join(md_dist), encoding="utf-8")

    tex_dist = [
        "% Tabela gerada automaticamente por analises/analise_rq07.py",
        "\\begin{table}[ht]",
        "\\centering",
        "\\caption{Distribuição dos repositórios nas categorias DORA por combinação de proxies.}",
        "\\label{tab:rq07_distribuicao_tiers}",
        "\\small",
        "\\begin{tabular}{lccc}",
        "\\toprule",
        "\\textbf{Faixa DORA} & \\textbf{C1 (Referência)} & \\textbf{C2 (Pré-releases)} & \\textbf{C3 (Git Tags)} \\\\",
        "\\midrule",
    ]
    for t in TIERS_ORDEM:
        tex_dist.append(
            f"\\textbf{{{t}}} & {c1_c[t]} ({(c1_c[t]/n_tot)*100:.1f}\\%) & "
            f"{c2_c[t]} ({(c2_c[t]/n_tot)*100:.1f}\\%) & "
            f"{c3_c[t]} ({(c3_c[t]/n_tot)*100:.1f}\\%) \\\\"
        )
    tex_dist.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    tex_path_dist = output_dir / "tabela_rq07_distribuicao_tiers.tex"
    tex_path_dist.write_text("\n".join(tex_dist), encoding="utf-8")

    return md_path_pares, tex_path_pares, md_path_dist, tex_path_dist


def executar_analise_rq07(
    dataset_path: Path | str = DATASET_PADRAO,
    output_dir: Path | str = OUTPUT_DIR_PADRAO,
) -> dict[str, Any]:
    """Executa a análise de sensibilidade da RQ 07 de ponta a ponta."""
    dataset_file = Path(dataset_path)
    out_dir = Path(output_dir)
    figuras_dir = out_dir / "figuras"

    logger.info("Carregando dataset de repositórios: %s", dataset_file)
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {dataset_file}")

    df = pd.read_csv(dataset_file)

    # 1. Avaliação individual dos 330 repositórios em C1, C2 e C3
    df_c1 = avaliar_combinacao_c1(df)
    df_c2 = avaliar_combinacao_c2(df)
    df_c3 = avaliar_combinacao_c3(df)

    df_sens = pd.concat([df_c1, df_c2, df_c3], axis=1)

    # 2. Avaliação pareada entre as combinações
    res_c1_c2 = calcular_sensibilidade_par(
        serie_1=df_sens["c1_overall_tier"],
        serie_2=df_sens["c2_overall_tier"],
        nome_1="C1 (Referência)",
        nome_2="C2 (Pré-rel. + LT b + CFR b)",
    )
    res_c1_c3 = calcular_sensibilidade_par(
        serie_1=df_sens["c1_overall_tier"],
        serie_2=df_sens["c3_overall_tier"],
        nome_1="C1 (Referência)",
        nome_2="C3 (Tags + LT b + CFR a)",
    )
    res_c2_c3 = calcular_sensibilidade_par(
        serie_1=df_sens["c2_overall_tier"],
        serie_2=df_sens["c3_overall_tier"],
        nome_1="C2 (Pré-rel.)",
        nome_2="C3 (Tags)",
    )

    lista_pares = [res_c1_c2, res_c1_c3, res_c2_c3]

    # 3. Geração de Gráficos e Exportação de Tabelas
    figs = gerar_figuras_rq07(df_sens, res_c1_c2, res_c1_c3, res_c2_c3, figuras_dir)
    exportar_tabelas_rq07(df_sens, lista_pares, out_dir)

    # 4. Exportação JSON consolidada
    json_path = out_dir / "rq07_sensibilidade.json"
    resultado_json = {
        "n_repositorios": len(df_sens),
        "distribuicao_tiers": {
            "C1": df_sens["c1_overall_tier"].value_counts().to_dict(),
            "C2": df_sens["c2_overall_tier"].value_counts().to_dict(),
            "C3": df_sens["c3_overall_tier"].value_counts().to_dict(),
        },
        "comparacoes_pares": [p.to_dict() for p in lista_pares],
        "figuras": figs,
    }
    json_path.write_text(json.dumps(resultado_json, indent=2, ensure_ascii=False), encoding="utf-8")

    return resultado_json


def main(argv: list[str] | None = None) -> int:
    """CLI para execução da análise de sensibilidade da RQ 07."""
    parser = argparse.ArgumentParser(
        description="Executa a análise de sensibilidade DORA (RQ 07 - Sprint 03 - João Pedro Peres)"
    )
    parser.add_argument("--dataset", type=Path, default=Path(DATASET_PADRAO), help="Caminho do repositorios.csv")
    parser.add_argument("--output-dir", type=Path, default=Path(OUTPUT_DIR_PADRAO), help="Diretório de saída")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        res = executar_analise_rq07(dataset_path=args.dataset, output_dir=args.output_dir)

        print("\n" + "=" * 65)
        print("RESUMO DA ANÁLISE DE SENSIBILIDADE DORA (RQ 07)")
        print("=" * 65)
        print(f"Total de repositórios avaliados: {res['n_repositorios']}")
        print("\nDistribuição de Categorias por Definição:")
        for comb, dist in res["distribuicao_tiers"].items():
            print(f"  {comb:4}: {dist}")

        print("\nConcordância Pareada e Mudança de Faixa:")
        for p in res["comparacoes_pares"]:
            print(
                f"  [{p['combinacao_1']} x {p['combinacao_2']}]\n"
                f"    - Repositórios com mudança de tier: {p['n_mudaram']}/{res['n_repositorios']} ({p['percentual_mudanca']:.1f}%)\n"
                f"    - Subiram: {p['n_subiram']} ({p['percentual_subiram']:.1f}%) | Desceram: {p['n_desceram']} ({p['percentual_desceram']:.1f}%)\n"
                f"    - Kappa Linear (Cohen): {p['kappa_linear']:.4f} ({p['interpretacao_kappa_linear']})\n"
                f"    - Kappa Simples: {p['kappa_simples']:.4f}"
            )

        print("\n[*] Artefatos salvos em:")
        print(f"  - JSON: {args.output_dir / 'rq07_sensibilidade.json'}")
        print(f"  - Tabelas LaTeX: {args.output_dir / 'tabela_rq07_sensibilidade.tex'} e {args.output_dir / 'tabela_rq07_distribuicao_tiers.tex'}")
        print(f"  - Tabelas Markdown: {args.output_dir / 'tabela_rq07_sensibilidade.md'} e {args.output_dir / 'tabela_rq07_distribuicao_tiers.md'}")
        print(f"  - Figuras: {len(res['figuras'])} arquivos em {args.output_dir / 'figuras'}")
        return 0
    except Exception as exc:
        logger.exception("Falha ao executar análise da RQ 07: %s", exc)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
