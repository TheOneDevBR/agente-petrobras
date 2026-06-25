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
import binascii
import datetime
import hashlib
import hmac
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
COGNITO_USER_POOL_ID = "us-east-1_B6yogaMYd"
COGNITO_IDP_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
# Endpoint de busca REAL usado pelo app (confirmado via DevTools).
PESQUISA_URL = "https://jyxnhcj9ba.execute-api.us-east-1.amazonaws.com/pesqusa280219-1"
TIMEOUT = 40
# assinante do plano gratuito (objeto, não string). Conta paga teria ativo='1'.
ASSINANTE_FREE = {"ativo": "0", "count_question": "0"}

# Grupo SRP fixo do AWS Cognito (3072-bit), g=2.
_N_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74"
    "020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F1437"
    "4FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF05"
    "98DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB"
    "9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718"
    "3995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D04507A33"
    "A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7"
    "ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6BF12FFA06D98A0864"
    "D87602733EC86A64521F2B18177B200CBBE117577A615D6C770988C0BAD946E2"
    "08E24FA074E5AB3143DB5BFCE0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF"
)
_G_HEX = "2"
_INFO_BITS = b"Caldera Derived Key"


class WQDError(Exception):
    pass


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decodifica o payload (claims) de um JWT sem verificar assinatura."""
    try:
        meio = token.split(".")[1]
        meio += "=" * (-len(meio) % 4)  # padding base64url
        return json.loads(base64.urlsafe_b64decode(meio))
    except Exception as e:
        raise WQDError(f"idToken inválido: {e}")


# ── Cognito SRP (USER_SRP_AUTH em Python puro, sem boto3) ─────────────────────
def _hex_hash(hex_str: str) -> str:
    return hashlib.sha256(bytearray.fromhex(hex_str)).hexdigest()


def _hex_to_long(h: str) -> int:
    return int(h, 16)


def _long_to_hex(n: int) -> str:
    return format(n, "x")


def _pad_hex(value: int | str) -> str:
    h = _long_to_hex(value) if isinstance(value, int) else value
    if len(h) % 2 == 1:
        h = "0" + h
    elif h[0] in "89abcdefABCDEF":
        h = "00" + h
    return h


def _compute_hkdf(ikm: bytes, salt: bytes) -> bytes:
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    return hmac.new(prk, _INFO_BITS + b"\x01", hashlib.sha256).digest()[:16]


def _timestamp() -> str:
    """Formato exigido pelo Cognito: 'Wed Jun 25 12:00:00 UTC 2026' (dia sem zero)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    dias = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    meses = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return (f"{dias[now.weekday()]} {meses[now.month - 1]} {now.day} "
            f"{now.hour:02d}:{now.minute:02d}:{now.second:02d} UTC {now.year}")


def _aws(action: str, payload: dict) -> dict:
    r = requests.post(
        COGNITO_IDP_URL, json=payload, timeout=TIMEOUT,
        headers={"Content-Type": "application/x-amz-json-1.1",
                 "X-Amz-Target": f"AWSCognitoIdentityProviderService.{action}"},
    )
    if r.status_code != 200:
        msg = (r.json().get("message", r.text[:200]) if r.content else r.text[:200])
        raise WQDError(f"Cognito {action} falhou ({r.status_code}): {msg}")
    return r.json()


