# Amostra-ouro: sorteio e conclusão do sorteio pendente (Issue #63)

**Código:** `analises/amostra_ouro.py` · **Testes:** `tests/test_amostra_ouro.py`
**Saídas:** `dados/amostra_ouro/` (`amostra_ouro_{template,marcela,gabriel,joao}.{csv,xlsx}` e `sorteio_info.json`)

## 1. Método do sorteio

1. **Repositórios.** `df.sample(n=60, random_state=42)` sobre `dados/repositorios.parquet`
   (os 330 repositórios da amostra final; o conjunto e a ordem não mudam).
2. **Releases.** Para o repositório de índice `i` (1 a 60), `df.sample(n=5, random_state=42*1000 + i)`
   sobre as releases elegíveis: publicadas na janela **2025-10-01 a 2026-09-30** (limites
   inclusivos), excluindo pré-releases (rascunhos já ficam fora da coleta). Com 5 ou menos
   releases elegíveis, entram todas. As sorteadas são ordenadas por `published_at`.
   As releases elegíveis vêm de `dados/releases/` (git-ignorado, gerado por
   `analises.persistir_amostra_ouro`).
3. **Planilhas.** Uma linha por (repositório, release sorteada): 60 × 5 = 300 linhas, em
   branco e sem nenhuma coluna da heurística (cegas). As quatro planilhas têm o mesmo conteúdo.

O sorteio não exige `previous_release`/`status` na release: o critério original é só
janela e não ser pré-release, e foi mantido para não alterar o sorteio já feito.

## 2. O problema: sorteio incompleto (30 de 60 repositórios)

A primeira geração (2026-10-15) ocorreu quando só as releases de 30 repositórios estavam
persistidas. Para os outros 30, `releases_sorteadas` ficou **vazia** em `sorteio_info.json` e
as 150 linhas correspondentes das planilhas saíram com `tag_name = "(pendente de persistência)"`,
sem data e com link genérico `.../releases`. Não havia release real para rotular, mas
`validacao/rotulos_marcela.csv` tem `release_corretiva` preenchida nessas 150 linhas
(rótulos void; ver `validacao/PROVENIENCIA.md`).

## 3. Correção: conclusão do sorteio pendente

`completar_sorteio_pendente` (CLI `--completar-pendentes`) conclui **apenas** os repositórios
pendentes, **com a mesma semente, método e janela** registrados em `sorteio_info.json`:

```bash
cd lab03 && uv sync
# 1. Com dados/releases/ contendo os 330 repositórios (persistir_amostra_ouro ou cópia local)
uv run python -m analises.amostra_ouro --completar-pendentes
```

Salvaguardas (qualquer falha aborta **sem gravar nada**, `SorteioInconsistenteError`):

* os 60 repositórios sorteados com a semente registrada coincidem com o `sorteio_info.json`;
* as releases persistidas **reproduzem exatamente** as releases já sorteadas dos 30
  repositórios não pendentes (o sorteio original nunca é alterado);
* as linhas já reais da planilha atual permanecem idênticas em conteúdo;
* todo repositório pendente tem releases persistidas na janela.

O comando é **determinístico e idempotente**: sem pendências, não reescreve arquivo algum. Os
fins de linha (CRLF) dos arquivos versionados são preservados, de modo que o diff mostra só
as linhas que mudaram. O resultado é idêntico a refazer o sorteio inteiro do zero com as
releases hoje persistidas (coberto por teste).

`sorteio_info.json` mantém `timestamp_utc` da geração original e ganha o bloco
`conclusao_sorteio_pendente` (timestamp, método, índices completados e nota de que completa o
sorteio pendente).

## 4. Impacto nos rótulos

* **Marcela:** as 150 linhas void foram rotuladas por uma execução de IA (claude-opus-5.5, `high`) e
  gravadas em `rotulos_marcela.csv`, que agora tem as 300 linhas válidas: 150 humanas de Marcela
  (inalteradas) e 150 de IA, distinguidas em `rotulos_marcela_origem.csv`. A lista das linhas antigas
  void está em `validacao/historico/marcela_linhas_invalidas.csv` (registro histórico, fora de
  `validacao/` para que a ferramenta não a use). Se Marcela vier a rotular as 150 linhas, basta
  substituí-las e marcar `origem=humano` (`docs/protocolo_consenso.md`, seção 7.3).
* **João e Gabriel:** `rotulos_joao.csv` (IA) foi adicionado e `rotulos_gabriel.csv` (IA) já existia;
  ambos usam as planilhas completas (300 linhas reais). Proveniência em `validacao/PROVENIENCIA.md`.
