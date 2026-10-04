# Baseline da grade atual — Atividade 03

Os apontamentos descrevem o ANTES; não são violações introduzidas por uma solução.

SHA-256 do CSV-fonte: `6101ab290feb8feee0cb7714692ef6aa8c67f647bf0bb970f92bf09a2f3ab5e0`.

## Regras de contagem

- Cada encontro físico canônico é contado uma vez; linhas repetidas por curso, membro ou docente não multiplicam a ocupação.
- Manhã: antes de 12:30; tarde: 13:30–18:30; noite: a partir de 18:30. Almoço (12:30–13:30) não pertence a turno.
- CH de turno é a duração em horas da interseção do encontro com cada janela. Encontros que cruzam limites são repartidos; almoço fica fora dos turnos.
- O percentual-alvo divide horas de turno-alvo pela soma de `numero_periodos` uma vez por encontro e curso. Diferenças entre relógio e períodos não são redistribuídas.
- Capacidade soma `vagas_oferecidas` por membro físico único (`turma`); compara também `vagas_turma` e `vagas_totais_compartilhadas`, sem somar cópias de linhas.
- Conflito de etapa inclui somente ARQU/DPRO/DVIS e etapa diferente de 0. Etapa 0 continua sujeita a conflitos de sala e docente.
- Cargas semanais são períodos por encontro, deduplicados. Conflitos também incluem cursos externos registrados.

## Inventário

| Métrica | Quantidade |
| --- | ---: |
| Linhas-fonte | 452 |
| Cursos | 5 |
| Etapas por curso | 32 |
| Disciplinas por curso | 158 |
| Grupos acadêmicos | 278 |
| Padrões semanais | 184 |
| Encontros físicos | 289 |
| Salas | 23 |
| Horários distintos | 92 |
| Docentes | 127 |
| Duplicatas exatas | 0 |

Cursos encontrados: ARQU, CAGR, DPRO, DVIS, ENGMEC.

## Turnos e capacidade

| Curso | Turno-alvo | CH no alvo (h) | CH em períodos | CH no alvo (%) |
| --- | --- | ---: | ---: | ---: |
| ARQU | Manhã, Noite | 447.00 | 550 | 81.27% |
| CAGR | N/A | 0.00 | 6 | 0.00% |
| DPRO | Noite, Tarde | 131.00 | 183 | 71.58% |
| DVIS | Noite, Tarde | 137.00 | 174 | 78.74% |
| ENGMEC | N/A | 0.00 | 4 | 0.00% |

Encontros acima de 110% da capacidade: 46; maior ocupação: 308.33%.
Divergências nos campos de vagas por tipo: {'vagas_oferecidas_vs_vagas_turma': 277}.
`vagas_oferecidas` foi comparada a `vagas_totais_compartilhadas`; `vagas_turma` foi comparada separadamente, sem presumir equivalência.

### Encontros por tipo de espaço

| Tipo | Encontros físicos |
| --- | ---: |
| Atelier | 148 |
| Laboratório de Informática | 43 |
| Sala de aula | 98 |

### Encontros acima de 110% da capacidade

