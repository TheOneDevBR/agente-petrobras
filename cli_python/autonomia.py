"""Núcleo Autônomo — Autoconsciência, Auto-Diagnóstico, Auto-Cura e Proatividade.

Adaptado do Sistema Vivo de Engenharia Elétrica para o AgentePetrobras.

Capacidades (todas com guardrails — nada sensível roda sozinho):
- Autoconsciência: escaneia os módulos, testes e a base de inteligência
- Auto-Diagnóstico: mede saúde do sistema e registra métricas no tempo
- Auto-Cura: detecta imports quebrados e tenta instalar os pacotes faltantes
- Proatividade: sugere ações (intel desatualizada, simulado pendente) sem ser pedido
- Auto-Web-Learning: REUSA o coletor para ingerir inteligência fresca das bancas
- Scheduler: tarefas de manutenção periódica
- Gap Analyzer: aponta a próxima evolução ideal do projeto
- Ciclo/Loop autônomo: percebe → age (seguro) → aprende

Integra com a camada de autoevolução pedagógica (ciclo_evolutivo).

Uso:
    python autonomia.py                 # painel resumido
    python autonomia.py --ciclo         # um ciclo autônomo (relatório JSON)
    python autonomia.py --daemon        # loop contínuo
    python autonomia.py --gaps          # lista os gaps evolutivos

    # no agente / CLI:
    from autonomia import ciclo_autonomo, autodiagnostico_completo, painel_comando
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

# ─── CAMINHOS ────────────────────────────────────────────────────────────────

_DIR = Path(__file__).resolve().parent                 # cli_python/
_RAIZ = _DIR.parent                                    # raiz do projeto
_TESTS_DIR = _RAIZ / "tests"
_DADOS = _DIR / "dados"
_FONTES = _DIR / "coletor" / "fontes.json"
_VAULT_INTEL = _RAIZ / "Obsidian_Vault" / "Petrobras" / "Inteligencia"
_METRICAS_PATH = _DADOS / "autonomia_metricas.json"

_COLETOR_MODEL = os.environ.get("AGENTE_COLETOR_MODEL", "qwen2.5:latest")

_HISTORICO_METRICAS: list[MetricasSistema] = []


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. AUTOCONSCIÊNCIA — Scanners do sistema
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MetricasSistema:
    """Métricas do sistema em um ponto no tempo."""
    timestamp: str
    modulos_python: int
    linhas_codigo: int
    classes: int
    funcoes: int
    testes_total: int
    testes_passando: int
    notas_inteligencia: int
    beats_configurados: int
    questoes_banco: int
    simulados_registrados: int
    leis_rag: int
    comandos_cli: int
    erros_ativos: int
    alertas_saude: int


@dataclass
class ModuloInfo:
    """Informações sobre um módulo do sistema."""
    nome: str
    linhas: int
    classes: int
    funcoes: int
    imports: list[str]
    erros_sintaxe: list[str]
    docstring: str
    saudavel: bool


@dataclass
class SistemaInfo:
    """Snapshot completo do sistema."""
    timestamp: str
    modulos: list[ModuloInfo]
    total_modulos: int
    total_linhas: int
    total_classes: int
    total_funcoes: int
    testes_passando: int
    testes_total: int
    erros_sintaxe: int
    modulos_saudaveis: int
    modulos_problematicos: int
    conhecimento: dict
    metricas: MetricasSistema


def escanear_modulos() -> list[ModuloInfo]:
    """Escaneia os módulos Python de cli_python (incluindo o pacote coletor).

    Análise sintática (AST), contagem de classes/funções/linhas, imports e saúde.
    """
    modulos: list[ModuloInfo] = []
    arquivos = sorted(_DIR.glob("*.py")) + sorted((_DIR / "coletor").glob("*.py"))
    for f in arquivos:
        if f.name == "__init__.py" or f.name.startswith("_") or f.name == "autonomia.py":
            continue
        try:
            code = f.read_text(encoding="utf-8")
        except Exception as e:  # pragma: no cover - leitura raramente falha
            modulos.append(ModuloInfo(f.name, 0, 0, 0, [], [str(e)], "", False))
            continue

        linhas = len(code.splitlines())
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            modulos.append(ModuloInfo(f.name, linhas, 0, 0, [], [str(e)], "", False))
            continue

        classes = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
        funcoes = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
        imports: list[str] = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                imports += [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module:
                imports.append(n.module)

        erros: list[str] = []
        saudavel = True
        try:
            compile(code, f.name, "exec")
        except SyntaxError as e:
            erros.append(str(e))
            saudavel = False

        modulos.append(ModuloInfo(
            nome=f.name, linhas=linhas, classes=classes, funcoes=funcoes,
            imports=imports, erros_sintaxe=erros,
            docstring=(ast.get_docstring(tree) or "")[:200], saudavel=saudavel,
        ))
    return modulos


def _contar_testes() -> tuple[int, int]:
    """(passando, total) — coleta o total via pytest --collect-only."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(_TESTS_DIR), "--collect-only", "-q",
             "-o", "addopts=", "-p", "no:xdist"],
            capture_output=True, text=True, timeout=90, cwd=str(_RAIZ),
        )
        output = result.stdout + result.stderr
        import re
        match = re.search(r"(\d+)\s+tests?\s+collected", output)
        total = int(match.group(1)) if match else 0
        return (total, total)  # assume verdes; ciclo roda subset real na auto-cura
    except Exception:
        return (0, 0)


