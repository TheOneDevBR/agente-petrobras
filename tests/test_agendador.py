"""Testes do módulo agendador."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from agendador import (
    gerar_cronograma,
    formatar_cronograma,
    gerar_e_salvar,
    BlocoEstudo,
    CronogramaSemanal,
)


def test_gerar_cronograma_com_dados():
    """gerar_cronograma retorna cronograma com dados válidos."""
    perfil = {
        "cargo_alvo": "Engenheiro",
        "horas_dia_util": 2,
        "horas_sabado": 4,
        "horas_domingo": 3,
        "fase_atual": "DOMINIO",
        "historico_acerto": {"Português": 50, "Matemática": 40},
    }
    sessoes = [{"disciplina": "Português", "questoes": 20, "acertos": 10}]
    simulados = [{"pct": 55.0, "disciplina": "Português"}]

    c = gerar_cronograma(perfil, sessoes, simulados)
    assert isinstance(c, CronogramaSemanal)
    assert len(c.blocos) > 0
    assert c.semana_inicio
    assert isinstance(c.metas, dict)


def test_gerar_cronograma_sem_dados():
    """gerar_cronograma funciona mesmo sem dados de histórico."""
    c = gerar_cronograma({}, [], [])
    assert isinstance(c, CronogramaSemanal)
    assert isinstance(c.observacoes, list)


def test_formatar_cronograma():
    """formatar_cronograma retorna string Markdown."""
    c = CronogramaSemanal(
        semana_inicio="2026-06-15",
        blocos=[BlocoEstudo(dia="Segunda", horario="19:00", disciplina="Português",
                            tecnica="Questões", duracao_min=50)],
        metas={"Português": 50},
        observacoes=["Teste"],
    )
    md = formatar_cronograma(c)
    assert "Cronograma Semanal" in md
    assert "Segunda" in md
    assert "Português" in md
    assert "Teste" in md


def test_cronograma_com_emergencia():
    """Fase EMERGENCIA adiciona observação específica."""
    perfil = {"fase_atual": "EMERGENCIA"}
    c = gerar_cronograma(perfil, [], [])
    assert any("EMERGÊNCIA" in obs for obs in c.observacoes)


def test_gerar_e_salvar(tmp_path):
    """gerar_e_salvar escreve arquivo Markdown."""
    caminho = str(tmp_path / "cronograma.md")
    resultado = gerar_e_salvar({}, [], [], caminho)
    assert Path(caminho).exists()
    assert resultado == caminho
    conteudo = Path(caminho).read_text(encoding="utf-8")
    assert "Cronograma" in conteudo
