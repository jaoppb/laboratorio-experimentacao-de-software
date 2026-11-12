# Apresentação oral — respostas da Marcela (perguntas 8, 9, 10, 13 e 15)

Respostas curtas (~30 s cada), apoiadas no dashboard. Os números vêm de
`dados/simulado/*.csv` e `dados/reais/resultado_testes.json` (semente 42).

> Nota: a Issue #141 lista as perguntas como 8–12, mas a numeração do
> enunciado (seção 5) para esses temas é **8, 9, 10, 13 e 15**.

## 8. Erro tipo I e tipo II no cenário; qual é mais grave

*Mostrar: seção 1 (hipóteses) e seção 4.*

- **Erro tipo I:** concluir que o bot de revisão muda o tempo até o merge quando, na verdade, não muda (falso alarme).
- **Erro tipo II:** não perceber uma mudança real (o bot realmente acelera ou atrasa o merge e o teste não detecta).
- **Mais grave:** depende da decisão. Se o time adotaria (ou pagaria) o bot com base no resultado, o tipo I é pior: investe numa ferramenta que não faz diferença. Se a intenção é só monitorar um possível atraso, o tipo II é pior. Como o estudo é observacional e exploratório, tratamos o tipo I como mais grave, e por isso controlamos o α em 5%. O G4 mostra que o tipo II é um risco real aqui (o Welch tem poder baixíssimo).

## 9. G3: algum teste se afastou de 5%? Liberal ou conservador?

*Mostrar: G3 (seção 4).*

- O **Mann-Whitney** ficou entre 4,3% e 4,8% em todas as situações: perto de 5%.
- O **Welch** se afastou, sempre para baixo, ou seja, **conservador**: 3,7% na referência (n=30, σ=1), 2,7% com n=10, 1,7% com outliers, 1,2% e 0,7% nos parâmetros reais (σ_log = 2,5 e 3,2) e 0,85% com assimetria extrema (σ=3).
- **Por quê:** o Welch compara médias. Com cauda pesada, poucos PRs enormes dominam a média e o desvio-padrão, a estatística t não segue mais a distribuição t, e raramente passa do valor crítico. Ele nunca foi liberal: o problema não é aceitar falsos efeitos, é quase não rejeitar.

## 10. G4: qual teste tem mais poder? A diferença muda com o tamanho do efeito?

*Mostrar: G4 (seção 5).*

- **O Mann-Whitney tem mais poder em todas as situações simuladas**; o Welch nunca o superou.
- **A diferença muda com o efeito:** com efeito pequeno os dois são baixos e próximos; ela cresce no meio da curva (referência, razão 2,0: 72% contra 55%) e some quando ambos saturam perto de 100% (razão ≥ 6 na referência).
- Nos parâmetros reais (cauda pesada) a distância é enorme: razão 4,0, com_bot, 35% contra 3,4%; razão 8,0, 66% contra 6,8%. Com assimetria extrema, o Welch fica próximo do erro tipo I mesmo com efeito grande.

## 13. A simulação confirmou o que o grupo esperava?

*Mostrar: seção 7 (expectativa × resultado) e `docs/cenario.md`.*

- **Esperávamos** (antes de simular, registrado em `docs/cenario.md`): Mann-Whitney perto de 5% e com mais poder; Welch com pouco poder e provavelmente conservador.
- **Confirmou**: Mann-Whitney perto de 5% e com maior poder; Welch conservador e fraco.
- **Surpresa/ressalva:** o Welch já era um pouco conservador (3,7%) na situação de referência, que não é patológica, e o Welch nunca ganhou, nem com n pequeno, que era a ressalva que tínhamos feito.

## 15. Qual teste recomendam, quando mudariam e qual a principal limitação?

*Mostrar: seção 7.*

- **Recomendação:** Mann-Whitney para o tempo até o merge: dados lognormais de cauda pesada (σ_log de 2,5 a 3,2), onde ele mantém o erro tipo I em ~5% e detecta muito mais.
- **Quando mudaria:** se a pergunta fosse mesmo sobre **diferença de médias** (custo total em horas, por exemplo), ou se os dados fossem aproximadamente simétricos e sem outliers (situação que não simulamos, então não sabemos o quanto o Welch se aproximaria; mesmo na referência o Mann-Whitney tem mais poder, 72% contra 55% na razão 2,0). Lembrar que o Mann-Whitney testa dominância estocástica, não medianas.
- **Principal limitação:** os dados reais são de períodos diferentes (antes × depois do bot), então o efeito está confundido com o tempo, e a simulação usa só uma família (lognormal) com contaminação simétrica nos dois grupos. Nos dados reais, nenhum teste rejeitou H₀ (p = 0,178 e p = 0,569) com n = 30 por grupo, o que não prova ausência de efeito.