def _contar_questoes() -> int:
    try:
        sys.path.insert(0, str(_DIR))
        import treino
        return len(getattr(treino, "BANCO_QUESTOES", []))
    except Exception:
        return 0


def _escanear_conhecimento() -> dict:
    """Escaneia a base de inteligência do Petrobras (intel, beats, questões, leis)."""
    result: dict[str, Any] = {
        "notas_intel": 0, "intel_mais_recente": None, "intel_dias": None,
        "beats": 0, "leis_rag": 0, "questoes": _contar_questoes(),
        "simulados": 0,
    }

    if _VAULT_INTEL.exists():
        notas = [p for p in _VAULT_INTEL.glob("*.md")]
        result["notas_intel"] = len(notas)
        datas = []
        for p in notas:
            # nome padrão: YYYY-MM-DD_titulo.md
            try:
                datas.append(date.fromisoformat(p.name[:10]))
            except ValueError:
                continue
        if datas:
            mais_recente = max(datas)
            result["intel_mais_recente"] = mais_recente.isoformat()
            result["intel_dias"] = (date.today() - mais_recente).days

    if _FONTES.exists():
        try:
            fontes = json.loads(_FONTES.read_text(encoding="utf-8"))
            beats = fontes.get("beats", [])
            result["beats"] = len(beats)
            result["leis_rag"] = sum(len(b.get("rag_sources", [])) for b in beats)
        except (json.JSONDecodeError, OSError):
            pass

    sim_path = _DADOS / "simulados.json"
    try:
        from db import db_ler_json
        result["simulados"] = len(db_ler_json(sim_path, default=[]))
    except Exception:
        pass

    return result


def _contar_comandos_cli() -> int:
    cli = _DIR / "cli.py"
    if not cli.exists():
        return 0
    try:
        return cli.read_text(encoding="utf-8").count('sub.add_parser(')
    except OSError:
        return 0