def cognito_login(user: str, senha: str) -> tuple[str, str]:
    """Autentica via SRP e retorna (id_token, locale). Python puro, sem boto3."""
    if not user or not senha:
        raise WQDError("Defina AGENTE_WQD_USER e AGENTE_WQD_PASS no .env.")

    big_n = _hex_to_long(_N_HEX)
    g = _hex_to_long(_G_HEX)
    k = _hex_to_long(_hex_hash("00" + _N_HEX + "0" + _G_HEX))
    small_a = _hex_to_long(binascii.hexlify(os.urandom(128)).decode()) % big_n
    big_a = pow(g, small_a, big_n)
    if big_a % big_n == 0:
        raise WQDError("SRP: A inválido (raro), tente de novo.")

    init = _aws("InitiateAuth", {
        "AuthFlow": "USER_SRP_AUTH",
        "ClientId": COGNITO_CLIENT_ID,
        "AuthParameters": {"USERNAME": user, "SRP_A": _long_to_hex(big_a)},
    })
    ch = init.get("ChallengeParameters", {})
    if init.get("ChallengeName") != "PASSWORD_VERIFIER":
        raise WQDError(f"Desafio inesperado: {init.get('ChallengeName')}")

    user_id = ch["USER_ID_FOR_SRP"]
    salt_hex = ch["SALT"]
    srp_b = _hex_to_long(ch["SRP_B"])
    secret_block = ch["SECRET_BLOCK"]
    pool_name = COGNITO_USER_POOL_ID.split("_")[1]

    # u = H(A | B)
    u = _hex_to_long(_hex_hash(_pad_hex(big_a) + _pad_hex(srp_b)))
    # x = H(salt | H(poolName + userId : password))
    id_hash = hashlib.sha256(f"{pool_name}{user_id}:{senha}".encode()).hexdigest()
    x = _hex_to_long(_hex_hash(_pad_hex(salt_hex) + id_hash))
    # S = (B - k*g^x) ^ (a + u*x) mod N
    s = pow(srp_b - k * pow(g, x, big_n), small_a + u * x, big_n)
    hkdf = _compute_hkdf(bytes.fromhex(_pad_hex(s)), bytes.fromhex(_pad_hex(u)))

    ts = _timestamp()
    msg = (pool_name.encode() + user_id.encode()
           + base64.standard_b64decode(secret_block) + ts.encode())
    signature = base64.standard_b64encode(
        hmac.new(hkdf, msg, hashlib.sha256).digest()).decode()

    resp = _aws("RespondToAuthChallenge", {
        "ChallengeName": "PASSWORD_VERIFIER",
        "ClientId": COGNITO_CLIENT_ID,
        "ChallengeResponses": {
            "USERNAME": user_id,
            "PASSWORD_CLAIM_SECRET_BLOCK": secret_block,
            "PASSWORD_CLAIM_SIGNATURE": signature,
            "TIMESTAMP": ts,
        },
    })
    res = resp.get("AuthenticationResult") or {}
    id_token = res.get("IdToken")
    if not id_token:
        raise WQDError(f"Sem IdToken: {json.dumps(resp)[:200]}")
    locale = _decode_jwt_payload(id_token).get("locale", "")
    return id_token, locale


# ── Busca ────────────────────────────────────────────────────────────────────
def montar_body(locale: str, *, q: str = "crase", start: int = 1, banca: str = "",
                disciplina: str = "", ano: str = "", nivel: str = "", tipo: str = "",
                classe: str = "concursos", assinante: dict | None = None) -> dict[str, Any]:
    """Monta o corpo do POST de busca (formato REAL confirmado via DevTools).

    Campos obrigatórios: ``q`` (termo), ``classe`` (categoria), ``locale`` (do
    idToken), ``assinante`` (OBJETO {ativo, count_question}) e os filtros vazios
    presentes (o Lambda faz ``.split()`` neles — omitir quebra a busca).
    """
    return {
        "q": q, "start": start, "locale": locale, "classe": classe,
        "assinante": assinante or ASSINANTE_FREE,
        "disciplina": disciplina, "banca": banca, "ano": ano,
        "nivel": nivel, "tipo": tipo,
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
    """Lista de questões: resposta real = ``hits.hits[]._source`` (ES)."""
    if not isinstance(resp, dict):
        return []
    for caminho in (("hits", "hits"), ("data", "hits", "hits"),
                    ("questoes",), ("data", "questoes")):
        cur: Any = resp
        for k in caminho:
            cur = cur.get(k) if isinstance(cur, dict) else None
            if cur is None:
                break
        if isinstance(cur, list) and cur:
            return [h.get("_source", h) if isinstance(h, dict) else h for h in cur]
    return []


def _flatten_fields(src: dict) -> dict[str, Any]:
    """O _source tem ``fields`` com valores em array (ES). Desembrulha [v]→v e
    funde com os campos de topo."""
    base = dict(src)
    f = base.pop("fields", {})
    if isinstance(f, dict):
        for k, v in f.items():
            base[k] = v[0] if isinstance(v, list) and len(v) == 1 else v
    return base


def converter_questao(item: dict) -> dict[str, Any] | None:
    """Converte um item do WQD (com gabarito) para o schema do store.

    Tolerante a nomes de campo. Retorna None se faltar enunciado/alternativas/
    gabarito (o chamador loga as chaves p/ finalizar o mapeamento no 1º hit real).
    """
    it = _flatten_fields(item)

    def g(*nomes):
        for n in nomes:
            for cand in (n, n.lower(), n.upper()):
                v = it.get(cand)
                if v not in ("", None, []):
                    return v
        return None

    enun = g("enunciado", "pergunta", "texto", "questao", "comando", "titulo")
    # alternativas: lista única OU campos a/b/c/d/e separados
    alts = g("alternativas", "opcoes", "options", "items")
    if not isinstance(alts, list):
        letras_alt = [g(f"alternativa{L}", f"alternativa_{L}", L) for L in "abcde"]
        alts = [a for a in letras_alt if a]
    correta = g("gabarito", "correta", "resposta", "alternativaCorreta", "gabaritooficial")
    if not (enun and isinstance(alts, list) and len(alts) >= 2 and correta not in (None, "")):
        return None
    opcoes = [a.get("texto", a) if isinstance(a, dict) else a for a in alts]
    c = str(correta).strip().upper()
    if c in _LETRAS:
        idx = _LETRAS.index(c)
    elif c.isdigit() and 0 <= int(c) < len(opcoes):
        idx = int(c)
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
        "disciplina": str(g("disciplina", "materia", "assunto") or "Geral"),
        "tags": ["extraida", "wqd"],
        "origem": "wqd",
        "hash": iq._hash(str(enun)),
    }


