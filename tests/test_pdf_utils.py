"""Testes do módulo pdf_utils."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from pdf_utils import disponivel, extrair_texto_pdf, extrair_texto_pdf_para_contexto, extrair_tabelas_pdf


def test_disponivel():
    """disponivel() retorna bool."""
    result = disponivel()
    assert isinstance(result, bool)


def test_extrair_texto_pdf_sem_arquivo():
    """extrair_texto_pdf levanta FileNotFoundError para PDF inexistente."""
    try:
        extrair_texto_pdf("/tmp/nao_existe.pdf")
        assert False, "Deveria ter levantado FileNotFoundError"
    except FileNotFoundError:
        pass


def test_extrair_texto_pdf_sem_dependencia(tmp_path):
    """extrair_texto_pdf levanta RuntimeError se opendataloader não instalado."""
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_text("fake", encoding="utf-8")
    with patch("pdf_utils._TEM_OPENDATALOADER", False):
        try:
            extrair_texto_pdf(str(pdf_path))
            assert False, "Deveria ter levantado RuntimeError"
        except RuntimeError as e:
            assert "não instalado" in str(e)


def test_extrair_texto_pdf_sucesso(tmp_path):
    """extrair_texto_pdf retorna texto quando conversão funciona."""
    pdf_path = tmp_path / "teste.pdf"
    pdf_path.write_text("fake pdf", encoding="utf-8")
    markdown_content = "# Título\n\nParágrafo de teste.\n"

    with (
        patch("pdf_utils._TEM_OPENDATALOADER", True),
        patch("pdf_utils.odp") as mock_odp,
        patch("tempfile.TemporaryDirectory") as mock_tmpdir,
    ):
        mock_tmpdir.return_value.__enter__.return_value = str(tmp_path / "odp_out")
        out_dir = Path(str(tmp_path / "odp_out"))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "teste.md").write_text(markdown_content, encoding="utf-8")

        texto = extrair_texto_pdf(str(pdf_path))
        assert "Título" in texto
        assert "Parágrafo de teste" in texto
        mock_odp.convert.assert_called_once()


def test_extrair_texto_pdf_para_contexto_com_cache(tmp_path):
    """extrair_texto_pdf_para_contexto salva e reusa cache."""
    with (
        patch("pdf_utils._TEM_OPENDATALOADER", True),
        patch("pdf_utils.extrair_texto_pdf") as mock_extract,
        patch("pdf_utils.CACHE_DIR", tmp_path),
    ):
        mock_extract.return_value = "Conteúdo do PDF"
        from pdf_utils import extrair_texto_pdf_para_contexto

        texto1 = extrair_texto_pdf_para_contexto(str(tmp_path / "doc.pdf"))
        assert texto1 == "Conteúdo do PDF"
        assert mock_extract.call_count == 1

        texto2 = extrair_texto_pdf_para_contexto(str(tmp_path / "doc.pdf"))
        assert texto2 == "Conteúdo do PDF"
        assert mock_extract.call_count == 1


def test_extrair_texto_pdf_para_contexto_force(tmp_path):
    """extrair_texto_pdf_para_contexto com force=True ignora cache."""
    with (
        patch("pdf_utils._TEM_OPENDATALOADER", True),
        patch("pdf_utils.extrair_texto_pdf") as mock_extract,
        patch("pdf_utils.CACHE_DIR", tmp_path),
    ):
        mock_extract.return_value = "Conteúdo"
        from pdf_utils import extrair_texto_pdf_para_contexto

        extrair_texto_pdf_para_contexto(str(tmp_path / "doc.pdf"))
        extrair_texto_pdf_para_contexto(str(tmp_path / "doc.pdf"), force=True)
        assert mock_extract.call_count == 2


def test_extrair_texto_pdf_para_contexto_trunca(tmp_path):
    """extrair_texto_pdf_para_contexto trunca texto maior que max_chars."""
    with (
        patch("pdf_utils._TEM_OPENDATALOADER", True),
        patch("pdf_utils.extrair_texto_pdf") as mock_extract,
        patch("pdf_utils.CACHE_DIR", tmp_path),
    ):
        mock_extract.return_value = "A" * 1000
        from pdf_utils import extrair_texto_pdf_para_contexto

        texto = extrair_texto_pdf_para_contexto(str(tmp_path / "doc.pdf"), max_chars=100)
        assert len(texto) <= 100 + 20
        assert "truncado" in texto


def test_extrair_tabelas_pdf_sem_arquivo():
    """extrair_tabelas_pdf levanta FileNotFoundError."""
    try:
        extrair_tabelas_pdf("/tmp/inexistente.pdf")
        assert False
    except FileNotFoundError:
        pass


def test_extrair_tabelas_pdf_com_tabelas(tmp_path):
    """extrair_tabelas_pdf retorna tabelas do JSON."""
    pdf_path = tmp_path / "tabela.pdf"
    pdf_path.write_text("fake", encoding="utf-8")

    json_content = json.dumps({
        "elements": [
            {"type": "table", "content": "Col1\tCol2\nVal1\tVal2"},
            {"type": "paragraph", "content": "Ignorado"},
        ]
    })

    with (
        patch("pdf_utils._TEM_OPENDATALOADER", True),
        patch("pdf_utils.odp") as mock_odp,
        patch("tempfile.TemporaryDirectory") as mock_tmpdir,
    ):
        mock_tmpdir.return_value.__enter__.return_value = str(tmp_path / "odp_tbl")
        out_dir = Path(str(tmp_path / "odp_tbl"))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "tabela.json").write_text(json_content, encoding="utf-8")

        tabelas = extrair_tabelas_pdf(str(pdf_path))
        assert len(tabelas) == 1
        assert "Col1" in tabelas[0][0]
        assert "Val1" in tabelas[0][1]
        mock_odp.convert.assert_called_once()


def test_extrair_tabelas_sem_dependencia(tmp_path):
    """extrair_tabelas_pdf levanta RuntimeError sem opendataloader."""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_text("fake", encoding="utf-8")
    with patch("pdf_utils._TEM_OPENDATALOADER", False):
        try:
            extrair_tabelas_pdf(str(pdf_path))
            assert False
        except RuntimeError as e:
            assert "não instalado" in str(e)


def test_extrair_texto_pdf_formato_json(tmp_path):
    """extrair_texto_pdf com formato json retorna texto dos elementos."""
    from pdf_utils import extrair_texto_pdf
    pdf_path = tmp_path / "doc.json.pdf"
    pdf_path.write_text("fake", encoding="utf-8")
    json_content = json.dumps({"elements": [{"content": "Linha 1"}, {"content": "Linha 2"}]})
    with (
        patch("pdf_utils._TEM_OPENDATALOADER", True),
        patch("pdf_utils.odp") as mock_odp,
        patch("tempfile.TemporaryDirectory") as mock_tmpdir,
    ):
        mock_tmpdir.return_value.__enter__.return_value = str(tmp_path / "odp_json")
        out_dir = Path(str(tmp_path / "odp_json"))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "doc.json").write_text(json_content, encoding="utf-8")
        texto = extrair_texto_pdf(str(pdf_path), formato="json")
        assert "Linha 1" in texto
        assert "Linha 2" in texto


def test_extrair_texto_pdf_erro_conversao(tmp_path):
    """extrair_texto_pdf levanta RuntimeError se conversão falha."""
    pdf_path = tmp_path / "erro.pdf"
    pdf_path.write_text("fake", encoding="utf-8")
    with (
        patch("pdf_utils._TEM_OPENDATALOADER", True),
        patch("pdf_utils.odp") as mock_odp,
    ):
        mock_odp.convert.side_effect = Exception("Falha na conversão")
        try:
            extrair_texto_pdf(str(pdf_path))
            assert False
        except RuntimeError as e:
            assert "Falha" in str(e)
