"""Modelo CP-SAT de viabilidade para os domínios da fase 5."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import gcd
from typing import Any

from ortools.sat.python import cp_model

from candidatos_03 import (
    ALMOCO,
    Candidato,
    _cursos_do_encontro,
    _intervalos_sobrepostos,
    _linhas_por_encontro,
    _minutos,
    alocacoes_fixos,
)
from modelo_ocupacao_03 import ModeloOcupacao
from restricoes_03 import CURSOS_ALVO, DIAS_VALIDOS, metricas_preferencia


@dataclass(frozen=True)
class ModeloCPsat:
    modelo: cp_model.CpModel
    variaveis: dict[str, tuple[tuple[Candidato, Any], ...]]
    intervalo_minutos: int
    quantidade_restricoes: int


def _recursos_etapa(registros: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (registro["curso"], registro["etapa"])
        for registro in registros
        if registro["curso"] in CURSOS_ALVO and registro["etapa"] != "0"
    }


def _validar_dominios(
    ocupacao: ModeloOcupacao,
    dominios: dict[str, tuple[Candidato, ...]],
) -> None:
    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}
    fixos = set(alocacoes_fixos(ocupacao))
    esperados = set(encontros).difference(fixos)
    if set(dominios) != esperados:
        raise ValueError(
            "Os domínios devem conter exatamente os encontros móveis: "
            f"esperados={len(esperados)}, recebidos={len(dominios)}."
        )
    if any(not candidatos for candidatos in dominios.values()):
        vazios = sorted(encontro_id for encontro_id, valores in dominios.items() if not valores)
        raise ValueError(f"Encontros móveis sem candidatos: {vazios}.")

    linhas = _linhas_por_encontro(ocupacao)
    salas: dict[tuple[str, str], tuple[int, set[str]]] = {}
    for registros in linhas.values():
        registro = registros[0]
        chave = (registro["predio"], registro["sala"])
        capacidade, tipos = salas.setdefault(chave, (int(registro["capacidade_sala"]), set()))
        if capacidade != int(registro["capacidade_sala"]):
            raise ValueError(f"Capacidade inconsistente para a sala {chave!r}.")
        tipos.add(registro["tipo_sala"])

    bloqueios_fixos = []
    docentes_por_encontro: dict[str, set[str]] = defaultdict(set)
    for atribuicao in ocupacao.atribuicoes_docentes:
        docentes_por_encontro[atribuicao.evento_fisico_id].add(atribuicao.docente)
    for encontro_id, alocacao in alocacoes_fixos(ocupacao).items():
        encontro = encontros[encontro_id]
        atributos = encontro.atributos_fisicos
        registros = linhas[encontro_id]
        bloqueios_fixos.append({
            "semestre": atributos["semestre"],
            "dia": alocacao["dia_semana"].strip().upper(),
            "inicio": _minutos(alocacao["hora_inicio"]),
            "fim": _minutos(alocacao["hora_fim"]),
            "predio": alocacao["predio"],
            "sala": alocacao["sala"],
            "docentes": docentes_por_encontro[encontro_id],
            "etapas": _recursos_etapa(registros),
        })

    for encontro_id, candidatos in dominios.items():
        encontro = encontros[encontro_id]
        atributos = encontro.atributos_fisicos
        duracao = _minutos(atributos["hora_fim"]) - _minutos(atributos["hora_inicio"])
        registros = linhas[encontro_id]
        vagas_membro: dict[str, set[int]] = defaultdict(set)
        for registro in registros:
            vagas_membro[registro["turma"]].add(int(registro["vagas_oferecidas"]))
        if any(len(valores) != 1 for valores in vagas_membro.values()):
            raise ValueError(f"Vagas divergentes para membros do encontro {encontro_id}.")
        vagas = sum(next(iter(valores)) for valores in vagas_membro.values())
        dependente_computador = "laborat" in atributos["tipo_sala"].casefold()
        cursos = _cursos_do_encontro(registros)

        for candidato in candidatos:
            inicio = _minutos(candidato.hora_inicio)
            fim = _minutos(candidato.hora_fim)
            sala = salas.get((candidato.predio, candidato.sala))
            if candidato.encontro_id != encontro_id:
                raise ValueError(f"Candidato associado ao encontro incorreto: {candidato!r}.")
            if candidato.dia_semana not in DIAS_VALIDOS or fim - inicio != duracao:
                raise ValueError(f"Dia ou duração inválidos no candidato {candidato!r}.")
            if _intervalos_sobrepostos(inicio, fim, *ALMOCO):
                raise ValueError(f"Candidato sobrepõe o almoço: {candidato!r}.")
            if sala is None or vagas > sala[0] * 1.10:
                raise ValueError(f"Sala inexistente ou capacidade excedida: {candidato!r}.")
            if dependente_computador and not any("laborat" in tipo.casefold() for tipo in sala[1]):
                raise ValueError(f"Candidato de turma dependente não é laboratório: {candidato!r}.")
            if candidato.minutos_fora_turno_alvo < 0 or candidato.minutos_fora_turno_alvo > duracao:
                raise ValueError(f"Minutos fora do turno-alvo inválidos: {candidato!r}.")
            docentes = docentes_por_encontro[encontro_id]
            etapas = _recursos_etapa(registros)
            for fixo in bloqueios_fixos:
                if fixo["semestre"] != atributos["semestre"] or fixo["dia"] != candidato.dia_semana:
                    continue
                if not _intervalos_sobrepostos(inicio, fim, fixo["inicio"], fixo["fim"]):
                    continue
                mesma_sala = (candidato.predio, candidato.sala) == (fixo["predio"], fixo["sala"])
                conflito_docente = bool(docentes & fixo["docentes"])
                conflito_etapa = bool(etapas & fixo["etapas"])
                if mesma_sala or conflito_docente or conflito_etapa:
                    raise ValueError(f"Candidato colide com encontro fixo: {candidato!r}.")


def construir_modelo_cp_sat(
    ocupacao: ModeloOcupacao,
    dominios: dict[str, tuple[Candidato, ...]],
) -> ModeloCPsat:
    """Cria um problema de viabilidade; objetivos são adicionados nas fases A/B/C."""

    return _construir_modelo_cp_sat(ocupacao, dominios, frozenset())


def construir_modelo_cp_sat_diagnostico(
    ocupacao: ModeloOcupacao,
    dominios: dict[str, tuple[Candidato, ...]],
    recurso_ignorado: str,
) -> ModeloCPsat:
    """Cria modelo diagnóstico sem uma categoria de conflito entre móveis.

    Uso restrito à investigação de inviabilidade; nunca use este modelo para
    exportar ou validar uma grade candidata.
    """

    recursos_validos = {"sala", "docente", "etapa"}
    if recurso_ignorado not in recursos_validos:
        raise ValueError(f"Recurso diagnóstico inválido: {recurso_ignorado!r}.")
    return _construir_modelo_cp_sat(ocupacao, dominios, frozenset({recurso_ignorado}))


def _construir_modelo_cp_sat(
    ocupacao: ModeloOcupacao,
    dominios: dict[str, tuple[Candidato, ...]],
    recursos_ignorados: frozenset[str],
) -> ModeloCPsat:
    """Implementação comum do modelo, opcionalmente relaxada para diagnóstico."""

    _validar_dominios(ocupacao, dominios)
    linhas = _linhas_por_encontro(ocupacao)
    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}

    marcas_tempo = []
    for candidatos in dominios.values():
        for candidato in candidatos:
            marcas_tempo.extend((_minutos(candidato.hora_inicio), _minutos(candidato.hora_fim)))
    for alocacao in alocacoes_fixos(ocupacao).values():
        marcas_tempo.extend((_minutos(alocacao["hora_inicio"]), _minutos(alocacao["hora_fim"])))
    intervalo_minutos = 0
    for marca in marcas_tempo:
        intervalo_minutos = gcd(intervalo_minutos, marca)
    intervalo_minutos = max(intervalo_minutos, 1)

    modelo = cp_model.CpModel()
    variaveis: dict[str, tuple[tuple[Candidato, Any], ...]] = {}
    grupos_recursos: dict[tuple[Any, ...], list[Any]] = defaultdict(list)

    for encontro_id, candidatos in sorted(dominios.items()):
        escolhas = []
        encontro = encontros[encontro_id]
        atributos = encontro.atributos_fisicos
        docentes = {
            atribuicao.docente
            for atribuicao in ocupacao.atribuicoes_docentes
            if atribuicao.evento_fisico_id == encontro_id
        }
        etapas = _recursos_etapa(linhas[encontro_id])
        semestre = atributos["semestre"]

        for indice, candidato in enumerate(candidatos):
            variavel = modelo.new_bool_var(f"x_{encontro_id}_{indice}")
            escolhas.append((candidato, variavel))
            inicio = _minutos(candidato.hora_inicio) // intervalo_minutos
            fim = _minutos(candidato.hora_fim) // intervalo_minutos
            for periodo in range(inicio, fim):
                grupos_recursos[("sala", semestre, candidato.dia_semana, candidato.predio, candidato.sala, periodo)].append(variavel)
                for docente in docentes:
                    grupos_recursos[("docente", semestre, candidato.dia_semana, docente, periodo)].append(variavel)
                for curso, etapa in etapas:
                    grupos_recursos[("etapa", semestre, candidato.dia_semana, curso, etapa, periodo)].append(variavel)
        modelo.add_exactly_one([variavel for _, variavel in escolhas])
        variaveis[encontro_id] = tuple(escolhas)

    for chave_recurso, selecoes in grupos_recursos.items():
        if chave_recurso[0] not in recursos_ignorados and len(selecoes) > 1:
            modelo.add_at_most_one(selecoes)

    validacao = modelo.validate()
    if validacao:
        raise ValueError(f"Modelo CP-SAT inválido: {validacao}")
    return ModeloCPsat(
        modelo=modelo,
        variaveis=variaveis,
        intervalo_minutos=intervalo_minutos,
        quantidade_restricoes=len(modelo.proto.constraints),
    )


def resolver_viabilidade(modelagem: ModeloCPsat, limite_segundos: float = 30.0) -> tuple[int, dict[str, Candidato]]:
    """Resolve apenas viabilidade e devolve o status CP-SAT e uma alocação."""

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limite_segundos
    solver.parameters.num_search_workers = 1
    status = solver.solve(modelagem.modelo)
    solucao = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for encontro_id, escolhas in modelagem.variaveis.items():
            selecionado = next(
                candidato for candidato, variavel in escolhas if solver.boolean_value(variavel)
            )
            solucao[encontro_id] = selecionado
    return status, solucao


def adicionar_objetivo_solucao_a(
    ocupacao: ModeloOcupacao,
    modelagem: ModeloCPsat,
) -> None:
    """Adiciona o objetivo lexicográfico de preservação ao modelo CP-SAT."""

    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}
    linhas = _linhas_por_encontro(ocupacao)
    quantidade = len(modelagem.variaveis)
    base = quantidade + 1
    pesos_nivel = {nivel: base ** (5 - nivel) for nivel in range(1, 6)}

    prioridades = metricas_preferencia(ocupacao, {})["ordem_prioridade_turmas"]
    ranking_turmas = {
        item["turma_academica_id"]: len(prioridades) - indice
        for indice, item in enumerate(prioridades)
    }
    prioridade_evento = {
        encontro_id: sum({
            ranking_turmas.get(linha["turma_academica_id"], 0)
            for linha in ocupacao.linhas_fonte
            if linha["evento_fisico_id"] == encontro_id
        })
        for encontro_id in modelagem.variaveis
    }

    tipos_sala: dict[tuple[str, str], set[str]] = defaultdict(set)
    for registros in linhas.values():
        for registro in registros:
            tipos_sala[(registro["predio"], registro["sala"])].add(registro["tipo_sala"])

    padroes: dict[str, list[str]] = defaultdict(list)
    for encontro in ocupacao.encontros_fisicos:
        padroes[encontro.padrao_semanal_id].append(encontro.id)
    padrao_preservado: dict[str, Any] = {}
    for padrao_id, encontro_ids in padroes.items():
        moveis = [encontro_id for encontro_id in encontro_ids if encontro_id in modelagem.variaveis]
        if not moveis:
            continue
        esperado: dict[str, int] = defaultdict(int)
        for encontro_id in encontro_ids:
            dia = encontros[encontro_id].atributos_fisicos["dia_semana"].strip().upper()
            esperado[dia] += 1

        iguais_por_dia = []
        for dia in sorted(DIAS_VALIDOS):
            fixos_no_dia = sum(
                1 for encontro_id in encontro_ids
                if encontro_id not in modelagem.variaveis
                and encontros[encontro_id].atributos_fisicos["dia_semana"].strip().upper() == dia
            )
            escolhas_no_dia = [
                variavel
                for encontro_id in moveis
                for candidato, variavel in modelagem.variaveis[encontro_id]
                if candidato.dia_semana == dia
            ]
            igual = modelagem.modelo.new_bool_var(f"padrao_dia_{padrao_id}_{dia}")
            contagem = fixos_no_dia + sum(escolhas_no_dia)
            modelo_igual = esperado[dia]
            modelagem.modelo.add(contagem == modelo_igual).only_enforce_if(igual)
            modelagem.modelo.add(contagem != modelo_igual).only_enforce_if(igual.Not())
            iguais_por_dia.append(igual)

        preservado = modelagem.modelo.new_bool_var(f"padrao_preservado_{padrao_id}")
        modelagem.modelo.add_bool_and(iguais_por_dia).only_enforce_if(preservado)
        modelagem.modelo.add_bool_or([igual.Not() for igual in iguais_por_dia]).only_enforce_if(preservado.Not())
        padrao_preservado[padrao_id] = preservado

    niveis_primarios = {nivel: [] for nivel in range(1, 6)}
    desempates = []
    soma_pesos_prioridade = 0
    for encontro_id, escolhas in modelagem.variaveis.items():
        original = encontros[encontro_id].atributos_fisicos
        original_dia = original["dia_semana"].strip().upper()
        dia_alterado = modelagem.modelo.new_bool_var(f"dia_alterado_{encontro_id}")
        for candidato, variavel in escolhas:
            candidato_dia = candidato.dia_semana.strip().upper()
            mesma_data_hora = all(
                candidato.alocacao()[campo] == original[campo]
                for campo in ("dia_semana", "hora_inicio", "hora_fim")
            )
            mesma_sala = (candidato.predio, candidato.sala) == (original["predio"], original["sala"])
            mesma_posicao = mesma_data_hora and mesma_sala
            if mesma_posicao:
                niveis_primarios[1].append(variavel)
            elif mesma_data_hora:
                niveis_primarios[2].append(variavel)
            elif candidato_dia == original_dia:
                niveis_primarios[3].append(variavel)
            if mesma_posicao:
                desempates.append(prioridade_evento[encontro_id] * variavel)

            sala_original = (original["predio"], original["sala"])
            tipo_original = {tipo.casefold() for tipo in tipos_sala[sala_original]}
            tipos_destino = tipos_sala[(candidato.predio, candidato.sala)]
            tipo_preservado = bool(tipo_original & {tipo.casefold() for tipo in tipos_destino})
            laboratorio_desnecessario = (
                "laborat" in " ".join(tipos_destino).casefold()
                and "laborat" not in " ".join(tipo_original).casefold()
            )
            inicio_tardio = _minutos(candidato.hora_inicio) >= 20 * 60
            desempates.extend((
                int(mesma_sala) * variavel,
                int(tipo_preservado) * variavel,
                -int(laboratorio_desnecessario) * variavel,
                -int(inicio_tardio) * variavel,
            ))

        soma_pesos_prioridade += prioridade_evento[encontro_id]
        soma_dias_alterados = sum(
            variavel for candidato, variavel in escolhas
            if candidato.dia_semana.strip().upper() != original_dia
        )
        modelagem.modelo.add(soma_dias_alterados == 1).only_enforce_if(dia_alterado)
        modelagem.modelo.add(soma_dias_alterados == 0).only_enforce_if(dia_alterado.Not())
        nivel_quatro = modelagem.modelo.new_bool_var(f"nivel_4_{encontro_id}")
        preservado = padrao_preservado[encontros[encontro_id].padrao_semanal_id]
        modelagem.modelo.add_bool_and([dia_alterado, preservado]).only_enforce_if(nivel_quatro)
        modelagem.modelo.add_bool_or([dia_alterado.Not(), preservado.Not()]).only_enforce_if(nivel_quatro.Not())
        niveis_primarios[4].append(nivel_quatro)
        niveis_primarios[5].append(dia_alterado - nivel_quatro)

    limite_desempate = soma_pesos_prioridade + 5 * quantidade
    escala_primaria = 2 * limite_desempate + 1
    termos_objetivo = [
        variavel * pesos_nivel[nivel] * escala_primaria
        for nivel, variaveis in niveis_primarios.items()
        for variavel in variaveis
    ]
    termos_objetivo.extend(desempates)
    modelagem.modelo.maximize(sum(termos_objetivo))
    validacao = modelagem.modelo.validate()
    if validacao:
        raise ValueError(f"Modelo CP-SAT inválido para a Solução A: {validacao}")


def resolver_solucao_a(
    ocupacao: ModeloOcupacao,
    modelagem: ModeloCPsat,
    limite_segundos: float = 300.0,
) -> tuple[int, dict[str, Candidato], dict[str, Any]]:
    """Maximiza lexicograficamente a preservação da grade para a Solução A."""

    adicionar_objetivo_solucao_a(ocupacao, modelagem)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limite_segundos
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status = solver.solve(modelagem.modelo)
    solucao = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for encontro_id, escolhas in modelagem.variaveis.items():
            solucao[encontro_id] = next(
                candidato for candidato, variavel in escolhas
                if solver.boolean_value(variavel)
            )
    detalhes = {
        "status": solver.status_name(status),
        "valor_objetivo": solver.objective_value if solucao else None,
        "melhor_limite": solver.best_objective_bound if solucao else None,
        "tempo_segundos": solver.wall_time,
        "limite_segundos": limite_segundos,
        "quantidade_variaveis": len(modelagem.modelo.proto.variables),
        "quantidade_restricoes": len(modelagem.modelo.proto.constraints),
    }
    return status, solucao, detalhes