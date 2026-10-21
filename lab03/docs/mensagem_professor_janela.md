# Rascunho de mensagem ao professor: confirmação da janela de observação

> **Rascunho. Nada foi enviado.** Cabe ao grupo revisar, ajustar o tom e escolher o canal
> (e-mail ou o canal da disciplina). Contexto e números: `docs/impacto_limitacoes_conhecidas.md`, seção 2.

**Assunto:** Lab03 (grupo Gabriel, João e Marcela): confirmação da janela de observação

---

Professor Danilo,

Boa noite. Estamos fechando a coleta do Lab03 e queremos confirmar a janela de observação oficial, porque o guia diz que as datas são fixadas pelo senhor na abertura da Lab03S01 e não encontramos o registro delas.

Hoje usamos **01/10/2025 a 30/09/2026** (12 meses). Pedimos duas confirmações:

1. **Essas são as datas oficiais?** Se o senhor definiu outras (ou o mesmo intervalo com outra data final), nos diga quais.
2. **A data final é inclusiva?** Isto é, entram releases e workflow runs de todo o dia 30/09/2026 (até 23:59:59), ou só até o início desse dia?

O motivo da segunda pergunta: no nosso pipeline a data `2026-09-30` é lida como `2026-09-30 00:00 UTC`. Na prática a janela termina no início do dia 30/09, tem 364 dias (e não 365) e deixa de fora o último dia. Se a janela oficial for "01/10/2025 até o fim de 30/09/2026", precisaremos coletar de novo esse último dia. Se for "até 30/09/2026 00:00", mantemos como está e só registramos a regra no artigo.

Se possível, confirme também o **fuso horário** de referência (usamos UTC, que é o que a API do GitHub devolve).

Com a resposta, registramos a regra na seção de Metodologia e, se necessário, atualizamos a coleta antes da entrega.

Obrigado,
Gabriel Assis de Souza, João Pedro Peres e Marcela Mendes Campos
