"""Métricas determinísticas da preparação.

O LLM raciocina, mas NÃO deve fazer contas críticas (P5 — progresso sempre
mensurável). Este módulo calcula em Python: dias até a prova, streak,
índice de consistência (§5), projeção de nota ponderada e gap para a meta —
e monta o [PAINEL_DE_CONTROLE] injetado no system prompt a cada sessão.
"""

from __future__ import annotations

import shutil
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

# Pesos médios por categoria na prova CESGRANRIO nível superior (§4/§11).
# Soma = 1.00. São referência; ajustam-se ao edital quando disponível.
PESOS_CATEGORIA = {
    "portugues": 0.22,
    "rl_mat": 0.15,
    "petrobras": 0.12,
    "legislacao": 0.11,
    "especificos": 0.40,
}

NOMES_CATEGORIA = {
    "portugues": "Língua Portuguesa",
    "rl_mat": "Raciocínio Lógico / Matemática",
    "petrobras": "Conhecimentos Petrobras / Setor",
    "legislacao": "Legislação / Governança",
    "especificos": "Conhecimentos Específicos",
}

# Palavras-chave → categoria de peso (heurística de mapeamento).
_KEYWORDS = [
    ("portugues", ("portug", "lingua", "língua", "leitura", "interpret", "gramat", "texto", "crase", "regencia", "regência")),
    ("rl_mat", ("logic", "lógic", "raciocin", "raciocín", "matemat", "matemát", " rl", "rl_", "probab", "combinat", "financeir", "estatist")),
    ("legislacao", ("lei", "legisl", "13.303", "13303", "lgpd", "governanc", "governanç", "complianc", "anticorrup", "estatuto", "14.133", "12.846")),
    ("petrobras", ("petrobras", "setor", "o&g", "oeg", "atualidad", "esg", "sustentab", "pre-sal", "pré-sal", "presal")),
]


def _categoria_de(disciplina: str) -> str:
    def _flat(s: str) -> str:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    d = f" {_flat(disciplina.lower())} "
    for cat, kws in _KEYWORDS:
        if any(_flat(k) in d for k in kws):
            return cat
    return "especificos"


def dias_ate_prova(perfil: dict[str, Any]) -> int | None:
    dp = perfil.get("data_prova")
    if not dp:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            d = datetime.strptime(str(dp).strip(), fmt).date()
            return (d - date.today()).days
        except ValueError:
            continue
    return None


