# Avaliação da heurística de release corretiva

Releases no consenso: **150** · avaliadas: **149** · excluídas: **1**. Classe positiva: `sim`.

| Versão | Regra | Precisão | Recall | F1 | N avaliadas | N excluídas | VP | FP | FN | VN | F1 ≥ 0.70 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| v1 | v1: only the patch changes AND some commit mentions revert/hotfix/fix. | 0.603 | 0.587 | 0.595 | 149 | 1 | 44 | 29 | 31 | 45 | não |
| v1_full_message | v1_full_message: same rule as v1, but reads the full commit message (subject + body). | 0.587 | 0.587 | 0.587 | 149 | 1 | 44 | 31 | 31 | 43 | não |

## Releases excluídas

| Motivo | N |
|---|---:|
| status != ok (first_release) | 1 |

`n/d` = métrica indefinida (denominador zero).
