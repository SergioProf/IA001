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
from restricoes_03 import (
    CURSOS_ALVO,
    DIAS_VALIDOS,
    etapa_cursavel,
    metricas_preferencia,
    secoes_por_etapa,
    validar_grade,
)

# Janela do turno que NÃO é alvo de cada curso (mesma definição da página Agenda, item 6).
JANELA_FORA_ALVO = {"ARQU": (810, 1110), "DPRO": (0, 750), "DVIS": (0, 750)}
ESCALA_PERCENTUAL = 10_000_000


@dataclass(frozen=True)
class ModeloCPsat:
    modelo: cp_model.CpModel
    variaveis: dict[str, tuple[tuple[Candidato, Any], ...]]
    escolhas_etapa: dict[tuple[str, str, str], dict[tuple[str, str], Any]]
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
    fixados: frozenset[str] = frozenset(),
) -> None:
    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}
    fixos = set(alocacoes_fixos(ocupacao, fixados))
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
    for encontro_id, alocacao in alocacoes_fixos(ocupacao, fixados).items():
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
            if sala is None or vagas > sala[0] * 1.20:
                raise ValueError(f"Sala inexistente ou capacidade excedida: {candidato!r}.")
            if dependente_computador and not any("laborat" in tipo.casefold() for tipo in sala[1]):
                raise ValueError(f"Candidato de turma dependente não é laboratório: {candidato!r}.")
            if candidato.minutos_fora_turno_alvo < 0 or candidato.minutos_fora_turno_alvo > duracao:
                raise ValueError(f"Minutos fora do turno-alvo inválidos: {candidato!r}.")
            docentes = docentes_por_encontro[encontro_id]
            for fixo in bloqueios_fixos:
                if fixo["semestre"] != atributos["semestre"] or fixo["dia"] != candidato.dia_semana:
                    continue
                if not _intervalos_sobrepostos(inicio, fim, fixo["inicio"], fixo["fim"]):
                    continue
                mesma_sala = (candidato.predio, candidato.sala) == (fixo["predio"], fixo["sala"])
                conflito_docente = bool(docentes & fixo["docentes"])
                if mesma_sala or conflito_docente:
                    raise ValueError(f"Candidato colide com encontro fixo: {candidato!r}.")


def _adicionar_restricoes_etapa(
    modelo: cp_model.CpModel,
    ocupacao: ModeloOcupacao,
    variaveis: dict[str, tuple[tuple[Candidato, Any], ...]],
    intervalo_minutos: int,
    fixados: frozenset[str],
    etapas_toleradas: frozenset[tuple[str, str, str]],
) -> dict[tuple[str, str, str], dict[tuple[str, str], Any]]:
    """H006: em cada etapa/curso, uma turma por disciplina precisa caber sem sobreposição."""

    # Para cada encontro: (dia, período) -> literais que o ocupam (True = encontro fixo).
    ocupa: dict[str, dict[tuple[str, int], list[Any]]] = defaultdict(lambda: defaultdict(list))
    for encontro_id, alocacao in alocacoes_fixos(ocupacao, fixados).items():
        dia = alocacao["dia_semana"].strip().upper()
        inicio = _minutos(alocacao["hora_inicio"]) // intervalo_minutos
        fim = _minutos(alocacao["hora_fim"]) // intervalo_minutos
        for periodo in range(inicio, fim):
            ocupa[encontro_id][(dia, periodo)].append(True)
    for encontro_id, escolhas in variaveis.items():
        for candidato, variavel in escolhas:
            inicio = _minutos(candidato.hora_inicio) // intervalo_minutos
            fim = _minutos(candidato.hora_fim) // intervalo_minutos
            for periodo in range(inicio, fim):
                ocupa[encontro_id][(candidato.dia_semana, periodo)].append(variavel)

    escolhas_etapa = {}
    for chave, disciplinas in secoes_por_etapa(ocupacao).items():
        if chave in etapas_toleradas:
            continue
        escolhida: dict[tuple[str, str], Any] = {}
        for codigo, turmas in disciplinas.items():
            for turma in turmas:
                escolhida[(codigo, turma)] = modelo.new_bool_var(f"turma_{chave}_{codigo}_{turma}")
            modelo.add_exactly_one([escolhida[(codigo, turma)] for turma in turmas])

        por_periodo: dict[tuple[str, int], dict[tuple[str, str], list[Any]]] = defaultdict(lambda: defaultdict(list))
        for codigo, turmas in disciplinas.items():
            for turma, encontros_turma in turmas.items():
                for encontro_id in encontros_turma:
                    for ponto, literais in ocupa.get(encontro_id, {}).items():
                        por_periodo[ponto][(codigo, turma)].extend(literais)

        for ponto, secoes in por_periodo.items():
            if len({codigo for codigo, _ in secoes}) < 2:
                continue
            presentes = []
            for secao, literais in secoes.items():
                selecionada = escolhida[secao]
                if any(literal is True for literal in literais):
                    presentes.append(selecionada)
                    continue
                if len(literais) == 1:
                    ocupado = literais[0]
                else:
                    ocupado = modelo.new_bool_var(f"ocupa_{chave}_{secao}_{ponto}")
                    for literal in literais:
                        modelo.add_implication(literal, ocupado)
                presente = modelo.new_bool_var(f"presente_{chave}_{secao}_{ponto}")
                modelo.add_bool_or([selecionada.Not(), ocupado.Not(), presente])
                presentes.append(presente)
            modelo.add_at_most_one(presentes)

        escolhas_etapa[chave] = escolhida
    return escolhas_etapa


