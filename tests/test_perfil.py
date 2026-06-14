"""Testes do módulo perfil (persistência do candidato)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from perfil import (
    _coagir,
    aplicar_diretivas,
    carregar,
    esta_vazio,
    perfil_vazio,
    resumo_para_prompt,
    salvar,
)


class TestPerfilVazio:
    def test_perfil_vazio_tem_campos_essenciais(self):
        p = perfil_vazio()
        assert "_criado_em" in p
        assert "_atualizado_em" in p
        assert p["cargo_alvo"] is None
        assert p["historico_acerto"] == {}
        assert p["distribuicao_erros"] == {"C": None, "A": None, "B": None, "T": None}

    def test_perfil_vazio_data_hoje(self):
        from datetime import date
        p = perfil_vazio()
        assert p["_criado_em"] == date.today().isoformat()


class TestCarregar:
    def test_carregar_arquivo_valido(self, tmp_path):
        perfil_path = tmp_path / "perfil.json"
        dados = {"cargo_alvo": "Engenheiro", "horas_dia_util": 3}
        perfil_path.write_text(json.dumps(dados), encoding="utf-8")
        resultado = carregar(perfil_path)
        assert resultado["cargo_alvo"] == "Engenheiro"
        assert resultado["horas_dia_util"] == 3

    def test_carregar_arquivo_inexistente(self, tmp_path):
        perfil_path = tmp_path / "inexistente.json"
        resultado = carregar(perfil_path)
        assert resultado["cargo_alvo"] is None
        assert "_criado_em" in resultado

    def test_carregar_json_invalido(self, tmp_path):
        perfil_path = tmp_path / "corrompido.json"
        perfil_path.write_text("{invalido}", encoding="utf-8")
        resultado = carregar(perfil_path)
        assert resultado["cargo_alvo"] is None

    def test_carregar_arquivo_vazio(self, tmp_path):
        perfil_path = tmp_path / "vazio.json"
        perfil_path.write_text("", encoding="utf-8")
        resultado = carregar(perfil_path)
        assert resultado["cargo_alvo"] is None

    def test_carregar_mescla_com_defaults(self, tmp_path):
        perfil_path = tmp_path / "parcial.json"
        perfil_path.write_text(json.dumps({"cargo_alvo": "Analista"}), encoding="utf-8")
        resultado = carregar(perfil_path)
        assert resultado["cargo_alvo"] == "Analista"
        assert resultado["horas_dia_util"] is None


class TestSalvar:
    def test_salvar_cria_arquivo(self, tmp_path):
        perfil_path = tmp_path / "dados" / "perfil.json"
        perfil = perfil_vazio()
        perfil["cargo_alvo"] = "Engenheiro"
        salvar(perfil, perfil_path)
        assert perfil_path.exists()
        dados = json.loads(perfil_path.read_text(encoding="utf-8"))
        assert dados["cargo_alvo"] == "Engenheiro"
        from datetime import date
        assert dados["_atualizado_em"] == date.today().isoformat()

    def test_salvar_atualiza_data(self, tmp_path):
        perfil_path = tmp_path / "perfil.json"
        perfil = perfil_vazio()
        perfil["_atualizado_em"] = "2020-01-01"
        salvar(perfil, perfil_path)
        from datetime import date
        dados = json.loads(perfil_path.read_text(encoding="utf-8"))
        assert dados["_atualizado_em"] == date.today().isoformat()

    def test_salvar_sobrescreve(self, tmp_path):
        perfil_path = tmp_path / "perfil.json"
        perfil_path.write_text(json.dumps({"cargo_alvo": "Velho"}), encoding="utf-8")
        perfil = perfil_vazio()
        perfil["cargo_alvo"] = "Novo"
        salvar(perfil, perfil_path)
        dados = json.loads(perfil_path.read_text(encoding="utf-8"))
        assert dados["cargo_alvo"] == "Novo"


class TestAplicarDiretivas:
    def test_aplicar_diretiva_simples(self):
        perfil = perfil_vazio()
        texto = "Bom trabalho! <<ATUALIZAR_PERFIL: cargo_alvo = Engenheiro>> Continue."
        limpo, mudancas = aplicar_diretivas(texto, perfil)
        assert perfil["cargo_alvo"] == "Engenheiro"
        assert "cargo_alvo = Engenheiro" in mudancas
        assert "<<ATUALIZAR_PERFIL:" not in limpo

    def test_aplicar_diretiva_numerica(self):
        perfil = perfil_vazio()
        texto = "<<ATUALIZAR_PERFIL: horas_dia_util = 4>>"
        aplicar_diretivas(texto, perfil)
        assert perfil["horas_dia_util"] == 4

    def test_aplicar_diretiva_float(self):
        perfil = perfil_vazio()
        texto = "<<ATUALIZAR_PERFIL: probabilidade_aprovacao = 0.75>>"
        aplicar_diretivas(texto, perfil)
        assert perfil["probabilidade_aprovacao"] == 0.75

    def test_aplicar_diretiva_none(self):
        perfil = perfil_vazio()
        perfil["cargo_alvo"] = "Engenheiro"
        texto = "<<ATUALIZAR_PERFIL: cargo_alvo = null>>"
        aplicar_diretivas(texto, perfil)
        assert perfil["cargo_alvo"] is None

    def test_aplicar_diretiva_subcampo(self):
        perfil = perfil_vazio()
        texto = "<<ATUALIZAR_PERFIL: historico_acerto.portugues = 85>>"
        aplicar_diretivas(texto, perfil)
        assert perfil["historico_acerto"]["portugues"] == 85

    def test_aplicar_diretivas_multiplas(self):
        perfil = perfil_vazio()
        texto = "<<ATUALIZAR_PERFIL: cargo_alvo = Analista>> e <<ATUALIZAR_PERFIL: horas_dia_util = 5>>"
        limpo, mudancas = aplicar_diretivas(texto, perfil)
        assert perfil["cargo_alvo"] == "Analista"
        assert perfil["horas_dia_util"] == 5
        assert len(mudancas) == 2

    def test_sem_diretivas_retorna_texto_original(self):
        perfil = perfil_vazio()
        texto = "Apenas um texto normal sem diretivas."
        limpo, mudancas = aplicar_diretivas(texto, perfil)
        assert limpo == texto
        assert mudancas == []

    def test_streak_atualiza_maior_streak(self):
        perfil = perfil_vazio()
        perfil["streak_dias"] = 10
        texto = "<<ATUALIZAR_PERFIL: streak_dias = 10>>"
        aplicar_diretivas(texto, perfil)
        assert perfil["maior_streak"] == 10

    def test_streak_nao_diminui_maior(self):
        perfil = perfil_vazio()
        perfil["maior_streak"] = 15
        texto = "<<ATUALIZAR_PERFIL: streak_dias = 5>>"
        aplicar_diretivas(texto, perfil)
        assert perfil["maior_streak"] == 15

    def test_streak_typeerror_tratado(self):
        perfil = perfil_vazio()
        perfil["streak_dias"] = "string"
        texto = "<<ATUALIZAR_PERFIL: streak_dias = 5>>"
        aplicar_diretivas(texto, perfil)
        # Should not raise TypeError


class TestCoagir:
    def test_coagir_nulo(self):
        assert _coagir("null") is None
        assert _coagir("none") is None
        assert _coagir("nenhum") is None
        assert _coagir("-") is None

    def test_coagir_inteiro(self):
        assert _coagir("42") == 42
        assert _coagir("-7") == -7

    def test_coagir_float(self):
        assert _coagir("3.14") == 3.14
        assert _coagir("-0.5") == -0.5

    def test_coagir_string(self):
        assert _coagir("Texto") == "Texto"
        assert _coagir('"com aspas"') == "com aspas"
        assert _coagir("'simples'") == "simples"


class TestEstaVazio:
    def test_vazio_sem_cargo(self):
        assert esta_vazio(perfil_vazio()) is True

    def test_nao_vazio_com_cargo(self):
        p = perfil_vazio()
        p["cargo_alvo"] = "Engenheiro"
        assert esta_vazio(p) is False


class TestResumoParaPrompt:
    def test_resumo_vazio(self):
        p = perfil_vazio()
        resumo = resumo_para_prompt(p)
        assert "VAZIO" in resumo
        assert "DIAGNÓSTICO INICIAL" in resumo

    def test_resumo_com_dados(self):
        p = perfil_vazio()
        p["cargo_alvo"] = "Engenheiro"
        p["horas_dia_util"] = 3
        resumo = resumo_para_prompt(p)
        assert "[PERFIL_CANDIDATO]" in resumo
        assert "Engenheiro" in resumo
        assert "horas_dia_util" in resumo

    def test_resumo_filtra_campos_internos(self):
        p = perfil_vazio()
        p["cargo_alvo"] = "Analista"
        p["_criado_em"] = "2026-01-01"
        resumo = resumo_para_prompt(p)
        assert "_criado_em" not in resumo
