# Dashboard interativo da Atividade 03.
#
# O aplicativo transforma a proposta de análise da Atividade 01 em uma interface
# interativa. A fonte de dados e este arquivo ficam na mesma pasta, o que torna
# a execução reproduzível com `streamlit run app.py`.

from pathlib import Path
import html as html_lib

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components


# -----------------------------------------------------------------------------
# Configuração geral e constantes
# -----------------------------------------------------------------------------

# O caminho é construído a partir da localização deste arquivo, e não do
# diretório em que o comando foi digitado. Assim, o app funciona mesmo quando
# o usuário o inicia a partir da raiz do projeto.
PASTA_APP = Path(__file__).resolve().parent
CAMINHO_DADOS = PASTA_APP / "mapa_salas_tidy_03.csv"
CAMINHO_OBJ = PASTA_APP / "PlantasBaixas.obj"
CAMINHO_SOLUCOES = {
    codigo: PASTA_APP / f"solucao_{codigo}.csv"
    for codigo in ("A", "B", "C")
}

# Estas colunas identificam um encontro físico da disciplina. A coluna `curso`
# fica fora da chave porque a mesma aula pode aparecer uma vez para cada curso
# atendido. A coluna `turmas_compartilhando_sala` ajuda a distinguir encontros
# diferentes que acontecem no mesmo horário e na mesma sala.
CHAVE_ENCONTRO_FISICO = [
    "sala",
    "codigo_disciplina",
    "dia_semana",
    "hora_inicio",
    "hora_fim",
    "turmas_compartilhando_sala",
]

ORDEM_DIAS = [
    "SEGUNDA-FEIRA",
    "TERÇA-FEIRA",
    "QUARTA-FEIRA",
    "QUINTA-FEIRA",
    "SEXTA-FEIRA",
]

COLUNAS_OBRIGATORIAS = {
    "semestre",
    "predio",
    "sala",
    "tipo_sala",
    "capacidade_sala",
    "vagas_turma",
    "codigo_disciplina",
    "turma",
    "nome_disciplina",
    "docente",
    "curso",
    "dia_semana",
    "hora_inicio",
    "hora_fim",
    "numero_periodos",
    "vagas_oferecidas",
    "vagas_totais_compartilhadas",
    "turmas_compartilhando_sala",
    "etapa",
    "creditos",
}

# Os códigos permanecem na coluna original para preservar a integridade dos
# filtros e dos agrupamentos. Estes nomes são usados apenas na interface, para
# que o usuário não precise interpretar siglas institucionais.
ROTULOS_CURSO = {
    "ARQU": "Arquitetura e Urbanismo",
    "DVIS": "Design Visual",
    "DPRO": "Design de Produto",
    "CAGR": "Ciências Agrárias",
    "ENGMEC": "Engenharia Mecânica",
}


# -----------------------------------------------------------------------------
# Leitura e preparação dos dados
# -----------------------------------------------------------------------------


@st.cache_data
def carregar_dados(caminho_dados: str) -> pd.DataFrame:
    # Lê o CSV, valida a estrutura e cria colunas úteis para o dashboard.
    # O cache evita que o arquivo seja lido novamente a cada interação com um
    # filtro. O caminho é recebido como texto para que o Streamlit consiga
    # acompanhar a dependência de forma estável.

    dados = pd.read_csv(caminho_dados, encoding="utf-8-sig")

    # Validar as colunas logo no início produz uma mensagem objetiva quando o
    # CSV for trocado por engano ou estiver incompleto.
    colunas_faltantes = COLUNAS_OBRIGATORIAS.difference(dados.columns)
    if colunas_faltantes:
        colunas_formatadas = ", ".join(sorted(colunas_faltantes))
        raise ValueError(f"Colunas obrigatórias ausentes: {colunas_formatadas}")

    # Essas colunas são quantitativas. A conversão torna os agrupamentos e as
    # comparações confiáveis mesmo que o CSV tenha sido editado manualmente.
    colunas_numericas = [
        "capacidade_sala",
        "vagas_turma",
        "numero_periodos",
        "vagas_oferecidas",
        "vagas_totais_compartilhadas",
        "etapa",
        "creditos",
    ]
    for coluna in colunas_numericas:
        dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")

    # Um horário no formato HH:MM é convertido para minutos desde meia-noite.
    # Essa representação permite ordenar horários e testar sobreposições sem
    # comparar textos como se fossem números.
    dados["inicio_minutos"] = dados["hora_inicio"].map(horario_para_minutos)
    dados["fim_minutos"] = dados["hora_fim"].map(horario_para_minutos)

    # A classificação em turnos é uma aproximação analítica baseada no horário
    # inicial do encontro. O intervalo de almoço não possui registros na base.
    dados["turno"] = dados["inicio_minutos"].map(classificar_turno)

    return dados


def horario_para_minutos(horario: str) -> int:
    # Converte um horário HH:MM para minutos desde 00:00.

    horas, minutos = str(horario).split(":")
    return int(horas) * 60 + int(minutos)


def classificar_turno(inicio_minutos: int) -> str:
    # Classifica o início de uma aula em manhã, tarde ou noite.

    if inicio_minutos < 12 * 60 + 30:
        return "Manhã"
    if inicio_minutos < 18 * 60 + 30:
        return "Tarde"
    return "Noite"


def criar_visao_fisica(dados: pd.DataFrame) -> pd.DataFrame:
    # Retorna uma linha por encontro físico, sem duplicação por curso.
    # A base detalhada contém várias linhas quando uma disciplina atende mais de
    # um curso ou quando turmas compartilham a sala. Para medir o uso físico do
    # espaço, essas linhas representam o mesmo evento e não devem ser somadas
    # várias vezes.

    return dados.drop_duplicates(subset=CHAVE_ENCONTRO_FISICO).copy()


def aplicar_filtros(
    dados: pd.DataFrame,
    cursos: list[str],
    salas: list[str],
    tipos_sala: list[str],
    dias: list[str],
    turnos: list[str],
    etapas: list[int],
    creditos: list[int],
) -> pd.DataFrame:
    # Aplica os filtros escolhidos pelo usuário.
    # Cada lista vazia representa a opção "Todos". O filtro é feito com uma
    # cópia para evitar alterações acidentais no DataFrame armazenado em cache.

    dados_filtrados = dados.copy()
    filtros = {
        "curso": cursos,
        "sala": salas,
        "tipo_sala": tipos_sala,
        "dia_semana": dias,
        "turno": turnos,
        "etapa": etapas,
        "creditos": creditos,
    }

    for coluna, valores in filtros.items():
        if valores:
            dados_filtrados = dados_filtrados[
                dados_filtrados[coluna].isin(valores)
            ]

    return dados_filtrados


