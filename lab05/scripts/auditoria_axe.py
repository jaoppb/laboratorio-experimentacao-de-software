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

from coleta_piloto import DIR_DADOS_PILOTO, TELAS, URLS_PADRAO, VERSOES

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
    por_impacto = {i: 0 for i in IMPACTOS}
    for v in violacoes:
        if v["impacto"] in por_impacto:
            por_impacto[v["impacto"]] += 1
    return {
        "total_violacoes": len(violacoes),
        "por_impacto": por_impacto,
        "regras_aprovadas": len(resultado.get("passes", [])),
        "regras_incompletas": len(resultado.get("incomplete", [])),
        "violacoes": violacoes,
    }


def auditar(
    urls: dict[str, str],
    rotas: dict[str, str],
    usuario: str,
    senha: str,
    destino: Path,
) -> list[Path]:
    from axe_playwright_python.sync_playwright import Axe
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    destino.mkdir(parents=True, exist_ok=True)
    gravados: list[Path] = []
    axe = Axe()
    with sync_playwright() as pw:
        navegador = pw.chromium.launch()
        try:
            for versao in VERSOES:
                pagina = navegador.new_context().new_page()
                pagina.goto(f"{urls[versao]}/login/index.php")
                pagina.fill("#username", usuario)
                pagina.fill("#password", senha)
                pagina.click("#loginbtn")
                try:
                    pagina.wait_for_url(lambda url: "/login/" not in url, timeout=30000)
                except PlaywrightTimeoutError as erro:
                    raise RuntimeError(f"Falha de autenticação em {versao}") from erro
                pagina.wait_for_load_state("networkidle")

                for tela, _ in TELAS:
                    publica = tela == "login"
                    if publica:
                        # A tela de login só renderiza para visitante: usa contexto limpo.
                        alvo = navegador.new_context().new_page()
                    else:
                        alvo = pagina
                    alvo.goto(f"{urls[versao]}{rotas[tela]}")
                    alvo.wait_for_load_state("networkidle")
                    resultado = axe.run(alvo, options={"runOnly": {"type": "tag", "values": TAGS_WCAG}})
                    conteudo = {
                        "versao": versao,
                        "tela": tela,
                        "rota": rotas[tela],
                        **resumir_resultado(resultado.response),
                    }
                    caminho = destino / f"{versao}_{tela}.json"
                    caminho.write_text(
                        json.dumps(conteudo, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    gravados.append(caminho)
        finally:
            navegador.close()
    return gravados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoria axe-core do piloto Lab05")
    parser.add_argument("--url-4-5", default=URLS_PADRAO["4.5_lts"])
    parser.add_argument("--url-5-3", default=URLS_PADRAO["5.3_lts"])
    parser.add_argument("--rota-curso", default="/course/view.php?id=2")
    parser.add_argument("--rota-quiz", default="/mod/quiz/view.php?id=1")
    parser.add_argument("--usuario", default="aluno_teste_1")
    parser.add_argument("--saida", type=Path, default=DIR_DADOS_PILOTO / "axe")
    args = parser.parse_args(argv)

    senha = os.environ.get("MOODLE_ALUNO_SENHA")
    if not senha:
        print("Defina MOODLE_ALUNO_SENHA (ver docker/.env.example).", file=sys.stderr)
        return 2

    rotas = {
        nome: {"curso": args.rota_curso, "questionario": args.rota_quiz}.get(nome, rota)
        for nome, rota in TELAS
    }
    urls = {"4.5_lts": args.url_4_5, "5.3_lts": args.url_5_3}
    try:
        gravados = auditar(urls, rotas, args.usuario, senha, args.saida)
    except Exception as erro:  # noqa: BLE001 - reporta qualquer falha de navegador/login
        print(f"Auditoria abortada: {erro}", file=sys.stderr)
        return 1
    print(f"{len(gravados)} relatórios axe gravados em {args.saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
