"""Importador de Questões — extrai questões REAIS de provas/apostilas em PDF.

Parseia questões de múltipla escolha (estilo CESGRANRIO) e o GABARITO, casa cada
questão com sua resposta correta e só mantém as confiáveis (5 alternativas +
gabarito conhecido). Deduplica contra o que já existe e guarda em
dados/questoes_extraidas.json — o treino mescla esse store ao BANCO_QUESTOES.

Princípio (mesmo do coletor): nada inventado. Se não há gabarito para a questão,
ela é descartada, não "chutada".

Uso:
    from importar_questoes import montar_questoes, importar, de_pdfs
    novas = montar_questoes(texto_prova, texto_gabarito, disciplina="Legislação")
    n = importar(novas)
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent
_STORE = _DIR / "dados" / "questoes_extraidas.json"

_LETRAS = "ABCDE"


def _hash(enunciado: str) -> str:
    norm = re.sub(r"\s+", " ", enunciado.strip().lower())
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


# ─── Parsing ─────────────────────────────────────────────────────────────────

def parsear_gabarito(texto: str) -> dict[int, str]:
    """Extrai {numero_questao: letra} de um texto de GABARITO.

    Aceita '1-A', '1 - A', '1) A', '1: A'. EXIGE um separador real entre número
    e letra — assim NÃO confunde o rótulo de alternativa '(A)' de uma prova com
    a resposta (evita gabarito falso a partir do texto da prova).
    """
    gab: dict[int, str] = {}
    # número, separador OBRIGATÓRIO (- – . : )), letra isolada (não precedida de '(')
    for num, letra in re.findall(r"(?<![\w(])(\d{1,3})\s*[-–.:\)]\s*(?<!\()([A-Ea-e])(?![\w)])", texto):
        n = int(num)
        if 1 <= n <= 250 and n not in gab:
            gab[n] = letra.upper()
    return gab


_OPCAO_RE = re.compile(r"^\s*-?\s*\(?([A-Ea-e])[\).]\s*(.+\S)")
_NUM_RE = re.compile(r"^\s*-?\s*(?:quest[ãa]o\s*)?(\d{1,3})\b[\s.):-]*(.*)", re.IGNORECASE)


def parsear_questoes(texto: str) -> list[dict[str, Any]]:
    """Extrai questões (numero, enunciado, opcoes) de texto de prova.

    Estratégia robusta a layout (funciona bem com a saída estruturada do
    opendataloader-pdf): localiza grupos de 5 alternativas A–E e usa a linha
    de texto anterior como enunciado (extraindo o número da questão).
    """
    linhas = texto.splitlines()
    questoes: list[dict[str, Any]] = []
    i = 0
    while i < len(linhas):
        m = _OPCAO_RE.match(linhas[i])
        if not (m and m.group(1).upper() == "A"):
            i += 1
            continue
        # coleta alternativas consecutivas A..E (tolerando linhas em branco)
        opcoes: dict[str, str] = {}
        j = i
        while j < len(linhas):
            mo = _OPCAO_RE.match(linhas[j])
            if mo:
                opcoes.setdefault(mo.group(1).upper(), re.sub(r"\s+", " ", mo.group(2)).strip())
                j += 1
            elif not linhas[j].strip():
                j += 1
            else:
                break
        if len(opcoes) >= 5:
            numero, enunciado = _enunciado_anterior(linhas, i)
            if enunciado and len(enunciado) >= 12:
                questoes.append({
                    "numero": numero, "enunciado": enunciado,
                    "opcoes": [opcoes[L] for L in _LETRAS],
                })
        i = max(j, i + 1)
    return questoes


def _enunciado_anterior(linhas: list[str], idx_opcao_a: int) -> tuple[int | None, str]:
    """Pega o enunciado e o número da questão antes da alternativa (A).

    Cobre número na própria linha do enunciado (opendataloader: '6 A concordância…')
    e número numa linha à parte acima ('QUESTÃO 1' / '1' seguido do enunciado).
    """
    # coleta até 4 linhas não-vazias antes de (A), parando se entrar noutro bloco
    ctx: list[str] = []
    k = idx_opcao_a - 1
    while k >= 0 and len(ctx) < 4:
        s = linhas[k].strip()
        if s:
            if _OPCAO_RE.match(s):
                break
            ctx.append(s)
        k -= 1
    if not ctx:
        return None, ""
    ctx.reverse()  # ordem de leitura

    numero: int | None = None
    for s in ctx:
        m = _NUM_RE.match(s)
        if m:
            numero = int(m.group(1))
            break

    enun = ctx[-1]  # linha mais próxima de (A)
    m = _NUM_RE.match(enun)
    if m and m.group(2).strip():
        enun = m.group(2).strip()
    elif m and not m.group(2).strip() and len(ctx) >= 2:
        enun = ctx[-2]  # número sozinho → enunciado é a linha anterior
    return numero, re.sub(r"\s+", " ", enun).strip()


def montar_questoes(texto_prova: str, texto_gabarito: str = "",
                    disciplina: str = "", origem: str = "pdf") -> list[dict[str, Any]]:
    """Casa questões + gabarito e retorna dicts prontos (com 'correta' como índice).

    Só inclui questões com 5 alternativas E resposta conhecida no gabarito.
    """
    gab = parsear_gabarito(texto_gabarito) if texto_gabarito else {}
    out: list[dict[str, Any]] = []
    for q in parsear_questoes(texto_prova):
        letra = gab.get(q["numero"])
        if not letra or letra not in _LETRAS:
            continue  # sem gabarito confiável → descarta (não inventa)
        out.append({
            "pergunta": q["enunciado"],
            "opcoes": q["opcoes"],
            "correta": _LETRAS.index(letra),
            "explicacao": f"Gabarito oficial: alternativa {letra}.",
            "disciplina": disciplina or "Geral",
            "tags": ["extraida", origem],
            "origem": origem,
            "hash": _hash(q["enunciado"]),
        })
    return out


# ─── Store ───────────────────────────────────────────────────────────────────

def carregar_extraidas(caminho: Path | None = None) -> list[dict]:
    caminho = caminho or _STORE
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def salvar_extraidas(questoes: list[dict], caminho: Path | None = None) -> None:
    caminho = caminho or _STORE
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(questoes, ensure_ascii=False, indent=2), encoding="utf-8")


def importar(novas: list[dict], caminho: Path | None = None) -> int:
    """Adiciona questões novas ao store, deduplicando por hash do enunciado.

    Retorna quantas foram efetivamente adicionadas.
    """
    existentes = carregar_extraidas(caminho)
    vistos = {q.get("hash") or _hash(q["pergunta"]) for q in existentes}
    adicionadas = 0
    for q in novas:
        h = q.get("hash") or _hash(q["pergunta"])
        if h in vistos:
            continue
        q.setdefault("hash", h)
        existentes.append(q)
        vistos.add(h)
        adicionadas += 1
    if adicionadas:
        salvar_extraidas(existentes, caminho)
    return adicionadas


def extrair_md(pdf: Path) -> str:
    """Extrai texto ESTRUTURADO do PDF via opendataloader-pdf (resolve mojibake e
    layout 2-colunas). Fallback para pdf_utils se a lib/Java não estiver presente.
    """
    try:
        import tempfile
        import opendataloader_pdf
        with tempfile.TemporaryDirectory() as td:
            opendataloader_pdf.convert(input_path=[str(pdf)], output_dir=td, format="markdown")
            mds = list(Path(td).rglob("*.md"))
            if mds:
                return mds[0].read_text(encoding="utf-8")
    except Exception:
        pass
    try:
        from pdf_utils import extrair_texto_pdf
        return extrair_texto_pdf(pdf) or ""
    except Exception:
        return ""


def de_pdfs(pdfs: list[Path] | None = None, disciplina: str = "",
            gabarito_pdf: Path | None = None, gabarito_texto: str = "") -> int:
    """Extrai (opendataloader), parseia e importa questões. Retorna nº adicionadas.

    O gabarito pode vir: (a) em PDF separado (gabarito_pdf), (b) como texto
    (gabarito_texto), ou (c) inline no próprio PDF da prova.
    """
    if pdfs is None:
        base = _DIR / "dados" / "provas"
        pdfs = sorted(base.glob("*.pdf")) if base.exists() else []

    if gabarito_pdf is not None and not gabarito_texto:
        gabarito_texto = extrair_md(Path(gabarito_pdf))

    total = 0
    for pdf in pdfs:
        texto = extrair_md(Path(pdf))
        if not texto:
            continue
        # gabarito SÓ de fonte explícita (separado) OU de seção marcada na prova;
        # nunca o corpo inteiro da prova (rótulos (A) viram resposta falsa).
        gab = gabarito_texto or _secao_gabarito(texto)
        novas = montar_questoes(texto, gab, disciplina=disciplina, origem=Path(pdf).stem[:40])
        total += importar(novas)
    return total


def _secao_gabarito(texto: str) -> str:
    """Isola a seção de gabarito da prova (texto após 'GABARITO'/'RESPOSTAS'),
    se existir. Sem isso, retorna '' (não arrisca gabarito falso)."""
    m = re.search(r"(?is)\b(?:gabarito|gabarito\s+oficial|respostas)\b", texto)
    if not m:
        return ""
    trecho = texto[m.end():]
    # só vale se parecer uma lista densa de respostas (>= 5 pares num-letra)
    if len(parsear_gabarito(trecho)) >= 5:
        return trecho
    return ""


def estatisticas(caminho: Path | None = None) -> dict[str, Any]:
    qs = carregar_extraidas(caminho)
    por_disc: dict[str, int] = {}
    for q in qs:
        por_disc[q.get("disciplina", "Geral")] = por_disc.get(q.get("disciplina", "Geral"), 0) + 1
    return {"total": len(qs), "por_disciplina": por_disc}


__all__ = [
    "parsear_gabarito", "parsear_questoes", "montar_questoes",
    "carregar_extraidas", "salvar_extraidas", "importar", "de_pdfs", "estatisticas",
]
