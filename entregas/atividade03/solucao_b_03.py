"""Execução reproduzível da proposta B (equilíbrio semanal)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from candidatos_03 import alocacoes_fixos, gerar_candidatos
from modelo_ocupacao_03 import ModeloOcupacao, carregar_modelo
from modelo_otimizacao_03 import (
    construir_modelo_cp_sat,
    fixados_baseline,
    resolver_solucao_b,
)
from restricoes_03 import (
    DIAS_VALIDOS,
    _minutos,
    diagnosticos_bloqueantes,
    secoes_por_etapa,
    validar_grade,
)
from solucao_a_03 import (
    CAMPOS_EXPORTADOS,
    CAMPOS_POSICAO,
    TURNOS_ALVO_TEXTO,
    _horas_turno,
    _minutos_alvo,
    _tipo_mudanca,
)
from ortools.sat.python import cp_model


def metricas_equilibrio(
    ocupacao: ModeloOcupacao,
    alocacoes: dict[str, dict[str, str]],
    etapas_escolhidas: dict[tuple[str, str, str], tuple[str, ...]],
) -> dict[str, Any]:
    """Recalcula a carga semanal de etapas escolhidas e docentes a partir da grade."""

    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}
    fontes_por_etapa = secoes_por_etapa(ocupacao)
    cargas_etapa: dict[tuple[str, str, str], dict[str, float]] = {}
    for chave, selecoes in etapas_escolhidas.items():
        cargas = {dia: 0.0 for dia in sorted(DIAS_VALIDOS)}
        for selecao in selecoes:
            codigo, turma = selecao.split(":", 1)
            ids = fontes_por_etapa[chave][codigo][turma]
            for encontro_id in ids:
                posicao = alocacoes[encontro_id]
                duracao = _minutos(posicao["hora_fim"]) - _minutos(posicao["hora_inicio"])
                dia = posicao["dia_semana"].strip().upper()
                cargas[dia] += duracao / 60
        cargas_etapa[chave] = cargas

    docentes_por_encontro: dict[str, set[str]] = defaultdict(set)
    for atribuicao in ocupacao.atribuicoes_docentes:
        docentes_por_encontro[atribuicao.evento_fisico_id].add(atribuicao.docente)
    cargas_docente: dict[str, dict[str, float]] = {}
    for encontro_id, docentes in docentes_por_encontro.items():
        posicao = alocacoes[encontro_id]
        dia = posicao["dia_semana"].strip().upper()
        duracao = (_minutos(posicao["hora_fim"]) - _minutos(posicao["hora_inicio"])) / 60
        for docente in docentes:
            cargas = cargas_docente.setdefault(docente, {d: 0.0 for d in sorted(DIAS_VALIDOS)})
            cargas[dia] += duracao

    def resumir(grupos: dict[Any, dict[str, float]]) -> dict[str, Any]:
        detalhes = []
        for identificador, cargas in sorted(grupos.items(), key=lambda item: str(item[0])):
            total = sum(cargas.values())
            media = total / len(cargas) if cargas else 0.0
            desvios = [abs(carga - media) for carga in cargas.values()]
            detalhes.append({
                "grupo": list(identificador) if isinstance(identificador, tuple) else identificador,
                "carga_diaria_horas": {dia: round(carga, 2) for dia, carga in cargas.items()},
                "desvio_absoluto_medio_diario_horas": round(sum(desvios) / len(desvios), 3) if desvios else 0.0,
                "amplitude_diaria_horas": round(max(cargas.values()) - min(cargas.values()), 2) if cargas else 0.0,
            })
        return {
            "grupos": detalhes,
            "quantidade_grupos": len(detalhes),
            "desvio_absoluto_medio_diario_horas": round(
                sum(item["desvio_absoluto_medio_diario_horas"] for item in detalhes) / len(detalhes), 3
            ) if detalhes else 0.0,
        }

    return {"etapas_obrigatorias": resumir(cargas_etapa), "docentes": resumir(cargas_docente)}


def calcular_solucao_b(
    ocupacao: ModeloOcupacao,
    limite_segundos: float = 300.0,
    usar_grade_horaria_meia_hora: bool = True,
) -> dict[str, Any]:
    """Resolve B mantendo conflitos de baseline fixos e validando a proposta."""

    fixados, toleradas = fixados_baseline(ocupacao, fixar_todos=False)
    dominios = gerar_candidatos(
        ocupacao,
        usar_grade_horaria_meia_hora=usar_grade_horaria_meia_hora,
        fixados=fixados,
    )
    if any(not candidatos for candidatos in dominios.values()):
        raise ValueError("Há encontros móveis sem candidatos; a Solução B não pode ser construída.")
    modelagem = construir_modelo_cp_sat(ocupacao, dominios, fixados, toleradas)
    status, escolhidos, etapas_escolhidas, detalhes_solver = resolver_solucao_b(
        ocupacao, modelagem, fixados, limite_segundos
    )
    resultado: dict[str, Any] = {
        "status_codigo": status,
        "solver": detalhes_solver,
        "fixados": sorted(fixados),
        "alocacoes": {},
        "etapas_escolhidas": etapas_escolhidas,
        "diagnosticos": [],
        "violacoes_bloqueantes": [],
        "metricas": {},
        "alteracoes": [],
        "excecoes_turno": {},
        "excecoes_detalhadas": [],
    }
    if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return resultado

    alocacoes = alocacoes_fixos(ocupacao, fixados)
    alocacoes.update({encontro_id: candidato.alocacao() for encontro_id, candidato in escolhidos.items()})
    fontes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for linha in ocupacao.linhas_fonte:
        fontes[linha["evento_fisico_id"]].append(linha["valores"])

    excecoes: dict[str, str] = {}
    excecoes_detalhadas = []
    alteracoes = []
    for encontro in ocupacao.encontros_fisicos:
        encontro_id = encontro.id
        original = {campo: encontro.atributos_fisicos[campo] for campo in CAMPOS_POSICAO}
        proposta = alocacoes[encontro_id]
        cursos = {registro["curso"] for registro in fontes[encontro_id]}
        inicio = _minutos(proposta["hora_inicio"])
        fim = _minutos(proposta["hora_fim"])
        minutos_fora = fim - inicio - _minutos_alvo(cursos, inicio, fim)
        if not cursos.isdisjoint(TURNOS_ALVO_TEXTO) and minutos_fora > 0:
            justificativa = "Exceção de turno registrada pela otimização global de equilíbrio da Solução B."
            excecoes[encontro_id] = justificativa
            excecoes_detalhadas.append({
                "encontro_id": encontro_id,
                "cursos": sorted(cursos),
                "codigo_disciplina": encontro.atributos_fisicos["codigo_disciplina"],
                "alocacao": proposta,
                "minutos_fora_do_alvo": minutos_fora,
                "justificativa": justificativa,
            })
        if proposta != original:
            alteracoes.append({
                "encontro_id": encontro_id,
                "codigo_disciplina": encontro.atributos_fisicos["codigo_disciplina"],
                "turmas_compartilhando_sala": encontro.atributos_fisicos["turmas_compartilhando_sala"],
                "original": original,
                "proposta": proposta,
                "tipo_mudanca": _tipo_mudanca(original, proposta),
            })

    diagnosticos = validar_grade(ocupacao, alocacoes, excecoes)
    bloqueantes = diagnosticos_bloqueantes(diagnosticos)
    metricas = {
        "equilibrio_proposto": metricas_equilibrio(ocupacao, alocacoes, etapas_escolhidas),
        "equilibrio_grade_original_mesmas_turmas": metricas_equilibrio(
            ocupacao,
            {
                encontro.id: {campo: encontro.atributos_fisicos[campo] for campo in CAMPOS_POSICAO}
                for encontro in ocupacao.encontros_fisicos
            },
            etapas_escolhidas,
        ),
        "encontros_alterados": len(alteracoes),
        "mudancas_por_tipo": {
            tipo: sum(tipo in item["tipo_mudanca"].split("+") for item in alteracoes)
            for tipo in ("sala", "dia", "horario")
        },
        "etapas_toleradas_baseline": [list(chave) for chave in sorted(toleradas)],
    }
    resultado.update({
        "alocacoes": alocacoes,
        "diagnosticos": [
            {"regra": item.regra, "severidade": item.severidade,
             "mensagem": item.mensagem, "encontros": list(item.encontros)}
            for item in diagnosticos
        ],
        "violacoes_bloqueantes": [
            {"regra": item.regra, "mensagem": item.mensagem, "encontros": list(item.encontros)}
            for item in bloqueantes
        ],
        "metricas": metricas,
        "alteracoes": alteracoes,
        "excecoes_turno": excecoes,
        "excecoes_detalhadas": excecoes_detalhadas,
    })
    return resultado


def exportar_solucao_b(
    ocupacao: ModeloOcupacao,
    resultado: dict[str, Any],
    arquivo_fonte: Path,
    pasta_saida: Path,
) -> dict[str, Path]:
    """Exporta B ou sua candidata provisória sem violações duras novas."""

    if resultado["status_codigo"] not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        raise ValueError(f"Sem alocação exportável: {resultado['solver']['status']}.")
    if resultado["violacoes_bloqueantes"]:
        raise ValueError("Solução B contém violações invioláveis; arquivos não foram exportados.")
    pasta_saida.mkdir(parents=True, exist_ok=True)
    otimo_provado = resultado["status_codigo"] == cp_model.OPTIMAL
    prefixo = "solucao_B" if otimo_provado else "candidato_B"
    situacao = "final" if otimo_provado else "candidata_provisoria"
    caminhos = {
        "csv": pasta_saida / f"{prefixo}.csv",
        "json": pasta_saida / f"{prefixo}.json",
        "markdown": pasta_saida / f"{prefixo}.md",
    }
    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}
    linhas_saida = []
    for linha in ocupacao.linhas_fonte:
        valores = dict(linha["valores"])
        encontro_id = linha["evento_fisico_id"]
        encontro = encontros[encontro_id]
        original = {campo: encontro.atributos_fisicos[campo] for campo in CAMPOS_POSICAO}
        proposta = resultado["alocacoes"][encontro_id]
        mudou = proposta != original
        inicio_original, fim_original = _minutos(original["hora_inicio"]), _minutos(original["hora_fim"])
        inicio_proposto, fim_proposto = _minutos(proposta["hora_inicio"]), _minutos(proposta["hora_fim"])
        valores.update({campo: proposta[campo] for campo in CAMPOS_POSICAO})
        valores.update({
            "encontro_id": encontro_id,
            "solucao": "B",
            "status_solver": resultado["solver"]["status"],
            "alterado": "sim" if mudou else "nao",
            "turno_original": "/".join(_horas_turno(inicio_original, fim_original)) or "Fora dos turnos",
            "turno_alvo": TURNOS_ALVO_TEXTO.get(valores["curso"], ""),
            "turno_proposto": "/".join(_horas_turno(inicio_proposto, fim_proposto)) or "Fora dos turnos",
            "motivo_alteracao": "Reequilíbrio semanal de etapas obrigatórias e docentes." if mudou else "",
            "excecao_turno": resultado["excecoes_turno"].get(encontro_id, ""),
            "tipo_mudanca": _tipo_mudanca(original, proposta),
        })
        linhas_saida.append(valores)
    with caminhos["csv"].open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=[*ocupacao.cabecalho, *CAMPOS_EXPORTADOS])
        escritor.writeheader()
        escritor.writerows(linhas_saida)

    selecoes_json = {"/".join(chave): list(selecoes)
                     for chave, selecoes in resultado["etapas_escolhidas"].items()}
    metadata = {
        "solucao": "B",
        "situacao": situacao,
        "observacao_status": (
            "Ótimo do objetivo de equilíbrio provado pelo CP-SAT."
            if otimo_provado else
            "FEASIBLE: solução viável encontrada, mas não prova o ótimo de equilíbrio; candidata provisória."
        ),
        "arquivo_csv": caminhos["csv"].name,
        "arquivo_fonte": arquivo_fonte.name,
        "sha256_fonte": hashlib.sha256(arquivo_fonte.read_bytes()).hexdigest(),
        "linhas_fonte": len(ocupacao.linhas_fonte),
        "encontros_fisicos": len(ocupacao.encontros_fisicos),
        "status_solver": resultado["solver"],
        "criterio": (
            "Minimizar igualmente a dispersão absoluta média diária das etapas obrigatórias e dos docentes; "
            "em empate, minimizar o número de encontros alterados. Sem teto diário fixo."
        ),
        "turmas_escolhidas_por_etapa": selecoes_json,
        "metricas": resultado["metricas"],
        "alteracoes": resultado["alteracoes"],
        "excecoes_turno": resultado["excecoes_detalhadas"],
        "diagnosticos": resultado["diagnosticos"],
        "violacoes_bloqueantes": resultado["violacoes_bloqueantes"],
    }
    caminhos["json"].write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metricas = metadata["metricas"]
    texto = [
        "# Solução B — equilíbrio semanal",
        "",
        f"- Situação: `{situacao}`. {metadata['observacao_status']}",
        f"- Status CP-SAT: `{resultado['solver']['status']}`.",
        f"- Fonte: `{metadata['arquivo_fonte']}` (SHA-256 `{metadata['sha256_fonte']}`).",
        f"- Encontros alterados: {metricas['encontros_alterados']}.",
        f"- Tempo: {resultado['solver']['tempo_segundos']:.2f}s de {resultado['solver']['limite_segundos']:.2f}s.",
        f"- Violações duras novas: {len(resultado['violacoes_bloqueantes'])}.",
        "",
        "## Equilíbrio semanal",
        "",
        "Desvio absoluto médio diário por grupo, em horas; menor indica distribuição mais uniforme entre os cinco dias.",
        "",
        "| Métrica | Grade original, mesmas turmas escolhidas | Proposta B |",
        "| --- | ---: | ---: |",
    ]
    for grupo, chave in (("Etapas obrigatórias", "etapas_obrigatorias"), ("Docentes", "docentes")):
        original = metricas["equilibrio_grade_original_mesmas_turmas"][chave]["desvio_absoluto_medio_diario_horas"]
        proposta = metricas["equilibrio_proposto"][chave]["desvio_absoluto_medio_diario_horas"]
        texto.append(f"| {grupo} | {original:.3f} | {proposta:.3f} |")
    texto.extend(["", f"Detalhes e turmas escolhidas: `{caminhos['json'].name}`.", "CSV-fonte preservado.", ""])
    caminhos["markdown"].write_text("\n".join(texto), encoding="utf-8")
    return caminhos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=Path(__file__).with_name("mapa_salas_tidy_03.csv"))
    parser.add_argument("--saida-dir", type=Path, default=Path(__file__).with_name("saida_solucao_B"))
    parser.add_argument("--limite-segundos", type=float, default=3000.0)
    args = parser.parse_args()
    ocupacao = carregar_modelo(args.entrada)
    resultado = calcular_solucao_b(ocupacao, args.limite_segundos)
    args.saida_dir.mkdir(parents=True, exist_ok=True)
    status = {
        "entrada": args.entrada.name,
        "sha256_fonte": hashlib.sha256(args.entrada.read_bytes()).hexdigest(),
        "status_solver": resultado["solver"]["status"],
        "status_codigo": int(resultado["status_codigo"]),
        "politica_inicios": "horaria_meia_hora_limites_fonte",
        "solucao_encontrada": bool(resultado["alocacoes"]),
        "limite_segundos": args.limite_segundos,
        "violacoes_bloqueantes": resultado["violacoes_bloqueantes"],
    }
    caminho_status = args.saida_dir / "status_execucao_B.json"
    caminho_status.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if resultado["status_codigo"] not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        print(json.dumps({**status, "arquivo_status": str(caminho_status)}, ensure_ascii=False, indent=2))
        return 2
    if resultado["violacoes_bloqueantes"]:
        print(json.dumps({**status, "arquivo_status": str(caminho_status)}, ensure_ascii=False, indent=2))
        return 3
    arquivos = exportar_solucao_b(ocupacao, resultado, args.entrada, args.saida_dir)
    print(json.dumps({"status": status, "arquivo_status": str(caminho_status),
                      "solver": resultado["solver"],
                      "arquivos": {nome: str(caminho) for nome, caminho in arquivos.items()}},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())