"""Análise empírica das RQ 05 e RQ 06 (Sprint 03).

Escopo do Integrante B (Gabriel Assis de Souza):
- RQ 05: Correlação de Spearman entre Frequência de Deploy e CFR:
  * Variante (a): Proxy de CI (deployment_frequency vs cfr_a).
  * Variante (b): Proxy de Entrega (deployment_frequency vs cfr_b).
  * Gráficos de dispersão em escala logarítmica com curvas de regressão/tendência.
- RQ 06: Características dos repositórios associadas ao desempenho DORA:
  * Fatores: Popularidade (estrelas em quartis), Tamanho da equipe (contribuidores em quartis),
    Maturidade (idade em quartis), Linguagem principal e Tipo de projeto.
  * Testes não paramétricos: Kruskal-Wallis (múltiplos grupos) e Mann-Whitney (comparações pareadas).
  * Ajuste para comparações múltiplas via método de Holm (FWER = 0.05).
  * Tamanho de efeito: Epsilon-quadrado (ε² para Kruskal-Wallis) e Cliff's delta (δ para Mann-Whitney).
  * Heatmap de tamanho de efeito e boxplots por subgrupos.

Gera artefatos em JSON, tabelas em Markdown e LaTeX (booktabs para o Overleaf)
e figuras em alta resolução (PNG 300 DPI e PDF vetorial).

Execução (a partir de lab03/):
    uv run python -m analises.analise_rq05_rq06
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
import scipy.stats as stats
import seaborn as sns
from statsmodels.stats.multitest import multipletests

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
TIPO_PROJETO_PADRAO = "dados/tipo_projeto_agentes.csv"
OUTPUT_DIR_PADRAO = "dados/analises"
DATA_FIM_JANELA = "2026-09-30T23:59:59Z"

METRICAS_DORA_RQ06 = [
    ("deployment_frequency", "Freq. Deploy (rel/sem)"),
    ("lead_time_b_hours", "Lead Time (b) (horas)"),
    ("cfr_a", "CFR (a) CI (%)"),
    ("cfr_b", "CFR (b) Entrega (%)"),
    ("recovery_hours", "Tempo Recuperação (horas)"),
]

FATORES_RQ06 = [
    ("quartil_estrelas", "Popularidade (Estrelas)"),
    ("quartil_contribuidores", "Equipe (Contribuidores)"),
    ("quartil_idade", "Maturidade (Idade do Projeto)"),
    ("linguagem_grupo", "Linguagem Principal"),
    ("tipo_projeto", "Tipo de Projeto"),
]


@dataclass
class ResultadoSpearman:
    id_rq: str
    nome_x: str
    nome_y: str
    descricao: str
    n_pares: int
    rho: float
    p_valor: float
    significativo_05: bool
    interpretacao: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResultadoKruskal:
    fator: str
    nome_fator: str
    metrica: str
    nome_metrica: str
    k_grupos: int
    n_total: int
    h_stat: float
    p_valor: float
    p_valor_holm: float
    significativo_raw: bool
    significativo_holm: bool
    epsilon_squared: float
    interpretacao_efeito: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResultadoComparacaoPareada:
    fator: str
    grupo1: str
    grupo2: str
    metrica: str
    nome_metrica: str
    n1: int
    n2: int
    u_stat: float
    p_valor: float
    p_valor_holm: float
    significativo_raw: bool
    significativo_holm: bool
    cliffs_delta: float
    interpretacao_efeito: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def interpretar_spearman(rho: float) -> str:
    """Interpreta magnitude e sentido da correlação de Spearman."""
    abs_r = abs(rho)
    if abs_r < 0.10:
        forca = "desprezível / ausência de correlação"
    elif abs_r < 0.30:
        forca = "fraca"
    elif abs_r < 0.50:
        forca = "moderada"
    elif abs_r < 0.70:
        forca = "forte"
    else:
        forca = "muito forte"
    sentido = "positiva (direta)" if rho > 0 else "negativa (inversa)"
    return f"{forca} {sentido}"


def interpretar_epsilon_squared(eps2: float) -> str:
    """Interpreta tamanho de efeito Epsilon-quadrado para Kruskal-Wallis."""
    if np.isnan(eps2) or eps2 < 0.01:
        return "desprezível"
    if eps2 < 0.06:
        return "pequeno"
    if eps2 < 0.14:
        return "médio"
    return "grande"


def interpretar_cliffs_delta(delta: float) -> str:
    """Interpreta tamanho de efeito Cliff's delta (Romano et al., 2006)."""
    if np.isnan(delta):
        return "indefinido"
    abs_d = abs(delta)
    if abs_d < 0.147:
        return "desprezível"
    if abs_d < 0.33:
        return "pequeno"
    if abs_d < 0.474:
        return "médio"
    return "grande"


