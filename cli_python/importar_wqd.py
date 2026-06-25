"""Importador de questões do WQD (wqd.com.br) — dados REAIS via API oficial do app.

O WQD é AngularJS + AWS API Gateway + Cognito + ElasticSearch. A busca de
questões exige um usuário logado (o app lê o claim ``locale`` do idToken Cognito
e o envia no corpo; sem ele a API responde ``null``). Este módulo:

1. Autentica no Cognito (User Pool) com USER_PASSWORD_AUTH via HTTP puro.
2. Extrai o ``locale`` do idToken.
3. Pagina o endpoint ``/pesquisa`` filtrando por banca/órgão.
4. Converte para o schema do projeto e importa (dedupe por hash) via
   ``importar_questoes.importar`` — nada inventado.

Credenciais (NUNCA no código/chat) — coloque no .env (gitignorado):
    AGENTE_WQD_USER=seu_email
    AGENTE_WQD_PASS=sua_senha

Uso:
    python importar_wqd.py --probe            # loga e mostra a ESTRUTURA da resposta
    python importar_wqd.py --banca CESGRANRIO --paginas 5
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except (AttributeError, ValueError):
    pass

# ── Constantes da recon (públicas, vindas dos bundles JS do app) ─────────────
COGNITO_REGION = "us-east-1"
COGNITO_CLIENT_ID = "3cqajauqdic4lrca1glork88ok"
COGNITO_IDP_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
PESQUISA_URL = "https://af9ntb3def.execute-api.us-east-1.amazonaws.com/pesquisa"
TIMEOUT = 40


class WQDError(Exception):
    pass


# ── Cognito (USER_PASSWORD_AUTH via HTTP puro) ───────────────────────────────
def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decodifica o payload (claims) de um JWT sem verificar assinatura."""
    try:
        meio = token.split(".")[1]
        meio += "=" * (-len(meio) % 4)  # padding base64url
        return json.loads(base64.urlsafe_b64decode(meio))
    except Exception as e:
        raise WQDError(f"idToken inválido: {e}")


def cognito_login(user: str, senha: str) -> tuple[str, str]:
    """Autentica e retorna (id_token, locale). Usa USER_PASSWORD_AUTH.

    Se o app client não permitir esse fluxo (usa SRP), a API retorna um erro
    claro — nesse caso é preciso o fluxo SRP (pycognito).
    """
    if not user or not senha:
        raise WQDError("Defina AGENTE_WQD_USER e AGENTE_WQD_PASS no .env.")
    payload = {
        "AuthFlow": "USER_PASSWORD_AUTH",
        "ClientId": COGNITO_CLIENT_ID,
        "AuthParameters": {"USERNAME": user, "PASSWORD": senha},
    }
    try:
        r = requests.post(
            COGNITO_IDP_URL, json=payload, timeout=TIMEOUT,
            headers={
                "Content-Type": "application/x-amz-json-1.1",
                "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
            },
        )
    except requests.RequestException as e:
        raise WQDError(f"Falha de rede no Cognito: {e}")
    if r.status_code != 200:
        msg = r.json().get("message", r.text[:200]) if r.content else r.text[:200]
        if "USER_PASSWORD_AUTH" in msg or "not enabled" in msg:
            raise WQDError(
                "O app client do WQD não habilita USER_PASSWORD_AUTH (usa SRP). "
                "Preciso adicionar o fluxo SRP (instalar pycognito) para logar."
            )
        raise WQDError(f"Login falhou ({r.status_code}): {msg}")
    res = r.json().get("AuthenticationResult") or {}
    id_token = res.get("IdToken")
    if not id_token:
        raise WQDError(f"Sem IdToken na resposta: {json.dumps(r.json())[:200]}")
    locale = _decode_jwt_payload(id_token).get("locale", "")
    return id_token, locale


# ── Busca ────────────────────────────────────────────────────────────────────
def montar_body(locale: str, *, q: str = "", start: int = 0, banca: str = "",
                disciplina: str = "", ano: str = "", nivel: str = "",
                classe: str = "concursos") -> dict[str, Any]:
    """Monta o corpo do POST /pesquisa (12 campos, como o app envia)."""
    return {
        "q": q, "start": start, "locale": locale, "disciplina": disciplina,
        "banca": banca, "ano": ano, "nivel": nivel, "tipo": "",
        "checkFavorito": "false", "questoesCertasErradas": "",
        "classe": classe, "assinante": "true",
    }