# -----------------------------------------------------------------------------
# Agregações para as três perguntas da Atividade 01
# -----------------------------------------------------------------------------


def horas_por_curso_e_dia(dados: pd.DataFrame) -> pd.DataFrame:
    # Soma horas por curso e dia para responder à primeira pergunta.

    resultado = (
        dados.groupby(["curso", "dia_semana"], as_index=False)["numero_periodos"]
        .sum()
        .rename(columns={"numero_periodos": "horas_aula"})
    )

    # Reindexar para manter os dias na ordem da semana, inclusive quando um
    # filtro deixa algum dia sem registros.
    resultado["dia_semana"] = pd.Categorical(
        resultado["dia_semana"], categories=ORDEM_DIAS, ordered=True
    )
    return resultado.sort_values(["curso", "dia_semana"])


def expandir_encontros_em_horas(dados: pd.DataFrame) -> pd.DataFrame:
    # Cria uma linha para cada hora ocupada de um encontro físico.
    # A base registra o começo e o fim de um intervalo contínuo. Para construir
    # o mapa de calor horário, cada período de uma hora é representado por uma
    # linha. O intervalo final é exclusivo: uma aula 09:30-12:30 ocupa 09:30,
    # 10:30 e 11:30, totalizando três períodos.

    registros_horarios = []
    for _, encontro in dados.iterrows():
        inicio = int(encontro["inicio_minutos"])
        fim = int(encontro["fim_minutos"])

        for inicio_periodo in range(inicio, fim, 60):
            registros_horarios.append(
                {
                    "dia_semana": encontro["dia_semana"],
                    "inicio_minutos": inicio_periodo,
                    "horario": minutos_para_horario(inicio_periodo),
                    "horas_aula": 1,
                }
            )

    return pd.DataFrame(registros_horarios)


def minutos_para_horario(minutos: int) -> str:
    # Converte minutos desde meia-noite para HH:MM.

    horas = minutos // 60
    minutos_resto = minutos % 60
    return f"{horas:02d}:{minutos_resto:02d}"


def horas_por_sala_e_curso(dados: pd.DataFrame) -> pd.DataFrame:
    # Soma horas por sala e curso, contando cada encontro uma vez por curso.

    encontros_por_curso = dados.drop_duplicates(
        subset=CHAVE_ENCONTRO_FISICO + ["curso"]
    )
    return (
        encontros_por_curso.groupby(
            ["sala", "tipo_sala", "curso"], as_index=False
        )["numero_periodos"]
        .sum()
        .rename(columns={"numero_periodos": "horas_aula"})
    )


# -----------------------------------------------------------------------------
# Análise de possíveis sobreposições de docentes
# -----------------------------------------------------------------------------


def encontrar_sobreposicoes_docentes(dados: pd.DataFrame) -> pd.DataFrame:
    # Encontra encontros sobrepostos do mesmo docente no mesmo dia.
    # A comparação usa intervalos semiabertos [início, fim). Assim, um encontro
    # que termina às 12:30 e outro que começa às 12:30 não é considerado
    # sobreposto. O resultado indica uma possibilidade de conflito na programação
    # registrada, não uma confirmação da indisponibilidade do professor.

    colunas_encontro_docente = [
        "docente",
        "dia_semana",
        "sala",
        "codigo_disciplina",
        "turma",
        "nome_disciplina",
        "turmas_compartilhando_sala",
        "hora_inicio",
        "hora_fim",
        "inicio_minutos",
        "fim_minutos",
    ]
    encontros = dados[colunas_encontro_docente].drop_duplicates().copy()
    conflitos = []

    for (docente, dia), grupo in encontros.groupby(["docente", "dia_semana"]):
        grupo_ordenado = grupo.sort_values("inicio_minutos").reset_index(drop=True)

        for indice_atual, encontro_atual in grupo_ordenado.iterrows():
            for indice_comparado in range(indice_atual + 1, len(grupo_ordenado)):
                encontro_comparado = grupo_ordenado.iloc[indice_comparado]

                # Como o grupo está ordenado pelo início, podemos parar quando
                # o próximo encontro começa após o fim do atual.
                if encontro_comparado["inicio_minutos"] >= encontro_atual[
                    "fim_minutos"
                ]:
                    break

                # Um mesmo registro físico pode aparecer duplicado por curso ou
                # por turma compartilhada. Só registramos pares de encontros
                # realmente diferentes.
                identificador_atual = (
                    encontro_atual["sala"],
                    encontro_atual["codigo_disciplina"],
                    encontro_atual["hora_inicio"],
                    encontro_atual["hora_fim"],
                    encontro_atual["turmas_compartilhando_sala"],
                )
                identificador_comparado = (
                    encontro_comparado["sala"],
                    encontro_comparado["codigo_disciplina"],
                    encontro_comparado["hora_inicio"],
                    encontro_comparado["hora_fim"],
                    encontro_comparado["turmas_compartilhando_sala"],
                )
                if identificador_atual == identificador_comparado:
                    continue

                inicio_conflito = max(
                    encontro_atual["inicio_minutos"],
                    encontro_comparado["inicio_minutos"],
                )
                fim_conflito = min(
                    encontro_atual["fim_minutos"],
                    encontro_comparado["fim_minutos"],
                )
                conflitos.append(
                    {
                        "docente": docente,
                        "dia_semana": dia,
                        "encontro_1": (
                            f"{encontro_atual['codigo_disciplina']} "
                            f"({encontro_atual['turma']}) - "
                            f"{encontro_atual['sala']}"
                        ),
                        "horario_1": (
                            f"{encontro_atual['hora_inicio']}-"
                            f"{encontro_atual['hora_fim']}"
                        ),
                        "encontro_2": (
                            f"{encontro_comparado['codigo_disciplina']} "
                            f"({encontro_comparado['turma']}) - "
                            f"{encontro_comparado['sala']}"
                        ),
                        "horario_2": (
                            f"{encontro_comparado['hora_inicio']}-"
                            f"{encontro_comparado['hora_fim']}"
                        ),
                        "sobreposicao": (
                            f"{minutos_para_horario(inicio_conflito)}-"
                            f"{minutos_para_horario(fim_conflito)}"
                        ),
                    }
                )

    return pd.DataFrame(conflitos)


# -----------------------------------------------------------------------------
# Componentes visuais
# -----------------------------------------------------------------------------


