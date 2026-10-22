"""Análise empírica descritiva das RQ 01 a RQ 04 e classificação DORA C1 (Sprint 03).

Escopo da Integrante A (Marcela Campos):
- RQ 01: Deployment frequency (releases/semana), IQR e faixas DORA.
- RQ 02: Lead time for changes em duas variantes obrigatórias:
  (a) por release e (b) por commit.
- RQ 03: Change failure rate (CFR) em duas variantes obrigatórias:
  (a) proxy de CI e (b) proxy de entrega (release corretiva em até 7 dias).
- RQ 04: Tempo de recuperação de falhas de CI (horas) e taxa de censura.
- Classificação geral DORA de referência (combinação C1).

Gera tabelas estatísticas em Markdown e LaTeX (booktabs para Overleaf) e
figuras em alta resolução (PNG 300 DPI e PDF vetorial).

Execução (a partir de lab03/):
    uv run python -m analises.analise_rq01_rq04
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

TIERS_ORDEM = ["Elite", "High", "Medium", "Low"]
TIERS_CORES = {
    "Elite": "#2ca02c",   # verde
    "High": "#1f77b4",    # azul
    "Medium": "#ff7f0e",  # laranja
    "Low": "#d62728",     # vermelho
}


@dataclass
class EstatisticasDescritivas:
    metrica: str
    nome_exibicao: str
    unidade: str
    n_total: int
    n_validos: int
    n_nulos: int
    media: float
    desvio_padrao: float
    minimo: float
    q1: float
    mediana: float
    q3: float
    iqr: float
    maximo: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calcular_estatisticas(serie: pd.Series, nome: str, exibicao: str, unidade: str) -> EstatisticasDescritivas:
    """Calcula métricas descritivas completas com foco em mediana e IQR."""
    validos = serie.dropna().astype(float)
    n_total = len(serie)
    n_validos = len(validos)
    n_nulos = n_total - n_validos

    if n_validos == 0:
        return EstatisticasDescritivas(
            metrica=nome,
            nome_exibicao=exibicao,
            unidade=unidade,
            n_total=n_total,
            n_validos=0,
            n_nulos=n_nulos,
            media=float("nan"),
            desvio_padrao=float("nan"),
            minimo=float("nan"),
            q1=float("nan"),
            mediana=float("nan"),
            q3=float("nan"),
            iqr=float("nan"),
            maximo=float("nan"),
        )

    q1 = float(np.percentile(validos, 25))
    mediana = float(np.median(validos))
    q3 = float(np.percentile(validos, 75))
    iqr = q3 - q1

    return EstatisticasDescritivas(
        metrica=nome,
        nome_exibicao=exibicao,
        unidade=unidade,
        n_total=n_total,
        n_validos=n_validos,
        n_nulos=n_nulos,
        media=float(validos.mean()),
        desvio_padrao=float(validos.std()),
        minimo=float(validos.min()),
        q1=q1,
        mediana=mediana,
        q3=q3,
        iqr=iqr,
        maximo=float(validos.max()),
    )


def calcular_distribuicao_tiers(df: pd.DataFrame, coluna_tier: str) -> dict[str, dict[str, Any]]:
    """Calcula contagem e percentual das faixas DORA."""
    total = len(df)
    contagens = df[coluna_tier].value_counts()
    res: dict[str, dict[str, Any]] = {}
    for tier in TIERS_ORDEM:
        qtd = int(contagens.get(tier, 0))
        pct = (qtd / total) * 100 if total > 0 else 0.0
        res[tier] = {"quantidade": qtd, "percentual": pct}
    return res


def gerar_graficos(df: pd.DataFrame, output_dir: Path) -> list[str]:
    """Gera figuras informativas para as seções de Resultados do artigo."""
    output_dir.mkdir(parents=True, exist_ok=True)
    arquivos_gerados: list[str] = []

    # ------------------------------------------------------------------ #
    # 1. RQ 01: Frequência de Deploy (Distribuição + Tiers)
    # ------------------------------------------------------------------ #
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    # Histograma / KDE com escala logarítmica devido à assimetria
    df_val = df["deployment_frequency"].dropna()
    sns.histplot(df_val, bins=30, kde=True, ax=ax1, color="#1f77b4", log_scale=True)
    med_df = df_val.median()
    ax1.axvline(med_df, color="#d62728", linestyle="--", linewidth=1.5, label=f"Mediana ({med_df:.2f})")
    ax1.set_title("Distribuição da Freq. de Deploy")
    ax1.set_xlabel("Releases por semana (escala log)")
    ax1.set_ylabel("Quantidade de repositórios")
    ax1.legend()

    # Gráfico de barras das faixas DORA
    tiers_df = df["deployment_tier"].value_counts().reindex(TIERS_ORDEM, fill_value=0)
    cores = [TIERS_CORES[t] for t in TIERS_ORDEM]
    bars = ax2.bar(TIERS_ORDEM, tiers_df.values, color=cores, edgecolor="black", linewidth=0.5)
    ax2.set_title("Classificação DORA — Freq. de Deploy")
    ax2.set_ylabel("Quantidade de repositórios")
    for bar in bars:
        h = bar.get_height()
        pct = (h / len(df)) * 100
        ax2.annotate(f"{h}\n({pct:.1f}%)", xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
    
    plt.tight_layout()
    for ext in ("png", "pdf"):
        caminho = output_dir / f"rq01_frequencia_deploy.{ext}"
        fig.savefig(caminho)
        arquivos_gerados.append(str(caminho))
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # 2. RQ 02: Comparação de Lead Time (Variante a vs Variante b)
    # ------------------------------------------------------------------ #
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    # Converter para dias para facilitar a interpretação
    lt_a_dias = df["lead_time_a_hours"].dropna() / 24.0
    lt_b_dias = df["lead_time_b_hours"].dropna() / 24.0
    
    dados_lt = pd.DataFrame({
        "Variante (a) Por Release": lt_a_dias,
        "Variante (b) Por Commit": lt_b_dias,
    })
    
    # Boxplot comparativo em escala log
    sns.boxplot(data=dados_lt, ax=ax1, palette=["#3274a1", "#e1812c"], log_scale=True)
    ax1.set_title("Comparação: Lead Time (a) vs (b)")
    ax1.set_ylabel("Lead Time em dias (escala log)")
    
    # Dispersão pareada
    ambos = df[["lead_time_a_hours", "lead_time_b_hours"]].dropna()
    ax2.scatter(ambos["lead_time_a_hours"] / 24.0, ambos["lead_time_b_hours"] / 24.0,
                alpha=0.6, edgecolors="none", color="#4c72b0", s=30)
    lim_max = max((ambos["lead_time_a_hours"] / 24.0).max(), (ambos["lead_time_b_hours"] / 24.0).max())
    ax2.plot([0.001, lim_max], [0.001, lim_max], "r--", linewidth=1.2, label="a = b")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_title("Dispersão Pareada: LT (a) vs LT (b)")
    ax2.set_xlabel("Variante (a) [dias, log]")
    ax2.set_ylabel("Variante (b) [dias, log]")
    ax2.legend()

    plt.tight_layout()
    for ext in ("png", "pdf"):
        caminho = output_dir / f"rq02_lead_time_comparacao.{ext}"
        fig.savefig(caminho)
        arquivos_gerados.append(str(caminho))
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # 3. RQ 03: Comparação de CFR (Proxy CI vs Proxy Entrega)
    # ------------------------------------------------------------------ #
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    cfr_a_pct = df["cfr_a"].dropna() * 100.0
    cfr_b_pct = df["cfr_b"].dropna() * 100.0

    sns.kdeplot(cfr_a_pct, ax=ax1, fill=True, color="#1f77b4", label=f"CFR (a) CI (med={cfr_a_pct.median():.1f}%)")
    sns.kdeplot(cfr_b_pct, ax=ax1, fill=True, color="#ff7f0e", label=f"CFR (b) Entrega (med={cfr_b_pct.median():.1f}%)")
    ax1.set_title("Distribuição do Change Failure Rate")
    ax1.set_xlabel("Taxa de Falha (%)")
    ax1.set_ylabel("Densidade")
    ax1.set_xlim(0, 100)
    ax1.legend()

    # Tiers comparativos
    t_a = df["cfr_tier"].value_counts().reindex(TIERS_ORDEM, fill_value=0)
    t_b = df["cfr_b_tier"].value_counts().reindex(TIERS_ORDEM, fill_value=0)
    x = np.arange(len(TIERS_ORDEM))
    w = 0.35
    ax2.bar(x - w / 2, t_a.values, width=w, label="CFR (a) CI", color="#1f77b4", edgecolor="black", linewidth=0.5)
    ax2.bar(x + w / 2, t_b.values, width=w, label="CFR (b) Entrega", color="#ff7f0e", edgecolor="black", linewidth=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(TIERS_ORDEM)
    ax2.set_title("Distribuição dos Tiers de CFR")
    ax2.set_ylabel("Quantidade de repositórios")
    ax2.legend()

    plt.tight_layout()
    for ext in ("png", "pdf"):
        caminho = output_dir / f"rq03_cfr_comparacao.{ext}"
        fig.savefig(caminho)
        arquivos_gerados.append(str(caminho))
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # 4. RQ 04: Tempo de Recuperação e Censura
    # ------------------------------------------------------------------ #
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    rec_val = df["recovery_hours"].dropna()
    sns.histplot(rec_val, bins=25, kde=True, ax=ax1, color="#2ca02c", log_scale=True)
    med_rec = rec_val.median()
    ax1.axvline(med_rec, color="#d62728", linestyle="--", linewidth=1.5, label=f"Mediana ({med_rec:.2f}h)")
    ax1.set_title("Tempo de Recuperação (CI)")
    ax1.set_xlabel("Tempo em horas (escala log)")
    ax1.set_ylabel("Quantidade de repositórios")
    ax1.legend()

    # Censura
    cens_val = df["censored_episodes_ratio"] * 100.0
    sns.histplot(cens_val, bins=20, ax=ax2, color="#7f7f7f", edgecolor="black", linewidth=0.5)
    ax2.set_title("Proporção de Falhas Censuradas")
    ax2.set_xlabel("% de episódios censurados no repositório")
    ax2.set_ylabel("Quantidade de repositórios")

    plt.tight_layout()
    for ext in ("png", "pdf"):
        caminho = output_dir / f"rq04_recuperacao_censura.{ext}"
        fig.savefig(caminho)
        arquivos_gerados.append(str(caminho))
    plt.close(fig)

    # ------------------------------------------------------------------ #
    # 5. Classificação Geral DORA (C1)
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(6, 4))
    tiers_geral = df["overall_dora_tier"].value_counts().reindex(TIERS_ORDEM, fill_value=0)
    cores = [TIERS_CORES[t] for t in TIERS_ORDEM]
    bars = ax.bar(TIERS_ORDEM, tiers_geral.values, color=cores, edgecolor="black", linewidth=0.6)
    ax.set_title("Classificação Geral DORA Consolidada (C1)")
    ax.set_ylabel("Quantidade de repositórios")
    for bar in bars:
        h = bar.get_height()
        pct = (h / len(df)) * 100
        ax.annotate(f"{h}\n({pct:.1f}%)", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")
    
    plt.tight_layout()
    for ext in ("png", "pdf"):
        caminho = output_dir / f"dora_overall_tiers.{ext}"
        fig.savefig(caminho)
        arquivos_gerados.append(str(caminho))
    plt.close(fig)

    return arquivos_gerados


def exportar_tabelas(
    estatisticas: list[EstatisticasDescritivas],
    tiers_por_metrica: dict[str, dict[str, dict[str, Any]]],
    output_dir: Path,
) -> tuple[Path, Path, Path]:
    """Exporta tabelas sumarizadas em Markdown e LaTeX para inclusão no artigo."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Tabela de Estatísticas Descritivas (Markdown)
    linhas_md = [
        "# Tabela Descritiva: Métricas DORA (RQ 01 a RQ 04)",
        "",
        "| Métrica | Dimensão | Unidade | n | Mediana | Q1 | Q3 | IQR | Min | Max |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in estatisticas:
        linhas_md.append(
            f"| {s.nome_exibicao} | {s.metrica} | {s.unidade} | {s.n_validos} | "
            f"{s.mediana:.3f} | {s.q1:.3f} | {s.q3:.3f} | {s.iqr:.3f} | {s.minimo:.3f} | {s.maximo:.3f} |"
        )
    md_path = output_dir / "tabela_metricas_dora.md"
    md_path.write_text("\n".join(linhas_md), encoding="utf-8")

    # 2. Tabela de Estatísticas Descritivas (LaTeX booktabs)
    linhas_tex = [
        "% Tabela gerada automaticamente por analises/analise_rq01_rq04.py",
        "\\begin{table*}[ht]",
        "\\centering",
        "\\caption{Estatísticas descritivas das métricas DORA mineradas (amostra de 330 repositórios).}",
        "\\label{tab:metricas_dora_descritiva}",
        "\\small",
        "\\begin{tabular}{llcrrrrrrr}",
        "\\toprule",
        "\\textbf{Métrica} & \\textbf{Dimensão/Variante} & \\textbf{Unid.} & \\textbf{n} & \\textbf{Mediana} & \\textbf{Q1} & \\textbf{Q3} & \\textbf{IQR} & \\textbf{Mín.} & \\textbf{Máx.} \\\\",
        "\\midrule",
    ]
    for s in estatisticas:
        nome_escapado = s.nome_exibicao.replace("%", "\\%").replace("_", "\\_")
        unid_escapada = s.unidade.replace("%", "\\%").replace("_", "\\_")
        linhas_tex.append(
            f"{nome_escapado} & {s.metrica} & {unid_escapada} & {s.n_validos} & "
            f"{s.mediana:.2f} & {s.q1:.2f} & {s.q3:.2f} & {s.iqr:.2f} & {s.minimo:.2f} & {s.maximo:.2f} \\\\"
        )
    linhas_tex.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table*}",
        "",
    ])
    tex_path = output_dir / "tabela_metricas_dora.tex"
    tex_path.write_text("\n".join(linhas_tex), encoding="utf-8")

    # 3. Tabela de Tiers DORA (LaTeX booktabs)
    linhas_tiers_tex = [
        "% Distribuição de faixas DORA gerada por analises/analise_rq01_rq04.py",
        "\\begin{table}[ht]",
        "\\centering",
        "\\caption{Distribuição dos repositórios nas faixas de desempenho DORA (\\%).}",
        "\\label{tab:dora_tiers}",
        "\\begin{tabular}{lrrrr}",
        "\\toprule",
        "\\textbf{Dimensão} & \\textbf{Elite (\\%)} & \\textbf{High (\\%)} & \\textbf{Medium (\\%)} & \\textbf{Low (\\%)} \\\\",
        "\\midrule",
    ]
    for dim_nome, faixas in tiers_por_metrica.items():
        linhas_tiers_tex.append(
            f"{dim_nome} & {faixas['Elite']['percentual']:.1f}\\% & "
            f"{faixas['High']['percentual']:.1f}\\% & "
            f"{faixas['Medium']['percentual']:.1f}\\% & "
            f"{faixas['Low']['percentual']:.1f}\\% \\\\"
        )
    linhas_tiers_tex.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
    ])
    tex_tiers_path = output_dir / "tabela_tiers_dora.tex"
    tex_tiers_path.write_text("\n".join(linhas_tiers_tex), encoding="utf-8")

    return md_path, tex_path, tex_tiers_path


