"""Testes do cliente LLM (local_llm.py) com HTTP mockado."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from local_llm import LocalLLM, LocalLLMError


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════

def _mock_sse_stream(chunks: list[str], done: bool = True):
    """Gera linhas no formato SSE do OpenAI."""
    lines = []
    for c in chunks:
        lines.append(f"data: {json.dumps(c)}\n".encode())
    if done:
        lines.append(b"data: [DONE]\n")
    return lines


def _mock_ollama_stream(chunks: list[dict], final: dict | None = None):
    """Gera linhas no formato nativo Ollama."""
    lines = []
    for c in chunks:
        lines.append(json.dumps(c).encode() + b"\n")
    if final:
        lines.append(json.dumps(final).encode() + b"\n")
    return lines


def _mock_response(lines: list[bytes]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.iter_lines.return_value = lines
    return resp


# ══════════════════════════════════════════════════════════════════════════
# LocalLLM.__init__
# ══════════════════════════════════════════════════════════════════════════

class TestInit:
    def test_defaults(self):
        llm = LocalLLM()
        assert llm.base_url == "http://127.0.0.1:11434"
        assert llm.model == "qwen2.5:1.5b"

    def test_base_url_sem_barra(self):
        llm = LocalLLM(base_url="http://localhost:11434/")
        assert llm.base_url == "http://localhost:11434"

    def test_chat_url(self):
        llm = LocalLLM(base_url="http://exemplo:8080", model="teste")
        assert llm._chat_url() == "http://exemplo:8080/v1/chat/completions"


# ══════════════════════════════════════════════════════════════════════════
# stream_chat
# ══════════════════════════════════════════════════════════════════════════

class TestStreamChat:
    def test_sse_streaming(self):
        llm = LocalLLM(base_url="http://mock", model="m")
        linhas = _mock_sse_stream([
            {"choices": [{"delta": {"content": "Olá"}}]},
            {"choices": [{"delta": {"content": " "}}]},
            {"choices": [{"delta": {"content": "mundo"}}]},
        ])
        with patch("local_llm.requests.post", return_value=_mock_response(linhas)):
            resultado = list(llm.stream_chat("system", [{"role": "user", "content": "hi"}]))
        assert resultado == ["Olá", " ", "mundo"]

    def test_ollama_native_streaming(self):
        llm = LocalLLM(base_url="http://mock", model="m")
        linhas = _mock_ollama_stream(
            [
                {"message": {"content": "Olá "}},
                {"message": {"content": "mundo"}},
            ],
            {"message": {"content": "!"}, "done": True},
        )
        with patch("local_llm.requests.post", return_value=_mock_response(linhas)):
            resultado = list(llm.stream_chat("system", [{"role": "user", "content": "hi"}]))
        assert resultado == ["Olá ", "mundo", "!"]

    def test_linhas_vazias_ignoradas(self):
        llm = LocalLLM(base_url="http://mock", model="m")
        linhas = [b"", b"\n", b"data: [DONE]\n"]
        with patch("local_llm.requests.post", return_value=_mock_response(linhas)):
            resultado = list(llm.stream_chat("sys", [{"role": "user", "content": "hi"}]))
        assert resultado == []

    def test_connection_error(self):
        llm = LocalLLM(base_url="http://mock", model="m")
        with patch("local_llm.requests.post", side_effect=__import__("requests").exceptions.ConnectionError):
            with pytest.raises(LocalLLMError, match="conectar"):
                list(llm.stream_chat("sys", [{"role": "user", "content": "hi"}]))

    def test_http_error(self):
        llm = LocalLLM(base_url="http://mock", model="m")
        resp = MagicMock()
        resp.raise_for_status.side_effect = __import__("requests").exceptions.HTTPError("404")
        with patch("local_llm.requests.post", return_value=resp):
            with pytest.raises(LocalLLMError, match="404"):
                list(llm.stream_chat("sys", [{"role": "user", "content": "hi"}]))


# ══════════════════════════════════════════════════════════════════════════
# chat
# ══════════════════════════════════════════════════════════════════════════

class TestChat:
    def test_join_streaming(self):
        llm = LocalLLM(base_url="http://mock", model="m")
        linhas = _mock_sse_stream([
            {"choices": [{"delta": {"content": "resposta"}}]},
            {"choices": [{"delta": {"content": " completa"}}]},
        ])
        with patch("local_llm.requests.post", return_value=_mock_response(linhas)):
            texto = llm.chat("sys", [{"role": "user", "content": "hi"}], max_tokens=100)
        assert texto == "resposta completa"

    def test_resposta_vazia(self):
        llm = LocalLLM(base_url="http://mock", model="m")
        linhas = _mock_sse_stream([])
        with patch("local_llm.requests.post", return_value=_mock_response(linhas)):
            texto = llm.chat("sys", [{"role": "user", "content": "hi"}])
        assert texto == ""


# ══════════════════════════════════════════════════════════════════════════
# _parse_tool_call (já testado em test_unit.py, complemento aqui)
# ══════════════════════════════════════════════════════════════════════════

class TestParseToolCall:
    def test_json_simples(self):
        llm = LocalLLM()
        r = llm._parse_tool_call('{"name": "web_search", "arguments": {"query": "teste"}}')
        assert r == ("web_search", {"query": "teste"})

    def test_json_invalido_retorna_none(self):
        llm = LocalLLM()
        assert llm._parse_tool_call("não é json") is None

    def test_sem_name_retorna_none(self):
        llm = LocalLLM()
        assert llm._parse_tool_call('{"x": 1}') is None

    def test_arguments_como_string(self):
        llm = LocalLLM()
        r = llm._parse_tool_call('{"name": "web_fetch", "arguments": "{\\"url\\": \\"https://x.com\\"}"}')
        assert r == ("web_fetch", {"url": "https://x.com"})


# ══════════════════════════════════════════════════════════════════════════
# _execute_tool
# ══════════════════════════════════════════════════════════════════════════

class TestExecuteTool:
    def test_web_search(self):
        llm = LocalLLM()
        with patch("local_web.web_search", return_value=[{"title": "R", "url": "u", "snippet": "s"}]):
            result = llm._execute_tool("web_search", {"query": "teste"}, "call_1")
        assert result["role"] == "tool"
        assert "R" in result["content"]

    def test_web_fetch(self):
        llm = LocalLLM()
        with patch("local_web.web_fetch", return_value="conteúdo"):
            result = llm._execute_tool("web_fetch", {"url": "https://x.com"}, "call_2")
        assert "conteúdo" in result["content"]

    def test_ferramenta_desconhecida(self):
        llm = LocalLLM()
        result = llm._execute_tool("foo", {}, "call_3")
        assert "desconhecida" in result["content"].lower()


# ══════════════════════════════════════════════════════════════════════════
# chat_with_tools
# ══════════════════════════════════════════════════════════════════════════

class TestChatWithTools:
    def test_resposta_direta_sem_tools(self):
        llm = LocalLLM(base_url="http://mock", model="m")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [{"message": {"content": "resposta final", "tool_calls": None}}]
        }
        with patch("local_llm.requests.post", return_value=resp):
            texto = llm.chat_with_tools("sys", [{"role": "user", "content": "hi"}], [])
        assert texto == "resposta final"

    def test_com_tool_call_fallback_textual(self):
        llm = LocalLLM(base_url="http://mock", model="m")

        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = {
            "choices": [{"message": {
                "content": '{"name": "web_search", "arguments": {"query": "petrobras"}}',
                "tool_calls": None,
            }}]
        }

        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = {
            "choices": [{"message": {"content": "resultado da busca", "tool_calls": None}}]
        }

        with (
            patch("local_llm.requests.post", side_effect=[resp1, resp2]),
            patch("local_web.web_search", return_value=[{"title": "R", "url": "u", "snippet": "s"}]),
        ):
            texto = llm.chat_with_tools("sys", [{"role": "user", "content": "busque"}], [{"type": "function", "function": {"name": "web_search"}}], max_turns=3)
        assert texto == "resultado da busca"

    def test_esgota_tentativas(self):
        llm = LocalLLM(base_url="http://mock", model="m")

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [{"message": {
                "content": '{"name": "web_search", "arguments": {"query": "x"}}',
                "tool_calls": None,
            }}]
        }

        with (
            patch("local_llm.requests.post", return_value=resp),
            patch("local_web.web_search", return_value=[]),
        ):
            with pytest.raises(LocalLLMError, match="não produziu resposta"):
                llm.chat_with_tools("sys", [{"role": "user", "content": "busque"}], [{"type": "function", "function": {"name": "web_search"}}], max_turns=2)
