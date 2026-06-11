"""Testes do loop principal do agente (_processar_entrada) com input mockado."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from agente import _processar_entrada
from local_llm import LocalLLM


@pytest.fixture
def perfil():
    return {
        "cargo_alvo": "Engenheiro",
        "fase_atual": "fundamentos",
        "questoes_resolvidas": 100,
    }


@pytest.fixture
def sessoes():
    return []


@pytest.fixture
def historico():
    return []


@pytest.fixture
def cliente():
    return LocalLLM(base_url="http://mock", model="m")


# ══════════════════════════════════════════════════════════════════════════
# Comandos
# ══════════════════════════════════════════════════════════════════════════

class TestComandos:
    def test_sair_salva_e_retorna_break(self, perfil, sessoes, historico, cliente):
        with (
            patch("agente.perfil_mod.salvar") as mock_salvar,
            patch("agente._gravar_json"),
        ):
            should_break, injetada = _processar_entrada("/sair", perfil, sessoes, historico, cliente)
        assert should_break is True
        assert injetada is None
        mock_salvar.assert_called_once()

    def test_sair_aceita_variantes(self, perfil, sessoes, historico, cliente):
        for cmd in ["/quit", "/exit", "/SAIR"]:
            with (
                patch("agente.perfil_mod.salvar"),
                patch("agente._gravar_json"),
            ):
                should_break, _ = _processar_entrada(cmd, perfil, sessoes, historico, cliente)
            assert should_break is True, f"{cmd} deveria encerrar"

    def test_perfil_sem_break(self, perfil, sessoes, historico, cliente):
        with patch("agente.mostrar_perfil"):
            should_break, injetada = _processar_entrada("/perfil", perfil, sessoes, historico, cliente)
        assert should_break is False
        assert injetada is None

    def test_painel_sem_break(self, perfil, sessoes, historico, cliente):
        with patch("agente.mostrar_painel"):
            should_break, _ = _processar_entrada("/painel", perfil, sessoes, historico, cliente)
        assert should_break is False

    def test_sessao_retorna_msg_injetada(self, perfil, sessoes, historico, cliente):
        with patch("agente.registrar_sessao", return_value="analise os dados"):
            should_break, injetada = _processar_entrada("/sessao", perfil, sessoes, historico, cliente)
        assert should_break is False
        assert injetada == "analise os dados"

    def test_sessao_sem_msg_retorna_none(self, perfil, sessoes, historico, cliente):
        with patch("agente.registrar_sessao", return_value=None):
            should_break, injetada = _processar_entrada("/sessao", perfil, sessoes, historico, cliente)
        assert injetada is None

    def test_salvar_dispara_salvamento(self, perfil, sessoes, historico, cliente):
        with (
            patch("agente.perfil_mod.salvar") as mock_salvar,
            patch("agente._gravar_json") as mock_json,
        ):
            should_break, _ = _processar_entrada("/salvar", perfil, sessoes, historico, cliente)
        assert should_break is False
        mock_salvar.assert_called_once()
        assert mock_json.call_count == 2  # historico + sessoes

    def test_limpar_limpa_historico(self, perfil, sessoes, historico, cliente):
        historico.append({"role": "user", "content": "msg"})
        with patch("agente._gravar_json") as mock_json:
            should_break, _ = _processar_entrada("/limpar", perfil, sessoes, historico, cliente)
        assert should_break is False
        assert len(historico) == 0
        mock_json.assert_called_once()

    def test_reset_confirmado(self, perfil, sessoes, historico, cliente):
        historico.append({"role": "user", "content": "msg"})
        confirm_fn = MagicMock(return_value="s")
        with (
            patch("agente.perfil_mod.salvar") as mock_salvar,
            patch("agente._gravar_json"),
        ):
            should_break, _ = _processar_entrada(
                "/reset", perfil, sessoes, historico, cliente, confirm_fn=confirm_fn,
            )
        assert should_break is False
        assert perfil.get("cargo_alvo") is None  # zerado
        assert perfil.get("questoes_resolvidas") is None
        assert len(historico) == 0
        mock_salvar.assert_called_once()
        confirm_fn.assert_called_once()

    def test_reset_nao_confirmado(self, perfil, sessoes, historico, cliente):
        cargo_antes = perfil["cargo_alvo"]
        confirm_fn = MagicMock(return_value="n")
        should_break, _ = _processar_entrada(
            "/reset", perfil, sessoes, historico, cliente, confirm_fn=confirm_fn,
        )
        assert should_break is False
        assert perfil["cargo_alvo"] == cargo_antes  # inalterado

    def test_turno_normal_chama_agente(self, perfil, sessoes, historico, cliente):
        with patch("agente.chamar_agente") as mock_chamar:
            should_break, _ = _processar_entrada("Quero estudar matemática", perfil, sessoes, historico, cliente)
        assert should_break is False
        mock_chamar.assert_called_once_with(cliente, perfil, sessoes, historico, "Quero estudar matemática")
