"""Testes do importador de questões de PDFs (importar_questoes.py)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import importar_questoes as IQ  # noqa: E402

_PROVA = """
QUESTÃO 1
A Lei 13.303/2016 dispõe sobre o estatuto jurídico das estatais. Assinale a correta.
(A) Aplica-se apenas a empresas privadas.
(B) É o Estatuto das Estatais.
(C) Revoga a Constituição.
(D) Trata só de tributos.
(E) Não existe.

QUESTÃO 2
Sobre licitações na Lei 14.133/2021, marque a alternativa correta.
(A) Proíbe pregão.
(B) Extingue a modalidade concorrência.
(C) É a Nova Lei de Licitações.
(D) Aplica-se ao setor privado.
(E) Foi revogada em 2020.
"""

_GABARITO = "GABARITO\n1 - B   2 - C\n"


class TestParsearGabarito:
    def test_formatos_variados(self):
        g = IQ.parsear_gabarito("1-A 2 - B 3) C 4: D 5 E")
        assert g == {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}

    def test_ignora_numeros_absurdos(self):
        g = IQ.parsear_gabarito("9999 - A 1 - C")
        assert g == {1: "C"}


class TestParsearQuestoes:
    def test_extrai_questoes_e_opcoes(self):
        qs = IQ.parsear_questoes(_PROVA)
        assert len(qs) == 2
        assert qs[0]["numero"] == 1
        assert len(qs[0]["opcoes"]) == 5
        assert "Estatuto das Estatais" in qs[0]["opcoes"][1]

    def test_questao_sem_5_opcoes_descartada(self):
        texto = "QUESTÃO 1\nEnunciado qualquer aqui.\n(A) um\n(B) dois\n"
        assert IQ.parsear_questoes(texto) == []


class TestMontarQuestoes:
    def test_casa_gabarito_e_define_correta(self):
        qs = IQ.montar_questoes(_PROVA, _GABARITO, disciplina="Legislação")
        assert len(qs) == 2
        q1 = qs[0]
        assert q1["correta"] == 1          # B
        assert q1["disciplina"] == "Legislação"
        assert "extraida" in q1["tags"]
        assert "B" in q1["explicacao"]

    def test_sem_gabarito_descarta(self):
        # sem gabarito → nenhuma questão (não inventa resposta)
        assert IQ.montar_questoes(_PROVA, "", disciplina="X") == []

    def test_gabarito_parcial_mantem_so_as_com_resposta(self):
        qs = IQ.montar_questoes(_PROVA, "1 - B", disciplina="X")
        assert len(qs) == 1 and qs[0]["correta"] == 1


class TestStoreEImportar:
    def test_importar_deduplica(self, tmp_path):
        store = tmp_path / "q.json"
        qs = IQ.montar_questoes(_PROVA, _GABARITO, disciplina="Leg")
        n1 = IQ.importar(qs, caminho=store)
        n2 = IQ.importar(qs, caminho=store)  # mesma coisa → 0 novas
        assert n1 == 2 and n2 == 0
        assert len(IQ.carregar_extraidas(store)) == 2

    def test_estatisticas(self, tmp_path):
        store = tmp_path / "q.json"
        IQ.importar(IQ.montar_questoes(_PROVA, _GABARITO, disciplina="Leg"), caminho=store)
        st = IQ.estatisticas(store)
        assert st["total"] == 2 and st["por_disciplina"]["Leg"] == 2


class TestIntegracaoTreino:
    def test_treino_banco_inclui_extraidas(self, tmp_path, monkeypatch):
        import treino
        import importar_questoes as iq
        store = tmp_path / "q.json"
        iq.importar(iq.montar_questoes(_PROVA, _GABARITO, disciplina="Leg"), caminho=store)
        monkeypatch.setattr(iq, "_STORE", store)
        n_curado = len(treino.BANCO_QUESTOES)
        completo = treino.banco()
        assert len(completo) == n_curado + 2
