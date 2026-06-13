"""Loop de Eficácia Fechado — Prescrição governada por outcomes.

Une as peças que já existem num laço fechado de coaching científico:

    diagnóstico (coaching) → escolhe a disciplina mais fraca (desempenho REAL)
    estratégia            → A/B ativo > ranking de eficácia comprovada > catálogo
    registra a decisão    → para depois medir o efeito (evolucao.DiarioEvolucao)
    mede o resultado      → registrar_resultado fecha o laço e alimenta o A/B

Assim a próxima recomendação passa a ser GOVERNADA pelo que funcionou de fato,
não por um palpite fixo.

Uso:
    from prescricao import prescrever, registrar_resultado_prescricao, eficacia_loop
    p = prescrever()                       # decide foco + estratégia + dose
    # ... candidato estuda e faz simulado ...
    registrar_resultado_prescricao(p["disciplina"], acerto_novo=72,
                                    experimento_id=p["experimento_id"], grupo=p["grupo"])
    print(formatar_eficacia())
"""

from __future__ import annotations

from typing import Any

# Catálogo de estratégias baseadas em evidência (prática de recuperação,
# intercalação, revisão espaçada, etc.) com a "dose" sugerida.
CATALOGO = {
    "retrieval_practice": "Prática de recuperação: {n} questões de {disc} de memória, depois confira e releia só os erros",
    "estudo_dirigido_erros": "Estudo dirigido aos erros: refaça os {n} tipos de questão de {disc} que mais erra e anote o porquê",
    "intercalacao": "Intercalação: alterne {disc} com outra disciplina a cada 25min para fixar discriminação",
    "simulado_cronometrado": "Simulado cronometrado de {disc} ({n} questões no tempo de prova) para consolidar sob pressão",
    "revisao_espacada": "Revisão espaçada: revise {disc} hoje, em 2 dias e em 7 dias (cartões SM-2 vencidos primeiro)",
}


def _estrategia_por_desempenho(acerto: float | None) -> str:
    """Escolhe uma estratégia do catálogo conforme o nível atual de acerto."""
    if acerto is None:
        return "retrieval_practice"
    if acerto < 50:
        return "retrieval_practice"      # construir base via recuperação ativa
    if acerto < 70:
        return "estudo_dirigido_erros"   # atacar pontos fracos específicos
    if acerto < 85:
        return "intercalacao"            # refinar discriminação
    return "simulado_cronometrado"       # consolidar sob condição de prova


def _dose(disciplina: str) -> int:
    return 20


def _acerto_atual(disciplina: str) -> float | None:
    """Acerto esperado a partir da habilidade medida (coaching) — desempenho REAL."""
    try:
        import coaching
        est = coaching.carregar()
        if disciplina.lower() in {d.lower() for d in est.get("habilidades", {})}:
            # casa ignorando caixa
            for d, rating in est["habilidades"].items():
                if d.lower() == disciplina.lower():
                    return round(coaching.expectativa(rating, coaching.RATING_INICIAL) * 100, 1)
    except Exception:
        pass
    return None


def _escolher_disciplina(diario=None) -> tuple[str, float | None]:
    """Disciplina-foco = mais fraca com dados no diagnóstico adaptativo."""
    try:
        import coaching
        diag = coaching.diagnostico()
        if diag["foco_recomendado"]:
            disc = diag["foco_recomendado"][0]
            return disc, _acerto_atual(disc)
        if diag["disciplinas"]:
            disc = diag["disciplinas"][0]["disciplina"]
            return disc, _acerto_atual(disc)
    except Exception:
        pass
    return "Geral", None


def prescrever(disciplina: str | None = None, acerto_atual: float | None = None,
               diario=None, ab=None) -> dict[str, Any]:
    """Decide a próxima ação de estudo e a registra como decisão (para medir depois).

    Ordem de escolha da estratégia:
        1. experimento A/B ativo para a disciplina (se houver);
        2. melhor estratégia comprovada no ranking de eficácia (usos >= 3);
        3. catálogo baseado em evidência conforme o nível de acerto.
    """
    if diario is None:
        from evolucao import DiarioEvolucao
        diario = DiarioEvolucao()
    if ab is None:
        from estrategia_ab import GerenciadorAB
        ab = GerenciadorAB()

    if disciplina is None:
        disciplina, acerto_inferido = _escolher_disciplina(diario)
        if acerto_atual is None:
            acerto_atual = acerto_inferido
    elif acerto_atual is None:
        acerto_atual = _acerto_atual(disciplina)

    fonte = "catalogo"
    experimento_id = grupo = None

    # 1. experimento A/B ativo
    escolha_ab = None
    try:
        escolha_ab = ab.selecionar_estrategia(disciplina, acerto_atual)
    except Exception:
        escolha_ab = None
    if escolha_ab:
        estrategia = escolha_ab["estrategia"]
        experimento_id = escolha_ab.get("experimento_id")
        grupo = escolha_ab.get("grupo")
        fonte = "ab"
    else:
        # 2. ranking de eficácia comprovada
        estrategia = None
        try:
            ranking = diario.ranking_estrategias(5)
            comprovadas = [r for r in ranking
                           if r.get("usos", 0) >= 3 and r.get("eficacia_media", 0) > 0]
            if comprovadas:
                estrategia = comprovadas[0]["estrategia"]
                fonte = "ranking"
        except Exception:
            estrategia = None
        # 3. catálogo por desempenho
        if not estrategia:
            estrategia = _estrategia_por_desempenho(acerto_atual)
            fonte = "catalogo"

    modelo = CATALOGO.get(estrategia, "{disc}: pratique {n} questões e revise os erros")
    prescricao_txt = modelo.format(disc=disciplina, n=_dose(disciplina))

    decisao_id = None
    try:
        decisao_id = diario.registrar_decisao(
            estrategia=estrategia, disciplina=disciplina, acerto_atual=acerto_atual,
            prescricao=prescricao_txt,
            contexto_extra={"fonte": fonte, "experimento_id": experimento_id, "grupo": grupo},
        )
    except Exception:
        pass

    return {
        "disciplina": disciplina, "estrategia": estrategia, "prescricao": prescricao_txt,
        "acerto_atual": acerto_atual, "fonte": fonte, "decisao_id": decisao_id,
        "experimento_id": experimento_id, "grupo": grupo,
    }


