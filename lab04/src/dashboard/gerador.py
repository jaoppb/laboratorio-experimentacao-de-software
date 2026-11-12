"""Gerador do Dashboard estático em HTML do Lab04 (Sprints 1 e 2).

Gera ``dashboard/index.html`` contendo:
- Topo com links para repositório, quadro GitHub Projects e endereço do Pages;
- Seção 1: Cenário (sem gráfico, com números dinâmicos lidos do CSV);
- Seção 2: Os dados (com gráfico G1 interativo em Plotly);
- Seção 3: Como os testes funcionam (com gráfico G2 interativo em Plotly);
- Seção 4: Erro tipo I (G3) e Seção 5: Poder (G4), a partir dos CSVs de Q1, Q2 e Q3;
- Seção 6: Dados reais (tabela de ``resultado_testes.json``);
- Seção 7: conclusão (expectativa × resultado e recomendação), a partir de G3 e G4;
- Plotly.js embutido para funcionamento 100% offline sem servidor.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from plotly.offline import get_plotlyjs
from scipy import stats

from scripts.exemplo_simulado import carregar_parametros, executar as executar_exemplo
from src.graficos.g1 import carregar_dados_reais, figura_g1
from src.dashboard.conclusao import texto_conclusao
from src.dashboard.formato import num as _num
from src.dashboard.formato import pct as _pct
from src.dashboard.sensibilidade import texto_sensibilidade
from src.graficos.dados_simulacao import (
    carregar_erro_tipo1,
    carregar_erro_tipo1_em,
    carregar_poder,
    carregar_poder_em,
)
from src.graficos.g2_plotly import figura_g2_plotly
from src.graficos.g3 import figura_g3
from src.graficos.g4 import figura_g4

RAIZ = Path(__file__).resolve().parents[2]
DIR_DASHBOARD = RAIZ / "dashboard"
ARQUIVO_HTML = DIR_DASHBOARD / "index.html"
ARQUIVO_RESULTADO_REAIS = RAIZ / "dados" / "reais" / "resultado_testes.json"
ARQUIVO_BUNDLE = RAIZ / "dados" / "dashboard_bundle.json"
ALFA_SENSIBILIDADE = 0.01


def texto_erro_tipo1(tipo1: pd.DataFrame, alpha: float = 0.05) -> str:
    """Texto da seção 4 (2 a 4 frases), calculado a partir das taxas simuladas."""
    w = tipo1[tipo1["teste"] == "welch"]["taxa_rejeicao"]
    m = tipo1[tipo1["teste"] == "mannwhitney"]["taxa_rejeicao"]
    n_rep_fmt = f"{int(tipo1['n_rep'].iloc[0]):,}".replace(",", ".")
    pior = tipo1[tipo1["teste"] == "welch"].sort_values("taxa_rejeicao").iloc[0]
    sentido = "conservador" if w.max() < alpha else "fora de 5%"
    return (
        f"O gráfico G3 mostra, em cada situação simulada com H₀ verdadeira, a proporção de "
        f"p-valores abaixo de {_num(alpha, 2)} de cada teste em {n_rep_fmt} repetições"
        f" (barras de erro: margem de 95%); a linha tracejada marca os 5% esperados. "
        f"O Mann-Whitney ficou entre {_pct(m.min())} e {_pct(m.max())}, perto de 5% em todas as situações. "
        f"O t de Welch foi o que se desviou: ficou {sentido}, entre {_pct(w.min())} e {_pct(w.max())}, "
        f"e o desvio foi maior nos cenários de cauda mais pesada (mínimo de {_pct(pior['taxa_rejeicao'])} "
        f"em {pior['cenario']}). "
        f"O grupo conclui que o Welch erra para menos (raramente \"encontra\" um efeito, falso ou verdadeiro), "
        f"e que o Mann-Whitney mantém o erro tipo I sob controle."
    )


def texto_poder(poder: pd.DataFrame) -> str:
    """Texto da seção 5 (2 a 4 frases), calculado a partir das curvas de poder."""
    piv = poder.pivot_table(
        index=["cenario", "razao_medianas"], columns="teste", values="taxa_rejeicao"
    )
    welch_vence = piv[piv["welch"] > piv["mannwhitney"]]
    max_razao = float(poder["razao_medianas"].max())
    ref = piv.loc[("referencia", 2.0)]
    com = piv.loc[("com_bot", 4.0)]
    if welch_vence.empty:
        lado = (
            "Em nenhuma das situações simuladas o Welch superou o Mann-Whitney, "
            "então a vantagem não mudou de lado"
        )
    else:
        lugares = ", ".join(sorted({c for c, _ in welch_vence.index}))
        lado = f"A vantagem mudou de lado em: {lugares}"
    return (
        f"O gráfico G4 traz as curvas de poder (proporção de rejeições × razão entre as medianas, "
        f"de 1,0 a {max_razao:g}); a razão 1,0 é o erro tipo I, e a cor identifica o teste. "
        f"O Mann-Whitney detecta melhor o efeito em todas as situações: com a razão 2,0 na situação "
        f"de referência, {_pct(ref['mannwhitney'])} contra {_pct(ref['welch'])} do Welch, e com os parâmetros "
        f"reais (com_bot) e razão 4,0, {_pct(com['mannwhitney'])} contra {_pct(com['welch'])}. "
        f"{lado}; a diferença é pequena na referência e enorme com assimetria extrema e com os "
        f"parâmetros reais, onde o Welch quase não detecta efeito."
    )


def tabela_dados_reais(resultado: dict) -> str:
    """Tabela HTML da seção 6: estatística, p-valor, efeito e conclusão de cada teste."""
    alpha = float(resultado["alfa"])
    linhas = []
    for chave, nome, rotulo_estat, rotulo_efeito in (
        ("welch", "t de Welch", "t", "d de Cohen"),
        ("mannwhitney", "Mann-Whitney", "z", "correlação rank-biserial"),
    ):
        r = resultado[chave]
        decisao = "Rejeita H₀" if float(r["p_valor"]) < alpha else "Não rejeita H₀"
        linhas.append(
            "        <tr>"
            f"<td>{nome}</td>"
            f"<td>{rotulo_estat} = {_num(float(r['estatistica']))}</td>"
            f"<td>{_num(float(r['p_valor']), 4)}</td>"
            f"<td>{rotulo_efeito} = {_num(float(r['tamanho_efeito']))} ({r['magnitude_efeito']})</td>"
            f"<td>{decisao} (α = {_num(alpha, 2)}): {r['conclusao'].split(': ', 1)[-1]}</td>"
            "</tr>"
        )
    corpo = "\n".join(linhas)
    return (
        '      <table class="tabela-testes">\n'
        "        <thead><tr><th>Teste</th><th>Estatística</th><th>p-valor</th>"
        "<th>Tamanho do efeito</th><th>Conclusão</th></tr></thead>\n"
        f"        <tbody>\n{corpo}\n        </tbody>\n"
        "      </table>"
    )


def texto_dados_reais(resultado: dict) -> str:
    """Texto curto da seção 6, calculado a partir de ``resultado_testes.json``."""
    n_com, n_sem = resultado["n"]["com_bot"], resultado["n"]["sem_bot"]
    med = resultado["medianas_horas"]
    w, m = resultado["welch"], resultado["mannwhitney"]
    alpha = float(resultado["alfa"])
    rejeitam = [
        r for r in (w, m) if float(r["p_valor"]) < alpha
    ]
    if not rejeitam:
        veredito = (
            "nenhum dos dois testes rejeita H₀: os dados não mostram diferença de tempo de merge "
            "entre os grupos"
        )
    elif len(rejeitam) == 2:
        veredito = "os dois testes rejeitam H₀"
    else:
        veredito = "os testes discordam"
    if rejeitam:
        ressalva = (
            "Como a coleta é observacional (grupos de períodos diferentes), a diferença não prova "
            "que o bot a causou."
        )
    else:
        ressalva = (
            f"Com n = {min(n_com, n_sem)} por grupo e a cauda pesada vista no G4, falta de significância "
            "não prova ausência de efeito: a amostra é pequena para detectá-lo."
        )
    return (
        f"A tabela aplica os dois testes (bicaudais, α = {_num(alpha, 2)}) aos {n_com} PRs com bot e {n_sem} "
        f"sem bot; as medianas são {_num(med['com_bot'], 2)} h e {_num(med['sem_bot'], 2)} h. "
        f"Com p = {_num(float(w['p_valor']), 3)} (Welch) e p = {_num(float(m['p_valor']), 3)} (Mann-Whitney), "
        f"{veredito}. "
        f"Os tamanhos de efeito são {w['magnitude_efeito']} (d = {_num(float(w['tamanho_efeito']), 2)}) e "
        f"{m['magnitude_efeito']} (rank-biserial = {_num(float(m['tamanho_efeito']), 2)}). "
        f"{ressalva}"
    )

LINK_REPO = "https://github.com/jaoppb/laboratorio-experimentacao-de-software"
LINK_PROJECTS = "https://github.com/users/jaoppb/projects/3/views/1"
LINK_PAGES = "https://jaoppb.github.io/laboratorio-experimentacao-de-software/lab04/"


def construir_html(
    df_reais: pd.DataFrame,
    params: dict,
    resultado_exemplo: dict,
    div_g1: str,
    div_g2: str,
    div_g3: str,
    div_g4: str,
    tipo1: pd.DataFrame,
    poder: pd.DataFrame,
    resultado_reais: dict,
    texto_alfa: str,
) -> str:
    """Monta o documento HTML completo com textos alimentados pelos dados."""
    texto_s4 = texto_erro_tipo1(tipo1)
    texto_s5 = texto_poder(poder)
    texto_s6 = texto_dados_reais(resultado_reais)
    texto_s7 = texto_conclusao(tipo1, poder)
    tabela_s6 = tabela_dados_reais(resultado_reais)
    n_total = len(df_reais)
    n_com = len(df_reais[df_reais["grupo"] == "com_bot"])
    n_sem = len(df_reais[df_reais["grupo"] == "sem_bot"])
    mediana_real_com = float(df_reais[df_reais["grupo"] == "com_bot"]["tempo_merge_horas"].median())
    mediana_real_sem = float(df_reais[df_reais["grupo"] == "sem_bot"]["tempo_merge_horas"].median())
    max_real_com = float(df_reais[df_reais["grupo"] == "com_bot"]["tempo_merge_horas"].max())

    p_com_med = float(params["com_bot"]["mediana"])
    p_com_sig = float(params["com_bot"]["sigma_log"])
    p_sem_med = float(params["sem_bot"]["mediana"])
    p_sem_sig = float(params["sem_bot"]["sigma_log"])

    w_stat = float(resultado_exemplo["welch"]["estatistica"])
    w_gl = float(resultado_exemplo["welch"]["gl"])
    w_p = float(resultado_exemplo["welch"]["p_valor"])
    mw_stat = float(resultado_exemplo["mannwhitney"]["estatistica"])
    mw_p = float(resultado_exemplo["mannwhitney"]["p_valor"])
    alpha = float(resultado_exemplo["parametros"]["alpha"])
    if w_p >= alpha and mw_p >= alpha:
        veredito_exemplo = f"ambos superiores a {alpha:g}, e nenhum teste rejeita H₀"
    elif w_p < alpha and mw_p < alpha:
        veredito_exemplo = f"ambos inferiores a {alpha:g}, e os dois testes rejeitam H₀"
    else:
        veredito_exemplo = f"em lados opostos de {alpha:g}, e os testes discordam"

    plotly_js = get_plotlyjs()

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lab04: Welch × Mann-Whitney em Dados Lognormais</title>
  <style>
    :root {{
      --cor-fundo: #f8fafc;
      --cor-card: #ffffff;
      --cor-texto: #1e293b;
      --cor-muted: #64748b;
      --cor-borda: #e2e8f0;
      --cor-primaria: #0369a1;
      --cor-destaque: #0284c7;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--cor-fundo);
      color: var(--cor-texto);
      line-height: 1.6;
      padding-bottom: 60px;
    }}
    header {{
      background: white;
      border-bottom: 1px solid var(--cor-borda);
      padding: 24px 32px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .header-content {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    h1 {{
      font-size: 1.75rem;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 12px;
    }}
    .nav-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 0.95rem;
    }}
    .nav-links a {{
      color: var(--cor-primaria);
      text-decoration: none;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      background: #f1f5f9;
      border-radius: 6px;
      transition: background 0.15s ease;
    }}
    .nav-links a:hover {{
      background: #e2e8f0;
    }}
    main {{
      max-width: 1200px;
      margin: 32px auto;
      padding: 0 24px;
      display: flex;
      flex-direction: column;
      gap: 32px;
    }}
    section.card {{
      background: var(--cor-card);
      border: 1px solid var(--cor-borda);
      border-radius: 10px;
      padding: 28px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    h2 {{
      font-size: 1.35rem;
      color: #0f172a;
      margin-bottom: 16px;
      border-bottom: 2px solid #f1f5f9;
      padding-bottom: 8px;
    }}
    p.secao-texto {{
      font-size: 1.02rem;
      color: #334155;
      margin-bottom: 20px;
    }}
    .grafico-container {{
      width: 100%;
      min-height: 480px;
      background: #ffffff;
      border-radius: 8px;
      overflow: hidden;
    }}
    table.tabela-testes {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }}
    table.tabela-testes th, table.tabela-testes td {{
      border: 1px solid var(--cor-borda);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    table.tabela-testes thead th {{
      background: #f1f5f9;
    }}
  </style>
  <script type="text/javascript">{plotly_js}</script>
</head>
<body>
  <header>
    <div class="header-content">
      <h1>Lab04 — Testes de Hipótese por Simulação: Welch × Mann-Whitney</h1>
      <nav class="nav-links">
        <a href="{LINK_REPO}" target="_blank" rel="noopener">Repositório GitHub</a>
        <a href="{LINK_PROJECTS}" target="_blank" rel="noopener">GitHub Projects (Quadro)</a>
        <a href="{LINK_PAGES}" target="_blank" rel="noopener">Dashboard Publicado (GitHub Pages)</a>
      </nav>
    </div>
  </header>

  <main>
    <!-- 1. Cenário -->
    <section class="card" id="cenario">
      <h2>1. Cenário</h2>
      <p class="secao-texto">
        O estudo investiga se o tempo até o merge de Pull Requests difere quando revisados pelo bot de revisão CodeRabbit em comparação a PRs sem bot de revisão no repositório público tailwindlabs/tailwindcss.
        A hipótese nula (H₀) postula que a distribuição do tempo até o merge é idêntica entre os grupos (médias iguais para Welch e probabilidade de dominância P(X_com &gt; X_sem) = 0,5 para Mann-Whitney), enquanto a hipótese alternativa (H₁) bicaudal afirma que os tempos diferem.
        Os dados reais foram coletados via API do GitHub antes e depois da adoção da ferramenta, totalizando {n_total} observações ({n_com} PRs com bot e {n_sem} PRs sem bot).
      </p>
    </section>

    <!-- 2. Os dados (G1) -->
    <section class="card" id="dados">
      <h2>2. Os dados (G1)</h2>
      <p class="secao-texto">
        O gráfico G1 apresenta a comparação dos histogramas dos dados reais com os dados simulados sob escala logarítmica (log10), evidenciando a forte assimetria à direita e a presença de outliers severos na amostra real (máximo de {max_real_com:.1f} h contra medianas empíricas de {mediana_real_com:.2f} h com bot e {mediana_real_sem:.2f} h sem bot).
        Como a média amostral é fortemente distorcida pela cauda longa, a simulação utiliza a distribuição lognormal parametrizada rigorosamente pelas medianas estimadas ({p_com_med:.2f} h e {p_sem_med:.2f} h) e desvios logarítmicos σ_log ({p_com_sig:.2f} e {p_sem_sig:.2f}).
        O grupo conclui que os dados sintéticos reproduzem a assimetria e a cauda pesada observadas, o que torna a simulação uma calibração realista; como são apenas {n_com} e {n_sem} PRs reais por grupo, os parâmetros têm incerteza considerável.
      </p>
      <div class="grafico-container">
        {div_g1}
      </div>
    </section>

    <!-- 3. Como os testes funcionam (G2) -->
    <section class="card" id="testes">
      <h2>3. Como os testes funcionam (G2)</h2>
      <p class="secao-texto">
        O gráfico G2 ilustra a distribuição amostral teórica da estatística de teste sob H₀ (t de Student com gl = {w_gl:.1f} para Welch e normal padrão assintótica para Mann-Whitney), destacando as regiões críticas de rejeição bilateral para α = {alpha:g}.
        O teste t de Welch compara a diferença de médias ponderada pelo erro-padrão, enquanto o Mann-Whitney avalia postos e dominância estocástica, não medindo diretamente medianas sob variâncias heterogêneas.
        No exemplo simulado, as estatísticas observadas (t = {w_stat:.3f} e z = {mw_stat:.3f}) geraram p-valores de {w_p:.4f} e {mw_p:.4f}, {veredito_exemplo}; essa amostra única não permite estimar erro tipo I nem poder, demandando a simulação de Monte Carlo com 10.000 repetições.
      </p>
      <div class="grafico-container">
        {div_g2}
      </div>
    </section>

    <!-- 4. Erro tipo I (G3) -->
    <section class="card" id="erro-tipo-i">
      <h2>4. Erro tipo I</h2>
      <p class="secao-texto">
        {texto_s4}
      </p>
      <div class="grafico-container">
        {div_g3}
      </div>
    </section>

    <!-- 5. Poder (G4) -->
    <section class="card" id="poder">
      <h2>5. Poder</h2>
      <p class="secao-texto">
        {texto_s5}
      </p>
      <div class="grafico-container">
        {div_g4}
      </div>
      <p class="secao-texto" id="sensibilidade-alfa">{texto_alfa}</p>
    </section>

    <!-- 6. Dados reais -->
    <section class="card" id="dados-reais">
      <h2>6. Dados reais</h2>
      <p class="secao-texto">
        {texto_s6}
      </p>
{tabela_s6}
    </section>

    <!-- 7. Conclusão -->
    <section class="card" id="conclusao">
      <h2>7. Conclusão</h2>
      <p class="secao-texto" id="conclusao-texto">
        {texto_s7}
      </p>
    </section>
  </main>
</body>
</html>
"""


