"""Gerenciamento de Persistência via SQLite.

Fornece atomicidade e previne race conditions sincronizando
os arquivos JSON de dados com o banco de dados local agente.db.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

AQUI = Path(__file__).resolve().parent
DADOS_DIR = AQUI / "dados"

# Isolamento do ambiente de teste para não poluir o banco de produção
if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
    DB_PATH = DADOS_DIR / "agente_test.db"
else:
    DB_PATH = DADOS_DIR / "agente.db"


def init_db() -> None:
    """Garante a criação do diretório de dados e a tabela json_store com suporte a mtime."""
    DADOS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS json_store (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    mtime REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            try:
                conn.execute("ALTER TABLE json_store ADD COLUMN mtime REAL;")
            except sqlite3.OperationalError:
                pass
    finally:
        conn.close()


def _caminho_para_chave(caminho: Path | str) -> str:
    """Gera uma chave de busca consistente baseada no caminho relativo."""
    path = Path(caminho).resolve()
    try:
        return str(path.relative_to(DADOS_DIR)).replace("\\", "/")
    except ValueError:
        for p in list(path.parents) + [path]:
            if p.name == "dados":
                try:
                    return str(path.relative_to(p)).replace("\\", "/")
                except ValueError:
                    pass
        return path.name


_SENTINEL = object()


def db_ler_json(caminho: Path | str, default: Any = _SENTINEL) -> Any:
    """Lê o JSON a partir do SQLite, verificando se o arquivo físico foi atualizado externamente."""
    init_db()
    key = _caminho_para_chave(caminho)
    path = Path(caminho)

    current_mtime = None
    if path.exists():
        try:
            current_mtime = path.stat().st_mtime
        except Exception:
            pass

    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value, mtime FROM json_store WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            val_str, db_mtime = row
            # Se o mtime do disco bate com o do banco, retorna o do banco para velocidade
            if current_mtime is not None and db_mtime is not None and abs(current_mtime - db_mtime) < 0.01:
                return json.loads(val_str)
    except Exception:
        pass
    finally:
        conn.close()

    # Fallback para o disco se falhar, mtime diferir, ou não constar no SQLite
    if path.exists():
        try:
            conteudo = path.read_text(encoding="utf-8")
            dados = json.loads(conteudo)
            # Sincroniza com o SQLite
            db_gravar_json(caminho, dados)
            return dados
        except Exception:
            pass
    return {} if default is _SENTINEL else default


def db_gravar_json(caminho: Path | str, dados: Any) -> None:
    """Grava os dados no SQLite sob transação e atualiza o arquivo físico."""
    init_db()
    key = _caminho_para_chave(caminho)
    val_str = json.dumps(dados, ensure_ascii=False, indent=2)

    # Gravação no disco (cache de compatibilidade e backups) primeiro para capturar o mtime correto
    current_mtime = None
    try:
        path = Path(caminho)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(val_str, encoding="utf-8")
        current_mtime = path.stat().st_mtime
    except Exception:
        pass

    # Gravação atômica no SQLite
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    try:
        with conn:
            conn.execute("""
                INSERT INTO json_store (key, value, mtime, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, mtime=excluded.mtime, updated_at=CURRENT_TIMESTAMP;
            """, (key, val_str, current_mtime))
    except Exception:
        pass
    finally:
        conn.close()
