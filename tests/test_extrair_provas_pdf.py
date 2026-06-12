"""Testes do módulo extrair_provas_pdf.

Funções puras testadas diretamente; funções com IO têm dependências
mockadas (requests, pdf_utils, local_web).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from extrair_provas_pdf import (
    FONTES_PROVAS,
    _baixar_pdf,
    _listar_pdfs_cesgranrio,
    baixar_provas,
    extrair_provas,
    gerar_questoes_do_texto,
    relatorio_provas,
)


# ══════════════════════════════════════════════════════════════════════════
# Constantes
# ══════════════════════════════════════════════════════════════════════════

class TestFontesProvas:
    """FONTES_PROVAS é uma lista de fontes conhecidas."""

    def test_nao_vazia(self):
        assert len(FONTES_PROVAS) > 0

    def test_estrutura(self):
        for fonte in FONTES_PROVAS:
            assert "nome" in fonte
            assert "url" in fonte
            assert "tags" in fonte
            assert isinstance(fonte["tags"], list)


# ══════════════════════════════════════════════════════════════════════════
# _baixar_pdf
# ══════════════════════════════════════════════════════════════════════════

class TestBaixarPdf:
    """Testes de _baixar_pdf com requests mockado."""

    def _setup_requests(self, **kwargs):
        """Cria mock de requests e o injeta em sys.modules."""
        mock_req = MagicMock()
        mock_resp = MagicMock()
        for k, v in kwargs.items():
            setattr(mock_resp, k, v)
        mock_req.get.return_value = mock_resp
        return mock_req, mock_resp

    def test_sucesso_pdf_content_type(self, tmp_path):
        """Baixa PDF quando Content-Type contém 'pdf'."""
        destino = tmp_path / "prova.pdf"
        mock_req, mock_resp = self._setup_requests(
            status_code=200,
            headers={"Content-Type": "application/pdf"},
            content=b"%PDF-1.4 fake content",
        )
        mock_resp.raise_for_status.return_value = None
        with patch.dict("sys.modules", {"requests": mock_req}):
            assert _baixar_pdf("https://exemplo.com/prova", destino) is True
        assert destino.read_bytes() == b"%PDF-1.4 fake content"

    def test_sucesso_url_termina_em_pdf(self, tmp_path):
        """Baixa PDF quando URL termina em .pdf, mesmo sem Content-Type."""
        destino = tmp_path / "prova.pdf"
        mock_req, mock_resp = self._setup_requests(
            status_code=200,
            headers={},
            content=b"%PDF-content",
        )
        mock_resp.raise_for_status.return_value = None
        with patch.dict("sys.modules", {"requests": mock_req}):
            assert _baixar_pdf("https://exemplo.com/prova.pdf", destino) is True
        assert destino.read_bytes() == b"%PDF-content"

    def test_nao_e_pdf_retorna_false(self, tmp_path):
        """Retorna False se não for PDF (nem Content-Type nem extensão)."""
        destino = tmp_path / "pagina.html"
        mock_req, mock_resp = self._setup_requests(
            status_code=200,
            headers={"Content-Type": "text/html"},
            content=b"<html>",
        )
        mock_resp.raise_for_status.return_value = None
        with patch.dict("sys.modules", {"requests": mock_req}):
            assert _baixar_pdf("https://exemplo.com/pagina", destino) is False
        assert not destino.exists()

    def test_erro_rede_retorna_false(self, tmp_path):
        """Retorna False em caso de exceção de rede."""
        destino = tmp_path / "falha.pdf"
        mock_req = MagicMock()
        mock_req.get.side_effect = Exception("Conexão falhou")
        with patch.dict("sys.modules", {"requests": mock_req}):
            assert _baixar_pdf("https://exemplo.com/prova.pdf", destino) is False
        assert not destino.exists()

    def test_http_error_retorna_false(self, tmp_path):
        """Retorna False quando raise_for_status levanta erro."""
        destino = tmp_path / "erro404.pdf"
        mock_req, mock_resp = self._setup_requests(
            status_code=404,
            headers={},
        )
        mock_resp.raise_for_status.side_effect = Exception("HTTP 404")
        with patch.dict("sys.modules", {"requests": mock_req}):
            assert _baixar_pdf("https://exemplo.com/prova.pdf", destino) is False
        assert not destino.exists()


# ══════════════════════════════════════════════════════════════════════════
# _listar_pdfs_cesgranrio
# ══════════════════════════════════════════════════════════════════════════

class TestListarPdfsCesgranrio:
    """Testes de _listar_pdfs_cesgranrio com web_search/web_fetch mockados."""

    def test_sem_resultados(self):
        """Retorna lista vazia quando web_search não acha nada."""
        with patch("extrair_provas_pdf.web_search", return_value=[]):
            assert _listar_pdfs_cesgranrio() == []

    def test_encontra_pdf_direto(self):
        """Encontra PDF quando URL termina em .pdf."""
        with patch("extrair_provas_pdf.web_search") as mock_search:
            mock_search.return_value = [
                {"url": "https://exemplo.com/prova.pdf", "title": "Prova"},
            ]
            resultados = _listar_pdfs_cesgranrio()
            assert len(resultados) == 1
            assert resultados[0]["url"] == "https://exemplo.com/prova.pdf"

    def test_ignora_duplicatas(self):
        """Ignora URLs duplicatas retornadas pela busca."""
        with patch("extrair_provas_pdf.web_search") as mock_search:
            mock_search.return_value = [
                {"url": "https://exemplo.com/prova.pdf", "title": "P1"},
                {"url": "https://exemplo.com/prova.pdf", "title": "P1 dup"},
            ]
            assert len(_listar_pdfs_cesgranrio()) == 1

    def test_busca_pdfs_em_pagina_html(self):
        """Busca PDFs dentro de páginas HTML retornadas por web_fetch."""
        with (
            patch("extrair_provas_pdf.web_search") as mock_search,
            patch("extrair_provas_pdf.web_fetch") as mock_fetch,
        ):
            mock_search.return_value = [
                {"url": "https://exemplo.com/provas", "title": "Provas"},
            ]
            mock_fetch.return_value = (
                '<a href="https://exemplo.com/prova1.pdf">Prova 1</a>'
            )
            resultados = _listar_pdfs_cesgranrio()
            assert len(resultados) == 1
            assert "prova1.pdf" in resultados[0]["url"]

    def test_erro_web_search_nao_interrompe(self):
        """Erro em uma query não interrompe as queries seguintes."""
        with patch("extrair_provas_pdf.web_search") as mock_search:
            mock_search.side_effect = [Exception("Falha"), []]
            # Deve processar sem levantar exceção
            assert _listar_pdfs_cesgranrio() == []

    def test_limite_de_pdfs_por_pagina(self):
        """Extrai no máximo 3 PDFs por página consultada."""
        with (
            patch("extrair_provas_pdf.web_search") as mock_search,
            patch("extrair_provas_pdf.web_fetch") as mock_fetch,
        ):
            mock_search.return_value = [
                {"url": "https://exemplo.com/provas", "title": "P"},
            ]
            mock_fetch.return_value = " ".join(
                f'<a href="https://ex.com/p{i}.pdf">P{i}</a>' for i in range(10)
            )
            resultados = _listar_pdfs_cesgranrio()
            assert len(resultados) == 3


# ══════════════════════════════════════════════════════════════════════════
# baixar_provas
# ══════════════════════════════════════════════════════════════════════════

class TestBaixarProvas:
    """Testes de baixar_provas com dependências mockadas."""

    def test_baixa_com_sucesso(self, tmp_path):
        """baixar_provas baixa PDFs e retorna os caminhos."""
        def _fake_baixar(url, destino):
            destino.write_text("fake pdf", encoding="utf-8")
            return True

        with (
            patch("extrair_provas_pdf.PDF_DIR", tmp_path),
            patch("extrair_provas_pdf._listar_pdfs_cesgranrio") as mock_listar,
            patch("extrair_provas_pdf._baixar_pdf") as mock_baixar,
        ):
            mock_listar.return_value = [
                {"url": "https://ex.com/p1.pdf", "titulo": "P1"},
                {"url": "https://ex.com/p2.pdf", "titulo": "P2"},
            ]
            mock_baixar.side_effect = _fake_baixar
            baixados = baixar_provas(limite=5)
            assert len(baixados) == 2
            assert mock_baixar.call_count == 2

    def test_arquivo_ja_existe(self, tmp_path):
        """Arquivo já existente é reaproveitado (não baixado de novo)."""
        pdf_existente = tmp_path / "p1.pdf"
        pdf_existente.write_text("conteudo existente", encoding="utf-8")
        with (
            patch("extrair_provas_pdf.PDF_DIR", tmp_path),
            patch("extrair_provas_pdf._listar_pdfs_cesgranrio") as mock_listar,
            patch("extrair_provas_pdf._baixar_pdf") as mock_baixar,
        ):
            mock_listar.return_value = [
                {"url": "https://ex.com/p1.pdf", "titulo": "P1"},
            ]
            mock_baixar.return_value = True
            baixados = baixar_provas(limite=5)
            assert len(baixados) == 1
            mock_baixar.assert_not_called()

    def test_falha_no_download(self, tmp_path):
        """Falha no download não interrompe os demais."""
        call_count = [0]

        def _fake_baixar(url, destino):
            call_count[0] += 1
            if call_count[0] == 1:
                return False
            destino.write_text("fake pdf", encoding="utf-8")
            return True

        with (
            patch("extrair_provas_pdf.PDF_DIR", tmp_path),
            patch("extrair_provas_pdf._listar_pdfs_cesgranrio") as mock_listar,
            patch("extrair_provas_pdf._baixar_pdf") as mock_baixar,
        ):
            mock_listar.return_value = [
                {"url": "https://ex.com/p1.pdf", "titulo": "P1"},
                {"url": "https://ex.com/p2.pdf", "titulo": "P2"},
            ]
            mock_baixar.side_effect = _fake_baixar
            baixados = baixar_provas(limite=5)
            assert len(baixados) == 1
            assert baixados[0].name == "p2.pdf"

    def test_sem_provas_encontradas(self, tmp_path):
        """Retorna lista vazia quando nenhuma prova é encontrada."""
        with (
            patch("extrair_provas_pdf.PDF_DIR", tmp_path),
            patch("extrair_provas_pdf._listar_pdfs_cesgranrio") as mock_listar,
        ):
            mock_listar.return_value = []
            assert baixar_provas(limite=5) == []

    def test_cria_diretorio_se_inexistente(self, tmp_path):
        """Cria o diretório de PDFs se não existir."""
        diretorio = tmp_path / "novo_dir"
        assert not diretorio.exists()
        with (
            patch("extrair_provas_pdf.PDF_DIR", diretorio),
            patch("extrair_provas_pdf._listar_pdfs_cesgranrio") as mock_listar,
            patch("extrair_provas_pdf._baixar_pdf") as mock_baixar,
        ):
            mock_listar.return_value = []
            mock_baixar.return_value = True
            baixar_provas(limite=5)
            assert diretorio.exists()


# ══════════════════════════════════════════════════════════════════════════
# extrair_provas
# ══════════════════════════════════════════════════════════════════════════

class TestExtrairProvas:
    """Testes de extrair_provas com pdf_utils mockado."""

    def test_sem_pdfs_retorna_vazio(self, tmp_path):
        """Lista vazia de PDFs retorna lista vazia."""
        assert extrair_provas(pdfs=[]) == []

    def test_sem_pdfs_none_com_diretorio_vazio(self, tmp_path):
        """pdfs=None em diretório vazio retorna lista vazia."""
        with patch("extrair_provas_pdf.PDF_DIR", tmp_path):
            assert extrair_provas(pdfs=None) == []

    def test_extrai_com_sucesso(self, tmp_path):
        """Extrai texto de PDF com sucesso e salva resultado."""
        pdf = tmp_path / "prova.pdf"
        pdf.write_text("fake", encoding="utf-8")
        with (
            patch("extrair_provas_pdf.RESULTADOS_DIR", tmp_path / "extraidas"),
            patch("extrair_provas_pdf.extrair_texto_pdf") as mock_extract,
        ):
            mock_extract.return_value = "# Prova\n\nConteúdo da prova."
            resultados = extrair_provas(pdfs=[pdf])
            assert len(resultados) == 1
            r = resultados[0]
            assert r["arquivo"] == "prova.pdf"
            assert r["chars"] == len("# Prova\n\nConteúdo da prova.")
            assert "Conteúdo" in r["texto"]
            assert (tmp_path / "extraidas" / "prova.md").exists()

    def test_texto_vazio_ignorado(self, tmp_path):
        """PDF com texto vazio após extração é ignorado."""
        pdf = tmp_path / "vazia.pdf"
        pdf.write_text("fake", encoding="utf-8")
        with (
            patch("extrair_provas_pdf.RESULTADOS_DIR", tmp_path / "extraidas"),
            patch("extrair_provas_pdf.extrair_texto_pdf") as mock_extract,
        ):
            mock_extract.return_value = ""
            assert extrair_provas(pdfs=[pdf]) == []

    def test_erro_extracao_ignorado(self, tmp_path):
        """Erro na extração de um PDF não interrompe os demais."""
        pdf1 = tmp_path / "ok.pdf"
        pdf2 = tmp_path / "falha.pdf"
        pdf1.write_text("fake", encoding="utf-8")
        pdf2.write_text("fake", encoding="utf-8")
        with (
            patch("extrair_provas_pdf.RESULTADOS_DIR", tmp_path / "extraidas"),
            patch("extrair_provas_pdf.extrair_texto_pdf") as mock_extract,
        ):
            mock_extract.side_effect = ["Texto OK", Exception("Falha na extração")]
            resultados = extrair_provas(pdfs=[pdf1, pdf2])
            assert len(resultados) == 1
            assert resultados[0]["arquivo"] == "ok.pdf"

    def test_cria_diretorio_resultados(self, tmp_path):
        """Cria diretório de resultados se não existir."""
        pdf = tmp_path / "prova.pdf"
        pdf.write_text("fake", encoding="utf-8")
        saida = tmp_path / "resultados_novo"
        assert not saida.exists()
        with (
            patch("extrair_provas_pdf.RESULTADOS_DIR", saida),
            patch("extrair_provas_pdf.extrair_texto_pdf") as mock_extract,
        ):
            mock_extract.return_value = "Conteúdo"
            extrair_provas(pdfs=[pdf])
            assert saida.exists()


# ══════════════════════════════════════════════════════════════════════════
# gerar_questoes_do_texto
# ══════════════════════════════════════════════════════════════════════════

class TestGerarQuestoesDoTexto:
    """Testes da função pura gerar_questoes_do_texto."""

    def test_texto_vazio(self):
        assert gerar_questoes_do_texto("") == []

    def test_sem_palavras_chave(self):
        texto = "Qual é a capital do Brasil?\nA) Rio\nB) Brasília\nC) SP\nD) BH\nE) Fortaleza"
        # "Qual" é uma das palavras-chave, então vai encontrar
        resultado = gerar_questoes_do_texto(texto)
        assert len(resultado) > 0

    def test_texto_sem_questoes(self):
        texto = "Este é apenas um parágrafo explicativo sobre a matéria."
        assert gerar_questoes_do_texto(texto) == []

    def test_bloco_muito_curto_ignorado(self):
        """Blocos com menos de 3 linhas são ignorados."""
        texto = "Linha 1\n\nLinha 2"
        assert gerar_questoes_do_texto(texto) == []

    def test_encontra_assinale_com_opcoes(self):
        texto = """Assinale a alternativa correta sobre a Lei 13.303.