| Disciplina | Grupo | Curso | Dia | Horário | Sala | Alunos | Capacidade | Ocupação |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| ARQ03139 | A | DPRO, DVIS | QUINTA-FEIRA | 15:30–17:30 | Sala 404 | 25 | 12 | 208.33% |
| ARQ03098 | B | DPRO, DVIS | TERÇA-FEIRA | 13:30–15:30 | Sala 404 | 22 | 12 | 183.33% |
| ARQ01044 | A/B/C/D | ARQU | QUINTA-FEIRA | 13:30–16:30 | Sala 304 | 70 | 48 | 145.83% |
| ARQ01044 | A/B/C/D | ARQU | QUINTA-FEIRA | 09:30–12:30 | Sala 304 | 70 | 48 | 145.83% |
| ENG02016 | U | ARQU | TERÇA-FEIRA | 14:30–18:30 | Sala 414 | 26 | 12 | 216.67% |
| ARQ02003 | B | ARQU | TERÇA-FEIRA | 09:30–12:30 | Sala 403 | 17 | 12 | 141.67% |
| ARQ02005 | A | ARQU | SEGUNDA-FEIRA | 09:30–13:30 | Sala 413 | 55 | 48 | 114.58% |
| ARQ01011 | B | ARQU | TERÇA-FEIRA | 18:30–22:30 | Sala 404 | 16 | 12 | 133.33% |
| ENG01169 | A | ARQU | SEXTA-FEIRA | 07:30–09:30 | Sala 405 | 37 | 12 | 308.33% |
| ARQ01084 | U | ARQU | SEGUNDA-FEIRA | 13:30–17:30 | Sala 403 | 15 | 12 | 125.00% |
| AGR06014 | B | ARQU | QUINTA-FEIRA | 13:30–16:30 | Sala 405 | 16 | 12 | 133.33% |
| ARQ01007 | D | ARQU | SEXTA-FEIRA | 09:30–12:30 | Sala 404 | 15 | 12 | 125.00% |
| ARQ01044 | A/B/C/D | ARQU | TERÇA-FEIRA | 09:30–12:30 | Sala 304 | 70 | 48 | 145.83% |
| ARQ01008 | D/B | ARQU | SEGUNDA-FEIRA | 18:30–22:30 | Sala 405 | 30 | 12 | 250.00% |
| ARQ03098 | A | DPRO, DVIS | TERÇA-FEIRA | 13:30–15:30 | Sala 403 | 22 | 12 | 183.33% |
| ENG02042 | B | ARQU | SEGUNDA-FEIRA | 13:30–17:30 | Sala 414 | 17 | 12 | 141.67% |
| ARQ01013 | A | ARQU | QUINTA-FEIRA | 16:30–19:30 | Sala 403 | 15 | 12 | 125.00% |
| ARQ03139 | A | DPRO, DVIS | TERÇA-FEIRA | 15:30–17:30 | Sala 404 | 25 | 12 | 208.33% |
| ARQ01049 | A | ARQU | SEGUNDA-FEIRA | 09:30–12:30 | Sala 407 | 15 | 10 | 150.00% |
| ARQ01008 | A | ARQU | QUARTA-FEIRA | 09:30–12:30 | Sala 403 | 15 | 12 | 125.00% |
| ENG03019 | C | DPRO | TERÇA-FEIRA | 09:30–12:30 | Sala 414 | 15 | 12 | 125.00% |
| ARQ01013 | A | ARQU | TERÇA-FEIRA | 18:30–22:30 | Sala 403 | 15 | 12 | 125.00% |
| ENG01169 | A | ARQU | QUARTA-FEIRA | 07:30–09:30 | Sala 405 | 37 | 12 | 308.33% |
| ARQ01013 | A | ARQU | SEGUNDA-FEIRA | 09:30–12:30 | Sala 403 | 15 | 12 | 125.00% |
| ARQ01008 | D/B | ARQU | QUARTA-FEIRA | 09:30–12:30 | Sala 405 | 30 | 12 | 250.00% |
| ARQ01011 | B | ARQU | SEGUNDA-FEIRA | 09:30–12:30 | Sala 404 | 16 | 12 | 133.33% |
| ARQ01007 | D | ARQU | SEGUNDA-FEIRA | 18:30–22:30 | Sala 404 | 15 | 12 | 125.00% |
| DIR03017 | U | ARQU | TERÇA-FEIRA | 18:30–22:30 | Sala 407 | 16 | 10 | 160.00% |
| ARQ01020 | A/B/C | ARQU | SEGUNDA-FEIRA | 09:30–12:30 | Sala 503 | 45 | 38 | 118.42% |
| ARQ01020 | A/B/C | ARQU | QUINTA-FEIRA | 09:30–12:30 | Sala 503 | 45 | 38 | 118.42% |
| ARQ02213 | A/B | ARQU | QUARTA-FEIRA | 08:30–12:30 | Sala 503 | 44 | 38 | 115.79% |
| ARQ03098 | B | DPRO, DVIS | QUINTA-FEIRA | 13:30–15:30 | Sala 404 | 22 | 12 | 183.33% |
| ARQ03085 | A | DPRO, DVIS | QUARTA-FEIRA | 13:30–17:30 | Sala 404 | 35 | 12 | 291.67% |
| ARQ02004 | C | ARQU | TERÇA-FEIRA | 08:30–12:30 | Sala 404 | 15 | 12 | 125.00% |
| ARQ03064 | A | DPRO, DVIS | TERÇA-FEIRA | 10:30–12:30 | Sala 503 | 44 | 38 | 115.79% |
| ARQ01049 | A | ARQU | SEXTA-FEIRA | 09:30–12:30 | Sala 407 | 15 | 10 | 150.00% |
| ARQ03098 | A | DPRO, DVIS | QUINTA-FEIRA | 13:30–15:30 | Sala 403 | 22 | 12 | 183.33% |
| ARQ03113 | A | DVIS | QUARTA-FEIRA | 09:30–12:30 | Sala 404 | 27 | 12 | 225.00% |
| ARQ01011 | B | ARQU | QUINTA-FEIRA | 18:30–21:30 | Sala 404 | 16 | 12 | 133.33% |
| ARQ02004 | C | ARQU | QUINTA-FEIRA | 09:30–12:30 | Sala 404 | 15 | 12 | 125.00% |
| ARQ01049 | A | ARQU | QUARTA-FEIRA | 09:30–12:30 | Sala 407 | 15 | 10 | 150.00% |
| ARQ01008 | A | ARQU | SEGUNDA-FEIRA | 18:30–22:30 | Sala 403 | 15 | 12 | 125.00% |
| ARQ01020 | A/B/C | ARQU | TERÇA-FEIRA | 18:30–22:30 | Sala 503 | 45 | 38 | 118.42% |
| ARQ01008 | D/B | ARQU | SEXTA-FEIRA | 09:30–12:30 | Sala 405 | 30 | 12 | 250.00% |
| ARQ02003 | B | ARQU | QUINTA-FEIRA | 08:30–12:30 | Sala 403 | 17 | 12 | 141.67% |
| ARQ01007 | D | ARQU | QUARTA-FEIRA | 18:30–21:30 | Sala 404 | 15 | 12 | 125.00% |

