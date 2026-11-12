"""Formatação pt-BR de números dos textos do dashboard."""


def pct(valor: float) -> str:
    """Formata proporção como porcentagem em pt-BR (ex.: 0,0456 -> '4,6%')."""
    return f"{valor * 100:.1f}".replace(".", ",") + "%"


def num(valor: float, casas: int = 3) -> str:
    """Formata número com vírgula decimal."""
    return f"{valor:.{casas}f}".replace(".", ",")
