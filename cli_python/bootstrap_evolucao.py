"""Bootstrap do sistema de autoevolução.

Popula o diário de decisões e outcomes, auto-avaliações e primeiro
experimento A/B com dados derivados das sessões existentes.

Uso:
    python bootstrap_evolucao.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auto_avaliacao import AutoAvaliador
from estrategia_ab import GerenciadorAB
from evolucao import DiarioEvolucao
from prompt_evoluivel import PromptEvoluivel

# ── 1. Popular diário de decisões + outcomes ─────────────────────────

print("🧬 [1/4] Populando diário de decisões e outcomes...")
diario = DiarioEvolucao()

# Decisões com outcomes reais (mapeiam as sessões)
decisoes_outcomes = [
    # (estrategia, disciplina, acerto_base, prescricao, acerto_outcome, questoes)
    ("retrieval_practice", "portugues", 55.0,
     "20min Retrieval Practice com questões CESGRANRIO de interpretação", 65.0, 20),
    ("retrieval_practice", "portugues", 62.0,
     "25min Retrieval Practice foco em crase e regência", 64.0, 25),
    ("retrieval_practice", "portugues", 64.0,
     "20min Retrieval Practice com gabarito comentado", 65.0, 20),
    ("sq3r", "legislacao", 40.0,
     "60min SQ3R na Lei 13.303/2016 arts. 1-30", 50.0, 20),
    ("sq3r", "legislacao", 50.0,
     "75min SQ3R + questões Lei das Estatais CESGRANRIO", 56.0, 25),
    ("pratica_deliberada", "legislacao", 48.0,
     "60min prática deliberada em questões de LGPD", 55.0, 20),
    ("intercalacao", "raciocinio_logico", 46.7,
     "60min intercalação lógica + probabilidade + combinatória", 60.0, 20),
    ("intercalacao", "raciocinio_logico", 55.0,
     "50min intercalação raciocínio lógico CESGRANRIO", 55.0, 20),
    ("pratica_deliberada", "engenharia_petroleo", 66.7,
     "90min prática deliberada reservatórios + perfuração", 75.0, 20),
    ("pratica_deliberada", "engenharia_petroleo", 71.0,
     "90min prática deliberada completação e teste de poço", 70.0, 20),
    ("feynman", "geologia", 58.0,
     "75min método Feynman para estratigrafia e sedimentologia", 60.0, 15),
    ("feynman", "geologia", 60.0,
     "60min Feynman geologia estrutural + bacia sedimentar", 53.3, 15),
    ("leitura_ativa", "ingles", 75.0,
     "30min leitura ativa artigos SPE em inglês", 80.0, 10),
]

for estr, disc, base, presc, outcome, q in decisoes_outcomes:
    diario.registrar_decisao(estr, disc, base, presc, fase="DOMINIO")
    diario.registrar_outcome(disc, outcome, q)

print(f"   ✓ {len(decisoes_outcomes)} decisões com outcomes registradas")
stats = diario.estatisticas()
print(f"   ✓ Eficácia global: {stats['eficacia_global']:.0%}")
print(f"   ✓ Top estratégia: {stats['top_estrategia']}")
ranking = diario.ranking_estrategias(5)
for r in ranking:
    print(f"     • {r['estrategia']}: {r['eficacia_media']:.0%} ({r['usos']} usos)")

# ── 2. Popular auto-avaliações ───────────────────────────────────────

print("\n🧬 [2/4] Populando auto-avaliações...")
avaliador = AutoAvaliador()

respostas_simuladas = [
    # Respostas de qualidade variada para criar tendência
    ("Estude o art. 13 da Lei 13.303/2016 por 25min, Retrieval Practice. "
     "Meta: acerto ≥ 70% em 15 questões CESGRANRIO. (Roediger & Karpicke 2006). "
     "→ Agora: abra Q32–Q38 e resolva em 20min.",
     False),
    ("Faça 20 questões de Português CESGRANRIO, foco em interpretação textual. "
     "Use SQ3R: leia o enunciado 2x antes de marcar. Meta: 70% de acerto. "
     "→ Agora: QConcursos > CESGRANRIO > Português > 20 questões.",
     False),
    ("Revise a LGPD art. 7 (bases legais de tratamento) por 30min. "
     "Prática deliberada: resolva 10 questões focando em 'consentimento vs. legítimo interesse'. "
     "Meta: errar ≤ 2. → Comece agora pelo Tec Concursos.",
     False),
    ("Continue estudando legislação. Leia a lei com calma.",
     False),
    ("Estude mais raciocínio lógico. Tente se dedicar.",
     False),
    ("Faça 15 questões de Engenharia de Petróleo (perfuração e completação), "
     "45min com Prática Deliberada. Meta: ≥ 80%. Classifique erros [C/A/B/T]. "
     "Fonte: simulados CESGRANRIO 2024. → Abra o QConcursos agora.",
     False),
    ("Use intercalação: 20min lógica proposicional + 20min probabilidade + 20min combinatória. "
     "15 questões de cada. Meta: ≥ 60% global. (Bjork & Bjork 2011). "
     "→ Monte o caderno no Tec Concursos com 3 temas.",
     False),
    ("Revise Geologia do Petróleo usando método Feynman: explique bacias sedimentares "
     "como se fosse para alguém leigo, sem consulta. 45min. Depois 10 questões. "
     "Meta: explicação fluente + ≥ 65% nas questões.",
     False),
]

for texto, is_diag in respostas_simuladas:
    avaliador.avaliar_resposta(texto, is_diagnostico=is_diag)

sa = avaliador.estatisticas()
print(f"   ✓ {sa['total']} avaliações registradas")
print(f"   ✓ Score médio: {sa['score_medio']}/100")
print(f"   ✓ Tendência: {sa['tendencia']}")

# ── 3. Criar primeiro experimento A/B ────────────────────────────────

print("\n🧬 [3/4] Criando primeiro experimento A/B...")
ab = GerenciadorAB()

if not ab.experimentos_ativos():
    exp_id = ab.criar_experimento(
        estrategia_a="retrieval_practice",
        estrategia_b="sq3r",
        condicao="disciplinas com acerto < 60% (Legislação, RL)",
        hipotese="Retrieval Practice > SQ3R para disciplinas fracas na fase DOMÍNIO",
    )
    print(f"   ✓ Experimento criado: {exp_id}")
    print("   ✓ Hipótese: Retrieval Practice > SQ3R para disciplinas fracas")
else:
    print("   → Experimento ativo já existe, pulando")

# ── 4. Inicializar overlays ──────────────────────────────────────────

print("\n🧬 [4/4] Inicializando overlays do prompt...")
pe = PromptEvoluivel()
stats_pe = pe.estatisticas()
print(f"   ✓ {len(stats_pe['overlays'])} overlays inicializados")
for nome, v in stats_pe['overlays'].items():
    print(f"     • {nome}: v{v}")

# ── Resumo final ─────────────────────────────────────────────────────

print("\n" + "═" * 60)
print("  🧬 BOOTSTRAP COMPLETO")
print("═" * 60)
print(f"  Decisões: {stats['total_decisoes']} ({stats['com_outcome']} com outcome)")
print(f"  Eficácia global: {stats['eficacia_global']:.0%}")
print(f"  Auto-avaliações: {sa['total']} (score médio: {sa['score_medio']})")
print(f"  Experimentos A/B: {len(ab.experimentos_ativos())} ativo(s)")
print(f"  Overlays: {len(stats_pe['overlays'])} inicializados")
print("═" * 60)
print("\n  Próximo passo: rode 'python agente.py' e use /evolucao para ver o painel.")
