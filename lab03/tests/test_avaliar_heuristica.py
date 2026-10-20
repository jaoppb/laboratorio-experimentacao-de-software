"""Testes da avaliação da heurística contra o consenso (Issue #62).

Fixtures sintéticas com matriz de confusão conhecida (nenhum dado real, nenhuma rede):
a heurística v1 sobre 10 releases tem VP=3, FP=1, FN=2, VN=4, logo
precisão = 3/4, recall = 3/5 e F1 = 2/3.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from analises import avaliar_heuristica as ah
from analises.avaliar_heuristica import (
    Amostra,
    AvaliacaoError,
    EntradaAusenteError,
    avaliar_todas,
    avaliar_versao,
    calcular_metricas,
    carregar_consenso,
    descrever_regra,
    listar_erros,
    main,
    montar_amostra,
)
from metricas.cfr_b import HEURISTICS

REPO = "org/repo"

_COMMITS_TYPE = pa.list_(
    pa.struct([("sha", pa.string()), ("committed_at", pa.string()), ("message", pa.string())])
)


def escrever_releases(
    releases_dir: Path, repo: str, linhas: list[tuple[str, str | None, str, list[str]]]
) -> None:
    """Grava o Parquet de releases no formato de `save_releases_to_parquet`.

    Cada linha é `(tag, previous_release, status, mensagens_de_commit)`.
    """
    releases_dir.mkdir(parents=True, exist_ok=True)
    tabela = pa.table(
        {
            "tag_name": pa.array([r[0] for r in linhas], pa.string()),
            "published_at": pa.array(
                [pd.Timestamp("2026-01-01", tz="UTC")] * len(linhas), pa.timestamp("us", tz="UTC")
            ),
            "prerelease": pa.array([False] * len(linhas), pa.bool_()),
            "previous_release": pa.array([r[1] for r in linhas], pa.string()),
            "status": pa.array([r[2] for r in linhas], pa.string()),
            "commits_count": pa.array([len(r[3]) for r in linhas], pa.int64()),
            "commits": pa.array(
                [
                    [
                        {"sha": f"{r[0]}-{j}", "committed_at": "2026-01-01T00:00:00+00:00", "message": m}
                        for j, m in enumerate(r[3])
                    ]
                    for r in linhas
                ],
                _COMMITS_TYPE,
            ),
        }
    )
    pq.write_table(tabela, releases_dir / f"{repo.replace('/', '__')}.parquet")


# (tag, previous, mensagens, consenso) — v1 prevê "sim" só com bump de patch + commit de fix.
CASOS_V1 = [
    ("1.0.1", "1.0.0", ["fix: crash"], "sim"),  # VP
    ("1.0.2", "1.0.1", ["Hotfix login"], "sim"),  # VP
    ("1.0.3", "1.0.2", ["revert: bad change"], "sim"),  # VP
    ("1.0.4", "1.0.3", ["fix: typo"], "não"),  # FP
    ("1.1.0", "1.0.4", ["fix: bug"], "sim"),  # FN (bump minor)
    ("1.1.1", "1.1.0", ["chore: deps"], "sim"),  # FN (sem fix)
    ("1.2.0", "1.1.1", ["feat: x"], "não"),  # VN
    ("1.2.1", "1.2.0", ["docs: y"], "não"),  # VN
    ("1.3.0", "1.2.1", ["feat: z"], "não"),  # VN
    ("2.0.0", "1.3.0", ["feat!: break"], "não"),  # VN
]


def montar_consenso(linhas: list[tuple[str, str, str]]) -> pd.DataFrame:
    """Consenso mínimo: `(repo, tag, release_corretiva)`."""
    return pd.DataFrame(
        {
            "repo_name": [r[0] for r in linhas],
            "tag_name": [r[1] for r in linhas],
            "release_corretiva": [r[2] for r in linhas],
        }
    )


@pytest.fixture
def cenario(tmp_path: Path) -> tuple[pd.DataFrame, Path]:
    """10 releases avaliáveis + 5 excluídas (um motivo diferente cada)."""
    releases_dir = tmp_path / "releases"
    linhas = [(t, p, "ok", m) for t, p, m, _ in CASOS_V1]
    linhas += [
        ("0.1.0", None, "first_release", []),
        ("0.2.0", "0.1.0", "not_found", []),
        ("0.3.0", None, "ok", ["fix: x"]),  # status ok mas sem anterior
    ]
    escrever_releases(releases_dir, REPO, linhas)
    consenso = [(REPO, t, c) for t, _, _, c in CASOS_V1]
    consenso += [
        (REPO, "0.1.0", "não"),
        (REPO, "0.2.0", "sim"),
        (REPO, "0.3.0", "sim"),
        (REPO, "9.9.9", "não"),  # tag que não está no Parquet
        ("org/sem-arquivo", "1.0.0", "sim"),  # repositório sem Parquet
    ]
    return montar_consenso(consenso), releases_dir


# --------------------------------------------------------------------------- #
# Métricas
# --------------------------------------------------------------------------- #
def test_calcular_metricas_matriz_conhecida():
    verdadeiro = [True] * 5 + [False] * 5
    previsto = [True] * 3 + [False] * 2 + [True] * 1 + [False] * 4
    p, r, f1, (vp, fp, fn, vn) = calcular_metricas(verdadeiro, previsto)
    assert (vp, fp, fn, vn) == (3, 1, 2, 4)
    assert p == pytest.approx(0.75)
    assert r == pytest.approx(0.6)
    assert f1 == pytest.approx(2 * 0.75 * 0.6 / (0.75 + 0.6))


def test_calcular_metricas_exemplo_do_guia():
    # Guia do Lab03: 40 marcadas, 30 confirmadas, 50 corretivas → P=0,75, R=0,60, F1≈0,67.
    verdadeiro = [True] * 30 + [True] * 20 + [False] * 10 + [False] * 40
    previsto = [True] * 30 + [False] * 20 + [True] * 10 + [False] * 40
    p, r, f1, _ = calcular_metricas(verdadeiro, previsto)
    assert (p, r) == (pytest.approx(0.75), pytest.approx(0.6))
    assert f1 == pytest.approx(0.6667, abs=1e-4)


def test_metricas_perfeitas():
    p, r, f1, _ = calcular_metricas([True, False, True], [True, False, True])
    assert (p, r, f1) == (1.0, 1.0, 1.0)


def test_metrica_indefinida_quando_nao_ha_previsao_positiva():
    p, r, f1, conf = calcular_metricas([True, True, False], [False, False, False])
    assert p is None  # nada marcado → precisão indefinida
    assert r == 0.0
    assert f1 == 0.0
    assert conf == (0, 0, 2, 1)


def test_metrica_indefinida_quando_consenso_sem_positivos():
    p, r, f1, _ = calcular_metricas([False, False], [True, False])
    assert p == 0.0
    assert r is None  # nenhuma corretiva no consenso → recall indefinido
    assert f1 == 0.0


def test_calcular_metricas_entradas_invalidas():
    with pytest.raises(AvaliacaoError, match="nenhuma release avaliável"):
        calcular_metricas([], [])
    with pytest.raises(ValueError):
        calcular_metricas([True], [True, False])


# --------------------------------------------------------------------------- #
# Carga e exclusões
# --------------------------------------------------------------------------- #
def test_montar_amostra_separa_avaliaveis_e_exclui_com_motivo(cenario):
    consenso, releases_dir = cenario
    amostra = montar_amostra(consenso, releases_dir)
    assert len(amostra.exemplos) == 10
    assert len(amostra.exclusoes) == 5
    assert amostra.motivos == {
        ah.MOTIVO_STATUS.format(status="first_release"): 1,
        ah.MOTIVO_STATUS.format(status="not_found"): 1,
        ah.MOTIVO_SEM_ANTERIOR: 1,
        ah.MOTIVO_TAG_AUSENTE: 1,
        ah.MOTIVO_SEM_ARQUIVO: 1,
    }
    primeira = amostra.exemplos[0]
    assert (primeira.tag_name, primeira.previous_release, primeira.consenso) == ("1.0.1", "1.0.0", True)
    assert [c.message for c in primeira.commits] == ["fix: crash"]


def test_avaliar_versao_v1_sobre_cenario(cenario):
    consenso, releases_dir = cenario
    resultado = avaliar_versao(montar_amostra(consenso, releases_dir), "v1")
    assert (resultado.vp, resultado.fp, resultado.fn, resultado.vn) == (3, 1, 2, 4)
    assert resultado.precisao == pytest.approx(0.75)
    assert resultado.recall == pytest.approx(0.6)
    assert resultado.f1 == pytest.approx(2 / 3)
    assert (resultado.n_avaliadas, resultado.n_excluidas) == (10, 5)
    assert resultado.atinge_meta is False  # 0,667 < 0,70
    assert resultado.regra == descrever_regra("v1")
    assert "patch" in resultado.regra


def test_meta_f1_configuravel(cenario):
    consenso, releases_dir = cenario
    amostra = montar_amostra(consenso, releases_dir)
    assert avaliar_versao(amostra, "v1", meta_f1=0.66).atinge_meta is True


def test_releases_dir_ausente(tmp_path):
    consenso = montar_consenso([(REPO, "1.0.0", "sim")])
    with pytest.raises(EntradaAusenteError, match="persistir_amostra_ouro"):
        montar_amostra(consenso, tmp_path / "nao_existe")


def test_todas_excluidas_nao_tem_metricas(tmp_path):
    (tmp_path / "releases").mkdir()
    amostra = montar_amostra(montar_consenso([(REPO, "1.0.0", "sim")]), tmp_path / "releases")
    assert amostra.exemplos == [] and len(amostra.exclusoes) == 1
    with pytest.raises(AvaliacaoError, match="nenhuma release avaliável"):
        avaliar_versao(amostra, "v1")


# --------------------------------------------------------------------------- #
# Versões da heurística
# --------------------------------------------------------------------------- #
@pytest.fixture
def heuristicas_extras(monkeypatch):
    """Registra versões sintéticas para testar a avaliação de várias versões."""

    def sempre(previous_tag, tag, commits):
        """vA: toda release é corretiva."""
        return True

    def nunca(previous_tag, tag, commits):
        """vN: nenhuma release é corretiva."""
        return False

    monkeypatch.setitem(HEURISTICS, "vA", sempre)
    monkeypatch.setitem(HEURISTICS, "vN", nunca)


def test_avalia_todas_as_versoes_registradas(cenario, heuristicas_extras):
    consenso, releases_dir = cenario
    amostra = montar_amostra(consenso, releases_dir)
    resultados = {r.versao: r for r in avaliar_todas(amostra)}
    assert list(resultados) == list(HEURISTICS)  # ordem de registro
    sempre, nunca = resultados["vA"], resultados["vN"]
    assert (sempre.vp, sempre.fp, sempre.fn, sempre.vn) == (5, 5, 0, 0)
    assert (sempre.precisao, sempre.recall) == (pytest.approx(0.5), 1.0)
    assert sempre.regra == "vA: toda release é corretiva."
    assert nunca.precisao is None and nunca.recall == 0.0 and nunca.f1 == 0.0
    assert nunca.atinge_meta is False
    assert {r.n_avaliadas for r in resultados.values()} == {10}  # mesmo conjunto para todas


def test_avaliar_versoes_selecionadas_e_desconhecida(cenario, heuristicas_extras):
    consenso, releases_dir = cenario
    amostra = montar_amostra(consenso, releases_dir)
    assert [r.versao for r in avaliar_todas(amostra, ["vN"])] == ["vN"]
    with pytest.raises(AvaliacaoError, match="desconhecida.*v99"):
        avaliar_todas(amostra, ["v99"])


# --------------------------------------------------------------------------- #
# Análise de erros
# --------------------------------------------------------------------------- #
def test_listar_erros_fp_e_fn(cenario):
    consenso, releases_dir = cenario
    erros = listar_erros(montar_amostra(consenso, releases_dir), ["v1"])
    fp = erros[erros["tipo"] == ah.TIPO_FP]
    fn = erros[erros["tipo"] == ah.TIPO_FN]
    assert list(fp["tag_name"]) == ["1.0.4"]
    assert sorted(fn["tag_name"]) == ["1.1.0", "1.1.1"]
    linha = fp.iloc[0]
    assert (linha["consenso"], linha["heuristica"], linha["bump_patch"]) == ("não", "sim", "sim")
    assert linha["mensagens_fix"] == "fix: typo"
    assert linha["n_commits_fix"] == 1
    minor = fn[fn["tag_name"] == "1.1.0"].iloc[0]
    assert minor["bump_patch"] == "não" and minor["mensagens_fix"] == "fix: bug"


def test_listar_erros_sem_erros_devolve_tabela_vazia_com_colunas(tmp_path):
    releases_dir = tmp_path / "r"
    escrever_releases(releases_dir, REPO, [("1.0.1", "1.0.0", "ok", ["fix: a"])])
    amostra = montar_amostra(montar_consenso([(REPO, "1.0.1", "sim")]), releases_dir)
    erros = listar_erros(amostra, ["v1"])
    assert erros.empty and "tipo" in erros.columns


# --------------------------------------------------------------------------- #
# Consenso
# --------------------------------------------------------------------------- #
def test_carregar_consenso_ausente(tmp_path):
    with pytest.raises(EntradaAusenteError, match="Consenso não encontrado"):
        carregar_consenso(tmp_path / "consenso.csv")


def test_carregar_consenso_valido_e_invalido(tmp_path):
    ok = tmp_path / "ok.csv"
    ok.write_text("repo_name,tag_name,release_corretiva\norg/a,v1,sim\norg/a,v2,não\n", encoding="utf-8")
    assert len(carregar_consenso(ok)) == 2

    sem_coluna = tmp_path / "sem_coluna.csv"
    sem_coluna.write_text("repo_name,tag_name\norg/a,v1\n", encoding="utf-8")
    with pytest.raises(AvaliacaoError, match="colunas ausentes: release_corretiva"):
        carregar_consenso(sem_coluna)

    valor_ruim = tmp_path / "ruim.csv"
    valor_ruim.write_text("repo_name,tag_name,release_corretiva\norg/a,v1,talvez\n", encoding="utf-8")
    with pytest.raises(AvaliacaoError, match="fora de"):
        carregar_consenso(valor_ruim)

    duplicado = tmp_path / "dup.csv"
    duplicado.write_text(
        "repo_name,tag_name,release_corretiva\norg/a,v1,sim\norg/a,v1,não\n", encoding="utf-8"
    )
    with pytest.raises(AvaliacaoError, match="duplicados"):
        carregar_consenso(duplicado)

    pendente = tmp_path / "pend.csv"
    pendente.write_text(
        "repo_name,tag_name,release_corretiva,release_corretiva_origem\norg/a,v1,sim,pendente\n",
        encoding="utf-8",
    )
    with pytest.raises(AvaliacaoError, match="pendente"):
        carregar_consenso(pendente)


# --------------------------------------------------------------------------- #
# Saída formatada
# --------------------------------------------------------------------------- #
def test_formatos_console_e_markdown(cenario):
    consenso, releases_dir = cenario
    amostra = montar_amostra(consenso, releases_dir)
    resultados = avaliar_todas(amostra)
    console = ah.formatar_console(resultados, amostra, 0.70)
    assert "avaliadas: 10 | excluídas: 5" in console
    assert "0.750" in console and "0.600" in console and "0.667" in console
    md = ah.formatar_markdown(resultados, amostra, 0.70)
    assert "| v1 |" in md and "| 0.750 | 0.600 | 0.667 | 10 | 5 | 3 | 1 | 2 | 4 | não |" in md
    assert "## Releases excluídas" in md and ah.MOTIVO_SEM_ARQUIVO in md


def test_markdown_sem_exclusoes_e_metrica_indefinida(tmp_path, heuristicas_extras):
    releases_dir = tmp_path / "r"
    escrever_releases(releases_dir, REPO, [("1.0.1", "1.0.0", "ok", ["feat: a"])])
    amostra = montar_amostra(montar_consenso([(REPO, "1.0.1", "sim")]), releases_dir)
    md = ah.formatar_markdown(avaliar_todas(amostra, ["vN"]), amostra, 0.70)
    assert "Nenhuma." in md and "n/d" in md


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def escrever_consenso_csv(path: Path, df: pd.DataFrame) -> None:
    df.to_csv(path, index=False, encoding="utf-8")


def test_cli_consenso_ausente_sai_com_codigo_2(tmp_path, capsys):
    codigo = main(["--consenso", str(tmp_path / "consenso.csv"), "--releases-dir", str(tmp_path)])
    assert codigo == 2
    err = capsys.readouterr().err
    assert "Consenso não encontrado" in err
    assert not (tmp_path / "consenso.csv").exists()  # nunca é criado


def test_cli_releases_dir_ausente_sai_com_codigo_2(tmp_path, capsys):
    consenso = tmp_path / "consenso.csv"
    escrever_consenso_csv(consenso, montar_consenso([(REPO, "1.0.0", "sim")]))
    assert main(["--consenso", str(consenso), "--releases-dir", str(tmp_path / "x")]) == 2
    assert "Diretório de releases não encontrado" in capsys.readouterr().err


def test_cli_fim_a_fim_markdown_e_erros(cenario, tmp_path, capsys):
    consenso_df, releases_dir = cenario
    consenso = tmp_path / "consenso.csv"
    escrever_consenso_csv(consenso, consenso_df)
    saida = tmp_path / "out" / "avaliacao.md"
    saida_erros = tmp_path / "out" / "erros.csv"

    codigo = main(
        [
            "--consenso", str(consenso), "--releases-dir", str(releases_dir),
            "--saida", str(saida), "--saida-erros", str(saida_erros), "--max-erros", "1",
        ]
    )  # fmt: skip

    assert codigo == 0
    out = capsys.readouterr().out
    assert "avaliadas: 10 | excluídas: 5" in out
    assert "Falsos positivos de v1: 1" in out and "Falsos negativos de v1: 2" in out
    assert "(+1; use --saida-erros" in out  # truncado em --max-erros 1
    assert "| 0.750 | 0.600 | 0.667 |" in saida.read_text(encoding="utf-8")
    erros = pd.read_csv(saida_erros)
    assert len(erros) == 3 and set(erros["tipo"]) == {ah.TIPO_FP, ah.TIPO_FN}


def test_cli_saida_csv(cenario, tmp_path):
    consenso_df, releases_dir = cenario
    consenso = tmp_path / "consenso.csv"
    escrever_consenso_csv(consenso, consenso_df)
    saida = tmp_path / "avaliacao.csv"
    assert main(["--consenso", str(consenso), "--releases-dir", str(releases_dir), "--saida", str(saida)]) == 0
    tabela = pd.read_csv(saida)
    assert list(tabela["versao"]) == ["v1"]
    assert tabela.loc[0, "f1"] == pytest.approx(2 / 3)
    assert tabela.loc[0, "n_excluidas"] == 5


def test_cli_nao_sobrescreve_sem_forcar_e_nunca_sobre_o_consenso(cenario, tmp_path, capsys):
    consenso_df, releases_dir = cenario
    consenso = tmp_path / "consenso.csv"
    escrever_consenso_csv(consenso, consenso_df)
    original = consenso.read_text(encoding="utf-8")
    base = ["--consenso", str(consenso), "--releases-dir", str(releases_dir)]

    saida = tmp_path / "avaliacao.md"
    saida.write_text("antigo", encoding="utf-8")
    assert main([*base, "--saida", str(saida)]) == 1
    assert "já existe" in capsys.readouterr().err
    assert saida.read_text(encoding="utf-8") == "antigo"
    assert main([*base, "--saida", str(saida), "--forcar"]) == 0
    assert saida.read_text(encoding="utf-8") != "antigo"

    assert main([*base, "--saida", str(consenso), "--forcar"]) == 1
    assert "arquivo de consenso" in capsys.readouterr().err
    assert consenso.read_text(encoding="utf-8") == original


def test_cli_versao_desconhecida_e_nenhuma_avaliavel(cenario, tmp_path, capsys):
    consenso_df, releases_dir = cenario
    consenso = tmp_path / "consenso.csv"
    escrever_consenso_csv(consenso, consenso_df)
    base = ["--consenso", str(consenso), "--releases-dir", str(releases_dir)]
    assert main([*base, "--versoes", "v99"]) == 1
    assert "desconhecida" in capsys.readouterr().err

    vazio = tmp_path / "vazio"
    vazio.mkdir()
    assert main(["--consenso", str(consenso), "--releases-dir", str(vazio)]) == 1
    assert "nenhuma release avaliável" in capsys.readouterr().err


def test_amostra_dataclass_motivos_vazio():
    assert Amostra(exemplos=[], exclusoes=[]).motivos == {}
