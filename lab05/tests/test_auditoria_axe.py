"""Testes do resumo do axe (não requer navegador)."""

from __future__ import annotations

import sys
import types

import pytest

import auditoria_axe as aa
import coleta_piloto as cp
import coleta_s02 as cs
import validar_piloto as vp


def test_resumir_resultado_conta_violacoes_por_impacto():
    resultado = {
        "violations": [
            {"id": "color-contrast", "impact": "serious", "tags": ["wcag2aa", "cat.color"], "nodes": [1, 2]},
            {"id": "label", "impact": "critical", "tags": ["wcag2a"], "nodes": [1]},
            {"id": "region", "impact": "moderate", "tags": ["best-practice"], "nodes": []},
        ]
    }
    resumo = aa.resumir_resultado(resultado)

    assert resumo["total_violacoes"] == 3
    assert resumo["por_impacto"] == {
        "critical": 1, "serious": 1, "moderate": 1, "minor": 0, "indefinido": 0
    }
    assert resumo["violacoes"][0] == {
        "id": "color-contrast",
        "impacto": "serious",
        "tags": ["wcag2aa"],
        "nos_afetados": 2,
    }


def test_resumir_resultado_sem_violacoes():
    resumo = aa.resumir_resultado({"passes": [{}, {}], "incomplete": [{}]})
    assert resumo["total_violacoes"] == 0
    assert resumo["regras_aprovadas"] == 2
    assert resumo["regras_incompletas"] == 1


def test_impacto_ausente_ou_desconhecido_conta_como_indefinido():
    resumo = aa.resumir_resultado(
        {"violations": [{"id": "a", "impact": None}, {"id": "b", "impact": "novo"}]}
    )
    assert resumo["total_violacoes"] == 2
    assert resumo["por_impacto"]["indefinido"] == 2
    assert sum(resumo["por_impacto"].values()) == resumo["total_violacoes"]


def test_main_exige_senha(monkeypatch, capsys):
    monkeypatch.delenv("MOODLE_ALUNO_SENHA", raising=False)
    assert aa.main([]) == 2
    assert "MOODLE_ALUNO_SENHA" in capsys.readouterr().err


