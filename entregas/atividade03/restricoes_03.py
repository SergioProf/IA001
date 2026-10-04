"""Regras executáveis para validar propostas de alocação da Atividade 03."""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Mapping

from modelo_ocupacao_03 import EncontroFisico, ModeloOcupacao


CURSOS_ALVO = {"ARQU", "DPRO", "DVIS"}
DIAS_VALIDOS = {"SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA"}
ALMOCO = (12 * 60 + 30, 13 * 60 + 30)
TURNOS_ALVO = {
    "ARQU": ((0, 12 * 60 + 30), (18 * 60 + 30, 24 * 60)),
    "DPRO": ((13 * 60 + 30, 18 * 60 + 30), (18 * 60 + 30, 24 * 60)),
    "DVIS": ((13 * 60 + 30, 18 * 60 + 30), (18 * 60 + 30, 24 * 60)),
}


@dataclass(frozen=True)
class Regra:
    id: str
    severidade: str
    descricao: str
    teste: str


@dataclass(frozen=True)
class Diagnostico:
    regra: str
    severidade: str
    mensagem: str
    encontros: tuple[str, ...] = ()


REGRAS = (
    Regra("H001", "inviolavel", "Conservar exatamente os encontros existentes.", "test_cobertura_de_encontros_e_campos_imutaveis"),
    Regra("H002", "inviolavel", "Permitir somente segunda a sexta-feira.", "test_dias_validos_e_sabado_proibido"),
    Regra("H003", "inviolavel", "Não permitir ocupação entre 12:30 e 13:30.", "test_limites_do_almoco"),
    Regra("H004", "inviolavel", "Impedir sobreposição de sala.", "test_sobreposicao_de_sala_e_intervalos_semiabertos"),
    Regra("H005", "inviolavel", "Impedir sobreposição de docente, em qualquer curso.", "test_conflito_docente_entre_cursos"),
    Regra("H006", "inviolavel", "Cada etapa/curso deve permitir cursar todas as disciplinas escolhendo uma turma de cada, sem sobreposição; turmas da mesma disciplina podem coincidir; etapa 0 é isenta somente aqui.", "test_etapa_obrigatoria_e_eletiva"),
    Regra("H007", "inviolavel", "Manter imóveis os encontros de cursos externos.", "test_cursos_externos_imoveis"),
    Regra("H008", "inviolavel", "Limitar vagas a 120% da capacidade, por membros físicos únicos.", "test_limite_de_capacidade"),
    Regra("H009", "inviolavel", "Manter encontros dependentes de computador em laboratório.", "test_dependencia_de_laboratorio"),
    Regra("H010", "inviolavel_com_excecao", "Exigir justificativa para cada minuto fora do turno-alvo.", "test_relaxamento_de_turno_com_justificativa"),
    Regra("P01", "preferencia", "Priorizar preservação de sala, dia e horário; depois dia/horário, dia e padrão semanal.", "test_nivel_de_preservacao"),
    Regra("P02", "preferencia", "Manter o tipo de espaço original quando possível.", "test_preferencias_de_espaco"),
    Regra("P03", "preferencia", "Evitar laboratório para encontros sem dependência de computador.", "test_preferencias_de_espaco"),
    Regra("P04", "preferencia", "Priorizar maior número de alunos, obrigatórias e maiores cargas.", "test_prioridade_de_alocacao"),
    Regra("P05", "preferencia", "Preferir início da noite e aulas consecutivas; equilibrar cargas semanais.", "test_metricas_de_preferencia"),
)

PRIORIDADE_TURMAS = ("alunos_desc", "obrigatoria_antes_eletiva", "encontros_desc", "ch_semanal_desc")
CAMPOS_ALOCACAO = {"predio", "sala", "dia_semana", "hora_inicio", "hora_fim"}


def _normalizar(texto: str) -> str:
    decomposicao = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(caractere for caractere in decomposicao if not unicodedata.combining(caractere))


def _minutos(horario: str) -> int:
    try:
        horas, minutos = (int(parte) for parte in horario.split(":"))
    except (ValueError, AttributeError) as erro:
        raise ValueError(f"Horário inválido: {horario!r}.") from erro
    if not 0 <= horas <= 24 or not 0 <= minutos < 60 or (horas == 24 and minutos != 0):
        raise ValueError(f"Horário inválido: {horario!r}.")
    return horas * 60 + minutos


