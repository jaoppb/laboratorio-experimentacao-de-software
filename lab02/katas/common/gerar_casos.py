"""Gera 20 casos de teste por kata, nomeados test01..test20.

Composicao: exemplos oficiais do caderno (preservados, sempre primeiro) +
casos de borda escritos a mao + casos aleatorios + um caso de desempenho (nos
katas 01-03). As saidas esperadas saem dos gabaritos, que foram validados
contra implementacoes independentes de forca bruta (ver stress_test.py).

Cada kata ganha um tests/MANIFEST.md descrevendo o que cada testNN cobre, ja
que o nome do arquivo sozinho nao carrega mais essa informacao.
"""

import random
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TARGET = 20


def gabarito(kata, stdin_text):
    p = subprocess.run(
        [sys.executable, str(BASE / "gabaritos" / f"{kata}.py")],
        input=stdin_text,
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        raise RuntimeError(f"{kata}: {p.stderr}")
    return p.stdout


def existing_samples(kata):
    """Le os exemplos oficiais ja presentes em tests/ (test01..testNN de uma
    rodada anterior, ou sampleNN de antes da padronizacao) antes de limpar o
    diretorio. Identificados pela ausencia de MANIFEST e por serem os
    primeiros N casos do manifest anterior, se existir; na primeira geracao,
    ficam marcados manualmente por kata em OFFICIAL_COUNT."""
    tdir = BASE / kata / "tests"
    manifest = tdir / "MANIFEST.md"
    count = OFFICIAL_COUNT[kata]
    if manifest.exists():
        names = [f"test{i:02d}" for i in range(1, count + 1)]
    else:
        candidates = sorted(tdir.glob("sample*.in")) or sorted(tdir.glob("test*.in"))[:count]
        names = [f.stem for f in candidates[:count]]
    pairs = []
    for name in names:
        inp = (tdir / f"{name}.in").read_text()
        out = (tdir / f"{name}.out").read_text()
        pairs.append((inp, out))
    assert len(pairs) == count, f"{kata}: esperava {count} exemplos oficiais, achei {len(pairs)}"
    return pairs


def write_manifest(kata, manifest):
    tdir = BASE / kata / "tests"
    lines = [f"# Casos de teste — {kata}", "", "| Arquivo | Descrição |", "|---|---|"]
    for name, desc in manifest:
        lines.append(f"| `{name}` | {desc} |")
    (tdir / "MANIFEST.md").write_text("\n".join(lines) + "\n")


def finalize(kata, sample_pairs, extra):
    """extra: lista de (descricao, texto_entrada). sample_pairs: lista de
    (entrada, saida) dos exemplos oficiais, preservados como vieram."""
    tdir = BASE / kata / "tests"
    for f in tdir.iterdir():
        f.unlink()

    manifest = []
    n = 0
    for i, (inp, out) in enumerate(sample_pairs, start=1):
        n += 1
        name = f"test{n:02d}"
        (tdir / f"{name}.in").write_text(inp)
        (tdir / f"{name}.out").write_text(out)
        manifest.append((name, f"Exemplo oficial {i} do caderno da maratona"))

    for desc, inp in extra:
        n += 1
        name = f"test{n:02d}"
        (tdir / f"{name}.in").write_text(inp)
        (tdir / f"{name}.out").write_text(gabarito(kata, inp))
        manifest.append((name, desc))

    assert n == TARGET, f"{kata} tem {n} casos, esperado {TARGET}"
    write_manifest(kata, manifest)
    print(f"{kata}: {n} casos")


OFFICIAL_COUNT = {
    "01-bario-world": 1,
    "02-cards": 2,
    "03-exploring-terrain": 3,
    "04-garment-groups": 2,
    "05-dish-rack": 3,
    "06-n-checkers": 3,
}


# ============================================================ 01 Bario World
def bario_case(levels):
    return f"{len(levels)}\n" + "".join(f"{len(s)}\n{s}\n" for s in levels)


def gen_bario():
    kata = "01-bario-world"
    samples = existing_samples(kata)
    extra = []

    extra.append(("Tres niveis num arquivo: minimo, buracos espalhados e buraco central",
                  bario_case(["xx", "xx.xx.xxx", "x....x"])))
    extra.append(("Minimo: N=2, so correr, sem pular", bario_case(["xx"])))
    extra.append(("Fase inteira solida (corre ate o fim)", bario_case(["x" * 500])))
    extra.append(("Buraco intransponivel logo apos o inicio", bario_case(["x.x"])))
    extra.append(("Buraco largo demais para o alcance inicial", bario_case(["x" + "." * 8 + "x"])))
    extra.append(("Multiplos casos de teste num so arquivo", bario_case(["xx.xx", "xxx.x", "x..xx"])))
    extra.append(("Buracos alternados curtos", bario_case(["x.xx.xx.xx.xx.x"])))
    extra.append(("Pulo que aterrissa exatamente no limite do alcance", bario_case(["xxxx" + "." + "xxxx"])))
    extra.append(("Buraco duplo no meio da fase", bario_case(["x" * 3 + "." * 2 + "x" * 3])))
    extra.append(("Padrao alternado longo (quase todo buraco)", bario_case([("x." * 40) + "x"])))

    rng = random.Random(101)
    many = []
    for _ in range(60):
        n = rng.randint(2, 15)
        many.append("x" + "".join(rng.choice("xx.") for _ in range(n - 2)) + "x")
    extra.append(("60 fases pequenas aleatorias num so arquivo", bario_case(many)))

    for idx in range(1, 8):
        rng = random.Random(200 + idx)
        levels = []
        for _ in range(rng.randint(1, 5)):
            n = rng.randint(2, 300)
            dens = rng.choice([0.1, 0.25, 0.4, 0.55])
            body = "".join("." if rng.random() < dens else "x" for _ in range(n - 2))
            levels.append("x" + body + "x")
        extra.append((f"Aleatorio {idx}: fases de tamanho e densidade variados", bario_case(levels)))

    rng = random.Random(999)
    big = "x" + "".join("." if rng.random() < 0.3 else "x" for _ in range(19998)) + "x"
    extra.append(("Desempenho: fase de tamanho 2x10^4", bario_case([big])))

    finalize(kata, samples, extra)


# ================================================================== 02 Cards
def cards_case(values):
    return f"{len(values)}\n" + " ".join(map(str, values)) + "\n"


def gen_cards():
    kata = "02-cards"
    samples = existing_samples(kata)
    extra = []

    extra.append(("Cascata de eliminacoes com revalorizacao do maximo",
                  cards_case([4, 2, 6, 2, 8, 4, 10, 6, 9, 2])))
    extra.append(("Minimo: N=1", cards_case([1])))
    extra.append(("Todas as jogadas com o mesmo valor", cards_case([1] * 12)))
    extra.append(("Sequencia estritamente crescente (nunca repete)", cards_case(list(range(1, 13)))))
    extra.append(("Sequencia estritamente decrescente (nunca repete)", cards_case(list(range(12, 0, -1)))))
    extra.append(("Dois valores alternados", cards_case([1, 2] * 6)))
    extra.append(("Dois valores alternados, o maior sempre reaparecendo", cards_case([10, 3, 10, 3, 10, 3, 10, 3, 10, 3])))
    extra.append(("Duas rodadas decrescentes identicas", cards_case([5, 4, 3, 2, 1, 5, 4, 3, 2, 1])))
    extra.append(("Pares repetidos consecutivos", cards_case([2, 2, 1, 1, 2, 2, 1, 1])))
    extra.append(("Maior valor eliminado e replantado no fim", cards_case([9] + [1] * 8 + [9])))

    for idx in range(1, 8):
        rng = random.Random(300 + idx)
        n = rng.choice([5, 20, 50, 200, 800])
        hi = rng.choice([2, 5, n])
        extra.append((f"Aleatorio {idx}: N={n}, valores ate {min(hi, n)}", cards_case([rng.randint(1, min(hi, n)) for _ in range(n)])))

    rng = random.Random(777)
    n = 5000
    extra.append(("Desempenho: N=5000", cards_case([rng.randint(1, n) for _ in range(n)])))

    finalize(kata, samples, extra)


# ================================================= 03 Exploring the Terrain
def terrain_case(n, m, grid, gp, ap):
    out = f"{n} {m} {len(gp)}\n"
    out += "".join(" ".join(map(str, row)) + "\n" for row in grid)
    out += "".join(f"{i} {j}\n" for i, j in gp)
    out += "".join(f"{i} {j}\n" for i, j in ap)
    return out


def gen_terrain():
    kata = "03-exploring-terrain"
    samples = existing_samples(kata)
    extra = []

    extra.append(("Grade 3x3, T=4, planos que se cruzam varias vezes",
                  terrain_case(3, 3, [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
                               [(2, 2), (1, 1), (2, 2), (3, 3)],
                               [(2, 2), (3, 3), (1, 1), (2, 2)])))
    extra.append(("Grade 1x1: uma unica celula, T=1", terrain_case(1, 1, [[7]], [(1, 1)], [(1, 1)])))
    extra.append(("Grade 1xM (uma linha)", terrain_case(1, 6, [[1, 2, 3, 4, 5, 6]],
                                                          [(1, 1), (1, 2)], [(1, 6), (1, 5)])))
    extra.append(("Grade Nx1 (uma coluna)", terrain_case(6, 1, [[i] for i in range(1, 7)],
                                                          [(1, 1), (2, 1)], [(6, 1), (5, 1)])))
    grid = [[random.Random(1).randint(1, 9) for _ in range(4)] for _ in range(4)]
    plan = [(2, 2), (3, 3), (1, 1), (4, 4)]
    extra.append(("Planos identicos: conflito total em todo instante (0 0)", terrain_case(4, 4, grid, plan, plan)))
    extra.append(("Maquinas sempre em cantos opostos: nunca ha conflito", terrain_case(5, 5, [[3] * 5 for _ in range(5)],
                                                                                        [(1, 1)] * 4, [(5, 5)] * 4)))
    extra.append(("Maquina parada no mesmo lugar (so extrai na 1a vez)", terrain_case(3, 3, [[9] * 3 for _ in range(3)],
                                                                                       [(2, 2)] * 5, [(1, 1)] * 5)))
    extra.append(("Grade 2x2 com as maquinas trocando de posicao", terrain_case(2, 2, [[1, 1], [1, 1]],
                                                                                 [(1, 1), (2, 2)], [(1, 2), (2, 1)])))

    for idx in range(1, 9):
        rng = random.Random(400 + idx)
        n = rng.randint(1, 30)
        m = rng.randint(1, 30)
        t = rng.randint(1, min(60, n * m))
        grid = [[rng.randint(1, 1000) for _ in range(m)] for _ in range(n)]
        gp = [(rng.randint(1, n), rng.randint(1, m)) for _ in range(t)]
        ap = [(rng.randint(1, n), rng.randint(1, m)) for _ in range(t)]
        extra.append((f"Aleatorio {idx}: grade {n}x{m}, T={t}", terrain_case(n, m, grid, gp, ap)))

    rng = random.Random(888)
    n = m = 60
    t = 600
    grid = [[rng.randint(1, 1000) for _ in range(m)] for _ in range(n)]
    gp = [(rng.randint(1, n), rng.randint(1, m)) for _ in range(t)]
    ap = [(rng.randint(1, n), rng.randint(1, m)) for _ in range(t)]
    extra.append(("Desempenho: grade 60x60, T=600", terrain_case(n, m, grid, gp, ap)))

    finalize(kata, samples, extra)


# ========================================================= 04 Garment Groups
def gen_garment():
    kata = "04-garment-groups"
    samples = existing_samples(kata)
    pares = [
        (1000000, 1, "Limite superior de N, uma unica corrente"),
        (1, 1, "Minimo: uma camisa, um grupo"),
        (2, 2, "Duas camisas, cada uma seu proprio grupo"),
        (3, 1, "Todas as camisas numa unica corrente"),
        (5, 5, "N=G: nenhuma camisa compartilha pregador"),
        (10, 3, "Dez camisas em tres grupos"),
        (1000000, 1000000, "Limite superior de N, todo mundo isolado"),
        (999999, 500000, "Perto do limite, metade dos grupos com duas camisas"),
        (100, 1, "Uma unica corrente longa"),
        (7, 4, "Sete camisas em quatro grupos"),
        (12, 5, "Doze camisas em cinco grupos de tamanhos desiguais"),
    ]
    extra = [(desc, f"{n} {g}\n") for n, g, desc in pares]
    for idx in range(1, 8):
        rng = random.Random(500 + idx)
        n = rng.randint(1, 10**6)
        g = rng.randint(1, n)
        extra.append((f"Aleatorio {idx}: N={n}, G={g}", f"{n} {g}\n"))
    finalize(kata, samples, extra)


# =========================================================== 05 Dish Rack
def gen_dish():
    kata = "05-dish-rack"
    samples = existing_samples(kata)
    pares = [
        (20, 13, "Escorredor de 20 posicoes com 13 copos"),
        (2, 1, "Minimo: um copo, um escorredor de 2 posicoes"),
        (2, 2, "Escorredor cheio, so 2 posicoes"),
        (3, 2, "Escorredor de 3 com 2 copos"),
        (10, 1, "Um unico copo num escorredor grande"),
        (10, 5, "Metade do escorredor ocupado"),
        (10, 6, "Pouco mais da metade ocupado"),
        (10, 10, "Escorredor completamente cheio"),
        (100, 50, "Escorredor grande, metade ocupada"),
        (100, 51, "Escorredor grande, ocupacao logo acima da metade"),
        (1000, 999, "Escorredor quase totalmente cheio"),
    ]
    extra = [(desc, f"{n} {c}\n") for n, c, desc in pares]
    for idx in range(1, 7):
        rng = random.Random(600 + idx)
        n = rng.choice([15, 40, 200, 3000])
        c = rng.randint(1, n)
        extra.append((f"Aleatorio {idx}: N={n}, C={c}", f"{n} {c}\n"))
    finalize(kata, samples, extra)


# ========================================================== 06 N-Checkers
def checkers_case(n, rows):
    return f"{n}\n" + "\n".join(rows) + "\n"


def board_from(n, pieces):
    grid = [["." for _ in range(n)] for _ in range(n)]
    for (r, c), ch in pieces.items():
        assert (r + c) % 2 == 1, f"peca em casa branca: {(r, c)}"
        grid[r][c] = ch
    return ["".join(row) for row in grid]


def random_board(rng, n, density):
    blacks = [(r, c) for r in range(n) for c in range(n) if (r + c) % 2 == 1]
    rng.shuffle(blacks)
    k = max(2, int(len(blacks) * density))
    chosen = blacks[:k]
    pieces = {chosen[0]: "B", chosen[1]: "P"}
    for cell in chosen[2:]:
        pieces[cell] = rng.choice("BPP")
    return board_from(n, pieces)


def gen_checkers():
    kata = "06-n-checkers"
    samples = existing_samples(kata)
    extra = []

    extra.append(("Captura unica sem continuacao, tabuleiro minimo (n=4)",
                  checkers_case(4, board_from(4, {(3, 0): "B", (2, 1): "P"}))))
    extra.append(("Nenhuma captura possivel", checkers_case(4, board_from(4, {(3, 0): "B", (0, 1): "P"}))))
    extra.append(("Captura simples, tabuleiro minimo (n=4)", checkers_case(4, board_from(4, {(0, 1): "B", (1, 2): "P"}))))
    extra.append(("Cadeia de duas capturas", checkers_case(6, board_from(6, {
        (5, 0): "B", (4, 1): "P", (2, 3): "P"}))))
    extra.append(("Peca bloqueada: casa de pouso ocupada", checkers_case(4, board_from(4, {
        (3, 0): "B", (2, 1): "P", (1, 2): "P"}))))
    extra.append(("Varias pecas de Bob, so uma com captura boa", checkers_case(6, board_from(6, {
        (5, 0): "B", (5, 2): "B", (4, 1): "P", (4, 3): "P", (2, 3): "P", (2, 1): "P"}))))
    extra.append(("Captura possivel nas quatro direcoes a partir do centro", checkers_case(6, board_from(6, {
        (2, 3): "B", (1, 2): "P", (3, 2): "P", (1, 4): "P", (3, 4): "P"}))))
    extra.append(("Captura curta com peca adversaria isolada por perto", checkers_case(4, board_from(4, {
        (1, 0): "B", (2, 1): "P", (0, 1): "P"}))))
    extra.append(("Tabuleiro no limite superior (n=14), cadeia longa", checkers_case(14, board_from(14, {
        (13, 0): "B", (12, 1): "P", (10, 3): "P", (8, 5): "P", (6, 7): "P"}))))

    idx = 1
    rng = random.Random(700)
    while idx <= 8:
        n = rng.choice([4, 6, 8, 10, 12, 14])
        density = rng.choice([0.15, 0.25, 0.35])
        rows = random_board(rng, n, density)
        text = checkers_case(n, rows)
        t0 = time.time()
        gabarito(kata, text)
        if time.time() - t0 > 2.0:
            continue
        extra.append((f"Aleatorio {idx}: tabuleiro {n}x{n}, densidade {density}", text))
        idx += 1

    finalize(kata, samples, extra)


if __name__ == "__main__":
    gen_bario()
    gen_cards()
    gen_terrain()
    gen_garment()
    gen_dish()
    gen_checkers()
