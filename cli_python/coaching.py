"""Coaching Adaptativo — Diagnóstico de habilidade e seleção por dificuldade.

Estima a habilidade do candidato POR DISCIPLINA e a dificuldade de cada questão
com um esquema tipo Elo (jogador × item). Com isso:

- serve questões na dificuldade certa (~75% de acerto esperado — "dificuldade
  desejável", onde se aprende mais);
- diagnostica forças/fraquezas a partir do desempenho REAL (não do que o
  candidato acha que sabe);
- recomenda em que disciplina focar.

O estado vive em dados/coaching_elo.json. Integra com treino (banco de questões)
sem precisar alterar a QuestaoMC: cada questão é identificada por um hash estável
do enunciado.

Uso:
    from coaching import registrar_resposta, selecionar_adaptativo, diagnostico
    registrar_resposta("Língua Portuguesa", questao, acertou=True)
    questoes = selecionar_adaptativo(5, "Língua Portuguesa")
    print(formatar_diagnostico())
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent
_ESTADO_PATH = _DIR / "dados" / "coaching_elo.json"

RATING_INICIAL = 1000.0
K_HABILIDADE = 32.0       # candidato move mais rápido
K_ITEM = 16.0             # item calibra mais devagar
# alvo de seleção: dificuldade ligeiramente abaixo da habilidade → ~75% de acerto
OFFSET_DESEJAVEL = 190.0


def qid(questao: Any) -> str:
    """Id estável de uma questão a partir do enunciado."""
    texto = getattr(questao, "pergunta", None) or str(questao)
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:12]


# ─── Persistência ────────────────────────────────────────────────────────────

def estado_vazio() -> dict[str, Any]:
    return {"habilidades": {}, "n_respostas": {}, "itens": {}}


def carregar(caminho: Path | None = None) -> dict[str, Any]:
    caminho = caminho or _ESTADO_PATH
    from db import db_ler_json
    d = db_ler_json(caminho, default=estado_vazio())
    for k in ("habilidades", "n_respostas", "itens"):
        d.setdefault(k, {})
    return d


def salvar(estado: dict[str, Any], caminho: Path | None = None) -> None:
    caminho = caminho or _ESTADO_PATH
    from db import db_gravar_json
    db_gravar_json(caminho, estado)


# ─── Elo ─────────────────────────────────────────────────────────────────────

def expectativa(habilidade: float, dificuldade: float) -> float:
    """Probabilidade esperada de o candidato acertar (logística Elo)."""
    return 1.0 / (1.0 + 10 ** ((dificuldade - habilidade) / 400.0))


def registrar_resposta(disciplina: str, questao: Any, acertou: bool,
                       estado: dict[str, Any] | None = None,
                       persistir: bool = True) -> dict[str, Any]:
    """Atualiza a habilidade da disciplina e a dificuldade do item.

    Retorna o estado atualizado. Se estado=None, carrega/salva do disco.
    """
    proprio = estado is None
    estado = estado if estado is not None else carregar()
    disc = disciplina or "Geral"
    item = qid(questao)

    hab = estado["habilidades"].get(disc, RATING_INICIAL)
    dif = estado["itens"].get(item, RATING_INICIAL)

    esperado = expectativa(hab, dif)
    resultado = 1.0 if acertou else 0.0

    estado["habilidades"][disc] = round(hab + K_HABILIDADE * (resultado - esperado), 1)
    estado["itens"][item] = round(dif + K_ITEM * (esperado - resultado), 1)
    estado["n_respostas"][disc] = estado["n_respostas"].get(disc, 0) + 1

    if proprio and persistir:
        salvar(estado)
    return estado


def habilidade(disciplina: str, estado: dict[str, Any] | None = None) -> float:
    estado = estado if estado is not None else carregar()
    return estado["habilidades"].get(disciplina or "Geral", RATING_INICIAL)


def dificuldade_questao(questao: Any, estado: dict[str, Any] | None = None) -> float:
    estado = estado if estado is not None else carregar()
    return estado["itens"].get(qid(questao), RATING_INICIAL)


def nivel(rating: float) -> str:
    """Rótulo legível para um rating de habilidade."""
    if rating < 850:
        return "iniciante"
    if rating < 1000:
        return "em desenvolvimento"
    if rating < 1150:
        return "intermediário"
    if rating < 1300:
        return "avançado"
    return "domínio"


# ─── Seleção adaptativa ──────────────────────────────────────────────────────

def selecionar_adaptativo(n: int, disciplina: str = "", banco: list | None = None,
                          estado: dict[str, Any] | None = None) -> list:
    """Seleciona n questões cuja dificuldade ~ habilidade do candidato (−offset).

    Mais perto do alvo = melhor; um pequeno desempate aleatório evita repetir
    sempre as mesmas. Questões sem dificuldade calibrada usam o rating inicial.
    """
    import random

    if banco is None:
        try:
            from treino import banco as _banco_completo
            banco = _banco_completo()
        except Exception:
            from treino import BANCO_QUESTOES
            banco = BANCO_QUESTOES
    estado = estado if estado is not None else carregar()

    pool = list(banco)
    if disciplina:
        pool = [q for q in pool if getattr(q, "disciplina", "").lower() == disciplina.lower()]
    if not pool:
        return []

    hab = estado["habilidades"].get(disciplina or "Geral", RATING_INICIAL)
    alvo = hab - OFFSET_DESEJAVEL

    def _custo(q):
        dif = estado["itens"].get(qid(q), RATING_INICIAL)
        return abs(dif - alvo) + random.uniform(0, 40)  # jitter p/ variedade

    pool.sort(key=_custo)
    return pool[:n]


# ─── Diagnóstico ─────────────────────────────────────────────────────────────

def diagnostico(estado: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resumo por disciplina + recomendação de foco (menor habilidade com dados)."""
    estado = estado if estado is not None else carregar()
    habs = estado.get("habilidades", {})
    ns = estado.get("n_respostas", {})

    disciplinas = []
    for disc, rating in sorted(habs.items(), key=lambda kv: kv[1]):
        disciplinas.append({
            "disciplina": disc,
            "rating": round(rating, 1),
            "nivel": nivel(rating),
            "respostas": ns.get(disc, 0),
            "acerto_esperado": round(expectativa(rating, RATING_INICIAL), 2),
        })

    # foco: disciplinas com pelo menos 3 respostas e menor rating
    com_dados = [d for d in disciplinas if d["respostas"] >= 3]
    foco = [d["disciplina"] for d in com_dados[:2]]

    return {
        "disciplinas": disciplinas,
        "foco_recomendado": foco,
        "total_respostas": sum(ns.values()),
        "itens_calibrados": len(estado.get("itens", {})),
    }