def _intervalos_sobrepostos(inicio_a: int, fim_a: int, inicio_b: int, fim_b: int) -> bool:
    return inicio_a < fim_b and inicio_b < fim_a


def _linhas_por_encontro(modelo: ModeloOcupacao) -> dict[str, list[dict[str, Any]]]:
    por_encontro: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for linha in modelo.linhas_fonte:
        por_encontro[linha["evento_fisico_id"]].append(linha["valores"])
    return por_encontro


def _alocacao_original(encontro: EncontroFisico) -> dict[str, str]:
    atributos = encontro.atributos_fisicos
    return {campo: atributos[campo] for campo in CAMPOS_ALOCACAO}


def _diagnostico(regra: str, severidade: str, mensagem: str, *encontros: str) -> Diagnostico:
    return Diagnostico(regra, severidade, mensagem, tuple(encontros))


def _unir_intervalos(intervalos: list[tuple[int, int]]) -> list[tuple[int, int]]:
    unidos: list[list[int]] = []
    for inicio, fim in sorted(intervalos):
        if unidos and inicio <= unidos[-1][1]:
            unidos[-1][1] = max(unidos[-1][1], fim)
        else:
            unidos.append([inicio, fim])
    return [(inicio, fim) for inicio, fim in unidos]


def secoes_por_etapa(
    modelo: ModeloOcupacao,
) -> dict[tuple[str, str, str], dict[str, dict[str, set[str]]]]:
    """(semestre, curso, etapa) -> disciplina -> turma -> encontros dessa turma (etapa 0 é isenta)."""

    grupos: dict[tuple[str, str, str], dict[str, dict[str, set[str]]]] = {}
    for linha in modelo.linhas_fonte:
        valores = linha["valores"]
        if valores["curso"] not in CURSOS_ALVO or valores["etapa"] == "0":
            continue
        chave = (valores["semestre"], valores["curso"], valores["etapa"])
        turmas = grupos.setdefault(chave, {}).setdefault(valores["codigo_disciplina"], {})
        turmas.setdefault(valores["turma"], set()).add(linha["evento_fisico_id"])
    return grupos


def etapa_cursavel(
    disciplinas: Mapping[str, Mapping[str, set[str]]],
    horarios: Mapping[str, tuple[str, int, int]],
) -> bool:
    """Há uma turma por disciplina tal que nenhuma escolhida se sobrepõe a outra?"""

    opcoes = sorted((list(turmas.values()) for turmas in disciplinas.values()), key=len)

    def sobrepoe(secao_a: set[str], secao_b: set[str]) -> bool:
        for a in secao_a:
            for b in secao_b:
                if a == b or a not in horarios or b not in horarios:
                    continue
                (dia_a, inicio_a, fim_a), (dia_b, inicio_b, fim_b) = horarios[a], horarios[b]
                if dia_a == dia_b and _intervalos_sobrepostos(inicio_a, fim_a, inicio_b, fim_b):
                    return True
        return False

    def buscar(indice: int, escolhidas: list[set[str]]) -> bool:
        if indice == len(opcoes):
            return True
        return any(
            not any(sobrepoe(secao, outra) for outra in escolhidas)
            and buscar(indice + 1, [*escolhidas, secao])
            for secao in opcoes[indice]
        )

    return buscar(0, [])


