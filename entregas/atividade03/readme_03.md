# Reestruturação dos horários — Atividade 03

Este documento registra a implementação, os resultados validados e os limites conhecidos do fluxo de reorganização da Atividade 03.

## Estado das fases

| Fase | Conteúdo | Estado |
| --- | --- | --- |
| 1–3 | Integridade do dado, modelo canônico e baseline | Concluídas (`modelo_ocupacao_03.py`, `auditoria_baseline_03.py`, `auditoria_03.md`, `baseline_03.md`) |
| 4 | Regras executáveis e testes | Concluída (`restricoes_03.py`) |
| 5 | Candidatos e modelo CP-SAT | Concluída (`candidatos_03.py`, `modelo_otimizacao_03.py`) |
| 6 | Solução A — preservação | Concluída em modo fallback (ver abaixo) |
| 7 | Solução B — equilíbrio | Proposta viável `FEASIBLE`; ótimo não comprovado |
| 8 | Solução C — turnos | Concluída (`OPTIMAL`), com 1 exceção de turno |
| 9 | Validação exportada A/B/C | Concluída: 0 violações duras novas |
| 10 | Entrega reproduzível e visualização comparativa | Implementada; ambiente limpo ainda não verificado |

**Validação atual:** fonte SHA-256 `5980965c9e96effa0d44f879551425e2f67f44b2c6b81cb7cc3e4fcd6a10c086`; 452 linhas e 289 encontros físicos. A, B e C não introduzem violações duras. As 3 violações duras do ANTES e as exceções de turno são reportadas separadamente.

## Base de dados

O arquivo canônico é `mapa_salas_tidy_03.csv`, da programação de salas do semestre `2026/2`: 452 registros, 20 colunas, 289 encontros físicos, 23 salas, 5 cursos (ARQU, DPRO, DVIS, CAGR, ENGMEC). Não use o CSV da raiz nem a saída histórica de `dadosBrutos/transformar_mapa_salas.py` (454 registros, 17 colunas), que não é equivalente e não deve ser usada para regenerar este arquivo.

Colunas: `semestre`, `predio`, `sala`, `capacidade_sala`, `tipo_sala`, `vagas_turma`, `codigo_disciplina`, `turma`, `nome_disciplina`, `docente`, `curso`, `dia_semana`, `hora_inicio`, `hora_fim`, `numero_periodos`, `vagas_oferecidas`, `vagas_totais_compartilhadas`, `turmas_compartilhando_sala`, `etapa`, `creditos`. São numéricas `capacidade_sala`, `vagas_turma`, `numero_periodos`, `vagas_oferecidas`, `vagas_totais_compartilhadas`, `etapa` e `creditos`.

### Alteração de capacidades (2026-10-04)

A coluna `capacidade_sala` foi editada diretamente neste CSV (94 linhas): Salas 403, 404, 405 e 414 passaram a 30; 407 a 15; 304 a 60; 503 a 40. Os dados de capacidade das salas, que vieram de um PDF mais antigo (2023) não estavam compatativeis com a utilização atual, algumas salas trocaram mesas por cadeiras com apoio para a escrita, assim a capacidade da sala aumentou; Por isso o SHA-256 atual é `5980965c9e96effa0d44f879551425e2f67f44b2c6b81cb7cc3e4fcd6a10c086` (o anterior era `6101ab29…`). Os documentos `baseline_03.md` (regerado com `auditoria_baseline_03.py`) e `auditoria_03.md` já refletem esta versão.

### Origem de `etapa` e `creditos`

`etapa` não é produzida pelo script histórico; foi conferida contra `dadosBrutos/curriculos.xlsx`: 119 códigos obrigatórios coincidem por curso/código; `ARQ01098` é `Alternativa` na Etapa 10 e aparece com `etapa=0`; outros 36 códigos com etapa 0 não constam do currículo do curso. A origem e a regra de associação de `creditos` continuam pendentes. `capacidade_sala` e `vagas_turma` não são equivalentes.

### Cuidados com a base

