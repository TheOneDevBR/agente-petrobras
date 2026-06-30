"""RAG local sobre materiais de estudo (apostilas) via chromadb.

Indexa textos (markdown extraído de apostilas/PDFs) numa coleção chromadb
persistente e local, com embeddings LOCAIS (ONNX all-MiniLM-L6-v2 — sem API).

Melhorias implementadas:
  - Chunking semântico (quebra em fronteiras de frase, não caractere fixo)
  - Reranker cross-encoder (segundo estágio, se disponível)
  - MMR (Maximum Marginal Relevance) para diversidade nos trechos
  - Prompt template com citação obrigatória de fonte

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

_CHUNK_MIN = 300
_CHUNK_MAX = 800
_MMR_LAMBDA = 0.6
_RERANK_K = 12


def disponivel() -> bool:
    try:
        import chromadb  # noqa: F401
        return True
    except ImportError:
        return False


def _tem_reranker() -> bool:
    try:
        from sentence_transformers import CrossEncoder  # noqa: F401
        return True
    except ImportError:
        return False


_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None and _tem_reranker():
        from sentence_transformers import CrossEncoder
        try:
            _reranker = CrossEncoder(
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
                device="cpu",
            )
        except Exception:
            _reranker = False
    return _reranker if _reranker is not False else None


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
    """Chunking semântico: quebra em sentenças, agrupa até _CHUNK_MAX.

    Sentenças isoladas maiores que _CHUNK_MAX (ex.: parágrafos sem pontuação)
    são fatiadas em pedaços de no máximo _CHUNK_MAX caracteres, garantindo que
    nenhum chunk exceda o limite — chunks gigantes degradam o embedding.
    """
    bruto = re.split(r"(?<=[.!?])\s+", texto.replace("\n", " "))
    sentencas: list[str] = []
    for s in bruto:
        s = s.strip()
        if len(s) < 10:
            continue
        if len(s) <= _CHUNK_MAX:
            sentencas.append(s)
        else:
            sentencas.extend(
                s[i:i + _CHUNK_MAX] for i in range(0, len(s), _CHUNK_MAX)
            )
    chunks: list[str] = []
    buf = ""
    for s in sentencas:
        if buf and len(buf) + len(s) + 1 > _CHUNK_MAX:
            chunks.append(buf)
            buf = s
        else:
            buf = f"{buf} {s}" if buf else s
    if buf:
        chunks.append(buf)
    return [c.strip() for c in chunks if len(c.strip()) >= _CHUNK_MIN]


def _id(fonte: str, texto: str) -> str:
    return hashlib.sha1(
        f"{fonte}::{texto}".encode(), usedforsecurity=False
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
    for i in range(0, len(ids), 256):
        col.upsert(ids=ids[i:i + 256], documents=docs[i:i + 256], metadatas=metas[i:i + 256])
    return len(ids)


def _rerank(trechos: list[dict], query: str, k: int) -> list[dict]:
    """Reranka com cross-encoder, mantendo os k melhores."""
    reranker = _get_reranker()
    if not reranker:
        return trechos[:k]
    pares = [(query, t["texto"]) for t in trechos]
    scores = reranker.predict(pares, show_progress_bar=False)
    for t, s in zip(trechos, scores):
        t["score_rerank"] = float(s)
    trechos.sort(key=lambda t: t.get("score_rerank", 0), reverse=True)
    return trechos[:k]


def _mmr(trechos: list[dict], k: int, lam: float = _MMR_LAMBDA) -> list[dict]:
    """Maximum Marginal Relevance: balanceia relevância e diversidade."""
    if len(trechos) <= k:
        return trechos
    import math
    selecionados: list[dict] = [trechos[0]]
    candidatos = list(trechos[1:])
    while len(selecionados) < k and candidatos:
        scores = []
        for c in candidatos:
            sim_ref = c.get("score_rerank", 1.0 - c.get("distancia", 1.0))
            sim_sel = max(
                _cos_sim_simples(c["texto"], s["texto"])
                for s in selecionados
            ) if selecionados else 0
            mmr_score = lam * sim_ref - (1 - lam) * sim_sel
            scores.append(mmr_score)
        best_idx = int(max(range(len(candidatos)), key=lambda i: scores[i]))
        selecionados.append(candidatos.pop(best_idx))
    return selecionados


def _cos_sim_simples(a: str, b: str) -> float:
    """Cosseno aproximado baseado em unigramas (rápido, sem modelo)."""
    set_a = set(a.lower().split()[:200])
    set_b = set(b.lower().split()[:200])
    inter = len(set_a & set_b)
    denom = (len(set_a) ** 0.5) * (len(set_b) ** 0.5)
    return inter / denom if denom > 0 else 0.0


def buscar(query: str, k: int = 4) -> list[dict[str, Any]]:
    """Recupera os k trechos mais relevantes (com rerank + MMR)."""
    if not disponivel() or not RAG_DIR.exists():
        return []
    try:
        col = _colecao()
        res = col.query(query_texts=[query], n_results=_RERANK_K)
    except Exception:
        return []
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[None] * len(docs)])[0]
    trechos = [
        {"texto": d, "fonte": (m or {}).get("fonte", "?"), "distancia": dist}
        for d, m, dist in zip(docs, metas, dists)
    ]
    trechos = _rerank(trechos, query, k * 2)
    return _mmr(trechos, k)


def contexto_para_prompt(query: str, k: int = 4, max_chars: int = 2500) -> str:
    """Bloco de contexto RAG com formatação melhorada."""
    trechos = buscar(query, k=k)
    if not trechos:
        return ""
    linhas = [
        "[MATERIAL_DE_ESTUDO]",
        "(Trechos das suas apostilas — use como apoio factual. "
        "Cite a fonte entre colchetes ao final de cada afirmação.)",
        "",
    ]
    total = 0
    for i, t in enumerate(trechos, 1):
        fonte = t["fonte"]
        score = t.get("score_rerank", None)
        score_str = f" [relevância: {score:.2f}]" if score is not None else ""
        cabecalho = f"[{i}] Fonte: {fonte}{score_str}"
        bloco = f"{cabecalho}\n{t['texto'].strip()}"
        if total + len(bloco) > max_chars:
            disponivel_chars = max_chars - total - len(cabecalho) - 10
            if disponivel_chars > 200:
                bloco = f"{cabecalho}\n{t['texto'].strip()[:disponivel_chars]}..."
            else:
                break
        linhas.append(bloco)
        total += len(bloco)
    linhas.append("")
    linhas.append(
        "(Regra: só responda com base nestes trechos. "
        "Se um trecho não cobrir a pergunta, diga 'Não encontrei nos materiais.' "
        "Nunca invente artigos de lei ou jurisprudência.)"
    )
    return "\n".join(linhas)


def estatisticas() -> dict[str, Any]:
    if not disponivel() or not RAG_DIR.exists():
        return {"disponivel": disponivel(), "chunks": 0, "reranker": _tem_reranker()}
    try:
        return {
            "disponivel": True,
            "chunks": _colecao().count(),
            "reranker": _tem_reranker(),
            "chunk_min": _CHUNK_MIN,
            "chunk_max": _CHUNK_MAX,
            "mmr_lambda": _MMR_LAMBDA,
        }
    except Exception:
        return {"disponivel": True, "chunks": 0, "reranker": _tem_reranker()}


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
