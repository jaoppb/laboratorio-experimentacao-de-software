"""Testes da análise do piloto: estatísticas contra valores conhecidos e dados versionados."""

from __future__ import annotations

import json

import numpy as np
import pytest

import analisar_piloto as ap
import coleta_piloto as cp

N_PEQUENO = 200  # bootstrap e simulações reduzidos para manter os testes rápidos


@pytest.fixture(scope="module")
def amostras():
    return ap.ler_amostras(cp.DIR_DADOS_PILOTO)


@pytest.fixture(scope="module")
def ttfb(amostras):
    return ap.analisar_ttfb(amostras, n_bootstrap=N_PEQUENO, n_simulacoes=N_PEQUENO)


# --- Δ de Cliff ------------------------------------------------------------ #


def test_delta_cliff_extremos_e_nulo():
    assert ap.delta_cliff([1, 2, 3], [4, 5, 6]) == 1.0
    assert ap.delta_cliff([4, 5, 6], [1, 2, 3]) == -1.0
    assert ap.delta_cliff([1, 2, 3], [1, 2, 3]) == 0.0


def test_delta_cliff_caso_misto():
    # pares (nova, base): 3>1, 3>2, 1<2 e 1=1 -> (2 - 1) / 4
    assert ap.delta_cliff([1, 2], [3, 1]) == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("d", "esperado"),
    [
        (0.0, "desprezível"),
        (0.146, "desprezível"),
        (0.147, "pequeno"),
        (-0.329, "pequeno"),
        (0.33, "médio"),
        (0.473, "médio"),
        (-0.474, "grande"),
        (1.0, "grande"),
    ],
)
def test_classificar_cliff_usa_limiares_de_romano(d, esperado):
    assert ap.classificar_cliff(d) == esperado


def test_ic_bootstrap_cliff_e_reprodutivel_e_contem_o_efeito():
    base, nova = [10, 11, 12, 13, 14, 15], [12, 14, 16, 18, 20, 22]
    d = ap.delta_cliff(base, nova)
    ic1 = ap.ic_bootstrap_cliff(base, nova, np.random.default_rng(1), 500)
    ic2 = ap.ic_bootstrap_cliff(base, nova, np.random.default_rng(1), 500)
    assert ic1 == ic2
    assert -1.0 <= ic1[0] <= d <= ic1[1] <= 1.0


# --- testes de hipótese ---------------------------------------------------- #


