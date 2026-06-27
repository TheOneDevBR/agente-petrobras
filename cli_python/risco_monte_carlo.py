"""Análise de Risco — Simulação Monte Carlo para aprovação.

Simula N cenários de prova com base no histórico de acertos do candidato
para estimar a probabilidade de atingir a nota de corte.

Backends (auto-selecionados):
  - python:  pure Python (fallback)
  - numpy:   vetorizado CPU  → default para n ≤ 100k
  - cupy:    vetorizado GPU  → default para n > 100k (se disponível)

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

import numpy as np

try:
    import cupy as cp
    _HAS_CUPY = True
except ImportError:
    _HAS_CUPY = False


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
    backend_usado: str = ""


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

    hist = perfil.get("historico_acerto", {})
    for disc, pct in hist.items():
        try:
            acertos_por_disc.setdefault(disc, []).append(float(pct))
        except (ValueError, TypeError):
            pass

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

    for s in sessoes:
        disc = s.get("disciplina", "geral")
        q = s.get("questoes", 0)
        a = s.get("acertos", 0)
        if q > 0:
            acertos_por_disc.setdefault(disc, []).append(a / q * 100)

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

        nota = random.gauss(media, dp)
        nota = max(0, min(100, nota))

        nota_total += nota * peso
        peso_total += peso

    if peso_total == 0:
        return 0.0

    return nota_total / peso_total


_LIMIAR_GPU = 100_000


def _escolher_backend(n_cenarios: int) -> str:
    if _HAS_CUPY and n_cenarios > _LIMIAR_GPU:
        return "cupy"
    return "numpy"


def _simular_cenarios_numpy(
    disciplinas: list[str],
    medias: np.ndarray,
    dps: np.ndarray,
    pesos_arr: np.ndarray,
    n_cenarios: int,
    nota_corte: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, int, float]:
    ruido = rng.normal(0, 1, size=(n_cenarios, len(disciplinas))).astype(np.float32)
    notas_disc = medias + dps * ruido
    notas_disc = np.clip(notas_disc, 0, 100, out=notas_disc)
    notas = notas_disc @ pesos_arr / pesos_arr.sum()
    aprovacoes = int(np.count_nonzero(notas >= nota_corte))
    return notas, aprovacoes


def _simular_cenarios_cupy(
    disciplinas: list[str],
    medias: np.ndarray,
    dps: np.ndarray,
    pesos_arr: np.ndarray,
    n_cenarios: int,
    nota_corte: float,
) -> tuple[np.ndarray, int, float]:
    m_gpu = cp.asarray(medias)
    d_gpu = cp.asarray(dps)
    p_gpu = cp.asarray(pesos_arr)
    ruido = cp.random.normal(0, 1, size=(n_cenarios, len(disciplinas)), dtype=cp.float32)
    notas_disc = m_gpu + d_gpu * ruido
    notas_disc = cp.clip(notas_disc, 0, 100, out=notas_disc)
    notas_gpu = notas_disc @ p_gpu / p_gpu.sum()
    cp.cuda.Stream.null.synchronize()
    notas = cp.asnumpy(notas_gpu)
    aprovacoes = int(cp.count_nonzero(notas_gpu >= nota_corte))
    return notas, aprovacoes


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
    backend: str = "auto",
    semente: int | None = None,
) -> ResultadoMonteCarlo:
    """Executa simulação Monte Carlo vetorizada.

    Args:
        perfil: Dicionário do perfil do candidato.
        sessoes: Lista de sessões de estudo.
        simulados: Lista de simulados realizados.
        n_cenarios: Número de cenários a simular (default: 10000).
        pesos: Pesos por disciplina (default: PESOS_PADRAO).
        backend: "auto", "numpy", "cupy", ou "python".
        semente: Seed para reprodutibilidade.

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
    disciplinas = list(desempenho.keys())
    medias = np.array([desempenho[d]["media"] for d in disciplinas], dtype=np.float32)
    dps = np.array([desempenho[d]["dp"] for d in disciplinas], dtype=np.float32)
    pesos_arr = np.array(
        [pesos_final.get(d, 0.10) for d in disciplinas], dtype=np.float32
    )

    if backend == "auto":
        backend = _escolher_backend(n_cenarios)

    if backend == "cupy" and _HAS_CUPY:
        notas_arr, aprovacoes = _simular_cenarios_cupy(
            disciplinas, medias, dps, pesos_arr, n_cenarios, nota_corte,
        )
        backend_usado = "cupy"
    elif backend in ("numpy", "auto"):
        rng = np.random.default_rng(semente)
        notas_arr, aprovacoes = _simular_cenarios_numpy(
            disciplinas, medias, dps, pesos_arr, n_cenarios, nota_corte, rng,
        )
        backend_usado = "numpy"
    else:
        backend_usado = "python"
        notas_arr_list: list[float] = []
        aprovacoes = 0
        if semente is not None:
            random.seed(semente)
        for _ in range(n_cenarios):
            nota = _simular_cenario(desempenho, pesos_final)
            notas_arr_list.append(nota)
            if nota >= nota_corte:
                aprovacoes += 1
        notas_arr = np.array(notas_arr_list, dtype=np.float32)

    if len(notas_arr) == 0:
        return ResultadoMonteCarlo(
            n_cenarios=n_cenarios,
            aprovacoes=0,
            prob_aprovacao=0.0,
            nota_media=0.0,
            nota_mediana=0.0,
            nota_min=0.0,
            nota_max=0.0,
            nota_corte=nota_corte,
            desvio_padrao=0.0,
            intervalo_confianca_90=(0.0, 0.0),
            notas=[],
            backend_usado=backend_usado,
        )

    notas_ordenadas = np.sort(notas_arr)
    n = len(notas_ordenadas)
    media = float(np.mean(notas_arr))
    mediana = float(np.median(notas_arr))
    dp = float(np.std(notas_arr, ddof=0))
    ic_inf = float(np.percentile(notas_arr, 5))
    ic_sup = float(np.percentile(notas_arr, 95))

    por_disciplina = {}
    for disc in disciplinas:
        info = desempenho[disc]
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
        nota_min=round(float(notas_ordenadas[0]), 1),
        nota_max=round(float(notas_ordenadas[-1]), 1),
        nota_corte=nota_corte,
        desvio_padrao=round(dp, 1),
        intervalo_confianca_90=(round(ic_inf, 1), round(ic_sup, 1)),
        notas=notas_ordenadas.tolist(),
        por_disciplina=por_disciplina,
        backend_usado=backend_usado,
    )


