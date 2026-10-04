# Plano de implementação: reestruturação auditável dos horários

## Objetivo

Implementar a reorganização global das disciplinas ARQU, DPRO e DVIS em fases verificáveis, preservando a estrutura acadêmica e o CSV-fonte. A solução deve produzir três propostas independentes (A: preservação; B: equilíbrio; C: maximização de CH nos turnos-alvo), acompanhadas de validação independente, exceções rastreáveis e comparação reproduzível. Nenhuma alteração da grade ocorre durante auditoria e modelagem. É um detalhamento do `roadmap01.md`, especificado em fases.

## Fases

### 1. Preparação e integridade do dado

Fixar `entregas/atividade03/mapa_salas_tidy_03.csv` como entrada candidata somente após confirmar versão, número de linhas, cabeçalho, tipos, valores ausentes e hash. Confrontar a versão efetiva com `readme_03.md`, os README da raiz e da atividade 02, e a transformação em `dadosBrutos/`. Registrar divergências, a origem das colunas `etapa` e `creditos` e os ajustes manuais citados no README. Não sobrescrever nem normalizar o CSV-fonte.

**Entrega:** inventário e relatório de auditoria inicial (`auditoria_03.md` ou seção equivalente no relatório final).

**Aceite:** cada afirmação de linhagem remete a arquivo/coluna/linha ou fica marcada como não confirmada.

### 2. Unidade de ocupação e modelo canônico

Criar uma representação intermediária determinística, sem editar o CSV, que separe: linha original e sua linhagem; turma acadêmica/matrícula; membro de compartilhamento; encontro físico; ocorrência semanal; docentes; e reserva externa fixa. Tratar qualquer `turmas_compartilhando_sala` com `/` como grupo indivisível; manter juntos todos os membros do mesmo evento físico e as atribuições de docentes. Não usar a contagem bruta de linhas para inferir turmas ou encontros, pois cursos e docentes podem repetir a mesma ocupação.

Definir chaves e regras de deduplicação com testes e exemplos concretos do CSV, incluindo oferta compartilhada entre DPRO/DVIS e encontros múltiplos da mesma disciplina.

**Entrega:** módulo de normalização (`modelo_ocupacao_03.py`) e relatório de reconciliação.

**Aceite:** transformação repetível, sem perda ou duplicação de membros, encontros ou vínculos com as linhas-fonte.

### 3. Auditoria de semântica e baseline “ANTES”

Contabilizar cursos, etapas, disciplinas, grupos, salas, horários, docentes e encontros; procurar duplicidades, inconsistências e padrões semanais. Considerar etapa 0 como eletiva e aplicar a exceção somente ao conflito de estudantes por etapa.

Para capacidade, calcular alunos por membros/turmas físicas únicas do grupo, evitando contar novamente linhas repetidas por curso/docente. Reconciliar com `vagas_totais_compartilhadas`, `vagas_oferecidas` e `vagas_turma`, documentando divergências sem presumir que campos redundantes sejam somáveis.

Definir e documentar os limites dos turnos e como contar CH de encontros que cruzam limites; não inferir a classificação apenas pelo curso ou pelo nome da disciplina. Rodar diagnósticos independentes na grade atual e rotular violações preexistentes como baseline, não como falhas criadas pelo otimizador.

**Entrega:** baseline de CH/percentual no turno-alvo, salas, capacidade, conflitos potenciais, carga semanal por etapa/docente, uso de laboratórios/ateliês e exceções atuais.

**Aceite:** métricas recalculáveis a partir do CSV e regras publicadas.

### 4. Regras executáveis e testes

Implementar módulo de regras (`restricoes_03.py`) com restrições invioláveis separadas das preferências.

Restrições invioláveis:
- Não criar/remover turma ou encontro; preservar frequência, duração, estrutura semanal e compartilhamentos.
- Usar somente segunda a sexta; não permitir encontro sobre o almoço, das 12:30 às 13:30.
- Evitar sobreposição de sala e de docente, inclusive entre cursos.
- Cada etapa/curso deve permitir cursar todas as disciplinas obrigatórias escolhendo uma turma de cada, sem sobreposição entre as escolhidas; turmas da mesma disciplina são alternativas e podem coincidir. Etapa 0 é isenta somente dessa regra de conflito de estudantes.
- Manter cursos externos imóveis e bloqueando recursos.
- Limitar a ocupação a 120% da capacidade da sala.
- Turma dependente de computador só pode ser alocada em laboratório.
- Turno-alvo pode ser relaxado, mas toda exceção deve ter registro e justificativa.

