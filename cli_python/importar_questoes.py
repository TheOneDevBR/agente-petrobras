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
    # Formato "comentado" de cadernos de curso: 'QUESTÃO 1 Gabarito: C',
    # 'Questão 12 - Gabarito: Letra B'. Específico (exige a palavra 'gabarito'),
    # então não confunde rótulos de alternativa.
    for num, letra in re.findall(
        r"(?i)quest[ãa]o\s*(\d{1,3})[\s.\-–:]{1,6}gabarito\s*:?\s*(?:letra\s*)?([A-Ea-e])\b",
        texto,
    ):
        n = int(num)
        if 1 <= n <= 250 and n not in gab:
            gab[n] = letra.upper()
    # Formato tabela CESGRANRIO: número, separador OBRIGATÓRIO (- – . : )), letra
    # isolada (não precedida de '(') — não confunde o rótulo '(A)' da prova.
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

    # Cadernos de curso têm enunciados longos: o cabeçalho 'QUESTÃO N' fica
    # além das 4 linhas de contexto. Se não achamos número, procuramos esse
    # cabeçalho mais acima, parando ao entrar no bloco de alternativas anterior
    # (assim não pegamos o número da questão de cima).
    if numero is None:
        k2 = idx_opcao_a - 1
        while k2 >= 0:
            s = linhas[k2].strip()
            if _OPCAO_RE.match(s):
                break
            mq = re.match(r"(?i)^#*\s*-?\s*quest[ãa]o\s*(\d{1,3})\b", s)
            if mq:
                numero = int(mq.group(1))
                break
            k2 -= 1

    enun = ctx[-1]  # linha mais próxima de (A)
    m = _NUM_RE.match(enun)
    if m and m.group(2).strip():
        enun = m.group(2).strip()
    elif m and not m.group(2).strip() and len(ctx) >= 2:
        enun = ctx[-2]  # número sozinho → enunciado é a linha anterior
    return numero, re.sub(r"\s+", " ", enun).strip()


# Texto de EDITAL/instrução de prova (não é questão de conteúdo) — descartar.
_EDITAL_RX = re.compile(
    r"(?i)(processo seletivo|cart[ãa]o[- ]resposta|folha de respostas|"
    r"ser[áa] eliminado|caderno de quest|do candidato|fiscal de sala|"
    r"tempo de prova|assinatura do candidato|preenchimento d|rascunho|"
    r"gabarito oficial preliminar|recurso contra|verifique se este caderno)"
)


def _eh_edital(enunciado: str) -> bool:
    """True se o enunciado é texto de edital/instrução (ruído, não conteúdo)."""
    return bool(_EDITAL_RX.search(enunciado or ""))


def montar_questoes(texto_prova: str, texto_gabarito: str = "",
                    disciplina: str = "", origem: str = "pdf") -> list[dict[str, Any]]:
    """Casa questões + gabarito e retorna dicts prontos (com 'correta' como índice).

    Só inclui questões com 5 alternativas E resposta conhecida no gabarito.
    Descarta texto de edital/instrução (não é questão de conteúdo).
    """
    gab = parsear_gabarito(texto_gabarito) if texto_gabarito else {}
    out: list[dict[str, Any]] = []
    for q in parsear_questoes(texto_prova):
        if _eh_edital(q["enunciado"]):
            continue  # regra de edital, não questão de conteúdo
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


# ─── Classificação de disciplina por conteúdo ──────────────────────────────────