def gerar_bundle(
    df_reais: pd.DataFrame,
    params: dict,
    resultado_exemplo: dict,
    tipo1_005: pd.DataFrame,
    tipo1_001: pd.DataFrame,
    poder_005: pd.DataFrame,
    poder_001: pd.DataFrame,
    resultado_reais: dict,
) -> dict:
    """Exporta todas as métricas, curvas de densidade teórica e textos canônicos em dict estruturado."""
    n_total = len(df_reais)
    n_com = len(df_reais[df_reais["grupo"] == "com_bot"])
    n_sem = len(df_reais[df_reais["grupo"] == "sem_bot"])
    mediana_real_com = float(df_reais[df_reais["grupo"] == "com_bot"]["tempo_merge_horas"].median())
    mediana_real_sem = float(df_reais[df_reais["grupo"] == "sem_bot"]["tempo_merge_horas"].median())
    max_real_com = float(df_reais[df_reais["grupo"] == "com_bot"]["tempo_merge_horas"].max())

    p_com_med = float(params["com_bot"]["mediana"])
    p_com_sig = float(params["com_bot"]["sigma_log"])
    p_sem_med = float(params["sem_bot"]["mediana"])
    p_sem_sig = float(params["sem_bot"]["sigma_log"])

    w_stat = float(resultado_exemplo["welch"]["estatistica"])
    w_gl = float(resultado_exemplo["welch"]["gl"])
    w_p = float(resultado_exemplo["welch"]["p_valor"])
    mw_stat = float(resultado_exemplo["mannwhitney"]["estatistica"])
    mw_p = float(resultado_exemplo["mannwhitney"]["p_valor"])
    alpha = float(resultado_exemplo["parametros"]["alpha"])

    if w_p >= alpha and mw_p >= alpha:
        veredito_exemplo = f"ambos superiores a {alpha:g}, e nenhum teste rejeita H₀"
    elif w_p < alpha and mw_p < alpha:
        veredito_exemplo = f"ambos inferiores a {alpha:g}, e os dois testes rejeitam H₀"
    else:
        veredito_exemplo = f"em lados opostos de {alpha:g}, e os testes discordam"

    secao_1 = (
        f"O estudo investiga se o tempo até o merge de Pull Requests difere quando revisados "
        f"pelo bot de revisão CodeRabbit em comparação a PRs sem bot de revisão no repositório "
        f"público tailwindlabs/tailwindcss. A hipótese nula (H₀) postula que a distribuição do "
        f"tempo até o merge é idêntica entre os grupos (médias iguais para Welch e probabilidade "
        f"de dominância P(X_com > X_sem) = 0,5 para Mann-Whitney), enquanto a hipótese alternativa "
        f"(H₁) bicaudal afirma que os tempos diferem. Os dados reais foram coletados via API do "
        f"GitHub antes e depois da adoção da ferramenta, totalizando {n_total} observações "
        f"({n_com} PRs com bot e {n_sem} PRs sem bot)."
    )

    secao_2 = (
        f"O gráfico G1 apresenta a comparação dos histogramas dos dados reais com os dados "
        f"simulados sob escala logarítmica (log10), evidenciando a forte assimetria à direita e a "
        f"presença de outliers severos na amostra real (máximo de {max_real_com:.1f} h contra medianas "
        f"empíricas de {mediana_real_com:.2f} h com bot e {mediana_real_sem:.2f} h sem bot). "
        f"Como a média amostral é fortemente distorcida pela cauda longa, a simulação utiliza a "
        f"distribuição lognormal parametrizada rigorosamente pelas medianas estimadas ({p_com_med:.2f} h "
        f"e {p_sem_med:.2f} h) e desvios logarítmicos σ_log ({p_com_sig:.2f} e {p_sem_sig:.2f}). "
        f"O grupo conclui que os dados sintéticos reproduzem a assimetria e a cauda pesada observadas, "
        f"o que torna a simulação uma calibração realista; como são apenas {n_com} e {n_sem} PRs reais por grupo, "
        f"os parâmetros têm incerteza considerável."
    )

    secao_3 = (
        f"O gráfico G2 ilustra a distribuição amostral teórica da estatística de teste sob H₀ (t de Student "
        f"com gl = {w_gl:.1f} para Welch e normal padrão assintótica para Mann-Whitney), destacando as "
        f"regiões críticas de rejeição bilateral para α = {alpha:g}. O teste t de Welch compara a diferença de "
        f"médias ponderada pelo erro-padrão, enquanto o Mann-Whitney avalia postos e dominância estocástica, não "
        f"medindo diretamente medianas sob variâncias heterogêneas. No exemplo simulado, as estatísticas "
        f"observadas (t = {w_stat:.3f} e z = {mw_stat:.3f}) geraram p-valores de {w_p:.4f} e {mw_p:.4f}, "
        f"{veredito_exemplo}; essa amostra única não permite estimar erro tipo I nem poder, demandando a simulação "
        f"de Monte Carlo com 10.000 repetições."
    )

    w_dist = stats.t(w_gl)
    w_crit_05 = float(w_dist.ppf(1.0 - 0.05 / 2.0))
    w_crit_01 = float(w_dist.ppf(1.0 - 0.01 / 2.0))
    w_lim = float(1.15 * max(abs(w_stat), w_crit_01, float(w_dist.ppf(0.9995))))
    w_x = np.linspace(-w_lim, w_lim, 600)
    w_y = w_dist.pdf(w_x)

    mw_dist = stats.norm()
    mw_crit_05 = float(mw_dist.ppf(1.0 - 0.05 / 2.0))
    mw_crit_01 = float(mw_dist.ppf(1.0 - 0.01 / 2.0))
    mw_lim = float(1.15 * max(abs(mw_stat), mw_crit_01, float(mw_dist.ppf(0.9995))))
    mw_x = np.linspace(-mw_lim, mw_lim, 600)
    mw_y = mw_dist.pdf(mw_x)

    def _tipo1_records(df: pd.DataFrame) -> list[dict]:
        recs = []
        for _, row in df.iterrows():
            n = int(row["n_rep"])
            p = float(row["taxa_rejeicao"])
            m = float(1.96 * np.sqrt(p * (1.0 - p) / n) * 100.0)
            recs.append({
                "cenario": str(row["cenario"]),
                "teste": str(row["teste"]),
                "n_rep": n,
                "alfa": float(row["alfa"]),
                "taxa_rejeicao": p,
                "margem_erro_pct": round(m, 3),
            })
        return recs

    def _poder_records(df: pd.DataFrame) -> list[dict]:
        recs = []
        for _, row in df.iterrows():
            recs.append({
                "cenario": str(row["cenario"]),
                "teste": str(row["teste"]),
                "razao_medianas": float(row["razao_medianas"]),
                "n_rep": int(row["n_rep"]),
                "alfa": float(row["alfa"]),
                "taxa_rejeicao": float(row["taxa_rejeicao"]),
            })
        return recs

    texto_s4_005 = texto_erro_tipo1(tipo1_005, 0.05)
    texto_s4_001 = texto_erro_tipo1(tipo1_001, 0.01)
    texto_s5_005 = texto_poder(poder_005)
    texto_s5_001 = texto_poder(poder_001)
    texto_sens = texto_sensibilidade(tipo1_005, tipo1_001, poder_005, poder_001)
    texto_s6 = texto_dados_reais(resultado_reais)
    texto_s7 = texto_conclusao(tipo1_005, poder_005)

    return {
        "links": {
            "repo": LINK_REPO,
            "projects": LINK_PROJECTS,
            "pages": LINK_PAGES,
        },
        "parametros": params,
        "resultado_exemplo": resultado_exemplo,
        "resultado_testes": resultado_reais,
        "textos": {
            "secao_1": secao_1,
            "secao_2": secao_2,
            "secao_3": secao_3,
            "secao_4_alfa_005": texto_s4_005,
            "secao_4_alfa_001": texto_s4_001,
            "secao_5_alfa_005": texto_s5_005,
            "secao_5_alfa_001": texto_s5_001,
            "sensibilidade_alfa": texto_sens,
            "secao_6": texto_s6,
            "secao_7": texto_s7,
        },
        "g2": {
            "welch": {
                "gl": w_gl,
                "estatistica": w_stat,
                "p_valor": w_p,
                "critico_005": round(w_crit_05, 4),
                "critico_001": round(w_crit_01, 4),
                "x": [round(float(v), 4) for v in w_x],
                "y": [round(float(v), 5) for v in w_y],
            },
            "mannwhitney": {
                "estatistica": mw_stat,
                "p_valor": mw_p,
                "u": float(resultado_exemplo["mannwhitney"].get("u", 0)),
                "critico_005": round(mw_crit_05, 4),
                "critico_001": round(mw_crit_01, 4),
                "x": [round(float(v), 4) for v in mw_x],
                "y": [round(float(v), 5) for v in mw_y],
            },
        },
        "simulacoes": {
            "erro_tipo1_005": _tipo1_records(tipo1_005),
            "erro_tipo1_001": _tipo1_records(tipo1_001),
            "poder_005": _poder_records(poder_005),
            "poder_001": _poder_records(poder_001),
        },
    }


