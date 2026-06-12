"""Agendador Semanal — cronograma de estudos automático com SM-2.

Gera um plano de estudos semanal personalizado baseado no perfil do candidato,
desempenho por disciplina, tempo disponível e revisões SM-2.

Uso:
    from agendador import gerar_cronograma, formatar_cronograma

    cronograma = gerar_cronograma(perfil, sessoes, simulados)
    print(formatar_cronograma(cronograma))
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any


@dataclass
class BlocoEstudo:
    dia: str
    horario: str
    disciplina: str
    tema: str = ""
    tecnica: str = "Questões"
    duracao_min: int = 50
    concluido: bool = False


@dataclass
class CronogramaSemanal:
    semana_inicio: str
    blocos: list[BlocoEstudo] = field(default_factory=list)
    metas: dict[str, int] = field(default_factory=dict)
    observacoes: list[str] = field(default_factory=list)


DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

TECNICAS_POR_FASE = {
    "FUNDACAO": ["SQ3R", "Retrieval Practice", "Anki", "Pomodoro 50/10"],
    "DOMINIO": ["Questões", "Intercalação", "Simulado Parcial", "Anki"],
    "CONSOLIDACAO": ["Simulado Completo", "Revisão Espaçada", "Anki"],
    "SPRINT": ["Simulado", "Anki", "Mapas Mentais"],
    "EMERGENCIA": ["Currículo Mínimo", "Questões", "Anki"],
}

PESOS_CATEGORIA = {
    "Português": 0.22,
    "Raciocínio Lógico": 0.15,
    "Legislação": 0.10,
    "Atualidades": 0.05,
    "Informática": 0.05,
    "Matemática": 0.15,
    "Engenharia": 0.28,
}


def _calcular_gaps(
    perfil: dict[str, Any],
    sessoes: list[dict],
    simulados: list[dict],
) -> dict[str, float]:
    """Calcula gaps de desempenho por disciplina (0-1, onde 1 = maior gap)."""
    gaps: dict[str, float] = {}

    # 1. Do perfil (historico_acerto)
    hist = perfil.get("historico_acerto", {})
    for disc, pct in hist.items():
        try:
            pct = float(pct)
        except (ValueError, TypeError):
            pct = 50.0
        gaps[disc] = max(0.0, (70.0 - pct) / 70.0)

    # 2. De simulados
    for s in simulados:
        pct_s = s.get("pct", 0)
        if pct_s < 70:
            disc = s.get("disciplina", "geral")
            gap_disc = max(0.0, (70.0 - pct_s) / 70.0)
            if disc not in gaps or gap_disc > gaps[disc]:
                gaps[disc] = gap_disc

    # 3. De sessoes (inferir gaps por erro dominante)
    erros = Counter()
    total_sessoes = 0
    for s in sessoes:
        erro = s.get("erro_dominante", "")
        if erro:
            erros[erro] += 1
            total_sessoes += 1
    if total_sessoes > 0 and "C" in erros and erros["C"] / total_sessoes > 0.3:
        gaps.setdefault("Conteúdo Base", 0.5)

    return gaps


def _priorizar_disciplinas(gaps: dict[str, float]) -> list[str]:
    """Ordena disciplinas por gap (maior primeiro)."""
    return sorted(gaps.keys(), key=lambda d: gaps.get(d, 0), reverse=True)


def _estimar_horas_disponiveis(perfil: dict[str, Any]) -> dict[str, int]:
    """Estima horas disponíveis por dia da semana."""
    h_util = int(perfil.get("horas_dia_util", 0) or 2)
    h_sab = int(perfil.get("horas_sabado", 0) or 4)
    h_dom = int(perfil.get("horas_domingo", 0) or 3)

    return {
        "Segunda": h_util,
        "Terça": h_util,
        "Quarta": h_util,
        "Quinta": h_util,
        "Sexta": h_util,
        "Sábado": h_sab,
        "Domingo": h_dom,
    }


def _alocar_blocos(
    prioridades: list[str],
    horas_dia: dict[str, int],
    fase: str,
) -> list[BlocoEstudo]:
    """Distribui blocos de estudo ao longo da semana."""
    blocos: list[BlocoEstudo] = []
    tecnicas = TECNICAS_POR_FASE.get(fase, TECNICAS_POR_FASE["DOMINIO"])

    for dia in DIAS_SEMANA:
        horas = horas_dia.get(dia, 0)
        if horas <= 0:
            continue

        # Divide o dia em blocos de 50min
        n_blocos = min(max(1, horas * 60 // 50), len(prioridades))
        blocos_dia = min(n_blocos, len(prioridades))

        for i in range(blocos_dia):
            disc_idx = (DIAS_SEMANA.index(dia) * 2 + i) % len(prioridades)
            disc = prioridades[disc_idx]
            tecnica = tecnicas[i % len(tecnicas)]

            # Horário aproximado
            horario_base = 8 if dia in ("Sábado", "Domingo") else 19
            horario = f"{horario_base + i * 1:02d}:00"

            blocos.append(BlocoEstudo(
                dia=dia,
                horario=horario,
                disciplina=disc,
                tecnica=tecnica,
                duracao_min=50,
            ))

    return blocos


def _gerar_metas(perfil: dict, gaps: dict) -> dict[str, int]:
    """Define metas semanais por disciplina."""
    fase = perfil.get("fase_atual", "DOMINIO")
    meta_base = 200 if fase == "FUNDACAO" else (300 if fase == "DOMINIO" else 400)

    n_prioridades = max(1, len(gaps))
    metas = {}
    for disc, gap in sorted(gaps.items(), key=lambda x: x[1], reverse=True):
        peso = max(0.2, gap)
        metas[disc] = int(meta_base * peso / sum(max(0.2, g) for g in gaps.values()))
    return metas


def _adicionar_revisoes_sm2(blocos: list[BlocoEstudo]) -> list[BlocoEstudo]:
    """Adiciona blocos de revisão SM-2 no início de cada dia."""
    try:
        from sm2 import revisoes_devidas, carregar
        cartoes = carregar()
        if not cartoes:
            return blocos
        devidos = revisoes_devidas(cartoes)
        if not devidos:
            return blocos
    except Exception:
        return blocos

    # Agrupa revisões por disciplina
    por_disc: dict[str, int] = {}
    for c in devidos:
        disc = c.get("disciplina", "Geral")
        por_disc[disc] = por_disc.get(disc, 0) + 1

    # Dias únicos já com blocos
    dias_presentes = set(b.dia for b in blocos)

    novos: list[BlocoEstudo] = []
    for dia in sorted(dias_presentes, key=lambda d: ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"].index(d)):
        disc_com_revisoes = [d for d in por_disc if por_disc[d] > 0]
        if not disc_com_revisoes:
            continue
        # Adiciona 1 bloco de revisão no início do dia
        disc_rev = disc_com_revisoes[len(novos) % len(disc_com_revisoes)]
        novos.append(BlocoEstudo(
            dia=dia,
            horario="07:00",
            disciplina=disc_rev,
            tema=f"Revisão SM-2 ({por_disc[disc_rev]} questões pendentes)",
            tecnica="Revisão Espaçada",
            duracao_min=30,
        ))
        por_disc[disc_rev] = 0  # não repete mesma disciplina

    return novos + blocos


def gerar_cronograma(
    perfil: dict[str, Any],
    sessoes: list[dict],
    simulados: list[dict],
) -> CronogramaSemanal:
    """Gera cronograma semanal personalizado com revisões SM-2.

    Args:
        perfil: Dicionário do perfil do candidato.
        sessoes: Lista de sessões de estudo.
        simulados: Lista de simulados realizados.

    Returns:
        CronogramaSemanal com blocos de estudo, metas e observações.
    """
    gaps = _calcular_gaps(perfil, sessoes, simulados)
    prioridades = _priorizar_disciplinas(gaps)
    horas_dia = _estimar_horas_disponiveis(perfil)
    fase = perfil.get("fase_atual", "DOMINIO")
    blocos = _alocar_blocos(prioridades, horas_dia, fase)
    blocos = _adicionar_revisoes_sm2(blocos)
    metas = _gerar_metas(perfil, gaps)

    hoje = date.today()
    seg = hoje - timedelta(days=hoje.weekday())
    semana_inicio = seg.isoformat()

    observacoes = []
    if gaps:
        pior = prioridades[0]
        observacoes.append(f"Prioridade: {pior} (gap de {gaps.get(pior, 0)*100:.0f}%)")
    if horas_dia.get("Segunda", 0) < 1:
        observacoes.append("Horas disponíveis muito baixas — considere ajustar rotina")
    if fase == "EMERGENCIA":
        observacoes.append("MODO EMERGÊNCIA ativo — foque apenas no currículo mínimo")

    try:
        from sm2 import revisoes_devidas, carregar
        devidos = revisoes_devidas(carregar())
        if devidos:
            observacoes.append(f"Revisões SM-2 pendentes: {len(devidos)} questões")
    except Exception:
        pass

    return CronogramaSemanal(
        semana_inicio=semana_inicio,
        blocos=blocos,
        metas=metas,
        observacoes=observacoes,
    )


def formatar_cronograma(c: CronogramaSemanal) -> str:
    """Formata o cronograma como string Markdown."""
    linhas = [
        "# Cronograma Semanal de Estudos",
        f"**Semana de:** {c.semana_inicio}",
        f"**Total de blocos:** {len(c.blocos)}",
        "",
    ]

    if c.observacoes:
        linhas.append("## Observações")
        for obs in c.observacoes:
            linhas.append(f"- {obs}")
        linhas.append("")

    linhas.append("## Blocos de Estudo")
    linhas.append("")

    dia_atual = ""
    for bloco in c.blocos:
        if bloco.dia != dia_atual:
            dia_atual = bloco.dia
            linhas.append(f"### {dia_atual}")
        bloco_str = (
            f"- **{bloco.horario}** — {bloco.disciplina} "
            f"({bloco.tecnica}, {bloco.duracao_min}min)"
        )
        if bloco.tema:
            bloco_str += f" — {bloco.tema}"
        linhas.append(bloco_str)

    if c.metas:
        linhas.append("")
        linhas.append("## Metas da Semana")
        for disc, qtd in sorted(c.metas.items(), key=lambda x: x[1], reverse=True):
            linhas.append(f"- {disc}: {qtd} questões")

    return "\n".join(linhas) + "\n"


def gerar_e_salvar(
    perfil: dict,
    sessoes: list[dict],
    simulados: list[dict],
    caminho: str | None = None,
) -> str:
    """Gera cronograma e salva em arquivo Markdown."""
    cronograma = gerar_cronograma(perfil, sessoes, simulados)
    md = formatar_cronograma(cronograma)

    if caminho:
        saida = Path(caminho)
    else:
        from pathlib import Path as _Path
        aqui = _Path(__file__).resolve().parent
        saida = aqui / "dados" / "cronograma_semanal.md"

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(md, encoding="utf-8")
    return str(saida)


from pathlib import Path
