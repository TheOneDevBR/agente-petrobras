"""Persistência com SQLite (primário) + fallback JSON.

Camada única de leitura/escrita. Dados conhecidos são armazenados no SQLite
(``dados/agente.db``) com schema relacional. Dados não mapeados usam o
mecanismo legado de arquivos JSON com escrita atômica.

As funções ``db_ler_json`` / ``db_gravar_json`` mantêm a assinatura original
para compatibilidade — internamente redirecionam para SQLite quando o caminho
for mapeado, ou caem no JSON legado.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

AQUI_DADOS = Path(__file__).resolve().parent / "dados"
DB_PATH = AQUI_DADOS / "agente.db"
_SENTINEL = object()

# Mapeia nome de arquivo JSON → (tabela_sqlite, coluna_pk, tipo)
# "tipo" diz como serializar/deserializar o valor
_JSON_FOR_SQLITE = {
    "perfil_candidato.json": ("perfil", "chave", "perfil"),
    "sessoes.json": ("sessoes", "id", "lista_dict"),
    "simulados.json": ("simulados", "id", "simulados"),
    "questoes_extraidas.json": ("questoes", "hash", "questoes"),
    "sm2.json": ("sm2", None, "sm2"),
    "coaching_elo.json": (None, None, "coaching_elo"),
    "erros_cabt.json": (None, None, "erros_cabt"),
    "historico_conversa.json": ("historico_conversa", "id", "lista_dict"),
    "historico_pratica.json": ("historico_pratica", "data", "pratica"),
    "autonomia_metricas.json": ("autonomia_metricas", "id", "lista_dict"),
    "meta_learning_history.json": ("meta_learning", "id", "lista_dict"),
    "fontes_descobertas.json": (None, None, "fontes_descobertas"),
    "evolucao/diario.json": (None, None, "evolucao_diario"),
    "evolucao/auto_avaliacao.json": (None, None, "evolucao_auto_avaliacao"),
    "evolucao/experimentos.json": (None, None, "evolucao_experimentos"),
}


def _conn():
    return sqlite3.connect(str(DB_PATH))


def _nome_json(caminho: Path) -> str | None:
    """Extrai o nome relativo do JSON (ex: 'evolucao/diario.json')."""
    try:
        abs_path = caminho.resolve()
        rel = str(abs_path.relative_to(AQUI_DADOS.resolve())).replace("\\", "/")
        return rel
    except ValueError:
        return None


# ── Conversores SQLite ↔ dict Python ──────────────────────────────────────


def _sqlite_para_perfil() -> dict:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT chave, valor FROM perfil").fetchall()
    dados = {}
    for r in rows:
        try:
            dados[r["chave"]] = json.loads(r["valor"])
        except (json.JSONDecodeError, TypeError):
            dados[r["chave"]] = r["valor"]
    return dados


def _perfil_para_sqlite(dados: dict):
    with _conn() as c:
        c.execute("DELETE FROM perfil")
        for k, v in dados.items():
            c.execute(
                "INSERT INTO perfil(chave, valor) VALUES(?,?)",
                (k, json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v),
            )


def _sqlite_para_lista(tabela: str) -> list:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(f"SELECT * FROM {tabela}").fetchall()
    return [dict(r) for r in rows]


def _lista_para_sqlite(tabela: str, dados: list[dict], mapeamento: dict[str, str]):
    if not dados:
        return
    with _conn() as c:
        c.execute(f"DELETE FROM {tabela}")
        cols = list(mapeamento.keys())
        for item in dados:
            vals = []
            for col, campo in mapeamento.items():
                v = item.get(campo)
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, ensure_ascii=False)
                vals.append(v)
            c.execute(
                f"INSERT INTO {tabela}({', '.join(cols)}) VALUES({', '.join('?' for _ in cols)})",
                vals,
            )


_SIMULADOS_MAP = {
    "data": "data", "disciplina": "disciplina", "questoes": "questoes",
    "acertos": "acertos", "pct": "pct", "tempo_seg": "tempo_seg",
    "tipo": "tipo", "cargo": "cargo",
    "respostas": "respostas", "disciplinas": "disciplinas",
}


def _questoes_para_lista() -> list[dict]:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM questoes").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["opcoes"] = json.loads(d.get("opcoes", "[]"))
        d["tags"] = json.loads(d.get("tags", "[]"))
        d.pop("importada_em", None)
        d.pop("hash", None)
        result.append(d)
    return result


def _lista_para_questoes(dados: list[dict]):
    import hashlib
    with _conn() as c:
        c.execute("DELETE FROM questoes")
        for item in dados:
            h = item.get("hash") or hashlib.sha1(
                item.get("pergunta", "").encode(), usedforsecurity=False
            ).hexdigest()[:16]
            c.execute(
                """INSERT INTO questoes(hash,pergunta,opcoes,correta,explicacao,disciplina,tags,origem,cargo)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    h, item.get("pergunta", ""),
                    json.dumps(item.get("opcoes", []), ensure_ascii=False),
                    item.get("correta"), item.get("explicacao", ""),
                    item.get("disciplina", ""),
                    json.dumps(item.get("tags", []), ensure_ascii=False),
                    item.get("origem", ""), item.get("cargo", ""),
                ),
            )


