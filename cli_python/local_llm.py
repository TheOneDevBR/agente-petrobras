"""Interface universal para LLM local (OpenAI-compatible API).

Suporta: Ollama (>=0.12), LM Studio, llama.cpp, vLLM.
Variáveis de ambiente:
  AGENTE_LLM_BASE_URL  (default: http://localhost:11434)
  AGENTE_LOCAL_MODEL   (default: qwen2.5:7b)
"""

from __future__ import annotations

import json
import os
from typing import Any, Iterator

import requests

DEFAULT_BASE_URL = os.environ.get("AGENTE_LLM_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("AGENTE_LOCAL_MODEL", "qwen2.5:7b")
DEFAULT_TIMEOUT = 180


class LocalLLMError(Exception):
    pass


class LocalLLM:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout

    def _chat_url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    def stream_chat(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 4096,
        **kwargs,
    ) -> Iterator[str]:
        msgs: list[dict] = [{"role": "system", "content": system}]
        msgs.extend(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }
        try:
            resp = requests.post(
                self._chat_url(), json=payload, stream=True, timeout=self.timeout
            )
            resp.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise LocalLLMError(
                f"Não consegui conectar em {self.base_url}.\n"
                "Certifique-se de que o servidor LLM local está rodando "
                "(Ollama, LM Studio, llama.cpp, vLLM).\n"
                f"AGENTE_LLM_BASE_URL={self.base_url}  AGENTE_LOCAL_MODEL={self.model}"
            )
        except requests.exceptions.RequestException as e:
            raise LocalLLMError(f"Erro na requisição: {e}")

        for line in resp.iter_lines():
            if not line:
                continue
            try:
                raw = line.decode("utf-8").strip()
            except UnicodeDecodeError:
                continue
            if not raw:
                continue
            # OpenAI SSE
            if raw.startswith("data: "):
                chunk = raw[6:]
                if chunk == "[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                for choice in data.get("choices", []):
                    content = choice.get("delta", {}).get("content") or ""
                    if content:
                        yield content
            # Ollama native SSE
            elif raw.startswith("{"):
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if "message" in data:
                    content = data["message"].get("content") or ""
                    if content:
                        yield content
                    if data.get("done"):
                        break

    def chat(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 4096,
    ) -> str:
        return "".join(self.stream_chat(system, messages, max_tokens))

    def chat_with_tools(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 12000,
        max_turns: int = 6,
    ) -> str:
        """Chat com tool calling: executa web_search/web_fetch localmente."""
        msgs: list[dict] = [{"role": "system", "content": system}]
        msgs.extend(messages)

        for turn in range(max_turns):
            payload: dict[str, Any] = {
                "model": self.model,
                "messages": msgs,
                "max_tokens": max_tokens,
                "stream": False,
            }
            if tools:
                payload["tools"] = tools

            try:
                resp = requests.post(
                    self._chat_url(), json=payload, timeout=self.timeout
                )
                resp.raise_for_status()
            except requests.exceptions.ConnectionError:
                raise LocalLLMError(
                    f"Não consegui conectar em {self.base_url}. "
                    "Verifique se o servidor LLM local está rodando."
                )
            except requests.exceptions.RequestException as e:
                raise LocalLLMError(f"Erro na requisição: {e}")

            result = resp.json()
            choice = result["choices"][0]
            msg = choice["message"]

            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                return msg.get("content") or ""

            role_content = msg.get("content") or ""
            assistant_msg: dict[str, Any] = {"role": "assistant", "tool_calls": tool_calls}
            if role_content:
                assistant_msg["content"] = role_content
            msgs.append(assistant_msg)

            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    args = {}

                from local_web import web_fetch, web_search

                if name == "web_search":
                    output = json.dumps(
                        web_search(args.get("query", "")), ensure_ascii=False, indent=2
                    )
                elif name == "web_fetch":
                    output = web_fetch(args.get("url", ""))
                else:
                    output = json.dumps({"error": f"Ferramenta desconhecida: {name}"})

                msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": output,
                })

        raise LocalLLMError(
            f"LLM não produziu resposta textual após {max_turns} turnos de ferramentas"
        )
