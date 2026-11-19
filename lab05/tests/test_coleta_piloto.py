"""Testes da coleta piloto: medição HTTP, alternância, persistência e fluxo do main (sem rede)."""

from __future__ import annotations

import csv
import json
import subprocess

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


def _clientes_ok() -> tuple[dict, dict]:
    return (
        {v: _cliente(_handler_ok) for v in cp.VERSOES},
        {v: _cliente(_handler_ok) for v in cp.VERSOES},
    )


# --- medição -------------------------------------------------------------- #


def test_medir_requisicao_registra_status_e_tamanho():
    with _cliente(_handler_ok) as cliente:
        medida = cp.medir_requisicao(cliente, "/my/")

    assert medida["status_http"] == 200
    assert medida["tamanho_bytes"] == 123
    assert 0 <= medida["ttfb_ms"] <= medida["tempo_total_ms"]


def test_ttfb_e_o_tempo_ate_os_cabecalhos_e_nao_ate_o_fim_do_corpo(monkeypatch):
    relogio = {"t": 0.0}
    monkeypatch.setattr(cp.time, "perf_counter", lambda: relogio["t"])

    class CorpoLento(httpx.SyncByteStream):
        def __iter__(self):
            relogio["t"] += 0.300  # 300 ms para transferir o corpo
            yield b"corpo"

    def handler(request: httpx.Request) -> httpx.Response:
        relogio["t"] += 0.050  # 50 ms até os cabeçalhos
        return httpx.Response(200, stream=CorpoLento())

    with _cliente(handler) as cliente:
        medida = cp.medir_requisicao(cliente, "/my/")

    assert medida["ttfb_ms"] == pytest.approx(50.0)
    assert medida["tempo_total_ms"] == pytest.approx(350.0)
    assert medida["tamanho_bytes"] == 5


# --- loop de coleta -------------------------------------------------------- #


def test_coletar_amostras_reais_alterna_versoes_e_marca_cache():
    clientes, publicos = _clientes_ok()
    amostras = cp.coletar_amostras_reais(
        clientes, publicos, n_repeticoes=3, dormir=lambda _s: None
    )

    assert len(amostras) == 3 * len(cp.TELAS) * len(cp.VERSOES)
    assert [a["id"] for a in amostras] == list(range(1, len(amostras) + 1))
    versoes = [a["versao"] for a in amostras]
    assert all(a != b for a, b in zip(versoes, versoes[1:]))
    assert {a["cache"] for a in amostras if a["repeticao"] == 1} == {"cold"}
    assert {a["cache"] for a in amostras if a["repeticao"] > 1} == {"warm"}
    assert list(amostras[0]) == list(cp.COLUNAS_CSV)


def test_coletar_amostras_reais_aplica_pausa_entre_requisicoes():
    clientes, publicos = _clientes_ok()
    pausas: list[float] = []
    cp.coletar_amostras_reais(
        clientes, publicos, n_repeticoes=1, pausa_ms=(200, 500), dormir=pausas.append
    )

    assert len(pausas) == len(cp.TELAS) * len(cp.VERSOES)
    assert all(0.2 <= p <= 0.5 for p in pausas)


def test_coletar_amostras_reais_aborta_com_status_diferente_de_200():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"erro")

    clientes = {v: _cliente(handler) for v in cp.VERSOES}
    with pytest.raises(cp.ErroColeta, match="status 500"):
        cp.coletar_amostras_reais(
            clientes, clientes, n_repeticoes=1, dormir=lambda _s: None
        )


