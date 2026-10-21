"""Testes do módulo de concordância (kappa de Fleiss) e consenso (Issue #65).

Usam fixtures sintéticas com kappa calculado à mão. Nenhum teste depende dos rótulos
humanos reais, exceto a checagem opcional de formato de `rotulos_marcela.csv`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from analises.amostra_ouro import TAG_PLACEHOLDER
from analises.concordancia import (
    AVISO_ROTULOS_IA,
    DIMENSOES,
    SUFIXO_LINHAS_INVALIDAS,
    ArquivosAusentesError,
    ConcordanciaError,
    RotulosInvalidosError,
    calcular_kappa_matriz,
    calcular_kappas,
    carregar_avaliadores,
    carregar_origem_validada,
    carregar_origens,
    carregar_csv,
    carregar_linhas_invalidas,
    carregar_rotulos_validados,
    formatar_proveniencia,
    gerar_consenso_automatico,
    gerar_modelo_consenso,
    interpretar_landis_koch,
    listar_divergencias,
    main,
    rotulos_por_unidade,
    resumir_proveniencia,
    validar_consenso,
    validar_planilha_referencia,
    validar_rotulos,
    votar,
)

DIM = {d.nome: d for d in DIMENSOES}
LAB03 = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Fixtures auxiliares
# --------------------------------------------------------------------------- #
def make_referencia(n_repos: int, releases: int = 2) -> pd.DataFrame:
    linhas = []
    for r in range(1, n_repos + 1):
        for i in range(1, releases + 1):
            linhas.append(
                {
                    "repo_idx": str(r),
                    "repo_name": f"org/repo{r}",
                    "repo_url": f"https://github.com/org/repo{r}",
                    "tipo_projeto": "",
                    "entrega_real": "",
                    "release_idx": str(i),
                    "tag_name": f"v{r}.{i}",
                    "published_at": "2026-01-01T00:00:00+00:00",
                    "release_url": f"https://github.com/org/repo{r}/releases/tag/v{r}.{i}",
                    "release_corretiva": "",
                    "notas_justificativa": "",
                }
            )
    return pd.DataFrame(linhas)


def preencher(
    ref: pd.DataFrame,
    tipo: list[str] | None = None,
    entrega: list[str] | None = None,
    corretiva: list[str] | None = None,
) -> pd.DataFrame:
    """Preenche a planilha: `tipo`/`entrega` por repositório; `corretiva` por linha."""
    df = ref.copy()
    n_repos = df["repo_idx"].nunique()
    tipo = tipo or ["aplicação/serviço"] * n_repos
    entrega = entrega or ["sim"] * n_repos
    corretiva = corretiva or ["não"] * len(df)
    por_repo = df["repo_idx"].astype(int) - 1
    df["tipo_projeto"] = [tipo[i] for i in por_repo]
    df["entrega_real"] = [entrega[i] for i in por_repo]
    df["release_corretiva"] = corretiva
    return df


def gravar(df: pd.DataFrame, path: Path) -> Path:
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def trio(ref: pd.DataFrame, **por_avaliador: dict) -> dict[str, pd.DataFrame]:
    return {a: preencher(ref, **kw) for a, kw in por_avaliador.items()}


# --------------------------------------------------------------------------- #
# Kappa com valores conhecidos
# --------------------------------------------------------------------------- #
def test_kappa_concordancia_perfeita_e_1():
    ref = make_referencia(4)
    tipos = ["biblioteca/framework", "aplicação/serviço", "ferramenta CLI", "outro"]
    corretivas = ["sim", "não", "não", "sim", "sim", "não", "não", "não"]
    kw = {"tipo": tipos, "corretiva": corretivas}
    rotulos = trio(ref, marcela=kw, gabriel=kw, joao=kw)

    res = {r.dimensao: r for r in calcular_kappas(rotulos, ref)}

    assert res["tipo_projeto"].kappa == pytest.approx(1.0)
    assert res["release_corretiva"].kappa == pytest.approx(1.0)
    assert res["tipo_projeto"].concordancia_unanime_pct == 100.0
    assert res["release_corretiva"].interpretacao == "quase perfeita"


def test_kappa_binario_calculado_a_mao_um_terco():
    # 4 releases, 3 avaliadores, categorias sim/não:
    #   u1 (sim,sim,sim) u2 (não,não,não) u3 (sim,sim,não) u4 (sim,não,não)
    #   P_i = 1, 1, 1/3, 1/3 -> P̄ = 2/3 ; p_sim = p_não = 1/2 -> P_e = 1/2
    #   kappa = (2/3 - 1/2) / (1 - 1/2) = 1/3
    ref = make_referencia(2, releases=2)
    rotulos = trio(
        ref,
        marcela={"corretiva": ["sim", "não", "sim", "sim"]},
        gabriel={"corretiva": ["sim", "não", "sim", "não"]},
        joao={"corretiva": ["sim", "não", "não", "não"]},
    )

    res = {r.dimensao: r for r in calcular_kappas(rotulos, ref)}["release_corretiva"]

    assert res.n_unidades == 4
    assert res.n_avaliadores == 3
    assert res.kappa == pytest.approx(1 / 3)
    assert res.concordancia_unanime_pct == pytest.approx(50.0)
    assert res.interpretacao == "razoável"


def test_kappa_tres_categorias_calculado_a_mao():
    # 4 repositórios, A=biblioteca/framework, B=aplicação/serviço, C=ferramenta CLI:
    #   u1 (A,A,A) u2 (A,B,C) u3 (B,B,C) u4 (C,C,C)
    #   P_i = 1, 0, 1/3, 1 -> P̄ = 7/12 ; p = (4/12, 3/12, 5/12) -> P_e = 25/72
    #   kappa = (7/12 - 25/72) / (1 - 25/72) = 17/47
    A, B, C = "biblioteca/framework", "aplicação/serviço", "ferramenta CLI"
    ref = make_referencia(4)
    rotulos = trio(
        ref,
        marcela={"tipo": [A, A, B, C]},
        gabriel={"tipo": [A, B, B, C]},
        joao={"tipo": [A, C, C, C]},
    )

    res = {r.dimensao: r for r in calcular_kappas(rotulos, ref)}["tipo_projeto"]

    assert res.kappa == pytest.approx(17 / 47)
    assert res.interpretacao == "razoável"


def test_unidade_de_analise_repo_conta_repositorios_e_nao_linhas():
    ref = make_referencia(4, releases=5)  # 20 linhas, 4 repositórios
    rotulos = trio(
        ref,
        marcela={"entrega": ["sim", "não", "sim", "sim"]},
        gabriel={"entrega": ["sim", "não", "sim", "não"]},
        joao={"entrega": ["sim", "não", "não", "não"]},
    )

    res = {r.dimensao: r for r in calcular_kappas(rotulos, ref)}

    assert res["entrega_real"].n_unidades == 4
    assert res["entrega_real"].unidade == "repositorio"
    assert res["entrega_real"].kappa == pytest.approx(1 / 3)  # mesmo padrão do caso binário
    assert res["release_corretiva"].n_unidades == 20
    assert res["release_corretiva"].unidade == "release"


def test_kappa_independe_da_ordem_dos_avaliadores():
    ref = make_referencia(2, releases=2)
    kw = {
        "marcela": {"corretiva": ["sim", "não", "sim", "sim"]},
        "gabriel": {"corretiva": ["sim", "não", "sim", "não"]},
        "joao": {"corretiva": ["sim", "não", "não", "não"]},
    }
    k1 = calcular_kappas(trio(ref, **kw), ref)[2].kappa
    k2 = calcular_kappas(trio(ref, **dict(reversed(kw.items()))), ref)[2].kappa
    assert k1 == pytest.approx(k2)


def test_kappa_indefinido_sem_variabilidade():
    ref = make_referencia(3)
    rotulos = trio(ref, marcela={}, gabriel={}, joao={})  # todos 'sim' em entrega_real

    res = {r.dimensao: r for r in calcular_kappas(rotulos, ref)}["entrega_real"]

    assert res.kappa is None
    assert res.concordancia_unanime_pct == 100.0
    assert "indefinido" in res.interpretacao


def test_kappa_matriz_invalida_levanta_erro():
    with pytest.raises(ConcordanciaError):
        calcular_kappa_matriz(pd.DataFrame(), DIM["tipo_projeto"])


@pytest.mark.parametrize(
    "kappa,faixa",
    [
        (-0.1, "pobre"),
        (0.0, "leve"),
        (0.20, "leve"),
        (0.21, "razoável"),
        (0.40, "razoável"),
        (0.41, "moderada"),
        (0.60, "moderada"),
        (0.61, "substancial"),
        (0.80, "substancial"),
        (0.81, "quase perfeita"),
        (1.0, "quase perfeita"),
    ],
)
def test_interpretacao_landis_koch(kappa, faixa):
    assert interpretar_landis_koch(kappa) == faixa


def test_rotulos_por_unidade_forma_e_ordem():
    ref = make_referencia(3, releases=5)
    rotulos = trio(ref, marcela={}, gabriel={}, joao={})
    assert rotulos_por_unidade(rotulos, DIM["tipo_projeto"], ref).shape == (3, 3)
    matriz = rotulos_por_unidade(rotulos, DIM["release_corretiva"], ref)
    assert matriz.shape == (15, 3)
    assert matriz.index[0] == "1/1"


# --------------------------------------------------------------------------- #
# Validação de formato
# --------------------------------------------------------------------------- #
@pytest.fixture
def ref() -> pd.DataFrame:
    return make_referencia(3, releases=2)


def test_validacao_aceita_arquivo_correto(ref):
    assert validar_rotulos(preencher(ref), ref) == []


def test_validacao_coluna_ausente(ref):
    erros = validar_rotulos(preencher(ref).drop(columns=["entrega_real"]), ref)
    assert erros == ["colunas ausentes: entrega_real"]


def test_validacao_quantidade_de_linhas(ref):
    erros = validar_rotulos(preencher(ref).iloc[:-1].reset_index(drop=True), ref)
    assert any("5 linhas, esperado 6" in e for e in erros)
    assert any("chaves ausentes" in e and "3/2" in e for e in erros)


def test_validacao_valor_fora_do_dominio_e_em_branco(ref):
    df = preencher(ref)
    df.loc[0, "release_corretiva"] = "talvez"
    df.loc[1, "release_corretiva"] = ""
    df["entrega_real"] = "incerto"
    df.loc[2:3, "tipo_projeto"] = "biblioteca"  # 'biblioteca' != 'biblioteca/framework'
    erros = validar_rotulos(df, ref)
    assert any("release_corretiva" in e and "'talvez'" in e for e in erros)
    assert any("release_corretiva em branco" in e for e in erros)
    assert any("tipo_projeto" in e and "'biblioteca'" in e for e in erros)
    assert not any("entrega_real" in e for e in erros)  # 'incerto' é válido em entrega_real


def test_validacao_incerto_nao_e_permitido_em_release_corretiva(ref):
    df = preencher(ref)
    df.loc[0, "release_corretiva"] = "incerto"
    assert any("release_corretiva" in e and "'incerto'" in e for e in validar_rotulos(df, ref))


def test_validacao_valor_por_repositorio_inconsistente(ref):
    df = preencher(ref)
    df.loc[0, "tipo_projeto"] = "outro"  # só uma das 2 linhas do repo 1
    erros = validar_rotulos(df, ref)
    assert any("tipo_projeto diverge entre as releases" in e and "1" in e for e in erros)


def test_validacao_chaves_duplicadas_e_inesperadas(ref):
    df = preencher(ref)
    df.loc[1, "release_idx"] = "1"  # duplica 1/1 e remove 1/2
    erros = validar_rotulos(df, ref)
    assert any("duplicadas" in e and "1/1" in e for e in erros)
    assert any("chaves ausentes" in e and "1/2" in e for e in erros)


def test_validacao_identificacao_diferente_da_planilha(ref):
    df = preencher(ref)
    df.loc[0, "tag_name"] = "v9.9"
    erros = validar_rotulos(df, ref)
    assert any("tag_name diferente da planilha" in e and "1/1" in e for e in erros)


def test_validacao_resume_muitos_erros(ref):
    df = preencher(ref)
    df["release_corretiva"] = "x"
    erro = next(e for e in validar_rotulos(df, ref) if e.startswith("release_corretiva com valor"))
    assert "(+1)" in erro  # 6 linhas, mostra 5


def test_planilha_referencia_invalida():
    with pytest.raises(RotulosInvalidosError):
        validar_planilha_referencia(pd.DataFrame({"repo_idx": ["1"]}))
    dup = pd.concat([make_referencia(1, 1)] * 2, ignore_index=True)
    with pytest.raises(RotulosInvalidosError, match="duplicados"):
        validar_planilha_referencia(dup)


def test_carregar_rotulos_validados_levanta_com_mensagem(tmp_path, ref):
    df = preencher(ref)
    df.loc[0, "release_corretiva"] = "talvez"
    caminho = gravar(df, tmp_path / "rotulos_joao.csv")
    with pytest.raises(RotulosInvalidosError, match="rotulos_joao.csv") as exc:
        carregar_rotulos_validados(caminho, ref, nome="rotulos_joao.csv")
    assert exc.value.erros


def test_carregar_csv_remove_bom_e_espacos(tmp_path, ref):
    df = preencher(ref)
    df["release_corretiva"] = " sim "
    carregado = carregar_csv(gravar(df, tmp_path / "x.csv"))
    assert carregado.columns[0] == "repo_idx"
    assert set(carregado["release_corretiva"]) == {"sim"}


def test_csv_ilegivel_vira_erro_de_formato(tmp_path, ref):
    caminho = tmp_path / "vazio.csv"
    caminho.write_text("", encoding="utf-8")
    with pytest.raises(RotulosInvalidosError, match="não foi possível ler"):
        carregar_rotulos_validados(caminho, ref)


def test_rotulos_marcela_reais_tem_formato_valido():
    """`rotulos_marcela.csv` tem as 300 linhas válidas (150 humanas + 150 de IA, #64/#57).

    A lista histórica das 150 linhas antigas void fica em `validacao/historico/` para que a
    ferramenta não a use automaticamente (ela ignoraria as 150 linhas agora válidas).
    """
    rotulos = LAB03 / "validacao" / "rotulos_marcela.csv"
    historico = LAB03 / "validacao" / "historico" / f"marcela{SUFIXO_LINHAS_INVALIDAS}"
    planilha = LAB03 / "dados" / "amostra_ouro" / "amostra_ouro_template.csv"
    if not (rotulos.is_file() and planilha.is_file() and historico.is_file()):
        pytest.skip("arquivos reais ausentes")
    referencia = carregar_csv(planilha)
    validar_planilha_referencia(referencia)  # sorteio completo: sem placeholders
    df = carregar_rotulos_validados(rotulos, referencia)
    assert len(df) == 300
    assert (df["tag_name"] != TAG_PLACEHOLDER).all()
    assert df["repo_idx"].nunique() == 60
    lista = carregar_linhas_invalidas(historico, referencia)
    assert len(lista) == 150
    # com a lista (uso antigo), só as 150 linhas humanas são consideradas
    assert len(carregar_rotulos_validados(rotulos, referencia, linhas_invalidas=lista)) == 150


# --------------------------------------------------------------------------- #
# Linhas-placeholder e lista explícita de linhas inválidas
# --------------------------------------------------------------------------- #
def _com_placeholders(df: pd.DataFrame, repos: tuple[str, ...]) -> pd.DataFrame:
    """Simula o estado antigo: linhas dos `repos` viram placeholder (sem release real)."""
    df = df.copy()
    alvo = df["repo_idx"].isin(repos)
    df.loc[alvo, "tag_name"] = TAG_PLACEHOLDER
    df.loc[alvo, "published_at"] = ""
    return df


def _lista(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df["tag_name"] == TAG_PLACEHOLDER, ["repo_idx", "release_idx"]].reset_index(drop=True)


def test_referencia_com_placeholder_e_rejeitada(ref):
    antiga = _com_placeholders(ref, ("2",))
    with pytest.raises(RotulosInvalidosError, match="placeholder.*--completar-pendentes"):
        validar_planilha_referencia(antiga)


def test_rotulos_com_placeholder_sao_rejeitados_com_erro_claro(ref):
    rotulos = _com_placeholders(preencher(ref), ("2",))

    erros = validar_rotulos(rotulos, ref)

    assert any("2 linha(s) com tag placeholder" in e and "2/1, 2/2" in e for e in erros)
    assert any("_linhas_invalidas.csv" in e for e in erros)


def test_lista_de_invalidas_aceita_arquivo_completo_com_linhas_void(tmp_path, ref):
    # O arquivo tem as 6 linhas (as do repo 2 são void); a planilha atual é real nas 6.
    rotulos = _com_placeholders(preencher(ref), ("2",))
    lista = _lista(rotulos)
    caminho = gravar(rotulos, tmp_path / "rotulos_marcela.csv")

    assert validar_rotulos(rotulos, ref, lista) == []
    df = carregar_rotulos_validados(caminho, ref, linhas_invalidas=lista)
    assert sorted(df["repo_idx"].unique()) == ["1", "3"]
    assert len(df) == 4


def test_lista_de_invalidas_aceita_arquivo_que_cobre_so_linhas_validas(ref):
    lista = ref.loc[ref["repo_idx"] == "2", ["repo_idx", "release_idx"]]
    apenas_validas = preencher(ref)[lambda d: d["repo_idx"] != "2"]

    assert validar_rotulos(apenas_validas, ref, lista) == []


def test_lista_de_invalidas_nao_dispensa_linhas_validas_faltantes(ref):
    lista = ref.loc[ref["repo_idx"] == "2", ["repo_idx", "release_idx"]]
    incompleto = preencher(ref)[lambda d: ~d["repo_idx"].isin(["2", "3"])]

    erros = validar_rotulos(incompleto, ref, lista)

    assert any("chaves ausentes" in e and "3/1" in e for e in erros)


def test_lista_de_invalidas_nao_relaxa_demais_validacoes(ref):
    rotulos = _com_placeholders(preencher(ref), ("2",))
    lista = _lista(rotulos)
    rotulos.loc[rotulos["repo_idx"] == "3", "entrega_real"] = "talvez"

    erros = validar_rotulos(rotulos, ref, lista)

    assert any("entrega_real com valor fora de" in e for e in erros)


def test_placeholder_fora_da_lista_continua_rejeitado(ref):
    rotulos = _com_placeholders(preencher(ref), ("2", "3"))
    lista = _lista(rotulos[rotulos["repo_idx"] == "2"])

    erros = validar_rotulos(rotulos, ref, lista)

    assert any("2 linha(s) com tag placeholder" in e and "3/1" in e for e in erros)


def test_lista_de_invalidas_com_chave_inexistente_e_rejeitada(tmp_path, ref):
    caminho = tmp_path / "x_linhas_invalidas.csv"
    caminho.write_text("repo_idx,release_idx\n99,1\n", encoding="utf-8")
    with pytest.raises(RotulosInvalidosError, match="inexistentes.*99/1"):
        carregar_linhas_invalidas(caminho, ref)


def test_lista_de_invalidas_duplicada_ou_sem_colunas_e_rejeitada(tmp_path, ref):
    dup = tmp_path / "dup.csv"
    dup.write_text("repo_idx,release_idx\n1,1\n1,1\n", encoding="utf-8")
    with pytest.raises(RotulosInvalidosError, match="duplicadas"):
        carregar_linhas_invalidas(dup, ref)
    sem = tmp_path / "sem.csv"
    sem.write_text("repo_idx\n1\n", encoding="utf-8")
    with pytest.raises(RotulosInvalidosError, match="colunas ausentes: release_idx"):
        carregar_linhas_invalidas(sem, ref)


def test_avaliador_parcial_usa_lista_ao_lado_do_arquivo_e_kappa_pede_linhas_faltantes(tmp_path, ref):
    validacao = tmp_path / "validacao"
    validacao.mkdir()
    marcela = _com_placeholders(preencher(ref), ("2",))
    gravar(marcela, validacao / "rotulos_marcela.csv")
    _lista(marcela).assign(chave_placeholder_antiga="x").to_csv(
        validacao / f"marcela{SUFIXO_LINHAS_INVALIDAS}", index=False
    )
    for a in ("gabriel", "joao"):
        gravar(preencher(ref), validacao / f"rotulos_{a}.csv")

    rotulos = carregar_avaliadores(validacao, ref)

    assert len(rotulos["marcela"]) == 4 and len(rotulos["gabriel"]) == 6
    with pytest.raises(ConcordanciaError, match="unidades sem rótulo.*marcela"):
        calcular_kappas(rotulos, ref)


def test_cli_validar_avaliador_parcial_informa_linhas_invalidas(tmp_path, ref, capsys):
    validacao = tmp_path / "v"
    validacao.mkdir()
    marcela = _com_placeholders(preencher(ref), ("2",))
    gravar(marcela, validacao / "rotulos_marcela.csv")
    base = ["--validacao-dir", str(validacao), "--planilha", str(gravar(ref, tmp_path / "p.csv"))]

    # Sem a lista: erro claro, código 1.
    assert main(["validar", *base, "--avaliadores", "marcela"]) == 1
    assert "placeholder" in capsys.readouterr().err

    _lista(marcela).to_csv(validacao / f"marcela{SUFIXO_LINHAS_INVALIDAS}", index=False)
    assert main(["validar", *base, "--avaliadores", "marcela"]) == 0
    out = capsys.readouterr().out
    assert "4 linhas válidas" in out and "2 inválidas" in out


def test_consenso_com_placeholder_e_rejeitado(ref, rotulos_divergentes):
    modelo = gerar_modelo_consenso(rotulos_divergentes, ref)
    antigo = _com_placeholders(modelo, ("2",))
    assert any("placeholder" in e for e in validar_consenso(antigo, ref))


# --------------------------------------------------------------------------- #
# Arquivos ausentes
# --------------------------------------------------------------------------- #
def test_menos_de_tres_avaliadores_falha_com_mensagem_clara(tmp_path, ref):
    gravar(preencher(ref), tmp_path / "rotulos_marcela.csv")
    with pytest.raises(ArquivosAusentesError) as exc:
        carregar_avaliadores(tmp_path, ref)
    assert exc.value.ausentes == ["gabriel", "joao"]
    assert "rotulos_gabriel.csv" in str(exc.value)
    assert "rotulos_joao.csv" in str(exc.value)


def test_carregar_avaliadores_subconjunto(tmp_path, ref):
    gravar(preencher(ref), tmp_path / "rotulos_marcela.csv")
    assert list(carregar_avaliadores(tmp_path, ref, ["marcela"])) == ["marcela"]


# --------------------------------------------------------------------------- #
# Votação, divergências e consenso
# --------------------------------------------------------------------------- #
def test_votar_regra_de_maioria():
    assert votar(["sim", "sim", "sim"]) == ("sim", "unanimidade")
    assert votar(["sim", "não", "sim"]) == ("sim", "maioria")
    assert votar(["sim", "não", "incerto"]) == (None, "pendente")


@pytest.fixture
def rotulos_divergentes(ref):
    # 3 repositórios x 2 releases
    A, B, C = "biblioteca/framework", "aplicação/serviço", "ferramenta CLI"
    return trio(
        ref,
        marcela={"tipo": [A, B, C], "entrega": ["sim", "sim", "sim"], "corretiva": ["sim", "não", "não", "não", "sim", "sim"]},
        gabriel={"tipo": [A, B, B], "entrega": ["sim", "não", "incerto"], "corretiva": ["sim", "não", "não", "não", "sim", "não"]},
        joao={"tipo": [A, A, "outro"], "entrega": ["sim", "não", "não"], "corretiva": ["sim", "não", "não", "não", "sim", "não"]},
    )  # fmt: skip


def test_listar_divergencias(ref, rotulos_divergentes):
    div = listar_divergencias(rotulos_divergentes, ref)

    por_dim = div.groupby("dimensao").size().to_dict()
    assert por_dim == {"tipo_projeto": 2, "entrega_real": 2, "release_corretiva": 1}

    tipo2 = div[(div.dimensao == "tipo_projeto") & (div.repo_idx == "2")].iloc[0]
    assert tipo2["padrao_votos"] == "2-1"
    assert tipo2["sugestao_maioria"] == "aplicação/serviço"
    assert tipo2["decisao"] == "maioria"
    assert (tipo2["rotulo_marcela"], tipo2["rotulo_gabriel"], tipo2["rotulo_joao"]) == (
        "aplicação/serviço", "aplicação/serviço", "biblioteca/framework",
    )  # fmt: skip

    tipo3 = div[(div.dimensao == "tipo_projeto") & (div.repo_idx == "3")].iloc[0]
    assert tipo3["padrao_votos"] == "1-1-1"
    assert tipo3["sugestao_maioria"] == ""
    assert tipo3["decisao"] == "pendente"

    corr = div[div.dimensao == "release_corretiva"].iloc[0]
    assert (corr["repo_idx"], corr["release_idx"], corr["tag_name"]) == ("3", "2", "v3.2")
    assert corr["unidade"] == "release"


def test_sem_divergencias_gera_tabela_vazia(ref):
    rotulos = trio(ref, marcela={}, gabriel={}, joao={})
    assert listar_divergencias(rotulos, ref).empty


def test_modelo_de_consenso(ref, rotulos_divergentes):
    modelo = gerar_modelo_consenso(rotulos_divergentes, ref)

    assert len(modelo) == 6
    repo = modelo.drop_duplicates("repo_idx").set_index("repo_idx")
    assert repo.loc["1", "tipo_projeto"] == "biblioteca/framework"
    assert repo.loc["1", "tipo_projeto_origem"] == "unanimidade"
    assert repo.loc["2", "tipo_projeto"] == "aplicação/serviço"
    assert repo.loc["2", "tipo_projeto_origem"] == "maioria"
    assert repo.loc["3", "tipo_projeto"] == ""
    assert repo.loc["3", "tipo_projeto_origem"] == "pendente"
    # entrega_real do repo 3: sim/incerto/não -> pendente; repo 2: sim/não/não -> não
    assert repo.loc["3", "entrega_real_origem"] == "pendente"
    assert repo.loc["2", "entrega_real"] == "não"
    # release_corretiva da última linha (3/2): marcela sim, demais não -> maioria "não"
    ultima = modelo.iloc[-1]
    assert (ultima["release_corretiva"], ultima["release_corretiva_origem"]) == ("não", "maioria")
    # o valor de repositório se repete nas releases do mesmo repo
    assert (modelo.groupby("repo_idx")["tipo_projeto"].nunique() == 1).all()


def test_consenso_com_pendencia_e_invalido_e_depois_de_resolvido_e_valido(ref, rotulos_divergentes):
    modelo = gerar_modelo_consenso(rotulos_divergentes, ref)
    erros = validar_consenso(modelo, ref)
    assert any("tipo_projeto em branco" in e for e in erros)
    assert any("tipo_projeto ainda pendente" in e for e in erros)

    # decisão da reunião para o repo 3
    mask = modelo["repo_idx"] == "3"
    modelo.loc[mask, ["tipo_projeto", "tipo_projeto_origem"]] = ["ferramenta CLI", "reuniao"]
    modelo.loc[mask, ["entrega_real", "entrega_real_origem"]] = ["incerto", "reuniao"]
    assert validar_consenso(modelo, ref) == []


def test_consenso_sem_colunas_de_origem_e_invalido(ref):
    erros = validar_consenso(preencher(ref), ref)
    assert any("tipo_projeto_origem" in e for e in erros)


def test_consenso_origem_desconhecida_e_invalida(ref, rotulos_divergentes):
    modelo = gerar_modelo_consenso(rotulos_divergentes, ref)
    modelo.loc[modelo["repo_idx"] == "3", ["tipo_projeto", "tipo_projeto_origem"]] = ["outro", "chute"]
    assert any("tipo_projeto_origem fora de" in e for e in validar_consenso(modelo, ref))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
@pytest.fixture
def ambiente(tmp_path, ref, rotulos_divergentes) -> dict[str, Path]:
    validacao = tmp_path / "validacao"
    validacao.mkdir()
    for avaliador, df in rotulos_divergentes.items():
        gravar(df, validacao / f"rotulos_{avaliador}.csv")
    planilha = gravar(ref, tmp_path / "planilha.csv")
    return {"validacao": validacao, "planilha": planilha, "tmp": tmp_path}


def _base(env) -> list[str]:
    return ["--validacao-dir", str(env["validacao"]), "--planilha", str(env["planilha"])]


def test_cli_validar_kappa_e_json(ambiente, capsys):
    assert main(["validar", *_base(ambiente)]) == 0
    assert capsys.readouterr().out.count("[ok]") == 3

    destino = ambiente["tmp"] / "kappa.json"
    assert main(["kappa", *_base(ambiente), "--json", str(destino)]) == 0
    saida = capsys.readouterr().out
    assert "tipo_projeto" in saida and "release_corretiva" in saida
    dados = json.loads(destino.read_text(encoding="utf-8"))
    assert [d["dimensao"] for d in dados] == ["tipo_projeto", "entrega_real", "release_corretiva"]


def test_cli_kappa_sem_variabilidade_mostra_nd(tmp_path, ref, capsys):
    validacao = tmp_path / "v"
    validacao.mkdir()
    for a in ("marcela", "gabriel", "joao"):
        gravar(preencher(ref), validacao / f"rotulos_{a}.csv")
    planilha = gravar(ref, tmp_path / "p.csv")
    assert main(["kappa", "--validacao-dir", str(validacao), "--planilha", str(planilha)]) == 0
    assert "n/d" in capsys.readouterr().out


def test_cli_avaliadores_ausentes_retorna_2_sem_criar_arquivos(tmp_path, ref, capsys):
    validacao = tmp_path / "validacao"
    validacao.mkdir()
    gravar(preencher(ref), validacao / "rotulos_marcela.csv")
    planilha = gravar(ref, tmp_path / "p.csv")
    base = ["--validacao-dir", str(validacao), "--planilha", str(planilha)]

    assert main(["kappa", *base]) == 2
    err = capsys.readouterr().err
    assert "rotulos_gabriel.csv" in err and "rotulos_joao.csv" in err
    assert main(["validar", *base, "--avaliadores", "marcela"]) == 0
    assert sorted(p.name for p in validacao.iterdir()) == ["rotulos_marcela.csv"]


def test_cli_arquivo_invalido_retorna_1(ambiente, capsys):
    caminho = ambiente["validacao"] / "rotulos_joao.csv"
    df = carregar_csv(caminho)
    df.loc[0, "entrega_real"] = "talvez"
    gravar(df, caminho)
    assert main(["kappa", *_base(ambiente)]) == 1
    assert "rotulos_joao.csv" in capsys.readouterr().err


def test_cli_planilha_inexistente_retorna_1(ambiente, capsys):
    argv = ["kappa", "--validacao-dir", str(ambiente["validacao"]), "--planilha", "nao_existe.csv"]
    assert main(argv) == 1
    assert "não encontrada" in capsys.readouterr().err


def test_cli_divergencias_saida_opcional(ambiente, capsys):
    assert main(["divergencias", *_base(ambiente)]) == 0
    assert "tipo_projeto: 2 divergência(s)" in capsys.readouterr().out
    assert list(ambiente["tmp"].glob("div*.csv")) == []

    destino = ambiente["tmp"] / "div.csv"
    assert main(["divergencias", *_base(ambiente), "--saida", str(destino)]) == 0
    assert len(pd.read_csv(destino)) == 5
    assert main(["divergencias", *_base(ambiente), "--saida", str(destino)]) == 1  # não sobrescreve
    assert main(["divergencias", *_base(ambiente), "--saida", str(destino), "--forcar"]) == 0


def test_cli_consenso_exige_saida_explicita(ambiente):
    with pytest.raises(SystemExit):
        main(["consenso", *_base(ambiente)])
    assert not (ambiente["validacao"] / "consenso.csv").exists()


def test_cli_consenso_gera_modelo_e_nao_sobrescreve(ambiente, capsys):
    destino = ambiente["tmp"] / "saida" / "consenso.csv"
    assert main(["consenso", *_base(ambiente), "--saida", str(destino)]) == 0
    out = capsys.readouterr().out
    assert "tipo_projeto: 2 linha(s) pendente(s)" in out
    modelo = carregar_csv(destino)
    assert "tipo_projeto_origem" in modelo.columns and len(modelo) == 6

    destino.write_text("decisoes da reuniao", encoding="utf-8")
    assert main(["consenso", *_base(ambiente), "--saida", str(destino)]) == 1
    assert destino.read_text(encoding="utf-8") == "decisoes da reuniao"
    assert "--forcar" in capsys.readouterr().err


def test_cli_verificar_consenso(ambiente, capsys):
    destino = ambiente["tmp"] / "consenso.csv"
    main(["consenso", *_base(ambiente), "--saida", str(destino)])
    capsys.readouterr()

    assert main(["verificar-consenso", *_base(ambiente), "--consenso", str(destino)]) == 1
    assert "pendente" in capsys.readouterr().err

    modelo = carregar_csv(destino)
    mask = modelo["repo_idx"] == "3"
    modelo.loc[mask, ["tipo_projeto", "tipo_projeto_origem"]] = ["outro", "reuniao"]
    modelo.loc[mask, ["entrega_real", "entrega_real_origem"]] = ["incerto", "reuniao"]
    gravar(modelo, destino)
    assert main(["verificar-consenso", *_base(ambiente), "--consenso", str(destino)]) == 0

    assert main(["verificar-consenso", *_base(ambiente), "--consenso", str(ambiente["tmp"] / "nada.csv")]) == 1


# --------------------------------------------------------------------------- #
# Proveniência (avaliadores IA) e consenso automático — fixtures sintéticas
# --------------------------------------------------------------------------- #
def make_origem(
    df: pd.DataFrame, origem: str = "ia", modelo: str = "modelo-x", esforco: str = "high"
) -> pd.DataFrame:
    """Arquivo auxiliar `rotulos_<id>_origem.csv` sintético para um DataFrame de rótulos."""
    return pd.DataFrame(
        {
            "repo_idx": df["repo_idx"],
            "release_idx": df["release_idx"],
            "origem": origem,
            "modelo": modelo,
            "esforco": esforco,
            "data_utc": "2026-01-01T00:00:00Z",
        }
    )


@pytest.fixture
def origens_ia(rotulos_divergentes) -> dict[str, pd.DataFrame]:
    return {a: make_origem(df) for a, df in rotulos_divergentes.items()}


@pytest.fixture
def ambiente_ia(ambiente, origens_ia) -> dict[str, Path]:
    for avaliador, df in origens_ia.items():
        gravar(df, ambiente["validacao"] / f"rotulos_{avaliador}_origem.csv")
    return ambiente


def test_resumo_de_proveniencia_por_avaliador_origem_modelo_esforco(rotulos_divergentes):
    marcela = rotulos_divergentes["marcela"]
    origem = make_origem(marcela)
    origem.loc[origem["repo_idx"] == "1", ["origem", "modelo", "esforco"]] = ["humano", "", ""]

    resumo = resumir_proveniencia({"marcela": origem, "joao": make_origem(marcela, modelo="m2", esforco="low")})
    linhas = {(r.avaliador, r.origem, r.modelo, r.esforco): r.n_linhas for r in resumo.itertuples()}
    assert linhas == {
        ("marcela", "humano", "", ""): 2,
        ("marcela", "ia", "modelo-x", "high"): 4,
        ("joao", "ia", "m2", "low"): 6,
    }


def test_formatar_proveniencia_avisa_quando_ha_ia(rotulos_divergentes):
    ia = {"joao": make_origem(rotulos_divergentes["joao"])}
    texto = formatar_proveniencia(ia)
    assert "joao: ia/modelo-x/high: 6" in texto
    assert AVISO_ROTULOS_IA in texto
    assert "não entre pessoas" in texto

    humano = {"joao": make_origem(rotulos_divergentes["joao"], "humano", "", "")}
    assert AVISO_ROTULOS_IA not in formatar_proveniencia(humano)
    assert "joao: humano/-/-: 6" in formatar_proveniencia(humano)


def _carregar_origem(tmp_path: Path, origem: pd.DataFrame, rotulos: pd.DataFrame) -> pd.DataFrame:
    return carregar_origem_validada(gravar(origem, tmp_path / "o.csv"), rotulos)


def test_origem_aceita_arquivo_correto(tmp_path, rotulos_divergentes):
    rotulos = rotulos_divergentes["joao"]
    assert len(_carregar_origem(tmp_path, make_origem(rotulos), rotulos)) == 6


@pytest.mark.parametrize(
    "mutacao,trecho",
    [
        (lambda o: o.drop(columns=["modelo"]), "colunas ausentes: modelo"),
        (lambda o: o.iloc[:-1], "sem origem (chaves ausentes): 3/2"),
        (lambda o: pd.concat([o, o.iloc[[0]]], ignore_index=True), "duplicadas: 1/1"),
        (
            lambda o: pd.concat([o, o.iloc[[0]].assign(repo_idx="9")], ignore_index=True),
            "chaves inexistentes nos rótulos: 9/1",
        ),
        (lambda o: o.assign(origem=o["origem"].where(o.index != 0, "robo")), "origem fora de ['ia', 'humano']"),
        (lambda o: o.assign(modelo=o["modelo"].where(o.index != 1, "")), "origem=ia sem modelo (linhas): 3"),
        (lambda o: o.assign(origem=o["origem"].where(o.index != 0, "humano")), "diverge entre as releases"),
    ],
)
def test_origem_invalida(tmp_path, rotulos_divergentes, mutacao, trecho):
    rotulos = rotulos_divergentes["joao"]
    origem = mutacao(make_origem(rotulos))
    with pytest.raises(RotulosInvalidosError) as exc:
        _carregar_origem(tmp_path, origem, rotulos)
    assert trecho in str(exc.value)


def test_origem_humano_nao_exige_modelo(tmp_path, rotulos_divergentes):
    rotulos = rotulos_divergentes["joao"]
    assert len(_carregar_origem(tmp_path, make_origem(rotulos, "humano", "", ""), rotulos)) == 6


def test_origem_cobre_so_as_linhas_validas_do_avaliador(tmp_path, ref, rotulos_divergentes):
    # avaliador com lista de linhas inválidas: o arquivo de origem cobre só o que sobrou
    invalidas = ref[ref["repo_idx"] == "3"][["repo_idx", "release_idx"]]
    gravar(rotulos_divergentes["marcela"], tmp_path / "rotulos_marcela.csv")
    gravar(invalidas, tmp_path / f"marcela{SUFIXO_LINHAS_INVALIDAS}")
    rotulos = carregar_avaliadores(tmp_path, ref, ["marcela"])
    assert len(rotulos["marcela"]) == 4
    gravar(make_origem(rotulos["marcela"]), tmp_path / "rotulos_marcela_origem.csv")
    assert len(carregar_origens(tmp_path, rotulos)["marcela"]) == 4


def test_carregar_origens_arquivo_ausente(tmp_path, rotulos_divergentes):
    with pytest.raises(ConcordanciaError, match="rotulos_joao_origem.csv"):
        carregar_origens(tmp_path, {"joao": rotulos_divergentes["joao"]})


def test_cli_sem_origens_nao_muda_a_saida(ambiente, capsys):
    assert main(["kappa", *_base(ambiente)]) == 0
    saida = capsys.readouterr().out
    assert "proveniência" not in saida and "AVISO" not in saida


@pytest.mark.parametrize("comando", ["validar", "kappa", "divergencias"])
def test_cli_origens_reporta_resumo_e_aviso_em_cada_saida(ambiente_ia, capsys, comando):
    assert main([comando, *_base(ambiente_ia), "--origens"]) == 0
    saida = capsys.readouterr().out
    assert "proveniência dos rótulos" in saida
    assert "gabriel: ia/modelo-x/high: 6" in saida
    assert AVISO_ROTULOS_IA in saida


def test_cli_consenso_modelo_com_origens_reporta_proveniencia(ambiente_ia, capsys):
    destino = ambiente_ia["tmp"] / "consenso_modelo.csv"
    assert main(["consenso", *_base(ambiente_ia), "--origens", "--saida", str(destino)]) == 0
    assert AVISO_ROTULOS_IA in capsys.readouterr().out
    assert "consenso_modo" not in carregar_csv(destino).columns  # modelo da reunião, sem alteração


def test_cli_kappa_json_com_origens_inclui_proveniencia(ambiente_ia):
    destino = ambiente_ia["tmp"] / "kappa.json"
    assert main(["kappa", *_base(ambiente_ia), "--origens", "--json", str(destino)]) == 0
    dados = json.loads(destino.read_text(encoding="utf-8"))
    assert [d["dimensao"] for d in dados["resultados"]] == ["tipo_projeto", "entrega_real", "release_corretiva"]
    assert dados["proveniencia"]["aviso"] == AVISO_ROTULOS_IA
    assert {r["avaliador"] for r in dados["proveniencia"]["resumo"]} == {"marcela", "gabriel", "joao"}


def test_cli_validar_origens_humanos_nao_emite_aviso(ambiente, rotulos_divergentes, capsys):
    for avaliador, df in rotulos_divergentes.items():
        gravar(make_origem(df, "humano", "", ""), ambiente["validacao"] / f"rotulos_{avaliador}_origem.csv")
    assert main(["validar", *_base(ambiente), "--origens"]) == 0
    saida = capsys.readouterr().out
    assert "humano/-/-: 6" in saida and AVISO_ROTULOS_IA not in saida


def test_cli_origens_ausente_ou_invalida_retorna_1(ambiente_ia, capsys):
    caminho = ambiente_ia["validacao"] / "rotulos_joao_origem.csv"
    origem = carregar_csv(caminho)
    gravar(origem.iloc[:-1], caminho)
    assert main(["kappa", *_base(ambiente_ia), "--origens"]) == 1
    assert "rotulos_joao_origem.csv" in capsys.readouterr().err

    caminho.unlink()
    assert main(["kappa", *_base(ambiente_ia), "--origens"]) == 1
    assert "origem ausentes" in capsys.readouterr().err


# ---- consenso automático ---------------------------------------------------- #
def test_consenso_automatico_maioria_e_desempate(ref, rotulos_divergentes, origens_ia):
    consenso = gerar_consenso_automatico(rotulos_divergentes, origens_ia, ref)

    assert len(consenso) == 6
    assert (consenso["consenso_modo"] == "automatico_maioria").all()
    repo = consenso.drop_duplicates("repo_idx").set_index("repo_idx")
    # repo 1: unânime; repo 2: 2-1; repo 3: 1-1-1 -> outro / incerto
    assert (repo.loc["1", "tipo_projeto"], repo.loc["1", "tipo_projeto_origem"]) == ("biblioteca/framework", "unanimidade")
    assert (repo.loc["2", "tipo_projeto"], repo.loc["2", "tipo_projeto_origem"]) == ("aplicação/serviço", "maioria")
    assert (repo.loc["3", "tipo_projeto"], repo.loc["3", "tipo_projeto_origem"]) == ("outro", "desempate_automatico")
    assert (repo.loc["3", "entrega_real"], repo.loc["3", "entrega_real_origem"]) == ("incerto", "desempate_automatico")
    assert "desempate automático" in repo.loc["3", "notas_consenso"]
    assert repo.loc["1", "notas_consenso"] == ""
    # release_corretiva é binária: nunca pendente nem desempate; por release
    assert set(consenso["release_corretiva_origem"]) <= {"unanimidade", "maioria"}
    assert consenso.iloc[-1]["release_corretiva"] == "não"
    assert not consenso.filter(like="_origem").isin(["pendente"]).any().any()


def test_consenso_automatico_conta_votos_ia_e_humano(ref, rotulos_divergentes):
    origens = {
        "marcela": make_origem(rotulos_divergentes["marcela"], "humano", "", ""),
        "gabriel": make_origem(rotulos_divergentes["gabriel"]),
        "joao": make_origem(rotulos_divergentes["joao"]),
    }
    consenso = gerar_consenso_automatico(rotulos_divergentes, origens, ref)

    assert (consenso["tipo_projeto_votos_ia"] == 2).all()
    assert (consenso["tipo_projeto_votos_humano"] == 1).all()
    assert (consenso["entrega_real_votos_ia"] + consenso["entrega_real_votos_humano"] == 3).all()
    assert (consenso["release_corretiva_votos_ia"] == 2).all()
    assert (consenso["release_corretiva_votos_humano"] == 1).all()


def test_consenso_automatico_votos_por_unidade_com_origem_mista_por_repo(ref, rotulos_divergentes, origens_ia):
    # Marcela humana só no repo 1: nesse repo 1 voto humano; nos demais, 0
    origens_ia["marcela"].loc[origens_ia["marcela"]["repo_idx"] == "1", ["origem", "modelo", "esforco"]] = ["humano", "", ""]
    consenso = gerar_consenso_automatico(rotulos_divergentes, origens_ia, ref)
    por_repo = consenso.groupby("repo_idx")["tipo_projeto_votos_humano"].first().to_dict()
    assert por_repo == {"1": 1, "2": 0, "3": 0}


def test_consenso_automatico_passa_em_verificar_consenso(ref, rotulos_divergentes, origens_ia):
    consenso = gerar_consenso_automatico(rotulos_divergentes, origens_ia, ref)
    assert validar_consenso(consenso, ref) == []


def test_desempate_automatico_so_vale_com_consenso_modo(ref, rotulos_divergentes, origens_ia):
    consenso = gerar_consenso_automatico(rotulos_divergentes, origens_ia, ref)
    sem_modo = consenso.drop(columns=["consenso_modo"])
    assert any("tipo_projeto_origem fora de" in e for e in validar_consenso(sem_modo, ref))
    consenso["consenso_modo"] = "reuniao"
    assert any("consenso_modo fora de" in e for e in validar_consenso(consenso, ref))


def test_cli_consenso_automatico_exige_flag_e_origens(ambiente_ia):
    destino = ambiente_ia["tmp"] / "consenso_auto.csv"
    # sem --modo-automatico o comando continua gerando só o modelo (com pendências), nunca o automático
    assert main(["consenso", *_base(ambiente_ia), "--origens", "--saida", str(destino)]) == 0
    modelo = carregar_csv(destino)
    assert "consenso_modo" not in modelo.columns and (modelo["tipo_projeto_origem"] == "pendente").any()

    # --modo-automatico sem --origens é recusado e não grava nada
    destino2 = ambiente_ia["tmp"] / "consenso_auto2.csv"
    assert main(["consenso", *_base(ambiente_ia), "--modo-automatico", "--saida", str(destino2)]) == 1
    assert not destino2.exists()


def test_cli_consenso_automatico_gera_e_avisa(ambiente_ia, capsys):
    destino = ambiente_ia["tmp"] / "consenso_auto.csv"
    argv = ["consenso", *_base(ambiente_ia), "--modo-automatico", "--origens", "--saida", str(destino)]
    assert main(argv) == 0
    saida = capsys.readouterr().out
    assert "tipo_projeto: unanimidade=2, maioria=2, desempate_automatico=2 (linhas)" in saida and "automatico_maioria" in saida
    assert AVISO_ROTULOS_IA in saida

    consenso = carregar_csv(destino)
    assert set(consenso["consenso_modo"]) == {"automatico_maioria"}
    assert {"tipo_projeto_votos_ia", "tipo_projeto_votos_humano"} <= set(consenso.columns)

    assert main(argv) == 1  # não sobrescreve sem --forcar
    assert main([*argv, "--forcar"]) == 0

    assert main(["verificar-consenso", *_base(ambiente_ia), "--consenso", str(destino)]) == 0
    assert "sem reunião" in capsys.readouterr().out


def test_slot_gabriel_com_claude_code_e_independencia_parcial(rotulos_divergentes, tmp_path, ambiente, capsys):
    # cenário real previsto: rótulos de IA feitos via Claude Code, esforço desconhecido,
    # independência apenas parcial (o mesmo assistente implementou a heurística v1)
    nota = "parcial: o mesmo assistente implementou a heurística v1"
    origem = make_origem(rotulos_divergentes["gabriel"], modelo="claude-opus-5.5 (Claude Code)", esforco="desconhecido")
    origem["independencia"] = nota
    validada = _carregar_origem(tmp_path, origem, rotulos_divergentes["gabriel"])
    assert validada["independencia"].eq(nota).all()

    texto = formatar_proveniencia({"gabriel": validada})
    assert "ia/claude-opus-5.5 (Claude Code)/desconhecido: 6" in texto
    assert f"independência (gabriel): {nota}" in texto
    assert AVISO_ROTULOS_IA in texto

    # pela CLI: a ressalva acompanha o resumo, e o JSON a registra
    for avaliador, df in rotulos_divergentes.items():
        o = origem if avaliador == "gabriel" else make_origem(df)
        gravar(o, ambiente["validacao"] / f"rotulos_{avaliador}_origem.csv")
    destino = tmp_path / "k.json"
    assert main(["kappa", *_base(ambiente), "--origens", "--json", str(destino)]) == 0
    assert nota in capsys.readouterr().out
    dados = json.loads(destino.read_text(encoding="utf-8"))
    assert dados["proveniencia"]["independencia"] == {"gabriel": [nota]}


def test_sidecar_sem_coluna_independencia_continua_valido(tmp_path, rotulos_divergentes):
    rotulos = rotulos_divergentes["joao"]
    validada = _carregar_origem(tmp_path, make_origem(rotulos), rotulos)
    assert "independencia" not in validada.columns
    assert "independência (" not in formatar_proveniencia({"joao": validada})
