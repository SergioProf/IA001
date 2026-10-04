# Auditoria de dados — Fase 01

**Data da auditoria:** 2026-10-03  
**Escopo:** inventário e verificação somente leitura da base a usar na reorganização.  
**Fonte canônica:** `entregas/atividade03/mapa_salas_tidy_03.csv`.

## Decisão sobre a fonte

Por orientação do responsável pelo projeto, o arquivo `mapa_salas_tidy_03.csv` é a base original a considerar. O README está desatualizado e será atualizado depois da conclusão do trabalho. O CSV da raiz e a descrição atual do README não foram usados como critério para aceitar ou rejeitar a fonte da atividade 03.

O CSV-fonte não foi alterado pela auditoria. Em 2026-10-04 a coluna `capacidade_sala` foi editada manualmente (Salas 403, 404, 405 e 414: 30; 407: 15; 304: 60; 503: 40; 94 linhas), o que mudou o hash. As seções abaixo refletem a versão atual; os achados da versão anterior (hash `6101ab29…`) são citados apenas como histórico.

## Integridade e esquema

| Verificação | Resultado |
| --- | --- |
| Arquivo | `entregas/atividade03/mapa_salas_tidy_03.csv` |
| Tamanho | 72.799 bytes |
| SHA-256 | `5980965c9e96effa0d44f879551425e2f67f44b2c6b81cb7cc3e4fcd6a10c086` |
| Registros | 452 |
| Colunas | 20 |
| Período registrado | `2026/2` em todas as 452 linhas |
| Valores ausentes | 0 |
| Campos de texto vazios | 0 |
| Linhas exatamente duplicadas | 0 |
| Horários fora do formato `HH:MM` | 0 |
| Divergências entre duração e `numero_periodos` | 0 |

Cabeçalho, na ordem do arquivo:

```text
semestre,predio,sala,capacidade_sala,tipo_sala,vagas_turma,codigo_disciplina,turma,nome_disciplina,docente,curso,dia_semana,hora_inicio,hora_fim,numero_periodos,vagas_oferecidas,vagas_totais_compartilhadas,turmas_compartilhando_sala,etapa,creditos
```

As colunas numéricas inferidas são `capacidade_sala`, `vagas_turma`, `numero_periodos`, `vagas_oferecidas`, `vagas_totais_compartilhadas`, `etapa` e `creditos` (inteiros). As demais 13 colunas foram lidas como texto.

## Conteúdo observado

- Cursos por quantidade de linhas: ARQU 277, DPRO 87, DVIS 83, CAGR 3 e ENGMEC 2. CAGR e ENGMEC estão fora do conjunto-alvo ARQU/DPRO/DVIS.
- 123 códigos de disciplina, 278 combinações únicas de curso/código/turma, 127 docentes e 23 salas.
- Tipos de espaço: Atelier 246 linhas, Sala de aula 139, Laboratório de Informática 67.
- 184 linhas têm `/` em `turmas_compartilhando_sala`; o total de linhas não representa a quantidade de ocupações físicas, pois cursos e grupos compartilhados são expandidos no CSV.
- Dias registrados: segunda 102, terça 106, quarta 94, quinta 103 e sexta 47. Não há linhas em sábado, domingo ou outro dia.
- Inícios entre 07:30 e 20:30; encerramentos entre 08:30 e 22:30.
- Distribuição de `etapa`: 0: 60, 1: 70, 2: 56, 3: 61, 4: 38, 5: 34, 6: 32, 7: 34, 8: 33 e 9: 34.
- Distribuição de `creditos`: 1: 12, 2: 57, 3: 26, 4: 171, 6: 72, 7: 18, 9: 24 e 10: 72.
- Cada sala tem um único valor de `capacidade_sala` no arquivo; não foram encontrados valores conflitantes para uma mesma sala. Valores atuais ajustados manualmente: Salas 403, 404, 405 e 414 com 30; 407 com 15; 304 com 60; 503 com 40.

## Verificações de horários

Foi encontrada uma linha que cruza o intervalo de almoço definido nas especificações (12:30–13:30):

| Disciplina | Turma | Dia | Horário |
| --- | --- | --- | --- |
| ARQ02005 | A | SEGUNDA-FEIRA | 09:30–13:30 |

