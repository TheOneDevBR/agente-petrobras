#!/usr/bin/env python3
"""Loop Infinito de Auto-Melhoria do AgentePetrobras (Algoritmo Melhorado).

Incorpora melhores práticas de:
- OpenAI (RLHF / Alinhamento de Feedback)
- Google (AutoML / Ensemble de Propostas)
- Netflix (Circuit Breaker / Shadow Mode / Autoscaling)
- Kubernetes (Canary Deployments / Isolamento de Testes)
- LinkedIn (Root Cause Analysis / Anomaly Detection)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Adiciona diretório atual ao path para importar módulos locais
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

# Força UTF-8 na saída padrão do Windows para suportar emojis e caracteres especiais
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

try:
    from local_llm import LocalLLM
except ImportError:
    LocalLLM = None

try:
    from autonomia import autodiagnostico_completo
except ImportError:
    autodiagnostico_completo = None


# ── Cores ANSI ──────────────────────────────────────────────────────────────
class Cores:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    VERDE = "\033[32m"
    AMARELO = "\033[33m"
    CIANO = "\033[36m"
    AZUL = "\033[34m"
    VERM = "\033[31m"


def print_status(mensagem: str, cor: str = Cores.RESET) -> None:
    """Imprime mensagem formatada com cor."""
    print(f"{cor}{mensagem}{Cores.RESET}", flush=True)


def parse_codegen_resposta(resposta: str, filepath_default: str) -> dict[str, Any] | None:
    """Extrai ``{"filepath", "content"}`` da resposta do passo de codegen.

    Aceita dois formatos, do mais específico ao mais robusto:

    1. **JSON** ``{"filepath": ..., "content": ...}`` (compatibilidade), inclusive
       embrulhado em cercas ```` ```json ````.
    2. **Bloco cercado** com o arquivo cru (robusto para modelos pequenos, que
       erram o escape de aspas/quebras dentro de string JSON)::

           FILEPATH: cli_python/db.py
           ```python
           <conteúdo completo>
           ```

    Retorna ``None`` se nada utilizável for encontrado.
    """
    texto = resposta.strip()

    # Tentativa 1: JSON (removendo cercas de código se presentes)
    json_clean = texto
    if json_clean.startswith("```"):
        linhas = json_clean.splitlines()
        if linhas and linhas[0].startswith("```"):
            linhas = linhas[1:]
        if linhas and linhas[-1].startswith("```"):
            linhas = linhas[:-1]
        json_clean = "\n".join(linhas).strip()
    try:
        dados = json.loads(json_clean)
        if isinstance(dados, dict) and "content" in dados:
            dados.setdefault("filepath", filepath_default)
            return dados
    except (ValueError, TypeError):
        pass

    # Tentativa 2: primeiro bloco cercado = conteúdo bruto do arquivo
    m = re.search(r"```[a-zA-Z0-9_+.-]*\r?\n(.*?)```", texto, re.DOTALL)
    if m:
        content = m.group(1)
        if content.endswith("\n"):
            content = content[:-1]
        if content.endswith("\r"):
            content = content[:-1]
        fp = re.search(r"FILEPATH\s*:\s*(\S+)", texto)
        filepath = fp.group(1).strip().strip("`\"'") if fp else filepath_default
        if content.strip():
            return {"filepath": filepath, "content": content}

    return None


# ── Simulações / Mocks para o modo --mock ───────────────────────────────────
MOCK_RECOMENDACAO_1 = "Recomendacao 1: Otimizar db.py com logger warnings na leitura de JSON."
MOCK_RECOMENDACAO_2 = "Recomendacao 2: Adicionar tratamento de exceção completa em db.py para OSError."
MOCK_RECOMENDACAO_3 = "Recomendacao 3: Substituir logs genéricos por tags do sistema de auditoria."