def _data_sessao(s: dict[str, Any]) -> date | None:
    try:
        return datetime.strptime(s.get("data", ""), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def streak_de_sessoes(sessoes: list[dict[str, Any]]) -> int:
    """Dias consecutivos com ≥1 sessão, terminando em hoje ou ontem."""
    datas = sorted({d for s in sessoes if (d := _data_sessao(s))}, reverse=True)
    if not datas:
        return 0
    hoje = date.today()
    if datas[0] not in (hoje, hoje - timedelta(days=1)):
        return 0
    streak = 1
    for ant, prox in zip(datas, datas[1:]):
        if (ant - prox).days == 1:
            streak += 1
        else:
            break
    return streak


def _sessoes_ultimos_dias(sessoes: list[dict[str, Any]], dias: int) -> list[dict[str, Any]]:
    limite = date.today() - timedelta(days=dias - 1)
    return [s for s in sessoes if (d := _data_sessao(s)) and d >= limite]


def consistencia_semanal(sessoes: list[dict[str, Any]], meta_questoes_semana: int) -> dict[str, Any]:
    """IC = (dias_estudados/7) × min(1, questões_feitas/meta). §5."""
    sem = _sessoes_ultimos_dias(sessoes, 7)
    dias_estudados = len({_data_sessao(s) for s in sem})
    questoes = sum(int(s.get("questoes", 0) or 0) for s in sem)
    meta = max(1, meta_questoes_semana)
    ic = (dias_estudados / 7) * min(1.0, questoes / meta)
    if ic > 0.85:
        nivel = "EXCELENTE"
    elif ic >= 0.65:
        nivel = "ADEQUADA (monitorar)"
    else:
        nivel = "CRÍTICA (intervenção)"
    return {
        "ic": round(ic, 2),
        "nivel": nivel,
        "dias_estudados_7d": dias_estudados,
        "questoes_7d": questoes,
        "meta_semana": meta,
    }


def projecao_nota(historico_acerto: dict[str, Any], meta_acerto: float | None) -> dict[str, Any] | None:
    """Média ponderada dos acertos por categoria (§5). Renormaliza sobre as
    categorias com dados — projeção sobre o que foi medido."""
    if not historico_acerto:
        return None
    por_cat: dict[str, list[float]] = {}
    for disc, pct in historico_acerto.items():
        try:
            valor = float(pct)
        except (TypeError, ValueError):
            continue
        por_cat.setdefault(_categoria_de(disc), []).append(valor)
    if not por_cat:
        return None

    peso_total = sum(PESOS_CATEGORIA[c] for c in por_cat)
    nota = sum(
        (sum(v) / len(v)) * (PESOS_CATEGORIA[c] / peso_total)
        for c, v in por_cat.items()
    )
    detalhe = {
        NOMES_CATEGORIA[c]: round(sum(v) / len(v), 1) for c, v in por_cat.items()
    }
    res = {
        "nota_projetada": round(nota, 1),
        "cobertura_pct": round(peso_total * 100),
        "por_categoria": detalhe,
    }
    if meta_acerto:
        try:
            res["gap_para_meta"] = round(float(meta_acerto) - nota, 1)
        except (TypeError, ValueError):
            pass
    return res


def _barra(pct: float, larg: int = 20) -> str:
    cheio = max(0, min(larg, round(pct / 100 * larg)))
    return "█" * cheio + "░" * (larg - cheio)


def painel(perfil: dict[str, Any], sessoes: list[dict[str, Any]]) -> str:
    """Texto do [PAINEL_DE_CONTROLE] injetado no system prompt."""
    linhas = ["[PAINEL_DE_CONTROLE] (valores calculados — use-os, não recalcule)"]

    dias = dias_ate_prova(perfil)
    if dias is not None:
        marca = "" if dias > 14 else "  ⚠️ JANELA CURTA"
        linhas.append(f"• Dias até a prova: {dias}{marca}")

    streak = streak_de_sessoes(sessoes)
    if sessoes:
        linhas.append(f"• Streak atual: {streak} dia(s)")

    meta_q = int(perfil.get("meta_questoes_semana") or 200)
    if sessoes:
        ic = consistencia_semanal(sessoes, meta_q)
        linhas.append(
            f"• Consistência (7d): IC={ic['ic']} {ic['nivel']} "
            f"({ic['dias_estudados_7d']}/7 dias, {ic['questoes_7d']}/{ic['meta_semana']} questões)"
        )

    proj = projecao_nota(perfil.get("historico_acerto", {}), perfil.get("meta_operacional_acerto"))
    if proj:
        linhas.append(
            f"• Nota projetada: {proj['nota_projetada']}% "
            f"(cobre {proj['cobertura_pct']}% do peso da prova)"
        )
        for cat, pct in proj["por_categoria"].items():
            linhas.append(f"    {pct:>5.1f}% {_barra(pct)} {cat}")
        if "gap_para_meta" in proj:
            g = proj["gap_para_meta"]
            sinal = "faltam" if g > 0 else "acima da meta em"
            linhas.append(f"• Gap para a meta: {sinal} {abs(g)} pp")

    if len(linhas) == 1:
        return ""  # nada calculável ainda
    return "\n".join(linhas)


def exportar_html(perfil: dict[str, Any], sessoes: list[dict[str, Any]], destino: str | None = None) -> str:
    """Gera um relatório HTML completo e autossuficiente (sem dependências externas).

    Args:
        perfil: Dados do perfil do candidato.
        sessoes: Lista de sessões de estudo.
        destino: Caminho opcional para salvar o arquivo.

    Returns:
        Conteúdo HTML como string.
    """
    hoje = date.today().isoformat()
    sem = _sessoes_ultimos_dias(sessoes, 7)
    total_min = sum(int(s.get("minutos", 0) or 0) for s in sem)
    total_q = sum(int(s.get("questoes", 0) or 0) for s in sem)
    total_ac = sum(int(s.get("acertos", 0) or 0) for s in sem)
    pct = round(total_ac / total_q * 100, 1) if total_q else 0.0
    meta_q = int(perfil.get("meta_questoes_semana") or 200)
    ic = consistencia_semanal(sessoes, meta_q)
    proj = projecao_nota(perfil.get("historico_acerto", {}), perfil.get("meta_operacional_acerto"))
    dias = dias_ate_prova(perfil)
    streak = streak_de_sessoes(sessoes)

    # tabela de sessões
    linhas_sessao = ""
    if sem:
        for s in sorted(sem, key=lambda x: x.get("data", "")):
            q = int(s.get("questoes", 0) or 0)
            a = int(s.get("acertos", 0) or 0)
            ap = f"{round(a / q * 100)}%" if q else "—"
            cor = "#28a745" if q > 0 and a / q >= 0.7 else ("#ffc107" if a / q >= 0.5 else "#dc3545") if q > 0 else "#666"
            linhas_sessao += (
                f"<tr><td>{s.get('data', '?')}</td>"
                f"<td>{s.get('disciplina', '?')}</td>"
                f"<td>{s.get('minutos', 0)}</td>"
                f"<td>{q}</td>"
                f"<td style='color:{cor}'><b>{ap}</b></td>"
                f"<td>{s.get('erro_dominante', '—')}</td></tr>\n"
            )

    # gráfico de barras por categoria
    barras_cat = ""
    if proj:
        for cat, p in proj["por_categoria"].items():
            h = max(1, int(p * 2))
            cor = "#28a745" if p >= 70 else ("#ffc107" if p >= 50 else "#dc3545")
            barras_cat += (
                f"<div style='margin-bottom:8px'>"
                f"<div style='display:flex;justify-content:space-between'>"
                f"<span>{cat}</span><span>{p}%</span></div>"
                f"<div style='background:#eee;border-radius:4px;height:24px'>"
                f"<div style='background:{cor};width:{p}%;height:24px;border-radius:4px;"
                f"text-align:right;padding-right:4px;color:#fff;font-size:12px;"
                f"line-height:24px'>{p}%</div></div></div>\n"
            )
    # simulados
    html_simulados = ""
    try:
        import treino as _t
        sims = _t.carregar_simulados()
        if sims:
            html_simulados = "<h2>Simulados</h2>\n<table><tr><th>Data</th><th>Disciplina</th><th>Acertos</th><th>%</th></tr>\n"
            for s in sims[-10:]:
                p = s.get("pct", 0)
                cor = "#28a745" if p >= 70 else ("#ffc107" if p >= 50 else "#dc3545")
                html_simulados += (
                    f"<tr><td>{s['data']}</td><td>{s['disciplina']}</td>"
                    f"<td>{s['acertos']}/{s['questoes']}</td>"
                    f"<td style='color:{cor}'><b>{p}%</b></td></tr>\n"
                )
            html_simulados += "</table>\n"
    except ImportError:
        pass

    cor_nivel = "#28a745" if ic["nivel"].startswith("EXCELENTE") else (
        "#ffc107" if ic["nivel"].startswith("ADEQUADA") else "#dc3545"
    )
    nivel_rotulo = ic["nivel"].split(" ")[0]
    nivel_sub = " ".join(ic["nivel"].split(" ")[1:])

    bloco_proj = ""
    if proj:
        gap_cel = ""
        if "gap_para_meta" in proj:
            g = proj["gap_para_meta"]
            cor_gap = "#dc3545" if g > 0 else "#28a745"
            dir_gap = "acima" if g < 0 else "faltam"
            gap_cel = '<span style="color:' + cor_gap + '"><b>Gap: ' + str(abs(g)) + ' pp ' + dir_gap + '</b></span>'
        bloco_proj = (
            '<div class="stats"><div class="card"><div class="num">' + str(proj["nota_projetada"]) +
            '%</div><div class="label">Nota projetada (' + str(proj["cobertura_pct"]) +
            '% do peso)</div></div><div class="card">' + gap_cel + '</div></div>'
        )

    bloco_sessoes = (
        '<table><tr><th>Data</th><th>Disciplina</th><th>Min</th>'
        '<th>Questoes</th><th>Acerto</th><th>Erro</th></tr>\n' + linhas_sessao + '</table>'
    ) if sem else '<p style="color:#999">Nenhuma sessao nos ultimos 7 dias.</p>'

    dias_str = str(dias) if dias is not None else "—"
    cargo = perfil.get("cargo_alvo", "—")
    fase = perfil.get("fase_atual", "—")

    html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório AgentePetrobras — """ + hoje + """</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box }
  body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
         color:#333; max-width:900px; margin:0 auto; padding:20px }
  h1 { color:#1a5276; border-bottom:3px solid #1a5276; padding-bottom:8px }
  h2 { color:#2c3e50; margin-top:24px }
  .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
            gap:12px; margin:16px 0 }
  .card { background:#f8f9fa; border-radius:8px; padding:12px; text-align:center;
           border:1px solid #dee2e6 }
  .card .num { font-size:28px; font-weight:700; color:#1a5276 }
  .card .label { font-size:12px; color:#666; text-transform:uppercase }
  table { width:100%; border-collapse:collapse; margin:8px 0 }
  th,td { padding:8px 10px; text-align:left; border-bottom:1px solid #dee2e6 }
  th { background:#1a5276; color:#fff; font-size:13px }
  tr:hover { background:#f0f7ff }
  .nivel { display:inline-block; padding:2px 10px; border-radius:12px; font-size:13px;
           font-weight:600 }
  .footer { margin-top:32px; padding-top:16px; border-top:1px solid #dee2e6;
             font-size:12px; color:#999; text-align:center }
  @media print { .no-print { display:none } }
</style>
</head>
<body>
<h1>Relatório AgentePetrobras</h1>
<p style='color:#666'>""" + hoje + """ &middot; Cargo: <b>""" + cargo + """</b>
 &middot; Fase: <b>""" + fase + """</b></p>

<div class="stats">
  <div class="card"><div class="num">""" + dias_str + """</div>
    <div class="label">Dias ate a prova</div></div>
  <div class="card"><div class="num">""" + str(streak) + """d</div>
    <div class="label">Streak atual</div></div>
  <div class="card"><div class="num">""" + str(ic["dias_estudados_7d"]) + """/7</div>
    <div class="label">Dias estudados (7d)</div></div>
  <div class="card"><div class="num">""" + str(ic["questoes_7d"]) + """/""" + str(meta_q) + """</div>
    <div class="label">Questoes / meta</div></div>
</div>

<div class="stats">
  <div class="card"><div class="num">""" + str(total_min // 60) + """h""" + f"{total_min%60:02d}" + """</div>
    <div class="label">Tempo (7d)</div></div>
  <div class="card"><div class="num">""" + str(pct) + """%</div>
    <div class="label">Acerto (7d)</div></div>
  <div class="card"><div class="num">""" + str(ic["ic"]) + """</div>
    <div class="label">Indice de Consistencia</div></div>
  <div class="card">
    <span class="nivel" style="background:""" + cor_nivel + """;color:#fff">""" + nivel_rotulo + """</span>
    <div class="label">""" + nivel_sub + """</div>
  </div>
</div>

""" + bloco_proj + """

""" + barras_cat + """

<h2>Sessoes da semana</h2>
""" + bloco_sessoes + """

""" + html_simulados + """

<p class="footer">Gerado pelo AgentePetrobras v4.0 &mdash; <a href='#' onclick='window.print()'>Imprimir</a></p>
</body>
</html>"""

    if destino:
        Path(destino).write_text(html, encoding="utf-8")
        print("  ✓ Relatório HTML salvo em: " + destino)

    return html


def relatorio_semanal_md(perfil: dict[str, Any], sessoes: list[dict[str, Any]]) -> str:
    """Relatório semanal em Markdown (§16)."""
    hoje = date.today()
    sem = _sessoes_ultimos_dias(sessoes, 7)
    total_min = sum(int(s.get("minutos", 0) or 0) for s in sem)
    total_q = sum(int(s.get("questoes", 0) or 0) for s in sem)
    total_ac = sum(int(s.get("acertos", 0) or 0) for s in sem)
    pct = round(total_ac / total_q * 100, 1) if total_q else 0.0
    meta_q = int(perfil.get("meta_questoes_semana") or 200)
    ic = consistencia_semanal(sessoes, meta_q)
    proj = projecao_nota(perfil.get("historico_acerto", {}), perfil.get("meta_operacional_acerto"))
    dias = dias_ate_prova(perfil)

    out = [
        "# Relatório Semanal — AgentePetrobras v4.0",
        f"_Gerado em {hoje.isoformat()}_  ·  Cargo: **{perfil.get('cargo_alvo', '—')}**"
        f"  ·  Fase: **{perfil.get('fase_atual', '—')}**",
        "",
        "## Esta semana",
        f"- Tempo estudado: **{total_min // 60}h{total_min % 60:02d}min**",
        f"- Questões: **{total_q}** (meta {meta_q}) — acerto **{pct}%**",
        f"- Dias estudados: **{ic['dias_estudados_7d']}/7**  ·  Streak: **{streak_de_sessoes(sessoes)}d**",
        f"- Índice de Consistência: **{ic['ic']} — {ic['nivel']}**",
    ]
    if dias is not None:
        out.append(f"- Dias até a prova: **{dias}**")
    if proj:
        out += [
            "",
            "## Projeção de nota",
            f"- Nota projetada: **{proj['nota_projetada']}%** (cobre {proj['cobertura_pct']}% do peso)",
        ]
        for cat, p in proj["por_categoria"].items():
            out.append(f"  - {cat}: {p}%")
        if "gap_para_meta" in proj:
            out.append(f"- Gap para a meta: **{proj['gap_para_meta']} pp**")

    out += ["", "## Sessões da semana"]
    if sem:
        out.append("| Data | Disciplina | Min | Questões | Acerto | Erro dom. |")
        out.append("|---|---|---:|---:|---:|:---:|")
        for s in sorted(sem, key=lambda x: x.get("data", "")):
            q = int(s.get("questoes", 0) or 0)
            a = int(s.get("acertos", 0) or 0)
            ap = f"{round(a / q * 100)}%" if q else "—"
            out.append(
                f"| {s.get('data', '?')} | {s.get('disciplina', '?')} | "
                f"{s.get('minutos', 0)} | {q} | {ap} | {s.get('erro_dominante', '—')} |"
            )
    else:
        out.append("_Sem sessões registradas nos últimos 7 dias._")

    return "\n".join(out) + "\n"
