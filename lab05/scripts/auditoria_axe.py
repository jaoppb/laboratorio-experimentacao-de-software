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
from typing import Any

from coleta_piloto import (
    DIR_DADOS_PILOTO,
    TELAS_PUBLICAS,
    VERSOES,
    adicionar_args_alvo,
    resolver_alvo,
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


def auditar(
    urls: dict[str, str],
    telas: tuple[tuple[str, str], ...],
    usuario: str,
    senha: str,
    destino: Path,
) -> list[Path]:
    from axe_playwright_python.sync_playwright import Axe
    from playwright.sync_api import sync_playwright

    destino.mkdir(parents=True, exist_ok=True)
    gravados: list[Path] = []
    axe = Axe()
    opcoes = {"runOnly": {"type": "tag", "values": TAGS_WCAG}}
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        try:
            for versao in VERSOES:
                logada = _entrar(navegador, urls[versao], usuario, senha)
                for tela, rota in telas:
                    # Telas públicas (login) só renderizam para visitante: contexto limpo.
                    publica = tela in TELAS_PUBLICAS
                    alvo = navegador.new_context().new_page() if publica else logada
                    try:
                        alvo.goto(f"{urls[versao]}{rota}")
                        alvo.wait_for_load_state("networkidle")
                        resultado = axe.run(alvo, options=opcoes)
                    finally:
                        if publica:
                            alvo.context.close()
                    conteudo = {
                        "versao": versao,
                        "tela": tela,
                        "rota": rota,
                        **resumir_resultado(resultado.response),
                    }
                    caminho = destino / f"{versao}_{tela}.json"
                    caminho.write_text(
                        json.dumps(conteudo, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    gravados.append(caminho)
                logada.context.close()
        finally:
            navegador.close()
    return gravados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoria axe-core do piloto Lab05")
    adicionar_args_alvo(parser)
    parser.add_argument("--saida", type=Path, default=DIR_DADOS_PILOTO / "axe")
    args = parser.parse_args(argv)

    senha = os.environ.get("MOODLE_ALUNO_SENHA")
    if not senha:
        print("Defina MOODLE_ALUNO_SENHA (ver docker/.env.example).", file=sys.stderr)
        return 2

    urls, telas = resolver_alvo(args)
    try:
        gravados = auditar(urls, telas, args.usuario, senha, args.saida)
    except Exception as erro:  # noqa: BLE001 - reporta qualquer falha de navegador/login
        print(f"Auditoria abortada: {erro}", file=sys.stderr)
        return 1
    print(f"{len(gravados)} relatórios axe gravados em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
