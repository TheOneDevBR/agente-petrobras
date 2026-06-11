"""Testes do módulo de treino/simulado."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from treino import (
    QuestaoMC,
    BANCO_QUESTOES,
    selecionar_questoes,
    carregar_simulados,
    salvar_simulado,
    resumo_para_prompt,
    desempenho_por_disciplina,
    iniciar_simulado,
)


def test_banco_tem_questoes():
    assert len(BANCO_QUESTOES) >= 20
    for q in BANCO_QUESTOES:
        assert q.pergunta
        assert len(q.opcoes) == 5
        assert 0 <= q.correta < len(q.opcoes)
        assert q.explicacao


def test_selecionar_sem_filtro():
    qs = selecionar_questoes(5)
    assert len(qs) == 5
    assert all(isinstance(q, QuestaoMC) for q in qs)


def test_selecionar_com_disciplina():
    qs = selecionar_questoes(10, disciplina="Legislação")
    assert all(q.disciplina == "Legislação" for q in qs)
    assert len(qs) > 0


def test_selecionar_mais_que_disponivel():
    qs = selecionar_questoes(100)
    assert len(qs) <= len(BANCO_QUESTOES)


def test_selecionar_por_tags():
    qs = selecionar_questoes(50, tags=["rl"])
    assert all("rl" in q.tags for q in qs)
    assert len(qs) > 0


def test_selecionar_sem_match():
    qs = selecionar_questoes(5, disciplina="Inexistente")
    assert qs == []


def test_carregar_simulados_sem_arquivo(tmp_path):
    with patch("treino.SIMULADOS_PATH", tmp_path / "inexistente.json"):
        assert carregar_simulados() == []


def test_salvar_e_carregar_simulado(tmp_path):
    sim_path = tmp_path / "simulados.json"
    with patch("treino.SIMULADOS_PATH", sim_path):
        registro = {
            "data": "2026-06-11",
            "questoes": 5,
            "acertos": 3,
            "pct": 60.0,
            "tempo_seg": 120.0,
            "disciplina": "Legislação",
            "respostas": [],
        }
        salvar_simulado(registro)
        salvar_simulado(registro)
        dados = carregar_simulados()
        assert len(dados) == 2
        assert dados[0]["pct"] == 60.0


def test_resumo_para_prompt_vazio(tmp_path):
    sim_path = tmp_path / "simulados.json"
    with patch("treino.SIMULADOS_PATH", sim_path):
        assert resumo_para_prompt() == ""


def test_resumo_para_prompt_com_dados(tmp_path):
    sim_path = tmp_path / "simulados.json"
    with patch("treino.SIMULADOS_PATH", sim_path):
        for pct in [80, 40, 90]:
            salvar_simulado({"data": "2026-06-11", "disciplina": "Teste",
                             "acertos": 4, "questoes": 5, "pct": float(pct),
                             "tempo_seg": 60.0, "respostas": []})
        resumo = resumo_para_prompt(ultimos=3)
        assert "SIMULADOS RECENTES" in resumo
        assert "80" in resumo
        assert "40" in resumo
        assert "90" in resumo


def test_desempenho_por_disciplina(tmp_path):
    sim_path = tmp_path / "simulados.json"
    with patch("treino.SIMULADOS_PATH", sim_path):
        salvar_simulado({"data": "a", "disciplina": "Português",
                         "acertos": 4, "questoes": 5, "pct": 80.0,
                         "tempo_seg": 60.0, "respostas": []})
        salvar_simulado({"data": "b", "disciplina": "Português",
                         "acertos": 2, "questoes": 5, "pct": 40.0,
                         "tempo_seg": 60.0, "respostas": []})
        salvar_simulado({"data": "c", "disciplina": "Legislação",
                         "acertos": 3, "questoes": 5, "pct": 60.0,
                         "tempo_seg": 60.0, "respostas": []})
        disc = desempenho_por_disciplina()
        assert disc.get("Português") == 60.0
        assert disc.get("Legislação") == 60.0


def test_iniciar_simulado_interativo(monkeypatch, capsys):
    import treino as t
    with patch("treino.BANCO_QUESTOES", t.BANCO_QUESTOES[:2]):
        monkeypatch.setattr("builtins.input", lambda _: "0")
        resultado = iniciar_simulado(n_questoes=2, cronometro=0)
        assert resultado["questoes"] == 2
        assert 0 <= resultado["acertos"] <= 2
        assert resultado["tempo_seg"] >= 0
        assert "data" in resultado


def test_iniciar_simulado_sem_questoes():
    resultado = iniciar_simulado(n_questoes=5, disciplina="Inexistente")
    assert "erro" in resultado


def test_iniciar_simulado_todas_certas(monkeypatch):
    import treino as t
    questoes = t.BANCO_QUESTOES[:3]
    answers = iter([str(q.correta) for q in questoes])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    with patch("treino.BANCO_QUESTOES", questoes):
        resultado = iniciar_simulado(n_questoes=3, cronometro=0)
        assert resultado["acertos"] == 3
        assert resultado["pct"] == 100.0
