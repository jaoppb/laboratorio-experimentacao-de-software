# Gabaritos — NÃO ABRIR DURANTE OS TRIALS DA S02

Soluções de referência dos 6 katas, em Python. Elas existem por dois motivos:

1. **Validar a infraestrutura de testes.** Todos os 6 gabaritos passam em 100%
   dos testes de aceitação — é assim que sabemos que os arquivos `tests/*.in` e
   `tests/*.out` foram transcritos corretamente do caderno oficial e que o
   `common/run_tests.py` e o `05-dish-rack/checker.py` funcionam.
2. **Gerar casos de teste extras**, se o grupo decidir ampliar a suíte além dos
   exemplos oficiais.

## Ameaça à validade

Estes arquivos estão versionados no mesmo repositório em que os trials da S02
vão acontecer. Se o assistente de IA tiver acesso ao repositório durante um
trial, ele pode simplesmente ler o gabarito — o que destruiria a medição
(o trial mediria "copiar arquivo", não "resolver kata").

**Mitigação obrigatória:** cada trial da S02 deve rodar em um diretório de
trabalho isolado, contendo apenas o `statement.md` do kata e a pasta `tests/`
(mais o `checker.py`, no caso do kata 05). Nem os gabaritos nem os outros katas
podem estar visíveis para o assistente durante o trial.

## Como rodar

```bash
python3 ../common/run_tests.py ../01-bario-world -- python3 01-bario-world.py
```
