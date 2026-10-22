# Avaliação da heurística de release corretiva

Releases no consenso: **150** · avaliadas: **149** · excluídas: **1**. Classe positiva: `sim`.

| Versão | Regra | Precisão | Recall | F1 | N avaliadas | N excluídas | VP | FP | FN | VN | F1 ≥ 0.70 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| v1 | v1: only the patch changes AND some commit mentions revert/hotfix/fix. | 0.441 | 0.433 | 0.437 | 149 | 1 | 26 | 33 | 34 | 56 | não |
| v1_full_message | v1_full_message: same rule as v1, but reads the full commit message (subject + body). | 0.435 | 0.450 | 0.443 | 149 | 1 | 27 | 35 | 33 | 54 | não |

## Releases excluídas

| Motivo | N |
|---|---:|
| status != ok (first_release) | 1 |

`n/d` = métrica indefinida (denominador zero).
