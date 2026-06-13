"""Testes do loop de eficácia fechado (prescricao.py)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import prescricao as P  # noqa: E402


def _diario_mock(ranking=None):
    d = MagicMock()
    d.ranking_estrategias.return_value = ranking or []
    d.registrar_decisao.return_value = "d_123"
    d.registrar_outcome.return_value = {"eficacia": 0.1}
    d.estatisticas.return_value = {"total_decisoes": 5, "com_outcome": 3, "eficacia_global": 0.12}
    return d


def _ab_mock(escolha=None):
    a = MagicMock()
    a.selecionar_estrategia.return_value = escolha
    a.registrar_resultado.return_value = {"id": "exp1"}
    a.estatisticas.return_value = {"ativos": 1}
    return a


class TestCatalogo:
    def test_estrategia_por_desempenho(self):
        assert P._estrategia_por_desempenho(None) == "retrieval_practice"
        assert P._estrategia_por_desempenho(40) == "retrieval_practice"
        assert P._estrategia_por_desempenho(60) == "estudo_dirigido_erros"
        assert P._estrategia_por_desempenho(78) == "intercalacao"
        assert P._estrategia_por_desempenho(90) == "simulado_cronometrado"


class TestPrescrever:
    def test_usa_ab_quando_ativo(self):
        ab = _ab_mock(escolha={"estrategia": "metodo_X", "experimento_id": "exp1", "grupo": "a"})
        p = P.prescrever(disciplina="Português", acerto_atual=60,
                         diario=_diario_mock(), ab=ab)
        assert p["estrategia"] == "metodo_X"
        assert p["fonte"] == "ab" and p["experimento_id"] == "exp1" and p["grupo"] == "a"

    def test_usa_ranking_quando_sem_ab(self):
        ranking = [{"estrategia": "retrieval_practice", "usos": 5, "eficacia_media": 0.2}]
        p = P.prescrever(disciplina="Português", acerto_atual=60,
                         diario=_diario_mock(ranking), ab=_ab_mock(None))
        assert p["fonte"] == "ranking" and p["estrategia"] == "retrieval_practice"

    def test_cai_no_catalogo(self):
        # sem A/B e ranking fraco (usos < 3) → catálogo por desempenho
        ranking = [{"estrategia": "x", "usos": 1, "eficacia_media": 0.9}]
        p = P.prescrever(disciplina="Português", acerto_atual=60,
                         diario=_diario_mock(ranking), ab=_ab_mock(None))
        assert p["fonte"] == "catalogo" and p["estrategia"] == "estudo_dirigido_erros"

    def test_registra_decisao(self):
        d = _diario_mock()
        p = P.prescrever(disciplina="Matemática", acerto_atual=45, diario=d, ab=_ab_mock(None))
        d.registrar_decisao.assert_called_once()
        assert p["decisao_id"] == "d_123"
        assert "Matemática" in p["prescricao"]


class TestFecharLoop:
    def test_registra_outcome_e_ab(self):
        d = _diario_mock()
        ab = _ab_mock(None)
        r = P.registrar_resultado_prescricao("Português", 72, experimento_id="exp1",
                                             grupo="a", diario=d, ab=ab)
        d.registrar_outcome.assert_called_once_with("Português", 72, questoes=0)
        ab.registrar_resultado.assert_called_once_with("exp1", "a", 72)
        assert r["decisao_atualizada"] and r["ab_atualizado"]

    def test_sem_experimento_nao_chama_ab(self):
        d = _diario_mock()
        ab = _ab_mock(None)
        P.registrar_resultado_prescricao("Português", 72, diario=d, ab=ab)
        ab.registrar_resultado.assert_not_called()


class TestEficacia:
    def test_eficacia_loop_recomenda_melhor(self):
        ranking = [
            {"estrategia": "ruim", "usos": 5, "eficacia_media": -0.1},
            {"estrategia": "boa", "usos": 4, "eficacia_media": 0.15},
        ]
        rel = P.eficacia_loop(diario=_diario_mock(ranking), ab=_ab_mock(None))
        assert rel["estrategia_recomendada"] == "boa"
        assert rel["decisoes"] == 5

    def test_formatar_eficacia(self):
        ranking = [{"estrategia": "boa", "usos": 4, "eficacia_media": 0.15}]
        txt = P.formatar_eficacia(P.eficacia_loop(diario=_diario_mock(ranking), ab=_ab_mock(None)))
        assert "EFICÁCIA DO COACHING" in txt

    def test_formatar_prescricao(self):
        p = {"disciplina": "Port", "estrategia": "x", "prescricao": "faça y",
             "acerto_atual": 60, "fonte": "ab"}
        assert "PRESCRIÇÃO" in P.formatar_prescricao(p)
