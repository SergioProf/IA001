"""Valida CSVs exportados e gera comparacao reproduzivel de A, B e C."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from modelo_ocupacao_03 import ModeloOcupacao, carregar_modelo
from restricoes_03 import (
    CAMPOS_ALOCACAO,
    CURSOS_ALVO,
    TURNOS_ALVO,
    secoes_por_etapa,
    selecionar_turmas_etapa,
    validar_grade,
)


CAMPOS_POSICAO = tuple(sorted(CAMPOS_ALOCACAO))
CAMPOS_VARIAVEIS = set(CAMPOS_POSICAO)
SOLUCOES_PADRAO = {
    "A": ("saida_solucao_A/solucao_A.csv", "solucao_A.csv"),
    "B": ("saida_solucao_B/solucao_B.csv", "saida_solucao_B/candidato_B.csv"),
    "C": ("saida_solucao_C/solucao_C.csv", "solucao_C.csv"),
}


def _ler_csv(caminho: Path) -> tuple[list[str], list[dict[str, str]]]:
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if leitor.fieldnames is None:
            raise ValueError(f"CSV sem cabecalho: {caminho}")
        return leitor.fieldnames, list(leitor)


def _assinatura(registro: dict[str, str], colunas: list[str]) -> tuple[str, ...]:
    return tuple(registro.get(coluna, "") for coluna in colunas)


def _minutos(horario: str) -> int:
    horas, minutos = (int(parte) for parte in horario.split(":"))
    return horas * 60 + minutos


def _minutos_alvo(curso: str, inicio: int, fim: int) -> int:
    return sum(max(0, min(fim, limite_fim) - max(inicio, limite_inicio))
               for limite_inicio, limite_fim in TURNOS_ALVO.get(curso, ()))


def _validar_integridade_csv(
    modelo: ModeloOcupacao,
    cabecalho_fonte: list[str],
    registros: list[dict[str, str]],
    cabecalho_solucao: list[str],
    linhas_solucao: list[dict[str, str]],
) -> dict[str, dict[str, str]]:
    faltantes = set(cabecalho_fonte).difference(cabecalho_solucao)
    if faltantes:
        raise ValueError(f"Colunas da fonte ausentes na solucao: {sorted(faltantes)}")
    if "encontro_id" not in cabecalho_solucao:
        raise ValueError("A solucao precisa preservar a coluna encontro_id.")

    colunas_imutaveis = [coluna for coluna in cabecalho_fonte if coluna not in CAMPOS_VARIAVEIS]
    esperadas = Counter(
        (_assinatura(registro, colunas_imutaveis), linha["evento_fisico_id"])
        for registro, linha in zip(registros, modelo.linhas_fonte)
    )
    recebidas = Counter(
        (_assinatura(registro, colunas_imutaveis), registro.get("encontro_id", ""))
        for registro in linhas_solucao
    )
    if len(registros) != len(modelo.linhas_fonte):
        raise ValueError("A leitura da fonte nao corresponde ao modelo normalizado.")
    if len(linhas_solucao) != len(registros) or recebidas != esperadas:
        faltando = sum((esperadas - recebidas).values())
        extras = sum((recebidas - esperadas).values())
        raise ValueError(f"Identidade/linhagem divergente: {faltando} linhas ausentes e {extras} extras/alteradas.")

    alocacoes: dict[str, dict[str, str]] = {}
    excecoes: dict[str, str] = {}
    for registro in linhas_solucao:
        encontro_id = registro["encontro_id"]
        alocacao = {campo: registro[campo] for campo in CAMPOS_POSICAO}
        if encontro_id in alocacoes and alocacoes[encontro_id] != alocacao:
            raise ValueError(f"Alocacoes divergentes entre linhas do encontro {encontro_id}.")
        alocacoes[encontro_id] = alocacao
        justificativa = registro.get("excecao_turno", "").strip()
        if justificativa:
            if encontro_id in excecoes and excecoes[encontro_id] != justificativa:
                raise ValueError(f"Justificativas divergentes no encontro {encontro_id}.")
            excecoes[encontro_id] = justificativa
    return {"alocacoes": alocacoes, "excecoes": excecoes}


def _metricas_curso(
    modelo: ModeloOcupacao, alocacoes: dict[str, dict[str, str]]
) -> dict[str, dict[str, float | int]]:
    cursos_turma = {turma.id: turma.curso for turma in modelo.turmas_academicas}
    total_por_turma: dict[str, int] = defaultdict(int)
    alvo_por_turma: dict[str, int] = defaultdict(int)
    for encontro in modelo.encontros_fisicos:
        posicao = alocacoes[encontro.id]
        inicio, fim = _minutos(posicao["hora_inicio"]), _minutos(posicao["hora_fim"])
        minutos = fim - inicio
        for turma_id in encontro.turmas_academicas:
            curso = cursos_turma[turma_id]
            if curso not in CURSOS_ALVO:
                continue
            total_por_turma[turma_id] += minutos
            alvo_por_turma[turma_id] += _minutos_alvo(curso, inicio, fim)
    resultado = {}
    for curso in sorted(CURSOS_ALVO):
        turmas = [turma.id for turma in modelo.turmas_academicas if turma.curso == curso]
        total = sum(total_por_turma[turma_id] for turma_id in turmas)
        alvo = sum(alvo_por_turma[turma_id] for turma_id in turmas)
        resultado[curso] = {
            "ch_total_horas": round(total / 60, 2),
            "ch_turno_alvo_horas": round(alvo / 60, 2),
            "percentual_turno_alvo": round(100 * alvo / total, 2) if total else 0,
            "turmas_total": len(turmas),
            "turmas_integralmente_no_alvo": sum(
                total_por_turma[turma_id] > 0
                and alvo_por_turma[turma_id] == total_por_turma[turma_id]
                for turma_id in turmas
            ),
            "turmas_com_algum_horario_no_alvo": sum(alvo_por_turma[turma_id] > 0 for turma_id in turmas),
        }
    return resultado


def _turmas_escolhidas_json(caminho_csv: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    caminho_json = caminho_csv.with_suffix(".json")
    if not caminho_json.is_file():
        return {}
    try:
        metadados = json.loads(caminho_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    selecoes = {}
    for chave, turmas in metadados.get("turmas_escolhidas_por_etapa", {}).items():
        try:
            semestre, curso, etapa = chave.rsplit("/", 2)
            selecoes[(semestre, curso, etapa)] = {
                disciplina: turma
                for item in turmas
                for disciplina, turma in [item.split(":", 1)]
            }
        except (AttributeError, TypeError, ValueError):
            continue
    return selecoes


def _inventarios(
    modelo: ModeloOcupacao,
    alocacoes: dict[str, dict[str, str]],
    rotulo: str,
    selecoes_preferidas: dict[tuple[str, str, str], dict[str, str]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    por_sala: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"encontros": set(), "minutos": 0})
    por_sala_curso: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(lambda: {"encontros": set(), "minutos": 0})
    por_etapa: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    turmas_por_etapa: dict[tuple[str, str], str] = {}
    por_docente: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    turmas = {turma.id: turma for turma in modelo.turmas_academicas}
    tipos_sala: dict[tuple[str, str], str] = {}
    for linha in modelo.linhas_fonte:
        valores = linha["valores"]
        tipos_sala[(valores["predio"], valores["sala"])] = valores["tipo_sala"]
    docentes_por_evento: dict[str, set[str]] = defaultdict(set)
    for atribuicao in modelo.atribuicoes_docentes:
        docentes_por_evento[atribuicao.evento_fisico_id].add(atribuicao.docente)
    salas_fonte = {
        (linha["valores"]["predio"], linha["valores"]["sala"])
        for linha in modelo.linhas_fonte
    }
    for chave_sala in salas_fonte:
        por_sala[chave_sala]

    for encontro in modelo.encontros_fisicos:
        posicao = alocacoes[encontro.id]
        chave_sala = (posicao["predio"], posicao["sala"])
        minutos = _minutos(posicao["hora_fim"]) - _minutos(posicao["hora_inicio"])
        sala = por_sala[chave_sala]
        sala["encontros"].add(encontro.id)
        sala["minutos"] += minutos
        for curso in {turmas[turma_id].curso for turma_id in encontro.turmas_academicas}:
            sala_curso = por_sala_curso[(posicao["predio"], posicao["sala"], curso)]
            sala_curso["encontros"].add(encontro.id)
            sala_curso["minutos"] += minutos
        dia = posicao["dia_semana"].upper()
        for docente in docentes_por_evento[encontro.id]:
            por_docente[docente][dia] += minutos

    horarios = {
        encontro.id: (
            alocacoes[encontro.id]["dia_semana"].strip().upper(),
            _minutos(alocacoes[encontro.id]["hora_inicio"]),
            _minutos(alocacoes[encontro.id]["hora_fim"]),
        )
        for encontro in modelo.encontros_fisicos
    }
    for chave, disciplinas in secoes_por_etapa(modelo).items():
        selecionadas = selecionar_turmas_etapa(
            disciplinas,
            horarios,
            (selecoes_preferidas or {}).get(chave),
        )
        if selecionadas is None:
            continue
        eventos_selecionados = {
            encontro_id
            for codigo, turma in selecionadas.items()
            for encontro_id in disciplinas[codigo][turma]
        }
        grupo_etapa = (chave[1], chave[2])
        turmas_por_etapa[grupo_etapa] = ", ".join(
            f"{codigo}:{turma}" for codigo, turma in sorted(selecionadas.items())
        )
        for encontro_id in eventos_selecionados:
            posicao = alocacoes[encontro_id]
            dia = posicao["dia_semana"].strip().upper()
            minutos = _minutos(posicao["hora_fim"]) - _minutos(posicao["hora_inicio"])
            por_etapa[grupo_etapa][dia] += minutos

    salas = [{
        "solucao": rotulo, "predio": predio, "sala": sala,
        "encontros": len(info["encontros"]), "horas_ocupadas": round(info["minutos"] / 60, 2),
        "situacao": "sem_ocupacao" if not info["encontros"] else "ocupada",
    } for (predio, sala), info in sorted(por_sala.items())]
    salas_por_curso = [{
        "solucao": rotulo, "predio": predio, "sala": sala,
        "tipo_sala": tipos_sala.get((predio, sala), ""), "curso": curso,
        "encontros": len(info["encontros"]), "horas_aula": round(info["minutos"] / 60, 2),
    } for (predio, sala, curso), info in sorted(por_sala_curso.items())]
    distribuicao = []
    equilibrio = []
    for tipo, grupos in (("etapa_aluno", por_etapa), ("docente", por_docente)):
        desvios = []
        amplitudes = []
        for grupo, cargas in sorted(grupos.items(), key=lambda item: str(item[0])):
            identificador = "/".join(grupo) if isinstance(grupo, tuple) else grupo
            dias = ("SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA")
            horas = [cargas.get(dia, 0) / 60 for dia in dias]
            media = sum(horas) / len(dias)
            desvios.append(sum(abs(valor - media) for valor in horas) / len(dias))
            amplitudes.append(max(horas) - min(horas))
            for dia in dias:
                distribuicao.append({
                    "solucao": rotulo, "grupo_tipo": tipo, "grupo": identificador,
                    "dia_semana": dia, "horas": round(cargas.get(dia, 0) / 60, 2),
                    "turmas_selecionadas": turmas_por_etapa.get(grupo, "") if tipo == "etapa_aluno" else "",
                })
        equilibrio.append({
            "solucao": rotulo, "grupo_tipo": tipo, "grupos": len(desvios),
            "desvio_absoluto_medio_diario_horas": round(sum(desvios) / len(desvios), 3) if desvios else 0,
            "amplitude_diaria_media_horas": round(sum(amplitudes) / len(amplitudes), 2) if amplitudes else 0,
        })
    return salas, salas_por_curso, distribuicao, equilibrio


def _gravar_csv(caminho: Path, linhas: list[dict[str, Any]], colunas: list[str]) -> None:
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, extrasaction="ignore")
        escritor.writeheader()
        escritor.writerows(linhas)


def _resolver_caminho(base: Path, candidatos: tuple[str, ...]) -> Path:
    for candidato in candidatos:
        caminho = base / candidato
        if caminho.is_file():
            return caminho
    raise FileNotFoundError(f"Nenhum artefato encontrado: {', '.join(candidatos)}")


def validar_e_comparar(
    arquivo_fonte: Path,
    caminhos: dict[str, Path],
    pasta_saida: Path,
) -> int:
    hash_fonte = hashlib.sha256(arquivo_fonte.read_bytes()).hexdigest()
    cabecalho_fonte, registros_fonte = _ler_csv(arquivo_fonte)
    modelo = carregar_modelo(arquivo_fonte)
    diagnosticos_antes = validar_grade(modelo)
    relatorio = [
        "# Validacao independente das propostas A, B e C", "",
        f"- Fonte: `{arquivo_fonte.name}` (SHA-256 `{hash_fonte}`).",
        f"- Linhas da fonte: {len(registros_fonte)}; encontros fisicos: {len(modelo.encontros_fisicos)}.",
        "- As regras sao validadas nos CSVs exportados; nenhum objeto interno do CP-SAT e lido.",
        "- A CH diaria por etapa conta uma turma por disciplina em uma combinacao sem sobreposicoes. A escolha pode variar entre propostas; A/C usam uma combinacao valida reconstruida, e B preserva a selecao do JSON quando compativel com o CSV.", "",
        "## Resultado", "",
        "| Proposta | Estado do artefato | Encontros | Alterados | Duras baseline | Duras novas | Excecoes turno | Resultado |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    comparacao: list[dict[str, Any]] = []
    excecoes_csv: list[dict[str, Any]] = []
    ocupacao_csv: list[dict[str, Any]] = []
    ocupacao_cursos_csv: list[dict[str, Any]] = []
    distribuicao_csv: list[dict[str, Any]] = []
    equilibrio_csv: list[dict[str, Any]] = []
    salas_usadas_antes: set[tuple[str, str]] = set()
    total_bloqueantes = 0
    baseline_por_regra = Counter(item.regra for item in diagnosticos_antes if item.severidade == "baseline")

    for rotulo in ("ANTES", "A", "B", "C"):
        if rotulo == "ANTES":
            alocacoes = {
                encontro.id: {campo: encontro.atributos_fisicos[campo] for campo in CAMPOS_POSICAO}
                for encontro in modelo.encontros_fisicos
            }
            diagnosticos = diagnosticos_antes
            situacao = "fonte"
            excecoes_turno = sum(item.regra == "H010" for item in diagnosticos if item.severidade == "baseline")
        else:
            caminho = caminhos[rotulo]
            cabecalho, linhas = _ler_csv(caminho)
            dados = _validar_integridade_csv(modelo, cabecalho_fonte, registros_fonte, cabecalho, linhas)
            alocacoes = dados["alocacoes"]
            diagnosticos = validar_grade(modelo, alocacoes, dados["excecoes"])
            situacao = "FEASIBLE nao otima" if rotulo == "B" and any(
                linha.get("status_solver") == "FEASIBLE" for linha in linhas
            ) else "exportada"
            excecoes_turno = sum(item.regra == "H010" and item.severidade == "excecao" for item in diagnosticos)
            for item in diagnosticos:
                if item.regra == "H010" and item.severidade == "excecao":
                    excecoes_csv.append({
                        "solucao": rotulo, "encontro_id": ";".join(item.encontros),
                        "regra": item.regra, "severidade": item.severidade, "detalhe": item.mensagem,
                    })

        novas = [item for item in diagnosticos if item.severidade == "inviolavel"]
        baseline = [item for item in diagnosticos if item.severidade == "baseline"]
        if rotulo != "ANTES":
            total_bloqueantes += len(novas)
            mudancas = Counter()
            for encontro in modelo.encontros_fisicos:
                original = {campo: encontro.atributos_fisicos[campo] for campo in CAMPOS_POSICAO}
                proposta = alocacoes[encontro.id]
                if proposta != original:
                    mudancas["encontros_alterados"] += 1
                    mudancas["salas_alteradas"] += (original["predio"], original["sala"]) != (proposta["predio"], proposta["sala"])
                    mudancas["dias_alterados"] += original["dia_semana"] != proposta["dia_semana"]
                    mudancas["horarios_alterados"] += (original["hora_inicio"], original["hora_fim"]) != (proposta["hora_inicio"], proposta["hora_fim"])
        else:
            mudancas = Counter()
            salas_usadas_antes = {
                (alocacao["predio"], alocacao["sala"]) for alocacao in alocacoes.values()
            }
        resultado = "FALHA" if novas else "OK"
        alterados = mudancas["encontros_alterados"]
        relatorio.append(
            f"| {rotulo} | {situacao} | {len(alocacoes)} | {alterados} | {len(baseline)} | {len(novas)} | {excecoes_turno} | {resultado} |"
        )
        violacoes_por_regra = Counter(item.regra for item in novas)
        for curso, valores in _metricas_curso(modelo, alocacoes).items():
            comparacao.append({
                "solucao": rotulo, "curso": curso, **valores,
                "encontros_alterados": alterados,
                "salas_alteradas": mudancas["salas_alteradas"],
                "dias_alterados": mudancas["dias_alterados"],
                "horarios_alterados": mudancas["horarios_alterados"],
                "violacoes_baseline": len(baseline), "violacoes_duras_novas": len(novas),
                "excecoes_turno": excecoes_turno,
                **{f"{regra}_novas": violacoes_por_regra[regra] for regra in ("H002", "H003", "H004", "H005", "H006", "H007", "H008", "H009", "H010")},
            })
        selecoes_preferidas = _turmas_escolhidas_json(caminhos[rotulo]) if rotulo == "B" else None
        salas, salas_por_curso, distribuicao, equilibrio = _inventarios(
            modelo, alocacoes, rotulo, selecoes_preferidas
        )
        for sala in salas:
            chave_sala = (sala["predio"], sala["sala"])
            if rotulo != "ANTES" and sala["situacao"] == "sem_ocupacao":
                sala["situacao"] = "liberada" if chave_sala in salas_usadas_antes else "sem_ocupacao_no_baseline"
        ocupacao_csv.extend(salas)
        ocupacao_cursos_csv.extend(salas_por_curso)
        distribuicao_csv.extend(distribuicao)
        equilibrio_csv.extend(equilibrio)

    relatorio.extend(["", "## Violacoes baseline", ""])
    relatorio.extend([f"- {regra}: {quantidade}" for regra, quantidade in sorted(baseline_por_regra.items())] or ["- Nenhuma."])
    relatorio.extend([
        "", "## Notas", "",
        "- `OK` significa zero violacoes duras novas; as violacoes baseline sao reportadas separadamente.",
        "- B continua identificada como viavel, mas sem prova de otimalidade.",
        "- As regras sao aplicadas a dados reconstruidos da fonte e dos CSVs exportados; variaveis e objetos do CP-SAT nao sao lidos.",
    ])
    pasta_saida.mkdir(parents=True, exist_ok=True)
    (pasta_saida / "validacao_A_B_C.md").write_text("\n".join(relatorio) + "\n", encoding="utf-8")
    _gravar_csv(pasta_saida / "comparacao_A_B_C.csv", comparacao, [
        "solucao", "curso", "ch_total_horas", "ch_turno_alvo_horas", "percentual_turno_alvo",
        "turmas_total", "turmas_integralmente_no_alvo", "turmas_com_algum_horario_no_alvo",
        "encontros_alterados", "salas_alteradas", "dias_alterados", "horarios_alterados",
        "violacoes_baseline", "violacoes_duras_novas", "excecoes_turno",
        "H002_novas", "H003_novas", "H004_novas", "H005_novas", "H006_novas",
        "H007_novas", "H008_novas", "H009_novas", "H010_novas",
    ])
    _gravar_csv(pasta_saida / "excecoes_A_B_C.csv", excecoes_csv,
                ["solucao", "encontro_id", "regra", "severidade", "detalhe"])
    _gravar_csv(pasta_saida / "ocupacao_salas_A_B_C.csv", ocupacao_csv,
                ["solucao", "predio", "sala", "encontros", "horas_ocupadas", "situacao"])
    _gravar_csv(pasta_saida / "ocupacao_salas_por_curso_A_B_C.csv", ocupacao_cursos_csv,
                ["solucao", "predio", "sala", "tipo_sala", "curso", "encontros", "horas_aula"])
    _gravar_csv(pasta_saida / "distribuicao_semanal_A_B_C.csv", distribuicao_csv,
                ["solucao", "grupo_tipo", "grupo", "dia_semana", "horas", "turmas_selecionadas"])
    _gravar_csv(pasta_saida / "equilibrio_semanal_A_B_C.csv", equilibrio_csv,
                ["solucao", "grupo_tipo", "grupos", "desvio_absoluto_medio_diario_horas", "amplitude_diaria_media_horas"])
    print(f"Fonte SHA-256: {hash_fonte}")
    print(f"Relatorio: {pasta_saida / 'validacao_A_B_C.md'}")
    print(f"Violacoes duras novas: {total_bloqueantes}")
    return 1 if total_bloqueantes else 0


def main() -> int:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fonte", type=Path, default=base / "mapa_salas_tidy_03.csv")
    parser.add_argument("--solucao-a", type=Path)
    parser.add_argument("--solucao-b", type=Path)
    parser.add_argument("--solucao-c", type=Path)
    parser.add_argument("--saida-dir", type=Path, default=base)
    args = parser.parse_args()
    caminhos = {}
    for rotulo, argumento in (("A", args.solucao_a), ("B", args.solucao_b), ("C", args.solucao_c)):
        caminhos[rotulo] = argumento or _resolver_caminho(base, SOLUCOES_PADRAO[rotulo])
    return validar_e_comparar(args.fonte, caminhos, args.saida_dir)


if __name__ == "__main__":
    raise SystemExit(main())