def _sm2_para_lista() -> list[dict]:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM sm2").fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["revisoes"] = json.loads(d.get("revisoes", "[]"))
        result.append(d)
    return result


def _lista_para_sm2(dados: list[dict]):
    with _conn() as c:
        c.execute("DELETE FROM sm2")
        for item in dados:
            c.execute(
                """INSERT INTO sm2(questao_idx,disciplina,pergunta,ease,interval_dias,rep,proxima_revisao,ultima_qualidade,revisoes)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    item.get("questao_idx", 0), item.get("disciplina", ""),
                    item.get("pergunta", ""), item.get("ease", 2.5),
                    item.get("interval_dias", 0), item.get("rep", 0),
                    item.get("proxima_revisao"), item.get("ultima_qualidade"),
                    json.dumps(item.get("revisoes", []), ensure_ascii=False),
                ),
            )


def _pratica_para_dict() -> dict:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM historico_pratica").fetchall()
    return {r["data"]: {"respondidas": r["respondidas"], "acertos": r["acertos"]} for r in rows}


def _dict_para_pratica(dados: dict):
    with _conn() as c:
        c.execute("DELETE FROM historico_pratica")
        for data_str, vals in dados.items():
            c.execute(
                "INSERT INTO historico_pratica(data,respondidas,acertos) VALUES(?,?,?)",
                (data_str, vals.get("respondidas", 0), vals.get("acertos", 0)),
            )


def _coaching_elo_para_dict() -> dict:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        habs = c.execute("SELECT * FROM coaching_habilidades").fetchall()
        itens = c.execute("SELECT * FROM coaching_itens").fetchall()
    return {
        "habilidades": {r["disciplina"]: r["rating"] for r in habs},
        "n_respostas": {r["disciplina"]: r["n_respostas"] for r in habs},
        "itens": {r["item_id"]: r["rating"] for r in itens},
    }


def _dict_para_coaching_elo(dados: dict):
    with _conn() as c:
        c.execute("DELETE FROM coaching_habilidades")
        c.execute("DELETE FROM coaching_itens")
        for disc, rating in dados.get("habilidades", {}).items():
            n_resp = dados.get("n_respostas", {}).get(disc, 0)
            c.execute(
                "INSERT INTO coaching_habilidades(disciplina,rating,n_respostas) VALUES(?,?,?)",
                (disc, rating, n_resp),
            )
        for item_id, rating in dados.get("itens", {}).items():
            c.execute(
                "INSERT INTO coaching_itens(item_id,rating) VALUES(?,?)",
                (item_id, rating),
            )


def _erros_cabt_para_dict() -> dict:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM erros_cabt").fetchall()
    contagem = {}
    por_disciplina = {}
    for r in rows:
        if r["disciplina"] == "__geral__":
            contagem[r["categoria"]] = r["contagem"]
        else:
            por_disciplina.setdefault(r["disciplina"], {})[r["categoria"]] = r["contagem"]
    return {"contagem": contagem, "por_disciplina": por_disciplina}


def _dict_para_erros_cabt(dados: dict):
    with _conn() as c:
        c.execute("DELETE FROM erros_cabt")
        for cat, val in dados.get("contagem", {}).items():
            c.execute("INSERT INTO erros_cabt(disciplina,categoria,contagem) VALUES(?,?,?)",
                      ("__geral__", cat, val))
        for disc, cats in dados.get("por_disciplina", {}).items():
            for cat, val in cats.items():
                c.execute("INSERT INTO erros_cabt(disciplina,categoria,contagem) VALUES(?,?,?)",
                          (disc, cat, val))


def _fontes_para_dict() -> dict:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM fontes_descobertas").fetchall()
    dados = {}
    for r in rows:
        dados[r["dominio"]] = {
            "ocorrencias": r["ocorrencias"],
            "contextos": json.loads(r["contextos"]),
            "exemplo": r["exemplo"],
            "promovida": bool(r["promovida"]),
        }
    return dados


def _dict_para_fontes(dados: dict):
    with _conn() as c:
        c.execute("DELETE FROM fontes_descobertas")
        for dominio, info in dados.items():
            c.execute(
                "INSERT INTO fontes_descobertas(dominio,ocorrencias,contextos,exemplo,promovida) VALUES(?,?,?,?,?)",
                (dominio, info.get("ocorrencias", 1),
                 json.dumps(info.get("contextos", []), ensure_ascii=False),
                 info.get("exemplo", ""), 1 if info.get("promovida") else 0),
            )


def _evolucao_diario_para_dict() -> dict:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM evolucao_diario").fetchall()
    decisoes = []
    for r in rows:
        d = dict(r)
        d["contexto"] = json.loads(d.get("contexto", "{}"))
        d.pop("id", None)
        decisoes.append(d)
    return {"decisoes": decisoes}


def _dict_para_evolucao_diario(dados: dict):
    with _conn() as c:
        c.execute("DELETE FROM evolucao_diario")
        for dec in dados.get("decisoes", []):
            c.execute(
                """INSERT INTO evolucao_diario(id,timestamp,estrategia,disciplina,prescricao,contexto,outcome_esperado,outcome_real,eficacia)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    dec.get("id", ""), dec.get("timestamp", ""),
                    dec.get("estrategia", ""), dec.get("disciplina", ""),
                    dec.get("prescricao", ""),
                    json.dumps(dec.get("contexto", {}), ensure_ascii=False),
                    dec.get("outcome_esperado", ""), dec.get("outcome_real", ""),
                    dec.get("eficacia"),
                ),
            )