def calcular_spearman(
    serie_x: pd.Series,
    serie_y: pd.Series,
    id_rq: str,
    nome_x: str,
    nome_y: str,
    descricao: str,
) -> ResultadoSpearman:
    """Calcula a correlação de Spearman entre duas variáveis com remoção pareada de NaNs."""
    df_par = pd.DataFrame({"x": serie_x, "y": serie_y}).dropna().astype(float)
    n = len(df_par)
    if n < 3:
        return ResultadoSpearman(
            id_rq=id_rq,
            nome_x=nome_x,
            nome_y=nome_y,
            descricao=descricao,
            n_pares=n,
            rho=float("nan"),
            p_valor=float("nan"),
            significativo_05=False,
            interpretacao="dados insuficientes",
        )

    res = stats.spearmanr(df_par["x"], df_par["y"])
    rho = float(res.statistic)
    p_val = float(res.pvalue)

    return ResultadoSpearman(
        id_rq=id_rq,
        nome_x=nome_x,
        nome_y=nome_y,
        descricao=descricao,
        n_pares=n,
        rho=rho,
        p_valor=p_val,
        significativo_05=bool(p_val < 0.05),
        interpretacao=interpretar_spearman(rho),
    )


def preparar_fatores(df: pd.DataFrame, df_tipo: pd.DataFrame | None = None) -> pd.DataFrame:
    """Prepara variáveis explicativas e subgrupos da amostra para a RQ 06."""
    df_proc = df.copy()

    # Integrar tipo do projeto se fornecido
    if df_tipo is not None and "tipo_projeto" in df_tipo.columns:
        if "tipo_projeto" in df_proc.columns:
            df_proc = df_proc.drop(columns=["tipo_projeto"])
        df_proc = df_proc.merge(df_tipo[["full_name", "tipo_projeto"]], on="full_name", how="left")
    elif "tipo_projeto" not in df_proc.columns:
        df_proc["tipo_projeto"] = "não rotulado"

    # Idade do projeto em anos no término da janela de observação
    ref_dt = pd.to_datetime(DATA_FIM_JANELA)
    created_dt = pd.to_datetime(df_proc["created_at"])
    df_proc["idade_anos"] = (ref_dt - created_dt).dt.total_seconds() / (365.25 * 86400.0)

    # 1. Quartis de Estrelas (Popularidade)
    try:
        df_proc["quartil_estrelas"] = pd.qcut(
            df_proc["stars"], q=4, labels=["Q1 (menor)", "Q2 (médio-baixo)", "Q3 (médio-alto)", "Q4 (maior)"]
        )
    except Exception:
        df_proc["quartil_estrelas"] = pd.cut(df_proc["stars"], bins=4)

    # 2. Quartis de Contribuidores (Tamanho da Equipe)
    try:
        df_proc["quartil_contribuidores"] = pd.qcut(
            df_proc["contributors_count"], q=4, labels=["Q1 (menor)", "Q2 (médio-baixo)", "Q3 (médio-alto)", "Q4 (maior)"]
        )
    except Exception:
        df_proc["quartil_contribuidores"] = pd.cut(df_proc["contributors_count"], bins=4)

    # 3. Quartis de Idade (Maturidade)
    try:
        df_proc["quartil_idade"] = pd.qcut(
            df_proc["idade_anos"], q=4, labels=["Q1 (mais novo)", "Q2 (jovem)", "Q3 (maduro)", "Q4 (mais antigo)"]
        )
    except Exception:
        df_proc["quartil_idade"] = pd.cut(df_proc["idade_anos"], bins=4)

    # 4. Agrupamento de Linguagem Principal (Top 6 linguagens + Outras)
    top_langs = df_proc["language"].value_counts().head(6).index.tolist()
    df_proc["linguagem_grupo"] = df_proc["language"].apply(lambda l: l if l in top_langs else "Outras")

    return df_proc