Este é um achado da grade atual para o baseline. Não foi corrigido nesta fase. A conferência entre `hora_inicio`, `hora_fim` e `numero_periodos` não encontrou divergências: a duração registrada coincide com o número de períodos em todas as linhas.

## Linhagem e discrepâncias documentais

- `dadosBrutos/MapaSalas.xlsx`, `dadosBrutos/transformar_mapa_salas.py` e `dadosBrutos/relatorio_transformacao_mapa_salas.md` estão presentes.
- O relatório de transformação descreve uma saída histórica com 23 abas, 454 registros e 17 colunas. A saída `dadosBrutos/mapa_salas_tidy.csv` não está presente no workspace; portanto, não foi possível comparar linha a linha a versão atual com aquela saída.
- O script histórico declara a coluna `capacidade_turma`; o CSV 03 tem `capacidade_sala` e `vagas_turma`. O script e o relatório histórico não contêm `etapa` nem `creditos`. A origem curricular de `etapa` foi confirmada por comparação com `dadosBrutos/curriculos.xlsx`; a origem e a regra de associação de `creditos` permanecem pendentes. A relação semântica entre `capacidade_sala` e `vagas_turma` também não pode ser confirmada. Não presumir equivalência entre nomes ou somar campos de vagas sem validar sua semântica.
- O README registra alterações posteriores envolvendo ARQ01013, ARQ01046, ARQ01090 e ARQ01091. No CSV 03, observa-se que ARQ01013 A/C/D somam 10 períodos por turma; ARQ01046 tem quatro linhas, uma ocorrência de 3 períodos por turma (A/B na sexta e C/D na quarta); e os créditos de ARQ01090 e ARQ01091 são 1. Como o README foi informado como desatualizado e não há a saída tidy histórica para comparação, esses dados confirmam o estado atual do CSV, mas não comprovam por si só o histórico ou a autoria dos ajustes.
- A base da raiz possui 452 linhas e 19 colunas, enquanto a fonte canônica 03 possui 452 linhas e 20 colunas. Ela não foi usada como autoridade, conforme orientação do responsável. Uma comparação posterior somente leitura encontrou as mesmas 278 chaves `curso`/`codigo_disciplina`/`turma` e zero divergências em `etapa` ou `creditos` entre a base da raiz e a fonte 03. Essa concordância corrobora consistência entre as duas cópias disponíveis, mas não confirma a origem original, a chave de associação nem a correção semântica dos atributos.
- `curriculos.xlsx`, planilha `Sheet1`, organiza três cursos em blocos com seções `Etapa 1`–`Etapa 10` e linhas de disciplinas com `Código` e `Caráter`. A comparação por curso/código encontrou 119 códigos obrigatórios com etapa igual à do CSV 03. `ARQ01098` consta como `Alternativa` na Etapa 10, e suas turmas têm `etapa=0` no CSV, de acordo com a convenção de eletivas desta atividade. Outros 36 códigos do CSV não aparecem no currículo específico do curso e todos têm `etapa=0`. Não foram encontradas outras divergências de etapa nos códigos cobertos pelo workbook. Essa verificação confirma a correspondência curricular observada; a origem e a chave de associação de `creditos` continuam pendentes.

## Conclusão da fase

A auditoria de integridade e inventário do CSV 03 está concluída: o arquivo foi lido sem alteração e não apresenta ausências, linhas idênticas duplicadas, horários malformados ou divergências de duração. A associação de `etapa` foi conferida contra o currículo, e foram registrados um cruzamento de almoço e questões restantes de linhagem/semântica.

**Pendências para etapas seguintes:** confirmar a origem e a regra de associação de `creditos`; esclarecer o significado de `vagas_turma` frente a `capacidade_sala`; e preservar o achado de almoço como condição do baseline até sua resolução sob as regras do projeto.

**Arquivos não modificados nesta fase:** CSV canônico, demais CSVs, script de transformação e READMEs.

## Fase 2 — Modelo canônico e reconciliação

**Implementação:** `modelo_ocupacao_03.py` normaliza o CSV em memória. A fonte não é reescrita nem convertida automaticamente em outro arquivo. O modelo mantém as 20 colunas originais por linha, o número físico da linha no CSV (cabeçalho na linha 1) e IDs determinísticos derivados de SHA-256.

### Entidades e chaves

