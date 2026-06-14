"""Descoberta de Fontes — o agente aprende NOVOS sites sozinho.

A cada coleta, observa os domínios reais que apareceram na busca, descarta
ruído (login/redes/buscadores genéricos) e o que já é conhecido, e acumula a
recorrência dos demais em dados/fontes_descobertas.json. Domínios que recorrem
(>= N vezes) são "promovidos" e passam a ser realimentados nas buscas futuras —
fechando o laço: achou site pertinente → vira fonte do agente.

Uso:
    from descoberta import registrar, promovidas, relatorio
    registrar(urls_reais, contexto="noticias-concurso")
    novos = promovidas()            # domínios a usar em buscas futuras
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_DIR = Path(__file__).resolve().parent
_STORE = _DIR / "dados" / "fontes_descobertas.json"
_FONTES = _DIR / "coletor" / "fontes.json"

# Ruído: login, redes sociais, buscadores, encurtadores, genéricos.
DENYLIST = (
    "google.", "bing.", "yahoo.", "duckduckgo.", "microsoft.", "live.com",
    "facebook.", "instagram.", "twitter.", "x.com", "linkedin.", "pinterest.",
    "reddit.", "tiktok.", "whatsapp.", "t.me", "telegram.",
    "wikipedia.", "wikimedia.", "amazon.", "apple.", "play.google",
    "bit.ly", "tinyurl", "scribd.com",  # scribd: paywall/login
)

MIN_PROMOCAO = 3  # ocorrências para promover um domínio a fonte


def extrair_dominio(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


def _eh_ruido(dom: str) -> bool:
    return (not dom) or any(j in dom for j in DENYLIST)


def _dominios_conhecidos() -> set[str]:
    """Domínios já listados nos beats de fontes.json."""
    conhecidos: set[str] = set()
    if _FONTES.exists():
        try:
            fontes = json.loads(_FONTES.read_text(encoding="utf-8"))
            for b in fontes.get("beats", []):
                for d in b.get("dominios_sugeridos", []):
                    conhecidos.add(d.lower().removeprefix("www."))
        except (json.JSONDecodeError, OSError):
            pass
    return conhecidos


# ─── Store ───────────────────────────────────────────────────────────────────

def carregar(caminho: Path | None = None) -> dict[str, Any]:
    caminho = caminho or _STORE
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def salvar(estado: dict[str, Any], caminho: Path | None = None) -> None:
    caminho = caminho or _STORE
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")


def registrar(urls: list[str], contexto: str = "",
              estado: dict[str, Any] | None = None, persistir: bool = True,
              caminho: Path | None = None) -> list[str]:
    """Observa domínios novos e relevantes. Retorna os domínios recém-vistos.

    Filtra ruído e domínios já conhecidos (fontes.json). Acumula ocorrências,
    contextos (beats) e um exemplo de URL por domínio.
    """
    proprio = estado is None
    estado = estado if estado is not None else carregar(caminho)
    conhecidos = _dominios_conhecidos()
    novos: list[str] = []
    for url in urls:
        dom = extrair_dominio(url)
        if _eh_ruido(dom) or dom in conhecidos:
            continue
        reg = estado.setdefault(dom, {"ocorrencias": 0, "contextos": [], "exemplo": url, "promovida": False})
        reg["ocorrencias"] += 1
        if contexto and contexto not in reg["contextos"]:
            reg["contextos"].append(contexto)
        reg.setdefault("exemplo", url)
        if dom not in novos:
            novos.append(dom)
        if reg["ocorrencias"] >= MIN_PROMOCAO:
            reg["promovida"] = True
    if proprio and persistir and novos:
        salvar(estado, caminho)
    return novos


def promovidas(estado: dict[str, Any] | None = None, limite: int = 8,
               caminho: Path | None = None) -> list[str]:
    """Domínios promovidos (recorrentes), ordenados por ocorrência — para
    realimentar buscas futuras."""
    estado = estado if estado is not None else carregar(caminho)
    proms = [(d, r) for d, r in estado.items() if r.get("promovida")]
    proms.sort(key=lambda dr: -dr[1].get("ocorrencias", 0))
    return [d for d, _ in proms[:limite]]


def relatorio(estado: dict[str, Any] | None = None, caminho: Path | None = None) -> str:
    estado = estado if estado is not None else carregar(caminho)
    if not estado:
        return "Nenhuma fonte nova descoberta ainda."
    itens = sorted(estado.items(), key=lambda dr: -dr[1].get("ocorrencias", 0))
    linhas = [
        "══════════════════════════════════════════════════",
        "     🛰️  FONTES DESCOBERTAS (auto-aprendidas)",
        "══════════════════════════════════════════════════",
        "",
        f"  Domínios novos: {len(estado)}  ·  promovidos: {sum(1 for _, r in itens if r.get('promovida'))}",
        "",
    ]
    for dom, r in itens[:20]:
        marca = "⭐" if r.get("promovida") else "  "
        ctx = ",".join(r.get("contextos", [])[:3])
        linhas.append(f"  {marca} {dom:34s} ({r.get('ocorrencias', 0)}x) [{ctx}]")
    linhas += ["", "══════════════════════════════════════════════════"]
    return "\n".join(linhas)


__all__ = [
    "extrair_dominio", "registrar", "promovidas", "relatorio",
    "carregar", "salvar", "DENYLIST", "MIN_PROMOCAO",
]
