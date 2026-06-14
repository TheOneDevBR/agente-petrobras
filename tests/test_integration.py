"""Testes de integração — pipeline do coletor com dependências mockadas."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python" / "coletor"))

from coletor import (
    atualizar_moc,
    coletar_beat,
    gravar_nota,
)

BEAT_EXAMPLE = {
    "id": "test-beat",
    "titulo": "Teste de integração",
    "tags": ["teste", "mock"],
    "instrucao": "Instrução de teste",
    "dominios_sugeridos": ["exemplo.com"],
}

BEAT_COM_RAG = {
    "id": "test-rag",
    "titulo": "Teste com RAG",
    "tags": ["teste"],
    "instrucao": "Instrução com RAG",
    "dominios_sugeridos": [],
    "rag_sources": [
        {"url": "https://leis.example.com/13303", "descricao": "Lei 13.303"},
        {"url": "https://leis.example.com/14133", "descricao": "Lei 14.133"},
    ],
}

LLM_RESPOSTA_EXEMPLO = (
    "resumo_uma_linha: Teste de integração passou.\n\n"
    "## Resumo executivo\n"
    "Nosso resumo executivo aqui.\n\n"
    "## Detalhes\n"
    "- Item 1\n"
    "- Item 2\n"
)


def test_buscar_para_beat_com_retorno():
    from coletor import _buscar_para_beat

    with (
        patch("coletor.web_search") as mock_search,
        patch("coletor.web_fetch") as mock_fetch,
    ):
        mock_search.return_value = [
            {"title": "Resultado 1", "href": "https://exemplo.com/1", "snippet": "Trecho 1", "body": ""},
            {"title": "Resultado 2", "href": "https://exemplo.com/2", "snippet": "Trecho 2", "body": ""},
        ]
        mock_fetch.return_value = "Conteúdo extraído com mais de 200 caracteres. " * 20

        resultado, urls = _buscar_para_beat(BEAT_EXAMPLE, max_resultados=2)

    assert "Resultado 1" in resultado
    assert "Resultado 2" in resultado
    assert "Conteúdo extraído" in resultado
    assert mock_search.call_count == 3  # titulo + 2 tags
    # as URLs reais ficam disponíveis para a conferência de fontes
    assert "https://exemplo.com/1" in urls


def test_buscar_para_beat_sem_resultados():
    from coletor import _buscar_para_beat

    with patch("coletor.web_search") as mock_search:
        mock_search.return_value = []
        resultado, urls = _buscar_para_beat(BEAT_EXAMPLE, max_resultados=2)
    assert "Nenhum resultado encontrado" in resultado
    assert urls == []


# ══════════════════════════════════════════════════════════════════════════
# _fetch_rag_context
# ══════════════════════════════════════════════════════════════════════════

def test_fetch_rag_context_sem_sources():
    from coletor import _fetch_rag_context
    assert _fetch_rag_context(BEAT_EXAMPLE) == ""


def test_fetch_rag_context_com_sources():
    from coletor import _fetch_rag_context

    with patch("coletor.web_fetch") as mock_fetch:
        texto_longo = "Art. 1 Esta Lei dispoe sobre o estatuto juridico. " * 15
        mock_fetch.return_value = texto_longo

        resultado = _fetch_rag_context(BEAT_COM_RAG)

    assert "Lei 13.303" in resultado
    assert "Art. 1" in resultado
    assert "Fonte: https://leis.example.com/13303" in resultado
    assert mock_fetch.call_count == 2


def test_fetch_rag_context_erro_web():
    from coletor import _fetch_rag_context

    with patch("coletor.web_fetch", side_effect=Exception("conexao falhou")):
        resultado = _fetch_rag_context(BEAT_COM_RAG)

    assert resultado == ""


def test_fetch_rag_context_conteudo_curto():
    from coletor import _fetch_rag_context

    with patch("coletor.web_fetch", return_value="curto"):
        resultado = _fetch_rag_context(BEAT_COM_RAG)

    assert resultado == ""


def test_coletar_beat_com_mocks():
    with (
        patch("coletor.web_search") as mock_search,
        patch("coletor.web_fetch") as mock_fetch,
    ):
        mock_search.return_value = [
            {"title": "Site", "href": "https://exemplo.com", "snippet": "Snippet", "body": ""},
        ]
        mock_fetch.return_value = "Texto longo o suficiente para passar no filtro. " * 50

        cliente = MagicMock()
        cliente.chat.return_value = LLM_RESPOSTA_EXEMPLO
        cliente.model = "mock-model"
        cliente.base_url = "http://mock"

        resultado = coletar_beat(cliente, BEAT_EXAMPLE, "cargo teste")

    assert resultado is not None
    corpo, resumo = resultado
    assert "Teste de integração passou" in corpo
    assert "Resumo executivo" in corpo
    assert "Teste de integração passou." == resumo
    cliente.chat.assert_called_once()


def test_coletar_beat_com_rag():
    """RAG sources sao incluidos no prompt quando presentes."""
    texto_longo = "Art. 1 Esta Lei dispoe sobre o estatuto juridico. " * 15
    with (
        patch("coletor.web_search", return_value=[]),
        patch("coletor.web_fetch", return_value=texto_longo) as mock_fetch,
    ):
        cliente = MagicMock()
        cliente.chat.return_value = LLM_RESPOSTA_EXEMPLO

        resultado = coletar_beat(cliente, BEAT_COM_RAG, "cargo")

    assert resultado is not None
    # RAG contexts foram buscados (2 chamadas web_fetch alem das web_search)
    assert mock_fetch.call_count >= 2
    # LLM recebeu o texto da lei no prompt
    prompt_enviado = cliente.chat.call_args[1]["messages"][0]["content"]
    assert "Lei 13.303" in prompt_enviado
    assert "Fonte: https://leis.example.com/13303" in prompt_enviado


def test_coletar_beat_erro_llm():
    with (
        patch("coletor.web_search") as mock_search,
        patch("coletor.web_fetch") as mock_fetch,
    ):
        mock_search.return_value = [{"title": "X", "href": "https://x.com", "snippet": "x"}]
        mock_fetch.return_value = "a" * 500

        cliente = MagicMock()
        cliente.chat.side_effect = __import__("coletor").LocalLLMError("erro simulado")

        resultado = coletar_beat(cliente, BEAT_EXAMPLE, "cargo")
    assert resultado is None


def test_coletar_beat_resposta_vazia():
    with (
        patch("coletor.web_search") as mock_search,
        patch("coletor.web_fetch") as mock_fetch,
    ):
        mock_search.return_value = [{"title": "X", "href": "https://x.com", "snippet": "x"}]
        mock_fetch.return_value = "a" * 500

        cliente = MagicMock()
        cliente.chat.return_value = ""
        resultado = coletar_beat(cliente, BEAT_EXAMPLE, "cargo")
    assert resultado is None


def test_gravar_nota(tmp_path):

    with patch("coletor.PASTA_INTEL", tmp_path / "Inteligencia"):
        beat = {**BEAT_EXAMPLE, "titulo": "Gravação Teste"}
        corpo = "## Resumo executivo\nConteúdo da nota."
        resumo = "Nota de teste"

        arquivo = gravar_nota(beat, corpo, resumo)

    assert arquivo.exists()
    conteudo = arquivo.read_text(encoding="utf-8")
    assert "titulo: Gravação Teste" in conteudo
    assert "beat: test-beat" in conteudo
    assert "resumo: \"Nota de teste\"" in conteudo
    assert "Conteúdo da nota" in conteudo
    assert "resumo_uma_linha:" not in conteudo


def test_gravar_nota_slug_acentos(tmp_path):

    with patch("coletor.PASTA_INTEL", tmp_path / "Inteligencia"):
        beat = {**BEAT_EXAMPLE, "titulo": "Notícias e Tendências"}
        corpo = "Conteúdo"
        arquivo = gravar_nota(beat, corpo, "teste")

    assert "noticias-e-tendencias" in arquivo.name


def test_atualizar_moc_cria_novo(tmp_path):
    moc_path = tmp_path / "_RESUMO_INTEL.md"
    with (
        patch("coletor.RESUMO_MOC", moc_path),
        patch("coletor.date") as mock_date,
    ):
        from datetime import date
        mock_date.today.return_value = date(2026, 6, 10)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        registros = [
            {
                "arquivo": Path("nota-teste.md"),
                "titulo": "Nota Teste",
                "resumo": "Resumo da nota",
            }
        ]
        atualizar_moc(registros)

    assert moc_path.exists()
    conteudo = moc_path.read_text(encoding="utf-8")
    assert "# 📡 Resumo de Inteligência" in conteudo
    assert "## Coleta de 2026-06-10" in conteudo
    assert "[[nota-teste|Nota Teste]]" in conteudo
    assert "Resumo da nota" in conteudo


def test_atualizar_moc_substitui_bloco_mesma_data(tmp_path):
    moc_path = tmp_path / "_RESUMO_INTEL.md"
    moc_path.write_text(
        "---\ntitulo: antigo\n---\n\n"
        "# Header\n\n"
        "## Coleta de 2026-06-10\n"
        "- [[velho|Nota Velha]] — resumo velho\n\n"
        "## Coleta de 2026-06-09\n"
        "- [[mais-antigo|Antiga]] — resumo\n",
        encoding="utf-8",
    )

    with (
        patch("coletor.RESUMO_MOC", moc_path),
        patch("coletor.date") as mock_date,
    ):
        from datetime import date
        mock_date.today.return_value = date(2026, 6, 10)
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)

        registros = [
            {
                "arquivo": Path("nota-nova.md"),
                "titulo": "Nota Nova",
                "resumo": "Substituiu",
            }
        ]
        atualizar_moc(registros)

    conteudo = moc_path.read_text(encoding="utf-8")
    assert "[[nota-nova|Nota Nova]]" in conteudo
    assert "Substituiu" in conteudo
    assert "[[velho|Nota Velha]]" not in conteudo
    assert "[[mais-antigo|Antiga]]" in conteudo