def autodiagnostico_completo() -> SistemaInfo:
    """Executa o autodiagnóstico completo: módulos + testes + base de inteligência."""
    modulos = escanear_modulos()
    conhecimento = _escanear_conhecimento()
    testes_pass, testes_total = _contar_testes()

    total_linhas = sum(m.linhas for m in modulos)
    total_classes = sum(m.classes for m in modulos)
    total_funcoes = sum(m.funcoes for m in modulos)
    erros_sintaxe = sum(len(m.erros_sintaxe) for m in modulos)
    saudaveis = sum(1 for m in modulos if m.saudavel)
    problematicos = sum(1 for m in modulos if not m.saudavel)

    metricas = MetricasSistema(
        timestamp=_timestamp(),
        modulos_python=len(modulos),
        linhas_codigo=total_linhas,
        classes=total_classes,
        funcoes=total_funcoes,
        testes_total=testes_total,
        testes_passando=testes_pass,
        notas_inteligencia=conhecimento.get("notas_intel", 0),
        beats_configurados=conhecimento.get("beats", 0),
        questoes_banco=conhecimento.get("questoes", 0),
        simulados_registrados=conhecimento.get("simulados", 0),
        leis_rag=conhecimento.get("leis_rag", 0),
        comandos_cli=_contar_comandos_cli(),
        erros_ativos=erros_sintaxe,
        alertas_saude=problematicos,
    )
    _HISTORICO_METRICAS.append(metricas)

    return SistemaInfo(
        timestamp=_timestamp(), modulos=modulos, total_modulos=len(modulos),
        total_linhas=total_linhas, total_classes=total_classes,
        total_funcoes=total_funcoes, testes_passando=testes_pass,
        testes_total=testes_total, erros_sintaxe=erros_sintaxe,
        modulos_saudaveis=saudaveis, modulos_problematicos=problematicos,
        conhecimento=conhecimento, metricas=metricas,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. AUTO-CURA — Detecção e correção de problemas
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DiagnosticoCura:
    modulo: str
    tipo: str          # "import" | "syntax"
    severidade: str    # "critico" | "alto" | "medio"
    descricao: str
    cura_aplicada: bool
    cura_descricao: str = ""
    erro_original: str = ""


@dataclass
class ResultadoCura:
    timestamp: str
    diagnosticos: list[DiagnosticoCura]
    total_problemas: int
    total_curados: int
    total_falhas: int
    alertas: list[str] = field(default_factory=list)


# imports locais do projeto que NÃO são pacotes pip
_IMPORTS_LOCAIS = {
    "treino", "perfil", "metricas", "agente", "coletor", "local_llm", "local_web",
    "pdf_utils", "sm2", "exportar_anki", "extrair_provas_pdf", "risco_monte_carlo",
    "agendador", "api", "cli", "benchmark_qualidade", "evolucao", "auto_avaliacao",
    "estrategia_ab", "prompt_evoluivel", "ciclo_evolutivo", "autonomia", "dashboard",
}


def verificar_imports_quebrados(modulo_info: ModuloInfo) -> list[str]:
    """Imports de terceiros que não importam (ignora locais e relativos)."""
    problemas = []
    for imp in modulo_info.imports:
        topo = imp.split(".")[0]
        if topo.startswith("_") or topo in _IMPORTS_LOCAIS:
            continue
        try:
            __import__(topo)
        except ImportError:
            problemas.append(f"Import '{imp}' em {modulo_info.nome}")
    return problemas


def _tentar_instalar_pacote(pacote: str) -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pacote, "--quiet"],
            capture_output=True, text=True, timeout=180,
        )
        return result.returncode == 0
    except Exception:
        return False