def test_mann_whitney_exato_para_grupos_separados():
    resultado = ap.mann_whitney([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
    assert resultado["u"] == 0.0
    assert resultado["p"] == pytest.approx(2 / 252)  # 2 / C(10, 5)


def test_mann_whitney_grupos_iguais_nao_rejeita():
    assert ap.mann_whitney([1, 2, 3, 4], [1, 2, 3, 4])["p"] == pytest.approx(1.0)


def test_ajustar_holm_mantem_ordem_original_e_monotonicidade():
    assert ap.ajustar_holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert ap.ajustar_holm([0.5, 0.9]) == pytest.approx([1.0, 1.0])


def test_wilson_zero_erros_em_40():
    inferior, superior = ap.wilson(0, 40)
    assert inferior == 0.0
    assert superior == pytest.approx(0.0876, abs=1e-3)


def test_wilson_e_simetrico_em_meio():
    inferior, superior = ap.wilson(5, 10)
    assert inferior + superior == pytest.approx(1.0)


def test_comparar_proporcoes_usa_fisher_com_contagem_esperada_baixa():
    resultado = ap.comparar_proporcoes(0, 40, 0, 40)
    assert resultado == {"teste": "fisher_exato", "p": pytest.approx(1.0)}


def test_comparar_proporcoes_fronteira_entre_fisher_e_z():
    # 5 erros em 50 + 5 em 50: contagem esperada mínima = 5 -> Z
    assert ap.comparar_proporcoes(5, 50, 5, 50)["teste"] == "z_duas_proporcoes"
    # 4 erros em 50 + 5 em 50: contagem esperada mínima = 4,5 -> Fisher
    assert ap.comparar_proporcoes(4, 50, 5, 50)["teste"] == "fisher_exato"


def test_comparar_proporcoes_usa_z_com_contagens_altas():
    resultado = ap.comparar_proporcoes(20, 100, 50, 100)
    assert resultado["teste"] == "z_duas_proporcoes"
    assert resultado["p"] < 0.001


def test_p_minimo_wilcoxon():
    assert ap.p_minimo_wilcoxon(4) == pytest.approx(0.125)
    assert ap.p_minimo_wilcoxon(6) == pytest.approx(2 / 64)
    assert ap.p_minimo_wilcoxon(0) == 1.0


# --- suficiência da amostra ------------------------------------------------ #

SEPARADOS = ([10.0, 11.0, 12.0, 13.0, 14.0], [100.0, 101.0, 102.0, 103.0, 104.0])
IGUAIS = ([10.0, 11.0, 12.0, 13.0, 14.0], [10.0, 11.0, 12.0, 13.0, 14.0])


def test_simular_poder_extremos():
    rng = np.random.default_rng(0)
    assert ap.simular_poder(*SEPARADOS, n=10, rng=rng, n_simulacoes=N_PEQUENO) == 1.0
    assert ap.simular_poder(*IGUAIS, n=30, rng=rng, n_simulacoes=1000) < 0.15


def test_estimar_n_necessario_separados_e_iguais():
    rng = np.random.default_rng(0)
    separados = ap.estimar_n_necessario(*SEPARADOS, rng, n_simulacoes=N_PEQUENO)
    assert separados["n_necessario"] == ap.GRADE_N[0]
    assert separados["poder_no_n_planejado"] == 1.0
    iguais = ap.estimar_n_necessario(*IGUAIS, rng, n_simulacoes=N_PEQUENO)
    assert iguais["n_necessario"] is None


@pytest.mark.parametrize(
    ("n_necessario", "faixa"),
    [
        (20, "folgado"),
        (40, "folgado"),
        (60, "suficiente"),
        (80, "suficiente"),
        (100, "insuficiente"),
        (None, "insuficiente"),
    ],
)
def test_classificar_suficiencia(n_necessario, faixa):
    assert ap.classificar_suficiencia(n_necessario) == faixa


# --- M1 sobre os dados versionados ----------------------------------------- #


def test_ttfb_usa_so_repeticoes_warm(ttfb):
    for tela in ttfb.values():
        for descricao in tela["warm"].values():
            assert descricao["n"] == 9


def test_ttfb_ignora_a_repeticao_cold(amostras):
    adulteradas = [
        {**a, "ttfb_ms": 9999.0} if a["cache"] == "cold" else a for a in amostras
    ]
    original = ap.analisar_ttfb(amostras, n_bootstrap=N_PEQUENO, n_simulacoes=N_PEQUENO)
    alterada = ap.analisar_ttfb(adulteradas, n_bootstrap=N_PEQUENO, n_simulacoes=N_PEQUENO)
    for tela in original:
        assert alterada[tela]["warm"] == original[tela]["warm"]
        assert alterada[tela]["delta_cliff"] == original[tela]["delta_cliff"]


def test_ttfb_cold_e_so_descrito(ttfb):
    for tela in ttfb.values():
        assert set(tela["cold"]) == set(cp.VERSOES)
        for descricao in tela["cold"].values():
            assert set(descricao) == {"ttfb_ms", "razao_a_mediana_warm"}


def test_ttfb_holm_nunca_diminui_o_p_bruto(ttfb):
    for tela in ttfb.values():
        mw = tela["mann_whitney"]
        assert mw["p"] <= mw["p_holm"] <= 1.0


def test_ttfb_razao_e_variacao_percentual_sao_consistentes(ttfb):
    for tela in ttfb.values():
        razao = tela["razao_medianas"]
        assert tela["variacao_percentual"] == pytest.approx((razao - 1) * 100, abs=0.1)


def test_razao_desvios_e_nula_quando_a_base_e_constante():
    constante = [50.0] * 9
    variavel = [40.0 + i for i in range(9)]
    tela = ap.comparar_tela(
        constante, variavel, {v: 100.0 for v in cp.VERSOES}, 1, 0, N_PEQUENO, N_PEQUENO
    )
    assert tela["razao_desvios"] is None


def test_ttfb_e_reprodutivel_com_a_mesma_semente(amostras, ttfb):
    de_novo = ap.analisar_ttfb(amostras, n_bootstrap=N_PEQUENO, n_simulacoes=N_PEQUENO)
    assert de_novo == ttfb


def test_mudar_o_bootstrap_nao_altera_a_suficiencia(amostras, ttfb):
    outro = ap.analisar_ttfb(amostras, n_bootstrap=N_PEQUENO // 2, n_simulacoes=N_PEQUENO)
    for tela in ttfb:
        assert outro[tela]["suficiencia"] == ttfb[tela]["suficiencia"]


def test_suficiencia_e_internamente_coerente(ttfb):
    for tela in ttfb.values():
        suf = tela["suficiencia"]
        curva = {int(n): poder for n, poder in suf["poder_por_n"].items()}
        esperado = next((n for n, poder in curva.items() if poder >= ap.PODER_ALVO), None)
        assert suf["n_necessario"] == esperado
        assert suf["faixa"] == ap.classificar_suficiencia(suf["n_necessario"])
        assert suf["poder_no_n_planejado"] == curva[ap.N_PLANEJADO]


# --- M3 e M4 ---------------------------------------------------------------- #


def test_erros_do_piloto_real_sao_zero(amostras):
    erros = ap.analisar_erros(amostras)
    for versao in cp.VERSOES:
        assert erros["por_versao"][versao]["erros"] == 0
        assert erros["por_versao"][versao]["n"] == 40
    assert erros["comparacao"]["teste"] == "fisher_exato"


@pytest.mark.parametrize(("status", "contado"), [(499, 0), (500, 1), (599, 1)])
def test_erros_fronteiras_da_regra_5xx(amostras, status, contado):
    alteradas = [dict(a) for a in amostras]
    next(a for a in alteradas if a["versao"] == "5.3_lts")["status_http"] = status
    assert ap.analisar_erros(alteradas)["por_versao"]["5.3_lts"]["erros"] == contado


def test_erros_conta_apenas_status_5xx(amostras):
    alteradas = [dict(a) for a in amostras]
    primeira = next(a for a in alteradas if a["versao"] == "5.3_lts")
    primeira["status_http"] = 503
    segunda = next(
        a for a in alteradas if a["versao"] == "5.3_lts" and a is not primeira
    )
    segunda["status_http"] = 404  # 4xx não entra em M3
    erros = ap.analisar_erros(alteradas)
    assert erros["por_versao"]["5.3_lts"]["erros"] == 1
    assert erros["por_versao"]["4.5_lts"]["erros"] == 0


def _relatorios(violacoes_53, violacoes_45=(0, 0, 0, 0)):
    relatorios = {}
    for indice, (tela, _) in enumerate(cp.TELAS):
        for versao, total in (("4.5_lts", violacoes_45[indice]), ("5.3_lts", violacoes_53[indice])):
            relatorios[(versao, tela)] = {
                "total_violacoes": total,
                "por_impacto": {"serious": total},
            }
    return relatorios


def test_acessibilidade_sem_diferencas_nao_aplica_wilcoxon():
    resultado = ap.analisar_acessibilidade(_relatorios((0, 0, 0, 0)))
    assert resultado["wilcoxon"]["aplicavel"] is False
    assert resultado["pares_com_diferenca"] == 0
    assert resultado["violacoes_por_severidade"]["4.5_lts"]["serious"] == 0


def test_acessibilidade_com_diferencas_aplica_wilcoxon():
    resultado = ap.analisar_acessibilidade(_relatorios((1, 2, 3, 4)))
    assert resultado["wilcoxon"]["aplicavel"] is True
    assert resultado["wilcoxon"]["p"] == pytest.approx(0.125)
    assert resultado["p_minimo_wilcoxon"] == pytest.approx(0.125)
    assert resultado["violacoes_por_severidade"]["5.3_lts"]["serious"] == 10


def test_acessibilidade_com_diferencas_mistas_descarta_pares_nulos():
    resultado = ap.analisar_acessibilidade(_relatorios((0, 0, 1, 2)))
    assert resultado["pares_com_diferenca"] == 2
    assert resultado["p_minimo_wilcoxon"] == pytest.approx(0.5)
    assert resultado["wilcoxon"]["aplicavel"] is True
    assert resultado["wilcoxon"]["p"] >= resultado["p_minimo_wilcoxon"]


def test_acessibilidade_dos_dados_versionados_nao_tem_violacoes():
    resultado = ap.analisar_acessibilidade(ap.ler_axe(cp.DIR_DADOS_PILOTO))
    assert resultado["wilcoxon"]["aplicavel"] is False


# --- pipeline completo -------------------------------------------------------- #


def test_json_versionado_bate_com_o_recalculo_dos_dados(ttfb):
    versionado = json.loads((cp.DIR_DADOS_PILOTO / ap.ARQUIVO_SAIDA).read_text(encoding="utf-8"))
    for tela, recalculado in ttfb.items():
        salvo = versionado["ttfb"][tela]
        # a parte determinística (sem bootstrap nem simulação) deve coincidir
        for chave in ("warm", "razao_medianas", "variacao_percentual", "razao_desvios", "cold"):
            assert salvo[chave] == recalculado[chave]
        assert salvo["delta_cliff"]["d"] == recalculado["delta_cliff"]["d"]
        assert salvo["mann_whitney"] == recalculado["mann_whitney"]


def test_json_versionado_tem_m3_e_m4_iguais_ao_recalculo(amostras):
    versionado = json.loads((cp.DIR_DADOS_PILOTO / ap.ARQUIVO_SAIDA).read_text(encoding="utf-8"))
    assert versionado["erros_http"] == ap.analisar_erros(amostras)
    recalculado = ap.analisar_acessibilidade(ap.ler_axe(cp.DIR_DADOS_PILOTO))
    assert versionado["acessibilidade"] == recalculado


def test_json_versionado_tem_suficiencia_coerente():
    versionado = json.loads((cp.DIR_DADOS_PILOTO / ap.ARQUIVO_SAIDA).read_text(encoding="utf-8"))
    for tela in versionado["ttfb"].values():
        suf = tela["suficiencia"]
        curva = {int(n): poder for n, poder in suf["poder_por_n"].items()}
        esperado = next((n for n, poder in curva.items() if poder >= ap.PODER_ALVO), None)
        assert suf["n_necessario"] == esperado
        assert suf["faixa"] == ap.classificar_suficiencia(suf["n_necessario"])
        assert suf["poder_no_n_planejado"] == curva[ap.N_PLANEJADO]


def test_analisar_recusa_dados_invalidos(tmp_path):
    cp.salvar_dados_piloto(cp.coletar_amostras_simuladas(), tmp_path)  # sem meta real
    with pytest.raises(ValueError, match="inválidos"):
        ap.analisar(tmp_path)


def test_main_grava_json_e_imprime_resumo(tmp_path, capsys):
    saida = tmp_path / "analise.json"
    codigo = ap.main(
        ["--saida", str(saida), "--n-bootstrap", str(N_PEQUENO), "--n-simulacoes", str(N_PEQUENO)]
    )
    assert codigo == 0
    analise = json.loads(saida.read_text(encoding="utf-8"))
    assert set(analise) == {"meta", "ttfb", "erros_http", "acessibilidade"}
    assert analise["meta"]["semente"] == ap.SEMENTE_PADRAO
    resumo = capsys.readouterr().out
    assert all(tela in resumo for tela, _ in cp.TELAS)


def test_main_falha_com_dados_invalidos(tmp_path, capsys):
    cp.salvar_dados_piloto(cp.coletar_amostras_simuladas(), tmp_path)
    assert ap.main(["--dir", str(tmp_path)]) == 1
    assert "inválidos" in capsys.readouterr().err