def registrar_resultado_prescricao(disciplina: str, acerto_novo: float,
                                   experimento_id: str | None = None, grupo: str | None = None,
                                   questoes: int = 0, diario=None, ab=None) -> dict[str, Any]:
    """Fecha o laço: correlaciona o outcome com a última decisão e alimenta o A/B."""
    if diario is None:
        from evolucao import DiarioEvolucao
        diario = DiarioEvolucao()
    decisao = None
    try:
        decisao = diario.registrar_outcome(disciplina, acerto_novo, questoes=questoes)
    except Exception:
        decisao = None

    exp = None
    if experimento_id and grupo:
        if ab is None:
            from estrategia_ab import GerenciadorAB
            ab = GerenciadorAB()
        try:
            exp = ab.registrar_resultado(experimento_id, grupo, acerto_novo)
        except Exception:
            exp = None

    return {
        "disciplina": disciplina, "acerto_novo": acerto_novo,
        "decisao_atualizada": decisao is not None,
        "eficacia": (decisao or {}).get("eficacia"),
        "ab_atualizado": exp is not None,
    }


def eficacia_loop(diario=None, ab=None) -> dict[str, Any]:
    """Relatório do laço: estratégias que melhoram a nota + recomendação."""
    if diario is None:
        from evolucao import DiarioEvolucao
        diario = DiarioEvolucao()
    if ab is None:
        from estrategia_ab import GerenciadorAB
        ab = GerenciadorAB()

    ranking = []
    try:
        ranking = diario.ranking_estrategias(10)
    except Exception:
        ranking = []
    stats = {}
    try:
        stats = diario.estatisticas()
    except Exception:
        stats = {}
    ab_stats = {}
    try:
        ab_stats = ab.estatisticas()
    except Exception:
        ab_stats = {}

    melhor = next((r for r in ranking if r.get("usos", 0) >= 3 and r.get("eficacia_media", 0) > 0), None)
    return {
        "ranking": ranking,
        "eficacia_global": stats.get("eficacia_global"),
        "decisoes": stats.get("total_decisoes"),
        "com_outcome": stats.get("com_outcome"),
        "experimentos_ativos": ab_stats.get("ativos"),
        "estrategia_recomendada": melhor["estrategia"] if melhor else None,
    }


def formatar_prescricao(p: dict[str, Any]) -> str:
    acerto = "—" if p["acerto_atual"] is None else f"{p['acerto_atual']:.0f}%"
    return (
        "🎓 PRESCRIÇÃO DE ESTUDO\n"
        f"  Disciplina-foco: {p['disciplina']}  (acerto atual: {acerto})\n"
        f"  Estratégia: {p['estrategia']}  [fonte: {p['fonte']}]\n"
        f"  ➜ {p['prescricao']}"
    )


def formatar_eficacia(rel: dict[str, Any] | None = None) -> str:
    rel = rel or eficacia_loop()
    linhas = [
        "══════════════════════════════════════════════════",
        "     🔬 EFICÁCIA DO COACHING (loop fechado)",
        "══════════════════════════════════════════════════",
        "",
        f"  Decisões: {rel.get('decisoes') or 0}  ·  com outcome: {rel.get('com_outcome') or 0}",
        f"  Eficácia global: {rel.get('eficacia_global')}",
        f"  Experimentos A/B ativos: {rel.get('experimentos_ativos') or 0}",
        "",
    ]
    ranking = rel.get("ranking") or []
    if ranking:
        linhas.append("  Estratégias por eficácia (Δ nota):")
        for r in ranking[:6]:
            ef = r.get("eficacia_media", 0)
            emoji = "🟢" if ef >= 0.05 else ("🟡" if ef >= 0 else "🔴")
            linhas.append(f"    {emoji} {r.get('estrategia', '?'):24s} "
                          f"Δ {ef:+.0%}  ({r.get('usos', 0)} usos)")
    if rel.get("estrategia_recomendada"):
        linhas += ["", f"  ➜ Estratégia recomendada: {rel['estrategia_recomendada']}"]
    linhas += ["", "══════════════════════════════════════════════════"]
    return "\n".join(linhas)


__all__ = [
    "prescrever", "registrar_resultado_prescricao", "eficacia_loop",
    "formatar_prescricao", "formatar_eficacia", "CATALOGO",
]
