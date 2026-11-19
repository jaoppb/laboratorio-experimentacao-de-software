"""Coleta piloto de desempenho (TTFB) para Moodle 4.5 LTS vs 5.3 LTS.

Protocolo de medição da Sprint Lab05S01 (ver ``docs/plano_coleta_instrumentacao.md``):

- mede TTFB (ms), tempo total (ms), status HTTP e tamanho do corpo por requisição;
- alterna as versões a cada requisição (ordem alternada balanceada);
- marca a 1ª repetição de cada tela/versão como ``cold`` (após purga de cache) e as
  demais como ``warm``;
- grava o CSV bruto e o resumo estatístico em JSON.

Modos:

- ``real`` (padrão): requisições HTTP contra as duas instâncias Moodle em Docker;
- ``--simulado``: gera amostras sintéticas (lognormais) para testar o pipeline sem
  subir os contêineres. Grava em ``dados/piloto_simulado/`` e nunca em
  ``dados/piloto/``, que contém apenas medições reais.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx
import numpy as np

RAIZ_LAB05 = Path(__file__).resolve().parents[1]
DIR_DADOS_PILOTO = RAIZ_LAB05 / "dados" / "piloto"
DIR_DADOS_SIMULADO = RAIZ_LAB05 / "dados" / "piloto_simulado"
ARQUIVO_COMPOSE = RAIZ_LAB05 / "docker" / "docker-compose.yml"

TELAS = (
    ("login", "/login/index.php"),
    ("dashboard", "/my/"),
    ("curso", "/course/view.php?id=2"),
    ("questionario", "/mod/quiz/view.php?id=1"),
)

VERSOES = ("4.5_lts", "5.3_lts")

# Telas medidas sem sessão (visitante); as demais usam o usuário estudante autenticado.
TELAS_PUBLICAS = frozenset({"login"})

COLUNAS_CSV = (
    "id",
    "versao",
    "tela",
    "rota",
    "repeticao",
    "cache",
    "status_http",
    "ttfb_ms",
    "tempo_total_ms",
    "tamanho_bytes",
)

# Serviço Docker (docker-compose.yml) e porta local de cada versão.
SERVICOS = {"4.5_lts": "moodle45", "5.3_lts": "moodle53"}
URLS_PADRAO = {
    "4.5_lts": "http://localhost:8045",
    "5.3_lts": "http://localhost:8053",
}

TIMEOUT_S = 60.0


class ErroColeta(RuntimeError):
    """Falha de coleta que invalida o piloto (login, status inesperado, etc.)."""


# --------------------------------------------------------------------------- #
# Coleta real
# --------------------------------------------------------------------------- #


def autenticar(cliente: httpx.Client, usuario: str, senha: str) -> None:
    """Autentica o usuário sintético; o cookie fica no cliente."""
    pagina = cliente.get("/login/index.php")
    achado = re.search(r'name="logintoken"\s+value="([^"]+)"', pagina.text)
    dados = {"username": usuario, "password": senha}
    if achado:
        dados["logintoken"] = achado.group(1)
    resposta = cliente.post("/login/index.php", data=dados)
    # Login válido redireciona para fora de /login/. Seguindo o redirect, a página
    # final não pode ser a de login nem conter o aviso de falha.
    if "/login/" in str(resposta.url) or "loginerrormessage" in resposta.text:
        raise ErroColeta(f"Falha de autenticação do usuário {usuario!r}")


def medir_requisicao(cliente: httpx.Client, rota: str) -> dict[str, Any]:
    """Executa um GET e devolve status, TTFB, tempo total e tamanho do corpo.

    O TTFB vai do envio da requisição até o recebimento dos cabeçalhos de resposta
    (``stream`` devolve a resposta assim que os cabeçalhos chegam).
    """
    inicio = time.perf_counter()
    with cliente.stream("GET", rota) as resposta:
        ttfb = time.perf_counter() - inicio
        tamanho = len(resposta.read())
        total = time.perf_counter() - inicio
        status = resposta.status_code
    return {
        "status_http": status,
        "ttfb_ms": round(ttfb * 1000, 2),
        "tempo_total_ms": round(total * 1000, 2),
        "tamanho_bytes": tamanho,
    }


def purgar_cache(servico: str) -> None:
    """Purga os caches do Moodle para que a 1ª repetição seja de fato ``cold``."""
    subprocess.run(
        [
            "docker", "compose", "-f", str(ARQUIVO_COMPOSE), "exec", "-T", servico,
            "php", "admin/cli/purge_caches.php",
        ],
        check=True,
    )


def coletar_amostras_reais(
    clientes: dict[str, httpx.Client],
    telas: tuple[tuple[str, str], ...] = TELAS,
    clientes_publicos: dict[str, httpx.Client] | None = None,
    n_repeticoes: int = 10,
    pausa_ms: tuple[int, int] = (200, 500),
    semente: int = 42,
    dormir: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    """Mede todas as telas nas duas versões, alternando a versão a cada requisição.

    Qualquer status diferente de 200 aborta a coleta: o piloto precisa expor o
    problema em vez de gravar dados que o Plano de Análise teria de descartar.
    ``clientes`` carregam a sessão do estudante; ``clientes_publicos`` (sem cookie)
    medem as telas de ``TELAS_PUBLICAS`` e, se omitidos, ``clientes`` é usado.
    """
    clientes_publicos = clientes_publicos or clientes
    gerador = random.Random(semente)
    amostras: list[dict[str, Any]] = []
    for repeticao in range(1, n_repeticoes + 1):
        for tela, rota in telas:
            for versao in VERSOES:
                cliente = (clientes_publicos if tela in TELAS_PUBLICAS else clientes)[versao]
                medida = medir_requisicao(cliente, rota)
                if medida["status_http"] != 200:
                    raise ErroColeta(
                        f"{versao} {tela} {rota}: status {medida['status_http']}"
                    )
                amostras.append(
                    {
                        "id": len(amostras) + 1,
                        "versao": versao,
                        "tela": tela,
                        "rota": rota,
                        "repeticao": repeticao,
                        "cache": "cold" if repeticao == 1 else "warm",
                        **medida,
                    }
                )
                dormir(gerador.uniform(*pausa_ms) / 1000)
    return amostras


# --------------------------------------------------------------------------- #
# Modo simulado (teste do pipeline sem contêineres)
# --------------------------------------------------------------------------- #


def coletar_amostras_simuladas(
    n_repeticoes: int = 10,
    semente: int = 42,
) -> list[dict[str, Any]]:
    """Gera amostras sintéticas lognormais. Não representam medições reais."""
    rng = np.random.default_rng(semente)
    amostras: list[dict[str, Any]] = []

    # Mediana (ms) e sigma_log por versão e tela.
    calibracao = {
        "4.5_lts": {
            "login": (120.0, 0.25),
            "dashboard": (240.0, 0.35),
            "curso": (310.0, 0.40),
            "questionario": (270.0, 0.30),
        },
        "5.3_lts": {
            "login": (110.0, 0.22),
            "dashboard": (210.0, 0.30),
            "curso": (275.0, 0.35),
            "questionario": (245.0, 0.28),
        },
    }

    for i in range(n_repeticoes):
        for tela_nome, rota in TELAS:
            for versao in VERSOES:
                mediana_base, sigma = calibracao[versao][tela_nome]
                is_cold = i == 0
                fator_frio = 1.6 if is_cold else 1.0
                ttfb = float(
                    rng.lognormal(mean=np.log(mediana_base * fator_frio), sigma=sigma)
                )
                tempo_total = ttfb + float(rng.uniform(15.0, 45.0))
                amostras.append(
                    {
                        "id": len(amostras) + 1,
                        "versao": versao,
                        "tela": tela_nome,
                        "rota": rota,
                        "repeticao": i + 1,
                        "cache": "cold" if is_cold else "warm",
                        "status_http": 200,
                        "ttfb_ms": round(ttfb, 2),
                        "tempo_total_ms": round(tempo_total, 2),
                        "tamanho_bytes": 18450 if tela_nome != "curso" else 42100,
                    }
                )
    return amostras


# --------------------------------------------------------------------------- #
# Resumo e persistência
# --------------------------------------------------------------------------- #


def calcular_resumo_estatistico(amostras: list[dict[str, Any]]) -> dict[str, Any]:
    """Calcula estatísticas descritivas (mediana, IQR, p95) por versão e tela."""
    resumo: dict[str, Any] = {"versoes": {}}

    for versao in VERSOES:
        resumo["versoes"][versao] = {}
        for tela_nome, _ in TELAS:
            valores = [
                a["ttfb_ms"]
                for a in amostras
                if a["versao"] == versao and a["tela"] == tela_nome
            ]
            if not valores:
                continue

            arr = np.array(valores, dtype=float)
            q25, q50, q75 = np.percentile(arr, [25, 50, 75])
            p95 = np.percentile(arr, 95)

            resumo["versoes"][versao][tela_nome] = {
                "n": len(arr),
                "mediana_ms": round(float(q50), 2),
                "iqr_ms": round(float(q75 - q25), 2),
                "media_ms": round(float(arr.mean()), 2),
                "p95_ms": round(float(p95), 2),
                "min_ms": round(float(arr.min()), 2),
                "max_ms": round(float(arr.max()), 2),
            }

    return resumo


def salvar_dados_piloto(
    amostras: list[dict[str, Any]],
    diretorio: Path = DIR_DADOS_PILOTO,
    meta: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    """Grava amostras em CSV e resumo estatístico em JSON.

    ``meta`` (versões exatas, data, origem dos dados) entra no JSON sob ``meta``.
    """
    if not amostras:
        raise ErroColeta("Nenhuma amostra para salvar")
    diretorio.mkdir(parents=True, exist_ok=True)
    caminho_csv = diretorio / "amostra_piloto.csv"
    caminho_json = diretorio / "resumo_piloto.json"

    with open(caminho_csv, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(COLUNAS_CSV))
        escritor.writeheader()
        escritor.writerows(amostras)

    resumo = calcular_resumo_estatistico(amostras)
    if meta:
        resumo = {"meta": meta, **resumo}
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return caminho_csv, caminho_json


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coleta piloto Lab05 - Moodle")
    parser.add_argument(
        "--repeticoes",
        type=int,
        default=10,
        help="Número de repetições por tela e versão (default: 10)",
    )
    parser.add_argument(
        "--simulado",
        action="store_true",
        help="Gera dados sintéticos em dados/piloto_simulado/ (não são medições)",
    )
    parser.add_argument("--url-4-5", default=URLS_PADRAO["4.5_lts"])
    parser.add_argument("--url-5-3", default=URLS_PADRAO["5.3_lts"])
    parser.add_argument("--rota-curso", default="/course/view.php?id=2")
    parser.add_argument("--rota-quiz", default="/mod/quiz/view.php?id=1")
    parser.add_argument("--usuario", default="aluno_teste_1")
    parser.add_argument(
        "--sem-purga",
        action="store_true",
        help="Não purga o cache antes da coleta (a repetição 1 deixa de ser fria)",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=None,
        help="Diretório de saída (default: dados/piloto, ou dados/piloto_simulado)",
    )
    return parser


def _release_moodle(servico: str) -> str:
    """Lê ``$release`` do ``version.php`` dentro do contêiner (raiz no 4.5, public/ no 5.x)."""
    resultado = subprocess.run(
        [
            "docker", "compose", "-f", str(ARQUIVO_COMPOSE), "exec", "-T", servico,
            "sh", "-c", "cat version.php public/version.php 2>/dev/null",
        ],
        capture_output=True,
        text=True,
    )
    achado = re.search(r"\$release\s*=\s*'([^']+)'", resultado.stdout)
    return achado.group(1) if achado else "desconhecida"


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)

    if args.simulado:
        destino = args.saida or DIR_DADOS_SIMULADO
        print(f"[SIMULADO] {args.repeticoes} repetições por tela (dados sintéticos)...")
        amostras = coletar_amostras_simuladas(n_repeticoes=args.repeticoes)
        meta = {"origem": "simulado", "gerado_em": datetime.now(timezone.utc).isoformat()}
    else:
        senha = os.environ.get("MOODLE_ALUNO_SENHA")
        if not senha:
            print("Defina MOODLE_ALUNO_SENHA (ver docker/.env.example).", file=sys.stderr)
            return 2
        destino = args.saida or DIR_DADOS_PILOTO
        telas = tuple(
            (nome, {"curso": args.rota_curso, "questionario": args.rota_quiz}.get(nome, rota))
            for nome, rota in TELAS
        )
        urls = {"4.5_lts": args.url_4_5, "5.3_lts": args.url_5_3}
        def novo_cliente(versao: str) -> httpx.Client:
            return httpx.Client(
                base_url=urls[versao], follow_redirects=True, timeout=TIMEOUT_S
            )

        clientes = {v: novo_cliente(v) for v in VERSOES}
        publicos = {v: novo_cliente(v) for v in VERSOES}
        try:
            releases = {v: _release_moodle(SERVICOS[v]) for v in VERSOES}
            for cliente in clientes.values():
                autenticar(cliente, args.usuario, senha)
            # Purga depois do login para que a 1ª repetição de cada tela seja de fato fria.
            if not args.sem_purga:
                for versao in VERSOES:
                    purgar_cache(SERVICOS[versao])
            print(f"Coletando {args.repeticoes} repetições por tela e versão...")
            amostras = coletar_amostras_reais(clientes, telas, publicos, args.repeticoes)
        except (ErroColeta, httpx.HTTPError, subprocess.CalledProcessError) as erro:
            print(f"Coleta abortada: {erro}", file=sys.stderr)
            return 1
        finally:
            for cliente in (*clientes.values(), *publicos.values()):
                cliente.close()
        meta = {
            "origem": "real",
            "releases_moodle": releases,
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "cache_purgado_antes": not args.sem_purga,
        }

    caminho_csv, caminho_json = salvar_dados_piloto(amostras, destino, meta)
    print("Coleta concluída.")
    print(f"- Amostras: {caminho_csv} ({len(amostras)} registros)")
    print(f"- Resumo: {caminho_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
