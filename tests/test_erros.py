"""Testes da classificação de erros C/A/B/T (erros.py)."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

import erros as E  # noqa: E402


@dataclass
class QFake:
    pergunta: str = "q?"
    opcoes: list = field(default_factory=lambda: ["a", "b"])
    correta: int = 0


class TestClassificar:
    def test_autorrelato_tem_prioridade(self):
        cat, motivo = E.classificar(autorrelato="b", tempo_seg=5)
        assert cat == "B" and "autorrelato" in motivo

    def test_autorrelato_invalido_ignorado(self):
        cat, _ = E.classificar(autorrelato="Z", tempo_seg=5)
        assert cat == "A"  # cai na heurística de tempo baixo

    def test_heuristica_tempo_baixo_atencao(self):
        cat, _ = E.classificar(tempo_seg=5)
        assert cat == "A"

    def test_heuristica_tempo_alto_interpretacao(self):
        cat, _ = E.classificar(tempo_seg=120)
        assert cat == "B"

    def test_default_conteudo(self):
        cat, motivo = E.classificar()
        assert cat == "C" and "assumido" in motivo

    def test_llm_quando_disponivel(self):
        cli = MagicMock()
        cli.chat.return_value = "B"
        cat, motivo = E.classificar(questao=QFake(), escolha=1, cliente=cli)
        assert cat == "B" and "LLM" in motivo


class TestAgregacao:
    def test_registrar_e_distribuir(self):
        est = E.estado_vazio()
        E.registrar_erro("Português", "A", estado=est)
        E.registrar_erro("Português", "A", estado=est)
        E.registrar_erro("Matemática", "C", estado=est)
        dist = E.distribuicao(est)
        assert dist["total"] == 3
        assert dist["dominante"] == "A"
        assert dist["contagem"]["A"] == 2
        assert est["por_disciplina"]["Português"]["A"] == 2

    def test_categoria_invalida_vira_C(self):
        est = E.estado_vazio()
        E.registrar_erro("X", "Z", estado=est)
        assert est["contagem"]["C"] == 1

    def test_prescricao_por_erro(self):
        assert "ATENÇÃO" in E.prescricao_por_erro("A")
        assert "Sem erros" in E.prescricao_por_erro(None)

    def test_distribuicao_vazia(self):
        d = E.distribuicao(E.estado_vazio())
        assert d["total"] == 0 and d["dominante"] is None


class TestPersistencia:
    def test_round_trip(self, tmp_path):
        est = E.estado_vazio()
        E.registrar_erro("Port", "T", estado=est)
        p = tmp_path / "e.json"
        E.salvar(est, p)
        assert E.carregar(p)["contagem"]["T"] == 1

    def test_formatar(self):
        est = E.estado_vazio()
        E.registrar_erro("Port", "B", estado=est)
        txt = E.formatar_distribuicao(est)
        assert "PERFIL DE ERROS" in txt and "INTERPRETAÇÃO" in txt
