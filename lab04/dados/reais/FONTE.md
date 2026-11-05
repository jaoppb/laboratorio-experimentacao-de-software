# Fonte dos dados reais

Arquivo: `pr_merge_time.csv` — colunas `repo, pr_number, grupo, tempo_merge_horas, url`.
60 observações: 30 PRs `com_bot` e 30 PRs `sem_bot`.

## De onde vieram

- **Repositório:** [tailwindlabs/tailwindcss](https://github.com/tailwindlabs/tailwindcss) (público, GitHub).
- **Bot de revisão:** [CodeRabbit](https://www.coderabbit.ai/) (`coderabbitai`), que passou a comentar nos PRs do repositório a partir de ~nov/2025. O Greptile (`greptile-apps`) também aparece nos mesmos PRs; ele não é usado como critério, só o CodeRabbit.
- **Data da coleta:** 2026-11-05 (via API GraphQL do GitHub, com a CLI `gh`).

## Como foi coletado

O script `scripts/coletar_prs.py` faz a coleta e é reproduzível (semente 42 no sorteio). Não foi feita anotação manual.

1. Busca os PRs **mergeados** do repositório, do mais novo para o mais antigo, até 2024-12-31.
2. Descarta PRs de rascunho (`isDraft`) e PRs cujo autor não é uma conta de usuário (Dependabot, outros bots).
3. Classifica cada PR:
   - **`sem_bot`:** criado entre 2025-01-01 e 2025-08-31 (período anterior a qualquer bot de revisão no repositório; o CodeRabbit não aparece em nenhum PR dessa janela).
   - **`com_bot`:** criado a partir de 2025-12-01 **e** com comentário ou review do `coderabbitai` publicado *antes* do merge.
4. Sorteia 30 PRs de cada grupo (`random.Random(42)`) entre os elegíveis (240 `com_bot` e 349 `sem_bot` na data da coleta).
5. `tempo_merge_horas = mergedAt − createdAt`, em horas.

## Por que este desenho

Procuramos repositórios em que PRs com e sem bot convivessem. Nos que testamos (openreplay, dotnet/aspire, home-assistant/frontend, microsoft/vscode, entre outros), ou o bot revisa quase todos os PRs, ou o time faz merge de seus próprios PRs em segundos (mediana de poucos minutos), o que mascara o efeito. No tailwindcss a adoção do bot é nítida (de 0% dos PRs até ago/2025 para ~100% desde dez/2025), e os tempos de merge são assimétricos e variados, como o cenário pede.

## Limitações conhecidas

- **Confusão temporal:** os dois grupos são de períodos diferentes (antes × depois da adoção do bot). Qualquer mudança no projeto entre os dois períodos (equipe, tipo de mudança, política de revisão) se mistura com o efeito do bot. Por isso os dados reais servem para calibrar a simulação e ilustrar os testes, não para afirmar que o bot *causa* a diferença.
- Os PRs `com_bot` incluem os que o bot de fato comentou; PRs em que ele não comentou ficam de fora.
- Amostra pequena (30 por grupo), conforme o enunciado.
