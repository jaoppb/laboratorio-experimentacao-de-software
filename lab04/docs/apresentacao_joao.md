# Apresentação oral — respostas do João (perguntas 4, 5, 6, 7 e 12)

Respostas curtas (~30 s cada), apoiadas no dashboard. Os números vêm de
`dados/parametros.json`, `dados/simulado/exemplo_resultado.json`,
`dados/simulado/*.csv` e `dados/simulado/*_p_valores.npz` (semente 42).

## 4. Como os dados reais ajudaram a escolher os parâmetros da simulação

*Mostrar: seção 2 (G1, dados reais sobre a curva simulada) e `dados/parametros.json`.*

- **O que os dados mostraram:** são muito assimétricos à direita. No grupo com bot, a média é 301 h e a mediana é 7,6 h; a assimetria é 3,39 (com bot) e 3,90 (sem bot), com 5 outliers de Tukey em cada grupo. No logaritmo, a assimetria cai para 0,37 e 0,69.
- **Escolha:** por isso cada grupo é simulado como **lognormal**, parametrizada pela **mediana** e pelo **σ_log** (desvio-padrão do log do tempo), estimados dos 30 PRs de cada grupo: 7,60 h e 3,22 com bot; 2,73 h e 2,50 sem bot.
- **Por que a mediana e não a média:** a média real é puxada por poucos PRs enormes (o maior chega a 3.742 h).
- **Na simulação:** sob H₀ os dois grupos usam os mesmos parâmetros; sob H₁ só a mediana de um grupo é multiplicada por um fator.

## 5. O que cada teste compara de fato

*Mostrar: seção 1 (hipóteses) e seção 6 (dados reais).*

- **t de Welch:** compara **médias**, ponderando a diferença pelo erro-padrão e aceitando variâncias diferentes. Nos dados reais, as médias são 301 h (com bot) e 70 h (sem bot).
- **Mann-Whitney:** compara **postos**. Ele testa a dominância estocástica, P(X_com > X_sem) = 0,5, e **não** testa medianas.
- **Por que isso importa aqui:** com cauda pesada, poucos PRs enormes dominam a média e o desvio-padrão, mas não mudam os postos. É isso que o G3 e o G4 vão mostrar.

## 6. G2: distribuição da estatística sob H₀ e por que a rejeição fica onde fica

*Mostrar: seção 3 (G2).*

- **O que é:** a curva que a estatística teria se H₀ fosse verdadeira e repetíssemos o experimento muitas vezes. É uma curva teórica: t de Student com gl = 56,6 no Welch e normal padrão no Mann-Whitney.
- **Por que nas caudas:** são os valores raros sob H₀. Com α = 5%, só 5% da área fica além dos valores críticos (±2,00 no t e ±1,96 no z).
- **Duas caudas:** o teste é bicaudal (o bot pode acelerar ou atrasar o merge), então a área se divide em 2,5% de cada lado. Se a estatística observada cai nessa região, ela é improvável sob H₀ e rejeitamos.

## 7. O que o p-valor do exemplo significa e o que não significa

*Mostrar: seção 3, as áreas hachuradas do G2.*

- **No exemplo (semente 42, n = 30 por grupo):** Welch t = 0,803, p = 0,425; Mann-Whitney z = 1,515, p = 0,130. Ambos ficam acima de 0,05, então nenhum rejeita H₀.
- **Significa:** se H₀ fosse verdadeira, a chance de obter uma estatística tão extrema ou mais (as duas caudas hachuradas) seria de 42,5% no Welch e de 13,0% no Mann-Whitney. Isso não é raro.
- **Não significa:** que H₀ tem 42,5% de chance de ser verdadeira; que não existe efeito (na simulação existe: medianas de 7,6 h e 2,7 h, e o teste só não o detectou); nem o tamanho ou a importância do efeito.
- **Ressalva:** é uma única amostra. Erro tipo I e poder só aparecem nas 10.000 repetições (G3 e G4).

## 12. O que mudaria no G3 e no G4 com α = 0,01

*Mostrar: G3 (seção 4) e G4 (seção 5), com o seletor de α. O texto-resumo vem de `src/dashboard/sensibilidade.py`. Os números de α = 0,01 saem dos p-valores guardados (`dados/simulado/*_p_valores.npz`), sem simular de novo.*

- **G3 (erro tipo I):** o nível nominal cai de 5% para 1%.
  - O **Mann-Whitney** foi de 4,3%–4,8% para **0,6%–0,8%**: acompanha o nível, ficando um pouco abaixo de 1%.
  - O **Welch**, que já era conservador (0,7%–3,7%), foi para **0,0%–0,4%**: rejeita quase nunca. Na referência, 3,7% passou a 0,4%.
- **G4 (poder):** cai nos dois testes, porque o valor crítico fica mais exigente. Em média, a proporção de rejeições com efeito cai 14,5 pontos percentuais no Mann-Whitney e 13,1 no Welch.
  - Referência, razão 2,0: Mann-Whitney de 72,0% para 47,9%; Welch de 55,2% para 25,0%.
  - Parâmetros reais, com_bot, razão 4,0: Mann-Whitney de 35,2% para 14,9%; Welch de 3,4% para 0,15%.
  - Onde ambos já saturavam (referência, razão ≥ 6), quase nada muda.
- **O que não muda:** o Mann-Whitney continua à frente do Welch em todas as situações e razões, e o Welch segue sem poder nas situações de cauda pesada.
- **Compromisso:** menos falsos alarmes (tipo I) em troca de mais erros tipo II. Com n = 30 por grupo e o Welch quase sem poder, α = 0,01 só agravaria o risco de não perceber um efeito real.
