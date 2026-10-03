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
from restricoes_03 import CURSOS_ALVO, DIAS_VALIDOS


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

    for selecoes in grupos_recursos.values():
        if len(selecoes) > 1:
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