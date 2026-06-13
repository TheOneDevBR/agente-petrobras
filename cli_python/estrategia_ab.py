"""Estratégia A/B — Testes pedagógicos adaptativos.

Mantém experimentos A/B entre estratégias de estudo. Mede qual funciona
melhor para o candidato específico com base em outcomes reais.

Uso:
    from estrategia_ab import GerenciadorAB

    ab = GerenciadorAB()
    ab.criar_experimento("Retrieval Practice", "SQ3R",
                         "disciplinas com acerto < 60%")
    estrategia = ab.selecionar_estrategia("portugues", 55)
    ab.registrar_resultado("portugues", 68)
"""

from __future__ import annotations

import json
import math
import random
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any


AQUI = Path(__file__).resolve().parent
DADOS_EVOLUCAO = AQUI / "dados" / "evolucao"
EXPERIMENTOS_PATH = DADOS_EVOLUCAO / "experimentos.json"

# Mínimo de amostras por grupo para considerar conclusivo
MIN_AMOSTRAS = 3
# Confiança mínima para declarar vencedor
CONFIANCA_MINIMA = 0.75


def _ler_experimentos() -> dict[str, Any]:
    if EXPERIMENTOS_PATH.exists():
        try:
            return json.loads(EXPERIMENTOS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"experimentos": [], "conclusoes": [], "_versao": 1}