def construir_modelo_cp_sat(
    ocupacao: ModeloOcupacao,
    dominios: dict[str, tuple[Candidato, ...]],
    fixados: frozenset[str] = frozenset(),
    etapas_toleradas: frozenset[tuple[str, str, str]] = frozenset(),
) -> ModeloCPsat:
    """Cria um problema de viabilidade; objetivos são adicionados nas fases A/B/C."""

    return _construir_modelo_cp_sat(ocupacao, dominios, frozenset(), fixados, etapas_toleradas)


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
    fixados: frozenset[str] = frozenset(),
    etapas_toleradas: frozenset[tuple[str, str, str]] = frozenset(),
) -> ModeloCPsat:
    """Implementação comum do modelo, opcionalmente relaxada para diagnóstico."""

    _validar_dominios(ocupacao, dominios, fixados)
    linhas = _linhas_por_encontro(ocupacao)
    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}

    marcas_tempo = []
    for candidatos in dominios.values():
        for candidato in candidatos:
            marcas_tempo.extend((_minutos(candidato.hora_inicio), _minutos(candidato.hora_fim)))
    for alocacao in alocacoes_fixos(ocupacao, fixados).values():
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
        modelo.add_exactly_one([variavel for _, variavel in escolhas])
        variaveis[encontro_id] = tuple(escolhas)

    for chave_recurso, selecoes in grupos_recursos.items():
        if chave_recurso[0] not in recursos_ignorados and len(selecoes) > 1:
            modelo.add_at_most_one(selecoes)

    escolhas_etapa = {}
    if "etapa" not in recursos_ignorados:
        escolhas_etapa = _adicionar_restricoes_etapa(
            modelo, ocupacao, variaveis, intervalo_minutos, fixados, etapas_toleradas
        )

    validacao = modelo.validate()
    if validacao:
        raise ValueError(f"Modelo CP-SAT inválido: {validacao}")
    return ModeloCPsat(
        modelo=modelo,
        variaveis=variaveis,
        escolhas_etapa=escolhas_etapa,
        intervalo_minutos=intervalo_minutos,
        quantidade_restricoes=len(modelo.proto.constraints),
    )


