# Especificações — Reorganização das turmas

## Objetivo
Reorganizar a grade de ARQU, DPRO e DVIS, buscando:
- ARQU: manhã + noite;
- DPRO/DVIS: tarde + noite;
- preservar a estrutura acadêmica;
- registrar explicitamente exceções quando o turno-alvo não puder ser atendido.

Não criar, remover, dividir ou fundir turmas.

## Regras de turno
- ARQU: manhã/noite.
- DPRO/DVIS: tarde/noite.
- Noite é válida para todos, priorizando início da noite e evitando, quando possível, horários muito tardios.
- Disciplina de Design que oferece vagas para Arquitetura continua sendo tratada como Design.
- O curso responsável determina o turno-alvo.
- Se o turno-alvo não puder ser atendido, pode ser relaxado e a exceção deve ser registrada.

## Dias e horários
- Segunda a sexta são os únicos dias disponíveis.
- Sábado é proibido.
- Respeitar almoço: 12:30–13:30.
- Preservar número de encontros semanais.
- Preservar duração de cada encontro.
- Preservar a estrutura semanal: uma aula de 4h continua sendo um encontro de 4h; 2×2h continua 2×2h.
- Tentar preservar o padrão relativo dos dias e seus intervalos.
- Não criar novos horários intermediários arbitrariamente; usar os intervalos/estruturas existentes.
- Não dividir encontros.

## Conflitos de estudantes
- Disciplinas obrigatórias da mesma etapa e mesmo curso não podem deixar o aluno sem opção de matrícula: deve ser possível cursar todas as disciplinas da etapa escolhendo uma turma de cada, sem sobreposição entre as escolhidas.
- Turmas diferentes da mesma disciplina são alternativas (o aluno cursa uma delas) e podem ocorrer no mesmo horário.
- Etapa 0 (eletivas) é exceção: pode ser colocada onde houver compatibilidade.
- Distribuir as disciplinas obrigatórias de cada etapa ao longo da semana, evitando dias muito carregados e outros muito leves.
- Não impor um limite fixo de horas/dia.

## Docentes
- O docente permanece em sua turma.
- Um docente não pode estar em duas ocupações simultâneas, independentemente de curso/etapa.
- Em turma compartilhada, todos os docentes devem estar livres no novo horário.
- Preferir aulas consecutivas do mesmo professor quando conveniente.
- Buscar equilíbrio semanal da carga docente; evitar dias muito leves ou excessivamente carregados.

## Turmas compartilhadas
O atributo `turmas_compartilhando_sala` identifica o grupo:
- `A` = turma única;
- qualquer valor contendo `/` = compartilhada.
Ex.: `A/AA`, `A/B/C/D`.

Turma compartilhada é indivisível:
- mantém grupo;
- mesmos dias/horários;
- mesma sala;
- mesma estrutura de encontros.
Não separar compartilhamentos.

## Capacidade
Regra:
`vagas da ocupação <= capacidade da sala × 1,20`
Até 20% de excedente é aceitável, mas sala com capacidade suficiente é preferida.
Para compartilhadas, somar as vagas do grupo.

## Espaços
Todas as salas estão disponíveis aos três cursos.

### Laboratório de informática
- Turma atualmente em laboratório é considerada dependente de computadores.
- Só pode ser deslocada para outro laboratório.
- Evitar colocar outras turmas em laboratório quando houver alternativa.

### Ateliê e sala de aula
- São intercambiáveis.
- O dataset não permite inferir perfeitamente a natureza da atividade.
- Preferir manter o tipo de espaço atual.
- Pode trocar quando necessário.

## Turmas de outros cursos
Turmas que não são ARQU, DPRO ou DVIS não podem ser alteradas. São restrições fixas.

## Sala
- Todas as salas podem ser usadas pelos três cursos.
- Manter sala original quando possível.
- Pode trocar quando necessário.

## Preservação da grade atual
Turmas já no turno correto devem preferencialmente permanecer.
Podem ser deslocadas se necessário para a solução global.

Preferência, em igualdade de condições:
1. manter dia + horário + sala;
2. manter dia + horário, mudando sala;
3. manter dia, mudando horário;
4. mudar dia preservando o padrão semanal;
5. mudanças mais amplas.

## Prioridade entre turmas
1. maior número de alunos;
2. obrigatórias antes de eletivas;
3. maior número de encontros e maior CH semanal antes de menores cargas.

## Três soluções
### A — Preservação
Minimizar alterações na grade atual, mantendo especialmente sala/dia/horário quando possível.

### B — Equilíbrio
Priorizar melhor distribuição semanal das disciplinas de cada etapa e dos docentes, aceitando mais alterações.

### C — Turnos
Maximizar a CH total colocada no turno-alvo.
Em empate, menor quantidade de alterações.
A métrica principal é CH, não quantidade de turmas.

## Métricas
Para cada solução:
- CH no turno-alvo;
- % da CH no turno-alvo;
- número de turmas no turno-alvo;
- exceções;
- turmas alteradas;
- mudanças de sala;
- mudanças de dia;
- mudanças de horário;
- conflitos docentes;
- conflitos de etapa;
- violações de capacidade;
- equilíbrio semanal das etapas;
- equilíbrio semanal dos docentes.

## Validação
Validar independentemente:
- nenhuma turma criada/removida;
- nenhum encontro criado/removido;
- estrutura e duração preservadas;
- compartilhamentos preservados;
- docentes sem conflito;
- etapas obrigatórias sem conflito;
- capacidade respeitada;
- laboratórios preservados;
- sábado não usado;
- almoço respeitado;
- turmas externas não alteradas.

## Dados
O CSV original deve permanecer intacto.
Cada solução deve ser salva separadamente, preservando as colunas originais.
Podem ser adicionadas colunas como `solucao`, `alterado`, `turno_original`, `turno_alvo`, `motivo_alteracao`, `excecao_turno`, `tipo_mudanca`.

## Princípio
Tratar a tarefa como problema de alocação com restrições. Procurar solução global, não simplesmente mover uma turma por vez. Toda exceção deve ser rastreável e explicada.
