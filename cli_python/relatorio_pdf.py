"""Relatório PDF de desempenho formatado.

Gera um PDF com:
- Capa com dados do candidato
- Estatísticas gerais (nota projetada, IC, gap, probabilidade)
- Gráfico de desempenho por disciplina
- Tabela de simulados recentes
- Análise de erros C/A/B/T
- Recomendações personalizadas

Dependências:
    pip install matplotlib reportlab
"""

from __future__ import annotations

import io
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"


def _ler_json(nome: str) -> Any:
    from db import db_ler_json
    return db_ler_json(DADOS / nome)


def gerar_relatorio(
    caminho_saida: str | Path | None = None,
    perfil: dict | None = None,
    sessoes: list[dict] | None = None,
    simulados: list[dict] | None = None,
    metricas: dict | None = None,
    erro_cabt: dict | None = None,
    coaching_elo: dict | None = None,
) -> bytes:
    """Gera PDF de relatório de desempenho. Retorna bytes do PDF."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Drawing

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
    )
    estilos = getSampleStyleSheet()
    estilo_titulo = estilos["Title"]
    estilo_normal = estilos["Normal"]
    estilo_cabecalho = estilos["Heading2"]
    estilo_cabecalho3 = estilos["Heading3"]

    elementos: list = []

    # ── Capa ──
    elementos.append(Spacer(1, 5 * cm))
    elementos.append(Paragraph("Relatório de Desempenho", estilo_titulo))
    elementos.append(Spacer(1, 0.5 * cm))
    elementos.append(Paragraph(
        f"AgentePetrobras — {date.today().strftime('%d/%m/%Y')}",
        estilo_normal,
    ))
    if perfil:
        cargo = perfil.get("cargo_alvo") or "Não definido"
        elementos.append(Spacer(1, 1 * cm))
        elementos.append(Paragraph(f"Cargo: <b>{cargo}</b>", estilo_normal))
        elementos.append(Paragraph(
            f"Fase: {perfil.get('fase_atual', '—')}  |  "
            f"Streak: {perfil.get('streak_dias', 0)} dias",
            estilo_normal,
        ))
    elementos.append(Spacer(1, 2 * cm))
    elementos.append(Paragraph(
        "Sistema autoevolutivo de preparação para concursos da Petrobras",
        ParagraphStyle("Legenda", parent=estilo_normal, fontSize=9, textColor=colors.gray),
    ))
    elementos.append(PageBreak())

    # ── Estatísticas Gerais ──
    elementos.append(Paragraph("1. Estatísticas Gerais", estilo_cabecalho))
    elementos.append(Spacer(1, 0.3 * cm))

    stats_data = []
    if perfil:
        meta = perfil.get("meta_e_calibração") or perfil
        proj = perfil.get("projecao_nota") or meta.get("meta_operacional_acerto", "—")
        prob = meta.get("probabilidade_aprovacao", meta.get("probabilidade_estimada_aprovação", "—"))
        corte = meta.get("nota_corte_estimada", meta.get("nota_corte_estimada_do_cargo", "—"))
        stats_data.extend([
            ["Nota projetada", str(proj) + "%"],
            ["Nota de corte", str(corte)],
            ["Meta operacional", str(meta.get("meta_operacional_acerto", meta.get("meta_operacional_de_acerto", "—"))) + "%"],
            ["Prob. aprovação", str(prob) + "%"],
            ["Dias até prova", str(perfil.get("total_dias_ate_prova", "—"))],
            ["Streak atual", str(perfil.get("streak_dias", perfil.get("estado_psicológico_e_motivacional", {}).get("streak_dias_consecutivos", 0))) + " dias"],
        ])

    if stats_data:
        t = Table(
            [[Paragraph(k, estilo_normal), Paragraph(f"<b>{v}</b>", estilo_normal)]
             for k, v in stats_data],
            colWidths=[8 * cm, 5 * cm],
        )
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        elementos.append(t)

    # ── Desempenho por disciplina ──
    if coaching_elo and coaching_elo.get("habilidades"):
        elementos.append(Spacer(1, 0.5 * cm))
        elementos.append(Paragraph("2. Mapa de Maestria (Elo)", estilo_cabecalho))
        elementos.append(Spacer(1, 0.3 * cm))

        habs = sorted(
            coaching_elo["habilidades"].items(),
            key=lambda x: x[1], reverse=True,
        )
        elo_data = [["Disciplina", "Rating Elo", "Nível", "Respostas"]]
        for disc, rating in habs:
            n_resp = (coaching_elo.get("n_respostas") or {}).get(disc, 0)
            nivel = (
                "Domínio" if rating >= 1300 else
                "Avançado" if rating >= 1150 else
                "Intermediário" if rating >= 1000 else
                "Em desenvolvimento" if rating >= 850 else
                "Iniciante"
            )
            elo_data.append([disc, f"{rating:.0f}", nivel, str(n_resp)])

        t = Table(elo_data, colWidths=[5 * cm, 3 * cm, 4 * cm, 3 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        elementos.append(t)

    # ── Simulados Recentes ──
    if simulados:
        elementos.append(Spacer(1, 0.5 * cm))
        elementos.append(Paragraph("3. Últimos Simulados", estilo_cabecalho))
        elementos.append(Spacer(1, 0.3 * cm))

        sim_data = [["Data", "Ques.", "Acertos", "%", "Disciplina"]]
        for s in simulados[-10:]:
            data = s.get("data", "")[:10]
            q = str(s.get("questoes", 0))
            a = str(s.get("acertos", 0))
            p = f"{s.get('pct', 0):.0f}%"
            disc = s.get("disciplina", "Geral")[:20]
            sim_data.append([data, q, a, p, disc])

        t = Table(sim_data, colWidths=[3.5 * cm, 2 * cm, 2 * cm, 2 * cm, 5.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        elementos.append(t)

    # ── Análise de Erros C/A/B/T ──
    if erro_cabt:
        elementos.append(Spacer(1, 0.5 * cm))
        elementos.append(Paragraph("4. Análise de Erros (C/A/B/T)", estilo_cabecalho))
        elementos.append(Spacer(1, 0.3 * cm))

        rotulos = {
            "C": "Conteúdo",
            "A": "Atenção",
            "B": "Banca",
            "T": "Tempo",
        }
        contagem = erro_cabt.get("contagem", {})
        total_erros = sum(contagem.values()) or 1
        cabt_data = [["Categoria", "Ocorrências", "%"]]
        for cat in ["C", "A", "B", "T"]:
            val = contagem.get(cat, 0)
            pct = val / total_erros * 100
            cabt_data.append([rotulos.get(cat, cat), str(val), f"{pct:.0f}%"])

        t = Table(cabt_data, colWidths=[5 * cm, 4 * cm, 4 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        elementos.append(t)

    # ── Recomendações ──
    elementos.append(Spacer(1, 0.5 * cm))
    elementos.append(Paragraph("5. Recomendações", estilo_cabecalho))
    elementos.append(Spacer(1, 0.3 * cm))

    recomendacoes = [
        "Mantenha a consistência — o Índice de Consistência (IC) é o maior preditor de aprovação.",
    ]
    if erro_cabt:
        cats = sorted(contagem.items(), key=lambda x: x[1], reverse=True)
        if cats:
            pior_cat = cats[0][0]
            dicas = {
                "C": "Revise a teoria com RAG + flashcards. Foque nos conceitos que mais erra.",
                "A": "Treine com questões em ambiente cronometrado. Leia cada enunciado duas vezes.",
                "B": "Estude o estilo da CESGRANRIO: marque a mais CERTA, não a perfeita.",
                "T": "Pratique simulados completos. Gerencie o tempo por questão (2 min/Q).",
            }
            recomendacoes.append(f"Erro dominante: <b>{rotulos.get(pior_cat, pior_cat)}</b>. {dicas.get(pior_cat, '')}")

    # Piores disciplinas
    if coaching_elo and coaching_elo.get("habilidades"):
        sorted_habs = sorted(coaching_elo["habilidades"].items(), key=lambda x: x[1])
        piores = sorted_habs[:3]
        if piores:
            recomendacoes.append(
                "Disciplinas prioritárias: " +
                ", ".join(f"<b>{d}</b> ({r:.0f})" for d, r in piores)
            )

    for r in recomendacoes:
        elementos.append(Paragraph(f"• {r}", estilo_normal))
        elementos.append(Spacer(1, 0.2 * cm))

    doc.build(elementos)
    pdf_bytes = buf.getvalue()
    buf.close()

    if caminho_saida:
        Path(caminho_saida).write_bytes(pdf_bytes)

    return pdf_bytes


def gerar_e_salvar(caminho: str | None = None) -> str:
    """Gera relatório e salva em arquivo. Retorna caminho."""
    saida = Path(caminho or DADOS / "relatorios" / f"relatorio_{date.today().isoformat()}.pdf")
    saida.parent.mkdir(parents=True, exist_ok=True)

    gerar_relatorio(
        caminho_saida=saida,
        perfil=_ler_json("perfil_candidato.json"),
        sessoes=_ler_json("sessoes.json"),
        simulados=_ler_json("simulados.json"),
        erro_cabt=_ler_json("erros_cabt.json"),
        coaching_elo=_ler_json("coaching_elo.json"),
    )
    return str(saida)


def PageBreak():
    from reportlab.platypus import PageBreak as _PB
    return _PB()


if __name__ == "__main__":
    import sys
    caminho = gerar_e_salvar(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"Relatório gerado: {caminho}")
