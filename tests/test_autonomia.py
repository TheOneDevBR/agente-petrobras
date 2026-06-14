"""Testes do núcleo autônomo (autonomia.py)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import autonomia as A  # noqa: E402


def _info_fake(**over):
    """SistemaInfo mínimo para alimentar funções puras sem rodar diagnóstico real."""
    base = dict(
        erros_sintaxe=0, testes_total=480, total_modulos=22, modulos_saudaveis=22,
        modulos_problematicos=0,
        conhecimento={"intel_dias": 1, "questoes": 503, "simulados": 5, "beats": 13},
    )
    base.update(over)
    return type("InfoFake", (), base)()


class TestEscanearModulos:
    def test_escaneia_cli_python(self):
        mods = A.escanear_modulos()
        assert len(mods) > 10
        nomes = {m.nome for m in mods}
        assert "treino.py" in nomes
        assert "autonomia.py" not in nomes  # auto-exclusão

    def test_modulos_saudaveis(self):
        # nenhum módulo do projeto deve estar quebrado
        assert all(m.saudavel for m in A.escanear_modulos())


class TestImports:
    def test_import_local_ignorado(self):
        mod = A.ModuloInfo("x.py", 10, 0, 0, ["treino", "perfil"], [], "", True)
        assert A.verificar_imports_quebrados(mod) == []

    def test_import_inexistente_flagado(self):
        mod = A.ModuloInfo("x.py", 10, 0, 0, ["pacote_que_nao_existe_zzz"], [], "", True)
        problemas = A.verificar_imports_quebrados(mod)
        assert len(problemas) == 1 and "pacote_que_nao_existe_zzz" in problemas[0]


class TestAutoCura:
    def test_auto_cura_sem_instalar(self):
        res = A.auto_cura(instalar=False)
        assert isinstance(res, A.ResultadoCura)
        # nenhum import deve ser "curado" quando instalar=False
        assert all(not d.cura_aplicada for d in res.diagnosticos)

    def test_auto_cura_nao_roda_pip_quando_desligado(self):
        with patch.object(A, "_tentar_instalar_pacote") as mock_pip:
            A.auto_cura(instalar=False)
        mock_pip.assert_not_called()


class TestGaps:
    def test_gaps_ordenados_por_prioridade(self):
        gaps = A.analisar_gaps(_info_fake())
        prioridades = [g.prioridade for g in gaps]
        assert prioridades == sorted(prioridades)

    def test_gap_erro_sintaxe_top(self):
        gaps = A.analisar_gaps(_info_fake(erros_sintaxe=2))
        assert gaps[0].prioridade == 1 and "sintaxe" in gaps[0].nome.lower()

    def test_gap_intel_desatualizada(self):
        gaps = A.analisar_gaps(_info_fake(conhecimento={"intel_dias": 30, "questoes": 503}))
        assert any("inteligência" in g.nome.lower() for g in gaps)


class TestSugestoes:
    def test_intel_fresca_sem_alerta_de_coleta(self):
        sugs = A.gerar_sugestoes_proativas(_info_fake(conhecimento={"intel_dias": 1, "simulados": 5}))
        assert not any("coletad" in s.descricao.lower() for s in sugs)

    def test_intel_ausente_sugere_coleta_alta(self):
        sugs = A.gerar_sugestoes_proativas(_info_fake(conhecimento={"intel_dias": None, "simulados": 0}))
        coleta = [s for s in sugs if "coletor" in s.comando_sugerido]
        assert coleta and coleta[0].urgencia == "alta"

    def test_sem_simulados_sugere_simulado(self):
        sugs = A.gerar_sugestoes_proativas(_info_fake(conhecimento={"intel_dias": 1, "simulados": 0}))
        assert any(s.comando_sugerido == "agente simulado" for s in sugs)


class TestWebLearning:
    def test_auto_web_learning_reusa_coletor(self):
        with (
            patch.object(A, "_beats_por_frescor", return_value=["editais", "noticias"]),
            patch.object(A, "_rodar_beat", return_value=(True, "ok")) as mock_run,
        ):
            res = A.auto_web_learning(max_beats=1)
        mock_run.assert_called_once()
        assert res.beats_rodados == ["editais"] and res.novos_conhecimentos == 1

    def test_auto_web_learning_coleta_erro(self):
        with (
            patch.object(A, "_beats_por_frescor", return_value=["editais"]),
            patch.object(A, "_rodar_beat", return_value=(False, "falhou")),
        ):
            res = A.auto_web_learning(max_beats=1)
        assert res.beats_rodados == [] and res.erros


class TestCicloAutonomo:
    def test_ciclo_estrutura_e_guardrail(self):
        """O ciclo monta passos e enfileira sugestões SEM executá-las."""
        with (
            patch.object(A, "autodiagnostico_completo", return_value=_info_fake()),
            patch.object(A, "auto_cura", return_value=A.ResultadoCura(
                timestamp="t", diagnosticos=[], total_problemas=0, total_curados=0, total_falhas=0)),
            patch.object(A, "auto_web_learning", return_value=A.ResultadoWebLearning(
                timestamp="t", beats_rodados=["editais"], novos_conhecimentos=1, resumo="ok")),
            patch.object(A, "gerar_sugestoes_proativas", return_value=[
                A.SugestaoProativa("faça simulado", "agente simulado", "media")]),
            patch.object(A, "_salvar_metricas"),
            patch("subprocess.run") as mock_sub,
        ):
            rel = A.ciclo_autonomo()
        assert set(rel["passos"]) >= {"diagnostico", "cura", "aprendizado", "sugestoes"}
        # guardrail: a sugestão fica pendente, nunca é executada
        assert rel["pendentes"][0]["comando"] == "agente simulado"
        mock_sub.assert_not_called()

    def test_ciclo_sem_aprender(self):
        with (
            patch.object(A, "autodiagnostico_completo", return_value=_info_fake()),
            patch.object(A, "auto_cura", return_value=A.ResultadoCura("t", [], 0, 0, 0)),
            patch.object(A, "auto_web_learning") as mock_wl,
            patch.object(A, "gerar_sugestoes_proativas", return_value=[]),
            patch.object(A, "_salvar_metricas"),
        ):
            rel = A.ciclo_autonomo(aprender=False)
        mock_wl.assert_not_called()
        assert "aprendizado" not in rel["passos"]


class TestTarefas:
    def test_tarefa_desconhecida(self):
        res = A.executar_tarefa("inexistente")
        assert res["ok"] is False

    def test_tarefa_conhecida(self):
        fake = MagicMock(returncode=0, stdout="feito")
        with patch("subprocess.run", return_value=fake):
            res = A.executar_tarefa("coletar")
        assert res["ok"] is True and res["tarefa"] == "coletar"


class TestPainel:
    def test_painel_resumo(self):
        with patch.object(A, "autodiagnostico_completo", return_value=A.SistemaInfo(
            timestamp="t", modulos=[], total_modulos=22, total_linhas=9000,
            total_classes=30, total_funcoes=400, testes_passando=480, testes_total=480,
            erros_sintaxe=0, modulos_saudaveis=22, modulos_problematicos=0,
            conhecimento={"intel_dias": 1, "questoes": 503, "simulados": 5},
            metricas=A.MetricasSistema(
                timestamp="t", modulos_python=22, linhas_codigo=9000, classes=30,
                funcoes=400, testes_total=480, testes_passando=480, notas_inteligencia=19,
                beats_configurados=13, questoes_banco=503, simulados_registrados=5,
                leis_rag=9, comandos_cli=12, erros_ativos=0, alertas_saude=0),
        )):
            saida = A.painel_comando("resumo")
        assert "PAINEL DE AUTONOMIA" in saida and "503" in saida


class TestCLI:
    def test_cmd_autonomia_painel(self, capsys):
        from cli import cmd_autonomia
        with patch("autonomia.painel_comando", return_value="PAINEL X") as mock:
            cmd_autonomia(argparse.Namespace(ciclo=False, gaps=False, confirmar=False))
        mock.assert_called_once()
        assert "PAINEL X" in capsys.readouterr().out

    def test_cmd_autonomia_ciclo(self, capsys):
        from cli import cmd_autonomia
        with patch("autonomia.ciclo_autonomo", return_value={"passos": {}, "pendentes": []}) as mock:
            cmd_autonomia(argparse.Namespace(ciclo=True, gaps=False, confirmar=False))
        mock.assert_called_once()
        assert "passos" in capsys.readouterr().out

    def test_subcomando_registrado(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["agente", "--help"])
        try:
            from cli import main as cli_main
            cli_main()
        except SystemExit:
            pass
        assert "autonomia" in capsys.readouterr().out
