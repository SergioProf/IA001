import csv
import tempfile
import unittest
from pathlib import Path

from candidatos_03 import Candidato
from modelo_ocupacao_03 import normalizar_registros
from modelo_otimizacao_03 import construir_modelo_cp_sat, resolver_solucao_a
from ortools.sat.python import cp_model
from solucao_a_03 import calcular_solucao_a, exportar_solucao_a
from test_restricoes_03 import CABECALHO, linha
from restricoes_03 import classificar_preservacao


def _candidato(encontro, *, sala=None, dia=None, inicio=None, fim=None):
    atributos = encontro.atributos_fisicos
    return Candidato(
        encontro.id,
        atributos["predio"],
        sala if sala is not None else atributos["sala"],
        dia if dia is not None else atributos["dia_semana"],
        inicio if inicio is not None else atributos["hora_inicio"],
        fim if fim is not None else atributos["hora_fim"],
        0,
    )


class TestSolucaoA(unittest.TestCase):
    def test_objetivo_prioriza_niveis_1_a_3_sobre_niveis_inferiores(self):
        for niveis_disponiveis, esperado in (
            ((1, 2, 3, 4, 5), 1),
            ((2, 3, 4, 5), 2),
            ((3, 4, 5), 3),
        ):
            with self.subTest(nivel_esperado=esperado):
                ocupacao = normalizar_registros(CABECALHO, [
                    linha("ARQ001", sala="S1", inicio="09:00", fim="10:00"),
                    linha("ARQ002", sala="S2", inicio="14:00", fim="15:00", docente="Prof02"),
                    linha("ARQ003", sala="S1", dia="TERÇA-FEIRA", inicio="10:00", fim="11:00", docente="Prof03"),
                ])
                encontros = {evento.atributos_fisicos["codigo_disciplina"]: evento
                             for evento in ocupacao.encontros_fisicos}
                alvo = encontros["ARQ001"]
                candidatos_por_nivel = {
                    1: _candidato(alvo),
                    2: _candidato(alvo, sala="S2"),
                    3: _candidato(alvo, inicio="10:00", fim="11:00"),
                    4: _candidato(alvo, dia="TERÇA-FEIRA"),
                    5: _candidato(alvo, dia="QUARTA-FEIRA", inicio="10:00", fim="11:00"),
                }
                dominios = {
                    evento.id: (
                        tuple(candidatos_por_nivel[nivel] for nivel in niveis_disponiveis)
                        if evento.id == alvo.id else (_candidato(evento),)
                    )
                    for evento in ocupacao.encontros_fisicos
                }

                modelagem = construir_modelo_cp_sat(ocupacao, dominios)
                status, solucao, _ = resolver_solucao_a(ocupacao, modelagem, limite_segundos=5)

                self.assertEqual(status, cp_model.OPTIMAL)
                self.assertEqual(
                    classificar_preservacao(ocupacao, {
                        encontro_id: candidato.alocacao()
                        for encontro_id, candidato in solucao.items()
                    })[alvo.id],
                    esperado,
                )

    def test_objetivo_reconhece_nivel_4_quando_preserva_padrao_semanal(self):
        ocupacao = normalizar_registros(CABECALHO, [
            linha("ARQ001", turma="A", grupo="A", dia="SEGUNDA-FEIRA", inicio="09:00", fim="10:00"),
            linha("ARQ001", turma="A", grupo="A", dia="TERÇA-FEIRA", inicio="09:00", fim="10:00"),
            linha("ARQ002", sala="S2", dia="SEXTA-FEIRA", inicio="14:00", fim="15:00", docente="Prof02"),
        ])
        encontros_padrao = [
            evento for evento in ocupacao.encontros_fisicos
            if evento.atributos_fisicos["codigo_disciplina"] == "ARQ001"
        ]
        segunda, terca = sorted(encontros_padrao, key=lambda evento: evento.atributos_fisicos["dia_semana"])
        dominios = {
            segunda.id: (
                _candidato(segunda, dia="TERÇA-FEIRA"),
                _candidato(segunda, dia="QUARTA-FEIRA"),
            ),
            terca.id: (
                _candidato(terca, dia="SEGUNDA-FEIRA"),
                _candidato(terca, dia="QUARTA-FEIRA"),
            ),
        }
        auxiliar = next(
            evento for evento in ocupacao.encontros_fisicos
            if evento.atributos_fisicos["codigo_disciplina"] == "ARQ002"
        )
        dominios[auxiliar.id] = (_candidato(auxiliar),)

        modelagem = construir_modelo_cp_sat(ocupacao, dominios)
        status, solucao, _ = resolver_solucao_a(ocupacao, modelagem, limite_segundos=5)
        niveis = classificar_preservacao(ocupacao, {
            encontro_id: candidato.alocacao()
            for encontro_id, candidato in solucao.items()
        })

        self.assertEqual(status, cp_model.OPTIMAL)
        self.assertEqual({niveis[evento.id] for evento in encontros_padrao}, {4})

    def test_desempate_preserva_turma_com_maior_prioridade(self):
        ocupacao = normalizar_registros(CABECALHO, [
            linha("ARQ001", sala="S1", vagas=30, capacidade=40, etapa="1", docente="Prof01"),
            linha("ARQ002", sala="S1", vagas=10, capacidade=40, etapa="2", docente="Prof02"),
            linha("ARQ003", sala="S2", dia="SEXTA-FEIRA", inicio="14:00", fim="15:00",
                docente="Prof03", capacidade=40),
            linha("ARQ004", sala="Lab1", tipo="Laboratório de informática", dia="QUARTA-FEIRA",
                inicio="14:00", fim="15:00", docente="Prof04", capacidade=40, etapa="4"),
        ])
        encontros = {evento.atributos_fisicos["codigo_disciplina"]: evento
                     for evento in ocupacao.encontros_fisicos}
        dominios = {}
        for codigo in ("ARQ001", "ARQ002"):
            evento = encontros[codigo]
            dominios[evento.id] = (
                _candidato(evento),
                _candidato(evento, sala="S2"),
                _candidato(evento, sala="Lab1"),
            )
        for codigo in ("ARQ003", "ARQ004"):
            evento = encontros[codigo]
            dominios[evento.id] = (_candidato(evento),)

        modelagem = construir_modelo_cp_sat(ocupacao, dominios)
        status, solucao, _ = resolver_solucao_a(ocupacao, modelagem, limite_segundos=5)

        self.assertEqual(status, cp_model.OPTIMAL)
        self.assertEqual(solucao[encontros["ARQ001"].id].sala, "S1")
        self.assertEqual(solucao[encontros["ARQ002"].id].sala, "S2")

    def test_exporta_posicao_proposta_sem_alterar_demais_colunas(self):
        registros = [
            linha("ARQ001", inicio="12:00", fim="13:00", sala="S1"),
            linha("ARQ002", inicio="09:00", fim="10:00", sala="S1", docente="Prof02"),
        ]
        ocupacao = normalizar_registros(CABECALHO, registros)
        resultado = calcular_solucao_a(ocupacao, limite_segundos=5)

        self.assertEqual(resultado["status_codigo"], cp_model.OPTIMAL)
        self.assertFalse(resultado["violacoes_bloqueantes"])
        encontro_movido = next(
            encontro for encontro in ocupacao.encontros_fisicos
            if encontro.atributos_fisicos["codigo_disciplina"] == "ARQ001"
        )
        proposta = resultado["alocacoes"][encontro_movido.id]
        self.assertNotEqual(proposta["dia_semana"], "SEGUNDA-FEIRA")

        with tempfile.TemporaryDirectory() as diretorio:
            pasta = Path(diretorio)
            fonte = pasta / "entrada.csv"
            with fonte.open("w", encoding="utf-8", newline="") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=CABECALHO)
                escritor.writeheader()
                escritor.writerows(registros)
            caminhos = exportar_solucao_a(ocupacao, resultado, fonte, pasta / "saida")

            with caminhos["csv"].open("r", encoding="utf-8-sig", newline="") as arquivo:
                exportados = list(csv.DictReader(arquivo))

        linha_movida = next(
            linha_exportada for linha_exportada in exportados
            if linha_exportada["codigo_disciplina"] == "ARQ001"
        )
        for campo in ("predio", "sala", "dia_semana", "hora_inicio", "hora_fim"):
            self.assertEqual(linha_movida[campo], proposta[campo])
        self.assertEqual(linha_movida["alterado"], "sim")
        original = next(
            encontro.atributos_fisicos for encontro in ocupacao.encontros_fisicos
            if encontro.id == encontro_movido.id
        )
        mudancas_esperadas = []
        if (original["predio"], original["sala"]) != (proposta["predio"], proposta["sala"]):
            mudancas_esperadas.append("sala")
        if original["dia_semana"] != proposta["dia_semana"]:
            mudancas_esperadas.append("dia")
        if (original["hora_inicio"], original["hora_fim"]) != (
            proposta["hora_inicio"], proposta["hora_fim"]
        ):
            mudancas_esperadas.append("horario")
        self.assertEqual(linha_movida["tipo_mudanca"], "+".join(mudancas_esperadas))
        for campo in CABECALHO:
            if campo not in {"predio", "sala", "dia_semana", "hora_inicio", "hora_fim"}:
                self.assertEqual(linha_movida[campo], registros[0][campo])

    def test_preserva_alocacao_original_e_exporta_linhagem(self):
        registro = linha("ARQ001")
        ocupacao = normalizar_registros(CABECALHO, [registro])

        resultado = calcular_solucao_a(ocupacao, limite_segundos=5)

        self.assertEqual(resultado["status_codigo"], cp_model.OPTIMAL)
        encontro = ocupacao.encontros_fisicos[0]
        self.assertEqual(resultado["alocacoes"][encontro.id], {
            "predio": registro["predio"],
            "sala": registro["sala"],
            "dia_semana": registro["dia_semana"],
            "hora_inicio": registro["hora_inicio"],
            "hora_fim": registro["hora_fim"],
        })
        self.assertFalse(resultado["violacoes_bloqueantes"])

        with tempfile.TemporaryDirectory() as diretorio:
            pasta = Path(diretorio)
            fonte = pasta / "entrada.csv"
            with fonte.open("w", encoding="utf-8", newline="") as arquivo:
                escritor = csv.DictWriter(arquivo, fieldnames=CABECALHO)
                escritor.writeheader()
                escritor.writerow(registro)
            caminhos = exportar_solucao_a(ocupacao, resultado, fonte, pasta / "saida")

            with caminhos["csv"].open("r", encoding="utf-8-sig", newline="") as arquivo:
                leitor = csv.DictReader(arquivo)
                exportado = next(leitor)
                self.assertEqual(leitor.fieldnames[:len(CABECALHO)], CABECALHO)
            for coluna in CABECALHO:
                self.assertEqual(exportado[coluna], registro[coluna])
            self.assertEqual(exportado["alterado"], "nao")
            self.assertEqual(exportado["solucao"], "A")
            self.assertEqual(exportado["turno_alvo"], "Manhã/Noite")
            self.assertTrue(caminhos["json"].is_file())
            self.assertTrue(caminhos["markdown"].is_file())


if __name__ == "__main__":
    unittest.main()