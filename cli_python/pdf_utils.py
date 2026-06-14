"""Extração de texto de PDFs usando opendataloader-pdf.

Requer:
  - Java 11+ (opendataloader-pdf depende de JVM)
  - pip install opendataloader-pdf

Uso:
    from pdf_utils import extrair_texto_pdf, extrair_texto_pdf_para_contexto

    texto = extrair_texto_pdf("editais/edital.pdf")
    contexto = extrair_texto_pdf_para_contexto("editais/edital.pdf", max_chars=4000)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

try:
    import opendataloader_pdf as odp
    _TEM_OPENDATALOADER = True
except ImportError:
    _TEM_OPENDATALOADER = False

try:
    from local_web import _CACHE_DIR
    CACHE_DIR = _CACHE_DIR
except ImportError:
    CACHE_DIR = Path(__file__).resolve().parent / ".web_cache"

PDF_CACHE_TTL = 86400  # 24h


def disponivel() -> bool:
    """Verifica se opendataloader-pdf está instalado e Java disponível."""
    return _TEM_OPENDATALOADER


def extrair_texto_pdf(
    caminho: str | Path,
    formato: str = "markdown",
    paginas: str | None = None,
    timeout: int = 120,
) -> str:
    """Extrai texto de um PDF usando opendataloader-pdf.

    Args:
        caminho: Caminho do arquivo PDF.
        formato: 'markdown', 'text' ou 'json'.
        paginas: Exemplo "1,3,5-7". None = todas.
        timeout: Timeout em segundos para conversão.

    Returns:
        Texto extraído.

    Raises:
        FileNotFoundError: se o PDF não existir.
        RuntimeError: se opendataloader não estiver disponível ou falhar.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"PDF não encontrado: {caminho}")

    if not _TEM_OPENDATALOADER:
        raise RuntimeError(
            "opendataloader-pdf não instalado. "
            "Instale com: pip install opendataloader-pdf"
        )

    with tempfile.TemporaryDirectory(prefix="odp_") as tmpdir:
        kwargs: dict[str, Any] = {
            "input_path": [str(caminho.resolve())],
            "output_dir": tmpdir,
            "format": formato,
            "quiet": True,
        }
        if paginas:
            kwargs["pages"] = paginas

        try:
            odp.convert(**kwargs)
        except Exception as e:
            raise RuntimeError(f"Falha ao extrair PDF '{caminho.name}': {e}")

        out_dir = Path(tmpdir)
        if formato == "json":
            json_files = list(out_dir.glob("*.json"))
            if json_files:
                try:
                    data = json.loads(json_files[0].read_text(encoding="utf-8"))
                    textos: list[str] = []
                    for el in data.get("elements", []):
                        if el.get("content"):
                            textos.append(el["content"])
                    return "\n".join(textos)
                except (json.JSONDecodeError, KeyError, OSError):
                    pass
        elif formato in ("markdown", "text"):
            ext = ".md" if formato == "markdown" else ".txt"
            out_files = list(out_dir.glob(f"*{ext}"))
            if out_files:
                try:
                    return out_files[0].read_text(encoding="utf-8")
                except OSError:
                    pass

        return ""


def extrair_texto_pdf_para_contexto(
    caminho: str | Path,
    max_chars: int = 8000,
    paginas: str | None = None,
    force: bool = False,
) -> str:
    """Extrai texto de PDF para usar como contexto LLM (com cache).

    O resultado é cacheadono mesmo diretório .web_cache/ usado pelo
    módulo local_web, com TTL de 24h.

    Args:
        caminho: Caminho do PDF.
        max_chars: Máximo de chars retornados.
        paginas: Páginas a extrair (ex: "1-5").
        force: Se True, ignora cache.

    Returns:
        Texto extraído (truncado em max_chars).
    """
    caminho = Path(caminho).resolve()
    import hashlib
    cache_key = f"pdf:{hashlib.md5(str(caminho).encode()).hexdigest()}"
    cache_file = CACHE_DIR / f"{cache_key.replace(':', '_')}.json.gz"

    if not force and cache_file.exists():
        import gzip
        try:
            data = json.loads(gzip.decompress(cache_file.read_bytes()))
            from time import time
            if time() < data["expires"]:
                return data["value"]
        except Exception:
            pass

    texto = extrair_texto_pdf(caminho, paginas=paginas)
    if not texto:
        return ""

    if len(texto) > max_chars:
        texto = texto[:max_chars] + "\n\n…(PDF truncado)"

    import gzip
    from time import time
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        cache_file.write_bytes(
            gzip.compress(
                json.dumps({"expires": time() + PDF_CACHE_TTL, "value": texto}).encode("utf-8"),
                compresslevel=6,
            )
        )
    except OSError:
        pass

    return texto


def extrair_tabelas_pdf(caminho: str | Path, paginas: str | None = None) -> list[list[str]]:
    """Extrai tabelas de um PDF como listas de strings (CSV-like).

    Requer opendataloader-pdf com saída JSON.

    Args:
        caminho: Caminho do PDF.
        paginas: Páginas a extrair.

    Returns:
        Lista de tabelas, cada tabela é uma lista de linhas.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"PDF não encontrado: {caminho}")

    if not _TEM_OPENDATALOADER:
        raise RuntimeError("opendataloader-pdf não instalado")

    import tempfile
    with tempfile.TemporaryDirectory(prefix="odp_") as tmpdir:
        kwargs: dict[str, Any] = {
            "input_path": [str(caminho.resolve())],
            "output_dir": tmpdir,
            "format": "json",
            "quiet": True,
        }
        if paginas:
            kwargs["pages"] = paginas

        try:
            odp.convert(**kwargs)
        except Exception as e:
            raise RuntimeError(f"Falha ao extrair PDF '{caminho.name}': {e}")

        json_files = list(Path(tmpdir).glob("*.json"))
        if not json_files:
            return []

        try:
            data = json.loads(json_files[0].read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        tabelas: list[list[str]] = []
        for el in data.get("elements", []):
            if el.get("type") == "table":
                conteudo = el.get("content", "")
                linhas = [ln.strip() for ln in conteudo.split("\n") if ln.strip()]
                if linhas:
                    tabelas.append(linhas)
        return tabelas
