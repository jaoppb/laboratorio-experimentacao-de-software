# Cenário

## Pergunta

O tempo até o merge de um PR é diferente quando o PR é revisado por um bot de revisão (CodeRabbit) do que quando não é?

## Hipóteses

- **H₀:** o tempo até o merge tem a mesma distribuição nos dois grupos (com e sem bot). Para o t de Welch, isso significa médias iguais (μ_com = μ_sem); para o Mann-Whitney, que nenhum grupo tende a ter tempos maiores que o outro (P(X_com > X_sem) = 0,5).
- **H₁:** os tempos diferem entre os grupos (μ_com ≠ μ_sem no Welch; P(X_com > X_sem) ≠ 0,5 no Mann-Whitney).

**Teste bicaudal.** Não há razão forte para prever o sentido: o bot pode acelerar o merge (feedback imediato, menos idas e vindas) ou atrasá-lo (mais comentários a resolver antes de aprovar). Um teste unicaudal só seria justificável com uma direção definida antes de ver os dados, e escolher o sentido depois de olhar a amostra inflaria o erro tipo I. A pergunta é "mudou?", não "melhorou?".

## Dados reais

Tempo até o merge (horas) de 30 PRs com bot e 30 sem bot do `tailwindlabs/tailwindcss` (detalhes em `dados/reais/FONTE.md`). Os dois grupos são de períodos diferentes (antes × depois da adoção do CodeRabbit), então a comparação é observacional e confundida pelo tempo.

## Distribuição da simulação: lognormal

Os dados reais são fortemente assimétricos à direita (a maioria dos PRs é mergeada em poucas horas, mas alguns levam semanas ou meses). Por isso cada grupo é simulado como **lognormal**, parametrizada pela **mediana** (= e^μ) e por **σ_log** (desvio-padrão do logaritmo do tempo). Os valores vêm de `scripts/estimar_parametros.py` e ficam em `dados/parametros.json`:

| Grupo | n | Mediana (h) | σ_log |
|---|---|---|---|
| com_bot | 30 | 7,60 | 3,22 |
| sem_bot | 30 | 2,73 | 2,50 |

Escolhemos a mediana (e não a média) porque a média real é puxada por poucos PRs muito longos (média de 301 h contra mediana de 7,6 h no grupo com bot). O σ_log alto (2,5 a 3,2) é um achado dos dados, não um acaso: a cauda é muito pesada. Sob H₀ da simulação, os dois grupos usam os mesmos parâmetros; sob H₁, só a mediana de um grupo é multiplicada por um fator.

## Expectativa antes de simular

> Registrada antes de rodar qualquer simulação.

**Esperamos que o Mann-Whitney se saia melhor que o t de Welch**, principalmente no poder.

Por quê:

1. Com σ_log em torno de 2,5 a 3, a lognormal tem cauda pesada: a média amostral é dominada por um ou dois PRs extremos, e o desvio-padrão também. O erro-padrão do Welch fica enorme e instável, então a estatística t perde sensibilidade para diferenças reais de localização. Esperamos **pouco poder do Welch**.
2. O Mann-Whitney usa postos, que não sofrem com valores extremos; um PR de 3.000 h vale o mesmo que um de 100 h. Esperamos **mais poder** nele.
3. Sobre o erro tipo I sem efeito: esperamos o Mann-Whitney perto de 5%. Para o Welch, esperamos desvio de 5% (provavelmente **conservador**, pois a distribuição da média é muito assimétrica com n = 30 e a aproximação pela t é ruim), mas sem apostar na direção.
4. Ressalva: com n pequeno e σ alto, o Welch pode até parecer "melhor" em algum cenário específico; por isso o lab simula também amostras menores e outras situações. O Mann-Whitney responde a uma pergunta diferente (dominância estocástica, não diferença de médias), o que também importa na recomendação final.
