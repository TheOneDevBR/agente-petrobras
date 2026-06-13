"""Testes da aderência/accountability (aderencia.py)."""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import aderencia as A  # noqa: E402


def _urgencias(ns):
    return [n["urgencia"] for n in ns]


class TestNudges:
    def test_sem_atividade_cobranca_alta(self):
        ns = A.nudges(streak=0, revisoes_vencidas=0, dias_inativo=None,
                      dias_ate_prova=None, ic=None)
        assert ns and ns[0]["urgencia"] == "alta"
        assert "comece" in ns[0]["texto"].lower() or "Comece" in ns[0]["texto"]

    def test_streak_mantido_hoje_parabeniza(self):
        ns = A.nudges(streak=5, revisoes_vencidas=0, dias_inativo=0,
                      dias_ate_prova=None, ic=0.8)
        assert any("mantido" in n["texto"] and n["urgencia"] == "baixa" for n in ns)

    def test_streak_em_risco(self):
        ns = A.nudges(streak=5, revisoes_vencidas=0, dias_inativo=2,
                      dias_ate_prova=None, ic=0.8)
        assert any("RISCO" in n["texto"] and n["urgencia"] == "alta" for n in ns)

    def test_revisoes_vencidas(self):
        ns = A.nudges(streak=1, revisoes_vencidas=12, dias_inativo=0,
                      dias_ate_prova=None, ic=0.8)
        rev = [n for n in ns if "SM-2" in n["texto"]]
        assert rev and rev[0]["urgencia"] == "alta"  # >=10 → alta

    def test_consistencia_baixa(self):
        ns = A.nudges(streak=1, revisoes_vencidas=0, dias_inativo=0,
                      dias_ate_prova=None, ic=0.3)
        assert any("Consistência" in n["texto"] for n in ns)

    def test_sprint_perto_da_prova(self):
        ns = A.nudges(streak=3, revisoes_vencidas=0, dias_inativo=0,
                      dias_ate_prova=15, ic=0.9)
        assert any("sprint" in n["texto"].lower() and n["urgencia"] == "alta" for n in ns)

    def test_ordenado_por_urgencia(self):
        ns = A.nudges(streak=1, revisoes_vencidas=12, dias_inativo=0,
                      dias_ate_prova=None, ic=0.3)
        u = _urgencias(ns)
        # nenhuma "media/baixa" antes de uma "alta"
        assert u == sorted(u, key=lambda x: {"alta": 0, "media": 1, "baixa": 2}[x])


class TestDiasInativo:
    def test_sem_sessoes(self):
        assert A._dias_inativo([]) is None

    def test_calcula_dias(self):
        ontem = (date.today() - timedelta(days=3)).isoformat()
        assert A._dias_inativo([{"data": ontem}]) == 3


class TestCheckin:
    def test_checkin_monta_estrutura(self):
        hoje = date.today().isoformat()
        sessoes = [{"data": hoje, "questoes": 10}]
        with patch("sm2.estatisticas", return_value={"vencidos": 4}):
            c = A.checkin(perfil={"meta_questoes_semana": 50}, sessoes=sessoes,
                          com_prescricao=False)
        assert c["revisoes_vencidas"] == 4
        assert c["dias_inativo"] == 0
        assert "nudges" in c and isinstance(c["nudges"], list)
        assert c["proxima_acao"] is None  # com_prescricao=False

    def test_formatar_checkin(self):
        with patch("sm2.estatisticas", return_value={"vencidos": 0}):
            c = A.checkin(perfil={}, sessoes=[], com_prescricao=False)
        txt = A.formatar_checkin(c)
        assert "CHECK-IN DIÁRIO" in txt
