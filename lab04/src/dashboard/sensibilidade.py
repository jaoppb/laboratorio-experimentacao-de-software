"""Texto da sensibilidade ao nível de significância (α = 0,01 contra α = 0,05)."""

from __future__ import annotations

import pandas as pd


def _pct(valor: float) -> str:
    return f"{valor * 100:.1f}".replace(".", ",") + "%"


def _faixa(df: pd.DataFrame, teste: str) -> str:
    taxas = df[df["teste"] == teste]["taxa_rejeicao"]
    return f"{_pct(taxas.min())} a {_pct(taxas.max())}"


def _num(valor: float, casas: int | None = None) -> str:
    texto = f"{valor:g}" if casas is None else f"{valor:.{casas}f}"
    return texto.replace(".", ",")


def _com_efeito(poder: pd.DataFrame) -> pd.DataFrame:
    """Pivô (cenário, razão > 1) × teste com a taxa de rejeição (poder)."""
    efeito = poder[poder["razao_medianas"] > 1.0]
    return efeito.pivot_table(
        index=["cenario", "razao_medianas"], columns="teste", values="taxa_rejeicao"
    )


def texto_sensibilidade(
    tipo1: pd.DataFrame, tipo1_alt: pd.DataFrame, poder: pd.DataFrame, poder_alt: pd.DataFrame
) -> str:
    """Resumo (3 frases) do que muda no G3 e no G4 com o α menor, calculado dos dados.

    ``tipo1``/``poder`` estão no α principal e ``*_alt`` no α menor (coluna ``alfa``).
    """
    a, b = float(tipo1["alfa"].iloc[0]), float(tipo1_alt["alfa"].iloc[0])
    p, q = _com_efeito(poder), _com_efeito(poder_alt)
    queda = (p - q).mean() * 100.0
    manteve = bool((p["mannwhitney"] >= p["welch"]).all() and (q["mannwhitney"] >= q["welch"]).all())
    ordem = (
        "O Mann-Whitney continuou à frente do Welch em todas as situações e efeitos"
        if manteve
        else "A ordem entre os testes mudou em alguma situação ou efeito"
    )
    return (
        f"Com α = {_num(b)} em vez de {_num(a)}, o erro tipo I esperado cai de {_pct(a)} para "
        f"{_pct(b)}: o Mann-Whitney foi de {_faixa(tipo1, 'mannwhitney')} para "
        f"{_faixa(tipo1_alt, 'mannwhitney')} e o Welch de {_faixa(tipo1, 'welch')} para "
        f"{_faixa(tipo1_alt, 'welch')}. "
        f"O preço é o poder: em média, a proporção de rejeições quando há efeito cai "
        f"{_num(queda['mannwhitney'], 1)} pontos percentuais no Mann-Whitney e "
        f"{_num(queda['welch'], 1)} no Welch. "
        f"{ordem}. Use os botões do G3 e do G4 para alternar entre os dois níveis."
    )