## Frequência dos padrões semanais

| Encontros no padrão | Padrões |
| ---: | ---: |
| 1 | 99 |
| 2 | 65 |
| 3 | 20 |

## Conflitos potenciais no ANTES

| Regra | Pares em conflito |
| --- | ---: |
| CONFLITO_SALA | 0 |
| CONFLITO_DOCENTE | 0 |
| CONFLITO_ETAPA | 2 |

| Regra | Encontro 1 | Encontro 2 | Dia | Sobreposição |
| --- | --- | --- | --- | --- |
| CONFLITO_ETAPA | EV-1b3d850a9da976a9 | EV-59a4bfdb40ac646a | QUARTA-FEIRA | 07:30–08:30 |
| CONFLITO_ETAPA | EV-1b3d850a9da976a9 | EV-7297f6c5d68ebd65 | QUARTA-FEIRA | 07:30–08:30 |

Encontros que cruzam o almoço: 1; horas não atribuídas a turno: 1.00.

### Encontros que cruzam o almoço

| Disciplina | Grupo | Dia | Horário |
| --- | --- | --- | --- |
| ARQ02005 | A | SEGUNDA-FEIRA | 09:30–13:30 |

## Carga semanal por etapa obrigatória

| Curso | Etapa | Dia | Períodos |
| --- | ---: | --- | ---: |
| ARQU | 1 | QUARTA-FEIRA | 8 |
| ARQU | 1 | QUINTA-FEIRA | 8 |
| ARQU | 1 | SEGUNDA-FEIRA | 8 |
| ARQU | 1 | SEXTA-FEIRA | 6 |
| ARQU | 1 | TERÇA-FEIRA | 9 |
| ARQU | 2 | QUARTA-FEIRA | 16 |
| ARQU | 2 | QUINTA-FEIRA | 16 |
| ARQU | 2 | SEGUNDA-FEIRA | 12 |
| ARQU | 2 | SEXTA-FEIRA | 17 |
| ARQU | 2 | TERÇA-FEIRA | 15 |
| ARQU | 3 | QUARTA-FEIRA | 17 |
| ARQU | 3 | QUINTA-FEIRA | 8 |
| ARQU | 3 | SEGUNDA-FEIRA | 26 |
| ARQU | 3 | SEXTA-FEIRA | 11 |
| ARQU | 3 | TERÇA-FEIRA | 4 |
| ARQU | 4 | QUARTA-FEIRA | 13 |
| ARQU | 4 | QUINTA-FEIRA | 6 |
| ARQU | 4 | SEGUNDA-FEIRA | 20 |
| ARQU | 4 | SEXTA-FEIRA | 14 |
| ARQU | 4 | TERÇA-FEIRA | 5 |
| ARQU | 5 | QUARTA-FEIRA | 4 |
| ARQU | 5 | QUINTA-FEIRA | 15 |
| ARQU | 5 | SEGUNDA-FEIRA | 2 |
| ARQU | 5 | SEXTA-FEIRA | 9 |
| ARQU | 5 | TERÇA-FEIRA | 16 |
| ARQU | 6 | QUARTA-FEIRA | 4 |
| ARQU | 6 | QUINTA-FEIRA | 9 |
| ARQU | 6 | SEGUNDA-FEIRA | 8 |
| ARQU | 6 | SEXTA-FEIRA | 4 |
| ARQU | 6 | TERÇA-FEIRA | 13 |
| ARQU | 7 | QUARTA-FEIRA | 6 |
| ARQU | 7 | QUINTA-FEIRA | 16 |
| ARQU | 7 | SEGUNDA-FEIRA | 8 |
| ARQU | 7 | SEXTA-FEIRA | 4 |
| ARQU | 7 | TERÇA-FEIRA | 16 |
| ARQU | 8 | QUARTA-FEIRA | 11 |
| ARQU | 8 | QUINTA-FEIRA | 8 |
| ARQU | 8 | SEGUNDA-FEIRA | 10 |
| ARQU | 8 | SEXTA-FEIRA | 5 |
| ARQU | 8 | TERÇA-FEIRA | 10 |
| ARQU | 9 | QUARTA-FEIRA | 6 |
| ARQU | 9 | QUINTA-FEIRA | 9 |
| ARQU | 9 | SEGUNDA-FEIRA | 11 |
| ARQU | 9 | SEXTA-FEIRA | 2 |
| ARQU | 9 | TERÇA-FEIRA | 12 |
| DPRO | 1 | QUINTA-FEIRA | 12 |
| DPRO | 1 | SEGUNDA-FEIRA | 4 |
| DPRO | 1 | SEXTA-FEIRA | 4 |
| DPRO | 1 | TERÇA-FEIRA | 14 |
| DPRO | 2 | QUINTA-FEIRA | 6 |
| DPRO | 2 | SEGUNDA-FEIRA | 4 |
| DPRO | 2 | TERÇA-FEIRA | 4 |
| DPRO | 3 | QUARTA-FEIRA | 6 |
| DPRO | 3 | QUINTA-FEIRA | 6 |
| DPRO | 3 | SEGUNDA-FEIRA | 6 |
| DPRO | 3 | TERÇA-FEIRA | 8 |
| DPRO | 4 | QUINTA-FEIRA | 3 |
| DPRO | 4 | SEGUNDA-FEIRA | 4 |
| DPRO | 4 | SEXTA-FEIRA | 3 |
| DPRO | 4 | TERÇA-FEIRA | 5 |
| DPRO | 5 | QUARTA-FEIRA | 2 |
| DPRO | 5 | QUINTA-FEIRA | 6 |
| DPRO | 5 | SEGUNDA-FEIRA | 4 |
| DPRO | 5 | SEXTA-FEIRA | 2 |
| DPRO | 5 | TERÇA-FEIRA | 6 |
| DPRO | 6 | QUARTA-FEIRA | 3 |
| DPRO | 6 | QUINTA-FEIRA | 4 |
| DPRO | 6 | SEGUNDA-FEIRA | 3 |
| DPRO | 7 | QUARTA-FEIRA | 4 |
| DPRO | 7 | QUINTA-FEIRA | 7 |
| DPRO | 7 | TERÇA-FEIRA | 7 |
| DPRO | 8 | QUARTA-FEIRA | 3 |
| DPRO | 8 | SEGUNDA-FEIRA | 3 |
| DPRO | 9 | QUARTA-FEIRA | 5 |
| DPRO | 9 | SEGUNDA-FEIRA | 3 |
| DVIS | 1 | QUINTA-FEIRA | 12 |
| DVIS | 1 | SEGUNDA-FEIRA | 4 |
| DVIS | 1 | SEXTA-FEIRA | 4 |
| DVIS | 1 | TERÇA-FEIRA | 14 |
| DVIS | 2 | QUARTA-FEIRA | 3 |
| DVIS | 2 | QUINTA-FEIRA | 6 |
| DVIS | 2 | SEGUNDA-FEIRA | 4 |
| DVIS | 2 | SEXTA-FEIRA | 2 |
| DVIS | 2 | TERÇA-FEIRA | 4 |
| DVIS | 3 | QUARTA-FEIRA | 8 |
| DVIS | 3 | QUINTA-FEIRA | 6 |
| DVIS | 3 | SEGUNDA-FEIRA | 8 |
| DVIS | 3 | SEXTA-FEIRA | 2 |
| DVIS | 3 | TERÇA-FEIRA | 8 |
| DVIS | 4 | QUARTA-FEIRA | 2 |
| DVIS | 4 | QUINTA-FEIRA | 3 |
| DVIS | 4 | SEGUNDA-FEIRA | 6 |
| DVIS | 4 | SEXTA-FEIRA | 3 |
| DVIS | 4 | TERÇA-FEIRA | 5 |
| DVIS | 5 | QUARTA-FEIRA | 5 |
| DVIS | 5 | SEGUNDA-FEIRA | 7 |
| DVIS | 5 | SEXTA-FEIRA | 2 |
| DVIS | 6 | QUARTA-FEIRA | 3 |
| DVIS | 6 | QUINTA-FEIRA | 4 |
| DVIS | 6 | SEGUNDA-FEIRA | 3 |
| DVIS | 6 | TERÇA-FEIRA | 4 |
| DVIS | 7 | QUARTA-FEIRA | 4 |
| DVIS | 7 | QUINTA-FEIRA | 5 |
| DVIS | 7 | TERÇA-FEIRA | 5 |
| DVIS | 8 | QUINTA-FEIRA | 5 |
| DVIS | 8 | TERÇA-FEIRA | 5 |
| DVIS | 9 | QUARTA-FEIRA | 5 |
| DVIS | 9 | SEGUNDA-FEIRA | 3 |