# Termos de busca para varrer questões (a busca EXIGE um q). Cobrem assuntos
# recorrentes; cada termo é uma página de até ~10 questões.
TERMOS_BUSCA = [
    "crase", "concordância", "regência", "porcentagem", "função", "probabilidade",
    "sujeito", "verbo", "licitação", "administração pública", "constituição",
    "petróleo", "reservatório", "segurança", "lei", "contrato", "logística",
]


def de_wqd(termos: list[str] | None = None, classe: str = "concursos",
           paginas: int = 1, schema_log: bool = True) -> int:
    """Loga (SRP), varre os termos de busca e importa as questões. Retorna nº add."""
    user = os.environ.get("AGENTE_WQD_USER", "")
    senha = os.environ.get("AGENTE_WQD_PASS", "")
    id_token, locale = cognito_login(user, senha)
    print(f"Login OK. locale={locale!r}")
    import importar_questoes as iq
    novas: list[dict] = []
    logou_schema = not schema_log
    for termo in (termos or TERMOS_BUSCA):
        for p in range(paginas):
            body = montar_body(locale, q=termo, classe=classe, start=1 + p)
            try:
                resp = pesquisar(body, id_token)
            except WQDError as e:
                print(f"  '{termo}' p{p+1}: erro {e}")
                continue
            itens = _achar_lista_questoes(resp)
            found = (resp.get("hits", {}) or {}).get("found") if isinstance(resp, dict) else None
            convertidas = [c for c in (converter_questao(i) for i in itens) if c]
            print(f"  '{termo}': found={found} hits={len(itens)} → {len(convertidas)} válidas")
            # Finaliza o mapeamento: loga as chaves do 1º hit que não converteu
            if not logou_schema and itens and not convertidas:
                print("  [SCHEMA do hit p/ finalizar parser]:",
                      sorted(_flatten_fields(itens[0]).keys()))
                logou_schema = True
            novas.extend(convertidas)
    return iq.importar(novas)


def main() -> None:
    ap = argparse.ArgumentParser(description="Importa questões reais do WQD")
    ap.add_argument("--probe", action="store_true",
                    help="Loga e mostra a ESTRUTURA da resposta (p/ finalizar o parser)")
    ap.add_argument("--termo", default="crase", help="Termo de busca (probe)")
    ap.add_argument("--classe", default="concursos")
    ap.add_argument("--paginas", type=int, default=1)
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
        body = montar_body(locale, q=args.termo, classe=args.classe)
        resp = pesquisar(body, id_token)
        print("=== ESTRUTURA DA RESPOSTA (chaves de topo) ===")
        if isinstance(resp, dict):
            print(list(resp.keys()))
            hits = (resp.get("hits") or {}).get("hits") or []
            print(f"found={resp.get('hits',{}).get('found')} hits_nesta_pagina={len(hits)}")
            if hits:
                print("CAMPOS:", sorted(_flatten_fields(hits[0]).keys()))
        else:
            print(repr(resp)[:500])
        return

    n = de_wqd(classe=args.classe, paginas=args.paginas)
    print(f"\n✓ {n} questão(ões) reais do WQD importadas.")


if __name__ == "__main__":
    main()
