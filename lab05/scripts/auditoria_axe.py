"""Auditoria de acessibilidade (axe-core / WCAG 2.1 AA) das 4 telas nas 2 versões.

Renderiza cada tela em Chromium headless (Playwright), executa o axe-core e grava
um JSON por tela e versão em ``dados/piloto/axe/<versao>_<tela>.json`` com as
violações (id da regra, impacto, tags WCAG e número de nós afetados).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

from coleta_piloto import (
    DIR_DADOS_PILOTO,
    SERVICOS,
    TELAS_PUBLICAS,
    VERSOES,
    adicionar_args_alvo,
    resolver_alvo,
)
from coleta_s02 import (
    DIR_DADOS_S02,
    descartar_tentativa_quiz,
    extrair_attempt_id,
    extrair_cmid,
    resolver_alvo_s02,
)

TAGS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
IMPACTOS = ("critical", "serious", "moderate", "minor")


def resumir_resultado(resultado: dict[str, Any]) -> dict[str, Any]:
    """Reduz a saída do axe às informações usadas na análise."""
    violacoes = [
        {
            "id": v["id"],
            "impacto": v.get("impact"),
            "tags": [t for t in v.get("tags", []) if t.startswith("wcag")],
            "nos_afetados": len(v.get("nodes", [])),
        }
        for v in resultado.get("violations", [])
    ]
    por_impacto = {i: 0 for i in (*IMPACTOS, "indefinido")}
    for v in violacoes:
        por_impacto[v["impacto"] if v["impacto"] in IMPACTOS else "indefinido"] += 1
    return {
        "total_violacoes": len(violacoes),
        "por_impacto": por_impacto,
        "regras_aprovadas": len(resultado.get("passes", [])),
        "regras_incompletas": len(resultado.get("incomplete", [])),
        "violacoes": violacoes,
    }


def _entrar(navegador: Any, url: str, usuario: str, senha: str) -> Any:
    """Abre um contexto novo, autentica o estudante e devolve a página logada."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    pagina = navegador.new_context().new_page()
    pagina.goto(f"{url}/login/index.php")
    pagina.fill("#username", usuario)
    pagina.fill("#password", senha)
    pagina.click("#loginbtn")
    try:
        pagina.wait_for_url(lambda destino: "/login/" not in destino, timeout=30000)
    except PlaywrightTimeoutError as erro:
        raise RuntimeError(f"Falha de autenticação em {url}") from erro
    pagina.wait_for_load_state("networkidle")
    return pagina


def _auditar_tentativa_quiz(
    alvo: Any,
    url_base: str,
    cmid: int,
    axe: Any,
    opcoes: dict[str, Any],
    servico: str,
    descartar_tentativa: Callable[[str, int], None],
) -> Any:
    """Inicia uma tentativa pelo navegador, executa o axe e descarta a tentativa."""
    alvo.goto(f"{url_base}/mod/quiz/view.php?id={cmid}")
    alvo.wait_for_load_state("networkidle")
    alvo.locator(
        'form[action*="startattempt.php"] button[type="submit"], '
        'form[action*="startattempt.php"] input[type="submit"]'
    ).first.click()
    alvo.wait_for_url("**/mod/quiz/attempt.php**", timeout=30000)
    alvo.wait_for_load_state("networkidle")
    attempt_id = extrair_attempt_id(alvo.url)
    try:
        return axe.run(alvo, options=opcoes)
    finally:
        descartar_tentativa(servico, attempt_id)


def auditar(
    urls: dict[str, str],
    telas: tuple[tuple[str, str], ...],
    usuario: str,
    senha: str,
    destino: Path,
    cmid: int | None = None,
    descartar_tentativa: Callable[[str, int], None] = descartar_tentativa_quiz,
) -> list[Path]:
    from axe_playwright_python.sync_playwright import Axe
    from playwright.sync_api import sync_playwright

    relatorios: dict[str, dict[str, Any]] = {}
    axe = Axe()
    opcoes = {"runOnly": {"type": "tag", "values": TAGS_WCAG}}
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        try:
            for versao in VERSOES:
                logada = _entrar(navegador, urls[versao], usuario, senha)
                try:
                    for tela, rota in telas:
                        # Telas públicas (login) só renderizam para visitante: contexto limpo.
                        publica = tela in TELAS_PUBLICAS
                        alvo = navegador.new_context().new_page() if publica else logada
                        try:
                            if tela == "tentativa_quiz":
                                if cmid is None:
                                    cmid = extrair_cmid(rota)
                                resultado = _auditar_tentativa_quiz(
                                    alvo,
                                    urls[versao],
                                    cmid,
                                    axe,
                                    opcoes,
                                    SERVICOS[versao],
                                    descartar_tentativa,
                                )
                            else:
                                alvo.goto(f"{urls[versao]}{rota}")
                                alvo.wait_for_load_state("networkidle")
                                resultado = axe.run(alvo, options=opcoes)
                        finally:
                            if publica:
                                alvo.context.close()
                        relatorios[f"{versao}_{tela}"] = {
                            "versao": versao,
                            "tela": tela,
                            "rota": rota,
                            **resumir_resultado(resultado.response),
                        }
                finally:
                    logada.context.close()
        finally:
            navegador.close()

    # Grava só depois de auditar tudo, para não deixar relatórios de duas execuções misturados.
    destino.mkdir(parents=True, exist_ok=True)
    gravados: list[Path] = []
    for nome, conteudo in relatorios.items():
        caminho = destino / f"{nome}.json"
        caminho.write_text(
            json.dumps(conteudo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        gravados.append(caminho)
    return gravados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoria axe-core do Lab05")
    adicionar_args_alvo(parser)
    parser.add_argument(
        "--s02",
        action="store_true",
        help="Audita as 4 telas da S02 (substitui questionario por tentativa_quiz)",
    )
    parser.add_argument("--saida", type=Path, default=None)
    args = parser.parse_args(argv)

    senha = os.environ.get("MOODLE_ALUNO_SENHA")
    if not senha:
        print("Defina MOODLE_ALUNO_SENHA (ver docker/.env.example).", file=sys.stderr)
        return 2

    if args.s02:
        urls, telas, cmid = resolver_alvo_s02(args)
        destino = args.saida or (DIR_DADOS_S02 / "axe")
        chamada = lambda: auditar(urls, telas, args.usuario, senha, destino, cmid=cmid)
    else:
        urls, telas = resolver_alvo(args)
        destino = args.saida or (DIR_DADOS_PILOTO / "axe")
        chamada = lambda: auditar(urls, telas, args.usuario, senha, destino)

    try:
        gravados = chamada()
    except Exception as erro:  # noqa: BLE001 - reporta qualquer falha de navegador/login
        print(f"Auditoria abortada: {erro}", file=sys.stderr)
        return 1
    print(f"{len(gravados)} relatórios axe gravados em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
