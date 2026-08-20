"""
Validação de dados - RQ01 (idade do repositório) + RQ02 (PRs aceitas)
Base: 1000 repositórios (Sprint S02)

Como rodar:
    pip install pytest pandas
    pytest test_validacao_rq01_rq02.py -v -s

O '-s' mostra os prints com as estatísticas de distribuição no terminal.
Os testes fazem checagens automáticas de outliers e valores ausentes.
"""

import pandas as pd
import pytest

CSV_PATH = "lab01/dados/unified_sample.csv"  # base completa (100k), amostra de 1000 é extraída abaixo
# Este script está em lab01/tests/, mas o caminho acima é relativo à raiz do
# repositório. Rode o pytest sempre a partir da raiz do projeto (onde está a
# pasta lab01), não de dentro de lab01/tests/.
AMOSTRA_SIZE = 1000
SEED = 42  # fixa a amostra para ser reproduzível


@pytest.fixture(scope="module")
def df():
    df_completo = pd.read_csv(CSV_PATH)
    if len(df_completo) > AMOSTRA_SIZE:
        return df_completo.sample(n=AMOSTRA_SIZE, random_state=SEED).reset_index(drop=True)
    return df_completo


def test_valores_ausentes_age_days(df):
    """Verifica se há valores ausentes (nulos) na coluna de idade (RQ01)."""
    ausentes = df["age_days"].isna().sum()
    print(f"\n[RQ01] Valores ausentes em age_days: {ausentes} de {len(df)}")
    assert ausentes == 0, f"Encontrados {ausentes} valores ausentes em age_days"


def test_valores_ausentes_merged_prs(df):
    """Verifica se há valores ausentes na coluna de PRs aceitas (RQ02)."""
    ausentes = df["merged_pull_requests"].isna().sum()
    print(f"[RQ02] Valores ausentes em merged_pull_requests: {ausentes} de {len(df)}")
    assert ausentes == 0, f"Encontrados {ausentes} valores ausentes em merged_pull_requests"


def test_distribuicao_age_days(df):
    """Mostra estatísticas de distribuição da idade dos repositórios (RQ01)."""
    stats = df["age_days"].describe()
    print(f"\n[RQ01] Distribuição de age_days (dias):\n{stats}")
    assert df["age_days"].min() >= 0, "Idade negativa encontrada — possível erro de data"


def test_distribuicao_merged_prs(df):
    """Mostra estatísticas de distribuição de PRs aceitas (RQ02)."""
    stats = df["merged_pull_requests"].describe()
    print(f"\n[RQ02] Distribuição de merged_pull_requests:\n{stats}")
    assert df["merged_pull_requests"].min() >= 0, "Valor negativo de PRs aceitas encontrado"


def test_outliers_age_days(df):
    """Identifica outliers em age_days usando o método IQR (intervalo interquartil)."""
    q1 = df["age_days"].quantile(0.25)
    q3 = df["age_days"].quantile(0.75)
    iqr = q3 - q1
    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr

    outliers = df[(df["age_days"] < limite_inferior) | (df["age_days"] > limite_superior)]
    print(f"\n[RQ01] Outliers em age_days: {len(outliers)} de {len(df)} repositórios")
    print(f"Limites considerados normais: {limite_inferior:.0f} a {limite_superior:.0f} dias")
    if not outliers.empty:
        print(outliers[["repo", "age_days"]].head(5))

    # Não falha o teste — outliers são esperados e só reportados para análise
    assert True


def test_outliers_merged_prs(df):
    """Identifica outliers em merged_pull_requests usando o método IQR."""
    q1 = df["merged_pull_requests"].quantile(0.25)
    q3 = df["merged_pull_requests"].quantile(0.75)
    iqr = q3 - q1
    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr

    outliers = df[
        (df["merged_pull_requests"] < limite_inferior)
        | (df["merged_pull_requests"] > limite_superior)
    ]
    print(f"\n[RQ02] Outliers em merged_pull_requests: {len(outliers)} de {len(df)} repositórios")
    print(f"Limites considerados normais: {limite_inferior:.0f} a {limite_superior:.0f}")
    if not outliers.empty:
        print(outliers[["repo", "merged_pull_requests"]].head(5))

    assert True