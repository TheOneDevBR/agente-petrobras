#!/usr/bin/env python3
"""Benchmark automático de qualidade — compara respostas do LLM com/sem RAG.

Uso:
    python cli_python/benchmark_qualidade.py
    python cli_python/benchmark_qualidade.py --model qwen2.5:7b
    python cli_python/benchmark_qualidade.py --output docs/benchmark_resultados.md

Requer LLM local rodando (Ollama).
"""

from __future__ import annotations

import os
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
        keywords=["13.303", "estatal", "empresa pública", "sociedade de economia mista",
                   "estatuto jurídico"],
        contexto_rag="""[TEXTO_DA_LEI] Lei 13.303/2016 — Estatuto das Estatais
Art. 1º Esta Lei dispõe sobre o estatuto jurídico da empresa pública,
da sociedade de economia mista e de suas subsidiárias, no âmbito da União,
dos Estados, do Distrito Federal e dos Municípios.
Art. 2º A exploração de atividade econômica pelo Estado será exercida
por meio de empresa pública e de sociedade de economia mista.
Art. 3º A empresa pública e a sociedade de economia mista não poderão
gozar de privilégios fiscais não extensivos às do setor privado.""",
    ),
    Questao(
        pergunta="Qual o regime de licitação aplicável às empresas estatais segundo a Lei 13.303/2016?",
        keywords=["13.303", "licitação", "estatal", "contratação",
                   "regulamento próprio", "procedimento licitatório"],
        contexto_rag="""[TEXTO_DA_LEI] Lei 13.303/2016 — Licitações nas Estatais
Art. 28º Os contratos com terceiros destinados à prestação de serviços
às empresas públicas e às sociedades de economia mista serão precedidos
de licitação pública, ressalvadas as hipóteses previstas nesta Lei.
Art. 29º É a empresa pública e a sociedade de economia mista quem
elabora o regulamento de licitações e contratos, aprovado pelo conselho
de administração, que deve observar os princípios da impessoalidade,
moralidade, igualdade, publicidade, eficiência, probidade administrativa.""",
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
                   "integralmente", "controle acionário"],
        contexto_rag="""[TEXTO_DA_LEI] Lei 13.303/2016 — Conceitos
Art. 3º Empresa pública é a entidade dotada de personalidade jurídica
de direito privado, com criação autorizada por lei e com patrimônio
próprio, cujo capital social é integralmente detido pela União, pelos
Estados, pelo Distrito Federal ou pelos Municípios.
Art. 4º Sociedade de economia mista é a entidade dotada de personalidade
jurídica de direito privado, com criação autorizada por lei, sob a forma
de sociedade anônima, cujas ações com direito a voto pertençam em sua
maioria à União, aos Estados, ao Distrito Federal ou aos Municípios.""",
    ),
    Questao(
        pergunta="Explique o que é a Lei 9.478/1997 (Lei do Petróleo) e sua importância.",
        keywords=["9.478", "petróleo", "Agência Nacional", "ANP", "exploração",
                   "produção", "monopólio", "União", "concessão"],
        contexto_rag="""[TEXTO_DA_LEI] Lei 9.478/1997 — Lei do Petróleo
Art. 1º As políticas nacionais para o aproveitamento das fontes de
energia visarão aos seguintes objetivos: preservar o interesse nacional,
promover o desenvolvimento, ampliar o mercado de trabalho, e valorizar
os recursos energéticos.
Art. 5º Fica instituída a Agência Nacional do Petróleo, Gás Natural e
Biocombustíveis (ANP), autarquia sob regime especial, vinculada ao
Ministério de Minas e Energia.
Art. 26º A União poderá contratar a exploração e a produção de petróleo
e gás natural mediante contratos de concessão, precedidos de licitação.""",
    ),
    Questao(
        pergunta="O que é o IC (Índice de Consistência) nos estudos?",
        keywords=["consistência", "frequência", "regularidade", "dias",
                   "semana", "média", "IC"],
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

    system = (
        "Você é um especialista em concursos CESGRANRIO/Petrobras. "
        "Responda de forma direta, objetiva e técnica. "
        "Se houver [TEXTO_DA_LEI], use-o como fonte primária. "
        "Máximo de 5 linhas por resposta."
    )
    if not usar_rag:
        system += " Não invente leis ou artigos — se não souber, diga que não sabe."

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
        try:
            resposta = cliente.chat(system=system, messages=[{"role": "user", "content": prompt}], max_tokens=1024)
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
