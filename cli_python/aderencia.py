"""Aderência & Accountability — o coach que te mantém na linha.

Reúne os sinais que já existem (streak de estudo, Índice de Consistência,
revisões SM-2 vencidas, dias até a prova) num CHECK-IN diário com nudges
acionáveis. Coach bom não só ensina — cobra cadência.

Uso:
    from aderencia import checkin, formatar_checkin
    print(formatar_checkin(checkin()))
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent
_DADOS = _DIR / "dados"

DIAS_SEM_SIMULADO_ALERTA = 4


def _ler_json(caminho: Path, default: Any):
    from db import db_ler_json
    return db_ler_json(caminho, default=default)


def _dias_inativo(sessoes: list[dict]) -> int | None:
    """Dias desde a última sessão de estudo registrada."""
    datas = []
    for s in sessoes or []:
        d = s.get("data") or s.get("date")
        if d:
            try:
                datas.append(date.fromisoformat(str(d)[:10]))
            except ValueError:
                continue
    if not datas:
        return None
    return (date.today() - max(datas)).days


def nudges(streak: int, revisoes_vencidas: int, dias_inativo: int | None,
           dias_ate_prova: int | None, ic: float | None) -> list[dict[str, str]]:
    """Lista de cobranças acionáveis, ordenadas por urgência."""
    out: list[dict[str, str]] = []

    if dias_inativo is None:
        out.append({"urgencia": "alta", "texto": "Você ainda não registrou estudo. Comece hoje — 1 sessão já inicia seu streak.",
                    "acao": "agente simulado -a"})
    elif dias_inativo == 0 and streak >= 1:
        out.append({"urgencia": "baixa", "texto": f"Streak de {streak} dia(s) mantido hoje. 👏 Continue amanhã.",
                    "acao": ""})
    elif dias_inativo >= 1:
        risco = "alta" if streak >= 1 else "media"
        msg = (f"Streak de {streak} dia(s) em RISCO — {dias_inativo} dia(s) sem estudar. Estude hoje para não zerar."
               if streak >= 1 else f"{dias_inativo} dia(s) sem estudar. Retome a cadência hoje.")
        out.append({"urgencia": risco, "texto": msg, "acao": "agente simulado -a"})

    if revisoes_vencidas > 0:
        out.append({"urgencia": "alta" if revisoes_vencidas >= 10 else "media",
                    "texto": f"{revisoes_vencidas} revisão(ões) SM-2 vencida(s) — revise antes de avançar (retenção cai rápido).",
                    "acao": "agente revisoes"})

    if dias_inativo is not None and dias_inativo >= DIAS_SEM_SIMULADO_ALERTA:
        out.append({"urgencia": "media",
                    "texto": f"{dias_inativo} dia(s) sem medir desempenho. Faça um simulado para calibrar o diagnóstico.",
                    "acao": "agente simulado -a"})

    if ic is not None and ic < 0.5:
        out.append({"urgencia": "media",
                    "texto": f"Consistência baixa (IC {ic:.0%}). Distribua o estudo na semana em vez de concentrar.",
                    "acao": "agente cronograma"})

    if dias_ate_prova is not None and 0 < dias_ate_prova <= 30:
        out.append({"urgencia": "alta",
                    "texto": f"Faltam {dias_ate_prova} dia(s) para a prova — fase de sprint: simulados cronometrados.",
                    "acao": "agente simulado -t 60"})

    ordem = {"alta": 0, "media": 1, "baixa": 2}
    out.sort(key=lambda n: ordem.get(n["urgencia"], 3))
    return out


def checkin(perfil: dict | None = None, sessoes: list | None = None,
            com_prescricao: bool = True) -> dict[str, Any]:
    """Monta o check-in diário (sinais + nudges + próxima ação)."""
    if perfil is None:
        perfil = _ler_json(_DADOS / "perfil_candidato.json", {})
    if sessoes is None:
        sessoes = _ler_json(_DADOS / "sessoes.json", [])

    import metricas as met
    streak = met.streak_de_sessoes(sessoes)
    dias_prova = met.dias_ate_prova(perfil)
    meta = perfil.get("meta_questoes_semana") or 100
    try:
        ic = met.consistencia_semanal(sessoes, meta).get("ic")
    except Exception:
        ic = None

    revisoes_vencidas = 0
    try:
        import sm2
        revisoes_vencidas = sm2.estatisticas().get("vencidos", 0)
    except Exception:
        pass

    dias_inativo = _dias_inativo(sessoes)
    lista = nudges(streak, revisoes_vencidas, dias_inativo, dias_prova, ic)

    proxima = None
    if com_prescricao:
        try:
            import prescricao
            p = prescricao.prescrever()
            proxima = {"disciplina": p["disciplina"], "estrategia": p["estrategia"],
                       "prescricao": p["prescricao"]}
        except Exception:
            proxima = None

    return {
        "data": datetime.now().strftime("%Y-%m-%d"),
        "streak": streak, "dias_inativo": dias_inativo,
        "revisoes_vencidas": revisoes_vencidas, "dias_ate_prova": dias_prova,
        "ic": ic, "nudges": lista, "proxima_acao": proxima,
    }


def formatar_checkin(c: dict[str, Any]) -> str:
    ic_txt = "—" if c.get("ic") is None else f"{c['ic']:.0%}"
    prova_txt = "—" if c.get("dias_ate_prova") is None else f"{c['dias_ate_prova']} dia(s)"
    linhas = [
        "══════════════════════════════════════════════════",
        "     📅 CHECK-IN DIÁRIO",
        "══════════════════════════════════════════════════",
        "",
        f"  🔥 Streak: {c['streak']} dia(s)    Consistência: {ic_txt}",
        f"  🗓️  Revisões vencidas: {c['revisoes_vencidas']}    Até a prova: {prova_txt}",
        "",
    ]
    if c["nudges"]:
        linhas.append("  Cobranças de hoje:")
        for n in c["nudges"]:
            marca = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}.get(n["urgencia"], "•")
            linhas.append(f"    {marca} {n['texto']}")
            if n.get("acao"):
                linhas.append(f"        → {n['acao']}")
    else:
        linhas.append("  ✅ Tudo em dia. Mantenha o ritmo.")

    p = c.get("proxima_acao")
    if p:
        linhas += ["", f"  🎯 Próximo passo: {p['disciplina']} ({p['estrategia']})",
                   f"     {p['prescricao']}"]
    linhas += ["", "══════════════════════════════════════════════════"]
    return "\n".join(linhas)


__all__ = ["nudges", "checkin", "formatar_checkin"]
