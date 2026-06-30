"""Testes do RAG local (rag.py) — chromadb mockado/isolado."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import rag


class TestChunk:
    def test_agrupa_paragrafos(self):
        texto = (
            "A regência verbal trata da relação entre o verbo e seus complementos, "
            "exigindo ou não preposição conforme o sentido empregado na frase.\n\n"
            "A crase resulta da fusão da preposição A com o artigo feminino A, sendo "
            "obrigatória diante de palavras femininas que pedem preposição, como em "
            "'obediência à norma' e 'referência à lei do concurso público'."
        )
        chunks = rag._chunk(texto)
        assert chunks
        assert all(len(c) >= rag._CHUNK_MIN for c in chunks)

    def test_descarta_curtos(self):
        assert rag._chunk("oi\n\nok") == []

    def test_fatia_paragrafo_gigante(self):
        gigante = "a" * 2500
        chunks = rag._chunk(gigante)
        assert len(chunks) >= 2
        assert all(len(c) <= rag._CHUNK_MAX for c in chunks)

    def test_id_deterministico(self):
        assert rag._id("fonte", "texto") == rag._id("fonte", "texto")
        assert rag._id("a", "x") != rag._id("b", "x")


class TestBuscarGraceful:
    def test_sem_chromadb_retorna_vazio(self):
        with patch("rag.disponivel", return_value=False):
            assert rag.buscar("qualquer", k=3) == []

    def test_sem_indice_retorna_vazio(self, tmp_path):
        with patch("rag.disponivel", return_value=True), \
             patch("rag.RAG_DIR", tmp_path / "inexistente"):
            assert rag.buscar("qualquer") == []

    def test_excecao_no_query_retorna_vazio(self, tmp_path):
        rag_dir = tmp_path / "idx"
        rag_dir.mkdir()
        col = MagicMock()
        col.query.side_effect = Exception("boom")
        with patch("rag.disponivel", return_value=True), \
             patch("rag.RAG_DIR", rag_dir), \
             patch("rag._colecao", return_value=col):
            assert rag.buscar("q") == []


class TestContextoParaPrompt:
    def test_vazio_quando_sem_resultados(self):
        with patch("rag.buscar", return_value=[]):
            assert rag.contexto_para_prompt("q") == ""

    def test_monta_bloco_com_fonte(self):
        trechos = [
            {"texto": "Regra de crase antes de palavra feminina.", "fonte": "Portugues", "distancia": 0.1},
            {"texto": "Concordância verbal com sujeito composto.", "fonte": "Portugues", "distancia": 0.2},
        ]
        with patch("rag.buscar", return_value=trechos):
            ctx = rag.contexto_para_prompt("crase")
        assert "[MATERIAL_DE_ESTUDO]" in ctx
        assert "Portugues" in ctx
        assert "crase" in ctx.lower()

    def test_respeita_max_chars(self):
        trechos = [{"texto": "x" * 5000, "fonte": "F", "distancia": 0.0}]
        with patch("rag.buscar", return_value=trechos):
            ctx = rag.contexto_para_prompt("q", max_chars=500)
        # cabeçalho + bloco truncado + rodapé — bem abaixo do texto original
        assert len(ctx) < 1200


class TestIndexar:
    def test_indexa_arquivos(self, tmp_path):
        f = tmp_path / "apostila.md"
        f.write_text("Parágrafo sobre licitações na Lei 13.303 e governança das estatais. " * 5,
                     encoding="utf-8")
        col = MagicMock()
        with patch("rag._colecao", return_value=col):
            n = rag.indexar([f])
        assert n >= 1
        assert col.upsert.called

    def test_arquivo_inexistente_ignorado(self, tmp_path):
        col = MagicMock()
        with patch("rag._colecao", return_value=col):
            n = rag.indexar([tmp_path / "naoexiste.md"])
        assert n == 0


class TestEstatisticas:
    def test_indisponivel(self):
        with patch("rag.disponivel", return_value=False):
            st = rag.estatisticas()
        assert st["chunks"] == 0
        assert st["disponivel"] is False
