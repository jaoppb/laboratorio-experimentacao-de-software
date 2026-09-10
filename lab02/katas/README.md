# Katas e testes de aceitação — Lab02 S01

Entrega do **Gabriel Assis** na Sprint 1: seleção dos katas e escrita/adaptação
dos testes automatizados de aceitação (Passo 2 do [enunciado](../docs/enunciado.md)).

## Fonte dos katas

Todos os 6 katas vêm do caderno de problemas da **XIII Maratona Mineira de
Programação (MMP 2026)**, realizada na Unifei no fim de maio de 2026. O caderno
está público no Codeforces Gym 106552.

**Por que essa fonte:** o enunciado aponta a *memorização* como ameaça à validade
— se a kata for muito conhecida (exercício clássico do LeetCode/HackerRank), o
assistente de IA reproduz uma solução já vista no treinamento em vez de
efetivamente ajudar. Um caderno de maratona regional de 2026 é o oposto disso:

- foi publicado há poucos meses, depois do corte de treinamento da maioria dos
  modelos disponíveis gratuitamente;
- circula essencialmente em um PDF no Gym, sem a enxurrada de repositórios de
  soluções, blogs e vídeos que acompanha os exercícios de plataformas de
  entrevista;
- os enunciados são autorais e com "tempero" local (Mariana, doce de leite,
  ArcelorMittal), o que reduz a chance de colisão com problemas equivalentes já
  indexados.

Os enunciados neste repositório são resumos em português escritos pelo grupo. Os
casos de teste (`tests/*.in` e `tests/*.out`) foram transcritos **literalmente**
dos exemplos oficiais do caderno.

## Os 6 katas

| # | Kata | Problema original | Técnica esperada | Testes | Par |
|---|------|-------------------|------------------|--------|-----|
| 01 | [Bario World](01-bario-world/statement.md) | B | greedy / alcance máximo em uma passada | 20 | A |
| 02 | [Cards](02-cards/statement.md) | C | fila + consulta de máximo corrente | 20 | B |
| 03 | [Exploring the Terrain](03-exploring-terrain/statement.md) | E | simulação em matriz com conflito por instante | 20 | B |
| 04 | [Garment Groups](04-garment-groups/statement.md) | G | raciocínio combinatório (código curto) | 20 | A |
| 05 | [Loading the Dish Rack](05-dish-rack/statement.md) | L | custo como fusão de blocos + construção da ordem | 20 | C |
| 06 | [N-Checkers](06-n-checkers/statement.md) | N | busca em profundidade com backtracking | 20 | C |

## Casos de teste

**20 casos por kata, 120 no total.** Ter 20 casos por kata importa para a RQ2: a
taxa de sucesso (`passed / total`) fica com granularidade de 5% em vez dos saltos
grosseiros que 2 ou 3 casos dariam.

Todos os arquivos seguem o mesmo padrão de nome — **`testNN.in` / `testNN.out`**,
`NN` de `01` a `20` — para ficar óbvio, sem depender de convenção externa, quantos
casos cada kata tem e em que ordem rodam. O que cada um cobre está documentado em
`tests/MANIFEST.md`, dentro de cada kata, e cai em três grupos:

- **Exemplos oficiais** — sempre os primeiros da numeração (`test01` em diante),
  transcritos literalmente do caderno da maratona (14 casos no total, entre 1 e 3
  por kata).
- **Bordas escritas à mão** — entrada mínima, limite superior das restrições,
  entrada impossível, conflito total entre as duas perfuratrizes, cascata de
  eliminações, captura sem continuação, tabuleiro sem captura possível, e assim
  por diante.
- **Aleatórios e um caso de desempenho** — entradas com tamanhos e densidades
  variadas para cobrir combinações que ninguém pensaria em escrever à mão; os
  katas 01, 02 e 03 fecham com um caso grande o bastante para reprovar uma
  solução de complexidade errada (por exemplo, quadrática onde a restrição pede
  linear).

### Como as saídas esperadas foram validadas

As saídas dos casos que não são exemplo oficial vêm dos gabaritos, então a suíte
inteira depende de eles estarem certos. A validação foi feita em duas camadas:

1. **Stress test contra força bruta independente.** Para cada kata foi escrita
   uma segunda implementação, ingênua e independente (BFS sobre estados para o
   Bario World, simulação `O(N²)` para o Cards, varredura célula a célula para o
   Exploring the Terrain, enumeração de composições para o Garment Groups, DP
   exaustiva sobre máscaras de ocupação para o Dish Rack, busca no espaço de
   estados para o N-Checkers). Os dois lados foram comparados em milhares de
   entradas pequenas aleatórias — e, no caso do Dish Rack, em **todos** os pares
   `(N, C)` com N de 2 a 14.
2. **Conferência caso a caso.** 93 dos 120 casos gerados foram reconferidos
   diretamente com a força bruta; os 27 restantes são grandes demais para ela e
   se apoiam nos gabaritos já validados na camada anterior.

Isso não foi zelo excessivo: o primeiro caso de borda do Bario World **revelou um
bug real na solução de referência** — ela contava um pulo a mais quando o trecho
final da fase é todo sólido, situação em que Bario apenas corre até o fim. Os
exemplos oficiais não pegavam isso, e o bug teria sido assado em 20 casos de
teste de uma vez.