Preferências:
- Preservar, nesta ordem, sala/dia/horário; dia/horário com mudança de sala; dia; padrão semanal; e então mudanças mais amplas.
- Manter sala e tipo de espaço originais quando possível.
- Evitar laboratório para turmas não dependentes de computador e evitar horários muito tardios.
- Preferir aulas consecutivas do docente quando conveniente e equilibrar cargas semanais.
- Priorizar maior número de alunos, obrigatórias e maiores cargas conforme a especificação.

Usar intervalos semiabertos para conflitos de horário, permitindo encontros consecutivos sem intervalo. Criar testes unitários para limites de almoço/turno, sobreposições, compartilhamentos, duração/frequência, capacidade, restrições externas e relaxamentos.

**Entrega:** regras e testes automatizados.

**Aceite:** cada regra tem identificador, severidade, teste e mensagem de diagnóstico compreensível.

### 5. Disponibilidade, candidatos e método de otimização

Montar mapa sala × dia × intervalo, bloqueando todas as turmas externas e ocupações já alocadas; permitir recursos compartilhados apenas se não houver conflito. Gerar inícios somente a partir dos intervalos/estruturas observados no CSV, preservando duração e encontros; não criar horários arbitrários. Restringir salas de encontros dependentes de computador a laboratórios e aplicar a capacidade conforme a semântica confirmada na fase 3.

Avaliar viabilidade e tamanho do problema antes de escolher e fixar uma biblioteca de otimização; as dependências atuais não declaram solver. Registrar versão, instalação e parâmetros. Distinguir “sem solução viável” de “limite de tempo/solução não comprovada”.

**Entrega:** candidatos documentados, dependência fixada e modelo de otimização testável.

**Aceite:** testes comprovam que encontros fixos não mudam e nenhum candidato infringe restrições duras.

### 6. Solução A — preservação

Resolver globalmente, partindo da mesma entrada normalizada e mantendo o máximo de ocupações atuais. Otimizar lexicograficamente as prioridades de preservação especificadas (sala/dia/horário, dia/horário com mudança de sala, dia, padrão semanal, mudanças maiores), sem sacrificar restrições duras.

**Entrega:** `solucao_A.csv`, metadados de mudanças/exceções e métricas.

**Aceite:** a grade tem as mesmas entidades e encontros da origem; toda mudança e relaxamento é rastreável.

### 7. Solução B — equilíbrio

Reutilizar os mesmos dados e restrições; definir métricas quantitativas explícitas de dispersão semanal por etapa obrigatória e por docente, incluindo dias muito leves/pesados sem impor teto fixo diário. Dar maior peso ao equilíbrio, aceitando mais mudanças que A quando isso melhorar a métrica sem quebrar restrições duras.

**Entrega:** `solucao_B.csv`, justificativa dos pesos/objetivos e métricas comparáveis com baseline/A.

**Aceite:** demonstrar a diferença de objetivo em relação a A e comparar o equilíbrio por medidas publicadas.

### 8. Solução C — maximização de turnos

Reutilizar o mesmo modelo e maximizar primeiro a CH nos turnos-alvo (ARQU manhã/noite; DPRO/DVIS tarde/noite), com preferência por início da noite e menor número de alterações como desempate. Contar CH segundo a regra dos encontros que atravessam limites, definida na fase 3.

Relaxar o turno-alvo somente quando necessário e registrar disciplina/turma, alvo, turno obtido, CH, restrição impeditiva e motivo.

**Entrega:** `solucao_C.csv`, relatório de exceções e métricas.

**Aceite:** CH no turno-alvo é o objetivo primário comprovável; em empate, aplicar o desempate por quantidade de alterações.

### 9. Validação independente e comparação

Implementar `validar_solucao_03.py` sem depender do estado interno do solver. Validar A/B/C contra a fonte:
- Contagem e identidade das turmas/encontros.
- Preservação de docentes, estrutura/frequência/duração e compartilhamentos.
- Cursos externos imóveis.
- Conflitos docentes, de sala e de etapa.
- Dias, almoço, laboratório e capacidade.
- Exceções de turno e preservação das colunas originais.

Recalcular métricas lendo os CSVs exportados. Produzir `validacao_A_B_C.md` (ou relatório estruturado equivalente), `comparacao_A_B_C.csv` e `excecoes_A_B_C.csv`, com ANTES × DEPOIS. Violações baseline devem aparecer separadas das novas violações; qualquer nova violação dura bloqueia a entrega da solução.

