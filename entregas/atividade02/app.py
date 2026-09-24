"""Dashboard interativo da Atividade 02.

O aplicativo transforma a proposta de análise da Atividade 01 em uma interface
interativa. A fonte de dados e este arquivo ficam na mesma pasta, o que torna a
execução reproduzível com `streamlit run app.py`.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------------------------------------------------------------
# Configuração geral e constantes
# -----------------------------------------------------------------------------

# O caminho é construído a partir da localização deste arquivo, e não do
# diretório em que o comando foi digitado. Assim, o app funciona mesmo quando
# o usuário o inicia a partir da raiz do projeto.
PASTA_APP = Path(__file__).resolve().parent
CAMINHO_DADOS = PASTA_APP / "mapa_salas_tidy_02.csv"

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
    """Lê o CSV, valida a estrutura e cria colunas úteis para o dashboard.

    O cache evita que o arquivo seja lido novamente a cada interação com um
    filtro. O caminho é recebido como texto para que o Streamlit consiga
    acompanhar a dependência de forma estável.
    """

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
    """Converte um horário HH:MM para minutos desde 00:00."""

    horas, minutos = str(horario).split(":")
    return int(horas) * 60 + int(minutos)


def classificar_turno(inicio_minutos: int) -> str:
    """Classifica o início de uma aula em manhã, tarde ou noite."""

    if inicio_minutos < 12 * 60 + 30:
        return "Manhã"
    if inicio_minutos < 18 * 60 + 30:
        return "Tarde"
    return "Noite"


def criar_visao_fisica(dados: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma linha por encontro físico, sem duplicação por curso.

    A base detalhada contém várias linhas quando uma disciplina atende mais de
    um curso ou quando turmas compartilham a sala. Para medir o uso físico do
    espaço, essas linhas representam o mesmo evento e não devem ser somadas
    várias vezes.
    """

    return dados.drop_duplicates(subset=CHAVE_ENCONTRO_FISICO).copy()


def aplicar_filtros(
    dados: pd.DataFrame,
    cursos: list[str],
    salas: list[str],
    tipos_sala: list[str],
    dias: list[str],
    turnos: list[str],
) -> pd.DataFrame:
    """Aplica os filtros escolhidos pelo usuário.

    Cada lista vazia representa a opção "Todos". O filtro é feito com uma
    cópia para evitar alterações acidentais no DataFrame armazenado em cache.
    """

    dados_filtrados = dados.copy()
    filtros = {
        "curso": cursos,
        "sala": salas,
        "tipo_sala": tipos_sala,
        "dia_semana": dias,
        "turno": turnos,
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
    """Soma horas por curso e dia para responder à primeira pergunta."""

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
    """Cria uma linha para cada hora ocupada de um encontro físico.

    A base registra o começo e o fim de um intervalo contínuo. Para construir
    o mapa de calor horário, cada período de uma hora é representado por uma
    linha. O intervalo final é exclusivo: uma aula 09:30-12:30 ocupa 09:30,
    10:30 e 11:30, totalizando três períodos.
    """

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
    """Converte minutos desde meia-noite para HH:MM."""

    horas = minutos // 60
    minutos_resto = minutos % 60
    return f"{horas:02d}:{minutos_resto:02d}"


def horas_por_sala_e_tipo(dados: pd.DataFrame) -> pd.DataFrame:
    """Soma horas físicas por sala e tipo de espaço para a terceira pergunta."""

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
    """Encontra encontros sobrepostos do mesmo docente no mesmo dia.

    A comparação usa intervalos semiabertos [início, fim). Assim, um encontro
    que termina às 12:30 e outro que começa às 12:30 não é considerado
    sobreposto. O resultado indica uma possibilidade de conflito na programação
    registrada, não uma confirmação da indisponibilidade do professor.
    """

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
    """Exibe a visualização da primeira pergunta com Plotly."""

    agregado = horas_por_curso_e_dia(dados)
    if agregado.empty:
        st.info("Não há dados para o mapa de calor por curso e dia.")
        return

    # Cria uma coluna exclusiva para exibição. O código original continua
    # disponível em `curso` e segue sendo usado para filtrar e agrupar.
    agregado["curso_nome"] = agregado["curso"].map(
        lambda codigo: ROTULOS_CURSO.get(codigo, codigo)
    )

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
    figura.update_layout(coloraxis_colorbar_title="Horas-aula")
    st.plotly_chart(figura, use_container_width=True)
    st.caption(
        "Biblioteca: Plotly. A soma mantém as linhas por curso para mostrar a "
        "distribuição da carga acadêmica. Um encontro compartilhado pode aparecer "
        "em mais de um curso."
    )


def exibir_grafico_horario(dados_fisicos: pd.DataFrame) -> None:
    """Exibe a visualização da segunda pergunta com Plotly."""

    dados_horarios = expandir_encontros_em_horas(dados_fisicos)
    if dados_horarios.empty:
        st.info("Não há dados para o mapa de calor por horário.")
        return

    agregado = (
        dados_horarios.groupby(["dia_semana", "horario"], as_index=False)["horas_aula"]
        .sum()
    )
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
        title="Ocupação física por dia e horário",
    )
    figura.update_yaxes(categoryorder="array", categoryarray=sorted(agregado["horario"].unique()))
    figura.update_layout(coloraxis_colorbar_title="Horas de ocupação")
    st.plotly_chart(figura, use_container_width=True)
    st.caption(
        "Biblioteca: Plotly. Cada encontro físico foi expandido em períodos de uma "
        "hora. A ausência de registro indica apenas que não há aula registrada "
        "naquele intervalo."
    )