def test_tela_publica_usa_cliente_sem_sessao():
    vistos: dict[str, list[str]] = {"auth": [], "publico": []}

    def handler_para(papel: str):
        def handler(request: httpx.Request) -> httpx.Response:
            vistos[papel].append(request.url.path)
            return httpx.Response(200, content=b"ok")

        return handler

    clientes = {v: _cliente(handler_para("auth")) for v in cp.VERSOES}
    publicos = {v: _cliente(handler_para("publico")) for v in cp.VERSOES}
    cp.coletar_amostras_reais(clientes, publicos, cp.TELAS, 1, dormir=lambda _s: None)

    assert vistos["publico"] == ["/login/index.php"] * len(cp.VERSOES)
    assert "/login/index.php" not in vistos["auth"]
    assert len(vistos["auth"]) == (len(cp.TELAS) - 1) * len(cp.VERSOES)


def test_simulado_tem_o_mesmo_formato_do_real():
    simuladas = cp.coletar_amostras_simuladas(n_repeticoes=2)
    clientes, publicos = _clientes_ok()
    reais = cp.coletar_amostras_reais(
        clientes, publicos, n_repeticoes=2, dormir=lambda _s: None
    )

    assert [list(a) for a in simuladas] == [list(a) for a in reais]
    assert [(a["id"], a["versao"], a["tela"], a["cache"]) for a in simuladas] == [
        (a["id"], a["versao"], a["tela"], a["cache"]) for a in reais
    ]


# --- autenticação ---------------------------------------------------------- #


def test_autenticar_detecta_login_recusado():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, text='<div id="loginerrormessage">invalido</div>')
        return httpx.Response(200, text='<input name="logintoken" value="abc">')

    with _cliente(handler) as cliente:
        with pytest.raises(cp.ErroColeta):
            cp.autenticar(cliente, "aluno_teste_1", "errada")


def test_autenticar_detecta_permanencia_na_pagina_de_login():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<form>sem token e sem aviso</form>")

    with _cliente(handler) as cliente:
        # httpx.MockTransport mantém a URL em /login/index.php após o POST.
        with pytest.raises(cp.ErroColeta):
            cp.autenticar(cliente, "aluno_teste_1", "x")


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


def test_autenticar_sem_logintoken_envia_so_credenciais():
    recebido = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            recebido.update(dict(httpx.QueryParams(request.content.decode())))
            return httpx.Response(303, headers={"location": "/my/"})
        return httpx.Response(200, text="painel")

    with _cliente(handler) as cliente:
        cp.autenticar(cliente, "u", "s")

    assert set(recebido) == {"username", "password"}


# --- persistência ---------------------------------------------------------- #


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


def test_resolver_alvo_aplica_rotas_informadas():
    args = cp.construir_parser().parse_args(
        ["--rota-quiz", "/mod/quiz/view.php?id=9", "--url-5-3", "http://x:1"]
    )
    urls, telas = cp.resolver_alvo(args)

    assert urls["5.3_lts"] == "http://x:1"
    assert dict(telas)["questionario"] == "/mod/quiz/view.php?id=9"
    assert dict(telas)["login"] == dict(cp.TELAS)["login"]


# --- main ------------------------------------------------------------------ #


def test_modo_simulado_grava_so_no_diretorio_simulado_por_padrao(tmp_path, monkeypatch):
    simulado, real = tmp_path / "simulado", tmp_path / "real"
    monkeypatch.setattr(cp, "DIR_DADOS_SIMULADO", simulado)
    monkeypatch.setattr(cp, "DIR_DADOS_PILOTO", real)

    assert cp.main(["--simulado"]) == 0

    assert (simulado / "amostra_piloto.csv").is_file()
    assert not real.exists()
    meta = json.loads((simulado / "resumo_piloto.json").read_text(encoding="utf-8"))["meta"]
    assert meta["origem"] == "simulado"


def test_modo_real_exige_senha_no_ambiente(monkeypatch, capsys):
    monkeypatch.delenv("MOODLE_ALUNO_SENHA", raising=False)
    assert cp.main([]) == 2
    assert "MOODLE_ALUNO_SENHA" in capsys.readouterr().err


