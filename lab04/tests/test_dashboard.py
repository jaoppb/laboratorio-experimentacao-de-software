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

    # Só a seção 7 mantém o aviso (seções 4 a 6 já preenchidas)
    assert conteudo.count("A ser preenchido na Sprint 2/entrega final.") == 1
    corpo7 = conteudo[conteudo.find("7. Conclusão") :]
    assert "A ser preenchido na Sprint 2/entrega final." in corpo7


def _secao(conteudo: str, inicio: str, fim: str) -> str:
    return conteudo[conteudo.find(inicio) : conteudo.find(fim)]


def test_secoes_4_e_5_tem_grafico_e_texto_de_2_a_4_frases(tmp_path):
    conteudo = gerar_dashboard(diretorio_saida=tmp_path).read_text(encoding="utf-8")
    for inicio, fim, div in (
        ("<h2>4. Erro tipo I</h2>", "<h2>5. Poder</h2>", 'id="grafico_g3"'),
        ("<h2>5. Poder</h2>", "<h2>6. Dados reais</h2>", 'id="grafico_g4"'),
    ):
        secao = _secao(conteudo, inicio, fim)
        assert div in secao
        assert "A ser preenchido" not in secao
        texto = re.search(r'<p class="secao-texto">(.*?)</p>', secao, re.S).group(1)
        frases = [f for f in re.split(r"(?<=[.!?])\s+", " ".join(texto.split())) if f]
        assert 2 <= len(frases) <= 4, frases


def test_secao_6_tem_tabela_com_os_dois_testes(tmp_path):
    conteudo = gerar_dashboard(diretorio_saida=tmp_path).read_text(encoding="utf-8")
    secao = _secao(conteudo, "<h2>6. Dados reais</h2>", "<h2>7. Conclusão</h2>")
    assert "A ser preenchido" not in secao
    assert "<table" in secao
    for texto in ("t de Welch", "Mann-Whitney", "p-valor", "Tamanho do efeito", "Conclusão"):
        assert texto in secao
    # valores de resultado_testes.json
    assert "0,1784" in secao and "0,5692" in secao
    assert "Não rejeita H₀" in secao


def test_dashboard_contem_graficos_plotly(tmp_path):
    caminho = gerar_dashboard(diretorio_saida=tmp_path)
    conteudo = caminho.read_text(encoding="utf-8")
    assert 'id="grafico_g1"' in conteudo
    assert 'id="grafico_g2"' in conteudo
    assert 'id="grafico_g3"' in conteudo
    assert 'id="grafico_g4"' in conteudo
    assert "plotly" in conteudo.lower()


def test_dashboard_duas_execucoes_sao_identicas(tmp_path):
    c1 = gerar_dashboard(diretorio_saida=tmp_path / "exec1")
    c2 = gerar_dashboard(diretorio_saida=tmp_path / "exec2")
    assert c1.read_text(encoding="utf-8") == c2.read_text(encoding="utf-8")


def test_secoes_1_a_3_e_6_tem_texto_de_2_a_4_frases(tmp_path):
    conteudo = gerar_dashboard(diretorio_saida=tmp_path).read_text(encoding="utf-8")
    for inicio, fim in (
        ("<h2>1. Cenário</h2>", "<h2>2. Os dados (G1)</h2>"),
        ("<h2>2. Os dados (G1)</h2>", "<h2>3. Como os testes funcionam (G2)</h2>"),
        ("<h2>3. Como os testes funcionam (G2)</h2>", "<h2>4. Erro tipo I</h2>"),
        ("<h2>6. Dados reais</h2>", "<h2>7. Conclusão</h2>"),
    ):
        secao = _secao(conteudo, inicio, fim)
        texto = re.search(r'<p class="secao-texto">(.*?)</p>', secao, re.S).group(1)
        frases = [f for f in re.split(r"(?<=[.!?])\s+", " ".join(texto.split())) if f]
        assert 2 <= len(frases) <= 4, (inicio, frases)


def test_links_ficam_no_topo_antes_da_primeira_secao(tmp_path):
    conteudo = gerar_dashboard(diretorio_saida=tmp_path).read_text(encoding="utf-8")
    primeira_secao = conteudo.find("<h2>1. Cenário</h2>")
    for link in (LINK_REPO, LINK_PROJECTS, LINK_PAGES):
        assert 0 < conteudo.find(link) < primeira_secao