def exibir_grafico_curso_dia(dados: pd.DataFrame) -> None:
    # Gráfico 1: horas de ocupação por curso e dia da semana.

    # Agrega as horas por curso e dia, mantendo cada curso como unidade de
    # análise para mostrar a distribuição da carga acadêmica.
    agregado = horas_por_curso_e_dia(dados)
    if agregado.empty:
        st.info("Não há dados para o mapa de calor por curso e dia.")
        return

    # Cria uma coluna exclusiva para exibição. O código original continua
    # disponível em `curso` e segue sendo usado para filtrar e agrupar.
    agregado["curso_nome"] = agregado["curso"].map(
        lambda codigo: ROTULOS_CURSO.get(codigo, codigo)
    )

    # Converte a tabela agregada em um mapa de calor: cores mais intensas
    # representam maior quantidade de horas-aula no cruzamento curso/dia.
    figura = px.density_heatmap(
        agregado,
        x="dia_semana",
        y="curso_nome",
        z="horas_aula",
        histfunc="sum",
        category_orders={"dia_semana": ORDEM_DIAS},
        color_continuous_scale="Blues",
        labels={
            "dia_semana": "Dia da semana",
            "curso_nome": "Curso",
            "horas_aula": "Horas-aula",
        },
        title="Horas de ocupação por curso e dia da semana",
    )
    # Exibe a escala de cores com unidade e insere o gráfico na página.
    figura.update_layout(coloraxis_colorbar_title="Horas-aula")
    st.plotly_chart(figura, use_container_width=True)
    st.caption(
        "A soma mantém as linhas por curso para mostrar a "
        "distribuição da carga acadêmica. Um encontro compartilhado pode aparecer "
        "em mais de um curso. Biblioteca: Plotly."
    )


def exibir_grafico_horario(dados_fisicos: pd.DataFrame) -> None:
    # Gráfico 2: ocupação física do prédio por dia e faixa de horário.

    # Expande cada encontro contínuo em períodos de uma hora para permitir a
    # contagem da ocupação física em cada ponto da grade semanal.
    dados_horarios = expandir_encontros_em_horas(dados_fisicos)
    if dados_horarios.empty:
        st.info("Não há dados para o mapa de calor por horário.")
        return

    # Soma a quantidade de horas ocupadas em cada combinação de dia e horário.
    agregado = (
        dados_horarios.groupby(["dia_semana", "horario"], as_index=False)["horas_aula"]
        .sum()
    )
    # Monta o mapa de calor da ocupação física, sem contar duas vezes aulas
    # compartilhadas que já foram deduplicadas antes desta função.
    figura = px.density_heatmap(
        agregado,
        x="dia_semana",
        y="horario",
        z="horas_aula",
        histfunc="sum",
        category_orders={"dia_semana": ORDEM_DIAS},
        color_continuous_scale="YlOrRd",
        labels={
            "dia_semana": "Dia da semana",
            "horario": "Início do período",
            "horas_aula": "Horas de ocupação",
        },
        title="Ocupação física total do prédio por dia e horário",
    )
    # Coloca 07:30 no topo e os horários seguintes abaixo, como em uma agenda.
    figura.update_yaxes(
        categoryorder="array",
        categoryarray=sorted(agregado["horario"].unique()),
        autorange="reversed",
    )
    # Mantém os dias da semana na parte superior do gráfico.
    figura.update_xaxes(side="top")
    # Mantém apenas um pequeno intervalo visual entre as colunas dos dias,
    # equivalente ao espaçamento reduzido usado na agenda por sala.
    figura.update_traces(xgap=2)

    # Cria separadores maiores nas transições entre manhã, tarde e noite.
    # Como os horários estão em ordem crescente, os limites ficam entre as
    # posições 4/5, 5/6 e 10/11 do eixo categórico.
    for posicao in (4.5, 5.5, 10.5):
        figura.add_hline(
            y=posicao,
            line_color="black",
            line_width=2,
            layer="above",
        )
    figura.update_layout(coloraxis_colorbar_title="Horas de ocupação")
    st.plotly_chart(figura, use_container_width=True)
    st.caption(
        "Cada encontro físico foi expandido em períodos de uma "
        "hora. A ausência de registro indica apenas que não há aula registrada "
        "naquele intervalo. Biblioteca: Plotly."
    )


def exibir_grafico_salas(dados: pd.DataFrame) -> None:
    # Gráfico 3: horas de ocupação por sala e curso.

    agregado = horas_por_sala_e_curso(dados)
    if agregado.empty:
        st.info("Não há dados para o gráfico de ocupação das salas por curso.")
        return

    tabela = agregado.pivot(
        index="sala", columns="curso", values="horas_aula"
    ).fillna(0)
    tabela["total"] = tabela.sum(axis=1)
    tabela = tabela.sort_values("total", ascending=True)
    cursos_existentes = set(agregado["curso"].unique())
    cursos_prioritarios = ["ARQU", "DPRO", "DVIS"]
    cursos = [curso for curso in cursos_prioritarios if curso in cursos_existentes]
    cursos.extend(sorted(cursos_existentes.difference(cursos_prioritarios)))
    tipos_por_sala = agregado.drop_duplicates("sala").set_index("sala")["tipo_sala"]
    maior_total = tabela["total"].max()

    figura, eixo = plt.subplots(figsize=(10, max(3, len(tabela) * 0.25)))
    inicio_faixa = pd.Series(0.0, index=tabela.index)
    cores_cursos = {
        "ARQU": "#d62728",
        "DPRO": "#1f77b4",
        "DVIS": "#2ca02c",
        "CAGR": "#ff7f0e",
        "ENGMEC": "#8c564b",
    }
    cores_outros = iter(plt.get_cmap("tab20").colors)
    for curso in cursos:
        horas = tabela[curso]
        cor = cores_cursos.get(curso)
        if cor is None:
            cor = next(cores_outros, "#7f7f7f")
        eixo.barh(
            tabela.index,
            horas,
            left=inicio_faixa,
            height=0.45,
            color=cor,
            label=ROTULOS_CURSO.get(curso, curso),
        )
        inicio_faixa += horas

    eixo.set_title("Horas de ocupação por sala e curso")
    eixo.set_xlabel("Horas-aula")
    eixo.set_ylabel("Sala")
    eixo.grid(axis="x", linestyle="--", alpha=0.35)
    eixo.set_axisbelow(True)
    eixo.set_yticks(
        range(len(tabela)),
        labels=[str(sala).removeprefix("Sala ") for sala in tabela.index],
    )
    eixo.set_xlim(right=maior_total + max(maior_total * 0.25, 1))

    for indice, sala in enumerate(tabela.index):
        eixo.text(
            tabela.at[sala, "total"] + maior_total * 0.01,
            indice,
            tipos_por_sala[sala],
            va="center",
            fontsize=8,
        )
    eixo.legend(title="Curso", loc="best", fontsize=8)

    # Ajusta os espaços, exibe a figura no Streamlit e libera o objeto Matplotlib.
    figura.tight_layout()
    st.pyplot(figura)
    plt.close(figura)
    st.caption(
        "Cada segmento representa as horas registradas para um curso. "
        "Encontros compartilhados podem ser contabilizados em mais de um curso, "
        "portanto a soma dos segmentos não representa a ocupação física exclusiva. "
        "Biblioteca: Matplotlib."
    )