def gerar_dashboard(diretorio_saida: Path = DIR_DASHBOARD) -> Path:
    """Executa o pipeline completo do Lab04, exporta o bundle JSON e gera o dashboard.

    1. Executa o exemplo simulado determinístico (semente 42);
    2. Lê os arquivos versionados (dados reais, parâmetros e resultado do exemplo);
    3. Constrói figuras Plotly e exporta lab04/dados/dashboard_bundle.json;
    4. Grava HTML em diretorio_saida (ou constrói SPA em DIR_DASHBOARD).
    """
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    # 1. Atualizar e obter resultado do exemplo simulado
    resultado_exemplo = executar_exemplo()

    # 2. Carregar dados reais e parâmetros
    df_reais = carregar_dados_reais()
    params = carregar_parametros()
    resultado_reais = json.loads(ARQUIVO_RESULTADO_REAIS.read_text(encoding="utf-8"))

    # 3. Simulações Q1 a Q3
    tipo1 = carregar_erro_tipo1()
    poder = carregar_poder()
    tipo1_01 = carregar_erro_tipo1_em(ALFA_SENSIBILIDADE)
    poder_01 = carregar_poder_em(ALFA_SENSIBILIDADE)

    # 4. Gerar e exportar dashboard_bundle.json
    bundle = gerar_bundle(
        df_reais=df_reais,
        params=params,
        resultado_exemplo=resultado_exemplo,
        tipo1_005=tipo1,
        tipo1_001=tipo1_01,
        poder_005=poder,
        poder_001=poder_01,
        resultado_reais=resultado_reais,
    )
    ARQUIVO_BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_BUNDLE.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    if diretorio_saida != DIR_DASHBOARD:
        (diretorio_saida / "dashboard_bundle.json").write_text(
            json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # 5. Gerar figuras com IDs fixos para garantir reprodutibilidade exata
    fig_g1 = figura_g1(dados_reais=df_reais, parametros=params, semente=42)
    div_g1 = fig_g1.to_html(include_plotlyjs=False, full_html=False, div_id="grafico_g1")

    fig_g2 = figura_g2_plotly(
        resultado_welch=resultado_exemplo["welch"],
        resultado_mw=resultado_exemplo["mannwhitney"],
        alpha=float(resultado_exemplo["parametros"]["alpha"]),
    )
    div_g2 = fig_g2.to_html(include_plotlyjs=False, full_html=False, div_id="grafico_g2")

    div_g3 = figura_g3(tipo1, 0.05, tipo1_01, ALFA_SENSIBILIDADE).to_html(
        include_plotlyjs=False, full_html=False, div_id="grafico_g3"
    )
    div_g4 = figura_g4(poder, 0.05, poder_01, ALFA_SENSIBILIDADE).to_html(
        include_plotlyjs=False, full_html=False, div_id="grafico_g4"
    )

    # 6. Renderizar HTML estático (para tmp_path e compatibilidade)
    html = construir_html(
        df_reais=df_reais,
        params=params,
        resultado_exemplo=resultado_exemplo,
        div_g1=div_g1,
        div_g2=div_g2,
        div_g3=div_g3,
        div_g4=div_g4,
        tipo1=tipo1,
        poder=poder,
        resultado_reais=resultado_reais,
        texto_alfa=texto_sensibilidade(tipo1, tipo1_01, poder, poder_01),
    )

    if diretorio_saida != DIR_DASHBOARD:
        caminho_final = diretorio_saida / "index.html"
        caminho_final.write_text(html, encoding="utf-8")
        return caminho_final

    # Quando apontado para DIR_DASHBOARD, compila a SPA React
    if (DIR_DASHBOARD / "package.json").exists():
        try:
            subprocess.run(["npm", "run", "build"], cwd=DIR_DASHBOARD, check=True, capture_output=True)
        except Exception:
            pass
        dist_index = DIR_DASHBOARD / "dist" / "index.html"
        if dist_index.exists():
            return dist_index

    return ARQUIVO_BUNDLE

