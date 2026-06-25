"""Organização de Provas e Editais Petrobras por cargo.

Baixa editais/provas/gabaritos de fontes (prioridade às OFICIAIS — CESGRANRIO),
organiza em ``Petrobras_[Ano]/[Cargo]/{Editais,Provas,Gabaritos}/`` preservando o
arquivo original, registra a URL de origem em um sidecar ``.fonte.txt`` (sem
editar o PDF) e gera um índice CSV.

Regras (do pedido):
- Preserva o arquivo original (não converte nem edita o conteúdo).
- Registra a URL de origem de cada arquivo.
- Material indisponível é MARCADO como "indisponível" no índice, nunca omitido.

Uso:
    python organizar_provas_editais.py                 # baixa + organiza + índice
    python organizar_provas_editais.py --no-baixar     # só (re)organiza o que já existe + índice
    python organizar_provas_editais.py --raiz CAMINHO  # raiz de saída custom
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ_SAIDA = AQUI / "dados" / "provas_editais"
PROVAS_URLS_PATH = AQUI / "provas_urls.txt"

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except (AttributeError, ValueError):
    pass


@dataclass
class Item:
    """Um material a organizar (edital, prova ou gabarito de um cargo)."""
    ano: str
    cargo: str
    tipo: str          # "Editais" | "Provas" | "Gabaritos"
    url: str
    banca: str = ""
    edital_num: str = ""
    data: str = ""
    fonte: str = ""    # "oficial" | "espelho"
    status: str = "pendente"
    arquivo: str = ""


# ── Catálogo OFICIAL curado (CESGRANRIO) ─────────────────────────────────────
# storage.ashx do CESGRANRIO é a fonte oficial dos PDFs.
def _ofc(id_concurso: str, nome_arquivo: str) -> str:
    return (f"https://inscricao.cesgranrio.com.br/storage.ashx?file=pdf%2F"
            f"{id_concurso}%2F{nome_arquivo}")


# CDN oficial do CEBRASPE (concurso Petrobras 2023, nível médio/técnico).
_CB = "https://cdn.cebraspe.org.br/concursos/petrobras_23_nm/arquivos"

CATALOGO_OFICIAL: list[Item] = [
    Item(ano="2018", cargo="Geral (todos os cargos)", tipo="Editais",
         url=_ofc("petrobras0118", "petrobras0118_edital.pdf"),
         banca="CESGRANRIO", edital_num="PSP RH 1/2018", fonte="oficial"),
    Item(ano="2011", cargo="Geral (todos os cargos)", tipo="Editais",
         url=_ofc("petrobras0111", "petrobras0111_edital.pdf"),
         banca="CESGRANRIO", edital_num="PSP RH 1/2011", fonte="oficial"),
    # Petrobras 2023 (CEBRASPE, nível médio) — prova + gabarito OFICIAIS
    Item(ano="2023", cargo="Geral (Nível Médio/Técnico)", tipo="Provas",
         url=f"{_CB}/822_PETROBRAS_23_CB1_01.PDF",
         banca="CEBRASPE", edital_num="PSP RH 2023", fonte="oficial"),
    Item(ano="2023", cargo="Geral (Nível Médio/Técnico)", tipo="Gabaritos",
         url=f"{_CB}/GAB_DEFINITIVO_822_PETROBRAS_23_CB1_01.PDF",
         banca="CEBRASPE", edital_num="PSP RH 2023", fonte="oficial"),
]

# Concursos cuja fonte oficial direta não foi localizada — marcar, não omitir.
PENDENTES_OFICIAIS: list[Item] = []


# ── Derivação de cargo/tipo a partir do nome do arquivo ──────────────────────
_RX_NOME = re.compile(
    r"(?P<banca>cesgranrio|cespe-cebraspe|cebraspe)-(?P<ano>\d{4})-"
    r"(?P<org>petrobras|transpetro)-(?P<resto>.+?)-(?P<tipo>prova|gabarito)\b",
    re.IGNORECASE,
)

_TIPO_MAP = {"prova": "Provas", "gabarito": "Gabaritos", "edital": "Editais"}


def cargo_legivel(slug: str) -> str:
    """'engenheiro-de-petroleo-junior' → 'Engenheiro De Petroleo Junior'."""
    palavras = [p for p in slug.replace("_", "-").split("-") if p]
    return " ".join(w.capitalize() for w in palavras) or "Indefinido"


def parse_item_de_url(url: str) -> Item | None:
    """Extrai {ano, cargo, tipo} do nome do arquivo de uma URL de prova/gabarito."""
    nome = url.split("/")[-1].split("?")[0]
    m = _RX_NOME.search(nome)
    if not m:
        return None
    tipo = _TIPO_MAP.get(m.group("tipo").lower(), "Provas")
    return Item(
        ano=m.group("ano"),
        cargo=cargo_legivel(m.group("resto")),
        tipo=tipo,
        url=url,
        banca=m.group("banca").upper(),
        fonte="espelho",  # qconcursos/estudegratis hospedam o caderno oficial
    )


def _ler_urls_curadas(caminho: Path | None = None) -> list[str]:
    caminho = caminho or PROVAS_URLS_PATH
    if not caminho.exists():
        return []
    urls = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        u = linha.strip()
        if u and not u.startswith("#"):
            urls.append(u)
    return urls


def montar_catalogo(urls: list[str] | None = None) -> list[Item]:
    """Junta o catálogo oficial + itens derivados das URLs curadas + pendentes."""
    itens: list[Item] = list(CATALOGO_OFICIAL)
    for url in (urls if urls is not None else _ler_urls_curadas()):
        it = parse_item_de_url(url)
        if it:
            itens.append(it)
    itens.extend(PENDENTES_OFICIAIS)
    return itens


# ── Organização (download + roteamento por cargo) ────────────────────────────
def _baixar(url: str, destino: Path) -> bool:
    """Baixa um PDF preservando o conteúdo. Reaproveita o downloader existente."""
    try:
        from extrair_provas_pdf import _baixar_pdf
        return _baixar_pdf(url, destino)
    except Exception:
        import requests
        try:
            r = requests.get(url, timeout=30, verify=False,
                             headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            if r.content[:4] != b"%PDF" and "pdf" not in r.headers.get("Content-Type", ""):
                return False
            destino.write_bytes(r.content)
            return True
        except Exception:
            return False


def organizar(itens: list[Item], raiz: Path | None = None, baixar: bool = True,
              baixar_fn=None) -> list[Item]:
    """Roteia cada item para Petrobras_[Ano]/[Cargo]/[Tipo]/ e registra a fonte.

    ``baixar_fn`` permite injetar um downloader (testes). Itens já marcados como
    'indisponível' não são baixados, mas entram no índice.
    """
    raiz = raiz or RAIZ_SAIDA
    baixar_fn = baixar_fn or _baixar
    for it in itens:
        if it.status == "indisponível":
            continue
        nome = nome_arquivo_de_url(it.url)
        if not nome.lower().endswith(".pdf"):
            nome = f"{it.tipo.lower()}_{it.cargo.replace(' ', '_')}.pdf"
        it.arquivo = nome
        destino_dir = raiz / f"Petrobras_{it.ano}" / it.cargo / it.tipo
        destino = destino_dir / nome
        if not baixar:
            it.status = "concluído" if destino.exists() else "pendente"
        elif destino.exists() and destino.stat().st_size > 0:
            it.status = "concluído"
        else:
            destino_dir.mkdir(parents=True, exist_ok=True)
            it.status = "concluído" if baixar_fn(it.url, destino) else "indisponível"
        # Sidecar de proveniência (não altera o PDF original)
        if it.status == "concluído":
            (destino_dir / f"{nome}.fonte.txt").write_text(
                f"url_origem: {it.url}\nbanca: {it.banca}\nfonte: {it.fonte}\n"
                f"edital: {it.edital_num}\nbaixado_em: {_hoje()}\n",
                encoding="utf-8",
            )
    return itens


def nome_arquivo_de_url(url: str) -> str:
    """Nome ORIGINAL do arquivo a partir da URL.

    Cobre URLs diretas (.../arquivo.pdf) e o storage.ashx do CESGRANRIO, onde o
    nome real está no parâmetro ``file=`` (ex.: '...file=pdf%2Fpetrobras0118%2F
    petrobras0118_edital.pdf' → 'petrobras0118_edital.pdf').
    """
    from urllib.parse import parse_qs, unquote, urlparse
    p = urlparse(url)
    qs = parse_qs(p.query)
    if "file" in qs and qs["file"]:
        return unquote(qs["file"][0]).replace("\\", "/").split("/")[-1]
    return unquote(p.path).split("/")[-1]


def _hoje() -> str:
    from datetime import date
    return date.today().isoformat()


# ── Detalhes dos editais ─────────────────────────────────────────────────────
def extrair_detalhes_edital(pdf: Path) -> dict:
    """Extrai detalhes do edital (cabeçalho + datas) e o texto completo.

    Usa o extrator de PDF do projeto (opendataloader-pdf, com fallback). Os
    campos do cabeçalho são robustos; o texto completo fica disponível para
    consulta. Nada inventado — se não achar, deixa em branco.
    """
    try:
        from importar_questoes import extrair_md
        txt = extrair_md(pdf)
    except Exception:
        txt = ""
    if not txt:
        return {"erro": "não foi possível extrair o texto do PDF", "texto": ""}

    cab = txt[:1500]
    m_titulo = re.search(r"EDITAL\s+N[ºo°]?\s*\d+[^\n]*?\d{4}", cab, re.IGNORECASE)
    m_data = re.search(r"\bDE\s+\d{1,2}\s+DE\s+[A-Za-zçÇ]+\s+DE\s+\d{4}", cab, re.IGNORECASE)
    niveis = re.search(r"N[ÍI]VE[IL]S?\s+(M[ÉE]DIO\s+E\s+SUPERIOR|SUPERIOR|M[ÉE]DIO)", cab, re.IGNORECASE)
    banca = "CESGRANRIO" if re.search(r"cesgranrio", txt, re.IGNORECASE) else (
            "CEBRASPE" if re.search(r"cebraspe|cespe", txt, re.IGNORECASE) else "")
    # Ano do edital (do título/data) para filtrar datas: o corpo cita datas de
    # leis antigas (ex.: 11/10/1972) que não são do cronograma.
    ano_m = re.search(r"\b(19|20)\d{2}\b", (m_data.group(0) if m_data else "") or
                      (m_titulo.group(0) if m_titulo else ""))
    ano_ed = int(ano_m.group(0)) if ano_m else 0
    datas = sorted({d for d in re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", txt)
                    if int(d[-4:]) >= ano_ed},
                   key=lambda d: (d[-4:], d[3:5].zfill(2), d[:2].zfill(2)))
    return {
        "titulo": (m_titulo.group(0).strip() if m_titulo else ""),
        "data_edital": (m_data.group(0).strip() if m_data else ""),
        "niveis": (niveis.group(0).strip() if niveis else ""),
        "banca": banca,
        "datas": datas,
        "chars": len(txt),
        "texto": txt,
    }


def salvar_detalhes_editais(itens: list[Item], raiz: Path | None = None) -> int:
    """Para cada EDITAL concluído, extrai detalhes e salva '<edital>.detalhes.md'
    (cabeçalho + datas + texto completo). Retorna quantos foram processados."""
    raiz = raiz or RAIZ_SAIDA
    n = 0
    consolidado = ["# Detalhes dos Editais — Petrobras", f"_Gerado em {_hoje()}_", ""]
    for it in sorted(itens, key=lambda x: x.ano):
        if it.tipo != "Editais" or it.status != "concluído" or not it.arquivo:
            continue
        pdf = raiz / f"Petrobras_{it.ano}" / it.cargo / "Editais" / it.arquivo
        if not pdf.exists():
            continue
        d = extrair_detalhes_edital(pdf)
        md = [
            f"# Edital Petrobras {it.ano}",
            f"- **Título:** {d.get('titulo') or it.edital_num}",
            f"- **Data:** {d.get('data_edital') or '—'}",
            f"- **Banca:** {d.get('banca') or it.banca}",
            f"- **Níveis:** {d.get('niveis') or '—'}",
            f"- **Datas citadas:** {', '.join(d.get('datas', [])[:20]) or '—'}",
            f"- **Fonte:** {it.url}",
            "", "---", "", "## Texto completo do edital", "",
            str(d.get("texto", "")),
        ]
        (pdf.parent / f"{it.arquivo}.detalhes.md").write_text("\n".join(md), encoding="utf-8")
        consolidado += [
            f"## {it.ano} — {d.get('titulo') or it.edital_num}",
            f"- Banca: {d.get('banca') or it.banca} · Níveis: {d.get('niveis') or '—'}",
            f"- Datas-chave: {', '.join(d.get('datas', [])[:12]) or '—'}",
            f"- Arquivo: `Petrobras_{it.ano}/{it.cargo}/Editais/{it.arquivo}`",
            f"- Fonte: {it.url}", "",
        ]
        n += 1
    if n:
        (raiz / "detalhes_editais.md").write_text("\n".join(consolidado), encoding="utf-8")
    return n


# ── Índice ───────────────────────────────────────────────────────────────────
_COLUNAS = ["ano", "cargo", "tipo", "banca", "edital_num", "data",
            "arquivo", "url_origem", "fonte", "status"]


def gerar_indice_csv(itens: list[Item], caminho: Path) -> Path:
    """Gera o índice resumo (cargo, edital, data, link da fonte, status)."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(_COLUNAS)
        for it in sorted(itens, key=lambda x: (x.ano, x.cargo, x.tipo)):
            w.writerow([it.ano, it.cargo, it.tipo, it.banca, it.edital_num,
                        it.data, it.arquivo, it.url, it.fonte, it.status])
    return caminho


def resumo(itens: list[Item]) -> dict[str, int]:
    r: dict[str, int] = {}
    for it in itens:
        r[it.status] = r.get(it.status, 0) + 1
    return r


def main() -> None:
    parser = argparse.ArgumentParser(description="Organiza provas/editais Petrobras por cargo")
    parser.add_argument("--raiz", type=str, default=None, help="Raiz de saída")
    parser.add_argument("--no-baixar", action="store_true", help="Não baixa; só organiza/indexa o que existe")
    args = parser.parse_args()

    raiz = Path(args.raiz) if args.raiz else RAIZ_SAIDA
    itens = montar_catalogo()
    print(f"Catálogo: {len(itens)} item(ns). Organizando em {raiz}/ ...")
    organizar(itens, raiz=raiz, baixar=not args.no_baixar)

    n_det = salvar_detalhes_editais(itens, raiz=raiz)
    if n_det:
        print(f"Detalhes de {n_det} edital(is) extraídos → detalhes_editais.md + *.detalhes.md")

    indice = gerar_indice_csv(itens, raiz / "indice.csv")
    r = resumo(itens)
    print(f"\nÍndice: {indice}")
    print("Status:", ", ".join(f"{k}={v}" for k, v in sorted(r.items())))
    # cargos distintos
    cargos = sorted({it.cargo for it in itens})
    print(f"Cargos ({len(cargos)}): " + "; ".join(cargos))


if __name__ == "__main__":
    main()
