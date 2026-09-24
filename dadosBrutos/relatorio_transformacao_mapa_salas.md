# Relatorio da Transformacao - Mapa de Salas

- Arquivo de origem: `MapaSalas.xlsx`
- Abas processadas: 23
- Registros Tidy: 454
- Colunas: 17
- Registros duplicados: 0

## Valores ausentes

- `semestre`: 0
- `predio`: 0
- `sala`: 0
- `tipo_sala`: 0
- `capacidade_turma`: 0
- `codigo_disciplina`: 0
- `turma`: 0
- `nome_disciplina`: 0
- `docente`: 0
- `curso`: 0
- `dia_semana`: 0
- `hora_inicio`: 0
- `hora_fim`: 0
- `numero_periodos`: 0
- `vagas_oferecidas`: 0
- `vagas_totais_compartilhadas`: 0
- `turmas_compartilhando_sala`: 0

## Chaves da grade sem descricao

- 302: ARQ01053-B/A
- 303: ARQ01013-C

## Regras aplicadas

- Turmas separadas por `/` receberam registros independentes.
- Vagas compartilhadas foram divididas entre as turmas; a primeira recebeu eventual resto.
- Periodos consecutivos foram consolidados em um encontro.
- Cursos separados por `/`, `;` ou `,` foram desagregados em linhas.
