"""Testes do módulo exportar_anki."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from exportar_anki import exportar_csv, exportar_apkg, main


class TestExportarCSV:
    def test_exportar_csv_todas(self, tmp_path):
        saida = tmp_path / "questoes.csv"
        total = exportar_csv(saida)
        assert total > 0
        assert saida.exists()
        import csv
        with saida.open(encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert rows[0] == ["Pergunta", "Resposta", "Disciplina", "Tags"]
        assert len(rows) - 1 == total

    def test_exportar_csv_filtro_disciplina(self, tmp_path):
        saida = tmp_path / "questoes_filtradas.csv"
        total = exportar_csv(saida, disciplina="Informática")
        assert total > 0
        with saida.open(encoding="utf-8") as f:
            import csv
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                assert row[2] == "Informática", f"Disciplina {row[2]} != Informática"

    def test_exportar_csv_filtro_sem_match(self, tmp_path):
        saida = tmp_path / "vazio.csv"
        total = exportar_csv(saida, disciplina="Inexistente")
        assert total == 0

    def test_exportar_csv_stdout_reconfigure(self, tmp_path):
        saida = tmp_path / "stdout.csv"
        total = exportar_csv(saida, disciplina="Português")
        assert total >= 0


class TestExportarApkg:
    def test_exportar_apkg_sucesso(self, tmp_path):
        mock_genanki = MagicMock()
        mock_model = MagicMock()
        mock_deck = MagicMock()
        mock_package = MagicMock()

        mock_genanki.Model.return_value = mock_model
        mock_genanki.Deck.return_value = mock_deck
        mock_genanki.Note.return_value = MagicMock()
        mock_genanki.Package.return_value = mock_package

        saida = tmp_path / "questoes.apkg"
        with patch.dict("sys.modules", {"genanki": mock_genanki}):
            total = exportar_apkg(saida, disciplina="Informática")

        assert total > 0
        mock_genanki.Model.assert_called_once()
        mock_genanki.Deck.assert_called_once()
        mock_package.write_to_file.assert_called_once_with(str(saida))

    def test_exportar_apkg_sem_genanki_fallback_csv(self, tmp_path):
        saida = tmp_path / "questoes.apkg"
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "genanki":
                raise ImportError("no genanki")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", mock_import):
            with patch("exportar_anki.exportar_csv", return_value=5) as mock_csv:
                total = exportar_apkg(saida, disciplina="Informática")
        assert total == 5

    def test_exportar_apkg_filtro_sem_match(self, tmp_path):
        mock_genanki = MagicMock()
        saida = tmp_path / "vazio.apkg"
        with patch.dict("sys.modules", {"genanki": mock_genanki}):
            total = exportar_apkg(saida, disciplina="Inexistente")
        assert total == 0

    def test_exportar_apkg_todas_disciplinas(self, tmp_path):
        mock_genanki = MagicMock()
        mock_model = MagicMock()
        mock_deck = MagicMock()
        mock_package = MagicMock()
        mock_genanki.Model.return_value = mock_model
        mock_genanki.Deck.return_value = mock_deck
        mock_genanki.Package.return_value = mock_package

        saida = tmp_path / "todas.apkg"
        with patch.dict("sys.modules", {"genanki": mock_genanki}):
            total = exportar_apkg(saida)
        assert total > 0


class TestMain:
    def test_main_csv_default(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr(sys, "argv", ["exportar_anki.py"])
        with patch("exportar_anki.Path", return_value=tmp_path / "questoes_anki.csv"):
            with patch("exportar_anki.exportar_csv", return_value=10) as mock_csv:
                with patch("pathlib.Path.write_text"):
                    main()
        captured = capsys.readouterr()
        assert "✓" in captured.out or "exportadas" in captured.out

    def test_main_csv_explicit(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["exportar_anki.py", "--formato", "csv", "--disciplina", "Português", "--output", "out.csv"])
        with patch("exportar_anki.exportar_csv", return_value=10) as mock_csv:
            main()
        captured = capsys.readouterr()
        assert "10" in captured.out

    def test_main_apkg(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["exportar_anki.py", "--formato", "apkg", "--output", "out.apkg"])
        with patch("exportar_anki.exportar_apkg", return_value=10) as mock_apkg:
            main()

    def test_main_sem_resultados(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["exportar_anki.py"])
        with patch("exportar_anki.exportar_csv", return_value=0) as mock_csv:
            main()
        captured = capsys.readouterr()
        assert "Nenhuma questão exportada" in captured.out

    def test_main_output_personalizado(self, monkeypatch, capsys, tmp_path):
        saida = tmp_path / "custom.csv"
        monkeypatch.setattr(sys, "argv", ["exportar_anki.py", "--output", str(saida)])
        main()
        assert saida.exists()

    def test_stdout_reconfigure_fallback(self, monkeypatch):
        original = sys.stdout
        class MockStdout:
            encoding = "utf-8"
            def reconfigure(self, **kwargs):
                raise AttributeError("no reconfigure")
        sys.stdout = MockStdout()  # type: ignore
        monkeypatch.setattr(sys, "stdout", MockStdout())
        try:
            from exportar_anki import exportar_csv
            total = exportar_csv(Path("test.csv"), disciplina="Informática")
            assert total >= 0
        finally:
            sys.stdout = original
