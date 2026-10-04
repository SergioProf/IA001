# Base de dados do mapa de salas — Atividade 03

## Origem e transformação

O arquivo canônico desta atividade é `entregas/atividade03/mapa_salas_tidy_03.csv`, referente à programação de salas do semestre `2026/2`. As análises, auditorias e propostas da Atividade 03 devem usar esse arquivo, não o CSV da raiz nem a saída histórica do script de transformação.

O script `dadosBrutos/transformar_mapa_salas.py` processa a planilha `dadosBrutos/MapaSalas.xlsx`; sua saída histórica é descrita em `dadosBrutos/relatorio_transformacao_mapa_salas.md` como 454 registros e 17 colunas. Essa fotografia histórica não é equivalente à base canônica 03: o CSV histórico não está disponível para comparação linha a linha e o script não gera todas as colunas presentes na base atual.

## Como os registros foram ampliados

A documentação da transformação histórica descreve a conversão da grade visual em registros tabulares. A base 03 contém linhas desmembradas por turma e por curso; assim, linhas repetidas podem representar a mesma ocupação física, e a contagem de linhas não deve ser tratada como contagem de encontros.

O modelo canônico documentado em `modelo_ocupacao_03.py` associa linhas à turma acadêmica, membro compartilhado, encontro físico e atribuições docentes, mantendo as linhas-fonte. Em `turmas_compartilhando_sala`, os tokens separados por `/` identificam os membros do grupo. Não some cópias de linhas por curso ou docente ao calcular ocupação física.

## Conteúdo da base atual

O arquivo `entregas/atividade03/mapa_salas_tidy_03.csv` contém 452 registros e 20 colunas. Cabeçalho: `semestre`, `predio`, `sala`, `capacidade_sala`, `tipo_sala`, `vagas_turma`, `codigo_disciplina`, `turma`, `nome_disciplina`, `docente`, `curso`, `dia_semana`, `hora_inicio`, `hora_fim`, `numero_periodos`, `vagas_oferecidas`, `vagas_totais_compartilhadas`, `turmas_compartilhando_sala`, `etapa` e `creditos`.

| Grupo | Colunas |
| --- | --- |
| Período e espaço | `semestre`, `predio`, `sala`, `capacidade_sala`, `tipo_sala` |
| Disciplina e oferta | `codigo_disciplina`, `turma`, `nome_disciplina`, `docente`, `curso`, `etapa`, `creditos` |
| Agenda | `dia_semana`, `hora_inicio`, `hora_fim`, `numero_periodos` |
| Vagas e compartilhamento | `vagas_turma`, `vagas_oferecidas`, `vagas_totais_compartilhadas`, `turmas_compartilhando_sala` |

As sete colunas numéricas do CSV são `capacidade_sala`, `vagas_turma`, `numero_periodos`, `vagas_oferecidas`, `vagas_totais_compartilhadas`, `etapa` e `creditos`; as outras 13 são texto. `etapa` não é produzida pelo script histórico; sua associação foi conferida contra `dadosBrutos/curriculos.xlsx`, planilha `Sheet1`. O workbook organiza três cursos em blocos com seções `Etapa 1`–`Etapa 10` e linhas `Código`/`Caráter`: 119 códigos obrigatórios coincidem por curso/código com a etapa do CSV; `ARQ01098` consta como `Alternativa` na Etapa 10 e aparece com `etapa=0`; outros 36 códigos etapa 0 não constam do currículo específico do curso. Não foram encontradas outras divergências nos códigos cobertos. O CSV da raiz coincide com o 03 nas 278 chaves acadêmicas para `etapa` e `creditos`, mas isso não é confirmação independente. A origem e a regra de associação de `creditos` continuam pendentes. A relação semântica entre `capacidade_sala` e `vagas_turma` também não está confirmada; não trate esses campos como equivalentes.

## Ajustes posteriores à transformação

O README anterior reportava os seguintes ajustes. O CSV 03 permite confirmar o estado atual dos registros, mas, sem a saída histórica tidy para comparação, não comprova autoria nem a diferença exata em relação àquela saída:

- `ARQ01013`: o CSV atual registra o encontro de terça-feira, 18:30–22:30, para C/D; o total relatado para A/C/D é de 10 períodos por turma.
- `ARQ01046`: o CSV atual contém uma ocorrência de 3 períodos para cada turma, com A/B na sexta-feira e C/D na quarta-feira.
- `ARQ01090` e `ARQ01091`: os créditos registrados no CSV atual são 1.

Essas observações não devem ser interpretadas como linhagem confirmada. A diferença documentada entre a saída histórica (454 registros e 17 colunas) e a fonte 03 (452 registros e 20 colunas) não pode ser reconciliada linha a linha com os arquivos disponíveis. Não sobrescreva nem regenere `mapa_salas_tidy_03.csv` a partir do script histórico.

## Cuidados para análises futuras

