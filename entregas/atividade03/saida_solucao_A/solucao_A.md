# Solução A — preservação

- Situação: `final`. Ótimo lexicográfico provado pelo CP-SAT. Modo fallback: encontros que já violavam regras invioláveis na grade atual permanecem fixos, nenhum curso piora no uso fora do turno-alvo e a otimalidade vale para esse modelo.
- Status CP-SAT: `OPTIMAL`.
- Fonte: `mapa_salas_tidy_03.csv` (SHA-256 `5980965c9e96effa0d44f879551425e2f67f44b2c6b81cb7cc3e4fcd6a10c086`).
- Linhas/encontros físicos: 452 / 289.
- Encontros alterados: 63.
- Tempo de solução: 510.11s; limite 3000.00s.
- Valor objetivo: 1.643570602507955e+17; melhor limite: 1.643570602507955e+17.

## Preservação

| Nível | Encontros |
| ---: | ---: |
| 1 | 226 |
| 2 | 0 |
| 3 | 61 |
| 4 | 0 |
| 5 | 2 |

Nível 1 mantém sala/dia/horário; 2 mantém dia/horário com troca de sala; 3 mantém o dia; 4 muda dias sem alterar o padrão semanal; 5 representa mudança mais ampla.

Exceções de turno registradas: 1.
Violações invioláveis novas: 0.

A lista detalhada de alterações, exceções, diagnósticos e metadados do solver está em `solucao_A.json`. O CSV-fonte não foi sobrescrito.