def exibir_agenda_sala(dados: pd.DataFrame, contexto: str = "original") -> None:
    # Gráfico 4: agenda semanal interativa de uma sala selecionada.

    # O seletor permite trocar de sala sem alterar a base original.
    salas = sorted(dados["sala"].dropna().unique())
    if not salas:
        st.info("Não há salas disponíveis para exibição.")
        return

    sala_selecionada = st.selectbox(
        "Selecione a sala",
        salas,
        key=f"sala_agenda_{contexto}",
    )
    encontros = dados[dados["sala"] == sala_selecionada].copy()
    cursos_disponiveis = sorted(encontros["curso"].dropna().unique())
    cursos_selecionados = st.multiselect(
        "Filtrar por curso",
        cursos_disponiveis,
        format_func=lambda codigo: ROTULOS_CURSO.get(codigo, codigo),
        key=f"cursos_agenda_{contexto}",
    )
    if cursos_selecionados:
        encontros = encontros[encontros["curso"].isin(cursos_selecionados)]

    # Uma aula compartilhada pode aparecer uma vez por curso na base detalhada;
    # aqui ela deve aparecer uma única vez como ocupação física da sala.
    encontros = encontros.drop_duplicates(subset=CHAVE_ENCONTRO_FISICO).copy()

    # Converte horários para minutos porque o eixo vertical do gráfico usa uma
    # escala contínua: 07:30 equivale a 450 e 13:30 equivale a 810 minutos.
    encontros["inicio_minutos"] = encontros["hora_inicio"].map(
        horario_para_minutos
    )
    encontros["fim_minutos"] = encontros["hora_fim"].map(horario_para_minutos)
    encontros["duracao_minutos"] = (
        encontros["fim_minutos"] - encontros["inicio_minutos"]
    )
    encontros["rotulo"] = (
        encontros["codigo_disciplina"] + " - " + encontros["turma"].astype(str)
    )

    # Mantém a mesma cor para todas as ocorrências de uma disciplina na sala.
    cores = px.colors.qualitative.Set3
    codigos = sorted(encontros["codigo_disciplina"].unique())
    cores_por_codigo = {
        codigo: cores[indice % len(cores)]
        for indice, codigo in enumerate(codigos)
    }

    figura = go.Figure()

    # A faixa cinza marca o intervalo de almoço em todos os dias. Ela é criada
    # como uma barra para que também tenha texto próprio no hover.
    figura.add_trace(
        go.Bar(
            x=ORDEM_DIAS,
            y=[60] * len(ORDEM_DIAS),
            base=[750] * len(ORDEM_DIAS),
            width=0.975,
            marker_color="gray",
            opacity=0.45,
            hovertemplate=(
                "Intervalo do almoço: horario preferencialmente sem utilização!"
                "<extra></extra>"
            ),
            name="Intervalo do almoço",
        )
    )
    # Cada encontro vira uma barra cuja base é o início e cuja altura é a
    # duração da aula. O hover consulta os dados acadêmicos do encontro.
    figura.add_trace(
        go.Bar(
            x=encontros["dia_semana"],
            y=encontros["duracao_minutos"],
            base=encontros["inicio_minutos"],
            width=0.975,
            text=encontros["rotulo"],
            textposition="inside",
            marker_color=[
                cores_por_codigo[codigo]
                for codigo in encontros["codigo_disciplina"]
            ],
            customdata=encontros[
                [
                    "codigo_disciplina",
                    "nome_disciplina",
                    "docente",
                    "turma",
                    "hora_inicio",
                    "hora_fim",
                ]
            ],
            hovertemplate=(
                "<b>%{customdata[0]} - %{customdata[3]}</b><br>"
                "Disciplina: %{customdata[1]}<br>"
                "Professor: %{customdata[2]}<br>"
                "Horário: %{customdata[4]} - %{customdata[5]}"
                "<extra></extra>"
            ),
        )
    )

    # Define marcações horárias de uma em uma hora e organiza os dias no topo.
    horarios = list(range(450, 1351, 60))
    figura.update_layout(
        title=f"Ocupação da {sala_selecionada} por dia e horário",
        xaxis={
            "title": "Dia da semana",
            "categoryorder": "array",
            "categoryarray": ORDEM_DIAS,
            "side": "top",
            "showgrid": True,
            "gridcolor": "#eeeeee",
            "gridwidth": 1,
        },
        yaxis={
            "title": "Horário",
            "tickmode": "array",
            "tickvals": horarios,
            "ticktext": [minutos_para_horario(horario) for horario in horarios],
            "autorange": False,
            "range": [1350, 450],
            "showgrid": True,
            "gridcolor": "#eeeeee",
            "gridwidth": 1,
        },
        height=700,
        # Sobrepõe as aulas à faixa cinza, mantendo ambas com a mesma largura.
        barmode="overlay",
        showlegend=False,
        hoverlabel={"align": "left"},
    )
    figura.add_shape(
        type="rect",
        xref="paper",
        yref="y",
        x0=0,
        x1=1,
        y0=450,
        y1=1350,
        line={"color": "#404040", "width": 2},
        fillcolor="rgba(0, 0, 0, 0)",
        layer="above",
    )

    # O gráfico é interativo: o detalhamento aparece ao passar o cursor sobre
    # cada encontro ou sobre o intervalo de almoço.
    st.plotly_chart(figura, use_container_width=True)
    st.caption(
        "A agenda combina a sala selecionada aos filtros ativos, incluindo "
        "curso. Passe o cursor sobre cada bloco para consultar o código, a "
        "disciplina, o professor, a turma e o horário. Biblioteca: Plotly. "
    )


def exibir_indicadores(dados_detalhados: pd.DataFrame, dados_fisicos: pd.DataFrame) -> None:
    # Exibe indicadores resumidos do recorte filtrado acima dos gráficos.

    # Calcula os números sobre o recorte atual, separando carga acadêmica
    # detalhada da quantidade física de horas e salas ocupadas.
    horas_fisicas = dados_fisicos["numero_periodos"].sum()
    quantidade_salas = dados_fisicos["sala"].nunique()
    quantidade_cursos = dados_detalhados["curso"].nunique()

    primeira_coluna, segunda_coluna, terceira_coluna = st.columns(3)
    # Organiza os três indicadores em colunas para leitura rápida do painel.
    primeira_coluna.metric("Horas-aula físicas", f"{horas_fisicas:.0f}")
    segunda_coluna.metric("Salas utilizadas", f"{quantidade_salas}")
    terceira_coluna.metric("Cursos no recorte", f"{quantidade_cursos}")


