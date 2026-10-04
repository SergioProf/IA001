"""Execução reproduzível da proposta A (preservação)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import tracemalloc
from pathlib import Path
from typing import Any

from candidatos_03 import alocacoes_fixos, gerar_candidatos, resumir_dominios
from modelo_ocupacao_03 import ModeloOcupacao, carregar_modelo
from modelo_otimizacao_03 import (
    adicionar_objetivo_solucao_a,
    construir_modelo_cp_sat,
    resolver_solucao_a,
)
from restricoes_03 import (
    TURNOS_ALVO,
    _minutos,
    classificar_preservacao,
    diagnosticos_bloqueantes,
    metricas_preferencia,
    validar_grade,
)
from ortools.sat.python import cp_model


JANELAS_TURNO = {"Manhã": (0, 750), "Tarde": (810, 1110), "Noite": (1110, 1440)}
CAMPOS_POSICAO = ("predio", "sala", "dia_semana", "hora_inicio", "hora_fim")
CAMPOS_EXPORTADOS = (
    "encontro_id",
    "solucao",
    "alterado",
    "turno_original",
    "turno_alvo",
    "turno_proposto",
    "motivo_alteracao",
    "excecao_turno",
    "tipo_mudanca",
    "status_solver",
)
TURNOS_ALVO_TEXTO = {"ARQU": "Manhã/Noite", "DPRO": "Tarde/Noite", "DVIS": "Tarde/Noite"}


def _janelas_unidas(janelas: list[tuple[int, int]]) -> list[tuple[int, int]]:
    unidas: list[list[int]] = []
    for inicio, fim in sorted(janelas):
        if unidas and inicio <= unidas[-1][1]:
            unidas[-1][1] = max(unidas[-1][1], fim)
        else:
            unidas.append([inicio, fim])
    return [(inicio, fim) for inicio, fim in unidas]


def _horas_turno(inicio: int, fim: int) -> list[str]:
    return [
        turno for turno, (limite_inicio, limite_fim) in JANELAS_TURNO.items()
        if max(0, min(fim, limite_fim) - max(inicio, limite_inicio)) > 0
    ]


def _minutos_alvo(cursos: set[str], inicio: int, fim: int) -> int:
    janelas = _janelas_unidas([
        janela for curso in cursos for janela in TURNOS_ALVO.get(curso, ())
    ])
    return sum(max(0, min(fim, limite_fim) - max(inicio, limite_inicio))
               for limite_inicio, limite_fim in janelas)


def _tipo_mudanca(original: dict[str, str], proposta: dict[str, str]) -> str:
    mudou_sala = (original["predio"], original["sala"]) != (proposta["predio"], proposta["sala"])
    mudou_dia = original["dia_semana"] != proposta["dia_semana"]
    mudou_horario = (original["hora_inicio"], original["hora_fim"]) != (
        proposta["hora_inicio"], proposta["hora_fim"]
    )
    mudancas = [
        nome for nome, mudou in (("sala", mudou_sala), ("dia", mudou_dia), ("horario", mudou_horario))
        if mudou
    ]
    return "+".join(mudancas) if mudancas else "sem_alteracao"


def preflight_solucao_a(
    caminho_csv: Path,
    usar_grade_horaria_meia_hora: bool = False,
) -> dict[str, Any]:
    """Valida dimensões e construção do modelo sem iniciar a busca CP-SAT."""

    caminho_csv = Path(caminho_csv)
    hash_inicial = hashlib.sha256(caminho_csv.read_bytes()).hexdigest()
    rastreamento_proprio = not tracemalloc.is_tracing()
    if rastreamento_proprio:
        tracemalloc.start()

    inicio_total = time.perf_counter()
    try:
        inicio = time.perf_counter()
        ocupacao = carregar_modelo(caminho_csv)
        tempo_carga = time.perf_counter() - inicio

        inicio = time.perf_counter()
        dominios = gerar_candidatos(
            ocupacao,
            usar_grade_horaria_meia_hora=usar_grade_horaria_meia_hora,
        )
        tempo_dominios = time.perf_counter() - inicio

        inicio = time.perf_counter()
        modelagem = construir_modelo_cp_sat(ocupacao, dominios)
        adicionar_objetivo_solucao_a(ocupacao, modelagem)
        validacao = modelagem.modelo.validate()
        tempo_modelo = time.perf_counter() - inicio
        tempo_total = time.perf_counter() - inicio_total
        _, pico_python_bytes = tracemalloc.get_traced_memory()
    finally:
        if rastreamento_proprio:
            tracemalloc.stop()

    hash_final = hashlib.sha256(caminho_csv.read_bytes()).hexdigest()
    resumo_dominios = resumir_dominios(dominios)
    modelo_valido = not validacao and resumo_dominios["dominios_vazios"] == 0
    return {
        "entrada": caminho_csv.name,
        "politica_inicios": "horaria_meia_hora_limites_fonte" if usar_grade_horaria_meia_hora else "pares_observados",
        "sha256_fonte": hash_inicial,
        "sha256_fonte_inalterado": hash_inicial == hash_final,
        "resumo_ocupacao": ocupacao.resumo(),
        "dominios": resumo_dominios,
        "modelo": {
            "status": "VALIDO" if modelo_valido else "INVALIDO",
            "mensagem_validacao": validacao or None,
            "intervalo_minutos": modelagem.intervalo_minutos,
            "variaveis": len(modelagem.modelo.proto.variables),
            "restricoes": len(modelagem.modelo.proto.constraints),
        },
        "tempos_segundos": {
            "carga_normalizacao": round(tempo_carga, 3),
            "geracao_dominios": round(tempo_dominios, 3),
            "construcao_modelo": round(tempo_modelo, 3),
            "total": round(tempo_total, 3),
        },
        "memoria": {
            "pico_python_bytes": pico_python_bytes if rastreamento_proprio else None,
            "observacao": "Pico de alocações Python via tracemalloc; não inclui memória nativa do OR-Tools.",
        },
        "solver_executado": False,
    }


def calcular_solucao_a(
    ocupacao: ModeloOcupacao,
    limite_segundos: float = 300.0,
    usar_grade_horaria_meia_hora: bool = False,
) -> dict[str, Any]:
    """Resolve e valida A; nenhum arquivo é escrito por esta função."""

    dominios = gerar_candidatos(
        ocupacao,
        usar_grade_horaria_meia_hora=usar_grade_horaria_meia_hora,
    )
    modelagem = construir_modelo_cp_sat(ocupacao, dominios)
    status, escolhidos, detalhes_solver = resolver_solucao_a(
        ocupacao, modelagem, limite_segundos
    )
    resultado: dict[str, Any] = {
        "status_codigo": status,
        "solver": detalhes_solver,
        "alocacoes": {},
        "excecoes_turno": {},
        "diagnosticos": [],
        "metricas": {},
        "alteracoes": [],
    }
    if status not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return resultado

    alocacoes = alocacoes_fixos(ocupacao)
    alocacoes.update({encontro_id: candidato.alocacao() for encontro_id, candidato in escolhidos.items()})
    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}
    fontes: dict[str, list[dict[str, Any]]] = {}
    for linha in ocupacao.linhas_fonte:
        fontes.setdefault(linha["evento_fisico_id"], []).append(linha["valores"])

    excecoes: dict[str, str] = {}
    relatorio_excecoes = []
    for encontro_id, encontro in encontros.items():
        cursos = {registro["curso"] for registro in fontes[encontro_id]}
        if cursos.isdisjoint(TURNOS_ALVO):
            continue
        posicao = alocacoes[encontro_id]
        inicio, fim = _minutos(posicao["hora_inicio"]), _minutos(posicao["hora_fim"])
        fora_alvo = fim - inicio - _minutos_alvo(cursos, inicio, fim)
        if fora_alvo <= 0:
            continue
        original = encontro.atributos_fisicos
        inalterado = all(posicao[campo] == original[campo] for campo in CAMPOS_POSICAO)
        justificativa = (
            "Posição fora do turno-alvo já existente na fonte, mantida pela prioridade de preservação da Solução A."
            if inalterado else
            "Exceção de turno registrada; a prioridade lexicográfica de preservação da Solução A foi aplicada globalmente."
        )
        excecoes[encontro_id] = justificativa
        relatorio_excecoes.append({
            "encontro_id": encontro_id,
            "cursos": sorted(cursos),
            "codigo_disciplina": original["codigo_disciplina"],
            "turmas_compartilhando_sala": original["turmas_compartilhando_sala"],
            "turnos_alvo": sorted({TURNOS_ALVO_TEXTO[curso] for curso in cursos if curso in TURNOS_ALVO_TEXTO}),
            "alocacao": {campo: posicao[campo] for campo in CAMPOS_POSICAO},
            "minutos_fora_do_alvo": fora_alvo,
            "justificativa": justificativa,
            "restricao_impeditiva": "Não inferida individualmente pelo CP-SAT; a solução A otimiza preservação global e registra o relaxamento.",
        })

    diagnosticos = validar_grade(ocupacao, alocacoes, excecoes)
    bloqueantes = diagnosticos_bloqueantes(diagnosticos)
    metricas = metricas_preferencia(ocupacao, alocacoes)
    alteracoes = []
    niveis = classificar_preservacao(ocupacao, alocacoes)
    for encontro_id, encontro in encontros.items():
        original = {campo: encontro.atributos_fisicos[campo] for campo in CAMPOS_POSICAO}
        proposta = alocacoes[encontro_id]
        if proposta != original:
            alteracoes.append({
                "encontro_id": encontro_id,
                "codigo_disciplina": encontro.atributos_fisicos["codigo_disciplina"],
                "turmas_compartilhando_sala": encontro.atributos_fisicos["turmas_compartilhando_sala"],
                "original": original,
                "proposta": proposta,
                "nivel_preservacao": niveis[encontro_id],
                "tipo_mudanca": _tipo_mudanca(original, proposta),
            })

    resultado.update({
        "alocacoes": alocacoes,
        "excecoes_turno": excecoes,
        "excecoes_detalhadas": relatorio_excecoes,
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
    })
    return resultado


def exportar_solucao_a(
    ocupacao: ModeloOcupacao,
    resultado: dict[str, Any],
    arquivo_fonte: Path,
    pasta_saida: Path,
) -> dict[str, Path]:
    """Exporta A ou uma candidata provisória sem violação dura nova."""

    if resultado["status_codigo"] not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        raise ValueError(f"Sem alocação exportável: {resultado['solver']['status']}.")
    if resultado["violacoes_bloqueantes"]:
        raise ValueError("Solução A contém violações invioláveis; arquivos não foram exportados.")

    pasta_saida.mkdir(parents=True, exist_ok=True)
    otimo_provado = resultado["status_codigo"] == cp_model.OPTIMAL
    prefixo = "solucao_A" if otimo_provado else "candidato_A"
    situacao = "final" if otimo_provado else "candidata_provisoria"
    caminho_csv = pasta_saida / f"{prefixo}.csv"
    caminho_json = pasta_saida / f"{prefixo}.json"
    caminho_md = pasta_saida / f"{prefixo}.md"
    encontros = {encontro.id: encontro for encontro in ocupacao.encontros_fisicos}
    niveis = classificar_preservacao(ocupacao, resultado["alocacoes"])
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
        curso = valores["curso"]
        alvo = TURNOS_ALVO_TEXTO.get(curso, "")
        justificativa = resultado["excecoes_turno"].get(encontro_id, "")
        valores.update({campo: proposta[campo] for campo in CAMPOS_POSICAO})
        valores.update({
            "encontro_id": encontro_id,
            "solucao": "A",
            "status_solver": resultado["solver"]["status"],
            "alterado": "sim" if mudou else "nao",
            "turno_original": "/".join(_horas_turno(inicio_original, fim_original)) or "Fora dos turnos",
            "turno_alvo": alvo,
            "turno_proposto": "/".join(_horas_turno(inicio_proposto, fim_proposto)) or "Fora dos turnos",
            "motivo_alteracao": (
                f"Ajuste global por restrições invioláveis; nível de preservação {niveis[encontro_id]}."
                if mudou else ""
            ),
            "excecao_turno": justificativa,
            "tipo_mudanca": _tipo_mudanca(original, proposta),
        })
        linhas_saida.append(valores)

    with caminho_csv.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=[*ocupacao.cabecalho, *CAMPOS_EXPORTADOS])
        escritor.writeheader()
        escritor.writerows(linhas_saida)

    metadata = {
        "solucao": "A",
        "situacao": situacao,
        "observacao_status": (
            "Ótimo lexicográfico provado pelo CP-SAT."
            if otimo_provado else
            "FEASIBLE: solução viável encontrada, mas não prova o ótimo lexicográfico; candidata provisória."
        ),
        "arquivo_json": caminho_json.name,
        "arquivo_fonte": arquivo_fonte.name,
        "sha256_fonte": hashlib.sha256(arquivo_fonte.read_bytes()).hexdigest(),
        "linhas_fonte": len(ocupacao.linhas_fonte),
        "encontros_fisicos": len(ocupacao.encontros_fisicos),
        "encontros_moveis": len(resultado["alocacoes"]) - len(alocacoes_fixos(ocupacao)),
        "solver": resultado["solver"],
        "criterio": "Maximização lexicográfica dos níveis de preservação 1 a 5; prioridades de turma e preferências de espaço são desempates.",
        "metricas": resultado["metricas"],
        "quantidade_encontros_alterados": len(resultado["alteracoes"]),
        "alteracoes": resultado["alteracoes"],
        "excecoes_turno": resultado["excecoes_detalhadas"],
        "diagnosticos": resultado["diagnosticos"],
        "violacoes_bloqueantes": resultado["violacoes_bloqueantes"],
    }
    caminho_json.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    caminho_md.write_text(_relatorio_markdown(metadata), encoding="utf-8")
    return {"csv": caminho_csv, "json": caminho_json, "markdown": caminho_md}


def _relatorio_markdown(metadata: dict[str, Any]) -> str:
    metricas = metadata["metricas"]
    contagens = metricas["contagem_niveis_preservacao"]
    linhas = [
        (
            "# Solução A — preservação"
            if metadata["situacao"] == "final"
            else "# Candidata provisória A — preservação"
        ),
        "",
        f"- Situação: `{metadata['situacao']}`. {metadata['observacao_status']}",
        f"- Status CP-SAT: `{metadata['solver']['status']}`.",
        f"- Fonte: `{metadata['arquivo_fonte']}` (SHA-256 `{metadata['sha256_fonte']}`).",
        f"- Linhas/encontros físicos: {metadata['linhas_fonte']} / {metadata['encontros_fisicos']}.",
        f"- Encontros alterados: {metadata['quantidade_encontros_alterados']}.",
        f"- Tempo de solução: {metadata['solver']['tempo_segundos']:.2f}s; limite {metadata['solver']['limite_segundos']:.2f}s.",
        f"- Valor objetivo: {metadata['solver']['valor_objetivo']}; melhor limite: {metadata['solver']['melhor_limite']}.",
        "",
        "## Preservação",
        "",
        "| Nível | Encontros |",
        "| ---: | ---: |",
        *[f"| {nivel} | {contagens[str(nivel)] if str(nivel) in contagens else contagens[nivel]} |" for nivel in range(1, 6)],
        "",
        "Nível 1 mantém sala/dia/horário; 2 mantém dia/horário com troca de sala; 3 mantém o dia; 4 muda dias sem alterar o padrão semanal; 5 representa mudança mais ampla.",
        "",
        f"Exceções de turno registradas: {len(metadata['excecoes_turno'])}.",
        f"Violações invioláveis novas: {len(metadata['violacoes_bloqueantes'])}.",
        "",
        f"A lista detalhada de alterações, exceções, diagnósticos e metadados do solver está em `{metadata['arquivo_json']}`. O CSV-fonte não foi sobrescrito.",
        "",
    ]
    return "\n".join(linhas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=Path(__file__).with_name("mapa_salas_tidy_03.csv"))
    parser.add_argument("--saida-dir", type=Path, default=Path(__file__).parent)
    parser.add_argument("--limite-segundos", type=float, default=300.0)
    parser.add_argument("--preflight", action="store_true", help="Valida domínios e modelo sem executar o solver.")
    args = parser.parse_args()

    if args.preflight:
        relatorio = preflight_solucao_a(args.entrada, usar_grade_horaria_meia_hora=True)
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
        return 0 if relatorio["modelo"]["status"] == "VALIDO" and relatorio["sha256_fonte_inalterado"] else 4

    ocupacao = carregar_modelo(args.entrada)
    resultado = calcular_solucao_a(
        ocupacao,
        args.limite_segundos,
        usar_grade_horaria_meia_hora=True,
    )
    args.saida_dir.mkdir(parents=True, exist_ok=True)
    caminho_status = args.saida_dir / "status_execucao_A.json"
    status_execucao = {
        "entrada": args.entrada.name,
        "sha256_fonte": hashlib.sha256(args.entrada.read_bytes()).hexdigest(),
        "status_solver": resultado["solver"]["status"],
        "status_codigo": int(resultado["status_codigo"]),
        "politica_inicios": "horaria_meia_hora_limites_fonte",
        "solucao_encontrada": bool(resultado["alocacoes"]),
        "limite_segundos": args.limite_segundos,
        "violacoes_bloqueantes": resultado.get("violacoes_bloqueantes", []),
    }
    caminho_status.write_text(
        json.dumps(status_execucao, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if resultado["status_codigo"] not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        print(json.dumps({**status_execucao, "arquivo_status": str(caminho_status)}, ensure_ascii=False, indent=2))
        return 2
    if resultado["violacoes_bloqueantes"]:
        print(json.dumps({**status_execucao, "arquivo_status": str(caminho_status)}, ensure_ascii=False, indent=2))
        return 3
    arquivos = exportar_solucao_a(ocupacao, resultado, args.entrada, args.saida_dir)
    print(json.dumps({"status": status_execucao, "arquivo_status": str(caminho_status), "solver": resultado["solver"], "arquivos": {
        chave: str(caminho) for chave, caminho in arquivos.items()
    }}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())