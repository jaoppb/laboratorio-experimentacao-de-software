# Avaliação da heurística de release corretiva

Releases no consenso: **150** · avaliadas: **149** · excluídas: **1**. Classe positiva: `sim`.

| Versão | Regra | Precisão | Recall | F1 | N avaliadas | N excluídas | VP | FP | FN | VN | F1 ≥ 0.70 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| v1 | v1: only the patch changes AND some commit mentions revert/hotfix/fix. | 0.627 | 0.712 | 0.667 | 149 | 1 | 37 | 22 | 15 | 75 | não |
| v1_full_message | v1_full_message: same rule as v1, but reads the full commit message (subject + body). | 0.613 | 0.731 | 0.667 | 149 | 1 | 38 | 24 | 14 | 73 | não |

## Releases excluídas

| Motivo | N |
|---|---:|
| status != ok (first_release) | 1 |

`n/d` = métrica indefinida (denominador zero).