def adicionar_objetivo_solucao_b(
    ocupacao: ModeloOcupacao,
    modelagem: ModeloCPsat,
    fixados: frozenset[str] = frozenset(),
) -> None:
    """Minimiza a dispersão diária de etapas e docentes; preserva em caso de empate."""

    modelo = modelagem.modelo
    dias = sorted(DIAS_VALIDOS)
    fixos = alocacoes_fixos(ocupacao, fixados)
    linhas_por_encontro = _linhas_por_encontro(ocupacao)
    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}
    escolhas_por_etapa = secoes_por_etapa(ocupacao)
    cargas_etapas: list[list[Any]] = []
    limites_etapas: list[int] = []
    cargas_docentes: dict[str, list[list[Any]]] = {}
    limites_docentes: dict[str, int] = defaultdict(int)
    ativos_dia: dict[tuple[str, str], Any] = {}

    def ativo_no_dia(encontro_id: str, dia: str) -> Any | None:
        chave = (encontro_id, dia)
        if chave in ativos_dia:
            return ativos_dia[chave]
        escolhas = modelagem.variaveis.get(encontro_id, ())
        variaveis_dia = [variavel for candidato, variavel in escolhas if candidato.dia_semana == dia]
        if not variaveis_dia:
            ativos_dia[chave] = None
            return None
        ativo = modelo.new_bool_var(f"ativo_{encontro_id}_{dia}")
        modelo.add(ativo == sum(variaveis_dia))
        ativos_dia[chave] = ativo
        return ativo

    for chave, disciplinas in escolhas_por_etapa.items():
        if chave not in modelagem.escolhas_etapa:
            continue
        escolhas = modelagem.escolhas_etapa[chave]
        cargas = [[] for _ in dias]
        ids_etapa: set[str] = set()
        for codigo, turmas in disciplinas.items():
            for turma, ids_encontros in turmas.items():
                selecionada = escolhas[(codigo, turma)]
                for encontro_id in ids_encontros:
                    ids_etapa.add(encontro_id)
                    duracao = (
                        _minutos(encontros[encontro_id].atributos_fisicos["hora_fim"])
                        - _minutos(encontros[encontro_id].atributos_fisicos["hora_inicio"])
                    ) // modelagem.intervalo_minutos
                    if encontro_id in fixos:
                        dia_original = fixos[encontro_id]["dia_semana"].strip().upper()
                        if dia_original in dias:
                            cargas[dias.index(dia_original)].append(duracao * selecionada)
                        continue
                    for indice, dia in enumerate(dias):
                        ativo = ativo_no_dia(encontro_id, dia)
                        if ativo is None:
                            continue
                        conjunto = modelo.new_bool_var(f"etapa_{chave}_{codigo}_{turma}_{encontro_id}_{dia}")
                        modelo.add_bool_and([selecionada, ativo]).only_enforce_if(conjunto)
                        modelo.add_bool_or([selecionada.Not(), ativo.Not(), conjunto])
                        cargas[indice].append(duracao * conjunto)
        cargas_etapas.append(cargas)
        limites_etapas.append(sum(
            (
                _minutos(encontros[encontro_id].atributos_fisicos["hora_fim"])
                - _minutos(encontros[encontro_id].atributos_fisicos["hora_inicio"])
            ) // modelagem.intervalo_minutos
            for encontro_id in ids_etapa
        ))

    docentes_por_encontro: dict[str, set[str]] = defaultdict(set)
    for atribuicao in ocupacao.atribuicoes_docentes:
        docentes_por_encontro[atribuicao.evento_fisico_id].add(atribuicao.docente)
    for encontro_id, encontro in encontros.items():
        duracao = (
            _minutos(encontro.atributos_fisicos["hora_fim"])
            - _minutos(encontro.atributos_fisicos["hora_inicio"])
        ) // modelagem.intervalo_minutos
        for docente in docentes_por_encontro[encontro_id]:
            cargas_docentes.setdefault(docente, [[] for _ in dias])
            limites_docentes[docente] += duracao
            if encontro_id in fixos:
                dia_original = fixos[encontro_id]["dia_semana"].strip().upper()
                if dia_original in dias:
                    cargas_docentes[docente][dias.index(dia_original)].append(duracao)
                continue
            for indice, dia in enumerate(dias):
                escolhas_dia = [
                    variavel for candidato, variavel in modelagem.variaveis[encontro_id]
                    if candidato.dia_semana == dia
                ]
                if escolhas_dia:
                    cargas_docentes[docente][indice].append(duracao * sum(escolhas_dia))

    def termos_dispersao(cargas: list[list[Any]], limites: list[int]) -> list[Any]:
        termos = []
        for indice_grupo, (carga_dias, limite) in enumerate(zip(cargas, limites)):
            total = sum(sum(carga) for carga in carga_dias)
            if limite <= 0:
                continue
            for indice_dia, carga in enumerate(carga_dias):
                desvio = modelo.new_int_var(0, 5 * limite, f"desvio_{indice_grupo}_{indice_dia}")
                modelo.add_abs_equality(desvio, 5 * sum(carga) - total)
                termos.append(desvio)
        return termos

    dispersao_etapas = termos_dispersao(cargas_etapas, limites_etapas)
    cargas_docentes_lista = list(cargas_docentes.values())
    dispersao_docentes = termos_dispersao(
        cargas_docentes_lista,
        [limites_docentes[docente] for docente in cargas_docentes],
    )
    quantidade_etapas = len(cargas_etapas)
    quantidade_docentes = len(cargas_docentes_lista)
    equilibrio = (
        sum(dispersao_etapas) * max(quantidade_docentes, 1)
        + sum(dispersao_docentes) * max(quantidade_etapas, 1)
    )

    preservados = []
    for encontro_id, escolhas in modelagem.variaveis.items():
        original = encontros[encontro_id].atributos_fisicos
        preservados.extend(
            variavel for candidato, variavel in escolhas
            if all(candidato.alocacao()[campo] == original[campo]
                   for campo in ("predio", "sala", "dia_semana", "hora_inicio", "hora_fim"))
        )
    modelagem.modelo.minimize(equilibrio * (len(modelagem.variaveis) + 1) - sum(preservados))
    validacao = modelagem.modelo.validate()
    if validacao:
        raise ValueError(f"Modelo CP-SAT inválido para a Solução B: {validacao}")


