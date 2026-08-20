"""
Validação de dados - RQ05 (linguagem) + RQ06 (razão issues fechadas/total)
Base: 1000 repositórios (Sprint S02)

Como rodar:
    pip install pytest pandas
    pytest test_validacao_rq05_rq06.py -v -s

O '-s' mostra os prints com as estatísticas de distribuição no terminal.
Os testes fazem checagens automáticas de outliers e valores ausentes.
"""

from pathlib import Path
import pandas as pd
import pytest

CSV_PATH = Path(__file__).parent.parent / "dados" / "unified_sample.csv"
AMOSTRA_SIZE = 1000
SEED = 42


@pytest.fixture(scope="module")
def df():
    df_completo = pd.read_csv(CSV_PATH)
    if len(df_completo) > AMOSTRA_SIZE:
        return df_completo.sample(n=AMOSTRA_SIZE, random_state=SEED).reset_index(drop=True)
    return df_completo


def test_valores_ausentes_linguagem(df):
    """Verifica se há valores ausentes (nulos) na coluna de linguagem (RQ05)."""
    ausentes = df["primary_language"].isna().sum()
    print(f"\n[RQ05] Valores ausentes em primary_language: {ausentes} de {len(df)}")
    assert ausentes == 0, f"Encontrados {ausentes} valores ausentes em primary_language"


def test_valores_ausentes_razao_issues(df):
    """Verifica se há valores ausentes na coluna da razão de issues fechadas/total (RQ06)."""
    ausentes = df["closed_issues_ratio"].isna().sum()
    print(f"\n[RQ06] Valores ausentes em closed_issues_ratio: {ausentes} de {len(df)}")
    assert ausentes == 0, f"Encontrados {ausentes} valores ausentes em closed_issues_ratio"


def test_distribuicao_linguagem(df):
    """Mostra distribuição por categoria (contagem por linguagem) para RQ05."""
    contagem = df["primary_language"].value_counts()
    print(f"\n[RQ05] Distribuição por linguagem (top 10):\n{contagem.head(10)}")
    assert not contagem.empty, "Nenhuma linguagem encontrada"


def test_distribuicao_razao_issues(df):
    """Mostra estatísticas de distribuição (média, mediana, min, max) para RQ06."""
    stats = df["closed_issues_ratio"].describe()
    print(f"\n[RQ06] Distribuição de closed_issues_ratio:\n{stats}")
    assert not df["closed_issues_ratio"].empty, "Nenhum dado de razão de issues encontrado"


def test_outliers_razao_issues(df):
    """Identifica outliers em closed_issues_ratio usando o método IQR (RQ06)."""
    q1 = df["closed_issues_ratio"].quantile(0.25)
    q3 = df["closed_issues_ratio"].quantile(0.75)
    iqr = q3 - q1
    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr

    outliers = df[
        (df["closed_issues_ratio"] < limite_inferior) | 
        (df["closed_issues_ratio"] > limite_superior)
    ]
    print(f"\n[RQ06] Outliers em closed_issues_ratio: {len(outliers)} de {len(df)} repositórios")
    print(f"Limites considerados normais: {limite_inferior:.2f} a {limite_superior:.2f}")
    if not outliers.empty:
        print(outliers[["repo", "closed_issues_ratio"]].head(5))

    assert True


def test_consistencia_razao_issues(df):
    """Verifica se a razão de issues está sempre entre 0 e 1 (inclusive)."""
    inconsistentes = df[
        (df["closed_issues_ratio"] < 0) | (df["closed_issues_ratio"] > 1)
    ]
    print(f"\n[RQ06] Valores inconsistentes em closed_issues_ratio (fora de [0, 1]): {len(inconsistentes)}")
    assert len(inconsistentes) == 0, f"Encontrados {len(inconsistentes)} valores fora de [0, 1]"