def formatar_diagnostico(estado: dict[str, Any] | None = None) -> str:
    diag = diagnostico(estado)
    linhas = [
        "══════════════════════════════════════════════════",
        "     🎯 DIAGNÓSTICO ADAPTATIVO",
        "══════════════════════════════════════════════════",
        "",
        f"  Respostas registradas: {diag['total_respostas']}  ·  "
        f"itens calibrados: {diag['itens_calibrados']}",
        "",
    ]
    if not diag["disciplinas"]:
        linhas.append("  (sem dados ainda — faça um simulado adaptativo)")
    else:
        linhas.append("  Habilidade por disciplina (menor → maior):")
        for d in diag["disciplinas"]:
            barra = "█" * max(1, int((d["rating"] - 700) / 60))
            linhas.append(
                f"    {d['disciplina'][:24]:24s} {d['rating']:6.0f} "
                f"[{d['nivel']:18s}] {barra}  (n={d['respostas']})")
    if diag["foco_recomendado"]:
        linhas += ["", f"  ➜ Foco recomendado: {', '.join(diag['foco_recomendado'])}"]
    linhas += ["", "══════════════════════════════════════════════════"]
    return "\n".join(linhas)


__all__ = [
    "qid", "carregar", "salvar", "estado_vazio", "expectativa",
    "registrar_resposta", "habilidade", "dificuldade_questao", "nivel",
    "selecionar_adaptativo", "diagnostico", "formatar_diagnostico",
    "RATING_INICIAL",
]
