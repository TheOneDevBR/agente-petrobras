#!/usr/bin/env python3
"""AgentePetrobras CLI — comando único com subcomandos.

Uso:
    agente chat                         # modo interativo (padrão)
    agente simulado                     # simulado rápido (5 questões)
    agente prova-completa               # prova completa 70q/4h
    agente benchmark                    # benchmark de qualidade
    agente cronograma                   # gera cronograma semanal
    agente risco                        # análise monte carlo
    agente provas                       # extrair provas PDF
    agente anki                         # exportar questões para Anki
    agente perfil                       # mostrar perfil
    agente metricas                     # mostrar métricas
    agente ciclo                        # ciclo de autoevolução
    agente ciclo --relatorio            # painel de autoevolução
    agente ciclo --rollback estrategias # rollback de um overlay
    agente autonomia                    # painel de autonomia do sistema
    agente autonomia --ciclo            # um ciclo autônomo (diagnóstico+cura+aprendizado)
    agente autonomia --gaps             # próximas evoluções do projeto
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

CLI_PYTHON = Path(__file__).resolve().parent
sys.path.insert(0, str(CLI_PYTHON))

try:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def cmd_chat(args: argparse.Namespace) -> None:
    """Modo interativo (padrão)."""
    from agente import main as agente_main
    sys.argv = [sys.argv[0]]
    agente_main()


def cmd_simulado(args: argparse.Namespace) -> None:
    """Simulado rápido."""
    from treino import iniciar_simulado
    iniciar_simulado(
        n_questoes=args.questoes,
        cronometro=args.tempo,
        disciplina=args.disciplina,
        adaptativo=getattr(args, "adaptativo", False),
    )


def cmd_diagnostico(args: argparse.Namespace) -> None:
    """Diagnóstico adaptativo de habilidade por disciplina."""
    import coaching
    print(coaching.formatar_diagnostico())


def cmd_prescrever(args: argparse.Namespace) -> None:
    """Prescreve a próxima ação de estudo (loop de eficácia fechado)."""
    import prescricao
    p = prescricao.prescrever(disciplina=args.disciplina or None)
    print(prescricao.formatar_prescricao(p))


def cmd_eficacia(args: argparse.Namespace) -> None:
    """Relatório de eficácia das estratégias (o que melhora a nota)."""
    import prescricao
    print(prescricao.formatar_eficacia())


def cmd_erros(args: argparse.Namespace) -> None:
    """Perfil de erros C/A/B/T e a correção prescrita."""
    import erros
    print(erros.formatar_distribuicao())


def cmd_importar_questoes(args: argparse.Namespace) -> None:
    """Extrai questões reais de PDFs de provas e acrescenta ao banco."""
    import importar_questoes as iq
    pdfs = None
    if args.prova:
        pdfs = [Path(args.prova)]
    elif args.pasta:
        pdfs = sorted(Path(args.pasta).glob("*.pdf"))
    gab_pdf = Path(args.gabarito) if args.gabarito else None
    if gab_pdf is None and pdfs is None:
        print("Sem gabarito, questões não são importadas (não inventamos resposta).")
    n = iq.de_pdfs(pdfs=pdfs, disciplina=args.disciplina, gabarito_pdf=gab_pdf)
    stats = iq.estatisticas()
    print(f"✓ {n} questão(ões) nova(s) importada(s).")
    print(f"  Banco de extraídas: {stats['total']} questões.")
    for disc, c in sorted(stats["por_disciplina"].items(), key=lambda kv: -kv[1]):
        print(f"    {disc}: {c}")


def cmd_fontes(args: argparse.Namespace) -> None:
    """Fontes novas descobertas automaticamente pela busca contínua."""
    import descoberta
    print(descoberta.relatorio())
    proms = descoberta.promovidas()
    if proms:
        print(f"\n  ⭐ Promovidas (realimentam as buscas): {', '.join(proms)}")


def cmd_checkin(args: argparse.Namespace) -> None:
    """Check-in diário: streak, consistência, revisões e próxima ação."""
    import aderencia
    print(aderencia.formatar_checkin(aderencia.checkin()))


def cmd_revisoes(args: argparse.Namespace) -> None:
    """Lista as revisões SM-2 vencidas/próximas."""
    import sm2
    devidas = sm2.revisoes_devidas()
    if not devidas:
        print("✅ Nenhuma revisão vencida. Em dia!")
        return
    print(f"🗓️  {len(devidas)} revisão(ões) vencida(s):")
    for c in devidas[: args.limite]:
        print(f"  • [{c.get('disciplina', '?')}] {c.get('resumo', c.get('pergunta', ''))[:70]}")


def cmd_redacao(args: argparse.Namespace) -> None:
    """Avalia uma redação/discursiva por rubrica CESGRANRIO."""
    import redacao
    texto = Path(args.arquivo).read_text(encoding="utf-8")
    cliente = None
    if not args.sem_llm:
        try:
            from local_llm import LocalLLM
            cliente = LocalLLM()
        except Exception:
            print("LLM indisponível — fazendo análise estrutural.")
    print(redacao.formatar(redacao.avaliar(texto, tema=args.tema, cliente=cliente)))


def cmd_prova_completa(args: argparse.Namespace) -> None:
    """Prova completa 70 questões / 4h."""
    from treino import iniciar_prova_completa
    iniciar_prova_completa()


def cmd_benchmark(args: argparse.Namespace) -> None:
    """Benchmark de qualidade."""
    from benchmark_qualidade import main as bm_main
    bm_args = [sys.argv[0]]
    if args.model:
        bm_args.extend(["--model", args.model])
    if args.skip_rag:
        bm_args.append("--skip-rag")
    if args.skip_no_rag:
        bm_args.append("--skip-no-rag")
    if args.output:
        bm_args.extend(["--output", args.output])
    sys.argv = bm_args
    bm_main()


def cmd_cronograma(args: argparse.Namespace) -> None:
    """Gera cronograma semanal."""
    import json

    from agendador import formatar_cronograma, gerar_cronograma, gerar_e_salvar

    dados = CLI_PYTHON / "dados"
    perfil = json.loads((dados / "perfil_candidato.json").read_text(encoding="utf-8")) if (dados / "perfil_candidato.json").exists() else {}
    sessoes = json.loads((dados / "sessoes.json").read_text(encoding="utf-8")) if (dados / "sessoes.json").exists() else []
    simulados = json.loads((dados / "simulados.json").read_text(encoding="utf-8")) if (dados / "simulados.json").exists() else []

    caminho = gerar_e_salvar(perfil, sessoes, simulados, args.output)
    print(f"Cronograma salvo em: {caminho}")
    print()
    cronograma = gerar_cronograma(perfil, sessoes, simulados)
    print(formatar_cronograma(cronograma))


def cmd_risco(args: argparse.Namespace) -> None:
    """Análise de risco Monte Carlo."""
    import json

    from risco_monte_carlo import formatar_relatorio, simular_aprovacao, simular_e_salvar

    dados = CLI_PYTHON / "dados"
    perfil = json.loads((dados / "perfil_candidato.json").read_text(encoding="utf-8")) if (dados / "perfil_candidato.json").exists() else {}
    sessoes = json.loads((dados / "sessoes.json").read_text(encoding="utf-8")) if (dados / "sessoes.json").exists() else []
    simulados = json.loads((dados / "simulados.json").read_text(encoding="utf-8")) if (dados / "simulados.json").exists() else []

    caminho = simular_e_salvar(perfil, sessoes, simulados, args.output, n_cenarios=args.cenarios)
    print(f"Relatório salvo em: {caminho}")
    resultado = simular_aprovacao(perfil, sessoes, simulados, n_cenarios=args.cenarios)
    print(formatar_relatorio(resultado))


def cmd_provas(args: argparse.Namespace) -> None:
    """Extrair provas PDF."""
    from extrair_provas_pdf import baixar_provas, extrair_provas, relatorio_provas

    if args.baixar:
        baixados = baixar_provas(limite=args.limite)
        print(f"\n{len(baixados)} PDF(s) baixados.")
    else:
        resultados = extrair_provas()
        if resultados:
            rel = relatorio_provas(resultados)
            saida = CLI_PYTHON / "dados" / "provas" / "relatorio_extracoes.md"
            saida.parent.mkdir(parents=True, exist_ok=True)
            saida.write_text(rel, encoding="utf-8")
            print(f"Relatório: {saida}")


def cmd_anki(args: argparse.Namespace) -> None:
    """Exportar questões para Anki."""
    from exportar_anki import exportar_apkg, exportar_csv

    if args.formato == "apkg":
        total = exportar_apkg(Path(args.output), args.disciplina)
    else:
        total = exportar_csv(Path(args.output), args.disciplina)

    if total:
        print(f"{total} questões exportadas para {args.output}")
    else:
        print("Nenhuma questão exportada.")


def cmd_perfil(args: argparse.Namespace) -> None:
    """Mostrar perfil do candidato."""
    import json
    dados = CLI_PYTHON / "dados"
    perfil_path = dados / "perfil_candidato.json"
    if not perfil_path.exists():
        print("Perfil não encontrado. Use 'agente chat' para criar um.")
        return
    perfil = json.loads(perfil_path.read_text(encoding="utf-8"))
    for k, v in perfil.items():
        print(f"  {k}: {v}")


def cmd_metricas(args: argparse.Namespace) -> None:
    """Mostrar métricas."""
    import json

    import metricas as met
    dados = CLI_PYTHON / "dados"
    perfil = json.loads((dados / "perfil_candidato.json").read_text(encoding="utf-8")) if (dados / "perfil_candidato.json").exists() else {}
    sessoes = json.loads((dados / "sessoes.json").read_text(encoding="utf-8")) if (dados / "sessoes.json").exists() else []
    pnl = met.painel(perfil, sessoes)
    print(pnl if pnl else "Sem dados suficientes.")


def cmd_ciclo(args: argparse.Namespace) -> None:
    """Ciclo de autoevolução (não interativo — útil para cron)."""
    from ciclo_evolutivo import executar_ciclo, relatorio_evolucao

    if args.relatorio:
        print(relatorio_evolucao())
        return

    if args.rollback:
        from prompt_evoluivel import PromptEvoluivel
        pe = PromptEvoluivel()
        ok = pe.rollback(args.rollback)
        print(f"{'Rollback OK' if ok else 'Falha no rollback'}: {args.rollback}")
        return

    cliente = None
    if not args.no_evolve:
        try:
            from local_llm import LocalLLM
            cliente = LocalLLM()
        except Exception:
            print("LLM não disponível — rodando sem evolução de prompts")

    executar_ciclo(
        cliente_llm=cliente,
        evoluir_prompts=not args.no_evolve and cliente is not None,
    )


def cmd_autonomia(args: argparse.Namespace) -> None:
    """Núcleo autônomo: autodiagnóstico, auto-cura, proatividade e aprendizado."""
    import json

    import autonomia as auto

    if args.ciclo:
        rel = auto.ciclo_autonomo(permitir_sensiveis=args.confirmar)
        print(json.dumps(rel, ensure_ascii=False, indent=2, default=str))
    elif args.gaps:
        print(auto.painel_comando("gaps"))
    else:
        print(auto.painel_comando("resumo"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AgentePetrobras — preparador autônomo para concurso Petrobras (CESGRANRIO)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="AgentePetrobras v4.0")

    sub = parser.add_subparsers(dest="comando", help="Comando a executar")

    # chat
    p_chat = sub.add_parser("chat", help="Modo interativo (padrão)")

    # simulado
    p_sim = sub.add_parser("simulado", help="Simulado rápido")
    p_sim.add_argument("-n", "--questoes", type=int, default=5, help="Número de questões")
    p_sim.add_argument("-t", "--tempo", type=int, default=0, help="Limite em minutos (0=sem limite)")
    p_sim.add_argument("-d", "--disciplina", default="", help="Filtrar por disciplina")
    p_sim.add_argument("-a", "--adaptativo", action="store_true",
                       help="Questões na dificuldade certa (coaching adaptativo)")

    # prova-completa
    p_prova = sub.add_parser("prova-completa", help="Prova completa 70q/4h")

    # benchmark
    p_bm = sub.add_parser("benchmark", help="Benchmark de qualidade")
    p_bm.add_argument("--model", default="qwen2.5:1.5b", help="Modelo para testar")
    p_bm.add_argument("--skip-rag", action="store_true", help="Pular teste com RAG")
    p_bm.add_argument("--skip-no-rag", action="store_true", help="Pular teste sem RAG")
    p_bm.add_argument("-o", "--output", help="Salvar relatório em arquivo")

    # cronograma
    p_cron = sub.add_parser("cronograma", help="Gerar cronograma semanal")
    p_cron.add_argument("-o", "--output", help="Caminho do arquivo de saída")

    # risco
    p_risco = sub.add_parser("risco", help="Análise de risco Monte Carlo")
    p_risco.add_argument("-n", "--cenarios", type=int, default=10000, help="Número de cenários")
    p_risco.add_argument("-o", "--output", help="Caminho do arquivo de saída")

    # provas
    p_prov = sub.add_parser("provas", help="Extrair provas PDF")
    p_prov.add_argument("--baixar", action="store_true", help="Só baixar PDFs")
    p_prov.add_argument("--limite", type=int, default=10, help="Limite de PDFs")

    # anki
    p_anki = sub.add_parser("anki", help="Exportar questões para Anki")
    p_anki.add_argument("-f", "--formato", choices=["csv", "apkg"], default="csv")
    p_anki.add_argument("-d", "--disciplina", default="", help="Filtrar por disciplina")
    p_anki.add_argument("-o", "--output", default="questoes_anki.csv", help="Arquivo de saída")

    # perfil
    sub.add_parser("perfil", help="Mostrar perfil do candidato")

    # metricas
    sub.add_parser("metricas", help="Mostrar métricas")

    # diagnostico (coaching adaptativo)
    sub.add_parser("diagnostico", help="Diagnóstico adaptativo de habilidade por disciplina")

    # prescrever (loop de eficácia fechado)
    p_presc = sub.add_parser("prescrever", help="Prescreve a próxima ação de estudo")
    p_presc.add_argument("-d", "--disciplina", default="", help="Forçar disciplina (padrão: a mais fraca)")

    # eficacia (relatório do loop)
    sub.add_parser("eficacia", help="Eficácia das estratégias (o que melhora a nota)")

    # erros (perfil C/A/B/T)
    sub.add_parser("erros", help="Perfil de erros C/A/B/T e correção prescrita")

    # importar-questoes (extrair de PDFs para o banco)
    p_iq = sub.add_parser("importar-questoes", help="Extrair questões reais de PDFs e acrescentar ao banco")
    p_iq.add_argument("--prova", default="", help="PDF do caderno de prova (questões)")
    p_iq.add_argument("--gabarito", default="", help="PDF do gabarito (respostas) — sem ele, nada é importado")
    p_iq.add_argument("--pasta", default="", help="Pasta com PDFs (padrão: dados/provas)")
    p_iq.add_argument("-d", "--disciplina", default="", help="Disciplina das questões")

    # fontes (descoberta automática de sites)
    sub.add_parser("fontes", help="Sites novos descobertos pela busca contínua")

    # checkin (aderência/accountability)
    sub.add_parser("checkin", help="Check-in diário (streak, consistência, próxima ação)")

    # revisoes (SM-2 vencidas)
    p_rev = sub.add_parser("revisoes", help="Revisões SM-2 vencidas")
    p_rev.add_argument("-l", "--limite", type=int, default=20, help="Máximo a listar")

    # redacao (avaliador discursivo)
    p_red = sub.add_parser("redacao", help="Avaliar uma redação/discursiva por rubrica")
    p_red.add_argument("arquivo", help="Caminho do arquivo de texto com a redação")
    p_red.add_argument("-t", "--tema", default="", help="Tema proposto")
    p_red.add_argument("--sem-llm", action="store_true", help="Só análise estrutural (sem LLM)")

    # ciclo (autoevolução)
    p_ciclo = sub.add_parser("ciclo", help="Ciclo de autoevolução")
    p_ciclo.add_argument("--relatorio", action="store_true", help="Apenas mostrar o painel de autoevolução")
    p_ciclo.add_argument("--rollback", metavar="OVERLAY", help="Rollback de um overlay do prompt")
    p_ciclo.add_argument("--no-evolve", action="store_true", help="Pular evolução de prompts (sem LLM)")

    # autonomia (núcleo autônomo)
    p_auto = sub.add_parser("autonomia", help="Núcleo autônomo (diagnóstico/cura/proatividade)")
    p_auto.add_argument("--ciclo", action="store_true", help="Executa um ciclo autônomo e imprime o relatório")
    p_auto.add_argument("--gaps", action="store_true", help="Lista as próximas evoluções (gaps)")
    p_auto.add_argument("--confirmar", action="store_true", help="Permite ações sensíveis (instalar pacotes na auto-cura)")

    args = parser.parse_args()

    # Default: chat
    if args.comando is None:
        cmd_chat(args)
        return

    dispatch = {
        "chat": cmd_chat,
        "simulado": cmd_simulado,
        "prova-completa": cmd_prova_completa,
        "benchmark": cmd_benchmark,
        "cronograma": cmd_cronograma,
        "risco": cmd_risco,
        "provas": cmd_provas,
        "anki": cmd_anki,
        "perfil": cmd_perfil,
        "metricas": cmd_metricas,
        "diagnostico": cmd_diagnostico,
        "prescrever": cmd_prescrever,
        "eficacia": cmd_eficacia,
        "erros": cmd_erros,
        "redacao": cmd_redacao,
        "importar-questoes": cmd_importar_questoes,
        "fontes": cmd_fontes,
        "checkin": cmd_checkin,
        "revisoes": cmd_revisoes,
        "ciclo": cmd_ciclo,
        "autonomia": cmd_autonomia,
    }

    handler = dispatch.get(args.comando)
    if handler:
        handler(args)


if __name__ == "__main__":
    main()