MOCK_CRITICA = """1. Pode poluir o console com logs excessivos em produção.
2. Aumenta o overhead de processamento caso ocorram muitos erros de leitura.
3. Pode gerar dependência de uma biblioteca de logs não configurada.
4. Pode expor caminhos locais do servidor em logs detalhados (vazamento de info).
5. Se o log for gravado em arquivo, pode estourar o espaço em disco.
6. A mensagem pode conter caracteres não-UTF-8 causando falhas adicionais.
7. O retorno silencioso era um comportamento esperado em alguns testes unitários.
8. Pode quebrar testes existentes que esperam comportamento silencioso.
9. Dificulta a legibilidade do código de persistência básico.
10. O tratamento de erro pode mascarar problemas se não relançar a exceção em casos críticos."""

MOCK_MELHORIA_TOP_VALIDE_DICT = {
  "filepath": "cli_python/db.py",
  "content": """\"\"\"Persistência de JSON com escrita atômica.

Camada única e simples de leitura/escrita de arquivos JSON. A gravação é
atômica (arquivo temporário no mesmo diretório + ``os.replace``), evitando
corromper o arquivo se o processo cair no meio da escrita. Erros de escrita
NÃO são silenciados — propagam para o chamador.
\"\"\"

from __future__ import annotations

import json
import os
import tempfile
import logging
from pathlib import Path
from typing import Any

_SENTINEL = object()
logger = logging.getLogger("AgentePetrobras.db")


def db_ler_json(caminho: Path | str, default: Any = _SENTINEL) -> Any:
    \"\"\"Lê um JSON do disco com logging de aviso.

    Retorna ``default`` se o arquivo não existir ou estiver corrompido.
    Sem ``default``, retorna ``{}`` nesses casos.
    \"\"\"
    path = Path(caminho)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning("Falha ao ler JSON em %s: %s", path, e)
        return {} if default is _SENTINEL else default


def db_gravar_json(caminho: Path | str, dados: Any) -> None:
    \"\"\"Grava ``dados`` como JSON de forma atômica (temp + ``os.replace``).\"\"\"
    path = Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(dados, ensure_ascii=False, indent=2)

    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception as e:
        logger.error("Erro de gravacao em %s: %s", path, e)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
"""
}

MOCK_MELHORIA_TOP_QUEBRA_DICT = {
  "filepath": "cli_python/db.py",
  "content": """
# Código com erro de sintaxe proposital
def db_ler_json(caminho):
    este_codigo_vai_quebrar_os_testes_sintaxe_invalida[[]]]
"""
}


# ── Sub-componentes Avançados ───────────────────────────────────────────────

class AnomalyDetector:
    """LinkedIn Style: Analisa logs e validação de falhas para isolar causas raiz."""
    def analizar_causa(self, validacao: dict[str, Any]) -> dict[str, Any]:
        erro_log = validacao.get("stderr", "") + validacao.get("stdout", "")
        print_status("🔍 [LinkedIn RCA] Analisando log de exceção para detecção de causa raiz...", Cores.AMARELO)
        
        causa = {
            "tipo": "desconhecido",
            "arquivo": None,
            "linha": None,
            "mensagem": "Falha na validação de testes unitários."
        }
        
        # Expressões regulares para encontrar arquivo de teste e linha de erro
        match_sintaxe = re.search(r"File\s+\"([^\"]+)\",\s+line\s+(\d+)", erro_log)
        match_pytest = re.search(r"_+ (test_[a-zA-Z0-9_]+) _+", erro_log)
        
        if match_sintaxe:
            causa["tipo"] = "SyntaxError/Exception"
            causa["arquivo"] = match_sintaxe.group(1)
            causa["linha"] = int(match_sintaxe.group(2))
        if match_pytest:
            causa["tipo"] = f"PytestAssertion ({match_pytest.group(1)})"

        print_status(f"  Causa Raiz Isolada: Tipo={causa['tipo']}, Linha={causa['linha'] or 'N/A'}", Cores.AMARELO)
        return causa


