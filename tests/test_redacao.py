"""Testes do avaliador de redação (redacao.py)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import redacao as R  # noqa: E402

_TEXTO_LONGO = ("A transição energética é um tema central. " * 30).strip()


class TestEstrutural:
    def test_vazio(self):
        r = R.avaliar("", tema="X")
        assert r["avaliado_por"] == "estrutural" and "vazio" in r["feedback"].lower()

    def test_curto(self):
        r = R.avaliar("Texto bem curto aqui.", tema="X")
        assert r["avaliado_por"] == "estrutural"
        assert "curto" in r["feedback"].lower()
        assert r["nota_total"] is None

    def test_sem_llm_faz_estrutural(self):
        r = R.avaliar(_TEXTO_LONGO, tema="Energia", cliente=None)
        assert r["avaliado_por"] == "estrutural"
        assert r["metricas"]["palavras"] >= R.MIN_PALAVRAS


class TestComLLM:
    def _cli(self, payload):
        cli = MagicMock()
        cli.chat.return_value = payload
        return cli

    def test_avalia_por_rubrica(self):
        payload = (
            '{"criterios": {"tema": {"nota": 2.0, "comentario": "ok"}, '
            '"conteudo": {"nota": 2.5, "comentario": "bom"}, '
            '"estrutura": {"nota": 2.0, "comentario": "coeso"}, '
            '"norma": {"nota": 1.5, "comentario": "alguns desvios"}}, '
            '"feedback": "Melhore a conclusão."}'
        )
        r = R.avaliar(_TEXTO_LONGO, tema="Energia", cliente=self._cli(payload))
        assert r["avaliado_por"] == "llm"
        assert r["nota_total"] == 8.0  # 2+2.5+2+1.5
        assert r["criterios"]["norma"]["max"] == 2.0
        assert "conclusão" in r["feedback"].lower()

    def test_clampa_nota_acima_do_maximo(self):
        # tema max=2.5; LLM tenta dar 9 → deve limitar a 2.5
        payload = '{"criterios": {"tema": {"nota": 9, "comentario": "x"}}, "feedback": "f"}'
        r = R.avaliar(_TEXTO_LONGO, tema="E", cliente=self._cli(payload))
        assert r["criterios"]["tema"]["nota"] == 2.5

    def test_json_invalido_nao_quebra(self):
        r = R.avaliar(_TEXTO_LONGO, tema="E", cliente=self._cli("desculpe, não consegui"))
        # sem JSON → notas zeram, mas não lança
        assert r["avaliado_por"] == "llm" and r["nota_total"] == 0.0

    def test_llm_excecao_cai_para_estrutural(self):
        cli = MagicMock()
        cli.chat.side_effect = RuntimeError("offline")
        r = R.avaliar(_TEXTO_LONGO, tema="E", cliente=cli)
        assert r["avaliado_por"] == "estrutural"


class TestFormatar:
    def test_formatar_estrutural(self):
        assert "AVALIAÇÃO DE REDAÇÃO" in R.formatar(R.avaliar("", tema="X"))
