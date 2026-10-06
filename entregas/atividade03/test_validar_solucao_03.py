import unittest

from modelo_ocupacao_03 import normalizar_registros
from test_restricoes_03 import CABECALHO, linha
from validar_solucao_03 import _inventarios, _metricas_curso, _validar_integridade_csv


class TestValidacaoIndependente(unittest.TestCase):
    def setUp(self):
        self.registros = [
            linha("ARQ001", turma="A", docente="Prof01", inicio="09:00", fim="11:00", grupo="A/B"),
            linha("ARQ001", turma="A", docente="Prof02", inicio="09:00", fim="11:00", grupo="A/B"),
            linha("ARQ001", turma="B", docente="Prof03", inicio="09:00", fim="11:00", grupo="A/B"),
        ]
        self.modelo = normalizar_registros(CABECALHO, self.registros)
        self.linhas_saida = []
        for registro, linha_fonte in zip(self.registros, self.modelo.linhas_fonte):
            self.linhas_saida.append({
                **registro,
                "encontro_id": linha_fonte["evento_fisico_id"],
                "excecao_turno": "",
            })

    def test_ch_conta_turma_encontro_sem_repetir_docente(self):
        encontro = self.modelo.encontros_fisicos[0]
        alocacoes = {encontro.id: {
            campo: encontro.atributos_fisicos[campo]
            for campo in ("predio", "sala", "dia_semana", "hora_inicio", "hora_fim")
        }}

        metricas = _metricas_curso(self.modelo, alocacoes)["ARQU"]

        self.assertEqual(metricas["ch_total_horas"], 4.0)
        self.assertEqual(metricas["ch_turno_alvo_horas"], 4.0)
        self.assertEqual(metricas["turmas_total"], 2)

    def test_ocupacao_sala_curso_conta_evento_compartilhado_uma_vez(self):
        encontro = self.modelo.encontros_fisicos[0]
        alocacoes = {encontro.id: {
            campo: encontro.atributos_fisicos[campo]
            for campo in ("predio", "sala", "dia_semana", "hora_inicio", "hora_fim")
        }}

        _, por_curso, _, _ = _inventarios(self.modelo, alocacoes, "ANTES")

        self.assertEqual(len(por_curso), 1)
        self.assertEqual(por_curso[0]["curso"], "ARQU")
        self.assertEqual(por_curso[0]["horas_aula"], 2.0)

    def test_ch_diaria_da_etapa_conta_uma_turma_por_disciplina(self):
        registros = [
            linha("ARQ001", turma="A", sala="S1", docente="Prof01"),
            linha("ARQ001", turma="B", sala="S2", docente="Prof02", dia="TERÇA-FEIRA"),
            linha("ARQ002", turma="A", sala="S3", docente="Prof03"),
        ]
        modelo_etapa = normalizar_registros(CABECALHO, registros)
        alocacoes = {
            encontro.id: {
                campo: encontro.atributos_fisicos[campo]
                for campo in ("predio", "sala", "dia_semana", "hora_inicio", "hora_fim")
            }
            for encontro in modelo_etapa.encontros_fisicos
        }

        _, _, distribuicao, _ = _inventarios(modelo_etapa, alocacoes, "A")
        etapa = [
            item for item in distribuicao
            if item["grupo_tipo"] == "etapa_aluno" and item["grupo"] == "ARQU/1"
        ]
        horas_por_dia = {item["dia_semana"]: item["horas"] for item in etapa}

        self.assertEqual(horas_por_dia["SEGUNDA-FEIRA"], 1.0)
        self.assertEqual(horas_por_dia["TERÇA-FEIRA"], 1.0)
        self.assertTrue(all(
            item["turmas_selecionadas"] == "ARQ001:B, ARQ002:A"
            for item in etapa
        ))

    def test_integridade_aceita_colunas_extras_e_linhagem_original(self):
        dados = _validar_integridade_csv(
            self.modelo, CABECALHO, self.registros,
            [*CABECALHO, "encontro_id", "excecao_turno"], self.linhas_saida,
        )

        self.assertEqual(len(dados["alocacoes"]), 1)

    def test_integridade_rejeita_alteracao_de_campo_original(self):
        linhas = [dict(registro) for registro in self.linhas_saida]
        linhas[0]["docente"] = "Outro docente"

        with self.assertRaisesRegex(ValueError, "linhagem divergente"):
            _validar_integridade_csv(
                self.modelo, CABECALHO, self.registros,
                [*CABECALHO, "encontro_id", "excecao_turno"], linhas,
            )


if __name__ == "__main__":
    unittest.main()