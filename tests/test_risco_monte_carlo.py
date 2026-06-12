"""Testes da simulação Monte Carlo."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from risco_monte_carlo import (
    simular_aprovacao,
    formatar_relatorio,
    simular_e_salvar,
    ResultadoMonteCarlo,
)


def test_simular_com_dados():
    """simular_aprovacao retorna resultados com dados válidos."""
    perfil = {
        "cargo_alvo": "Engenheiro de Petróleo",
        "historico_acerto": {"Português": 65, "Raciocínio Lógico": 55},
    }
    sessoes = [{"disciplina": "Português", "questoes": 20, "acertos": 14}]
    simulados = [{"pct": 58.0, "disciplina": "Legislação"}]

    r = simular_aprovacao(perfil, sessoes, simulados, n_cenarios=1000)
    assert isinstance(r, ResultadoMonteCarlo)
    assert r.n_cenarios == 1000
    assert 0 <= r.prob_aprovacao <= 100
    assert 0 <= r.nota_media <= 100
    assert r.por_disciplina


def test_simular_sem_dados():
    """simular_aprovacao retorna resultado vazio sem dados."""
    r = simular_aprovacao({}, [], [], n_cenarios=100)
    assert r.n_cenarios == 0
    assert r.prob_aprovacao == 0.0


def test_formatar_relatorio():
    """formatar_relatorio retorna string."""
    r = ResultadoMonteCarlo(
        n_cenarios=1000, aprovacoes=600, prob_aprovacao=60.0,
        nota_media=68.0, nota_mediana=67.5, nota_min=45.0, nota_max=92.0,
        nota_corte=65.0, desvio_padrao=8.5,
        intervalo_confianca_90=(55.0, 80.0),
        notas=[50, 60, 70, 80],
        por_disciplina={"Português": {"media": 65.0, "dp": 10.0, "n": 5}},
    )
    rel = formatar_relatorio(r)
    assert "Monte Carlo" in rel
    assert "60.0%" in rel
    assert "68.0" in rel


def test_formatar_relatorio_vazio():
    """formatar_relatorio com dados vazios retorna mensagem."""
    r = ResultadoMonteCarlo(
        n_cenarios=0, aprovacoes=0, prob_aprovacao=0.0,
        nota_media=0.0, nota_mediana=0.0, nota_min=0.0, nota_max=0.0,
        nota_corte=0.0, desvio_padrao=0.0,
        intervalo_confianca_90=(0.0, 0.0),
        notas=[], por_disciplina={},
    )
    rel = formatar_relatorio(r)
    assert "Sem dados" in rel


def test_simular_e_salvar(tmp_path):
    """simular_e_salvar escreve arquivo."""
    caminho = str(tmp_path / "risco.md")
    resultado = simular_e_salvar({}, [], [], caminho, n_cenarios=100)
    assert Path(caminho).exists()
    conteudo = Path(caminho).read_text(encoding="utf-8")
    assert "Sem dados" in conteudo


def test_nota_corte_por_cargo():
    """Nota de corte muda conforme o cargo."""
    r_eng = simular_aprovacao({"cargo_alvo": "engenheiro", "historico_acerto": {"P": 70}},
                              [{"disciplina": "P", "questoes": 5, "acertos": 4}],
                              [], n_cenarios=100)
    r_tec = simular_aprovacao({"cargo_alvo": "tecnico", "historico_acerto": {"P": 70}},
                              [{"disciplina": "P", "questoes": 5, "acertos": 4}],
                              [], n_cenarios=100)
    assert r_eng.nota_corte != r_tec.nota_corte
