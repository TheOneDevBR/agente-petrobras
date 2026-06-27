"""Persistência SQLite unificada.

Substitui gradualmente os JSONs avulsos por um banco SQLite relacional,
mantendo compatibilidade com a API de ``db_ler_json`` / ``db_gravar_json``.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Any

AQUI = Path(__file__).resolve().parent
DB_PATH = AQUI / "dados" / "agente.db"

_SCHEMA_SQL = """
-- Perfil do candidato (1 registro)
CREATE TABLE IF NOT EXISTS perfil (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Sessões de estudo
CREATE TABLE IF NOT EXISTS sessoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    disciplina TEXT NOT NULL DEFAULT '',
    minutos REAL NOT NULL DEFAULT 0,
    questoes INTEGER NOT NULL DEFAULT 0,
    acertos INTEGER NOT NULL DEFAULT 0,
    acerto_pct REAL,
    erro_dominante TEXT DEFAULT '',
    anotacoes TEXT DEFAULT ''
);

-- Resultados de simulados
CREATE TABLE IF NOT EXISTS simulados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    disciplina TEXT DEFAULT '',
    questoes INTEGER NOT NULL DEFAULT 0,
    acertos INTEGER NOT NULL DEFAULT 0,
    pct REAL,
    tempo_seg REAL,
    tipo TEXT DEFAULT '',
    cargo TEXT DEFAULT '',
    respostas TEXT DEFAULT '[]',
    disciplinas TEXT DEFAULT '{}'
);

-- Questões extraídas de PDFs
CREATE TABLE IF NOT EXISTS questoes (
    hash TEXT PRIMARY KEY,
    pergunta TEXT NOT NULL,
    opcoes TEXT NOT NULL DEFAULT '[]',
    correta INTEGER,
    explicacao TEXT DEFAULT '',
    disciplina TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    origem TEXT DEFAULT '',
    cargo TEXT DEFAULT '',
    importada_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- SM-2 (repetição espaçada)
CREATE TABLE IF NOT EXISTS sm2 (
    questao_idx INTEGER NOT NULL,
    disciplina TEXT NOT NULL,
    pergunta TEXT NOT NULL,
    ease REAL NOT NULL DEFAULT 2.5,
    interval_dias INTEGER NOT NULL DEFAULT 0,
    rep INTEGER NOT NULL DEFAULT 0,
    proxima_revisao TEXT,
    ultima_qualidade INTEGER,
    revisoes TEXT DEFAULT '[]',
    PRIMARY KEY (questao_idx, disciplina)
);

-- ELO coaching
CREATE TABLE IF NOT EXISTS coaching_habilidades (
    disciplina TEXT PRIMARY KEY,
    rating REAL NOT NULL DEFAULT 1000.0,
    n_respostas INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS coaching_itens (
    item_id TEXT PRIMARY KEY,
    rating REAL NOT NULL DEFAULT 1000.0
);

-- Classificação de erros C/A/B/T
CREATE TABLE IF NOT EXISTS erros_cabt (
    disciplina TEXT NOT NULL,
    categoria TEXT NOT NULL CHECK(categoria IN ('C','A','B','T')),
    contagem INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (disciplina, categoria)
);

-- Histórico de conversa
CREATE TABLE IF NOT EXISTS historico_conversa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    papel TEXT NOT NULL CHECK(papel IN ('user','assistant','system')),
    conteudo TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    sessao TEXT DEFAULT ''
);

-- Prática diária
CREATE TABLE IF NOT EXISTS historico_pratica (
    data TEXT PRIMARY KEY,
    respondidas INTEGER NOT NULL DEFAULT 0,
    acertos INTEGER NOT NULL DEFAULT 0
);

-- Métricas de autonomia
CREATE TABLE IF NOT EXISTS autonomia_metricas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    metricas TEXT NOT NULL
);

-- Meta-learning history
CREATE TABLE IF NOT EXISTS meta_learning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    feedback TEXT,
    impacto_estimado REAL
);

-- Fontes descobertas pelo coletor
CREATE TABLE IF NOT EXISTS fontes_descobertas (
    dominio TEXT PRIMARY KEY,
    ocorrencias INTEGER NOT NULL DEFAULT 1,
    contextos TEXT DEFAULT '[]',
    exemplo TEXT DEFAULT '',
    promovida INTEGER NOT NULL DEFAULT 0
);