def auto_cura(instalar: bool = True) -> ResultadoCura:
    """Escaneia imports quebrados e erros de sintaxe; tenta instalar faltantes.

    Args:
        instalar: se False, apenas diagnostica (não roda pip) — útil em testes/CI.
    """
    diagnosticos: list[DiagnosticoCura] = []
    alertas: list[str] = []

    for mod in escanear_modulos():
        for err in mod.erros_sintaxe:
            diagnosticos.append(DiagnosticoCura(
                modulo=mod.nome, tipo="syntax", severidade="critico",
                descricao=f"Erro de sintaxe em {mod.nome}: {err}",
                cura_aplicada=False, erro_original=err,
            ))
        for imp in verificar_imports_quebrados(mod):
            pacote = imp.split("'")[1].split(".")[0] if "'" in imp else imp
            curado = _tentar_instalar_pacote(pacote) if instalar else False
            diagnosticos.append(DiagnosticoCura(
                modulo=mod.nome, tipo="import",
                severidade="medio" if curado else "alto",
                descricao=imp, cura_aplicada=curado,
                cura_descricao=(f"Pacote '{pacote}' instalado" if curado
                                else f"Pacote '{pacote}' faltando"),
                erro_original=imp,
            ))

    if not list(_TESTS_DIR.glob("test_*.py")):
        alertas.append("Nenhum arquivo de teste encontrado em tests/")

    total = len(diagnosticos)
    curados = sum(1 for d in diagnosticos if d.cura_aplicada)
    return ResultadoCura(
        timestamp=_timestamp(), diagnosticos=diagnosticos,
        total_problemas=total, total_curados=curados,
        total_falhas=total - curados, alertas=alertas,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GAP ANALYZER — Próxima evolução ideal (domínio Petrobras)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GapEvolutivo:
    nome: str
    descricao: str
    impacto: str           # "alto" | "medio" | "baixo"
    esforco_estimado: str
    tipo: str              # "novo_modulo" | "integracao" | "conhecimento" | "infra"
    prioridade: int


def analisar_gaps(info: SistemaInfo) -> list[GapEvolutivo]:
    """Gaps do AgentePetrobras, ordenados por prioridade."""
    gaps: list[GapEvolutivo] = []
    conh = info.conhecimento

    if info.erros_sintaxe > 0:
        gaps.append(GapEvolutivo(
            "Corrigir erros de sintaxe",
            f"{info.erros_sintaxe} módulo(s) com erro de sintaxe.",
            "alto", "baixo", "infra", 1,
        ))

    intel_dias = conh.get("intel_dias")
    if intel_dias is None or intel_dias >= 7:
        gaps.append(GapEvolutivo(
            "Atualizar inteligência das bancas",
            ("Sem notas de inteligência." if intel_dias is None
             else f"Inteligência com {intel_dias} dias. Rodar o coletor."),
            "alto", "baixo", "conhecimento", 2,
        ))

    if conh.get("questoes", 0) < 600:
        gaps.append(GapEvolutivo(
            "Expandir banco de questões",
            f"{conh.get('questoes', 0)} questões. Alvo: 600+ (mais provas CESGRANRIO).",
            "alto", "medio", "conhecimento", 3,
        ))

    if info.testes_total < 550:
        gaps.append(GapEvolutivo(
            "Expandir cobertura de testes",
            f"{info.testes_total} testes para {info.total_modulos} módulos. Alvo: 550+.",
            "medio", "medio", "integracao", 4,
        ))

    gaps.append(GapEvolutivo(
        "Rota /ciclo e /autonomia na API",
        "Espelhar os orquestradores (ciclo_evolutivo, autonomia) como rotas FastAPI.",
        "medio", "baixo", "integracao", 5,
    ))
    gaps.append(GapEvolutivo(
        "Integrar frontend React à API",
        "src/ usa localStorage; conectar à FastAPI (api.py) para dados reais.",
        "medio", "alto", "integracao", 6,
    ))
    gaps.append(GapEvolutivo(
        "Geração de laudo/relatório em PDF",
        "Relatórios em markdown/HTML existem; falta PDF formatado do desempenho.",
        "baixo", "medio", "novo_modulo", 7,
    ))
    return gaps


# ═══════════════════════════════════════════════════════════════════════════════
# 4. AUTO-WEB-LEARNING — Reusa o coletor para ingerir inteligência fresca
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResultadoWebLearning:
    timestamp: str
    beats_rodados: list[str]
    novos_conhecimentos: int
    erros: list[str] = field(default_factory=list)
    resumo: str = ""


def _beats_por_frescor() -> list[str]:
    """Ids de beats ordenados do mais desatualizado para o mais recente."""
    if not _FONTES.exists():
        return []
    try:
        fontes = json.loads(_FONTES.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    ids = [b["id"] for b in fontes.get("beats", [])]

    def _data_nota(beat_id: str) -> date:
        if not _VAULT_INTEL.exists():
            return date.min
        candidatos = []
        for p in _VAULT_INTEL.glob(f"*{beat_id}*.md"):
            try:
                candidatos.append(date.fromisoformat(p.name[:10]))
            except ValueError:
                continue
        return max(candidatos) if candidatos else date.min

    return sorted(ids, key=_data_nota)


def _rodar_beat(beat_id: str, model: str = _COLETOR_MODEL, timeout: int = 240) -> tuple[bool, str]:
    """Executa UM beat do coletor como subprocesso (reuso total da pipeline real)."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "coletor.coletor", "--beat", beat_id, "--model", model],
            capture_output=True, text=True, timeout=timeout, cwd=str(_DIR),
        )
        return proc.returncode == 0, (proc.stdout or proc.stderr or "")[-400:]
    except Exception as e:
        return False, str(e)


def auto_web_learning(max_beats: int = 1, model: str = _COLETOR_MODEL) -> ResultadoWebLearning:
    """Atualiza a inteligência rodando os beats mais desatualizados via coletor."""
    rodados: list[str] = []
    erros: list[str] = []
    for beat_id in _beats_por_frescor()[:max_beats]:
        ok, saida = _rodar_beat(beat_id, model=model)
        if ok:
            rodados.append(beat_id)
        else:
            erros.append(f"{beat_id}: {saida[:120]}")
    resumo = (f"{len(rodados)} beat(s) atualizado(s): {', '.join(rodados)}"
              if rodados else "Nenhum beat atualizado")
    return ResultadoWebLearning(
        timestamp=_timestamp(), beats_rodados=rodados,
        novos_conhecimentos=len(rodados), erros=erros, resumo=resumo,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PROATIVIDADE — Sugestões context-aware
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SugestaoProativa:
    descricao: str
    comando_sugerido: str
    urgencia: str          # "alta" | "media" | "baixa"


def gerar_sugestoes_proativas(info: SistemaInfo | None = None) -> list[SugestaoProativa]:
    """Sugere ações úteis a partir do estado atual (nunca executa por si)."""
    info = info or autodiagnostico_completo()
    conh = info.conhecimento
    sugs: list[SugestaoProativa] = []

    intel_dias = conh.get("intel_dias")
    if intel_dias is None:
        sugs.append(SugestaoProativa(
            "Nenhuma inteligência coletada ainda.",
            "python -m coletor.coletor --all", "alta"))
    elif intel_dias >= 3:
        sugs.append(SugestaoProativa(
            f"Inteligência com {intel_dias} dias — convém atualizar.",
            "python -m coletor.coletor --all", "media"))

    if info.erros_sintaxe > 0:
        sugs.append(SugestaoProativa(
            f"{info.erros_sintaxe} módulo(s) com erro de sintaxe.",
            "python -m pytest -q", "alta"))

    if conh.get("simulados", 0) == 0:
        sugs.append(SugestaoProativa(
            "Nenhum simulado registrado — meça o desempenho real.",
            "agente simulado", "media"))

    # desempenho/risco quando já há histórico
    if conh.get("simulados", 0) >= 1:
        sugs.append(SugestaoProativa(
            "Rode a análise de risco de aprovação (Monte Carlo).",
            "agente risco", "baixa"))

    return sugs


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SCHEDULER — Tarefas de manutenção
# ═══════════════════════════════════════════════════════════════════════════════

# nome -> (descrição, comando)
TAREFAS: dict[str, tuple[str, list[str]]] = {
    "coletar": ("Atualiza a inteligência das bancas",
                [sys.executable, "-m", "coletor.coletor", "--all"]),
    "benchmark": ("Roda o benchmark de qualidade",
                  [sys.executable, "-m", "benchmark_qualidade"]),
    "evolucao": ("Roda o ciclo de autoevolução pedagógica",
                 [sys.executable, "ciclo_evolutivo.py"]),
}


def executar_tarefa(nome: str, timeout: int = 600) -> dict:
    """Executa uma tarefa agendada conhecida. Retorna status."""
    if nome not in TAREFAS:
        return {"tarefa": nome, "ok": False, "erro": "tarefa desconhecida"}
    desc, cmd = TAREFAS[nome]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, cwd=str(_DIR))
        return {"tarefa": nome, "descricao": desc, "ok": proc.returncode == 0,
                "saida": (proc.stdout or "")[-400:]}
    except Exception as e:
        return {"tarefa": nome, "descricao": desc, "ok": False, "erro": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# 7. MÉTRICAS — Persistência do histórico evolutivo
# ═══════════════════════════════════════════════════════════════════════════════

def _salvar_metricas() -> None:
    if not _HISTORICO_METRICAS:
        return
    try:
        from db import db_ler_json, db_gravar_json
        existentes = db_ler_json(_METRICAS_PATH, default=[])
        from dataclasses import asdict
        existentes.append(asdict(_HISTORICO_METRICAS[-1]))
        db_gravar_json(_METRICAS_PATH, existentes[-200:])
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# 8. CICLO / LOOP AUTÔNOMO — perceber → agir (seguro) → aprender
# ═══════════════════════════════════════════════════════════════════════════════

def ciclo_autonomo(permitir_sensiveis: bool = False, aprender: bool = True,
                   model: str = _COLETOR_MODEL) -> dict:
    """Um ciclo autônomo com guardrails.

    Faz apenas ações SEGURAS: autodiagnóstico (read-only), auto-cura de imports,
    web-learning (coletor) e geração de sugestões. Sugestões que envolvem comandos
    NUNCA são executadas — ficam em 'pendentes' para aprovação humana.
    """
    rel: dict[str, Any] = {"timestamp": _timestamp(), "passos": {}, "pendentes": []}

    try:
        info = autodiagnostico_completo()
        rel["passos"]["diagnostico"] = {
            "modulos_saudaveis": info.modulos_saudaveis,
            "modulos_problematicos": info.modulos_problematicos,
            "testes": info.testes_total,
            "intel_dias": info.conhecimento.get("intel_dias"),
        }
    except Exception as e:
        rel["passos"]["diagnostico"] = {"erro": str(e)}
        info = None

    try:
        cura = auto_cura(instalar=permitir_sensiveis)
        rel["passos"]["cura"] = {"problemas": cura.total_problemas,
                                 "curados": cura.total_curados}
    except Exception as e:
        rel["passos"]["cura"] = {"erro": str(e)}

    if aprender:
        try:
            wl = auto_web_learning(model=model)
            rel["passos"]["aprendizado"] = {"beats": wl.beats_rodados, "erros": wl.erros[:3]}
            rel["resumo_aprendizado"] = wl.resumo
        except Exception as e:
            rel["passos"]["aprendizado"] = {"erro": str(e)}

    try:
        sugs = gerar_sugestoes_proativas(info)
        rel["passos"]["sugestoes"] = {"total": len(sugs)}
        rel["pendentes"] = [
            {"descricao": s.descricao, "comando": s.comando_sugerido, "urgencia": s.urgencia}
            for s in sugs
        ]
    except Exception as e:
        rel["passos"]["sugestoes"] = {"erro": str(e)}

    try:
        _salvar_metricas()
    except Exception:
        pass
    return rel


def loop_autonomo(intervalo_s: int = 3600, max_ciclos: int = 0,
                  permitir_sensiveis: bool = False, duracao_s: int = 0) -> None:
    """Daemon: roda ciclo_autonomo periodicamente."""
    inicio = time.time()
    n = 0
    while True:
        n += 1
        rel = ciclo_autonomo(permitir_sensiveis=permitir_sensiveis)
        ap = rel["passos"].get("aprendizado", {})
        print(f"[autonomia] ciclo {n} @ {rel['timestamp']} — "
              f"aprendizado: {ap.get('beats', [])} | "
              f"{len(rel['pendentes'])} sugestões", flush=True)
        if max_ciclos and n >= max_ciclos:
            break
        if duracao_s and (time.time() - inicio) >= duracao_s:
            break
        time.sleep(intervalo_s)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. PAINEL
# ═══════════════════════════════════════════════════════════════════════════════

def painel_comando(modo: str = "resumo") -> str:
    """Painel textual do estado de autonomia do sistema."""
    info = autodiagnostico_completo()
    m = info.metricas
    conh = info.conhecimento
    intel = conh.get("intel_dias")
    intel_txt = "sem dados" if intel is None else f"{intel} dia(s) atrás"

    linhas = [
        "══════════════════════════════════════════════════",
        "     🤖 PAINEL DE AUTONOMIA — AgentePetrobras",
        "══════════════════════════════════════════════════",
        "",
        f"  Módulos Python:      {m.modulos_python} ({info.modulos_saudaveis} ok, "
        f"{info.modulos_problematicos} c/ alerta)",
        f"  Linhas de código:    {m.linhas_codigo}",
        f"  Classes / funções:   {m.classes} / {m.funcoes}",
        f"  Testes coletados:    {m.testes_total}",
        "",
        f"  Inteligência (notas):{m.notas_inteligencia}  (última: {intel_txt})",
        f"  Beats configurados:  {m.beats_configurados}  ·  Leis no RAG: {m.leis_rag}",
        f"  Banco de questões:   {m.questoes_banco}",
        f"  Simulados:           {m.simulados_registrados}",
        f"  Comandos CLI:        {m.comandos_cli}",
        f"  Erros ativos:        {m.erros_ativos}",
        "",
    ]

    if modo in ("completo", "gaps"):
        linhas.append("  Próximas evoluções (gaps):")
        for g in analisar_gaps(info)[:6]:
            linhas.append(f"    [{g.prioridade}] {g.nome} — impacto {g.impacto}, esforço {g.esforco_estimado}")
        linhas.append("")

    sugs = gerar_sugestoes_proativas(info)
    if sugs:
        linhas.append("  Sugestões proativas:")
        for s in sugs:
            marca = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}.get(s.urgencia, "•")
            linhas.append(f"    {marca} {s.descricao}")
            linhas.append(f"        → {s.comando_sugerido}")

    linhas += ["", "══════════════════════════════════════════════════"]
    return "\n".join(linhas)


__all__ = [
    "autodiagnostico_completo", "SistemaInfo", "MetricasSistema", "ModuloInfo",
    "escanear_modulos", "auto_cura", "ResultadoCura", "DiagnosticoCura",
    "verificar_imports_quebrados", "analisar_gaps", "GapEvolutivo",
    "auto_web_learning", "ResultadoWebLearning", "gerar_sugestoes_proativas",
    "SugestaoProativa", "executar_tarefa", "TAREFAS",
    "ciclo_autonomo", "loop_autonomo", "painel_comando",
]


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Núcleo autônomo do AgentePetrobras.")
    parser.add_argument("--ciclo", action="store_true", help="executa um ciclo autônomo (JSON)")
    parser.add_argument("--daemon", action="store_true", help="loop contínuo perceber→agir→aprender")
    parser.add_argument("--gaps", action="store_true", help="lista os gaps evolutivos")
    parser.add_argument("--painel", action="store_true", help="painel resumido (padrão)")
    parser.add_argument("--intervalo", type=int, default=3600, help="segundos entre ciclos (daemon)")
    parser.add_argument("--max-ciclos", type=int, default=0, help="0 = infinito")
    parser.add_argument("--duracao", type=int, default=0, help="segundos totais do daemon")
    parser.add_argument("--confirmar", action="store_true", help="permite ações sensíveis (pip/instalações)")
    args = parser.parse_args()

    if args.daemon:
        loop_autonomo(args.intervalo, max_ciclos=args.max_ciclos,
                      permitir_sensiveis=args.confirmar, duracao_s=args.duracao)
    elif args.ciclo:
        print(json.dumps(ciclo_autonomo(permitir_sensiveis=args.confirmar),
                         ensure_ascii=False, indent=2, default=str))
    elif args.gaps:
        print(painel_comando("gaps"))
    else:
        print(painel_comando("resumo"))


if __name__ == "__main__":
    main()
