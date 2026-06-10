#!/usr/bin/env python3
"""Coletor de inteligência do AgentePetrobras (local LLM).

Busca periódica em fontes PÚBLICAS (banca CESGRANRIO, carreiras Petrobras,
blogs de cursinhos, portais de concurso) usando LLM local + web_search/fetch
locais. Cada "beat" de fontes.json vira UMA nota Markdown no vault do Obsidian.

Uso:
    python coletor.py                 # roda todos os beats
    python coletor.py --beat editais  # só um beat
    python coletor.py --listar        # lista os beats configurados

Variáveis de ambiente:
    AGENTE_LLM_BASE_URL  (default: http://localhost:11434)
    AGENTE_LOCAL_MODEL   (default: qwen2.5:7b)
    AGENTE_VAULT         caminho do vault Obsidian (default: <projeto>/Obsidian_Vault)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

AQUI = Path(__file__).resolve().parent
PROJETO = AQUI.parents[1]
CLI_PYTHON = AQUI.parent
sys.path.insert(0, str(CLI_PYTHON))

try:
    from local_web import web_search, web_fetch
except ImportError:
    web_search = web_fetch = None  # opcional

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv()
except ImportError:
    pass

try:
    from local_llm import LocalLLM, LocalLLMError
except ImportError:
    print("Falta local_llm.py. Copie para cli_python/ e instale as dependências.")
    sys.exit(1)

FONTES_PATH = AQUI / "fontes.json"

VAULT = Path(os.environ.get("AGENTE_VAULT", PROJETO / "Obsidian_Vault"))
PASTA_PETROBRAS = VAULT / "Petrobras"
PASTA_INTEL = PASTA_PETROBRAS / "Inteligencia"
RESUMO_MOC = PASTA_PETROBRAS / "_RESUMO_INTEL.md"

SYSTEM = """\
Responda SEMPRE em português do Brasil.
Você é o braço de inteligência do AgentePetrobras — um analista que monitora
fontes públicas para preparar candidatos ao concurso da Petrobras (banca
CESGRANRIO). Sua função: ANALISAR e SINTETIZAR informações coletadas da web.

REGRAS:
- Use APENAS os dados fornecidos abaixo nos [RESULTADOS_DA_BUSCA].
- Distinga fato confirmado por fonte oficial de boato/especulação — rotule.
- Honestidade clínica: se não houver novidade ou edital aberto, diga isso
  claramente; não invente.
- Hoje é {hoje}. Priorize o que é recente e acionável para o candidato.

FORMATO DA SAÍDA — produza UMA nota Obsidian em Markdown igual ao exemplo
abaixo. Copie a estrutura EXATA. NÃO coloque cercas de código. NÃO escreva
texto antes ou depois.

EXEMPLO:
resumo_uma_linha: Inscrições abertas para o concurso Petrobras 2026, 200 vagas para Eng. de Petróleo

## Resumo executivo
- Edital publicado em 15/03/2026 com 200 vagas para Engenheiro de Petróleo Júnior
- Inscrições de 01/04 a 30/04/2026 pelo site da CESGRANRIO
- Salário inicial de R$ 11.000,00 + benefícios

## Detalhes
O concurso Petrobras 2026 foi autorizado pela Portaria 123/2026 [1]. As provas
serão aplicadas em maio pela banca CESGRANRIO [2]. O conteúdo programático
inclui Língua Portuguesa, Matemática, Engenharia de Petróleo e Legislação.

## O que muda para o candidato
- Intensificar estudos de Engenharia de Petróleo (maior peso no edital)
- Treinar redação CESGRANRIO (estilo banca confirmado)

## Disciplinas relacionadas
[[Língua Portuguesa]], [[Engenharia de Petróleo]], [[Lei 13.303]]

## Fontes
1. https://www.petrobras.com.br/carreiras
2. https://www.cesgranrio.org.br/concursos

SIGA EXATAMENTE este formato, incluindo a linha resumo_uma_linha: no topo."""

PROMPT_BEAT = """\
MISSÃO ({beat_id}): {titulo}
Cargo em foco: {cargo}

{instrucao}

[RESULTADOS_DA_BUSCA]
{resultados}

