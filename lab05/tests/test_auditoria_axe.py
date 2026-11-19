"""Testes do resumo do axe (não requer navegador)."""

from __future__ import annotations

import auditoria_axe as aa


def test_resumir_resultado_conta_violacoes_por_impacto():
    resultado = {
        "violations": [
            {"id": "color-contrast", "impact": "serious", "tags": ["wcag2aa", "cat.color"], "nodes": [1, 2]},
            {"id": "label", "impact": "critical", "tags": ["wcag2a"], "nodes": [1]},
            {"id": "region", "impact": "moderate", "tags": ["best-practice"], "nodes": []},
        ]
    }
    resumo = aa.resumir_resultado(resultado)

    assert resumo["total_violacoes"] == 3
    assert resumo["por_impacto"] == {
        "critical": 1, "serious": 1, "moderate": 1, "minor": 0, "indefinido": 0
    }
    assert resumo["violacoes"][0] == {
        "id": "color-contrast",
        "impacto": "serious",
        "tags": ["wcag2aa"],
        "nos_afetados": 2,
    }


def test_resumir_resultado_sem_violacoes():
    resumo = aa.resumir_resultado({"passes": [{}, {}], "incomplete": [{}]})
    assert resumo["total_violacoes"] == 0
    assert resumo["regras_aprovadas"] == 2
    assert resumo["regras_incompletas"] == 1


def test_impacto_ausente_ou_desconhecido_conta_como_indefinido():
    resumo = aa.resumir_resultado(
        {"violations": [{"id": "a", "impact": None}, {"id": "b", "impact": "novo"}]}
    )
    assert resumo["total_violacoes"] == 2
    assert resumo["por_impacto"]["indefinido"] == 2
    assert sum(resumo["por_impacto"].values()) == resumo["total_violacoes"]
