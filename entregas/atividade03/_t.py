import sys, os
sys.path.insert(0, os.environ["APPDIR"])
import app_03 as m
d = m.carregar_dados(str(m.CAMINHO_DADOS))
m.exibir_animacao_plantas(d)