def _auto_avaliacao_para_dict() -> dict:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM evolucao_auto_avaliacao").fetchall()
    avaliacoes = []
    for r in rows:
        d = dict(r)
        d["dimensoes"] = json.loads(d.get("dimensoes", "{}"))
        d.pop("id", None)
        avaliacoes.append(d)
    return {"avaliacoes": avaliacoes}


def _dict_para_auto_avaliacao(dados: dict):
    with _conn() as c:
        c.execute("DELETE FROM evolucao_auto_avaliacao")
        for av in dados.get("avaliacoes", []):
            c.execute(
                """INSERT INTO evolucao_auto_avaliacao(timestamp,score_total,dimensoes,sugestao_melhoria,dimensao_mais_fraca)
                   VALUES(?,?,?,?,?)""",
                (
                    av.get("timestamp", ""), av.get("score_total"),
                    json.dumps(av.get("dimensoes", {}), ensure_ascii=False),
                    av.get("sugestao_melhoria", ""), av.get("dimensao_mais_fraca", ""),
                ),
            )


def _experimentos_para_dict() -> dict:
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM evolucao_experimentos").fetchall()
    experimentos = [dict(r) for r in rows]
    return {"experimentos": experimentos, "conclusoes": [], "_versao": 1}


def _dict_para_experimentos(dados: dict):
    with _conn() as c:
        c.execute("DELETE FROM evolucao_experimentos")
        for e in dados.get("experimentos", []):
            c.execute(
                """INSERT INTO evolucao_experimentos(id,hipotese,condicao,grupo_a,grupo_b,vencedor,status)
                   VALUES(?,?,?,?,?,?,?)""",
                (e.get("id"), e.get("hipotese"), e.get("condicao"),
                 e.get("grupo_a"), e.get("grupo_b"), e.get("vencedor"), e.get("status")),
            )


