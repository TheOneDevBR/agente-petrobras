"""Testes do benchmark de qualidade."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from benchmark_qualidade import (
    Questao, Resultado, BENCHMARK, gerar_markdown,
    executar_benchmark, _tem_gabarito,
)


def test_questoes_definidas():
    assert len(BENCHMARK) >= 5
    for q in BENCHMARK:
        assert q.pergunta
        assert len(q.keywords) >= 2


def test_tem_gabarito_acerta_tudo():
    q = Questao(pergunta="teste", keywords=["legalidade", "impessoalidade", "moralidade"])
    texto = "A legalidade, impessoalidade e moralidade são princípios."
    resultados = _tem_gabarito(texto, [q])
    assert resultados[q.pergunta[:60]] == 1.0


def test_tem_gabarito_acerta_parcial():
    q = Questao(pergunta="teste", keywords=["legalidade", "impessoalidade", "publicidade"])
    texto = "A legalidade é importante."
    resultados = _tem_gabarito(texto, [q])
    score = resultados[q.pergunta[:60]]
    assert 0 < score < 0.5


def test_tem_gabarito_zero():
    q = Questao(pergunta="teste", keywords=["legalidade", "moralidade"])
    texto = "nada a ver"
    resultados = _tem_gabarito(texto, [q])
    assert resultados[q.pergunta[:60]] == 0.0


def test_executar_benchmark_mockado():
    cliente_mock = MagicMock()
    cliente_mock.chat.return_value = (
        "A Lei 13.303/2016 é o estatuto jurídico das empresas públicas "
        "e sociedades de economia mista."
    )
    with patch("benchmark_qualidade.LocalLLM", return_value=cliente_mock):
        resultado = executar_benchmark("mock-model", usar_rag=True)

    assert resultado.config == "mock-model +RAG"
    assert resultado.total_keywords > 0
    assert len(resultado.respostas) == len(BENCHMARK)
    assert resultado.respostas[0]["acertos"] > 0


def test_executar_benchmark_mockado_sem_rag():
    cliente_mock = MagicMock()
    cliente_mock.chat.return_value = "Resposta genérica."
    with patch("benchmark_qualidade.LocalLLM", return_value=cliente_mock):
        resultado = executar_benchmark("mock-model", usar_rag=False)

    assert resultado.config == "mock-model sem RAG"
    assert resultado.tempo >= 0


def test_gerar_markdown_vazio():
    md = gerar_markdown([])
    assert "Benchmark de Qualidade" in md
    assert "## Sumário" in md


def test_gerar_markdown_com_resultados():
    r = Resultado(
        config="teste",
        acertos=10,
        total_keywords=20,
        tempo=30.0,
        chars=500,
        respostas=[{
            "pergunta": "P?",
            "resposta": "R.",
            "tempo": 5.0,
            "keywords": 3,
            "acertos": 2,
            "score": 67,
        }],
    )
    md = gerar_markdown([r])
    assert "teste" in md
    assert "67%" in md
    assert "P?" in md


def test_erro_llm_no_benchmark():
    cliente_mock = MagicMock()
    cliente_mock.chat.side_effect = Exception("LLM caiu")
    with patch("benchmark_qualidade.LocalLLM", return_value=cliente_mock):
        resultado = executar_benchmark("mock-model", usar_rag=True)

    for resp in resultado.respostas:
        assert "ERRO" in resp["resposta"]
