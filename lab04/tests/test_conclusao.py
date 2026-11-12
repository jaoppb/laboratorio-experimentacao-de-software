"""Testes do texto da seção 7 (conclusão), calculado das taxas simuladas."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from src.dashboard.conclusao import texto_conclusao
from src.graficos.dados_simulacao import carregar_erro_tipo1, carregar_poder

CENARIOS = ("com_bot", "sem_bot", "referencia")


def _tipo1(mw: float = 0.047, welch: float = 0.02) -> pd.DataFrame:
    linhas = []
    for c in CENARIOS:
        linhas.append(dict(cenario=c, teste="mannwhitney", n_rep=10000, alfa=0.05, taxa_rejeicao=mw))
        linhas.append(dict(cenario=c, teste="welch", n_rep=10000, alfa=0.05, taxa_rejeicao=welch))
    return pd.DataFrame(linhas)


def _poder(mw: float = 0.60, welch: float = 0.05, welch_vence_em: str | None = None) -> pd.DataFrame:
    linhas = []
    for c in CENARIOS:
        for razao in (1.0, 4.0):
            w = welch
            m = mw
            if c == welch_vence_em and razao == 4.0:
                w, m = 0.9, 0.5
            linhas.append(dict(cenario=c, teste="mannwhitney", razao_medianas=razao, n_rep=10000, alfa=0.05, taxa_rejeicao=m))
            linhas.append(dict(cenario=c, teste="welch", razao_medianas=razao, n_rep=10000, alfa=0.05, taxa_rejeicao=w))
    return pd.DataFrame(linhas)


def _frases(texto: str) -> list[str]:
    return [f for f in re.split(r"(?<=[.!?])\s+", " ".join(texto.split())) if f]



def test_confirmou_tudo_tem_quatro_frases_e_diz_confirmou():
    texto = texto_conclusao(_tipo1(), _poder())
    assert len(_frases(texto)) == 4
    assert "confirmou" in texto and "não confirmou" not in texto
    assert "nem com n pequeno" in texto
    assert "Mann-Whitney" in texto.split(". ")[1]  # recomendação


def test_numeros_vem_dos_dados_formatados_em_pt_br():
    texto = texto_conclusao(_tipo1(mw=0.047, welch=0.02), _poder())
    assert "4,7%" in texto and "2,0%" in texto
    assert "60,0% das repetições contra 5,0%" in texto  # poder em com_bot, razão 4,0


def test_mw_fora_da_faixa_nao_confirma_e_recomendacao_fica_neutra():
    texto = texto_conclusao(_tipo1(mw=0.08), _poder())
    assert "não confirmou" in texto
    assert "perto de 5%" in texto
    assert "Recomendamos o Mann-Whitney" not in texto
    assert "G4" in texto
    assert len(_frases(texto)) == 4


def test_mw_no_limite_de_um_ponto_ainda_confirma():
    assert "não confirmou" not in texto_conclusao(_tipo1(mw=0.059), _poder())
    assert "não confirmou" not in texto_conclusao(_tipo1(mw=0.041), _poder())
    assert "não confirmou" in texto_conclusao(_tipo1(mw=0.039), _poder())


def test_welch_vence_em_algum_ponto_cita_a_situacao_e_nao_recomenda_mw():
    texto = texto_conclusao(_tipo1(), _poder(welch_vence_em="referencia"))
    assert "não confirmou" in texto
    assert "referencia" in texto
    assert "nem com n pequeno" not in texto
    assert "Recomendamos o Mann-Whitney" not in texto


def test_welch_liberal_nao_confirma_conservador():
    texto = texto_conclusao(_tipo1(welch=0.07), _poder())
    assert "não confirmou" in texto
    assert "conservador" in texto


def test_welch_com_poder_alto_nos_parametros_reais_nao_confirma_pouco_poder():
    texto = texto_conclusao(_tipo1(), _poder(welch=0.55, mw=0.9))
    assert "não confirmou" in texto
    assert "pouco poder" in texto


def test_quando_muda_e_limitacao_estao_presentes():
    texto = texto_conclusao(_tipo1(), _poder())
    assert "diferença de médias" in texto
    assert "não simulamos" in texto
    assert "confundida com o tempo" in texto


def test_dados_versionados_confirmam_a_expectativa():
    texto = texto_conclusao(carregar_erro_tipo1(), carregar_poder())
    assert "não confirmou" not in texto
    assert "4,3% e 4,8%" in texto
    assert "35,2% das repetições contra 3,4%" in texto
    assert len(_frases(texto)) == 4


def test_sem_cenario_de_parametros_reais_levanta_erro_claro():
    poder = _poder()
    poder = poder[poder["cenario"] != "com_bot"]
    with pytest.raises(ValueError, match="com_bot"):
        texto_conclusao(_tipo1(), poder)
