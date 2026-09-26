# Base de dados do mapa de salas

## Origem e transformação

O arquivo de trabalho `mapa_salas_tidy.csv` foi preparado a partir da programação de salas do semestre `2026/2`. A transformação original lê as abas da planilha `MapaSalas.xlsx`, organiza a grade semanal em formato tabular e associa cada encontro às informações acadêmicas e de espaço descritas na própria planilha.

O código da transformação está em `dadosBrutos/transformar_mapa_salas.py`. Sua saída original é `dadosBrutos/mapa_salas_tidy.csv`, acompanhada pelo relatório `dadosBrutos/relatorio_transformacao_mapa_salas.md`. O relatório registra 23 abas processadas, 454 registros e 17 colunas para essa versão da saída.

## Como os registros foram ampliados

A planilha organiza parte das informações em uma grade visual. Para permitir filtros, agrupamentos e gráficos, os encontros foram convertidos para registros tabulares:

- Cada registro descreve uma turma, disciplina, dia e faixa horária, junto com os dados do espaço.
- Chaves com turmas compartilhadas, como `A/B`, são desmembradas em linhas por turma.
- Disciplinas associadas a mais de um curso são desmembradas em linhas por curso. Portanto, um mesmo encontro pode aparecer mais de uma vez na base quando atende cursos diferentes.
- Períodos consecutivos da mesma turma, sala e dia são consolidados em um encontro com início, fim e `numero_periodos`.
- Docente, curso e vagas são associados às turmas a partir da tabela descritiva da planilha.
- As vagas de uma chave compartilhada são repartidas entre as turmas; eventual resto é atribuído à primeira turma. `vagas_oferecidas` representa a parcela da turma, enquanto `vagas_totais_compartilhadas` registra o total compartilhado e pode se repetir nas linhas do encontro.

## Conteúdo da base atual

O arquivo principal `mapa_salas_tidy.csv` contém atualmente 452 registros e 19 colunas. Além dos 17 campos da saída original, a versão de trabalho inclui `etapa` e `creditos`.

| Grupo | Colunas |
| --- | --- |
| Período e espaço | `semestre`, `predio`, `sala`, `tipo_sala`, `capacidade_turma` |
| Disciplina e oferta | `codigo_disciplina`, `turma`, `nome_disciplina`, `docente`, `curso`, `etapa`, `creditos` |
| Agenda | `dia_semana`, `hora_inicio`, `hora_fim`, `numero_periodos` |
| Vagas e compartilhamento | `vagas_oferecidas`, `vagas_totais_compartilhadas`, `turmas_compartilhando_sala` |

`etapa` e `creditos` estão presentes na base atual, mas não são produzidos por `dadosBrutos/transformar_mapa_salas.py` nem descritos no relatório da transformação. A fonte original desses dois campos e o procedimento usado para associá-los às turmas ainda precisam ser registrados. Antes de reutilizar ou atualizar a base, convém documentar a fonte oficial, a chave de correspondência e o significado dos valores, inclusive o valor `0` em `etapa`.

## Ajustes posteriores à transformação

A base principal recebeu ajustes manuais em relação à saída original do script:

- Na disciplina `ARQ01013`, foi incluído o encontro de terça-feira, das 18:30 às 22:30, para as turmas C e D. Com isso, ambas têm a mesma grade semanal e somam 10 períodos.
- Na disciplina `ARQ01046`, foram removidos os quatro encontros vespertinos das turmas A, B, C e D. Cada turma permanece com o encontro matinal de 3 períodos.
- Na disciplina `ARQ01090` e na disciplina `ARQ01091`, os créditos foram ajustados de 2 para 1 em todas as turmas registradas.

Essas alterações explicam a diferença entre a saída original reportada (454 registros e 17 colunas) e a base de trabalho atual (452 registros e 19 colunas). Elas não estão incorporadas ao script de transformação. A saída do script em `dadosBrutos/` não deve ser tratada como cópia atualizada da base principal sem reaplicar e documentar esses complementos.

## Cuidados para análises futuras

- Defina a unidade de análise antes de agregar. Para carga por curso, mantenha os registros separados por `curso`; para ocupação física, não conte novamente as linhas repetidas apenas por desagregação de cursos.
- Não some `vagas_totais_compartilhadas` em todas as linhas de um mesmo encontro, pois o total pode estar repetido. Use `vagas_oferecidas` para a parcela atribuída a cada turma.
- Use `numero_periodos` para somar a duração semanal. Os horários indicam os limites do encontro, e o horário final é o limite de encerramento.
- Preserve a distinção entre `turma` e `turmas_compartilhando_sala`: a primeira identifica o registro da turma; a segunda descreve a chave de turmas que compartilham o encontro.
- Os docentes aparecem anonimizados, por exemplo, como `Prof01`; esses identificadores não devem ser interpretados como nomes reais.
- A base descreve a programação regular do semestre `2026/2`. Ela não representa necessariamente usos eventuais, disponibilidade de espaços fora da grade ou alterações posteriores que não tenham sido incorporadas ao CSV. Registre no histórico da próxima atividade qualquer atualização feita na base.
