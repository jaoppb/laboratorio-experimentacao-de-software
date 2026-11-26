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


@pytest.mark.parametrize(
    ("html", "esperado"),
    [
        ('<script>M.cfg={"sesskey":"abc123XYZ"};</script>', "abc123XYZ"),
        ('<input type="hidden" name="sesskey" value="formTok9">', "formTok9"),
        ('<a href="/logout.php?sesskey=urlTok7">sair</a>', "urlTok7"),
    ],
)
def test_extrair_sesskey_encontra_todos_formatos(html, esperado):
    with _cliente(lambda _req: httpx.Response(200, text=html)) as cliente:
        assert cs.extrair_sesskey(cliente, 6) == esperado


@pytest.mark.parametrize(
    ("status", "html"),
    [
        (500, "erro"),
        (200, "<html>sem sesskey</html>"),
    ],
)
def test_extrair_sesskey_falha_em_status_ou_ausencia(status, html):
    with _cliente(lambda _req: httpx.Response(status, text=html)) as cliente:
        with pytest.raises(cp.ErroColeta):
            cs.extrair_sesskey(cliente, 6)


@pytest.mark.parametrize(
    "url",
    [
        "/mod/quiz/attempt.php?cmid=6",
        "/mod/quiz/attempt.php?attempt=abc&cmid=6",
    ],
)
def test_extrair_attempt_id_falha_quando_ausente_ou_nao_numerico(url):
    with pytest.raises(cp.ErroColeta):
        cs.extrair_attempt_id(url)


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
    with _cliente(lambda _req: httpx.Response(200, text="erro")) as cliente:
        with pytest.raises(cp.ErroColeta, match="não redirecionou"):
            cs.iniciar_tentativa_quiz(cliente, 6, "tok")


def test_coletar_amostras_s02_inicia_mede_descarta_e_isola_tela_publica():
    eventos: list[str] = []
    rotas_publicas: list[str] = []
    rotas_auth: list[str] = []
    descartadas: list[tuple[str, int]] = []
    contador = {"attempt": 100}

    def handler_auth(request: httpx.Request) -> httpx.Response:
        rotas_auth.append(request.url.path)
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

    def handler_publico(request: httpx.Request) -> httpx.Response:
        rotas_publicas.append(request.url.path)
        return httpx.Response(200, content=b"login")

    clientes = {v: _cliente(handler_auth) for v in cp.VERSOES}
    publicos = {v: _cliente(handler_publico) for v in cp.VERSOES}
    amostras = cs.coletar_amostras_s02(
        clientes,
        publicos,
        n_repeticoes=2,
        dormir=lambda _s: None,
        descartar_tentativa=lambda serv, aid: descartadas.append((serv, aid)),
    )

    assert len(amostras) == 2 * len(cs.TELAS_S02) * len(cp.VERSOES)
    tentativas = [a for a in amostras if a["tela"] == "tentativa_quiz"]
    assert len(tentativas) == 4
    assert all(a["rota"] == "/mod/quiz/attempt.php?cmid=6" for a in tentativas)
    assert len(descartadas) == 4
    assert [aid for _, aid in descartadas] == [101, 102, 103, 104]
    assert rotas_publicas == ["/login/index.php"] * 4
    assert "/login/index.php" not in rotas_auth
    assert eventos.count("view") == 2
    pares_start_get = [
        (eventos[i], eventos[i + 1])
        for i, ev in enumerate(eventos)
        if ev.startswith("start:")
    ]
    assert pares_start_get == [
        ("start:101", "get_attempt:101"),
        ("start:102", "get_attempt:102"),
        ("start:103", "get_attempt:103"),
        ("start:104", "get_attempt:104"),
    ]


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
            descartar_tentativa=lambda serv, aid: descartadas.append((serv, aid)),
        )

    assert len(descartadas) == 1
    assert descartadas[0][1] == 77


