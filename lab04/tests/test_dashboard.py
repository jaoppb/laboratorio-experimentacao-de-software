"""Testes do gerador do dashboard HTML (Sprint 1)."""

from __future__ import annotations

import re
from pathlib import Path

from src.dashboard.gerador import (
    LINK_PAGES,
    LINK_PROJECTS,
    LINK_REPO,
    gerar_dashboard,
)


def test_gerar_dashboard_cria_arquivo(tmp_path):
    caminho = gerar_dashboard(diretorio_saida=tmp_path)
    assert caminho.exists()
    assert caminho.name == "index.html"
    conteudo = caminho.read_text(encoding="utf-8")
    assert len(conteudo) > 500


def test_dashboard_contem_topo_com_links(tmp_path):
    caminho = gerar_dashboard(diretorio_saida=tmp_path)
    conteudo = caminho.read_text(encoding="utf-8")
    assert LINK_REPO in conteudo
    assert LINK_PROJECTS in conteudo
    assert LINK_PAGES in conteudo


def test_dashboard_contem_secoes_obrigatorias(tmp_path):
    caminho = gerar_dashboard(diretorio_saida=tmp_path)
    conteudo = caminho.read_text(encoding="utf-8")
    # Seções 1 a 7 na ordem
    secoes = [
        "1. Cenário",
        "2. Os dados (G1)",
        "3. Como os testes funcionam (G2)",
        "4. Erro tipo I",
        "5. Poder",
        "6. Dados reais",
        "7. Conclusão",
    ]
    pos_anterior = -1
    for s in secoes:
        pos = conteudo.find(s)
        assert pos != -1, f"Seção {s!r} não encontrada no HTML"
        assert pos > pos_anterior, f"Seção {s!r} fora de ordem no HTML"
        pos_anterior = pos

    # Aviso da Sprint 2 nas seções 4 a 7
    assert conteudo.count("A ser preenchido na Sprint 2/entrega final.") == 4


def test_dashboard_contem_graficos_plotly(tmp_path):
    caminho = gerar_dashboard(diretorio_saida=tmp_path)
    conteudo = caminho.read_text(encoding="utf-8")
    assert 'id="grafico_g1"' in conteudo
    assert 'id="grafico_g2"' in conteudo
    assert "plotly" in conteudo.lower()


def test_dashboard_duas_execucoes_sao_identicas(tmp_path):
    c1 = gerar_dashboard(diretorio_saida=tmp_path / "exec1")
    c2 = gerar_dashboard(diretorio_saida=tmp_path / "exec2")
    assert c1.read_text(encoding="utf-8") == c2.read_text(encoding="utf-8")
