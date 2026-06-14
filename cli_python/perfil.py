"""Modelo vivo do candidato — persistência em JSON.

Guarda o estado do PERFIL_CANDIDATO descrito no §2 do system prompt.
O agente emite diretivas <<ATUALIZAR_PERFIL: campo = valor>> na resposta;
este módulo as aplica e salva em disco, dando memória de longo prazo.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

# Diretiva emitida pelo modelo dentro da resposta.
# Ex.: <<ATUALIZAR_PERFIL: historico_acerto.portugues = 64>>
_DIRETIVA = re.compile(
    r"<<\s*ATUALIZAR_PERFIL\s*:\s*([a-zA-Z0-9_.]+)\s*=\s*(.+?)\s*>>"
)

# Diretiva de estratégia (autoevolução) — parsada por evolucao.py,
# removida do texto visível aqui.
# Ex.: <<ESTRATEGIA: retrieval_practice = portugues acerto 55%>>
_DIRETIVA_ESTRATEGIA = re.compile(
    r"<<\s*ESTRATEGIA\s*:\s*\w+\s*=\s*.+?\s*>>"
)


def perfil_vazio() -> dict[str, Any]:
    """Estrutura inicial — espelha os campos do §2."""
    return {
        "_criado_em": date.today().isoformat(),
        "_atualizado_em": date.today().isoformat(),
        # Dados estruturais
        "cargo_alvo": None,
        "area": None,
        "nivel_cargo": None,
        "formacao": None,
        "dominios_expertise": None,
        "data_prova": None,
        "total_dias_ate_prova": None,
        "horas_dia_util": None,
        "horas_sabado": None,
        "horas_domingo": None,
        "restricoes": None,
        # Estado do plano
        "fase_atual": None,  # FUNDACAO|DOMINIO|CONSOLIDACAO|SPRINT|EMERGENCIA
        "semana_atual": None,
        "semana_total": None,
        "ritmo_vs_planejado": None,
        "horas_acumuladas": None,
        "questoes_resolvidas": None,
        "meta_questoes_semana": None,  # usado no Índice de Consistência (§5)
        # Performance (sub-dicionários por disciplina)
        "historico_acerto": {},
        "tendencia": {},
        "distribuicao_erros": {"C": None, "A": None, "B": None, "T": None},
        "erro_dominante_historico": None,
        "projecao_nota": None,
        # Comportamento
        "melhor_horario": None,
        "duracao_foco_min": None,
        "gatilhos_procrastinacao": None,
        # Psicológico
        "nivel_ansiedade": None,  # BAIXO|MEDIO|ALTO|CRITICO
        "tipo_bloqueio": None,  # PROCRASTINACAO|BURNOUT|MEDO|NENHUM
        "streak_dias": 0,
        "maior_streak": 0,
        "ultima_vitoria": None,
        "semanas_consecutivas_queda": 0,
        "narrativa_identidade": None,
        # Meta
        "nota_corte_estimada": None,
        "meta_operacional_acerto": None,
        "gap_para_meta": None,
        "probabilidade_aprovacao": None,
    }


def carregar(caminho: Path) -> dict[str, Any]:
    from db import db_ler_json
    dados = db_ler_json(caminho, default={})
    base = perfil_vazio()
    base.update(dados)
    return base


def salvar(perfil: dict[str, Any], caminho: Path) -> None:
    perfil["_atualizado_em"] = date.today().isoformat()
    from db import db_gravar_json
    db_gravar_json(caminho, perfil)


def _coagir(valor: str) -> Any:
    """Converte 'null'/números/strings vindos da diretiva para tipos Python."""
    v = valor.strip().strip('"').strip("'")
    if v.lower() in ("null", "none", "nenhum", "-"):
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def _set_campo(perfil: dict[str, Any], caminho_campo: str, valor: Any) -> None:
    """Aplica 'a.b = valor' navegando/criando sub-dicionários."""
    partes = caminho_campo.split(".")
    alvo = perfil
    for p in partes[:-1]:
        if not isinstance(alvo.get(p), dict):
            alvo[p] = {}
        alvo = alvo[p]
    alvo[partes[-1]] = valor


def aplicar_diretivas(texto: str, perfil: dict[str, Any]) -> tuple[str, list[str]]:
    """Extrai e aplica todas as diretivas <<ATUALIZAR_PERFIL>> do texto.

    Retorna (texto_limpo_sem_diretivas, lista_de_mudancas_legiveis).
    """
    mudancas: list[str] = []

    for campo, valor_bruto in _DIRETIVA.findall(texto):
        valor = _coagir(valor_bruto)
        _set_campo(perfil, campo, valor)
        mudancas.append(f"{campo} = {valor}")

    # Mantém maior_streak coerente
    try:
        if (perfil.get("streak_dias") or 0) > (perfil.get("maior_streak") or 0):
            perfil["maior_streak"] = perfil["streak_dias"]
    except TypeError:
        pass

    texto_limpo = _DIRETIVA.sub("", texto)
    texto_limpo = _DIRETIVA_ESTRATEGIA.sub("", texto_limpo).strip()
    return texto_limpo, mudancas


def esta_vazio(perfil: dict[str, Any]) -> bool:
    """True se ainda não houve diagnóstico (sem cargo definido)."""
    return not perfil.get("cargo_alvo")


def resumo_para_prompt(perfil: dict[str, Any]) -> str:
    """Serializa o perfil para injetar no system prompt a cada sessão."""
    if esta_vazio(perfil):
        return (
            "[PERFIL_CANDIDATO] VAZIO — primeira sessão. "
            "Execute o DIAGNÓSTICO INICIAL (§3). Não faça abertura de 3 linhas."
        )
    relevante = {k: v for k, v in perfil.items() if not k.startswith("_") and v not in (None, {}, [])}
    return "[PERFIL_CANDIDATO]\n" + json.dumps(relevante, ensure_ascii=False, indent=2)
