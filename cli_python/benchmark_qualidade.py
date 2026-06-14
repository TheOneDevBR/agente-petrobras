#!/usr/bin/env python3
"""Benchmark automático de qualidade — compara respostas do LLM com/sem RAG.

Uso:
    python cli_python/benchmark_qualidade.py
    python cli_python/benchmark_qualidade.py --model qwen2.5:7b
    python cli_python/benchmark_qualidade.py --output docs/benchmark_resultados.md

Requer LLM local rodando (Ollama).
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from local_llm import LocalLLM

# ── Questões do benchmark ──────────────────────────────────────────────

@dataclass
class Questao:
    pergunta: str
    keywords: list[str]
    contexto_rag: str = ""


BENCHMARK: list[Questao] = [
    Questao(
        pergunta="O que é a Lei 13.303/2016 e qual seu principal objeto?",
        keywords=["13.303", "estatal", "empresa pública", "estatuto jurídico",
                   "governança", "licitação"],
        contexto_rag="""[TEXTO_DA_LEI] Lei 13.303/2016 — Estatuto das Estatais
A Lei 13.303/2016 é o ESTATUTO JURÍDICO DAS ESTATAIS. Ela dispõe sobre as EMPRESAS PÚBLICAS (capital 100% público) e SOCIEDADES DE ECONOMIA MISTA (maioria das ações com voto sob controle público). Regula governança, licitações, contratos, conselho de administração, comitê de auditoria e transparência.""",
    ),
    Questao(
        pergunta="Qual o regime de licitação aplicável às empresas estatais segundo a Lei 13.303/2016?",
        keywords=["13.303", "licitação", "estatal", "contratação",
                   "regulamento próprio", "procedimento licitatório"],
        contexto_rag="""[TEXTO_DA_LEI] Lei 13.303/2016 — Licitações nas Estatais
As estatais devem realizar LICITAÇÃO PÚBLICA para contratos com terceiros (Art. 28). Elas próprias elaboram REGULAMENTO PRÓPRIO de licitações, aprovado pelo conselho de administração (Art. 29), observando os princípios da impessoalidade, moralidade, igualdade, publicidade, eficiência e probidade. O procedimento licitatório deve seguir este regulamento próprio.""",
    ),
    Questao(
        pergunta="Cite três princípios da administração pública previstos no caput do Art. 37 da CF.",
        keywords=["legalidade", "impessoalidade", "moralidade", "publicidade", "eficiência"],
    ),
    Questao(
        pergunta="O que é a transição energética e quais os principais desafios para o Brasil?",
        keywords=["transição energética", "descarbonização", "renovável",
                   "hidrogênio", "eólica", "solar", "biocombustível"],
    ),
    Questao(
        pergunta="Qual a diferença entre empresa pública e sociedade de economia mista?",
        keywords=["capital", "público", "privado", "maioria", "ações",
                   "integralmente", "sociedade de economia mista"],
        contexto_rag="""[TEXTO_DA_LEI] Lei 13.303/2016 — Diferença
EMPRESA PÚBLICA: capital INTEGRALMENTE PÚBLICO (100% do Estado).
SOCIEDADE DE ECONOMIA MISTA: capital com MAIORIA de ações com direito a voto sob CONTROLE PÚBLICO (admite capital PRIVADO minoritário).
Ambas têm personalidade jurídica de direito privado e criação autorizada por lei.""",
    ),
    Questao(
        pergunta="Explique o que é a Lei 9.478/1997 (Lei do Petróleo) e sua importância.",
        keywords=["9.478", "petróleo", "Agência Nacional", "ANP", "exploração",
                   "produção", "monopólio", "União", "concessão"],
        contexto_rag="""[TEXTO_DA_LEI] Lei 9.478/1997 — Lei do Petróleo
A Lei 9.478/1997 (LEI DO PETRÓLEO) instituiu a AGÊNCIA NACIONAL DO PETRÓLEO, GÁS NATURAL E BIOCOMBUSTÍVEIS (ANP), autarquia reguladora. Ela flexibilizou o MONOPÓLIO da UNIÃO, permitindo que a exploração e PRODUÇÃO de petróleo e gás sejam contratadas mediante CONCESSÃO, precedida de licitação. É a base do marco regulatório do setor de O&G no Brasil.""",
    ),
    Questao(
        pergunta="O que é o IC (Índice de Consistência) nos estudos?",
        keywords=["consistência", "frequência", "regularidade", "dias",
                   "semana", "média", "IC", "Índice de Consistência"],
        contexto_rag="""[CONTEXTO] Método de Estudos RTK
