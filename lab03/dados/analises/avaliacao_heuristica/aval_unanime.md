# Avaliação da heurística de release corretiva

Releases no consenso: **217** · avaliadas: **215** · excluídas: **2**. Classe positiva: `sim`.

| Versão | Regra | Precisão | Recall | F1 | N avaliadas | N excluídas | VP | FP | FN | VN | F1 ≥ 0.70 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| v1 | v1: only the patch changes AND some commit mentions revert/hotfix/fix. | 0.624 | 0.685 | 0.653 | 215 | 2 | 63 | 38 | 29 | 85 | não |
| v1_full_message | v1_full_message: same rule as v1, but reads the full commit message (subject + body). | 0.610 | 0.696 | 0.650 | 215 | 2 | 64 | 41 | 28 | 82 | não |

## Releases excluídas

| Motivo | N |
|---|---:|
| status != ok (first_release) | 2 |

`n/d` = métrica indefinida (denominador zero).