def formatar_relatorio(r: ResultadoMonteCarlo) -> str:
    """Formata o resultado da simulação como Markdown."""
    if r.n_cenarios == 0:
        return "Sem dados suficientes para simulação. Registre sessões e simulados primeiro."

    def _barra(pct: float, tamanho: int = 20) -> str:
        preenchido = int(pct / 100 * tamanho)
        return "█" * preenchido + "░" * (tamanho - preenchido)

    backend_label = {
        "cupy": "GPU (CuPy)",
        "numpy": "CPU (NumPy vetorizado)",
        "python": "CPU (Python puro)",
    }.get(r.backend_usado, r.backend_usado)

    linhas = [
        "# Análise de Risco — Monte Carlo",
        "",
        f"**Cenários simulados:** {r.n_cenarios:,}",
        f"**Backend:** {backend_label}",
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
    backend: str = "auto",
    semente: int | None = None,
) -> str:
    """Simula e salva relatório em arquivo."""
    from pathlib import Path

    resultado = simular_aprovacao(
        perfil, sessoes, simulados, n_cenarios,
        backend=backend, semente=semente,
    )
    md = formatar_relatorio(resultado)

    if caminho:
        saida = Path(caminho)
    else:
        saida = Path(__file__).resolve().parent / "dados" / "risco_monte_carlo.md"

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(md, encoding="utf-8")
    return str(saida)
