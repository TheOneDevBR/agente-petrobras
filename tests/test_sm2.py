"""Testes do módulo SM-2 de repetição espaçada."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from sm2 import (
    calcular_proximo_intervalo,
    carregar,
    estatisticas,
    inicializar_do_banco,
    proximas_revisoes,
    registrar_revisao,
    revisoes_devidas,
    salvar,
)


def test_calcular_proximo_intervalo_qualidade_baixa():
    intervalo, ease, rep = calcular_proximo_intervalo(1, 5, 30, 2.5)
    assert intervalo == 1
    assert rep == 0
    assert ease >= 1.3


def test_calcular_proximo_intervalo_primeira_vez():
    intervalo, ease, rep = calcular_proximo_intervalo(5, 0, 0, 2.5)
    assert intervalo == 1
    assert rep == 1
    assert ease > 2.5

    # qualidade 4 mantém ease (não aumenta)
    _, ease2, _ = calcular_proximo_intervalo(4, 0, 0, 2.5)
    assert ease2 == 2.5


def test_calcular_proximo_intervalo_segunda_vez():
    intervalo, ease, rep = calcular_proximo_intervalo(5, 1, 1, 2.5)
    assert intervalo == 6
    assert rep == 2


def test_calcular_proximo_intervalo_terceira_vez():
    intervalo, ease, rep = calcular_proximo_intervalo(4, 2, 6, 2.5)
    assert intervalo == round(6 * 2.5)
    assert rep == 3


def test_calcular_proximo_intervalo_ease_minimo():
    intervalo, ease, rep = calcular_proximo_intervalo(0, 0, 0, 1.0)
    assert ease >= 1.3


def test_carregar_sem_arquivo(tmp_path):
    with patch("sm2.SM2_PATH", tmp_path / "nonexistent.json"):
        assert carregar() == []


def test_carregar_json_invalido(tmp_path):
    p = tmp_path / "sm2.json"
    p.write_text("invalid", encoding="utf-8")
    with patch("sm2.SM2_PATH", p):
        assert carregar() == []


def test_salvar_e_carregar(tmp_path):
    p = tmp_path / "sm2.json"
    dados = [{"questao_idx": 0, "disciplina": "Teste", "pergunta": "Q?", "ease": 2.5, "interval_dias": 1, "rep": 1, "proxima_revisao": "2026-01-01", "ultima_qualidade": 4, "revisoes": 1}]
    with patch("sm2.SM2_PATH", p):
        salvar(dados)
        assert p.exists()
        loaded = carregar()
        assert len(loaded) == 1
        assert loaded[0]["disciplina"] == "Teste"


def test_registrar_revisao_novo_cartao(tmp_path):
    p = tmp_path / "sm2.json"
    with patch("sm2.SM2_PATH", p):
        cartoes = registrar_revisao(0, "Matemática", "Quanto é 2+2?", 5)
        assert len(cartoes) == 1
        assert cartoes[0]["questao_idx"] == 0
        assert cartoes[0]["rep"] == 1
        assert cartoes[0]["interval_dias"] == 1


def test_registrar_revisao_existente(tmp_path):
    p = tmp_path / "sm2.json"
    with patch("sm2.SM2_PATH", p):
        cartoes = registrar_revisao(0, "Matemática", "Quanto é 2+2?", 5)
        cartoes = registrar_revisao(0, "Matemática", "Quanto é 2+2?", 4)
        assert len(cartoes) == 1
        assert cartoes[0]["rep"] == 2
        assert cartoes[0]["interval_dias"] == 6


def test_registrar_revisao_qualidade_baixa_reseta(tmp_path):
    p = tmp_path / "sm2.json"
    with patch("sm2.SM2_PATH", p):
        cartoes = registrar_revisao(0, "Teste", "P?", 5)  # rep=1
        cartoes = registrar_revisao(0, "Teste", "P?", 1)  # rep deve resetar
        assert cartoes[0]["rep"] == 0
        assert cartoes[0]["interval_dias"] == 1


def test_revisoes_devidas(tmp_path):
    p = tmp_path / "sm2.json"
    with patch("sm2.SM2_PATH", p):
        hoje = date.today().isoformat()
        salvar([
            {"questao_idx": 0, "disciplina": "A", "pergunta": "P1", "ease": 2.5, "interval_dias": 0, "rep": 0, "proxima_revisao": hoje, "ultima_qualidade": 0, "revisoes": 0},
            {"questao_idx": 1, "disciplina": "A", "pergunta": "P2", "ease": 2.5, "interval_dias": 0, "rep": 0, "proxima_revisao": "2099-01-01", "ultima_qualidade": 0, "revisoes": 0},
        ])
        devidos = revisoes_devidas()
        assert len(devidos) == 1
        assert devidos[0]["questao_idx"] == 0


def test_revisoes_devidas_sem_cartoes(tmp_path):
    with patch("sm2.SM2_PATH", tmp_path / "empty.json"):
        assert revisoes_devidas() == []


def test_proximas_revisoes(tmp_path):
    p = tmp_path / "sm2.json"
    with patch("sm2.SM2_PATH", p):
        salvar([
            {"questao_idx": i, "disciplina": "A", "pergunta": f"P{i}", "ease": 2.5, "interval_dias": 0, "rep": 0, "proxima_revisao": f"2026-01-{i+1:02d}", "ultima_qualidade": 0, "revisoes": 0}
            for i in range(5)
        ])
        prox = proximas_revisoes(limite=3)
        assert len(prox) == 3


def test_estatisticas_vazio(tmp_path):
    with patch("sm2.SM2_PATH", tmp_path / "empty.json"):
        stats = estatisticas()
        assert stats["total"] == 0


def test_estatisticas_com_dados(tmp_path):
    p = tmp_path / "sm2.json"
    with patch("sm2.SM2_PATH", p):
        salvar([
            {"questao_idx": 0, "disciplina": "A", "pergunta": "P1", "ease": 2.5, "interval_dias": 0, "rep": 0, "proxima_revisao": date.today().isoformat(), "ultima_qualidade": 4, "revisoes": 5},
        ])
        stats = estatisticas()
        assert stats["total"] == 1
        assert stats["vencidos"] == 1
        assert stats["ease_medio"] == 2.5
        assert stats["revisoes_total"] == 5


def test_inicializar_do_banco_com_dados(tmp_path):
    p = tmp_path / "sm2.json"
    with patch("sm2.SM2_PATH", p):
        salvar([{"questao_idx": 0, "disciplina": "A", "pergunta": "P", "ease": 2.5, "interval_dias": 0, "rep": 0, "proxima_revisao": "", "ultima_qualidade": 0, "revisoes": 0}])
        cartoes = inicializar_do_banco([])
        assert len(cartoes) == 1


def test_inicializar_do_banco_vazio(tmp_path):
    p = tmp_path / "sm2.json"
    with patch("sm2.SM2_PATH", p):
        cartoes = inicializar_do_banco([type("Q", (), {"disciplina": "A", "pergunta": "P"})()])
        assert len(cartoes) == 1
        assert cartoes[0]["disciplina"] == "A"
