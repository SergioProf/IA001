import unittest

from modelo_ocupacao_03 import normalizar_registros
from restricoes_03 import (
    DIAS_VALIDOS,
    PRIORIDADE_TURMAS,
    REGRAS,
    classificar_preservacao,
    diagnosticos_bloqueantes,
    metricas_preferencia,
    selecionar_turmas_etapa,
    validar_grade,
)


CABECALHO = [
    "semestre", "predio", "sala", "capacidade_sala", "tipo_sala", "vagas_turma",
    "codigo_disciplina", "turma", "nome_disciplina", "docente", "curso", "dia_semana",
    "hora_inicio", "hora_fim", "numero_periodos", "vagas_oferecidas",
    "vagas_totais_compartilhadas", "turmas_compartilhando_sala", "etapa", "creditos",
]


def linha(codigo, curso="ARQU", turma="A", docente="Prof01", dia="SEGUNDA-FEIRA",
          inicio="09:00", fim="10:00", sala="S1", tipo="Sala de aula",
          vagas=10, capacidade=10, etapa="1", grupo=None):
    return {
        "semestre": "2026/2", "predio": "Bloco 1", "sala": sala,
        "capacidade_sala": str(capacidade), "tipo_sala": tipo, "vagas_turma": str(vagas),
        "codigo_disciplina": codigo, "turma": turma, "nome_disciplina": codigo,
        "docente": docente, "curso": curso, "dia_semana": dia, "hora_inicio": inicio,
        "hora_fim": fim, "numero_periodos": str(((int(fim[:2]) * 60 + int(fim[3:])) -
                                (int(inicio[:2]) * 60 + int(inicio[3:]))) // 60),
        "vagas_oferecidas": str(vagas), "vagas_totais_compartilhadas": str(vagas),
        "turmas_compartilhando_sala": grupo or turma, "etapa": etapa, "creditos": "2",
    }


def modelo(*registros):
    return normalizar_registros(CABECALHO, list(registros))


def posicao(encontro, **alteracoes):
    resultado = {
        "predio": encontro.atributos_fisicos["predio"],
        "sala": encontro.atributos_fisicos["sala"],
        "dia_semana": encontro.atributos_fisicos["dia_semana"],
        "hora_inicio": encontro.atributos_fisicos["hora_inicio"],
        "hora_fim": encontro.atributos_fisicos["hora_fim"],
    }
    resultado.update(alteracoes)
    return resultado


def regras(diagnosticos):
    return {item.regra for item in diagnosticos}


class TestRestricoes(unittest.TestCase):
    def test_cobertura_de_encontros_e_campos_imutaveis(self):
        grade = modelo(linha("ARQ001"))
        encontro = grade.encontros_fisicos[0]
        self.assertIn("H001", regras(validar_grade(grade, {})))
        self.assertIn("H001", regras(validar_grade(grade, {encontro.id: {
            **posicao(encontro), "docente": "Outro",
        }})))
        self.assertIn("H001", regras(validar_grade(grade, {
            encontro.id: posicao(encontro), "EV-inexistente": {},
        })))
        self.assertIn("H001", regras(validar_grade(grade, {encontro.id: posicao(
            encontro, hora_fim="10:30",
        )})))

    def test_dias_validos_e_sabado_proibido(self):
        self.assertEqual(len(DIAS_VALIDOS), 5)
        grade = modelo(linha("ARQ001"))
        encontro = grade.encontros_fisicos[0]
        resultado = validar_grade(grade, {encontro.id: posicao(encontro, dia_semana="SÁBADO")})
        self.assertIn("H002", regras(resultado))

    def test_limites_do_almoco(self):
        for inicio, fim in (("11:30", "12:30"), ("13:30", "14:30")):
            grade = modelo(linha(f"ARQ{inicio}"))
            self.assertNotIn("H003", regras(validar_grade(grade)))
        grade = modelo(linha("ARQ001", inicio="12:00", fim="13:00"))
        self.assertIn("H003", regras(validar_grade(grade)))

    def test_sobreposicao_de_sala_e_intervalos_semiabertos(self):
        grade = modelo(
            linha("ARQ001", sala="S1"),
            linha("ARQ002", sala="S1", inicio="10:00", fim="11:00", docente="Prof02"),
        )
        self.assertNotIn("H004", regras(validar_grade(grade)))
        segundo = grade.encontros_fisicos[1]
        resultado = validar_grade(grade, {segundo.id: posicao(segundo, hora_inicio="09:30", hora_fim="10:30")})
        self.assertIn("H004", regras(resultado))

    def test_conflito_docente_entre_cursos(self):
        grade = modelo(
            linha("DPR001", curso="DPRO", docente="Prof01", sala="S1"),
            linha("DVS001", curso="DVIS", docente="Prof01", sala="S2", dia="TERÇA-FEIRA"),
        )
        segundo = next(e for e in grade.encontros_fisicos if e.atributos_fisicos["sala"] == "S2")
        resultado = validar_grade(grade, {segundo.id: posicao(segundo, dia_semana="SEGUNDA-FEIRA")})
        self.assertIn("H005", regras(resultado))
        self.assertEqual(next(item for item in resultado if item.regra == "H005").severidade, "inviolavel")

    def test_etapa_obrigatoria_e_eletiva(self):
        obrigatorias = modelo(
            linha("ARQ001", etapa="2", docente="Prof01", sala="S1"),
            linha("ARQ002", etapa="2", docente="Prof02", sala="S2", dia="TERÇA-FEIRA"),
        )
        segundo = next(e for e in obrigatorias.encontros_fisicos if e.atributos_fisicos["sala"] == "S2")
        conflito = validar_grade(obrigatorias, {segundo.id: posicao(segundo, dia_semana="SEGUNDA-FEIRA")})
        self.assertIn("H006", regras(conflito))
        self.assertEqual(next(item for item in conflito if item.regra == "H006").severidade, "inviolavel")
        eletivas = modelo(
            linha("ARQ001", etapa="0", docente="Prof01", sala="S1"),
            linha("ARQ002", etapa="0", docente="Prof02", sala="S2"),
        )
        self.assertNotIn("H006", regras(validar_grade(eletivas)))

    def test_h006_aceita_turma_alternativa_da_mesma_disciplina(self):
        # ARQ001 A coincide com ARQ002, mas a turma B de ARQ001 permite cursar ambas.
        com_alternativa = modelo(
            linha("ARQ001", turma="A", etapa="2", docente="Prof01", sala="S1"),
            linha("ARQ001", turma="B", etapa="2", docente="Prof03", sala="S3", dia="TERÇA-FEIRA"),
            linha("ARQ002", turma="A", etapa="2", docente="Prof02", sala="S2"),
        )
        self.assertNotIn("H006", regras(validar_grade(com_alternativa)))
        sem_alternativa = modelo(
            linha("ARQ001", turma="A", etapa="2", docente="Prof01", sala="S1"),
            linha("ARQ001", turma="B", etapa="2", docente="Prof03", sala="S3"),
            linha("ARQ002", turma="A", etapa="2", docente="Prof02", sala="S2"),
        )
        self.assertIn("H006", regras(validar_grade(sem_alternativa)))

    def test_seleciona_uma_turma_por_disciplina_sem_conflitos(self):
        disciplinas = {
            "ARQ001": {"A": {"a"}, "B": {"b"}, "C": {"d"}},
            "ARQ002": {"A": {"c"}},
        }
        horarios = {
            "a": ("SEGUNDA-FEIRA", 540, 600),
            "b": ("TERÇA-FEIRA", 540, 600),
            "c": ("SEGUNDA-FEIRA", 540, 600),
            "d": ("QUARTA-FEIRA", 540, 600),
        }

        selecao = selecionar_turmas_etapa(disciplinas, horarios)
        selecao_preferida = selecionar_turmas_etapa(
            disciplinas,
            horarios,
            {"ARQ001": "C", "ARQ002": "A"},
        )
        preferida_conflitante = selecionar_turmas_etapa(
            disciplinas,
            horarios,
            {"ARQ001": "A", "ARQ002": "A"},
        )

        self.assertEqual(selecao, {"ARQ001": "B", "ARQ002": "A"})
        self.assertEqual(selecao_preferida, {"ARQ001": "C", "ARQ002": "A"})
        self.assertEqual(preferida_conflitante, {"ARQ001": "B", "ARQ002": "A"})
        self.assertIsNone(selecionar_turmas_etapa(
            {"ARQ001": {"A": {"a"}}, "ARQ002": {"A": {"c"}}},
            horarios,
        ))

    def test_cursos_externos_imoveis(self):
        grade = modelo(linha("MUS001", curso="MUS", dia="TERÇA-FEIRA"))
        encontro = grade.encontros_fisicos[0]
        resultado = validar_grade(grade, {encontro.id: posicao(encontro, dia_semana="QUARTA-FEIRA")})
        self.assertIn("H007", regras(resultado))
        compartilhada = modelo(
            linha("MIX001", curso="ARQU", turma="A", grupo="A/B"),
            linha("MIX001", curso="MUS", turma="B", grupo="A/B"),
        )
        evento = compartilhada.encontros_fisicos[0]
        fixo = validar_grade(compartilhada, {evento.id: posicao(evento, dia_semana="TERÇA-FEIRA")})
        self.assertIn("H007", regras(fixo))

    def test_limite_de_capacidade(self):
        for vagas, violacao in ((10, False), (12, False), (13, True)):
            grade = modelo(linha("ARQ001", vagas=vagas, capacidade=10))
            self.assertEqual("H008" in regras(validar_grade(grade)), violacao)
        compartilhada = modelo(
            linha("DSG001", curso="DPRO", turma="A", grupo="A/B", vagas=7, capacidade=10),
            linha("DSG001", curso="DVIS", turma="B", grupo="A/B", vagas=7, capacidade=10),
        )
        self.assertIn("H008", regras(validar_grade(compartilhada)))

    def test_dependencia_de_laboratorio(self):
        grade = modelo(
            linha("ARQ001", tipo="Laboratório de informática", sala="Lab1"),
            linha("ARQ002", tipo="Sala de aula", sala="S1"),
        )
        laboratorio = next(e for e in grade.encontros_fisicos if e.atributos_fisicos["sala"] == "Lab1")
        resultado = validar_grade(grade, {laboratorio.id: posicao(laboratorio, sala="S1")})
        self.assertIn("H009", regras(resultado))

    def test_relaxamento_de_turno_com_justificativa(self):
        grade = modelo(linha("DPR001", curso="DPRO", inicio="14:00", fim="15:00"))
        encontro = grade.encontros_fisicos[0]
        proposta = {encontro.id: posicao(encontro, hora_inicio="09:00", hora_fim="10:00")}
        sem_justificativa = validar_grade(grade, proposta)
        self.assertIn("H010", regras(sem_justificativa))
        self.assertEqual(next(item for item in sem_justificativa if item.regra == "H010").severidade, "inviolavel")
        com_justificativa = validar_grade(grade, proposta, {encontro.id: "Conflito de sala sem alternativa."})
        diagnostico = next(item for item in com_justificativa if item.regra == "H010")
        self.assertEqual(diagnostico.severidade, "excecao")
        self.assertIn("Conflito de sala", diagnostico.mensagem)
        self.assertEqual(diagnosticos_bloqueantes(com_justificativa), [])

    def test_nivel_de_preservacao(self):
        grade = modelo(linha("ARQ001"))
        encontro = grade.encontros_fisicos[0]
        self.assertEqual(classificar_preservacao(grade, {})[encontro.id], 1)
        self.assertEqual(classificar_preservacao(grade, {encontro.id: posicao(encontro, sala="S2")})[encontro.id], 2)
        self.assertEqual(classificar_preservacao(grade, {encontro.id: posicao(encontro, hora_inicio="10:00", hora_fim="11:00")})[encontro.id], 3)
        self.assertEqual(classificar_preservacao(grade, {encontro.id: posicao(encontro, dia_semana="TERÇA-FEIRA")})[encontro.id], 5)

    def test_preferencias_de_espaco(self):
        grade = modelo(
            linha("ARQ001", tipo="Sala de aula", sala="S1"),
            linha("ARQ002", tipo="Laboratório de informática", sala="Lab1"),
        )
        evento = next(e for e in grade.encontros_fisicos if e.atributos_fisicos["sala"] == "S1")
        metricas = metricas_preferencia(grade, {evento.id: posicao(evento, sala="Lab1")})
        self.assertEqual(metricas["laboratorios_sem_dependencia"], 1)
        self.assertEqual(metricas["tipos_espaco_alterados"], 1)

    def test_prioridade_de_alocacao(self):
        self.assertEqual(PRIORIDADE_TURMAS, (
            "alunos_desc", "obrigatoria_antes_eletiva", "encontros_desc", "ch_semanal_desc",
        ))
        grade = modelo(
            linha("ARQ001", etapa="1", vagas=10),
            linha("ARQ002", etapa="0", vagas=10),
            linha("ARQ003", etapa="0", vagas=11),
        )
        ordem = metricas_preferencia(grade, {})["ordem_prioridade_turmas"]
        self.assertEqual([item["codigo_disciplina"] for item in ordem], ["ARQ003", "ARQ001", "ARQ002"])

    def test_metricas_de_preferencia(self):
        grade = modelo(
            linha("ARQ001", docente="Prof01"),
            linha("ARQ002", docente="Prof01", inicio="11:00", fim="12:00"),
        )
        metricas = metricas_preferencia(grade, {})
        self.assertIn("Prof01", metricas["dispersao_carga_docente_periodos"])
        self.assertEqual(metricas["inicios_noturnos_tardios"], 0)
        self.assertEqual(metricas["contagem_niveis_preservacao"][1], 2)
        self.assertEqual(metricas["intervalos_livres_docente_minutos"]["Prof01"], 60)
        self.assertEqual(metricas["dispersao_carga_etapa_periodos"]["ARQU/etapa 1"], 2)
        self.assertTrue(metricas["ordem_prioridade_turmas"])
        noturno = modelo(linha("ARQ003", inicio="20:00", fim="21:00"))
        self.assertEqual(metricas_preferencia(noturno, {})["inicios_noturnos_tardios"], 1)

    def test_catalogo_de_regras_tem_id_severidade_e_teste(self):
        self.assertEqual(len({regra.id for regra in REGRAS}), len(REGRAS))
        self.assertTrue(all(regra.severidade and regra.teste for regra in REGRAS))

    def test_diagnostico_existente_na_fonte_e_rotulado_como_baseline(self):
        grade = modelo(
            linha("ARQ001", etapa="2", docente="Prof01", sala="S1"),
            linha("ARQ002", etapa="2", docente="Prof02", sala="S2"),
        )
        resultado = validar_grade(grade)
        self.assertEqual(next(item for item in resultado if item.regra == "H006").severidade, "baseline")
        proposta = {e.id: posicao(e) for e in grade.encontros_fisicos}
        repetida = validar_grade(grade, proposta)
        self.assertEqual(next(item for item in repetida if item.regra == "H006").severidade, "baseline")


if __name__ == "__main__":
    unittest.main()