| Entidade | Chave de identidade | Conteúdo e regra |
| --- | --- | --- |
| Linha-fonte | Número físico da linha CSV | Guarda todos os valores originais e os IDs das entidades associadas. |
| Turma acadêmica | `semestre`, `curso`, `codigo_disciplina`, `turma` | Mantém `etapa`, `creditos` e nome no âmbito do curso; repetições devem concordar nesses metadados. |
| Padrão semanal | `semestre`, `codigo_disciplina`, `turmas_compartilhando_sala` | Agrupa encontros físicos do mesmo grupo declarado ao longo da semana. |
| Membro compartilhado | Chave do padrão semanal + token de `turma` | `A/AA` é interpretado como os tokens exatos `A` e `AA`; uma linha só pertence se `turma` for um desses tokens. |
| Encontro físico | `semestre`, `predio`, `sala`, `codigo_disciplina`, `dia_semana`, `hora_inicio`, `hora_fim`, `turmas_compartilhando_sala` | Curso, turma acadêmica e docente não entram na chave: suas linhas podem descrever a mesma ocupação física. Os atributos físicos devem concordar dentro do encontro. |
| Atribuição docente | ID do encontro + ID do membro + `docente` | Linhas de cursos distintos são reunidas quando descrevem o mesmo docente ensinando o mesmo membro no mesmo encontro; cursos e linhas-fonte permanecem vinculados à atribuição. |

Os IDs de entidades usam os componentes da chave serializados de forma estável e um digest SHA-256 truncado. A identidade do encontro não depende da ordem das linhas. `vagas_turma`, `vagas_oferecidas` e `vagas_totais_compartilhadas` permanecem nos registros de origem e não são somadas nesta fase.

### Reconciliação no CSV 03

| Camada | Quantidade |
| --- | ---: |
| Linhas-fonte preservadas | 452 |
| Turmas acadêmicas distintas | 278 |
| Membros de compartilhamento por padrão semanal | 227 |
| Atribuições docentes distintas | 376 |
| Encontros físicos | 289 |
| Padrões semanais | 184 |

As 452 linhas estão ligadas exatamente uma vez a um encontro físico, e cada uma continua acessível com todas as suas colunas originais. Todos os membros declarados estão representados em cada encontro físico do CSV. As 376 atribuições docentes também retêm as linhas de origem e todas as turmas acadêmicas relacionadas; a diferença decorre de registros repetidos para cursos diferentes numa oferta compartilhada, não de descarte de linhas.

Exemplos conferidos no CSV:

- `ARQ01045`, grupo `C/D`, segunda-feira 09:30–12:30: as linhas 2–3 descrevem um encontro, com membros `C` e `D` e docentes associados separadamente. O grupo `A/B` da quarta-feira é outro padrão, não uma ocorrência do grupo `C/D`.
- `ARQ03067`, grupo `A/AA`: as linhas 6–9 (terça-feira) formam um encontro físico; as linhas 10–13 (quinta-feira) formam outro. Ambos pertencem ao mesmo padrão semanal. As linhas repetidas entre DPRO e DVIS permanecem ligadas às respectivas turmas acadêmicas, sem multiplicar o espaço físico ou a mesma atribuição docente.
- Foram encontrados eventos físicos em que `etapa` varia entre cursos. Por isso, etapa e créditos pertencem à turma acadêmica, não são atributos invariantes da ocupação física.

### Validação e limites

Os testes em `test_modelo_ocupacao_03.py` cobrem oferta compartilhada entre cursos, múltiplos encontros semanais, metadados acadêmicos por curso, linhagem reversível, estabilidade dos IDs, rejeição de membro incompatível ou ausente e leitura integral do CSV real. Execução: `python -m unittest discover -s entregas/atividade03 -p "test_modelo_ocupacao_03.py" -v` — 6 testes passaram.

O SHA-256 atual do CSV é `5980965c9e96effa0d44f879551425e2f67f44b2c6b81cb7cc3e4fcd6a10c086` (mudou da fase 1 por causa do ajuste de capacidades; a estrutura de linhas e encontros é a mesma). Nenhuma dependência foi adicionada.

O padrão semanal agrupa pelo código da disciplina e pelo grupo declarado, não afirma equivalência de vagas nem define uma regra de capacidade. Reservas externas, regras de conflito e classificação de turnos continuam fora do escopo desta fase; serão tratadas nas fases de baseline e restrições. A normalização não reorganiza nem altera a grade.

