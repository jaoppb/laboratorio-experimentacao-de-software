"""Coleta da Sprint Lab05S02 (TTFB) para Moodle 4.5 LTS vs 5.3 LTS.

Mede as 4 telas definidas para a S02 (``login``, ``dashboard``, ``curso`` e
``tentativa_quiz`` em ``/mod/quiz/attempt.php``), com ordem contrabalanceada
ABBA determinística entre as versões.

Para ``tentativa_quiz``, cada repetição inicia uma tentativa limpa via
``POST /mod/quiz/startattempt.php``, mede exclusivamente o
``GET /mod/quiz/attempt.php?attempt=<id>&cmid=<cmid>`` e descarta a tentativa
via CLI (``quiz_delete_attempt``) para não acumular estado entre repetições.
"""

from __future__ import annotations

import argparse
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

import httpx
import numpy as np

from coleta_piloto import (
    DIR_DADOS_PILOTO,
    RAIZ_LAB05,
    SERVICOS,
    TELAS_PUBLICAS,
    TIMEOUT_S,
    VERSOES,
    ErroColeta,
    _compose_exec,
    adicionar_args_alvo,
    autenticar,
    coletar_amostras,
    ler_release_moodle,
    medir_requisicao,
    purgar_cache,
    salvar_dados_piloto,
)

DIR_DADOS_S02 = RAIZ_LAB05 / "dados" / "reais"
DIR_DADOS_S02_SIMULADO = RAIZ_LAB05 / "dados" / "reais_simulado"

NOME_CSV_S02 = "amostra_s02.csv"
NOME_JSON_S02 = "resumo_s02.json"

TELAS_S02 = (
    ("login", "/login/index.php"),
    ("dashboard", "/my/"),
    ("curso", "/course/view.php?id=2"),
    ("tentativa_quiz", "/mod/quiz/attempt.php?cmid=6"),
)

_PHP_DESCARTAR_TENTATIVA = (
    "define('CLI_SCRIPT', true);"
    "require '/var/www/html/config.php';"
    "require_once $CFG->dirroot . '/mod/quiz/locallib.php';"
    "$aid = (int) $argv[1];"
    "if ($att = $DB->get_record('quiz_attempts', ['id' => $aid])) {"
    "  $quiz = $DB->get_record('quiz', ['id' => $att->quiz], '*', MUST_EXIST);"
    "  quiz_delete_attempt($att, $quiz);"
    "}"
)


def extrair_cmid(rota_quiz: str) -> int:
    """Extrai o ``cmid`` numérico de uma rota como ``/mod/quiz/view.php?id=6``."""
    achado = re.search(r"[?&](?:cmid|id)=(\d+)", rota_quiz)
    if not achado:
        raise ErroColeta(f"Não foi possível extrair cmid de {rota_quiz!r}")
    return int(achado.group(1))


def extrair_sesskey(cliente: httpx.Client, cmid: int) -> str:
    """Obtém o ``sesskey`` da sessão autenticada a partir da página do quiz."""
    resposta = cliente.get(f"/mod/quiz/view.php?id={cmid}")
    if resposta.status_code != 200:
        raise ErroColeta(f"Falha ao abrir quiz cmid={cmid}: status {resposta.status_code}")
    for padrao in (
        r'"sesskey"\s*:\s*"([^"]+)"',
        r'name="sesskey"\s+value="([^"]+)"',
        r"sesskey=([A-Za-z0-9]+)",
    ):
        achado = re.search(padrao, resposta.text)
        if achado:
            return achado.group(1)
    raise ErroColeta(f"sesskey não encontrado ao abrir /mod/quiz/view.php?id={cmid}")


def extrair_attempt_id(url: str) -> int:
    """Extrai o parâmetro ``attempt`` de uma URL ``/mod/quiz/attempt.php?...``."""
    query = parse_qs(urlparse(url).query)
    valores = query.get("attempt")
    if not valores or not valores[0].isdigit():
        raise ErroColeta(f"Parâmetro attempt ausente em {url!r}")
    return int(valores[0])


