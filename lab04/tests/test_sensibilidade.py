"""Testes do texto de sensibilidade a α e do seletor nos gráficos."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from src.dashboard.sensibilidade import texto_sensibilidade
from src.graficos.g3 import figura_g3
from src.graficos.g4 import figura_g4


def _tipo1(alfa, mw, w):
    return pd.DataFrame(
        [
            {"cenario": "referencia", "teste": "mannwhitney", "n_rep": 100, "alfa": alfa, "taxa_rejeicao": mw},
            {"cenario": "referencia", "teste": "welch", "n_rep": 100, "alfa": alfa, "taxa_rejeicao": w},
        ]
    )


def _poder(alfa, mw, w):
    linhas = []
    for razao, m, v in ((1.0, 0.05, 0.05), (2.0, mw, w)):
        for teste, taxa in (("mannwhitney", m), ("welch", v)):
            linhas.append({"cenario": "referencia", "teste": teste, "razao_medianas": razao,
                           "n_rep": 100, "alfa": alfa, "taxa_rejeicao": taxa})
    return pd.DataFrame(linhas)


T5, T1 = _tipo1(0.05, 0.05, 0.04), _tipo1(0.01, 0.01, 0.008)
P5, P1 = _poder(0.05, 0.60, 0.50), _poder(0.01, 0.40, 0.30)


def test_texto_cita_os_numeros_dos_dados():
    t = texto_sensibilidade(T5, T1, P5, P1)
    assert "α = 0,01 em vez de 0,05" in t
    assert "de 5,0% para 1,0%" in t
    assert "Mann-Whitney foi de 5,0% a 5,0% para 1,0% a 1,0%" in t
    assert "Welch de 4,0% a 4,0% para 0,8% a 0,8%" in t
    assert "cai 20,0 pontos percentuais no Mann-Whitney e 20,0 no Welch" in t
    assert "continuou à frente" in t


def test_texto_avisa_quando_a_ordem_muda():
    p1 = _poder(0.01, 0.30, 0.40)
    assert "ordem entre os testes mudou" in texto_sensibilidade(T5, T1, P5, p1)


def test_texto_tem_de_2_a_4_frases():
    t = texto_sensibilidade(T5, T1, P5, P1)
    assert 2 <= len([f for f in re.split(r"(?<=[.!?])\s+", t) if f]) <= 4


def test_g3_com_seletor_tem_dois_conjuntos_e_o_alternativo_oculto():
    fig = figura_g3(T5, 0.05, T1, 0.01)
    assert len(fig.data) == 4
    assert [t.visible for t in fig.data] == [True, True, False, False]
    assert list(fig.data[2].y) == pytest.approx([0.8])
    botoes = fig.layout.updatemenus[0].buttons
    assert [b.label for b in botoes] == ["Nível α = 0,05", "Nível α = 0,01"]
    visivel, layout = botoes[1].args
    assert visivel["visible"] == [False, False, True, True]
    assert layout["shapes[0].y0"] == pytest.approx(1.0)
    assert "1%" in layout["annotations[0].text"]


def test_g4_com_seletor_alterna_a_linha_de_referencia():
    fig = figura_g4(P5, 0.05, P1, 0.01)
    assert len(fig.data) == 4
    assert [t.visible for t in fig.data] == [True, True, False, False]
    assert fig.layout.shapes[0].y0 == pytest.approx(5.0)
    _, layout = fig.layout.updatemenus[0].buttons[1].args
    assert layout["shapes[0].y1"] == pytest.approx(1.0)


def test_sem_alternativo_nao_tem_botoes():
    assert not figura_g3(T5).layout.updatemenus
    assert not figura_g4(P5).layout.updatemenus


@pytest.mark.parametrize("fabrica", [lambda: figura_g3(T5, 0.05, T1), lambda: figura_g4(P5, 0.05, None, 0.01)])
def test_alternativo_exige_dados_e_alfa_juntos(fabrica):
    with pytest.raises(ValueError, match="juntos"):
        fabrica()


def test_legenda_continua_visivel_em_todos_os_tracos():
    for fig in (figura_g3(T5, 0.05, T1, 0.01), figura_g4(P5, 0.05, P1, 0.01)):
        assert all(t.showlegend is not False for t in fig.data)


def test_seletor_exige_so_a_linha_de_referencia():
    from src.graficos.seletor_alfa import adicionar_seletor

    fig = figura_g3(T5, 0.05, T1, 0.01)
    fig.add_hline(y=3)
    with pytest.raises(ValueError, match="linha de referência"):
        adicionar_seletor(fig, 2, (0.05, 0.01), str, (8.0, 8.0))