IC (ÍNDICE DE CONSISTÊNCIA) = dias com sessão de estudo na semana / 7.
Mede a REGULARIDADE/consistência do hábito de estudos, independentemente de horas.
Um IC alto indica estudo consistente ao longo da semana.
Fórmula: (dias com estudo na semana) / 7.""",
    ),
]


@dataclass
class Resultado:
    config: str
    acertos: int
    total_keywords: int
    tempo: float
    chars: int
    respostas: list[dict] = field(default_factory=list)


def _tem_gabarito(texto: str, questoes: list[Questao]) -> dict[str, bool]:
    resultados = {}
    texto_lower = texto.lower()
    for q in questoes:
        presentes = [kw for kw in q.keywords if kw.lower() in texto_lower]
        resultados[q.pergunta[:60]] = len(presentes) / len(q.keywords) if q.keywords else 1.0
    return resultados


def executar_benchmark(modelo: str, usar_rag: bool) -> Resultado:
    cliente = LocalLLM(model=modelo, timeout=180)
    config = f"{modelo} {'+RAG' if usar_rag else 'sem RAG'}"

    few_shot = """Exemplos de respostas esperadas:

P: O que é a Lei 13.303/2016 e qual seu principal objeto?
R: Lei 13.303/2016 é o Estatuto Jurídico das Estatais (empresas públicas e sociedades de economia mista). Seu principal objeto é regulamentar a exploração de atividade econômica pelo Estado, estabelecendo regras de governança, licitações e contratos.

P: Cite três princípios da administração pública previstos no caput do Art. 37 da CF.
R: Os princípios são: legalidade, impessoalidade, moralidade, publicidade e eficiência (LIMPE). Qualquer três dos cinco está correto.

