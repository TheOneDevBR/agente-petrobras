"""Testes de integração do agente.py — fluxo de comandos com LLM mockado."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python" / "coletor"))

from agente import (
    _intel_recente,
    chamar_agente,
    montar_system,
    registrar_sessao,
)
from local_llm import LocalLLMError

# ══════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def perfil_vazio():
    return {
        "cargo_alvo": "",
        "fase_atual": "",
        "questoes_resolvidas": 0,
        "horas_acumuladas": 0.0,
        "erro_dominante_historico": None,
        "meta_acerto": 0.8,
        "data_prova": None,
        "historico_acerto": {},
    }


@pytest.fixture
def cliente_mock():
    c = MagicMock()
    c.stream_chat.return_value = iter(["Resposta ", "mockada ", "do ", "agente."])
    c.model = "mock-model"
    c.base_url = "http://mock"
    return c


@pytest.fixture
def sessoes_vazias():
    return []


@pytest.fixture
def historico_vazio():
    return []


# ══════════════════════════════════════════════════════════════════════════
# chamar_agente
# ══════════════════════════════════════════════════════════════════════════

class TestChamarAgente:
    def test_resposta_valida(self, cliente_mock, perfil_vazio, sessoes_vazias, historico_vazio):
        with (
            patch("agente.montar_system") as mock_mount,
            patch("agente.perfil_mod.aplicar_diretivas") as mock_dir,
        ):
            mock_mount.return_value = "system prompt"
            mock_dir.return_value = ("Resposta mockada do agente.", [])

            ok = chamar_agente(cliente_mock, perfil_vazio, sessoes_vazias, historico_vazio, "Olá")
            assert ok is True
            assert len(historico_vazio) == 2
            assert historico_vazio[0] == {"role": "user", "content": "Olá"}
            assert "mockada" in historico_vazio[1]["content"]

    def test_erro_llm_desempilha_historico(self, cliente_mock, perfil_vazio, sessoes_vazias, historico_vazio):
        cliente_mock.stream_chat.side_effect = LocalLLMError("erro simulado")
        with patch("agente.montar_system") as mock_mount:
            mock_mount.return_value = "system"
            ok = chamar_agente(cliente_mock, perfil_vazio, sessoes_vazias, historico_vazio, "teste")
            assert ok is False
            assert len(historico_vazio) == 0

    def test_diretivas_aplicadas(self, cliente_mock, perfil_vazio, sessoes_vazias, historico_vazio):
        with (
            patch("agente.montar_system") as mock_mount,
            patch("agente.perfil_mod.aplicar_diretivas") as mock_dir,
        ):
            mock_mount.return_value = "system"
            mock_dir.return_value = ("texto limpo", ["cargo_alvo = Eng"])

            ok = chamar_agente(cliente_mock, perfil_vazio, sessoes_vazias, historico_vazio, "meu cargo")
            assert ok is True
            # diretivas aplicadas ao texto e perfil
            args, _ = mock_dir.call_args
            assert args[0] == "Resposta mockada do agente."
            assert isinstance(args[1], dict)
            # historico guarda o texto limpo (sem diretivas)
            assert historico_vazio[-1]["content"] == "texto limpo"

    def test_historico_limitado_por_max_turnos(self, cliente_mock, perfil_vazio, sessoes_vazias):
        historico_grande = [{"role": "user", "content": f"msg {i}"} for i in range(50)]
        with patch("agente.montar_system") as mock_mount:
            mock_mount.return_value = "system"
            chamar_agente(cliente_mock, perfil_vazio, sessoes_vazias, historico_grande, "mais uma")
            # Verifica que a janela enviada ao cliente tem no max 40 turnos
            chamado = cliente_mock.stream_chat.call_args
            msgs_enviadas = chamado[1]["messages"]
            assert len(msgs_enviadas) <= 41  # 40 turnos + a nova mensagem
            assert "msg 0" not in str(msgs_enviadas[0])  # antiga foi cortada


# ══════════════════════════════════════════════════════════════════════════
# registrar_sessao
# ══════════════════════════════════════════════════════════════════════════

class TestRegistrarSessao:
    def test_cancela_se_entrada_vazia(self, perfil_vazio, sessoes_vazias):
        with patch("builtins.input", return_value=""):
            resultado = registrar_sessao(perfil_vazio, sessoes_vazias)
            assert resultado is None
            assert len(sessoes_vazias) == 0

    def test_registra_sessao_valida(self, perfil_vazio, sessoes_vazias):
        entradas = iter(["Matemática", "45", "10", "8", "C"])
        with (
            patch("builtins.input", side_effect=lambda _="": next(entradas)),
            patch("agente._gravar_json"),
            patch("agente.perfil_mod.salvar"),
        ):
            resultado = registrar_sessao(perfil_vazio, sessoes_vazias)
            assert resultado is not None
            assert "Matemática" in resultado
            assert "80.0%" in resultado
            assert len(sessoes_vazias) == 1
            assert sessoes_vazias[0]["disciplina"] == "Matemática"
            assert sessoes_vazias[0]["acerto_pct"] == 80.0
            assert sessoes_vazias[0]["questoes"] == 10

    def test_registra_sem_erro_dominante(self, perfil_vazio, sessoes_vazias):
        entradas = iter(["Português", "30", "5", "5", ""])
        with (
            patch("builtins.input", side_effect=lambda _="": next(entradas)),
            patch("agente._gravar_json"),
            patch("agente.perfil_mod.salvar"),
        ):
            resultado = registrar_sessao(perfil_vazio, sessoes_vazias)
            assert resultado is not None
            assert sessoes_vazias[0]["erro_dominante"] is None

    def test_questoes_zero_nao_quebra(self, perfil_vazio, sessoes_vazias):
        entradas = iter(["Revisão", "60", "0", "0", ""])
        with (
            patch("builtins.input", side_effect=lambda _="": next(entradas)),
            patch("agente._gravar_json"),
            patch("agente.perfil_mod.salvar"),
        ):
            resultado = registrar_sessao(perfil_vazio, sessoes_vazias)
            assert resultado is not None
            assert "60min" in resultado
            assert sessoes_vazias[0]["acerto_pct"] is None


# ══════════════════════════════════════════════════════════════════════════
# montar_system
# ══════════════════════════════════════════════════════════════════════════

class TestMontarSystem:
    def test_inclui_painel_e_perfil(self, perfil_vazio, sessoes_vazias):
        with (
            patch("agente.PROMPT_PATH") as mock_prompt,
            patch("agente.met.painel") as mock_painel,
            patch("agente._intel_recente", return_value=""),
            patch("agente.perfil_mod.resumo_para_prompt") as mock_resumo,
        ):
            mock_prompt.read_text.return_value = "PROMPT_BASE"
            mock_painel.return_value = "[PAINEL_DE_CONTROLE]"
            mock_resumo.return_value = "perfil resumido"

            system = montar_system(perfil_vazio, sessoes_vazias)
            assert "Responda SEMPRE em português do Brasil." in system
            assert "PROMPT_BASE" in system
            assert "[PAINEL_DE_CONTROLE]" in system
            assert "perfil resumido" in system

    def test_intel_recente_incluido_quando_existe(self, perfil_vazio, sessoes_vazias):
        with (
            patch("agente.PROMPT_PATH") as mock_prompt,
            patch("agente.met.painel", return_value=""),
            patch("agente._intel_recente", return_value="Resumo de inteligência"),
            patch("agente.perfil_mod.resumo_para_prompt", return_value=""),
        ):
            mock_prompt.read_text.return_value = "PROMPT_BASE"
            system = montar_system(perfil_vazio, sessoes_vazias)
            assert "Resumo de inteligência" in system
            assert "[INTEL_RECENTE]" in system


# ══════════════════════════════════════════════════════════════════════════
# _intel_recente
# ══════════════════════════════════════════════════════════════════════════

class TestIntelRecente:
    def test_sem_arquivo_retorna_vazio(self):
        inexistente = Path(tempfile.mkdtemp()) / "_inexistente.md"
        with patch("agente.INTEL_MOC", inexistente):
            assert _intel_recente() == ""

    def test_com_arquivo_retorna_conteudo(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("---\ntitulo: MOC\n---\n\n# Resumo\n\nConteúdo do resumo.")
            tmp = Path(f.name)
        try:
            with patch("agente.INTEL_MOC", tmp):
                resultado = _intel_recente()
                assert "Conteúdo do resumo" in resultado
        finally:
            tmp.unlink(missing_ok=True)

    def test_frontmatter_removido(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("---\ntitulo: antigo\n---\n\ntexto real")
            tmp = Path(f.name)
        try:
            with patch("agente.INTEL_MOC", tmp):
                resultado = _intel_recente()
                assert "titulo:" not in resultado
                assert "texto real" in resultado
        finally:
            tmp.unlink(missing_ok=True)

    def test_trunca_se_muito_longo(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("a" * 5000)
            tmp = Path(f.name)
        try:
            with patch("agente.INTEL_MOC", tmp), patch("agente.INTEL_MAX_CHARS", 100):
                resultado = _intel_recente()
                assert len(resultado) <= 200  # 100 chars + "...(ver notas completas...)"
                assert "ver notas completas" in resultado
        finally:
            tmp.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════
# Slug sem acentos (agora normaliza via unicodedata)
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("entrada, esperado", [
    ("Tendências de cobrança", "tendencias-de-cobranca"),
    ("Notícias e Atualidades", "noticias-e-atualidades"),
    ("Legislação Aplicável (Lei 13.303)", "legislacao-aplicavel-lei-13303"),
    (" Língua   Portuguesa ", "lingua-portuguesa"),
    ("", "nota"),
])
def test_slug_sem_acentos(entrada, esperado):
    import importlib
    slug_mod = importlib.import_module("coletor")
    assert slug_mod._slug(entrada) == esperado