_SINAIS_DISC = [
    ("Legislação e Governança", re.compile(
        r"(?i)\b(art\.?\s*\d+|cf\s*/?\s*88|constitui[çc]|lei\s+(n?[ºo]?\s*)?\d|"
        r"princ[íi]pio|administra[çc][ãa]o p[úu]blica|licita[çc]|estatuto|lgpd|"
        r"jur[íi]dic|jurisprud|tribunal|decreto|improbidade|estatais|"
        r"servidor p[úu]blico|13\.303|8\.666|14\.133|14\.13[03]|12\.846|"
        r"governan[çc]a|complian[cs]e|anticorrup|[ée]tica|c[óo]digo de conduta|"
        r"integridade|conflito de interesse|sanç[ãa]o administrativa|"
        r"contrata[çc][ãa]o p[úu]blica|controle interno|ag[êe]ncia reguladora)\b")),
    ("Língua Portuguesa", re.compile(
        r"(?i)\b(crase|reg[êe]ncia|concord[âa]ncia (verbal|nominal)|v[íi]rgula|"
        r"ora[çc][ãa]o|sujeito|predicado|coes[ãa]o|coer[êe]ncia|"
        r"figura de linguagem|acentua[çc]|ortografi|morfossint|sint[áa]tic|"
        r"pronome|no texto|na frase|do texto|adv[ée]rbio|conjun[çc][ãa]o|"
        r"substantiv|crase|coloca[çc][ãa]o pronominal)\b")),
    ("Raciocínio Lógico / Matemática", re.compile(
        r"(?i)\b(probabilidade|porcentagem|percentual|equa[çc][ãa]o|fun[çc][ãa]o|"
        r"proposi[çc][ãa]o|l[óo]gic|conjunto|m[ée]dia aritm|juros|raz[ãa]o e propor|"
        r"propor[çc][ãa]o|[âa]ngulo|tri[âa]ngulo|negaç[ãa]o|silogismo|"
        r"verdadeir[oa]s? (e|ou)|tautologia)\b")),
]


def classificar_disciplina(texto: str) -> str | None:
    """Detecta a disciplina pelo CONTEÚDO (heurística). None se incerto."""
    melhor, melhor_n = None, 0
    for disc, rgx in _SINAIS_DISC:
        n = len(rgx.findall(texto or ""))
        if n > melhor_n:
            melhor, melhor_n = disc, n
    return melhor if melhor_n >= 1 else None


# Canonicalização de rótulos de disciplina (corrige variantes sem acento e
# unifica sinônimos). Cargos não-mapeados ficam como estão (ex.: 'Eng Petroleo
# Jr' são conhecimentos específicos daquela prova — não viram outra disciplina).
_ALIAS_DISC = {
    "lingua portuguesa": "Língua Portuguesa",
    "portugues": "Língua Portuguesa",
    "matematica": "Raciocínio Lógico / Matemática",
    "raciocinio logico": "Raciocínio Lógico / Matemática",
    "raciocinio logico / matematica": "Raciocínio Lógico / Matemática",
    "legislacao": "Legislação e Governança",
    "legislacao e governanca": "Legislação e Governança",
    # Sub-ramos do direito que compõem o bloco de legislação/governança das
    # estatais (caem em provas Petrobras como parte do conhecimento jurídico
    # comum, não apenas para Advogado) — unificados na básica de Legislação.
    "direito administrativo": "Legislação e Governança",
    "direito constitucional": "Legislação e Governança",
    "conhecimentos especificos": "Conhecimentos Específicos",
}


