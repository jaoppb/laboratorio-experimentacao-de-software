# Tabela RQ 06: Testes de Kruskal-Wallis com Correção de Holm

| Fator | Métrica DORA | k | n | H | p-valor bruto | p-valor (Holm) | ε² | Tamanho do Efeito | Rejeita H0 (Holm) |
|---|---|---:|---:|---:|---:|---:|---:|---|:---:|
| Popularidade (Estrelas) | Freq. Deploy (rel/sem) | 4 | 330 | 5.66 | 0.1295 | 1.0000 | 0.0172 | pequeno | Não |
| Popularidade (Estrelas) | Lead Time (b) (horas) | 4 | 329 | 1.84 | 0.6053 | 1.0000 | 0.0056 | desprezível | Não |
| Popularidade (Estrelas) | CFR (a) CI (%) | 4 | 330 | 3.57 | 0.3119 | 1.0000 | 0.0108 | pequeno | Não |
| Popularidade (Estrelas) | CFR (b) Entrega (%) | 4 | 328 | 2.32 | 0.5091 | 1.0000 | 0.0071 | desprezível | Não |
| Popularidade (Estrelas) | Tempo Recuperação (horas) | 4 | 312 | 0.52 | 0.9136 | 1.0000 | 0.0017 | desprezível | Não |
| Equipe (Contribuidores) | Freq. Deploy (rel/sem) | 4 | 330 | 3.50 | 0.3201 | 1.0000 | 0.0107 | pequeno | Não |
| Equipe (Contribuidores) | Lead Time (b) (horas) | 4 | 329 | 69.30 | 0.0000 | 0.0000 | 0.2113 | grande | Sim (*) |
| Equipe (Contribuidores) | CFR (a) CI (%) | 4 | 330 | 1.35 | 0.7170 | 1.0000 | 0.0041 | desprezível | Não |
| Equipe (Contribuidores) | CFR (b) Entrega (%) | 4 | 328 | 11.09 | 0.0113 | 0.1917 | 0.0339 | pequeno | Não |
| Equipe (Contribuidores) | Tempo Recuperação (horas) | 4 | 312 | 1.43 | 0.6987 | 1.0000 | 0.0046 | desprezível | Não |
| Maturidade (Idade do Projeto) | Freq. Deploy (rel/sem) | 4 | 330 | 32.81 | 0.0000 | 0.0000 | 0.0997 | médio | Sim (*) |
| Maturidade (Idade do Projeto) | Lead Time (b) (horas) | 4 | 329 | 116.04 | 0.0000 | 0.0000 | 0.3538 | grande | Sim (*) |
| Maturidade (Idade do Projeto) | CFR (a) CI (%) | 4 | 330 | 7.44 | 0.0590 | 0.7676 | 0.0226 | pequeno | Não |
| Maturidade (Idade do Projeto) | CFR (b) Entrega (%) | 4 | 328 | 60.18 | 0.0000 | 0.0000 | 0.1840 | grande | Sim (*) |
| Maturidade (Idade do Projeto) | Tempo Recuperação (horas) | 4 | 312 | 12.46 | 0.0060 | 0.1073 | 0.0401 | pequeno | Não |
| Linguagem Principal | Freq. Deploy (rel/sem) | 7 | 330 | 20.90 | 0.0019 | 0.0363 | 0.0635 | médio | Sim (*) |
| Linguagem Principal | Lead Time (b) (horas) | 7 | 329 | 32.10 | 0.0000 | 0.0003 | 0.0979 | médio | Sim (*) |
| Linguagem Principal | CFR (a) CI (%) | 7 | 330 | 15.36 | 0.0176 | 0.2818 | 0.0467 | pequeno | Não |
| Linguagem Principal | CFR (b) Entrega (%) | 7 | 328 | 14.27 | 0.0268 | 0.4021 | 0.0436 | pequeno | Não |
| Linguagem Principal | Tempo Recuperação (horas) | 7 | 312 | 12.42 | 0.0532 | 0.7453 | 0.0399 | pequeno | Não |
| Tipo de Projeto | Freq. Deploy (rel/sem) | 4 | 330 | 0.75 | 0.8626 | 1.0000 | 0.0023 | desprezível | Não |
| Tipo de Projeto | Lead Time (b) (horas) | 4 | 329 | 23.26 | 0.0000 | 0.0007 | 0.0709 | médio | Sim (*) |
| Tipo de Projeto | CFR (a) CI (%) | 4 | 330 | 0.41 | 0.9385 | 1.0000 | 0.0012 | desprezível | Não |
| Tipo de Projeto | CFR (b) Entrega (%) | 4 | 328 | 3.26 | 0.3527 | 1.0000 | 0.0100 | desprezível | Não |
| Tipo de Projeto | Tempo Recuperação (horas) | 4 | 312 | 4.88 | 0.1812 | 1.0000 | 0.0157 | pequeno | Não |