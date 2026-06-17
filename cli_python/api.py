"""API REST do AgentePetrobras (FastAPI).

Uso:
    uvicorn api:app --reload --port 8000
    ou
    python api.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
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
HISTORICO_PRATICA = DADOS / "historico_pratica.json"


def _log_pratica(acertos: int, total: int) -> None:
    """Acumula contagem diária de prática (para o gráfico de progresso)."""
    if total <= 0:
        return
    try:
        hist = _ler_json(HISTORICO_PRATICA, {})
        dia = hist.setdefault(date.today().isoformat(), {"respondidas": 0, "acertos": 0})
        dia["respondidas"] += total
        dia["acertos"] += acertos
        _gravar_json(HISTORICO_PRATICA, hist)
    except Exception:
        pass


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


# ── Loop de prática (recall espaçado + coach) ─────────────────────────────

class RespostaPraticaInput(BaseModel):
    id: str
    escolha: int
    tempo_seg: float = 0.0


class ClassificarErroInput(BaseModel):
    disciplina: str = ""
    categoria: str  # C / A / B / T


def _qid(q) -> str:
    """ID estável da questão (hash do enunciado)."""
    return hashlib.sha1(q.pergunta.encode(), usedforsecurity=False).hexdigest()[:12]


def _qidx(q) -> int:
    """Chave inteira estável para o SM-2."""
    return int(_qid(q)[:8], 16)


def _achar_questao(qid: str):
    import treino
    return next((q for q in treino.banco() if _qid(q) == qid), None)


def _payload_questao(q, tipo: str, pendentes: int) -> dict:
    return {
        "id": _qid(q),
        "pergunta": q.pergunta,
        "opcoes": q.opcoes,
        "disciplina": q.disciplina or "Geral",
        "tipo": tipo,  # "revisao" (SM-2 devida) ou "nova"
        "revisoes_pendentes": pendentes,
    }


@app.get("/pratica/proxima", tags=["Prática"])
def pratica_proxima(disciplina: str = "") -> dict:
    """Próxima questão. Prioriza REVISÕES DEVIDAS (SM-2) — fecha o loop de
    repetição espaçada — e só então serve uma questão nova adaptativa."""
    import treino
    banco = treino.banco()

    # 1) Revisões espaçadas devidas têm prioridade
    devidas: list[dict] = []
    try:
        import sm2
        devidas = sm2.revisoes_devidas()
        por_idx = {_qidx(q): q for q in banco}
        for card in devidas:
            q = por_idx.get(card.get("questao_idx"))
            if q is not None and (not disciplina or (q.disciplina or "Geral") == disciplina):
                return _payload_questao(q, "revisao", len(devidas))
    except Exception:
        pass

    # 2) Questão nova — seleção adaptativa por Elo (alvo ~75% de acerto =
    #    zona de desenvolvimento proximal). Fallback para a seleção simples.
    qs = []
    try:
        import coaching
        qs = coaching.selecionar_adaptativo(1, disciplina=disciplina, banco=banco)
    except Exception:
        qs = []
    if not qs:
        qs = treino.selecionar_questoes(1, disciplina=disciplina)
    if not qs:
        raise HTTPException(status_code=404, detail="Nenhuma questão disponível")
    return _payload_questao(qs[0], "nova", len(devidas))


@app.post("/pratica/responder", tags=["Prática"])
def pratica_responder(inp: RespostaPraticaInput) -> dict:
    """Corrige, agenda revisão espaçada (SM-2) e devolve feedback imediato."""
    q = _achar_questao(inp.id)
    if q is None:
        raise HTTPException(status_code=404, detail="Questão não encontrada")
    acertou = inp.escolha == q.correta

    # Elo: atualiza a habilidade REAL do candidato (que o coach injeta no prompt)
    # e a dificuldade do item — abastece a autoevolução com dados de prática.
    try:
        import coaching
        coaching.registrar_resposta(q.disciplina or "Geral", q, acertou)
    except Exception:
        pass
    _log_pratica(1 if acertou else 0, 1)

    revisar_em = ""
    try:
        import sm2
        qualidade = 5 if acertou else 2
        if acertou and inp.tempo_seg and inp.tempo_seg > 180:
            qualidade = 4  # acertou, mas demorou
        cartoes = sm2.registrar_revisao(_qidx(q), q.disciplina or "Geral", q.pergunta, qualidade)
        for c in cartoes:
            if c["questao_idx"] == _qidx(q):
                revisar_em = c.get("proxima_revisao", "")
                break
    except Exception:
        pass

    fonte = ""
    try:
        import rag
        tr = rag.buscar(q.pergunta, k=1)
        if tr:
            fonte = f"({tr[0]['fonte']}) {tr[0]['texto'][:400]}"
    except Exception:
        pass

    return {
        "correta": acertou,
        "correta_idx": q.correta,
        "explicacao": q.explicacao,
        "fonte": fonte,
        "disciplina": q.disciplina or "Geral",
        "revisar_em": revisar_em,
    }


@app.post("/pratica/coach", tags=["Prática"])
def pratica_coach(inp: RespostaPraticaInput) -> dict:
    """Explicação socrática do coach (LLM) — best-effort, carregada à parte."""
    q = _achar_questao(inp.id)
    if q is None:
        raise HTTPException(status_code=404, detail="Questão não encontrada")
    try:
        import treino
        cliente = LocalLLM()
        return {"feedback": treino._feedback_llm(cliente, q, inp.escolha) or ""}
    except Exception:
        return {"feedback": ""}


@app.get("/plano-hoje", tags=["Plano"])
def plano_hoje() -> dict:
    """Plano do dia: revisões devidas + foco (Elo) + meta + recomendação por
    evidência (recuperação espaçada primeiro, depois prática no ponto fraco)."""
    import coaching
    diag = coaching.diagnostico()
    foco = diag.get("foco_recomendado", [])
    try:
        import sm2
        revisoes = len(sm2.revisoes_devidas())
    except Exception:
        revisoes = 0

    perfil = _ler_json(PERFIL_PATH, {})
    meta = int(perfil.get("meta_questoes_dia") or 12)
    try:
        dias = met.dias_ate_prova(perfil)
    except Exception:
        dias = None

    passos = []
    if revisoes > 0:
        passos.append(
            f"1) Faça suas {revisoes} revisão(ões) devida(s) primeiro — recuperação "
            "espaçada é a prioridade (maior efeito de retenção)."
        )
    n = 2 if revisoes > 0 else 1
    if foco:
        passos.append(
            f"{n}) Pratique ~{meta} questões novas com foco em {foco[0]} "
            "(seu ponto mais fraco pela habilidade medida)."
        )
    else:
        passos.append(f"{n}) Pratique ~{meta} questões novas (modo adaptativo).")
    passos.append(
        f"{n + 1}) Em cada erro, classifique (C/A/B/T) e explique a resposta em voz "
        "alta (auto-explicação) — não apenas releia."
    )

    return {
        "revisoes_devidas": revisoes,
        "foco": foco,
        "meta_diaria": meta,
        "dias_ate_prova": dias,
        "passos": passos,
        "disciplinas": diag.get("disciplinas", []),
    }


def _parse_nota_intel(texto: str, stem: str) -> tuple[str, str]:
    """Extrai (título, resumo) de uma nota de inteligência (.md do vault)."""
    titulo = stem.replace("_", " ").strip()
    resumo = ""
    titulo_do_h1 = ""
    for ln in texto.splitlines():
        s = ln.strip()
        m = re.match(r"(?i)^titulo:\s*(.+)", s)
        if m:
            titulo = m.group(1).strip()
        m2 = re.match(r"(?i)^resumo[_a-z]*:\s*(.+)", s)
        if m2 and not resumo:
            resumo = m2.group(1).strip()
        if s.startswith("# ") and not titulo_do_h1:
            titulo_do_h1 = s[2:].strip()
    if titulo == stem.replace("_", " ").strip() and titulo_do_h1:
        titulo = titulo_do_h1
    if not resumo:
        corpo = []
        for ln in texto.splitlines():
            s = ln.strip()
            if not s or s.startswith(("#", "---", "-", "|", "_")) or re.match(r"(?i)^\w+:\s", s):
                continue
            corpo.append(s)
            if len(" ".join(corpo)) > 200:
                break
        resumo = " ".join(corpo)
    return titulo[:120], resumo[:240]


@app.get("/intel", tags=["Radar"])
def intel(limite: int = 15) -> dict:
    """Notas de inteligência recentes (coletor + radar Instagram) do vault."""
    vault = Path(os.environ.get("AGENTE_VAULT", BASE.parent / "Obsidian_Vault"))
    pasta = vault / "Petrobras" / "Inteligencia"
    if not pasta.exists():
        return {"notas": []}
    notas = []
    arquivos = sorted(pasta.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for md in arquivos[:limite]:
        try:
            texto = md.read_text(encoding="utf-8")
        except OSError:
            continue
        titulo, resumo = _parse_nota_intel(texto, md.stem)
        notas.append({
            "arquivo": md.name,
            "titulo": titulo,
            "resumo": resumo,
            "atualizado": datetime.fromtimestamp(md.stat().st_mtime).isoformat(timespec="seconds"),
        })
    return {"notas": notas}


@app.get("/maestria", tags=["Maestria"])
def maestria() -> dict:
    """Painel de maestria: habilidade (Elo) por disciplina + revisões de hoje."""
    import coaching
    diag = coaching.diagnostico()
    try:
        import sm2
        revisoes_hoje = len(sm2.revisoes_devidas())
    except Exception:
        revisoes_hoje = 0
    return {
        "disciplinas": diag.get("disciplinas", []),
        "foco": diag.get("foco_recomendado", []),
        "revisoes_hoje": revisoes_hoje,
    }


class RespostaItem(BaseModel):
    id: str
    escolha: int


class CorrigirSimuladoInput(BaseModel):
    respostas: list[RespostaItem]
    tempo_seg: float = 0.0


@app.get("/simulado/montar", tags=["Simulado"])
def simulado_montar(n: int = 20, disciplina: str = "") -> dict:
    """Monta um simulado com N questões (sem as respostas)."""
    import treino
    n = max(1, min(n, 70))
    qs = treino.selecionar_questoes(n, disciplina=disciplina)
    if not qs:
        raise HTTPException(status_code=404, detail="Nenhuma questão disponível")
    return {
        "n": len(qs),
        "questoes": [
            {"id": _qid(q), "pergunta": q.pergunta, "opcoes": q.opcoes, "disciplina": q.disciplina or "Geral"}
            for q in qs
        ],
    }


@app.post("/simulado/corrigir", tags=["Simulado"])
def simulado_corrigir(inp: CorrigirSimuladoInput) -> dict:
    """Corrige o simulado, devolve nota + desempenho por disciplina e alimenta o Elo."""
    import treino
    banco = {_qid(q): q for q in treino.banco()}
    por_disc: dict[str, dict] = {}
    detalhes = []
    acertos = 0
    for r in inp.respostas:
        q = banco.get(r.id)
        if q is None:
            continue
        ok = r.escolha == q.correta
        acertos += 1 if ok else 0
        disc = q.disciplina or "Geral"
        d = por_disc.setdefault(disc, {"total": 0, "acertos": 0})
        d["total"] += 1
        d["acertos"] += 1 if ok else 0
        detalhes.append({
            "id": r.id, "disciplina": disc, "sua": r.escolha,
            "correta_idx": q.correta, "acertou": ok,
            "pergunta": q.pergunta, "opcoes": q.opcoes, "explicacao": q.explicacao,
        })
        try:
            import coaching
            coaching.registrar_resposta(disc, q, ok)
        except Exception:
            pass
    total = len(detalhes)
    for d in por_disc.values():
        d["pct"] = round(d["acertos"] / d["total"] * 100) if d["total"] else 0
    _log_pratica(acertos, total)
    return {
        "total": total,
        "acertos": acertos,
        "pct": round(acertos / total * 100) if total else 0,
        "por_disciplina": por_disc,
        "detalhes": detalhes,
    }


class RedacaoInput(BaseModel):
    texto: str
    tema: str = ""


@app.post("/redacao/avaliar", tags=["Redação"])
def redacao_avaliar(inp: RedacaoInput) -> dict:
    """Avalia uma redação/discursiva por rubrica CESGRANRIO (LLM local).
    Sem LLM, devolve análise estrutural (contagem + orientação)."""
    import redacao
    try:
        cliente = LocalLLM()
    except Exception:
        cliente = None
    return redacao.avaliar(inp.texto, tema=inp.tema, cliente=cliente)


@app.get("/progresso", tags=["Progresso"])
def progresso(dias: int = 14) -> dict:
    """Série diária de prática (para o gráfico de evolução) + totais acumulados."""
    dias = max(1, min(dias, 90))
    hist = _ler_json(HISTORICO_PRATICA, {})
    hoje = date.today()
    serie = []
    for i in range(dias - 1, -1, -1):
        d = (hoje - timedelta(days=i)).isoformat()
        reg = hist.get(d, {})
        r = reg.get("respondidas", 0)
        a = reg.get("acertos", 0)
        serie.append({"data": d, "respondidas": r, "acertos": a, "pct": round(a / r * 100) if r else 0})
    tot_r = sum(v.get("respondidas", 0) for v in hist.values())
    tot_a = sum(v.get("acertos", 0) for v in hist.values())
    return {
        "serie": serie,
        "total_respondidas": tot_r,
        "total_acertos": tot_a,
        "pct_geral": round(tot_a / tot_r * 100) if tot_r else 0,
        "dias_ativos": sum(1 for v in hist.values() if v.get("respondidas", 0) > 0),
    }


@app.post("/pratica/classificar", tags=["Prática"])
def pratica_classificar(inp: ClassificarErroInput) -> dict:
    """Registra a classificação do erro (Conteúdo/Atenção/Branco/Tempo)."""
    try:
        import erros
        erros.registrar_erro(inp.disciplina or "Geral", inp.categoria)
        return {"status": "ok", "categoria": inp.categoria}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