def validar_grade(
    modelo: ModeloOcupacao,
    alocacoes: Mapping[str, Mapping[str, str]] | None = None,
    excecoes_turno: Mapping[str, str] | None = None,
) -> list[Diagnostico]:
    """Valida posições candidatas; docentes, membros, frequência e duração são imutáveis.

    Cada alocação aceita somente predio, sala, dia_semana, hora_inicio e hora_fim.
    """

    encontros = {encontro.id: encontro for encontro in modelo.encontros_fisicos}
    alocacoes_informadas = alocacoes is not None
    alocacoes = {} if alocacoes is None else alocacoes
    excecoes_turno = excecoes_turno or {}
    diagnosticos: list[Diagnostico] = []
    extras = set(alocacoes).difference(encontros)
    ausentes = set(encontros).difference(alocacoes) if alocacoes_informadas else set()
    if extras or ausentes:
        diagnosticos.append(_diagnostico(
            "H001", "inviolavel",
            f"A proposta deve conter exatamente os {len(encontros)} encontros originais; ausentes={len(ausentes)}, desconhecidos={len(extras)}.",
            *sorted(ausentes | extras),
        ))

    fontes = _linhas_por_encontro(modelo)
    alocacoes_efetivas: dict[str, dict[str, str]] = {}
    for encontro_id, encontro in encontros.items():
        original = _alocacao_original(encontro)
        proposta = dict(alocacoes.get(encontro_id, original))
        campos_inesperados = set(proposta).difference(CAMPOS_ALOCACAO)
        campos_ausentes = CAMPOS_ALOCACAO.difference(proposta)
        if campos_inesperados or campos_ausentes:
            diagnosticos.append(_diagnostico(
                "H001", "inviolavel",
                f"Encontro {encontro_id}: alocação deve conter somente {sorted(CAMPOS_ALOCACAO)}; campos ausentes={sorted(campos_ausentes)}, extras={sorted(campos_inesperados)}.",
                encontro_id,
            ))
            proposta = {**original, **{k: v for k, v in proposta.items() if k in CAMPOS_ALOCACAO}}
        alocacoes_efetivas[encontro_id] = proposta

    inventario_salas: dict[tuple[str, str], dict[str, Any]] = {}
    for registros in fontes.values():
        for registro in registros:
            chave_sala = (registro["predio"], registro["sala"])
            sala = inventario_salas.setdefault(chave_sala, {"capacidades": set(), "tipos": set()})
            sala["capacidades"].add(int(registro["capacidade_sala"]))
            sala["tipos"].add(registro["tipo_sala"])

    eventos: dict[str, dict[str, Any]] = {}
    docentes: dict[str, set[str]] = {}

    for encontro_id, encontro in encontros.items():
        proposta = alocacoes_efetivas[encontro_id]
        registros = fontes[encontro_id]
        primeiro = registros[0]
        try:
            inicio = _minutos(proposta["hora_inicio"])
            fim = _minutos(proposta["hora_fim"])
        except ValueError as erro:
            diagnosticos.append(_diagnostico("H001", "inviolavel", f"Encontro {encontro_id}: {erro}", encontro_id))
            continue
        if fim <= inicio:
            diagnosticos.append(_diagnostico("H001", "inviolavel", f"Encontro {encontro_id}: hora_fim deve ser posterior a hora_inicio.", encontro_id))
            continue
        duracao_original = _minutos(encontro.atributos_fisicos["hora_fim"]) - _minutos(encontro.atributos_fisicos["hora_inicio"])
        if fim - inicio != duracao_original:
            diagnosticos.append(_diagnostico("H001", "inviolavel", f"Encontro {encontro_id}: duração proposta ({fim - inicio} min) difere da original ({duracao_original} min).", encontro_id))

        dia = proposta["dia_semana"].strip().upper()
        if dia not in DIAS_VALIDOS:
            diagnosticos.append(_diagnostico("H002", "inviolavel", f"Encontro {encontro_id}: dia {dia!r} não é segunda a sexta-feira.", encontro_id))
        if _intervalos_sobrepostos(inicio, fim, *ALMOCO):
            diagnosticos.append(_diagnostico("H003", "inviolavel", f"Encontro {encontro_id}: {proposta['hora_inicio']}–{proposta['hora_fim']} sobrepõe o almoço 12:30–13:30.", encontro_id))

        sala_chave = (proposta["predio"], proposta["sala"])
        sala_info = inventario_salas.get(sala_chave)
        if sala_info is None:
            diagnosticos.append(_diagnostico("H008", "inviolavel", f"Encontro {encontro_id}: sala {sala_chave!r} não consta do inventário da fonte.", encontro_id))
            capacidade, tipos_sala = 0, set()
        else:
            capacidade, tipos_sala = min(sala_info["capacidades"]), sala_info["tipos"]

        membros_vagas: dict[str, set[int]] = defaultdict(set)
        for registro in registros:
            membros_vagas[registro["turma"]].add(int(registro["vagas_oferecidas"]))
        if any(len(valores) > 1 for valores in membros_vagas.values()):
            diagnosticos.append(_diagnostico("H008", "inviolavel", f"Encontro {encontro_id}: vagas_oferecidas divergentes para um membro compartilhado.", encontro_id))
        alunos = sum(max(valores) for valores in membros_vagas.values())
        if capacidade <= 0 or alunos > capacidade * 1.20:
            diagnosticos.append(_diagnostico("H008", "inviolavel", f"Encontro {encontro_id}: {alunos} vagas excedem 120% da capacidade {capacidade} da sala.", encontro_id))

        tipo_original = _normalizar(encontro.atributos_fisicos["tipo_sala"])
        dependente_computador = "laborat" in tipo_original
        tipo_destino_laboratorio = any("laborat" in _normalizar(tipo) for tipo in tipos_sala)
        if dependente_computador and not tipo_destino_laboratorio:
            diagnosticos.append(_diagnostico("H009", "inviolavel", f"Encontro {encontro_id}: turma dependente de computador precisa permanecer em laboratório.", encontro_id))

        cursos = {registro["curso"] for registro in registros}
        if not cursos.issubset(CURSOS_ALVO) and proposta != _alocacao_original(encontro):
            diagnosticos.append(_diagnostico("H007", "inviolavel", f"Encontro externo {encontro_id}: curso fora de ARQU/DPRO/DVIS não pode ser alterado.", encontro_id))

        janelas_alvo = [janela for curso in cursos for janela in TURNOS_ALVO.get(curso, ())]
        minutos_alvo = sum(
            max(0, min(fim, limite_fim) - max(inicio, limite_inicio))
            for limite_inicio, limite_fim in _unir_intervalos(janelas_alvo)
        )
        if not cursos.isdisjoint(CURSOS_ALVO) and minutos_alvo < fim - inicio:
            justificativa = excecoes_turno.get(encontro_id, "").strip()
            if justificativa:
                diagnosticos.append(_diagnostico("H010", "excecao", f"Encontro {encontro_id}: relaxamento de turno registrado ({fim - inicio - minutos_alvo} min fora do alvo): {justificativa}", encontro_id))
            else:
                diagnosticos.append(_diagnostico("H010", "inviolavel", f"Encontro {encontro_id}: {fim - inicio - minutos_alvo} min fora do turno-alvo sem justificativa de exceção.", encontro_id))

        eventos[encontro_id] = {
            "semestre": primeiro["semestre"], "dia": dia, "inicio": inicio, "fim": fim,
            "proposta": proposta,
        }
        docentes[encontro_id] = {
            atribuicao.docente for atribuicao in modelo.atribuicoes_docentes
            if atribuicao.evento_fisico_id == encontro_id
        }

    for encontro_a, encontro_b in combinations(sorted(eventos), 2):
        evento_a, evento_b = eventos[encontro_a], eventos[encontro_b]
        if (evento_a["semestre"], evento_a["dia"]) != (evento_b["semestre"], evento_b["dia"]):
            continue
        if not _intervalos_sobrepostos(evento_a["inicio"], evento_a["fim"], evento_b["inicio"], evento_b["fim"]):
            continue
        local_a, local_b = evento_a["proposta"], evento_b["proposta"]
        if (local_a["predio"], local_a["sala"]) == (local_b["predio"], local_b["sala"]):
            diagnosticos.append(_diagnostico("H004", "inviolavel", f"Encontros {encontro_a} e {encontro_b} sobrepõem a mesma sala.", encontro_a, encontro_b))
        comuns_docentes = sorted(docentes.get(encontro_a, set()) & docentes.get(encontro_b, set()))
        if comuns_docentes:
            diagnosticos.append(_diagnostico("H005", "inviolavel", f"Encontros {encontro_a} e {encontro_b} sobrepõem docente(s): {', '.join(comuns_docentes)}.", encontro_a, encontro_b))

    horarios = {
        encontro_id: (evento["dia"], evento["inicio"], evento["fim"])
        for encontro_id, evento in eventos.items()
    }
    for (semestre, curso, etapa), disciplinas in sorted(secoes_por_etapa(modelo).items()):
        if not etapa_cursavel(disciplinas, horarios):
            ids = sorted({i for turmas in disciplinas.values() for secao in turmas.values() for i in secao})
            diagnosticos.append(_diagnostico(
                "H006", "inviolavel",
                f"{curso}/etapa {etapa} ({semestre}): nenhuma escolha de turmas permite cursar todas as disciplinas sem sobreposição.",
                *ids,
            ))

    for encontro_id in set(excecoes_turno).difference(encontros):
        diagnosticos.append(_diagnostico("H010", "inviolavel", f"Exceção de turno referencia encontro inexistente {encontro_id}.", encontro_id))
    if alocacoes_informadas:
        baseline = {
            (item.regra, item.encontros, item.mensagem)
            for item in validar_grade(modelo)
            if item.severidade == "baseline"
        }
        diagnosticos = [
            Diagnostico(item.regra, "baseline", item.mensagem, item.encontros)
            if item.severidade == "inviolavel"
            and (item.regra, item.encontros, item.mensagem) in baseline
            else item
            for item in diagnosticos
        ]
    else:
        diagnosticos = [
            Diagnostico(item.regra, "baseline", item.mensagem, item.encontros)
            if item.severidade == "inviolavel" else item
            for item in diagnosticos
        ]
    return diagnosticos


