"""Testes do validador: dados bons passam e cada defeito é apontado."""

from __future__ import annotations

import copy
import csv
import json

import pytest

import coleta_piloto as cp
import validar_piloto as vp

META_REAL = {
    "origem": "real",
    "releases_moodle": {"4.5_lts": "4.5.16", "5.3_lts": "5.3.1"},
}


def _gravar(tmp_path, meta=None, axe=False):
    cp.salvar_dados_piloto(cp.coletar_amostras_simuladas(), tmp_path, meta=meta)
    if axe:
        _gravar_axe(tmp_path / "axe")
    return tmp_path


def _gravar_axe(destino):
    destino.mkdir()
    for versao in cp.VERSOES:
        for tela, rota in cp.TELAS:
            (destino / f"{versao}_{tela}.json").write_text(
                json.dumps(
                    {
                        "versao": versao,
                        "tela": tela,
                        "rota": rota,
                        "total_violacoes": 1,
                        "por_impacto": {"serious": 1},
                        "regras_aprovadas": 20,
                        "violacoes": [{"id": "x"}],
                    }
                ),
                encoding="utf-8",
            )


def _linhas(tmp_path):
    return vp.ler_csv(tmp_path / "amostra_piloto.csv")


# --- dados versionados ----------------------------------------------------- #


def test_dados_versionados_do_piloto_sao_validos():
    assert vp.validar_diretorio(cp.DIR_DADOS_PILOTO) == []


# --- CSV ------------------------------------------------------------------- #


def test_dados_validos_passam(tmp_path):
    assert vp.validar_diretorio(_gravar(tmp_path), exigir_real=False) == []
    assert vp.main(["--dir", str(tmp_path), "--permitir-simulado"]) == 0


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


@pytest.mark.parametrize(
    ("indice", "campo", "valor", "mensagem"),
    [
        (3, "status_http", "302", "status_http 302"),
        (0, "ttfb_ms", "9999", "maior que tempo_total_ms"),
        (0, "ttfb_ms", "0", "ttfb_ms não positivo"),
        (0, "tamanho_bytes", "0", "tamanho_bytes não positivo"),
        (0, "ttfb_ms", "abc", "não numérico"),
        (0, "id", "99", "fora de sequência"),
        (0, "versao", "6.0", "versão desconhecida"),
        (0, "tela", "inexistente", "tela desconhecida"),
        (0, "repeticao", "11", "fora de 1..10"),
        (1, "repeticao", "0", "fora de 1..10"),
        (79, "cache", "cold", "cache 'cold'"),
        (1, "versao", "4.5_lts", "não alternada"),
        (2, "rota", "/outra/", "rotas diferentes"),
    ],
)
def test_cada_defeito_do_csv_e_apontado(tmp_path, indice, campo, valor, mensagem):
    colunas, linhas = _linhas(_gravar(tmp_path))
    linhas[indice][campo] = valor
    assert any(mensagem in p for p in vp.validar_amostras(colunas, linhas))


def test_ttfb_igual_ao_tempo_total_e_aceito(tmp_path):
    colunas, linhas = _linhas(_gravar(tmp_path))
    linhas[0]["ttfb_ms"] = linhas[0]["tempo_total_ms"]
    assert vp.validar_amostras(colunas, linhas) == []


def test_cache_warm_na_primeira_repeticao_e_apontado(tmp_path):
    colunas, linhas = _linhas(_gravar(tmp_path))
    linhas[0]["cache"] = "warm"
    assert any("cache 'warm'" in p for p in vp.validar_amostras(colunas, linhas))


# --- resumo ---------------------------------------------------------------- #


def test_resumo_divergente_do_csv(tmp_path):
    _gravar(tmp_path)
    caminho = tmp_path / "resumo_piloto.json"
    resumo = json.loads(caminho.read_text(encoding="utf-8"))
    resumo["versoes"]["4.5_lts"]["login"]["mediana_ms"] += 50
    caminho.write_text(json.dumps(resumo), encoding="utf-8")

    problemas = vp.validar_diretorio(tmp_path, exigir_real=False)
    assert any("4.5_lts/login/mediana_ms" in p for p in problemas)


