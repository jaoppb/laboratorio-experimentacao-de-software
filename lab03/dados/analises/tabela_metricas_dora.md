# Tabela Descritiva: Métricas DORA (RQ 01 a RQ 04)

| Métrica | Dimensão | Unidade | n | Mediana | Q1 | Q3 | IQR | Min | Max |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Frequência de Deploy (RQ 01) | deployment_frequency | rel/sem | 330 | 0.499 | 0.235 | 1.204 | 0.969 | 0.096 | 49.597 |
| Lead Time (a) por Release (RQ 02) | lead_time_a_hours | horas | 269 | 165.875 | 41.386 | 454.722 | 413.336 | 0.008 | 78858.697 |
| Lead Time (b) por Commit (RQ 02) | lead_time_b_hours | horas | 269 | 145.572 | 44.676 | 356.641 | 311.964 | 0.008 | 62894.492 |
| CFR (a) Proxy de CI (RQ 03) | cfr_a | proporção | 330 | 0.047 | 0.024 | 0.112 | 0.088 | 0.000 | 1.000 |
| CFR (b) Proxy de Entrega (RQ 03) | cfr_b | proporção | 328 | 0.186 | 0.038 | 0.407 | 0.369 | 0.000 | 0.980 |
| Tempo de Recuperação (RQ 04) | recovery_hours | horas | 312 | 2.611 | 1.067 | 6.733 | 5.666 | 0.065 | 560.001 |
| Taxa de Censura de Falhas (RQ 04) | censored_episodes_ratio | proporção | 330 | 0.000 | 0.000 | 0.014 | 0.014 | 0.000 | 1.000 |