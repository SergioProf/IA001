# Atividade 02 - Dashboard interativo com Streamlit

Este trabalho dá continuidade à proposta de análise visual desenvolvida na Atividade 01. A base trata da ocupação regular de salas, ateliers e laboratórios da Faculdade de Arquitetura da UFRGS no período letivo de 2026/2.

**Status:** aplicação implementada e registro da atividade preenchido. A conferência visual de todas as combinações possíveis de filtros continua sendo uma etapa recomendada antes da entrega final.

## Objetivo

Construir uma aplicação em **Streamlit** que permita ao público definido na Atividade 01 explorar os dados e investigar pelo menos duas das perguntas propostas anteriormente. A aplicação deve transformar os gráficos estáticos e as perguntas da primeira atividade em uma experiência interativa, com filtros e textos que apoiem a interpretação.

O dashboard investiga a distribuição da ocupação por curso, dia, horário, sala e tipo de espaço. A pergunta sobre a concentração de Arquitetura e Urbanismo nos turnos da manhã e da noite e dos cursos de Design nos turnos da tarde e da noite é tratada como análise descritiva complementar, não como uma proposta de nova grade viável.

## Entrega prevista

| Arquivo | Situação e descrição |
| --- | --- |
| `atividade02_dashboard_streamlit.ipynb` | Notebook com o enunciado e o registro preenchido do grupo, das perguntas, das visualizações, dos resultados e das limitações. |
| `dicionario_dados_mapa_salas_02.ipynb` | Dicionário de dados e cuidados para a análise da Atividade 02. |
| `mapa_salas_tidy_02.csv` | Base normalizada utilizada pelo dashboard. |
| `app.py` | Aplicação Streamlit com filtros, três visualizações e análise de possíveis sobreposições docentes. |
| `requirements_02.txt` | Dependências fixadas do ambiente para o dashboard e a reprodução do notebook. |
| `PLANO_APP_STREAMLIT.md` | Plano de implementação e critérios de verificação do dashboard. |
| `README_02.md` | Instruções de instalação, execução, escopo e registro da entrega. |

A entrega final também deverá conter eventuais arquivos auxiliares e as instruções necessárias para executar a aplicação localmente.

## Aplicação implementada

O arquivo `app.py` apresenta, nesta ordem:

1. As três perguntas investigadas e a configuração recomendada de filtros para cada uma.
2. Filtros interativos por curso, sala, tipo de espaço, dia da semana e turno.
3. Indicadores de horas-aula físicas, salas utilizadas e cursos no recorte.
4. Mapa de calor de horas por curso e dia, produzido com Plotly.
5. Mapa de calor de ocupação física por dia e horário, produzido com Plotly.
6. Gráfico de barras de horas por sala e tipo de espaço, produzido com Matplotlib.
7. Tabela de possíveis sobreposições de horários por docente anonimizado.
8. Observações metodológicas e checklist dos requisitos da atividade.

Os códigos de curso são apresentados com rótulos mais informativos no dashboard: `ARQU` como Arquitetura e Urbanismo, `DVIS` como Design Visual, `DPRO` como Design de Produto, `CAGR` como Ciências Agrárias e `ENGMEC` como Engenharia Mecânica. Os códigos originais são preservados internamente para os cálculos.

## Requisitos do dashboard

De acordo com a proposta da atividade, a aplicação deverá:

1. Investigar pelo menos duas perguntas da Atividade 01.
2. Apresentar pelo menos três visualizações.
3. Utilizar pelo menos duas bibliotecas de visualização entre Altair, Plotly, Seaborn, Matplotlib e Folium. Streamlit é a estrutura da aplicação e não conta como uma dessas bibliotecas.
4. Oferecer pelo menos dois controles interativos, como filtros de curso, sala, tipo de espaço, dia ou período.
5. Atualizar as visualizações pertinentes quando os filtros forem alterados e informar quando a seleção não produzir dados.
6. Apresentar títulos, rótulos, unidades, fonte dos dados e textos curtos de interpretação.
7. Permitir execução local e ser acompanhado de instruções reproduzíveis.

## Base de dados

O arquivo `mapa_salas_tidy_02.csv` organiza os encontros da programação em formato tidy. Entre as colunas disponíveis estão:

| Grupo | Colunas |
| --- | --- |
| Espaço | `predio`, `sala`, `tipo_sala`, `capacidade_turma` |
| Oferta acadêmica | `codigo_disciplina`, `turma`, `nome_disciplina`, `docente`, `curso` |
| Agenda | `dia_semana`, `hora_inicio`, `hora_fim`, `numero_periodos` |
| Vagas e compartilhamento | `vagas_oferecidas`, `vagas_totais_compartilhadas`, `turmas_compartilhando_sala` |
| Período | `semestre` |

