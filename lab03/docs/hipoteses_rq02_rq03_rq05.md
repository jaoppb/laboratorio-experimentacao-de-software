# Hipóteses informais — RQ 02, RQ 03 e RQ 05

> Rascunho da Issue #44 para a seção de Introdução do artigo (Overleaf).
> Escrito **antes** de qualquer coleta ou análise dos dados, como exige o guia.

## RQ 02 — Qual o tempo entre um commit e seu respectivo deploy?

**Hipótese.** Esperamos lead times longos para os padrões DORA: a mediana por
commit (variante b) deve ficar na faixa **Medium** (entre 1 semana e 30 dias), e
a mediana por release (variante a) deve ser bem maior que a (b), chegando com
frequência à faixa **Low** (≥ 30 dias).

**Por quê.** Projetos open-source populares acumulam mudanças no default branch
e publicam releases em ciclos (semanais, mensais ou por *milestone*), e não a
cada merge. Assim, um commit típico espera parte do ciclo até ser entregue. A
variante (a) mede o commit **mais antigo** de cada release: basta um commit
"esquecido" ou um *backport* para inflar o valor. Por isso esperamos que a
diferença entre (a) e (b) seja grande e que a (a) tenha IQR mais largo. Também
esperamos que *squash merges* e rebases, que reescrevem `commit.author.date`,
distorçam os valores em alguns repositórios (ameaça à validade de construto).

## RQ 03 — Qual a taxa de falha das mudanças entregues?

**Hipótese.** Esperamos que as duas variantes discordem:

- **(a) proxy de CI:** CFR mediano entre **15% e 30%** (faixa **High**), com
  alguns repositórios bem acima de 45%, puxados por *workflows* instáveis
  (*flaky tests*) ou dependências externas.
- **(b) proxy de entrega:** CFR mediano **abaixo de 15%** (faixa **Elite**),
  porque poucas releases são seguidas por uma release corretiva em até 7 dias.

**Por quê.** A variante (a) conta falhas de pipeline, que são frequentes e
geralmente corrigidas antes de chegar ao usuário, e não falhas em produção. Já a
variante (b) só detecta falhas que motivaram uma nova release às pressas, o que
é raro em projetos com bom CI. Esperamos ainda baixa correlação entre (a) e (b)
no mesmo repositório, o que reforça que os dois proxies medem coisas diferentes.

## RQ 05 — Repositórios com maior frequência de deploy têm maior ou menor taxa de falha?

**Hipótese.** Esperamos **ausência de *trade-off***: correlação de Spearman
**fraca e negativa ou próxima de zero** entre deployment frequency e CFR (b), em
linha com a afirmação do DORA. Para o CFR (a), esperamos correlação **fraca e
positiva**.

**Por quê.** Projetos que publicam com frequência tendem a ter automação
madura (testes, *release* automatizada), o que reduz falhas que exigem release
corretiva. Por outro lado, projetos muito ativos executam muito mais *workflows*
e mais variados, o que aumenta a chance de falhas de pipeline, sem que isso
signifique pior qualidade da entrega. Há ainda um viés no CFR (b): quem publica
muitas releases tem mais chance de ter duas releases separadas por menos de 7
dias, o que pode inflar artificialmente o CFR (b) e gerar uma correlação
positiva espúria. Em qualquer caso, correlação não implica causalidade.
