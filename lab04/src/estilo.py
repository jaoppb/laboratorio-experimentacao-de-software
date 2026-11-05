"""Definições centralizadas de estilo e paleta de cores para os gráficos do Lab04.

Garante consistência visual entre Matplotlib e Plotly, acessibilidade a
daltonismo (baseado na paleta de Okabe-Ito) e conformidade com o enunciado:
a MESMA cor para cada teste (Welch e Mann-Whitney) em todos os gráficos.
"""

from __future__ import annotations

# Cores dos testes de hipótese (reutilizadas em G2, G3 e G4)
COR_WELCH = "#0072B2"        # Azul (Okabe-Ito)
COR_MANNWHITNEY = "#D55E00"  # Vermilion / Laranja avermelhado (Okabe-Ito)

# Cores dos grupos experimentais (reutilizadas em G1 e tabelas)
COR_COM_BOT = "#0072B2"      # Azul
COR_SEM_BOT = "#E69F00"      # Laranja âmbar (Okabe-Ito)

# Cores auxiliares para curvas sob H0 e regiões de teste
COR_CURVA = "#444444"        # Cinza escuro para densidade teórica
COR_REJEICAO = "#E69F00"     # Laranja âmbar para região de rejeição crítica
COR_P_VALOR = "#56B4E9"      # Azul celeste para área do p-valor
COR_OBSERVADA = "#D55E00"    # Vermilion para a linha da estatística observada
COR_CRITICO = "#CC79A7"      # Púrpura avermelhado / linha de corte

# Cores para tipos de dados em G1 (reais vs simulados)
COR_DADOS_REAIS = "#0072B2"
COR_DADOS_SIMULADOS = "#E69F00"

# Layout padrão para gráficos Plotly
LAYOUT_BASE_PLOTLY = dict(
    font=dict(family="sans-serif", size=12, color="#333333"),
    paper_bgcolor="white",
    plot_bgcolor="#fcfcfc",
    margin=dict(l=60, r=40, t=60, b=50),
    legend=dict(
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="#dddddd",
        borderwidth=1,
    ),
)

