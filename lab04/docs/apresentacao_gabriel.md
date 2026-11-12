# Apresentação oral — respostas do Gabriel (perguntas 1, 2, 3, 11 e 14)

Respostas curtas (~30 s cada), apoiadas no dashboard. Os números vêm de
`dados/reais/pr_merge_time.csv`, `dados/reais/resultado_testes.json`,
`dados/parametros.json` e `dados/simulado/q3_*.csv` (semente 42).

## 1. Cenário, H₀ e H₁ em palavras simples

*Mostrar: seção 1 (cenário).*

- **Cenário:** o tempo até o merge de um PR muda quando ele é revisado por um bot de revisão (CodeRabbit)? Comparamos 30 PRs com bot e 30 sem bot do `tailwindlabs/tailwindcss`.
- **H₀:** o bot não faz diferença: os dois grupos têm o mesmo comportamento de tempo de merge (médias iguais no Welch; nenhum grupo tende a demorar mais no Mann-Whitney).
- **H₁:** o tempo de merge é diferente entre os grupos, para mais ou para menos.

## 2. Unicaudal ou bicaudal, e por quê

*Mostrar: seção 1 e G2 (duas caudas sombreadas).*

- **Bicaudal**, com α = 5% (2,5% em cada cauda).
- **Por quê:** não temos razão forte para prever o sentido. O bot pode acelerar o merge (feedback imediato) ou atrasá-lo (mais comentários para resolver). A pergunta é "mudou?", não "melhorou?".
- Escolher o sentido depois de olhar os dados inflaria o erro tipo I; por isso a escolha foi feita antes, em `docs/cenario.md`.

## 3. Como os dados reais foram coletados e o que mostraram sobre a forma

*Mostrar: seção 2 (G1) e `dados/reais/FONTE.md`.*

- **Coleta:** `scripts/coletar_prs.py`, via API do GitHub (`gh`). Só PRs mergeados, de autor humano e não rascunho. `sem_bot`: criados entre jan e ago/2025, antes de qualquer bot. `com_bot`: criados a partir de dez/2025 com comentário do CodeRabbit antes do merge. Sorteamos 30 de cada grupo (240 e 349 elegíveis), com semente 42.
- **Forma:** muito assimétrica à direita. Metade dos PRs é mergeada em poucas horas (medianas de 7,6 h com bot e 2,7 h sem bot), mas poucos levam semanas ou meses (o maior chega a 3.742 h). A média é 301 h com bot e 70 h sem bot, muito acima da mediana, e cada grupo tem 5 outliers de Tukey. No logaritmo, a assimetria cai para perto de zero, o que sustenta a lognormal.
- **Ressalva:** os grupos são de períodos diferentes (antes × depois do bot), então a comparação é observacional.

## 11. Que violação de pressuposto foi simulada e por que afeta mais um teste

*Mostrar: G3 e G4 (seções 4 e 5) e `docs/violacoes_q3.md`.*

- **Simulamos três violações do Welch**, mudando um fator por vez a partir de uma referência (n = 30, σ_log = 1,0): **amostra pequena** (n = 10), **assimetria extrema** (σ_log = 3,0, perto dos 2,5 a 3,2 dos dados reais) e **outliers** (5% das observações multiplicadas por 20).
- **Por que o Welch sofre mais:** ele compara médias, e a média e o desvio-padrão são dominados por poucos PRs enormes. A estatística t deixa de seguir a distribuição t, e o teste fica **conservador**: erro tipo I de 0,85% com assimetria extrema e 1,7% com outliers (contra 4,6% e 4,8% do Mann-Whitney), e poder muito menor.
- **O Mann-Whitney usa postos:** um PR de 3.000 h vale o mesmo que um de 100 h, então quase não sente a violação. Ele só perde poder com n pequeno (menos informação) e com σ muito alto.

## 14. Nos dados reais os testes concordaram? O efeito importa na prática?

*Mostrar: seção 6 (tabela dos dados reais).*

- **Concordaram: nenhum rejeita H₀ (α = 5%).** Welch: t = 1,375, p = 0,178. Mann-Whitney: z = 0,569, p = 0,569.
- **Tamanho do efeito:** d de Cohen = 0,36 (pequeno) no Welch; correlação rank-biserial = 0,09 (desprezível) no Mann-Whitney, ou seja, P(com bot > sem bot) ≈ 54%, quase o 50% de "nenhuma diferença".
- **Importância prática:** as medianas diferem em cerca de 5 h (7,6 h contra 2,7 h), o que pode importar no dia a dia, mas os dados não sustentam que a diferença seja real, e ela pode vir da diferença de períodos, não do bot.
- **Cuidado:** não rejeitar H₀ não prova ausência de efeito. Com n = 30 por grupo e cauda pesada, o G4 mostra poder baixo (principalmente no Welch).
