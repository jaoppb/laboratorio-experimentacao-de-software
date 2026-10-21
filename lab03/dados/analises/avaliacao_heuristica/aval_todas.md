# Avaliação da heurística de release corretiva

Releases no consenso: **300** · avaliadas: **298** · excluídas: **2**. Classe positiva: `sim`.

| Versão | Regra | Precisão | Recall | F1 | N avaliadas | N excluídas | VP | FP | FN | VN | F1 ≥ 0.70 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| v1 | v1: only the patch changes AND some commit mentions revert/hotfix/fix. | 0.614 | 0.638 | 0.625 | 298 | 2 | 81 | 51 | 46 | 120 | não |
| v1_full_message | v1_full_message: same rule as v1, but reads the full commit message (subject + body). | 0.599 | 0.646 | 0.621 | 298 | 2 | 82 | 55 | 45 | 116 | não |

## Releases excluídas

| Motivo | N |
|---|---:|
| status != ok (first_release) | 2 |

`n/d` = métrica indefinida (denominador zero).