def _gravar_experimentos(dados: dict[str, Any]) -> None:
    DADOS_EVOLUCAO.mkdir(parents=True, exist_ok=True)
    dados["_atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    EXPERIMENTOS_PATH.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _teste_t_simples(grupo_a: list[float], grupo_b: list[float]) -> float:
    """Teste t de Student simplificado. Retorna confiança 0–1."""
    if len(grupo_a) < 2 or len(grupo_b) < 2:
        return 0.0

    na, nb = len(grupo_a), len(grupo_b)
    ma = sum(grupo_a) / na
    mb = sum(grupo_b) / nb

    va = sum((x - ma) ** 2 for x in grupo_a) / (na - 1) if na > 1 else 0
    vb = sum((x - mb) ** 2 for x in grupo_b) / (nb - 1) if nb > 1 else 0

    se = math.sqrt(va / na + vb / nb) if (va / na + vb / nb) > 0 else 0.001
    t = abs(ma - mb) / se

    # Aproximação da confiança baseada em t e graus de liberdade
    df = na + nb - 2
    if df <= 0:
        return 0.0

    # Sigmoid simples como proxy de p-valor
    confianca = 1 - 1 / (1 + math.exp(0.5 * (t - 2)))
    return round(min(1.0, max(0.0, confianca)), 2)


class GerenciadorAB:
    """Gerencia experimentos A/B entre estratégias pedagógicas."""

    def __init__(self, caminho: Path | None = None):
        self._caminho = caminho or EXPERIMENTOS_PATH
        self._dados = self._carregar()

    def _carregar(self) -> dict[str, Any]:
        if self._caminho.exists():
            try:
                return json.loads(self._caminho.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"experimentos": [], "conclusoes": [], "_versao": 1}

    def _salvar(self) -> None:
        self._caminho.parent.mkdir(parents=True, exist_ok=True)
        self._dados["_atualizado_em"] = datetime.now().isoformat(timespec="seconds")
        self._caminho.write_text(
            json.dumps(self._dados, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @property
    def experimentos(self) -> list[dict]:
        return self._dados.get("experimentos", [])

    def criar_experimento(
        self,
        estrategia_a: str,
        estrategia_b: str,
        condicao: str,
        hipotese: str | None = None,
    ) -> str:
        """Cria um novo experimento A/B.

        Args:
            estrategia_a: Nome da primeira estratégia.
            estrategia_b: Nome da segunda estratégia.
            condicao: Em que contexto se aplica (ex: "disciplinas < 60%").
            hipotese: Hipótese do experimento.

        Returns:
            ID do experimento criado.
        """
        exp_id = f"exp_{uuid.uuid4().hex[:6]}"
        experimento = {
            "id": exp_id,
            "criado_em": datetime.now().isoformat(timespec="seconds"),
            "hipotese": hipotese or f"{estrategia_a} > {estrategia_b} para {condicao}",
            "condicao": condicao,
            "grupo_a": {
                "estrategia": estrategia_a.lower().replace(" ", "_"),
                "resultados": [],
            },
            "grupo_b": {
                "estrategia": estrategia_b.lower().replace(" ", "_"),
                "resultados": [],
            },
            "vencedor": None,
            "confianca": 0.0,
            "status": "ATIVO",
            "grupo_atual": "a",  # alterna entre a/b
        }
        self._dados.setdefault("experimentos", []).append(experimento)
        self._salvar()
        return exp_id

    def _encontrar_ativo(self, disciplina: str | None = None) -> dict | None:
        """Encontra experimento ativo, opcionalmente filtrado por relevância."""
        for exp in self._dados.get("experimentos", []):
            if exp.get("status") == "ATIVO":
                return exp
        return None

    def selecionar_estrategia(
        self,
        disciplina: str,
        acerto_atual: float | None = None,
    ) -> dict[str, Any] | None:
        """Seleciona qual estratégia usar baseado no experimento ativo.

        Returns:
            Dict com 'estrategia' e 'experimento_id', ou None se sem experimento.
        """
        exp = self._encontrar_ativo(disciplina)
        if not exp:
            return None

        # Alternar entre grupo A e B
        grupo = exp.get("grupo_atual", "a")
        grupo_key = f"grupo_{grupo}"
        estrategia = exp[grupo_key]["estrategia"]

        # Preparar próximo grupo (alternância)
        exp["grupo_atual"] = "b" if grupo == "a" else "a"
        self._salvar()

        return {
            "estrategia": estrategia,
            "experimento_id": exp["id"],
            "grupo": grupo,
            "hipotese": exp["hipotese"],
        }

    def registrar_resultado(
        self,
        experimento_id: str,
        grupo: str,
        acerto: float,
    ) -> dict | None:
        """Registra resultado de uma sessão no experimento.

        Args:
            experimento_id: ID do experimento.
            grupo: "a" ou "b".
            acerto: Percentual de acerto obtido.

        Returns:
            O experimento atualizado, ou None se não encontrado.
        """
        exp = None
        for e in self._dados.get("experimentos", []):
            if e["id"] == experimento_id:
                exp = e
                break

        if not exp or exp.get("status") != "ATIVO":
            return None

        grupo_key = f"grupo_{grupo}"
        exp[grupo_key]["resultados"].append(round(acerto, 1))

        # Verificar se já temos dados suficientes
        ra = exp["grupo_a"]["resultados"]
        rb = exp["grupo_b"]["resultados"]

        if len(ra) >= MIN_AMOSTRAS and len(rb) >= MIN_AMOSTRAS:
            confianca = _teste_t_simples(ra, rb)
            exp["confianca"] = confianca

            ma = sum(ra) / len(ra)
            mb = sum(rb) / len(rb)

            if confianca >= CONFIANCA_MINIMA:
                exp["vencedor"] = exp["grupo_a"]["estrategia"] if ma > mb else exp["grupo_b"]["estrategia"]
                exp["status"] = "CONCLUIDO"
                exp["concluido_em"] = datetime.now().isoformat(timespec="seconds")

                # Registrar conclusão
                self._dados.setdefault("conclusoes", []).append({
                    "experimento_id": exp["id"],
                    "vencedor": exp["vencedor"],
                    "confianca": confianca,
                    "media_a": round(ma, 1),
                    "media_b": round(mb, 1),
                    "n_a": len(ra),
                    "n_b": len(rb),
                    "data": date.today().isoformat(),
                })

        self._salvar()
        return exp

    def conclusoes(self) -> list[dict]:
        """Retorna conclusões de todos os experimentos finalizados."""
        return self._dados.get("conclusoes", [])

    def experimentos_ativos(self) -> list[dict]:
        """Retorna experimentos ativos."""
        return [e for e in self._dados.get("experimentos", []) if e.get("status") == "ATIVO"]

    def resumo_para_prompt(self) -> str:
        """Gera texto para injetar no system prompt."""
        conclusoes = self.conclusoes()
        ativos = self.experimentos_ativos()

        if not conclusoes and not ativos:
            return ""

        linhas = []

        if conclusoes:
            linhas.append("[EXPERIMENTOS_CONCLUIDOS] (resultados de A/B tests com este candidato)")
            for c in conclusoes[-5:]:
                linhas.append(
                    f"  ✓ {c['vencedor']} venceu (confiança {c['confianca']:.0%}) "
                    f"— médias {c.get('media_a', '?')}% vs {c.get('media_b', '?')}%"
                )

        if ativos:
            linhas.append("[EXPERIMENTO_ATIVO] (teste em andamento)")
            for exp in ativos[:2]:
                grupo = exp.get("grupo_atual", "a")
                grupo_key = f"grupo_{grupo}"
                linhas.append(
                    f"  Testando: {exp['hipotese']}"
                )
                linhas.append(
                    f"  → Use a estratégia '{exp[grupo_key]['estrategia']}' nesta prescrição"
                )

        return "\n".join(linhas)

    def estatisticas(self) -> dict[str, Any]:
        """Estatísticas gerais dos experimentos."""
        exps = self._dados.get("experimentos", [])
        return {
            "total": len(exps),
            "ativos": len([e for e in exps if e.get("status") == "ATIVO"]),
            "concluidos": len([e for e in exps if e.get("status") == "CONCLUIDO"]),
            "conclusoes": len(self._dados.get("conclusoes", [])),
        }

    def propor_experimento_padrao(self, perfil: dict) -> dict | None:
        """Propõe um experimento padrão baseado no perfil do candidato.

        Returns:
            Dict com a proposta, ou None se já há experimento ativo.
        """
        if self.experimentos_ativos():
            return None  # já tem um ativo

        fase = perfil.get("fase_atual", "FUNDACAO")
        hist = perfil.get("historico_acerto", {})

        # Identificar disciplinas fracas
        fracas = [d for d, p in hist.items() if isinstance(p, (int, float)) and p < 60]

        if fase in ("FUNDACAO", "DOMINIO") and fracas:
            return {
                "estrategia_a": "retrieval_practice",
                "estrategia_b": "sq3r",
                "condicao": f"disciplinas com acerto < 60% ({', '.join(fracas[:3])})",
                "hipotese": f"Retrieval Practice > SQ3R para disciplinas fracas (fase {fase})",
            }
        elif fase in ("CONSOLIDACAO", "SPRINT"):
            return {
                "estrategia_a": "pratica_deliberada",
                "estrategia_b": "simulacao_total",
                "condicao": "consolidação pré-prova",
                "hipotese": "Prática Deliberada > Simulação Total para consolidar",
            }

        return {
            "estrategia_a": "intercalacao",
            "estrategia_b": "pomodoro",
            "condicao": "sessões longas (>90min)",
            "hipotese": "Intercalação > Pomodoro para sessões longas",
        }
