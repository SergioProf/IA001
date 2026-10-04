# Validacao independente das propostas A, B e C

- Fonte: `mapa_salas_tidy_03.csv` (SHA-256 `5980965c9e96effa0d44f879551425e2f67f44b2c6b81cb7cc3e4fcd6a10c086`).
- Linhas da fonte: 452; encontros fisicos: 289.
- Validacao executada sobre CSVs exportados; nenhum estado interno do solver e lido.
- A carga por etapa contabiliza todas as ofertas/turmas da etapa, nao uma matricula individual.

## Resultado

| Proposta | Estado do artefato | Encontros | Alterados | Duras baseline | Duras novas | Excecoes turno | Resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| ANTES | fonte | 289 | 0 | 64 | 0 | 61 | OK |
| A | exportada | 289 | 63 | 3 | 0 | 1 | OK |
| B | FEASIBLE nao otima | 289 | 178 | 3 | 0 | 93 | OK |
| C | exportada | 289 | 68 | 3 | 0 | 1 | OK |

## Violacoes baseline

- H003: 1
- H008: 2
- H010: 61

## Notas

- `OK` significa zero violacoes duras novas; as violacoes baseline sao reportadas separadamente.
- B continua identificada como viavel, mas sem prova de otimalidade.
- As regras sao aplicadas a dados reconstruidos da fonte e dos CSVs exportados; variaveis e objetos do CP-SAT nao sao lidos.
