"""Testes da camada web (local_web.py) com dependências mockadas."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import local_web as lw
from local_web import (
    _cache_key,
    _cache_set,
    _get_session,
    _rate_limit,
    _retry,
    _search_via_ddg_html,
    _search_via_google,
    cache_clear,
    cache_stats,
    web_fetch,
    web_search,
)

# ══════════════════════════════════════════════════════════════════════════
# Cache
# ══════════════════════════════════════════════════════════════════════════

class TestCache:
    def setup_method(self):
        cache_clear()
        lw._CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def test_cache_miss_retorna_none(self):
        from local_web import _cache_get
        assert _cache_get("nonexistent") is None

    def test_cache_set_e_get(self):
        from local_web import _cache_get
        _cache_set("test_key", {"foo": "bar"}, ttl=3600)
        val = _cache_get("test_key")
        assert val == {"foo": "bar"}

    def test_cache_expira(self):
        from local_web import _cache_get
        _cache_set("exp_key", "val", ttl=-1)
        assert _cache_get("exp_key") is None

    def test_cache_stats(self):
        cache_clear()
        _cache_set("k1", "v1", ttl=3600)
        from local_web import _cache_get
        _cache_get("k1")
        _cache_get("k1")
        _cache_get("missing")
        stats = cache_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1

    def test_cache_clear(self):
        from local_web import _cache_get
        _cache_set("k", "v", ttl=3600)
        assert _cache_get("k") == "v"
        cache_clear()
        assert _cache_get("k") is None

    def test_force_ignores_cache(self):
        with (
            patch("ddgs.DDGS", side_effect=Exception("no ddgs")),
            patch("local_web._search_via_ddg_html") as mock_html,
            patch("local_web._rate_limit"),
            patch("local_web._cache_get") as mock_get,
        ):
            mock_get.return_value = [{"title": "cached", "url": "", "snippet": ""}]
            mock_html.return_value = [{"title": "fresh", "url": "", "snippet": ""}]
            resultados = web_search("teste", force=True)
            assert resultados[0]["title"] == "fresh"

    def test_disk_cache_persiste(self):
        from local_web import _cache_get
        _cache_set("disk_k", {"data": 42}, ttl=3600)
        lw._memory_cache.clear()
        val = _cache_get("disk_k")
        assert val == {"data": 42}

    def test_cache_corrompido_ignorado(self):
        from local_web import _cache_get
        bad_file = lw._CACHE_DIR / f"{_cache_key('fetch', 'http://bad.test').replace(':', '_')}.json"
        bad_file.write_text("{corrupt", encoding="utf-8")
        assert _cache_get(_cache_key("fetch", "http://bad.test")) is None

    def teardown_method(self):
        cache_clear()


# ══════════════════════════════════════════════════════════════════════════
# Session
# ══════════════════════════════════════════════════════════════════════════

class TestSession:
    def setup_method(self):
        lw._session = None

    def test_get_session_cria(self):
        s = _get_session()
        assert s is not None
        assert s.headers["User-Agent"].startswith("Mozilla")

    def test_get_session_reusa(self):
        s1 = _get_session()
        s2 = _get_session()
        assert s1 is s2


# ══════════════════════════════════════════════════════════════════════════
# _rate_limit
# ══════════════════════════════════════════════════════════════════════════

class TestRateLimit:
    def setup_method(self):
        lw._ULTIMA_BUSCA = 0.0

    def test_sem_espera_quando_fresco(self):
        inicio = time.perf_counter()
        _rate_limit()
        assert time.perf_counter() - inicio < 0.2

    def test_espera_quando_recente(self):
        lw._ULTIMA_BUSCA = time.perf_counter()
        inicio = time.perf_counter()
        _rate_limit()
        assert time.perf_counter() - inicio >= 0.8


# ══════════════════════════════════════════════════════════════════════════
# _retry
# ══════════════════════════════════════════════════════════════════════════

class TestRetry:
    def test_sucesso_na_primeira(self):
        fn = MagicMock(return_value=42)
        assert _retry(fn) == 42
        fn.assert_called_once()

    def test_sucesso_apos_falhas(self):
        fn = MagicMock(side_effect=[ValueError("tentativa 1"), ValueError("tentativa 2"), "ok"])
        assert _retry(fn) == "ok"
        assert fn.call_count == 3

    def test_esgota_tentativas(self):
        fn = MagicMock(side_effect=ValueError("sempre erro"))
        with pytest.raises(ValueError):
            _retry(fn)
        assert fn.call_count == 3

    def test_delay_exponencial_com_jitter(self):
        fn = MagicMock(side_effect=[ValueError, ValueError, "ok"])
        with patch("local_web.time.sleep") as mock_sleep:
            _retry(fn)
            assert mock_sleep.call_count == 2
            delays = [c[0][0] for c in mock_sleep.call_args_list]
            assert 1.0 <= delays[0] <= 2.0
            assert 2.0 <= delays[1] <= 3.0


# ══════════════════════════════════════════════════════════════════════════
# web_search
# ══════════════════════════════════════════════════════════════════════════

class TestWebSearch:
    def test_via_ddgs(self):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {"title": "Resultado", "href": "https://exemplo.com", "body": "snippet"},
        ]
        with (
            patch("ddgs.DDGS") as mock_ddgs_primario,
            patch("local_web._rate_limit"),
            patch("local_web._cache_get", return_value=None),
        ):
            mock_ddgs_primario.return_value.__enter__.return_value = mock_ddgs_instance
            resultados = web_search("teste")
            assert len(resultados) == 1
            assert resultados[0]["title"] == "Resultado"
            assert resultados[0]["url"] == "https://exemplo.com"

    def test_fallback_ddg_html_quando_ddgs_falha(self):
        with (
            patch("ddgs.DDGS", side_effect=Exception("falha")),
            patch("local_web._rate_limit"),
            patch("local_web._search_via_ddg_html") as mock_html,
            patch("local_web._cache_get", return_value=None),
        ):
            mock_html.return_value = [{"title": "HTML", "url": "https://html.com", "snippet": "via html"}]
            resultados = web_search("teste")
            assert len(resultados) == 1
            assert resultados[0]["title"] == "HTML"

    def test_fallback_google_quando_tudo_falha(self):
        with (
            patch("ddgs.DDGS", side_effect=Exception("falha")),
            patch("local_web._rate_limit"),
            patch("local_web._search_via_ddg_html", side_effect=Exception("falha")),
            patch("local_web._search_via_google") as mock_google,
            patch("local_web._cache_get", return_value=None),
        ):
            mock_google.return_value = [{"title": "Google", "url": "https://google.com", "snippet": "via google"}]
            resultados = web_search("teste")
            assert len(resultados) == 1
            assert resultados[0]["title"] == "Google"

    def test_tudo_falha_retorna_erro(self):
        with (
            patch("ddgs.DDGS", side_effect=Exception("falha")),
            patch("local_web._rate_limit"),
            patch("local_web._search_via_ddg_html", side_effect=Exception("falha")),
            patch("local_web._search_via_google", side_effect=Exception("falha")),
            patch("local_web._cache_get", return_value=None),
        ):
            resultados = web_search("teste")
            assert len(resultados) == 1
            assert "Não foi possível" in resultados[0]["title"]

    def test_cache_hit_retorna_rapido(self):
        with patch("local_web._cache_get") as mock_get:
            mock_get.return_value = [{"title": "cached", "url": "", "snippet": ""}]
            resultados = web_search("teste")
            assert resultados[0]["title"] == "cached"


# ══════════════════════════════════════════════════════════════════════════
# _search_via_ddg_html
# ══════════════════════════════════════════════════════════════════════════

class TestSearchViaDdgHtml:
    def test_parseia_resultados(self):
        html = """
        <html><body>
          <div class="result">
            <div class="result__title"><a href="https://exemplo.com/1">Título 1</a></div>
            <div class="result__snippet">Snippet 1</div>
          </div>
          <div class="result">
            <div class="result__title"><a href="https://exemplo.com/2">Título 2</a></div>
            <div class="result__snippet">Snippet 2</div>
          </div>
        </body></html>
        """
        with (
            patch("local_web._get_session") as mock_session,
            patch("local_web._rate_limit"),
        ):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = html
            mock_session.return_value.get.return_value = mock_resp
            resultados = _search_via_ddg_html("teste", max_results=2)
            assert len(resultados) == 2
            assert resultados[0]["title"] == "Título 1"
            assert resultados[0]["url"] == "https://exemplo.com/1"

    def test_sem_resultados_retorna_vazio(self):
        with (
            patch("local_web._get_session") as mock_session,
            patch("local_web._rate_limit"),
        ):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "<html></html>"
            mock_session.return_value.get.return_value = mock_resp
            assert _search_via_ddg_html("teste") == []


# ══════════════════════════════════════════════════════════════════════════
# _search_via_google
# ══════════════════════════════════════════════════════════════════════════

class TestSearchViaGoogle:
    def test_retorna_urls(self):
        with patch("googlesearch.search") as mock_gs:
            mock_gs.return_value = ["https://a.com", "https://b.com"]
            resultados = _search_via_google("teste", 2)
            assert len(resultados) == 2
            assert resultados[0]["url"] == "https://a.com"
            assert resultados[1]["url"] == "https://b.com"

    def test_vazio_quando_sem_resultados(self):
        with patch("googlesearch.search") as mock_gs:
            mock_gs.return_value = []
            assert _search_via_google("teste") == []

    def test_usa_idioma_portugues(self):
        with patch("googlesearch.search") as mock_gs:
            mock_gs.return_value = []
            _search_via_google("consulta", 3)
            mock_gs.assert_called_with("consulta", num_results=3, lang="pt")


# ══════════════════════════════════════════════════════════════════════════
# web_fetch
# ══════════════════════════════════════════════════════════════════════════

class TestWebFetch:
    def _mock_resp(self, text: str):
        m = MagicMock()
        m.status_code = 200
        m.text = text
        m.headers = {"Content-Type": "text/html; charset=utf-8"}
        m.apparent_encoding = "utf-8"
        m.content = text.encode("utf-8")
        return m

    def test_extrai_texto(self):
        html = "<html><body><p>Olá mundo</p><script>js</script></body></html>"
        with (
            patch("local_web._get_session") as mock_session,
            patch("local_web._rate_limit"),
            patch("local_web._cache_get", return_value=None),
        ):
            mock_session.return_value.get.return_value = self._mock_resp(html)
            texto = web_fetch("https://exemplo.com")
            assert "Olá mundo" in texto
            assert "js" not in texto

    def test_trunca_texto_longo(self):
        with (
            patch("local_web._get_session") as mock_session,
            patch("local_web._rate_limit"),
            patch("local_web._cache_get", return_value=None),
        ):
            mock_session.return_value.get.return_value = self._mock_resp("<p>" + "a" * 1000 + "</p>")
            texto = web_fetch("https://exemplo.com", max_chars=50)
            assert len(texto) <= 100
            assert "truncado" in texto

    def test_erro_retorna_mensagem(self):
        with (
            patch("local_web._get_session", side_effect=Exception("timeout")),
            patch("local_web._rate_limit"),
            patch("local_web._cache_get", return_value=None),
        ):
            texto = web_fetch("https://exemplo.com")
            assert "erro" in texto.lower()

    def test_cache_hit_retorna_rapido(self):
        with patch("local_web._cache_get") as mock_get:
            mock_get.return_value = "conteudo em cache"
            texto = web_fetch("https://exemplo.com")
            assert texto == "conteudo em cache"

    def test_render_false_nao_chama_render(self):
        """Default (render=False): conteúdo curto NÃO dispara o Playwright."""
        with (
            patch("local_web._get_session") as mock_session,
            patch("local_web._rate_limit"),
            patch("local_web._cache_get", return_value=None),
            patch("local_web.web_fetch_render") as mock_render,
        ):
            mock_session.return_value.get.return_value = self._mock_resp("<p>curto</p>")
            texto = web_fetch("https://exemplo.com")
            assert texto == "curto"
            mock_render.assert_not_called()

    def test_render_true_fallback_quando_pobre(self):
        """render=True: conteúdo pobre dispara o fallback de renderização."""
        with (
            patch("local_web._get_session") as mock_session,
            patch("local_web._rate_limit"),
            patch("local_web._cache_get", return_value=None),
            patch("local_web.web_fetch_render", return_value="conteudo renderizado " * 20) as mock_render,
        ):
            mock_session.return_value.get.return_value = self._mock_resp("<p>curto</p>")
            texto = web_fetch("https://spa.exemplo.com", render=True)
            assert "renderizado" in texto
            mock_render.assert_called_once()

    def test_render_true_degrada_se_playwright_ausente(self):
        """render=True mas Playwright indisponível: mantém o texto simples."""
        with (
            patch("local_web._get_session") as mock_session,
            patch("local_web._rate_limit"),
            patch("local_web._cache_get", return_value=None),
            patch("local_web.web_fetch_render", side_effect=RuntimeError("sem playwright")),
        ):
            mock_session.return_value.get.return_value = self._mock_resp("<p>curto</p>")
            texto = web_fetch("https://spa.exemplo.com", render=True)
            assert texto == "curto"


# ══════════════════════════════════════════════════════════════════════════
# web_fetch_render (Playwright / Chromium headless)
# ══════════════════════════════════════════════════════════════════════════

class TestWebFetchRender:
    def test_extrai_texto_renderizado(self):
        from local_web import web_fetch_render

        html = "<html><body><article><p>Conteudo renderizado via JS</p></article>" \
               "<script>app()</script></body></html>"
        mock_page = MagicMock()
        mock_page.content.return_value = html
        mock_browser = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_pw = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_ctx = MagicMock()
        mock_ctx.__enter__.return_value = mock_pw

        fake_sync_api = MagicMock()
        fake_sync_api.sync_playwright.return_value = mock_ctx

        with (
            patch("local_web._cache_get", return_value=None),
            patch("local_web._rate_limit"),
            patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_sync_api}),
        ):
            texto = web_fetch_render("https://spa.exemplo.com")
            assert "Conteudo renderizado via JS" in texto
            assert "app()" not in texto
            mock_browser.close.assert_called_once()

    def test_erro_se_playwright_ausente(self):
        from local_web import web_fetch_render

        with (
            patch("local_web._cache_get", return_value=None),
            patch.dict(sys.modules, {"playwright": None, "playwright.sync_api": None}),
        ):
            with pytest.raises(RuntimeError):
                web_fetch_render("https://spa.exemplo.com")