- As linhas são desmembradas por turma, curso e docente: a contagem de linhas não é contagem de encontros. O modelo canônico (`modelo_ocupacao_03.py`) liga linhas a turma acadêmica, membro compartilhado, encontro físico e docentes; em `turmas_compartilhando_sala`, os tokens separados por `/` são os membros do grupo.
- Capacidade física soma `vagas_oferecidas` dos membros físicos únicos do encontro, sem somar cópias por curso ou docente nem `vagas_totais_compartilhadas`.
- Use `numero_periodos` para duração semanal; `hora_fim` é o limite de encerramento.
- Docentes são anonimizados (`Prof01`…). A base é a programação regular do semestre, não usos eventuais.
- Ajustes manuais anteriores observáveis no CSV (autoria não confirmada): `ARQ01013` (terça 18:30–22:30, C/D), `ARQ01046` (3 períodos por turma, A/B sexta e C/D quarta) e créditos 1 em `ARQ01090`/`ARQ01091`.

## Regras (`restricoes_03.py`)

`validar_grade(modelo, alocacoes, excecoes_turno)` valida uma proposta sem editar o CSV. Cada encontro físico (ID determinístico) só pode mudar `predio`, `sala`, `dia_semana`, `hora_inicio` e `hora_fim`.

| Regra | Conteúdo |
| --- | --- |
| H001 | Conservar encontros, duração e campos imutáveis |
| H002 | Somente segunda a sexta |
| H003 | Nada entre 12:30 e 13:30 |
| H004 | Sem sobreposição de sala |
| H005 | Sem sobreposição de docente, entre quaisquer cursos |
| H006 | Em cada curso/etapa (etapa 0 isenta), deve existir uma escolha de uma turma por disciplina sem sobreposição entre as escolhidas |
| H007 | Encontros com curso externo (fora de ARQU/DPRO/DVIS) ficam imóveis |
| H008 | Vagas até **120%** da capacidade da sala |
| H009 | Turmas em laboratório permanecem em laboratório |
| H010 | Minutos fora do turno-alvo exigem justificativa registrada (severidade `excecao`) |

**H006.** Turmas da mesma disciplina são alternativas: podem coincidir no horário, pois o aluno cursa uma delas. O que se proíbe é uma etapa em que alguma disciplina fique sem turma compatível com as demais. Toda disciplina com etapa diferente de 0 é tratada como obrigatória (o CSV não tem essa coluna), e a turma é identificada pela letra dentro da disciplina (`secoes_por_etapa`, `etapa_cursavel`).

Violações já presentes na grade atual recebem severidade `baseline`; `diagnosticos_bloqueantes` retorna apenas as violações duras novas. Turnos: manhã antes de 12:30, tarde de 13:30 a 18:30, noite a partir de 18:30; intervalos semiabertos.

Preferências P01–P05 (preservação em níveis 1–5, espaço e tipo originais, laboratório desnecessário, início tardio a partir de 20:00, intervalos e dispersão semanal) ficam em `classificar_preservacao` e `metricas_preferencia`, separadas das restrições duras.

### Grade atual frente às regras

Com as capacidades atuais, o limite de 120% e a H006 por turmas alternativas, a grade original tem 3 violações duras (baseline) e 61 encontros com H010:

- H003: `ARQ02005/A`, segunda 09:30–13:30, Sala 413, invade o almoço.
- H008: `ENG01169/A`, quarta e sexta 07:30–09:30, Sala 405, com 37 vagas contra 36 permitidos.
- H006: nenhuma etapa violada.

## Candidatos e modelo CP-SAT (fases 4–5)

`candidatos_03.py` gera, em memória, o domínio de cada encontro móvel. Encontros com qualquer curso externo ficam fixos (4 encontros; 285 são móveis). Os candidatos preservam a duração, usam segunda a sexta, evitam o almoço, respeitam capacidade (120%) e laboratório, e removem posições que colidam em sala ou docente com encontros fixos. Conflitos de etapa não são podados aqui: são tratados no modelo. Duas políticas de início:

- padrão: pares início/fim já observados na fonte para a mesma duração;
- `usar_grade_horaria_meia_hora` (usada pela execução da Solução A): inícios `HH:30` de hora em hora, entre o menor e o maior início da fonte, ainda sem horários fora desse padrão. Gera 255.348 candidatos (domínio de 120 a 1.485, média 896) e nenhum domínio vazio.