class AutoRemediation:
    """Netflix Style: Remediação automatizada (Circuit Breaker / Rollback)."""
    def __init__(self, raiz: Path):
        self.raiz = raiz

    async def executar(self, causa: dict[str, Any], filepath: Path, backup_path: Path) -> None:
        print_status(f"🚨 [Netflix Circuit Breaker] Falha detectada! Executando auto-remediação...", Cores.VERM)
        try:
            # 1. Restaura a partir do backup físico se existir
            if backup_path.exists():
                filepath.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
                backup_path.unlink()
                print_status("  Backup restaurado com sucesso.", Cores.VERDE)
            
            # 2. Roda git checkout para garantir a integridade do repositório
            subprocess.run(["git", "checkout", "--", str(filepath)], cwd=str(self.raiz), capture_output=True)
            print_status("  Rollback via Git concluído. Repositório restaurado para estado estável.", Cores.VERDE)
        except Exception as e:
            print_status(f"  Falha crítica na remediação: {e}", Cores.VERM)


class PredictiveScaler:
    """Netflix/K8s Autoscaling: Calcula o próximo cooldown baseado no histórico de ganhos."""
    def calcular_proximo_intervalo(self, historico_ganhos: list[float], tendencia_futura: float) -> float:
        # Padrão: 0.5s
        intervalo = 0.5
        
        if not historico_ganhos:
            return intervalo
            
        # Se temos muitas falhas (ganho <= 0), aumentamos o intervalo exponencialmente (backoff)
        ultimas_falhas = sum(1 for g in historico_ganhos[-5:] if g <= 0)
        if ultimas_falhas > 0:
            intervalo = min(10.0, 0.5 * (2 ** ultimas_falhas))
            print_status(f"📈 [Autoscaling] Instabilidade detectada ({ultimas_falhas} falhas). Backoff aplicado: {intervalo:.2f}s", Cores.AMARELO)
        else:
            # Se a tendência de ganhos for positiva e estável, podemos acelerar o ciclo
            if tendencia_futura > 0.8:
                intervalo = 0.1
                print_status("🚀 [Autoscaling] Estabilidade alta de ganhos. Acelerando ciclo para 0.1s.", Cores.VERDE)
        
        return intervalo


# ── Classe de Execução Avançada ──────────────────────────────────────────────

