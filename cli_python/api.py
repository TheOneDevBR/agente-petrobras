"""API REST do AgentePetrobras (FastAPI).

Uso:
    uvicorn api:app --reload --port 8000
    ou
    python api.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

import metricas as met
import treino as treino_mod
from local_llm import LocalLLM

app = FastAPI(
    title="AgentePetrobras API",
    description="API REST do preparador autônomo para concurso Petrobras (CESGRANRIO)",
    version="4.0",
)

# CORS — libera o frontend React (Vite dev server) a chamar a API.
# Em produção, restrinja allow_origins ao domínio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DADOS = BASE / "dados"
PERFIL_PATH = DADOS / "perfil_candidato.json"
SESSOES_PATH = DADOS / "sessoes.json"
SIMULADOS_PATH = DADOS / "simulados.json"


def _ler_json(path: Path, default):
    from db import db_ler_json
    return db_ler_json(path, default=default)


def _gravar_json(path: Path, data) -> None:
    from db import db_gravar_json
    db_gravar_json(path, data)


# ── Schemas ──────────────────────────────────────────────────────────────

class Mensagem(BaseModel):
    message: str


class PerfilResponse(BaseModel):
    perfil: dict
    sessoes: int
    simulados: int


class SessaoInput(BaseModel):
    disciplina: str
    questoes: int = 0
    acertos: int = 0
    minutos: int = 0
    erro: str = ""


class SimuladoInput(BaseModel):
    n_questoes: int = 5
    cronometro: int = 0
    disciplina: str = ""


class PerguntaInput(BaseModel):
    mensagem: str
    # Contexto compacto do candidato vindo do frontend (perfil em localStorage).
    # Injetado no system prompt sem acoplar os dois esquemas de perfil.
    contexto_extra: str = ""
    # Histórico da conversa gerenciado pelo cliente (web). Se vazio, o backend
    # usa o histórico persistido em dados/historico_conversa.json.
    historico: list[dict] = []


# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/", tags=["Status"])
def root() -> dict:
    return {
        "api": "AgentePetrobras v4.0",
        "hoje": date.today().isoformat(),
        "perfil_existe": PERFIL_PATH.exists(),
        "sessoes": len(_ler_json(SESSOES_PATH, [])),
        "simulados": len(_ler_json(SIMULADOS_PATH, [])),
    }


@app.get("/perfil", response_model=PerfilResponse, tags=["Perfil"])
def get_perfil() -> dict:
    perfil = _ler_json(PERFIL_PATH, {})
    sessoes = _ler_json(SESSOES_PATH, [])
    simulados = _ler_json(SIMULADOS_PATH, [])
    return {
        "perfil": perfil,
        "sessoes": len(sessoes),
        "simulados": len(simulados),
    }


@app.post("/perfil/atualizar", tags=["Perfil"])
def atualizar_perfil(dados: dict) -> dict:
    perfil = _ler_json(PERFIL_PATH, {})
    perfil.update(dados)
    _gravar_json(PERFIL_PATH, perfil)
    return {"status": "ok", "campos": list(dados.keys())}


@app.get("/metricas", tags=["Métricas"])
def get_metricas() -> dict:
    perfil = _ler_json(PERFIL_PATH, {})
    sessoes = _ler_json(SESSOES_PATH, [])
    return {
        "painel": met.painel(perfil, sessoes),
        "streak": met.streak_de_sessoes(sessoes),
        "ic": met.consistencia_semanal(sessoes, int(perfil.get("meta_questoes_semana") or 200)),
        "dias_ate_prova": met.dias_ate_prova(perfil),
        "projecao": met.projecao_nota(
            perfil.get("historico_acerto", {}),
            perfil.get("meta_operacional_acerto"),
        ),
    }


@app.post("/sessao", tags=["Sessão"])
def registrar_sessao(input_data: SessaoInput) -> dict:
    perfil = _ler_json(PERFIL_PATH, {})
    sessoes = _ler_json(SESSOES_PATH, [])

    from agente import registrar_sessao as reg_fn
    msg = reg_fn(perfil, sessoes, input_data.model_dump())

    return {"status": "ok", "mensagem": str(msg)}


@app.get("/sessoes", tags=["Sessão"])
def listar_sessoes(limite: int = 20) -> list:
    sessoes = _ler_json(SESSOES_PATH, [])
    return sorted(sessoes, key=lambda s: s.get("data", ""), reverse=True)[:limite]


@app.get("/simulados", tags=["Simulado"])
def listar_simulados(limite: int = 20) -> list:
    simulados = _ler_json(SIMULADOS_PATH, [])
    return sorted(simulados, key=lambda s: s.get("data", ""), reverse=True)[:limite]


@app.post("/simulado/iniciar", tags=["Simulado"])
def iniciar_simulado(input_data: SimuladoInput) -> dict:
    resultado = treino_mod.iniciar_simulado(
        n_questoes=input_data.n_questoes,
        cronometro=input_data.cronometro,
        disciplina=input_data.disciplina,
    )
    if resultado.get("erro"):
        raise HTTPException(status_code=400, detail=resultado["erro"])
    return resultado


@app.post("/prova-completa", tags=["Simulado"])
def prova_completa() -> dict:
    if not hasattr(treino_mod, "iniciar_prova_completa"):
        raise HTTPException(status_code=501, detail="Função não disponível")
    resultado = treino_mod.iniciar_prova_completa()
    return resultado


@app.post("/perguntar", tags=["Agente"])
def perguntar(input_data: PerguntaInput) -> dict:
    """Envia pergunta ao agente e retorna resposta."""
    try:
        cliente = LocalLLM()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM não disponível: {e}")

    perfil = _ler_json(PERFIL_PATH, {})
    sessoes = _ler_json(SESSOES_PATH, [])
    historico = _ler_json(DADOS / "historico_conversa.json", [])

    from agente import montar_system
    system = montar_system(perfil, sessoes)
    if input_data.contexto_extra:
        system += (
            "\n\n[CONTEXTO DO CANDIDATO (informado pelo app web)]\n"
            + input_data.contexto_extra
        )
    # RAG: trechos relevantes das apostilas indexadas (se houver índice)
    try:
        import rag
        ctx_rag = rag.contexto_para_prompt(input_data.mensagem)
        if ctx_rag:
            system += "\n\n" + ctx_rag
    except Exception:
        pass

    # Prioriza o histórico enviado pelo cliente web; senão usa o persistido.
    base_hist = input_data.historico if input_data.historico else historico
    messages = base_hist[-20:] + [{"role": "user", "content": input_data.mensagem}]

    try:
        resposta = cliente.chat(system=system, messages=messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no LLM: {e}")

    historico.append({"role": "user", "content": input_data.mensagem})
    historico.append({"role": "assistant", "content": resposta})
    _gravar_json(DADOS / "historico_conversa.json", historico)

    return {"pergunta": input_data.mensagem, "resposta": resposta}


@app.get("/banco-questoes", tags=["Banco de Questões"])
def banco_questoes(disciplina: str = "") -> list[dict]:
    from treino import BANCO_QUESTOES
    questoes = []
    for q in BANCO_QUESTOES:
        if disciplina and q.disciplina.lower() != disciplina.lower():
            continue
        questoes.append({
            "pergunta": q.pergunta,
            "opcoes": q.opcoes,
            "correta": q.correta,
            "explicacao": q.explicacao,
            "disciplina": q.disciplina,
            "tags": q.tags,
        })
    return questoes


@app.get("/relatorio", tags=["Relatório"])
def relatorio(formato: str = "md") -> dict:
    perfil = _ler_json(PERFIL_PATH, {})
    sessoes = _ler_json(SESSOES_PATH, [])
    md = met.relatorio_semanal_md(perfil, sessoes)
    html = met.exportar_html(perfil, sessoes) if hasattr(met, "exportar_html") else ""
    return {
        "markdown": md,
        "html": html if formato == "html" else "",
    }


@app.post("/ciclo", tags=["Evolução"])
def disparar_ciclo() -> dict:
    """Dispara o ciclo evolutivo usando o modelo 7B para auto-tuning de prompts."""
    try:
        from ciclo_evolutivo import executar_ciclo
        from local_llm import LocalLLM
        
        cliente_7b = LocalLLM(model="qwen2.5:7b")
        resultado = executar_ciclo(cliente_llm=cliente_7b, evoluir_prompts=True, verbose=False)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/autonomia/ciclo", tags=["Autonomia"])
def disparar_autonomia() -> dict:
    """Dispara um ciclo autônomo (perceber -> agir -> aprender)."""
    try:
        from autonomia import ciclo_autonomo
        resultado = ciclo_autonomo(permitir_sensiveis=False, aprender=True)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/autonomia/diagnostico", tags=["Autonomia"])
def get_autonomia_diagnostico() -> dict:
    """Retorna o autodiagnóstico de saúde completo do sistema."""
    try:
        from autonomia import autodiagnostico_completo, painel_comando
        from dataclasses import asdict
        
        info = autodiagnostico_completo()
        return {
            "snapshot": asdict(info.metricas),
            "painel": painel_comando("resumo")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/autonomia/gaps", tags=["Autonomia"])
def get_autonomia_gaps() -> list:
    """Retorna a lista de gaps evolutivos identificados."""
    try:
        from autonomia import analisar_gaps, autodiagnostico_completo
        from dataclasses import asdict
        
        info = autodiagnostico_completo()
        gaps = analisar_gaps(info)
        return [asdict(g) for g in gaps]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
