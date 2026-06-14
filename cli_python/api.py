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

DADOS = BASE / "dados"
PERFIL_PATH = DADOS / "perfil_candidato.json"
SESSOES_PATH = DADOS / "sessoes.json"
SIMULADOS_PATH = DADOS / "simulados.json"


def _ler_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default
    return default


def _gravar_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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
    messages = historico[-20:] + [{"role": "user", "content": input_data.mensagem}]

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


if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