def test_main_repassa_alvo_e_reporta_falha(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("MOODLE_ALUNO_SENHA", "segredo")
    recebido = {}

    def auditar_falso(urls, telas, usuario, senha, destino):
        recebido.update(urls=urls, telas=dict(telas), usuario=usuario, destino=destino)
        raise RuntimeError("navegador indisponível")

    monkeypatch.setattr(aa, "auditar", auditar_falso)
    codigo = aa.main(["--rota-quiz", "/mod/quiz/view.php?id=9", "--saida", str(tmp_path)])

    assert codigo == 1
    assert "navegador indisponível" in capsys.readouterr().err
    assert recebido["telas"]["questionario"] == "/mod/quiz/view.php?id=9"
    assert recebido["usuario"] == "aluno_teste_1"
    assert recebido["destino"] == tmp_path


class _Navegador:
    """Dublê mínimo de Playwright: registra os contextos abertos."""

    def __init__(self):
        self.contextos: list = []

    def new_context(self):
        contexto = types.SimpleNamespace(fechado=False)
        contexto.close = lambda: setattr(contexto, "fechado", True)

        def goto(url):
            pagina.url = url

        def locator(_selector):
            def click():
                base = pagina.url.split("/mod/quiz/")[0]
                pagina.url = f"{base}/mod/quiz/attempt.php?attempt=88&cmid=6"

            return types.SimpleNamespace(first=types.SimpleNamespace(click=click))

        pagina = types.SimpleNamespace(
            context=contexto,
            url="http://x/my/",
            goto=goto,
            locator=locator,
            fill=lambda *a, **k: None,
            click=lambda *a, **k: None,
            wait_for_url=lambda *a, **k: None,
            wait_for_load_state=lambda *a, **k: None,
        )
        contexto.new_page = lambda: pagina
        self.contextos.append(contexto)
        return contexto

    def close(self):
        pass


def _instalar_dubles(monkeypatch, navegador, falha_na_versao: str | None = None):
    chamadas = {"n": 0}

    class Axe:
        def run(self, pagina, options=None):
            chamadas["n"] += 1
            # A falha acontece na 1ª tela auditada da versão 5.3 (a 5ª auditoria).
            if falha_na_versao and chamadas["n"] == 5:
                raise RuntimeError(f"falha simulada em {falha_na_versao}")
            return types.SimpleNamespace(response={"passes": [{}], "violations": []})

    class ContextoPw:
        chromium = types.SimpleNamespace(launch=lambda: navegador)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    pw_mod = types.ModuleType("playwright.sync_api")
    pw_mod.sync_playwright = lambda: ContextoPw()
    pw_mod.TimeoutError = TimeoutError
    axe_mod = types.ModuleType("axe_playwright_python.sync_playwright")
    axe_mod.Axe = Axe
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", pw_mod)
    monkeypatch.setitem(sys.modules, "axe_playwright_python", types.ModuleType("axe_playwright_python"))
    monkeypatch.setitem(sys.modules, "axe_playwright_python.sync_playwright", axe_mod)


URLS = {"4.5_lts": "http://a", "5.3_lts": "http://b"}


def test_auditar_grava_8_relatorios_validos_e_fecha_contextos(monkeypatch, tmp_path):
    navegador = _Navegador()
    _instalar_dubles(monkeypatch, navegador)

    gravados = aa.auditar(URLS, cp.TELAS, "aluno", "senha", tmp_path / "axe")

    assert sorted(p.name for p in gravados) == sorted(
        f"{v}_{t}.json" for v in cp.VERSOES for t, _ in cp.TELAS
    )
    assert vp.validar_axe(tmp_path / "axe") == []
    assert all(c.fechado for c in navegador.contextos)


def test_auditar_nao_grava_nada_quando_uma_auditoria_falha(monkeypatch, tmp_path):
    navegador = _Navegador()
    _instalar_dubles(monkeypatch, navegador, falha_na_versao="5.3_lts")
    destino = tmp_path / "axe"
    destino.mkdir()
    antigo = destino / "4.5_lts_login.json"
    antigo.write_text("relatório de execução anterior", encoding="utf-8")

    with pytest.raises(RuntimeError, match="falha simulada"):
        aa.auditar(URLS, cp.TELAS, "aluno", "senha", destino)

    assert [p.name for p in destino.iterdir()] == [antigo.name]
    assert antigo.read_text(encoding="utf-8") == "relatório de execução anterior"
    assert all(c.fechado for c in navegador.contextos)


def test_auditar_s02_inicia_e_descarta_tentativa_quiz(monkeypatch, tmp_path):
    navegador = _Navegador()
    _instalar_dubles(monkeypatch, navegador)
    descartadas: list[tuple[str, int]] = []

    gravados = aa.auditar(
        URLS,
        cs.TELAS_S02,
        "aluno",
        "senha",
        tmp_path / "axe",
        descartar_tentativa=lambda serv, aid: descartadas.append((serv, aid)),
    )

    assert sorted(p.name for p in gravados) == sorted(
        f"{v}_{t}.json" for v in cp.VERSOES for t, _ in cs.TELAS_S02
    )
    assert vp.validar_axe(tmp_path / "axe", telas=cs.TELAS_S02) == []
    assert descartadas == [("moodle45", 88), ("moodle53", 88)]
    assert all(c.fechado for c in navegador.contextos)


def test_auditar_s02_descarta_tentativa_mesmo_quando_axe_falha(monkeypatch, tmp_path):
    navegador = _Navegador()

    class AxeQueFalha:
        def run(self, pagina, options=None):
            if "attempt.php" in pagina.url:
                raise RuntimeError("falha no axe")
            return types.SimpleNamespace(response={"passes": [{}], "violations": []})

    _instalar_dubles(monkeypatch, navegador)
    monkeypatch.setattr(sys.modules["axe_playwright_python.sync_playwright"], "Axe", AxeQueFalha)
    descartadas: list[tuple[str, int]] = []

    with pytest.raises(RuntimeError, match="falha no axe"):
        aa.auditar(
            URLS,
            cs.TELAS_S02,
            "aluno",
            "senha",
            tmp_path / "axe",
            descartar_tentativa=lambda serv, aid: descartadas.append((serv, aid)),
        )

    assert descartadas == [("moodle45", 88)]
    assert all(c.fechado for c in navegador.contextos)


def test_main_s02_usa_telas_s02_e_destino_padrao(monkeypatch, tmp_path):
    monkeypatch.setenv("MOODLE_ALUNO_SENHA", "segredo")
    monkeypatch.setattr(aa, "DIR_DADOS_S02", tmp_path / "reais")
    recebido = {}

    def auditar_falso(urls, telas, usuario, senha, destino):
        recebido.update(urls=urls, telas=dict(telas), destino=destino)
        return []

    monkeypatch.setattr(aa, "auditar", auditar_falso)
    assert aa.main(["--s02", "--rota-quiz", "/mod/quiz/view.php?id=12"]) == 0
    assert recebido["telas"]["tentativa_quiz"] == "/mod/quiz/attempt.php?cmid=12"
    assert recebido["destino"] == tmp_path / "reais" / "axe"
