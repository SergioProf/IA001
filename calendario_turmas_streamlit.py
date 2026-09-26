from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PASTA_APP = Path(__file__).resolve().parent
CAMINHO_DADOS = PASTA_APP / "mapa_salas_tidy.csv"
ORDEM_DIAS = [
    "SEGUNDA-FEIRA",
    "TERÇA-FEIRA",
    "QUARTA-FEIRA",
    "QUINTA-FEIRA",
    "SEXTA-FEIRA",
]
ROTULOS_CURSO = {
    "ARQU": "Arquitetura e Urbanismo",
    "DVIS": "Design Visual",
    "DPRO": "Design de Produto",
    "CAGR": "Ciências Agrárias",
    "ENGMEC": "Engenharia Mecânica",
}
CHAVE_ENCONTRO = [
    "semestre",
    "predio",
    "sala",
    "tipo_sala",
    "codigo_disciplina",
    "nome_disciplina",
    "dia_semana",
    "hora_inicio",
    "hora_fim",
    "turmas_compartilhando_sala",
]


@st.cache_data

def carregar_dados(caminho: Path) -> pd.DataFrame:
    dados = pd.read_csv(caminho, encoding="utf-8-sig")
    obrigatorias = set(CHAVE_ENCONTRO) | {
        "capacidade_turma",
        "turma",
        "docente",
        "curso",
        "etapa",
        "numero_periodos",
        "vagas_oferecidas",
        "vagas_totais_compartilhadas",
    }
    faltantes = obrigatorias.difference(dados.columns)
    if faltantes:
        raise ValueError("Colunas ausentes: " + ", ".join(sorted(faltantes)))

    dados["etapa_num"] = pd.to_numeric(dados["etapa"], errors="coerce")
    dados["etapa_label"] = dados["etapa_num"].map(
        lambda valor: (
            str(int(valor))
            if pd.notna(valor) and float(valor).is_integer()
            else str(valor) if pd.notna(valor) else ""
        )
    )
    for coluna in [
        "capacidade_turma",
        "numero_periodos",
        "vagas_oferecidas",
        "vagas_totais_compartilhadas",
    ]:
        dados[coluna] = pd.to_numeric(dados[coluna], errors="coerce")
    return dados


def valores_unicos(valores) -> str:
    unicos = {
        str(valor).strip()
        for valor in valores
        if pd.notna(valor) and str(valor).strip()
    }
    return ", ".join(sorted(unicos)) or "Não informado"


def vagas_por_turma(grupo: pd.DataFrame) -> str:
    linhas = grupo[["turma", "curso", "vagas_oferecidas"]].drop_duplicates()
    vagas = []
    for linha in linhas.itertuples(index=False):
        if pd.notna(linha.vagas_oferecidas):
            curso = ROTULOS_CURSO.get(linha.curso, linha.curso)
            quantidade = f"{linha.vagas_oferecidas:g}"
            vagas.append(f"Turma {linha.turma} ({curso}): {quantidade}")
    return "<br>".join(sorted(set(vagas))) or "Não informado"


def criar_encontros(dados: pd.DataFrame) -> pd.DataFrame:
    registros = []
    for _, grupo in dados.groupby(CHAVE_ENCONTRO, dropna=False, sort=False):
        base = grupo.iloc[0]
        cursos = sorted(grupo["curso"].dropna().astype(str).unique())
        cursos_rotulados = [
            f"{curso} ({ROTULOS_CURSO.get(curso, curso)})" for curso in cursos
        ]
        registros.append(
            {
                **{coluna: base[coluna] for coluna in CHAVE_ENCONTRO},
                "cursos_hover": ", ".join(cursos_rotulados) or "Não informado",
                "etapas_hover": valores_unicos(grupo["etapa_label"]),
                "turmas_hover": valores_unicos(grupo["turma"]),
                "docentes_hover": valores_unicos(grupo["docente"]),
                "capacidade_hover": valores_unicos(grupo["capacidade_turma"]),
                "vagas_turma_hover": vagas_por_turma(grupo),
                "vagas_compartilhadas_hover": valores_unicos(
                    grupo["vagas_totais_compartilhadas"]
                ),
                "periodos": base["numero_periodos"],
            }
        )
    return pd.DataFrame(registros)