P: Qual a diferença entre empresa pública e sociedade de economia mista?
R: Empresa pública tem capital integralmente público (100% do Estado). Sociedade de economia mista tem maioria de ações com direito a voto sob controle público, podendo ter capital privado minoritário."""

    system = (
        "Você é um especialista em concursos CESGRANRIO/Petrobras. "
        "Responda de forma direta, objetiva e técnica. "
        "Se houver [TEXTO_DA_LEI], use-o como fonte primária e cite artigos específicos. "
        "Máximo de 8 linhas por resposta.\n\n"
        "IMPORTANTE — NUNCA invente leis, artigos, datas ou fatos. "
        "Se NÃO tiver certeza, escreva apenas: 'Não tenho essa informação com precisão.' "
        "É melhor dizer que não sabe do que inventar. "
        "Alucinações (informações falsas) são inaceitáveis neste contexto."
        f"\n\n{few_shot}"
    )
    if not usar_rag:
        system += (
            "\n\nVOCÊ NÃO TEM ACESSO AOS TEXTOS DE LEI. "
            "Responda apenas com seu conhecimento prévio. "
            "Se não souber com exatidão, diga 'Não sei com precisão' — não invente."
        )

    acertos_total = 0
    total_kw = 0
    todas_respostas: list[dict] = []

    inicio = time.time()
    chars_total = 0

    for i, q in enumerate(BENCHMARK, 1):
        prompt = f"Pergunta {i}/{len(BENCHMARK)}: {q.pergunta}"
        if usar_rag and q.contexto_rag:
            prompt = f"{q.contexto_rag}\n\nPergunta: {q.pergunta}"

        t0 = time.time()
        prompt_final = (
            f"{prompt}\n\n"
            "INSTRUÇÃO: Responda de forma completa, incluindo os principais termos técnicos, "
            "números de leis, artigos e conceitos. Use vocabulário preciso da área."
        )
        try:
            resposta = cliente.chat(system=system, messages=[{"role": "user", "content": prompt_final}], max_tokens=1536)
        except Exception as e:
            resposta = f"[ERRO: {e}]"
        t1 = time.time()

        chars_total += len(resposta)
        acertos_q = sum(1 for kw in q.keywords if kw.lower() in resposta.lower())
        total_kw += len(q.keywords)
        acertos_total += acertos_q

        todas_respostas.append({
            "pergunta": q.pergunta,
            "resposta": resposta[:300],
            "tempo": round(t1 - t0, 1),
            "keywords": len(q.keywords),
            "acertos": acertos_q,
            "score": round(acertos_q / len(q.keywords) * 100) if q.keywords else 0,
        })
        sys.stdout.write(f"  [{i}/{len(BENCHMARK)}] {config}: {todas_respostas[-1]['score']}% ({acertos_q}/{len(q.keywords)} kw) em {t1-t0:.1f}s\n")
        sys.stdout.flush()

    tempo_total = time.time() - inicio
    return Resultado(
        config=config,
        acertos=acertos_total,
        total_keywords=total_kw,
        tempo=round(tempo_total, 1),
        chars=chars_total,
        respostas=todas_respostas,
    )


def gerar_markdown(resultados: list[Resultado]) -> str:
    hoje = date.today().isoformat()
    linhas = [
        "# Benchmark de Qualidade — Automatizado",
        f"**Data:** {hoje}",
        f"**Perguntas:** {len(BENCHMARK)}",
        f"**Total de keywords:** {sum(len(q.keywords) for q in BENCHMARK)}",
        "",
        "## Sumário",
        "",
    ]

    for r in resultados:
        pct = round(r.acertos / r.total_keywords * 100) if r.total_keywords else 0
        tok_s = round(r.chars / r.tempo, 1) if r.tempo > 0 else 0
        linhas.append(f"- **{r.config}**: `{pct}%` acerto keywords · {r.tempo}s · {r.chars} chars ({tok_s} char/s)")

    linhas += ["", "## Detalhes por configuração", ""]

    for r in resultados:
        pct = round(r.acertos / r.total_keywords * 100) if r.total_keywords else 0
        linhas += [
            f"### {r.config}",
            f"- **Score:** {pct}% ({r.acertos}/{r.total_keywords} keywords)",
            f"- **Tempo total:** {r.tempo}s",
            f"- **Chars:** {r.chars}",
            "",
        ]
        for resp in r.respostas:
            linhas += [
                f"**P:** {resp['pergunta']}",
                f"**Score:** {resp['score']}% ({resp['acertos']}/{resp['keywords']} kw) · {resp['tempo']}s",
                f"**R:** {resp['resposta']}",
                "",
            ]

    linhas += [
        "## Metodologia",
        "",
        f"- {len(BENCHMARK)} perguntas sobre legislação Petrobras, CF, transição energética",
        "- Cada pergunta tem keywords esperadas (n-gramas)",
        "- Score = proporção de keywords encontradas na resposta (case-insensitive)",
        "- RAG injeta `[TEXTO_DA_LEI]` com artigos reais no prompt",
        "- Modelo: timeout 180s, max_tokens 1024",
        "",
    ]
    return "\n".join(linhas)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark de qualidade LLM")
    parser.add_argument("--model", default="qwen2.5:1.5b", help="Modelo a testar (default: qwen2.5:1.5b)")
    parser.add_argument("--output", help="Arquivo de saída .md (opcional)")
    parser.add_argument("--skip-no-rag", action="store_true", help="Pula teste sem RAG")
    parser.add_argument("--skip-rag", action="store_true", help="Pula teste com RAG")
    args = parser.parse_args()

    resultados: list[Resultado] = []

    if not args.skip_no_rag:
        print(f"\n▶ Rodando benchmark: {args.model} sem RAG")
        resultados.append(executar_benchmark(args.model, usar_rag=False))

    if not args.skip_rag:
        print(f"\n▶ Rodando benchmark: {args.model} com RAG")
        resultados.append(executar_benchmark(args.model, usar_rag=True))

    report = gerar_markdown(resultados)
    print("\n" + "=" * 60)
    print(report)

    if args.output:
        out = Path(args.output)
        out.write_text(report, encoding="utf-8")
        print(f"\n✓ Relatório salvo em {out}")

    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO:")
    for r in resultados:
        pct = round(r.acertos / r.total_keywords * 100) if r.total_keywords else 0
        print(f"  {r.config:30s} {pct:3d}%  {r.tempo:6.1f}s  {r.chars:5d} chars")


if __name__ == "__main__":
    main()