def _sem_acento(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower().strip()


def normalizar_disciplina(disc: str) -> str:
    """Canonicaliza o rótulo de disciplina (acentos/sinônimos)."""
    return _ALIAS_DISC.get(_sem_acento(disc or ""), disc)


# ─── Cargo (para dividir simulados por cargo do concurso) ──────────────────────

# Disciplinas BÁSICAS são compartilhadas por TODOS os cargos (caem em qualquer
# prova CESGRANRIO/CEBRASPE da Petrobras). O resto é conhecimento específico.
DISCIPLINAS_BASICAS = {
    "Língua Portuguesa", "Raciocínio Lógico / Matemática", "Legislação e Governança",
}

# Mapeia (parte do) origem/disciplina → cargo legível. Substring, ordem importa.
_CARGO_MAP = [
    ("engenheiro-de-petroleo", "Engenheiro de Petróleo Júnior"),
    ("engenharia de petroleo", "Engenheiro de Petróleo Júnior"),
    ("eng petroleo", "Engenheiro de Petróleo Júnior"),
    ("engenharia naval", "Engenharia Naval"),
    ("eng naval", "Engenharia Naval"),
    ("engenheiro-de-equipamentos", "Engenheiro de Equipamentos Júnior"),
    ("transpetro", "Transpetro Nível Superior"),
    ("advogado", "Advogado Júnior"),
    ("tecnico-de-log", "Técnico de Logística Júnior"),
    ("tec logistica", "Técnico de Logística Júnior"),
    ("administrador", "Administrador Júnior"),
    ("quimico", "Químico de Petróleo Júnior"),
    ("geologo", "Geólogo Júnior"),
    ("contador", "Contador Júnior"),
    ("cebraspe-2023-nm", "Petrobras Nível Médio (2023)"),
    ("operação", "Técnico de Operação"),
    ("operacao", "Técnico de Operação"),
]


def cargo_de_origem(origem: str, disciplina: str = "") -> str:
    """Deriva o cargo a partir do `origem` (prova) e/ou `disciplina`.

    Retorna "" quando não há cargo identificável (ex.: material só de básicos).
    """
    alvo = _sem_acento(f"{origem} {disciplina}")
    for chave, cargo in _CARGO_MAP:
        if _sem_acento(chave) in alvo:
            return cargo
    return ""


def backfill_cargo(caminho: Path | None = None) -> dict[str, Any]:
    """Preenche o campo `cargo` em cada questão do store (a partir de origem/
    disciplina). Específicos sem cargo viram 'Geral'. Retorna contagem por cargo."""
    qs = carregar_extraidas(caminho)
    mudou = 0
    for q in qs:
        if q.get("disciplina") in DISCIPLINAS_BASICAS:
            cargo = ""  # básico é COMPARTILHADO por todos os cargos
        else:
            cargo = cargo_de_origem(q.get("origem", ""), q.get("disciplina", "")) or "Geral"
        if q.get("cargo") != cargo:
            q["cargo"] = cargo
            mudou += 1
    if mudou:
        salvar_extraidas(qs, caminho)
    cont: dict[str, int] = {}
    for q in qs:
        cont[q.get("cargo") or "(básico/compartilhado)"] = cont.get(q.get("cargo") or "(básico/compartilhado)", 0) + 1
    return {"atualizadas": mudou, "por_cargo": cont}


def reclassificar_store(caminho: Path | None = None) -> dict[str, Any]:
    """Re-etiqueta a disciplina das questões do store pelo conteúdo (corrige
    rótulos herdados do arquivo de origem). Só muda quando há sinal claro."""
    qs = carregar_extraidas(caminho)
    mudou = 0
    for q in qs:
        # 1) reclassifica por conteúdo (enunciado + ALTERNATIVAS — muitas questões
        #    de legislação citam a lei nas opções, não no enunciado);
        # 2) senão, ao menos canonicaliza o rótulo atual (acentos/sinônimos).
        texto = (q.get("pergunta", "") + " " + " ".join(q.get("opcoes", [])))
        nova = classificar_disciplina(texto) or normalizar_disciplina(q.get("disciplina", ""))
        if nova and nova != q.get("disciplina"):
            q["disciplina"] = nova
            q.setdefault("tags", [])
            if "reclassificada" not in q["tags"]:
                q["tags"].append("reclassificada")
            mudou += 1
    if mudou:
        salvar_extraidas(qs, caminho)
    contagem: dict[str, int] = {}
    for q in qs:
        contagem[q.get("disciplina", "?")] = contagem.get(q.get("disciplina", "?"), 0) + 1
    return {"reclassificadas": mudou, "total": len(qs), "por_disciplina": contagem}


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
        origem = Path(pdf).stem[:40]
        # Roda OS DOIS parsers e mescla: CESGRANRIO (5 alternativas) e CEBRASPE
        # (Certo/Errado). Cada um só rende no seu formato, então mesclar é seguro
        # e evita perder a prova C/E quando o parser de 5-alt acha falsos positivos.
        novas = montar_questoes(texto, gab, disciplina=disciplina, origem=origem)
        novas += montar_questoes_ce(texto, gabarito_texto, disciplina=disciplina, origem=origem)
        total += importar(novas)
    return total


# ─── Pareamento automático prova↔gabarito (árvore organizada) ──────────────────

def _stem_base(nome: str) -> str:
    """Reduz o nome de arquivo ao 'tronco' do concurso (sem -prova/-gabarito/ano).

    Serve para casar a prova com o gabarito CERTO quando há vários numa pasta.
    Ex.: 'cesgranrio-2018-petrobras-advogado-junior-prova' →
         'cesgranrio 2018 petrobras advogado junior'.
    """
    s = _sem_acento(nome)
    s = re.sub(r"\.pdf$", "", s)
    s = re.sub(r"\b(prova|gabarito|caderno|respostas?|oficial|preliminar|definitivo)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _melhor_gabarito(prova: Path, gabaritos: list[Path]) -> Path | None:
    """Escolhe o gabarito que mais combina com a prova (por tronco do nome).

    Com um único gabarito na pasta, devolve-o. Com vários, casa pela maior
    sobreposição de palavras do tronco (mesma ênfase/cargo).
    """
    if not gabaritos:
        return None
    if len(gabaritos) == 1:
        return gabaritos[0]
    alvo = set(_stem_base(prova.name).split())
    melhor, score = gabaritos[0], -1
    for g in gabaritos:
        s = len(alvo & set(_stem_base(g.name).split()))
        if s > score:
            melhor, score = g, s
    return melhor


def encontrar_pares(base: Path | None = None) -> list[dict[str, Any]]:
    """Varre dados/provas_editais e pareia (prova↔gabarito) por pasta de cargo.

    Estrutura esperada (gerada pelo organizar_provas_editais):
        Petrobras_<ANO>/<Cargo>/Provas/*.pdf  +  .../Gabaritos/*.pdf

    Retorna uma lista de {prova, gabarito, ano, cargo} (gabarito pode ser None).
    """
    base = base or (_DIR / "dados" / "provas_editais")
    pares: list[dict[str, Any]] = []
    if not base.exists():
        return pares
    for ano_dir in sorted(base.glob("Petrobras_*")):
        if not ano_dir.is_dir():
            continue
        ano = ano_dir.name.replace("Petrobras_", "")
        for cargo_dir in sorted(p for p in ano_dir.iterdir() if p.is_dir()):
            d_prova, d_gab = cargo_dir / "Provas", cargo_dir / "Gabaritos"
            provas = sorted(d_prova.glob("*.pdf")) if d_prova.exists() else []
            gabaritos = sorted(d_gab.glob("*.pdf")) if d_gab.exists() else []
            for prova in provas:
                pares.append({
                    "prova": prova,
                    "gabarito": _melhor_gabarito(prova, gabaritos),
                    "ano": ano,
                    "cargo": cargo_dir.name,
                })
    return pares


def de_provas_editais(base: Path | None = None,
                      reclassificar: bool = True) -> dict[str, Any]:
    """Importa TODAS as provas da árvore organizada, pareando prova+gabarito
    automaticamente pela pasta do cargo (sem precisar passar --prova/--gabarito).

    Após importar, reetiqueta disciplina (conteúdo) e preenche o cargo de cada
    questão — deixando o store pronto para os simulados por cargo.
    """
    pares = encontrar_pares(base)
    total = 0
    relatorio: list[dict[str, Any]] = []
    for par in pares:
        gab = par["gabarito"]
        if gab is None:
            relatorio.append({"cargo": par["cargo"], "ano": par["ano"],
                              "prova": par["prova"].name, "importadas": 0,
                              "obs": "sem gabarito na pasta — pulado"})
            continue
        n = de_pdfs([par["prova"]], gabarito_pdf=gab)
        total += n
        relatorio.append({"cargo": par["cargo"], "ano": par["ano"],
                          "prova": par["prova"].name,
                          "gabarito": gab.name, "importadas": n})
    resumo: dict[str, Any] = {"total_importadas": total, "pares": len(pares),
                              "relatorio": relatorio}
    if total and reclassificar:
        resumo["reclassificacao"] = reclassificar_store()
        resumo["cargos"] = backfill_cargo()
    return resumo


# ─── CEBRASPE: itens Certo/Errado ──────────────────────────────────────────────

_ITEM_CE_RE = re.compile(r"^-?\s*(\d{1,3})\s+(\S.*)$")


def parsear_gabarito_ce(texto: str) -> dict[int, str]:
    """Gabarito CEBRASPE: grade com a linha de números e a de respostas (C/E/X)
    no mesmo bloco. Casa posicionalmente número↔letra; ignora '0' (vazio) e
    'X' (anulada)."""
    gab: dict[int, str] = {}
    for linha in texto.splitlines():
        toks = linha.split()
        nums = [int(t) for t in toks if t.isdigit() and t != "0"]
        ans = [t.upper() for t in toks if t.upper() in ("C", "E", "X")]
        if nums and len(nums) == len(ans):
            for n, a in zip(nums, ans):
                if a in ("C", "E") and 1 <= n <= 250:
                    gab.setdefault(n, a)
    return gab


def parsear_itens_ce(texto: str) -> list[dict[str, Any]]:
    """Extrai itens Certo/Errado ('- 16 <afirmação>') do texto da prova,
    acumulando linhas de continuação até o próximo item."""
    itens: list[dict[str, Any]] = []
    atual: dict[str, Any] | None = None
    for raw in texto.splitlines():
        linha = raw.strip()
        if not linha:
            continue
        m = _ITEM_CE_RE.match(linha)
        if m and len(m.group(2)) >= 12:
            if atual:
                itens.append(atual)
            atual = {"numero": int(m.group(1)), "enunciado": m.group(2).strip()}
        elif atual:
            atual["enunciado"] += " " + linha
    if atual:
        itens.append(atual)
    return [it for it in itens if len(it["enunciado"]) >= 20]


def montar_questoes_ce(texto_prova: str, texto_gabarito: str = "",
                       disciplina: str = "", origem: str = "pdf") -> list[dict[str, Any]]:
    """Casa itens Certo/Errado + gabarito CEBRASPE. Só inclui itens com resposta
    C ou E conhecida (descarta anuladas/sem gabarito)."""
    gab = parsear_gabarito_ce(texto_gabarito) if texto_gabarito else {}
    if not gab:
        return []
    out: list[dict[str, Any]] = []
    for it in parsear_itens_ce(texto_prova):
        if _eh_edital(it["enunciado"]):
            continue  # regra de edital, não item de conteúdo
        letra = gab.get(it["numero"])
        if letra not in ("C", "E"):
            continue
        out.append({
            "pergunta": "(Certo/Errado) " + it["enunciado"],
            "opcoes": ["Certo", "Errado"],
            "correta": 0 if letra == "C" else 1,
            "explicacao": f"Gabarito oficial: {'Certo' if letra == 'C' else 'Errado'}.",
            "disciplina": disciplina or "Geral",
            "tags": ["extraida", "certo_errado", origem],
            "origem": origem,
            "hash": _hash(it["enunciado"]),
        })
    return out


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
    "encontrar_pares", "de_provas_editais", "reclassificar_store", "backfill_cargo",
]
