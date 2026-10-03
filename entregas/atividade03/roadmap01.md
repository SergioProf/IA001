# Roadmap — Reorganização das turmas

## Estratégia
Não pedir ao agente para reorganizar tudo de uma vez. Trabalhar em microetapas, validando cada uma antes da próxima.

## 1. Auditoria
Ler o CSV e verificar colunas, cursos, etapas, disciplinas, turmas, docentes, salas, horários, compartilhamentos, ausências, duplicidades e inconsistências.
**Não alterar dados.**
Saída: relatório de auditoria.

## 2. Unidade de ocupação
Interpretar `turmas_compartilhando_sala`, identificar grupos compartilhados, somar vagas, associar docentes e preservar a estrutura semanal.
Saída: estrutura intermediária sem alterar o original.

## 3. Modelo de restrições
Transformar as especificações em regras computáveis: conflitos, capacidade, espaços, turnos, estrutura semanal e preferências.
Saída: módulo/estrutura de regras testável.

## 4. Baseline
Medir a situação atual: ocupação por sala/curso/turno, CH, conflitos, capacidade, uso de laboratórios/ateliês, distribuição das etapas e docentes.
Este é o **ANTES**.

## 5. Disponibilidade
Criar mapa de sala × dia × horário, considerando capacidade, tipo de espaço, compartilhamentos e turmas externas fixas.

## 6. Função de custo
Criar critérios quantitativos configuráveis para:
- atendimento ao turno;
- CH no turno-alvo;
- mudanças de sala/dia/horário;
- deslocamento de turmas já compatíveis;
- equilíbrio de etapas;
- equilíbrio de docentes;
- noite tardia;
- prioridades entre turmas.

## 7. Solução A — Preservação
Minimizar alterações. Priorizar manter turmas já compatíveis, sala, dia, horário e padrão semanal. Produzir grade, alterações e exceções.

## 8. Validação A
Validação independente de todas as regras.

## 9. Solução B — Equilíbrio
Partir dos mesmos dados e regras, mas aumentar o peso da distribuição semanal de etapas e docentes. Pode aceitar mais mudanças. Produzir grade, alterações e exceções.

## 10. Validação B
Mesma validação independente + comparação do equilíbrio com original e A.

## 11. Solução C — Turnos
Maximizar CH no turno-alvo:
- ARQU: manhã/noite;
- DPRO/DVIS: tarde/noite.
Em empate, menor número de alterações.
Preferir início da noite.

## 12. Validação C
Validar especialmente CH no turno-alvo, exceções, conflitos, capacidade, compartilhamentos e estrutura semanal.

## 13. Comparação A × B × C
Gerar tabela comparativa com CH e % no turno-alvo, exceções, alterações, conflitos, capacidade e equilíbrio de etapas/docentes.

## 14. Exceções
Criar relatório detalhado: disciplina, turma, curso, etapa, CH, original, proposta, turno desejado, turno efetivo, sala e motivo/restrição.

## 15. Visualizações
Criar ANTES × DEPOIS:
- ocupação por turno;
- CH por curso/turno;
- heatmaps de salas;
- distribuição semanal;
- carga das etapas;
- carga dos docentes;
- salas liberadas;
- exceções.

## 16. Entrega
Manter:
- CSV original;
- soluções A/B/C;
- validações;
- comparação;
- exceções;
- notebook;
- código.

Tudo deve ser reproduzível.

## Estrutura
```text
CSV original
  ↓
1 Auditoria
  ↓
2 Unidade de ocupação
  ↓
3 Restrições
  ↓
4 Baseline
  ↓
5 Disponibilidade
  ↓
6 Função de custo
  ↓
A / B / C
  ↓
Validação
  ↓
Comparação
  ↓
Exceções
  ↓
Visualização
  ↓
Entrega
```

## Prompt de cada etapa
Cada prompt futuro deve conter:
1. contexto;
2. arquivos permitidos;
3. arquivos proibidos;
4. objetivo;
5. regras relevantes;
6. tarefas;
7. critérios de aceitação;
8. testes;
9. instrução para parar ao concluir.

O agente deve executar somente uma etapa por vez.
