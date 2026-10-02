# Dashboard interativo da Atividade 03.
#
# O aplicativo transforma a proposta de análise da Atividade 01 em uma interface
# interativa. A fonte de dados e este arquivo ficam na mesma pasta, o que torna
# a execução reproduzível com `streamlit run app.py`.

from pathlib import Path
import json

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
CAMINHO_OBJ = PASTA_APP / "teste.obj"

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
    "capacidade_turma",
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
        "capacidade_turma",
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


def horas_por_sala_e_tipo(dados: pd.DataFrame) -> pd.DataFrame:
    # Soma horas físicas por sala e tipo de espaço para a terceira pergunta.

    return (
        dados.groupby(["sala", "tipo_sala"], as_index=False)["numero_periodos"]
        .sum()
        .rename(columns={"numero_periodos": "horas_aula"})
        .sort_values("horas_aula", ascending=True)
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


def exibir_grafico_salas(dados_fisicos: pd.DataFrame) -> None:
    # Gráfico 3: horas de ocupação por sala e tipo de espaço.

    # Agrega as horas físicas por sala e tipo de espaço para comparar a
    # utilização dos ambientes sem duplicar encontros compartilhados.
    agregado = horas_por_sala_e_tipo(dados_fisicos)
    if agregado.empty:
        st.info("Não há dados para o gráfico de salas e tipos de espaço.")
        return

    # Usa barras horizontais para acomodar a lista de salas e seus rótulos.
    figura, eixo = plt.subplots(figsize=(10, max(4, len(agregado) * 0.35)))
    eixo.barh(
        agregado["sala"],
        agregado["horas_aula"],
        color="#2f6690",
    )
    eixo.set_title("Horas de ocupação por sala")
    eixo.set_xlabel("Horas-aula")
    eixo.set_ylabel("Sala")
    eixo.grid(axis="x", linestyle="--", alpha=0.35)

    # O tipo do espaço é escrito ao lado da barra para manter a visualização
    # legível mesmo quando o usuário seleciona muitas salas.
    maior_valor = agregado["horas_aula"].max()
    for indice, (_, linha) in enumerate(agregado.iterrows()):
        eixo.text(
            linha["horas_aula"] + maior_valor * 0.01,
            indice,
            linha["tipo_sala"],
            va="center",
            fontsize=8,
        )

    # Ajusta os espaços, exibe a figura no Streamlit e libera o objeto Matplotlib.
    figura.tight_layout()
    st.pyplot(figura)
    plt.close(figura)
    st.caption(
        "As horas são calculadas sobre encontros físicos "
        "deduplicados; por isso, turmas que compartilham uma sala não inflacionam "
        "o total do espaço. Biblioteca: Matplotlib. "
    )


def exibir_agenda_sala(dados: pd.DataFrame) -> None:
    # Gráfico 4: agenda semanal interativa de uma sala selecionada.

    # O seletor permite trocar de sala sem alterar a base original.
    salas = sorted(dados["sala"].dropna().unique())
    if not salas:
        st.info("Não há salas disponíveis para exibição.")
        return

    sala_selecionada = st.selectbox(
        "Selecione a sala",
        salas,
        key="sala_agenda",
    )
    encontros = dados[dados["sala"] == sala_selecionada].copy()
    cursos_disponiveis = sorted(encontros["curso"].dropna().unique())
    cursos_selecionados = st.multiselect(
        "Filtrar por curso",
        cursos_disponiveis,
        format_func=lambda codigo: ROTULOS_CURSO.get(codigo, codigo),
        key="cursos_agenda",
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


def ler_obj_para_cena(caminho_obj: Path) -> dict:
        vertices = []
        objetos = []
        objeto_atual = None

        for linha in caminho_obj.read_text(encoding="utf-8").splitlines():
                partes = linha.split()
                if not partes:
                        continue

                if partes[0] == "o":
                        objeto_atual = {"nome": " ".join(partes[1:]), "faces": [], "curvas": []}
                        objetos.append(objeto_atual)
                elif partes[0] == "v":
                        vertices.append([float(valor) for valor in partes[1:4]])
                elif partes[0] == "f" and objeto_atual:
                        indices = []
                        for referencia in partes[1:]:
                                indice = int(referencia.split("/")[0])
                                indices.append(indice - 1 if indice > 0 else len(vertices) + indice)
                        objeto_atual["faces"].append(indices)
                elif partes[0] == "curv" and objeto_atual:
                        objeto_atual["curvas"].append([int(indice) - 1 for indice in partes[3:]])

        return {"vertices": vertices, "objetos": objetos}


def exibir_visualizacao_3d(dados: pd.DataFrame) -> None:
        st.subheader("5. Ocupação semanal das salas em 3D")
        st.caption(
                "Gire com o mouse ou toque, use a roda para zoom e escolha um dia e horário. "
                "As cores indicam Arquitetura (vermelho), Design de Produto (azul) e "
                "Design Visual (verde)."
        )

        if not CAMINHO_OBJ.exists():
                st.warning(f"Modelo 3D não encontrado: {CAMINHO_OBJ.name}")
                return

        try:
                cena = ler_obj_para_cena(CAMINHO_OBJ)
        except (OSError, ValueError) as erro:
                st.error(f"Não foi possível ler o modelo 3D: {erro}")
                return

        nomes_obj = {objeto["nome"] for objeto in cena["objetos"]}
        salas_obj = {
                nome.replace("_", " ")
                for nome in nomes_obj
                if nome.replace("_", " ") in {"Sala 301A", "Sala 501", "Sala 504"}
                and any(objeto["nome"] == nome and objeto["faces"] for objeto in cena["objetos"])
        }
        if not salas_obj:
                st.error("O OBJ não contém objetos nomeados para as salas 301A, 501 e 504.")
                return

        colunas_agenda = [
                "sala",
            "tipo_sala",
            "capacidade_turma",
                "dia_semana",
                "hora_inicio",
                "hora_fim",
                "codigo_disciplina",
                "nome_disciplina",
                "turma",
                "curso",
            "docente",
            "numero_periodos",
            "vagas_oferecidas",
            "vagas_totais_compartilhadas",
            "turmas_compartilhando_sala",
            "etapa",
            "creditos",
        ]
        agenda = (
                dados[dados["sala"].isin(salas_obj)][colunas_agenda]
                .drop_duplicates()
                .to_dict(orient="records")
        )
        conteudo = {**cena, "agenda": agenda, "dias": ORDEM_DIAS}
        dados_json = json.dumps(conteudo, ensure_ascii=False).replace("<", "\\u003c")

        html = r'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
    * { box-sizing: border-box; }
    body { margin: 0; color: #17262c; font: 14px/1.4 system-ui, sans-serif; }
    .viewer { border: 1px solid #cbd6d3; background: #f2f6f4; }
    .controls { display: grid; grid-template-columns: minmax(150px, 220px) 1fr auto; align-items: center; gap: 20px; padding: 14px 18px; background: #fff; border-bottom: 1px solid #d8e0dd; }
    label { display: grid; gap: 5px; color: #596a70; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    select, input[type=range] { width: 100%; }
    select { min-height: 36px; padding: 0 9px; border: 1px solid #aebcb8; background: white; color: #17262c; font: inherit; }
    .time-box { display: grid; grid-template-columns: 1fr 62px; align-items: center; gap: 12px; }
    input[type=range] { accent-color: #167b68; }
    output { color: #167b68; font-size: 17px; font-weight: 750; font-variant-numeric: tabular-nums; }
    button { min-height: 36px; border: 1px solid #aebcb8; background: white; color: #17262c; padding: 0 12px; cursor: pointer; font: inherit; }
    button:hover { border-color: #167b68; }
    .scene-wrap { height: 540px; position: relative; overflow: hidden; background: radial-gradient(ellipse at 50% 40%, #fff 0%, #e8f0ed 65%, #dce7e2 100%); }
    canvas { display: block; width: 100%; height: 100%; }
    .room-label { position: absolute; z-index: 2; transform: translate(-50%, -100%); padding: 4px 8px; border: 1px solid #aebcb8; background: rgba(255,255,255,.88); color: #17262c; font-size: 11px; font-weight: 750; white-space: nowrap; cursor: pointer; }
    canvas { cursor: grab; }
    canvas:active { cursor: grabbing; }
    .status-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid #d8e0dd; background: white; }
    .status { min-width: 0; padding: 12px 16px; border-right: 1px solid #e2e8e6; }
    .status:last-child { border-right: 0; }
    .status h3 { margin: 0 0 5px; font-size: 13px; }
    .status p { margin: 0; color: #5a6b70; font-size: 12px; overflow-wrap: anywhere; }
    .swatch { display: inline-block; width: 9px; height: 9px; margin: 0 5px 0 0; border-radius: 50%; vertical-align: 0; }
    .room-info { position: absolute; z-index: 4; left: 12px; right: 12px; bottom: 12px; max-height: 82%; overflow: auto; padding: 16px 18px; border: 1px solid #cbd6d3; background: rgba(255,255,255,.97); box-shadow: 0 8px 24px rgba(23,38,44,.18); }
    .room-info-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
    .room-info h2 { margin: 0; font-size: 18px; }
    .room-meta { margin: 4px 0 14px; color: #5a6b70; font-size: 12px; }
    .room-info button { flex: 0 0 auto; }
    .agenda-wrap { overflow: auto; border: 1px solid #d8e0dd; }
    .agenda-grid { display: grid; grid-template-columns: 58px repeat(5, minmax(124px, 1fr)); grid-template-rows: 34px repeat(30, 25px); min-width: 760px; position: relative; background: #fff; }
    .agenda-day { grid-row: 1; z-index: 2; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid #bfcac6; background: #f2f6f4; color: #52645f; font-size: 10px; font-weight: 750; }
    .agenda-tick { grid-column: 1; z-index: 2; padding: 0 5px; transform: translateY(-8px); background: white; color: #60716d; font-size: 10px; font-variant-numeric: tabular-nums; text-align: right; }
    .agenda-track { z-index: 0; grid-row: 2 / span 30; border-left: 1px solid #e2e8e6; background: repeating-linear-gradient(to bottom, transparent 0, transparent 24px, #e2e8e6 24px, #e2e8e6 25px); }
    .agenda-lunch { z-index: 1; grid-row: 12 / span 2; background: rgba(125, 139, 135, .14); border-block: 1px dashed #aebcb8; pointer-events: none; }
    .agenda-event { z-index: 2; min-width: 0; overflow: hidden; margin: 2px 3px; padding: 4px 5px; border: 1px solid rgba(34, 48, 52, .22); border-left: 4px solid var(--event-color); border-radius: 3px; background: var(--event-tint); color: #17262c; box-shadow: 0 1px 3px rgba(23, 38, 44, .12); font-size: 10px; line-height: 1.22; }
    .agenda-event strong, .agenda-event span { display: block; overflow: hidden; text-overflow: ellipsis; }
    .agenda-event strong { font-size: 10px; }
    .agenda-event .event-name, .agenda-event .event-details { display: none; }
    .agenda-event.is-long .event-name, .agenda-event.is-long .event-details { display: block; }
    .event-courses { display: flex !important; flex-wrap: wrap; gap: 2px; margin-top: 2px; }
    .event-course { display: inline-block !important; padding: 1px 3px; border-radius: 2px; color: white; font-size: 8px; white-space: nowrap; }
    .empty-selection { position: absolute; z-index: 3; left: 12px; bottom: 12px; max-width: calc(100% - 24px); padding: 10px 12px; border: 1px solid #cbd6d3; background: rgba(255,255,255,.92); color: #5a6b70; font-size: 12px; pointer-events: none; }
    .error { padding: 24px; color: #9e342b; }
    @media (max-width: 650px) {
        .controls { grid-template-columns: 1fr auto; gap: 12px; padding: 12px; }
        .time-control { grid-column: 1 / -1; grid-row: 2; }
        .scene-wrap { height: 390px; }
        .status-row { grid-template-columns: 1fr; }
        .status { border-right: 0; border-bottom: 1px solid #e2e8e6; padding: 9px 12px; }
        .room-info { padding: 12px; }
        .room-info { left: 8px; right: 8px; bottom: 8px; max-height: 72%; }
        .empty-selection { left: 8px; bottom: 8px; max-width: calc(100% - 16px); }
        .agenda-grid { grid-template-columns: 48px repeat(5, minmax(116px, 1fr)); min-width: 628px; }
    }
</style>
</head>
<body>
<div class="viewer">
    <div class="controls">
        <label>Dia da semana<select id="day"></select></label>
        <label class="time-control">Horário<div class="time-box"><input id="time" type="range" min="450" max="1350" step="30" value="570"><output id="clock">09:30</output></div></label>
        <button id="reset" type="button" aria-label="Centralizar a câmera">Centralizar</button>
    </div>
    <div class="scene-wrap" id="scene-wrap">
        <div class="error" id="error" hidden></div>
        <div class="empty-selection" id="selection-hint">Selecione um bloco para consultar os dados da sala e a agenda semanal de cada turma.</div>
        <section class="room-info" id="room-info" hidden></section>
    </div>
    <div class="status-row" id="statuses"></div>
</div>
<script id="scene-data" type="application/json">__SCENE_DATA__</script>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js"}}</script>
<script type="module">
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/controls/OrbitControls.js';

const data = JSON.parse(document.getElementById('scene-data').textContent);
const colors = { ARQU: '#e23d3d', DPRO: '#2673df', DVIS: '#20a467', OTHER: '#9aa6aa' };
const courseNames = { ARQU: 'Arquitetura', DPRO: 'Design de Produto', DVIS: 'Design Visual' };
const wrap = document.getElementById('scene-wrap');
const errorBox = document.getElementById('error');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 2000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
wrap.prepend(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff, 0x899a95, 2.1));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.3);
keyLight.position.set(-15, 28, 22);
scene.add(keyLight);
scene.add(new THREE.AmbientLight(0xffffff, 0.5));
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.target.set(8, 2, -4);

const roomMeshes = new Map();
const roomEdges = new Map();
const labels = new Map();
let selectedRoom = null;
const roomNames = ['Sala 301A', 'Sala 501', 'Sala 504'];
for (const object of data.objetos) {
    if (object.faces.length) {
        const globalIndices = [...new Set(object.faces.flat())];
        const localIndices = new Map(globalIndices.map((index, position) => [index, position]));
        const positions = globalIndices.flatMap(index => data.vertices[index]);
        const indices = [];
        const groups = [];
        let cursor = 0;
        for (let faceIndex = 0; faceIndex < object.faces.length; faceIndex++) {
            const face = object.faces[faceIndex];
            const start = cursor;
            for (let i = 1; i < face.length - 1; i++) {
                indices.push(localIndices.get(face[0]), localIndices.get(face[i]), localIndices.get(face[i + 1]));
                cursor += 3;
            }
            groups.push({ start, count: cursor - start, faceIndex });
        }
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        geometry.setIndex(indices);
        for (const group of groups) geometry.addGroup(group.start, group.count, 0);
        geometry.computeVertexNormals();
        geometry.computeBoundingBox();
        geometry.computeBoundingSphere();
        const surfaceMaterials = [
            new THREE.MeshStandardMaterial({ color: colors.ARQU, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false, roughness: 0.32 }),
            new THREE.MeshStandardMaterial({ color: colors.DPRO, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false, roughness: 0.32 }),
            new THREE.MeshStandardMaterial({ color: colors.DVIS, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false, roughness: 0.32 }),
            new THREE.MeshStandardMaterial({ color: colors.OTHER, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false, roughness: 0.32 }),
            new THREE.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: 0.055, side: THREE.DoubleSide, depthWrite: false, roughness: 0.32, metalness: 0.12 }),
        ];
        const mesh = new THREE.Mesh(geometry, surfaceMaterials);
        mesh.userData.groups = groups;
        mesh.userData.objectName = object.nome;
        mesh.userData.surfaceMaterials = surfaceMaterials;
        scene.add(mesh);
        const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry, 1), new THREE.LineBasicMaterial({ color: 0x71827e, transparent: true, opacity: 0.66 }));
        scene.add(edges);
        const room = object.nome.replaceAll('_', ' ');
        if (roomNames.includes(room)) {
            mesh.userData.room = room;
            roomMeshes.set(room, mesh);
            const tag = document.createElement('div');
            tag.className = 'room-label';
            tag.textContent = room;
            tag.title = `Selecionar ${room}`;
            tag.setAttribute('role', 'button');
            tag.setAttribute('tabindex', '0');
            tag.addEventListener('click', () => selectRoom(room));
            tag.addEventListener('keydown', event => {
                if (event.key === 'Enter' || event.key === ' ') selectRoom(room);
            });
            wrap.appendChild(tag);
            labels.set(room, tag);
            roomEdges.set(room, edges);
        }
    }
    for (const curve of object.curvas) {
        const points = curve.map(index => new THREE.Vector3(...data.vertices[index]));
        if (points.length > 1) {
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            scene.add(new THREE.Line(geometry, new THREE.LineBasicMaterial({ color: 0x435954, transparent: true, opacity: 0.8 })));
        }
    }
}

if (!roomMeshes.size) {
    errorBox.hidden = false;
    errorBox.textContent = 'O OBJ não contém sólidos nomeados Sala_301A, Sala_501 ou Sala_504.';
    throw new Error(errorBox.textContent);
}

const bounds = new THREE.Box3().setFromObject(scene);
const center = bounds.getCenter(new THREE.Vector3());
const size = bounds.getSize(new THREE.Vector3());
const span = Math.max(size.x, size.y, size.z);
controls.target.copy(center);
camera.position.copy(center).add(new THREE.Vector3(span * 1.2, span * 0.85, span * 1.4));
camera.near = Math.max(span / 1000, 0.01);
camera.far = span * 20;
camera.updateProjectionMatrix();
const grid = new THREE.GridHelper(Math.max(size.x, size.z) * 1.2, 24, 0xb4c3bf, 0xd4dfdc);
grid.position.set(center.x, bounds.min.y - 0.08, center.z);
scene.add(grid);

const dayControl = document.getElementById('day');
for (const day of data.dias) {
    const option = document.createElement('option');
    option.value = day;
    option.textContent = day.replace('-FEIRA', '');
    dayControl.appendChild(option);
}
const timeControl = document.getElementById('time');
const clock = document.getElementById('clock');
const statuses = document.getElementById('statuses');
const selectionHint = document.getElementById('selection-hint');
const roomInfo = document.getElementById('room-info');
const roomOrder = Object.fromEntries(data.dias.map((day, index) => [day, index]));
const formatTime = value => `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
const toMinutes = value => { const [hours, minutes] = value.split(':').map(Number); return hours * 60 + minutes; };
const category = course => Object.hasOwn(colors, course) ? course : 'OTHER';

function updateOccupation() {
    const day = dayControl.value;
    const time = Number(timeControl.value);
    clock.value = formatTime(time);
    clock.textContent = formatTime(time);
    statuses.replaceChildren();
    for (const room of roomNames) {
        const events = data.agenda.filter(event => event.sala === room && event.dia_semana === day && toMinutes(event.hora_inicio) <= time && time < toMinutes(event.hora_fim));
        const activeCourses = [...new Set(events.map(event => category(event.curso)))];
        const mesh = roomMeshes.get(room);
        if (mesh) {
            const materials = mesh.userData.surfaceMaterials;
            for (const material of materials) material.opacity = 0;
            if (activeCourses.length) {
                for (const course of activeCourses) {
                    const materialIndex = { ARQU: 0, DPRO: 1, DVIS: 2, OTHER: 3 }[course];
                    materials[materialIndex].opacity = 0.64;
                }
            } else {
                materials[4].opacity = 0.055;
            }
            const activeMaterials = activeCourses.length
                ? activeCourses.map(course => ({ ARQU: 0, DPRO: 1, DVIS: 2, OTHER: 3 })[course])
                : [4];
            mesh.geometry.clearGroups();
            for (const group of mesh.userData.groups) mesh.geometry.addGroup(group.start, group.count, activeMaterials[group.faceIndex % activeMaterials.length]);
            const edges = roomEdges.get(room);
            if (edges) edges.material.color.set(
                selectedRoom === room ? 0x17262c : activeCourses.length === 1 ? colors[activeCourses[0]] : 0x71827e
            );
        }
        const status = document.createElement('div');
        status.className = 'status';
        const title = document.createElement('h3');
        title.textContent = room;
        const detail = document.createElement('p');
        if (!events.length) {
            detail.textContent = 'Livre neste horário';
        } else {
            detail.innerHTML = [...new Map(events.map(event => [`${event.codigo_disciplina}/${event.turma}/${event.curso}`, event])).values()].map(event => {
                const key = category(event.curso);
                const name = courseNames[key] || event.curso;
                const swatch = colors[key] || colors.OTHER;
                return `<span class="swatch" style="background:${swatch}"></span>${name}: ${event.codigo_disciplina} · ${event.nome_disciplina}`;
            }).join('<br>');
        }
        status.append(title, detail);
        statuses.appendChild(status);
    }
}

function selectRoom(room) {
    selectedRoom = room;
    selectionHint.hidden = true;
    roomInfo.hidden = false;
    roomInfo.replaceChildren();
    const records = data.agenda.filter(event => event.sala === room);
    const first = records[0];
    const meetings = new Map();
    for (const event of records) {
        const key = [event.codigo_disciplina, event.turma, event.dia_semana, event.hora_inicio, event.hora_fim, event.turmas_compartilhando_sala].join('|');
        if (!meetings.has(key)) meetings.set(key, { ...event, courses: new Map(), teachers: new Set() });
        meetings.get(key).courses.set(event.curso, event);
        meetings.get(key).teachers.add(event.docente);
    }
    const weeklyEvents = [...meetings.values()].map(event => ({
        ...event,
        courses: [...event.courses.values()],
        teachers: [...event.teachers],
    })).sort((a, b) =>
        roomOrder[a.dia_semana] - roomOrder[b.dia_semana]
        || a.hora_inicio.localeCompare(b.hora_inicio)
        || a.codigo_disciplina.localeCompare(b.codigo_disciplina)
    );

    const header = document.createElement('div');
    header.className = 'room-info-head';
    const title = document.createElement('h2');
    title.textContent = `${room} · ${first?.tipo_sala || 'Tipo de sala indisponível'}`;
    const close = document.createElement('button');
    close.type = 'button';
    close.textContent = 'Fechar';
    close.setAttribute('aria-label', 'Fechar informações da sala');
    close.addEventListener('click', () => {
        selectedRoom = null;
        roomInfo.hidden = true;
        selectionHint.hidden = false;
        updateOccupation();
    });
    header.append(title, close);
    const metadata = document.createElement('p');
    metadata.className = 'room-meta';
    const capacityValues = [...new Set(records.map(event => event.capacidade_turma))];
    metadata.textContent = `Capacidade da turma: ${capacityValues.join(' / ') || 'não informada'} lugares · ${weeklyEvents.length} encontros na semana`;
    roomInfo.append(header, metadata);

    if (!weeklyEvents.length) {
        const empty = document.createElement('p');
        empty.textContent = 'Não há registros de utilização desta sala no CSV.';
        roomInfo.appendChild(empty);
        return;
    }

    const agendaWrap = document.createElement('div');
    agendaWrap.className = 'agenda-wrap';
    const agendaGrid = document.createElement('div');
    agendaGrid.className = 'agenda-grid';

    data.dias.forEach((day, dayIndex) => {
        const heading = document.createElement('div');
        heading.className = 'agenda-day';
        heading.style.gridColumn = String(dayIndex + 2);
        heading.textContent = day;
        agendaGrid.appendChild(heading);

        const track = document.createElement('div');
        track.className = 'agenda-track';
        track.style.gridColumn = String(dayIndex + 2);
        agendaGrid.appendChild(track);

        const lunch = document.createElement('div');
        lunch.className = 'agenda-lunch';
        lunch.style.gridColumn = String(dayIndex + 2);
        lunch.title = 'Intervalo de almoço';
        agendaGrid.appendChild(lunch);
    });

    for (let minute = 450; minute <= 1350; minute += 60) {
        const tick = document.createElement('div');
        tick.className = 'agenda-tick';
        tick.style.gridRow = String(2 + (minute - 450) / 30);
        tick.textContent = formatTime(minute);
        agendaGrid.appendChild(tick);
    }

    const courseShortNames = { ARQU: 'Arquitetura', DPRO: 'Produto', DVIS: 'Visual' };
    const courseTints = { ARQU: '#fce9e9', DPRO: '#e8f0fd', DVIS: '#e7f5ed', OTHER: '#eef1f2' };
    for (const event of weeklyEvents) {
        const start = Math.max(450, toMinutes(event.hora_inicio));
        const end = Math.min(1350, toMinutes(event.hora_fim));
        if (end <= start) continue;

        const startSlot = Math.floor((start - 450) / 30);
        const durationSlots = Math.max(1, Math.ceil((end - start) / 30));
        const dayIndex = data.dias.indexOf(event.dia_semana);
        if (dayIndex < 0) continue;

        const eventBox = document.createElement('div');
        eventBox.className = 'agenda-event';
        eventBox.style.gridColumn = String(dayIndex + 2);
        eventBox.style.gridRow = `${2 + startSlot} / span ${durationSlots}`;
        const firstCourse = category(event.courses[0]?.curso);
        const eventColor = colors[firstCourse] || colors.OTHER;
        eventBox.style.setProperty('--event-color', eventColor);
        eventBox.style.setProperty('--event-tint', courseTints[firstCourse] || courseTints.OTHER);
        if (durationSlots >= 4) eventBox.classList.add('is-long');

        const courseNamesForEvent = event.courses.map(course => courseNames[category(course.curso)] || course.curso);
        const detailText = [
            `${event.codigo_disciplina} · ${event.nome_disciplina}`,
            `Turma ${event.turma} · ${event.dia_semana} · ${event.hora_inicio}–${event.hora_fim}`,
            `Curso(s): ${courseNamesForEvent.join(', ')}`,
            `Docente(s): ${event.teachers.join(', ')}`,
            `${event.numero_periodos} períodos · etapa ${event.etapa} · ${event.creditos} créditos`,
            `Vagas: ${event.vagas_oferecidas} de ${event.vagas_totais_compartilhadas} (${event.turmas_compartilhando_sala})`,
        ];
        eventBox.title = detailText.join('\n');

        const eventTitle = document.createElement('strong');
        eventTitle.textContent = `${event.codigo_disciplina} · Turma ${event.turma}`;
        const courseList = document.createElement('span');
        courseList.className = 'event-courses';
        for (const course of event.courses) {
            const courseTag = document.createElement('span');
            const courseCategory = category(course.curso);
            courseTag.className = 'event-course';
            courseTag.style.backgroundColor = colors[courseCategory] || colors.OTHER;
            courseTag.textContent = courseShortNames[courseCategory] || course.curso;
            courseList.appendChild(courseTag);
        }
        const eventName = document.createElement('span');
        eventName.className = 'event-name';
        eventName.textContent = event.nome_disciplina;
        const eventTime = document.createElement('span');
        eventTime.textContent = `${event.hora_inicio}–${event.hora_fim}`;
        const eventDetails = document.createElement('span');
        eventDetails.className = 'event-details';
        eventDetails.textContent = `${event.teachers.join('/')} · ${event.numero_periodos} períodos · ${event.creditos} cr`;
        eventBox.append(eventTitle, courseList, eventName, eventTime, eventDetails);
        agendaGrid.appendChild(eventBox);
    }

    agendaWrap.appendChild(agendaGrid);
    roomInfo.appendChild(agendaWrap);
    updateOccupation();
}

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
renderer.domElement.addEventListener('click', event => {
    const bounds = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
    pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const intersections = raycaster.intersectObjects([...roomMeshes.values()], false);
    if (intersections.length) selectRoom(intersections[0].object.userData.room);
});

function resize() {
    const width = wrap.clientWidth;
    const height = wrap.clientHeight;
    const aspect = width / height;
    const direction = camera.position.clone().sub(controls.target).normalize();
    const verticalFov = THREE.MathUtils.degToRad(camera.fov);
    const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * aspect);
    const fitFov = Math.min(verticalFov, horizontalFov);
    const sphere = bounds.getBoundingSphere(new THREE.Sphere());
    const distance = (sphere.radius / Math.sin(fitFov / 2)) * 1.14;
    camera.position.copy(center).addScaledVector(direction, distance);
    controls.target.copy(center);
    renderer.setSize(width, height, false);
    camera.aspect = aspect;
    camera.updateProjectionMatrix();
}
const resizeObserver = new ResizeObserver(resize);
resizeObserver.observe(wrap);
dayControl.addEventListener('change', updateOccupation);
timeControl.addEventListener('input', updateOccupation);
document.getElementById('reset').addEventListener('click', () => {
    controls.target.copy(center);
    camera.position.copy(center).add(new THREE.Vector3(span * 1.2, span * 0.85, span * 1.4));
    controls.update();
});
updateOccupation();
resize();
function animate() {
    controls.update();
    renderer.render(scene, camera);
    for (const [room, tag] of labels) {
        const mesh = roomMeshes.get(room);
        const point = mesh.geometry.boundingBox.getCenter(new THREE.Vector3());
        point.y = mesh.geometry.boundingBox.max.y + 0.8;
        mesh.localToWorld(point);
        point.project(camera);
        if (wrap.clientWidth < 500) {
            const mobilePosition = { 'Sala 301A': 0.18, 'Sala 501': 0.5, 'Sala 504': 0.82 }[room];
            tag.style.left = `${wrap.clientWidth * mobilePosition}px`;
            tag.style.top = '11%';
        } else {
            tag.style.left = `${(point.x * 0.5 + 0.5) * wrap.clientWidth}px`;
            tag.style.top = `${(-point.y * 0.5 + 0.5) * wrap.clientHeight}px`;
        }
        tag.hidden = point.z < -1 || point.z > 1;
    }
    requestAnimationFrame(animate);
}
animate();
</script>
</body>
</html>'''
        components.html(
                html.replace("__SCENE_DATA__", dados_json),
                height=740,
                scrolling=False,
        )


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
        "**3. Como as diferentes salas e tipos de espaço são utilizados ao "
        "longo da semana?**  \n"
        "**Configuração:** use `Tipo de espaço`, `Sala` e `Dia da semana`. "
        "O gráfico **Utilização das salas e tipos de espaço** compara as "
        "horas-aula por sala, usando encontros físicos deduplicados."
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

    st.subheader("3. Utilização das salas e tipos de espaço")
    exibir_grafico_salas(dados_fisicos)


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

    st.subheader("Possíveis sobreposições de horários por docente")
    st.write(
        "A tabela apresenta sobreposições na programação registrada para o mesmo "
        "docente e dia. Ela é um alerta para investigação, não uma confirmação "
        "de conflito real, pois a base não registra todas as restrições docentes."
    )
    conflitos = encontrar_sobreposicoes_docentes(dados)
    if conflitos.empty:
        st.success("Não foram encontradas possíveis sobreposições no recorte filtrado.")
    else:
        st.dataframe(conflitos, use_container_width=True, hide_index=True)

    st.subheader("Observações metodológicas")
    st.markdown(
        "- A visão por curso mantém linhas repetidas quando um encontro atende "
        "mais de um curso.\n"
        "- As visualizações físicas deduplicam o mesmo encontro para não contar "
        "uma sala várias vezes.\n"
        "- Horários sem registro não garantem disponibilidade operacional.\n"
        "- A análise descreve a ocupação regular de 2026/2 e não resolve, sozinha, "
        "a montagem de uma nova grade."
    )

    # O checklist final torna explícita a relação entre a implementação e os
    # requisitos da atividade. Ele também funciona como uma conferência rápida
    # para o grupo antes de entregar o dashboard.
    st.subheader("Checklist de atendimento da atividade")
    st.markdown(
        "- [✓] Investiga pelo menos duas perguntas da Atividade 01.\n"
        "- [✓] Apresenta quatro visualizações de dados; o gráfico 4 descreve a ocupação atual por sala.\n"
        "- [✓] Utiliza duas bibliotecas de visualização: Plotly e Matplotlib.\n"
        "- [✓] Oferece mais de dois controles interativos na barra lateral.\n"
        "- [✓] Atualiza as visualizações conforme os filtros são alterados.\n"
        "- [✓] Informa quando a seleção de filtros não encontra registros.\n"
        "- [✓] Apresenta títulos, rótulos, unidades, fonte e textos interpretativos.\n"
        "- [✓] Permite execução local com `streamlit run app.py`."
    )

    exibir_visualizacao_3d(dados)


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
        ],
        position="top",
    )
    navegacao.run()


if __name__ == "__main__":
    main()