def resolver_solucao_b(
    ocupacao: ModeloOcupacao,
    modelagem: ModeloCPsat,
    fixados: frozenset[str] = frozenset(),
    limite_segundos: float = 300.0,
) -> tuple[int, dict[str, Candidato], dict[tuple[str, str, str], tuple[str, ...]], dict[str, Any]]:
    """Resolve B e retorna alocações, turmas de etapa escolhidas e metadados do solver."""

    adicionar_objetivo_solucao_b(ocupacao, modelagem, fixados)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limite_segundos
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 0
    status = solver.solve(modelagem.modelo)
    alocacoes = {}
    etapas_escolhidas = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for encontro_id, escolhas in modelagem.variaveis.items():
            alocacoes[encontro_id] = next(
                candidato for candidato, variavel in escolhas if solver.boolean_value(variavel)
            )
        for chave, escolhas in modelagem.escolhas_etapa.items():
            etapas_escolhidas[chave] = tuple(sorted(
                f"{codigo}:{turma}" for (codigo, turma), variavel in escolhas.items()
                if solver.boolean_value(variavel)
            ))
    detalhes = {
        "status": solver.status_name(status),
        "valor_objetivo": solver.objective_value if alocacoes else None,
        "melhor_limite": solver.best_objective_bound if alocacoes else None,
        "tempo_segundos": solver.wall_time,
        "limite_segundos": limite_segundos,
        "quantidade_variaveis": len(modelagem.modelo.proto.variables),
        "quantidade_restricoes": len(modelagem.modelo.proto.constraints),
        "objetivo": "desvio absoluto diário médio de etapas obrigatórias e docentes; alterações minimizadas em empate",
    }
    return status, alocacoes, etapas_escolhidas, detalhes


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


def _fora_do_alvo(curso: str, inicio: int, fim: int) -> int:
    janela_inicio, janela_fim = JANELA_FORA_ALVO[curso]
    return max(0, min(fim, janela_fim) - max(inicio, janela_inicio))


