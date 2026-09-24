# Plano do App Streamlit

## Objetivo

Criar um único `app.py` para responder às três primeiras perguntas da Atividade 01 e atender aos requisitos de desenvolvimento da Atividade 02.

## Perguntas e visualizações

1. **Distribuição das horas de ocupação por curso e dia:** mapa de calor interativo com Plotly, usando `curso`, `dia_semana` e `numero_periodos`.
2. **Variação da ocupação ao longo dos horários:** mapa de calor interativo com Plotly, usando intervalos de uma hora e encontros físicos deduplicados.
3. **Utilização das salas e tipos de espaço:** barras horizontais ordenadas com Matplotlib, usando `sala`, `tipo_sala`, `dia_semana` e `numero_periodos`.

## Preparação dos dados

- Carregar `mapa_salas_tidy_02.csv` com caminho relativo a `app.py`.
- Validar as 17 colunas esperadas e converter atributos numéricos.
- Criar minutos de início/fim e a categoria derivada `turno`.
- Manter uma visão detalhada para comparações por curso.
- Criar uma visão física deduplicada por sala, disciplina, dia, horário e compartilhamento.
- Não somar diretamente `vagas_totais_compartilhadas` entre linhas repetidas.

## Interação e requisitos

- Filtros laterais para curso, sala, tipo de espaço, dia e turno.
- As visualizações são atualizadas a cada alteração dos filtros.
- Seleções sem registros exibem uma mensagem explicativa.
- Todos os gráficos possuem título, eixos, unidades, fonte e texto interpretativo.
- O app utiliza Streamlit como interface e Plotly/Matplotlib como bibliotecas de visualização.

## Análise complementar

- Comparar a ocupação de Arquitetura e Design por turno como análise descritiva.
- Identificar possíveis sobreposições do mesmo docente no mesmo dia.
- Usar os identificadores anonimizados `Prof01`, `Prof02` etc.
- Tratar uma sobreposição como alerta para investigação, não como prova de conflito real.

## Verificação

- Validar a leitura e os tipos da base real.
- Conferir os três agrupamentos com exemplos conhecidos.
- Testar turmas compartilhadas sem duplicar ocupação física.
- Testar filtros com resultados e sem resultados.
- Executar `streamlit run app.py` na pasta `atividade02`.
- Preencher o notebook e atualizar este README com resultados efetivamente observados.

## Limitações

A base representa somente a programação regular de 2026/2. Horários sem registro não garantem disponibilidade operacional, e a análise não contém todas as preferências docentes, regras de grade ou restrições necessárias para propor uma nova grade viável.