def classificar_preservacao(
    modelo: ModeloOcupacao,
    alocacoes: Mapping[str, Mapping[str, str]],
) -> dict[str, int]:
    """Classifica cada encontro em 1 (melhor) a 5 (mudança mais ampla)."""

    niveis = {}
    por_padrao: dict[str, list[str]] = defaultdict(list)
    por_id = {encontro.id: encontro for encontro in modelo.encontros_fisicos}
    for encontro in modelo.encontros_fisicos:
        original = _alocacao_original(encontro)
        proposta = {**original, **alocacoes.get(encontro.id, {})}
        mesmo_dia_horario = all(proposta[campo] == original[campo] for campo in ("dia_semana", "hora_inicio", "hora_fim"))
        mesma_sala = all(proposta[campo] == original[campo] for campo in ("predio", "sala"))
        if mesmo_dia_horario and mesma_sala:
            nivel = 1
        elif mesmo_dia_horario:
            nivel = 2
        elif proposta["dia_semana"] == original["dia_semana"]:
            nivel = 3
        else:
            nivel = 4
        niveis[encontro.id] = nivel
        por_padrao[encontro.padrao_semanal_id].append(encontro.id)
    for ids in por_padrao.values():
        originais = sorted(por_id[evento_id].atributos_fisicos["dia_semana"] for evento_id in ids)
        atuais = sorted(alocacoes.get(evento_id, _alocacao_original(por_id[evento_id])).get("dia_semana", "") for evento_id in ids)
        if atuais != originais:
            for evento_id in ids:
                if niveis[evento_id] == 4:
                    niveis[evento_id] = 5
    return niveis