def horario_em_minutos(horario: str) -> int:
    horas, minutos = map(int, str(horario).split(":"))
    return horas * 60 + minutos


def distribuir_em_faixas(encontros: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    encontros = encontros.copy()
    encontros["inicio_minutos"] = encontros["hora_inicio"].map(horario_em_minutos)
    encontros["fim_minutos"] = encontros["hora_fim"].map(horario_em_minutos)
    encontros["duracao_minutos"] = (
        encontros["fim_minutos"] - encontros["inicio_minutos"]
    )
    indice_dias = {dia: indice for indice, dia in enumerate(ORDEM_DIAS)}
    encontros["dia_indice"] = encontros["dia_semana"].map(indice_dias)
    encontros = encontros.dropna(
        subset=["dia_indice", "inicio_minutos", "fim_minutos"]
    ).copy()
    encontros["dia_indice"] = encontros["dia_indice"].astype(int)
    encontros["faixa"] = 0

    faixas_por_dia = {}
    for dia, grupo in encontros.groupby("dia_indice"):
        finais_faixas = []
        ordem = grupo.sort_values(["inicio_minutos", "fim_minutos"]).index
        for indice in ordem:
            inicio = encontros.at[indice, "inicio_minutos"]
            fim = encontros.at[indice, "fim_minutos"]
            faixa = next(
                (i for i, final in enumerate(finais_faixas) if final <= inicio),
                len(finais_faixas),
            )
            if faixa == len(finais_faixas):
                finais_faixas.append(fim)
            else:
                finais_faixas[faixa] = fim
            encontros.at[indice, "faixa"] = faixa
        faixas_por_dia[dia] = len(finais_faixas)

    encontros["posicao_x"] = encontros.apply(
        lambda linha: (
            linha["dia_indice"] - 0.45
            + (linha["faixa"] + 0.5)
            * 0.9
            / faixas_por_dia[linha["dia_indice"]]
        ),
        axis=1,
    )
    encontros["largura"] = encontros["dia_indice"].map(
        lambda dia: 0.86 / faixas_por_dia[dia]
    )
    encontros["rotulo"] = (
        encontros["codigo_disciplina"] + " - " + encontros["turmas_hover"]
    )
    return encontros, faixas_por_dia


def criar_grafico(encontros: pd.DataFrame) -> go.Figure:
    figura = go.Figure()
    if encontros.empty:
        return figura

    encontros, _ = distribuir_em_faixas(encontros)
    codigos = sorted(encontros["codigo_disciplina"].unique())
    cores = px.colors.qualitative.Set3
    cores_por_codigo = {
        codigo: cores[indice % len(cores)]
        for indice, codigo in enumerate(codigos)
    }
    dados_hover = encontros[
        [
            "codigo_disciplina",
            "nome_disciplina",
            "cursos_hover",
            "etapas_hover",
            "turmas_hover",
            "docentes_hover",
            "predio",
            "sala",
            "tipo_sala",
            "capacidade_hover",
            "vagas_turma_hover",
            "vagas_compartilhadas_hover",
            "periodos",
            "hora_inicio",
            "hora_fim",
        ]
    ].to_numpy()
    rotulos = [
        rotulo if largura >= 0.18 and duracao >= 120 else ""
        for rotulo, largura, duracao in zip(
            encontros["rotulo"],
            encontros["largura"],
            encontros["duracao_minutos"],
        )
    ]
    figura.add_trace(
        go.Bar(
            x=encontros["posicao_x"],
            y=encontros["duracao_minutos"],
            base=encontros["inicio_minutos"],
            width=encontros["largura"],
            text=rotulos,
            textposition="inside",
            insidetextanchor="middle",
            textfont={"size": 9},
            marker_color=[
                cores_por_codigo[codigo]
                for codigo in encontros["codigo_disciplina"]
            ],
            customdata=dados_hover,
            hovertemplate=(
                "<b>%{customdata[0]} - %{customdata[4]}</b><br>"
                "Disciplina: %{customdata[1]}<br>"
                "Curso(s): %{customdata[2]}<br>"
                "Etapa(s): %{customdata[3]}<br>"
                "Docente(s): %{customdata[5]}<br>"
                "Prédio / sala: %{customdata[6]} / %{customdata[7]}<br>"
                "Tipo de sala: %{customdata[8]}<br>"
                "Capacidade: %{customdata[9]}<br>"
                "Vagas por turma:<br>%{customdata[10]}<br>"
                "Vagas compartilhadas: %{customdata[11]}<br>"
                "Períodos: %{customdata[12]}<br>"
                "Horário: %{customdata[13]} - %{customdata[14]}"
                "<extra></extra>"
            ),
            name="Encontros",
        )
    )

    horarios = list(range(450, 1351, 60))
    figura.update_layout(
        title="Calendário semanal das turmas",
        height=760,
        margin={"l": 65, "r": 25, "t": 65, "b": 45},
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        hoverlabel={"align": "left"},
        barmode="overlay",
        xaxis={
            "title": "Dia da semana",
            "tickmode": "array",
            "tickvals": list(range(len(ORDEM_DIAS))),
            "ticktext": ORDEM_DIAS,
            "range": [-0.55, len(ORDEM_DIAS) - 0.45],
            "side": "top",
            "showgrid": True,
            "gridcolor": "#e5e7eb",
            "zeroline": False,
        },
        yaxis={
            "title": "Horário",
            "tickmode": "array",
            "tickvals": horarios,
            "ticktext": [
                f"{minuto // 60:02d}:{minuto % 60:02d}"
                for minuto in horarios
            ],
            "range": [1350, 450],
            "showgrid": True,
            "gridcolor": "#e5e7eb",
            "zeroline": False,
        },
    )
    return figura


def main() -> None:
    st.set_page_config(page_title="Calendário semanal de turmas", layout="wide")
    st.title("Calendário semanal de turmas")

    if not CAMINHO_DADOS.exists():
        st.error(f"Arquivo de dados não encontrado: {CAMINHO_DADOS}")
        st.stop()

    try:
        dados = carregar_dados(CAMINHO_DADOS)
    except (OSError, ValueError, pd.errors.ParserError) as erro:
        st.error(f"Não foi possível carregar os dados: {erro}")
        st.stop()

    cursos = sorted(dados["curso"].dropna().astype(str).unique())
    st.sidebar.header("Filtros")
    cursos_selecionados = st.sidebar.multiselect(
        "Curso",
        cursos,
        default=cursos,
        format_func=lambda codigo: (
            f"{ROTULOS_CURSO.get(codigo, codigo)} ({codigo})"
        ),
    )
    if not cursos_selecionados:
        st.info("Selecione ao menos um curso.")
        st.stop()

    dados_curso = dados[dados["curso"].astype(str).isin(cursos_selecionados)]
    etapas = sorted(
        etapa for etapa in dados_curso["etapa_label"].unique() if etapa
    )
    etapas_selecionadas = st.sidebar.multiselect(
        "Etapa", etapas, default=etapas
    )
    dias_disponiveis = [
        dia for dia in ORDEM_DIAS if dia in dados_curso["dia_semana"].unique()
    ]
    dias_selecionados = st.sidebar.multiselect(
        "Dia da semana", dias_disponiveis, default=dias_disponiveis
    )

    if not etapas_selecionadas or not dias_selecionados:
        st.info("Selecione ao menos uma etapa e um dia da semana.")
        st.stop()

    dados_filtrados = dados_curso[
        dados_curso["etapa_label"].isin(etapas_selecionadas)
        & dados_curso["dia_semana"].isin(dias_selecionados)
    ].copy()
    if dados_filtrados.empty:
        st.warning("Nenhum encontro corresponde aos filtros selecionados.")
        st.stop()

    encontros = criar_encontros(dados_filtrados)
    figura = criar_grafico(encontros)
    primeira_metrica, segunda_metrica = st.columns(2)
    primeira_metrica.metric("Encontros", len(encontros))
    segunda_metrica.metric(
        "Cursos selecionados", len(cursos_selecionados)
    )
    st.plotly_chart(figura, use_container_width=True)


if __name__ == "__main__":
    main()
