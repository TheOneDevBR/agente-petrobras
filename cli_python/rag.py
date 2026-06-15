"""RAG local sobre materiais de estudo (apostilas) via chromadb.

Indexa textos (markdown extraído de apostilas/PDFs) numa coleção chromadb
persistente e local, com embeddings LOCAIS (ONNX all-MiniLM-L6-v2 — sem API).
No chat, recupera os trechos mais relevantes à pergunta e injeta no prompt.

O índice fica em dados/rag_index/ (gitignored) — não versiona conteúdo protegido.

Uso:
    python rag.py --indexar "<dir-ou-arquivo>"   # indexa .md/.txt
    python rag.py --buscar "regência verbal"      # testa a recuperação
    python rag.py --stats
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

AQUI = Path(__file__).resolve().parent
RAG_DIR = AQUI / "dados" / "rag_index"
COLECAO = "materiais_petrobras"

_CHUNK_CHARS = 1000
_CHUNK_OVERLAP = 150
_MIN_CHUNK = 50


def disponivel() -> bool:
    """True se o chromadb estiver instalado."""
    try:
        import chromadb  # noqa: F401
        return True
    except ImportError:
        return False


def _colecao():
    import chromadb
    from chromadb.config import Settings
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(RAG_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(COLECAO)


def _chunk(texto: str) -> list[str]:
    """Quebra o texto em pedaços de ~_CHUNK_CHARS, agrupando por parágrafos."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 1 <= _CHUNK_CHARS:
            buf = f"{buf}\n{p}" if buf else p
        else:
            if buf:
                chunks.append(buf)
                buf = ""
            if len(p) > _CHUNK_CHARS:  # parágrafo gigante → fatia com overlap
                for i in range(0, len(p), _CHUNK_CHARS - _CHUNK_OVERLAP):
                    chunks.append(p[i:i + _CHUNK_CHARS])
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return [c.strip() for c in chunks if len(c.strip()) >= _MIN_CHUNK]


def _id(fonte: str, texto: str) -> str:
    # ID de conteúdo (não-criptográfico) para deduplicar chunks no índice.
    return hashlib.sha1(
        f"{fonte}::{texto}".encode("utf-8"), usedforsecurity=False
    ).hexdigest()[:16]


def indexar(arquivos: list[Path]) -> int:
    """Indexa arquivos .md/.txt na coleção (upsert). Retorna nº de chunks."""
    col = _colecao()
    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []
    for arq in arquivos:
        try:
            texto = Path(arq).read_text(encoding="utf-8")
        except OSError:
            continue
        fonte = Path(arq).stem
        for ch in _chunk(texto):
            cid = _id(fonte, ch)
            if cid in ids:
                continue
            ids.append(cid)
            docs.append(ch)
            metas.append({"fonte": fonte})
    if not ids:
        return 0
    for i in range(0, len(ids), 256):  # lotes (chromadb limita batch)
        col.upsert(ids=ids[i:i + 256], documents=docs[i:i + 256], metadatas=metas[i:i + 256])
    return len(ids)


def buscar(query: str, k: int = 4) -> list[dict[str, Any]]:
    """Recupera os k trechos mais relevantes. [] se indisponível/sem índice."""
    if not disponivel() or not RAG_DIR.exists():
        return []
    try:
        col = _colecao()
        res = col.query(query_texts=[query], n_results=k)
    except Exception:
        return []
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[None] * len(docs)])[0]
    return [
        {"texto": d, "fonte": (m or {}).get("fonte", "?"), "distancia": dist}
        for d, m, dist in zip(docs, metas, dists)
    ]


def contexto_para_prompt(query: str, k: int = 4, max_chars: int = 2000) -> str:
    """Bloco de contexto RAG para injetar no system prompt (ou '' se nada)."""
    trechos = buscar(query, k=k)
    if not trechos:
        return ""
    linhas = ["[MATERIAL_DE_ESTUDO] (trechos relevantes das suas apostilas)"]
    total = 0
    for t in trechos:
        bloco = f"— ({t['fonte']}) {t['texto'].strip()}"
        if total + len(bloco) > max_chars:
            bloco = bloco[: max(0, max_chars - total)]
        if bloco:
            linhas.append(bloco)
            total += len(bloco)
        if total >= max_chars:
            break
    linhas.append("(Use como apoio factual; cite a fonte quando usar. Não invente além disto.)")
    return "\n".join(linhas)


def estatisticas() -> dict[str, Any]:
    if not disponivel() or not RAG_DIR.exists():
        return {"disponivel": disponivel(), "chunks": 0}
    try:
        return {"disponivel": True, "chunks": _colecao().count()}
    except Exception:
        return {"disponivel": True, "chunks": 0}


def main() -> None:
    import argparse
    import sys
    for _s in (sys.stdout, sys.stderr):  # console Windows (cp1252) → UTF-8
        try:
            _s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description="RAG local de materiais de estudo")
    p.add_argument("--indexar", metavar="CAMINHO", help="arquivo ou diretório (.md/.txt)")
    p.add_argument("--buscar", metavar="QUERY", help="testa a recuperação")
    p.add_argument("--stats", action="store_true", help="mostra estatísticas do índice")
    p.add_argument("-k", type=int, default=4, help="nº de trechos a recuperar")
    args = p.parse_args()

    if not disponivel():
        print("chromadb não instalado. Rode: pip install chromadb")
        return

    if args.indexar:
        base = Path(args.indexar)
        if base.is_dir():
            arqs = sorted(base.rglob("*.md")) + sorted(base.rglob("*.txt"))
        else:
            arqs = [base]
        n = indexar(arqs)
        print(f"✓ {n} chunk(s) de {len(arqs)} arquivo(s). Total no índice: {estatisticas()['chunks']}")

    if args.buscar:
        trechos = buscar(args.buscar, k=args.k)
        if not trechos:
            print("(sem resultados — índice vazio? rode --indexar primeiro)")
        for i, t in enumerate(trechos, 1):
            print(f"\n[{i}] ({t['fonte']}) dist={t['distancia']:.3f}")
            print(t["texto"][:300])

    if args.stats:
        print(estatisticas())


if __name__ == "__main__":
    main()