_READERS: dict[str, Any] = {
    "perfil": _sqlite_para_perfil,
    "lista_dict": _sqlite_para_lista,
    "simulados": lambda: _sqlite_para_lista("simulados"),
    "questoes": _questoes_para_lista,
    "sm2": _sm2_para_lista,
    "coaching_elo": _coaching_elo_para_dict,
    "erros_cabt": _erros_cabt_para_dict,
    "pratica": _pratica_para_dict,
    "fontes_descobertas": _fontes_para_dict,
    "evolucao_diario": _evolucao_diario_para_dict,
    "evolucao_auto_avaliacao": _auto_avaliacao_para_dict,
    "evolucao_experimentos": _experimentos_para_dict,
}

_WRITERS: dict[str, Any] = {
    "perfil": _perfil_para_sqlite,
    "lista_dict": lambda t, d: _lista_para_sqlite(t, d, {}),
    "simulados": lambda t, d: _lista_para_sqlite("simulados", d, _SIMULADOS_MAP),
    "questoes": _lista_para_questoes,
    "sm2": _lista_para_sm2,
    "coaching_elo": _dict_para_coaching_elo,
    "erros_cabt": _dict_para_erros_cabt,
    "pratica": _dict_para_pratica,
    "fontes_descobertas": _dict_para_fontes,
    "evolucao_diario": _dict_para_evolucao_diario,
    "evolucao_auto_avaliacao": _dict_para_auto_avaliacao,
    "evolucao_experimentos": _dict_para_experimentos,
}


# ── API pública (compatível com código legado) ────────────────────────────


def db_ler_json(caminho: Path | str, default: Any = _SENTINEL) -> Any:
    """Lê dados, preferencialmente do SQLite, com fallback para JSON."""
    path = Path(caminho)
    nome = _nome_json(path)

    if nome and nome in _JSON_FOR_SQLITE:
        _, _, tipo = _JSON_FOR_SQLITE[nome]
        try:
            if tipo in _READERS:
                if tipo == "lista_dict":
                    tabela, _, _ = _JSON_FOR_SQLITE[nome]
                    return _READERS[tipo](tabela)
                return _READERS[tipo]()
        except Exception:
            pass  # fallback para JSON

    # Fallback: JSON legado
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {} if default is _SENTINEL else default


def _escrever_json_atomico(path: Path, dados: Any):
    """Escreve JSON com atomicidade (temp + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(dados, ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def db_gravar_json(caminho: Path | str, dados: Any) -> None:
    """Grava dados no SQLite (primário) + JSON (backup compatível)."""
    path = Path(caminho)
    nome = _nome_json(path)

    if nome and nome in _JSON_FOR_SQLITE:
        tabela, _, tipo = _JSON_FOR_SQLITE[nome]
        try:
            if tipo in _WRITERS:
                if tipo == "lista_dict":
                    _WRITERS[tipo](tabela, dados)
                else:
                    _WRITERS[tipo](dados)
        except Exception:
            pass

    _escrever_json_atomico(path, dados)


def db_inicializar():
    """Garante que o SQLite existe e tem o schema."""
    from db_sqlite import Database
    db = Database.inst()
    db.init_db()


def db_migrar_json():
    """Migra JSONs existentes para SQLite."""
    from db_sqlite import migrar_json_para_sqlite
    return migrar_json_para_sqlite()