A transformação original associa a grade semanal às informações das turmas, desagrega turmas compartilhadas e consolida períodos consecutivos do mesmo encontro. Para esta atividade, foi necessário incluir também o atributo `docente`, identificando o professor responsável por cada disciplina. Por razões de privacidade, os dados dos docentes foram anonimizados e substituídos por identificadores como `Prof01`, `Prof02` e assim por diante. Essa informação permite considerar, nas análises do dashboard, a possibilidade de conflitos de horário quando o mesmo professor estiver associado a encontros simultâneos ou sobrepostos. Consulte `dicionario_dados_mapa_salas_02.ipynb` antes de definir os cálculos do dashboard.

## Como preparar o ambiente

O ambiente está organizado em `requirements_02.txt` e contém as bibliotecas utilizadas pelo app e pelo notebook:

```text
pandas==3.0.6
matplotlib==3.11.2
streamlit==1.64.0
plotly==7.1.0
jupyter==1.1.1
```

Matplotlib e Plotly são as bibliotecas de visualização; Streamlit organiza a interface, Pandas prepara os dados e Jupyter permite executar e reproduzir o notebook da atividade.

Na pasta `entregas/atividade02`, instale as dependências:

```powershell
python -m pip install -r requirements_02.txt
```

Execute o dashboard com:

```powershell
streamlit run app.py
```

O aplicativo será disponibilizado, por padrão, em `http://localhost:8501`.

O notebook da atividade pode ser aberto no VS Code ou em um ambiente Jupyter já instalado para acompanhar o planejamento e registrar as decisões:

```powershell
jupyter notebook atividade02_dashboard_streamlit.ipynb
```

## Cuidados na análise

- Para medir ocupação física, deduplicar encontros que diferem apenas por `curso`; uma mesma aula pode atender mais de um curso.
- Para analisar demanda ou carga horária por curso, mantenha os registros separados por `curso` e explique essa escolha.
- Não some `vagas_totais_compartilhadas` entre linhas do mesmo encontro compartilhado.
- Compare a capacidade do espaço com as vagas da turma com cuidado: a base pode registrar turmas compartilhadas e a capacidade pode não representar a soma de todas as vagas.
- Horários livres não aparecem no CSV; células vazias da grade original representam ausência de encontro.
- A base representa somente a programação regular de 2026/2. Usos eventuais, disponibilidade docente e outras restrições de montagem de grade não estão registrados.
- A aplicação indica quando filtros combinados não encontram registros, em vez de apresentar gráficos vazios sem explicação.
- A análise de docentes usa identificadores anonimizados, como `Prof01` e `Prof02`. Uma sobreposição indica apenas um conflito potencial na programação registrada.

## Resultados da validação inicial

O carregamento e as funções principais foram testados com `mapa_salas_tidy_02.csv`:

- 454 registros detalhados;
- 290 encontros físicos após a deduplicação;
- 770 períodos horários expandidos para o mapa de calor;
- nenhuma possível sobreposição docente encontrada no arquivo completo durante o teste inicial.

Também foi verificado que o app compila sem erros e inicia localmente com Streamlit. A validação visual de todas as combinações de filtros ainda deve ser feita pelo grupo antes da entrega.

## Checklist de desenvolvimento

- [x] Revisar as perguntas da Atividade 01 e escolher três perguntas para o dashboard.
- [x] Definir o público do dashboard e o que cada visualização deve responder.
- [x] Escolher pelo menos duas bibliotecas de visualização e atualizar `requirements_02.txt`.
- [x] Criar `app.py` e carregar `mapa_salas_tidy_02.csv`.
- [x] Implementar pelo menos dois controles interativos.
- [x] Criar pelo menos três visualizações com títulos, rótulos, unidades e fonte.
- [x] Implementar tratamento para combinações de filtros sem dados.
- [ ] Executar o app e conferir visualmente todas as combinações relevantes de filtros.
- [x] Registrar no notebook as escolhas, um resultado observado, uma limitação, o uso de IA e as referências.
- [x] Atualizar este README com os resultados verificados e o modo de execução.

## Registro da atividade

O registro detalhado do grupo, das perguntas, das visualizações, do uso dos filtros, dos resultados, das limitações, das mudanças em relação à Atividade 01 e do uso de IA está preenchido em `atividade02_dashboard_streamlit.ipynb`.

## Licença e uso

Não foi identificada uma licença pública para os dados administrativos originais. O material tratado neste repositório destina-se ao uso acadêmico e deve respeitar as condições de acesso da UFRGS e a legislação aplicável.
