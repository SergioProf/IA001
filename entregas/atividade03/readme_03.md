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

## Regras executáveis — fase 4

`restricoes_03.py` valida propostas sem editar o CSV-fonte. Cada alocação é identificada pelo ID determinístico do encontro físico e pode alterar somente `predio`, `sala`, `dia_semana`, `hora_inicio` e `hora_fim`; membros, docentes, frequência e duração permanecem ligados ao modelo original. `validar_grade(modelo)` valida a posição atual; para uma proposta, informe todas as alocações em `validar_grade(modelo, alocacoes, excecoes_turno)`.

As regras `H001`–`H010` são invioláveis: identidade/duração, dias úteis, almoço, conflitos de sala/docente/etapa, cursos externos imóveis, capacidade de 110%, laboratório e justificativa de turno. Uma violação já presente na fonte é marcada `baseline`; uma exceção de turno documentada retorna severidade `excecao`. Ambas não são violações novas bloqueantes; `diagnosticos_bloqueantes` separa as violações duras novas. O turno segue as janelas publicadas na auditoria: manhã antes de 12:30, tarde de 13:30 a 18:30 e noite a partir de 18:30. A interseção dos intervalos usa limites semiabertos.

As preferências `P01`–`P05` ficam separadas das restrições duras. `classificar_preservacao` retorna níveis 1–5; `metricas_preferencia` calcula preservação, troca de espaço, laboratório sem dependência, início noturno tardio, intervalos livres e dispersão semanal de docentes/etapas, além da prioridade por alunos, obrigatoriedade, encontros e CH. O limite de início noturno tardio é configurável (padrão `20:00`); não é uma restrição dura.

Execute os testes a partir da raiz do workspace:

```powershell
python -m unittest discover -s entregas/atividade03 -p "test_*.py"
```

As regras da fase 4 validam propostas, mas não reorganizam a grade nem produzem soluções A/B/C.

## Candidatos e método de otimização — fase 5

`candidatos_03.py` cria em memória os domínios determinísticos para cada encontro móvel. Os intervalos candidato são pares `hora_inicio`/`hora_fim` já observados na fonte e só são reutilizados para encontros de duração igual; nenhum início arbitrário é criado. Os dias candidatos são segunda a sexta. Intervalos que cruzam 12:30–13:30 são excluídos. Todas as 23 salas observadas são avaliadas por capacidade (110% no máximo) e tipo; encontros originalmente em laboratório só recebem candidatos em laboratórios.

Encontros que incluem qualquer curso fora de ARQU/DPRO/DVIS permanecem fixos. Suas salas e horários bloqueiam candidatos que colidam com a sala ou com docentes; conflitos de etapa obrigatória também são bloqueados quando aplicável. Conflitos entre encontros móveis não são removidos dos domínios individualmente: devem ser expressos como restrições globais do solver, para que a busca possa mover ambos. `alocacoes_fixos` expõe as posições imutáveis e `resumir_dominios` informa a dimensão e domínios sem opções. Nenhum CSV de solução é gravado.

A fonte contém 289 encontros físicos: 285 móveis e 4 que permanecem fixos por envolverem cursos externos. Há 23 salas e 27 intervalos distintos sem cruzamento do almoço, distribuídos em quatro durações (60, 120, 180 e 240 minutos). Na execução atual, os filtros produziram 155.133 alocações candidatas (média 544,33 por encontro), sem domínios vazios; o menor domínio tem 31 opções e o maior, 1.255. A construção do modelo CP-SAT resultou em 155.133 variáveis booleanas, 24.479 restrições e granularidade de 30 minutos; esses números medem a formulação, não o tempo de solução.

**Solver escolhido:** OR-Tools CP-SAT, fixado em `ortools==9.15.6755` e instalado no ambiente virtual Python 3.14.7. A escolha se baseia na natureza discreta do problema e nos 285 encontros móveis com domínios finitos; CP-SAT oferece variáveis inteiras/booleanas e restrições globais de não sobreposição, apropriadas a sala, docente e etapa. A dependência é declarada em `requirements_03.txt`. A fase 5 não executa busca nem prova viabilidade global; solver sem solução, limite de tempo e solução ótima/provada deverão ser reportados separadamente na fase de otimização.

`modelo_otimizacao_03.py` constrói e valida o modelo CP-SAT: exatamente uma alocação por encontro móvel e não sobreposição por sala, docente e etapa obrigatória. As ocupações externas fixas são retiradas dos domínios; a construção também rejeita colisões com elas. `resolver_viabilidade` permanece disponível para testes mínimos e distingue `INFEASIBLE`, `UNKNOWN`, `FEASIBLE` e `OPTIMAL`.

Validar domínios e modelo com `python -m unittest discover -s entregas/atividade03 -p "test_candidatos_03.py" -v`. Inspecionar a dimensão dos domínios com `python entregas/atividade03/candidatos_03.py`. A construção do modelo não executa o problema real, não seleciona uma grade e não grava soluções.

## Solução A — preservação, fase 6

`solucao_a_03.py` executa a otimização global da Solução A. O objetivo é lexicográfico: maximiza, nesta ordem, encontros que mantêm sala/dia/horário; dia/horário com mudança de sala; dia; mudança de dia mantendo o padrão semanal; e, por fim, mudanças mais amplas. A prioridade de turmas e as preferências por sala/tipo de espaço e horários não tardios só desempatarem resultados com o mesmo nível de preservação. Encontros externos continuam fixos.

Execute com o ambiente do projeto:

```powershell
python entregas/atividade03/solucao_a_03.py --limite-segundos 300
```

O comando lê `mapa_salas_tidy_03.csv` sem sobrescrevê-lo. Se encontrar solução sem violações invioláveis novas, grava `solucao_A.csv` (20 colunas de origem mais colunas de auditoria), `solucao_A.json` (alocações, mudanças, exceções, diagnósticos e métricas) e `solucao_A.md` (resumo). Use `--entrada` e `--saida-dir` para caminhos alternativos. O limite de tempo é configurável.

`OPTIMAL` significa que o CP-SAT provou o ótimo do objetivo; `FEASIBLE` significa que encontrou uma alocação válida, mas não provou o ótimo; `INFEASIBLE` indica inviabilidade provada; `UNKNOWN` indica que não houve prova nem solução dentro do limite. Nos dois últimos casos, o comando não exporta uma proposta. Exceções de turno incluem os minutos fora do alvo e uma justificativa; o CP-SAT não atribui uma causa impeditiva individual para cada exceção. A validação usa `validar_grade` após reconstruir a proposta a partir das alocações e bloqueia a exportação quando encontra violações invioláveis novas.

## Ocupação nas plantas baixas

O painel `app_03.py` lê `PlantasBaixas.obj` (curvas 2D no plano XZ) e relaciona os polígonos aos dados pelo nome do objeto: `o Sala 301A`, `o Sala 501` etc. As demais curvas são desenhadas como fundo da planta.

Um gráfico Plotly anima a ocupação das salas ao longo do dia selecionado (controle deslizante e botão Play, passos de 30 minutos). Arquitetura aparece em vermelho, Design de Produto em azul, Design Visual em verde e encontros com mais de um curso em roxo. Passe o cursor sobre uma sala para ver as disciplinas em andamento.