def iniciar_tentativa_quiz(cliente: httpx.Client, cmid: int, sesskey: str) -> int:
    """Inicia uma tentativa via ``POST /mod/quiz/startattempt.php`` sem seguir redirect."""
    resposta = cliente.post(
        "/mod/quiz/startattempt.php",
        data={"cmid": str(cmid), "sesskey": sesskey},
        follow_redirects=False,
    )
    if resposta.status_code not in (302, 303) or "location" not in resposta.headers:
        raise ErroColeta(
            f"startattempt.php não redirecionou (status {resposta.status_code})"
        )
    return extrair_attempt_id(resposta.headers["location"])


def descartar_tentativa_quiz(servico: str, attempt_id: int) -> None:
    """Remove a tentativa do banco via ``quiz_delete_attempt`` dentro do contêiner."""
    _compose_exec(
        servico,
        "php",
        "-r",
        _PHP_DESCARTAR_TENTATIVA,
        "--",
        str(attempt_id),
        check=True,
    )


def coletar_amostras_s02(
    clientes: dict[str, httpx.Client],
    clientes_publicos: dict[str, httpx.Client],
    telas: tuple[tuple[str, str], ...] = TELAS_S02,
    n_repeticoes: int = 80,
    pausa_ms: tuple[int, int] = (200, 500),
    semente: int = 42,
    dormir: Callable[[float], None] | None = None,
    cmid: int = 6,
    descartar_tentativa: Callable[[str, int], None] = descartar_tentativa_quiz,
) -> list[dict[str, Any]]:
    """Mede todas as telas da S02 nas duas versões via HTTP.

    Para ``tentativa_quiz``, cria uma tentativa nova antes do GET medido e a
    apaga no bloco ``finally`` para manter o banco sem acúmulo entre repetições.
    """
    dormir = dormir or time.sleep
    gerador = random.Random(semente)
    sesskeys: dict[str, str] = {}

    def medir(versao: str, tela: str, rota: str, _repeticao: int) -> dict[str, Any]:
        if tela == "tentativa_quiz":
            cliente = clientes[versao]
            if versao not in sesskeys:
                sesskeys[versao] = extrair_sesskey(cliente, cmid)
            attempt_id = iniciar_tentativa_quiz(cliente, cmid, sesskeys[versao])
            try:
                medida = medir_requisicao(
                    cliente, f"/mod/quiz/attempt.php?attempt={attempt_id}&cmid={cmid}"
                )
            finally:
                descartar_tentativa(SERVICOS[versao], attempt_id)
        else:
            cliente = (clientes_publicos if tela in TELAS_PUBLICAS else clientes)[versao]
            medida = medir_requisicao(cliente, rota)

        if medida["status_http"] != 200:
            raise ErroColeta(f"{versao} {tela} {rota}: status {medida['status_http']}")
        dormir(gerador.uniform(*pausa_ms) / 1000)
        return medida

    return coletar_amostras(medir, telas, n_repeticoes)


def coletar_amostras_simuladas_s02(
    n_repeticoes: int = 80,
    semente: int = 42,
) -> list[dict[str, Any]]:
    """Gera amostras sintéticas para testar o pipeline S02 sem contêineres."""
    rng = np.random.default_rng(semente)
    calibracao = {
        "4.5_lts": {
            "login": (120.0, 0.25),
            "dashboard": (240.0, 0.35),
            "curso": (310.0, 0.40),
            "tentativa_quiz": (340.0, 0.32),
        },
        "5.3_lts": {
            "login": (110.0, 0.22),
            "dashboard": (210.0, 0.30),
            "curso": (275.0, 0.35),
            "tentativa_quiz": (305.0, 0.30),
        },
    }

    def medir(versao: str, tela: str, _rota: str, repeticao: int) -> dict[str, Any]:
        mediana_base, sigma = calibracao[versao][tela]
        fator_frio = 1.6 if repeticao == 1 else 1.0
        ttfb = float(rng.lognormal(mean=np.log(mediana_base * fator_frio), sigma=sigma))
        tempo_total = ttfb + float(rng.uniform(15.0, 45.0))
        return {
            "status_http": 200,
            "ttfb_ms": round(ttfb, 2),
            "tempo_total_ms": round(tempo_total, 2),
            "tamanho_bytes": 42100 if tela in ("curso", "tentativa_quiz") else 18450,
        }

    return coletar_amostras(medir, TELAS_S02, n_repeticoes)