def test_resumo_sem_celula_ou_metrica(tmp_path):
    amostras = cp.coletar_amostras_simuladas()
    resumo = cp.calcular_resumo_estatistico(amostras)
    sem_celula = copy.deepcopy(resumo)
    del sem_celula["versoes"]["5.3_lts"]["curso"]
    sem_metrica = copy.deepcopy(resumo)
    del sem_metrica["versoes"]["4.5_lts"]["login"]["p95_ms"]
    tipadas = [vp.tipar_linha({k: str(v) for k, v in a.items()}) for a in amostras]

    assert any("5.3_lts/curso ausente" in p for p in vp.validar_resumo(tipadas, sem_celula))
    assert any("4.5_lts/login/p95_ms" in p for p in vp.validar_resumo(tipadas, sem_metrica))


# --- origem e axe ---------------------------------------------------------- #


def test_dados_reais_completos_passam(tmp_path):
    assert vp.validar_diretorio(_gravar(tmp_path, META_REAL, axe=True)) == []


def test_dados_simulados_sao_recusados_por_padrao(tmp_path):
    problemas = vp.validar_diretorio(
        _gravar(tmp_path, {"origem": "simulado"}, axe=True)
    )
    assert any("meta.origem" in p for p in problemas)


def test_release_ausente_ou_desconhecido(tmp_path):
    meta = {"origem": "real", "releases_moodle": {"4.5_lts": ""}}
    problemas = vp.validar_diretorio(_gravar(tmp_path, meta, axe=True))
    assert sum("releases_moodle" in p for p in problemas) == 2


def test_axe_ausente_e_apontado(tmp_path):
    problemas = vp.validar_diretorio(_gravar(tmp_path, META_REAL))
    assert sum("axe: arquivo ausente" in p for p in problemas) == 8


def test_axe_com_contagens_inconsistentes(tmp_path):
    _gravar(tmp_path, META_REAL, axe=True)
    alvo = tmp_path / "axe" / "4.5_lts_login.json"
    dados = json.loads(alvo.read_text(encoding="utf-8"))
    dados["total_violacoes"] = 5
    dados["regras_aprovadas"] = 0
    alvo.write_text(json.dumps(dados), encoding="utf-8")

    problemas = vp.validar_axe(tmp_path / "axe")
    assert any("total_violacoes != len" in p for p in problemas)
    assert any("sem regras aprovadas" in p for p in problemas)


def test_axe_com_versao_ou_tela_trocadas(tmp_path):
    _gravar(tmp_path, META_REAL, axe=True)
    alvo = tmp_path / "axe" / "4.5_lts_login.json"
    dados = json.loads(alvo.read_text(encoding="utf-8"))
    dados["tela"] = "curso"
    alvo.write_text(json.dumps(dados), encoding="utf-8")

    assert any("divergentes" in p for p in vp.validar_axe(tmp_path / "axe"))


def test_axe_com_por_impacto_que_nao_soma_o_total(tmp_path):
    _gravar(tmp_path, META_REAL, axe=True)
    alvo = tmp_path / "axe" / "5.3_lts_curso.json"
    dados = json.loads(alvo.read_text(encoding="utf-8"))
    dados["por_impacto"] = {"serious": 2}
    alvo.write_text(json.dumps(dados), encoding="utf-8")

    assert any("não soma o total" in p for p in vp.validar_axe(tmp_path / "axe"))


def test_axe_sem_campos_obrigatorios_ou_json_invalido(tmp_path):
    _gravar(tmp_path, META_REAL, axe=True)
    sem_campos = tmp_path / "axe" / "5.3_lts_curso.json"
    dados = json.loads(sem_campos.read_text(encoding="utf-8"))
    del dados["violacoes"]
    sem_campos.write_text(json.dumps(dados), encoding="utf-8")
    (tmp_path / "axe" / "4.5_lts_login.json").write_text("{truncado", encoding="utf-8")

    problemas = vp.validar_axe(tmp_path / "axe")
    assert any("sem violacoes/por_impacto" in p for p in problemas)
    assert any("não é JSON válido" in p for p in problemas)


def test_csv_gravado_tem_cabecalho_esperado(tmp_path):
    caminho_csv, _ = cp.salvar_dados_piloto(cp.coletar_amostras_simuladas(), tmp_path)
    with open(caminho_csv, newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == list(cp.COLUNAS_CSV)