def calcular_cliffs_delta(x: np.ndarray, y: np.ndarray) -> tuple[float, str]:
    """Calcula o tamanho de efeito Cliff's delta (Romano et al., 2006)."""
    n1 = len(x)
    n2 = len(y)
    if n1 == 0 or n2 == 0:
        return float("nan"), "indefinido"

    res = stats.mannwhitneyu(x, y, alternative="two-sided")
    u1 = float(res.statistic)
    delta = (2.0 * u1) / (n1 * n2) - 1.0
    return delta, interpretar_cliffs_delta(delta)


def executar_kruskal(
    df: pd.DataFrame,
    fator: str,
    nome_fator: str,
    metrica: str,
    nome_metrica: str,
) -> ResultadoKruskal:
    """Executa o teste de Kruskal-Wallis e calcula o Epsilon-quadrado (ε²)."""
    subgrupos = []
    for _, g in df.groupby(fator, observed=True):
        valores = g[metrica].dropna().astype(float).values
        if len(valores) > 0:
            subgrupos.append(valores)

    k = len(subgrupos)
    n_total = sum(len(g) for g in subgrupos)

    if k < 2 or n_total <= k:
        return ResultadoKruskal(
            fator=fator,
            nome_fator=nome_fator,
            metrica=metrica,
            nome_metrica=nome_metrica,
            k_grupos=k,
            n_total=n_total,
            h_stat=float("nan"),
            p_valor=float("nan"),
            p_valor_holm=float("nan"),
            significativo_raw=False,
            significativo_holm=False,
            epsilon_squared=float("nan"),
            interpretacao_efeito="dados insuficientes",
        )

    res = stats.kruskal(*subgrupos)
    h_stat = float(res.statistic)
    p_val = float(res.pvalue)
    eps2 = h_stat / (n_total - 1) if n_total > 1 else float("nan")

    return ResultadoKruskal(
        fator=fator,
        nome_fator=nome_fator,
        metrica=metrica,
        nome_metrica=nome_metrica,
        k_grupos=k,
        n_total=n_total,
        h_stat=h_stat,
        p_valor=p_val,
        p_valor_holm=p_val,  # atualizado posteriormente no multipletests
        significativo_raw=bool(p_val < 0.05),
        significativo_holm=False,
        epsilon_squared=eps2,
        interpretacao_efeito=interpretar_epsilon_squared(eps2),
    )


def executar_comparacoes_pareadas(
    df: pd.DataFrame,
    fator: str,
    pares: list[tuple[str, str]],
    metrica: str,
    nome_metrica: str,
) -> list[ResultadoComparacaoPareada]:
    """Executa comparações pareadas via Mann-Whitney U e Cliff's Delta para pares de subgrupos."""
    resultados: list[ResultadoComparacaoPareada] = []
    for g1_nome, g2_nome in pares:
        g1 = df[df[fator] == g1_nome][metrica].dropna().astype(float).values
        g2 = df[df[fator] == g2_nome][metrica].dropna().astype(float).values
        n1 = len(g1)
        n2 = len(g2)
        if n1 < 2 or n2 < 2:
            continue

        res_mw = stats.mannwhitneyu(g1, g2, alternative="two-sided")
        u_val = float(res_mw.statistic)
        p_val = float(res_mw.pvalue)
        delta, interp = calcular_cliffs_delta(g1, g2)

        resultados.append(
            ResultadoComparacaoPareada(
                fator=fator,
                grupo1=str(g1_nome),
                grupo2=str(g2_nome),
                metrica=metrica,
                nome_metrica=nome_metrica,
                n1=n1,
                n2=n2,
                u_stat=u_val,
                p_valor=p_val,
                p_valor_holm=p_val,
                significativo_raw=bool(p_val < 0.05),
                significativo_holm=False,
                cliffs_delta=delta,
                interpretacao_efeito=interp,
            )
        )
    return resultados


def aplicar_correcao_holm_kruskal(resultados: list[ResultadoKruskal]) -> list[ResultadoKruskal]:
    """Aplica a correção de Holm-Bonferroni para comparações múltiplas em resultados de Kruskal."""
    p_vals = [r.p_valor for r in resultados]
    valid_mask = [not np.isnan(p) for p in p_vals]
    p_validos = [p for p, v in zip(p_vals, valid_mask) if v]

    if len(p_validos) > 0:
        rejeita, p_corrigidos, _, _ = multipletests(p_validos, method="holm")
        idx_val = 0
        for r, is_val in zip(resultados, valid_mask):
            if is_val:
                p_adj = float(p_corrigidos[idx_val])
                r.p_valor_holm = p_adj
                r.significativo_holm = bool(rejeita[idx_val])
                idx_val += 1
    return resultados