def resolver_alvo_s02(
    args: argparse.Namespace,
) -> tuple[dict[str, str], tuple[tuple[str, str], ...], int]:
    """Devolve URLs por versão, telas S02 e o ``cmid`` do quiz."""
    cmid = extrair_cmid(args.rota_quiz)
    sobrescritas = {
        "curso": args.rota_curso,
        "tentativa_quiz": f"/mod/quiz/attempt.php?cmid={cmid}",
    }
    telas = tuple((nome, sobrescritas.get(nome, rota)) for nome, rota in TELAS_S02)
    urls = {"4.5_lts": args.url_4_5, "5.3_lts": args.url_5_3}
    return urls, telas, cmid


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coleta S02 Lab05 - Moodle")
    parser.add_argument(
        "--repeticoes",
        type=int,
        default=80,
        help="Número de repetições por tela e versão (default: 80)",
    )
    parser.add_argument(
        "--simulado",
        action="store_true",
        help="Gera dados sintéticos em dados/reais_simulado/ (não são medições)",
    )
    adicionar_args_alvo(parser)
    parser.add_argument(
        "--sem-purga",
        action="store_true",
        help="Não purga o cache antes da coleta (a repetição 1 deixa de ser fria)",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=None,
        help="Diretório de saída (default: dados/reais, ou dados/reais_simulado)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)

    if args.simulado:
        destino = args.saida or DIR_DADOS_S02_SIMULADO
        print(f"[SIMULADO S02] {args.repeticoes} repetições por tela (dados sintéticos)...")
        amostras = coletar_amostras_simuladas_s02(n_repeticoes=args.repeticoes)
        meta = {
            "origem": "simulado",
            "ordem_pares": "contrabalanceada_abba",
            "gerado_em": datetime.now(timezone.utc).isoformat(),
        }
    else:
        senha = os.environ.get("MOODLE_ALUNO_SENHA")
        if not senha:
            print("Defina MOODLE_ALUNO_SENHA (ver docker/.env.example).", file=sys.stderr)
            return 2
        destino = args.saida or DIR_DADOS_S02
        urls, telas, cmid = resolver_alvo_s02(args)

        def novo_cliente(versao: str) -> httpx.Client:
            return httpx.Client(
                base_url=urls[versao], follow_redirects=True, timeout=TIMEOUT_S
            )

        clientes = {v: novo_cliente(v) for v in VERSOES}
        publicos = {v: novo_cliente(v) for v in VERSOES}
        try:
            releases = {v: ler_release_moodle(SERVICOS[v]) for v in VERSOES}
            for cliente in clientes.values():
                autenticar(cliente, args.usuario, senha)
            if not args.sem_purga:
                for versao in VERSOES:
                    purgar_cache(SERVICOS[versao])
            print(f"Coletando S02: {args.repeticoes} repetições por tela e versão...")
            amostras = coletar_amostras_s02(
                clientes, publicos, telas, args.repeticoes, cmid=cmid
            )
        except (ErroColeta, httpx.HTTPError, subprocess.CalledProcessError) as erro:
            print(f"Coleta abortada: {erro}", file=sys.stderr)
            return 1
        finally:
            for cliente in (*clientes.values(), *publicos.values()):
                cliente.close()
        meta = {
            "origem": "real",
            "releases_moodle": releases,
            "ordem_pares": "contrabalanceada_abba",
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "cache_purgado_antes": not args.sem_purga,
        }

    caminho_csv, caminho_json = salvar_dados_piloto(
        amostras,
        destino,
        meta,
        telas=TELAS_S02,
        nome_csv=NOME_CSV_S02,
        nome_json=NOME_JSON_S02,
    )
    print("Coleta S02 concluída.")
    print(f"- Amostras: {caminho_csv} ({len(amostras)} registros)")
    print(f"- Resumo: {caminho_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
