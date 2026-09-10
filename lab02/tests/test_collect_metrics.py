"""
Testes unitários e de integração para lab02/scripts/collect_metrics.py
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.collect_metrics import (
    analyze_file,
    format_csv,
    format_json,
    format_table,
)


def test_loc_metrics(tmp_path: Path):
    code = (
        "# Comentário inicial\n"
        "def hello():\n"
        "    # Comentário interno\n"
        "    msg = 'Hello World'\n"
        "    print(msg)\n"
        "\n"
        "hello()\n"
    )
    f = tmp_path / "hello.py"
    f.write_text(code, encoding="utf-8")

    res = analyze_file(f)
    assert res.status == "ok"
    assert res.loc == 7
    assert res.sloc == 4
    assert res.comments == 2
    assert res.blank == 1


def test_cyclomatic_complexity_with_functions(tmp_path: Path):
    code = (
        "def func_simple():\n"
        "    return 42\n"
        "\n"
        "def func_complex(x):\n"
        "    if x > 10:\n"
        "        for i in range(x):\n"
        "            if i % 2 == 0:\n"
        "                print(i)\n"
        "    return x\n"
    )
    f = tmp_path / "cc_test.py"
    f.write_text(code, encoding="utf-8")

    res = analyze_file(f)
    assert res.status == "ok"
    assert res.functions_count == 2
    # func_simple = 1, func_complex = 1 + 1 (if) + 1 (for) + 1 (if) = 4
    # Média = (1 + 4) / 2 = 2.5
    assert res.cc_avg == 2.5
    assert res.cc_max == 4
    assert res.cc_min == 1
    assert len(res.functions) == 2


def test_cyclomatic_complexity_script_without_functions(tmp_path: Path):
    code = (
        "import sys\n"
        "n = int(sys.stdin.read())\n"
        "if n > 0:\n"
        "    print(n)\n"
        "else:\n"
        "    print(0)\n"
    )
    f = tmp_path / "script_flat.py"
    f.write_text(code, encoding="utf-8")

    res = analyze_file(f)
    assert res.status == "ok"
    assert res.functions_count == 0
    # CC do script: 1 + 1 (if) = 2
    assert res.cc_avg == 2.0
    assert res.cc_max == 2


def test_duplication_clean_code(tmp_path: Path):
    code = (
        "def a():\n"
        "    return 1\n"
        "def b():\n"
        "    return 'different'\n"
        "def c():\n"
        "    x = [1, 2, 3]\n"
        "    return sum(x)\n"
    )
    f = tmp_path / "clean.py"
    f.write_text(code, encoding="utf-8")

    res = analyze_file(f, engine="python", min_lines=3)
    assert res.duplicated_lines == 0
    assert res.duplication_percentage == 0.0
    assert res.clones_count == 0


def test_duplication_with_clones_python_engine(tmp_path: Path):
    duplicated_block = (
        "    val = x * 2 + y\n"
        "    total += val\n"
        "    items.append(val)\n"
        "    print(f'Computed: {val}')\n"
    )
    code = (
        "def first_function(x, y, items):\n"
        "    total = 0\n"
        f"{duplicated_block}"
        "    return total\n"
        "\n"
        "def second_function(x, y, items):\n"
        "    total = 0\n"
        f"{duplicated_block}"
        "    return total\n"
    )
    f = tmp_path / "dup.py"
    f.write_text(code, encoding="utf-8")

    res = analyze_file(f, engine="python", min_lines=4)
    assert res.status == "ok"
    assert res.clones_count >= 1
    assert res.duplicated_lines >= 4
    assert res.duplication_percentage > 0.0


def test_maintainability_index(tmp_path: Path):
    code = (
        "import sys\n"
        "def solve():\n"
        "    lines = sys.stdin.read().split()\n"
        "    print(sum(map(int, lines)))\n"
        "if __name__ == '__main__':\n"
        "    solve()\n"
    )
    f = tmp_path / "mi_test.py"
    f.write_text(code, encoding="utf-8")

    res = analyze_file(f)
    assert res.status == "ok"
    assert 0.0 <= res.mi <= 100.0
    assert res.mi_rank in ("A", "B", "C")


def test_metadata_fields(tmp_path: Path):
    code = "print('hello')\n"
    f = tmp_path / "meta.py"
    f.write_text(code, encoding="utf-8")

    res = analyze_file(
        f,
        kata="01-bario-world",
        participant="joao",
        treatment="ai",
        trial_id="trial-42",
    )
    assert res.kata == "01-bario-world"
    assert res.participant == "joao"
    assert res.treatment == "ai"
    assert res.trial_id == "trial-42"


def test_format_outputs(tmp_path: Path):
    code = "def a(): pass\n"
    f = tmp_path / "f.py"
    f.write_text(code, encoding="utf-8")

    res = [analyze_file(f, kata="test-kata", participant="joao")]

    tbl = format_table(res)
    assert "test-kata" in tbl
    assert "LOC" in tbl

    js = format_json(res)
    data = json.loads(js)
    assert len(data) == 1
    assert data[0]["kata"] == "test-kata"
    assert data[0]["participant"] == "joao"

    csv_out = format_csv(res)
    assert "kata,participant" in csv_out
    assert "test-kata,joao" in csv_out


def test_all_official_gabaritos():
    """Valida que todos os 6 gabaritos oficiais rodam com sucesso e métricas consistentes."""
    gabaritos_dir = Path(__file__).resolve().parent.parent / "katas" / "gabaritos"
    gabaritos = sorted(gabaritos_dir.glob("*.py"))
    assert len(gabaritos) == 6, f"Esperado 6 gabaritos, encontrados: {len(gabaritos)}"

    for g in gabaritos:
        res = analyze_file(g, engine="python")
        assert res.status == "ok", f"Erro no gabarito {g.name}: {res.error_message}"
        assert res.loc > 0, f"LOC inválido no gabarito {g.name}"
        assert res.cc_avg >= 1.0, f"CC inválido no gabarito {g.name}"
        assert res.duplication_percentage == 0.0, (
            f"Duplicação detectada indevidamente em {g.name}"
        )
        assert res.mi > 0.0, f"MI inválido no gabarito {g.name}"
        assert res.mi_rank == "A", f"Rank MI abaixo de A no gabarito {g.name}"