- Defina a unidade de análise antes de agregar. Para carga por curso, mantenha os registros separados por `curso`; para ocupação física, não conte novamente as linhas repetidas apenas por desagregação de cursos.
- Não some `vagas_totais_compartilhadas` em todas as linhas de um mesmo encontro, pois o total pode estar repetido. Para capacidade física, deduplique linhas repetidas por curso/docente e some `vagas_oferecidas` dos membros físicos únicos, conforme a regra de auditoria desta atividade; divergências entre os campos devem ser reportadas, não presumidas.
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
.venv/Scripts/python.exe -m unittest discover -s entregas/atividade03 -p "test_*.py"
```

As regras da fase 4 validam propostas, mas não reorganizam a grade nem produzem soluções A/B/C.

## Candidatos e método de otimização — fase 5

`candidatos_03.py` cria em memória os domínios determinísticos para cada encontro móvel. Os intervalos candidato são pares `hora_inicio`/`hora_fim` já observados na fonte e só são reutilizados para encontros de duração igual; nenhum início arbitrário é criado. Os dias candidatos são segunda a sexta. Intervalos que cruzam 12:30–13:30 são excluídos. Todas as 23 salas observadas são avaliadas por capacidade (110% no máximo) e tipo; encontros originalmente em laboratório só recebem candidatos em laboratórios.

Encontros que incluem qualquer curso fora de ARQU/DPRO/DVIS permanecem fixos. Suas salas e horários bloqueiam candidatos que colidam com a sala ou com docentes; conflitos de etapa obrigatória também são bloqueados quando aplicável. Conflitos entre encontros móveis não são removidos dos domínios individualmente: devem ser expressos como restrições globais do solver, para que a busca possa mover ambos. `alocacoes_fixos` expõe as posições imutáveis e `resumir_dominios` informa a dimensão e domínios sem opções. Nenhum CSV de solução é gravado.

A fonte contém 289 encontros físicos: 285 móveis e 4 que permanecem fixos por envolverem cursos externos. Há 23 salas e 27 intervalos distintos sem cruzamento do almoço, distribuídos em quatro durações (60, 120, 180 e 240 minutos). Na execução atual, os filtros produziram 155.133 alocações candidatas (média 544,33 por encontro), sem domínios vazios; o menor domínio tem 31 opções e o maior, 1.255. A construção do modelo CP-SAT resultou em 155.133 variáveis booleanas, 24.479 restrições e granularidade de 30 minutos; esses números medem a formulação, não o tempo de solução.

**Solver escolhido:** OR-Tools CP-SAT, fixado em `ortools==9.15.6755` e instalado no ambiente virtual Python 3.14.7. A escolha se baseia na natureza discreta do problema e nos 285 encontros móveis com domínios finitos; CP-SAT oferece variáveis inteiras/booleanas e restrições globais de não sobreposição, apropriadas a sala, docente e etapa. A dependência é declarada em `requirements_03.txt`. A fase 5 não executa busca nem prova viabilidade global; solver sem solução, limite de tempo e solução ótima/provada deverão ser reportados separadamente na fase de otimização.

`modelo_otimizacao_03.py` constrói e valida o modelo CP-SAT: exatamente uma alocação por encontro móvel e não sobreposição por sala, docente e etapa obrigatória. As ocupações externas fixas são retiradas dos domínios; a construção também rejeita colisões com elas. `resolver_viabilidade` permanece disponível para testes mínimos e distingue `INFEASIBLE`, `UNKNOWN`, `FEASIBLE` e `OPTIMAL`.

Validar domínios e modelo com `.venv/Scripts/python.exe -m unittest discover -s entregas/atividade03 -p "test_candidatos_03.py" -v`. Inspecionar a dimensão dos domínios com `.venv/Scripts/python.exe entregas/atividade03/candidatos_03.py`. A construção do modelo não executa o solver, não seleciona uma grade e não grava soluções.

## Solução A — preservação, fase 6

`solucao_a_03.py` executa a otimização global da Solução A. O objetivo é lexicográfico: maximiza, nesta ordem, encontros que mantêm sala/dia/horário; dia/horário com mudança de sala; dia; mudança de dia mantendo o padrão semanal; e, por fim, mudanças mais amplas. A prioridade de turmas e as preferências por sala/tipo de espaço e horários não tardios só desempatarão soluções com o mesmo perfil de preservação. Encontros externos continuam fixos.

Execute com o ambiente do projeto:

```powershell
.venv/Scripts/python.exe entregas/atividade03/solucao_a_03.py --preflight
.venv/Scripts/python.exe entregas/atividade03/solucao_a_03.py --limite-segundos 300
```

`--preflight` lê `mapa_salas_tidy_03.csv`, gera os domínios, constrói e valida o modelo completo da Solução A, e imprime um relatório JSON com hash, dimensões, tempos e pico de alocações Python. Não chama o solver nem cria arquivos de solução. A medição `tracemalloc` não inclui memória nativa do OR-Tools.

**Preflight da fonte canônica — 2026-10-03:** status `VALIDO`; SHA-256 `6101ab290feb8feee0cb7714692ef6aa8c67f647bf0bb970f92bf09a2f3ab5e0`, inalterado. Foram confirmados 452 linhas, 289 encontros físicos (285 móveis, 4 fixos), 155.133 candidatos e nenhum domínio vazio (mínimo 31, máximo 1.255). O modelo completo, já com o objetivo A, contém 156.789 variáveis, 27.791 restrições e granularidade de 30 minutos. O preflight levou 37,39 s no ambiente medido (0,151 s de carga, 6,832 s de domínios e 30,407 s de modelo); o pico rastreado de alocações Python foi 101.812.273 bytes, sem incluir memória nativa do OR-Tools. Nenhuma busca CP-SAT foi iniciada.

O comando de otimização lê a mesma fonte sem sobrescrevê-la. Toda tentativa grava `status_execucao_A.json` na pasta de saída com o status CP-SAT, o hash da fonte, o limite e se uma alocação foi encontrada, inclusive quando o solver retorna `UNKNOWN` ou `INFEASIBLE`. Com `OPTIMAL` e sem violações invioláveis novas, grava `solucao_A.csv` (20 colunas de origem mais colunas de auditoria), `solucao_A.json` (alocações, mudanças, exceções, diagnósticos e métricas) e `solucao_A.md` (resumo). Com `FEASIBLE`, grava `candidato_A.csv`, `candidato_A.json` e `candidato_A.md`; são artefatos provisórios, não o aceite da fase. Ambos os CSVs registram o status do solver. Use `--entrada` e `--saida-dir` para caminhos alternativos. O limite de tempo é configurável.

`OPTIMAL` significa que o CP-SAT provou o ótimo do objetivo; `FEASIBLE` significa que encontrou uma alocação válida, mas não provou o ótimo; `INFEASIBLE` indica inviabilidade provada; `UNKNOWN` indica que não houve prova nem solução dentro do limite. `INFEASIBLE` e `UNKNOWN` não geram arquivos. Exceções de turno incluem os minutos fora do alvo e uma justificativa; o CP-SAT não atribui uma causa impeditiva individual para cada exceção. A validação usa `validar_grade` após reconstruir a proposta a partir das alocações e bloqueia a exportação quando encontra violações invioláveis novas.

### Diagnóstico de viabilidade — 2026-10-03

O modelo-base sem objetivo A foi executado com oito workers e provou `INFEASIBLE` em 31,97 s. A mesma busca com um worker e limite de 60 s retornou `UNKNOWN`; essa diferença reforça que `UNKNOWN` sozinho não é prova de inviabilidade. A fonte permaneceu com o SHA-256 registrado acima; os 285 encontros móveis têm candidatos (155.133 no total) e nenhum domínio vazio.

Para localizar a restrição associada, foram construídas variantes exclusivamente diagnósticas que omitem uma categoria de conflito entre encontros móveis por vez. Omitir sala continuou `INFEASIBLE` em 2,48 s; omitir docente retornou `UNKNOWN` no limite de 25 s; omitir etapa produziu `OPTIMAL` em 15,96 s. Essa alocação diagnóstica apresentou 75 violações H006 novas, além de 4 já classificadas como baseline, e nenhuma outra violação dura nova. Portanto, não é uma solução utilizável e não foi exportada como grade.

Também foi testada uma ampliação que mantém durações existentes e combina cada uma com todos os inícios observados no CSV, excluindo almoço e encerramentos após 24:00. O domínio cresceu para 219.665 candidatos, sem encontros sem opções, mas o modelo estrito com H006 continuou `INFEASIBLE` (47,66 s, oito workers). O resultado está em `saida_solucao_A/diagnostico_inicios_observados_A.json`; a variante não foi adotada como produção.

Os relatórios reproduzíveis estão em `saida_solucao_A/diagnostico_viabilidade_A.json`, `diagnostico_viabilidade_paralela_A.json`, `diagnostico_recursos_A.json` e `diagnostico_conflitos_etapa_A.json`. `construir_modelo_cp_sat_diagnostico` em `modelo_otimizacao_03.py` serve somente para esse teste de sensibilidade; modelos relaxados não devem ser usados para gerar ou validar entregas.

**Conclusão operacional:** a Solução A não tem grade viável com H006 e os inícios observados, mesmo combinados com todas as durações existentes. A etapa foi conferida contra `curriculos.xlsx`; a pendência de `creditos` não explica o conflito H006. B/C também não devem ser executadas sobre o mesmo modelo inviável. Para continuar, é necessária uma decisão de escopo: autorizar inícios que não aparecem no CSV ou revisar formalmente a regra H006/exceções. Até haver autorização, não gerar horários arbitrários, não relaxar H006 e manter a fonte intacta.

## Ocupação nas plantas baixas

O painel `app_03.py` lê `PlantasBaixas.obj` (curvas 2D no plano XZ) e relaciona os polígonos aos dados pelo nome do objeto: `o Sala 301A`, `o Sala 501` etc. As demais curvas são desenhadas como fundo da planta.

Um gráfico Plotly anima a ocupação das salas ao longo do dia selecionado (controle deslizante e botão Play, passos de 30 minutos). Arquitetura aparece em vermelho, Design de Produto em azul, Design Visual em verde e encontros com mais de um curso em roxo. Passe o cursor sobre uma sala para ver as disciplinas em andamento.