def executar_analise(dataset_path: Path, output_dir: Path) -> dict[str, Any]:
    """Executa a análise ponta a ponta e retorna o relatório consolidado."""
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset não encontrado: {dataset_path}")

    df = pd.read_csv(dataset_path) if dataset_path.suffix == ".csv" else pd.read_parquet(dataset_path)
    logger.info("Dataset carregado: %d repositórios em %s", len(df), dataset_path)

    # 1. Estatísticas descritivas
    metricas_alvo = [
        ("deployment_frequency", "Frequência de Deploy (RQ 01)", "rel/sem"),
        ("lead_time_a_hours", "Lead Time (a) por Release (RQ 02)", "horas"),
        ("lead_time_b_hours", "Lead Time (b) por Commit (RQ 02)", "horas"),
        ("cfr_a", "CFR (a) Proxy de CI (RQ 03)", "proporção"),
        ("cfr_b", "CFR (b) Proxy de Entrega (RQ 03)", "proporção"),
        ("recovery_hours", "Tempo de Recuperação (RQ 04)", "horas"),
        ("censored_episodes_ratio", "Taxa de Censura de Falhas (RQ 04)", "proporção"),
    ]

    estatisticas = [
        calcular_estatisticas(df[col], col, nome, unid)
        for col, nome, unid in metricas_alvo
    ]

    # 2. Faixas DORA
    tiers = {
        "Frequência de Deploy (RQ 01)": calcular_distribuicao_tiers(df, "deployment_tier"),
        "Lead Time for Changes (RQ 02)": calcular_distribuicao_tiers(df, "lead_time_tier"),
        "Change Failure Rate (a) - CI": calcular_distribuicao_tiers(df, "cfr_tier"),
        "Change Failure Rate (b) - Entrega": calcular_distribuicao_tiers(df, "cfr_b_tier"),
        "Tempo de Recuperação (RQ 04)": calcular_distribuicao_tiers(df, "recovery_tier"),
        "Classificação Geral DORA (C1)": calcular_distribuicao_tiers(df, "overall_dora_tier"),
    }

    # 3. Exportações
    figuras_dir = output_dir / "figuras"
    figs = gerar_graficos(df, figuras_dir)
    md_tab, tex_tab, tex_tiers = exportar_tabelas(estatisticas, tiers, output_dir)

    resultado_json = {
        "n_repositorios": len(df),
        "estatisticas": [s.to_dict() for s in estatisticas],
        "distribuicao_tiers": tiers,
        "arquivos_gerados": {
            "figuras": figs,
            "tabela_markdown": str(md_tab),
            "tabela_latex": str(tex_tab),
            "tabela_tiers_latex": str(tex_tiers),
        },
    }

    json_path = output_dir / "rq01_rq04_metricas.json"
    json_path.write_text(json.dumps(resultado_json, indent=2, ensure_ascii=False), encoding="utf-8")
    resultado_json["json_path"] = str(json_path)

    return resultado_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Análise descritiva das RQ 01 a RQ 04 e DORA C1")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("dados/repositorios.csv"),
        help="Caminho do repositorios.csv ou repositorios.parquet",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dados/analises"),
        help="Diretório de saída para relatórios e figuras",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    res = executar_analise(args.dataset, args.output_dir)

    print("\n" + "=" * 60)
    print("RESUMO ESTATÍSTICO DAS MÉTRICAS DORA (RQ 01 a RQ 04)")
    print("=" * 60)
    for s in res["estatisticas"]:
        print(f"[{s['metrica']}] n={s['n_validos']}/{s['n_total']}")
        print(f"  Mediana: {s['mediana']:.3f} {s['unidade']} | IQR: {s['iqr']:.3f} (Q1={s['q1']:.3f}, Q3={s['q3']:.3f})")
        print(f"  Média ± DP: {s['media']:.3f} ± {s['desvio_padrao']:.3f} | Min={s['minimo']:.3f}, Max={s['maximo']:.3f}")
    
    print("\n" + "=" * 60)
    print("DISTRIBUIÇÃO DORA GERAL CONSOLIDADA (C1)")
    print("=" * 60)
    for tier, dados in res["distribuicao_tiers"]["Classificação Geral DORA (C1)"].items():
        print(f"  {tier:8s}: {dados['quantidade']:3d} repos ({dados['percentual']:.1f}%)")

    print("\n[*] Artefatos salvos em:")
    print(f"  - JSON: {res['json_path']}")
    print(f"  - Tabelas LaTeX: {res['arquivos_gerados']['tabela_latex']}")
    print(f"  - Figuras (PNG e PDF): {len(res['arquivos_gerados']['figuras'])} arquivos em {args.output_dir / 'figuras'}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