def aplicar_correcao_holm_pareadas(resultados: list[ResultadoComparacaoPareada]) -> list[ResultadoComparacaoPareada]:
    """Aplica a correção de Holm-Bonferroni nas comparações pareadas."""
    p_vals = [r.p_valor for r in resultados]
    valid_mask = [not np.isnan(p) for p in p_vals]
    p_validos = [p for p, v in zip(p_vals, valid_mask) if v]

    if len(p_validos) > 0:
        rejeita, p_corrigidos, _, _ = multipletests(p_validos, method="holm")
        idx_val = 0
        for r, is_val in zip(resultados, valid_mask):
            if is_val:
                p_adj = float(p_corrigidos[idx_val])
                r.p_valor_holm = p_adj
                r.significativo_holm = bool(rejeita[idx_val])
                idx_val += 1
    return resultados


def gerar_graficos_rq05(
    df: pd.DataFrame,
    res_a: ResultadoSpearman,
    res_b: ResultadoSpearman,
    output_dir: Path,
) -> list[str]:
    """Gera figuras de dispersão para a RQ 05 com escala log e anotações estatísticas."""
    output_dir.mkdir(parents=True, exist_ok=True)
    arquivos_gerados: list[str] = []

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    # Painel 1: Deployment Frequency vs CFR (a) CI
    df_a = df[["deployment_frequency", "cfr_a"]].dropna().copy()
    df_a["cfr_a_pct"] = df_a["cfr_a"] * 100.0
    sns.regplot(
        data=df_a,
        x="deployment_frequency",
        y="cfr_a_pct",
        ax=ax1,
        color="#1f77b4",
        scatter_kws={"alpha": 0.5, "s": 25},
        line_kws={"color": "#d62728", "linewidth": 1.5},
        logx=True,
    )
    ax1.set_xscale("log")
    ax1.set_title("RQ 05: Freq. Deploy vs CFR (a) [CI]")
    ax1.set_xlabel("Frequência de Deploy (releases/semana, escala log)")
    ax1.set_ylabel("CFR (a) — Proxy de CI (%)")
    texto_a = f"Spearman $\\rho = {res_a.rho:.3f}$\n$p = {res_a.p_valor:.4f}$\n$n = {res_a.n_pares}$"
    ax1.text(
        0.05,
        0.92,
        texto_a,
        transform=ax1.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.85, edgecolor="#ccc"),
    )

    # Painel 2: Deployment Frequency vs CFR (b) Entrega
    df_b = df[["deployment_frequency", "cfr_b"]].dropna().copy()
    df_b["cfr_b_pct"] = df_b["cfr_b"] * 100.0
    sns.regplot(
        data=df_b,
        x="deployment_frequency",
        y="cfr_b_pct",
        ax=ax2,
        color="#ff7f0e",
        scatter_kws={"alpha": 0.5, "s": 25},
        line_kws={"color": "#d62728", "linewidth": 1.5},
        logx=True,
    )
    ax2.set_xscale("log")
    ax2.set_title("RQ 05: Freq. Deploy vs CFR (b) [Entrega]")
    ax2.set_xlabel("Frequência de Deploy (releases/semana, escala log)")
    ax2.set_ylabel("CFR (b) — Releases Corretivas <= 7 dias (%)")
    texto_b = f"Spearman $\\rho = {res_b.rho:.3f}$\n$p = {res_b.p_valor:.1e}$\n$n = {res_b.n_pares}$"
    ax2.text(
        0.05,
        0.92,
        texto_b,
        transform=ax2.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", alpha=0.85, edgecolor="#ccc"),
    )

    plt.tight_layout()
    for ext in ("png", "pdf"):
        caminho = output_dir / f"rq05_spearman_dispersao.{ext}"
        fig.savefig(caminho)
        arquivos_gerados.append(str(caminho))
    plt.close(fig)

    return arquivos_gerados


