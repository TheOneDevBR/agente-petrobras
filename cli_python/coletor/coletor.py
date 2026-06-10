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

AQUI = Path(__file__).resolve().parent
PROJETO = AQUI.parents[1]
FONTES_PATH = AQUI / "fontes.json"

VAULT = Path(os.environ.get("AGENTE_VAULT", PROJETO / "Obsidian_Vault"))
PASTA_PETROBRAS = VAULT / "Petrobras"
PASTA_INTEL = PASTA_PETROBRAS / "Inteligencia"
RESUMO_MOC = PASTA_PETROBRAS / "_RESUMO_INTEL.md"

TOOLS_WEB = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Busca informações recentes na web sobre concurso Petrobras, CESGRANRIO, editais, provas",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Termo de busca (ex.: 'edital Petrobras 2026 CESGRANRIO')",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Acessa uma URL e extrai o conteúdo textual para análise",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL completa para acessar"},
                },
                "required": ["url"],
            },
        },
    },
]

SYSTEM = """\
Você é o braço de inteligência do AgentePetrobras — um analista que monitora
fontes públicas para preparar candidatos ao concurso da Petrobras (banca
CESGRANRIO). Sua função: buscar na web, verificar e SINTETIZAR informação útil.

REGRAS:
- Use APENAS informação pública (editais, gabaritos, provas, notícias, artigos
  abertos de blog). Nunca tente acessar conteúdo pago/atrás de login.
- Cite SEMPRE as fontes com URL. Sem URL, a informação não entra.
- Distinga fato confirmado por fonte oficial de boato/especulação — rotule.
- Honestidade clínica: se não houver novidade ou edital aberto, diga isso
  claramente; não invente.
- Hoje é {hoje}. Priorize o que é recente e acionável para o candidato.
- Use as ferramentas web_search e web_fetch para obter informações atuais.

FORMATO DA SAÍDA — produza UMA nota Obsidian em Markdown, exatamente nesta
estrutura (sem cercas de código ao redor, sem texto antes ou depois):

resumo_uma_linha: <uma frase objetiva, <140 caracteres, para índice>

## Resumo executivo
<3 a 6 bullets com o essencial>

## Detalhes
<parágrafos com os achados, datas, números, nomes — cite [n] referências>

## O que muda para o candidato
<2 a 4 bullets de ação concreta: o que estudar/ajustar por causa disto>

## Disciplinas relacionadas
<liste links no estilo [[Língua Portuguesa]], [[Lei 13.303]], [[Engenharia de Petróleo]] etc.>

## Fontes
<lista numerada de URLs reais que você consultou>"""

PROMPT_BEAT = """\
MISSÃO ({beat_id}): {titulo}
Cargo em foco: {cargo}

{instrucao}

Domínios sugeridos (não exclusivos): {dominios}

Pesquise agora e produza a nota no formato definido."""


def _slug(texto: str) -> str:
    s = re.sub(r"[^\w\s-]", "", texto.lower(), flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "nota"


def _extrair_resumo(corpo: str) -> str:
    m = re.search(r"resumo_uma_linha:\s*(.+)", corpo)
    return m.group(1).strip() if m else "(sem resumo)"


def coletar_beat(cliente, beat: dict, cargo: str) -> tuple[str, str] | None:
    """Executa um beat: web search + síntese via LLM local. Retorna (corpo_markdown, resumo)."""
    prompt = PROMPT_BEAT.format(
        beat_id=beat["id"],
        titulo=beat["titulo"],
        cargo=cargo,
        instrucao=beat["instrucao"],
        dominios=", ".join(beat.get("dominios_sugeridos", [])) or "—",
    )
    system = SYSTEM.format(hoje=date.today().isoformat())
    messages = [{"role": "user", "content": prompt}]

    try:
        corpo = cliente.chat_with_tools(
            system=system,
            messages=messages,
            tools=TOOLS_WEB,
            max_tokens=12000,
        )
    except LocalLLMError as e:
        print(f"   [erro no beat '{beat['id']}': {e}]")
        return None

    if not corpo:
        print(f"   [beat '{beat['id']}' não retornou texto]")
        return None
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
    """Reescreve o _RESUMO_INTEL.md (mapa de conteúdo) com os achados do dia no topo."""
    hoje = date.today().isoformat()
    linhas_hoje = [f"## Coleta de {hoje}", ""]
    for r in registros:
        linhas_hoje.append(f"- [[{r['arquivo'].stem}|{r['titulo']}]] — {r['resumo']}")
    linhas_hoje.append("")

    anterior = ""
    if RESUMO_MOC.exists():
        anterior = RESUMO_MOC.read_text(encoding="utf-8")
        anterior = re.sub(r"^---.*?---\n\n", "", anterior, count=1, flags=re.DOTALL)
        anterior = re.sub(r"^# .*?\n\n", "", anterior, count=1, flags=re.DOTALL)

    header = (
        "---\ntitulo: Resumo de Inteligência (MOC)\ntipo: indice\n"
        f"atualizado_em: {hoje}\n---\n\n"
        "# 📡 Resumo de Inteligência — AgentePetrobras\n\n"
        "_Mapa de conteúdo gerado pela coleta automática. As notas completas "
        "estão em [[Inteligencia]]._\n\n"
    )
    RESUMO_MOC.parent.mkdir(parents=True, exist_ok=True)
    RESUMO_MOC.write_text(header + "\n".join(linhas_hoje) + "\n" + anterior, encoding="utf-8")


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