def metricas_preferencia(
    modelo: ModeloOcupacao,
    alocacoes: Mapping[str, Mapping[str, str]],
    limite_inicio_noite: str = "20:00",
) -> dict[str, Any]:
    """Expõe métricas de preferência sem transformá-las em bloqueios."""

    fontes = _linhas_por_encontro(modelo)
    tipos_sala = {}
    for registros in fontes.values():
        for registro in registros:
            tipos_sala[(registro["predio"], registro["sala"])] = registro["tipo_sala"]
    niveis = classificar_preservacao(modelo, alocacoes)
    cargas_docente_dia: dict[tuple[str, str], int] = defaultdict(int)
    intervalos_docente_dia: dict[tuple[str, str], set[tuple[int, int]]] = defaultdict(set)
    cargas_etapa_dia: dict[tuple[str, str, str], int] = defaultdict(int)
    inicios_noite_tardios = 0
    tipos_originais_alterados = 0
    laboratorios_nao_necessarios = 0
    salas_originais_preservadas = 0
    prioridade_por_turma: dict[str, dict[str, Any]] = {}
    for encontro in modelo.encontros_fisicos:
        original = _alocacao_original(encontro)
        proposta = {**original, **alocacoes.get(encontro.id, {})}
        inicio = _minutos(proposta["hora_inicio"])
        fim = _minutos(proposta["hora_fim"])
        if inicio >= 18 * 60 + 30 and inicio >= _minutos(limite_inicio_noite):
            inicios_noite_tardios += 1
        if (proposta["predio"], proposta["sala"]) == (original["predio"], original["sala"]):
            salas_originais_preservadas += 1
        tipo_destino = _normalizar(tipos_sala.get((proposta["predio"], proposta["sala"]), ""))
        tipo_original = _normalizar(encontro.atributos_fisicos["tipo_sala"])
        if tipo_destino and tipo_destino != tipo_original:
            tipos_originais_alterados += 1
        if "laborat" in tipo_destino and "laborat" not in tipo_original:
            laboratorios_nao_necessarios += 1
        periodos = int(encontro.atributos_fisicos["numero_periodos"])
        docentes_evento = {
            atribuicao.docente for atribuicao in modelo.atribuicoes_docentes
            if atribuicao.evento_fisico_id == encontro.id
        }
        for docente in docentes_evento:
            chave_dia = (docente, proposta["dia_semana"])
            cargas_docente_dia[chave_dia] += periodos
            intervalos_docente_dia[chave_dia].add((inicio, fim))
        etapas_evento = {
            (registro["curso"], registro["etapa"])
            for registro in fontes[encontro.id]
            if registro["curso"] in CURSOS_ALVO and registro["etapa"] != "0"
        }
        for curso, etapa in etapas_evento:
            cargas_etapa_dia[(curso, etapa, proposta["dia_semana"])] += periodos
    gaps_docentes = {}
    dispersao_docentes = {}
    docentes = {atribuicao.docente for atribuicao in modelo.atribuicoes_docentes}
    for docente in docentes:
        cargas = [cargas_docente_dia[(docente, dia)] for dia in DIAS_VALIDOS]
        dispersao_docentes[docente] = max(cargas, default=0) - min(cargas, default=0)
        gaps_docentes[docente] = sum(
            max(0, inicio_atual - fim_anterior)
            for dia in DIAS_VALIDOS
            for (_, fim_anterior), (inicio_atual, _) in zip(
                sorted(intervalos_docente_dia[(docente, dia)]),
                sorted(intervalos_docente_dia[(docente, dia)])[1:],
            )
        )
    etapas = {
        (turma.curso, turma.etapa)
        for turma in modelo.turmas_academicas
        if turma.curso in CURSOS_ALVO and turma.etapa != "0"
    }
    dispersao_etapas = {
        f"{curso}/etapa {etapa}": max(
            (cargas_etapa_dia[(curso, etapa, dia)] for dia in DIAS_VALIDOS), default=0
        ) - min((cargas_etapa_dia[(curso, etapa, dia)] for dia in DIAS_VALIDOS), default=0)
        for curso, etapa in etapas
    }
    for linha in modelo.linhas_fonte:
        valores = linha["valores"]
        turma_id = linha["turma_academica_id"]
        info = prioridade_por_turma.setdefault(turma_id, {
            "turma_academica_id": turma_id,
            "curso": valores["curso"],
            "codigo_disciplina": valores["codigo_disciplina"],
            "turma": valores["turma"],
            "etapa": valores["etapa"],
            "vagas_por_encontro": {},
            "periodos_por_encontro": {},
        })
        evento_id = linha["evento_fisico_id"]
        info["vagas_por_encontro"][evento_id] = max(
            info["vagas_por_encontro"].get(evento_id, 0), int(valores["vagas_oferecidas"])
        )
        info["periodos_por_encontro"][evento_id] = int(valores["numero_periodos"])
    prioridade = sorted(
        ({
            "turma_academica_id": info["turma_academica_id"],
            "curso": info["curso"],
            "codigo_disciplina": info["codigo_disciplina"],
            "turma": info["turma"],
            "alunos": max(info["vagas_por_encontro"].values(), default=0),
            "obrigatoria": info["etapa"] != "0",
            "encontros_semanais": len(info["periodos_por_encontro"]),
            "ch_periodos_semanais": sum(info["periodos_por_encontro"].values()),
        } for info in prioridade_por_turma.values()),
        key=lambda info: (
            -info["alunos"], not info["obrigatoria"], -info["encontros_semanais"],
            -info["ch_periodos_semanais"], info["turma_academica_id"],
        ),
    )
    return {
        "preservacao_por_encontro": niveis,
        "contagem_niveis_preservacao": {nivel: sum(valor == nivel for valor in niveis.values()) for nivel in range(1, 6)},
        "salas_originais_preservadas": salas_originais_preservadas,
        "tipos_espaco_alterados": tipos_originais_alterados,
        "laboratorios_sem_dependencia": laboratorios_nao_necessarios,
        "inicios_noturnos_tardios": inicios_noite_tardios,
        "limite_inicio_noite": limite_inicio_noite,
        "intervalos_livres_docente_minutos": gaps_docentes,
        "dispersao_carga_docente_periodos": dispersao_docentes,
        "dispersao_carga_etapa_periodos": dispersao_etapas,
        "prioridade_turmas": PRIORIDADE_TURMAS,
        "ordem_prioridade_turmas": prioridade,
    }


def diagnosticos_bloqueantes(diagnosticos: list[Diagnostico]) -> list[Diagnostico]:
    """Retorna violações invioláveis; exceções documentadas não bloqueiam."""

    return [item for item in diagnosticos if item.severidade == "inviolavel"]
