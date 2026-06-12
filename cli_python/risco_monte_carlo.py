"""Análise de Risco — Simulação Monte Carlo para aprovação.

Simula N cenários de prova com base no histórico de acertos do candidato
para estimar a probabilidade de atingir a nota de corte.

Uso:
    from risco_monte_carlo import simular_aprovacao, formatar_relatorio

    resultado = simular_aprovacao(perfil, sessoes, simulados, n_cenarios=10000)
    print(formatar_relatorio(resultado))
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResultadoMonteCarlo:
    n_cenarios: int
    aprovacoes: int
    prob_aprovacao: float
    nota_media: float
    nota_mediana: float
    nota_min: float
    nota_max: float
    nota_corte: float
    desvio_padrao: float
    intervalo_confianca_90: tuple[float, float]
    notas: list[float] = field(default_factory=list)
    por_disciplina: dict[str, dict] = field(default_factory=dict)


PESOS_PADRAO = {
    "Português": 0.22,
    "Raciocínio Lógico": 0.12,
    "Matemática": 0.10,
    "Legislação": 0.10,
    "Informática": 0.05,
    "Atualidades": 0.05,
    "Engenharia Civil": 0.36,
    "Engenharia Mecânica": 0.36,
    "Engenharia Elétrica": 0.36,
    "Engenharia Química": 0.36,
    "Engenharia de Produção": 0.36,
    "Conteúdo Base": 0.10,
}


def _extrair_desempenho(
    perfil: dict,
    sessoes: list[dict],
    simulados: list[dict],
) -> dict[str, dict]:
    """Extrai média e desvio padrão de acerto por disciplina."""
    acertos_por_disc: dict[str, list[float]] = {}

    # 1. Do perfil (histórico de acerto)
    hist = perfil.get("historico_acerto", {})
    for disc, pct in hist.items():
        try:
            acertos_por_disc.setdefault(disc, []).append(float(pct))
        except (ValueError, TypeError):
            pass

    # 2. De simulados (pct por disciplina)
    for s in simulados:
        if "disciplinas" in s:
            for disc, info in s["disciplinas"].items():
                if "pct" in info:
                    acertos_por_disc.setdefault(disc, []).append(info["pct"])
        else:
            pct = s.get("pct")
            disc = s.get("disciplina", "geral")
            if pct is not None:
                acertos_por_disc.setdefault(disc, []).append(pct)

    # 3. De sessoes (questoes/acertos)
    for s in sessoes:
        disc = s.get("disciplina", "geral")
        q = s.get("questoes", 0)
        a = s.get("acertos", 0)
        if q > 0:
            acertos_por_disc.setdefault(disc, []).append(a / q * 100)

    # Calcular média e desvio padrão
    resultado: dict[str, dict] = {}
    for disc, valores in acertos_por_disc.items():
        if len(valores) < 2:
            continue
        media = sum(valores) / len(valores)
        var = sum((v - media) ** 2 for v in valores) / len(valores)
        dp = math.sqrt(var)
        resultado[disc] = {
            "media": round(media, 1),
            "dp": round(max(dp, 5.0), 1),
            "n_amostras": len(valores),
        }

    return resultado


def _simular_cenario(
    desempenho: dict[str, dict],
    pesos: dict[str, float],
) -> float:
    """Simula uma prova: amostra nota por disciplina com ruído normal."""
    nota_total = 0.0
    peso_total = 0.0

    for disc, info in desempenho.items():
        peso = pesos.get(disc, 0.10)
        media = info["media"]
        dp = info["dp"]

        # Amostra da distribuição normal, limitada a [0, 100]
        nota = random.gauss(media, dp)
        nota = max(0, min(100, nota))

        nota_total += nota * peso
        peso_total += peso

    if peso_total == 0:
        return 0.0

    return nota_total / peso_total


def _estimar_nota_corte(perfil: dict) -> float:
    """Estima a nota de corte com base no cargo alvo."""
    cargo = (perfil.get("cargo_alvo") or "").lower()
    nota_corte = perfil.get("nota_corte_estimada")
    if nota_corte:
        try:
            return float(nota_corte)
        except (ValueError, TypeError):
            pass

    # Fallback por cargo
    tabela = {
        "engenheiro": 65,
        "eng": 65,
        "administrador": 62,
        "contador": 63,
        "analista": 62,
        "tecnico": 58,
        "geologo": 66,
        "quimico": 64,
        "advogado": 66,
    }
    for chave, nota in tabela.items():
        if chave in cargo:
            return nota
    return 62.0


def simular_aprovacao(
    perfil: dict[str, Any],
    sessoes: list[dict],
    simulados: list[dict],
    n_cenarios: int = 10000,
    pesos: dict[str, float] | None = None,
) -> ResultadoMonteCarlo:
    """Executa simulação Monte Carlo.

    Args:
        perfil: Dicionário do perfil do candidato.
        sessoes: Lista de sessões de estudo.
        simulados: Lista de simulados realizados.
        n_cenarios: Número de cenários a simular (default: 10000).
        pesos: Pesos por disciplina (default: PESOS_PADRAO).

    Returns:
        ResultadoMonteCarlo com estatísticas da simulação.
    """
    desempenho = _extrair_desempenho(perfil, sessoes, simulados)

    if not desempenho:
        return ResultadoMonteCarlo(
            n_cenarios=0,
            aprovacoes=0,
            prob_aprovacao=0.0,
            nota_media=0.0,
            nota_mediana=0.0,
            nota_min=0.0,
            nota_max=0.0,
            nota_corte=0.0,
            desvio_padrao=0.0,
            intervalo_confianca_90=(0.0, 0.0),
            notas=[],
        )

    pesos_final = pesos or PESOS_PADRAO
    nota_corte = _estimar_nota_corte(perfil)

    notas: list[float] = []
    aprovacoes = 0

    for _ in range(n_cenarios):
        nota = _simular_cenario(desempenho, pesos_final)
        notas.append(nota)
        if nota >= nota_corte:
            aprovacoes += 1

    notas_ordenadas = sorted(notas)
    n = len(notas_ordenadas)
    media = sum(notas) / n
    mediana = notas_ordenadas[n // 2]
    var = sum((v - media) ** 2 for v in notas) / n
    dp = math.sqrt(var)
    ic_inf = notas_ordenadas[int(n * 0.05)]
    ic_sup = notas_ordenadas[int(n * 0.95)]

    # Desempenho por disciplina
    por_disciplina = {}
    for disc, info in desempenho.items():
        por_disciplina[disc] = {
            "media": info["media"],
            "dp": info["dp"],
            "n": info["n_amostras"],
        }

    return ResultadoMonteCarlo(
        n_cenarios=n_cenarios,
        aprovacoes=aprovacoes,
        prob_aprovacao=round(aprovacoes / n_cenarios * 100, 1),
        nota_media=round(media, 1),
        nota_mediana=round(mediana, 1),
        nota_min=round(notas_ordenadas[0], 1),
        nota_max=round(notas_ordenadas[-1], 1),
        nota_corte=nota_corte,
        desvio_padrao=round(dp, 1),
        intervalo_confianca_90=(round(ic_inf, 1), round(ic_sup, 1)),
        notas=notas_ordenadas,
        por_disciplina=por_disciplina,
    )


def formatar_relatorio(r: ResultadoMonteCarlo) -> str:
    """Formata o resultado da simulação como Markdown."""
    if r.n_cenarios == 0:
        return "Sem dados suficientes para simulação. Registre sessões e simulados primeiro."

    def _barra(pct: float, tamanho: int = 20) -> str:
        preenchido = int(pct / 100 * tamanho)
        return "█" * preenchido + "░" * (tamanho - preenchido)

    linhas = [
        "# Análise de Risco — Monte Carlo",
        "",
        f"**Cenários simulados:** {r.n_cenarios:,}",
        f"**Nota de corte estimada:** {r.nota_corte:.0f}",
        "",
        "## Resultado",
        "",
        f"**Probabilidade de aprovação:** {r.prob_aprovacao:.1f}%",
        f"{_barra(r.prob_aprovacao)}",
        "",
        f"**Aprovações:** {r.aprovacoes:,} / {r.n_cenarios:,}",
        "",
        "## Estatísticas da Nota Final",
        "",
        f"- Média: {r.nota_media:.1f}",
        f"- Mediana: {r.nota_mediana:.1f}",
        f"- Desvio padrão: {r.desvio_padrao:.1f}",
        f"- Mínimo: {r.nota_min:.1f}",
        f"- Máximo: {r.nota_max:.1f}",
        f"- IC 90%: [{r.intervalo_confianca_90[0]:.1f}, {r.intervalo_confianca_90[1]:.1f}]",
        "",
        "## Desempenho por Disciplina",
        "",
    ]
    for disc, info in sorted(r.por_disciplina.items()):
        linhas.append(
            f"- **{disc}**: média {info['media']}% (dp {info['dp']}, n={info['n']})"
        )

    linhas += [
        "",
        "## Interpretação",
        "",
    ]
    if r.prob_aprovacao >= 80:
        linhas.append("✅ **Alta probabilidade** — mantenha a consistência.")
    elif r.prob_aprovacao >= 50:
        linhas.append("🟡 **Probabilidade moderada** — foque nas disciplinas com maior gap.")
    elif r.prob_aprovacao >= 20:
        linhas.append("🟠 **Probabilidade baixa** — intensifique estudos nas disciplinas mais pesadas.")
    else:
        linhas.append("🔴 **Probabilidade muito baixa** — considere revisar a estratégia e metas.")

    if r.intervalo_confianca_90[1] < r.nota_corte:
        linhas.append(
            "\n⚠ Mesmo no cenário otimista (IC 90% superior), a nota fica abaixo do corte. "
            "É necessário um salto de desempenho em pelo menos uma disciplina."
        )

    return "\n".join(linhas) + "\n"


def simular_e_salvar(
    perfil: dict,
    sessoes: list[dict],
    simulados: list[dict],
    caminho: str | None = None,
    n_cenarios: int = 10000,
) -> str:
    """Simula e salva relatório em arquivo."""
    from pathlib import Path

    resultado = simular_aprovacao(perfil, sessoes, simulados, n_cenarios)
    md = formatar_relatorio(resultado)

    if caminho:
        saida = Path(caminho)
    else:
        saida = Path(__file__).resolve().parent / "dados" / "risco_monte_carlo.md"

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(md, encoding="utf-8")
    return str(saida)
