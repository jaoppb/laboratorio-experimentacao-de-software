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
import random
import re
import sys
import time
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

import httpx

from coleta_piloto import (
    RAIZ_LAB05,
    SERVICOS,
    TELAS_PUBLICAS,
    ErroColeta,
    _compose_exec,
    coletar_amostras,
    coletar_amostras_simuladas,
    construir_parser as construir_parser_base,
    executar_cli,
    medir_requisicao,
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

CALIBRACAO_SIMULADA_S02 = {
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

_PHP_DESCARTAR_TENTATIVA = (
    "define('CLI_SCRIPT', true);"
    "require '/var/www/html/config.php';"
    "require_once $CFG->dirroot . '/mod/quiz/locallib.php';"
    "$aid = (int) $argv[1];"
    "if ($att = $DB->get_record('quiz_attempts', ['id' => $aid])) {"
    "  $quiz = $DB->get_record('quiz', ['id' => $att->quiz], '*', MUST_EXIST);"
    "  $tx = $DB->start_delegated_transaction();"
    "  quiz_delete_attempt($att, $quiz);"
    "  $tx->allow_commit();"
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
    descartar_tentativa: Callable[[str, int], None] | None = None,
) -> list[dict[str, Any]]:
    """Mede todas as telas da S02 nas duas versões via HTTP.

    Para ``tentativa_quiz``, deriva ``cmid`` da própria rota, cria uma tentativa
    nova antes do GET medido e a apaga no bloco ``finally`` para manter o banco
    sem acúmulo entre repetições.
    """
    dormir = dormir or time.sleep
    descartar = descartar_tentativa or descartar_tentativa_quiz
    gerador = random.Random(semente)
    sesskeys: dict[str, str] = {}

    def medir(versao: str, tela: str, rota: str, _repeticao: int) -> dict[str, Any]:
        if tela == "tentativa_quiz":
            cmid = extrair_cmid(rota)
            cliente = clientes[versao]
            if versao not in sesskeys:
                sesskeys[versao] = extrair_sesskey(cliente, cmid)
            attempt_id = iniciar_tentativa_quiz(cliente, cmid, sesskeys[versao])
            try:
                medida = medir_requisicao(
                    cliente, f"/mod/quiz/attempt.php?attempt={attempt_id}&cmid={cmid}"
                )
            finally:
                descartar(SERVICOS[versao], attempt_id)
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
    return coletar_amostras_simuladas(
        n_repeticoes=n_repeticoes,
        semente=semente,
        telas=TELAS_S02,
        calibracao=CALIBRACAO_SIMULADA_S02,
        telas_grandes=frozenset({"curso", "tentativa_quiz"}),
    )


def resolver_alvo_s02(
    args: argparse.Namespace,
) -> tuple[dict[str, str], tuple[tuple[str, str], ...]]:
    """Devolve URLs por versão e telas S02 com as rotas informadas nas flags."""
    cmid = extrair_cmid(args.rota_quiz)
    sobrescritas = {
        "curso": args.rota_curso,
        "tentativa_quiz": f"/mod/quiz/attempt.php?cmid={cmid}",
    }
    telas = tuple((nome, sobrescritas.get(nome, rota)) for nome, rota in TELAS_S02)
    urls = {"4.5_lts": args.url_4_5, "5.3_lts": args.url_5_3}
    return urls, telas


def construir_parser() -> argparse.ArgumentParser:
    return construir_parser_base(
        descricao="Coleta S02 Lab05 - Moodle",
        default_repeticoes=80,
        help_simulado="Gera dados sintéticos em dados/reais_simulado/ (não são medições)",
        help_saida="Diretório de saída (default: dados/reais, ou dados/reais_simulado)",
    )


def main(argv: list[str] | None = None) -> int:
    return executar_cli(
        argv,
        parser=construir_parser(),
        dir_real=DIR_DADOS_S02,
        dir_simulado=DIR_DADOS_S02_SIMULADO,
        resolver=resolver_alvo_s02,
        coletar_real=coletar_amostras_s02,
        coletar_simulado=lambda n: coletar_amostras_simuladas_s02(n_repeticoes=n),
        telas_padrao=TELAS_S02,
        nome_csv=NOME_CSV_S02,
        nome_json=NOME_JSON_S02,
        rotulo="S02",
    )


if __name__ == "__main__":
    sys.exit(main())
