"""SM-2 Spaced Repetition — algoritmo de revisão espaçada.

Baseado no algoritmo SM-2 (SuperMemo), usado no Anki.
Gerencia qual questão revisar e quando, conforme o desempenho do usuário.

Uso:
    from sm2 import SM2, revisoes_devidas, registrar_revisao
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"
SM2_PATH = DADOS / "sm2.json"


@dataclass
class CartaoSM2:
    questao_idx: int
    disciplina: str
    pergunta: str
    ease: float = 2.5
    interval_dias: int = 0
    rep: int = 0
    proxima_revisao: str = ""  # ISO date
    ultima_qualidade: int = 0
    revisoes: int = 0

    @property
    def vencido(self) -> bool:
        if not self.proxima_revisao:
            return True
        return date.fromisoformat(self.proxima_revisao) <= date.today()

    @property
    def dias_ate_vencimento(self) -> int:
        if not self.proxima_revisao:
            return 0
        return (date.fromisoformat(self.proxima_revisao) - date.today()).days


def _default() -> list[dict]:
    return []


def carregar() -> list[dict]:
    if not SM2_PATH.exists():
        return []
    try:
        return json.loads(SM2_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def salvar(cartoes: list[dict]) -> None:
    DADOS.mkdir(parents=True, exist_ok=True)
    SM2_PATH.write_text(json.dumps(cartoes, ensure_ascii=False, indent=2), encoding="utf-8")


def calcular_proximo_intervalo(qualidade: int, rep: int, interval_dias: int, ease: float) -> tuple[int, float, int]:
    """Aplica SM-2 e retorna (novo_intervalo, novo_ease, nova_rep)."""
    if qualidade < 3:
        return (1, max(1.3, ease - 0.2), 0)

    if rep == 0:
        novo_intervalo = 1
    elif rep == 1:
        novo_intervalo = 6
    else:
        novo_intervalo = round(interval_dias * ease)

    novo_ease = ease + (0.1 - (5 - qualidade) * (0.08 + (5 - qualidade) * 0.02))
    novo_ease = max(1.3, novo_ease)

    return (novo_intervalo, round(novo_ease, 2), rep + 1)


def registrar_revisao(
    questao_idx: int,
    disciplina: str,
    pergunta: str,
    qualidade: int,
    cartoes: list[dict] | None = None,
) -> list[dict]:
    """Registra a revisão de uma questão e retorna a lista atualizada."""
    if cartoes is None:
        cartoes = carregar()

    idx = next((i for i, c in enumerate(cartoes) if c["questao_idx"] == questao_idx), None)

    if idx is not None:
        c = cartoes[idx]
    else:
        c = {"questao_idx": questao_idx, "disciplina": disciplina, "pergunta": pergunta,
             "ease": 2.5, "interval_dias": 0, "rep": 0,
             "proxima_revisao": "", "ultima_qualidade": 0, "revisoes": 0}
        cartoes.append(c)

    novo_intervalo, novo_ease, nova_rep = calcular_proximo_intervalo(
        qualidade, c["rep"], c["interval_dias"], c["ease"]
    )

    c["ease"] = novo_ease
    c["interval_dias"] = novo_intervalo
    c["rep"] = nova_rep
    c["proxima_revisao"] = (date.today() + timedelta(days=novo_intervalo)).isoformat()
    c["ultima_qualidade"] = qualidade
    c["revisoes"] += 1

    salvar(cartoes)
    return cartoes


def revisoes_devidas(cartoes: list[dict] | None = None) -> list[dict]:
    """Retorna cartões vencidos (devidos para revisão hoje)."""
    if cartoes is None:
        cartoes = carregar()
    hoje = date.today().isoformat()
    return [c for c in cartoes if c.get("proxima_revisao", "") <= hoje]


def proximas_revisoes(limite: int = 10, cartoes: list[dict] | None = None) -> list[dict]:
    """Retorna os próximos cartões a vencer (ordenados por data)."""
    if cartoes is None:
        cartoes = carregar()
    ordenados = sorted(cartoes, key=lambda c: c.get("proxima_revisao", "9999-99-99"))
    return ordenados[:limite]


def estatisticas(cartoes: list[dict] | None = None) -> dict[str, Any]:
    """Estatísticas do SM-2."""
    if cartoes is None:
        cartoes = carregar()
    if not cartoes:
        return {"total": 0, "vencidos": 0, "ease_medio": 0, "revisoes_hoje": 0}

    hoje = date.today().isoformat()
    vencidos = [c for c in cartoes if c.get("proxima_revisao", "") <= hoje]
    return {
        "total": len(cartoes),
        "vencidos": len(vencidos),
        "ease_medio": round(sum(c.get("ease", 2.5) for c in cartoes) / len(cartoes), 2),
        "revisoes_hoje": len(vencidos),
        "revisoes_total": sum(c.get("revisoes", 0) for c in cartoes),
    }


def inicializar_do_banco(banco: list | None = None) -> list[dict]:
    """Cria cartões SM-2 para todas as questões do banco se não existirem."""
    cartoes = carregar()
    if cartoes:
        return cartoes

    if banco is None:
        from treino import BANCO_QUESTOES
        banco = BANCO_QUESTOES

    for i, q in enumerate(banco):
        cartoes.append({
            "questao_idx": i,
            "disciplina": q.disciplina,
            "pergunta": q.pergunta[:80],
            "ease": 2.5,
            "interval_dias": 0,
            "rep": 0,
            "proxima_revisao": date.today().isoformat(),
            "ultima_qualidade": 0,
            "revisoes": 0,
        })

    salvar(cartoes)
    return cartoes
