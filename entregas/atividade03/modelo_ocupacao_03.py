"""Normalização determinística do CSV da Atividade 03, sem alterar a fonte."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


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

CHAVE_EVENTO_FISICO = (
    "semestre",
    "predio",
    "sala",
    "codigo_disciplina",
    "dia_semana",
    "hora_inicio",
    "hora_fim",
    "turmas_compartilhando_sala",
)

COLUNAS_FISICAS_INVARIANTES = (
    "semestre",
    "predio",
    "sala",
    "capacidade_sala",
    "tipo_sala",
    "codigo_disciplina",
    "nome_disciplina",
    "dia_semana",
    "hora_inicio",
    "hora_fim",
    "numero_periodos",
    "turmas_compartilhando_sala",
)

CHAVE_TURMA_ACADEMICA = ("semestre", "curso", "codigo_disciplina", "turma")
CHAVE_PADRAO_SEMANAL = (
    "semestre",
    "codigo_disciplina",
    "turmas_compartilhando_sala",
)

ORDEM_DIAS = {
    "SEGUNDA-FEIRA": 0,
    "TERÇA-FEIRA": 1,
    "QUARTA-FEIRA": 2,
    "QUINTA-FEIRA": 3,
    "SEXTA-FEIRA": 4,
}


@dataclass(frozen=True)
class TurmaAcademica:
    id: str
    semestre: str
    curso: str
    codigo_disciplina: str
    turma: str
    nome_disciplina: str
    etapa: str
    creditos: str


@dataclass(frozen=True)
class MembroCompartilhamento:
    id: str
    padrao_semanal_id: str
    turma: str


@dataclass(frozen=True)
class AtribuicaoDocente:
    id: str
    evento_fisico_id: str
    membro_compartilhamento_id: str
    docente: str
    turmas_academicas: tuple[str, ...]
    linhas_fonte: tuple[int, ...]


@dataclass(frozen=True)
class EncontroFisico:
    id: str
    padrao_semanal_id: str
    atributos_fisicos: dict[str, str]
    membros: tuple[str, ...]
    turmas_academicas: tuple[str, ...]
    atribuicoes_docentes: tuple[str, ...]
    linhas_fonte: tuple[int, ...]


@dataclass(frozen=True)
class PadraoSemanal:
    id: str
    semestre: str
    codigo_disciplina: str
    grupo_compartilhado: str
    membros: tuple[str, ...]
    encontros_fisicos: tuple[str, ...]


@dataclass(frozen=True)
class ModeloOcupacao:
    cabecalho: tuple[str, ...]
    linhas_fonte: tuple[dict[str, Any], ...]
    turmas_academicas: tuple[TurmaAcademica, ...]
    membros_compartilhamento: tuple[MembroCompartilhamento, ...]
    atribuicoes_docentes: tuple[AtribuicaoDocente, ...]
    encontros_fisicos: tuple[EncontroFisico, ...]
    padroes_semanais: tuple[PadraoSemanal, ...]

    def resumo(self) -> dict[str, int]:
        return {
            "linhas_fonte": len(self.linhas_fonte),
            "turmas_academicas": len(self.turmas_academicas),
            "membros_compartilhamento": len(self.membros_compartilhamento),
            "atribuicoes_docentes": len(self.atribuicoes_docentes),
            "encontros_fisicos": len(self.encontros_fisicos),
            "padroes_semanais": len(self.padroes_semanais),
        }

    def para_dict(self) -> dict[str, Any]:
        return asdict(self)


def _id_deterministico(prefixo: str, chave: tuple[str, ...]) -> str:
    serializada = json.dumps(chave, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(serializada.encode("utf-8")).hexdigest()[:16]
    return f"{prefixo}-{digest}"


def _tokens_compartilhamento(valor: str, linha_fonte: int) -> tuple[str, ...]:
    tokens = tuple(token.strip() for token in valor.split("/"))
    if any(not token for token in tokens) or len(set(tokens)) != len(tokens):
        raise ValueError(
            f"Linha {linha_fonte}: grupo de compartilhamento inválido: {valor!r}."
        )
    return tokens


def _chave(registro: dict[str, str], colunas: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(registro[coluna] for coluna in colunas)


def _ordenar_encontro(encontro: EncontroFisico) -> tuple[int, str, str, str]:
    atributos = encontro.atributos_fisicos
    return (
        ORDEM_DIAS.get(atributos["dia_semana"], 99),
        atributos["hora_inicio"],
        atributos["sala"],
        encontro.id,
    )


def normalizar_registros(
    cabecalho: list[str], registros: list[dict[str, str]]
) -> ModeloOcupacao:
    """Constrói o modelo canônico e mantém a referência a cada linha CSV."""

    colunas_faltantes = COLUNAS_OBRIGATORIAS.difference(cabecalho)
    if colunas_faltantes:
        faltantes = ", ".join(sorted(colunas_faltantes))
        raise ValueError(f"Colunas obrigatórias ausentes: {faltantes}.")

    fontes: list[dict[str, Any]] = []
    por_evento: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    metadados_turma: dict[tuple[str, ...], set[tuple[str, str, str]]] = defaultdict(set)

    for numero_linha, registro_original in enumerate(registros, start=2):
        if None in registro_original:
            raise ValueError(f"Linha {numero_linha}: há campos além do cabeçalho.")
        registro = dict(registro_original)
        ausentes = [
            coluna
            for coluna in COLUNAS_OBRIGATORIAS
            if not registro.get(coluna, "").strip()
        ]
        if ausentes:
            raise ValueError(
                f"Linha {numero_linha}: valores vazios em {', '.join(sorted(ausentes))}."
            )

        tokens = _tokens_compartilhamento(
            registro["turmas_compartilhando_sala"], numero_linha
        )
        if registro["turma"] not in tokens:
            raise ValueError(
                f"Linha {numero_linha}: turma {registro['turma']!r} não pertence "
                f"ao grupo {registro['turmas_compartilhando_sala']!r}."
            )

        chave_evento = _chave(registro, CHAVE_EVENTO_FISICO)
        chave_turma = _chave(registro, CHAVE_TURMA_ACADEMICA)
        chave_padrao = _chave(registro, CHAVE_PADRAO_SEMANAL)
        evento_id = _id_deterministico("EV", chave_evento)
        turma_id = _id_deterministico("TU", chave_turma)
        padrao_id = _id_deterministico("PS", chave_padrao)
        membro_id = _id_deterministico("ME", (*chave_padrao, registro["turma"]))
        linha = {
            "linha_fonte": numero_linha,
            "valores": registro,
            "evento_fisico_id": evento_id,
            "turma_academica_id": turma_id,
            "membro_compartilhamento_id": membro_id,
            "padrao_semanal_id": padrao_id,
        }
        fontes.append(linha)
        por_evento[chave_evento].append(linha)
        metadados_turma[chave_turma].add(
            (registro["nome_disciplina"], registro["etapa"], registro["creditos"])
        )

    conflitos_turma = [
        (chave, valores)
        for chave, valores in metadados_turma.items()
        if len(valores) != 1
    ]
    if conflitos_turma:
        chave, valores = conflitos_turma[0]
        raise ValueError(
            f"Metadados acadêmicos inconsistentes para {chave!r}: {sorted(valores)!r}."
        )

    turmas_por_chave = {}
    for chave, valores in metadados_turma.items():
        nome_disciplina, etapa, creditos = next(iter(valores))
        turmas_por_chave[chave] = TurmaAcademica(
            id=_id_deterministico("TU", chave),
            semestre=chave[0],
            curso=chave[1],
            codigo_disciplina=chave[2],
            turma=chave[3],
            nome_disciplina=nome_disciplina,
            etapa=etapa,
            creditos=creditos,
        )

    padroes_temporarios: dict[tuple[str, ...], dict[str, Any]] = {}
    membros_por_chave: dict[tuple[str, ...], set[str]] = defaultdict(set)
    encontros: list[EncontroFisico] = []
    atribuicoes_temporarias: dict[tuple[str, str, str], dict[str, set[Any]]] = {}

    for chave_evento, linhas in por_evento.items():
        primeira = linhas[0]["valores"]
        inconsistencias = [
            coluna
            for coluna in COLUNAS_FISICAS_INVARIANTES
            if len({linha["valores"][coluna] for linha in linhas}) > 1
        ]
        if inconsistencias:
            raise ValueError(
                "Atributos físicos inconsistentes no evento "
                f"{_id_deterministico('EV', chave_evento)}: "
                f"{', '.join(inconsistencias)}."
            )

        chave_padrao = _chave(primeira, CHAVE_PADRAO_SEMANAL)
        padrao_id = _id_deterministico("PS", chave_padrao)
        tokens = _tokens_compartilhamento(
            primeira["turmas_compartilhando_sala"], linhas[0]["linha_fonte"]
        )
        membros_observados = {linha["valores"]["turma"] for linha in linhas}
        if membros_observados != set(tokens):
            faltantes = sorted(set(tokens).difference(membros_observados))
            raise ValueError(
                f"Evento {_id_deterministico('EV', chave_evento)} sem linhas-fonte "
                f"para os membros declarados: {', '.join(faltantes)}."
            )
        membros_ids = tuple(
            _id_deterministico("ME", (*chave_padrao, token)) for token in tokens
        )
        membros_por_chave[chave_padrao].update(tokens)

        turma_ids = tuple(sorted({linha["turma_academica_id"] for linha in linhas}))
        atribuicoes_ids = set()
        for linha in linhas:
            valores = linha["valores"]
            chave_atribuicao = (
                linha["evento_fisico_id"],
                linha["membro_compartilhamento_id"],
                valores["docente"],
            )
            atribuicao = atribuicoes_temporarias.setdefault(
                chave_atribuicao, {"linhas": set(), "turmas": set()}
            )
            atribuicao["linhas"].add(linha["linha_fonte"])
            atribuicao["turmas"].add(linha["turma_academica_id"])
            atribuicoes_ids.add(_id_deterministico("DO", chave_atribuicao))

        encontro = EncontroFisico(
            id=_id_deterministico("EV", chave_evento),
            padrao_semanal_id=padrao_id,
            atributos_fisicos={
                coluna: primeira[coluna] for coluna in COLUNAS_FISICAS_INVARIANTES
            },
            membros=membros_ids,
            turmas_academicas=tuple(sorted(turma_ids)),
            atribuicoes_docentes=tuple(sorted(atribuicoes_ids)),
            linhas_fonte=tuple(sorted(linha["linha_fonte"] for linha in linhas)),
        )
        encontros.append(encontro)
        padroes_temporarios.setdefault(
            chave_padrao,
            {
                "id": padrao_id,
                "semestre": primeira["semestre"],
                "codigo_disciplina": primeira["codigo_disciplina"],
                "grupo_compartilhado": primeira["turmas_compartilhando_sala"],
                "encontros": [],
            },
        )["encontros"].append(encontro)

    atribuicoes = tuple(
        AtribuicaoDocente(
            id=_id_deterministico("DO", chave),
            evento_fisico_id=chave[0],
            membro_compartilhamento_id=chave[1],
            docente=chave[2],
            turmas_academicas=tuple(sorted(associacao["turmas"])),
            linhas_fonte=tuple(sorted(associacao["linhas"])),
        )
        for chave, associacao in sorted(atribuicoes_temporarias.items())
    )
    membros = tuple(
        MembroCompartilhamento(
            id=_id_deterministico("ME", (*chave, token)),
            padrao_semanal_id=_id_deterministico("PS", chave),
            turma=token,
        )
        for chave, tokens in sorted(membros_por_chave.items())
        for token in sorted(tokens)
    )
    padroes = tuple(
        PadraoSemanal(
            id=info["id"],
            semestre=info["semestre"],
            codigo_disciplina=info["codigo_disciplina"],
            grupo_compartilhado=info["grupo_compartilhado"],
            membros=tuple(
                _id_deterministico("ME", (*chave, token))
                for token in sorted(membros_por_chave[chave])
            ),
            encontros_fisicos=tuple(
                encontro.id
                for encontro in sorted(info["encontros"], key=_ordenar_encontro)
            ),
        )
        for chave, info in sorted(padroes_temporarios.items())
    )

    modelo = ModeloOcupacao(
        cabecalho=tuple(cabecalho),
        linhas_fonte=tuple(fontes),
        turmas_academicas=tuple(
            turmas_por_chave[chave] for chave in sorted(turmas_por_chave)
        ),
        membros_compartilhamento=membros,
        atribuicoes_docentes=atribuicoes,
        encontros_fisicos=tuple(sorted(encontros, key=lambda encontro: encontro.id)),
        padroes_semanais=padroes,
    )

    linhas_reconciliadas = [
        linha
        for encontro in modelo.encontros_fisicos
        for linha in encontro.linhas_fonte
    ]
    linhas_originais = [linha["linha_fonte"] for linha in modelo.linhas_fonte]
    if sorted(linhas_reconciliadas) != sorted(linhas_originais):
        raise AssertionError("A reconciliação dos encontros não preservou as linhas-fonte.")

    return modelo


def carregar_modelo(caminho_csv: str | Path) -> ModeloOcupacao:
    """Carrega e normaliza um CSV mantendo o número físico de cada linha-fonte."""

    with Path(caminho_csv).open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if leitor.fieldnames is None:
            raise ValueError("O CSV não contém cabeçalho.")
        registros = list(leitor)
        return normalizar_registros(leitor.fieldnames, registros)


if __name__ == "__main__":
    caminho = Path(__file__).with_name("mapa_salas_tidy_03.csv")
    modelo = carregar_modelo(caminho)
    print(json.dumps(modelo.resumo(), ensure_ascii=False, indent=2))