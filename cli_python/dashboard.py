"""Dashboard web — Streamlit.

Uso:
    streamlit run cli_python/dashboard.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date, datetime
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


def _ler_json(path: Path, default):
    from db import db_ler_json
    return db_ler_json(path, default=default)


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
SIMULADOS_PATH = DADOS / "simulados.json"
simulados = _ler_json(SIMULADOS_PATH, [])

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

# ── Inicializa estado do simulado ──────────────────────────────────
if "simulado_idx" not in st.session_state:
    st.session_state.simulado_idx = 0
    st.session_state.simulado_acertos = 0
    st.session_state.simulado_total = 0
    st.session_state.simulado_questoes = []
    st.session_state.simulado_respostas = []
    st.session_state.simulado_concluido = False
    st.session_state.simulado_respondido = False

# ── Abas ────────────────────────────────────────────────────────────
tab_crono, tab_simulado, tab_risco, tab_provas, tab_evolucao, tab_principal = st.tabs([
    "📅 Cronograma", "🎯 Simulado", "🎲 Risco", "📄 Provas", "🧬 Evolução", "📊 Principal"
])

with tab_crono:
    st.subheader("📅 Cronograma Semanal de Estudos")
    try:
        from agendador import formatar_cronograma, gerar_cronograma
        cronograma = gerar_cronograma(perfil, sessoes, simulados)
        st.markdown(formatar_cronograma(cronograma))
    except Exception as e:
        st.info(f"Cronograma indisponível: {e}")

with tab_simulado:
    st.subheader("🎯 Simulado Interativo")
    try:
        from treino import BANCO_QUESTOES, selecionar_questoes
    except Exception:
        st.error("Banco de questões não disponível")
        BANCO_QUESTOES = []

    if not BANCO_QUESTOES:
        st.info("Nenhuma questão cadastrada no banco.")
    elif st.session_state.simulado_concluido:
        qtd = st.session_state.simulado_total
        acertos = st.session_state.simulado_acertos
        pct = round(acertos / qtd * 100, 1) if qtd else 0
        st.success(f"**Resultado:** {acertos}/{qtd} ({pct}%)")
        col1, col2 = st.columns(2)
        with col1:
            for i, q in enumerate(st.session_state.simulado_questoes):
                resp = st.session_state.simulado_respostas[i]
                face = "✅" if resp["acertou"] else "❌"
                with st.expander(f"{face} {q.pergunta[:60]}..."):
                    st.write(f"**Disciplina:** {q.disciplina}")
                    st.write(f"**Sua resposta:** {resp['escolha']}) {q.opcoes[resp['escolha']]}")
                    st.write(f"**Correta:** {q.correta}) {q.opcoes[q.correta]}")
                    st.write(f"**{q.explicacao}**")
        with col2:
            st.metric("Aproveitamento", f"{pct}%")
            st.metric("Acertos", acertos)
            st.metric("Erros", qtd - acertos)
        if st.button("🔄 Novo Simulado", use_container_width=True):
            st.session_state.simulado_idx = 0
            st.session_state.simulado_acertos = 0
            st.session_state.simulado_total = 0
            st.session_state.simulado_questoes = []
            st.session_state.simulado_respostas = []
            st.session_state.simulado_concluido = False
            st.session_state.simulado_respondido = False
            st.rerun()
    elif not st.session_state.simulado_questoes:
        with st.form("config_simulado"):
            col_q, col_d = st.columns(2)
            with col_q:
                n = st.number_input("Número de questões", 1, 50, 5)
            with col_d:
                disciplinas = sorted(set(q.disciplina for q in BANCO_QUESTOES))
                disc = st.selectbox("Disciplina", ["Todas"] + disciplinas)
            if st.form_submit_button("🎯 Iniciar Simulado", use_container_width=True, type="primary"):
                st.session_state.simulado_questoes = selecionar_questoes(
                    n, disciplina="" if disc == "Todas" else disc
                )
                st.session_state.simulado_idx = 0
                st.session_state.simulado_acertos = 0
                st.session_state.simulado_total = len(st.session_state.simulado_questoes)
                st.session_state.simulado_respostas = []
                st.session_state.simulado_concluido = False
                st.session_state.simulado_respondido = False
                st.rerun()
    else:
        questoes = st.session_state.simulado_questoes
        idx = st.session_state.simulado_idx
        if idx < len(questoes):
            q = questoes[idx]
            st.progress((idx) / len(questoes), text=f"Questão {idx+1} de {len(questoes)}")
            st.markdown(f"**{q.pergunta}**")
            st.caption(f"Disciplina: {q.disciplina}")

            if st.session_state.simulado_respondido:
                resp = st.session_state.simulado_respostas[-1]
                if resp["acertou"]:
                    st.success("✅ Correto!")
                else:
                    st.error(f"❌ Incorreto. Resposta: {q.correta}) {q.opcoes[q.correta]}")
                st.info(f"📖 {q.explicacao}")
                if st.button("Próxima →", use_container_width=True, type="primary"):
                    st.session_state.simulado_idx += 1
                    st.session_state.simulado_respondido = False
                    st.rerun()
            else:
                with st.form("resposta"):
                    escolha = st.radio("Selecione sua resposta:", list(enumerate(q.opcoes)), format_func=lambda x: f"{x[0]}) {x[1]}")
                    if st.form_submit_button("Responder", use_container_width=True, type="primary"):
                        escolha_idx = escolha[0]
                        correta = escolha_idx == q.correta
                        if correta:
                            st.session_state.simulado_acertos += 1
                        st.session_state.simulado_respostas.append({
                            "escolha": escolha_idx, "acertou": correta
                        })
                        st.session_state.simulado_respondido = True
                        st.rerun()
        else:
            st.session_state.simulado_concluido = True
            st.rerun()

with tab_risco:
    st.subheader("🎲 Análise de Risco — Monte Carlo")
    try:
        from risco_monte_carlo import formatar_relatorio, simular_aprovacao
        with st.spinner("Simulando 5.000 cenários..."):
            resultado = simular_aprovacao(perfil, sessoes, simulados, n_cenarios=5000)
        if resultado.n_cenarios == 0:
            st.info("Sem dados suficientes. Registre sessões e simulados primeiro.")
        else:
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Prob. Aprovação", f"{resultado.prob_aprovacao}%",
                          delta=f"{resultado.aprovacoes}/{resultado.n_cenarios}")
            with col_r2:
                st.metric("Nota Média", f"{resultado.nota_media:.1f}",
                          delta=f"Corte: {resultado.nota_corte:.0f}")
            with col_r3:
                st.metric("IC 90%", f"[{resultado.intervalo_confianca_90[0]}, {resultado.intervalo_confianca_90[1]}]")

            import plotly.graph_objects as go
            bins = list(range(0, 101, 5))
            hist = [sum(1 for n in resultado.notas if lo <= n < lo+5) for lo in bins[:-1]]
            fig = go.Figure(data=[
                go.Bar(x=[f"{lo}-{lo+4}" for lo in bins[:-1]], y=hist,
                       marker_color=["#2ecc71" if lo+5 >= resultado.nota_corte else "#e74c3c" for lo in bins[:-1]])
            ])
            fig.add_vline(x=resultado.nota_corte/5, line_dash="dash", line_color="green",
                          annotation_text=f"Corte {resultado.nota_corte:.0f}")
            fig.update_layout(title="Distribuição das Notas Simuladas", height=300,
                              margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Relatório detalhado"):
                st.markdown(formatar_relatorio(resultado))
    except Exception as e:
        st.info(f"Simulação indisponível: {e}")

with tab_provas:
    st.subheader("📄 Provas Extraídas")
    provas_dir = DADOS / "provas_extraidas" if hasattr(DADOS, 'parent') else Path("dados/provas_extraidas")
    if hasattr(DADOS, '__truediv__'):
        provas_dir = DADOS / "provas_extraidas"
    else:
        provas_dir = BASE / "dados" / "provas_extraidas"
    if provas_dir.exists():
        provas = list(provas_dir.glob("*.md"))
        if provas:
            st.caption(f"{len(provas)} prova(s) extraída(s)")
            for p in sorted(provas, reverse=True)[:10]:
                with st.expander(p.stem):
                    st.markdown(p.read_text(encoding="utf-8")[:2000])
        else:
            st.info("Nenhuma prova extraída ainda. Use extrair_provas_pdf.py")
    else:
        provas_pdf_dir = BASE / "provas_baixadas"
        pdfs = list(provas_pdf_dir.glob("*.pdf")) if provas_pdf_dir.exists() else []
        st.info(f"Nenhuma prova extraída. {len(pdfs)} PDF(s) aguardando extração.")

with tab_evolucao:
    st.subheader("🧬 Painel de Autoevolução do Agente")

    diario_data = _ler_json(DADOS / "evolucao" / "diario.json", {})
    experimentos_data = _ler_json(DADOS / "evolucao" / "experimentos.json", {})
    auto_aval_data = _ler_json(DADOS / "evolucao" / "auto_avaliacao.json", {})

    decisoes = diario_data.get("decisoes", [])
    estrategias_ranking = diario_data.get("estrategias_ranking", {})
    experimentos = experimentos_data.get("experimentos", [])
    avaliacoes = auto_aval_data.get("avaliacoes", [])

    if not decisoes and not avaliacoes and not experimentos:
        st.info("Nenhum dado de autoevolução registrado ainda. Realize sessões de estudo e ciclos evolutivos para gerar dados.")
    else:
        col_e1, col_e2, col_e3, col_e4 = st.columns(4)
        
        com_outcome = [d for d in decisoes if d.get("outcome_real") is not None]
        if com_outcome:
            eficacia_global = sum(float(d.get("eficacia", 0.0) or 0.0) for d in com_outcome) / len(com_outcome)
            eficacia_pct = f"{round(eficacia_global * 100)}%"
        else:
            eficacia_pct = "—"

        with col_e1:
            st.metric("Decisões Registradas", len(decisoes))
        with col_e2:
            st.metric("Com Outcome", len(com_outcome))
        with col_e3:
            st.metric("Eficácia Global", eficacia_pct)
        with col_e4:
            score_medio = auto_aval_data.get("score_medio_7d", "—")
            if score_medio != "—":
                st.metric("Nota das Respostas (7d)", f"{score_medio}/100", delta=auto_aval_data.get("tendencia"))
            else:
                st.metric("Nota das Respostas (7d)", "—")

        st.divider()

        col_left, col_right = st.columns(2)

        with col_left:
            st.write("### 🏆 Ranking de Técnicas de Estudo")
            if estrategias_ranking:
                ranking_items = []
                for k, v in estrategias_ranking.items():
                    ranking_items.append({
                        "Estratégia": k.replace("_", " ").title(),
                        "Usos": v.get("usos", 0),
                        "Eficácia Média": round(float(v.get("eficacia_media", 0.0) or 0.0) * 100, 1)
                    })
                ranking_items.sort(key=lambda x: x["Eficácia Média"], reverse=True)

                fig_rank = go.Figure(data=[
                    go.Bar(
                        x=[x["Eficácia Média"] for x in ranking_items],
                        y=[x["Estratégia"] for x in ranking_items],
                        orientation="h",
                        marker_color=["#2ecc71" if x["Eficácia Média"] >= 70 else "#f39c12" if x["Eficácia Média"] >= 50 else "#e74c3c" for x in ranking_items],
                        text=[f"{x['Eficácia Média']}%" for x in ranking_items],
                        textposition="outside"
                    )
                ])
                fig_rank.update_layout(
                    xaxis_title="% Eficácia",
                    xaxis_range=[0, 110],
                    height=250,
                    margin=dict(l=10, r=10, t=10, b=10),
                    showlegend=False
                )
                st.plotly_chart(fig_rank, use_container_width=True)
            else:
                st.info("Sem ranking de estratégias disponível ainda.")

        with col_right:
            st.write("### 📈 Auto-avaliação do System Prompt (Tuning)")
            if avaliacoes:
                scores = [a.get("score_total", 0) for a in avaliacoes]
                timestamps = []
                for i, a in enumerate(avaliacoes):
                    ts = a.get("timestamp")
                    if ts:
                        try:
                            timestamps.append(datetime.fromisoformat(ts).strftime("%d/%m %H:%M"))
                        except Exception:
                            timestamps.append(f"Aval #{i+1}")
                    else:
                        timestamps.append(f"Aval #{i+1}")

                fig_aval = go.Figure(data=[
                    go.Scatter(
                        x=timestamps,
                        y=scores,
                        mode="lines+markers",
                        line=dict(color="#2ecc71", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(46, 204, 113, 0.1)"
                    )
                ])
                fig_aval.update_layout(
                    title="Evolução da Nota do Prompt",
                    yaxis_title="Score (0-100)",
                    yaxis_range=[0, 105],
                    height=180,
                    margin=dict(l=10, r=10, t=30, b=10)
                )
                st.plotly_chart(fig_aval, use_container_width=True)
            else:
                st.info("Nenhuma auto-avaliação registrada ainda.")

        if avaliacoes:
            with st.expander("Detalhamento por Dimensão de Auto-avaliação"):
                total_aval = len(avaliacoes)
                dims_sum = {"especificidade": 0, "evidencia": 0, "mensurabilidade": 0, "acao": 0, "budget": 0}
                for a in avaliacoes:
                    for d_k in dims_sum:
                        dims_sum[d_k] += a.get("dimensoes", {}).get(d_k, 0)

                dims_avg = {k.title(): round(v / total_aval) for k, v in dims_sum.items()}

                fig_dims = go.Figure(data=[
                    go.Bar(
                        x=list(dims_avg.values()),
                        y=list(dims_avg.keys()),
                        orientation="h",
                        marker_color="#3498db",
                        text=[f"{v}%" for v in dims_avg.values()],
                        textposition="outside"
                    )
                ])
                fig_dims.update_layout(
                    title="Desempenho Médio por Dimensão",
                    xaxis_range=[0, 110],
                    height=200,
                    margin=dict(l=10, r=10, t=30, b=10)
                )
                st.plotly_chart(fig_dims, use_container_width=True)

        st.write("### 🧪 Experimentos A/B Pedagógicos")
        if experimentos:
            for exp in experimentos:
                status_color = "🟢" if exp.get("status") == "ATIVO" else "🔴"
                with st.expander(f"{status_color} Experimento: {exp.get('hipotese')}"):
                    col_ab1, col_ab2 = st.columns(2)
                    with col_ab1:
                        st.markdown(f"**Condição:** {exp.get('condicao')}")
                        st.markdown(f"**Status:** {exp.get('status')}")
                        st.markdown(f"**Confiança:** {round(float(exp.get('confianca', 0.0) or 0.0) * 100, 1)}%")
                    with col_ab2:
                        grupo_a_size = len(exp.get("grupo_a", {}).get("resultados", []))
                        grupo_b_size = len(exp.get("grupo_b", {}).get("resultados", []))
                        st.markdown(f"**Grupo A ({exp.get('grupo_a', {}).get('estrategia')}):** {grupo_a_size} resultado(s)")
                        st.markdown(f"**Grupo B ({exp.get('grupo_b', {}).get('estrategia')}):** {grupo_b_size} resultado(s)")
                        if exp.get("vencedor"):
                            st.success(f"🏆 **Vencedor:** Grupo {exp.get('vencedor').upper()}")
        else:
            st.info("Nenhum experimento ativo no momento.")

        st.write("### 📅 Diário de Decisões e Outcomes")
        if decisoes:
            diario_df = []
            for d in reversed(decisoes):
                outcome = d.get("outcome_real")
                if outcome:
                    acerto_novo = outcome.get("acerto", 0.0)
                    delta = outcome.get("delta")
                    delta_str = f"{delta:+.1f}%" if delta is not None else "—"
                    res_outcome = f"{acerto_novo}% ({delta_str})"
                    eficacia = f"{round(float(d.get('eficacia', 0.0) or 0.0) * 100)}%"
                else:
                    res_outcome = "Aguardando outcome"
                    eficacia = "—"

                ts_raw = d.get("timestamp")
                ts_str = "—"
                if ts_raw:
                    try:
                        ts_str = datetime.fromisoformat(ts_raw).strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        ts_str = str(ts_raw)

                diario_df.append({
                    "Data/Hora": ts_str,
                    "Estratégia": d.get("estrategia", "").replace("_", " ").title(),
                    "Disciplina": d.get("disciplina", "").title(),
                    "Prescrição": d.get("prescricao", ""),
                    "Resultado": res_outcome,
                    "Eficácia": eficacia
                })
            st.dataframe(diario_df, use_container_width=True, hide_index=True)
        else:
            st.info("Diário de decisões vazio.")

    # ── Seção de Autonomia e Saúde do Sistema ──
    st.divider()
    st.subheader("🤖 Autonomia & Saúde do Sistema")

    # Botões de Ação
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        if st.button("🧬 Disparar Autoevolução (Qwen 7B)", use_container_width=True):
            with st.spinner("Executando ciclo evolutivo pedagógico via Qwen 7B (meta-tuning)..."):
                try:
                    from ciclo_evolutivo import executar_ciclo
                    from local_llm import LocalLLM
                    cliente_7b = LocalLLM(model="qwen2.5:7b")
                    resultado = executar_ciclo(cliente_llm=cliente_7b, evoluir_prompts=True, verbose=False)
                    st.success("Ciclo evolutivo concluído com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao executar ciclo: {e}")
                    
    with col_btn2:
        if st.button("⚙️ Executar Ciclo Autônomo", use_container_width=True):
            with st.spinner("Percebendo, agindo e curando..."):
                try:
                    from autonomia import ciclo_autonomo
                    resultado = ciclo_autonomo(permitir_sensiveis=False, aprender=True)
                    st.success("Ciclo autônomo concluído!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao executar autonomia: {e}")
                    
    with col_btn3:
        if st.button("📊 Atualizar Diagnóstico de Sistema", use_container_width=True):
            st.rerun()

    # Métricas de Saúde (Autodiagnóstico)
    try:
        from autonomia import autodiagnostico_completo, analisar_gaps, gerar_sugestoes_proativas
        info = autodiagnostico_completo()
        m = info.metricas

        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
        with col_s1:
            st.metric("Módulos Python", m.modulos_python)
        with col_s2:
            st.metric("Linhas de Código", m.linhas_codigo)
        with col_s3:
            st.metric("Classes / Funções", f"{m.classes} / {m.funcoes}")
        with col_s4:
            st.metric("Testes Coletados", m.testes_total)
        with col_s5:
            st.metric("Alertas de Saúde", m.alertas_saude, delta=-m.alertas_saude if m.alertas_saude > 0 else None, delta_color="inverse")

        col_gaps, col_sugs = st.columns(2)
        with col_gaps:
            st.write("### 🧭 Próximas Evoluções (Gaps)")
            gaps = analisar_gaps(info)
            if gaps:
                for g in gaps[:5]:
                    marca = "🔴" if g.impacto == "alto" else "🟡" if g.impacto == "medio" else "🟢"
                    st.markdown(f"{marca} **{g.nome}** — *Esforço: {g.esforco_estimado}*\n\n{g.descricao}")
            else:
                st.success("Nenhum gap evolutivo detectado! Sistema 100% atualizado.")

        with col_sugs:
            st.write("### 💡 Sugestões Proativas do Agente")
            sugestoes = gerar_sugestoes_proativas(info)
            if sugestoes:
                for s in sugestoes[:5]:
                    marca = "🔴" if s.urgencia == "alta" else "🟡" if s.urgencia == "media" else "🟢"
                    st.markdown(f"{marca} **{s.descricao}**")
                    if s.comando_sugerido:
                        st.code(s.comando_sugerido, language="powershell")
            else:
                st.info("Sem sugestões proativas pendentes no momento.")

    except Exception as e:
        st.info(f"Dados de autonomia indisponíveis temporariamente: {e}")

with tab_principal:
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

    # ── Gap Analysis ──────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("🎯 Análise de Gaps")

        gap_data = {}
        if proj and proj.get("por_categoria"):
            gap_data = {k: v for k, v in sorted(proj["por_categoria"].items(), key=lambda x: x[1])}
        elif simulados:
            disc_scores = {}
            for s in simulados:
                d = s.get("disciplina", "geral")
                disc_scores.setdefault(d, []).append(s["pct"])
            if disc_scores:
                gap_data = {d: round(sum(v)/len(v), 1) for d, v in sorted(disc_scores.items(), key=lambda x: sum(x[1])/len(x[1]))}

        if gap_data:
            bar_colors = ["#e74c3c" if v < 50 else "#f39c12" if v < 70 else "#2ecc71" for v in gap_data.values()]
            fig = go.Figure(data=[
                go.Bar(x=list(gap_data.values()), y=list(gap_data.keys()), orientation="h",
                       marker_color=bar_colors,
                       text=[f"{v}%" for v in gap_data.values()], textposition="outside")
            ])
            fig.update_layout(title="Desempenho por Disciplina (menor → maior)",
                              xaxis_title="% Acerto", xaxis_range=[0, 100],
                              height=300, margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
            fig.add_vline(x=70, line_dash="dash", line_color="green", opacity=0.5)
            fig.add_vline(x=50, line_dash="dash", line_color="red", opacity=0.5)
            st.plotly_chart(fig, use_container_width=True)

            worst = list(gap_data.keys())[0] if gap_data else "—"
            worst_pct = list(gap_data.values())[0] if gap_data else 0
            best = list(gap_data.keys())[-1] if gap_data else "—"
            st.caption(f"🔴 Prioritária: **{worst}** ({worst_pct}%) | 🟢 Mais forte: **{best}%**")
            st.caption("Meta: ≥70% em todas as disciplinas. Abaixo de 50% requer intervenção imediata.")
        else:
            st.info("Sem dados suficientes para análise de gaps. Registre sessões e simulados.")

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

    with st.container(border=True):
        st.subheader("📝 Histórico de Simulados")
        if simulados:
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                sorted_sim = sorted(simulados, key=lambda s: s.get("data", ""))
                if len(sorted_sim) > 1:
                    df_sim = [{"Data": s["data"], "Disciplina": s.get("disciplina", "geral"),
                               "%": s["pct"], "Acertos": f"{s['acertos']}/{s['questoes']}"}
                              for s in sorted_sim]
                    fig = px.line(df_sim, x="Data", y="%", color="Disciplina",
                                  markers=True, title="Evolução do Desempenho",
                                  range_y=[0, 100])
                    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Registre mais simulados para ver o gráfico de evolução")
            with col_s2:
                disc_avg = {}
                for s in simulados:
                    d = s.get("disciplina", "geral")
                    disc_avg.setdefault(d, []).append(s["pct"])
                if disc_avg:
                    fig = go.Figure(data=[
                        go.Bar(x=list(disc_avg.keys()), y=[sum(v)/len(v) for v in disc_avg.values()],
                               marker_color="#2ecc71",
                               text=[f"{sum(v)/len(v):.0f}%" for v in disc_avg.values()],
                               textposition="outside")
                    ])
                    fig.update_layout(title="Média por Disciplina", xaxis_title="Disciplina",
                                      yaxis_title="%", height=300,
                                      margin=dict(l=10, r=10, t=30, b=10), showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

            with st.expander("Tabela de Simulados"):
                table_data = [
                    {"Data": s.get("data", "?"), "Disciplina": s.get("disciplina", "?"),
                     "Questões": s.get("questoes", 0), "Acertos": f"{s['acertos']}/{s['questoes']}",
                     "%": f"{s['pct']}%"}
                    for s in sorted(simulados, key=lambda x: x.get("data", ""), reverse=True)
                ]
                st.dataframe(table_data, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum simulado realizado ainda. Use /simulado no agente.")

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
