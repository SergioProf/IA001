"""Auditoria semântica reproduzível da grade atual (baseline ANTES)."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from modelo_ocupacao_03 import ModeloOcupacao, carregar_modelo

CURSOS_ALVO = {"ARQU", "DPRO", "DVIS"}
JANELAS_TURNO = {"Manhã": (0, 750), "Tarde": (810, 1110), "Noite": (1110, 1440)}
ALMOCO = (750, 810)


def _minutos(horario: str) -> int:
    horas, minutos = horario.split(":")
    return int(horas) * 60 + int(minutos)


def _horario(minutos: int) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _intersecao(inicio: int, fim: int, limite_inicio: int, limite_fim: int) -> int:
    return max(0, min(fim, limite_fim) - max(inicio, limite_inicio))


def _horas_por_turno(inicio: int, fim: int) -> dict[str, float]:
    return {turno: _intersecao(inicio, fim, *janela) / 60 for turno, janela in JANELAS_TURNO.items()}


def _conflitos(ocorrencias: list[dict[str, Any]]) -> list[dict[str, Any]]:
    por_periodo: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for ocorrencia in ocorrencias:
        por_periodo[(ocorrencia["semestre"], ocorrencia["dia"])].append(ocorrencia)

    conflitos = []
    for eventos in por_periodo.values():
        eventos.sort(key=lambda item: item["inicio"])
        for atual, outro in combinations(eventos, 2):
            if outro["inicio"] >= atual["fim"]:
                break
            inicio = max(atual["inicio"], outro["inicio"])
            fim = min(atual["fim"], outro["fim"])
            comum = {
                "encontro_1": atual["id"], "encontro_2": outro["id"],
                "dia": atual["dia"], "sobreposicao": f"{_horario(inicio)}–{_horario(fim)}",
            }
            if (atual["predio"], atual["sala"]) == (outro["predio"], outro["sala"]):
                conflitos.append({"regra": "CONFLITO_SALA", **comum})
            docentes = sorted(atual["docentes"] & outro["docentes"])
            if docentes:
                conflitos.append({"regra": "CONFLITO_DOCENTE", "docentes": docentes, **comum})
            etapas = sorted(atual["etapas"] & outro["etapas"])
            if etapas:
                conflitos.append({"regra": "CONFLITO_ETAPA", "curso_etapa": etapas, **comum})
    return conflitos


def auditar_baseline(modelo: ModeloOcupacao) -> dict[str, Any]:
    """Calcula o ANTES por encontro físico, sem multiplicar linhas repetidas."""
    linhas_por_evento: dict[str, list[dict[str, str]]] = defaultdict(list)
    for linha in modelo.linhas_fonte:
        linhas_por_evento[linha["evento_fisico_id"]].append(linha["valores"])

    ocorrencias = []
    almoco = []
    por_curso_turno: dict[str, Counter[str]] = defaultdict(Counter)
    ch_periodos_curso: Counter[str] = Counter()
    horas_fora_turno = 0.0
    capacidade_eventos = []
    divergencias_vagas = []

    for encontro in modelo.encontros_fisicos:
        registros = linhas_por_evento[encontro.id]
        primeiro = registros[0]
        inicio, fim = _minutos(primeiro["hora_inicio"]), _minutos(primeiro["hora_fim"])
        cursos = {linha["curso"] for linha in registros}
        etapas = {
            (linha["curso"], linha["etapa"]) for linha in registros
            if linha["curso"] in CURSOS_ALVO and linha["etapa"] != "0"
        }
        docentes = {
            atribuicao.docente for atribuicao in modelo.atribuicoes_docentes
            if atribuicao.evento_fisico_id == encontro.id
        }
        evento = {
            "id": encontro.id, "semestre": primeiro["semestre"], "predio": primeiro["predio"],
            "sala": primeiro["sala"], "tipo_sala": primeiro["tipo_sala"],
            "dia": primeiro["dia_semana"], "inicio": inicio, "fim": fim,
            "periodos": int(primeiro["numero_periodos"]), "cursos": cursos,
            "etapas": etapas, "docentes": docentes,
        }
        ocorrencias.append(evento)
        horas_turno = _horas_por_turno(inicio, fim)
        horas_fora_turno += max(0, fim - inicio) / 60 - sum(horas_turno.values())
        for curso in cursos:
            ch_periodos_curso[curso] += evento["periodos"]
            for turno, horas in horas_turno.items():
                por_curso_turno[curso][turno] += horas
        if _intersecao(inicio, fim, *ALMOCO):
            almoco.append({
                "encontro_id": encontro.id, "disciplina": primeiro["codigo_disciplina"],
                "grupo": primeiro["turmas_compartilhando_sala"], "dia": evento["dia"],
                "horario": f"{_horario(inicio)}–{_horario(fim)}",
            })

        por_membro: dict[str, set[tuple[int, int]]] = defaultdict(set)
        for linha in registros:
            por_membro[linha["turma"]].add((int(linha["vagas_oferecidas"]), int(linha["vagas_turma"])))
        if any(len(valores) != 1 for valores in por_membro.values()):
            divergencias_vagas.append({"encontro_id": encontro.id, "tipo": "valores_por_membro"})
        unicos = {membro: sorted(valores)[0] for membro, valores in por_membro.items() if valores}
        alunos = sum(valores[0] for valores in unicos.values())
        soma_vagas_turma = sum(valores[1] for valores in unicos.values())
        total_compartilhado = {int(linha["vagas_totais_compartilhadas"]) for linha in registros}
        if len(total_compartilhado) != 1 or alunos not in total_compartilhado:
            divergencias_vagas.append({
                "encontro_id": encontro.id, "tipo": "vagas_oferecidas_vs_vagas_totais_compartilhadas",
                "soma_vagas_oferecidas_unicas": alunos,
                "valores_vagas_totais_compartilhadas": sorted(total_compartilhado),
            })
        if alunos != soma_vagas_turma:
            divergencias_vagas.append({
                "encontro_id": encontro.id, "tipo": "vagas_oferecidas_vs_vagas_turma",
                "soma_vagas_oferecidas_unicas": alunos, "soma_vagas_turma_unicas": soma_vagas_turma,
            })
        capacidade = int(primeiro["capacidade_sala"])
        capacidade_eventos.append({
            "encontro_id": encontro.id, "disciplina": primeiro["codigo_disciplina"],
            "grupo": primeiro["turmas_compartilhando_sala"], "curso": ", ".join(sorted(cursos)),
            "sala": primeiro["sala"], "dia": evento["dia"],
            "horario": f"{_horario(inicio)}–{_horario(fim)}",
            "alunos": alunos, "capacidade_sala": capacidade,
            "ocupacao_percentual": 100 * alunos / capacidade if capacidade else None,
            "violacao_110": alunos > capacidade * 1.10,
        })

    conflitos = _conflitos(ocorrencias)
    linhas = [item["valores"] for item in modelo.linhas_fonte]
    cursos = {linha["curso"] for linha in linhas}
    cursos_objetivo = {"ARQU": {"Manhã", "Noite"}, "DPRO": {"Tarde", "Noite"}, "DVIS": {"Tarde", "Noite"}}
    turnos = {}
    for curso in sorted(cursos):
        objetivo = cursos_objetivo.get(curso, set())
        alvo = sum(por_curso_turno[curso][turno] for turno in objetivo)
        total = ch_periodos_curso[curso]
        turnos[curso] = {
            "objetivo": sorted(objetivo), "horas_por_turno": dict(sorted(por_curso_turno[curso].items())),
            "horas_turno_alvo": alvo, "ch_periodos_total": total,
            "percentual_ch_alvo": 100 * alvo / total if total else 0,
        }

    cargas_etapa: Counter[tuple[str, str, str]] = Counter()
    carga_docente_dia: Counter[tuple[str, str]] = Counter()
    carga_docente: Counter[str] = Counter()
    for evento in ocorrencias:
        for curso, etapa in evento["etapas"]:
            cargas_etapa[(curso, etapa, evento["dia"])] += evento["periodos"]
        if evento["cursos"] & CURSOS_ALVO:
            for docente in evento["docentes"]:
                carga_docente_dia[(docente, evento["dia"])] += evento["periodos"]
                carga_docente[docente] += evento["periodos"]

    tipos_sala = Counter(evento["tipo_sala"] for evento in ocorrencias)
    divergencias_por_tipo = Counter(item["tipo"] for item in divergencias_vagas)
    padroes_por_frequencia = Counter(len(padrao.encontros_fisicos) for padrao in modelo.padroes_semanais)
    salas = {(linha["predio"], linha["sala"]) for linha in linhas}
    disciplinas = {(linha["curso"], linha["codigo_disciplina"]) for linha in linhas}
    grupos = {(linha["curso"], linha["codigo_disciplina"], linha["turma"]) for linha in linhas}
    etapas = {(linha["curso"], linha["etapa"]) for linha in linhas}
    duplicatas = len(linhas) - len({tuple(linha[col] for col in modelo.cabecalho) for linha in linhas})
    return {
        "resumo": {
            **modelo.resumo(), "cursos": len(cursos), "etapas_curso": len(etapas),
            "disciplinas_curso": len(disciplinas), "grupos_academicos": len(grupos),
            "salas": len(salas), "horarios_distintos": len({(r["dia_semana"], r["hora_inicio"], r["hora_fim"]) for r in linhas}),
            "docentes": len({r["docente"] for r in linhas}), "duplicatas_exatas": duplicatas,
            "encontros_cruzam_almoco": len(almoco), "horas_fora_dos_turnos": horas_fora_turno,
        },
        "cursos_encontrados": sorted(cursos), "eventos_por_tipo_sala": dict(sorted(tipos_sala.items())),
        "padroes_por_numero_encontros": dict(sorted(padroes_por_frequencia.items())),
        "turnos_por_curso": turnos,
        "capacidade": {
            "acima_110_percentual": sum(item["violacao_110"] for item in capacidade_eventos),
            "maior_ocupacao_percentual": max((item["ocupacao_percentual"] or 0 for item in capacidade_eventos), default=0),
            "divergencias_vagas": divergencias_vagas,
            "divergencias_vagas_por_tipo": dict(sorted(divergencias_por_tipo.items())),
            "encontros": capacidade_eventos,
        },
        "conflitos_baseline": conflitos,
        "cargas_etapa_por_dia": [
            {"curso": c, "etapa": e, "dia": d, "periodos": n} for (c, e, d), n in sorted(cargas_etapa.items())
        ],
        "cargas_docente_por_dia": [
            {"docente": docente, "dia": dia, "periodos": n} for (docente, dia), n in sorted(carga_docente_dia.items())
        ],
        "carga_total_docente": [{"docente": docente, "periodos": n} for docente, n in sorted(carga_docente.items())],
        "encontros_cruzam_almoco": almoco,
    }


def gerar_relatorio_markdown(resultado: dict[str, Any]) -> str:
    resumo = resultado["resumo"]
    linhas = [
        "# Baseline da grade atual — Atividade 03", "",
        "Os apontamentos descrevem o ANTES; não são violações introduzidas por uma solução.", "",
        f"SHA-256 do CSV-fonte: `{resultado.get('source_sha256', 'não informado')}`.", "",
        "## Regras de contagem", "",
        "- Cada encontro físico canônico é contado uma vez; linhas repetidas por curso, membro ou docente não multiplicam a ocupação.",
        "- Manhã: antes de 12:30; tarde: 13:30–18:30; noite: a partir de 18:30. Almoço (12:30–13:30) não pertence a turno.",
        "- CH de turno é a duração em horas da interseção do encontro com cada janela. Encontros que cruzam limites são repartidos; almoço fica fora dos turnos.",
        "- O percentual-alvo divide horas de turno-alvo pela soma de `numero_periodos` uma vez por encontro e curso. Diferenças entre relógio e períodos não são redistribuídas.",
        "- Capacidade soma `vagas_oferecidas` por membro físico único (`turma`); compara também `vagas_turma` e `vagas_totais_compartilhadas`, sem somar cópias de linhas.",
        "- Conflito de etapa inclui somente ARQU/DPRO/DVIS e etapa diferente de 0. Etapa 0 continua sujeita a conflitos de sala e docente.",
        "- Cargas semanais são períodos por encontro, deduplicados. Conflitos também incluem cursos externos registrados.",
        "", "## Inventário", "", "| Métrica | Quantidade |", "| --- | ---: |",
    ]
    metricas = [("Linhas-fonte", "linhas_fonte"), ("Cursos", "cursos"), ("Etapas por curso", "etapas_curso"),
                ("Disciplinas por curso", "disciplinas_curso"), ("Grupos acadêmicos", "grupos_academicos"),
                ("Padrões semanais", "padroes_semanais"), ("Encontros físicos", "encontros_fisicos"),
                ("Salas", "salas"), ("Horários distintos", "horarios_distintos"), ("Docentes", "docentes"),
                ("Duplicatas exatas", "duplicatas_exatas")]
    linhas.extend(f"| {nome} | {resumo[chave]} |" for nome, chave in metricas)
    linhas.extend(["", f"Cursos encontrados: {', '.join(resultado['cursos_encontrados'])}.", "", "## Turnos e capacidade", "",
                   "| Curso | Turno-alvo | CH no alvo (h) | CH em períodos | CH no alvo (%) |", "| --- | --- | ---: | ---: | ---: |"])
    for curso, dados in resultado["turnos_por_curso"].items():
        linhas.append(f"| {curso} | {', '.join(dados['objetivo']) or 'N/A'} | {dados['horas_turno_alvo']:.2f} | {dados['ch_periodos_total']} | {dados['percentual_ch_alvo']:.2f}% |")
    capacidade = resultado["capacidade"]
    linhas.extend(["", f"Encontros acima de 110% da capacidade: {capacidade['acima_110_percentual']}; maior ocupação: {capacidade['maior_ocupacao_percentual']:.2f}%.",
                   f"Divergências nos campos de vagas por tipo: {capacidade['divergencias_vagas_por_tipo']}.",
                   "`vagas_oferecidas` foi comparada a `vagas_totais_compartilhadas`; `vagas_turma` foi comparada separadamente, sem presumir equivalência.",
                   "", "### Encontros por tipo de espaço", "",
                   "| Tipo | Encontros físicos |", "| --- | ---: |"])
    linhas.extend(f"| {tipo} | {quantidade} |" for tipo, quantidade in resultado["eventos_por_tipo_sala"].items())
    violacoes_capacidade = [evento for evento in capacidade["encontros"] if evento["violacao_110"]]
    if violacoes_capacidade:
        linhas.extend(["", "### Encontros acima de 110% da capacidade", "",
                       "| Disciplina | Grupo | Curso | Dia | Horário | Sala | Alunos | Capacidade | Ocupação |",
                       "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |"])
        for evento in violacoes_capacidade:
            linhas.append(f"| {evento['disciplina']} | {evento['grupo']} | {evento['curso']} | {evento['dia']} | {evento['horario']} | {evento['sala']} | {evento['alunos']} | {evento['capacidade_sala']} | {evento['ocupacao_percentual']:.2f}% |")
    linhas.extend(["", "## Frequência dos padrões semanais", "",
                   "| Encontros no padrão | Padrões |", "| ---: | ---: |"])
    linhas.extend(f"| {frequencia} | {quantidade} |" for frequencia, quantidade in resultado["padroes_por_numero_encontros"].items())
    por_regra = Counter(item["regra"] for item in resultado["conflitos_baseline"])
    linhas.extend(["", "## Conflitos potenciais no ANTES", "", "| Regra | Pares em conflito |", "| --- | ---: |"])
    for regra in ("CONFLITO_SALA", "CONFLITO_DOCENTE", "CONFLITO_ETAPA"):
        linhas.append(f"| {regra} | {por_regra[regra]} |")
    if resultado["conflitos_baseline"]:
        linhas.extend(["", "| Regra | Encontro 1 | Encontro 2 | Dia | Sobreposição |", "| --- | --- | --- | --- | --- |"])
        linhas.extend(f"| {conflito['regra']} | {conflito['encontro_1']} | {conflito['encontro_2']} | {conflito['dia']} | {conflito['sobreposicao']} |" for conflito in resultado["conflitos_baseline"])
    linhas.extend(["", f"Encontros que cruzam o almoço: {resumo['encontros_cruzam_almoco']}; horas não atribuídas a turno: {resumo['horas_fora_dos_turnos']:.2f}.", ""])
    if resultado["encontros_cruzam_almoco"]:
        linhas.extend(["### Encontros que cruzam o almoço", "", "| Disciplina | Grupo | Dia | Horário |", "| --- | --- | --- | --- |"])
        linhas.extend(f"| {e['disciplina']} | {e['grupo']} | {e['dia']} | {e['horario']} |" for e in resultado["encontros_cruzam_almoco"])
        linhas.append("")
    linhas.extend(["## Carga semanal por etapa obrigatória", "", "| Curso | Etapa | Dia | Períodos |", "| --- | ---: | --- | ---: |"])
    linhas.extend(f"| {e['curso']} | {e['etapa']} | {e['dia']} | {e['periodos']} |" for e in resultado["cargas_etapa_por_dia"])
    linhas.extend(["", "## Carga semanal por docente", "", "| Docente | Dia | Períodos |", "| --- | --- | ---: |"])
    linhas.extend(f"| {e['docente']} | {e['dia']} | {e['periodos']} |" for e in resultado["cargas_docente_por_dia"])
    linhas.extend(["", "## Limites", "", "- Sala sem aula no CSV não prova disponibilidade externa à grade registrada.",
                   "- `etapa` e `creditos` são usados como registrados; a origem permanece não confirmada na auditoria de linhagem.",
                   "- Divergências nos campos de vagas são reportadas, não corrigidas automaticamente.", ""])
    return "\n".join(linhas)


def main() -> None:
    pasta = Path(__file__).parent
    fonte = pasta / "mapa_salas_tidy_03.csv"
    resultado = auditar_baseline(carregar_modelo(fonte))
    resultado["source_sha256"] = hashlib.sha256(fonte.read_bytes()).hexdigest()
    destino = pasta / "baseline_03.md"
    destino.write_text(gerar_relatorio_markdown(resultado), encoding="utf-8")
    print(f"Relatório gerado: {destino}")
    print(resultado["resumo"])


if __name__ == "__main__":
    main()