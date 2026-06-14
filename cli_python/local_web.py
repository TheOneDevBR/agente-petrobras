"""Ferramentas web locais — substituem Anthropic server-side tools.

Funções:
  web_search(query, max_results=5, force=False) -> list[{"title","url","snippet"}]
  web_fetch(url, max_chars=8000, force=False)   -> str (texto extraído)
"""

from __future__ import annotations

import gzip
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any

import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}

_ULTIMA_BUSCA: float = 0.0
_MAX_RETRIES = 3
_BASE_DELAY = 1.0
_CONNECT_TIMEOUT = 10
_READ_TIMEOUT = 30
_CACHE_DIR = Path(__file__).resolve().parent / ".web_cache"
_CACHE_TTL_SEARCH = 3600
_CACHE_TTL_FETCH = 86400
_CACHE_HITS = 0
_CACHE_MISSES = 0

_session: requests.Session | None = None
_memory_cache: dict[str, tuple[float, Any]] = {}


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(_HEADERS)
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0,
        )
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session


def _cache_key(prefix: str, key: str) -> str:
    return f"{prefix}:{hashlib.md5(key.encode()).hexdigest()}"


def _cache_get(mem_key: str) -> Any | None:
    global _CACHE_HITS, _CACHE_MISSES
    now = time.time()
    if mem_key in _memory_cache:
        expires, val = _memory_cache[mem_key]
        if now < expires:
            _CACHE_HITS += 1
            return val
        del _memory_cache[mem_key]

    cache_file = _CACHE_DIR / f"{mem_key.replace(':', '_')}.json.gz"
    if cache_file.exists():
        try:
            data = json.loads(gzip.decompress(cache_file.read_bytes()))
            if now < data["expires"]:
                _memory_cache[mem_key] = (data["expires"], data["value"])
                _CACHE_HITS += 1
                return data["value"]
            cache_file.unlink(missing_ok=True)
        except (json.JSONDecodeError, OSError):
            cache_file.unlink(missing_ok=True)

    _CACHE_MISSES += 1
    return None


def _cache_set(mem_key: str, value: Any, ttl: int) -> None:
    expires = time.time() + ttl
    _memory_cache[mem_key] = (expires, value)
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = _CACHE_DIR / f"{mem_key.replace(':', '_')}.json.gz"
        cache_file.write_bytes(
            gzip.compress(
                json.dumps({"expires": expires, "value": value}, ensure_ascii=False).encode("utf-8"),
                compresslevel=6,
            )
        )
    except OSError:
        pass


def cache_stats() -> dict[str, int]:
    return {"hits": _CACHE_HITS, "misses": _CACHE_MISSES}


def cache_clear() -> None:
    global _memory_cache, _CACHE_HITS, _CACHE_MISSES
    _memory_cache.clear()
    _CACHE_HITS = _CACHE_MISSES = 0
    try:
        for f in _CACHE_DIR.glob("*.json.gz"):
            f.unlink()
    except OSError:
        pass


def _rate_limit():
    global _ULTIMA_BUSCA
    agora = time.perf_counter()
    if agora - _ULTIMA_BUSCA < 1.0:
        time.sleep(1.0 - (agora - _ULTIMA_BUSCA))
    _ULTIMA_BUSCA = time.perf_counter()


def _retry(fn, *args, **kwargs):
    ultimo_erro = None
    for tentativa in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            ultimo_erro = e
            if tentativa < _MAX_RETRIES - 1:
                delay = _BASE_DELAY * (2 ** tentativa) + random.uniform(0, 0.5)
                print(f"   [retry {tentativa + 1}/{_MAX_RETRIES} em {delay:.1f}s: {e}]")
                time.sleep(delay)
    raise ultimo_erro


def _format_result(r: dict) -> dict[str, Any]:
    return {
        "title": r.get("title", ""),
        "url": r.get("href") or r.get("link", ""),
        "snippet": r.get("body") or r.get("snippet", ""),
    }


def web_search(query: str, max_results: int = 5, force: bool = False) -> list[dict[str, Any]]:
    """Busca na web. Tenta DuckDuckGo API → DuckDuckGo HTML → Google.

    Args:
        query: Termo de busca.
        max_results: Máximo de resultados.
        force: Se True, ignora cache e força nova busca.
    """
    if not force:
        mem_key = _cache_key("search", f"{query}:{max_results}")
        cached = _cache_get(mem_key)
        if cached is not None:
            return cached

    _rate_limit()
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    def _via_ddgs():
        with DDGS() as ddgs:
            return [_format_result(r) for r in ddgs.text(query, max_results=max_results)]

    # 1. DuckDuckGo API
    try:
        resultados = _retry(_via_ddgs)
        if resultados:
            if not force:
                _cache_set(_cache_key("search", f"{query}:{max_results}"),
                           resultados, _CACHE_TTL_SEARCH)
            return resultados
    except Exception:
        pass

    # 2. DuckDuckGo HTML
    try:
        resultados = _retry(_search_via_ddg_html, query, max_results)
        if resultados:
            if not force:
                _cache_set(_cache_key("search", f"{query}:{max_results}"),
                           resultados, _CACHE_TTL_SEARCH)
            return resultados
    except Exception:
        pass

    # 3. Google fallback
    try:
        resultados = _retry(_search_via_google, query, max_results)
        if resultados:
            if not force:
                _cache_set(_cache_key("search", f"{query}:{max_results}"),
                           resultados, _CACHE_TTL_SEARCH)
            return resultados
    except Exception:
        pass

    msg = "Não foi possível buscar após todas as tentativas"
    return [{"title": msg, "url": "", "snippet": ""}]


def _search_via_ddg_html(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    from urllib.parse import quote

    from bs4 import BeautifulSoup

    session = _get_session()
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    resp = session.get(url, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
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


def _detect_encoding(resp: requests.Response) -> str:
    ct = resp.headers.get("Content-Type", "")
    if "charset=" in ct:
        enc = ct.split("charset=")[-1].split(";")[0].strip()
        return enc
    return resp.apparent_encoding or "utf-8"


def web_fetch(url: str, max_chars: int = 8000, force: bool = False) -> str:
    """Faz fetch de uma URL e extrai o texto principal.

    Args:
        url: URL para acessar.
        max_chars: Máximo de caracteres no texto retornado.
        force: Se True, ignora cache e força novo fetch.
    """
    if not force:
        mem_key = _cache_key("fetch", url)
        cached = _cache_get(mem_key)
        if cached is not None:
            return cached

    _rate_limit()

    def _fetch():
        from bs4 import BeautifulSoup
        session = _get_session()
        try:
            resp = session.get(url, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
        except Exception as e:
            if type(e).__name__ != "SSLError":
                raise
            # cert store local incompleto → repete sem verificação (conteúdo público)
            import urllib3
            urllib3.disable_warnings()
            resp = session.get(url, timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT), verify=False)
        resp.raise_for_status()
        enc = _detect_encoding(resp)
        try:
            html = resp.content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            html = resp.content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        text = "\n".join(lines)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n…(conteúdo truncado)"
        return text

    try:
        resultado = _retry(_fetch)
        if not force:
            _cache_set(_cache_key("fetch", url), resultado, _CACHE_TTL_FETCH)
        return resultado
    except Exception as e:
        return f"[erro ao acessar {url}: {e}]"
