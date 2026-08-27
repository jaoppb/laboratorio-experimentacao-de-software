"""
Gera a seção de Resultados do relatório (RQ01 a RQ07) diretamente a partir
dos dados coletados, evitando números "copiados na mão" do dashboard.

Como rodar:
    pip install pandas
    python gerar_resultados.py

Saída: lab01/dados/resultados_gerados.md
"""

import os
import pandas as pd

CSV_PATH = "lab01/dados/unified_sample.csv"
OUTPUT_PATH = "lab01/dados/resultados_gerados.md"

TOP_N_LINGUAGENS = 10


def calcular_outliers_iqr(serie):
    q1 = serie.quantile(0.25)
    q3 = serie.quantile(0.75)
    iqr = q3 - q1
    limite_inf = q1 - 1.5 * iqr
    limite_sup = q3 + 1.5 * iqr
    outliers = serie[(serie < limite_inf) | (serie > limite_sup)]
    return len(outliers), limite_inf, limite_sup


def gerar_rq01(df):
    s = df["age_days"] / 365.25
    return (
        "### RQ01 - Idade do repositório\n"
        f"- Mediana: **{s.median():.1f} anos** | Média: {s.mean():.1f} anos | Máximo: {s.max():.1f} anos\n"
        f"- Base: {s.notna().sum()} de {len(df)} repositórios com dado válido.\n\n"
    )


def gerar_rq02(df):
    s = df["merged_pull_requests"]
    n_out, lim_inf, lim_sup = calcular_outliers_iqr(s)
    return (
        "### RQ02 - Pull requests aceitas (mescladas)\n"
        f"- Mediana: **{s.median():.0f}** | Média: {s.mean():.1f} | P90: {s.quantile(0.9):.0f} | P99: {s.quantile(0.99):.0f}\n"
        f"- Outliers (IQR): {n_out} de {len(s)} ({100*n_out/len(s):.1f}%), limites normais [{lim_inf:.0f}, {lim_sup:.0f}]\n\n"
    )


def gerar_rq03(df):
    s = df["total_releases"]
    pct_zero = (s == 0).mean() * 100
    return (
        "### RQ03 - Total de releases\n"
        f"- {pct_zero:.1f}% dos repositórios não têm nenhuma release cadastrada.\n"
        f"- Mediana geral: {s.median():.0f} | Média geral: {s.mean():.1f}\n\n"
    )


def gerar_rq04(df):
    s = df["time_since_update_days"]
    return (
        "### RQ04 - Tempo até a última atualização\n"
        f"- Mediana: **{s.median():.0f} dias** | Média: {s.mean():.1f} dias | Máximo: {s.max():.0f} dias\n\n"
    )


def gerar_rq05(df):
    total = len(df)
    ausentes = df["primary_language"].isna().sum()
    top = df["primary_language"].value_counts().head(TOP_N_LINGUAGENS)
    linhas = "\n".join(f"  - {lang}: {count}" for lang, count in top.items())
    return (
        "### RQ05 - Linguagem primária\n"
        f"- Linguagem líder: **{top.index[0]}** ({top.iloc[0]} repositórios, {100*top.iloc[0]/total:.1f}%)\n"
        f"- Valores ausentes: {ausentes} de {total} ({100*ausentes/total:.2f}%)\n"
        f"- Top {TOP_N_LINGUAGENS} linguagens:\n{linhas}\n\n"
    )


def gerar_rq06(df):
    s = df["closed_issues_ratio"].dropna()
    n_out, lim_inf, lim_sup = calcular_outliers_iqr(s)
    ausentes = df["closed_issues_ratio"].isna().sum()
    return (
        "### RQ06 - Razão de issues fechadas/total\n"
        f"- Mediana: **{s.median():.3f}** | Média: {s.mean():.3f} | Desvio padrão: {s.std():.3f}\n"
        f"- Valores ausentes: {ausentes} de {len(df)} ({100*ausentes/len(df):.2f}%)\n"
        f"- Outliers (IQR): {n_out}, limites [{lim_inf:.3f}, {lim_sup:.3f}]\n\n"
    )


def gerar_rq07(df):
    top_langs = df["primary_language"].value_counts().head(12).index
    subset = df[df["primary_language"].isin(top_langs)]
    agrupado = subset.groupby("primary_language")[
        ["merged_pull_requests", "total_releases", "time_since_update_days"]
    ].median().sort_values("merged_pull_requests", ascending=False)

    linhas = "\n".join(
        f"  - {lang}: PRs={row.merged_pull_requests:.0f}, Releases={row.total_releases:.0f}, "
        f"Dias s/ update={row.time_since_update_days:.0f}"
        for lang, row in agrupado.iterrows()
    )
    return (
        "### RQ07 - Cruzamento RQ02/03/04 por linguagem (mediana)\n"
        f"{linhas}\n\n"
    )


def gerar_correlacao(df):
    colunas = [
        "age_days", "merged_pull_requests", "total_releases",
        "time_since_update_days", "total_issues", "closed_issues_ratio",
    ]
    corr = df[colunas].corr(method="spearman").round(2)
    return (
        "### Matriz de correlação (Spearman)\n\n"
        "```\n" + corr.to_string() + "\n```\n\n"
    )


def main():
    if not os.path.exists(CSV_PATH):
        raise SystemExit(f"Arquivo não encontrado: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    total_repos = len(df)

    conteudo = (
        "# Resultados (gerado automaticamente a partir dos dados coletados)\n\n"
        f"Base analisada: **{total_repos}** repositórios "
        f"(arquivo `{CSV_PATH}`).\n\n"
        + gerar_rq01(df)
        + gerar_rq02(df)
        + gerar_rq03(df)
        + gerar_rq04(df)
        + gerar_rq05(df)
        + gerar_rq06(df)
        + gerar_rq07(df)
        + gerar_correlacao(df)
    )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(conteudo)

    print(f"Resultados gerados em {OUTPUT_PATH}")


if __name__ == "__main__":
    main()