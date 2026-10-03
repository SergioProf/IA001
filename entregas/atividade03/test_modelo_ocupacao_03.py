import csv
import unittest
from pathlib import Path

from modelo_ocupacao_03 import carregar_modelo, normalizar_registros


CABECALHO = [
    "semestre", "predio", "sala", "capacidade_sala", "tipo_sala", "vagas_turma",
    "codigo_disciplina", "turma", "nome_disciplina", "docente", "curso", "dia_semana",
    "hora_inicio", "hora_fim", "numero_periodos", "vagas_oferecidas",
    "vagas_totais_compartilhadas", "turmas_compartilhando_sala", "etapa", "creditos",
]


def linha(turma, curso, docente, dia, etapa):
    return {
        "semestre": "2026/2", "predio": "Bloco 1", "sala": "Sala 1",
        "capacidade_sala": "30", "tipo_sala": "Sala de aula", "vagas_turma": "10",
        "codigo_disciplina": "DSN00001", "turma": turma, "nome_disciplina": "Projeto",
        "docente": docente, "curso": curso, "dia_semana": dia, "hora_inicio": "09:30",
        "hora_fim": "11:30", "numero_periodos": "2", "vagas_oferecidas": "10",
        "vagas_totais_compartilhadas": "20", "turmas_compartilhando_sala": "A/AA",
        "etapa": etapa, "creditos": "2",
    }


class TestModeloOcupacao(unittest.TestCase):
    def setUp(self):
        self.registros = [
            linha("A", "DPRO", "Prof01", "SEGUNDA-FEIRA", "2"),
            linha("AA", "DPRO", "Prof02", "SEGUNDA-FEIRA", "2"),
            linha("A", "DVIS", "Prof01", "SEGUNDA-FEIRA", "3"),
            linha("AA", "DVIS", "Prof02", "SEGUNDA-FEIRA", "3"),
            linha("A", "DPRO", "Prof01", "QUARTA-FEIRA", "2"),
            linha("AA", "DPRO", "Prof02", "QUARTA-FEIRA", "2"),
            linha("A", "DVIS", "Prof01", "QUARTA-FEIRA", "3"),
            linha("AA", "DVIS", "Prof02", "QUARTA-FEIRA", "3"),
        ]

    def test_separa_turmas_cursos_eventos_e_padroes_semanais(self):
        modelo = normalizar_registros(CABECALHO, self.registros)

        self.assertEqual(modelo.resumo(), {
            "linhas_fonte": 8, "turmas_academicas": 4, "membros_compartilhamento": 2,
            "atribuicoes_docentes": 4, "encontros_fisicos": 2, "padroes_semanais": 1,
        })
        self.assertEqual(len(modelo.encontros_fisicos[0].membros), 2)
        self.assertEqual(len(modelo.padroes_semanais[0].encontros_fisicos), 2)
        self.assertEqual({turma.etapa for turma in modelo.turmas_academicas}, {"2", "3"})
        self.assertTrue(all(len(atribuicao.turmas_academicas) == 2
                    for atribuicao in modelo.atribuicoes_docentes))
        self.assertTrue(all(len(atribuicao.linhas_fonte) == 2
                    for atribuicao in modelo.atribuicoes_docentes))

    def test_linhagem_retorna_cada_linha_original_uma_vez(self):
        modelo = normalizar_registros(CABECALHO, self.registros)
        linhas_encontros = [
            numero for encontro in modelo.encontros_fisicos for numero in encontro.linhas_fonte
        ]

        self.assertEqual(sorted(linhas_encontros), list(range(2, 10)))
        self.assertEqual(len({linha["linha_fonte"] for linha in modelo.linhas_fonte}), 8)
        self.assertEqual(
            {linha["valores"]["curso"] for linha in modelo.linhas_fonte}, {"DPRO", "DVIS"}
        )

    def test_ids_de_eventos_nao_dependem_da_ordem_das_linhas(self):
        original = normalizar_registros(CABECALHO, self.registros)
        invertido = normalizar_registros(CABECALHO, list(reversed(self.registros)))

        self.assertEqual(
            {evento.id for evento in original.encontros_fisicos},
            {evento.id for evento in invertido.encontros_fisicos},
        )

    def test_rejeita_membro_que_nao_pertence_ao_grupo(self):
        with self.assertRaisesRegex(ValueError, "não pertence ao grupo"):
            normalizar_registros(CABECALHO, [dict(self.registros[0], turma="B")])

    def test_rejeita_grupo_com_membro_sem_linha_fonte(self):
        with self.assertRaisesRegex(ValueError, "sem linhas-fonte para os membros"):
            normalizar_registros(CABECALHO, [self.registros[0]])

    def test_carrega_csv_real(self):
        caminho = Path(__file__).with_name("mapa_salas_tidy_03.csv")
        with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
            quantidade = sum(1 for _ in csv.DictReader(arquivo))

        modelo = carregar_modelo(caminho)

        self.assertEqual(modelo.resumo()["linhas_fonte"], quantidade)
        self.assertEqual(len(modelo.encontros_fisicos), 289)
        self.assertEqual(len(modelo.padroes_semanais), 184)


if __name__ == "__main__":
    unittest.main()