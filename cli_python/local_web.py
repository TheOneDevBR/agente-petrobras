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
_MAX_RETRIES = 3
_BASE_DELAY = 2.0  # segundos


def _rate_limit():
    global _ULTIMA_BUSCA
    agora = time.time()
    if agora - _ULTIMA_BUSCA < 1.0:
        time.sleep(1.0 - (agora - _ULTIMA_BUSCA))
    _ULTIMA_BUSCA = time.time()


def _retry(fn, *args, **kwargs):
    """Tenta executar fn até _MAX_RETRIES vezes com backoff exponencial."""
    ultimo_erro = None
    for tentativa in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            ultimo_erro = e
            if tentativa < _MAX_RETRIES - 1:
                delay = _BASE_DELAY * (2 ** tentativa)
                print(f"   [retry {tentativa + 1}/{_MAX_RETRIES} em {delay:.0f}s: {e}]")
                time.sleep(delay)
    raise ultimo_erro  # type: ignore[misc]


def _format_result(r: dict) -> dict[str, Any]:
    """Normaliza resultado de busca para formato padrão."""
    return {
        "title": r.get("title", ""),
        "url": r.get("href") or r.get("link", ""),
        "snippet": r.get("body") or r.get("snippet", ""),
    }


def web_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Busca na web. Tenta DuckDuckGo API → DuckDuckGo HTML → Google."""
    _rate_limit()

    # 1. DuckDuckGo via API
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    def _via_ddgs():
        with DDGS() as ddgs:
            return [_format_result(r) for r in ddgs.text(query, max_results=max_results)]

    try:
        return _retry(_via_ddgs)
    except Exception:
        pass

    # 2. Fallback: scrape DuckDuckGo HTML
    try:
        return _retry(_search_via_ddg_html, query, max_results)
    except Exception:
        pass

    # 3. Fallback: Google (googlesearch-python)
    try:
        return _retry(_search_via_google, query, max_results)
    except Exception as e:
        return [{"title": f"Não foi possível buscar: {e}", "url": "", "snippet": ""}]


def _search_via_ddg_html(query: str, max_results: int = 5) -> list[dict[str, Any]]:
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


def _search_via_google(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    from googlesearch import search as gs

    results = []
    for url in gs(query, num_results=max_results, lang="pt"):
        results.append({"title": "", "url": url, "snippet": ""})
    return results


def web_fetch(url: str, max_chars: int = 8000) -> str:
    """Faz fetch de uma URL e extrai o texto principal."""
    _rate_limit()

    def _fetch():
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

    try:
        return _retry(_fetch)
    except Exception as e:
        return f"[erro ao acessar {url}: {e}]"
