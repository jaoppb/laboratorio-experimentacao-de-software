"""Testes do validador: dados bons passam e cada defeito é apontado."""

from __future__ import annotations

import csv
import json

import coleta_piloto as cp
import validar_piloto as vp


def _gravar(tmp_path, amostras=None, resumo=None):
    amostras = amostras or cp.coletar_amostras_simuladas()
    cp.salvar_dados_piloto(amostras, tmp_path)
    if resumo is not None:
        (tmp_path / "resumo_piloto.json").write_text(json.dumps(resumo), encoding="utf-8")
    return tmp_path


def _linhas(tmp_path):
    return vp.ler_csv(tmp_path / "amostra_piloto.csv")


def test_dados_validos_passam(tmp_path):
    assert vp.validar_diretorio(_gravar(tmp_path)) == []
    assert vp.main(["--dir", str(tmp_path)]) == 0


def test_arquivo_ausente(tmp_path):
    assert vp.validar_diretorio(tmp_path)[0].startswith("arquivo ausente")
    assert vp.main(["--dir", str(tmp_path)]) == 1


def test_colunas_inesperadas(tmp_path):
    colunas, linhas = _linhas(_gravar(tmp_path))
    problemas = vp.validar_amostras(["a"] + colunas[1:], linhas)
    assert "colunas inesperadas" in problemas[0]


def test_linha_faltando_aponta_contagem_total_e_por_grupo(tmp_path):
    colunas, linhas = _linhas(_gravar(tmp_path))
    problemas = vp.validar_amostras(colunas, linhas[:-1])
    assert any("79 linhas" in p for p in problemas)
    assert any("9 amostras" in p for p in problemas)


def test_status_diferente_de_200(tmp_path):
    colunas, linhas = _linhas(_gravar(tmp_path))
    linhas[3]["status_http"] = "302"
    assert any("status_http 302" in p for p in vp.validar_amostras(colunas, linhas))


def test_ttfb_maior_que_tempo_total(tmp_path):
    colunas, linhas = _linhas(_gravar(tmp_path))
    linhas[0]["ttfb_ms"] = "9999"
    assert any("maior que tempo_total_ms" in p for p in vp.validar_amostras(colunas, linhas))


def test_valor_nao_numerico(tmp_path):
    colunas, linhas = _linhas(_gravar(tmp_path))
    linhas[0]["ttfb_ms"] = "abc"
    assert any("não numérico" in p for p in vp.validar_amostras(colunas, linhas))


def test_cache_frio_so_na_primeira_repeticao(tmp_path):
    colunas, linhas = _linhas(_gravar(tmp_path))
    linhas[-1]["cache"] = "cold"
    assert any("cache 'cold'" in p for p in vp.validar_amostras(colunas, linhas))


def test_ordem_nao_alternada(tmp_path):
    colunas, linhas = _linhas(_gravar(tmp_path))
    linhas[1]["versao"] = linhas[0]["versao"]
    assert any("não alternada" in p for p in vp.validar_amostras(colunas, linhas))


def test_resumo_divergente_do_csv(tmp_path):
    resumo = cp.calcular_resumo_estatistico(cp.coletar_amostras_simuladas())
    resumo["versoes"]["4.5_lts"]["login"]["mediana_ms"] += 50
    problemas = vp.validar_diretorio(_gravar(tmp_path, resumo=resumo))
    assert any("4.5_lts/login/mediana_ms" in p for p in problemas)


def test_resumo_aceita_chave_meta(tmp_path):
    amostras = cp.coletar_amostras_simuladas()
    cp.salvar_dados_piloto(amostras, tmp_path, meta={"origem": "teste"})
    assert vp.validar_diretorio(tmp_path) == []


def test_csv_gravado_tem_cabecalho_esperado(tmp_path):
    caminho_csv, _ = cp.salvar_dados_piloto(cp.coletar_amostras_simuladas(), tmp_path)
    with open(caminho_csv, newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == list(cp.COLUNAS_CSV)
