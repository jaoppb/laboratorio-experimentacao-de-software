"""Testes da coleta piloto: medição HTTP, alternância e persistência (sem rede)."""

from __future__ import annotations

import csv
import json

import httpx
import pytest

import coleta_piloto as cp


def _cliente(handler) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://moodle.test",
        follow_redirects=True,
    )


def _handler_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=b"x" * 123)


def test_medir_requisicao_registra_status_tamanho_e_tempos():
    with _cliente(_handler_ok) as cliente:
        medida = cp.medir_requisicao(cliente, "/my/")

    assert medida["status_http"] == 200
    assert medida["tamanho_bytes"] == 123
    assert 0 <= medida["ttfb_ms"] <= medida["tempo_total_ms"]


def test_coletar_amostras_reais_alterna_versoes_e_marca_cache():
    clientes = {v: _cliente(_handler_ok) for v in cp.VERSOES}
    amostras = cp.coletar_amostras_reais(
        clientes, n_repeticoes=3, dormir=lambda _s: None
    )

    assert len(amostras) == 3 * len(cp.TELAS) * len(cp.VERSOES)
    assert [a["id"] for a in amostras] == list(range(1, len(amostras) + 1))
    versoes = [a["versao"] for a in amostras]
    assert all(a != b for a, b in zip(versoes, versoes[1:]))
    assert {a["cache"] for a in amostras if a["repeticao"] == 1} == {"cold"}
    assert {a["cache"] for a in amostras if a["repeticao"] > 1} == {"warm"}
    assert [list(a) for a in amostras][0] == list(cp.COLUNAS_CSV)


def test_coletar_amostras_reais_aborta_com_status_diferente_de_200():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"erro")

    clientes = {v: _cliente(handler) for v in cp.VERSOES}
    with pytest.raises(cp.ErroColeta, match="status 500"):
        cp.coletar_amostras_reais(clientes, n_repeticoes=1, dormir=lambda _s: None)


def test_autenticar_detecta_login_recusado():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, text='<div id="loginerrormessage">invalido</div>')
        return httpx.Response(200, text='<input name="logintoken" value="abc">')

    with _cliente(handler) as cliente:
        with pytest.raises(cp.ErroColeta):
            cp.autenticar(cliente, "aluno_teste_1", "errada")


def test_autenticar_envia_logintoken_e_aceita_redirecionamento():
    recebido = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            recebido.update(dict(httpx.QueryParams(request.content.decode())))
            return httpx.Response(303, headers={"location": "/my/"})
        if request.url.path == "/my/":
            return httpx.Response(200, text="painel")
        return httpx.Response(200, text='<input name="logintoken"  value="tok123">')

    with _cliente(handler) as cliente:
        cp.autenticar(cliente, "aluno_teste_1", "segredo")

    assert recebido["logintoken"] == "tok123"
    assert recebido["username"] == "aluno_teste_1"


def test_salvar_dados_piloto_grava_csv_json_e_meta(tmp_path):
    amostras = cp.coletar_amostras_simuladas(n_repeticoes=10)
    caminho_csv, caminho_json = cp.salvar_dados_piloto(
        amostras, tmp_path, meta={"origem": "teste"}
    )

    with open(caminho_csv, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        assert leitor.fieldnames == list(cp.COLUNAS_CSV)
        assert len(list(leitor)) == 80

    resumo = json.loads(caminho_json.read_text(encoding="utf-8"))
    assert resumo["meta"] == {"origem": "teste"}
    assert resumo["versoes"]["4.5_lts"]["login"]["n"] == 10


def test_salvar_dados_piloto_recusa_lista_vazia(tmp_path):
    with pytest.raises(cp.ErroColeta):
        cp.salvar_dados_piloto([], tmp_path)


def test_modo_simulado_nunca_grava_no_diretorio_de_dados_reais(tmp_path):
    assert cp.main(["--simulado", "--saida", str(tmp_path)]) == 0
    assert (tmp_path / "amostra_piloto.csv").is_file()
    assert cp.DIR_DADOS_SIMULADO != cp.DIR_DADOS_PILOTO


def test_modo_real_exige_senha_no_ambiente(monkeypatch, capsys):
    monkeypatch.delenv("MOODLE_ALUNO_SENHA", raising=False)
    assert cp.main([]) == 2
    assert "MOODLE_ALUNO_SENHA" in capsys.readouterr().err


def test_tela_publica_usa_cliente_sem_sessao():
    vistos: dict[str, list[str]] = {"auth": [], "publico": []}

    def handler_para(papel: str):
        def handler(request: httpx.Request) -> httpx.Response:
            vistos[papel].append(request.url.path)
            return httpx.Response(200, content=b"ok")

        return handler

    clientes = {v: _cliente(handler_para("auth")) for v in cp.VERSOES}
    publicos = {v: _cliente(handler_para("publico")) for v in cp.VERSOES}
    cp.coletar_amostras_reais(clientes, cp.TELAS, publicos, 1, dormir=lambda _s: None)

    assert vistos["publico"] == ["/login/index.php"] * len(cp.VERSOES)
    assert "/login/index.php" not in vistos["auth"]
    assert len(vistos["auth"]) == (len(cp.TELAS) - 1) * len(cp.VERSOES)