def fixados_baseline(
    ocupacao: ModeloOcupacao, fixar_todos: bool
) -> tuple[frozenset[str], frozenset[tuple[str, str, str]]]:
    """Encontros fixos na posição atual por já violarem regras invioláveis, e etapas H006 toleradas.

    H003/H008 fixam o encontro; etapas/curso sem combinação de turmas válida hoje
    ficam toleradas e todos os seus encontros fixos; para conflitos H004/H005 fixa-se
    uma cobertura gulosa dos pares (ou ambos os lados, se `fixar_todos`).
    H010 não fixa: é o que o fallback tenta reduzir.
    """

    externos = set(alocacoes_fixos(ocupacao))
    fixados: set[str] = set()
    arestas: set[tuple[str, ...]] = set()
    for item in validar_grade(ocupacao):
        if item.severidade != "baseline" or item.regra in ("H010", "H006"):
            continue
        if item.regra in ("H004", "H005") and len(item.encontros) == 2:
            arestas.add(tuple(sorted(item.encontros)))
        else:
            fixados.update(item.encontros)
    horarios = {
        encontro.id: (
            encontro.atributos_fisicos["dia_semana"].strip().upper(),
            _minutos(encontro.atributos_fisicos["hora_inicio"]),
            _minutos(encontro.atributos_fisicos["hora_fim"]),
        )
        for encontro in ocupacao.encontros_fisicos
    }
    toleradas = set()
    for chave, disciplinas in secoes_por_etapa(ocupacao).items():
        if not etapa_cursavel(disciplinas, horarios):
            toleradas.add(chave)
            fixados.update(i for turmas in disciplinas.values() for secao in turmas.values() for i in secao)
    if fixar_todos:
        for aresta in arestas:
            fixados.update(aresta)
        return frozenset(fixados - externos), frozenset(toleradas)

    pendentes = {aresta for aresta in arestas if not (externos | fixados).intersection(aresta)}
    while pendentes:
        grau: dict[str, int] = defaultdict(int)
        for aresta in pendentes:
            for encontro_id in aresta:
                grau[encontro_id] += 1
        escolhido = max(sorted(grau), key=lambda encontro_id: grau[encontro_id])
        fixados.add(escolhido)
        pendentes = {aresta for aresta in pendentes if escolhido not in aresta}
    return frozenset(fixados - externos), frozenset(toleradas)