**Arquivos adicionados:** `modelo_ocupacao_03.py` e `test_modelo_ocupacao_03.py`. **Arquivo atualizado:** este relatório de auditoria.

## Fase 3 — Auditoria semântica e baseline ANTES

**Implementação:** `auditoria_baseline_03.py`; **resultado reproduzível:** `baseline_03.md`; **teste:** `test_auditoria_baseline_03.py`. Gerar novamente com `python entregas/atividade03/auditoria_baseline_03.py`. O relatório inclui o SHA-256 da fonte, atualmente igual ao hash registrado nas fases anteriores.

### Regras publicadas

- A unidade física é o encontro canônico; cursos, docentes e membros repetidos nas linhas não multiplicam sala nem conflito.
- Turnos: manhã antes de 12:30; tarde de 13:30 a 18:30; noite a partir de 18:30. O almoço (12:30–13:30) fica fora dos turnos. CH por turno é a interseção em horas do intervalo de relógio com cada janela, dividindo encontros que atravessam limites. O percentual-alvo usa como denominador `numero_periodos` por encontro e curso.
- Ocupação física usa `vagas_oferecidas` somadas uma vez por membro único (`turma`). O total é confrontado com `vagas_totais_compartilhadas`; `vagas_turma` é comparada separadamente, sem presumir equivalência. O limite é 120% da capacidade da sala.
- Conflito de etapa (H006): em cada curso-alvo e etapa diferente de 0, deve existir uma turma por disciplina sem sobreposição entre as escolhidas; turmas da mesma disciplina são alternativas e podem coincidir. A etapa 0 continua considerada em conflitos de sala/docente. Diagnósticos incluem cursos externos registrados.
- Cargas por etapa/docente somam `numero_periodos` por encontro físico. Padrões semanais são contados pela quantidade de encontros canônicos associados.

### Resultado observado

| Métrica | Resultado |
| --- | ---: |
| Linhas / cursos / etapas-curso / disciplinas-curso | 452 / 5 / 32 / 158 |
| Grupos acadêmicos / salas / horários distintos / docentes | 278 / 23 / 92 / 127 |
| Padrões semanais / encontros físicos / duplicatas exatas | 184 / 289 / 0 |
| Frequência: 1, 2 e 3 encontros por padrão | 99, 65 e 20 padrões |
| Encontros acima de 120% da capacidade | 2 |
| Baseline: conflitos de sala / docente / etapas sem combinação de turmas válida (H006) | 0 / 0 / 0 |
| Encontros cruzando o almoço | 1 |

No CSV real, a soma de `vagas_oferecidas` por membros únicos reconcilia com `vagas_totais_compartilhadas` em todos os encontros. Em 277 encontros há diferença entre essa soma e `vagas_turma`; por isso esse campo permanece reportado como divergente, sem ser usado como substituto ou somado aos demais. A maior ocupação calculada é 123,33%; os 2 encontros acima do limite são os dois encontros semanais de `ENG01169`, grupo A (quarta e sexta, 07:30–09:30, Sala 405, 37 vagas contra capacidade 30), detalhados no baseline. Com as capacidades originais e o limite de 110%, eram 46 encontros e a maior ocupação era 308,33%.

Nenhuma etapa de curso-alvo fica sem combinação de turmas válida e não há conflitos de sala ou docente no baseline. (Pela regra anterior, que tratava toda sobreposição de etapa como conflito, havia 93 pares; ela foi substituída porque turmas da mesma disciplina são alternativas.) A ocorrência `ARQ02005`, grupo A, na segunda-feira, 09:30–13:30, cruza o almoço e permanece como exceção preexistente; uma hora de relógio desse evento não é atribuída a turno.

As horas-alvo calculadas são: ARQU 447 h (81,27% de 550 períodos), DPRO 131 h (71,58% de 183) e DVIS 137 h (78,74% de 174). Essas métricas medem o baseline, não uma proposta reorganizada. As cargas completas por etapa/dia, docente/dia e os diagnósticos individualizados estão em `baseline_03.md` e no resultado de `auditar_baseline`.

**Validação:** `python -m unittest discover -s entregas/atividade03 -v` — 48 testes passaram (suite completa, 2026-10-04). A auditoria não altera o CSV-fonte.
