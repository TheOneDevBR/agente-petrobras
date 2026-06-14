"""Persistência de JSON com escrita atômica.

Camada única e simples de leitura/escrita de arquivos JSON. A gravação é
atômica (arquivo temporário no mesmo diretório + ``os.replace``), evitando
corromper o arquivo se o processo cair no meio da escrita. Erros de escrita
NÃO são silenciados — propagam para o chamador.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

_SENTINEL = object()


def db_ler_json(caminho: Path | str, default: Any = _SENTINEL) -> Any:
    """Lê um JSON do disco.

    Retorna ``default`` se o arquivo não existir ou estiver corrompido.
    Sem ``default``, retorna ``{}`` nesses casos.
    """
    path = Path(caminho)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # OSError: arquivo ausente/ilegível. ValueError: JSON/UTF-8 inválido
        # (JSONDecodeError e UnicodeDecodeError são subclasses de ValueError).
        return {} if default is _SENTINEL else default


def db_gravar_json(caminho: Path | str, dados: Any) -> None:
    """Grava ``dados`` como JSON de forma atômica (temp + ``os.replace``)."""
    path = Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(dados, ensure_ascii=False, indent=2)

    # Arquivo temporário no MESMO diretório: os.replace só é atômico dentro do
    # mesmo sistema de arquivos. Em seguida, renomeia por cima do destino.
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
