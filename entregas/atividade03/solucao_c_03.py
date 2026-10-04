"""Execução reproduzível da proposta C (maximização de carga horária nos turnos-alvo)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from ortools.sat.python import cp_model

from candidatos_03 import _linhas_por_encontro, alocacoes_fixos, gerar_candidatos
from modelo_ocupacao_03 import ModeloOcupacao, carregar_modelo
from modelo_otimizacao_03 import ModeloCPsat, construir_modelo_cp_sat, fixados_baseline
from restricoes_03 import _minutos, diagnosticos_bloqueantes, validar_grade
from solucao_a_03 import (
    CAMPOS_EXPORTADOS,
    CAMPOS_POSICAO,
    TURNOS_ALVO_TEXTO,
    _horas_turno,
    _minutos_alvo,
    _tipo_mudanca,
)

INICIO_NOITE = 18 * 60 + 30


def adicionar_objetivo_solucao_c(ocupacao: ModeloOcupacao, modelagem: ModeloCPsat) -> None:
    """Lexicográfico: minutos fora do alvo, depois início tardio na noite, depois alterações."""

    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}
    quantidade = len(modelagem.variaveis)
    fora, tardio, alterados = [], [], []
    for encontro_id, escolhas in modelagem.variaveis.items():
        original = encontros[encontro_id].atributos_fisicos
        for candidato, variavel in escolhas:
            fora.append(candidato.minutos_fora_turno_alvo * variavel)
            inicio = _minutos(candidato.hora_inicio)
            if inicio > INICIO_NOITE:
                tardio.append((inicio - INICIO_NOITE) * variavel)
            if any(candidato.alocacao()[campo] != original[campo] for campo in CAMPOS_POSICAO):
                alterados.append(variavel)
    peso_alteracoes = 1
    peso_tardio = quantidade + 1
    peso_fora = peso_tardio * (6 * 60 * quantidade + 1)
    modelagem.modelo.minimize(
        peso_fora * sum(fora) + peso_tardio * sum(tardio) + peso_alteracoes * sum(alterados)
    )
    validacao = modelagem.modelo.validate()
    if validacao:
        raise ValueError(f"Modelo CP-SAT inválido para a Solução C: {validacao}")


def carga_turno_alvo(ocupacao: ModeloOcupacao, alocacoes: dict[str, dict[str, str]]) -> dict[str, Any]:
    """CH (horas) dentro do turno-alvo por curso alvo, contada por linha-fonte."""

    total: dict[str, float] = defaultdict(float)
    no_alvo: dict[str, float] = defaultdict(float)
    for linha in ocupacao.linhas_fonte:
        curso = linha["valores"]["curso"]
        if curso not in TURNOS_ALVO_TEXTO:
            continue
        posicao = alocacoes[linha["evento_fisico_id"]]
        inicio, fim = _minutos(posicao["hora_inicio"]), _minutos(posicao["hora_fim"])
        total[curso] += (fim - inicio) / 60
        no_alvo[curso] += _minutos_alvo({curso}, inicio, fim) / 60
    return {
        curso: {
            "ch_total_horas": round(total[curso], 2),
            "ch_no_alvo_horas": round(no_alvo[curso], 2),
            "percentual_no_alvo": round(100 * no_alvo[curso] / total[curso], 2) if total[curso] else 0.0,
        }
        for curso in sorted(total)
    }


def calcular_solucao_c(ocupacao: ModeloOcupacao, limite_segundos: float = 300.0) -> dict[str, Any]:
    fixados, toleradas = fixados_baseline(ocupacao, fixar_todos=False)
    dominios = gerar_candidatos(ocupacao, usar_grade_horaria_meia_hora=True, fixados=fixados)
    if any(not candidatos for candidatos in dominios.values()):
        raise ValueError("Há encontros móveis sem candidatos; a Solução C não pode ser construída.")
    modelagem = construir_modelo_cp_sat(ocupacao, dominios, fixados, toleradas)
    adicionar_objetivo_solucao_c(ocupacao, modelagem)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limite_segundos
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 0
    status = solver.solve(modelagem.modelo)
    resultado: dict[str, Any] = {
        "status_codigo": status,
        "solver": {
            "status": solver.status_name(status),
            "valor_objetivo": None,
            "melhor_limite": None,
            "tempo_segundos": solver.wall_time,
            "limite_segundos": limite_segundos,
            "quantidade_variaveis": len(modelagem.modelo.proto.variables),
            "quantidade_restricoes": len(modelagem.modelo.proto.constraints),
        },
        "alocacoes": {},
        "violacoes_bloqueantes": [],
    }
    if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return resultado
    resultado["solver"]["valor_objetivo"] = solver.objective_value
    resultado["solver"]["melhor_limite"] = solver.best_objective_bound

    alocacoes = alocacoes_fixos(ocupacao, fixados)
    for encontro_id, escolhas in modelagem.variaveis.items():
        alocacoes[encontro_id] = next(
            candidato.alocacao() for candidato, variavel in escolhas if solver.boolean_value(variavel)
        )
    fontes = _linhas_por_encontro(ocupacao)

    excecoes: dict[str, str] = {}
    excecoes_detalhadas, alteracoes = [], []
    originais = {}
    for encontro in ocupacao.encontros_fisicos:
        encontro_id = encontro.id
        original = {campo: encontro.atributos_fisicos[campo] for campo in CAMPOS_POSICAO}
        originais[encontro_id] = original
        proposta = alocacoes[encontro_id]
        cursos = {registro["curso"] for registro in fontes[encontro_id]}
        inicio, fim = _minutos(proposta["hora_inicio"]), _minutos(proposta["hora_fim"])
        fora = fim - inicio - _minutos_alvo(cursos, inicio, fim)
        if not cursos.isdisjoint(TURNOS_ALVO_TEXTO) and fora > 0:
            motivo = (
                "Encontro fixado por conflito já existente no baseline."
                if encontro_id in fixados else
                "Turno-alvo não obtido sem violar restrições duras (docente, sala, etapa, laboratório ou capacidade)."
            )
            excecoes[encontro_id] = motivo
            excecoes_detalhadas.append({
                "encontro_id": encontro_id,
                "cursos": sorted(cursos),
                "codigo_disciplina": encontro.atributos_fisicos["codigo_disciplina"],
                "turno_alvo": sorted({TURNOS_ALVO_TEXTO[c] for c in cursos if c in TURNOS_ALVO_TEXTO}),
                "turno_obtido": "/".join(_horas_turno(inicio, fim)) or "Fora dos turnos",
                "alocacao": proposta,
                "minutos_fora_do_alvo": fora,
                "motivo": motivo,
            })
        if proposta != original:
            alteracoes.append({
                "encontro_id": encontro_id,
                "codigo_disciplina": encontro.atributos_fisicos["codigo_disciplina"],
                "original": original,
                "proposta": proposta,
                "tipo_mudanca": _tipo_mudanca(original, proposta),
            })

    diagnosticos = validar_grade(ocupacao, alocacoes, excecoes)
    bloqueantes = diagnosticos_bloqueantes(diagnosticos)
    resultado.update({
        "alocacoes": alocacoes,
        "violacoes_bloqueantes": [
            {"regra": d.regra, "mensagem": d.mensagem, "encontros": list(d.encontros)} for d in bloqueantes
        ],
        "diagnosticos": [
            {"regra": d.regra, "severidade": d.severidade, "mensagem": d.mensagem, "encontros": list(d.encontros)}
            for d in diagnosticos
        ],
        "metricas": {
            "carga_turno_alvo_original": carga_turno_alvo(ocupacao, originais),
            "carga_turno_alvo_proposta": carga_turno_alvo(ocupacao, alocacoes),
            "encontros_alterados": len(alteracoes),
            "etapas_toleradas_baseline": [list(chave) for chave in sorted(toleradas)],
        },
        "alteracoes": alteracoes,
        "excecoes_turno": excecoes,
        "excecoes_detalhadas": excecoes_detalhadas,
    })
    return resultado


def exportar_solucao_c(
    ocupacao: ModeloOcupacao, resultado: dict[str, Any], arquivo_fonte: Path, pasta_saida: Path
) -> dict[str, Path]:
    if resultado["violacoes_bloqueantes"]:
        raise ValueError("Solução C contém violações invioláveis; arquivos não foram exportados.")
    pasta_saida.mkdir(parents=True, exist_ok=True)
    otimo = resultado["status_codigo"] == cp_model.OPTIMAL
    prefixo = "solucao_C" if otimo else "candidato_C"
    caminhos = {ext: pasta_saida / f"{prefixo}.{ext}" for ext in ("csv", "json", "md")}
    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}

    linhas_saida = []
    for linha in ocupacao.linhas_fonte:
        valores = dict(linha["valores"])
        encontro_id = linha["evento_fisico_id"]
        atributos = encontros[encontro_id].atributos_fisicos
        original = {campo: atributos[campo] for campo in CAMPOS_POSICAO}
        proposta = resultado["alocacoes"][encontro_id]
        mudou = proposta != original
        valores.update({campo: proposta[campo] for campo in CAMPOS_POSICAO})
        valores.update({
            "encontro_id": encontro_id,
            "solucao": "C",
            "status_solver": resultado["solver"]["status"],
            "alterado": "sim" if mudou else "nao",
            "turno_original": "/".join(_horas_turno(_minutos(original["hora_inicio"]), _minutos(original["hora_fim"]))) or "Fora dos turnos",
            "turno_alvo": TURNOS_ALVO_TEXTO.get(valores["curso"], ""),
            "turno_proposto": "/".join(_horas_turno(_minutos(proposta["hora_inicio"]), _minutos(proposta["hora_fim"]))) or "Fora dos turnos",
            "motivo_alteracao": "Maximização da carga horária no turno-alvo." if mudou else "",
            "excecao_turno": resultado["excecoes_turno"].get(encontro_id, ""),
            "tipo_mudanca": _tipo_mudanca(original, proposta),
        })
        linhas_saida.append(valores)
    with caminhos["csv"].open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=[*ocupacao.cabecalho, *CAMPOS_EXPORTADOS])
        escritor.writeheader()
        escritor.writerows(linhas_saida)

    metadata = {
        "solucao": "C",
        "situacao": "final" if otimo else "candidata_provisoria",
        "arquivo_fonte": arquivo_fonte.name,
        "sha256_fonte": hashlib.sha256(arquivo_fonte.read_bytes()).hexdigest(),
        "status_solver": resultado["solver"],
        "criterio": (
            "Minimizar minutos fora do turno-alvo; em empate, preferir início da noite "
            f"(penaliza início após {INICIO_NOITE // 60}:{INICIO_NOITE % 60:02d}); depois, minimizar encontros alterados."
        ),
        "metricas": resultado["metricas"],
        "alteracoes": resultado["alteracoes"],
        "excecoes_turno": resultado["excecoes_detalhadas"],
        "diagnosticos": resultado["diagnosticos"],
        "violacoes_bloqueantes": resultado["violacoes_bloqueantes"],
    }
    caminhos["json"].write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    metricas = resultado["metricas"]
    texto = [
        "# Solução C — maximização de turnos",
        "",
        f"- Situação: `{metadata['situacao']}`; status CP-SAT: `{resultado['solver']['status']}`.",
        f"- Encontros alterados: {metricas['encontros_alterados']}.",
        f"- Exceções de turno: {len(resultado['excecoes_detalhadas'])}.",
        f"- Tempo: {resultado['solver']['tempo_segundos']:.2f}s de {resultado['solver']['limite_segundos']:.2f}s.",
        "",
        "## CH no turno-alvo (horas semanais)",
        "",
        "| Curso | Original | % original | Proposta C | % proposta |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for curso, antes in metricas["carga_turno_alvo_original"].items():
        depois = metricas["carga_turno_alvo_proposta"][curso]
        texto.append(
            f"| {curso} | {antes['ch_no_alvo_horas']:.2f} | {antes['percentual_no_alvo']:.2f} "
            f"| {depois['ch_no_alvo_horas']:.2f} | {depois['percentual_no_alvo']:.2f} |"
        )
    texto.extend(["", f"Exceções e alterações detalhadas: `{caminhos['json'].name}`.", ""])
    caminhos["md"].write_text("\n".join(texto), encoding="utf-8")
    return caminhos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=Path(__file__).with_name("mapa_salas_tidy_03.csv"))
    parser.add_argument("--saida-dir", type=Path, default=Path(__file__).with_name("saida_solucao_C"))
    parser.add_argument("--limite-segundos", type=float, default=300.0)
    args = parser.parse_args()
    ocupacao = carregar_modelo(args.entrada)
    resultado = calcular_solucao_c(ocupacao, args.limite_segundos)
    args.saida_dir.mkdir(parents=True, exist_ok=True)
    status = {
        "entrada": args.entrada.name,
        "status_solver": resultado["solver"]["status"],
        "solucao_encontrada": bool(resultado["alocacoes"]),
        "limite_segundos": args.limite_segundos,
        "violacoes_bloqueantes": resultado["violacoes_bloqueantes"],
    }
    (args.saida_dir / "status_execucao_C.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if resultado["status_codigo"] not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 2
    if resultado["violacoes_bloqueantes"]:
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 3
    arquivos = exportar_solucao_c(ocupacao, resultado, args.entrada, args.saida_dir)
    print(json.dumps({"status": status, "solver": resultado["solver"],
                      "arquivos": {nome: str(caminho) for nome, caminho in arquivos.items()}},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
