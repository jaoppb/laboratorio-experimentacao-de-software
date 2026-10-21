"""Sorteio da amostra-ouro e geração de planilhas de rotulação (Issue #63).

Este módulo implementa o protocolo de validação manual do Lab03 (Seção 6 do Guia):
1. Sorteia 60 repositórios da amostra final aceita (`dados/repositorios.parquet`),
   com semente fixa (default: 42) para reprodutibilidade estrita.
2. Para cada repositório sorteado, obtém suas releases publicadas dentro da janela
   (12 meses: 2025-10-01 a 2026-09-30, releases regulares, sem rascunhos nem pré-releases)
   e sorteia 5 releases com semente determinística por repositório.
3. Gera uma planilha em branco por avaliador (Marcela, Gabriel, João) e um template geral,
   em formato CSV (UTF-8) e Excel (.xlsx) com hyperlinks diretos no GitHub e validação
   de dados (dropdowns), totalmente cega para qualquer saída da heurística.
4. Exporta metadados do sorteio (`sorteio_info.json`) para rastreabilidade científica.

Sorteio incompleto (correção da Issue #63): se a primeira execução ocorreu antes de as
releases de todos os repositórios estarem persistidas, os repositórios sem releases saem
com linhas-placeholder (`TAG_PLACEHOLDER`). `completar_sorteio_pendente` conclui apenas
esses repositórios, com a mesma semente, método e janela, sem tocar nos já sorteados.

Execução (a partir de `lab03/`):
    uv run python -m analises.amostra_ouro
    uv run python -m analises.amostra_ouro --seed 42 --output-dir dados/amostra_ouro
    uv run python -m analises.amostra_ouro --completar-pendentes
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
import pandas as pd
import pyarrow.parquet as pq

from metricas.schemas import _parse_datetime, parse_window_end

logger = logging.getLogger(__name__)

# Configurações padrão conforme Guia do Lab03
DEFAULT_SEED = 42
DEFAULT_NUM_REPOS = 60
DEFAULT_RELEASES_PER_REPO = 5
DEFAULT_WINDOW_START = "2025-10-01"
DEFAULT_WINDOW_END = "2026-09-30"

# Tag gravada nas planilhas quando o repositório ainda não tinha releases persistidas.
# Linhas com esta tag NÃO são rotuláveis (não há release real por trás delas).
TAG_PLACEHOLDER = "(pendente de persistência)"

AVALIADORES = [
    {"id": "marcela", "nome": "Marcela Campos"},
    {"id": "gabriel", "nome": "Gabriel Assis"},
    {"id": "joao", "nome": "João Pedro Peres"},
]

OPCOES_TIPO_PROJETO = [
    "biblioteca/framework",
    "aplicação/serviço",
    "ferramenta CLI",
    "outro",
]

OPCOES_ENTREGA_REAL = [
    "sim",
    "não",
    "incerto",
]

OPCOES_RELEASE_CORRETIVA = [
    "sim",
    "não",
]


@dataclass
class ReleaseItem:
    tag_name: str
    published_at: str
    release_url: str


@dataclass
class RepoSampleItem:
    repo_idx: int
    full_name: str
    owner: str
    name: str
    repo_url: str
    stars: int
    language: str
    releases_count_window: int
    releases: list[ReleaseItem]


def sortear_repositorios(
    dataset_path: Path | str,
    n: int = DEFAULT_NUM_REPOS,
    seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
    """Sorteia `n` repositórios da amostra final com semente fixa (`random_state`)."""
    path = Path(dataset_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset de repositórios não encontrado: {path}")

    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)

    if len(df) < n:
        raise ValueError(f"Dataset possui apenas {len(df)} repositórios, menor que n={n}")

    # Sorteio reproduzível conforme Guia Seção 6: df.sample(n=60, random_state=42)
    sample_df = df.sample(n=n, random_state=seed).copy()
    sample_df = sample_df.reset_index(drop=True)
    return sample_df


def carregar_releases_repositorio(
    full_name: str,
    releases_dir: Path,
    window_start: datetime,
    window_end: datetime,
) -> list[ReleaseItem]:
    """Carrega as releases de um repositório a partir de `dados/releases/`."""
    owner, repo = full_name.split("/", 1)
    parquet_path = releases_dir / f"{owner}__{repo}.parquet"

    if not parquet_path.is_file():
        return []

    table = pq.read_table(parquet_path)
    tag_names = table.column("tag_name").to_pylist()
    published_ats = table.column("published_at").to_pylist()
    prereleases = (
        table.column("prerelease").to_pylist()
        if "prerelease" in table.column_names
        else [False] * len(tag_names)
    )

    releases: list[ReleaseItem] = []
    for tag, pub, is_pre in zip(tag_names, published_ats, prereleases):
        if is_pre:
            continue
        pub_dt = _parse_datetime(pub)
        if pub_dt is None:
            continue
        if window_start <= pub_dt <= window_end:
            url = f"https://github.com/{owner}/{repo}/releases/tag/{tag}"
            releases.append(
                ReleaseItem(
                    tag_name=tag,
                    published_at=pub_dt.isoformat(),
                    release_url=url,
                )
            )

    # Ordena cronologicamente por published_at
    releases.sort(key=lambda r: r.published_at)
    return releases


def sortear_releases_repositorio(
    releases: Sequence[ReleaseItem],
    n: int = DEFAULT_RELEASES_PER_REPO,
    seed: int = DEFAULT_SEED,
) -> list[ReleaseItem]:
    """Sorteia `n` releases com semente determinística, retornando em ordem cronológica."""
    if not releases:
        return []

    if len(releases) <= n:
        return sorted(releases, key=lambda r: r.published_at)

    # Converte para DataFrame para amostragem reproduzível com pandas
    df_rels = pd.DataFrame([asdict(r) for r in releases])
    sampled = df_rels.sample(n=n, random_state=seed)
    # Ordena as sorteadas em ordem cronológica para facilitar a leitura
    sampled = sampled.sort_values(by="published_at").reset_index(drop=True)

    return [
        ReleaseItem(
            tag_name=row["tag_name"],
            published_at=row["published_at"],
            release_url=row["release_url"],
        )
        for _, row in sampled.iterrows()
    ]


def construir_dados_amostra_ouro(
    sample_repos: pd.DataFrame,
    releases_dir: Path,
    window_start: datetime,
    window_end: datetime,
    releases_per_repo: int = DEFAULT_RELEASES_PER_REPO,
    base_seed: int = DEFAULT_SEED,
) -> list[RepoSampleItem]:
    """Constrói a estrutura completa da amostra-ouro com repositórios e releases sorteadas."""
    itens: list[RepoSampleItem] = []

    for idx, (_, row) in enumerate(sample_repos.iterrows(), start=1):
        full_name = str(row["full_name"])
        owner, name = full_name.split("/", 1)
        repo_url = f"https://github.com/{full_name}"

        # Semente determinística por repositório (derivada da base_seed e do índice)
        repo_seed = base_seed * 1000 + idx

        all_releases = carregar_releases_repositorio(
            full_name=full_name,
            releases_dir=releases_dir,
            window_start=window_start,
            window_end=window_end,
        )

        sampled_releases = sortear_releases_repositorio(
            releases=all_releases,
            n=releases_per_repo,
            seed=repo_seed,
        )

        itens.append(
            RepoSampleItem(
                repo_idx=idx,
                full_name=full_name,
                owner=owner,
                name=name,
                repo_url=repo_url,
                stars=int(row.get("stars", 0)),
                language=str(row.get("language", "Unknown")),
                releases_count_window=int(row.get("releases_count_window", len(all_releases))),
                releases=sampled_releases,
            )
        )

    return itens


def gerar_dataframe_rotulacao(itens: list[RepoSampleItem]) -> pd.DataFrame:
    """Gera DataFrame tabular em branco para rotulação manual independente.

    IMPORTANTE: Conforme o Guia Seção 6 e Requisitos da Issue #63, nenhuma
    coluna da heurística automática pode estar presente nesta tabela,
    garantindo o cegamento completo do avaliador.
    """
    linhas: list[dict[str, Any]] = []

    for item in itens:
        if not item.releases:
            # Caso o repositório não tenha releases persistidas ainda,
            # cria linhas indicativas para não quebrar a estrutura dos 60 repos
            for r_idx in range(1, DEFAULT_RELEASES_PER_REPO + 1):
                linhas.append(
                    {
                        "repo_idx": item.repo_idx,
                        "repo_name": item.full_name,
                        "repo_url": item.repo_url,
                        "tipo_projeto": "",
                        "entrega_real": "",
                        "release_idx": r_idx,
                        "tag_name": TAG_PLACEHOLDER,
                        "published_at": "",
                        "release_url": f"{item.repo_url}/releases",
                        "release_corretiva": "",
                        "notas_justificativa": "",
                    }
                )
            continue

        for r_idx, rel in enumerate(item.releases, start=1):
            linhas.append(
                {
                    "repo_idx": item.repo_idx,
                    "repo_name": item.full_name,
                    "repo_url": item.repo_url,
                    "tipo_projeto": "",
                    "entrega_real": "",
                    "release_idx": r_idx,
                    "tag_name": rel.tag_name,
                    "published_at": rel.published_at,
                    "release_url": rel.release_url,
                    "release_corretiva": "",
                    "notas_justificativa": "",
                }
            )

    return pd.DataFrame(linhas)


def salvar_planilha_excel(
    df: pd.DataFrame,
    output_path: Path,
    avaliador_nome: str | None = None,
) -> None:
    """Gera arquivo Excel (.xlsx) com layout limpo, validações de dados e aba de instruções."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()

    # --- Aba 1: Rotulação ---
    ws = wb.active
    ws.title = "Rotulacao_Amostra_Ouro"
    ws.views.sheetView[0].showGridLines = True

    # Cores e Estilos
    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
    header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    data_font = Font(name="Segoe UI", size=9)
    link_font = Font(name="Segoe UI", size=9, color="2563EB", underline="single")
    border_thin = Side(style="thin", color="E5E7EB")
    cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

    headers = [
        "repo_idx",
        "repo_name",
        "repo_url",
        "tipo_projeto",
        "entrega_real",
        "release_idx",
        "tag_name",
        "published_at",
        "release_url",
        "release_corretiva",
        "notas_justificativa",
    ]

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.row_dimensions[1].height = 28

    # Preenchimento de dados
    for row_idx, row in df.iterrows():
        excel_row = row_idx + 2
        ws.append(
            [
                row["repo_idx"],
                row["repo_name"],
                row["repo_url"],
                row["tipo_projeto"],
                row["entrega_real"],
                row["release_idx"],
                row["tag_name"],
                row["published_at"],
                row["release_url"],
                row["release_corretiva"],
                row["notas_justificativa"],
            ]
        )

        ws.row_dimensions[excel_row].height = 20

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=excel_row, column=col_num)
            cell.font = data_font
            cell.border = cell_border
            cell.alignment = Alignment(vertical="center")

            # Alinhamentos específicos
            if headers[col_num - 1] in ["repo_idx", "release_idx"]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif headers[col_num - 1] in ["tipo_projeto", "entrega_real", "release_corretiva"]:
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # Hyperlinks nos campos de URL
            if headers[col_num - 1] in ["repo_url", "release_url"] and cell.value:
                cell.hyperlink = str(cell.value)
                cell.font = link_font

    # Validações de Dados (Dropdowns no Excel)
    max_row = len(df) + 1
    if max_row >= 2:
        # Coluna D: tipo_projeto
        dv_tipo = DataValidation(
            type="list",
            formula1=f'"{",".join(OPCOES_TIPO_PROJETO)}"',
            allow_blank=True,
        )
        dv_tipo.error = "Selecione uma opção válida da lista"
        dv_tipo.errorTitle = "Opção Inválida"
        dv_tipo.prompt = "Escolha o tipo de projeto"
        ws.add_data_validation(dv_tipo)
        dv_tipo.add(f"D2:D{max_row}")

        # Coluna E: entrega_real
        dv_entrega = DataValidation(
            type="list",
            formula1=f'"{",".join(OPCOES_ENTREGA_REAL)}"',
            allow_blank=True,
        )
        dv_entrega.error = "Selecione: sim, não ou incerto"
        dv_entrega.errorTitle = "Opção Inválida"
        ws.add_data_validation(dv_entrega)
        dv_entrega.add(f"E2:E{max_row}")

        # Coluna J: release_corretiva
        dv_corretiva = DataValidation(
            type="list",
            formula1=f'"{",".join(OPCOES_RELEASE_CORRETIVA)}"',
            allow_blank=True,
        )
        dv_corretiva.error = "Selecione: sim ou não"
        dv_corretiva.errorTitle = "Opção Inválida"
        ws.add_data_validation(dv_corretiva)
        dv_corretiva.add(f"J2:J{max_row}")

    # Ajuste de larguras de coluna
    col_widths = {
        "A": 10,  # repo_idx
        "B": 32,  # repo_name
        "C": 36,  # repo_url
        "D": 24,  # tipo_projeto
        "E": 14,  # entrega_real
        "F": 12,  # release_idx
        "G": 22,  # tag_name
        "H": 22,  # published_at
        "I": 42,  # release_url
        "J": 18,  # release_corretiva
        "K": 35,  # notas_justificativa
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    ws.freeze_panes = "A2"

    # --- Aba 2: Instruções ---
    ws_inst = wb.create_sheet(title="Instrucoes")
    ws_inst.views.sheetView[0].showGridLines = True

    instrucoes = [
        ["GUIA DE ROTULAÇÃO MANUAL — AMOSTRA-OURO (LAB03)", ""],
        ["Avaliador:", avaliador_nome or "Não especificado"],
        ["Data de Geração:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["", ""],
        ["1. REGRAS DO PROCESSO", ""],
        ["• Cada integrante rotula TODA a amostra de forma 100% INDEPENDENTE.", ""],
        ["• É proibido consultar os colegas durante o preenchimento.", ""],
        ["• Os rótulos serão usados para calcular a concordância (Kappa de Fleiss).", ""],
        ["", ""],
        ["2. DIMENSÕES DE CLASSIFICAÇÃO", ""],
        ["(i) tipo_projeto", "Classifique o repositório em uma das 4 categorias:"],
        ["", "• biblioteca/framework: código para reuso em outros sistemas (ex.: react, zustand, fastapi)."],
        ["", "• aplicação/serviço: software final/servidor executado por usuários (ex.: posthog, ghost)."],
        ["", "• ferramenta CLI: utilitário executado na linha de comando (ex.: gemini-cli, ruff, yt-dlp)."],
        ["", "• outro: datasets, documentação, templates sem executável próprio."],
        ["", ""],
        ["(ii) entrega_real", "As releases do projeto representam entregas reais ao usuário final?"],
        ["", "• sim: releases correspondem a versões efetivamente utilizáveis/publicadas para usuários."],
        ["", "• não: releases são apenas tags automáticas de CI, testes vazios ou builds sem código novo."],
        ["", "• incerto: não foi possível determinar com segurança."],
        ["", ""],
        ["(iii) release_corretiva", "A release sorteada tem caráter corretivo (bugfix/hotfix/revert)?"],
        ["", "• Abra o link direto da release no GitHub (coluna release_url)."],
        ["", "• Leia as release notes e a lista de commits."],
        ["", "• sim: objetivo principal da release foi consertar bugs, corrigir regressões ou reverter falhas."],
        ["", "• não: release trouxe novas funcionalidades (features) ou atualizações planejadas."],
        ["", ""],
        ["Dúvidas ou ambiguidades devem ser registradas na coluna notas_justificativa.", ""],
    ]

    for r_i, linha in enumerate(instrucoes, start=1):
        ws_inst.append(linha)
        c1 = ws_inst.cell(row=r_i, column=1)
        c2 = ws_inst.cell(row=r_i, column=2)
        c1.font = Font(name="Segoe UI", size=10, bold=(linha[0].startswith(("GUIA", "1.", "2.", "(i)", "(ii)", "(iii)", "Avaliador:", "Data:"))))
        c2.font = Font(name="Segoe UI", size=10)

    ws_inst.column_dimensions["A"].width = 25
    ws_inst.column_dimensions["B"].width = 90

    wb.save(output_path)


def exportar_planilhas(
    df_rotulacao: pd.DataFrame,
    output_dir: Path,
    avaliadores: list[dict[str, str]] | None = None,
    lineterminator: str | None = None,
) -> dict[str, list[Path]]:
    """Exporta as planilhas por avaliador em CSV e Excel (.xlsx).

    `lineterminator` permite preservar o fim de linha de CSVs já versionados (CRLF).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    avals = avaliadores or AVALIADORES

    arquivos_gerados: dict[str, list[Path]] = {}

    # Template em branco
    template_csv = output_dir / "amostra_ouro_template.csv"
    template_xlsx = output_dir / "amostra_ouro_template.xlsx"
    df_rotulacao.to_csv(template_csv, index=False, encoding="utf-8-sig", lineterminator=lineterminator)
    salvar_planilha_excel(df_rotulacao, template_xlsx, avaliador_nome="Template")
    arquivos_gerados["template"] = [template_csv, template_xlsx]

    # Uma planilha para cada avaliador
    for av in avals:
        av_id = av["id"]
        av_nome = av["nome"]

        csv_path = output_dir / f"amostra_ouro_{av_id}.csv"
        xlsx_path = output_dir / f"amostra_ouro_{av_id}.xlsx"

        df_rotulacao.to_csv(csv_path, index=False, encoding="utf-8-sig", lineterminator=lineterminator)
        salvar_planilha_excel(df_rotulacao, xlsx_path, avaliador_nome=av_nome)

        arquivos_gerados[av_id] = [csv_path, xlsx_path]
        logger.info("Planilhas geradas para %s: %s, %s", av_nome, csv_path.name, xlsx_path.name)

    return arquivos_gerados


def executar_sorteio_amostra_ouro(
    dataset_path: Path | str = "dados/repositorios.parquet",
    releases_dir: Path | str = "dados/releases",
    output_dir: Path | str = "dados/amostra_ouro",
    num_repos: int = DEFAULT_NUM_REPOS,
    releases_per_repo: int = DEFAULT_RELEASES_PER_REPO,
    seed: int = DEFAULT_SEED,
    window_start_str: str = DEFAULT_WINDOW_START,
    window_end_str: str = DEFAULT_WINDOW_END,
) -> dict[str, Any]:
    """Pipeline completo de sorteio da amostra-ouro e exportação das planilhas."""
    dataset_path = Path(dataset_path)
    releases_dir = Path(releases_dir)
    output_dir = Path(output_dir)

    window_start = _parse_datetime(window_start_str)
    window_end = parse_window_end(window_end_str)

    logger.info("1. Sorteando %d repositórios com seed=%d...", num_repos, seed)
    sample_repos = sortear_repositorios(dataset_path=dataset_path, n=num_repos, seed=seed)

    logger.info("2. Construindo itens da amostra e sorteando %d releases por repositório...", releases_per_repo)
    itens = construir_dados_amostra_ouro(
        sample_repos=sample_repos,
        releases_dir=releases_dir,
        window_start=window_start,
        window_end=window_end,
        releases_per_repo=releases_per_repo,
        base_seed=seed,
    )

    logger.info("3. Gerando tabela de rotulação em branco...")
    df_rotulacao = gerar_dataframe_rotulacao(itens)

    logger.info("4. Exportando planilhas em CSV e Excel para cada avaliador em %s...", output_dir)
    arquivos = exportar_planilhas(df_rotulacao=df_rotulacao, output_dir=output_dir)

    # 5. Salva metadados do sorteio para replicação
    info_sorteio = {
        "timestamp_utc": datetime.now().isoformat(),
        "seed": seed,
        "num_repos": num_repos,
        "releases_per_repo": releases_per_repo,
        "window_start": window_start_str,
        "window_end": window_end_str,
        "dataset_origem": str(dataset_path),
        "total_linhas_planilha": len(df_rotulacao),
        "avaliadores": [a["nome"] for a in AVALIADORES],
        "repositorios": [
            {
                "idx": item.repo_idx,
                "full_name": item.full_name,
                "stars": item.stars,
                "language": item.language,
                "total_releases_window": item.releases_count_window,
                "releases_sorteadas": [r.tag_name for r in item.releases],
            }
            for item in itens
        ],
    }

    info_path = output_dir / "sorteio_info.json"
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info_sorteio, f, indent=2, ensure_ascii=False)

    logger.info("Sorteio concluído! Metadados gravados em %s", info_path)

    return {
        "num_repos": len(sample_repos),
        "total_linhas": len(df_rotulacao),
        "arquivos": {k: [str(p) for p in v] for k, v in arquivos.items()},
        "info_json": str(info_path),
        "itens": itens,
        "df_rotulacao": df_rotulacao,
    }


def _fim_de_linha(path: Path) -> str:
    """Retorna CRLF se o arquivo versionado usa CRLF; senão LF."""
    return "\r\n" if b"\r\n" in path.read_bytes() else "\n"


class SorteioInconsistenteError(Exception):
    """O sorteio registrado não pode ser completado de forma segura e determinística."""


def completar_sorteio_pendente(
    dataset_path: Path | str = "dados/repositorios.parquet",
    releases_dir: Path | str = "dados/releases",
    output_dir: Path | str = "dados/amostra_ouro",
    agora: datetime | None = None,
) -> dict[str, Any]:
    """Completa o sorteio dos repositórios sem releases sorteadas (placeholders).

    Lê `sorteio_info.json` e reaplica, **com os parâmetros ali registrados** (semente,
    releases por repositório e janela), exatamente o método original
    (`construir_dados_amostra_ouro`: semente por repositório `seed * 1000 + repo_idx`).
    Garante que:

    * o conjunto e a ordem dos repositórios coincidem com o registrado;
    * as releases já sorteadas são reproduzidas idênticas pelas releases persistidas
      (se alguma divergir, nada é gravado e `SorteioInconsistenteError` é levantado);
    * as linhas já reais da planilha permanecem idênticas (apenas placeholders mudam);
    * todo repositório pendente tem releases persistidas (senão, nada é gravado).

    É idempotente: sem repositórios pendentes, não reescreve nenhum arquivo.
    Retorna um resumo com os índices completados.
    """
    dataset_path = Path(dataset_path)
    releases_dir = Path(releases_dir)
    output_dir = Path(output_dir)
    info_path = output_dir / "sorteio_info.json"
    template_path = output_dir / "amostra_ouro_template.csv"

    info = json.loads(info_path.read_text(encoding="utf-8"))
    registrados = info["repositorios"]
    pendentes = [r["idx"] for r in registrados if not r["releases_sorteadas"]]
    if not pendentes:
        logger.info("Nenhum repositório pendente em %s; nada a completar.", info_path)
        return {"pendentes_completados": [], "total_linhas": info["total_linhas_planilha"], "alterado": False}

    seed = int(info["seed"])
    releases_per_repo = int(info["releases_per_repo"])
    window_start = _parse_datetime(info["window_start"])
    window_end = _parse_datetime(info["window_end"])

    sample_repos = sortear_repositorios(dataset_path, n=int(info["num_repos"]), seed=seed)
    if sample_repos["full_name"].tolist() != [r["full_name"] for r in registrados]:
        raise SorteioInconsistenteError(
            "Os repositórios sorteados com a semente registrada diferem de sorteio_info.json; "
            "o conjunto de repositórios não pode mudar."
        )

    itens = construir_dados_amostra_ouro(
        sample_repos=sample_repos,
        releases_dir=releases_dir,
        window_start=window_start,
        window_end=window_end,
        releases_per_repo=releases_per_repo,
        base_seed=seed,
    )

    divergentes = [
        r["full_name"]
        for r, item in zip(registrados, itens)
        if r["releases_sorteadas"] and [x.tag_name for x in item.releases] != r["releases_sorteadas"]
    ]
    if divergentes:
        raise SorteioInconsistenteError(
            "As releases persistidas não reproduzem o sorteio já registrado em: "
            f"{', '.join(divergentes[:5])}. O sorteio original não será alterado."
        )

    sem_releases = [item.full_name for item in itens if item.repo_idx in pendentes and not item.releases]
    if sem_releases:
        raise SorteioInconsistenteError(
            "Repositórios pendentes sem releases persistidas na janela em "
            f"{releases_dir}: {', '.join(sem_releases[:5])}. Rode analises.persistir_amostra_ouro."
        )

    df_novo = gerar_dataframe_rotulacao(itens)

    # Linhas já reais da planilha atual devem permanecer idênticas, conteúdo a conteúdo.
    atual = pd.read_csv(template_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    reais = atual[atual["tag_name"] != TAG_PLACEHOLDER]
    novo_str = df_novo.astype(str)
    chave = ["repo_idx", "release_idx"]
    esperado = novo_str.merge(reais[chave], on=chave, how="inner")
    if len(reais) != len(esperado) or not (
        esperado.sort_values(chave, key=lambda c: c.astype(int)).reset_index(drop=True)
        .equals(reais.sort_values(chave, key=lambda c: c.astype(int)).reset_index(drop=True))
    ):
        raise SorteioInconsistenteError(
            "As linhas reais da planilha atual não coincidem com o sorteio reproduzido; "
            "nada foi gravado."
        )

    # Preserva o fim de linha dos arquivos versionados (o diff mostra só o que mudou).
    fim_csv = _fim_de_linha(template_path)
    fim_json = _fim_de_linha(info_path)
    arquivos = exportar_planilhas(df_novo, output_dir, lineterminator=fim_csv)

    for registro, item in zip(registrados, itens):
        if registro["idx"] in pendentes:
            registro["releases_sorteadas"] = [r.tag_name for r in item.releases]
    agora = agora or datetime.now(timezone.utc)
    info["total_linhas_planilha"] = len(df_novo)
    info["conclusao_sorteio_pendente"] = {
        "timestamp_utc": agora.isoformat(),
        "repos_completados_idx": pendentes,
        "metodo": (
            "Conclusão do sorteio pendente: mesmo método do sorteio original "
            "(construir_dados_amostra_ouro; df.sample com random_state = seed*1000 + repo_idx), "
            "mesma semente, janela e releases por repositório registradas neste arquivo, "
            "aplicado apenas aos repositórios que estavam sem releases sorteadas. "
            "Os demais repositórios e o conjunto de 60 repositórios não foram alterados."
        ),
        "nota": (
            "Completa o sorteio pendente: na geração original (timestamp_utc acima) as releases "
            "destes repositórios ainda não estavam persistidas e as planilhas continham linhas "
            "'(pendente de persistência)'. Comando: "
            "uv run python -m analises.amostra_ouro --completar-pendentes"
        ),
    }
    texto = json.dumps(info, indent=2, ensure_ascii=False).replace("\n", fim_json)
    with open(info_path, "w", encoding="utf-8", newline="") as f:
        f.write(texto)

    logger.info("Sorteio pendente completado para %d repositórios.", len(pendentes))
    return {
        "pendentes_completados": pendentes,
        "total_linhas": len(df_novo),
        "alterado": True,
        "arquivos": {k: [str(p) for p in v] for k, v in arquivos.items()},
        "info_json": str(info_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sorteia amostra-ouro e gera planilhas de rotulação por avaliador (Issue #63)"
    )
    parser.add_argument("--dataset", default="dados/repositorios.parquet", help="Caminho do repositorios.parquet")
    parser.add_argument("--releases-dir", default="dados/releases", help="Diretório com releases persistidas")
    parser.add_argument("--output-dir", default="dados/amostra_ouro", help="Diretório de saída das planilhas")
    parser.add_argument("--num-repos", type=int, default=DEFAULT_NUM_REPOS, help="Quantidade de repositórios (default: 60)")
    parser.add_argument("--releases-per-repo", type=int, default=DEFAULT_RELEASES_PER_REPO, help="Releases por repositório (default: 5)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Semente pseudoaleatória (default: 42)")

    parser.add_argument(
        "--completar-pendentes",
        action="store_true",
        help="Completa apenas o sorteio dos repositórios sem releases sorteadas (placeholders), "
        "sem alterar os já sorteados (idempotente)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.completar_pendentes:
        res = completar_sorteio_pendente(
            dataset_path=args.dataset,
            releases_dir=args.releases_dir,
            output_dir=args.output_dir,
        )
        if res["alterado"]:
            print(f"[*] Sorteio completado para {len(res['pendentes_completados'])} repositórios pendentes")
            print(f"[*] Linhas na planilha: {res['total_linhas']}")
            print(f"[*] Metadados: {res['info_json']}")
        else:
            print("[*] Nenhum repositório pendente; nada a fazer")
        return 0

    res = executar_sorteio_amostra_ouro(
        dataset_path=args.dataset,
        releases_dir=args.releases_dir,
        output_dir=args.output_dir,
        num_repos=args.num_repos,
        releases_per_repo=args.releases_per_repo,
        seed=args.seed,
    )

    print(f"[*] Amostra-ouro gerada com sucesso!")
    print(f"[*] Repositórios sorteados: {res['num_repos']}")
    print(f"[*] Linhas na planilha: {res['total_linhas']}")
    print(f"[*] Metadados: {res['info_json']}")
    print(f"[*] Planilhas disponíveis em: {args.output_dir}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
