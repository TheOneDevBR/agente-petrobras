"""Ferramentas web locais — substituem Anthropic server-side tools.

Funções:
  web_search(query, max_results=5) -> list[{"title","url","snippet"}]
  web_fetch(url, max_chars=8000)   -> str (texto extraído)
"""

from __future__ import annotations

import time
from typing import Any

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}

_ULTIMA_BUSCA: float = 0.0


def _rate_limit():
    global _ULTIMA_BUSCA
    agora = time.time()
    if agora - _ULTIMA_BUSCA < 1.0:
        time.sleep(1.0 - (agora - _ULTIMA_BUSCA))
    _ULTIMA_BUSCA = time.time()


def web_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Busca na web via DuckDuckGo. Fallback para scraping HTML."""
    _rate_limit()
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in results
            ]
    except Exception:
        return _search_fallback(query, max_results)


def _search_fallback(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import quote

        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        resp = requests.get(url, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select(".result")[:max_results]:
            title_el = item.select_one(".result__title a")
            snippet_el = item.select_one(".result__snippet")
            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })
        return results
    except Exception as e:
        return [{"title": f"Erro na busca: {e}", "url": "", "snippet": ""}]


def web_fetch(url: str, max_chars: int = 8000) -> str:
    """Faz fetch de uma URL e extrai o texto principal."""
    _rate_limit()
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n…(conteúdo truncado)"
        return text
    except Exception as e:
        return f"[erro ao acessar {url}: {e}]"
