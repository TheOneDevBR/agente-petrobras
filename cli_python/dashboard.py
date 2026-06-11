"""Dashboard web — Streamlit.

Uso:
    streamlit run cli_python/dashboard.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metricas import (
    consistencia_semanal,
    dias_ate_prova,
    painel,
    projecao_nota,
    streak_de_sessoes,
)

# ── Caminhos ─────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
DADOS = BASE / "dados"
PERFIL_PATH = DADOS / "perfil_candidato.json"
SESSOES_PATH = DADOS / "sessoes.json"
HIST_PATH = DADOS / "historico_conversa.json"
RELATORIOS_DIR = DADOS / "relatorios"
VAULT = Path(__file__).resolve().parent.parent / "Obsidian_Vault" / "Petrobras"
PASTA_INTEL = VAULT / "Inteligencia"
MOC_PATH = VAULT / "_RESUMO_INTEL.md"


# ── Helpers ──────────────────────────────────────────────────────────────────
def _ler_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default
    return default


# ── Página ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AgentePetrobras",
    page_icon="📊",
    layout="wide",
)

st.title("📊 AgentePetrobras — Dashboard")
st.caption(f"Atualizado em {datetime.now():%d/%m/%Y %H:%M}")

perfil = _ler_json(PERFIL_PATH, {})
sessoes = _ler_json(SESSOES_PATH, [])
historico = _ler_json(HIST_PATH, [])

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("👤 Perfil")
    cargo = perfil.get("cargo_alvo") or "—"
    st.metric("Cargo", cargo)
    fase = perfil.get("fase_atual") or "—"
    st.metric("Fase", fase)
    questoes = perfil.get("questoes_resolvidas", 0)
    st.metric("Questões resolvidas", questoes)
    horas = perfil.get("horas_acumuladas", 0)
    st.metric("Horas acumuladas", f"{horas:.1f}h")

    st.divider()
    st.header("📅 Prova")
    dp = dias_ate_prova(perfil)
    if dp is not None:
        st.metric("Dias até a prova", dp, delta=-dp if dp > 0 else None)
    else:
        st.info("Data da prova não definida")

    st.divider()
    st.header("🔥 Streak")
    streak = streak_de_sessoes(sessoes)
    st.metric("Streak atual", f"{streak}d")

    st.divider()
    st.header("📁 Dados")
    st.caption(f"Sessões: {len(sessoes)}")
    st.caption(f"Histórico: {len(historico)} turnos")
    intel_files = list(PASTA_INTEL.glob("*.md")) if PASTA_INTEL.exists() else []
    st.caption(f"Notas de inteligência: {len(intel_files)}")

# ── Painel de Controle ───────────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("📋 Painel de Controle")
    pnl = painel(perfil, sessoes)
    if pnl:
        st.code(pnl, language="markdown")
    else:
        st.info("Sem dados suficientes. Defina a data da prova e registre sessões com /sessao.")

# ── Métricas em cards ────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

meta_q = int(perfil.get("meta_questoes_semana") or 200)
ic = consistencia_semanal(sessoes, meta_q) if sessoes else None

with col1:
    st.subheader("📈 Consistência")
    if ic:
        st.metric("IC (7d)", f"{ic['ic']:.2f}")
        st.caption(f"{ic['nivel']} — {ic['dias_estudados_7d']}/7 dias, {ic['questoes_7d']} questões")
    else:
        st.info("Nenhuma sessão registrada")

with col2:
    st.subheader("🎯 Projeção de Nota")
    hist = perfil.get("historico_acerto", {})
    meta_acerto = perfil.get("meta_operacional_acerto")
    proj = projecao_nota(hist, meta_acerto) if hist else None
    if proj:
        st.metric("Nota projetada", f"{proj['nota_projetada']}%")
        st.caption(f"Cobertura: {proj['cobertura_pct']}% do peso")
        if "gap_para_meta" in proj:
            st.metric("Gap para meta", f"{proj['gap_para_meta']:+.1f} pp")
        for cat, pct in proj["por_categoria"].items():
            st.caption(f"{cat}: {pct}%")
    else:
        st.info("Sem dados de acerto ainda")

with col3:
    st.subheader("📚 Sessões (7d)")
    if sessoes:
        hoje = date.today()
        recentes = [s for s in sessoes
                    if (d := s.get("data")) and abs((date.fromisoformat(d) - hoje).days) <= 7]
        st.metric("Sessões na semana", len(recentes))
        total_min = sum(int(s.get("minutos", 0) or 0) for s in recentes)
        st.caption(f"{total_min // 60}h{total_min % 60:02d}min na semana")
    else:
        st.info("Nenhuma sessão")

# ── Gráficos ─────────────────────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("📊 Gráficos")

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        if proj and proj.get("por_categoria"):
            cats = list(proj["por_categoria"].keys())
            vals = list(proj["por_categoria"].values())
            fig = go.Figure(data=[
                go.Bar(x=vals, y=cats, orientation="h",
                       marker_color=["#2ecc71" if v >= 70 else "#f39c12" if v >= 50 else "#e74c3c" for v in vals],
                       text=[f"{v}%" for v in vals], textposition="outside")
            ])
            fig.update_layout(title="Projeção por Categoria", xaxis_title="% Acerto",
                              height=250, margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados de projeção para exibir")

    with col_g2:
        if sessoes:
            dias = Counter(s.get("data", "?") for s in sessoes)
            sorted_dias = sorted(dias.items())
            if len(sorted_dias) > 1:
                fig = go.Figure(data=[
                    go.Scatter(x=[d for d, _ in sorted_dias],
                               y=[c for _, c in sorted_dias],
                               mode="lines+markers",
                               line=dict(color="#3498db", width=2),
                               fill="tozeroy", fillcolor="rgba(52,152,219,0.1)")
                ])
                fig.update_layout(title="Sessões por Dia", xaxis_title="Data",
                                  yaxis_title="Sessões", height=250,
                                  margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Uma data apenas — registre mais sessões para ver o gráfico")
        else:
            st.info("Nenhuma sessão registrada")

    if ic and dp is not None:
        col_g3, col_g4 = st.columns(2)
        with col_g3:
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=ic["ic"],
                delta={"reference": 0.65},
                gauge={"axis": {"range": [0, 1]},
                       "bar": {"color": "#2ecc71" if ic["ic"] >= 0.85 else "#f39c12" if ic["ic"] >= 0.65 else "#e74c3c"},
                       "steps": [
                           {"range": [0, 0.65], "color": "#fce4e4"},
                           {"range": [0.65, 0.85], "color": "#fef3cd"},
                           {"range": [0.85, 1], "color": "#d4edda"},
                       ],
                       "threshold": {"line": {"color": "red", "width": 2}, "value": 0.65}},
                title={"text": "Índice de Consistência"}
            ))
            fig.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)
        with col_g4:
            fig = go.Figure(go.Indicator(
                mode="number+delta",
                value=dp,
                delta={"reference": 0, "increasing": {"color": "red"}, "decreasing": {"color": "green"}},
                title={"text": "Dias até a Prova"}
            ))
            fig.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)

# ── Sessões recentes ─────────────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("📋 Últimas Sessões")
    if sessoes:
        sorted_sessoes = sorted(sessoes, key=lambda s: s.get("data", ""), reverse=True)[:20]
        data = []
        for s in sorted_sessoes:
            q = int(s.get("questoes", 0) or 0)
            a = int(s.get("acertos", 0) or 0)
            ap = f"{round(a / q * 100)}%" if q else "—"
            data.append({
                "Data": s.get("data", "?"),
                "Disciplina": s.get("disciplina", "?"),
                "Min": s.get("minutos", 0),
                "Questões": q,
                "Acertos": f"{a}/{q}" if q else "—",
                "%": ap,
                "Erro": s.get("erro_dominante", "—"),
            })
        st.dataframe(data, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma sessão registrada ainda. Use /sessao no agente.")

# ── Inteligência ─────────────────────────────────────────────────────────────
with st.container(border=True):
    st.subheader("🔍 Inteligência Recolhida")
    if MOC_PATH.exists():
        moc = MOC_PATH.read_text(encoding="utf-8")
        st.markdown(moc[:2000] + ("..." if len(moc) > 2000 else ""))
    else:
        st.info("Nenhuma coleta de inteligência disponível. Execute o coletor.")

    if intel_files:
        with st.expander(f"Notas detalhadas ({len(intel_files)})"):
            for f in sorted(intel_files, reverse=True)[:10]:
                nome = f.stem.replace("-", " ").title()
                with st.container(border=True):
                    st.caption(f"{f.stem}")
                    try:
                        texto = f.read_text(encoding="utf-8")
                        st.markdown(texto[:500] + ("..." if len(texto) > 500 else ""))
                    except Exception:
                        st.warning("Não foi possível ler o arquivo")

# ── Histórico da conversa ────────────────────────────────────────────────────
with st.expander("💬 Histórico da Conversa"):
    if historico:
        for msg in historico[-20:]:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            label = "🧑 **Você**" if role == "user" else "🤖 **Agente**"
            st.markdown(f"{label}: {content[:300]}{'...' if len(content) > 300 else ''}")
            st.divider()
    else:
        st.info("Nenhum histórico de conversa.")

# ── Relatórios ───────────────────────────────────────────────────────────────
if RELATORIOS_DIR.exists():
    rels = list(RELATORIOS_DIR.glob("*.md"))
    if rels:
        with st.expander("📄 Relatórios Semanais"):
            for r in sorted(rels, reverse=True):
                with st.container(border=True):
                    st.caption(r.name)
                    st.markdown(r.read_text(encoding="utf-8"))
