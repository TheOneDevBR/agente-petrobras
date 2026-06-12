"""Testes do loop principal do agente (_processar_entrada) com input mockado."""

from __future__ import annotations

import sys
from datetime import date, timedelta
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

    def test_relatorio_comando(self, perfil, sessoes, historico, cliente):
        with (
            patch("agente.met.relatorio_semanal_md") as mock_md,
            patch("agente.met.exportar_html") as mock_html,
        ):
            mock_md.return_value = "# Relatorio"
            should_break, _ = _processar_entrada("/relatorio", perfil, sessoes, historico, cliente)
        assert should_break is False
        mock_md.assert_called_once_with(perfil, sessoes)
        mock_html.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════
# agente.py — gaps de cobertura (funções auxiliares)
# ══════════════════════════════════════════════════════════════════════════

class TestCor:
    def test_com_cor(self):
        from agente import _cor, C
        colored = _cor("texto", C.VERDE)
        assert C.VERDE in colored
        assert "texto" in colored

    def test_no_color_env(self):
        from agente import _cor
        with patch.dict("os.environ", {"NO_COLOR": "1"}):
            assert _cor("texto", "\033[32m") == "texto"


class TestLerJson:
    def test_arquivo_existe(self, tmp_path):
        from agente import _ler_json
        f = tmp_path / "dados.json"
        f.write_text('{"chave": "valor"}', encoding="utf-8")
        assert _ler_json(f, {}) == {"chave": "valor"}

    def test_arquivo_inexistente(self, tmp_path):
        from agente import _ler_json
        assert _ler_json(tmp_path / "inexistente.json", []) == []

    def test_json_corrupto(self, tmp_path):
        from agente import _ler_json
        f = tmp_path / "corrupto.json"
        f.write_text("{corrupto}", encoding="utf-8")
        assert _ler_json(f, {}) == {}


class TestBanner:
    def test_perfil_vazio(self, capsys):
        from agente import banner
        from perfil import perfil_vazio
        banner(perfil_vazio(), [])
        out = capsys.readouterr().out
        assert "AGENTE PETROBRAS" in out
        assert "diagnóstico" in out

    def test_perfil_preenchido(self, capsys):
        from agente import banner
        p = {"cargo_alvo": "Engenheiro", "fase_atual": "FUNDACAO",
             "data_prova": "2026-12-31"}
        banner(p, [{"data": "2026-06-10"}])
        out = capsys.readouterr().out
        assert "Engenheiro" in out
        assert "FUNDACAO" in out
        assert "d p/ prova" in out


class TestMostrarPerfil:
    def test_mostra_campos_relevantes(self, capsys):
        from agente import mostrar_perfil
        p = {"cargo_alvo": "Engenheiro", "questoes_resolvidas": 100,
             "distribuicao_erros": {"C": None}, "tendencia": {}}
        mostrar_perfil(p)
        out = capsys.readouterr().out
        assert "PERFIL DO CANDIDATO" in out
        assert "Engenheiro" in out
        assert "tendencia" not in out  # dict vazio filtrado


class TestMostrarPainel:
    def test_com_dados(self, capsys):
        from agente import mostrar_painel
        hoje = date.today()
        perfil = {"data_prova": (hoje + timedelta(days=60)).isoformat()}
        mostrar_painel(perfil, [{"data": hoje.isoformat()}])
        out = capsys.readouterr().out
        assert "PAINEL_DE_CONTROLE" in out

    def test_sem_dados(self, capsys):
        from agente import mostrar_painel
        mostrar_painel({}, [])
        out = capsys.readouterr().out
        assert "Sem dados suficientes" in out


class TestInputInt:
    def test_vazio_retorna_default(self):
        from agente import _input_int
        with patch("builtins.input", return_value=""):
            assert _input_int("quantos?", 42) == 42

    def test_valor_invalido_retorna_default(self):
        from agente import _input_int
        with patch("builtins.input", return_value="abc"):
            assert _input_int("quantos?", 42) == 42

    def test_valor_valido(self):
        from agente import _input_int
        with patch("builtins.input", return_value="10"):
            assert _input_int("quantos?") == 10


class TestGerarRelatorio:
    def test_cria_arquivo(self, tmp_path, capsys):
        from agente import gerar_relatorio
        with patch("agente.RELATORIOS_DIR", tmp_path):
            gerar_relatorio({"cargo_alvo": "X"}, [])
            files = list(tmp_path.iterdir())
            assert len(files) == 1
            assert files[0].suffix == ".md"
        out = capsys.readouterr().out
        assert "Relatório salvo" in out


# ── API (FastAPI) ───────────────────────────────────────────────────
class TestAPI:
    def test_root_endpoint(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "api" in data
        assert "AgentePetrobras" in data["api"]

    def test_perfil_endpoint(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/perfil")
        assert resp.status_code == 200
        data = resp.json()
        assert "perfil" in data
        assert "sessoes" in data

    def test_metricas_endpoint(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/metricas")
        assert resp.status_code == 200

    def test_banco_questoes_endpoint(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/banco-questoes")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "pergunta" in data[0]

    def test_banco_questoes_filtro(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/banco-questoes?disciplina=Legislação")
        assert resp.status_code == 200
        data = resp.json()
        for q in data:
            assert q["disciplina"] == "Legislação"

    def test_simulado_iniciar_sem_questoes(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/simulado/iniciar", json={"n_questoes": 5, "disciplina": "Inexistente"})
        assert resp.status_code == 400

    def test_perfil_atualizar(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/perfil/atualizar", json={"cargo_alvo": "Teste"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_sessoes_listar(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/sessoes")
        assert resp.status_code == 200

    def test_simulados_listar(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/simulados")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_relatorio_endpoint(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/relatorio")
        assert resp.status_code == 200
        data = resp.json()
        assert "markdown" in data

    def test_redoc_endpoint(self):
        from api import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/redoc")
        assert resp.status_code == 200