## Carga semanal por docente

| Docente | Dia | Períodos |
| --- | --- | ---: |
| Prof01 | QUARTA-FEIRA | 3 |
| Prof01 | QUINTA-FEIRA | 6 |
| Prof01 | SEGUNDA-FEIRA | 6 |
| Prof01 | SEXTA-FEIRA | 3 |
| Prof01 | TERÇA-FEIRA | 6 |
| Prof02 | QUINTA-FEIRA | 3 |
| Prof02 | SEGUNDA-FEIRA | 6 |
| Prof02 | SEXTA-FEIRA | 4 |
| Prof02 | TERÇA-FEIRA | 3 |
| Prof03 | QUARTA-FEIRA | 4 |
| Prof03 | SEGUNDA-FEIRA | 4 |
| Prof03 | SEXTA-FEIRA | 4 |
| Prof04 | QUARTA-FEIRA | 2 |
| Prof04 | QUINTA-FEIRA | 4 |
| Prof04 | SEGUNDA-FEIRA | 2 |
| Prof04 | TERÇA-FEIRA | 2 |
| Prof05 | QUARTA-FEIRA | 5 |
| Prof05 | SEGUNDA-FEIRA | 3 |
| Prof06 | QUINTA-FEIRA | 6 |
| Prof06 | TERÇA-FEIRA | 6 |
| Prof07 | QUINTA-FEIRA | 3 |
| Prof07 | SEXTA-FEIRA | 3 |
| Prof07 | TERÇA-FEIRA | 4 |
| Prof08 | QUARTA-FEIRA | 6 |
| Prof08 | QUINTA-FEIRA | 3 |
| Prof08 | SEGUNDA-FEIRA | 6 |
| Prof08 | SEXTA-FEIRA | 3 |
| Prof09 | QUARTA-FEIRA | 4 |
| Prof09 | TERÇA-FEIRA | 4 |
| Prof10 | QUARTA-FEIRA | 6 |
| Prof10 | SEGUNDA-FEIRA | 6 |
| Prof100 | TERÇA-FEIRA | 4 |
| Prof101 | QUARTA-FEIRA | 3 |
| Prof101 | QUINTA-FEIRA | 3 |
| Prof101 | SEGUNDA-FEIRA | 3 |
| Prof101 | SEXTA-FEIRA | 3 |
| Prof101 | TERÇA-FEIRA | 3 |
| Prof102 | QUARTA-FEIRA | 2 |
| Prof102 | SEGUNDA-FEIRA | 2 |
| Prof103 | QUINTA-FEIRA | 2 |
| Prof103 | TERÇA-FEIRA | 2 |
| Prof104 | QUARTA-FEIRA | 2 |
| Prof104 | TERÇA-FEIRA | 6 |
| Prof105 | QUINTA-FEIRA | 2 |
| Prof105 | SEGUNDA-FEIRA | 4 |
| Prof106 | SEXTA-FEIRA | 5 |
| Prof106 | TERÇA-FEIRA | 2 |
| Prof107 | QUARTA-FEIRA | 2 |
| Prof107 | SEXTA-FEIRA | 2 |
| Prof108 | QUARTA-FEIRA | 2 |
| Prof108 | SEXTA-FEIRA | 2 |
| Prof109 | TERÇA-FEIRA | 4 |
| Prof11 | QUARTA-FEIRA | 5 |
| Prof11 | SEGUNDA-FEIRA | 3 |
| Prof110 | SEGUNDA-FEIRA | 4 |
| Prof111 | QUARTA-FEIRA | 2 |
| Prof111 | SEGUNDA-FEIRA | 2 |
| Prof112 | SEGUNDA-FEIRA | 3 |
| Prof112 | SEXTA-FEIRA | 3 |
| Prof113 | SEGUNDA-FEIRA | 3 |
| Prof114 | QUINTA-FEIRA | 2 |
| Prof114 | TERÇA-FEIRA | 2 |
| Prof115 | QUINTA-FEIRA | 2 |
| Prof115 | TERÇA-FEIRA | 2 |
| Prof116 | QUINTA-FEIRA | 2 |
| Prof116 | TERÇA-FEIRA | 2 |
| Prof117 | QUINTA-FEIRA | 4 |
| Prof117 | TERÇA-FEIRA | 4 |
| Prof118 | QUINTA-FEIRA | 2 |
| Prof118 | TERÇA-FEIRA | 2 |
| Prof119 | QUINTA-FEIRA | 2 |
| Prof119 | TERÇA-FEIRA | 2 |
| Prof12 | QUINTA-FEIRA | 2 |
| Prof12 | TERÇA-FEIRA | 2 |
| Prof120 | SEGUNDA-FEIRA | 2 |
| Prof120 | SEXTA-FEIRA | 2 |
| Prof121 | QUARTA-FEIRA | 4 |
| Prof122 | QUARTA-FEIRA | 3 |
| Prof122 | QUINTA-FEIRA | 3 |
| Prof122 | SEGUNDA-FEIRA | 3 |
| Prof122 | SEXTA-FEIRA | 3 |
| Prof123 | QUINTA-FEIRA | 3 |
| Prof123 | SEGUNDA-FEIRA | 4 |
| Prof123 | TERÇA-FEIRA | 3 |
| Prof125 | QUINTA-FEIRA | 4 |
| Prof125 | TERÇA-FEIRA | 3 |
| Prof126 | QUARTA-FEIRA | 4 |
| Prof126 | QUINTA-FEIRA | 4 |
| Prof126 | TERÇA-FEIRA | 3 |
| Prof127 | QUARTA-FEIRA | 3 |
| Prof127 | SEGUNDA-FEIRA | 3 |
| Prof128 | QUINTA-FEIRA | 3 |
| Prof128 | SEGUNDA-FEIRA | 5 |
| Prof128 | TERÇA-FEIRA | 4 |
| Prof129 | QUINTA-FEIRA | 3 |
| Prof129 | SEGUNDA-FEIRA | 3 |
| Prof129 | TERÇA-FEIRA | 4 |
| Prof13 | QUARTA-FEIRA | 3 |
| Prof13 | SEGUNDA-FEIRA | 4 |
| Prof13 | SEXTA-FEIRA | 3 |
| Prof130 | QUINTA-FEIRA | 3 |
| Prof130 | SEXTA-FEIRA | 3 |
| Prof130 | TERÇA-FEIRA | 4 |
| Prof131 | QUARTA-FEIRA | 2 |
| Prof131 | QUINTA-FEIRA | 2 |
| Prof131 | TERÇA-FEIRA | 4 |
| Prof132 | QUINTA-FEIRA | 2 |
| Prof132 | SEGUNDA-FEIRA | 4 |
| Prof132 | TERÇA-FEIRA | 4 |
| Prof133 | QUINTA-FEIRA | 3 |
| Prof133 | SEGUNDA-FEIRA | 4 |
| Prof14 | QUARTA-FEIRA | 2 |
| Prof14 | SEGUNDA-FEIRA | 2 |
| Prof15 | QUARTA-FEIRA | 2 |
| Prof15 | QUINTA-FEIRA | 3 |
| Prof15 | TERÇA-FEIRA | 3 |
| Prof16 | QUARTA-FEIRA | 4 |
| Prof16 | SEGUNDA-FEIRA | 4 |
| Prof17 | QUINTA-FEIRA | 3 |
| Prof17 | SEXTA-FEIRA | 4 |
| Prof17 | TERÇA-FEIRA | 3 |
| Prof18 | QUARTA-FEIRA | 3 |
| Prof18 | SEGUNDA-FEIRA | 8 |
| Prof18 | SEXTA-FEIRA | 3 |
| Prof19 | QUARTA-FEIRA | 3 |
| Prof19 | SEGUNDA-FEIRA | 3 |
| Prof20 | QUINTA-FEIRA | 6 |
| Prof20 | TERÇA-FEIRA | 6 |
| Prof21 | QUARTA-FEIRA | 3 |
| Prof21 | SEGUNDA-FEIRA | 5 |
| Prof21 | TERÇA-FEIRA | 2 |
| Prof22 | QUINTA-FEIRA | 3 |
| Prof22 | TERÇA-FEIRA | 3 |
| Prof23 | QUINTA-FEIRA | 2 |
| Prof23 | TERÇA-FEIRA | 2 |
| Prof24 | QUINTA-FEIRA | 3 |
| Prof24 | SEGUNDA-FEIRA | 3 |
| Prof24 | TERÇA-FEIRA | 4 |
| Prof25 | QUARTA-FEIRA | 3 |
| Prof25 | SEGUNDA-FEIRA | 4 |
| Prof25 | SEXTA-FEIRA | 3 |
| Prof26 | QUARTA-FEIRA | 6 |
| Prof26 | SEGUNDA-FEIRA | 7 |
| Prof26 | SEXTA-FEIRA | 3 |
| Prof27 | QUINTA-FEIRA | 3 |
| Prof27 | TERÇA-FEIRA | 4 |
| Prof28 | SEGUNDA-FEIRA | 4 |
| Prof28 | TERÇA-FEIRA | 4 |
| Prof29 | QUINTA-FEIRA | 3 |
| Prof29 | SEGUNDA-FEIRA | 3 |
| Prof29 | TERÇA-FEIRA | 4 |
| Prof30 | QUARTA-FEIRA | 3 |
| Prof30 | QUINTA-FEIRA | 3 |
| Prof30 | SEGUNDA-FEIRA | 7 |
| Prof30 | SEXTA-FEIRA | 3 |
| Prof30 | TERÇA-FEIRA | 4 |
| Prof31 | QUARTA-FEIRA | 3 |
| Prof31 | QUINTA-FEIRA | 2 |
| Prof31 | SEGUNDA-FEIRA | 5 |
| Prof31 | TERÇA-FEIRA | 4 |
| Prof32 | QUINTA-FEIRA | 3 |
| Prof32 | TERÇA-FEIRA | 4 |
| Prof33 | QUARTA-FEIRA | 3 |
| Prof33 | SEGUNDA-FEIRA | 3 |
| Prof34 | QUARTA-FEIRA | 3 |
| Prof34 | QUINTA-FEIRA | 3 |
| Prof34 | SEGUNDA-FEIRA | 7 |
| Prof35 | QUINTA-FEIRA | 3 |
| Prof35 | SEGUNDA-FEIRA | 3 |
| Prof35 | TERÇA-FEIRA | 4 |
| Prof36 | QUINTA-FEIRA | 5 |
| Prof36 | SEGUNDA-FEIRA | 5 |
| Prof36 | TERÇA-FEIRA | 4 |
| Prof37 | QUINTA-FEIRA | 6 |
| Prof37 | TERÇA-FEIRA | 3 |
| Prof38 | QUARTA-FEIRA | 4 |
| Prof38 | QUINTA-FEIRA | 6 |
| Prof38 | TERÇA-FEIRA | 3 |
| Prof39 | QUARTA-FEIRA | 3 |
| Prof39 | QUINTA-FEIRA | 6 |
| Prof39 | SEXTA-FEIRA | 3 |
| Prof39 | TERÇA-FEIRA | 3 |
| Prof40 | QUINTA-FEIRA | 3 |
| Prof40 | SEGUNDA-FEIRA | 3 |
| Prof40 | SEXTA-FEIRA | 3 |
| Prof40 | TERÇA-FEIRA | 7 |
| Prof41 | QUINTA-FEIRA | 6 |
| Prof41 | TERÇA-FEIRA | 3 |
| Prof42 | QUARTA-FEIRA | 3 |
| Prof43 | SEGUNDA-FEIRA | 2 |
| Prof43 | TERÇA-FEIRA | 6 |
| Prof44 | QUARTA-FEIRA | 2 |
| Prof44 | SEGUNDA-FEIRA | 2 |
| Prof45 | QUARTA-FEIRA | 3 |
| Prof45 | QUINTA-FEIRA | 2 |
| Prof45 | SEGUNDA-FEIRA | 4 |
| Prof45 | SEXTA-FEIRA | 3 |
| Prof46 | QUARTA-FEIRA | 4 |
| Prof46 | QUINTA-FEIRA | 2 |
| Prof46 | SEXTA-FEIRA | 2 |
| Prof47 | QUARTA-FEIRA | 2 |
| Prof47 | QUINTA-FEIRA | 4 |
| Prof47 | SEGUNDA-FEIRA | 4 |
| Prof48 | QUINTA-FEIRA | 6 |
| Prof48 | SEGUNDA-FEIRA | 4 |
| Prof48 | TERÇA-FEIRA | 3 |
| Prof49 | QUARTA-FEIRA | 2 |
| Prof49 | SEXTA-FEIRA | 2 |
| Prof50 | TERÇA-FEIRA | 2 |
| Prof51 | QUINTA-FEIRA | 2 |
| Prof52 | QUARTA-FEIRA | 2 |
| Prof52 | SEGUNDA-FEIRA | 2 |
| Prof53 | SEGUNDA-FEIRA | 4 |
| Prof54 | QUINTA-FEIRA | 2 |
| Prof54 | SEGUNDA-FEIRA | 2 |
| Prof54 | TERÇA-FEIRA | 4 |
| Prof55 | QUARTA-FEIRA | 4 |
| Prof55 | SEGUNDA-FEIRA | 2 |
| Prof55 | TERÇA-FEIRA | 4 |
| Prof56 | QUARTA-FEIRA | 4 |
| Prof56 | QUINTA-FEIRA | 2 |
| Prof57 | SEGUNDA-FEIRA | 3 |
| Prof58 | TERÇA-FEIRA | 2 |
| Prof59 | SEXTA-FEIRA | 4 |
| Prof60 | SEGUNDA-FEIRA | 4 |
| Prof61 | QUINTA-FEIRA | 3 |
| Prof61 | SEXTA-FEIRA | 3 |
| Prof61 | TERÇA-FEIRA | 6 |
| Prof62 | QUINTA-FEIRA | 6 |
| Prof62 | SEXTA-FEIRA | 3 |
| Prof62 | TERÇA-FEIRA | 3 |
| Prof65 | QUINTA-FEIRA | 2 |
| Prof66 | QUARTA-FEIRA | 2 |
| Prof66 | SEXTA-FEIRA | 2 |
| Prof67 | QUINTA-FEIRA | 3 |
| Prof67 | TERÇA-FEIRA | 3 |
| Prof68 | SEXTA-FEIRA | 4 |
| Prof69 | SEGUNDA-FEIRA | 2 |
| Prof70 | QUARTA-FEIRA | 3 |
| Prof70 | SEGUNDA-FEIRA | 4 |
| Prof70 | SEXTA-FEIRA | 3 |
| Prof71 | QUINTA-FEIRA | 4 |
| Prof71 | TERÇA-FEIRA | 4 |
| Prof72 | QUARTA-FEIRA | 6 |
| Prof72 | SEGUNDA-FEIRA | 6 |
| Prof73 | QUINTA-FEIRA | 4 |
| Prof73 | TERÇA-FEIRA | 4 |
| Prof74 | QUARTA-FEIRA | 3 |
| Prof74 | SEGUNDA-FEIRA | 4 |
| Prof74 | SEXTA-FEIRA | 3 |
| Prof75 | QUINTA-FEIRA | 3 |
| Prof75 | SEGUNDA-FEIRA | 3 |
| Prof75 | SEXTA-FEIRA | 3 |
| Prof75 | TERÇA-FEIRA | 3 |
| Prof76 | QUINTA-FEIRA | 3 |
| Prof76 | TERÇA-FEIRA | 3 |
| Prof77 | QUARTA-FEIRA | 6 |
| Prof77 | SEGUNDA-FEIRA | 6 |
| Prof78 | QUINTA-FEIRA | 3 |
| Prof78 | SEXTA-FEIRA | 3 |
| Prof78 | TERÇA-FEIRA | 4 |
| Prof79 | QUARTA-FEIRA | 3 |
| Prof79 | SEGUNDA-FEIRA | 3 |
| Prof79 | SEXTA-FEIRA | 3 |
| Prof80 | QUINTA-FEIRA | 5 |
| Prof80 | TERÇA-FEIRA | 5 |
| Prof81 | QUARTA-FEIRA | 3 |
| Prof82 | QUARTA-FEIRA | 4 |
| Prof83 | QUINTA-FEIRA | 4 |
| Prof83 | TERÇA-FEIRA | 3 |
| Prof84 | QUINTA-FEIRA | 2 |
| Prof84 | TERÇA-FEIRA | 2 |
| Prof85 | QUARTA-FEIRA | 3 |
| Prof85 | SEGUNDA-FEIRA | 4 |
| Prof85 | SEXTA-FEIRA | 3 |
| Prof86 | QUINTA-FEIRA | 3 |
| Prof86 | SEGUNDA-FEIRA | 3 |
| Prof86 | TERÇA-FEIRA | 4 |
| Prof87 | QUARTA-FEIRA | 7 |
| Prof87 | QUINTA-FEIRA | 7 |
| Prof87 | TERÇA-FEIRA | 4 |
| Prof88 | QUINTA-FEIRA | 4 |
| Prof88 | SEGUNDA-FEIRA | 2 |
| Prof88 | TERÇA-FEIRA | 6 |
| Prof89 | QUINTA-FEIRA | 3 |
| Prof90 | QUARTA-FEIRA | 3 |
| Prof90 | SEGUNDA-FEIRA | 4 |
| Prof90 | SEXTA-FEIRA | 3 |
| Prof91 | QUARTA-FEIRA | 3 |
| Prof91 | SEGUNDA-FEIRA | 4 |
| Prof91 | SEXTA-FEIRA | 3 |
| Prof92 | QUARTA-FEIRA | 2 |
| Prof92 | SEXTA-FEIRA | 2 |
| Prof93 | QUARTA-FEIRA | 3 |
| Prof93 | SEGUNDA-FEIRA | 3 |
| Prof93 | SEXTA-FEIRA | 3 |

## Limites

- Sala sem aula no CSV não prova disponibilidade externa à grade registrada.
- `etapa` é conferida com as etapas/caráteres de `dadosBrutos/curriculos.xlsx`; 119 códigos obrigatórios coincidem, `ARQ01098` é uma alternativa codificada como 0, e 36 ofertas com etapa 0 não constam no currículo específico do curso. A origem e a regra de associação de `creditos` permanecem pendentes.
- Divergências nos campos de vagas são reportadas, não corrigidas automaticamente.
