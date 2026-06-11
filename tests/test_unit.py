"""Testes unitários — métricas, perfil, parser tool call, formatação.
Uso: pytest tests/ -v
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from metricas import (
    _categoria_de,
    _barra,
    consistencia_semanal,
    dias_ate_prova,
    painel,
    projecao_nota,
    streak_de_sessoes,
)
from perfil import (
    _coagir,
    _set_campo,
    aplicar_diretivas,
    esta_vazio,
    perfil_vazio,
)

from local_llm import LocalLLM

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python" / "coletor"))
try:
    from coletor import _fix_nota, _slug, _extrair_resumo
except ImportError:
    # _fix_nota e _extrair_resumo dependem de imports complexos
    # _slug só usa re — implementação local para testes
    _fix_nota = _extrair_resumo = None
    import re as _re
    def _slug(texto: str) -> str:
        s = _re.sub(r"[^\w\s-]", "", texto.lower(), flags=_re.UNICODE)
        s = _re.sub(r"[\s_-]+", "-", s).strip("-")
        return s or "nota"


# ══════════════════════════════════════════════════════════════════════════
# metricas.py
# ══════════════════════════════════════════════════════════════════════════

class TestDiasAteProva:
    def test_formato_iso(self):
        dp = {"data_prova": (date.today() + timedelta(days=30)).isoformat()}
        assert dias_ate_prova(dp) == 30

    def test_formato_br(self):
        dp = {"data_prova": (date.today() + timedelta(days=15)).strftime("%d/%m/%Y")}
        assert dias_ate_prova(dp) == 15

    def test_sem_data(self):
        assert dias_ate_prova({}) is None

    def test_data_passada(self):
        dp = {"data_prova": (date.today() - timedelta(days=5)).isoformat()}
        assert dias_ate_prova(dp) == -5

    def test_data_invalida(self):
        dp = {"data_prova": "99/99/9999"}
        assert dias_ate_prova(dp) is None


class TestCategoriaDe:
    def test_portugues(self):
        assert _categoria_de("Língua Portuguesa") == "portugues"
        assert _categoria_de("gramática aplicada") == "portugues"
        assert _categoria_de("Interpretação de Texto") == "portugues"

    def test_rl_mat(self):
        assert _categoria_de("Raciocínio Lógico") == "rl_mat"
        assert _categoria_de("Matemática Financeira") == "rl_mat"

    def test_legislacao(self):
        assert _categoria_de("Lei 13.303") == "legislacao"
        assert _categoria_de("LGPD") == "legislacao"

    def test_petrobras(self):
        assert _categoria_de("Conhecimentos Petrobras") == "petrobras"
        assert _categoria_de("Pré-Sal") == "petrobras"

    def test_default_especificos(self):
        assert _categoria_de("Física") == "especificos"
        assert _categoria_de("Química do Petróleo") == "especificos"


class TestStreak:
    def test_sem_sessoes(self):
        assert streak_de_sessoes([]) == 0

    def test_streak_1_hoje(self):
        s = [{"data": date.today().isoformat()}]
        assert streak_de_sessoes(s) == 1

    def test_streak_1_ontem(self):
        s = [{"data": (date.today() - timedelta(days=1)).isoformat()}]
        assert streak_de_sessoes(s) == 1

    def test_streak_3_dias(self):
        hoje = date.today()
        s = [{"data": (hoje - timedelta(days=i)).isoformat()} for i in range(3)]
        assert streak_de_sessoes(s) == 3

    def test_streak_quebrado(self):
        hoje = date.today()
        s = [
            {"data": hoje.isoformat()},
            {"data": (hoje - timedelta(days=2)).isoformat()},
        ]
        assert streak_de_sessoes(s) == 1  # só hoje conta

    def test_streak_antigo(self):
        s = [{"data": (date.today() - timedelta(days=5)).isoformat()}]
        assert streak_de_sessoes(s) == 0

    def test_datas_duplicadas(self):
        hoje = date.today().isoformat()
        s = [{"data": hoje}, {"data": hoje}, {"data": hoje}]
        assert streak_de_sessoes(s) == 1


class TestConsistenciaSemanal:
    def test_excelente(self):
        hoje = date.today()
        sessoes = [{"data": (hoje - timedelta(days=i)).isoformat(), "questoes": 50} for i in range(7)]
        ic = consistencia_semanal(sessoes, meta_questoes_semana=200)
        assert ic["ic"] >= 0.85
        assert ic["nivel"] == "EXCELENTE"

    def test_critico_zero(self):
        ic = consistencia_semanal([], meta_questoes_semana=200)
        assert ic["ic"] <= 0.15
        assert ic["nivel"] == "CRÍTICA (intervenção)"

    def test_adequado(self):
        hoje = date.today()
        sessoes = [{"data": (hoje - timedelta(days=i)).isoformat(), "questoes": 20} for i in range(5)]
        ic = consistencia_semanal(sessoes, meta_questoes_semana=200)
        assert 0.65 > ic["ic"] >= 0.15
        assert ic["nivel"] == "CRÍTICA (intervenção)"  # poucas questões


class TestProjecaoNota:
    def test_vazio(self):
        assert projecao_nota({}, meta_acerto=None) is None

    def test_calculo_simples(self):
        hist = {"portugues": 80, "matematica": 70}
        proj = projecao_nota(hist, meta_acerto=75)
        assert proj is not None
        assert "nota_projetada" in proj
        assert "gap_para_meta" in proj
        assert "cobertura_pct" in proj
        assert 0 < proj["nota_projetada"] < 100

    def test_gap_para_meta(self):
        hist = {"portugues": 60}
        proj = projecao_nota(hist, meta_acerto=80)
        assert proj["gap_para_meta"] > 0  # falta pra chegar na meta

    def test_acima_da_meta(self):
        hist = {"portugues": 95}
        proj = projecao_nota(hist, meta_acerto=80)
        assert proj["gap_para_meta"] < 0  # acima da meta


class TestPainel:
    def test_vazio_sem_dados(self):
        p = painel({}, [])
        assert p == ""

    def test_com_data_prova(self):
        dp = {"data_prova": (date.today() + timedelta(days=60)).isoformat()}
        p = painel(dp, [])
        assert "PAINEL_DE_CONTROLE" in p
        assert "60" in p

    def test_janela_curta(self):
        dp = {"data_prova": (date.today() + timedelta(days=5)).isoformat()}
        p = painel(dp, [])
        assert "JANELA CURTA" in p

    def test_com_streak(self):
        p = painel({}, [{"data": date.today().isoformat()}])
        assert "Streak" in p


class TestBarra:
    def test_0(self):
        assert _barra(0) == "░" * 20

    def test_100(self):
        assert _barra(100) == "█" * 20

    def test_50(self):
        b = _barra(50)
        assert b.count("█") == 10
        assert b.count("░") == 10


# ══════════════════════════════════════════════════════════════════════════
# perfil.py
# ══════════════════════════════════════════════════════════════════════════

class TestCoagir:
    def test_nulo(self):
        assert _coagir("null") is None
        assert _coagir("none") is None
        assert _coagir("nenhum") is None

    def test_int(self):
        assert _coagir("42") == 42
        assert _coagir("-5") == -5

    def test_float(self):
        assert _coagir("3.14") == 3.14

    def test_string(self):
        assert _coagir("engenheiro") == "engenheiro"
        assert _coagir('"valor com aspas"') == "valor com aspas"


class TestSetCampo:
    def test_campo_simples(self):
        p = {}
        _set_campo(p, "cargo_alvo", "Engenheiro")
        assert p["cargo_alvo"] == "Engenheiro"

    def test_campo_aninhado(self):
        p = {}
        _set_campo(p, "historico_acerto.portugues", 85)
        assert p["historico_acerto"]["portugues"] == 85

    def test_sobrescreve(self):
        p = {"x": {"y": 1}}
        _set_campo(p, "x.y", 2)
        assert p["x"]["y"] == 2


class TestAplicarDiretivas:
    def test_extrai_e_remove(self):
        texto = "blah <<ATUALIZAR_PERFIL: cargo_alvo = Engenheiro>> fim"
        perfil = {}
        limpo, mudancas = aplicar_diretivas(texto, perfil)
        assert perfil.get("cargo_alvo") == "Engenheiro"
        assert "blah" in limpo
        assert "fim" in limpo
        assert "ATUALIZAR_PERFIL" not in limpo
        assert len(mudancas) == 1

    def test_multiplas_diretivas(self):
        texto = "a <<ATUALIZAR_PERFIL: x = 1>> b <<ATUALIZAR_PERFIL: y = 2>> c"
        p = {}
        limpo, mudancas = aplicar_diretivas(texto, p)
        assert p["x"] == 1
        assert p["y"] == 2
        assert len(mudancas) == 2
        assert "a  b  c" == limpo

    def test_sem_diretiva(self):
        texto = "apenas texto normal"
        p = {"cargo_alvo": "X"}
        limpo, mud = aplicar_diretivas(texto, p)
        assert limpo == texto
        assert mud == []

    def test_campo_aninhado_na_diretiva(self):
        texto = "<<ATUALIZAR_PERFIL: historico_acerto.portugues = 88>>"
        p = {}
        aplicar_diretivas(texto, p)
        assert p["historico_acerto"]["portugues"] == 88

    def test_valor_nulo(self):
        texto = "<<ATUALIZAR_PERFIL: nivel_ansiedade = null>>"
        p = {"nivel_ansiedade": "ALTO"}
        aplicar_diretivas(texto, p)
        assert p["nivel_ansiedade"] is None

    def test_maior_streak_atualiza(self):
        texto = "<<ATUALIZAR_PERFIL: streak_dias = 10>>"
        p = {"streak_dias": 10, "maior_streak": 5}
        aplicar_diretivas(texto, p)
        assert p["maior_streak"] == 10


class TestEstaVazio:
    def test_vazio(self):
        assert esta_vazio(perfil_vazio()) is True

    def test_com_cargo(self):
        p = perfil_vazio()
        p["cargo_alvo"] = "Engenheiro"
        assert esta_vazio(p) is False


class TestPerfilVazio:
    def test_estrutura(self):
        p = perfil_vazio()
        assert "_criado_em" in p
        assert "cargo_alvo" in p
        assert p["cargo_alvo"] is None
        assert "historico_acerto" in p
        assert "distribuicao_erros" in p
        assert p["distribuicao_erros"]["C"] is None


# ══════════════════════════════════════════════════════════════════════════
# local_llm.py — _parse_tool_call
# ══════════════════════════════════════════════════════════════════════════

class TestParseToolCall:
    def setup_method(self):
        self.llm = LocalLLM(base_url="http://localhost:11434", model="test")

    def test_json_simples(self):
        result = self.llm._parse_tool_call('{"name": "web_search", "arguments": {"query": "edital"}}')
        assert result is not None
        name, args = result
        assert name == "web_search"
        assert args["query"] == "edital"

    def test_com_fence(self):
        result = self.llm._parse_tool_call(
            '```json\n{"name": "web_search", "arguments": {"query": "petrobras"}}\n```'
        )
        assert result is not None
        assert result[0] == "web_search"

    def test_funcao_aninhada(self):
        result = self.llm._parse_tool_call(
            '{"function": {"name": "web_fetch", "arguments": {"url": "http://ex.com"}}}'
        )
        assert result is not None
        name, args = result
        assert name == "web_fetch"
        assert args["url"] == "http://ex.com"

    def test_json_invalido(self):
        result = self.llm._parse_tool_call("isto não é json")
        assert result is None

    def test_sem_name(self):
        result = self.llm._parse_tool_call('{"foo": "bar"}')
        assert result is None

    def test_arguments_como_string(self):
        result = self.llm._parse_tool_call(
            '{"name": "web_search", "arguments": "{\\"query\\": \\"teste\\"}"}'
        )
        assert result is not None
        assert result[1]["query"] == "teste"


# ══════════════════════════════════════════════════════════════════════════
# coletor.py — funções auxiliares
# ══════════════════════════════════════════════════════════════════════════

class TestSlug:
    def test_simples(self):
        assert _slug("Editais e cronogramas") == "editais-e-cronogramas"

    def test_acentos(self):
        assert _slug("Tendências de cobrança") == "tendencias-de-cobranca"

    def test_caracteres_especiais(self):
        assert _slug("O&G (atualidades)") == "og-atualidades"

    def test_vazio(self):
        assert _slug("") == "nota"


class TestExtrairResumo:
    def test_com_resumo(self):
        texto = "resumo_uma_linha: Inscrições abertas até 30/04\n## Detalhes..."
        assert _extrair_resumo(texto) == "Inscrições abertas até 30/04"

    def test_sem_resumo(self):
        assert _extrair_resumo("## Resumo executivo\nblah") == "(sem resumo)"

    def test_resumo_com_aspas(self):
        texto = 'resumo_uma_linha: "Edital publicado" confirma'
        assert _extrair_resumo(texto) == '"Edital publicado" confirma'


class TestFixNota:
    def test_remove_code_fence(self):
        nota = "```markdown\nresumo_uma_linha: x\n## Detalhes\n```"
        fixed = _fix_nota(nota)
        assert "```" not in fixed
        assert fixed.startswith("resumo_uma_linha")

    def test_header_sem_dois_pontos(self):
        nota = "## Resumo executivo:\nblah"
        fixed = _fix_nota(nota)
        assert "## Resumo executivo\n" in fixed

    def test_adiciona_resumo_faltando(self):
        nota = "Artigo sobre licitações e contratos\nblah"
        fixed = _fix_nota(nota)
        assert fixed.startswith("resumo_uma_linha: Artigo sobre licitações")

    def test_remove_linhas_extras(self):
        nota = "texto significativo com mais de 10 caracteres\n\n\n\nb"
        fixed = _fix_nota(nota)
        assert "resumo_uma_linha:" in fixed
        assert "\n\n\n" not in fixed

    def test_vazio(self):
        assert _fix_nota("") == ""
        assert _fix_nota("  ") == ""
