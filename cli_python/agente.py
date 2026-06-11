#!/usr/bin/env python3
"""AgentePetrobras v4.0 — CLI.

Preparador autônomo para concursos Petrobras (banca CESGRANRIO), construído
sobre o SDK da Anthropic. Carrega o system prompt v4.0, mantém memória
persistente do candidato, registra sessões de estudo e calcula métricas
determinísticas (painel) que injeta no prompt a cada interação.

Uso:
    python agente.py
Comandos no chat:
    /sessao     registra uma sessão de estudo (alimenta o painel) e pede análise
    /painel     mostra as métricas calculadas (dias, IC, projeção, gap)
    /relatorio  gera relatório semanal em Markdown (salvo em dados/relatorios/)
    /perfil     mostra o modelo do candidato
    /simulado   inicia um simulado estilo CESGRANRIO (questões múltipla escolha)
    /treino     atalho para /simulado (5 questões, sem cronômetro)
    /salvar     força gravação de tudo
    /reset      apaga o perfil e recomeça o diagnóstico
    /limpar     limpa o histórico da conversa (mantém o perfil)
    /sair       encerra (salva tudo)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import metricas as met
import perfil as perfil_mod

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Console Windows costuma usar cp1252 e quebra ao imprimir emojis/box-chars
# do agente e do painel. Força UTF-8 na saída.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

# ── Config ────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent
DADOS = BASE / "dados"
PROMPT_PATH = BASE / "AgentePetrobras_v4.md"
PERFIL_PATH = DADOS / "perfil_candidato.json"
HIST_PATH = DADOS / "historico_conversa.json"
SESSOES_PATH = DADOS / "sessoes.json"
RELATORIOS_DIR = DADOS / "relatorios"

try:
    from local_llm import LocalLLM, LocalLLMError
except ImportError:
    print("Falta o módulo local_llm.py. Verifique se está no mesmo diretório.")
    sys.exit(1)

import treino as treino_mod

MAX_TOKENS = int(os.environ.get("AGENTE_MAX_TOKENS", "4096"))
MAX_TURNOS_CONTEXTO = 40  # nº de mensagens mantidas na janela de contexto

# Resumo de inteligência produzido pelo coletor (coletor/coletor.py)
VAULT = Path(os.environ.get("AGENTE_VAULT", BASE.parent / "Obsidian_Vault"))
INTEL_MOC = VAULT / "Petrobras" / "_RESUMO_INTEL.md"
INTEL_MAX_CHARS = 2500  # quanto do resumo injetar no prompt


# ── Cores ANSI ──────────────────────────────────────────────────────────────
class C:
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    VERDE = "\033[32m"
    AMARELO = "\033[33m"
    CIANO = "\033[36m"
    AZUL = "\033[34m"
    VERM = "\033[31m"


def _cor(txt: str, cor: str) -> str:
    if os.environ.get("NO_COLOR"):
        return txt
    return f"{cor}{txt}{C.RESET}"


# ── Persistência genérica de JSON ────────────────────────────────────────────
def _ler_json(caminho: Path, default):
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default
    return default


def _gravar_json(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


# ── System prompt dinâmico ───────────────────────────────────────────────────
def _intel_recente() -> str:
    """Lê o resumo de inteligência coletado (se existir) para injetar no prompt."""
    if not INTEL_MOC.exists():
        return ""
    try:
        texto = INTEL_MOC.read_text(encoding="utf-8")
    except OSError:
        return ""
    # remove frontmatter
    import re as _re
    texto = _re.sub(r"^---.*?---\n", "", texto, count=1, flags=_re.DOTALL).strip()
    if len(texto) > INTEL_MAX_CHARS:
        texto = texto[:INTEL_MAX_CHARS] + "\n…(ver notas completas no Obsidian)"
    return texto


def montar_system(perfil: dict, sessoes: list[dict]) -> str:
    base = "Responda SEMPRE em português do Brasil.\n\n" + PROMPT_PATH.read_text(encoding="utf-8")
    painel = met.painel(perfil, sessoes)
    bloco_painel = f"\n{painel}\n" if painel else ""
    intel = _intel_recente()
    bloco_intel = (
        "\n[INTEL_RECENTE] (coletado automaticamente de fontes públicas; "
        "use para alertar o candidato sobre editais/tendências e ajustar o plano)\n"
        f"{intel}\n" if intel else ""
    )
    contexto = (
        f"\n\n━━━ CONTEXTO DESTA SESSÃO ━━━\n"
        f"Data de hoje: {date.today().isoformat()}\n\n"
        f"{perfil_mod.resumo_para_prompt(perfil)}\n"
        f"{bloco_painel}"
        f"{bloco_intel}"
    )
    return base + contexto


# ── UI ───────────────────────────────────────────────────────────────────────
def banner(perfil: dict, sessoes: list[dict]) -> None:
    linha = "═" * 64
    print(_cor(linha, C.AZUL))
    print(_cor("  AGENTE PETROBRAS v4.0", C.BOLD + C.AMARELO)
          + _cor("  ·  CESGRANRIO  ·  Estrategista+Coach+Cientista", C.DIM))
    print(_cor(linha, C.AZUL))
    if perfil_mod.esta_vazio(perfil):
        print(_cor("  Primeira sessão — o agente vai iniciar o diagnóstico.", C.DIM))
    else:
        alvo = perfil.get("cargo_alvo", "—")
        fase = perfil.get("fase_atual", "—")
        streak = met.streak_de_sessoes(sessoes)
        dias = met.dias_ate_prova(perfil)
        extra = f"  ·  {dias}d p/ prova" if dias is not None else ""
        print(_cor(f"  Candidato: {alvo}  ·  Fase: {fase}  ·  Streak: {streak}d{extra}", C.DIM))
    print(_cor("  Comandos: /sessao /painel /simulado /perfil /reset /sair", C.DIM))
    print(_cor(linha, C.AZUL))


def mostrar_perfil(perfil: dict) -> None:
    relevante = {k: v for k, v in perfil.items() if v not in (None, {}, [], 0)}
    print(_cor("\n── PERFIL DO CANDIDATO ──", C.CIANO))
    print(json.dumps(relevante, ensure_ascii=False, indent=2))
    print()


def mostrar_painel(perfil: dict, sessoes: list[dict]) -> None:
    txt = met.painel(perfil, sessoes)
    print(_cor("\n", C.RESET) + (_cor(txt, C.CIANO) if txt
          else _cor("Sem dados suficientes ainda. Defina a data da prova e registre sessões com /sessao.", C.DIM)))
    print()


def _input_int(rotulo: str, default: int = 0) -> int:
    v = input(_cor(rotulo, C.AMARELO)).strip()
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def registrar_sessao(perfil: dict, sessoes: list[dict]) -> str | None:
    """Coleta uma sessão de estudo, atualiza perfil e sessoes.json.
    Retorna uma mensagem sintética para o agente analisar (ou None se cancelado)."""
    print(_cor("\n── REGISTRAR SESSÃO DE ESTUDO ──  (Enter vazio cancela disciplina)", C.CIANO))
    disciplina = input(_cor("Disciplina/tema: ", C.AMARELO)).strip()
    if not disciplina:
        print(_cor("Cancelado.", C.DIM))
        return None
    minutos = _input_int("Minutos estudados: ")
    questoes = _input_int("Questões resolvidas: ")
    acertos = _input_int("Acertos: ")
    erro_dom = input(_cor("Tipo de erro dominante [C/A/B/T ou Enter]: ", C.AMARELO)).strip().upper()
    if erro_dom not in ("C", "A", "B", "T"):
        erro_dom = None

    pct = round(acertos / questoes * 100, 1) if questoes else None
    sessao = {
        "data": date.today().isoformat(),
        "disciplina": disciplina,
        "minutos": minutos,
        "questoes": questoes,
        "acertos": acertos,
        "acerto_pct": pct,
        "erro_dominante": erro_dom,
    }
    sessoes.append(sessao)
    _gravar_json(SESSOES_PATH, sessoes)

    # Atualiza o perfil com dados derivados (determinísticos).
    if pct is not None:
        perfil.setdefault("historico_acerto", {})[_chave(disciplina)] = pct
    perfil["questoes_resolvidas"] = (perfil.get("questoes_resolvidas") or 0) + questoes
    perfil["horas_acumuladas"] = round((perfil.get("horas_acumuladas") or 0) + minutos / 60, 1)
    perfil["streak_dias"] = met.streak_de_sessoes(sessoes)
    if perfil["streak_dias"] > (perfil.get("maior_streak") or 0):
        perfil["maior_streak"] = perfil["streak_dias"]
    if erro_dom:
        perfil["erro_dominante_historico"] = erro_dom
    perfil_mod.salvar(perfil, PERFIL_PATH)

    resumo = (f"{disciplina}: {minutos}min, {acertos}/{questoes} questões"
              f"{f' ({pct}%)' if pct is not None else ''}"
              f"{f', erro dominante [{erro_dom}]' if erro_dom else ''}")
    print(_cor(f"  ✓ Sessão registrada — {resumo}", C.VERDE))
    return (
        f"Registrei esta sessão de estudo: {resumo}. "
        "Analise como Coach+Cientista usando o PAINEL_DE_CONTROLE atualizado: "
        "comente o resultado, classifique a tendência e prescreva o próximo passo concreto."
    )


def _chave(disciplina: str) -> str:
    """Normaliza o nome da disciplina para chave do historico_acerto."""
    import re
    s = disciplina.lower().strip()
    s = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE)
    return s.strip("_") or "geral"


def gerar_relatorio(perfil: dict, sessoes: list[dict]) -> None:
    md = met.relatorio_semanal_md(perfil, sessoes)
    RELATORIOS_DIR.mkdir(parents=True, exist_ok=True)
    nome = RELATORIOS_DIR / f"relatorio_{date.today().isoformat()}.md"
    nome.write_text(md, encoding="utf-8")
    print(_cor(f"\n  ✓ Relatório salvo em: {nome}\n", C.VERDE))
    print(_cor(md, C.DIM))


# ── Chamada ao modelo (streaming) ────────────────────────────────────────────
def chamar_agente(cliente, perfil, sessoes, historico, entrada) -> bool:
    """Processa um turno: envia 'entrada', faz streaming, aplica diretivas.
    Retorna True se houve resposta válida."""
    historico.append({"role": "user", "content": entrada})
    system = montar_system(perfil, sessoes)
    janela = historico[-MAX_TURNOS_CONTEXTO:]

    print(_cor("\nAgente ▸ ", C.CIANO), end="", flush=True)
    resposta_texto = ""
    try:
        for delta in cliente.stream_chat(system=system, messages=janela, max_tokens=MAX_TOKENS):
            print(delta, end="", flush=True)
            resposta_texto += delta
        print()
    except LocalLLMError as e:
        print(_cor(f"\n[erro: {e}]", C.VERM))
        historico.pop()
        return False
    except KeyboardInterrupt:
        print(_cor("\n[interrompido]", C.DIM))
        if not resposta_texto:
            historico.pop()
            return False

    texto_limpo, mudancas = perfil_mod.aplicar_diretivas(resposta_texto, perfil)
    historico.append({"role": "assistant", "content": texto_limpo})
    if mudancas:
        perfil_mod.salvar(perfil, PERFIL_PATH)
        print(_cor(f"  ↳ perfil atualizado: {', '.join(mudancas)}", C.DIM))
    _gravar_json(HIST_PATH, historico)
    return True


# ── Loop principal ───────────────────────────────────────────────────────────

def _processar_entrada(
    entrada: str,
    perfil: dict,
    sessoes: list,
    historico: list,
    cliente: LocalLLM,
    confirm_fn=None,
) -> tuple[bool, str | None]:
    """Processa um comando/entrada do usuário.

    Retorna (should_break, nova_entrada_injetada).
    should_break=True indica que o loop deve encerrar.
    confirm_fn é usado para testes (padrão = input embutido).
    """
    if confirm_fn is None:
        confirm_fn = input
    cmd = entrada.lower()

    if cmd in ("/sair", "/quit", "/exit"):
        perfil_mod.salvar(perfil, PERFIL_PATH)
        _gravar_json(HIST_PATH, historico)
        _gravar_json(SESSOES_PATH, sessoes)
        print(_cor("\nTudo salvo. Bons estudos — você está construindo isso hoje.", C.AMARELO))
        return True, None

    if cmd == "/perfil":
        mostrar_perfil(perfil)
        return False, None

    if cmd == "/painel":
        mostrar_painel(perfil, sessoes)
        return False, None

    if cmd == "/relatorio":
        gerar_relatorio(perfil, sessoes)
        return False, None

    if cmd == "/sessao":
        msg = registrar_sessao(perfil, sessoes)
        return False, msg

    if cmd in ("/simulado", "/treino"):
        if cmd == "/treino":
            n = 5
            tempo = 0
            disc = ""
        else:
            print(_cor("\nConfiguração do simulado:", C.CIANO))
            n = _input_int("Número de questões (Enter=5): ", default=5)
            tempo = _input_int("Limite em minutos (Enter=0 sem limite): ", default=0)
            disc = input(_cor("Disciplina (Enter=todas): ", C.AMARELO)).strip()
        resultado = treino_mod.iniciar_simulado(n_questoes=n, cronometro=tempo, disciplina=disc)
        if resultado.get("erro"):
            print(_cor(f"  {resultado['erro']}", C.VERM))
            return False, None
        pct = resultado.get("pct", 0)
        face = "✅" if pct >= 70 else ("🟡" if pct >= 50 else "❌")
        msg_inj = (
            f"{face} Simulado concluído: {resultado['acertos']}/{resultado['questoes']} ({pct}%) "
            f"em {resultado['disciplina']} ({resultado['tempo_seg']}s). "
            "Analise o desempenho como Coach+Cientista: aponte padrões de erro, "
            "sugira revisão direcionada e um próximo passo concreto."
        )
        return False, msg_inj

    if cmd == "/salvar":
        perfil_mod.salvar(perfil, PERFIL_PATH)
        _gravar_json(HIST_PATH, historico)
        _gravar_json(SESSOES_PATH, sessoes)
        print(_cor("Salvo.", C.DIM))
        return False, None

    if cmd == "/limpar":
        historico.clear()
        _gravar_json(HIST_PATH, historico)
        print(_cor("Histórico de conversa limpo (perfil e sessões mantidos).", C.DIM))
        return False, None

    if cmd == "/reset":
        confirm = confirm_fn(_cor("Apagar perfil e recomeçar o diagnóstico? (sessões serão mantidas) (s/N) ", C.AMARELO)).strip().lower()
        if confirm == "s":
            perfil.clear()
            perfil.update(perfil_mod.perfil_vazio())
            historico.clear()
            perfil_mod.salvar(perfil, PERFIL_PATH)
            _gravar_json(HIST_PATH, historico)
            print(_cor("Perfil apagado. Reinicie a conversa quando quiser.", C.DIM))
        return False, None

    # ── Turno normal com o agente ──
    chamar_agente(cliente, perfil, sessoes, historico, entrada)
    return False, None


def main(input_fn=None) -> None:
    """Loop principal do agente.

    input_fn: injetável para testes (padrão = None → usa input() real).
    """
    cliente = LocalLLM()
    perfil = perfil_mod.carregar(PERFIL_PATH)
    sessoes = _ler_json(SESSOES_PATH, [])
    historico = _ler_json(HIST_PATH, [])

    banner(perfil, sessoes)
    print(_cor(f"  LLM: {cliente.model} @ {cliente.base_url}", C.DIM))
    print(_cor("  Variáveis: AGENTE_LLM_BASE_URL / AGENTE_LOCAL_MODEL", C.DIM))

    if input_fn is None:
        input_fn = input

    entrada_injetada: str | None = None
    if not historico and not perfil_mod.esta_vazio(perfil):
        entrada_injetada = "Iniciar sessão. Faça a abertura de 3 linhas (§2) e proponha o foco de hoje com base no PAINEL_DE_CONTROLE."
    elif not historico:
        entrada_injetada = "Olá! Quero começar minha preparação."

    while True:
        if entrada_injetada is not None:
            entrada = entrada_injetada
            entrada_injetada = None
            print(_cor("\nVocê ▸ ", C.VERDE) + _cor("(início automático)", C.DIM))
        else:
            try:
                entrada = input_fn(_cor("\nVocê ▸ ", C.VERDE)).strip()
            except (EOFError, KeyboardInterrupt):
                entrada = "/sair"

        if not entrada:
            continue

        should_break, nova_injetada = _processar_entrada(
            entrada, perfil, sessoes, historico, cliente,
            confirm_fn=input_fn,
        )
        if should_break:
            break
        if nova_injetada:
            entrada_injetada = nova_injetada


if __name__ == "__main__":
    main()
