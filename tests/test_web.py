"""Testes da camada web (local_web.py) com dependências mockadas."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from local_web import (
    web_search,
    web_fetch,
    _retry,
    _rate_limit,
    _ULTIMA_BUSCA,
    _search_via_ddg_html,
    _search_via_google,
)


# ══════════════════════════════════════════════════════════════════════════
# _rate_limit
# ══════════════════════════════════════════════════════════════════════════

class TestRateLimit:
    def setup_method(self):
        global _ULTIMA_BUSCA
        _ULTIMA_BUSCA = 0.0

    def test_sem_espera_quando_fresco(self):
        inicio = time.time()
        _rate_limit()
        assert time.time() - inicio < 0.2

    def test_espera_quando_recente(self):
        global _ULTIMA_BUSCA
        _ULTIMA_BUSCA = time.time()
        inicio = time.time()
        _rate_limit()
        assert time.time() - inicio >= 0.8


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

    def test_delay_exponencial(self):
        fn = MagicMock(side_effect=[ValueError, ValueError, "ok"])
        with patch("local_web.time.sleep") as mock_sleep:
            _retry(fn)
            assert mock_sleep.call_count == 2
            delays = [c[0][0] for c in mock_sleep.call_args_list]
            assert delays == [2.0, 4.0]


# ══════════════════════════════════════════════════════════════════════════
# web_search
# ══════════════════════════════════════════════════════════════════════════

class TestWebSearch:
    def test_via_ddgs(self):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {"title": "Resultado", "href": "https://exemplo.com", "body": "snippet"},
        ]
        # PATCH AMBOS os módulos (ddgs é o primário, duckduckgo_search é fallback)
        with (
            patch("ddgs.DDGS") as mock_ddgs_primario,
            patch("local_web._rate_limit"),
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
        ):
            resultados = web_search("teste")
            assert len(resultados) == 1
            assert "Erro" in resultados[0]["title"] or "Não foi possível" in resultados[0]["title"]


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
            patch("requests.get") as mock_get,
            patch("local_web._rate_limit"),
        ):
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = html
            resultados = _search_via_ddg_html("teste", max_results=2)
            assert len(resultados) == 2
            assert resultados[0]["title"] == "Título 1"
            assert resultados[0]["url"] == "https://exemplo.com/1"

    def test_sem_resultados_retorna_vazio(self):
        with (
            patch("requests.get") as mock_get,
            patch("local_web._rate_limit"),
        ):
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "<html></html>"
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
    def test_extrai_texto(self):
        html = "<html><body><p>Olá mundo</p><script>js</script></body></html>"
        with (
            patch("requests.get") as mock_get,
            patch("local_web._rate_limit"),
        ):
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = html
            texto = web_fetch("https://exemplo.com")
            assert "Olá mundo" in texto
            assert "js" not in texto

    def test_trunca_texto_longo(self):
        with (
            patch("requests.get") as mock_get,
            patch("local_web._rate_limit"),
        ):
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "<p>" + "a" * 1000 + "</p>"
            texto = web_fetch("https://exemplo.com", max_chars=50)
            assert len(texto) <= 100
            assert "truncado" in texto

    def test_erro_retorna_mensagem(self):
        with (
            patch("requests.get", side_effect=Exception("timeout")),
            patch("local_web._rate_limit"),
        ):
            texto = web_fetch("https://exemplo.com")
            assert "erro" in texto.lower()
