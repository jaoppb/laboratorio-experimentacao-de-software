"""Testes do validador S02."""

from __future__ import annotations

import json

import coleta_piloto as cp
import coleta_s02 as cs
import validar_s02 as vs


def _gravar_s02(tmp_path, meta=None, axe=False, repeticoes=4):
    amostras = cs.coletar_amostras_simuladas_s02(n_repeticoes=repeticoes)
    cp.salvar_dados_piloto(
        amostras,
        tmp_path,
        meta=meta,
        telas=cs.TELAS_S02,
        nome_csv=cs.NOME_CSV_S02,
        nome_json=cs.NOME_JSON_S02,
    )
    if axe:
        destino = tmp_path / "axe"
        destino.mkdir()
        for versao in cp.VERSOES:
            for tela, rota in cs.TELAS_S02:
                (destino / f"{versao}_{tela}.json").write_text(
                    json.dumps(
                        {
                            "versao": versao,
                            "tela": tela,
                            "rota": rota,
                            "total_violacoes": 0,
                            "por_impacto": {"critical": 0, "serious": 0, "moderate": 0, "minor": 0, "indefinido": 0},
                            "regras_aprovadas": 22,
                            "violacoes": [],
                        }
                    ),
                    encoding="utf-8",
                )
    return tmp_path


def test_dados_s02_simulados_passam_com_permitir_simulado(tmp_path):
    _gravar_s02(tmp_path, repeticoes=4)
    assert vs.validar_diretorio_s02(tmp_path, repeticoes=4, exigir_real=False) == []
    assert vs.main(["--dir", str(tmp_path), "--repeticoes", "4", "--permitir-simulado"]) == 0


def test_dados_s02_reais_completos_passam(tmp_path):
    meta = {"origem": "real", "releases_moodle": {"4.5_lts": "4.5.16", "5.3_lts": "5.3.1"}}
    _gravar_s02(tmp_path, meta=meta, axe=True, repeticoes=2)
    assert vs.validar_diretorio_s02(tmp_path, repeticoes=2, exigir_real=True) == []
    assert vs.main(["--dir", str(tmp_path), "--repeticoes", "2"]) == 0


def test_dados_s02_sem_axe_falha(tmp_path):
    meta = {"origem": "real", "releases_moodle": {"4.5_lts": "4.5.16", "5.3_lts": "5.3.1"}}
    _gravar_s02(tmp_path, meta=meta, axe=False, repeticoes=2)
    problemas = vs.validar_diretorio_s02(tmp_path, repeticoes=2, exigir_real=True)
    assert sum("axe: arquivo ausente" in p for p in problemas) == 8
    assert vs.main(["--dir", str(tmp_path), "--repeticoes", "2"]) == 1
