"""Extrator de provas anteriores CESGRANRIO/Petrobras em PDF.

Baixa PDFs de fontes conhecidas, extrai texto com opendataloader-pdf,
e gera relatório do conteúdo encontrado.

Uso:
    python extrair_provas_pdf.py                         # baixa e extrai todas
    python extrair_provas_pdf.py --baixar               # só baixar
    python extrair_provas_pdf.py --extrair diretorio/   # extrair PDFs já baixados
    python extrair_provas_pdf.py --gerar-questoes       # tenta gerar questões via LLM

Requer:
    pip install opendataloader-pdf requests beautifulsoup4
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

AQUI = Path(__file__).resolve().parent
PDF_DIR = AQUI / "provas_baixadas"
RESULTADOS_DIR = AQUI / "provas_extraidas"
PROVAS_URLS_PATH = AQUI / "provas_urls.txt"

try:
    from pdf_utils import disponivel, extrair_tabelas_pdf, extrair_texto_pdf
except ImportError:
    def extrair_texto_pdf(*a, **kw): raise RuntimeError("pdf_utils não encontrado")
    def extrair_tabelas_pdf(*a, **kw): raise RuntimeError("pdf_utils não encontrado")
    def disponivel(): return False

try:
    from local_web import web_fetch, web_search
except ImportError:
    def web_search(*a, **kw): return []
    def web_fetch(*a, **kw): return ""


# Fontes conhecidas de provas CESGRANRIO/Petrobras
FONTES_PROVAS = [
    {
        "nome": "CESGRANRIO - Provas Anteriores",
        "url": "https://www.cesgranrio.org.br/concursos/provas_anteriores",
        "tags": ["cesgranrio", "provas"],
    },
    {
        "nome": "PCI Concursos - Provas Petrobras",
        "url": "https://www.pciconcursos.com.br/provas/petrobras",
        "tags": ["petrobras", "provas"],
    },
    {
        "nome": "QConcursos - Petrobras",
        "url": "https://www.qconcursos.com/questoes-de-concursos/provas/petrobras",
        "tags": ["petrobras", "questoes"],
    },
]


def _baixar_pdf(url: str, destino: Path) -> bool:
    """Baixa um PDF de uma URL (com fallback de SSL e checagem de bytes mágicos)."""
    import requests
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for verify in (True, False):
        try:
            if not verify:
                import urllib3
                urllib3.disable_warnings()
            resp = requests.get(url, timeout=30, headers=headers, verify=verify)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            eh_pdf = ("pdf" in content_type or url.lower().endswith(".pdf")
                      or resp.content[:4] == b"%PDF")
            if not eh_pdf:
                print(f"   ⚠ URL não parece ser PDF: {content_type}")
                return False
            destino.write_bytes(resp.content)
            return True
        except Exception as e:
            # SSL: repete sem verificação (cert store local incompleto)
            if type(e).__name__ == "SSLError" and verify:
                continue
            print(f"   [erro ao baixar {url}: {e}]")
            return False
    return False


def _listar_pdfs_cesgranrio() -> list[dict]:
    """Busca na web por provas CESGRANRIO em PDF e retorna lista de URLs."""
    urls_vistas: set[str] = set()
    resultados: list[dict] = []

    # filetype:pdf traz PDF real; 'comentada' tende a ter questao+gabarito juntos
    queries = [
        "prova comentada Petrobras CESGRANRIO gabarito filetype:pdf",
        "prova gabarito Petrobras CESGRANRIO filetype:pdf",
        "prova Transpetro CESGRANRIO gabarito filetype:pdf",
    ]

    def _parece_pdf(u: str) -> bool:
        ul = u.lower()
        return ("pdf" in ul or "gabarito" in ul or "/arquivo" in ul
                or "storage.ashx" in ul)

    for q in queries:
        try:
            busca = web_search(q, max_results=6)
        except Exception as e:
            print(f"   [erro busca: {e}]")
            continue
        for r in busca:
            url = r.get("url", "")
            if not url or url in urls_vistas:
                continue
            urls_vistas.add(url)
            if _parece_pdf(url):
                resultados.append({
                    "url": url,
                    "titulo": r.get("title", url.split("/")[-1]),
                    "fonte": q,
                })
            else:
                try:
                    conteudo = web_fetch(url, max_chars=2000)
                    import re
                    pdfs = re.findall(r'(https?://[^\s"\']+\.pdf)', conteudo)
                    for pdf_url in pdfs[:3]:
                        if pdf_url not in urls_vistas:
                            urls_vistas.add(pdf_url)
                            resultados.append({
                                "url": pdf_url,
                                "titulo": pdf_url.split("/")[-1],
                                "fonte": url,
                            })
                except Exception:
                    pass

    return resultados


def _urls_curadas(arquivo: Path | None = None) -> list[dict]:
    """Lê a lista curada de URLs diretas de PDF (provas_urls.txt).

    Caminho confiável que NÃO depende da busca web (cujo backend grátis ignora
    os operadores site:/filetype:). Uma URL por linha; '#' e linhas vazias são
    ignoradas.
    """
    caminho = arquivo or PROVAS_URLS_PATH
    if not caminho.exists():
        return []
    provas: list[dict] = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        url = linha.strip()
        if not url or url.startswith("#"):
            continue
        provas.append({
            "url": url,
            "titulo": url.split("/")[-1],
            "fonte": "curado",
        })
    return provas


def baixar_curado(arquivo: Path | None = None, limite: int = 50) -> list[Path]:
    """Baixa as provas da lista curada (provas_urls.txt)."""
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    provas = _urls_curadas(arquivo)
    print(f"Lista curada: {len(provas)} URL(s)")
    return _baixar_lista(provas, limite)


def _baixar_lista(provas: list[dict], limite: int) -> list[Path]:
    """Baixa uma lista de candidatos {url, titulo, ...} para PDF_DIR."""
    baixados: list[Path] = []
    for i, p in enumerate(provas[:limite], 1):
        nome = p["url"].split("/")[-1].split("?")[0]
        if not nome.endswith(".pdf"):
            nome = f"prova_{i}.pdf"
        destino = PDF_DIR / nome
        if destino.exists():
            print(f"  [{i}/{min(limite, len(provas))}] já existe: {nome}")
            baixados.append(destino)
            continue
        print(f"  [{i}/{min(limite, len(provas))}] baixando: {nome}")
        if _baixar_pdf(p["url"], destino):
            print(f"    ✓ {destino.stat().st_size // 1024} KB")
            baixados.append(destino)
        else:
            print("    ✗ falha")
    return baixados


def baixar_provas(limite: int = 10) -> list[Path]:
    """Busca e baixa provas em PDF."""
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    print("Buscando provas CESGRANRIO/Petrobras...")
    provas = _listar_pdfs_cesgranrio()
    print(f"  {len(provas)} PDF(s) encontrado(s)")

    baixados: list[Path] = []
    for i, p in enumerate(provas[:limite], 1):
        nome = p["url"].split("/")[-1].split("?")[0]
        if not nome.endswith(".pdf"):
            nome = f"prova_{i}.pdf"
        destino = PDF_DIR / nome
        if destino.exists():
            print(f"  [{i}/{limite}] já existe: {nome}")
            baixados.append(destino)
            continue
        print(f"  [{i}/{limite}] baixando: {nome}")
        if _baixar_pdf(p["url"], destino):
            print(f"    ✓ {destino.stat().st_size // 1024} KB")
            baixados.append(destino)
        else:
            print("    ✗ falha")

    return baixados


def extrair_provas(pdfs: list[Path] | None = None) -> list[dict]:
    """Extrai texto de PDFs de provas."""
    if pdfs is None:
        pdfs = sorted(PDF_DIR.glob("*.pdf"))

    if not pdfs:
        print("Nenhum PDF para extrair.")
        return []

    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    resultados: list[dict] = []

    for pdf in pdfs:
        print(f"Extraindo: {pdf.name}")
        try:
            texto = extrair_texto_pdf(str(pdf), formato="markdown")
            if not texto:
                print("  ⚠ texto vazio")
                continue
            saida = RESULTADOS_DIR / f"{pdf.stem}.md"
            saida.write_text(texto, encoding="utf-8")
            chars = len(texto)
            print(f"  ✓ {chars} chars → {saida.name}")
            resultados.append({
                "arquivo": pdf.name,
                "chars": chars,
                "texto": texto[:500],
                "caminho": str(saida),
            })
        except Exception as e:
            print(f"  ✗ erro: {e}")

    return resultados


def gerar_questoes_do_texto(texto: str, disciplina: str = "Geral") -> list[dict]:
    """Tenta extrair questões de um texto de prova usando heurísticas simples.

    Retorna lista de dicts com pergunta, opcoes (se encontrar) e texto bruto.
    """
    questoes: list[dict] = []
    blocos = texto.split("\n\n")
    for bloco in blocos:
        linhas = [ln.strip() for ln in bloco.split("\n") if ln.strip()]
        if len(linhas) < 3:
            continue
        for i, linha in enumerate(linhas):
            if any(m in linha.lower() for m in ["assinale", "marque", "indique", "qual"]):
                opcoes_encontradas = []
                for ln in linhas[i + 1:i + 6]:
                    import re
                    m = re.match(r"^[\(\)]?[A-Ea-e][\)\.\s]", ln)
                    if m:
                        opcoes_encontradas.append(ln)
                questoes.append({
                    "enunciado": linha,
                    "opcoes": opcoes_encontradas if len(opcoes_encontradas) == 5 else [],
                    "total_linhas": len(linhas),
                    "disciplina": disciplina,
                })
    return questoes


def relatorio_provas(resultados: list[dict]) -> str:
    """Gera relatório Markdown das provas extraídas."""
    linhas = [
        "# Provas CESGRANRIO/Petrobras Extraídas",
        f"**Data:** {date.today().isoformat()}",
        f"**Total de PDFs:** {len(resultados)}",
        "",
        "## Resultados",
        "",
    ]
    for r in resultados:
        linhas += [
            f"### {r['arquivo']}",
            f"- **Chars:** {r['chars']}",
            f"- **Preview:** {r['texto'][:200]}...",
            "",
        ]

    # Tenta extrair questões
    total_questoes = 0
    for r in resultados:
        qs = gerar_questoes_do_texto(r["texto"])
        total_questoes += len(qs)

    linhas += [
        "## Questões Detectadas",
        f"Total estimado: {total_questoes}",
        "",
        "## Metodologia",
        "- PDFs baixados via busca web (CESGRANRIO, PCI, QConcursos)",
        "- Extração com opendataloader-pdf (markdown)",
        "- Detecção de questões por heurística de padrões textuais",
        "",
    ]

    return "\n".join(linhas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrator de provas CESGRANRIO/Petrobras")
    parser.add_argument("--baixar", action="store_true", help="Só baixar PDFs (via busca web)")
    parser.add_argument("--curado", action="store_true",
                        help="Baixar da lista curada provas_urls.txt (confiável, sem busca)")
    parser.add_argument("--extrair", nargs="?", const="auto", help="Extrair PDFs (diretório ou auto)")
    parser.add_argument("--gerar-questoes", action="store_true", help="Gerar questões via heurística")
    parser.add_argument("--limite", type=int, default=50, help="Limite de PDFs para baixar")
    args = parser.parse_args()

    if not disponivel():
        print("⚠ opendataloader-pdf não disponível. Instale com: pip install opendataloader-pdf")
        if not args.baixar:
            print("  Continuando apenas com busca/download (sem extração).")

    if args.curado:
        baixados = baixar_curado(limite=args.limite)
        if baixados:
            print(f"\n✓ {len(baixados)} PDF(s) em {PDF_DIR}")
        else:
            print("\nNenhum PDF baixado da lista curada.")
    elif args.baixar or (not args.extrair and not args.gerar_questoes):
        baixados = baixar_provas(limite=args.limite)
        if baixados:
            print(f"\n✓ {len(baixados)} PDF(s) em {PDF_DIR}")
        else:
            print("\nNenhum PDF baixado.")

    if args.extrair:
        if args.extrair == "auto":
            pdfs = None
        else:
            pdf_dir = Path(args.extrair)
            pdfs = sorted(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else None
        resultados = extrair_provas(pdfs)
        if resultados:
            relatorio = relatorio_provas(resultados)
            relatorio_path = RESULTADOS_DIR / "relatorio_extracoes.md"
            relatorio_path.write_text(relatorio, encoding="utf-8")
            print(f"\n✓ Relatório salvo em {relatorio_path}")
    elif args.gerar_questoes:
        resultados = extrair_provas()
        if not resultados:
            print("Nenhum resultado para gerar questões.")
            return
        todas_questoes = []
        for r in resultados:
            qs = gerar_questoes_do_texto(r["texto"])
            if qs:
                print(f"  {r['arquivo']}: {len(qs)} questão(ões) detectada(s)")
                todas_questoes.extend(qs)
        questoes_path = RESULTADOS_DIR / "questoes_detectadas.json"
        questoes_path.write_text(
            json.dumps(todas_questoes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n✓ {len(todas_questoes)} questão(ões) salva(s) em {questoes_path}")


if __name__ == "__main__":
    main()
