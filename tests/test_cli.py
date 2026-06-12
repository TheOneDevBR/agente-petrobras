"""Testes do CLI unificado."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))


class TestParser:
    def test_parser_criado(self):
        from cli import main as cli_main
        import inspect
        source = inspect.getsource(cli_main)
        assert "ArgumentParser" in source

    def test_version_flag(self, monkeypatch):
        from cli import main as cli_main
        monkeypatch.setattr(sys, "argv", ["agente", "--version"])
        try:
            cli_main()
        except SystemExit as e:
            assert e.code == 0

    def test_help_text(self, monkeypatch):
        from cli import main as cli_main
        monkeypatch.setattr(sys, "argv", ["agente", "--help"])
        try:
            cli_main()
        except SystemExit as e:
            assert e.code == 0

    def test_subcommands_registered(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["agente", "--help"])
        try:
            from cli import main as cli_main
            cli_main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        for cmd in ["chat", "simulado", "prova-completa", "benchmark", "cronograma",
                      "risco", "provas", "anki", "perfil", "metricas"]:
            assert cmd in captured.out


class TestCmdChat:
    def test_chat_inicia_agente(self, monkeypatch):
        from cli import cmd_chat
        args = argparse.Namespace()
        with monkeypatch.context() as m:
            m.setattr("builtins.input", lambda _: "/sair")
            try:
                cmd_chat()
            except (SystemExit, Exception):
                pass

    def test_chat_default_command(self, monkeypatch):
        from cli import main as cli_main
        monkeypatch.setattr(sys, "argv", ["agente"])
        with monkeypatch.context() as m:
            m.setattr("builtins.input", lambda _: "/sair")
            try:
                cli_main()
            except (SystemExit, Exception):
                pass


class TestCmdSimulado:
    def test_simulado_defaults(self, monkeypatch):
        from cli import cmd_simulado
        with patch("treino.iniciar_simulado") as mock:
            args = argparse.Namespace(questoes=5, tempo=0, disciplina="")
            cmd_simulado(args)
        mock.assert_called_once_with(n_questoes=5, cronometro=0, disciplina="")

    def test_simulado_com_filtros(self, monkeypatch):
        from cli import cmd_simulado
        with patch("treino.iniciar_simulado") as mock:
            args = argparse.Namespace(questoes=10, tempo=30, disciplina="Matemática")
            cmd_simulado(args)
        mock.assert_called_once_with(n_questoes=10, cronometro=30, disciplina="Matemática")


class TestCmdProvaCompleta:
    def test_prova_completa(self):
        from cli import cmd_prova_completa
        with patch("treino.iniciar_prova_completa") as mock:
            cmd_prova_completa(argparse.Namespace())
        mock.assert_called_once()


class TestCmdBenchmark:
    def test_benchmark_defaults(self):
        from cli import cmd_benchmark
        with (
            patch("benchmark_qualidade.main") as mock_bm,
        ):
            cmd_benchmark(argparse.Namespace(model=None, skip_rag=False, skip_no_rag=False, output=None))
        mock_bm.assert_called_once()

    def test_benchmark_com_args(self):
        from cli import cmd_benchmark
        with (
            patch("benchmark_qualidade.main") as mock_bm,
            patch("sys.argv", ["agente"]),
        ):
            cmd_benchmark(argparse.Namespace(model="phi3", skip_rag=True, skip_no_rag=True, output="relatorio.md"))
        mock_bm.assert_called_once()

    def test_benchmark_output(self):
        from cli import cmd_benchmark
        with (
            patch("benchmark_qualidade.main") as mock_bm,
            patch("sys.argv", ["agente"]),
        ):
            cmd_benchmark(argparse.Namespace(model=None, skip_rag=False, skip_no_rag=False, output="out.md"))
        mock_bm.assert_called_once()


class TestCmdCronograma:
    def test_cronograma_gera(self, monkeypatch, tmp_path):
        from cli import cmd_cronograma
        with (
            patch("agendador.gerar_e_salvar", return_value=tmp_path / "cron.md"),
            patch("agendador.gerar_cronograma", return_value=[]),
            patch("agendador.formatar_cronograma", return_value=""),
        ):
            cmd_cronograma(argparse.Namespace(output=str(tmp_path / "cron.md")))

    def test_cronograma_sem_output(self):
        from cli import cmd_cronograma
        with (
            patch("agendador.gerar_e_salvar", return_value=Path("cron.md")),
            patch("agendador.gerar_cronograma", return_value=[]),
            patch("agendador.formatar_cronograma", return_value=""),
        ):
            cmd_cronograma(argparse.Namespace(output=None))


class TestCmdRisco:
    def test_risco_gera(self, tmp_path):
        from cli import cmd_risco
        with (
            patch("risco_monte_carlo.simular_e_salvar", return_value=tmp_path / "risco.md"),
            patch("risco_monte_carlo.simular_aprovacao", return_value={}),
            patch("risco_monte_carlo.formatar_relatorio", return_value=""),
        ):
            cmd_risco(argparse.Namespace(output=str(tmp_path / "risco.md"), cenarios=100))

    def test_risco_default_cenarios(self):
        from cli import cmd_risco
        with (
            patch("risco_monte_carlo.simular_e_salvar", return_value=Path("risco.md")),
            patch("risco_monte_carlo.simular_aprovacao", return_value={}),
            patch("risco_monte_carlo.formatar_relatorio", return_value=""),
        ):
            cmd_risco(argparse.Namespace(output=None, cenarios=10000))


class TestCmdProvas:
    def test_provas_extrair(self):
        from cli import cmd_provas
        with (
            patch("extrair_provas_pdf.extrair_provas", return_value=[]),
            patch("extrair_provas_pdf.relatorio_provas", return_value="relatorio"),
        ):
            cmd_provas(argparse.Namespace(baixar=False, limite=10))

    def test_provas_extrair_com_resultados(self, tmp_path):
        from cli import cmd_provas
        with (
            patch("extrair_provas_pdf.extrair_provas", return_value=[{"disciplina": "Matemática"}]),
            patch("extrair_provas_pdf.relatorio_provas", return_value="# Relatório"),
            patch("cli.CLI_PYTHON", tmp_path),
        ):
            cmd_provas(argparse.Namespace(baixar=False, limite=10))

    def test_provas_baixar(self):
        from cli import cmd_provas
        with patch("extrair_provas_pdf.baixar_provas", return_value=[]) as mock:
            cmd_provas(argparse.Namespace(baixar=True, limite=5))
        mock.assert_called_once_with(limite=5)


class TestCmdAnki:
    def test_anki_csv(self, monkeypatch, tmp_path):
        from cli import cmd_anki
        with patch("exportar_anki.exportar_csv", return_value=5) as mock:
            cmd_anki(argparse.Namespace(formato="csv", output=str(tmp_path / "test.csv"), disciplina="Informática"))
        mock.assert_called_once_with(Path(str(tmp_path / "test.csv")), "Informática")

    def test_anki_apkg(self, tmp_path):
        from cli import cmd_anki
        with patch("exportar_anki.exportar_apkg", return_value=5) as mock:
            cmd_anki(argparse.Namespace(formato="apkg", output=str(tmp_path / "test.apkg"), disciplina=""))
        mock.assert_called_once_with(Path(str(tmp_path / "test.apkg")), "")

    def test_anki_sem_resultados(self, capsys):
        from cli import cmd_anki
        with patch("exportar_anki.exportar_csv", return_value=0):
            cmd_anki(argparse.Namespace(formato="csv", output="out.csv", disciplina="Inexistente"))
        captured = capsys.readouterr()
        assert "Nenhuma questão exportada" in captured.out


class TestCmdPerfil:
    def test_perfil_sem_arquivo(self, monkeypatch, capsys):
        from cli import cmd_perfil
        with patch("pathlib.Path.exists", return_value=False):
            cmd_perfil(argparse.Namespace())
        captured = capsys.readouterr()
        assert "Perfil não encontrado" in captured.out

    def test_perfil_com_arquivo(self, tmp_path, capsys):
        from cli import cmd_perfil
        dados_dir = tmp_path / "dados"
        dados_dir.mkdir()
        perfil_path = dados_dir / "perfil_candidato.json"
        perfil_path.write_text('{"cargo_alvo": "Engenheiro"}', encoding="utf-8")

        with patch("cli.CLI_PYTHON", tmp_path):
            cmd_perfil(argparse.Namespace())
        captured = capsys.readouterr()
        assert "cargo_alvo" in captured.out
        assert "Engenheiro" in captured.out


class TestCmdMetricas:
    def test_metricas_sem_dados(self, monkeypatch, capsys):
        from cli import cmd_metricas
        with (
            patch("metricas.painel", return_value=""),
        ):
            cmd_metricas(argparse.Namespace())
        captured = capsys.readouterr()
        assert "Sem dados suficientes" in captured.out or "Sem dados" in captured.out

    def test_metricas_com_dados(self, capsys):
        from cli import cmd_metricas
        with (
            patch("metricas.painel", return_value="Painel de métricas com 10 sessões"),
        ):
            cmd_metricas(argparse.Namespace())
        captured = capsys.readouterr()
        assert "Painel" in captured.out


class TestDispatch:
    def test_comando_desconhecido(self, monkeypatch):
        from cli import main as cli_main
        monkeypatch.setattr(sys, "argv", ["agente", "comando_invalido"])
        try:
            cli_main()
        except SystemExit:
            pass

    def test_parser_simulado_args(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["agente", "simulado", "--help"])
        try:
            from cli import main as cli_main
            cli_main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "questoes" in captured.out or "-n" in captured.out

    def test_parser_benchmark_args(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["agente", "benchmark", "--help"])
        try:
            from cli import main as cli_main
            cli_main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "model" in captured.out

    def test_parser_provas_args(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["agente", "provas", "--help"])
        try:
            from cli import main as cli_main
            cli_main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "baixar" in captured.out

    def test_parser_anki_args(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["agente", "anki", "--help"])
        try:
            from cli import main as cli_main
            cli_main()
        except SystemExit:
            pass
        captured = capsys.readouterr()
        assert "formato" in captured.out

    def test_main_dispatch_chart(self, monkeypatch):
        from cli import main as cli_main
        monkeypatch.setattr(sys, "argv", ["agente", "chat"])
        with monkeypatch.context() as m:
            m.setattr("builtins.input", lambda _: "/sair")
            try:
                cli_main()
            except (SystemExit, Exception):
                pass

    def test_stdout_reconfigure_fallback(self, monkeypatch):
        class MockStdout:
            encoding = "utf-8"
            def reconfigure(self, **kwargs):
                raise AttributeError("no reconfigure")
        monkeypatch.setattr(sys, "stdout", MockStdout())
        import importlib
        import cli
        importlib.reload(cli)