def pesquisar(body: dict[str, Any], id_token: str = "") -> Any:
    """POST /pesquisa. Retorna o JSON (pode ser None se filtros não casarem)."""
    headers = {"Content-Type": "application/json", "Origin": "https://wqd.com.br"}
    if id_token:
        headers["Authorization"] = id_token
    try:
        r = requests.post(PESQUISA_URL, json=body, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        raise WQDError(f"Falha na busca: {e}")
    return r.json()


# ── Conversão para o schema do projeto ───────────────────────────────────────
_LETRAS = "ABCDE"


def _achar_lista_questoes(resp: Any) -> list[dict]:
    """Localiza a lista de questões na resposta (schema do ES descoberto após o
    probe). Defensivo: procura hits/itens com enunciado + alternativas."""
    if not isinstance(resp, dict):
        return []
    # caminhos prováveis (ES): data.hits.hits[]._source, data.questoes, etc.
    for caminho in (("data", "hits", "hits"), ("hits", "hits"),
                    ("data", "questoes"), ("questoes",), ("data", "results")):
        cur: Any = resp
        for k in caminho:
            cur = cur.get(k) if isinstance(cur, dict) else None
            if cur is None:
                break
        if isinstance(cur, list) and cur:
            return [h.get("_source", h) if isinstance(h, dict) else h for h in cur]
    return []


def converter_questao(item: dict) -> dict[str, Any] | None:
    """Converte um item do WQD para o schema do store. Só aceita com gabarito.

    Tolerante a nomes de campo (finalizado após o probe ver a estrutura real).
    """
    def g(*nomes):
        for n in nomes:
            if isinstance(item.get(n), (str, int, list)) and item.get(n) not in ("", None):
                return item[n]
        return None

    enun = g("enunciado", "pergunta", "texto", "questao", "comando")
    alts = g("alternativas", "opcoes", "options", "items")
    correta = g("gabarito", "correta", "resposta", "alternativaCorreta")
    if not (enun and isinstance(alts, list) and len(alts) >= 2 and correta is not None):
        return None
    opcoes = [a.get("texto", a) if isinstance(a, dict) else a for a in alts]
    # correta pode ser letra ('C'), índice (2) ou id
    if isinstance(correta, str) and correta.upper() in _LETRAS:
        idx = _LETRAS.index(correta.upper())
    elif isinstance(correta, int) and 0 <= correta < len(opcoes):
        idx = correta
    else:
        return None
    if idx >= len(opcoes):
        return None
    import importar_questoes as iq
    return {
        "pergunta": str(enun).strip(),
        "opcoes": [str(o).strip() for o in opcoes],
        "correta": idx,
        "explicacao": "Fonte: WQD Questões (gabarito da plataforma).",
        "disciplina": str(g("disciplina", "materia") or "Geral"),
        "tags": ["extraida", "wqd"],
        "origem": "wqd",
        "hash": iq._hash(str(enun)),
    }


def de_wqd(banca: str = "CESGRANRIO", disciplina: str = "", paginas: int = 3,
           por_pagina: int = 20) -> int:
    """Loga, pagina /pesquisa e importa as questões. Retorna nº adicionadas."""
    user = os.environ.get("AGENTE_WQD_USER", "")
    senha = os.environ.get("AGENTE_WQD_PASS", "")
    id_token, locale = cognito_login(user, senha)
    print(f"Login OK. locale={locale!r}")
    import importar_questoes as iq
    novas: list[dict] = []
    for p in range(paginas):
        body = montar_body(locale, banca=banca, disciplina=disciplina,
                           start=p * por_pagina)
        resp = pesquisar(body, id_token)
        itens = _achar_lista_questoes(resp)
        if not itens:
            print(f"  página {p+1}: 0 questões (fim ou filtro sem retorno)")
            break
        convertidas = [c for c in (converter_questao(i) for i in itens) if c]
        print(f"  página {p+1}: {len(itens)} itens → {len(convertidas)} válidas")
        novas.extend(convertidas)
    return iq.importar(novas)


def main() -> None:
    ap = argparse.ArgumentParser(description="Importa questões reais do WQD")
    ap.add_argument("--probe", action="store_true",
                    help="Loga e mostra a ESTRUTURA da resposta (p/ finalizar o parser)")
    ap.add_argument("--banca", default="CESGRANRIO")
    ap.add_argument("--disciplina", default="")
    ap.add_argument("--paginas", type=int, default=3)
    args = ap.parse_args()

    # carrega .env (mesmo loader do loop)
    try:
        from loop_infinito import carregar_dotenv
        carregar_dotenv()
    except Exception:
        pass

    if args.probe:
        user = os.environ.get("AGENTE_WQD_USER", "")
        senha = os.environ.get("AGENTE_WQD_PASS", "")
        id_token, locale = cognito_login(user, senha)
        print(f"Login OK. locale={locale!r}")
        body = montar_body(locale, banca=args.banca, classe="concursos")
        resp = pesquisar(body, id_token)
        print("=== ESTRUTURA DA RESPOSTA (chaves de topo) ===")
        if isinstance(resp, dict):
            print(list(resp.keys()))
            print(json.dumps(resp, ensure_ascii=False, indent=2)[:2500])
        else:
            print(repr(resp)[:500])
        return

    n = de_wqd(banca=args.banca, disciplina=args.disciplina, paginas=args.paginas)
    print(f"\n✓ {n} questão(ões) reais do WQD importadas.")


if __name__ == "__main__":
    main()