def test_resolver_alvo_s02_aplica_cmid_e_curso():
    args = cs.construir_parser().parse_args(
        ["--rota-quiz", "/mod/quiz/view.php?id=9", "--rota-curso", "/course/view.php?id=3"]
    )
    urls, telas = cs.resolver_alvo_s02(args)
    assert urls == cp.URLS_PADRAO
    assert dict(telas)["tentativa_quiz"] == "/mod/quiz/attempt.php?cmid=9"
    assert dict(telas)["curso"] == "/course/view.php?id=3"


def test_modo_simulado_s02_grava_arquivos_esperados(tmp_path, monkeypatch):
    simulado = tmp_path / "reais_simulado"
    monkeypatch.setattr(cs, "DIR_DADOS_S02_SIMULADO", simulado)

    assert cs.main(["--simulado", "--repeticoes", "2"]) == 0
    assert (simulado / cs.NOME_CSV_S02).is_file()
    resumo = json.loads((simulado / cs.NOME_JSON_S02).read_text(encoding="utf-8"))
    assert "tentativa_quiz" in resumo["versoes"]["4.5_lts"]
    assert resumo["meta"]["ordem_pares"] == "contrabalanceada_abba"


def test_main_s02_exige_senha_no_ambiente(monkeypatch, capsys):
    monkeypatch.delenv("MOODLE_ALUNO_SENHA", raising=False)
    assert cs.main([]) == 2
    assert "MOODLE_ALUNO_SENHA" in capsys.readouterr().err


def _montar_ambiente_real(monkeypatch, status_attempt: int = 200):
    descartadas: list[tuple[str, int]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/login/index.php":
            return httpx.Response(303, headers={"location": "/my/"})
        if request.url.path == "/mod/quiz/view.php":
            return httpx.Response(200, text='<input name="sesskey" value="sk">')
        if request.url.path == "/mod/quiz/startattempt.php":
            return httpx.Response(303, headers={"location": "/mod/quiz/attempt.php?attempt=15&cmid=6"})
        if request.url.path == "/mod/quiz/attempt.php" and status_attempt != 200:
            return httpx.Response(status_attempt, content=b"erro")
        return httpx.Response(200, content=b"ok")

    class ClienteFalso(httpx.Client):
        def __init__(self, **kwargs):
            kwargs.pop("transport", None)
            super().__init__(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(cp.httpx, "Client", ClienteFalso)
    monkeypatch.setattr(
        cp.subprocess,
        "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, "$release = '9.9';\n", ""),
    )
    monkeypatch.setattr(cs, "descartar_tentativa_quiz", lambda s, a: descartadas.append((s, a)))
    monkeypatch.setattr(cs.time, "sleep", lambda _s: None)
    monkeypatch.setenv("MOODLE_ALUNO_SENHA", "segredo")
    return descartadas


def test_main_s02_real_executa_fluxo(monkeypatch, tmp_path):
    descartadas = _montar_ambiente_real(monkeypatch, status_attempt=200)
    assert cs.main(["--repeticoes", "1", "--saida", str(tmp_path)]) == 0
    assert (tmp_path / cs.NOME_CSV_S02).is_file()
    assert len(descartadas) == 2


def test_main_s02_real_aborta_sem_gravar_em_erro(monkeypatch, tmp_path):
    descartadas = _montar_ambiente_real(monkeypatch, status_attempt=503)
    assert cs.main(["--repeticoes", "1", "--saida", str(tmp_path)]) == 1
    assert list(tmp_path.iterdir()) == []
    assert len(descartadas) == 1


def test_descartar_tentativa_quiz_chama_compose_exec(monkeypatch):
    chamado = {}

    def fake_exec(servico, *comando, **kwargs):
        chamado["servico"] = servico
        chamado["comando"] = comando
        chamado["kwargs"] = kwargs
        return subprocess.CompletedProcess(comando, 0, "", "")

    monkeypatch.setattr(cs, "_compose_exec", fake_exec)
    cs.descartar_tentativa_quiz("moodle45", 55)
    assert chamado["servico"] == "moodle45"
    assert chamado["kwargs"].get("check") is True
    assert "quiz_delete_attempt" in " ".join(chamado["comando"])
    assert chamado["comando"][-1] == "55"
