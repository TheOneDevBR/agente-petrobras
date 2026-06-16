"""Radar Instagram — monitora hashtags do tema via Instagram Graph API (oficial).

NÃO faz scraping nem login (isso viola os Termos do Instagram e arrisca a conta).
Usa a API Graph oficial da Meta: exige uma conta Instagram Business/Creator
vinculada a uma Página do Facebook, um app Meta e um token de acesso. O token é
SEU e vem por variável de ambiente — nunca é versionado.

Variáveis de ambiente:
    INSTAGRAM_TOKEN        token de acesso (obrigatório)
    INSTAGRAM_IG_USER_ID   id da conta IG Business usada como user_id (obrigatório)
    INSTAGRAM_TAGS         hashtags (csv) — default abaixo
    INSTAGRAM_API_VERSION  versão da Graph API (default v21.0)

Uso:
    python instagram.py --tags concursopetrobras,cesgranrio
    python instagram.py            # usa INSTAGRAM_TAGS ou o default
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import requests

AQUI = Path(__file__).resolve().parent
TAGS_DEFAULT = ["concursopetrobras", "petrobrasconcurso", "concursospetrobras", "cesgranrio"]


def _api_base() -> str:
    return f"https://graph.facebook.com/{os.environ.get('INSTAGRAM_API_VERSION', 'v21.0')}"


def _cfg() -> tuple[str, str]:
    return os.environ.get("INSTAGRAM_TOKEN", ""), os.environ.get("INSTAGRAM_IG_USER_ID", "")


def disponivel() -> bool:
    """True se token + id da conta Business estiverem configurados."""
    tok, uid = _cfg()
    return bool(tok and uid)


def _get(url: str, params: dict) -> dict:
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def buscar_hashtag(tag: str, limite: int = 10) -> list[dict[str, Any]]:
    """Posts públicos recentes de uma hashtag, via Graph API. [] se não configurado."""
    tok, uid = _cfg()
    if not (tok and uid):
        return []
    api = _api_base()
    try:
        busca = _get(f"{api}/ig_hashtag_search", {"user_id": uid, "q": tag, "access_token": tok})
        hid = (busca.get("data") or [{}])[0].get("id")
        if not hid:
            return []
        media = _get(
            f"{api}/{hid}/recent_media",
            {"user_id": uid, "fields": "caption,permalink,timestamp,media_type", "access_token": tok},
        )
    except Exception as e:
        return [{"tag": tag, "erro": str(e)}]
    out: list[dict[str, Any]] = []
    for m in (media.get("data") or [])[:limite]:
        out.append({
            "tag": tag,
            "caption": (m.get("caption") or "")[:280],
            "permalink": m.get("permalink", ""),
            "timestamp": m.get("timestamp", ""),
            "tipo": m.get("media_type", ""),
        })
    return out


def monitorar(tags: list[str] | None = None, limite: int = 10) -> list[dict[str, Any]]:
    """Agrega posts recentes de várias hashtags, deduplicando por permalink."""
    tags = tags or TAGS_DEFAULT
    vistos: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for t in tags:
        for p in buscar_hashtag(t, limite):
            link = p.get("permalink")
            if link and link not in vistos:
                vistos.add(link)
                uniq.append(p)
    return uniq


def buscar_perfil(username: str, limite: int = 10) -> list[dict[str, Any]]:
    """Posts públicos recentes de um perfil PROFISSIONAL (Business/Creator) via
    Business Discovery — caminho mais simples que a busca de hashtag. [] se não
    configurado. O perfil-alvo precisa ser conta profissional (não pessoal)."""
    tok, uid = _cfg()
    if not (tok and uid):
        return []
    user = username.lstrip("@").strip()
    api = _api_base()
    campo = (
        f"business_discovery.username({user})"
        f"{{username,media.limit({limite}){{caption,permalink,timestamp,media_type}}}}"
    )
    try:
        data = _get(f"{api}/{uid}", {"fields": campo, "access_token": tok})
    except Exception as e:
        return [{"perfil": user, "erro": str(e)}]
    media = ((data.get("business_discovery") or {}).get("media") or {}).get("data", [])
    out: list[dict[str, Any]] = []
    for m in media[:limite]:
        out.append({
            "perfil": user,
            "caption": (m.get("caption") or "")[:280],
            "permalink": m.get("permalink", ""),
            "timestamp": m.get("timestamp", ""),
            "tipo": m.get("media_type", ""),
        })
    return out


def monitorar_perfis(usernames: list[str], limite: int = 10) -> list[dict[str, Any]]:
    """Agrega posts recentes de vários perfis, deduplicando por permalink."""
    vistos: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for u in usernames:
        for p in buscar_perfil(u, limite):
            link = p.get("permalink")
            if link and link not in vistos:
                vistos.add(link)
                uniq.append(p)
    return uniq


def gravar_radar(posts: list[dict[str, Any]], vault: Path | None = None) -> Path:
    """Grava uma nota Markdown no vault (a inteligência que o coach já lê)."""
    base = Path(vault or os.environ.get("AGENTE_VAULT", AQUI.parent / "Obsidian_Vault"))
    pasta = base / "Petrobras" / "Inteligencia"
    pasta.mkdir(parents=True, exist_ok=True)
    nome = pasta / "_RADAR_INSTAGRAM.md"
    linhas = [
        f"# Radar Instagram — {date.today().isoformat()}",
        "",
        "_Monitoramento de hashtags do tema via Instagram Graph API (oficial)._",
        "",
    ]
    for p in posts:
        cap = (p.get("caption") or "").replace("\n", " ").strip()
        rotulo = f"#{p['tag']}" if p.get("tag") else f"@{p.get('perfil', '')}"
        linhas.append(
            f"- **{rotulo}** · {p.get('timestamp', '')[:10]} — {cap[:160]}\n"
            f"  {p.get('permalink', '')}"
        )
    if not posts:
        linhas.append("_(sem posts — verifique o token/hashtags)_")
    nome.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return nome


def main() -> None:
    import argparse
    import sys
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="Radar Instagram (Graph API oficial — sem scraping)")
    ap.add_argument("--tags", help="hashtags separadas por vírgula (busca por hashtag)")
    ap.add_argument("--perfis", help="@perfis separados por vírgula (Business Discovery)")
    ap.add_argument("--limite", type=int, default=10, help="posts por hashtag/perfil")
    args = ap.parse_args()

    if not disponivel():
        print("Instagram não configurado (sem scraping/login — só API oficial).")
        print("Defina INSTAGRAM_TOKEN e INSTAGRAM_IG_USER_ID. Passos:")
        print("  1. Converta seu perfil para Conta Business/Creator e vincule a uma Página do Facebook.")
        print("  2. Crie um app em developers.facebook.com e gere um token (Instagram Graph API).")
        print("  3. Exporte: $env:INSTAGRAM_TOKEN=... ; $env:INSTAGRAM_IG_USER_ID=...")
        return

    perfis_env = os.environ.get("INSTAGRAM_PERFIS", "")
    if args.perfis or perfis_env:
        fonte = args.perfis or perfis_env
        perfis = [p.strip() for p in fonte.split(",") if p.strip()]
        posts = monitorar_perfis(perfis, args.limite)
    else:
        if args.tags:
            tags = [t.strip().lstrip("#") for t in args.tags.split(",") if t.strip()]
        elif os.environ.get("INSTAGRAM_TAGS"):
            tags = [t.strip().lstrip("#") for t in os.environ["INSTAGRAM_TAGS"].split(",") if t.strip()]
        else:
            tags = None
        posts = monitorar(tags, args.limite)

    nome = gravar_radar(posts)
    print(f"{len(posts)} post(s) coletado(s) → {nome}")


if __name__ == "__main__":
    main()
