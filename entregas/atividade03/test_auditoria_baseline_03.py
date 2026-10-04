import unittest
from pathlib import Path

from auditoria_baseline_03 import _horas_por_turno, auditar_baseline
from modelo_ocupacao_03 import carregar_modelo


class TestAuditoriaBaseline(unittest.TestCase):
    def test_encontro_que_cruza_limites_e_dividido_por_horas(self):
        self.assertEqual(_horas_por_turno(12 * 60, 14 * 60), {"Manhã": 0.5, "Tarde": 0.5, "Noite": 0.0})
        self.assertEqual(_horas_por_turno(18 * 60, 19 * 60), {"Manhã": 0.0, "Tarde": 0.5, "Noite": 0.5})

    def test_grade_real_tem_baseline_reconciliado(self):
        csv = Path(__file__).with_name("mapa_salas_tidy_03.csv")
        resultado = auditar_baseline(carregar_modelo(csv))
        self.assertEqual(resultado["resumo"]["linhas_fonte"], 452)
        self.assertEqual(resultado["resumo"]["encontros_fisicos"], 289)
        self.assertEqual(sum(resultado["padroes_por_numero_encontros"].values()), 184)
        divergencias = resultado["capacidade"]["divergencias_vagas_por_tipo"]
        self.assertEqual(divergencias.get("vagas_oferecidas_vs_vagas_totais_compartilhadas", 0), 0)
        self.assertGreater(divergencias.get("vagas_oferecidas_vs_vagas_turma", 0), 0)
        self.assertEqual(resultado["resumo"]["encontros_cruzam_almoco"], 1)
        self.assertEqual(resultado["conflitos_baseline"], [])
        self.assertEqual(resultado["etapas_sem_combinacao"], [])


if __name__ == "__main__":
    unittest.main()