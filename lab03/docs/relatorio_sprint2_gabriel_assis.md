# Relatório individual — Lab03S02

**Integrante:** Gabriel Assis de Souza (@GabriAssiss)
**Sprint:** Lab03S02

## Antes de tudo: do que estamos falando?

Projetos de software no GitHub lançam **versões** de tempos em tempos (por
exemplo, a versão 2.3.0 e depois a 2.3.1). Cada versão lançada se chama
**release**. Cada mudança no código se chama **commit**.

Nesta sprint eu fiz três tarefas: guardar as releases, descobrir quais delas
foram lançadas para consertar um erro e investigar um problema nos dados.

| Tarefa | O que eu fiz, em uma frase | Terminou? |
|---|---|---|
| #58 | Guardei a lista de releases de cada projeto e os commits de cada uma | Sim |
| #59 | Criei uma regra para descobrir quais releases foram "conserto" | Sim |
| #60 | Descobri e consertei um erro que fazia faltar dados | Sim |
| #61 | Olhar releases e dizer, eu mesmo, quais são conserto | Ainda não, espera a planilha da Marcela (#63) |
| #62 | Ver quantas vezes a minha regra acerta | Ainda não, espera a #61 e a #65 |

## 1. Guardar as releases (#58)

**O problema:** o programa olhava as releases de cada projeto, fazia as contas
e jogava a lista fora. Sem a lista, ninguém conseguia olhar as releases de
novo para conferir.

**O que eu fiz:**

- Agora o programa guarda, para cada projeto, a lista de releases. Para cada
  release ele anota quais commits ela trouxe e se deu certo comparar com a
  release anterior.
- Os 330 projetos da nossa amostra já tinham sido coletados antes dessa
  mudança. Por isso criei um comando que vai lá e busca as releases deles:

  ```bash
  uv run python -m pipeline.persist_releases --config config.yaml
  ```

- Rodei o comando: deu certo nos 330 projetos, com 25.732 releases, em mais ou
  menos 12 minutos.

**Detalhe:** esses arquivos ficaram grandes demais (cerca de 320 MB) para
mandar ao GitHub, então eles não estão no repositório. Quem precisar roda o
comando acima e eles aparecem de novo.

## 2. Descobrir quais releases foram "conserto" (#59)

**A ideia:** se um projeto lança uma versão e, poucos dias depois, precisa
lançar outra só para consertar um erro, então a primeira versão "falhou".
A porcentagem de versões que falharam é o **CFR (b)**.

**A regra que eu criei.** Uma release é "conserto" quando acontecem as duas
coisas juntas:

1. só o último número da versão muda (2.3.0 → 2.3.1);
2. algum commit tem a palavra "fix", "hotfix" ou "revert" (que querem dizer
   "consertar" ou "desfazer").

Se o nome da versão não tiver esse formato de números (por exemplo,
"nightly"), a regra olha só as palavras dos commits.

**Exemplo do guia:**

- A versão 2.3.0 saiu no dia 10. A 2.3.1 saiu no dia 12, só mudou o último
  número e tem o commit "fix: crash ao abrir arquivo". Então a 2.3.0
  **falhou**.
- A versão 2.4.0 saiu no dia 1º. A próxima foi a 2.5.0, quase 20 dias depois.
  Então a 2.4.0 **não falhou**.

**Regrinhas do cálculo:**

- O conserto precisa chegar em **até 7 dias**.
- Versões lançadas nos últimos 7 dias do período ficam de fora, porque ainda
  não dá para saber se vão precisar de conserto.
- Se não deu para ver os commits da versão seguinte, a versão também fica de
  fora.

**Por que "as duas coisas juntas" e não "uma ou outra"?** Quase toda versão tem
algum commit com "fix". Se bastasse isso, quase tudo viraria conserto. Na
tarefa #62 vamos conferir se essa escolha acerta.

Escrevi **39 testes** para essa parte, e todos passam.

## 3. O erro que fazia faltar dados (#60)

**O problema:** 61 dos 330 projetos estavam sem **lead time**, que é o tempo
entre escrever o código e ele sair numa versão.

**O que eu descobri:** era um erro no programa. Ele baixava só a "linha
principal" de cada projeto. Muitos projetos lançam versões a partir de outras
linhas (por exemplo, consertos para versões antigas), e essas versões não
eram encontradas. Mais ou menos **1 em cada 5 releases** estava sendo
ignorada.

**O que eu fiz:** mudei o programa para baixar as versões de todas as linhas.

**Resultado:**

| | Antes | Depois |
|---|---:|---:|
| Releases que o programa não encontrava | 5.289 | 1 |
| Projetos sem lead time | 61 | 1 |

O único projeto que continua sem lead time (`expo/expo`) está certo assim:
quase todas as versões dele saem sem nenhum código novo.

**Outra dúvida da tarefa:** em alguns projetos, o lead time "por commit" (b)
saía maior que o lead time "por release" (a). Parecia erro, mas não é.
Acontece quando o projeto tem uma versão enorme, com centenas de commits, e
várias versões pequenas. Na conta (a), cada versão vale 1. Na conta (b), cada
commit vale 1, então a versão enorme pesa muito mais. Conferi isso em todos os
commits e em 4 projetos, um por um.

**Uma coisa para avisar no artigo:** às vezes a "versão anterior" de uma
release é de outra linha (por exemplo, a 19.0.1 é comparada com a 19.2.0).
Isso deixa a conta maior do que deveria. Mantive a regra do guia, que é igual
para a turma toda, e anotei isso como um cuidado na hora de ler os
resultados.

A explicação completa está em `docs/investigacao_lead_time.md`.

## 4. Testes

O projeto tem **186 testes, e todos passam**. As contas das métricas estão
100% testadas.

## 5. Commits

| Commit | Tarefa | O que faz |
|---|---|---|
| `0ebe021` | #59 | Regra de conserto e cálculo do CFR (b) |
| `360e3fd` | #58 | Guarda as releases e cria o comando que busca as que faltavam |
| `287ac2b` | #60 | Conserta o erro das versões que não eram encontradas |
| `533302f` | #58 | Deixa os arquivos grandes fora do GitHub e explica como gerar de novo |
| `30a551c` | #60 | Script e documento da investigação |

## 6. O que falta

- **#61:** eu mesmo preciso olhar algumas releases e dizer quais são conserto,
  **sem olhar** o que a regra diz. Isso espera a planilha da Marcela (#63).
- **#62:** depois que o grupo concordar nas respostas (#65), conferir quantas
  vezes a regra acerta. Se acertar pouco, melhoro a regra.
- **Avisar o João (#55 e #56):**
  - os números de lead time do arquivo final precisam ser calculados de novo,
    agora com o erro consertado;
  - mexi em dois arquivos dele (`git_clone.py` e o orquestrador).
- **#68:** escrever a minha parte da Metodologia do artigo usando os números
  deste relatório.
- **#69:** decidir com a Marcela quais fatores entram na RQ 06.
