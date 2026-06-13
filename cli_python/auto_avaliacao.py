"""Auto-avaliação — Meta-cognição do agente.

Avalia a qualidade das respostas do agente em 5 dimensões baseadas nos
princípios P1–P5 do system prompt. Mantém histórico e detecta regressões.

Uso:
    from auto_avaliacao import AutoAvaliador

    avaliador = AutoAvaliador()
    score = avaliador.avaliar_resposta(texto, contexto)
    print(avaliador.historico_qualidade())
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


AQUI = Path(__file__).resolve().parent
DADOS_EVOLUCAO = AQUI / "dados" / "evolucao"
AVALIACAO_PATH = DADOS_EVOLUCAO / "auto_avaliacao.json"

# Limiar para alertar sobre regressão
LIMIAR_REGRESSAO = 55
JANELA_REGRESSAO = 10  # últimas N respostas


def _ler_avaliacoes() -> dict[str, Any]:
    if AVALIACAO_PATH.exists():
        try:
            return json.loads(AVALIACAO_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"avaliacoes": [], "score_medio_7d": 0, "tendencia": "NOVA", "_versao": 1}


def _gravar_avaliacoes(dados: dict[str, Any]) -> None:
    DADOS_EVOLUCAO.mkdir(parents=True, exist_ok=True)
    dados["_atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    AVALIACAO_PATH.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Avaliadores por dimensão ────────────────────────────────────────────

def _score_especificidade(texto: str) -> int:
    """P1 — Especificidade cirúrgica: tema, tempo, técnica, material, critério."""
    score = 0
    # Tem tempo concreto? (Nmin, Nh, N minutos)
    if re.search(r"\d+\s*(?:min|minutos?|h|horas?)", texto, re.IGNORECASE):
        score += 20
    # Tem tema/disciplina específica?
    if re.search(
        r"(?:art\.?\s*\d|lei\s*\d|§|portugu[eê]s|matem[aá]|l[oó]gic|legisla|petrobras|"
        r"espec[ií]fic|regência|crase|NR-|ISO|LGPD|13\.303|CESGRANRIO)",
        texto, re.IGNORECASE
    ):
        score += 20
    # Tem técnica nomeada?
    if re.search(
        r"(?:Retrieval|SQ3R|Intercala|Feynman|Cornell|Pomodoro|Anki|"
        r"Pr[aá]tica Deliberada|Dual Coding|Mapa Mental|Simula[cç][aã]o)",
        texto, re.IGNORECASE,
    ):
        score += 20
    # Tem material concreto? (questão X, Q32, prova 2018)
    if re.search(r"(?:Q\d|quest[ãa]o|prova\s*\d|edital|Qconcursos)", texto, re.IGNORECASE):
        score += 20
    # Tem critério de sucesso? (meta, ≥, %, acerto)
    if re.search(r"(?:meta|≥|>=|\d+%|acerto|critério|mínimo)", texto, re.IGNORECASE):
        score += 20
    return min(100, score)


def _score_evidencia(texto: str) -> int:
    """P2 — Evidência antes de opinião: cita fonte, pesquisa, dado de prova."""
    score = 0
    # Referência a pesquisador/estudo
    if re.search(
        r"(?:Ebbinghaus|Roediger|Karpicke|Bjork|Ericsson|Walker|Ratey|"
        r"Kornell|Pressley|Paivio|Cirillo|Robinson|pesquisa|estudo|"
        r"meta-an[aá]lise|evid[eê]ncia)",
        texto, re.IGNORECASE,
    ):
        score += 40
    # Referência a dado concreto (prova, edital, artigo de lei)
    if re.search(
        r"(?:prova\s*\d{4}|edital|art\.?\s*\d|Lei\s*\d|CESGRANRIO\s*\d|"
        r"nota de corte|históric[oa]|dados?\s+d[aeo])",
        texto, re.IGNORECASE,
    ):
        score += 30
    # Referência a padrão de banca
    if re.search(r"(?:ARM-|ALT-|padr[aã]o de banca|armadilha|distrator)", texto, re.IGNORECASE):
        score += 30
    return min(100, score)


def _score_mensurabilidade(texto: str) -> int:
    """P5 — Progresso mensurável: meta numérica, critério de avanço."""
    score = 0
    # Números + unidade
    nums = re.findall(r"\d+\s*(?:%|questões|questoes|min|minutos?|pp|pontos?|dias?)", texto, re.IGNORECASE)
    if nums:
        score += min(50, len(nums) * 15)
    # Comparativo
    if re.search(r"(?:≥|>=|>|meta|mínimo|pelo menos|no mínimo|alvo|objetivo)", texto, re.IGNORECASE):
        score += 25
    # Critério de avanço/sucesso
    if re.search(r"(?:avanç|aprovação|critério|se\s+.{3,20}(?:≥|>=|>)\s*\d)", texto, re.IGNORECASE):
        score += 25
    return min(100, score)


def _score_acao_concreta(texto: str) -> int:
    """Termina com ação para AGORA."""
    linhas = [l.strip() for l in texto.strip().split("\n") if l.strip()]
    if not linhas:
        return 0

    # Verificar as últimas 3 linhas por ação concreta
    ultimas = linhas[-3:]
    texto_final = " ".join(ultimas).lower()

    score = 0
    # Imperativos
    if re.search(
        r"(?:comece|estude|resolva|faça|abra|revise|pratique|treine|"
        r"agora|próximo passo|hoje|imediatamente|já|→|▸|►|⏩|🎯)",
        texto_final, re.IGNORECASE,
    ):
        score += 60
    # Tem especificidade na ação?
    if re.search(r"\d+\s*(?:min|questões|questoes|h)", texto_final, re.IGNORECASE):
        score += 40
    return min(100, score)


def _score_budget(texto: str) -> int:
    """Aderência ao budget de 7 linhas (exceto abertura/diagnóstico)."""
    linhas = [l for l in texto.strip().split("\n") if l.strip()]
    n = len(linhas)
    if n <= 7:
        return 100
    elif n <= 10:
        return 70
    elif n <= 15:
        return 40
    elif n <= 20:
        return 20
    return 0


# ── Classe principal ────────────────────────────────────────────────────

class AutoAvaliador:
    """Avalia e rastreia a qualidade das respostas do agente."""

    DIMENSOES = ["especificidade", "evidencia", "mensurabilidade", "acao", "budget"]
    PESOS = {
        "especificidade": 0.30,
        "evidencia": 0.20,
        "mensurabilidade": 0.20,
        "acao": 0.20,
        "budget": 0.10,
    }

    def __init__(self, caminho: Path | None = None):
        self._caminho = caminho or AVALIACAO_PATH
        self._dados = self._carregar()

    def _carregar(self) -> dict[str, Any]:
        if self._caminho.exists():
            try:
                return json.loads(self._caminho.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"avaliacoes": [], "score_medio_7d": 0, "tendencia": "NOVA", "_versao": 1}

    def _salvar(self) -> None:
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        self._dados["_atualizado_em"] = datetime.now().isoformat(timespec="seconds")
        self._caminho.write_text(
            json.dumps(self._dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def avaliar_resposta(
        self,
        texto: str,
        contexto: dict | None = None,
        is_diagnostico: bool = False,
    ) -> dict[str, Any]:
        """Avalia uma resposta do agente em 5 dimensões.

        Args:
            texto: Texto completo da resposta do agente.
            contexto: Contexto opcional (disciplina, fase, etc.).
            is_diagnostico: Se True, relaxa o budget (diagnóstico é longo).

        Returns:
            Dict com scores por dimensão e score total.
        """
        dimensoes = {
            "especificidade": _score_especificidade(texto),
            "evidencia": _score_evidencia(texto),
            "mensurabilidade": _score_mensurabilidade(texto),
            "acao": _score_acao_concreta(texto),
            "budget": 100 if is_diagnostico else _score_budget(texto),
        }

        score_total = round(
            sum(dimensoes[d] * self.PESOS[d] for d in self.DIMENSOES)
        )

        # Sugestão de melhoria baseada na dimensão mais fraca
        mais_fraca = min(dimensoes, key=lambda d: dimensoes[d])
        sugestoes = {
            "especificidade": "Inclua tema, tempo, técnica, material e critério concretos",
            "evidencia": "Cite fonte: pesquisa, dado de prova ou artigo de lei",
            "mensurabilidade": "Adicione meta numérica mensurável",
            "acao": "Termine com uma ação concreta para AGORA",
            "budget": "Reduza para ≤7 linhas (seja cirúrgico)",
        }

        avaliacao = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "score_total": score_total,
            "dimensoes": dimensoes,
            "sugestao_melhoria": sugestoes.get(mais_fraca, ""),
            "dimensao_mais_fraca": mais_fraca,
        }

        self._dados.setdefault("avaliacoes", []).append(avaliacao)
        # Max 1000 avaliações
        if len(self._dados["avaliacoes"]) > 1000:
            self._dados["avaliacoes"] = self._dados["avaliacoes"][-1000:]

        self._atualizar_metricas()
        self._salvar()
        return avaliacao

    def _atualizar_metricas(self) -> None:
        """Atualiza score médio dos últimos 7 dias e tendência."""
        avaliacoes = self._dados.get("avaliacoes", [])
        if not avaliacoes:
            return

        hoje = date.today()
        limite = (hoje - timedelta(days=7)).isoformat()

        recentes = [
            a for a in avaliacoes
            if a.get("timestamp", "")[:10] >= limite
        ]

        if recentes:
            self._dados["score_medio_7d"] = round(
                sum(a["score_total"] for a in recentes) / len(recentes)
            )

        # Tendência: comparar primeira e segunda metade das últimas 20
        if len(avaliacoes) >= 6:
            ultimas = avaliacoes[-20:]
            meio = len(ultimas) // 2
            media_antiga = sum(a["score_total"] for a in ultimas[:meio]) / meio
            media_nova = sum(a["score_total"] for a in ultimas[meio:]) / (len(ultimas) - meio)
            if media_nova > media_antiga + 3:
                self._dados["tendencia"] = "SUBINDO"
            elif media_nova < media_antiga - 3:
                self._dados["tendencia"] = "CAINDO"
            else:
                self._dados["tendencia"] = "ESTAVEL"

    def historico_qualidade(self, n: int = 20) -> list[dict]:
        """Retorna as últimas N avaliações."""
        return list(reversed(self._dados.get("avaliacoes", [])[-n:]))

    def detectar_regressao(self) -> dict[str, Any] | None:
        """Detecta se houve regressão na qualidade das respostas.

        Returns:
            Dict com detalhes da regressão, ou None se tudo OK.
        """
        avaliacoes = self._dados.get("avaliacoes", [])
        if len(avaliacoes) < JANELA_REGRESSAO:
            return None

        recentes = avaliacoes[-JANELA_REGRESSAO:]
        media = sum(a["score_total"] for a in recentes) / len(recentes)

        if media < LIMIAR_REGRESSAO:
            # Encontrar dimensão que mais piorou
            dims_medias = {}
            for dim in self.DIMENSOES:
                dims_medias[dim] = round(
                    sum(a["dimensoes"].get(dim, 0) for a in recentes) / len(recentes)
                )

            pior_dim = min(dims_medias, key=lambda d: dims_medias[d])
            return {
                "alerta": True,
                "score_medio": round(media),
                "dimensao_critica": pior_dim,
                "score_dim_critica": dims_medias[pior_dim],
                "mensagem": (
                    f"⚠ Qualidade em regressão: score médio {media:.0f}/100 "
                    f"(últimas {JANELA_REGRESSAO} respostas). "
                    f"Dimensão crítica: {pior_dim} ({dims_medias[pior_dim]})"
                ),
            }
        return None

    def resumo_para_prompt(self) -> str:
        """Gera bloco para injetar no system prompt com auto-feedback."""
        avaliacoes = self._dados.get("avaliacoes", [])
        if len(avaliacoes) < 3:
            return ""

        ultimas = avaliacoes[-5:]
        media = sum(a["score_total"] for a in ultimas) / len(ultimas)

        # Encontrar dimensão mais fraca consistentemente
        dims_freq: dict[str, int] = {}
        for a in ultimas:
            fraca = a.get("dimensao_mais_fraca", "")
            if fraca:
                dims_freq[fraca] = dims_freq.get(fraca, 0) + 1

        dim_recorrente = max(dims_freq, key=dims_freq.get) if dims_freq else None

        linhas = [
            f"[AUTO_AVALIACAO] Score médio recente: {media:.0f}/100 · Tendência: {self._dados.get('tendencia', '?')}"
        ]
        if dim_recorrente and dims_freq.get(dim_recorrente, 0) >= 2:
            sugestoes = {
                "especificidade": "seja mais específico (tema+tempo+técnica+critério)",
                "evidencia": "cite mais fontes (pesquisa, prova, lei)",
                "mensurabilidade": "inclua metas numéricas",
                "acao": "termine sempre com ação concreta",
                "budget": "respostas mais curtas (≤7 linhas)",
            }
            linhas.append(f"  LEMBRETE: {sugestoes.get(dim_recorrente, '')}")

        regressao = self.detectar_regressao()
        if regressao:
            linhas.append(f"  {regressao['mensagem']}")

        return "\n".join(linhas)

    def estatisticas(self) -> dict[str, Any]:
        """Estatísticas gerais da auto-avaliação."""
        avaliacoes = self._dados.get("avaliacoes", [])
        if not avaliacoes:
            return {"total": 0, "score_medio": 0, "tendencia": "NOVA"}

        return {
            "total": len(avaliacoes),
            "score_medio": round(sum(a["score_total"] for a in avaliacoes) / len(avaliacoes)),
            "score_medio_7d": self._dados.get("score_medio_7d", 0),
            "tendencia": self._dados.get("tendencia", "?"),
            "ultimo_score": avaliacoes[-1]["score_total"],
        }