Com base APENAS nos resultados acima, produza a nota no formato definido.
Comece com a linha exata: resumo_uma_linha:"""


def _slug(texto: str) -> str:
    s = re.sub(r"[^\w\s-]", "", texto.lower(), flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "nota"


def _extrair_resumo(corpo: str) -> str:
    m = re.search(r"resumo_uma_linha:\s*(.+)", corpo)
    return m.group(1).strip() if m else "(sem resumo)"


def _fix_nota(corpo: str) -> str:
    """Corrige formatação comum de modelos pequenos."""
    if not corpo:
        return corpo
    # remove linhas tipo "---" ou "```" que cercam a nota
    corpo = re.sub(r"^```[\w]*\n", "", corpo, flags=re.MULTILINE)
    corpo = re.sub(r"\n```\s*$", "", corpo)
    corpo = re.sub(r"^---+", "", corpo)
    # se não tem resumo_uma_linha, tenta extrair da primeira linha significativa
    if not re.search(r"^resumo_uma_linha:", corpo, re.MULTILINE):
        linhas = [l.strip() for l in corpo.split("\n") if l.strip()]
        first = next((l for l in linhas if len(l) > 10), "")
        if first and "## " not in first:
            corpo = f"resumo_uma_linha: {first[:140]}\n\n" + corpo
    # headers com dois pontos extras: "## Resumo executivo:" -> "## Resumo executivo"
    corpo = re.sub(r"^(#{1,6}\s+.+?):(\s|$)", r"\1\2", corpo, flags=re.MULTILINE)
    # remove linhas de separação extras
    corpo = re.sub(r"\n{3,}", "\n\n", corpo)
    return corpo.strip()


def _buscar_para_beat(beat: dict, max_resultados: int = 3) -> str:
    """Gera queries a partir do beat, busca na web e retorna texto formatado."""
    dominios = beat.get("dominios_sugeridos", [])
    queries = [beat["titulo"]]
    queries += beat.get("tags", [])
    if dominios:
        queries.append(f"{beat['titulo']} {' '.join(dominios[:2])}")

    blocos = []
    visitados: set[str] = set()
    for q in queries[:3]:
        print(f"   ↳ buscando: {q}")
        try:
            resultados = web_search(q, max_results=max_resultados)
        except Exception as e:
            print(f"   [erro web_search: {e}]")
            continue
        for r in resultados:
            url = r.get("href") or r.get("link", "")
            if not url or url in visitados:
                continue
            visitados.add(url)
            titulo = r.get("title", "")
            snippet = r.get("snippet", r.get("body", ""))
            blocos.append(f"### {titulo}\nURL: {url}\n{snippet}\n")
            try:
                conteudo = web_fetch(url)
                if conteudo and len(conteudo) > 200:
                    blocos.append(f"**Conteúdo extraído:**\n{conteudo[:1500]}\n")
            except Exception as e:
                blocos.append(f"(erro ao acessar: {e})\n")

    if not blocos:
        return "Nenhum resultado encontrado na web para as queries realizadas."
    return "\n".join(blocos)


def coletar_beat(cliente, beat: dict, cargo: str) -> tuple[str, str] | None:
    """Executa um beat: busca web direta + síntese via LLM local. Retorna (corpo_markdown, resumo)."""
    print("   Buscando na web...")
    resultados = _buscar_para_beat(beat)

    prompt = PROMPT_BEAT.format(
        beat_id=beat["id"],
        titulo=beat["titulo"],
        cargo=cargo,
        instrucao=beat["instrucao"],
        resultados=resultados,
    )
    system = SYSTEM.format(hoje=date.today().isoformat())
    messages = [{"role": "user", "content": prompt}]

    try:
        corpo = cliente.chat(
            system=system,
            messages=messages,
            max_tokens=12000,
        )
    except LocalLLMError as e:
        print(f"   [erro no beat '{beat['id']}': {e}]")
        return None

    if not corpo:
        print(f"   [beat '{beat['id']}' não retornou texto]")
        return None
    corpo = _fix_nota(corpo)
    return corpo, _extrair_resumo(corpo)


def gravar_nota(beat: dict, corpo: str, resumo: str) -> Path:
    PASTA_INTEL.mkdir(parents=True, exist_ok=True)
    hoje = date.today().isoformat()
    nome = PASTA_INTEL / f"{hoje}_{_slug(beat['titulo'])}.md"
    tags = " ".join(f"#{t}" for t in (["petrobras", "inteligencia"] + beat.get("tags", [])))
    frontmatter = (
        "---\n"
        f"titulo: {beat['titulo']}\n"
        f"beat: {beat['id']}\n"
        f"data: {hoje}\n"
        f"coletado_em: {datetime.now().isoformat(timespec='seconds')}\n"
        f"resumo: \"{resumo.replace(chr(34), chr(39))}\"\n"
        "tipo: inteligencia\n"
        "---\n\n"
    )
    corpo_limpo = re.sub(r"^\s*resumo_uma_linha:.*\n+", "", corpo, count=1)
    nome.write_text(frontmatter + f"{tags}\n\n# {beat['titulo']}\n\n" + corpo_limpo + "\n", encoding="utf-8")
    return nome


def atualizar_moc(registros: list[dict]) -> None:
    """Reescreve o _RESUMO_INTEL.md (mapa de conteúdo) com os achados do dia no topo.
    Remove bloco anterior da mesma data para evitar duplicação."""
    hoje = date.today().isoformat()
    bloco_hoje = "## Coleta de " + hoje + "\n\n"
    for r in registros:
        bloco_hoje += f"- [[{r['arquivo'].stem}|{r['titulo']}]] — {r['resumo']}\n"
    bloco_hoje += "\n"

    anterior = ""
    if RESUMO_MOC.exists():
        anterior = RESUMO_MOC.read_text(encoding="utf-8")
        anterior = re.sub(r"^---.*?---\n\n", "", anterior, count=1, flags=re.DOTALL)
        anterior = re.sub(r"^# .*?\n\n", "", anterior, count=1, flags=re.DOTALL)
        anterior = re.sub(r"^_Mapa de conteúdo.*\n?", "", anterior, flags=re.MULTILINE)
        # remove bloco da mesma data para substituir
        anterior = re.sub(
            r"\n?## Coleta de " + re.escape(hoje) + r".*?(?=\n## Coleta de|\Z)",
            "", anterior, flags=re.DOTALL
        )
        anterior = anterior.strip()

    header = (
        "---\ntitulo: Resumo de Inteligência (MOC)\ntipo: indice\n"
        f"atualizado_em: {hoje}\n---\n\n"
        "# 📡 Resumo de Inteligência — AgentePetrobras\n\n"
        "_Mapa de conteúdo gerado pela coleta automática. As notas completas "
        "estão em [[Inteligencia]]._\n\n"
    )
    RESUMO_MOC.parent.mkdir(parents=True, exist_ok=True)
    RESUMO_MOC.write_text(header + bloco_hoje + anterior + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Coletor de inteligência AgentePetrobras")
    parser.add_argument("--beat", help="roda apenas o beat com este id")
    parser.add_argument("--listar", action="store_true", help="lista os beats e sai")
    args = parser.parse_args()

    fontes = json.loads(FONTES_PATH.read_text(encoding="utf-8"))
    beats = fontes["beats"]
    cargo = fontes.get("cargo_foco", "candidato Petrobras")

    if args.listar:
        print("Beats configurados em fontes.json:")
        for b in beats:
            print(f"  • {b['id']:20s} {b['titulo']}")
        return

    if args.beat:
        beats = [b for b in beats if b["id"] == args.beat]
        if not beats:
            print(f"Beat '{args.beat}' não encontrado. Use --listar.")
            sys.exit(1)

    cliente = LocalLLM()
    print(f"📡 Coleta iniciada — {date.today().isoformat()} — vault: {VAULT}")
    print(f"   {len(beats)} missão(ões) · LLM local: {cliente.model} @ {cliente.base_url}\n")

    registros = []
    for i, beat in enumerate(beats, 1):
        print(f"[{i}/{len(beats)}] {beat['titulo']} ...")
        res = coletar_beat(cliente, beat, cargo)
        if not res:
            continue
        corpo, resumo = res
        arquivo = gravar_nota(beat, corpo, resumo)
        registros.append({"titulo": beat["titulo"], "resumo": resumo, "arquivo": arquivo})
        print(f"   ✓ {arquivo.name} — {resumo[:80]}")

    if registros:
        atualizar_moc(registros)
        print(f"\n✓ {len(registros)} nota(s) gravada(s). MOC: {RESUMO_MOC}")
    else:
        print("\nNenhuma nota gerada nesta execução.")


if __name__ == "__main__":
    main()
