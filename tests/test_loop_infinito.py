"""Testes unitários para o loop de auto-melhoria assíncrono (loop_infinito.py)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Adiciona o diretório cli_python ao path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cli_python"))

from loop_infinito import AlgoritmoMelhoradoComPraticasWeb


@pytest.fixture
def temp_repo(tmp_path):
    """Cria arquivos temporários simulando a pasta cli_python."""
    cli_dir = tmp_path / "cli_python"
    cli_dir.mkdir()
    
    # Cria arquivos simulados
    db_file = cli_dir / "db.py"
    db_file.write_text("def db_ler_json():\n    return {}\n", encoding="utf-8")
    
    other_file = cli_dir / "outro.py"
    other_file.write_text("def func():\n    pass\n", encoding="utf-8")
    
    # Cria subpasta tests
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_unit.py"
    test_file.write_text("def test_dummy():\n    assert True\n", encoding="utf-8")
    
    return tmp_path


def test_obter_arquivos_candidatos(temp_repo):
    """Testa que obter_arquivos_candidatos encontra arquivos candidatos corretamente."""
    with (
        patch("loop_infinito.AQUI", temp_repo / "cli_python"),
        patch("loop_infinito.Path.glob") as mock_glob
    ):
        mock_glob.return_value = [
            temp_repo / "cli_python" / "db.py",
            temp_repo / "cli_python" / "outro.py",
            temp_repo / "cli_python" / "loop_infinito.py"  # Deve ser ignorado
        ]
        
        loop = AlgoritmoMelhoradoComPraticasWeb(target_file=None, delay=0.1, mock=True)
        candidatos = loop.obter_arquivos_candidatos()
        
        nomes = [c.name for c in candidatos]
        assert "db.py" in nomes
        assert "outro.py" in nomes
        assert "loop_infinito.py" not in nomes


def test_obter_estado_atual(temp_repo):
    """Testa se obter_estado_atual roda sem exceções."""
    loop = AlgoritmoMelhoradoComPraticasWeb(target_file=None, delay=0.1, mock=True)
    loop.raiz = temp_repo
    
    with (
        patch("subprocess.run") as mock_run,
        patch("loop_infinito.autodiagnostico_completo") as mock_diag
    ):
        mock_run.return_value = MagicMock(stdout="M db.py\n")
        diag_info = MagicMock(total_modulos=10, erros_sintaxe=0, modulos_saudaveis=10)
        mock_diag.return_value = diag_info
        
        estado = loop.obter_estado_atual()
        assert "M db.py" in estado
        assert "Módulos Python: 10" in estado


def test_ensemble_e_votacao(temp_repo):
    """Testa que o ensemble e votação escolhem a melhor proposta."""
    db_file = temp_repo / "cli_python" / "db.py"
    loop = AlgoritmoMelhoradoComPraticasWeb(target_file="db.py", delay=0.1, mock=True)
    loop.raiz = temp_repo

    recomendacoes = asyncio.run(loop.gerar_ensemble_recomendacoes(db_file, "conteudo"))
    assert len(recomendacoes) == 3
    
    melhor = loop.selecionar_melhor_by_voting(recomendacoes)
    assert melhor == recomendacoes[1]


def test_autoscale_predictive(temp_repo):
    """Testa que o predictive autoscaler adapta o delay baseado em estabilidade e falhas."""
    loop = AlgoritmoMelhoradoComPraticasWeb(target_file=None, delay=0.1, mock=True)
    
    # Caso 1: Estabilidade perfeita
    tempo_1 = loop.predictive_scaler.calcular_proximo_intervalo([1.0, 1.0, 1.0], 0.9)
    assert tempo_1 == 0.1
    
    # Caso 2: Falha (backoff exponencial)
    tempo_2 = loop.predictive_scaler.calcular_proximo_intervalo([1.0, 0.0], 0.0)
    assert tempo_2 == 1.0  # 0.5 * (2^1)


def test_anomaly_detection_e_rca(temp_repo):
    """Testa isolamento de causa raiz pelo Anomaly Detector."""
    loop = AlgoritmoMelhoradoComPraticasWeb(target_file=None, delay=0.1, mock=True)
    
    # Simula erro de sintaxe
    log_erro = 'File "cli_python/db.py", line 42\nSyntaxError: invalid syntax'
    causa = loop.anomaly_detector.analizar_causa({"stdout": log_erro, "stderr": ""})
    
    assert causa["tipo"] == "SyntaxError/Exception"
    assert "db.py" in causa["arquivo"]
    assert causa["linha"] == 42


def test_executar_passo_canary_e_shadow_sucesso(temp_repo):
    """Testa o ciclo avançado de sucesso com Canary e Shadow Mode."""
    db_file = temp_repo / "cli_python" / "db.py"
    db_file.write_text("def db_ler_json():\n    return {}\n", encoding="utf-8")
    
    loop = AlgoritmoMelhoradoComPraticasWeb(target_file="db.py", delay=0.01, mock=True, force_fail=False)
    loop.raiz = temp_repo
    
    with (
        patch("loop_infinito.AQUI", temp_repo / "cli_python"),
        patch("loop_infinito.Path.glob", return_value=[db_file]),
        patch("asyncio.create_subprocess_exec") as mock_exec
    ):
        # Simula processo do pytest com retorno 0 (sucesso)
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"...", b""))
        mock_proc.returncode = 0
        mock_exec.return_value = mock_proc
        
        asyncio.run(loop.loop_auto_melhoria_producao(max_iter=1))
        
        conteudo = db_file.read_text(encoding="utf-8")
        assert "logger = logging.getLogger" in conteudo


def test_executar_passo_canary_falha_circuit_breaker(temp_repo):
    """Testa que falhas no Canary ativam o Circuit Breaker (Auto-remediação)."""
    db_file = temp_repo / "cli_python" / "db.py"
    original_content = "def db_ler_json():\n    return {}\n"
    db_file.write_text(original_content, encoding="utf-8")
    
    loop = AlgoritmoMelhoradoComPraticasWeb(target_file="db.py", delay=0.01, mock=True, force_fail=True)
    loop.raiz = temp_repo
    
    with (
        patch("loop_infinito.AQUI", temp_repo / "cli_python"),
        patch("loop_infinito.Path.glob", return_value=[db_file]),
        patch("asyncio.create_subprocess_exec") as mock_exec
    ):
        # Simula processo do pytest com retorno 1 (falha de testes)
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(return_value=(b"Syntax Error!", b""))
        mock_proc.returncode = 1
        mock_exec.return_value = mock_proc
        
        asyncio.run(loop.loop_auto_melhoria_producao(max_iter=1))
        
        # O arquivo db.py deve ter sido revertido para o original pela remediação
        conteudo = db_file.read_text(encoding="utf-8")
        assert conteudo == original_content
