"""Testes da API REST (FastAPI)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from api import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_dados(tmp_path):
    dados = tmp_path / "dados"
    dados.mkdir()
    return dados


class TestRoot:
    def test_root(self, client, monkeypatch):
        with (
            patch("api.PERFIL_PATH", Path("/nonexistent/perfil.json")),
            patch("api.SESSOES_PATH", Path("/nonexistent/sessoes.json")),
            patch("api.SIMULADOS_PATH", Path("/nonexistent/simulados.json")),
        ):
            resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "api" in data
        assert "AgentePetrobras" in data["api"]


class TestPerfil:
    def test_get_perfil_vazio(self, client):
        with (
            patch("api.PERFIL_PATH", Path("/nonexistent/perfil.json")),
            patch("api.SESSOES_PATH", Path("/nonexistent/sessoes.json")),
            patch("api.SIMULADOS_PATH", Path("/nonexistent/simulados.json")),
        ):
            resp = client.get("/perfil")
        assert resp.status_code == 200
        data = resp.json()
        assert data["perfil"] == {}
        assert data["sessoes"] == 0
        assert data["simulados"] == 0

    def test_atualizar_perfil(self, client, tmp_path):
        perfil_path = tmp_path / "perfil.json"
        perfil_path.write_text('{"cargo_alvo": "Engenheiro"}', encoding="utf-8")
        with (
            patch("api.PERFIL_PATH", perfil_path),
            patch("api.SESSOES_PATH", Path("/nonexistent/sessoes.json")),
            patch("api.SIMULADOS_PATH", Path("/nonexistent/simulados.json")),
        ):
            resp = client.post("/perfil/atualizar", json={"cargo_alvo": "Analista", "horas_dia": 4})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "cargo_alvo" in data["campos"]
        assert "horas_dia" in data["campos"]
        assert json.loads(perfil_path.read_text(encoding="utf-8"))["cargo_alvo"] == "Analista"


class TestSessoes:
    def test_listar_sessoes_vazias(self, client):
        with patch("api.SESSOES_PATH", Path("/nonexistent/sessoes.json")):
            resp = client.get("/sessoes")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_listar_sessoes_com_dados(self, client, tmp_path):
        sessoes_path = tmp_path / "sessoes.json"
        dados = [{"data": "2026-01-02", "disciplina": "Português"}, {"data": "2026-01-01", "disciplina": "Matemática"}]
        sessoes_path.write_text(json.dumps(dados), encoding="utf-8")
        with patch("api.SESSOES_PATH", sessoes_path):
            resp = client.get("/sessoes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["disciplina"] == "Português"

    def test_listar_sessoes_com_limite(self, client, tmp_path):
        sessoes_path = tmp_path / "sessoes.json"
        dados = [{"data": f"2026-01-{i:02d}", "disciplina": f"Disc{i}"} for i in range(30)]
        sessoes_path.write_text(json.dumps(dados), encoding="utf-8")
        with patch("api.SESSOES_PATH", sessoes_path):
            resp = client.get("/sessoes?limite=5")
        assert resp.status_code == 200
        assert len(resp.json()) == 5


class TestSimulados:
    def test_listar_simulados_vazios(self, client):
        with patch("api.SIMULADOS_PATH", Path("/nonexistent/simulados.json")):
            resp = client.get("/simulados")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_listar_simulados_com_dados(self, client, tmp_path):
        sim_path = tmp_path / "simulados.json"
        dados = [{"data": "2026-01-02", "pct": 80.0}]
        sim_path.write_text(json.dumps(dados), encoding="utf-8")
        with patch("api.SIMULADOS_PATH", sim_path):
            resp = client.get("/simulados")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestRelatorio:
    def test_relatorio_md(self, client):
        with (
            patch("api.PERFIL_PATH", Path("/nonexistent/perfil.json")),
            patch("api.SESSOES_PATH", Path("/nonexistent/sessoes.json")),
        ):
            resp = client.get("/relatorio")
        assert resp.status_code == 200
        data = resp.json()
        assert "markdown" in data
        assert "html" in data

    def test_relatorio_html(self, client):
        with (
            patch("api.PERFIL_PATH", Path("/nonexistent/perfil.json")),
            patch("api.SESSOES_PATH", Path("/nonexistent/sessoes.json")),
            patch("metricas.exportar_html", return_value="<html>relatorio</html>"),
        ):
            resp = client.get("/relatorio?formato=html")
        assert resp.status_code == 200
        data = resp.json()
        assert data["html"] == "<html>relatorio</html>"


class TestRedoc:
    def test_redoc_disponivel(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200
        assert "redoc" in resp.text.lower()

    def test_docs_disponivel(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert "swagger" in resp.text.lower()


class TestSessaoRegistrar:
    def test_registrar_sessao(self, client, tmp_path):
        perfil_path = tmp_path / "perfil.json"
        perfil_path.write_text('{"cargo_alvo": "Engenheiro"}', encoding="utf-8")
        sessoes_path = tmp_path / "sessoes.json"
        sessoes_path.write_text("[]", encoding="utf-8")
        with (
            patch("api.PERFIL_PATH", perfil_path),
            patch("api.SESSOES_PATH", sessoes_path),
            patch("agente.registrar_sessao", return_value="Sessão registrada!"),
        ):
            resp = client.post("/sessao", json={"disciplina": "Português", "questoes": 20, "acertos": 15, "minutos": 60})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "Sessão registrada!" in data["mensagem"]


class TestPerguntarSucesso:
    def test_perguntar_sucesso(self, client, tmp_path):
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "Resposta do LLM"
        dados_dir = tmp_path / "dados"
        dados_dir.mkdir()
        perfil_path = dados_dir / "perfil.json"
        perfil_path.write_text("{}", encoding="utf-8")
        sessoes_path = dados_dir / "sessoes.json"
        sessoes_path.write_text("[]", encoding="utf-8")
        hist_path = dados_dir / "historico_conversa.json"
        hist_path.write_text("[]", encoding="utf-8")
        with (
            patch("api.LocalLLM", return_value=mock_llm),
            patch("api.PERFIL_PATH", perfil_path),
            patch("api.SESSOES_PATH", sessoes_path),
            patch("api.DADOS", dados_dir),
            patch("agente.montar_system", return_value="system prompt"),
        ):
            resp = client.post("/perguntar", json={"mensagem": "Qual a lei?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["resposta"] == "Resposta do LLM"
        assert data["pergunta"] == "Qual a lei?"

    def test_perguntar_escreve_historico(self, client, tmp_path):
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "Resposta"
        dados_dir = tmp_path / "dados"
        dados_dir.mkdir()
        perfil_path = dados_dir / "perfil.json"
        perfil_path.write_text("{}", encoding="utf-8")
        sessoes_path = dados_dir / "sessoes.json"
        sessoes_path.write_text("[]", encoding="utf-8")
        hist_path = dados_dir / "historico_conversa.json"
        hist_path.write_text("[]", encoding="utf-8")
        with (
            patch("api.LocalLLM", return_value=mock_llm),
            patch("api.PERFIL_PATH", perfil_path),
            patch("api.SESSOES_PATH", sessoes_path),
            patch("api.DADOS", dados_dir),
            patch("agente.montar_system", return_value="system"),
        ):
            client.post("/perguntar", json={"mensagem": "Ola"})
        hist = json.loads(hist_path.read_text(encoding="utf-8"))
        assert len(hist) == 2
        assert hist[0]["role"] == "user"
        assert hist[1]["role"] == "assistant"


class TestErrorHandling:
    def test_prova_completa_nao_disponivel(self, client):
        with patch("api.hasattr", return_value=False):
            resp = client.post("/prova-completa")
        assert resp.status_code == 501

    def test_perguntar_llm_indisponivel(self, client):
        with (
            patch("api.LocalLLM", side_effect=Exception("LLM nao encontrado")),
            patch("api.PERFIL_PATH", Path("/nonexistent/perfil.json")),
            patch("api.SESSOES_PATH", Path("/nonexistent/sessoes.json")),
        ):
            resp = client.post("/perguntar", json={"mensagem": "ola"})
        assert resp.status_code == 500
        assert "LLM" in resp.json()["detail"]

    def test_perguntar_erro_chat(self, client):
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = Exception("Erro no chat")
        with (
            patch("api.LocalLLM", return_value=mock_llm),
            patch("api.PERFIL_PATH", Path("/nonexistent/perfil.json")),
            patch("api.SESSOES_PATH", Path("/nonexistent/sessoes.json")),
        ):
            resp = client.post("/perguntar", json={"mensagem": "ola"})
        assert resp.status_code == 500
        assert "Erro no LLM" in resp.json()["detail"]

    def test_simulado_iniciar_erro(self, client):
        with patch("treino.iniciar_simulado", return_value={"erro": "disciplina invalida"}):
            resp = client.post("/simulado/iniciar", json={"disciplina": "invalida"})
        assert resp.status_code == 400
        assert "disciplina invalida" in resp.json()["detail"]

    def test_simulado_iniciar_sucesso(self, client):
        with patch("treino.iniciar_simulado", return_value={"questoes": 5, "acertos": 3}):
            resp = client.post("/simulado/iniciar", json={"n_questoes": 5, "disciplina": "Matemática"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["questoes"] == 5

    def test_json_decode_error_leitura(self, client, tmp_path):
        perfil_path = tmp_path / "perfil.json"
        perfil_path.write_text("invalid json{", encoding="utf-8")
        with (
            patch("api.PERFIL_PATH", perfil_path),
            patch("api.SESSOES_PATH", Path("/nonexistent/sessoes.json")),
            patch("api.SIMULADOS_PATH", Path("/nonexistent/simulados.json")),
        ):
            resp = client.get("/")
        assert resp.status_code == 200


class TestPratica:
    def _fake_q(self):
        from types import SimpleNamespace
        return SimpleNamespace(
            pergunta="Qual a capital do Brasil?",
            opcoes=["SP", "DF", "RJ", "BA", "MG"],
            correta=1, explicacao="É a B (DF).", disciplina="Geografia", tags=[],
        )

    def test_proxima_nao_vaza_resposta(self, client):
        q = self._fake_q()
        with (
            patch("treino.selecionar_questoes", return_value=[q]),
            patch("treino.banco", return_value=[]),
            patch("sm2.revisoes_devidas", return_value=[]),
        ):
            resp = client.get("/pratica/proxima")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pergunta"] == "Qual a capital do Brasil?"
        assert len(data["opcoes"]) == 5
        assert "correta" not in data and "correta_idx" not in data
        assert data["tipo"] == "nova"

    def test_proxima_serve_revisao_devida(self, client):
        q = self._fake_q()
        import api
        card = {"questao_idx": api._qidx(q), "disciplina": "Geografia", "pergunta": q.pergunta}
        with (
            patch("treino.banco", return_value=[q]),
            patch("sm2.revisoes_devidas", return_value=[card]),
        ):
            resp = client.get("/pratica/proxima")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tipo"] == "revisao"
        assert data["revisoes_pendentes"] == 1

    def test_proxima_sem_questoes_404(self, client):
        with (
            patch("treino.selecionar_questoes", return_value=[]),
            patch("treino.banco", return_value=[]),
            patch("sm2.revisoes_devidas", return_value=[]),
        ):
            resp = client.get("/pratica/proxima")
        assert resp.status_code == 404

    def test_responder_correto(self, client):
        q = self._fake_q()
        with (
            patch("treino.selecionar_questoes", return_value=[q]),
            patch("treino.banco", return_value=[q]),
            patch("sm2.revisoes_devidas", return_value=[]),
            patch("sm2.registrar_revisao", return_value=[]),
            patch("rag.buscar", return_value=[]),
        ):
            qid = client.get("/pratica/proxima").json()["id"]
            resp = client.post("/pratica/responder", json={"id": qid, "escolha": 1, "tempo_seg": 20})
        assert resp.status_code == 200
        data = resp.json()
        assert data["correta"] is True
        assert data["correta_idx"] == 1
        assert "DF" in data["explicacao"]

    def test_responder_errado(self, client):
        q = self._fake_q()
        with (
            patch("treino.selecionar_questoes", return_value=[q]),
            patch("treino.banco", return_value=[q]),
            patch("sm2.revisoes_devidas", return_value=[]),
            patch("sm2.registrar_revisao", return_value=[]),
            patch("rag.buscar", return_value=[]),
        ):
            qid = client.get("/pratica/proxima").json()["id"]
            resp = client.post("/pratica/responder", json={"id": qid, "escolha": 0})
        assert resp.status_code == 200
        assert resp.json()["correta"] is False

    def test_responder_id_invalido_404(self, client):
        with patch("treino.banco", return_value=[]):
            resp = client.post("/pratica/responder", json={"id": "inexistente", "escolha": 0})
        assert resp.status_code == 404

    def test_coach_feedback(self, client):
        q = self._fake_q()
        with (
            patch("treino.selecionar_questoes", return_value=[q]),
            patch("treino.banco", return_value=[q]),
            patch("sm2.revisoes_devidas", return_value=[]),
            patch("api.LocalLLM", return_value=MagicMock()),
            patch("treino._feedback_llm", return_value="Porque DF é a capital federal."),
        ):
            qid = client.get("/pratica/proxima").json()["id"]
            resp = client.post("/pratica/coach", json={"id": qid, "escolha": 0})
        assert resp.status_code == 200
        assert "capital" in resp.json()["feedback"]

    def test_classificar_erro(self, client):
        with patch("erros.registrar_erro") as mock_reg:
            resp = client.post("/pratica/classificar", json={"disciplina": "Geografia", "categoria": "C"})
        assert resp.status_code == 200
        assert resp.json()["categoria"] == "C"
        mock_reg.assert_called_once()


class TestAutonomiaAPI:
    def test_disparar_ciclo(self, client):
        mock_llm = MagicMock()
        with (
            patch("api.LocalLLM", return_value=mock_llm),
            patch("ciclo_evolutivo.executar_ciclo", return_value={"sucesso": True}) as mock_exec
        ):
            resp = client.post("/ciclo")
        assert resp.status_code == 200
        assert resp.json() == {"sucesso": True}
        mock_exec.assert_called_once()

    def test_disparar_autonomia(self, client):
        with patch("autonomia.ciclo_autonomo", return_value={"status": "ok"}) as mock_ciclo:
            resp = client.post("/autonomia/ciclo")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        mock_ciclo.assert_called_once_with(permitir_sensiveis=False, aprender=True)

    def test_autonomia_diagnostico(self, client):
        mock_info = MagicMock()
        mock_info.metricas = MagicMock()
        with (
            patch("autonomia.autodiagnostico_completo", return_value=mock_info),
            patch("autonomia.painel_comando", return_value="painel text"),
            patch("dataclasses.asdict", return_value={"modulos_python": 5})
        ):
            resp = client.get("/autonomia/diagnostico")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot"] == {"modulos_python": 5}
        assert data["painel"] == "painel text"

    def test_autonomia_gaps(self, client):
        mock_info = MagicMock()
        mock_gap = MagicMock()
        with (
            patch("autonomia.autodiagnostico_completo", return_value=mock_info),
            patch("autonomia.analisar_gaps", return_value=[mock_gap]),
            patch("dataclasses.asdict", return_value={"nome": "gap1"})
        ):
            resp = client.get("/autonomia/gaps")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["nome"] == "gap1"
