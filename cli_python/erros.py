"""Classificação de Erros C/A/B/T — coaching a partir do erro REAL.

Taxonomia de erro em prova (padrão de cursinhos CESGRANRIO):
    C = Conteúdo       — não sabia a matéria
    A = Atenção        — sabia, mas errou por desatenção/pressa
    B = Interpretação  — entendeu errado o enunciado / caiu na pegadinha da banca
    T = Tempo          — errou/chutou por falta de tempo

Classifica cada erro (preferindo o autorrelato do candidato, com heurística e
LLM como apoio), acumula a distribuição e prescreve a correção certa para o erro
DOMINANTE — porque a forma de subir a nota muda conforme o motivo do erro.

Uso:
    from erros import classificar, registrar_erro, distribuicao, prescricao_por_erro
    cat, motivo = classificar(questao, escolha, tempo_seg=6, autorrelato="A")
    registrar_erro("Português", cat)
    print(formatar_distribuicao())
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent
_ESTADO_PATH = _DIR / "dados" / "erros_cabt.json"

CATEGORIAS = {
    "C": "Conteúdo (não sabia)",
    "A": "Atenção (sabia, errou por desatenção)",
    "B": "Interpretação (pegadinha da banca / enunciado)",
    "T": "Tempo (faltou tempo / chute)",
}

# Correção prescrita para cada erro dominante.
PRESCRICAO = {
    "C": "Erro de CONTEÚDO domina: priorize teoria + prática de recuperação na "
         "disciplina fraca antes de mais simulados. Estude o tópico, depois refaça.",
    "A": "Erro de ATENÇÃO domina: você sabe a matéria. Treine revisão da resposta "
         "antes de marcar, sublinhe o que a questão pede e desacelere nas fáceis.",
    "B": "Erro de INTERPRETAÇÃO domina: foque no estilo CESGRANRIO — leia o "
         "comando, marque negações/exceções ('EXCETO', 'INCORRETO') e refaça "
         "questões comentadas da banca.",
    "T": "Erro de TEMPO domina: treine simulados cronometrados, defina tempo-alvo "
         "por questão e aprenda a pular e voltar em vez de travar.",
}


def classificar(questao: Any = None, escolha: int | None = None,
                tempo_seg: float | None = None, autorrelato: str | None = None,
                cliente: Any = None) -> tuple[str, str]:
    """Classifica um erro em C/A/B/T. Retorna (categoria, motivo).

    Prioridade: autorrelato do candidato > LLM (se houver) > heurística de tempo.
    """
    if autorrelato:
        cat = autorrelato.strip().upper()[:1]
        if cat in CATEGORIAS:
            return cat, "autorrelato do candidato"

    if cliente is not None and questao is not None:
        try:
            cat = _classificar_llm(cliente, questao, escolha)
            if cat in CATEGORIAS:
                return cat, "inferido por LLM"
        except Exception:
            pass

    # Heurística por tempo (apoio fraco; honesta sobre a incerteza)
    if tempo_seg is not None:
        if tempo_seg < 10:
            return "A", "heurística: resposta muito rápida (pressa/desatenção)"
        if tempo_seg > 90:
            return "B", "heurística: muito tempo (provável dificuldade de interpretação)"
    return "C", "assumido (sem sinais suficientes — confirme o motivo)"


def _classificar_llm(cliente: Any, questao: Any, escolha: int | None) -> str:
    pergunta = getattr(questao, "pergunta", str(questao))
    opcoes = getattr(questao, "opcoes", [])
    correta = getattr(questao, "correta", None)
    system = (
        "Você classifica o tipo de erro de um candidato em prova, em UMA letra: "
        "C (conteúdo/não sabia), A (atenção/sabia mas errou), B (interpretação/"
        "pegadinha), T (tempo). Responda APENAS a letra."
    )
    prompt = (
        f"Questão: {pergunta}\n"
        f"Opções: {opcoes}\n"
        f"Correta: {correta} | Escolha do candidato: {escolha}\n"
        "Classifique o erro mais provável (C/A/B/T):"
    )
    resp = cliente.chat(system=system, messages=[{"role": "user", "content": prompt}], max_tokens=4)
    return (resp or "").strip().upper()[:1]


# ─── Persistência e agregação ────────────────────────────────────────────────

def estado_vazio() -> dict[str, Any]:
    return {"contagem": {"C": 0, "A": 0, "B": 0, "T": 0}, "por_disciplina": {}}


def carregar(caminho: Path | None = None) -> dict[str, Any]:
    caminho = caminho or _ESTADO_PATH
    from db import db_ler_json
    d = db_ler_json(caminho, default=estado_vazio())
    d.setdefault("contagem", {"C": 0, "A": 0, "B": 0, "T": 0})
    d.setdefault("por_disciplina", {})
    return d


def salvar(estado: dict[str, Any], caminho: Path | None = None) -> None:
    caminho = caminho or _ESTADO_PATH
    from db import db_gravar_json
    db_gravar_json(caminho, estado)


def registrar_erro(disciplina: str, categoria: str,
                   estado: dict[str, Any] | None = None, persistir: bool = True) -> dict[str, Any]:
    cat = categoria.strip().upper()[:1]
    if cat not in CATEGORIAS:
        cat = "C"
    proprio = estado is None
    estado = estado if estado is not None else carregar()
    estado["contagem"][cat] = estado["contagem"].get(cat, 0) + 1
    disc = (disciplina or "Geral")
    pd = estado["por_disciplina"].setdefault(disc, {"C": 0, "A": 0, "B": 0, "T": 0})
    pd[cat] = pd.get(cat, 0) + 1
    if proprio and persistir:
        salvar(estado)
    return estado


def distribuicao(estado: dict[str, Any] | None = None) -> dict[str, Any]:
    estado = estado if estado is not None else carregar()
    cont = estado.get("contagem", {})
    total = sum(cont.values())
    pct = {k: (round(v / total * 100, 1) if total else 0.0) for k, v in cont.items()}
    dominante = max(cont, key=cont.get) if total else None
    return {"contagem": cont, "percentuais": pct, "total": total, "dominante": dominante}


def prescricao_por_erro(dominante: str | None) -> str:
    if not dominante:
        return "Sem erros registrados ainda — faça um simulado e classifique os erros."
    return PRESCRICAO.get(dominante, "")


def formatar_distribuicao(estado: dict[str, Any] | None = None) -> str:
    dist = distribuicao(estado)
    linhas = [
        "══════════════════════════════════════════════════",
        "     🧭 PERFIL DE ERROS (C/A/B/T)",
        "══════════════════════════════════════════════════",
        "",
        f"  Erros classificados: {dist['total']}",
        "",
    ]
    if dist["total"] == 0:
        linhas.append("  (sem dados — classifique os erros dos simulados)")
    else:
        for k, nome in CATEGORIAS.items():
            n = dist["contagem"].get(k, 0)
            p = dist["percentuais"].get(k, 0)
            barra = "█" * int(p / 5)
            linhas.append(f"  {k} {nome[:34]:34s} {n:3d}  {p:4.0f}% {barra}")
        linhas += ["", f"  ➜ {prescricao_por_erro(dist['dominante'])}"]
    linhas += ["", "══════════════════════════════════════════════════"]
    return "\n".join(linhas)


__all__ = [
    "CATEGORIAS", "PRESCRICAO", "classificar", "registrar_erro",
    "carregar", "salvar", "estado_vazio", "distribuicao",
    "prescricao_por_erro", "formatar_distribuicao",
]
