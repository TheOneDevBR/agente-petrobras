"""Avaliador de Redação / Discursiva — rubrica CESGRANRIO, fundamentado.

Avalia uma resposta discursiva por uma rubrica explícita (atendimento ao tema,
conteúdo/argumentação, estrutura/coesão, norma culta). Usa o LLM apenas para
JULGAR o texto fornecido — com a mesma diretriz anti-invenção do coletor: não
inventa trechos, aponta problemas concretos do texto. Sem LLM, faz uma análise
estrutural objetiva (contagem de palavras/parágrafos) e sinaliza o que falta.

Uso:
    from redacao import avaliar, formatar
    r = avaliar(texto, tema="Transição energética e o papel da Petrobras", cliente=llm)
    print(formatar(r))
"""

from __future__ import annotations

import json
import re
from typing import Any

# (chave, rótulo, pontuação máxima) — soma = 10
RUBRICA = [
    ("tema", "Atendimento ao tema / abordagem", 2.5),
    ("conteudo", "Conteúdo e argumentação", 3.0),
    ("estrutura", "Estrutura, coesão e coerência", 2.5),
    ("norma", "Norma culta (gramática/ortografia)", 2.0),
]
NOTA_MAXIMA = sum(p for _, _, p in RUBRICA)
MIN_PALAVRAS = 100


def _contar(texto: str) -> dict[str, int]:
    palavras = len(re.findall(r"\b\w+\b", texto))
    paragrafos = len([p for p in re.split(r"\n\s*\n", texto.strip()) if p.strip()])
    return {"palavras": palavras, "paragrafos": paragrafos}


def avaliar(texto: str, tema: str = "", cliente: Any = None) -> dict[str, Any]:
    """Avalia a redação. Com LLM → rubrica completa; sem LLM → análise estrutural."""
    texto = (texto or "").strip()
    metricas = _contar(texto)
    base: dict[str, Any] = {
        "tema": tema, "metricas": metricas, "criterios": {},
        "nota_total": None, "nota_maxima": NOTA_MAXIMA, "feedback": "", "avaliado_por": None,
    }

    if not texto:
        base["feedback"] = "Texto vazio — nada a avaliar."
        base["avaliado_por"] = "estrutural"
        return base

    if metricas["palavras"] < MIN_PALAVRAS:
        base["feedback"] = (
            f"Texto muito curto ({metricas['palavras']} palavras; mínimo sugerido "
            f"{MIN_PALAVRAS}). Desenvolva tese, argumentos e conclusão.")
        base["avaliado_por"] = "estrutural"
        return base

    if cliente is None:
        base["feedback"] = (
            f"Análise estrutural: {metricas['palavras']} palavras, "
            f"{metricas['paragrafos']} parágrafo(s). Avaliação por rubrica requer o LLM.")
        base["avaliado_por"] = "estrutural"
        return base

    try:
        base.update(_avaliar_llm(texto, tema, cliente))
        base["avaliado_por"] = "llm"
    except Exception as e:
        base["feedback"] = f"Falha na avaliação por LLM ({e}); use a análise estrutural."
        base["avaliado_por"] = "estrutural"
    return base


def _avaliar_llm(texto: str, tema: str, cliente: Any) -> dict[str, Any]:
    criterios_txt = "\n".join(f"- {k} ({rot}): 0 a {p}" for k, rot, p in RUBRICA)
    system = (
        "Você é avaliador de prova discursiva da banca CESGRANRIO. Avalie APENAS o "
        "texto fornecido pela rubrica. NÃO invente trechos nem elogios genéricos; "
        "aponte problemas concretos citando o que está (ou falta) no texto. "
        "Responda SOMENTE com JSON válido."
    )
    prompt = (
        f"TEMA: {tema or '(livre)'}\n\nRUBRICA (criterio: 0..max):\n{criterios_txt}\n\n"
        f"TEXTO DO CANDIDATO:\n\"\"\"\n{texto[:4000]}\n\"\"\"\n\n"
        "Devolva exatamente este JSON (notas numéricas dentro do máximo de cada critério):\n"
        '{"criterios": {"tema": {"nota": 0, "comentario": ""}, '
        '"conteudo": {"nota": 0, "comentario": ""}, '
        '"estrutura": {"nota": 0, "comentario": ""}, '
        '"norma": {"nota": 0, "comentario": ""}}, '
        '"feedback": "2-3 frases objetivas de como melhorar"}'
    )
    resp = cliente.chat(system=system, messages=[{"role": "user", "content": prompt}], max_tokens=700)
    dados = _parse_json(resp)

    criterios: dict[str, Any] = {}
    total = 0.0
    for k, rot, pmax in RUBRICA:
        item = (dados.get("criterios", {}) or {}).get(k, {}) if isinstance(dados, dict) else {}
        try:
            nota = float(item.get("nota", 0))
        except (TypeError, ValueError):
            nota = 0.0
        nota = max(0.0, min(pmax, nota))   # clamp dentro do máximo
        total += nota
        criterios[k] = {"rotulo": rot, "nota": round(nota, 2), "max": pmax,
                        "comentario": str(item.get("comentario", ""))[:300]}
    return {
        "criterios": criterios,
        "nota_total": round(total, 2),
        "feedback": str((dados or {}).get("feedback", ""))[:500],
    }


def _parse_json(resp: str | None) -> dict:
    if not resp:
        return {}
    m = re.search(r"\{.*\}", resp, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def formatar(r: dict[str, Any]) -> str:
    linhas = [
        "══════════════════════════════════════════════════",
        "     ✍️  AVALIAÇÃO DE REDAÇÃO",
        "══════════════════════════════════════════════════",
        "",
        f"  Tema: {r.get('tema') or '(livre)'}",
        f"  Palavras: {r['metricas']['palavras']}  ·  parágrafos: {r['metricas']['paragrafos']}",
        "",
    ]
    if r.get("criterios"):
        for k, c in r["criterios"].items():
            linhas.append(f"  {c['rotulo'][:38]:38s} {c['nota']:.1f}/{c['max']}")
            if c.get("comentario"):
                linhas.append(f"      {c['comentario']}")
        linhas += ["", f"  NOTA: {r['nota_total']:.1f} / {r['nota_maxima']}"]
    if r.get("feedback"):
        linhas += ["", f"  ➜ {r['feedback']}"]
    linhas += ["", f"  (avaliado por: {r.get('avaliado_por')})",
               "══════════════════════════════════════════════════"]
    return "\n".join(linhas)


__all__ = ["RUBRICA", "NOTA_MAXIMA", "avaliar", "formatar"]
