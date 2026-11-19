"""Valida a completude, a consistência e o formato dos dados da coleta piloto.

Uso::

    python scripts/validar_piloto.py [--dir dados/piloto] [--repeticoes 10]

Sai com código 0 quando não há problemas e 1 caso contrário (uma linha por problema).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from coleta_piloto import (
    COLUNAS_CSV,
    DIR_DADOS_PILOTO,
    TELAS,
    VERSOES,
    calcular_resumo_estatistico,
)

CAMPOS_INTEIROS = ("id", "repeticao", "status_http", "tamanho_bytes")
CAMPOS_REAIS = ("ttfb_ms", "tempo_total_ms")
TOLERANCIA_RESUMO = 0.011  # arredondamento a 2 casas


def ler_csv(caminho: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(caminho, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        return list(leitor.fieldnames or []), list(leitor)


def _converter(linha: dict[str, str], numero: int, problemas: list[str]) -> dict[str, Any] | None:
    convertida: dict[str, Any] = dict(linha)
    try:
        for campo in CAMPOS_INTEIROS:
            convertida[campo] = int(linha[campo])
        for campo in CAMPOS_REAIS:
            convertida[campo] = float(linha[campo])
    except (TypeError, ValueError, KeyError) as erro:
        problemas.append(f"linha {numero}: valor não numérico ou ausente ({erro})")
        return None
    return convertida


def validar_amostras(
    colunas: list[str],
    linhas: list[dict[str, str]],
    repeticoes: int = 10,
) -> list[str]:
    """Retorna a lista de problemas encontrados no CSV bruto (vazia se válido)."""
    problemas: list[str] = []

    if colunas != list(COLUNAS_CSV):
        problemas.append(f"colunas inesperadas: {colunas} (esperado {list(COLUNAS_CSV)})")
        return problemas

    esperado = repeticoes * len(TELAS) * len(VERSOES)
    if len(linhas) != esperado:
        problemas.append(f"{len(linhas)} linhas (esperado {esperado})")

    telas_validas = {nome: rota for nome, rota in TELAS}
    contagem: dict[tuple[str, str], int] = {}
    versao_anterior = None

    for numero, bruta in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        linha = _converter(bruta, numero, problemas)
        if linha is None:
            continue

        if linha["id"] != numero - 1:
            problemas.append(f"linha {numero}: id {linha['id']} fora de sequência")
        if linha["versao"] not in VERSOES:
            problemas.append(f"linha {numero}: versão desconhecida {linha['versao']!r}")
        if linha["tela"] not in telas_validas:
            problemas.append(f"linha {numero}: tela desconhecida {linha['tela']!r}")
        if linha["status_http"] != 200:
            problemas.append(f"linha {numero}: status_http {linha['status_http']} != 200")
        if linha["ttfb_ms"] <= 0:
            problemas.append(f"linha {numero}: ttfb_ms não positivo")
        if linha["ttfb_ms"] > linha["tempo_total_ms"]:
            problemas.append(f"linha {numero}: ttfb_ms maior que tempo_total_ms")
        if linha["tamanho_bytes"] <= 0:
            problemas.append(f"linha {numero}: tamanho_bytes não positivo")
        if not 1 <= linha["repeticao"] <= repeticoes:
            problemas.append(f"linha {numero}: repeticao {linha['repeticao']} fora de 1..{repeticoes}")
        esperado_cache = "cold" if linha["repeticao"] == 1 else "warm"
        if linha["cache"] != esperado_cache:
            problemas.append(
                f"linha {numero}: cache {linha['cache']!r} (esperado {esperado_cache!r})"
            )
        if linha["versao"] == versao_anterior:
            problemas.append(f"linha {numero}: versão repetida em sequência (ordem não alternada)")
        versao_anterior = linha["versao"]

        chave = (linha["versao"], linha["tela"])
        contagem[chave] = contagem.get(chave, 0) + 1

    for versao in VERSOES:
        for tela, _ in TELAS:
            n = contagem.get((versao, tela), 0)
            if n != repeticoes:
                problemas.append(f"{versao}/{tela}: {n} amostras (esperado {repeticoes})")

    return problemas


def validar_resumo(
    amostras: list[dict[str, Any]],
    resumo: dict[str, Any],
) -> list[str]:
    """Confere que o JSON de resumo corresponde ao recálculo a partir do CSV."""
    problemas: list[str] = []
    recalculado = calcular_resumo_estatistico(amostras)["versoes"]
    gravado = resumo.get("versoes", {})

    for versao in VERSOES:
        for tela, _ in TELAS:
            esperado = recalculado.get(versao, {}).get(tela)
            atual = gravado.get(versao, {}).get(tela)
            if esperado is None or atual is None:
                problemas.append(f"resumo: {versao}/{tela} ausente")
                continue
            for metrica, valor in esperado.items():
                if metrica not in atual or abs(atual[metrica] - valor) > TOLERANCIA_RESUMO:
                    problemas.append(
                        f"resumo: {versao}/{tela}/{metrica} = {atual.get(metrica)} "
                        f"(recalculado {valor})"
                    )
    return problemas


def validar_diretorio(diretorio: Path, repeticoes: int = 10) -> list[str]:
    caminho_csv = diretorio / "amostra_piloto.csv"
    caminho_json = diretorio / "resumo_piloto.json"
    for caminho in (caminho_csv, caminho_json):
        if not caminho.is_file():
            return [f"arquivo ausente: {caminho}"]

    colunas, linhas = ler_csv(caminho_csv)
    problemas = validar_amostras(colunas, linhas, repeticoes)
    if problemas:
        return problemas

    amostras = [
        {**l, **{c: float(l[c]) for c in CAMPOS_REAIS}} for l in linhas
    ]
    with open(caminho_json, encoding="utf-8") as f:
        resumo = json.load(f)
    return validar_resumo(amostras, resumo)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida os dados da coleta piloto")
    parser.add_argument("--dir", type=Path, default=DIR_DADOS_PILOTO)
    parser.add_argument("--repeticoes", type=int, default=10)
    args = parser.parse_args(argv)

    problemas = validar_diretorio(args.dir, args.repeticoes)
    if problemas:
        print(f"{len(problemas)} problema(s) em {args.dir}:", file=sys.stderr)
        for problema in problemas:
            print(f"- {problema}", file=sys.stderr)
        return 1
    print(f"OK: dados de {args.dir} completos, consistentes e no formato esperado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