-- Diário de evolução
CREATE TABLE IF NOT EXISTS evolucao_diario (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    estrategia TEXT DEFAULT '',
    disciplina TEXT DEFAULT '',
    prescricao TEXT DEFAULT '',
    contexto TEXT DEFAULT '{}',
    outcome_esperado TEXT DEFAULT '',
    outcome_real TEXT DEFAULT '',
    eficacia REAL
);

-- Auto-avaliação do sistema
CREATE TABLE IF NOT EXISTS evolucao_auto_avaliacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    score_total REAL,
    dimensoes TEXT DEFAULT '{}',
    sugestao_melhoria TEXT DEFAULT '',
    dimensao_mais_fraca TEXT DEFAULT ''
);

-- Experimentos A/B
CREATE TABLE IF NOT EXISTS evolucao_experimentos (
    id TEXT PRIMARY KEY,
    hipotese TEXT DEFAULT '',
    condicao TEXT DEFAULT '',
    grupo_a TEXT DEFAULT '',
    grupo_b TEXT DEFAULT '',
    vencedor TEXT DEFAULT '',
    status TEXT DEFAULT 'ativo'
);
"""

_JSON_TO_TABLE = {
    "perfil_candidato.json": ("perfil", "_import_perfil"),
    "sessoes.json": ("sessoes", "_import_sessoes"),
    "simulados.json": ("simulados", "_import_simulados"),
    "questoes_extraidas.json": ("questoes", "_import_questoes"),
    "sm2.json": ("sm2", "_import_sm2"),
    "coaching_elo.json": ("coaching_habilidades,coaching_itens", "_import_coaching"),
    "erros_cabt.json": ("erros_cabt", "_import_erros_cabt"),
    "historico_conversa.json": ("historico_conversa", "_import_conversa"),
    "historico_pratica.json": ("historico_pratica", "_import_pratica"),
    "autonomia_metricas.json": ("autonomia_metricas", "_import_autonomia"),
    "meta_learning_history.json": ("meta_learning", "_import_meta_learning"),
    "fontes_descobertas.json": ("fontes_descobertas", "_import_fontes"),
    "evolucao/diario.json": ("evolucao_diario", "_import_diario"),
    "evolucao/auto_avaliacao.json": ("evolucao_auto_avaliacao", "_import_auto_avaliacao"),
    "evolucao/experimentos.json": ("evolucao_experimentos", "_import_experimentos"),
}


class Database:
    _inst: Database | None = None

    def __init__(self, path: str | Path = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @classmethod
    def inst(cls) -> Database:
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    @contextmanager
    def conn(self):
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield self._conn
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def init_db(self):
        with self.conn() as c:
            c.executescript(_SCHEMA_SQL)

    def fechar(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # --- helpers ---

    def _get(self, table: str, pk_col: str, pk_val: Any) -> dict | None:
        with self.conn() as c:
            row = c.execute(
                f"SELECT * FROM {table} WHERE {pk_col} = ?", (pk_val,)
            ).fetchone()
            return dict(row) if row else None

    def _list(self, table: str, order: str = "") -> list[dict]:
        with self.conn() as c:
            q = f"SELECT * FROM {table}"
            if order:
                q += f" ORDER BY {order}"
            return [dict(r) for r in c.execute(q).fetchall()]

    def _upsert(self, table: str, data: dict, pk_cols: list[str] | None = None):
        with self.conn() as c:
            cols = list(data.keys())
            placeholders = ", ".join("?" for _ in cols)
            conflict = (
                f"ON CONFLICT({', '.join(pk_cols)}) DO UPDATE SET "
                + ", ".join(f"{k}=excluded.{k}" for k in cols)
            ) if pk_cols else ""
            c.execute(
                f"INSERT INTO {table}({', '.join(cols)}) VALUES({placeholders}) {conflict}",
                [data[k] for k in cols],
            )

    def _delete(self, table: str, pk_col: str, pk_val: Any):
        with self.conn() as c:
            c.execute(f"DELETE FROM {table} WHERE {pk_col} = ?", (pk_val,))


def _caminho_json(nome: str) -> Path:
    return AQUI / "dados" / nome


def migrar_json_para_sqlite(db: Database | None = None) -> dict[str, int]:
    """Migra todos os JSONs existentes para o SQLite. Retorna contagem por tabela."""
    if db is None:
        db = Database.inst()
    db.init_db()
    total: dict[str, int] = {}

    with db.conn() as c:
        # perfil
        p = _caminho_json("perfil_candidato.json")
        if p.exists():
            try:
                dados = json.loads(p.read_text(encoding="utf-8"))
                c.execute("DELETE FROM perfil")
                for k, v in dados.items():
                    c.execute(
                        "INSERT INTO perfil(chave, valor, atualizado_em) VALUES(?,?,datetime('now'))"
                        " ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor, atualizado_em=datetime('now')",
                        (k, json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v),
                    )
                total["perfil"] = len(dados)
            except Exception:
                pass

        # sessoes
        s = _caminho_json("sessoes.json")
        if s.exists():
            try:
                lista = json.loads(s.read_text(encoding="utf-8"))
                cnt = 0
                for item in lista:
                    c.execute(
                        """INSERT INTO sessoes(data,disciplina,minutos,questoes,acertos,acerto_pct,erro_dominante)
                           VALUES(?,?,?,?,?,?,?)""",
                        (
                            item.get("data", ""),
                            item.get("disciplina", ""),
                            item.get("minutos", 0),
                            item.get("questoes", 0),
                            item.get("acertos", 0),
                            item.get("acerto_pct"),
                            item.get("erro_dominante", ""),
                        ),
                    )
                    cnt += 1
                total["sessoes"] = cnt
            except Exception:
                pass

        # simulados
        sm = _caminho_json("simulados.json")
        if sm.exists():
            try:
                lista = json.loads(sm.read_text(encoding="utf-8"))
                cnt = 0
                for item in lista:
                    c.execute(
                        """INSERT INTO simulados(data,disciplina,questoes,acertos,pct,tempo_seg,tipo,cargo,respostas,disciplinas)
                           VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (
                            item.get("data", ""),
                            item.get("disciplina", ""),
                            item.get("questoes", 0),
                            item.get("acertos", 0),
                            item.get("pct"),
                            item.get("tempo_seg"),
                            item.get("tipo", ""),
                            item.get("cargo", ""),
                            json.dumps(item.get("respostas", []), ensure_ascii=False),
                            json.dumps(item.get("disciplinas", {}), ensure_ascii=False),
                        ),
                    )
                    cnt += 1
                total["simulados"] = cnt
            except Exception:
                pass

        # questoes_extraidas
        q = _caminho_json("questoes_extraidas.json")
        if q.exists():
            try:
                lista = json.loads(q.read_text(encoding="utf-8"))
                cnt = 0
                for item in lista:
                    import hashlib
                    h = item.get("hash") or hashlib.sha1(
                        item.get("pergunta", "").encode(), usedforsecurity=False
                    ).hexdigest()[:16]
                    c.execute(
                        """INSERT OR IGNORE INTO questoes(hash,pergunta,opcoes,correta,explicacao,disciplina,tags,origem,cargo)
                           VALUES(?,?,?,?,?,?,?,?,?)""",
                        (
                            h,
                            item.get("pergunta", ""),
                            json.dumps(item.get("opcoes", []), ensure_ascii=False),
                            item.get("correta"),
                            item.get("explicacao", ""),
                            item.get("disciplina", ""),
                            json.dumps(item.get("tags", []), ensure_ascii=False),
                            item.get("origem", ""),
                            item.get("cargo", ""),
                        ),
                    )
                    cnt += 1
                total["questoes"] = cnt
            except Exception:
                pass

        # sm2
        sm2 = _caminho_json("sm2.json")
        if sm2.exists():
            try:
                lista = json.loads(sm2.read_text(encoding="utf-8"))
                cnt = 0
                for item in lista:
                    c.execute(
                        """INSERT OR IGNORE INTO sm2(questao_idx,disciplina,pergunta,ease,interval_dias,rep,proxima_revisao,ultima_qualidade,revisoes)
                           VALUES(?,?,?,?,?,?,?,?,?)""",
                        (
                            item.get("questao_idx", 0),
                            item.get("disciplina", ""),
                            item.get("pergunta", ""),
                            item.get("ease", 2.5),
                            item.get("interval_dias", 0),
                            item.get("rep", 0),
                            item.get("proxima_revisao"),
                            item.get("ultima_qualidade"),
                            json.dumps(item.get("revisoes", []), ensure_ascii=False),
                        ),
                    )
                    cnt += 1
                total["sm2"] = cnt
            except Exception:
                pass

        # coaching_elo
        elo = _caminho_json("coaching_elo.json")
        if elo.exists():
            try:
                dados = json.loads(elo.read_text(encoding="utf-8"))
                cnt_h = 0
                for disc, rating in dados.get("habilidades", {}).items():
                    n_resp = dados.get("n_respostas", {}).get(disc, 0)
                    c.execute(
                        "INSERT INTO coaching_habilidades(disciplina,rating,n_respostas) VALUES(?,?,?)"
                        " ON CONFLICT(disciplina) DO UPDATE SET rating=excluded.rating, n_respostas=excluded.n_respostas",
                        (disc, rating, n_resp),
                    )
                    cnt_h += 1
                cnt_i = 0
                for item_id, rating in dados.get("itens", {}).items():
                    c.execute(
                        "INSERT INTO coaching_itens(item_id,rating) VALUES(?,?)"
                        " ON CONFLICT(item_id) DO UPDATE SET rating=excluded.rating",
                        (item_id, rating),
                    )
                    cnt_i += 1
                total["coaching_habilidades"] = cnt_h
                total["coaching_itens"] = cnt_i
            except Exception:
                pass

        # erros_cabt
        erros = _caminho_json("erros_cabt.json")
        if erros.exists():
            try:
                dados = json.loads(erros.read_text(encoding="utf-8"))
                cnt = 0
                for cat, val in dados.get("contagem", {}).items():
                    c.execute(
                        "INSERT INTO erros_cabt(disciplina,categoria,contagem) VALUES(?,?,?)"
                        " ON CONFLICT(disciplina,categoria) DO UPDATE SET contagem=excluded.contagem",
                        ("__geral__", cat, val),
                    )
                    cnt += 1
                for disc, cats in dados.get("por_disciplina", {}).items():
                    for cat, val in cats.items():
                        c.execute(
                            "INSERT INTO erros_cabt(disciplina,categoria,contagem) VALUES(?,?,?)"
                            " ON CONFLICT(disciplina,categoria) DO UPDATE SET contagem=excluded.contagem",
                            (disc, cat, val),
                        )
                        cnt += 1
                total["erros_cabt"] = cnt
            except Exception:
                pass

        # historico_conversa
        conv = _caminho_json("historico_conversa.json")
        if conv.exists():
            try:
                lista = json.loads(conv.read_text(encoding="utf-8"))
                cnt = 0
                for item in lista:
                    c.execute(
                        "INSERT INTO historico_conversa(papel,conteudo) VALUES(?,?)",
                        (item.get("role", "user"), item.get("content", "")),
                    )
                    cnt += 1
                total["historico_conversa"] = cnt
            except Exception:
                pass

        # historico_pratica
        prat = _caminho_json("historico_pratica.json")
        if prat.exists():
            try:
                dados = json.loads(prat.read_text(encoding="utf-8"))
                cnt = 0
                for data_str, vals in dados.items():
                    c.execute(
                        "INSERT OR IGNORE INTO historico_pratica(data,respondidas,acertos) VALUES(?,?,?)",
                        (data_str, vals.get("respondidas", 0), vals.get("acertos", 0)),
                    )
                    cnt += 1
                total["historico_pratica"] = cnt
            except Exception:
                pass

        # autonomia_metricas
        aut = _caminho_json("autonomia_metricas.json")
        if aut.exists():
            try:
                lista = json.loads(aut.read_text(encoding="utf-8"))
                cnt = 0
                for item in lista:
                    c.execute(
                        "INSERT INTO autonomia_metricas(timestamp,metricas) VALUES(?,?)",
                        (item.get("timestamp", ""), json.dumps(item, ensure_ascii=False)),
                    )
                    cnt += 1
                total["autonomia_metricas"] = cnt
            except Exception:
                pass

        # meta_learning
        ml = _caminho_json("meta_learning_history.json")
        if ml.exists():
            try:
                lista = json.loads(ml.read_text(encoding="utf-8"))
                cnt = 0
                for item in lista:
                    c.execute(
                        "INSERT INTO meta_learning(timestamp,feedback,impacto_estimado) VALUES(?,?,?)",
                        (item.get("timestamp", ""), item.get("feedback"), item.get("impacto_estimado")),
                    )
                    cnt += 1
                total["meta_learning"] = cnt
            except Exception:
                pass

        # fontes_descobertas
        fd = _caminho_json("fontes_descobertas.json")
        if fd.exists():
            try:
                dados = json.loads(fd.read_text(encoding="utf-8"))
                cnt = 0
                for dominio, info in dados.items():
                    c.execute(
                        "INSERT OR IGNORE INTO fontes_descobertas(dominio,ocorrencias,contextos,exemplo,promovida) VALUES(?,?,?,?,?)",
                        (
                            dominio,
                            info.get("ocorrencias", 1),
                            json.dumps(info.get("contextos", []), ensure_ascii=False),
                            info.get("exemplo", ""),
                            1 if info.get("promovida") else 0,
                        ),
                    )
                    cnt += 1
                total["fontes_descobertas"] = cnt
            except Exception:
                pass

        # evolucao/diario
        diario = _caminho_json("evolucao/diario.json")
        if diario.exists():
            try:
                dados = json.loads(diario.read_text(encoding="utf-8"))
                cnt = 0
                for dec in dados.get("decisoes", []):
                    c.execute(
                        """INSERT OR IGNORE INTO evolucao_diario(id,timestamp,estrategia,disciplina,prescricao,contexto,outcome_esperado,outcome_real,eficacia)
                           VALUES(?,?,?,?,?,?,?,?,?)""",
                        (
                            dec.get("id", ""),
                            dec.get("timestamp", ""),
                            dec.get("estrategia", ""),
                            dec.get("disciplina", ""),
                            dec.get("prescricao", ""),
                            json.dumps(dec.get("contexto", {}), ensure_ascii=False),
                            dec.get("outcome_esperado", ""),
                            dec.get("outcome_real", ""),
                            dec.get("eficacia"),
                        ),
                    )
                    cnt += 1
                total["evolucao_diario"] = cnt
            except Exception:
                pass

        # evolucao/auto_avaliacao
        aa = _caminho_json("evolucao/auto_avaliacao.json")
        if aa.exists():
            try:
                dados = json.loads(aa.read_text(encoding="utf-8"))
                cnt = 0
                for av in dados.get("avaliacoes", []):
                    c.execute(
                        """INSERT INTO evolucao_auto_avaliacao(timestamp,score_total,dimensoes,sugestao_melhoria,dimensao_mais_fraca)
                           VALUES(?,?,?,?,?)""",
                        (
                            av.get("timestamp", ""),
                            av.get("score_total"),
                            json.dumps(av.get("dimensoes", {}), ensure_ascii=False),
                            av.get("sugestao_melhoria", ""),
                            av.get("dimensao_mais_fraca", ""),
                        ),
                    )
                    cnt += 1
                total["evolucao_auto_avaliacao"] = cnt
            except Exception:
                pass

        # evolucao/experimentos
        exp = _caminho_json("evolucao/experimentos.json")
        if exp.exists():
            try:
                dados = json.loads(exp.read_text(encoding="utf-8"))
                cnt = 0
                for e in dados.get("experimentos", []):
                    c.execute(
                        """INSERT OR IGNORE INTO evolucao_experimentos(id,hipotese,condicao,grupo_a,grupo_b,vencedor,status)
                           VALUES(?,?,?,?,?,?,?)""",
                        (
                            e.get("id", ""),
                            e.get("hipotese", ""),
                            e.get("condicao", ""),
                            e.get("grupo_a", ""),
                            e.get("grupo_b", ""),
                            e.get("vencedor", ""),
                            e.get("status", "ativo"),
                        ),
                    )
                    cnt += 1
                total["evolucao_experimentos"] = cnt
            except Exception:
                pass

    return total


def resetar_db():
    """Dropa e recria o banco."""
    db = Database.inst()
    if db.path.exists():
        db.path.unlink()
    db.init_db()


if __name__ == "__main__":
    import sys
    if "--reset" in sys.argv:
        resetar_db()
        print("Banco recriado do zero.")
    r = migrar_json_para_sqlite()
    print("Migração concluída:")
    for tabela, n in sorted(r.items()):
        print(f"  {tabela}: {n} registros")
