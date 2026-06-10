#!/usr/bin/env python3
"""Coletor de inteligência do AgentePetrobras.

Busca periódica em fontes PÚBLICAS (banca CESGRANRIO, carreiras Petrobras,
blogs de cursinhos, portais de concurso) usando as ferramentas server-side
web_search + web_fetch da API da Anthropic. Cada "beat" de fontes.json vira
UMA nota Markdown no vault do Obsidian. Ao final, dispara o /graphify (via
CLI headless do Claude Code) para atualizar o grafo de conhecimento.

Uso:
    python coletor.py                 # roda todos os beats + graphify
    python coletor.py --beat editais  # só um beat
    python coletor.py --no-graph      # não roda o graphify
    python coletor.py --listar        # lista os beats configurados

Variáveis de ambiente:
    ANTHROPIC_API_KEY   (obrigatória)
    AGENTE_VAULT        caminho do vault Obsidian (default: <projeto>/Obsidian_Vault)
    AGENTE_MODELO       default claude-opus-4-8
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

# UTF-8 na saída (console Windows é cp1252 e quebra com emoji/acento).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

try:
    import anthropic
except ImportError:
    print("Falta o SDK. Rode:  pip install -r ../requirements.txt")
    sys.exit(1)

try:
    from dotenv import load_dotenv

    # .env fica em cli_python/
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv()
except ImportError:
    pass

# ── Caminhos ─────────────────────────────────────────────────────────────────
AQUI = Path(__file__).resolve().parent
PROJETO = AQUI.parents[1]  # <projeto>/cli_python/coletor -> <projeto>
FONTES_PATH = AQUI / "fontes.json"

VAULT = Path(os.environ.get("AGENTE_VAULT", PROJETO / "Obsidian_Vault"))
PASTA_PETROBRAS = VAULT / "Petrobras"
PASTA_INTEL = PASTA_PETROBRAS / "Inteligencia"
RESUMO_MOC = PASTA_PETROBRAS / "_RESUMO_INTEL.md"

MODELO = os.environ.get("AGENTE_MODELO", "claude-opus-4-8")

# Ferramentas server-side (rodam na infra da Anthropic). A versão _20260209
# tem dynamic filtering embutido — sem beta header.
TOOLS_WEB = [
    {"type": "web_search_20260209", "name": "web_search"},
    {"type": "web_fetch_20260209", "name": "web_fetch"},
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
<lista numerada de URLs reais que você consultou>
"""

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


def _extrair_texto(message) -> str:
    return "".join(b.text for b in message.content if getattr(b, "type", "") == "text").strip()


def _extrair_resumo(corpo: str) -> str:
    m = re.search(r"resumo_uma_linha:\s*(.+)", corpo)
    return m.group(1).strip() if m else "(sem resumo)"


def coletar_beat(cliente, beat: dict, cargo: str) -> tuple[str, str] | None:
    """Executa um beat: web search + síntese. Retorna (corpo_markdown, resumo)."""
    prompt = PROMPT_BEAT.format(
        beat_id=beat["id"],
        titulo=beat["titulo"],
        cargo=cargo,
        instrucao=beat["instrucao"],
        dominios=", ".join(beat.get("dominios_sugeridos", [])) or "—",
    )
    system = SYSTEM.format(hoje=date.today().isoformat())
    messages = [{"role": "user", "content": prompt}]

    final = None
    for _ in range(6):  # tolera pause_turn do loop server-side de tools
        try:
            with cliente.messages.stream(
                model=MODELO,
                max_tokens=12000,
                system=system,
                tools=TOOLS_WEB,
                thinking={"type": "adaptive"},
                messages=messages,
            ) as stream:
                final = stream.get_final_message()
        except anthropic.APIError as e:
            print(f"   [erro de API no beat '{beat['id']}': {e}]")
            return None

        if final.stop_reason == "pause_turn":
            # preserva blocos (thinking + server_tool_use) e continua
            messages.append({"role": "assistant", "content": final.content})
            continue
        break

    corpo = _extrair_texto(final) if final else ""
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
        # remove cabeçalho antigo para não duplicar
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


def rodar_graphify() -> None:
    """Aciona o /graphify headless via CLI do Claude Code para atualizar o grafo."""
    claude = _achar_claude()
    if not claude:
        print("⚠️  CLI 'claude' não encontrado — pulei o graphify. "
              "Rode manualmente: /graphify no Claude Code sobre a pasta Petrobras.")
        return
    alvo = str(PASTA_PETROBRAS)
    cmd = [claude, "-p", f"/graphify \"{alvo}\" --update --obsidian --obsidian-dir \"{VAULT}\""]
    print(f"\n🧠 Atualizando knowledge graph (graphify) sobre {alvo} ...")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if r.returncode == 0:
            print("   ✓ graphify concluído.")
        else:
            print(f"   [graphify retornou {r.returncode}] {r.stderr[-400:]}")
    except FileNotFoundError:
        print("   [não consegui executar o claude CLI]")
    except subprocess.TimeoutExpired:
        print("   [graphify excedeu o tempo limite de 30min]")


def _achar_claude() -> str | None:
    import shutil
    c = shutil.which("claude")
    if c:
        return c
    for cand in (Path.home() / ".local/bin/claude", Path.home() / ".local/bin/claude.exe",
                 Path.home() / ".local/bin/claude.cmd"):
        if cand.exists():
            return str(cand)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Coletor de inteligência AgentePetrobras")
    parser.add_argument("--beat", help="roda apenas o beat com este id")
    parser.add_argument("--no-graph", action="store_true", help="não roda o graphify")
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

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERRO: defina ANTHROPIC_API_KEY (no .env de cli_python/ ou variável de ambiente).")
        sys.exit(1)

    cliente = anthropic.Anthropic(api_key=api_key)
    print(f"📡 Coleta iniciada — {date.today().isoformat()} — vault: {VAULT}")
    print(f"   {len(beats)} missão(ões) · modelo {MODELO}\n")

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
        if not args.no_graph:
            rodar_graphify()
    else:
        print("\nNenhuma nota gerada nesta execução.")


if __name__ == "__main__":
    main()
