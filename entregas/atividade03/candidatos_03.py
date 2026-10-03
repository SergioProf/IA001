"""Geração determinística dos domínios de alocação da fase 5."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from modelo_ocupacao_03 import EncontroFisico, ModeloOcupacao
from restricoes_03 import (
    CURSOS_ALVO,
    DIAS_VALIDOS,
    TURNOS_ALVO,
    _intervalos_sobrepostos,
    _minutos,
    _normalizar,
)


ORDEM_DIAS = ("SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA")
ALMOCO = (12 * 60 + 30, 13 * 60 + 30)


@dataclass(frozen=True, order=True)
class Candidato:
    encontro_id: str
    predio: str
    sala: str
    dia_semana: str
    hora_inicio: str
    hora_fim: str
    minutos_fora_turno_alvo: int

    def alocacao(self) -> dict[str, str]:
        return {
            "predio": self.predio,
            "sala": self.sala,
            "dia_semana": self.dia_semana,
            "hora_inicio": self.hora_inicio,
            "hora_fim": self.hora_fim,
        }


def _formatar_hora(minutos: int) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _linhas_por_encontro(modelo: ModeloOcupacao) -> dict[str, list[dict[str, Any]]]:
    por_encontro: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for linha in modelo.linhas_fonte:
        por_encontro[linha["evento_fisico_id"]].append(linha["valores"])
    return por_encontro


def _docentes_por_encontro(modelo: ModeloOcupacao) -> dict[str, set[str]]:
    por_encontro: dict[str, set[str]] = defaultdict(set)
    for atribuicao in modelo.atribuicoes_docentes:
        por_encontro[atribuicao.evento_fisico_id].add(atribuicao.docente)
    return por_encontro


def _cursos_do_encontro(registros: list[dict[str, Any]]) -> set[str]:
    return {registro["curso"] for registro in registros}


def _encontro_externo(
    encontro: EncontroFisico, linhas: dict[str, list[dict[str, Any]]]
) -> bool:
    return not _cursos_do_encontro(linhas[encontro.id]).issubset(CURSOS_ALVO)


def _vagas_do_encontro(registros: list[dict[str, Any]]) -> int:
    vagas_por_membro: dict[str, set[int]] = defaultdict(set)
    for registro in registros:
        vagas_por_membro[registro["turma"]].add(int(registro["vagas_oferecidas"]))
    if any(len(vagas) != 1 for vagas in vagas_por_membro.values()):
        return -1
    return sum(next(iter(vagas)) for vagas in vagas_por_membro.values())


def _minutos_fora_do_alvo(cursos: set[str], inicio: int, fim: int) -> int:
    janelas = sorted(
        janela
        for curso in cursos
        for janela in TURNOS_ALVO.get(curso, ())
    )
    unidos: list[list[int]] = []
    for limite_inicio, limite_fim in janelas:
        if unidos and limite_inicio <= unidos[-1][1]:
            unidos[-1][1] = max(unidos[-1][1], limite_fim)
        else:
            unidos.append([limite_inicio, limite_fim])
    minutos_no_alvo = sum(
        max(0, min(fim, limite_fim) - max(inicio, limite_inicio))
        for limite_inicio, limite_fim in unidos
    )
    return fim - inicio - minutos_no_alvo


def gerar_candidatos(
    modelo: ModeloOcupacao,
) -> dict[str, tuple[Candidato, ...]]:
    """Gera domínios móveis; encontros externos ficam fixos na posição original.

    Os intervalos são pares início/fim observados na fonte, reutilizados somente
    para encontros da mesma duração. Conflitos entre encontros móveis ficam para
    o modelo global; colisões com encontros externos fixos são removidas aqui.
    """

    linhas = _linhas_por_encontro(modelo)
    docentes = _docentes_por_encontro(modelo)
    fixos = [encontro for encontro in modelo.encontros_fisicos if _encontro_externo(encontro, linhas)]

    intervalos_por_duracao: dict[int, set[tuple[int, int]]] = defaultdict(set)
    for encontro in modelo.encontros_fisicos:
        inicio = _minutos(encontro.atributos_fisicos["hora_inicio"])
        fim = _minutos(encontro.atributos_fisicos["hora_fim"])
        if not _intervalos_sobrepostos(inicio, fim, *ALMOCO):
            intervalos_por_duracao[fim - inicio].add((inicio, fim))

    salas: dict[tuple[str, str], dict[str, Any]] = {}
    for registros in linhas.values():
        registro = registros[0]
        chave = (registro["predio"], registro["sala"])
        sala = salas.setdefault(chave, {"capacidades": set(), "tipos": set()})
        sala["capacidades"].add(int(registro["capacidade_sala"]))
        sala["tipos"].add(registro["tipo_sala"])

    ocupacoes_fixas: list[dict[str, Any]] = []
    for encontro in fixos:
        atributos = encontro.atributos_fisicos
        registros = linhas[encontro.id]
        ocupacoes_fixas.append({
            "semestre": atributos["semestre"],
            "predio": atributos["predio"],
            "sala": atributos["sala"],
            "dia": atributos["dia_semana"].strip().upper(),
            "inicio": _minutos(atributos["hora_inicio"]),
            "fim": _minutos(atributos["hora_fim"]),
            "docentes": docentes[encontro.id],
            "etapas": {
                (registro["curso"], registro["etapa"])
                for registro in registros
                if registro["curso"] in CURSOS_ALVO and registro["etapa"] != "0"
            },
        })

    dominios: dict[str, tuple[Candidato, ...]] = {}
    for encontro in sorted(modelo.encontros_fisicos, key=lambda item: item.id):
        if encontro in fixos:
            continue
        atributos = encontro.atributos_fisicos
        registros = linhas[encontro.id]
        cursos = _cursos_do_encontro(registros)
        inicio_original = _minutos(atributos["hora_inicio"])
        fim_original = _minutos(atributos["hora_fim"])
        duracao = fim_original - inicio_original
        vagas = _vagas_do_encontro(registros)
        dependente_computador = "laborat" in _normalizar(atributos["tipo_sala"])
        etapas = {
            (registro["curso"], registro["etapa"])
            for registro in registros
            if registro["curso"] in CURSOS_ALVO and registro["etapa"] != "0"
        }
        candidatos: set[Candidato] = set()

        for inicio, fim in sorted(intervalos_por_duracao[duracao]):
            for dia in ORDEM_DIAS:
                minutos_fora = _minutos_fora_do_alvo(cursos, inicio, fim)
                for (predio, sala_nome), informacao in sorted(salas.items()):
                    capacidade = min(informacao["capacidades"])
                    eh_laboratorio = any(
                        "laborat" in _normalizar(tipo) for tipo in informacao["tipos"]
                    )
                    if vagas < 0 or vagas > capacidade * 1.10:
                        continue
                    if dependente_computador and not eh_laboratorio:
                        continue
                    conflito_fixo = False
                    for fixo in ocupacoes_fixas:
                        if fixo["semestre"] != atributos["semestre"] or fixo["dia"] != dia:
                            continue
                        if not _intervalos_sobrepostos(inicio, fim, fixo["inicio"], fixo["fim"]):
                            continue
                        if (predio, sala_nome) == (fixo["predio"], fixo["sala"]):
                            conflito_fixo = True
                            break
                        if docentes[encontro.id] & fixo["docentes"]:
                            conflito_fixo = True
                            break
                        if etapas & fixo["etapas"]:
                            conflito_fixo = True
                            break
                    if conflito_fixo:
                        continue
                    candidatos.add(Candidato(
                        encontro_id=encontro.id,
                        predio=predio,
                        sala=sala_nome,
                        dia_semana=dia,
                        hora_inicio=_formatar_hora(inicio),
                        hora_fim=_formatar_hora(fim),
                        minutos_fora_turno_alvo=minutos_fora,
                    ))
        dominios[encontro.id] = tuple(sorted(candidatos))
    return dominios


def resumir_dominios(dominios: dict[str, tuple[Candidato, ...]]) -> dict[str, Any]:
    tamanhos = [len(candidatos) for candidatos in dominios.values()]
    return {
        "encontros_moveis": len(dominios),
        "candidatos_totais": sum(tamanhos),
        "dominios_vazios": sum(tamanho == 0 for tamanho in tamanhos),
        "menor_dominio": min(tamanhos, default=0),
        "maior_dominio": max(tamanhos, default=0),
        "dominio_medio": round(sum(tamanhos) / len(tamanhos), 2) if tamanhos else 0,
    }


def alocacoes_fixos(modelo: ModeloOcupacao) -> dict[str, dict[str, str]]:
    """Retorna as posições originais dos encontros com qualquer curso externo."""

    linhas = _linhas_por_encontro(modelo)
    resultado = {}
    for encontro in modelo.encontros_fisicos:
        if _encontro_externo(encontro, linhas):
            atributos = encontro.atributos_fisicos
            resultado[encontro.id] = {
                campo: atributos[campo]
                for campo in ("predio", "sala", "dia_semana", "hora_inicio", "hora_fim")
            }
    return resultado


def dominio_para_dict(
    dominios: dict[str, tuple[Candidato, ...]],
) -> dict[str, list[dict[str, Any]]]:
    """Serialização simples para inspecionar/exportar o mapa de candidatos."""

    return {
        encontro_id: [asdict(candidato) for candidato in candidatos]
        for encontro_id, candidatos in sorted(dominios.items())
    }


if __name__ == "__main__":
    from pathlib import Path

    from modelo_ocupacao_03 import carregar_modelo

    fonte = Path(__file__).with_name("mapa_salas_tidy_03.csv")
    modelo = carregar_modelo(fonte)
    dominios = gerar_candidatos(modelo)
    print(resumir_dominios(dominios))