`modelo_otimizacao_03.py` usa OR-Tools CP-SAT (`ortools==9.15.6755`, declarado em `requirements_03.txt`; Python 3.14.7 no `.venv`). O modelo escolhe exatamente uma posição por encontro móvel e impõe: sem sobreposição de sala e docente (grupos por período de 30 min) e H006 (variável de turma escolhida por disciplina; para cada curso/etapa e período, no máximo uma turma escolhida ocupa o horário). `fixados` e `etapas_toleradas` permitem manter encontros e etapas que já violam hoje. `construir_modelo_cp_sat_diagnostico` serve só a testes de sensibilidade e nunca para gerar entregas.

## Solução A — preservação (fase 6)

`solucao_a_03.py` tem três modos (`--modo`):

- `estrito`: nenhuma violação dura, mesmo as já existentes (objetivo lexicográfico de preservação).
- `fallback` (padrão): mantém fixos os encontros que já violam H003/H008 e tolera etapas já inviáveis (hoje, nenhuma); nunca piora o uso fora do turno-alvo de nenhum curso. Resolve em duas etapas: (1) minimiza a soma dos percentuais fora do turno-alvo (ARQU na tarde; DPRO e DVIS na manhã, mesma definição do item 6 da página Agenda); (2) mantém esse valor e maximiza a preservação lexicográfica: sala/dia/horário, depois dia/horário com troca de sala, dia, padrão semanal e mudanças amplas, com prioridade de turmas e preferências de espaço como desempate.
- `auto`: tenta o estrito e, sem solução, usa o fallback.

Comandos (a partir da raiz):

```powershell
.venv/Scripts/python.exe entregas/atividade03/solucao_a_03.py --preflight
.venv/Scripts/python.exe entregas/atividade03/solucao_a_03.py --limite-segundos 3000 --saida-dir entregas/atividade03/saida_solucao_A
```

Toda execução grava `status_execucao_A.json`. Com `OPTIMAL` e sem violações duras novas, grava `solucao_A.csv/.json/.md`; com `FEASIBLE`, grava `candidato_A.*` (provisório). `INFEASIBLE` e `UNKNOWN` não geram solução. `--preflight` apenas constrói e valida o modelo.

### Resultado (2026-10-04)

Fallback, limite de 3000 s, SHA-256 da fonte `5980965c…`: status `OPTIMAL` em 510 s (315.779 variáveis, 1.757.052 restrições). O ótimo vale para o modelo do fallback, ou seja, com os 3 encontros acima fixos.

| Curso | Fora do turno-alvo (atual) | Fora do turno-alvo (A) |
| --- | ---: | ---: |
| ARQU | 18,55% | 0,0% |
| DPRO | 28,42% | 0,0% |
| DVIS | 21,26% | 0,0% |

- Encontros alterados: 63 de 289. Níveis de preservação: 226 no nível 1, 61 no nível 3 (só mudaram de dia), 2 no nível 5.
- Violações duras novas: 0.
- Regras relaxadas ou toleradas: somente os 3 encontros já violadores acima. H010 tem uma exceção registrada (`ARQ02005/A`, 60 min fora do alvo, mantido da fonte); H003 e H008 permanecem como baseline.

Arquivos em `saida_solucao_A/`: `solucao_A.csv` (20 colunas de origem mais `encontro_id`, `solucao`, `alterado`, `turno_original`, `turno_alvo`, `turno_proposto`, `motivo_alteracao`, `excecao_turno`, `tipo_mudanca`, `status_solver`), `solucao_A.json`, `solucao_A.md` e `status_execucao_A.json`. Uma cópia de `solucao_A.csv` está em `entregas/atividade03/` para a página Streamlit.

### Histórico: viabilidade com a regra anterior

