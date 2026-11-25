"""Testes da coleta S02: ciclo de tentativa do quiz, runner e modo simulado (sem rede)."""

from __future__ import annotations

import json
import subprocess

import httpx
import pytest

import coleta_piloto as cp
import coleta_s02 as cs


def _cliente(handler) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://moodle.test",
        follow_redirects=True,
    )


def test_extrair_cmid_aceita_id_ou_cmid_e_rejeita_invalido():
    assert cs.extrair_cmid("/mod/quiz/view.php?id=6") == 6
    assert cs.extrair_cmid("/mod/quiz/attempt.php?cmid=14") == 14
    with pytest.raises(cp.ErroColeta):
        cs.extrair_cmid("/mod/quiz/view.php")


def test_extrair_sesskey_encontra_json_ou_input():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text='<script>M.cfg={"sesskey":"abc123XYZ"};</script>')

    with _cliente(handler) as cliente:
        assert cs.extrair_sesskey(cliente, 6) == "abc123XYZ"


def test_iniciar_tentativa_quiz_retorna_attempt_id_do_redirect():
    recebido = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mod/quiz/startattempt.php":
            recebido.update(dict(httpx.QueryParams(request.content.decode())))
            return httpx.Response(
                303, headers={"location": "http://moodle.test/mod/quiz/attempt.php?attempt=42&cmid=6"}
            )
        return httpx.Response(200, text="nao deveria seguir redirect")

    with _cliente(handler) as cliente:
        attempt_id = cs.iniciar_tentativa_quiz(cliente, 6, "tok")

    assert attempt_id == 42
    assert recebido == {"cmid": "6", "sesskey": "tok"}


def test_iniciar_tentativa_quiz_falha_sem_redirect():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="erro")

    with _cliente(handler) as cliente:
        with pytest.raises(cp.ErroColeta, match="não redirecionou"):
            cs.iniciar_tentativa_quiz(cliente, 6, "tok")


def test_coletar_amostras_s02_inicia_mede_e_descarta_tentativa_mesmo_em_erro():
    eventos: list[str] = []
    descartadas: list[tuple[str, int]] = []
    contador = {"attempt": 100}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mod/quiz/view.php":
            eventos.append("view")
            return httpx.Response(200, text='<input name="sesskey" value="sk1">')
        if request.url.path == "/mod/quiz/startattempt.php":
            contador["attempt"] += 1
            aid = contador["attempt"]
            eventos.append(f"start:{aid}")
            return httpx.Response(
                303, headers={"location": f"/mod/quiz/attempt.php?attempt={aid}&cmid=6"}
            )
        if request.url.path == "/mod/quiz/attempt.php":
            eventos.append(f"get_attempt:{request.url.params['attempt']}")
            return httpx.Response(200, content=b"questoes")
        return httpx.Response(200, content=b"ok")

    clientes = {v: _cliente(handler) for v in cp.VERSOES}
    publicos = {v: _cliente(handler) for v in cp.VERSOES}
    amostras = cs.coletar_amostras_s02(
        clientes,
        publicos,
        n_repeticoes=2,
        dormir=lambda _s: None,
        cmid=6,
        descartar_tentativa=lambda serv, aid: descartadas.append((serv, aid)),
    )

    assert len(amostras) == 2 * len(cs.TELAS_S02) * len(cp.VERSOES)
    tentativas = [a for a in amostras if a["tela"] == "tentativa_quiz"]
    assert len(tentativas) == 4
    assert all(a["rota"] == "/mod/quiz/attempt.php?cmid=6" for a in tentativas)
    assert len(descartadas) == 4
    assert [aid for _, aid in descartadas] == [101, 102, 103, 104]
    # sesskey foi extraído uma vez por versão, não 4 vezes
    assert eventos.count("view") == 2


def test_coletar_amostras_s02_descarta_tentativa_quando_attempt_retorna_500():
    descartadas: list[tuple[str, int]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mod/quiz/view.php":
            return httpx.Response(200, text='<input name="sesskey" value="sk1">')
        if request.url.path == "/mod/quiz/startattempt.php":
            return httpx.Response(
                303, headers={"location": "/mod/quiz/attempt.php?attempt=77&cmid=6"}
            )
        if request.url.path == "/mod/quiz/attempt.php":
            return httpx.Response(500, content=b"erro")
        return httpx.Response(200, content=b"ok")

    clientes = {v: _cliente(handler) for v in cp.VERSOES}
    with pytest.raises(cp.ErroColeta, match="status 500"):
        cs.coletar_amostras_s02(
            clientes,
            clientes,
            n_repeticoes=1,
            dormir=lambda _s: None,
            cmid=6,
            descartar_tentativa=lambda serv, aid: descartadas.append((serv, aid)),
        )

    assert len(descartadas) == 1
    assert descartadas[0][1] == 77


def test_modo_simulado_s02_grava_arquivos_esperados(tmp_path, monkeypatch):
    simulado = tmp_path / "reais_simulado"
    monkeypatch.setattr(cs, "DIR_DADOS_S02_SIMULADO", simulado)

    assert cs.main(["--simulado", "--repeticoes", "2"]) == 0
    assert (simulado / cs.NOME_CSV_S02).is_file()
    resumo = json.loads((simulado / cs.NOME_JSON_S02).read_text(encoding="utf-8"))
    assert "tentativa_quiz" in resumo["versoes"]["4.5_lts"]
    assert resumo["meta"]["ordem_pares"] == "contrabalanceada_abba"


def test_descartar_tentativa_quiz_chama_compose_exec(monkeypatch):
    chamado = {}

    def fake_exec(servico, *comando, **kwargs):
        chamado["servico"] = servico
        chamado["comando"] = comando
        return subprocess.CompletedProcess(comando, 0, "", "")

    monkeypatch.setattr(cs, "_compose_exec", fake_exec)
    cs.descartar_tentativa_quiz("moodle45", 55)
    assert chamado["servico"] == "moodle45"
    assert chamado["comando"][-1] == "55"
