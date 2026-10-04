import unittest

from candidatos_03 import alocacoes_fixos, gerar_candidatos, resumir_dominios
from candidatos_03 import Candidato
from modelo_otimizacao_03 import (
    construir_modelo_cp_sat,
    construir_modelo_cp_sat_diagnostico,
    resolver_viabilidade,
)
from ortools.sat.python import cp_model
from test_restricoes_03 import linha, modelo


class TestCandidatos(unittest.TestCase):
    def test_dominio_usa_janelas_observadas_preserva_duracao_e_evita_almoco(self):
        grade = modelo(
            linha("ARQ001", inicio="09:00", fim="10:00"),
            linha("ARQ002", inicio="10:00", fim="11:00", docente="Prof02"),
            linha("ARQ003", inicio="12:00", fim="13:00", docente="Prof03"),
        )
        dominios = gerar_candidatos(grade)
        for candidatos in dominios.values():
            self.assertTrue(candidatos)
            for candidato in candidatos:
                self.assertIn((candidato.hora_inicio, candidato.hora_fim), {
                    ("09:00", "10:00"), ("10:00", "11:00")
                })
                self.assertIn(candidato.dia_semana, {
                    "SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA"
                })

    def test_diagnostico_combina_inicio_observado_com_duracao_existente(self):
        grade = modelo(
            linha("ARQ001", inicio="09:00", fim="10:00"),
            linha("ARQ002", inicio="10:00", fim="12:00", docente="Prof02"),
        )
        encontro = next(
            item for item in grade.encontros_fisicos
            if item.atributos_fisicos["codigo_disciplina"] == "ARQ001"
        )
        original = gerar_candidatos(grade)[encontro.id]
        expandido = gerar_candidatos(grade, combinar_inicios_observados=True)[encontro.id]
        posicoes_originais = {(item.hora_inicio, item.hora_fim) for item in original}
        posicoes_expandidas = {(item.hora_inicio, item.hora_fim) for item in expandido}

        self.assertIn(("10:00", "11:00"), posicoes_expandidas)
        self.assertNotIn(("10:00", "11:00"), posicoes_originais)
        for candidato in expandido:
            self.assertEqual(candidato.hora_fim, "10:00" if candidato.hora_inicio == "09:00" else "11:00")
            self.assertNotEqual((candidato.hora_inicio, candidato.hora_fim), ("12:00", "13:00"))

    def test_grade_horaria_usa_somente_inicios_hh30_e_preserva_limites(self):
        grade = modelo(
            linha("ARQ001", inicio="09:30", fim="10:30"),
            linha("ARQ002", inicio="13:30", fim="14:30", docente="Prof02"),
        )
        encontro = next(
            item for item in grade.encontros_fisicos
            if item.atributos_fisicos["codigo_disciplina"] == "ARQ001"
        )
        candidatos = gerar_candidatos(grade, usar_grade_horaria_meia_hora=True)[encontro.id]

        self.assertTrue(candidatos)
        self.assertTrue(all(candidato.hora_inicio.endswith(":30") for candidato in candidatos))
        self.assertIn(("11:30", "12:30"), {
            (candidato.hora_inicio, candidato.hora_fim) for candidato in candidatos
        })
        self.assertFalse(any(candidato.hora_inicio == "12:30" for candidato in candidatos))
        self.assertTrue(all(candidato.hora_fim <= "14:30" for candidato in candidatos))

    def test_encontros_externos_ficam_fixos_e_bloqueiam_sala(self):
        grade = modelo(
            linha("ARQ001", sala="S1", inicio="09:00", fim="10:00", docente="Prof01"),
            linha("MUS001", curso="MUS", sala="S2", inicio="10:00", fim="11:00", docente="Prof02"),
        )
        fixos = alocacoes_fixos(grade)
        externo = next(e for e in grade.encontros_fisicos if e.id in fixos)
        self.assertEqual(fixos[externo.id]["dia_semana"], "SEGUNDA-FEIRA")
        self.assertEqual(fixos[externo.id]["hora_inicio"], "10:00")

        alvo = next(e for e in grade.encontros_fisicos if e.id not in fixos)
        candidatos = gerar_candidatos(grade)[alvo.id]
        posicoes = {
            (candidato.sala, candidato.dia_semana, candidato.hora_inicio)
            for candidato in candidatos
        }
        self.assertNotIn(("S2", "SEGUNDA-FEIRA", "10:00"), posicoes)
        self.assertIn(("S1", "SEGUNDA-FEIRA", "10:00"), posicoes)

    def test_encontro_externo_bloqueia_docente_em_qualquer_sala(self):
        grade = modelo(
            linha("ARQ001", sala="S1", docente="Prof01"),
            linha("MUS001", curso="MUS", sala="S2", inicio="10:00", fim="11:00", docente="Prof01"),
        )
        alvo = next(e for e in grade.encontros_fisicos if e.id not in alocacoes_fixos(grade))
        candidatos = gerar_candidatos(grade)[alvo.id]
        self.assertFalse(any(
            candidato.dia_semana == "SEGUNDA-FEIRA" and candidato.hora_inicio == "10:00"
            for candidato in candidatos
        ))

    def test_dominio_respeita_limite_de_capacidade_da_sala(self):
        grade = modelo(
            linha("ARQ001", sala="S1", vagas=13, capacidade=10),
            linha("ARQ002", sala="S2", vagas=13, capacidade=20, docente="Prof02"),
        )
        evento = next(e for e in grade.encontros_fisicos if e.atributos_fisicos["sala"] == "S1")
        salas_candidatas = {candidato.sala for candidato in gerar_candidatos(grade)[evento.id]}
        self.assertNotIn("S1", salas_candidatas)
        self.assertIn("S2", salas_candidatas)

    def test_dependencia_de_computador_restringe_laboratorio(self):
        grade = modelo(
            linha("ARQ001", sala="Lab1", tipo="Laboratório de informática"),
            linha("ARQ002", sala="Sala1", tipo="Sala de aula", docente="Prof02"),
        )
        dominios = gerar_candidatos(grade)
        evento_laboratorio = next(
            evento for evento in grade.encontros_fisicos
            if evento.atributos_fisicos["sala"] == "Lab1"
        )
        self.assertTrue(dominios[evento_laboratorio.id])
        self.assertEqual({candidato.sala for candidato in dominios[evento_laboratorio.id]}, {"Lab1"})

    def test_resumo_contabiliza_dominio_vazio(self):
        self.assertEqual(resumir_dominios({"EV1": (), "EV2": ()}), {
            "encontros_moveis": 2,
            "candidatos_totais": 0,
            "dominios_vazios": 2,
            "menor_dominio": 0,
            "maior_dominio": 0,
            "dominio_medio": 0.0,
        })

    def test_modelo_cp_sat_resolve_caso_minimo_e_preserva_encontro_externo(self):
        grade = modelo(
            linha("ARQ001", sala="S1", inicio="09:00", fim="10:00", docente="Prof01"),
            linha("MUS001", curso="MUS", sala="S2", inicio="10:00", fim="11:00", docente="Prof02"),
        )
        dominios = gerar_candidatos(grade)
        modelagem = construir_modelo_cp_sat(grade, dominios)
        status, solucao = resolver_viabilidade(modelagem, limite_segundos=5)
        self.assertIn(status, (cp_model.OPTIMAL, cp_model.FEASIBLE))
        self.assertEqual(set(solucao), set(dominios))
        self.assertEqual(modelagem.intervalo_minutos, 60)
        self.assertEqual(len(alocacoes_fixos(grade)), 1)

    def test_modelo_cp_sat_rejeita_dominio_vazio(self):
        grade = modelo(linha("ARQ001"))
        with self.assertRaisesRegex(ValueError, "sem candidatos"):
            construir_modelo_cp_sat(grade, {grade.encontros_fisicos[0].id: ()})

    def test_modelo_cp_sat_impede_sobreposicao_de_sala(self):
        grade = modelo(
            linha("ARQ001", sala="S1", docente="Prof01"),
            linha("ARQ002", sala="S2", docente="Prof02", etapa="2"),
        )
        primeiro, segundo = grade.encontros_fisicos
        dominios = {
            primeiro.id: (Candidato(primeiro.id, "Bloco 1", "S1", "SEGUNDA-FEIRA", "09:00", "10:00", 0),),
            segundo.id: (Candidato(segundo.id, "Bloco 1", "S1", "SEGUNDA-FEIRA", "09:00", "10:00", 0),),
        }
        modelagem = construir_modelo_cp_sat(grade, dominios)
        status, _ = resolver_viabilidade(modelagem, limite_segundos=5)
        self.assertEqual(status, cp_model.INFEASIBLE)

        diagnostico = construir_modelo_cp_sat_diagnostico(grade, dominios, "sala")
        status_relaxado, _ = resolver_viabilidade(diagnostico, limite_segundos=5)
        self.assertEqual(status_relaxado, cp_model.OPTIMAL)

    def test_modelo_diagnostico_rejeita_recurso_desconhecido(self):
        grade = modelo(linha("ARQ001"))
        dominios = gerar_candidatos(grade)
        with self.assertRaisesRegex(ValueError, "Recurso diagnóstico inválido"):
            construir_modelo_cp_sat_diagnostico(grade, dominios, "curso")

    def test_fonte_real_tem_candidato_para_cada_encontro_movivel(self):
        from pathlib import Path

        from modelo_ocupacao_03 import carregar_modelo

        fonte = Path(__file__).with_name("mapa_salas_tidy_03.csv")
        grade = carregar_modelo(fonte)
        dominios = gerar_candidatos(grade)
        self.assertEqual(len(dominios), 285)
        self.assertEqual(resumir_dominios(dominios)["dominios_vazios"], 0)
        self.assertEqual(len(alocacoes_fixos(grade)), 4)


if __name__ == "__main__":
    unittest.main()