**Entrega:** resultados e logs reproduzíveis.

**Aceite:** zero violações duras introduzidas e totais conciliados; exceções explicam todos os turnos-alvo não atendidos.

### 10. Entrega reproduzível e visualização

Documentar ambiente, comandos, versões, sementes/parâmetros, ordem de execução e caminhos de entrada/saída em `readme_03.md`. Manter o CSV original intacto e salvar cada solução separadamente, com todas as colunas originais e colunas adicionais documentadas (`solucao`, `alterado`, turnos, motivo, exceção e tipo de mudança).

Gerar tabelas/gráficos ANTES × A/B/C para CH por curso/turno, ocupação de salas, distribuição semanal das etapas e docentes, salas liberadas e exceções. Não misturar a interface Streamlit existente com o solver, salvo necessidade validada.

**Aceite:** uma execução limpa reproduz os arquivos e os mesmos indicadores a partir da fonte congelada.

## Arquivos relevantes

- `entregas/atividade03/especificacoes.md`: regras, prioridades, métricas, soluções e validação requerida.
- `entregas/atividade03/roadmap01.md`: ordem de microetapas e estrutura de entrega já proposta.
- `entregas/atividade03/mapa_salas_tidy_03.csv`: candidata a entrada imutável; o cabeçalho observado contém 20 colunas.
- `entregas/atividade03/readme_03.md`: histórico, ajustes manuais e discrepâncias a reconciliar com a versão real do CSV.
- `entregas/atividade03/app_03.py`: referência para checagem de colunas, horários em minutos, classificação de turno, chave de evento físico e relatório de sobreposição; não é solver nem validador completo.
- `entregas/atividade03/requirements_03.txt`: dependências atuais do dashboard; verificar e registrar eventual dependência nova do solver/testes.
- `entregas/atividade02/app.py`: referência adicional para deduplicação de eventos e sobreposição, sem assumir que conflitos possíveis confirmam indisponibilidade real.
- `dadosBrutos/transformar_mapa_salas.py` e `dadosBrutos/relatorio_transformacao_mapa_salas.md`: linhagem da transformação; a fotografia antiga não substitui automaticamente o CSV posterior da atividade 03.

## Verificação

1. **Auditoria:** registrar hash, linhas, colunas e tipos; reconciliar divergências documentais e origem dos campos sem editar a entrada.
2. **Normalização:** testar chaves, deduplicação de linhas por curso/docente, membros compartilhados, ocorrências semanais e correspondência reversível às linhas-fonte.
3. **Regras:** testar sobreposição semiaberta, almoço inclusive nos limites, sábado, capacidade em 100%/120%/acima de 120%, salas/laboratórios, docentes, etapa 0 e externas fixas.
4. **Soluções:** validar independentemente A/B/C e conferir que nenhuma entidade/encontro foi criado/removido nem teve estrutura alterada.
5. **Métricas:** recalcular CH/percentuais, alterações e equilíbrio a partir dos arquivos exportados; conciliar cada exceção com sua justificativa e restrição.
6. **Reprodutibilidade:** executar o fluxo documentado em ambiente limpo; não usar `streamlit run` como validação do otimizador. Não há atualmente comando de teste/solver identificado nos arquivos inspecionados; definir o comando quando a estrutura de testes e a dependência forem escolhidas.

## Decisões e limites

- Etapa 0 é eletiva e pode ignorar somente a regra de conflito obrigatório por etapa; não fica isenta de conflitos de docente/sala nem das demais restrições.
- Capacidade representa o total de pessoas que ocupa o espaço físico. Somar membros físicos únicos de grupos compartilhados e deduplicar repetições por curso/docente; reconciliar esse cálculo com campos agregados, sem somar cópias de linhas.
- Horários candidatos devem usar inícios/estruturas já observados, sem inventar intervalos.
- A fonte original permanece intacta; soluções A/B/C, validações e exceções são artefatos separados.
- Salas desocupadas no CSV não provam disponibilidade operacional fora da premissa declarada; reservas externas registradas são fixas e bloqueiam recursos.
- Não iniciar a otimização enquanto versão do CSV, chaves de ocupação, limites de turnos e forma de contar CH não estiverem documentados e testados.
- Fora de escopo: criar/remover/fundir/dividir turmas, alterar docentes, editar o CSV-fonte ou executar a reorganização durante as fases de planejamento.
