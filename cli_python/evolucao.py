"""Memória Evolutiva — Diário de decisões e outcomes.

Registra cada prescrição do agente (estratégia + contexto), correlaciona
com o resultado obtido pelo candidato, e calcula a eficácia de cada
estratégia ao longo do tempo.

Uso:
    from evolucao import DiarioEvolucao

    diario = DiarioEvolucao()
    diario.registrar_decisao("retrieval_practice", "portugues", 55,
                              "20min RP + 15 questões CESGRANRIO")
    diario.registrar_outcome("portugues", 68)
    print(diario.ranking_estrategias())
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any


AQUI = Path(__file__).resolve().parent
DADOS_EVOLUCAO = AQUI / "dados" / "evolucao"
DIARIO_PATH = DADOS_EVOLUCAO / "diario.json"

# Estratégias conhecidas (o agente pode emitir qualquer uma)
ESTRATEGIAS_CONHECIDAS = [
    "retrieval_practice",
    "sq3r",
    "intercalacao",
    "elaboracao_interrogativa",
    "feynman",
    "cornell_notes",
    "mapa_mental",
    "dual_coding",
    "pomodoro",
    "pratica_deliberada",
    "simulacao_total",
    "anki",
    "questoes_cesgranrio",
    "revisao_espacada",
    "leitura_ativa",
]

# Regex para extrair a diretiva <<ESTRATEGIA: nome = contexto>>
_DIRETIVA_ESTRATEGIA = re.compile(
    r"<<\s*ESTRATEGIA\s*:\s*(\w+)\s*=\s*(.+?)\s*>>"
)

# Regex para extrair prescrições concretas do texto do agente
_PRESCRICAO_PATTERNS = [
    # "estude X" / "resolva Y" / "revise Z"
    re.compile(r"(?:estude|resolva|revise|pratique|faça|treine)\s+(.{10,80})", re.IGNORECASE),
    # "N min" / "Nh" / "N questões"
    re.compile(r"(\d+\s*(?:min|minutos?|h|horas?|questões|questoes))", re.IGNORECASE),
    # técnicas nomeadas
    re.compile(
        r"(Retrieval Practice|SQ3R|Intercala[cç][aã]o|Feynman|Cornell|"
        r"Mapa Mental|Dual Coding|Pomodoro|Pr[aá]tica Deliberada|"
        r"Anki|Simula[cç][aã]o|Repeti[cç][aã]o Espa[cç]ada)",
        re.IGNORECASE,
    ),
]


def _ler_diario() -> dict[str, Any]:
    """Lê o diário de evolução do disco."""
    if DIARIO_PATH.exists():
        try:
            return json.loads(DIARIO_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "decisoes": [],
        "estrategias_ranking": {},
        "_versao": 1,
        "_criado_em": datetime.now().isoformat(timespec="seconds"),
    }


def _gravar_diario(dados: dict[str, Any]) -> None:
    """Salva o diário no disco."""
    DADOS_EVOLUCAO.mkdir(parents=True, exist_ok=True)
    dados["_atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    DIARIO_PATH.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def extrair_estrategia_da_resposta(texto: str) -> tuple[str, str] | None:
    """Extrai diretiva <<ESTRATEGIA: nome = contexto>> do texto do agente."""
    m = _DIRETIVA_ESTRATEGIA.search(texto)
    if m:
        return m.group(1).lower().strip(), m.group(2).strip()
    return None


def extrair_prescricoes(texto: str) -> list[str]:
    """Extrai prescrições concretas do texto do agente (heurística)."""
    encontradas = []
    for pat in _PRESCRICAO_PATTERNS:
        for m in pat.finditer(texto):
            frag = m.group(1) if m.lastindex else m.group(0)
            frag = frag.strip().rstrip(".,;:")
            if frag and len(frag) > 3 and frag not in encontradas:
                encontradas.append(frag)
    return encontradas[:5]  # max 5 prescrições por resposta


def _normalizar_estrategia(nome: str) -> str:
    """Normaliza nome de estratégia para chave consistente."""
    mapa = {
        "retrieval practice": "retrieval_practice",
        "retrieval_practice": "retrieval_practice",
        "sq3r": "sq3r",
        "intercalação": "intercalacao",
        "intercalacao": "intercalacao",
        "feynman": "feynman",
        "cornell": "cornell_notes",
        "cornell notes": "cornell_notes",
        "mapa mental": "mapa_mental",
        "mapa_mental": "mapa_mental",
        "dual coding": "dual_coding",
        "dual_coding": "dual_coding",
        "pomodoro": "pomodoro",
        "prática deliberada": "pratica_deliberada",
        "pratica deliberada": "pratica_deliberada",
        "pratica_deliberada": "pratica_deliberada",
        "anki": "anki",
        "simulação": "simulacao_total",
        "simulacao": "simulacao_total",
        "simulacao_total": "simulacao_total",
        "repetição espaçada": "revisao_espacada",
        "repeticao espacada": "revisao_espacada",
        "revisao_espacada": "revisao_espacada",
        "questões cesgranrio": "questoes_cesgranrio",
        "questoes cesgranrio": "questoes_cesgranrio",
        "questoes_cesgranrio": "questoes_cesgranrio",
        "leitura ativa": "leitura_ativa",
        "leitura_ativa": "leitura_ativa",
    }
    return mapa.get(nome.lower().strip(), nome.lower().strip().replace(" ", "_"))


class DiarioEvolucao:
    """Gerencia o diário de decisões e outcomes do agente."""

    def __init__(self, caminho: Path | None = None):
        self._caminho = caminho or DIARIO_PATH
        self._dados = self._carregar()

    def _carregar(self) -> dict[str, Any]:
        if self._caminho.exists():
            try:
                return json.loads(self._caminho.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "decisoes": [],
            "estrategias_ranking": {},
            "_versao": 1,
            "_criado_em": datetime.now().isoformat(timespec="seconds"),
        }

    def _salvar(self) -> None:
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        self._dados["_atualizado_em"] = datetime.now().isoformat(timespec="seconds")
        self._caminho.write_text(
            json.dumps(self._dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @property
    def decisoes(self) -> list[dict]:
        return self._dados.get("decisoes", [])

    def registrar_decisao(
        self,
        estrategia: str,
        disciplina: str,
        acerto_atual: float | None,
        prescricao: str,
        fase: str | None = None,
        contexto_extra: dict | None = None,
    ) -> str:
        """Registra uma decisão/prescrição do agente.

        Returns:
            ID da decisão registrada.
        """
        decisao_id = f"d_{uuid.uuid4().hex[:8]}"
        decisao = {
            "id": decisao_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "estrategia": _normalizar_estrategia(estrategia),
            "disciplina": disciplina.lower().strip() if disciplina else "geral",
            "prescricao": prescricao[:200],
            "contexto": {
                "acerto_atual": acerto_atual,
                "fase": fase,
                **(contexto_extra or {}),
            },
            "outcome_esperado": None,
            "outcome_real": None,
            "eficacia": None,
        }
        self._dados.setdefault("decisoes", []).append(decisao)
        # Manter max 500 decisões (FIFO)
        if len(self._dados["decisoes"]) > 500:
            self._dados["decisoes"] = self._dados["decisoes"][-500:]
        self._salvar()
        return decisao_id

    def registrar_decisao_da_resposta(
        self,
        texto_resposta: str,
        perfil: dict,
    ) -> str | None:
        """Extrai estratégia e prescrições da resposta do agente e registra."""
        estr = extrair_estrategia_da_resposta(texto_resposta)
        prescricoes = extrair_prescricoes(texto_resposta)

        if not estr and not prescricoes:
            return None

        nome_estrategia = estr[0] if estr else (
            _normalizar_estrategia(prescricoes[0]) if prescricoes else "geral"
        )
        prescricao_texto = estr[1] if estr else "; ".join(prescricoes)

        # Tentar extrair disciplina do contexto
        disciplina = "geral"
        if estr:
            # A disciplina pode estar no contexto da diretiva
            for disc_known in ["portugues", "português", "rl", "matemat", "legisl",
                               "petrobras", "especif", "logica", "lógica"]:
                if disc_known in prescricao_texto.lower():
                    disciplina = disc_known
                    break

        hist = perfil.get("historico_acerto", {})
        acerto = hist.get(disciplina) if disciplina != "geral" else None

        return self.registrar_decisao(
            estrategia=nome_estrategia,
            disciplina=disciplina,
            acerto_atual=acerto,
            prescricao=prescricao_texto,
            fase=perfil.get("fase_atual"),
        )

    def registrar_outcome(
        self,
        disciplina: str,
        acerto_novo: float,
        questoes: int = 0,
    ) -> dict | None:
        """Correlaciona o outcome de uma sessão com a última decisão para essa disciplina.

        Returns:
            A decisão atualizada, ou None se não houver decisão pendente.
        """
        disc = disciplina.lower().strip() if disciplina else "geral"
        # Encontrar última decisão pendente (sem outcome) para essa disciplina
        pendentes = [
            d for d in reversed(self._dados.get("decisoes", []))
            if d.get("outcome_real") is None
            and (d.get("disciplina") == disc or d.get("disciplina") == "geral")
        ]
        if not pendentes:
            return None

        decisao = pendentes[0]
        acerto_anterior = decisao["contexto"].get("acerto_atual")
        delta = round(acerto_novo - acerto_anterior, 1) if acerto_anterior is not None else None

        decisao["outcome_real"] = {
            "acerto": acerto_novo,
            "delta": delta,
            "questoes": questoes,
            "data": date.today().isoformat(),
        }

        # Calcular eficácia: 1.0 se melhorou, 0.5 se manteve, 0.0 se piorou
        if delta is not None:
            if delta > 5:
                decisao["eficacia"] = 1.0
            elif delta > 0:
                decisao["eficacia"] = 0.75
            elif delta > -5:
                decisao["eficacia"] = 0.5
            else:
                decisao["eficacia"] = 0.0
        else:
            # Sem baseline → eficácia neutra
            decisao["eficacia"] = 0.5 if acerto_novo >= 60 else 0.25

        # Atualizar ranking
        self._atualizar_ranking(decisao["estrategia"], decisao["eficacia"])
        self._salvar()
        return decisao

    def _atualizar_ranking(self, estrategia: str, eficacia: float) -> None:
        """Atualiza o ranking incremental de estratégias."""
        ranking = self._dados.setdefault("estrategias_ranking", {})
        entry = ranking.setdefault(estrategia, {"usos": 0, "eficacia_total": 0.0, "eficacia_media": 0.0})
        entry["usos"] += 1
        entry["eficacia_total"] = round(entry.get("eficacia_total", 0.0) + eficacia, 2)
        entry["eficacia_media"] = round(entry["eficacia_total"] / entry["usos"], 2)

    def calcular_eficacia(self, estrategia: str | None = None) -> dict[str, Any]:
        """Calcula eficácia de uma estratégia ou de todas."""
        decisoes = [
            d for d in self._dados.get("decisoes", [])
            if d.get("eficacia") is not None
        ]
        if estrategia:
            decisoes = [d for d in decisoes if d["estrategia"] == _normalizar_estrategia(estrategia)]

        if not decisoes:
            return {"n": 0, "eficacia_media": 0.0, "melhor_disciplina": None}

        media = sum(d["eficacia"] for d in decisoes) / len(decisoes)

        # Melhor disciplina para essa estratégia
        por_disc: dict[str, list[float]] = {}
        for d in decisoes:
            por_disc.setdefault(d["disciplina"], []).append(d["eficacia"])

        melhor_disc = max(por_disc, key=lambda k: sum(por_disc[k]) / len(por_disc[k])) if por_disc else None

        return {
            "n": len(decisoes),
            "eficacia_media": round(media, 2),
            "melhor_disciplina": melhor_disc,
        }

    def ranking_estrategias(self, top_n: int = 10) -> list[dict[str, Any]]:
        """Retorna as top-N estratégias por eficácia."""
        ranking = self._dados.get("estrategias_ranking", {})
        if not ranking:
            return []

        items = [
            {"estrategia": k, **v}
            for k, v in ranking.items()
            if v.get("usos", 0) >= 2  # mínimo 2 usos para rankear
        ]
        items.sort(key=lambda x: x.get("eficacia_media", 0), reverse=True)
        return items[:top_n]

    def decisoes_recentes(self, n: int = 10) -> list[dict]:
        """Retorna as últimas N decisões."""
        return list(reversed(self._dados.get("decisoes", [])[-n:]))

    def resumo_para_prompt(self) -> str:
        """Gera texto para injetar no system prompt com insights de evolução."""
        ranking = self.ranking_estrategias(5)
        if not ranking:
            return ""

        linhas = ["[ESTRATEGIAS_COMPROVADAS] (ranking por eficácia com este candidato)"]
        for i, r in enumerate(ranking, 1):
            ef = r.get("eficacia_media", 0)
            emoji = "🟢" if ef >= 0.7 else ("🟡" if ef >= 0.5 else "🔴")
            linhas.append(
                f"  {i}. {emoji} {r['estrategia']} — eficácia {ef:.0%} ({r['usos']} usos)"
            )

        # Adicionar insights de decisões recentes
        recentes = self.decisoes_recentes(3)
        if recentes:
            linhas.append("")
            linhas.append("[DECISOES_RECENTES] (suas últimas prescrições e outcomes)")
            for d in recentes:
                outcome = d.get("outcome_real")
                if outcome:
                    delta = outcome.get("delta", "?")
                    linhas.append(
                        f"  • {d['estrategia']} em {d['disciplina']}: "
                        f"delta {'+' if isinstance(delta, (int, float)) and delta > 0 else ''}{delta}pp"
                    )
                else:
                    linhas.append(
                        f"  • {d['estrategia']} em {d['disciplina']}: aguardando outcome"
                    )

        return "\n".join(linhas)

    def estatisticas(self) -> dict[str, Any]:
        """Estatísticas gerais do diário."""
        decisoes = self._dados.get("decisoes", [])
        com_outcome = [d for d in decisoes if d.get("outcome_real") is not None]
        ranking = self._dados.get("estrategias_ranking", {})

        return {
            "total_decisoes": len(decisoes),
            "com_outcome": len(com_outcome),
            "sem_outcome": len(decisoes) - len(com_outcome),
            "estrategias_distintas": len(ranking),
            "eficacia_global": round(
                sum(d["eficacia"] for d in com_outcome) / len(com_outcome), 2
            ) if com_outcome else 0.0,
            "top_estrategia": (
                max(ranking, key=lambda k: ranking[k].get("eficacia_media", 0))
                if ranking else None
            ),
        }