class _Ambiente:
    """Troca httpx.Client e subprocess.run para registrar a ordem dos eventos do main."""

    def __init__(self, monkeypatch, status_medicao: int = 200, docker_ok: bool = True):
        self.eventos: list[str] = []
        self.fechados = 0
        eventos = self.eventos
        ambiente = self

        def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                eventos.append("login")
                return httpx.Response(303, headers={"location": "/inicio"})
            if request.url.path in ("/login/index.php", "/inicio"):
                return httpx.Response(200, text="pagina")
            eventos.append("medicao")
            return httpx.Response(status_medicao, content=b"corpo")

        class ClienteFalso(httpx.Client):
            def __init__(self, **kwargs):
                kwargs.pop("transport", None)
                super().__init__(transport=httpx.MockTransport(handler), **kwargs)

            def close(self):
                ambiente.fechados += 1
                super().close()

        def executar(comando, **kwargs):
            if not docker_ok:
                raise subprocess.CalledProcessError(1, comando)
            if any("purge_caches.php" in parte for parte in comando):
                eventos.append("purga")
                return subprocess.CompletedProcess(comando, 0, "", "")
            return subprocess.CompletedProcess(
                comando, 0, "$release = '9.9.9 (Build: 1)';\n", ""
            )

        monkeypatch.setattr(cp.httpx, "Client", ClienteFalso)
        monkeypatch.setattr(cp.subprocess, "run", executar)
        monkeypatch.setattr(cp.time, "sleep", lambda _s: None)
        monkeypatch.setenv("MOODLE_ALUNO_SENHA", "segredo")


def test_main_real_faz_login_depois_purga_depois_mede(monkeypatch, tmp_path):
    amb = _Ambiente(monkeypatch)

    assert cp.main(["--repeticoes", "1", "--saida", str(tmp_path)]) == 0

    primeira_medicao = amb.eventos.index("medicao")
    assert amb.eventos.count("login") == 2
    assert amb.eventos.count("purga") == 2
    assert max(i for i, e in enumerate(amb.eventos) if e == "login") < amb.eventos.index("purga")
    assert max(i for i, e in enumerate(amb.eventos) if e == "purga") < primeira_medicao
    meta = json.loads((tmp_path / "resumo_piloto.json").read_text(encoding="utf-8"))["meta"]
    assert meta["origem"] == "real"
    assert meta["cache_purgado_antes"] is True
    assert meta["releases_moodle"] == {"4.5_lts": "9.9.9 (Build: 1)", "5.3_lts": "9.9.9 (Build: 1)"}
    assert amb.fechados == 4


def test_main_real_sem_purga_registra_no_meta(monkeypatch, tmp_path):
    amb = _Ambiente(monkeypatch)

    assert cp.main(["--repeticoes", "1", "--sem-purga", "--saida", str(tmp_path)]) == 0

    assert "purga" not in amb.eventos
    meta = json.loads((tmp_path / "resumo_piloto.json").read_text(encoding="utf-8"))["meta"]
    assert meta["cache_purgado_antes"] is False


def test_main_real_aborta_sem_gravar_quando_status_nao_e_200(monkeypatch, tmp_path, capsys):
    amb = _Ambiente(monkeypatch, status_medicao=503)

    assert cp.main(["--repeticoes", "1", "--saida", str(tmp_path)]) == 1

    assert "status 503" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []
    assert amb.fechados == 4


def test_main_real_aborta_quando_docker_falha(monkeypatch, tmp_path):
    _Ambiente(monkeypatch, docker_ok=False)

    assert cp.main(["--repeticoes", "1", "--saida", str(tmp_path)]) == 1
    assert list(tmp_path.iterdir()) == []


def test_ler_release_falha_quando_nao_acha_release(monkeypatch):
    monkeypatch.setattr(
        cp.subprocess, "run", lambda c, **k: subprocess.CompletedProcess(c, 0, "nada", "")
    )
    with pytest.raises(cp.ErroColeta):
        cp.ler_release_moodle("moodle45")