def resolver_solucao_a_fallback(
    ocupacao: ModeloOcupacao,
    modelagem: ModeloCPsat,
    fixados: frozenset[str],
    limite_segundos: float = 300.0,
) -> tuple[int, dict[str, Candidato], dict[str, Any]]:
    """Reduz o uso fora do turno-alvo sem piorar nenhum curso e depois maximiza a preservação.

    Etapa 1 minimiza a soma dos percentuais fora do alvo por curso (cada curso
    limitado ao valor atual); a etapa 2 mantém esse valor e aplica o objetivo de A.
    """

    linhas = _linhas_por_encontro(ocupacao)
    fixos = alocacoes_fixos(ocupacao, fixados)
    totais: dict[str, int] = defaultdict(int)
    atual: dict[str, int] = defaultdict(int)
    fora_fixo: dict[str, int] = defaultdict(int)
    termos: dict[str, list[Any]] = defaultdict(list)
    originais = {encontro.id: encontro.atributos_fisicos for encontro in ocupacao.encontros_fisicos}
    for encontro_id, original in originais.items():
        inicio0, fim0 = _minutos(original["hora_inicio"]), _minutos(original["hora_fim"])
        cursos = {registro["curso"] for registro in linhas[encontro_id]} & set(JANELA_FORA_ALVO)
        for curso in cursos:
            totais[curso] += fim0 - inicio0
            atual[curso] += _fora_do_alvo(curso, inicio0, fim0)
            if encontro_id in fixos:
                fora_fixo[curso] += _fora_do_alvo(curso, inicio0, fim0)
            else:
                for candidato, variavel in modelagem.variaveis[encontro_id]:
                    minutos = _fora_do_alvo(curso, _minutos(candidato.hora_inicio), _minutos(candidato.hora_fim))
                    if minutos:
                        termos[curso].append(minutos * variavel)

    modelo = modelagem.modelo
    cursos_ativos = [curso for curso in JANELA_FORA_ALVO if totais[curso] > 0]
    fora_curso = {curso: fora_fixo[curso] + sum(termos[curso]) for curso in cursos_ativos}
    for curso in cursos_ativos:
        modelo.add(fora_curso[curso] <= atual[curso])
    objetivo_fora = sum(
        fora_curso[curso] * (ESCALA_PERCENTUAL // totais[curso]) for curso in cursos_ativos
    )
    modelo.minimize(objetivo_fora)
    for encontro_id, escolhas in modelagem.variaveis.items():
        original = originais[encontro_id]
        for candidato, variavel in escolhas:
            modelo.add_hint(variavel, int(all(
                candidato.alocacao()[campo] == original[campo]
                for campo in ("predio", "sala", "dia_semana", "hora_inicio", "hora_fim")
            )))

    def novo_solver(tempo: float) -> cp_model.CpSolver:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = tempo
        solver.parameters.num_search_workers = 8
        solver.parameters.random_seed = 0
        return solver

    def extrair(solver: cp_model.CpSolver) -> dict[str, Candidato]:
        return {
            encontro_id: next(c for c, variavel in escolhas if solver.boolean_value(variavel))
            for encontro_id, escolhas in modelagem.variaveis.items()
        }

    solver_1 = novo_solver(limite_segundos * 0.4)
    status_1 = solver_1.solve(modelo)
    nomes = cp_model.CpSolver()
    detalhes: dict[str, Any] = {
        "modo": "fallback",
        "encontros_fixados_baseline": len(fixados),
        "status_etapa_1": nomes.status_name(status_1),
        "limite_segundos": limite_segundos,
        "quantidade_variaveis": len(modelo.proto.variables),
        "quantidade_restricoes": len(modelo.proto.constraints),
    }
    if status_1 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        detalhes.update({"status": nomes.status_name(status_1), "valor_objetivo": None,
                         "melhor_limite": None, "tempo_segundos": solver_1.wall_time})
        return status_1, {}, detalhes

    solucao = extrair(solver_1)
    melhor_fora = int(round(solver_1.objective_value))
    modelo.clear_hints()
    for escolhas in modelagem.variaveis.values():
        for _, variavel in escolhas:
            modelo.add_hint(variavel, solver_1.boolean_value(variavel))
    modelo.add(objetivo_fora <= melhor_fora)
    adicionar_objetivo_solucao_a(ocupacao, modelagem)

    solver_2 = novo_solver(max(limite_segundos - solver_1.wall_time, limite_segundos * 0.2))
    status_2 = solver_2.solve(modelo)
    if status_2 in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        solucao = extrair(solver_2)
        status = cp_model.OPTIMAL if status_1 == status_2 == cp_model.OPTIMAL else cp_model.FEASIBLE
        valor, limite = solver_2.objective_value, solver_2.best_objective_bound
    else:
        status, valor, limite = cp_model.FEASIBLE, None, None

    cursos_por_encontro = {e: {r["curso"] for r in linhas[e]} for e in originais}
    proposto = {
        curso: fora_fixo[curso] + sum(
            _fora_do_alvo(curso, _minutos(candidato.hora_inicio), _minutos(candidato.hora_fim))
            for encontro_id, candidato in solucao.items()
            if curso in cursos_por_encontro[encontro_id]
        )
        for curso in cursos_ativos
    }
    detalhes.update({
        "status": nomes.status_name(status),
        "status_etapa_2": nomes.status_name(status_2),
        "valor_objetivo": valor,
        "melhor_limite": limite,
        "tempo_segundos": solver_1.wall_time + solver_2.wall_time,
        "fora_do_alvo_percentual_atual": {c: round(100 * atual[c] / totais[c], 2) for c in cursos_ativos},
        "fora_do_alvo_percentual_proposto": {c: round(100 * proposto[c] / totais[c], 2) for c in cursos_ativos},
    })
    return status, solucao, detalhes