A) É a lei das estatais
B) É a lei de licitações
C) É o estatuto do servidor
D) É a lei anticorrupção
E) É a lei de responsabilidade fiscal"""
        resultado = gerar_questoes_do_texto(texto)
        assert len(resultado) == 1
        q = resultado[0]
        assert "Assinale" in q["enunciado"]
        assert len(q["opcoes"]) == 5
        assert q["disciplina"] == "Geral"

    def test_disciplina_personalizada(self):
        texto = """Marque a opção correta.
A) Opção 1
B) Opção 2
C) Opção 3
D) Opção 4
E) Opção 5"""
        resultado = gerar_questoes_do_texto(texto, disciplina="Direito")
        assert resultado[0]["disciplina"] == "Direito"

    def test_questao_sem_opcoes_completas(self):
        """Questão com menos de 5 opções retorna opções vazias."""
        texto = """Indique a resposta:
A) Primeira
B) Segunda"""
        resultado = gerar_questoes_do_texto(texto)
        assert len(resultado) == 1
        assert resultado[0]["opcoes"] == []

    def test_multiplas_questoes(self):
        texto = """Assinale a primeira questão.
A) Alt 1
B) Alt 2
C) Alt 3
D) Alt 4
E) Alt 5

Marque a segunda questão.
A) Opt 1
B) Opt 2
C) Opt 3
D) Opt 4
E) Opt 5"""
        resultado = gerar_questoes_do_texto(texto)
        assert len(resultado) == 2


# ══════════════════════════════════════════════════════════════════════════
# relatorio_provas
# ══════════════════════════════════════════════════════════════════════════

class TestRelatorioProvas:
    """Testes da função pura relatorio_provas."""

    def test_sem_resultados(self):
        relatorio = relatorio_provas([])
        assert "# Provas CESGRANRIO/Petrobras Extraídas" in relatorio
        assert "**Total de PDFs:** 0" in relatorio
        assert "Total estimado: 0" in relatorio

    def test_com_um_resultado(self):
        resultados = [
            {"arquivo": "prova_2024.pdf", "chars": 5000, "texto": "Conteúdo da prova..."},
        ]
        relatorio = relatorio_provas(resultados)
        assert "prova_2024.pdf" in relatorio
        assert "5000" in relatorio

    def test_com_multiplos_resultados(self):
        resultados = [
            {"arquivo": f"prova_{i}.pdf", "chars": 1000 * i, "texto": "abc"}
            for i in range(1, 4)
        ]
        relatorio = relatorio_provas(resultados)
        for i in range(1, 4):
            assert f"prova_{i}.pdf" in relatorio

    def test_metodologia_incluida(self):
        relatorio = relatorio_provas([])
        assert "Metodologia" in relatorio
        assert "opendataloader-pdf" in relatorio
        assert "CESGRANRIO" in relatorio