def gerar_graficos_rq06(
    df: pd.DataFrame,
    resultados_kruskal: list[ResultadoKruskal],
    output_dir: Path,
) -> list[str]:
    """Gera visualizações estatísticas da RQ 06 (Heatmap de ε² e Boxplots dos fatores mais relevantes)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    arquivos_gerados: list[str] = []

    # 1. Heatmap de Tamanho de Efeito (Epsilon-quadrado)
    matriz_eps: dict[str, dict[str, float]] = {}
    for r in resultados_kruskal:
        if r.nome_fator not in matriz_eps:
            matriz_eps[r.nome_fator] = {}
        matriz_eps[r.nome_fator][r.nome_metrica] = r.epsilon_squared

    df_heatmap = pd.DataFrame(matriz_eps).T

    fig, ax = plt.subplots(figsize=(9, 4.2))
    sns.heatmap(
        df_heatmap,
        annot=True,
        fmt=".3f",
        cmap="YlGnBu",
        cbar_kws={"label": "Tamanho de Efeito ($\\epsilon^2$)"},
        ax=ax,
        linewidths=0.5,
        linecolor="#eee",
    )
    ax.set_title("RQ 06: Tamanho de Efeito ($\\epsilon^2$) por Fator $\\times$ Métrica DORA")
    ax.set_xlabel("Métrica DORA")
    ax.set_ylabel("Fator / Característica")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()

    for ext in ("png", "pdf"):
        caminho = output_dir / f"rq06_heatmap_efeitos.{ext}"
        fig.savefig(caminho)
        arquivos_gerados.append(str(caminho))
    plt.close(fig)

    # 2. Painel de Boxplots: Lead Time (b) e Freq. Deploy por Idade e Contribuidores
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    # (a) Idade vs Lead Time (b)
    sns.boxplot(
        data=df,
        x="quartil_idade",
        y="lead_time_b_hours",
        hue="quartil_idade",
        legend=False,
        ax=axes[0, 0],
        palette="Blues",
        log_scale=True,
    )
    axes[0, 0].set_title("Idade do Projeto vs Lead Time (b)")
    axes[0, 0].set_xlabel("Quartil de Idade")
    axes[0, 0].set_ylabel("Lead Time (b) [horas, log]")

    # (b) Contribuidores vs Lead Time (b)
    sns.boxplot(
        data=df,
        x="quartil_contribuidores",
        y="lead_time_b_hours",
        hue="quartil_contribuidores",
        legend=False,
        ax=axes[0, 1],
        palette="Greens",
        log_scale=True,
    )
    axes[0, 1].set_title("Tamanho da Equipe vs Lead Time (b)")
    axes[0, 1].set_xlabel("Quartil de Contribuidores")
    axes[0, 1].set_ylabel("Lead Time (b) [horas, log]")

    # (c) Idade vs Frequência de Deploy
    sns.boxplot(
        data=df,
        x="quartil_idade",
        y="deployment_frequency",
        hue="quartil_idade",
        legend=False,
        ax=axes[1, 0],
        palette="Oranges",
        log_scale=True,
    )
    axes[1, 0].set_title("Idade do Projeto vs Frequência de Deploy")
    axes[1, 0].set_xlabel("Quartil de Idade")
    axes[1, 0].set_ylabel("Freq. Deploy [rel/sem, log]")

    # (d) Tipo de Projeto vs Lead Time (b)
    df_tp = df[df["tipo_projeto"].isin(["aplicação/serviço", "biblioteca/framework", "ferramenta CLI"])]
    sns.boxplot(
        data=df_tp,
        x="tipo_projeto",
        y="lead_time_b_hours",
        hue="tipo_projeto",
        legend=False,
        ax=axes[1, 1],
        palette="Purples",
        log_scale=True,
    )
    axes[1, 1].set_title("Tipo de Projeto vs Lead Time (b)")
    axes[1, 1].set_xlabel("Tipo de Projeto")
    axes[1, 1].set_ylabel("Lead Time (b) [horas, log]")

    plt.tight_layout()
    for ext in ("png", "pdf"):
        caminho = output_dir / f"rq06_fatores_boxplots.{ext}"
        fig.savefig(caminho)
        arquivos_gerados.append(str(caminho))
    plt.close(fig)

    return arquivos_gerados


def exportar_tabelas_rq05_rq06(
    spearman_results: list[ResultadoSpearman],
    kruskal_results: list[ResultadoKruskal],
    pareadas_results: list[ResultadoComparacaoPareada],
    output_dir: Path,
) -> tuple[Path, Path, Path, Path]:
    """Exporta tabelas formatadas em Markdown e LaTeX para o Overleaf."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 1. Tabela RQ 05 (Spearman) - Markdown e LaTeX
    # ------------------------------------------------------------------ #
    md_spearman = [
        "# Tabela RQ 05: Correlações de Spearman (Frequência de Deploy vs CFR)",
        "",
        "| ID | Relação Avaliada | n | Spearman (ρ) | p-valor bruto | Significativo (α=0.05) | Interpretação |",
        "|---|---|---:|---:|---:|:---:|---|",
    ]
    for s in spearman_results:
        sig = "Sim" if s.significativo_05 else "Não"
        md_spearman.append(
            f"| {s.id_rq} | {s.descricao} | {s.n_pares} | {s.rho:.4f} | {s.p_valor:.4e} | {sig} | {s.interpretacao} |"
        )
    md_path_sp = output_dir / "tabela_rq05_spearman.md"
    md_path_sp.write_text("\n".join(md_spearman), encoding="utf-8")

    tex_spearman = [
        "% Tabela gerada automaticamente por analises/analise_rq05_rq06.py",
        "\\begin{table}[ht]",
        "\\centering",
        "\\caption{Correlação de Spearman ($\\rho$) entre Frequência de Deploy e Taxas de Falha (RQ 05).}",
        "\\label{tab:rq05_spearman}",
        "\\small",
        "\\begin{tabular}{llcccc}",
        "\\toprule",
        "\\textbf{Variante} & \\textbf{Proxy de Falha} & \\textbf{n} & \\textbf{Spearman ($\\rho$)} & \\textbf{$p$-valor} & \\textbf{Interpretação} \\\\",
        "\\midrule",
    ]
    for s in spearman_results:
        desc_escapada = s.descricao.replace("%", "\\%").replace("_", "\\_")
        tex_spearman.append(
            f"{s.id_rq} & {desc_escapada} & {s.n_pares} & {s.rho:.3f} & {s.p_valor:.3e} & {s.interpretacao} \\\\"
        )
    tex_spearman.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    tex_path_sp = output_dir / "tabela_rq05_spearman.tex"
    tex_path_sp.write_text("\n".join(tex_spearman), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # 2. Tabela RQ 06 (Kruskal-Wallis) - Markdown e LaTeX
    # ------------------------------------------------------------------ #
    md_kruskal = [
        "# Tabela RQ 06: Testes de Kruskal-Wallis com Correção de Holm",
        "",
        "| Fator | Métrica DORA | k | n | H | p-valor bruto | p-valor (Holm) | ε² | Tamanho do Efeito | Rejeita H0 (Holm) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|:---:|",
    ]
    for k in kruskal_results:
        rej = "Sim (*)" if k.significativo_holm else "Não"
        md_kruskal.append(
            f"| {k.nome_fator} | {k.nome_metrica} | {k.k_grupos} | {k.n_total} | "
            f"{k.h_stat:.2f} | {k.p_valor:.4f} | {k.p_valor_holm:.4f} | {k.epsilon_squared:.4f} | "
            f"{k.interpretacao_efeito} | {rej} |"
        )
    md_path_kr = output_dir / "tabela_rq06_kruskal.md"
    md_path_kr.write_text("\n".join(md_kruskal), encoding="utf-8")

    tex_kruskal = [
        "% Tabela gerada automaticamente por analises/analise_rq05_rq06.py",
        "\\begin{table*}[ht]",
        "\\centering",
        "\\caption{Resultados do teste de Kruskal-Wallis e correção de Holm para fatores de repositórios (RQ 06).}",
        "\\label{tab:rq06_kruskal}",
        "\\small",
        "\\begin{tabular}{llrrrrrcc}",
        "\\toprule",
        "\\textbf{Fator} & \\textbf{Métrica DORA} & \\textbf{$k$} & \\textbf{$n$} & \\textbf{$H$} & \\textbf{$p$-bruto} & \\textbf{$p$-Holm} & \\textbf{$\\epsilon^2$} & \\textbf{Efeito} \\\\",
        "\\midrule",
    ]
    for k in kruskal_results:
        fator_esc = k.nome_fator.replace("%", "\\%").replace("_", "\\_")
        metrica_esc = k.nome_metrica.replace("%", "\\%").replace("_", "\\_")
        mark = "$^*$" if k.significativo_holm else ""
        tex_kruskal.append(
            f"{fator_esc} & {metrica_esc} & {k.k_grupos} & {k.n_total} & "
            f"{k.h_stat:.2f} & {k.p_valor:.3e} & {k.p_valor_holm:.3e}{mark} & {k.epsilon_squared:.3f} & {k.interpretacao_efeito} \\\\"
        )
    tex_kruskal.extend(
        [
            "\\bottomrule",
            "\\multicolumn{9}{l}{\\footnotesize $^*$Significativo após correção de Holm-Bonferroni ($\\alpha = 0{,}05$).}\\\\",
            "\\end{tabular}",
            "\\end{table*}",
        ]
    )
    tex_path_kr = output_dir / "tabela_rq06_kruskal.tex"
    tex_path_kr.write_text("\n".join(tex_kruskal), encoding="utf-8")

    return md_path_sp, tex_path_sp, md_path_kr, tex_path_kr


def executar_analise_rq05_rq06(
    dataset_path: Path | str = DATASET_PADRAO,
    tipo_projeto_path: Path | str = TIPO_PROJETO_PADRAO,
    output_dir: Path | str = OUTPUT_DIR_PADRAO,
) -> dict[str, Any]:
    """Executa o pipeline analítico completo das RQ 05 e RQ 06."""
    dataset_file = Path(dataset_path)
    tipo_file = Path(tipo_projeto_path)
    out_dir = Path(output_dir)
    figuras_dir = out_dir / "figuras"

    logger.info("Carregando datasets: %s e %s", dataset_file, tipo_file)
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset principal não encontrado: {dataset_file}")

    df_base = pd.read_csv(dataset_file)
    df_tipo = pd.read_csv(tipo_file) if tipo_file.exists() else None

    # Preparar variáveis explicativas e quartis
    df = preparar_fatores(df_base, df_tipo)

    # ------------------------------------------------------------------ #
    # 1. RQ 05: Correlações de Spearman
    # ------------------------------------------------------------------ #
    res_spearman_a = calcular_spearman(
        serie_x=df["deployment_frequency"],
        serie_y=df["cfr_a"],
        id_rq="RQ05a",
        nome_x="deployment_frequency",
        nome_y="cfr_a",
        descricao="Freq. Deploy vs CFR (a) Proxy de CI",
    )
    res_spearman_b = calcular_spearman(
        serie_x=df["deployment_frequency"],
        serie_y=df["cfr_b"],
        id_rq="RQ05b",
        nome_x="deployment_frequency",
        nome_y="cfr_b",
        descricao="Freq. Deploy vs CFR (b) Proxy de Entrega",
    )
    lista_spearman = [res_spearman_a, res_spearman_b]

    # ------------------------------------------------------------------ #
    # 2. RQ 06: Testes de Kruskal-Wallis com Correção de Holm
    # ------------------------------------------------------------------ #
    lista_kruskal: list[ResultadoKruskal] = []
    for fator_col, fator_nome in FATORES_RQ06:
        for metrica_col, metrica_nome in METRICAS_DORA_RQ06:
            res_k = executar_kruskal(
                df=df,
                fator=fator_col,
                nome_fator=fator_nome,
                metrica=metrica_col,
                nome_metrica=metrica_nome,
            )
            lista_kruskal.append(res_k)

    lista_kruskal = aplicar_correcao_holm_kruskal(lista_kruskal)

    # ------------------------------------------------------------------ #
    # 3. RQ 06: Comparações Pareadas e Cliff's Delta (Extremos e Contrastes)
    # ------------------------------------------------------------------ #
    pares_fatores = [
        ("quartil_estrelas", [("Q1 (menor)", "Q4 (maior)")]),
        ("quartil_contribuidores", [("Q1 (menor)", "Q4 (maior)")]),
        ("quartil_idade", [("Q1 (mais novo)", "Q4 (mais antigo)")]),
        ("tipo_projeto", [("biblioteca/framework", "aplicação/serviço"), ("biblioteca/framework", "ferramenta CLI")]),
    ]
    lista_pareadas: list[ResultadoComparacaoPareada] = []
    for fator_col, pares in pares_fatores:
        for metrica_col, metrica_nome in METRICAS_DORA_RQ06:
            res_par = executar_comparacoes_pareadas(
                df=df,
                fator=fator_col,
                pares=pares,
                metrica=metrica_col,
                nome_metrica=metrica_nome,
            )
            lista_pareadas.extend(res_par)

    lista_pareadas = aplicar_correcao_holm_pareadas(lista_pareadas)

    # ------------------------------------------------------------------ #
    # 4. Geração de Gráficos e Exportação de Tabelas
    # ------------------------------------------------------------------ #
    figs_rq05 = gerar_graficos_rq05(df, res_spearman_a, res_spearman_b, figuras_dir)
    figs_rq06 = gerar_graficos_rq06(df, lista_kruskal, figuras_dir)
    exportar_tabelas_rq05_rq06(lista_spearman, lista_kruskal, lista_pareadas, out_dir)

    # Exportar JSON consolidado
    resultado_json = {
        "rq05": [s.to_dict() for s in lista_spearman],
        "rq06_kruskal": [k.to_dict() for k in lista_kruskal],
        "rq06_comparacoes_pareadas": [p.to_dict() for p in lista_pareadas],
        "figuras": figs_rq05 + figs_rq06,
    }
    json_path = out_dir / "rq05_rq06_metricas.json"
    json_path.write_text(json.dumps(resultado_json, indent=2, ensure_ascii=False), encoding="utf-8")

    return resultado_json


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada via CLI para a execução da análise das RQ 05 e RQ 06."""
    parser = argparse.ArgumentParser(
        description="Executa análise empírica das RQ 05 e RQ 06 (Sprint 03 - Gabriel Assis)"
    )
    parser.add_argument("--dataset", type=Path, default=Path(DATASET_PADRAO), help="Caminho do repositorios.csv")
    parser.add_argument(
        "--tipo-projeto", type=Path, default=Path(TIPO_PROJETO_PADRAO), help="Caminho do tipo_projeto_agentes.csv"
    )
    parser.add_argument("--output-dir", type=Path, default=Path(OUTPUT_DIR_PADRAO), help="Diretório de saída")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        res = executar_analise_rq05_rq06(
            dataset_path=args.dataset,
            tipo_projeto_path=args.tipo_projeto,
            output_dir=args.output_dir,
        )
        print("\n" + "=" * 65)
        print("RESUMO DA ANÁLISE EMPÍRICA: RQ 05 (CORRELAÇÕES DE SPEARMAN)")
        print("=" * 65)
        for s in res["rq05"]:
            sig_txt = "Sim (p < 0.05)" if s["significativo_05"] else "Não (p >= 0.05)"
            print(f"[{s['id_rq']}] {s['descricao']}")
            print(f"  rho = {s['rho']:.4f} | p-valor = {s['p_valor']:.4e} | n = {s['n_pares']}")
            print(f"  Significativo: {sig_txt} | Interpretação: {s['interpretacao']}")

        print("\n" + "=" * 65)
        print("RESUMO DA ANÁLISE EMPÍRICA: RQ 06 (KRUSKAL-WALLIS E HOLM)")
        print("=" * 65)
        significativos = [k for k in res["rq06_kruskal"] if k["significativo_holm"]]
        print(f"Total de testes realizados: {len(res['rq06_kruskal'])}")
        print(f"Testes com significância mantida pós-Holm (alpha=0.05): {len(significativos)}")
        for k in significativos:
            print(
                f"  * {k['nome_fator']} x {k['nome_metrica']}: "
                f"H={k['h_stat']:.2f}, p_raw={k['p_valor']:.4e}, p_holm={k['p_valor_holm']:.4e}, "
                f"eps2={k['epsilon_squared']:.4f} ({k['interpretacao_efeito']})"
            )

        print("\n[*] Artefatos salvos em:")
        print(f"  - JSON: {args.output_dir / 'rq05_rq06_metricas.json'}")
        print(f"  - Tabelas LaTeX: {args.output_dir / 'tabela_rq05_spearman.tex'} e {args.output_dir / 'tabela_rq06_kruskal.tex'}")
        print(f"  - Tabelas Markdown: {args.output_dir / 'tabela_rq05_spearman.md'} e {args.output_dir / 'tabela_rq06_kruskal.md'}")
        print(f"  - Figuras geradas: {len(res['figuras'])} arquivos em {args.output_dir / 'figuras'}")
        return 0
    except Exception as exc:
        logger.exception("Falha ao executar análise das RQ 05 e RQ 06: %s", exc)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