Com a H006 antiga (qualquer sobreposição de etapa proibida), capacidade de 110% e as capacidades originais, o modelo estrito era inviável (`INFEASIBLE`, 31,97 s; a grade original tinha 93 pares H006, 46 encontros acima de 110% e 1 no almoço). Os JSONs `diagnostico_*.json` e `status_execucao_A.json` anteriores em `saida_solucao_A/` registram essa investigação e não refletem o modelo atual. A viabilidade foi resolvida pela definição de H006 por turmas alternativas e pelas novas capacidades.

## Solução B — equilíbrio (fase 7)

`solucao_b_03.py` gerou `saida_solucao_B/candidato_B.csv` com status `FEASIBLE` em 2.572 s de um limite de 3.000 s. A proposta tem 178 encontros alterados e nenhuma violação dura nova. Não se declara ótimo: a candidata é uma proposta viável, sem prova de otimalidade.

As métricas do objetivo de B, usando as mesmas turmas escolhidas pelo modelo, estão em `saida_solucao_B/candidato_B.md` e `.json`. A comparação independente também resume a oferta completa de cada etapa: desvio absoluto médio diário de etapas cai de 3,935 h no ANTES para 2,519 h em B; para docentes, de 1,487 h para 1,261 h. A oferta completa inclui turmas alternativas e não representa a carga de um estudante individual.

## Solução C — turnos (fase 8)

`saida_solucao_C/solucao_C.csv` tem status `OPTIMAL`, 68 encontros alterados e 1 exceção de turno. A CH no alvo, recalculada por turma acadêmica × encontro, é 772/777 h (99,36%) para ARQU, 217/219 h (99,09%) para DPRO e 208/210 h (99,05%) para DVIS.

## Validação e comparação (fases 9–10)

`validar_solucao_03.py` reconstrói a fonte, confere linhagem/colunas e valida os CSVs exportados de A/B/C; não lê estado interno do CP-SAT. Reutiliza as regras executáveis em `restricoes_03.py`, ou seja, é independente dos objetos e resultados internos do solver, mas não mantém uma segunda implementação das regras. Violações baseline são separadas das novas.

Execute a partir da raiz:

```powershell
.venv/Scripts/python.exe entregas/atividade03/validar_solucao_03.py
.venv/Scripts/python.exe -m unittest discover -s entregas/atividade03 -p "test_*.py"
```

A validação gera `validacao_A_B_C.md`, `comparacao_A_B_C.csv`, `excecoes_A_B_C.csv`, `ocupacao_salas_A_B_C.csv`, `ocupacao_salas_por_curso_A_B_C.csv`, `distribuicao_semanal_A_B_C.csv` e `equilibrio_semanal_A_B_C.csv`. CH é contada por turma acadêmica e encontro, sem multiplicar linhas de docentes. O gráfico de ocupação comparativa usa a mesma regra da página inicial: cada encontro físico conta uma vez por curso em cada sala, com barras empilhadas por curso. O total físico da sala continua separado; salas usadas no ANTES e vazias depois ficam marcadas como liberadas.

## Página Streamlit (`app_03.py`)

Execução: `.venv/Scripts/python.exe -m streamlit run entregas/atividade03/app_03.py`.

- **Agenda:** grade atual, com agenda interativa por sala, ocupação das salas nas plantas baixas (`PlantasBaixas.obj`; Plotly, passos de 30 min, cores por curso) e o item 6, uso dos cursos fora do turno-alvo.
- **Propostas A/B/C:** mostram agenda por sala, plantas baixas e métricas específicas; B carrega a candidata viável quando ainda não há arquivo final.
- **Comparação A/B/C:** apresenta CH no alvo, turmas atendidas, mudanças, violações, uso/liberação de salas, distribuição semanal e exceções. Requer os relatórios gerados pelo validador.

## Testes

```powershell
.venv/Scripts/python.exe -m unittest discover -s entregas/atividade03 -p "test_*.py"
```

## Pendências

- B permanece `FEASIBLE`: não há prova de otimalidade; seu uso como proposta viável está sinalizado.
- A origem de `creditos` e a obrigatoriedade das disciplinas não foram confirmadas externamente; operacionalmente, ofertas com etapa diferente de 0 são tratadas como obrigatórias.
- O fluxo foi reproduzido no ambiente atual, mas ainda não em uma instalação limpa. Versões estão fixadas em `requirements_03.txt`.