@st.cache_data
def ler_plantas_obj(caminho_obj: str) -> dict:
    # Lê as curvas 2D do OBJ (plano XZ) e separa as salas do restante do desenho.
    vertices = []
    salas = {}
    fundo_x, fundo_y = [], []
    nome_atual = None

    with open(caminho_obj, encoding="utf-8") as arquivo:
        for linha in arquivo:
            if linha.startswith("v "):
                _, x, _, z = linha.split()[:4]
                vertices.append((float(x), float(z)))
            elif linha.startswith("o "):
                nome_atual = linha[2:].strip()
            elif linha.startswith("curv ") and nome_atual:
                indices = [int(i) for i in linha.split()[3:]]
                pontos = [
                    vertices[i - 1 if i > 0 else len(vertices) + i] for i in indices
                ]
                # Em vista de topo, o eixo vertical da tela corresponde a -Z.
                xs = [round(p[0], 3) for p in pontos]
                ys = [round(-p[1], 3) for p in pontos]
                if nome_atual.startswith("Sala ") and nome_atual not in salas:
                    salas[nome_atual] = (xs, ys)
                else:
                    fundo_x.extend(xs + [None])
                    fundo_y.extend(ys + [None])

    return {"salas": salas, "fundo": (fundo_x, fundo_y)}


COR_CURSO_PLANTA = {
    "ARQU": "#e23d3d",
    "DPRO": "#2673df",
    "DVIS": "#20a467",
    "OUTRO": "#9aa6aa",
    "COMPARTILHADO": "#8e5bd0",
}
COR_SALA_LIVRE = "#dfe5e3"

_TINTAS_CURSO = {
    "ARQU": "#fce9e9",
    "DPRO": "#e8f0fd",
    "DVIS": "#e7f5ed",
    "OUTRO": "#eef1f2",
}
_NOMES_CURTOS = {"ARQU": "Arquitetura", "DPRO": "Produto", "DVIS": "Visual"}

_CSS_FICHA = """
* { box-sizing: border-box; }
body { margin: 0; color: #17262c; font: 14px/1.4 system-ui, sans-serif; }
.room-info { padding: 16px 18px; border: 1px solid #cbd6d3; background: #fff; }
.room-info h2 { margin: 0; font-size: 18px; }
.room-meta { margin: 4px 0 14px; color: #5a6b70; font-size: 12px; }
.agenda-wrap { overflow: auto; border: 1px solid #d8e0dd; }
.agenda-grid { display: grid; grid-template-columns: 58px repeat(5, minmax(124px, 1fr)); grid-template-rows: 34px repeat(30, 25px); min-width: 760px; position: relative; background: #fff; }
.agenda-day { grid-row: 1; z-index: 2; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid #bfcac6; background: #f2f6f4; color: #52645f; font-size: 10px; font-weight: 750; }
.agenda-tick { grid-column: 1; z-index: 2; padding: 0 5px; transform: translateY(-8px); background: white; color: #60716d; font-size: 10px; font-variant-numeric: tabular-nums; text-align: right; }
.agenda-track { z-index: 0; grid-row: 2 / span 30; border-left: 1px solid #e2e8e6; background: repeating-linear-gradient(to bottom, transparent 0, transparent 24px, #e2e8e6 24px, #e2e8e6 25px); }
.agenda-lunch { z-index: 1; grid-row: 12 / span 2; background: rgba(125, 139, 135, .14); border-block: 1px dashed #aebcb8; pointer-events: none; }
.agenda-event { z-index: 2; min-width: 0; overflow: hidden; margin: 2px 3px; padding: 4px 5px; border: 1px solid rgba(34, 48, 52, .22); border-left: 4px solid var(--event-color); border-radius: 3px; background: var(--event-tint); color: #17262c; box-shadow: 0 1px 3px rgba(23, 38, 44, .12); font-size: 10px; line-height: 1.22; }
.agenda-event strong, .agenda-event span { display: block; overflow: hidden; text-overflow: ellipsis; }
.agenda-event .event-name, .agenda-event .event-details { display: none; }
.agenda-event.is-long .event-name, .agenda-event.is-long .event-details { display: block; }
.event-courses { display: flex !important; flex-wrap: wrap; gap: 2px; margin-top: 2px; }
.event-course { display: inline-block !important; padding: 1px 3px; border-radius: 2px; color: white; font-size: 8px; white-space: nowrap; }
"""


def _categoria_curso(curso: str) -> str:
    return curso if curso in ("ARQU", "DPRO", "DVIS") else "OUTRO"


