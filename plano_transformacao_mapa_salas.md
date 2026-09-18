# Plano de Transformação: Mapa de Salas

## Objetivo

Transformar `MapaSalas.xlsx` em `mapa_salas_tidy.csv`, um conjunto de dados para análise de ocupação de salas, turmas, disciplinas e cursos no período letivo 2026/2.

## Unidade de análise

Cada linha do CSV representa um encontro de uma turma de um curso em uma sala, dia da semana e intervalo contínuo de horários.

## Regras de transformação

1. Cada aba do Excel é uma sala. O nome da sala e o período letivo são lidos do cabeçalho da própria aba.
2. A grade semanal é convertida para registros usando o dia da semana da coluna e o horário da linha.
3. Identificadores como `ARQ01045 - A/B` são separados em duas turmas: `A` e `B`.
4. As vagas de turmas compartilhadas são divididas igualmente. Quando o total for ímpar, a primeira turma recebe a vaga restante.
5. Períodos consecutivos da mesma turma, sala e dia são consolidados em um único encontro, com hora inicial, hora final e número de períodos.
6. Turmas que atendem vários cursos são separadas em uma linha por curso, preservando um único CSV para análises por curso.
7. A tabela descritiva da parte inferior da aba fornece nome da disciplina, cursos e vagas; ela é associada à grade pelo campo `Sigla Turma`.

## Saídas

- `mapa_salas_tidy.csv`: dados normalizados em UTF-8 com BOM.
- `relatorio_transformacao_mapa_salas.md`: resumo das abas, registros, exceções de junção e validações.

## Colunas do CSV

`semestre`, `predio`, `sala`, `codigo_disciplina`, `turma`, `nome_disciplina`, `curso`, `dia_semana`, `hora_inicio`, `hora_fim`, `numero_periodos`, `vagas_oferecidas`, `vagas_totais_compartilhadas`, `turmas_compartilhando_sala`.

Para medir ocupação física, deve-se deduplicar encontros que diferem apenas em `curso`.