### Por que 6 e não 4

O enunciado permite as duas opções. Com 6 katas cada integrante gera 3 trials com
IA e 3 sem, o que dá 9 pares para o teste de Wilcoxon no grupo todo (contra 6, se
fossem 4 katas). O N continua pequeno, mas é a diferença entre um teste pareado
com alguma chance de detectar efeito e um praticamente incapaz disso.

### Pareamento por dificuldade

Os 6 katas **não** têm dificuldade idêntica — em um caderno de maratona a
variação é grande por construção. Em vez de fingir uniformidade, eles foram
agrupados em **3 pares de dificuldade e natureza semelhantes**:

- **Par A — Bario World ↔ Garment Groups:** código curto, a dificuldade está em
  enxergar a regra certa (o modelo de carga das botas; a invariante dos grupos).
- **Par B — Cards ↔ Exploring the Terrain:** simulação de tamanho médio, sem
  sacada algorítmica, com bastante contabilidade de estado para errar.
- **Par C — Dish Rack ↔ N-Checkers:** os dois mais pesados, exigindo construção
  de solução (ordem ótima de inserção) ou busca com backtracking.

**Como isso entra no desenho do experimento:** dentro de cada par, cada
integrante resolve um kata **com** IA e o outro **sem**, contrabalanceado entre
os integrantes. Assim toda comparação IA vs. manual é feita entre katas de
dificuldade equivalente, e a diferença de peso entre os pares deixa de
contaminar o resultado. Isso precisa ser refletido na matriz de alocação do
desenho do experimento (Passo 1).

### Katas descartados

- **A (Ana, Hooray for Mariana!) e D (Dubious Dates):** triviais (fórmula
  aritmética / sequência de condicionais). Todo mundo terminaria em poucos
  minutos com ou sem IA — efeito de piso, sem sinal para a RQ1.
- **F, H, I, J, K, M, O:** exigem técnicas pesadas (fluxo máximo/corte mínimo,
  decomposição em árvore, teoria dos números, contagem com módulo, geometria
  computacional, árvore de Fenwick com composição de funções afins). Com
  time-box de 35 minutos e sujeitos de graduação, quase todos os trials seriam
  censurados nos 35 min — o que mata a RQ1 (sem tempo até o verde para comparar)
  e deixa a RQ2 no chão em ambos os tratamentos.

## Formato dos testes

Todos os katas usam **stdin/stdout**, sem dependência de linguagem: a solução lê
da entrada padrão e escreve na saída padrão. Isso mantém a escolha de linguagem
(tarefa do João Pedro, que precisa casar com a ferramenta de métricas estáticas)
independente da suíte de testes.

```
<kata>/
├── statement.md      # enunciado em português
├── tests/
│   ├── test01.in      # entrada do caso 1 (sempre um exemplo oficial)
│   ├── test01.out     # saída esperada
│   ├── ...
│   ├── test20.in
│   ├── test20.out
│   └── MANIFEST.md    # o que cada test01..test20 cobre
└── checker.py         # só no kata 05, que aceita mais de uma resposta válida
```

## Como rodar

```bash
python3 common/run_tests.py 01-bario-world -- python3 solution.py
python3 common/run_tests.py 06-n-checkers  -- java -cp out Main
python3 common/run_tests.py 05-dish-rack   -- ./a.out
```

Opções (todas antes do `--`): `--timeout SEGUNDOS`, `--quiet`, `--json ARQUIVO`.

### Interface com os outros scripts da S01

- **Script de cronometragem (Marcela) — RQ1:** o runner sai com **código 0 se e
  somente se todos os testes passam**. É esse o sinal de *time-to-green*: basta
  reexecutá-lo em laço e cronometrar até o exit code 0, respeitando o corte de
  35 min (trial censurado, não descartado).
- **Coleta de defeitos — RQ2:** `--json arquivo.json` grava
  `{"kata", "passed", "total", "tests": [...]}`. A taxa de sucesso da RQ2 é
  `passed / total` ao fim do time-box; o número absoluto de testes falhando é
  `total - passed`.
- **Métricas estáticas (João Pedro) — RQ3:** rodam sobre o arquivo de solução do
  trial, que é independente desta suíte.

### Verificação da suíte

Os 6 gabaritos em [`gabaritos/`](gabaritos/README.md) passam nos 120 casos —
é a evidência de que a transcrição dos exemplos oficiais e o runner estão
corretos. Leia o aviso de ameaça à validade nesse README antes da S02: os
trials precisam rodar em diretório isolado, sem os gabaritos visíveis para o
assistente de IA.

Dois scripts em `common/` deixam a suíte reproduzível:

```bash
python3 common/stress_test.py     # compara gabaritos vs. forca bruta independente
python3 common/gerar_casos.py     # regenera os 120 casos (deterministico, com seed fixa)
```

O `gerar_casos.py` é idempotente: rodá-lo de novo reproduz byte a byte os mesmos
casos, porque todas as entradas aleatórias usam seeds fixas. Os exemplos oficiais
(sempre `test01` em diante, antes dos casos gerados) nunca são recalculados —
o script lê o que já está em `tests/` a partir do `MANIFEST.md` e preserva esse
conteúdo exatamente como veio do caderno.
