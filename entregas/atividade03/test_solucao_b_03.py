import unittest

from candidatos_03 import Candidato
from modelo_ocupacao_03 import normalizar_registros
from modelo_otimizacao_03 import construir_modelo_cp_sat, resolver_solucao_b
from ortools.sat.python import cp_model
from test_restricoes_03 import CABECALHO, linha


class TestSolucaoB(unittest.TestCase):
    def test_objetivo_distribui_etapa_e_minimiza_alteracoes_no_empate(self):
        ocupacao = normalizar_registros(CABECALHO, [
            linha("ARQ001", docente="Prof01", dia="SEGUNDA-FEIRA", inicio="09:00", fim="10:00", sala="S1"),
            linha("ARQ002", docente="Prof02", dia="SEGUNDA-FEIRA", inicio="10:00", fim="11:00", sala="S2"),
        ])
        encontros = {encontro.atributos_fisicos["codigo_disciplina"]: encontro
                     for encontro in ocupacao.encontros_fisicos}
        dominios = {}
        for codigo, encontro in encontros.items():
            atributos = encontro.atributos_fisicos
            dominios[encontro.id] = (
                Candidato(encontro.id, atributos["predio"], atributos["sala"],
                          "SEGUNDA-FEIRA", atributos["hora_inicio"], atributos["hora_fim"], 0),
                Candidato(encontro.id, atributos["predio"], atributos["sala"],
                          "TERÇA-FEIRA", atributos["hora_inicio"], atributos["hora_fim"], 0),
            )
        modelagem = construir_modelo_cp_sat(ocupacao, dominios)

        status, solucao, etapas, detalhes = resolver_solucao_b(ocupacao, modelagem, limite_segundos=5)

        self.assertEqual(status, cp_model.OPTIMAL)
        self.assertEqual(len(solucao), 2)
        self.assertEqual({candidato.dia_semana for candidato in solucao.values()},
                         {"SEGUNDA-FEIRA", "TERÇA-FEIRA"})
        self.assertEqual(len(etapas[("2026/2", "ARQU", "1")]), 2)
        self.assertIn("desvio absoluto diário", detalhes["objetivo"])


if __name__ == "__main__":
    unittest.main()