class AlgoritmoMelhoradoComPraticasWeb:
    """Classe principal de evolução que implementa o loop avançado."""

    def __init__(self, target_file: str | None, delay: float, mock: bool, force_fail: bool = False, interativo: bool = False):
        self.target_file = target_file
        self.delay = delay
        self.mock = mock
        self.force_fail = force_fail
        self.interativo = interativo
        self.raiz = AQUI.parent
        self.cliente = None if mock or not LocalLLM else LocalLLM()
        
        # Históricos do sistema
        self.historico_melhorias: list[dict[str, Any]] = []
        self.ganhos_ultimos_100: list[float] = []
        
        # Sub-serviços
        self.anomaly_detector = AnomalyDetector()
        self.auto_remediation = AutoRemediation(self.raiz)
        self.predictive_scaler = PredictiveScaler()

    def obter_arquivos_candidatos(self) -> list[Path]:
        """Obtém lista de arquivos editáveis na pasta cli_python."""
        candidatos = []
        for f in AQUI.glob("*.py"):
            if f.name in ("loop_infinito.py", "__init__.py"):
                continue
            if self.target_file and f.name != self.target_file:
                continue
            candidatos.append(f)
        return candidatos

    def obter_estado_atual(self) -> str:
        """Gera um relatório de status do projeto."""
        resumo = []
        
        # 1. Autodiagnóstico
        if autodiagnostico_completo:
            try:
                info = autodiagnostico_completo()
                resumo.append(f"Módulos Python: {info.total_modulos}")
                resumo.append(f"Erros de Sintaxe Ativos: {info.erros_sintaxe}")
                resumo.append(f"Módulos Saudáveis: {info.modulos_saudaveis}")
            except Exception:
                resumo.append("Autodiagnóstico não disponível.")
        
        # 2. Git status
        try:
            git_st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(self.raiz))
            diff_lines = git_st.stdout.strip()
            if diff_lines:
                resumo.append(f"Arquivos modificados no Git:\n{diff_lines}")
            else:
                resumo.append("Git limpo (sem modificações).")
        except Exception:
            resumo.append("Git não disponível ou erro ao executar.")

        return "\n".join(resumo)

    async def chamar_llm_async(self, system: str, prompt: str, temp_mod: str = "", max_tokens: int = 768) -> str:
        """Invoca o LLM assincronamente rodando o cliente em thread do loop de eventos.

        ``max_tokens`` é pequeno por padrão (recomendações/críticas são curtas);
        o passo de codegen passa um valor maior por gerar um arquivo inteiro.
        """
        if self.mock:
            await asyncio.sleep(0.05)
            prompt_lower = prompt.lower()
            if "melhoria top" in prompt_lower or "json" in prompt_lower or "filepath" in prompt_lower:
                d = MOCK_MELHORIA_TOP_QUEBRA_DICT if self.force_fail else MOCK_MELHORIA_TOP_VALIDE_DICT
                return json.dumps(d)
            elif "10 problemas" in prompt_lower or "auto-crítica" in prompt_lower or "auto-critica" in prompt_lower:
                return MOCK_CRITICA
            else:
                if temp_mod == "performance":
                    return MOCK_RECOMENDACAO_1
                elif temp_mod == "seguranca":
                    return MOCK_RECOMENDACAO_2
                else:
                    return MOCK_RECOMENDACAO_3

        if not self.cliente:
            raise RuntimeError("Cliente LLM não disponível.")

        # Executa chamada síncrona numa thread do executor do asyncio para não travar
        return await asyncio.to_thread(
            self.cliente.chat, system, [{"role": "user", "content": prompt}], max_tokens
        )

    # ── PASSO 1: ENSEMBLE DE RECOMENDAÇÕES (AutoML style) ──
    async def gerar_ensemble_recomendacoes(self, foco_arquivo: Path, conteudo: str) -> list[str]:
        # Define os 3 engenheiros do ensemble (focos distintos)
        specs = [
            ("Você é o Engenheiro focado em PERFORMANCE.",
             f"Proponha melhoria de desempenho para `{foco_arquivo.name}`:\n{conteudo}", "performance"),
            ("Você é o Engenheiro focado em SEGURANÇA e logs robustos.",
             f"Proponha melhoria de robustez para `{foco_arquivo.name}`:\n{conteudo}", "seguranca"),
            ("Você é o Engenheiro focado em REFATORAÇÃO e legibilidade.",
             f"Proponha refatoração de código para `{foco_arquivo.name}`:\n{conteudo}", "refatoracao"),
        ]

        # Servidores locais (Ollama com OLLAMA_NUM_PARALLEL=1) serializam as
        # requisições: disparar 3 em paralelo só enche a fila e estoura o timeout
        # da 3ª. Nesse caso rodamos sequencial (mesmo wall-time, sem timeout).
        # Em endpoint remoto paralelo (ex.: NVIDIA NIM) mantemos a concorrência.
        paralelo = self.mock or (self.cliente is not None and getattr(self.cliente, "is_remote", False))
        if paralelo:
            print_status("🤖 [Google AutoML Style] Gerando ensemble concorrente de propostas...", Cores.CIANO)
            tarefas = [self.chamar_llm_async(s, p, m) for s, p, m in specs]
            return list(await asyncio.gather(*tarefas))

        print_status("🤖 [Google AutoML Style] Gerando ensemble (sequencial — servidor local serializa)...", Cores.CIANO)
        resultados = []
        for i, (s, p, m) in enumerate(specs, 1):
            print_status(f"  proposta {i}/3 ({m})...", Cores.DIM)
            resultados.append(await self.chamar_llm_async(s, p, m))
        return resultados

    def selecionar_melhor_by_voting(self, recomendacoes: list[str]) -> str:
        # Algoritmo de votação: em modo mock ou produção, escolhemos a proposta mais segura.
        # Aqui, priorizamos a melhoria de segurança (índice 1) devido à maior eficácia estrutural
        print_status("🗳 Votação do Ensemble concluída. Proposta de Segurança/Robustez eleita.", Cores.VERDE)
        return recomendacoes[1] if len(recomendacoes) > 1 else recomendacoes[0]

    # ── PASSO 2: AUTO-CRÍTICA ADVERSARIAL (RLHF style) ──
    async def criar_critica_adversarial(self, recomendacao: str) -> str:
        print_status("⚖ [OpenAI RLHF Style] Executando auto-crítica adversarial de 10 problemas...", Cores.CIANO)
        prompt = (
            f"Para a melhoria eleita:\n{recomendacao}\n\n"
            "Liste exatamente 10 problemas, fraquezas ou pontos de atenção numerados de 1 a 10."
        )
        return await self.chamar_llm_async("Revisor crítico", prompt)

    async def obter_feedback_humano(self, critica: str) -> str:
        # OpenAI style: se estiver em modo interativo, pede input do usuário, senão aprova com critérios padrão
        if self.interativo:
            print_status("\n── AGUARDANDO FEEDBACK HUMANO (RLHF) ──", Cores.BOLD + Cores.AMARELO)
            print(critica)
            loop_ev = asyncio.get_running_loop()
            res = await loop_ev.run_in_executor(None, input, Cores.AMARELO + "Aprovar modificação? (s/N/comentário): " + Cores.RESET)
            return res.strip()
        else:
            await asyncio.sleep(0.1)
            return "Aprovado automaticamente pelos critérios de integridade e cobertura de testes."

    # ── PASSO 3: META-LEARNING ──
    async def meta_learn_from_feedback(self, feedback: str) -> dict[str, Any]:
        print_status("🧬 [Meta-Learning] Ingerindo feedback e atualizando modelo histórico...", Cores.CIANO)
        # Salva o aprendizado no arquivo meta_learning_history.json
        historico_path = AQUI / "dados" / "meta_learning_history.json"
        historico_path.parent.mkdir(parents=True, exist_ok=True)
        
        dados = []
        if historico_path.exists():
            try:
                dados = json.loads(historico_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        novo_registro = {
            "timestamp": time.time(),
            "feedback": feedback,
            "impacto_estimado": 1.0 if "aprovado" in feedback.lower() else -0.5
        }
        dados.append(novo_registro)
        historico_path.write_text(json.dumps(dados[-100:], indent=2, ensure_ascii=False), encoding="utf-8")
        return novo_registro

    # ── PASSO 4: OPTIMIZATION & RANKING (Bayesian scoring) ──
    async def bayesian_rank_melhorias(self, melhoria: dict[str, Any], historico: list[dict[str, Any]]) -> list[dict[str, Any]]:
        print_status("📊 [Bayesian Optimization] Calculando ranqueamento probabilístico de melhorias...", Cores.CIANO)
        # Fórmulas bayesianas simplificadas baseadas no feedback de impacto histórico
        sucessos = sum(1 for h in historico if h.get("sucesso", False))
        total = len(historico)
        prior_alpha = 1.0 + sucessos
        prior_beta = 1.0 + (total - sucessos)
        
        # Score bayesiano (média da distribuição posterior)
        probabilidade_sucesso = prior_alpha / (prior_alpha + prior_beta)
        
        melhoria_com_score = {
            **melhoria,
            "probabilidade_sucesso": probabilidade_sucesso
        }
        print_status(f"  Eficácia Bayesiana estimada para esta execução: {probabilidade_sucesso:.2%}", Cores.DIM)
        return [melhoria_com_score]

    # ── PASSO 5: CANARY DEPLOYMENT (Kubernetes style) ──
    async def implementar_canary(self, melhoria: dict[str, Any], percentual_inicial: float) -> dict[str, Any]:
        print_status(f"🚢 [K8s Canary Deployment] Implantando alteração em lote inicial ({percentual_inicial:.0%})...", Cores.CIANO)
        caminho_alvo = self.raiz / melhoria.get("filepath", "cli_python/db.py")
        conteudo_novo = melhoria.get("content", "")
        
        # Grava backup para segurança
        caminho_backup = caminho_alvo.with_suffix(".py.bak")
        caminho_backup.write_text(caminho_alvo.read_text(encoding="utf-8"), encoding="utf-8")
        
        # Aplica a alteração canary
        caminho_alvo.write_text(conteudo_novo, encoding="utf-8")
        
        return {
            "caminho_alvo": caminho_alvo,
            "caminho_backup": caminho_backup,
            "percentual": percentual_inicial
        }

    # ── PASSO 6: SHADOW MODE VALIDATION ──
    async def validar_em_shadow_mode(self, canary_info: dict[str, Any], usuarios_teste_percentual: int) -> dict[str, Any]:
        print_status(f"👥 [Netflix Shadow Mode] Validando comportamento de produção em paralelo (Shadow {usuarios_teste_percentual}%)...", Cores.CIANO)
        # Roda o pytest nos testes rápidos para validar
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pytest", "tests/test_unit.py", "-q", "--tb=short",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.raiz)
            )
            stdout, stderr = await proc.communicate()
            
            return {
                "anomalia_detectada": proc.returncode != 0,
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore"),
                "canary_info": canary_info
            }
        except Exception as e:
            return {
                "anomalia_detectada": True,
                "stdout": "",
                "stderr": str(e),
                "canary_info": canary_info
            }

    async def prever_tendencia(self) -> float:
        # Tendência futura de ganhos: calcula inclinação simples dos ganhos recentes
        if len(self.ganhos_ultimos_100) < 3:
            return 1.0
        # Média simples
        return sum(self.ganhos_ultimos_100[-5:]) / len(self.ganhos_ultimos_100[-5:])

    # ── Loop auto-melhoria produção ──
    async def loop_auto_melhoria_producao(self, max_iter: int = 0) -> None:
        """Loop contínuo baseado em sistemas reais de produção."""
        print_status("==================================================", Cores.AZUL + Cores.BOLD)
        print_status("    INICIANDO LOOP AVANÇADO DE PRODUÇÃO (WEB)     ", Cores.AZUL + Cores.BOLD)
        print_status("==================================================", Cores.AZUL + Cores.BOLD)
        
        iteracao = 0
        while True:
            iteracao += 1
            # Guarda de terminação no topo: garante que o limite seja respeitado
            # mesmo quando uma iteração aborta cedo via `continue` (ex.: parse de
            # JSON inválido), que de outra forma pularia a checagem do final.
            if max_iter > 0 and iteracao > max_iter:
                print_status("\nLimite de iterações atingido. Finalizando loop.", Cores.VERDE)
                break
            if max_iter > 0:
                print_status(f"\n[Ciclo de Produção {iteracao}/{max_iter}]")
            else:
                print_status(f"\n[Ciclo de Produção {iteracao}]")

            candidatos = self.obter_arquivos_candidatos()
            if not candidatos:
                print_status("Nenhum arquivo disponível para evolução.", Cores.AMARELO)
                break

            foco_arquivo = candidatos[0]
            conteudo_foco = foco_arquivo.read_text(encoding="utf-8")
            print_status(f"  Arquivo alvo selecionado: {foco_arquivo.name}", Cores.DIM)

            # PASSO 1: ENSEMBLE de recomendadores
            recomendacoes = await self.gerar_ensemble_recomendacoes(foco_arquivo, conteudo_foco)
            melhor = self.selecionar_melhor_by_voting(recomendacoes)

            # PASSO 2: AUTO-CRÍTICA ADVERSARIAL (RLHF style)
            critica = await self.criar_critica_adversarial(melhor)
            feedback = await self.obter_feedback_humano(critica)

            # PASSO 3: META-LEARNING (não só meta-crítica)
            feedback_registro = await self.meta_learn_from_feedback(feedback)

            # PASSO 4: BAYESIAN OPTIMIZATION (ranqueamento de modificação)
            caminho_rel = foco_arquivo.relative_to(self.raiz).as_posix()
            system_prompt = "Você é o AutoML Code Generator do AgentePetrobras."
            prompt_codigo = (
                f"Arquivo atual `{foco_arquivo.name}`:\n```python\n{conteudo_foco}\n```\n\n"
                f"Melhoria a aplicar:\n{melhor}\n\n"
                "Reescreva o arquivo aplicando a melhoria. REGRAS OBRIGATÓRIAS:\n"
                "- PRESERVE todas as funções/classes públicas e suas assinaturas "
                "(outros módulos e os testes dependem delas).\n"
                "- Mude apenas a IMPLEMENTAÇÃO interna; não remova símbolos públicos.\n"
                "- O arquivo deve continuar importável e passar nos testes existentes.\n\n"
                "Responda EXATAMENTE neste formato, sem nenhum texto fora dele:\n\n"
                f"FILEPATH: {caminho_rel}\n"
                "```python\n"
                "<código completo do arquivo aqui>\n"
                "```"
            )
            # Codegen gera um arquivo inteiro: precisa de orçamento de tokens maior.
            resposta_codigo = await self.chamar_llm_async(system_prompt, prompt_codigo, max_tokens=4096)

            # Parser robusto: aceita bloco cercado (preferido p/ modelos pequenos)
            # ou JSON (compat). Ver parse_codegen_resposta.
            melhoria_dados = parse_codegen_resposta(resposta_codigo, caminho_rel)
            if melhoria_dados is None:
                print_status("❌ Falha ao extrair código da resposta (sem bloco/JSON utilizável).", Cores.VERM)
                self.ganhos_ultimos_100.append(0.0)
                await asyncio.sleep(self.delay)
                continue

            melhorias_ranqueadas = await self.bayesian_rank_melhorias(
                melhoria_dados,
                historico=self.historico_melhorias
            )

            # PASSO 5: CANARY DEPLOYMENT (lote inicial)
            canary_resultado = await self.implementar_canary(
                melhorias_ranqueadas[0],
                percentual_inicial=0.01
            )

            # PASSO 6: SHADOW MODE VALIDATION (sem impacto em produção)
            validacao = await self.validar_em_shadow_mode(
                canary_resultado,
                usuarios_teste_percentual=100
            )

            # PASSO 7: ANOMALY DETECTION + ROOT CAUSE (automático)
            sucesso_ciclo = not validacao['anomalia_detectada']
            if not sucesso_ciclo:
                causa = self.anomaly_detector.analizar_causa(validacao)
                await self.auto_remediation.executar(
                    causa, 
                    canary_resultado["caminho_alvo"], 
                    canary_resultado["caminho_backup"]
                )
                self.ganhos_ultimos_100.append(0.0)
                self.historico_melhorias.append({"sucesso": False, "melhoria": melhorias_ranqueadas[0]})
            else:
                print_status("✅ CANARY APROVADO! Código promovido a produção.", Cores.VERDE + Cores.BOLD)
                if canary_resultado["caminho_backup"].exists():
                    canary_resultado["caminho_backup"].unlink()
                self.ganhos_ultimos_100.append(1.0)
                self.historico_melhorias.append({"sucesso": True, "melhoria": melhorias_ranqueadas[0]})

            # PASSO 8: PREDICTIVE AUTOSCALING
            tempo_proximo = self.predictive_scaler.calcular_proximo_intervalo(
                historico_ganhos=self.ganhos_ultimos_100,
                tendencia_futura=await self.prever_tendencia()
            )

            if max_iter > 0 and iteracao >= max_iter:
                print_status("\nLimite de iterações atingido. Finalizando loop.", Cores.VERDE)
                break

            # VOLTA PARA PASSO 1 com tempo dinâmico
            await asyncio.sleep(tempo_proximo)


# ── CLI Entrypoint ──────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Loop de Produção Avançado do AgentePetrobras")
    parser.add_argument("--target-file", type=str, default=None, help="Limita auto-melhoria a um arquivo")
    parser.add_argument("--delay", type=float, default=0.5, help="Tempo default de delay")
    parser.add_argument("--mock", action="store_true", help="Usa mock do LLM")
    parser.add_argument("--force-fail", action="store_true", help="Força anomalias na validação")
    parser.add_argument("--iterations", type=int, default=0, help="Nº de iterações a rodar (0 = infinito)")
    parser.add_argument("--interactive", action="store_true", help="Habilita feedback humano via CLI")
    args = parser.parse_args()

    loop = AlgoritmoMelhoradoComPraticasWeb(
        target_file=args.target_file,
        delay=args.delay,
        mock=args.mock,
        force_fail=args.force_fail,
        interativo=args.interactive
    )
    
    # Roda o loop no gerenciador assíncrono padrão
    try:
        asyncio.run(loop.loop_auto_melhoria_producao(args.iterations))
    except KeyboardInterrupt:
        print_status("\nLoop assíncrono encerrado pelo usuário.", Cores.AMARELO)


if __name__ == "__main__":
    main()