def exibir_ficha_sala(dados: pd.DataFrame, sala: str) -> None:
    # Ficha da sala clicada: tipo, capacidade e agenda semanal por turma.
    registros = dados[dados["sala"] == sala]
    esc = html_lib.escape
    if registros.empty:
        st.info(f"Não há registros de utilização da {sala} no CSV.")
        return

    encontros = {}
    for r in registros.itertuples():
        chave = (
            r.codigo_disciplina, r.turma, r.dia_semana, r.hora_inicio,
            r.hora_fim, r.turmas_compartilhando_sala,
        )
        e = encontros.setdefault(chave, {"base": r, "cursos": {}, "docentes": []})
        e["cursos"].setdefault(r.curso, r)
        if r.docente not in e["docentes"]:
            e["docentes"].append(r.docente)

    capacidades = " / ".join(str(c) for c in registros["capacidade_sala"].unique())
    blocos = []
    for indice, dia in enumerate(ORDEM_DIAS):
        coluna = indice + 2
        blocos.append(
            f'<div class="agenda-day" style="grid-column:{coluna}">{esc(dia)}</div>'
            f'<div class="agenda-track" style="grid-column:{coluna}"></div>'
            f'<div class="agenda-lunch" style="grid-column:{coluna}" '
            'title="Intervalo de almoço"></div>'
        )
    for minuto in range(450, 1351, 60):
        blocos.append(
            f'<div class="agenda-tick" style="grid-row:{2 + (minuto - 450) // 30}">'
            f"{minutos_para_horario(minuto)}</div>"
        )

    for e in sorted(
        encontros.values(),
        key=lambda e: (
            ORDEM_DIAS.index(e["base"].dia_semana)
            if e["base"].dia_semana in ORDEM_DIAS else 99,
            e["base"].hora_inicio,
            e["base"].codigo_disciplina,
        ),
    ):
        b = e["base"]
        if b.dia_semana not in ORDEM_DIAS:
            continue
        inicio = max(450, horario_para_minutos(b.hora_inicio))
        fim = min(1350, horario_para_minutos(b.hora_fim))
        if fim <= inicio:
            continue
        slot_inicial = (inicio - 450) // 30
        duracao = max(1, -(-(fim - inicio) // 30))
        cursos = list(e["cursos"])
        primeira = _categoria_curso(cursos[0])
        nomes_cursos = ", ".join(ROTULOS_CURSO.get(c, c) for c in cursos)
        dica = "\n".join(
            [
                f"{b.codigo_disciplina} · {b.nome_disciplina}",
                f"Turma {b.turma} · {b.dia_semana} · {b.hora_inicio}–{b.hora_fim}",
                f"Curso(s): {nomes_cursos}",
                f"Docente(s): {', '.join(map(str, e['docentes']))}",
                f"{b.numero_periodos} períodos · etapa {b.etapa} · {b.creditos} créditos",
                f"Vagas da turma: {b.vagas_oferecidas} de {b.vagas_totais_compartilhadas} "
                f"({b.turmas_compartilhando_sala})",
            ]
        )
        tags = "".join(
            f'<span class="event-course" style="background:'
            f'{COR_CURSO_PLANTA[_categoria_curso(c)]}">'
            f"{esc(_NOMES_CURTOS.get(_categoria_curso(c), c))}</span>"
            for c in cursos
        )
        classe = "agenda-event is-long" if duracao >= 4 else "agenda-event"
        blocos.append(
            f'<div class="{classe}" title="{esc(dica)}" style="grid-column:'
            f"{ORDEM_DIAS.index(b.dia_semana) + 2};grid-row:{2 + slot_inicial} / "
            f"span {duracao};--event-color:{COR_CURSO_PLANTA[primeira]};"
            f'--event-tint:{_TINTAS_CURSO[primeira]}">'
            f"<strong>{esc(str(b.codigo_disciplina))} · Turma {esc(str(b.turma))} · "
            f"{esc(str(int(b.vagas_oferecidas)))} vagas</strong>"
            f'<span class="event-courses">{tags}</span>'
            f'<span class="event-name">{esc(str(b.nome_disciplina))}</span>'
            f"<span>{b.hora_inicio}–{b.hora_fim}</span>"
            f'<span class="event-details">{esc("/".join(map(str, e["docentes"])))} · '
            f"{b.numero_periodos} períodos · {b.creditos} cr</span></div>"
        )

    documento = (
        f"<style>{_CSS_FICHA}</style><section class='room-info'>"
        f"<h2>{esc(sala)} · {esc(str(registros.iloc[0]['tipo_sala']))}</h2>"
        f"<p class='room-meta'>Capacidade da sala: {esc(capacidades)} lugares · "
        f"{len(encontros)} encontros na semana</p>"
        f"<div class='agenda-wrap'><div class='agenda-grid'>{''.join(blocos)}"
        "</div></div></section>"
    )
    components.html(documento, height=960, scrolling=True)


def _rgba(hex_cor: str, alpha: float) -> str:
    r, g, b = (int(hex_cor[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def exibir_animacao_plantas(dados: pd.DataFrame, contexto: str = "original") -> None:
    st.subheader("5. Ocupação das salas nas plantas baixas")
    st.caption(
        "Escolha o dia e use o controle deslizante ou o botão Play para animar a "
        "ocupação das salas ao longo do dia. Biblioteca: Plotly."
    )

    if not CAMINHO_OBJ.exists():
        st.warning(f"Plantas baixas não encontradas: {CAMINHO_OBJ.name}")
        return

    try:
        plantas = ler_plantas_obj(str(CAMINHO_OBJ))
    except (OSError, ValueError) as erro:
        st.error(f"Não foi possível ler as plantas baixas: {erro}")
        return

    salas = plantas["salas"]
    if not salas:
        st.error("O OBJ não contém polígonos nomeados como 'Sala xxx'.")
        return

    dia = st.selectbox("Dia da semana", ORDEM_DIAS, key=f"dia_plantas_{contexto}")
    agenda = dados[dados["dia_semana"] == dia]
    agenda = agenda[agenda["sala"].isin(salas)]
    eventos_por_sala = {sala: grupo for sala, grupo in agenda.groupby("sala")}

    def estado_sala(sala: str, minuto: int) -> tuple[str, str]:
        grupo = eventos_por_sala.get(sala)
        ativos = None
        if grupo is not None:
            ativos = grupo[
                (grupo["inicio_minutos"] <= minuto) & (minuto < grupo["fim_minutos"])
            ]
        if ativos is None or ativos.empty:
            return _rgba(COR_SALA_LIVRE, 0.6), f"<b>{sala}</b><br>Livre"
        cursos = sorted(ativos["curso"].unique())
        categorias = {c if c in COR_CURSO_PLANTA else "OUTRO" for c in cursos}
        categoria = categorias.pop() if len(categorias) == 1 else "COMPARTILHADO"
        encontros = ativos.drop_duplicates(
            subset=["codigo_disciplina", "turma", "hora_inicio"]
        )
        detalhe = "<br>".join(
            f"{e.codigo_disciplina} · {e.nome_disciplina} ({e.turma}) "
            f"{e.hora_inicio}-{e.hora_fim}"
            for e in encontros.itertuples()
        )
        cursos_txt = ", ".join(ROTULOS_CURSO.get(c, c) for c in cursos)
        return (
            _rgba(COR_CURSO_PLANTA[categoria], 0.7),
            f"<b>{sala}</b><br>{cursos_txt}<br>{detalhe}",
        )

    nomes = sorted(salas)
    minutos = list(range(450, 1351, 60))

    figura = go.Figure()
    fundo_x, fundo_y = plantas["fundo"]
    figura.add_trace(
        go.Scattergl(
            x=fundo_x,
            y=fundo_y,
            mode="lines",
            line={"color": "#8a9a96", "width": 0.6},
            hoverinfo="skip",
            showlegend=False,
        )
    )

    for sala in nomes:
        xs, ys = salas[sala]
        cor, texto = estado_sala(sala, minutos[0])
        figura.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                fill="toself",
                fillcolor=cor,
                line={"color": "#17262c", "width": 1.2},
                hoveron="fills",
                text=texto,
                hoverinfo="text",
                showlegend=False,
            )
        )

    # Scattergl desenha acima dos traços SVG; os rótulos também são gl para ficarem sobre o mobiliário.
    figura.add_trace(
        go.Scattergl(
            x=[sum(salas[s][0]) / len(salas[s][0]) for s in nomes],
            y=[sum(salas[s][1]) / len(salas[s][1]) for s in nomes],
            mode="text",
            text=[s.replace("Sala ", "") for s in nomes],
            textposition="middle center",
            textfont={"size": 16, "color": "#000000", "family": "Arial Black, Arial"},
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Posições em x/y das plantas no OBJ; os nomes ficam abaixo de cada desenho.
    figura.add_trace(
        go.Scatter(
            x=[-13, 16, 43, 73],
            y=[30.5] * 4,
            mode="text",
            text=["Térreo", "3º Andar", "4º Andar", "5º Andar"],
            textfont={"size": 20, "color": "#17262c"},
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Marcadores invisíveis no centro das salas recebem o clique e repetem o hover.
    centros_x = [sum(salas[s][0]) / len(salas[s][0]) for s in nomes]
    centros_y = [sum(salas[s][1]) / len(salas[s][1]) for s in nomes]
    figura.add_trace(
        go.Scatter(
            x=centros_x,
            y=centros_y,
            mode="markers",
            marker={"size": 28, "opacity": 0},
            text=[estado_sala(s, minutos[0])[1] for s in nomes],
            hoverinfo="text",
            showlegend=False,
        )
    )
    indice_cliques = len(figura.data) - 1

    legenda = {
        "Arquitetura": "ARQU",
        "Design de Produto": "DPRO",
        "Design Visual": "DVIS",
        "Cursos compartilhando": "COMPARTILHADO",
        "Livre": None,
    }
    for rotulo, chave in legenda.items():
        figura.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker={
                    "symbol": "square",
                    "size": 12,
                    "color": COR_CURSO_PLANTA[chave] if chave else COR_SALA_LIVRE,
                    "line": {"color": "#17262c", "width": 1},
                },
                name=rotulo,
            )
        )

    indices_salas = list(range(1, len(nomes) + 1))
    figura.frames = [
        go.Frame(
            name=minutos_para_horario(minuto),
            data=[
                go.Scatter(fillcolor=c, text=t)
                for c, t in (estado_sala(s, minuto) for s in nomes)
            ]
            + [go.Scatter(text=[estado_sala(s, minuto)[1] for s in nomes])],
            traces=indices_salas + [indice_cliques],
        )
        for minuto in minutos
    ]

    parametros = {"mode": "immediate", "transition": {"duration": 0}}
    figura.update_layout(
        title=f"Ocupação das salas - {dia}",
        height=720,
        xaxis={"visible": False},
        yaxis={"visible": False, "scaleanchor": "x", "scaleratio": 1},
        plot_bgcolor="white",
        legend={"orientation": "h", "y": 1.02, "x": 0},
        margin={"l": 10, "r": 10, "t": 70, "b": 10},
        updatemenus=[
            {
                "type": "buttons",
                "direction": "left",
                "x": 0,
                "y": -0.02,
                "yanchor": "top",
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                **parametros,
                                "frame": {"duration": 700, "redraw": True},
                                "fromcurrent": True,
                            },
                        ],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [[None], {**parametros, "frame": {"duration": 0}}],
                    },
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "x": 0.12,
                "len": 0.88,
                "y": -0.02,
                "yanchor": "top",
                "currentvalue": {"prefix": "Horário: "},
                "steps": [
                    {
                        "label": minutos_para_horario(m),
                        "method": "animate",
                        "args": [
                            [minutos_para_horario(m)],
                            {**parametros, "frame": {"duration": 0, "redraw": True}},
                        ],
                    }
                    for m in minutos
                ],
            }
        ],
    )

    evento = st.plotly_chart(
        figura,
        use_container_width=True,
        key=f"grafico_plantas_{contexto}",
        on_select="rerun",
        selection_mode="points",
    )
    st.caption(
        "Cores indicam o curso que ocupa a sala no horário; roxo indica mais de um "
        "curso no mesmo encontro. Passe o cursor sobre uma sala para ver as "
        "disciplinas e clique nela para abrir a agenda semanal. Salas sem "
        "registro no CSV aparecem como livres."
    )

    pontos = [
        p
        for p in evento.selection.points
        if p.get("curve_number") == indice_cliques
    ]
    if pontos:
        sala_clicada = nomes[pontos[0]["point_index"]]
        exibir_ficha_sala(dados, sala_clicada)


# -----------------------------------------------------------------------------
# Construção da página
# -----------------------------------------------------------------------------


def carregar_base_para_pagina() -> pd.DataFrame:
    # Carrega a base e encerra a página com uma mensagem objetiva em caso de erro.
    if not CAMINHO_DADOS.exists():
        st.error(f"Arquivo de dados não encontrado: {CAMINHO_DADOS}")
        st.stop()

    try:
        dados = carregar_dados(str(CAMINHO_DADOS))
    except (ValueError, OSError, pd.errors.ParserError) as erro:
        st.error(f"Não foi possível carregar a base de dados: {erro}")
        st.stop()
    return dados


def pagina_inicial() -> None:
    st.title("Ocupação dos espaços de ensino")
    st.write(
        "Dashboard interativo da Atividade 03 sobre a programação regular de "
        "salas da Faculdade de Arquitetura no semestre 2026/2."
    )

    st.subheader("Perguntas investigadas")
    st.markdown(
        "**1. Como a distribuição das horas de ocupação ao longo da semana "
        "difere entre os cursos?**  \n"
        "**Configuração:** use o filtro `Curso` e, se necessário, `Dia da semana`. "
        "O mapa de calor **Ocupação por curso e dia** compara as horas-aula por "
        "curso e dia, mantendo os cursos na unidade de análise."
    )
    st.markdown(
        "**2. Como a ocupação dos espaços varia ao longo dos horários de "
        "funcionamento da unidade?**  \n"
        "**Configuração:** use os filtros `Dia da semana`, `Turno`, `Sala` ou "
        "`Tipo de espaço`. O mapa de calor **Ocupação ao longo do horário** "
        "mostra as horas de ocupação física por dia e período horário."
    )
    st.markdown(
        "**3. Como cada curso ocupa as diferentes salas ao longo da semana?**  \n"
        "**Configuração:** use `Curso`, `Sala` e `Dia da semana`. "
        "O gráfico **Ocupação das salas por curso** compara as horas-aula "
        "registradas para cada curso em cada sala."
    )

    dados = carregar_base_para_pagina()

    # Os filtros são criados a partir dos valores reais da base. A opção vazia
    # significa "todos" e evita inserir artificialmente uma categoria no CSV.
    st.sidebar.header("Filtros")
    cursos_selecionados = st.sidebar.multiselect(
        "Curso",
        sorted(dados["curso"].dropna().unique()),
        format_func=lambda codigo: ROTULOS_CURSO.get(codigo, codigo),
    )
    salas_selecionadas = st.sidebar.multiselect(
        "Sala", sorted(dados["sala"].dropna().unique())
    )
    tipos_selecionados = st.sidebar.multiselect(
        "Tipo de espaço", sorted(dados["tipo_sala"].dropna().unique())
    )
    dias_selecionados = st.sidebar.multiselect(
        "Dia da semana", ORDEM_DIAS
    )
    turnos_selecionados = st.sidebar.multiselect(
        "Turno", ["Manhã", "Tarde", "Noite"]
    )
    etapas_disponiveis = sorted(dados["etapa"].dropna().unique())
    etapas_selecionadas = st.sidebar.multiselect(
        "Etapa", etapas_disponiveis
    )
    creditos_disponiveis = sorted(dados["creditos"].dropna().unique())
    creditos_selecionados = st.sidebar.multiselect(
        "Créditos", creditos_disponiveis
    )

    dados_filtrados = aplicar_filtros(
        dados,
        cursos_selecionados,
        salas_selecionadas,
        tipos_selecionados,
        dias_selecionados,
        turnos_selecionados,
        etapas_selecionadas,
        creditos_selecionados,
    )
    dados_fisicos = criar_visao_fisica(dados_filtrados)

    st.caption(
        "Docentes são identificadores anonimizados "
        "(por exemplo, Prof01 e Prof02). Fonte: mapa_salas_tidy_03.csv."
    )

    if dados_filtrados.empty:
        st.warning(
            "Nenhum registro foi encontrado para os filtros selecionados. "
            "Altere uma ou mais opções na barra lateral."
        )
        st.stop()

    exibir_indicadores(dados_filtrados, dados_fisicos)

    st.subheader("1. Ocupação por curso e dia")
    exibir_grafico_curso_dia(dados_filtrados)

    st.subheader("2. Ocupação ao longo do horário")
    exibir_grafico_horario(dados_fisicos)

    st.subheader("3. Ocupação das salas por curso")
    exibir_grafico_salas(dados_filtrados)


# Turno fora do alvo de cada curso (alvo: ARQU manhã/noite; DPRO e DVIS tarde/noite).
TURNO_FORA_ALVO = {
    "ARQU": ("Arquitetura", "Tarde", (810, 1110)),
    "DPRO": ("Design de Produto", "Manhã", (0, 750)),
    "DVIS": ("Design Visual", "Manhã", (0, 750)),
}


def exibir_uso_fora_do_turno_alvo(dados: pd.DataFrame) -> None:
    # Percentual da carga horária (minutos de relógio) de cada curso alocada
    # no turno que não é o alvo dele.
    encontros = dados.drop_duplicates(CHAVE_ENCONTRO_FISICO + ["curso"])
    for sigla, (nome, turno, (ini, fim)) in TURNO_FORA_ALVO.items():
        curso = encontros[encontros["curso"] == sigla]
        total = (curso["fim_minutos"] - curso["inicio_minutos"]).sum()
        fora = (
            curso["fim_minutos"].clip(upper=fim) - curso["inicio_minutos"].clip(lower=ini)
        ).clip(lower=0).sum()
        percentual = 100 * fora / total if total else 0
        st.markdown(
            f'<span style="color:{COR_CURSO_PLANTA[sigla]}">&#9679;</span> '
            f"**{nome}:** {percentual:.1f}% de carga horária alocada no "
            f"turno da {turno.lower()}.",
            unsafe_allow_html=True,
        )


def pagina_agenda() -> None:
    st.title("Agenda")
    st.write(
        "Agenda e análises complementares da programação regular de salas "
        "do semestre 2026/2."
    )
    dados = carregar_base_para_pagina()

    st.caption(
        "Docentes são identificadores anonimizados "
        "(por exemplo, Prof01 e Prof02). Fonte: mapa_salas_tidy_03.csv."
    )
    st.subheader("4. Agenda interativa por sala")
    exibir_agenda_sala(dados)

    exibir_animacao_plantas(dados)

    st.subheader("6. Uso dos cursos fora do turno-alvo")
    exibir_uso_fora_do_turno_alvo(dados)


def caminho_proposta(codigo: str) -> Path:
    # Prefere a solução final; sem ela, usa a candidata provisória do solver.
    final = CAMINHO_SOLUCOES[codigo]
    candidata = PASTA_APP / f"saida_solucao_{codigo}" / f"candidato_{codigo}.csv"
    return final if final.exists() or not candidata.exists() else candidata


def carregar_proposta_para_pagina(codigo: str) -> pd.DataFrame | None:
    caminho = caminho_proposta(codigo)
    if not caminho.exists():
        st.info(
            f"A proposta {codigo} ainda não foi gerada. "
            f"Arquivo esperado: {caminho.name}."
        )
        return None

    try:
        return carregar_dados(str(caminho))
    except (ValueError, OSError, pd.errors.ParserError) as erro:
        st.error(f"Não foi possível carregar {caminho.name}: {erro}")
        return None


def pagina_proposta(codigo: str, titulo: str, descricao: str) -> None:
    st.title(titulo)
    st.write(descricao)

    dados = carregar_proposta_para_pagina(codigo)
    if dados is None:
        return

    st.caption(
        f"Fonte: {caminho_proposta(codigo).name}. "
        "A agenda exibe somente os dados desta proposta."
    )
    st.subheader("Agenda interativa por sala")
    exibir_agenda_sala(dados, contexto=f"proposta_{codigo}")
    exibir_animacao_plantas(dados, contexto=f"proposta_{codigo}")
    st.subheader("Uso dos cursos fora do turno-alvo")
    exibir_uso_fora_do_turno_alvo(dados)


def pagina_proposta_a() -> None:
    pagina_proposta(
        "A",
        "Proposta A — Preservação",
        "Agenda da solução que prioriza manter a grade atual e reduzir alterações.",
    )


def pagina_proposta_b() -> None:
    pagina_proposta(
        "B",
        "Proposta B — Equilíbrio",
        "Agenda da solução que prioriza a distribuição semanal das disciplinas e "
        "da carga docente.",
    )


def pagina_proposta_c() -> None:
    pagina_proposta(
        "C",
        "Proposta C — Turnos-alvo",
        "Agenda da solução que maximiza a carga horária nos turnos-alvo.",
    )


def main() -> None:
    st.set_page_config(
        page_title="Mapa de salas - Atividade 03",
        page_icon="📊",
        layout="wide",
    )

    navegacao = st.navigation(
        [
            st.Page(pagina_inicial, title="Início", default=True),
            st.Page(pagina_agenda, title="Agenda"),
            st.Page(pagina_proposta_a, title="Proposta A"),
            st.Page(pagina_proposta_b, title="Proposta B"),
            st.Page(pagina_proposta_c, title="Proposta C"),
        ],
        position="top",
    )
    navegacao.run()


if __name__ == "__main__":
    main()