def exibir_grafico_salas(dados_fisicos: pd.DataFrame) -> None:
    """Exibe a visualização da terceira pergunta com Matplotlib."""

    agregado = horas_por_sala_e_tipo(dados_fisicos)
    if agregado.empty:
        st.info("Não há dados para o gráfico de salas e tipos de espaço.")
        return

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

    figura.tight_layout()
    st.pyplot(figura)
    plt.close(figura)
    st.caption(
        "Biblioteca: Matplotlib. As horas são calculadas sobre encontros físicos "
        "deduplicados; por isso, turmas que compartilham uma sala não inflacionam "
        "o total do espaço."
    )


def exibir_indicadores(dados_detalhados: pd.DataFrame, dados_fisicos: pd.DataFrame) -> None:
    """Exibe indicadores resumidos do recorte filtrado."""

    horas_fisicas = dados_fisicos["numero_periodos"].sum()
    quantidade_salas = dados_fisicos["sala"].nunique()
    quantidade_cursos = dados_detalhados["curso"].nunique()

    primeira_coluna, segunda_coluna, terceira_coluna = st.columns(3)
    primeira_coluna.metric("Horas-aula físicas", f"{horas_fisicas:.0f}")
    segunda_coluna.metric("Salas utilizadas", f"{quantidade_salas}")
    terceira_coluna.metric("Cursos no recorte", f"{quantidade_cursos}")


# -----------------------------------------------------------------------------
# Construção da página
# -----------------------------------------------------------------------------


def main() -> None:
    """Monta a página do dashboard e coordena filtros e gráficos."""

    st.set_page_config(
        page_title="Mapa de salas - Atividade 02",
        page_icon="📊",
        layout="wide",
    )

    st.title("Ocupação dos espaços de ensino")
    st.write(
        "Dashboard interativo da Atividade 02 sobre a programação regular de "
        "salas da Faculdade de Arquitetura no semestre 2026/2."
    )

    # Esta seção apresenta o roteiro analítico antes dos filtros e gráficos.
    # Assim, o usuário entende qual pergunta cada componente do dashboard ajuda
    # a investigar e não precisa inferir essa relação apenas pelos títulos.
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

    if not CAMINHO_DADOS.exists():
        st.error(f"Arquivo de dados não encontrado: {CAMINHO_DADOS}")
        st.stop()

    try:
        dados = carregar_dados(str(CAMINHO_DADOS))
    except (ValueError, OSError, pd.errors.ParserError) as erro:
        st.error(f"Não foi possível carregar a base de dados: {erro}")
        st.stop()

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

    dados_filtrados = aplicar_filtros(
        dados,
        cursos_selecionados,
        salas_selecionadas,
        tipos_selecionados,
        dias_selecionados,
        turnos_selecionados,
    )
    dados_fisicos = criar_visao_fisica(dados_filtrados)

    st.caption(
        "Fonte: mapa_salas_tidy_02.csv. Docentes são identificadores anonimizados "
        "(por exemplo, Prof01 e Prof02)."
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

    st.subheader("Possíveis sobreposições de horários por docente")
    st.write(
        "A tabela apresenta sobreposições na programação registrada para o mesmo "
        "docente e dia. Ela é um alerta para investigação, não uma confirmação "
        "de conflito real, pois a base não registra todas as restrições docentes."
    )
    conflitos = encontrar_sobreposicoes_docentes(dados_filtrados)
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
        "- [x] Investiga pelo menos duas perguntas da Atividade 01.\n"
        "- [x] Apresenta três visualizações de dados.\n"
        "- [x] Utiliza duas bibliotecas de visualização: Plotly e Matplotlib.\n"
        "- [x] Oferece mais de dois controles interativos na barra lateral.\n"
        "- [x] Atualiza as visualizações conforme os filtros são alterados.\n"
        "- [x] Informa quando a seleção de filtros não encontra registros.\n"
        "- [x] Apresenta títulos, rótulos, unidades, fonte e textos interpretativos.\n"
        "- [x] Permite execução local com `streamlit run app.py`."
    )


if __name__ == "__main__":
    main()