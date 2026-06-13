"""Ciclo Evolutivo — Orquestrador de melhoria contínua.

Roda periodicamente (cron ou manual via /ciclo) e orquestra todas as
camadas de autoevolução: coleta dados, analisa eficácia, propõe
experimentos, evolui overlays e gera relatório.

Uso:
    python ciclo_evolutivo.py                # ciclo completo
    python ciclo_evolutivo.py --relatorio    # apenas relatório
    python ciclo_evolutivo.py --rollback estrategias  # rollback de overlay

    # No agente:
    from ciclo_evolutivo import executar_ciclo, relatorio_evolucao
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"
DADOS_EVOLUCAO = DADOS / "evolucao"
RELATORIOS_DIR = DADOS_EVOLUCAO / "relatorios"
PERFIL_PATH = DADOS / "perfil_candidato.json"
SESSOES_PATH = DADOS / "sessoes.json"


def _ler_json(caminho: Path, default: Any = None) -> Any:
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return default if default is not None else {}


def _carregar_perfil() -> dict:
    return _ler_json(PERFIL_PATH, {})


def _carregar_sessoes() -> list[dict]:
    return _ler_json(SESSOES_PATH, [])


def executar_ciclo(
    cliente_llm: Any | None = None,
    evoluir_prompts: bool = True,
    verbose: bool = True,
) -> dict[str, Any]:
    """Executa o ciclo completo de autoevolução.

    Etapas:
        1. COLETAR: Lê diário, outcomes, auto-avaliações
        2. ANALISAR: Calcula eficácia, detecta regressões
        3. EXPERIMENTAR: Propõe/atualiza A/B tests
        4. EVOLUIR: Reescreve overlays do prompt (se habilitado)
        5. VALIDAR: Verifica sanidade
        6. REPORTAR: Gera relatório

    Args:
        cliente_llm: Instância de LocalLLM (necessário para etapa 4).
        evoluir_prompts: Se True, roda a etapa 4 (auto-tuning de prompt).
        verbose: Se True, imprime progresso.

    Returns:
        Dict com resultados de cada etapa.
    """
    from evolucao import DiarioEvolucao
    from auto_avaliacao import AutoAvaliador
    from estrategia_ab import GerenciadorAB
    from prompt_evoluivel import PromptEvoluivel

    resultado = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "etapas": {},
        "sucesso": True,
    }

    perfil = _carregar_perfil()
    sessoes = _carregar_sessoes()

    if verbose:
        print("🔄 Ciclo evolutivo iniciado...\n")

    # ── Etapa 1: COLETAR ─────────────────────────────────────────────
    if verbose:
        print("  [1/6] Coletando dados...")

    diario = DiarioEvolucao()
    avaliador = AutoAvaliador()
    ab = GerenciadorAB()
    pe = PromptEvoluivel()

    stats_diario = diario.estatisticas()
    stats_avaliacao = avaliador.estatisticas()
    stats_ab = ab.estatisticas()
    stats_prompt = pe.estatisticas()

    resultado["etapas"]["coletar"] = {
        "decisoes": stats_diario["total_decisoes"],
        "outcomes": stats_diario["com_outcome"],
        "avaliacoes": stats_avaliacao["total"],
        "experimentos": stats_ab["total"],
    }

    if verbose:
        print(f"    {stats_diario['total_decisoes']} decisões, "
              f"{stats_diario['com_outcome']} com outcome, "
              f"{stats_avaliacao['total']} auto-avaliações")

    # ── Etapa 2: ANALISAR ────────────────────────────────────────────
    if verbose:
        print("  [2/6] Analisando eficácia...")

    ranking = diario.ranking_estrategias(10)
    regressao = avaliador.detectar_regressao()

    resultado["etapas"]["analisar"] = {
        "ranking_top3": [r["estrategia"] for r in ranking[:3]],
        "eficacia_global": stats_diario["eficacia_global"],
        "score_medio_respostas": stats_avaliacao.get("score_medio", 0),
        "regressao_detectada": regressao is not None,
    }

    if verbose:
        ef = stats_diario["eficacia_global"]
        sc = stats_avaliacao.get("score_medio", 0)
        print(f"    Eficácia global: {ef:.0%} | Score respostas: {sc}/100")
        if ranking:
            print(f"    Top estratégia: {ranking[0]['estrategia']} ({ranking[0]['eficacia_media']:.0%})")
        if regressao:
            print(f"    ⚠ {regressao['mensagem']}")

    # ── Etapa 3: EXPERIMENTAR ────────────────────────────────────────
    if verbose:
        print("  [3/6] Gerenciando experimentos A/B...")

    novo_exp = None
    if not ab.experimentos_ativos() and stats_diario["com_outcome"] >= 5:
        proposta = ab.propor_experimento_padrao(perfil)
        if proposta:
            exp_id = ab.criar_experimento(**proposta)
            novo_exp = {"id": exp_id, **proposta}
            if verbose:
                print(f"    ✓ Novo experimento criado: {proposta['hipotese']}")

    resultado["etapas"]["experimentar"] = {
        "ativos": stats_ab["ativos"],
        "concluidos": stats_ab["concluidos"],
        "novo_criado": novo_exp is not None,
    }

    if verbose and not novo_exp:
        ativos = ab.experimentos_ativos()
        if ativos:
            print(f"    Experimento ativo: {ativos[0].get('hipotese', '?')}")
        else:
            print("    Sem experimentos (dados insuficientes ou já concluídos)")

    # ── Etapa 4: EVOLUIR PROMPTS ─────────────────────────────────────
    overlays_evoluidos = []
    if evoluir_prompts and cliente_llm is not None:
        if verbose:
            print("  [4/6] Evoluindo overlays do prompt...")

        contexto = json.dumps(
            {k: v for k, v in perfil.items() if not k.startswith("_") and v is not None},
            ensure_ascii=False, indent=2
        )[:1500]

        # Evoluir overlay de estratégias se temos ranking
        if ranking and len(ranking) >= 2:
            ranking_txt = "\n".join(
                f"  {r['estrategia']}: eficácia {r['eficacia_media']:.0%} ({r['usos']} usos)"
                for r in ranking
            )
            ok, msg = pe.evoluir_overlay(
                "estrategias", cliente_llm, contexto,
                dados_extra={"ranking": ranking_txt},
            )
            if ok:
                overlays_evoluidos.append("estrategias")
            if verbose:
                print(f"    {'✓' if ok else '✗'} Estratégias: {msg}")

        # Evoluir overlay de prescrições se temos histórico
        hist = perfil.get("historico_acerto", {})
        if hist and len(hist) >= 2:
            hist_txt = json.dumps(hist, ensure_ascii=False, indent=2)
            ok, msg = pe.evoluir_overlay(
                "prescricoes", cliente_llm, contexto,
                dados_extra={"historico": hist_txt},
            )
            if ok:
                overlays_evoluidos.append("prescricoes")
            if verbose:
                print(f"    {'✓' if ok else '✗'} Prescrições: {msg}")

    elif verbose:
        print("  [4/6] Evolução de prompts desabilitada (sem LLM ou --no-evolve)")

    resultado["etapas"]["evoluir"] = {
        "overlays_evoluidos": overlays_evoluidos,
        "versoes": pe.estatisticas()["overlays"],
    }

    # ── Etapa 5: VALIDAR ─────────────────────────────────────────────
    if verbose:
        print("  [5/6] Validando sanidade...")

    valido = True
    for nome in overlays_evoluidos:
        conteudo = pe.ler_overlay(nome)
        ok, erro = pe.validar_overlay(nome, conteudo)
        if not ok:
            if verbose:
                print(f"    ⚠ Overlay '{nome}' inválido: {erro}. Fazendo rollback...")
            pe.rollback(nome)
            valido = False

    resultado["etapas"]["validar"] = {"valido": valido}
    if verbose:
        print(f"    {'✓ Todos os overlays válidos' if valido else '⚠ Rollback aplicado'}")

    # ── Etapa 6: REPORTAR ────────────────────────────────────────────
    if verbose:
        print("  [6/6] Gerando relatório...")

    relatorio = _gerar_relatorio(resultado, ranking, stats_diario, stats_avaliacao, stats_ab, stats_prompt)
    RELATORIOS_DIR.mkdir(parents=True, exist_ok=True)
    nome_rel = RELATORIOS_DIR / f"evolucao_{date.today().isoformat()}.md"
    nome_rel.write_text(relatorio, encoding="utf-8")

    resultado["relatorio_path"] = str(nome_rel)

    if verbose:
        print(f"\n✓ Ciclo concluído. Relatório: {nome_rel}")

    return resultado


def _gerar_relatorio(
    resultado: dict,
    ranking: list[dict],
    stats_diario: dict,
    stats_avaliacao: dict,
    stats_ab: dict,
    stats_prompt: dict,
) -> str:
    """Gera relatório markdown do ciclo evolutivo."""
    hoje = date.today().isoformat()
    linhas = [
        "# Relatório de Evolução — AgentePetrobras",
        f"_Gerado em {hoje}_",
        "",
        "## Resumo",
        "",
        f"- **Decisões registradas:** {stats_diario['total_decisoes']}",
        f"- **Com outcome:** {stats_diario['com_outcome']}",
        f"- **Eficácia global:** {stats_diario['eficacia_global']:.0%}",
        f"- **Score médio respostas:** {stats_avaliacao.get('score_medio', 0)}/100",
        f"- **Tendência qualidade:** {stats_avaliacao.get('tendencia', '?')}",
        f"- **Experimentos A/B:** {stats_ab['ativos']} ativos, {stats_ab['concluidos']} concluídos",
        "",
    ]

    if ranking:
        linhas += ["## Ranking de Estratégias", ""]
        linhas.append("| # | Estratégia | Eficácia | Usos |")
        linhas.append("|---|-----------|---------|------|")
        for i, r in enumerate(ranking, 1):
            ef = r.get("eficacia_media", 0)
            emoji = "🟢" if ef >= 0.7 else ("🟡" if ef >= 0.5 else "🔴")
            linhas.append(f"| {i} | {emoji} {r['estrategia']} | {ef:.0%} | {r['usos']} |")
        linhas.append("")

    etapas = resultado.get("etapas", {})
    evoluir = etapas.get("evoluir", {})
    if evoluir.get("overlays_evoluidos"):
        linhas += [
            "## Overlays Evoluídos", "",
        ]
        for nome in evoluir["overlays_evoluidos"]:
            versao = evoluir.get("versoes", {}).get(nome, "?")
            linhas.append(f"- **{nome}** → v{versao}")
        linhas.append("")

    versoes = stats_prompt.get("overlays", {})
    linhas += [
        "## Versões dos Overlays", "",
        "| Overlay | Versão |",
        "|---------|--------|",
    ]
    for nome, v in versoes.items():
        linhas.append(f"| {nome} | v{v} |")

    linhas += [
        "",
        "---",
        f"_AgentePetrobras Autoevolutivo — Ciclo de {hoje}_",
    ]

    return "\n".join(linhas) + "\n"


def relatorio_evolucao(formato: str = "texto") -> str:
    """Gera um resumo do estado da autoevolução para exibir ao usuário.

    Args:
        formato: "texto" (CLI) ou "md" (Markdown).
    """
    from evolucao import DiarioEvolucao
    from auto_avaliacao import AutoAvaliador
    from estrategia_ab import GerenciadorAB
    from prompt_evoluivel import PromptEvoluivel

    diario = DiarioEvolucao()
    avaliador = AutoAvaliador()
    ab = GerenciadorAB()
    pe = PromptEvoluivel()

    sd = diario.estatisticas()
    sa = avaliador.estatisticas()
    sab = ab.estatisticas()
    sp = pe.estatisticas()

    ranking = diario.ranking_estrategias(5)

    if formato == "md":
        return _gerar_relatorio(
            {"etapas": {"evoluir": {"overlays_evoluidos": [], "versoes": sp["overlays"]}}},
            ranking, sd, sa, sab, sp,
        )

    # Formato texto (CLI)
    linhas = [
        "══════════════════════════════════════════════════",
        "     🧬 PAINEL DE AUTOEVOLUÇÃO",
        "══════════════════════════════════════════════════",
        "",
        f"  Decisões registradas:  {sd['total_decisoes']}",
        f"  Com outcome:           {sd['com_outcome']}",
        f"  Eficácia global:       {sd['eficacia_global']:.0%}",
        f"  Top estratégia:        {sd['top_estrategia'] or '(sem dados)'}",
        "",
        f"  Score respostas (7d):  {sa.get('score_medio_7d', 0)}/100",
        f"  Tendência qualidade:   {sa.get('tendencia', '?')}",
        "",
        f"  Experimentos A/B:      {sab['ativos']} ativos · {sab['concluidos']} concluídos",
        "",
    ]

    if ranking:
        linhas.append("  Ranking de Estratégias:")
        for i, r in enumerate(ranking, 1):
            ef = r.get("eficacia_media", 0)
            emoji = "🟢" if ef >= 0.7 else ("🟡" if ef >= 0.5 else "🔴")
            linhas.append(f"    {i}. {emoji} {r['estrategia']:25s} {ef:.0%} ({r['usos']} usos)")

    linhas += [
        "",
        "  Overlays do Prompt:",
    ]
    for nome, v in sp.get("overlays", {}).items():
        linhas.append(f"    • {nome}: v{v}")

    regressao = avaliador.detectar_regressao()
    if regressao:
        linhas += ["", f"  ⚠ {regressao['mensagem']}"]

    linhas += [
        "",
        "══════════════════════════════════════════════════",
    ]
    return "\n".join(linhas)


def main() -> None:
    """CLI do ciclo evolutivo."""
    import argparse

    sys.path.insert(0, str(AQUI))

    parser = argparse.ArgumentParser(description="Ciclo evolutivo do AgentePetrobras")
    parser.add_argument("--relatorio", action="store_true", help="Apenas gerar relatório")
    parser.add_argument("--rollback", metavar="OVERLAY", help="Rollback de um overlay")
    parser.add_argument("--no-evolve", action="store_true", help="Pular evolução de prompts")
    args = parser.parse_args()

    if args.relatorio:
        print(relatorio_evolucao())
        return

    if args.rollback:
        from prompt_evoluivel import PromptEvoluivel
        pe = PromptEvoluivel()
        ok = pe.rollback(args.rollback)
        print(f"{'✓ Rollback OK' if ok else '✗ Falha no rollback'}: {args.rollback}")
        return

    # Ciclo completo
    cliente = None
    if not args.no_evolve:
        try:
            from local_llm import LocalLLM
            cliente = LocalLLM()
        except Exception:
            print("⚠ LLM não disponível — rodando sem evolução de prompts")

    executar_ciclo(
        cliente_llm=cliente,
        evoluir_prompts=not args.no_evolve and cliente is not None,
    )


if __name__ == "__main__":
    main()
