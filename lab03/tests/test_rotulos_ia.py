"""Guardas dos rótulos de avaliadores IA versionados em `validacao/` (Issues #57, #61, #64, #65).

Garantem: 300 linhas por slot, chaves iguais às da planilha, arquivos de origem coerentes,
as 150 linhas humanas de Marcela inalteradas (hash fixo) e o arquivo de Gabriel intocado.
Não calculam kappa de Fleiss, consenso nem resultados da heurística.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from analises.auditoria_rotulos_ia import (
    comparar_rotulos,
    confiabilidade_gabriel,
    formatar,
    hash_linhas,
    ia_vs_humano,
    ler_linhas_brutas,
    main,
    verificar_linhas_humanas,
)
from analises.concordancia import (
    COLUNAS_ORIGEM,
    carregar_avaliadores,
    carregar_csv,
    carregar_origens,
    main as main_concordancia,
)

LAB03 = Path(__file__).resolve().parent.parent
VALIDACAO = LAB03 / "validacao"
PLANILHA = LAB03 / "dados" / "amostra_ouro" / "amostra_ouro_template.csv"
INVALIDAS = VALIDACAO / "historico" / "marcela_linhas_invalidas.csv"
EXTRA = VALIDACAO / "extra" / "rotulos_gabriel_execucao2_ia.csv"
SLOTS = ["joao", "gabriel", "marcela"]

# SHA-256 das 150 linhas humanas de rotulos_marcela.csv (ordem do arquivo, CRLF), tal como
# commitadas por Marcela (8b20a10). Mudar uma delas muda o hash e quebra este teste.
HASH_LINHAS_HUMANAS_MARCELA = "7c59bb376dca7e4d07b396198dcc4be6f724863e1b2401b95a52287f570ee57b"

pytestmark = pytest.mark.skipif(
    not (PLANILHA.is_file() and INVALIDAS.is_file()), reason="arquivos reais da amostra-ouro ausentes"
)


@pytest.fixture(scope="module")
def referencia() -> pd.DataFrame:
    return carregar_csv(PLANILHA)


def _chaves(df: pd.DataFrame) -> set[tuple[str, str]]:
    return set(zip(df["repo_idx"], df["release_idx"]))


@pytest.mark.parametrize("slot", SLOTS)
def test_slot_tem_300_linhas_com_as_chaves_da_planilha(slot, referencia):
    rotulos = carregar_csv(VALIDACAO / f"rotulos_{slot}.csv")
    assert len(rotulos) == 300
    assert _chaves(rotulos) == _chaves(referencia)
    assert list(zip(rotulos["repo_idx"], rotulos["release_idx"], rotulos["tag_name"])) == list(
        zip(referencia["repo_idx"], referencia["release_idx"], referencia["tag_name"])
    )


@pytest.mark.parametrize("slot", SLOTS)
def test_origem_tem_300_linhas_e_chaves_iguais_as_dos_rotulos(slot):
    rotulos = carregar_csv(VALIDACAO / f"rotulos_{slot}.csv")
    origem = carregar_csv(VALIDACAO / f"rotulos_{slot}_origem.csv")
    assert list(origem.columns)[: len(COLUNAS_ORIGEM)] == COLUNAS_ORIGEM
    assert len(origem) == 300
    assert _chaves(origem) == _chaves(rotulos)


def test_origens_declaradas_por_slot():
    ori = {s: carregar_csv(VALIDACAO / f"rotulos_{s}_origem.csv") for s in SLOTS}
    assert set(ori["joao"]["origem"]) == {"ia"}
    assert set(ori["joao"]["modelo"]) == {"claude-opus-5.5"}
    assert set(ori["joao"]["esforco"]) == {"high"}
    # Gabriel: derivado da linha dele em PROVENIENCIA.md (esforço não declarado)
    assert set(ori["gabriel"]["origem"]) == {"ia"}
    assert set(ori["gabriel"]["modelo"]) == {"claude-opus-5.5 (Claude Code)"}
    assert set(ori["gabriel"]["esforco"]) == {"desconhecido"}
    assert set(ori["gabriel"]["data_utc"]) == {"2026-10-21"}
    assert ori["gabriel"]["independencia"].str.startswith("parcial").all()
    assert ori["marcela"]["origem"].value_counts().to_dict() == {"humano": 150, "ia": 150}


def test_linhas_de_ia_de_marcela_sao_exatamente_as_da_lista_historica():
    lista = carregar_csv(INVALIDAS)
    assert len(lista) == 150
    origem = carregar_csv(VALIDACAO / "rotulos_marcela_origem.csv")
    assert _chaves(origem[origem["origem"] == "ia"]) == _chaves(lista)
    assert _chaves(origem[origem["origem"] == "humano"]).isdisjoint(_chaves(lista))


def test_linhas_humanas_de_marcela_nao_mudaram():
    linhas = ler_linhas_brutas(VALIDACAO / "rotulos_marcela.csv")
    lista = carregar_csv(INVALIDAS)
    invalidas = _chaves(lista)
    origem = carregar_csv(VALIDACAO / "rotulos_marcela_origem.csv")
    humanas_ordem = [
        i for i, (r, rel) in enumerate(zip(origem["repo_idx"], origem["release_idx"])) if (r, rel) not in invalidas
    ]
    assert len(humanas_ordem) == 150
    assert hash_linhas([linhas[1:][i] for i in humanas_ordem]) == HASH_LINHAS_HUMANAS_MARCELA
    # nenhuma linha humana tem a tag-placeholder do sorteio incompleto
    marcela = carregar_csv(VALIDACAO / "rotulos_marcela.csv")
    assert (marcela["tag_name"] != "(pendente de persistência)").all()


def test_rotulos_de_gabriel_nao_foram_tocados():
    """O slot `gabriel` é o arquivo de Gabriel (Claude Code); a execução 2 é um extra à parte."""
    gabriel = (VALIDACAO / "rotulos_gabriel.csv").read_bytes()
    extra = EXTRA.read_bytes()
    assert gabriel != extra
    assert len(carregar_csv(EXTRA)) == 300
    assert not (VALIDACAO / "rotulos_gabriel_execucao2_ia.csv").exists()  # fora dos slots


def test_ferramenta_valida_os_tres_slots_com_origens(capsys):
    assert main_concordancia(["validar", "--planilha", str(PLANILHA), "--validacao-dir", str(VALIDACAO), "--origens"]) == 0
    saida = capsys.readouterr().out
    assert "marcela: humano/-/-: 150; ia/claude-opus-5.5/high: 150" in saida
    assert "rótulos de IA" in saida


def test_carregar_avaliadores_e_origens_cobrem_300_linhas(referencia):
    rotulos = carregar_avaliadores(VALIDACAO, referencia)
    assert {a: len(df) for a, df in rotulos.items()} == {"marcela": 300, "gabriel": 300, "joao": 300}
    assert all(len(o) == 300 for o in carregar_origens(VALIDACAO, rotulos).values())


def test_lista_historica_nao_fica_ao_lado_dos_rotulos():
    """Ao lado de rotulos_marcela.csv ela faria a ferramenta ignorar as 150 linhas de IA."""
    assert not (VALIDACAO / "marcela_linhas_invalidas.csv").exists()


def test_verificar_linhas_humanas_com_o_proprio_arquivo_detecta_ia_igual_ao_anterior():
    """Contra si mesmo as linhas humanas são idênticas (e as de IA também, o que é aceito)."""
    r = verificar_linhas_humanas(VALIDACAO / "rotulos_marcela.csv", VALIDACAO / "rotulos_marcela.csv", INVALIDAS)
    assert r.ok and r.n_humanas == 150 and r.n_ia == 150
    assert r.hash_humanas == HASH_LINHAS_HUMANAS_MARCELA


def test_verificar_linhas_humanas_detecta_edicao(tmp_path):
    linhas = ler_linhas_brutas(VALIDACAO / "rotulos_marcela.csv")
    lista = carregar_csv(INVALIDAS)
    invalidas = _chaves(lista)
    alvo = next(
        i for i, l in enumerate(linhas[1:], start=1) if tuple(l.decode("utf-8-sig").split(",")[i0] for i0 in (0, 5)) not in invalidas
    )
    editado = list(linhas)
    editado[alvo] = editado[alvo] + b" "
    copia = tmp_path / "rotulos_marcela.csv"
    copia.write_bytes(b"\r\n".join(editado) + b"\r\n")
    r = verificar_linhas_humanas(VALIDACAO / "rotulos_marcela.csv", copia, INVALIDAS)
    assert not r.humanas_identicas and not r.ok
    assert r.hash_humanas != HASH_LINHAS_HUMANAS_MARCELA


def test_ler_linhas_brutas_exige_crlf(tmp_path):
    arq = tmp_path / "x.csv"
    arq.write_bytes(b"a,b\n1,2\n")
    with pytest.raises(ValueError, match="CRLF"):
        ler_linhas_brutas(arq)


def test_comparar_rotulos_a_mao():
    def df(tipo, corretiva):
        return pd.DataFrame(
            {
                "repo_idx": ["1", "1", "2", "2"],
                "release_idx": ["1", "2", "1", "2"],
                "tipo_projeto": tipo,
                "entrega_real": ["sim"] * 4,
                "release_corretiva": corretiva,
            }
        )

    a = df(["outro", "outro", "ferramenta CLI", "ferramenta CLI"], ["sim", "sim", "não", "não"])
    b = df(["outro", "outro", "ferramenta CLI", "ferramenta CLI"], ["sim", "não", "não", "sim"])
    res = {r.dimensao: r for r in comparar_rotulos(a, b)}
    assert res["tipo_projeto"].n == 2 and res["tipo_projeto"].concordancia_pct == pytest.approx(100.0)
    assert res["tipo_projeto"].kappa_cohen == pytest.approx(1.0)
    assert res["entrega_real"].kappa_cohen is None  # sem variabilidade: indefinido
    assert res["release_corretiva"].n == 4
    assert res["release_corretiva"].concordancia_pct == pytest.approx(50.0)
    assert res["release_corretiva"].kappa_cohen == pytest.approx(0.0)
    assert "n/d" in formatar("t", list(res.values()))


def test_numeros_da_documentacao_de_confiabilidade():
    """Os números de docs/confiabilidade_execucoes_ia.md vêm destas funções."""
    conf = {r.dimensao: r for r in confiabilidade_gabriel(VALIDACAO)}
    assert conf["tipo_projeto"].n == 60 and conf["release_corretiva"].n == 300
    assert round(conf["tipo_projeto"].concordancia_pct, 1) == 88.3
    assert round(conf["release_corretiva"].concordancia_pct, 1) == 92.7
    assert round(conf["release_corretiva"].kappa_cohen, 3) == 0.852
    joao = {r.dimensao: r for r in ia_vs_humano(VALIDACAO, INVALIDAS, "joao")}
    assert joao["release_corretiva"].n == 150
    assert round(joao["release_corretiva"].concordancia_pct, 1) == 58.0
    assert round(joao["tipo_projeto"].concordancia_pct, 1) == 70.0


def test_cli_confiabilidade_ia_vs_humano_e_humanas(capsys):
    base = ["--validacao-dir", str(VALIDACAO), "--invalidas", str(INVALIDAS)]
    assert main([*base, "confiabilidade"]) == 0
    assert "kappa de Cohen" in capsys.readouterr().out
    assert main([*base, "ia-vs-humano"]) == 0
    assert "Marcela humana" in capsys.readouterr().out
    anterior = VALIDACAO / "rotulos_marcela.csv"
    assert main([*base, "humanas", "--anterior", str(anterior)]) == 0
    assert HASH_LINHAS_HUMANAS_MARCELA in capsys.readouterr().out
