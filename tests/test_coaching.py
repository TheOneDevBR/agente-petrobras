"""Testes do coaching adaptativo (coaching.py)."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import coaching as C  # noqa: E402


@dataclass
class QFake:
    pergunta: str
    disciplina: str = ""
    tags: list = field(default_factory=list)


class TestElo:
    def test_expectativa_simetrica(self):
        assert C.expectativa(1000, 1000) == 0.5
        assert C.expectativa(1200, 1000) > 0.5
        assert C.expectativa(800, 1000) < 0.5

    def test_acerto_sobe_habilidade_e_baixa_dificuldade(self):
        est = C.estado_vazio()
        q = QFake("2+2?", "Matemática")
        C.registrar_resposta("Matemática", q, acertou=True, estado=est)
        assert est["habilidades"]["Matemática"] > C.RATING_INICIAL
        assert est["itens"][C.qid(q)] < C.RATING_INICIAL
        assert est["n_respostas"]["Matemática"] == 1

    def test_erro_baixa_habilidade_e_sobe_dificuldade(self):
        est = C.estado_vazio()
        q = QFake("integral?", "Matemática")
        C.registrar_resposta("Matemática", q, acertou=False, estado=est)
        assert est["habilidades"]["Matemática"] < C.RATING_INICIAL
        assert est["itens"][C.qid(q)] > C.RATING_INICIAL

    def test_qid_estavel(self):
        a = QFake("mesma pergunta", "X")
        b = QFake("mesma pergunta", "Y")
        assert C.qid(a) == C.qid(b)  # depende só do enunciado


class TestNivel:
    def test_faixas(self):
        assert C.nivel(800) == "iniciante"
        assert C.nivel(1000) == "intermediário"
        assert C.nivel(1350) == "domínio"


class TestSelecaoAdaptativa:
    def _banco(self):
        return [QFake(f"q{i}", "Port") for i in range(20)]

    def test_filtra_por_disciplina(self):
        banco = [QFake("a", "Port"), QFake("b", "Mat")]
        sel = C.selecionar_adaptativo(5, "Port", banco=banco, estado=C.estado_vazio())
        assert all(q.disciplina == "Port" for q in sel)

    def test_seleciona_proximo_do_alvo(self):
        banco = self._banco()
        est = C.estado_vazio()
        # habilidade alta → alvo alto; questão "q5" calibrada difícil deve ser preferida
        est["habilidades"]["Port"] = 1400.0
        alvo = 1400.0 - C.OFFSET_DESEJAVEL
        est["itens"][C.qid(banco[5])] = alvo          # exatamente no alvo
        est["itens"][C.qid(banco[0])] = 700.0         # longe do alvo
        sel = C.selecionar_adaptativo(3, "Port", banco=banco, estado=est)
        assert banco[5] in sel

    def test_pool_vazio(self):
        assert C.selecionar_adaptativo(3, "Inexistente", banco=self._banco(),
                                       estado=C.estado_vazio()) == []


class TestDiagnostico:
    def test_diagnostico_ordena_e_recomenda_foco(self):
        est = C.estado_vazio()
        est["habilidades"] = {"Forte": 1300.0, "Fraca": 850.0}
        est["n_respostas"] = {"Forte": 10, "Fraca": 8}
        diag = C.diagnostico(est)
        # menor rating primeiro
        assert diag["disciplinas"][0]["disciplina"] == "Fraca"
        assert "Fraca" in diag["foco_recomendado"]

    def test_foco_exige_minimo_de_respostas(self):
        est = C.estado_vazio()
        est["habilidades"] = {"Pouca": 800.0}
        est["n_respostas"] = {"Pouca": 1}  # < 3 → não entra no foco
        assert C.diagnostico(est)["foco_recomendado"] == []

    def test_formatar_sem_dados(self):
        txt = C.formatar_diagnostico(C.estado_vazio())
        assert "DIAGNÓSTICO ADAPTATIVO" in txt


class TestPersistencia:
    def test_round_trip(self, tmp_path):
        est = C.estado_vazio()
        q = QFake("x", "Port")
        C.registrar_resposta("Port", q, True, estado=est)
        p = tmp_path / "elo.json"
        C.salvar(est, p)
        recarregado = C.carregar(p)
        assert recarregado["habilidades"]["Port"] == est["habilidades"]["Port"]

    def test_carregar_inexistente(self, tmp_path):
        d = C.carregar(tmp_path / "nao_existe.json")
        assert d == C.estado_vazio()
