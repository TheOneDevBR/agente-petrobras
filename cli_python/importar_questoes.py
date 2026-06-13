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
    """Extrai {numero_questao: letra} de um texto de gabarito.

    Aceita formatos como '1-A', '1 - A', '1) A', '1: A', '1 A' (em tabela).
    """
    gab: dict[int, str] = {}
    for num, letra in re.findall(r"\b(\d{1,3})\s*[-–:.\)]?\s*([A-Ea-e])\b", texto):
        n = int(num)
        # primeira ocorrência vence; ignora números absurdos
        if 1 <= n <= 250 and n not in gab:
            gab[n] = letra.upper()
    return gab


def parsear_questoes(texto: str) -> list[dict[str, Any]]:
    """Extrai questões (numero, enunciado, opcoes) de um texto de prova.

    Reconhece blocos iniciados por 'QUESTÃO N' ou 'N.'/'N)' seguidos de 5
    alternativas rotuladas (A)..(E) / A) / a).
    """
    # normaliza marcadores de questão para um separador único
    marc = re.sub(r"(?im)^\s*quest[ãa]o\s+(\d{1,3})\b[ .:)-]*", r"\n@@Q\1@@ ", texto)
    marc = re.sub(r"(?m)^\s*(\d{1,3})[.\)]\s+", r"\n@@Q\1@@ ", marc)
    partes = re.split(r"@@Q(\d{1,3})@@", marc)

    questoes: list[dict[str, Any]] = []
    # partes = [pré, num1, corpo1, num2, corpo2, ...]
    for i in range(1, len(partes) - 1, 2):
        try:
            numero = int(partes[i])
        except ValueError:
            continue
        corpo = partes[i + 1]
        opcoes = _extrair_opcoes(corpo)
        if len(opcoes) != 5:
            continue
        # enunciado = tudo antes da primeira alternativa
        corte = re.search(r"\(?[A-Ea-e][\).]\s", corpo)
        enunciado = corpo[: corte.start()].strip() if corte else corpo.strip()
        enunciado = re.sub(r"\s+", " ", enunciado)
        if len(enunciado) < 12:
            continue
        questoes.append({"numero": numero, "enunciado": enunciado, "opcoes": opcoes})
    return questoes


def _extrair_opcoes(corpo: str) -> list[str]:
    """Extrai as 5 alternativas A–E de um corpo de questão."""
    # captura "(A) texto" / "A) texto" / "a. texto" até a próxima alternativa
    padrao = re.compile(
        r"\(?([A-Ea-e])[\).]\s*(.+?)(?=\s*\(?[A-Ea-e][\).]\s|\Z)", re.DOTALL)
    achadas: dict[str, str] = {}
    for letra, txt in padrao.findall(corpo):
        L = letra.upper()
        if L not in achadas:
            achadas[L] = re.sub(r"\s+", " ", txt).strip()
    return [achadas[L] for L in _LETRAS if L in achadas]


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


def de_pdfs(pdfs: list[Path] | None = None, disciplina: str = "",
            gabarito_texto: str = "") -> int:
    """Extrai texto dos PDFs (provas), parseia e importa. Retorna nº adicionadas.

    Se a prova e o gabarito estiverem no mesmo PDF, o gabarito é detectado no
    próprio texto; senão, passe gabarito_texto.
    """
    from pdf_utils import extrair_texto_pdf
    if pdfs is None:
        base = _DIR / "dados" / "provas"
        pdfs = sorted(base.glob("*.pdf")) if base.exists() else []

    total = 0
    for pdf in pdfs:
        try:
            texto = extrair_texto_pdf(pdf)
        except Exception:
            continue
        if not texto:
            continue
        gab = gabarito_texto or texto  # tenta achar gabarito no próprio texto
        novas = montar_questoes(texto, gab, disciplina=disciplina, origem=Path(pdf).stem[:40])
        total += importar(novas)
    return total


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
