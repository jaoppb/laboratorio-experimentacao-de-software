"""Texto da seção 7 (conclusão): expectativa registrada × resultado simulado.

A expectativa vem de ``docs/cenario.md`` (escrita antes de simular) e aqui é
reduzida a quatro afirmações, cada uma checada contra as taxas de G3 e G4. O
texto só diz que a simulação confirmou se todas passam; caso contrário cita as
que falharam e a recomendação fica neutra.
"""

from __future__ import annotations

import pandas as pd

from src.dashboard.formato import num as _num
from src.dashboard.formato import pct as _pct

ALFA = 0.05
TOLERANCIA_ERRO_TIPO1 = 0.01  # "perto de 5%": |taxa − 5%| ≤ 1 ponto percentual
RAZAO_PODER_REAL = 4.0  # razão entre medianas em que se avalia "pouco poder"
LIMITE_PODER_BAIXO = 0.5  # Welch com "pouco poder": abaixo disso nessa razão
SITUACOES_REAIS = ("com_bot", "sem_bot")
SITUACAO_DESTAQUE = "com_bot"


def _no_alfa(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["alfa"] == ALFA] if "alfa" in df.columns else df


def _faixa(taxas: pd.Series) -> str:
    return f"entre {_pct(taxas.min())} e {_pct(taxas.max())}"


def _lista(itens: list[str]) -> str:
    return ", ".join(sorted(set(itens)))


def _poder_por_teste(poder: pd.DataFrame) -> pd.DataFrame:
    com_efeito = _no_alfa(poder)
    com_efeito = com_efeito[com_efeito["razao_medianas"] > 1.0]
    return com_efeito.pivot_table(
        index=["cenario", "razao_medianas"], columns="teste", values="taxa_rejeicao"
    )


def _poder_real(piv: pd.DataFrame) -> pd.DataFrame:
    faltando = [s for s in SITUACOES_REAIS if (s, RAZAO_PODER_REAL) not in piv.index]
    if faltando:
        raise ValueError(
            f"poder sem a situação {', '.join(faltando)} com razão {RAZAO_PODER_REAL:g}"
        )
    return piv.loc[[(s, RAZAO_PODER_REAL) for s in SITUACOES_REAIS]]


def _falhas(tipo1: pd.DataFrame, piv: pd.DataFrame) -> tuple[list[str], bool]:
    """Devolve (afirmações da expectativa que falharam, se o Mann-Whitney sustenta a recomendação).

    A recomendação depende só das duas afirmações sobre o Mann-Whitney (erro tipo I perto de 5%
    e mais poder que o Welch).
    """
    falhas: list[str] = []
    mw = tipo1[tipo1["teste"] == "mannwhitney"]
    fora = mw[(mw["taxa_rejeicao"] - ALFA).abs() > TOLERANCIA_ERRO_TIPO1 + 1e-12]
    if not fora.empty:
        falhas.append(
            f"o Mann-Whitney perto de 5% (saiu da faixa em {_lista(list(fora['cenario']))})"
        )
    welch_vence = piv[piv["welch"] > piv["mannwhitney"]]
    lugares = [c for c, _ in welch_vence.index]
    mw_sustenta = fora.empty and not lugares
    if lugares:
        falhas.append(f"o Mann-Whitney com mais poder (o Welch o superou em {_lista(lugares)})")
    real = _poder_real(piv)
    alto = real[real["welch"] >= LIMITE_PODER_BAIXO]
    if not alto.empty:
        falhas.append(
            f"o Welch com pouco poder (passou de {_pct(LIMITE_PODER_BAIXO)} em "
            f"{_lista([c for c, _ in alto.index])} com razão {RAZAO_PODER_REAL:g})"
        )
    welch = tipo1[tipo1["teste"] == "welch"]
    nao_conservador = welch[welch["taxa_rejeicao"] >= ALFA - TOLERANCIA_ERRO_TIPO1]
    if not nao_conservador.empty:
        falhas.append(
            f"o Welch conservador (ficou em {_pct(ALFA - TOLERANCIA_ERRO_TIPO1)} ou mais em "
            f"{_lista(list(nao_conservador['cenario']))})"
        )
    return falhas, mw_sustenta


def texto_conclusao(tipo1: pd.DataFrame, poder: pd.DataFrame) -> str:
    """Parágrafo de 4 frases da seção 7, calculado das taxas simuladas (α = 0,05)."""
    tipo1 = _no_alfa(tipo1)
    piv = _poder_por_teste(poder)
    falhas, recomenda_mw = _falhas(tipo1, piv)
    mw = tipo1[tipo1["teste"] == "mannwhitney"]["taxa_rejeicao"]
    w = tipo1[tipo1["teste"] == "welch"]["taxa_rejeicao"]
    esperado = (
        "Antes de simular esperávamos o Mann-Whitney perto de 5% de erro tipo I e com mais poder, "
        "e o Welch conservador e com pouco poder"
    )
    numeros = f"Mann-Whitney {_faixa(mw)}, Welch {_faixa(w)}"
    if falhas:
        achado = f"{esperado}, mas a simulação não confirmou: {'; '.join(falhas)} ({numeros})."
    else:
        achado = (
            f"{esperado}, e a simulação confirmou ({numeros}), sem que o Welch superasse o "
            "Mann-Whitney em nenhuma situação, nem com n pequeno, que era a nossa ressalva."
        )

    if recomenda_mw:
        destaque = piv.loc[(SITUACAO_DESTAQUE, RAZAO_PODER_REAL)]
        recomendacao = (
            "Recomendamos o Mann-Whitney para o tempo até o merge: com a cauda pesada dos "
            f"parâmetros reais ({SITUACAO_DESTAQUE}, razão {_num(RAZAO_PODER_REAL, 1)}) ele "
            f"detectou o efeito em {_pct(destaque['mannwhitney'])} das repetições contra "
            f"{_pct(destaque['welch'])} do Welch, mantendo o erro tipo I perto de 5%."
        )
    else:
        recomendacao = (
            "A simulação não aponta um único teste para o cenário: compare o erro tipo I do G3 "
            "com as curvas de poder do G4 antes de escolher."
        )
    mudanca = (
        "A escolha mudaria se a pergunta passasse a ser sobre a diferença de médias (por exemplo, "
        "o custo total em horas), que o Mann-Whitney não testa, ou se os dados fossem "
        "aproximadamente simétricos e sem outliers, situação que não simulamos."
    )
    limitacao = (
        "A principal limitação é que os dados reais vêm de períodos diferentes (antes e depois "
        "do CodeRabbit), então qualquer diferença entre os grupos fica confundida com o tempo e "
        "não pode ser atribuída ao bot."
    )
    return " ".join((achado, recomendacao, mudanca, limitacao))
