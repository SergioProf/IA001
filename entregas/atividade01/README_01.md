# Atividade 01 - Análise e Visualização de Dados

Proposta de análise visual da ocupação dos espaços de ensino da Faculdade de Arquitetura da Universidade Federal do Rio Grande do Sul (UFRGS), referente ao período letivo de 2026/2.

O projeto transforma planilhas administrativas organizadas por sala em uma base única no formato Tidy Data. A partir dela, o notebook explora a distribuição de aulas entre cursos, salas, tipos de espaço, dias e horários, apoiando discussões sobre a organização da grade acadêmica.

## Objetivo

Caracterizar a ocupação regular das salas, ateliers e laboratórios do prédio da Faculdade de Arquitetura e investigar padrões que possam apoiar uma eventual reorganização de horários e espaços. O recorte considera os cursos de Arquitetura e Urbanismo, Design de Produto e Design Visual, além de algumas turmas de outros cursos que utilizam o prédio.

Uma pergunta central da atividade é avaliar, sob a perspectiva da ocupação física, se a distribuição atual permite concentrar Arquitetura e Urbanismo nos turnos da manhã e da noite, e os cursos de Design nos turnos da tarde e da noite.

## Conteúdo

| Arquivo | Descrição |
| --- | --- |
| `atividade01_proposta_analise_visual.ipynb` | Notebook principal com contextualização, exploração, estatísticas, gráficos e perguntas de análise. |
| `mapa_salas_tidy_01.csv` | Base de dados normalizada utilizada no notebook. |
| `dadosBrutos/transformar_mapa_salas.py` | Script que converte a planilha original em CSV Tidy. |
| `dadosBrutos/relatorio_transformacao_mapa_salas.md` | Registro da execução, validações e exceções encontradas. |
| `dicionario_dados_mapa_salas_01.ipynb` | Dicionário de dados da base utilizada nesta atividade. |
| `entregas/atividade01/README_01.md` | Documentação desta entrega. |

## Origem e recorte dos dados

Os dados originais são registros administrativos de alocação de disciplinas, turmas e salas, obtidos no Portal do Servidor da UFRGS por acesso institucional. A versão tratada remove informações pessoais, incluindo nomes de docentes, e contém a programação regular de 23 espaços do prédio para o semestre 2026/2.

O arquivo de origem utilizado na transformação foi `dadosBrutos/MapaSalas.xlsx`. Cada aba representa uma sala e contém:

- metadados da sala, como prédio, tipo e capacidade;
- uma grade semanal com dias, horários e identificadores de turma;
- uma tabela descritiva com disciplina, cursos e vagas oferecidas.

O arquivo original não é necessário para executar a análise sobre o CSV já incluído. Como a fonte depende de acesso institucional, não há URL pública direta para a planilha original.

## Transformação para Tidy Data

O script associa a grade semanal à tabela descritiva pelo identificador da turma, por exemplo `ARQ01045-A/B`, e produz uma tabela em que cada linha representa um encontro de uma turma, de um curso, em uma sala, dia da semana e intervalo contínuo de horários.

As regras principais são:

1. Cada aba do Excel é processada como uma sala.
2. A grade semanal é convertida de colunas de dias e linhas de horários para registros.
3. Turmas compartilhadas, como `A/B`, são desagregadas em turmas individuais.
4. As vagas de turmas compartilhadas são divididas igualmente; em caso de resto, a primeira turma recebe a vaga adicional.
5. Períodos consecutivos da mesma turma, sala e dia são consolidados em um único encontro.
6. Turmas vinculadas a mais de um curso recebem uma linha por curso.

O resultado atual possui 440 registros, 16 atributos, nenhum valor ausente e nenhum registro exatamente duplicado.

## Dicionário resumido

| Coluna | Descrição |
| --- | --- |
| `semestre` | Período letivo da oferta. |
| `predio`, `sala`, `tipo_sala`, `capacidade_turma` | Características do espaço físico. |
| `codigo_disciplina`, `turma`, `nome_disciplina`, `curso` | Identificação acadêmica do encontro. |
| `dia_semana`, `hora_inicio`, `hora_fim`, `numero_periodos` | Agenda do encontro; cada período corresponde a uma hora. |
| `vagas_oferecidas` | Vagas atribuídas à turma individual. |
| `vagas_totais_compartilhadas` | Total original de vagas das turmas que compartilham o encontro. |
| `turmas_compartilhando_sala` | Turmas que ocupam simultaneamente a mesma sala. |

Consulte `dicionario_dados_mapa_salas_01.ipynb`, na mesma pasta desta atividade, para as definições completas e os cuidados metodológicos da base utilizada.

## Como reproduzir

### Requisitos de ambiente

Este projeto foi validado com Python 3.14.7 e as dependências listadas em `entregas/atividade01/requirements_01.txt`.

### Transformar os dados originais

Com o ambiente Python configurado e as dependências instaladas, execute na raiz do projeto:

```powershell
python -m pip install -r entregas/atividade01/requirements_01.txt
python dadosBrutos/transformar_mapa_salas.py
```

O comando gera ou atualiza a base Tidy em UTF-8 com BOM. Para esta entrega, o arquivo utilizado é `mapa_salas_tidy_01.csv`, localizado na mesma pasta do notebook e deste README. O relatório é salvo em `dadosBrutos/relatorio_transformacao_mapa_salas.md`.

### Executar a análise

Instale as bibliotecas do projeto e execute o notebook em ordem, a partir da pasta `entregas/atividade01`:

```powershell
python -m pip install -r requirements_01.txt
jupyter notebook atividade01_proposta_analise_visual.ipynb
```

O notebook calcula total de horas-aula, ocupação por curso, tipo de sala e sala, além de apresentar gráficos de barras e uma agenda semanal da Sala 301A.

## Cuidados na análise

- Para medir ocupação física das salas, deduplique linhas que diferem apenas em `curso`; uma mesma aula pode atender vários cursos.
- Para analisar demanda ou carga horária por curso, mantenha os registros separados por `curso`.
- Não some `vagas_totais_compartilhadas` entre linhas do mesmo encontro compartilhado.
- Horários livres não aparecem no CSV: células vazias da grade original representam ausência de encontro.
- A base representa somente a programação regular de 2026/2. Usos eventuais e restrições como disponibilidade docente ou regras de grade não estão registrados.

## Licença e uso

Não foi identificada uma licença pública para os dados administrativos originais. O material tratado neste repositório destina-se ao uso acadêmico, foi anonimizado e deve respeitar as condições de acesso da UFRGS e a legislação aplicável.
