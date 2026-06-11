"""Módulo de treino — simulados estilo CESGRANRIO.

Funcionalidades:
  - Banco de questões curadas (~25) com gabarito e explicação
  - Geração de questões via LLM (tópicos aleatórios)
  - Modo cronometrado (opcional)
  - Correção automática com análise de desempenho
  - Persistência em dados/simulados.json

Uso:
    from treino import iniciar_simulado, corrigir_simulado
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

AQUI = Path(__file__).resolve().parent
DADOS = AQUI / "dados"
SIMULADOS_PATH = DADOS / "simulados.json"


@dataclass
class QuestaoMC:
    pergunta: str
    opcoes: list[str]
    correta: int
    explicacao: str
    disciplina: str = ""
    tags: list[str] = field(default_factory=list)


def _q(pergunta: str, opcoes: list[str], correta: int, explicacao: str, disciplina: str = "", tags: list[str] | None = None) -> QuestaoMC:
    return QuestaoMC(pergunta=pergunta, opcoes=opcoes, correta=correta, explicacao=explicacao, disciplina=disciplina, tags=tags or [])


BANCO_QUESTOES: list[QuestaoMC] = [
    _q(
        "Nos termos da Lei 13.303/2016, assinale a alternativa correta sobre as empresas públicas e sociedades de economia mista:",
        ["Ambas têm capital integralmente público.",
         "A empresa pública tem capital integralmente público; a sociedade de economia mista, maioria de ações com direito a voto sob controle público.",
         "Ambas podem ter capital majoritariamente privado.",
         "A sociedade de economia mista tem capital integralmente público.",
         "Empresa pública é sinônimo de sociedade de economia mista."],
        1,
        "Art. 3º e 4º da Lei 13.303/2016: empresa pública tem capital 100% público; sociedade de economia mista tem maioria de ações com voto sob controle público.",
        "Legislação", ["13303"]
    ),
    _q(
        "Segundo a Lei 13.303/2016, a licitação nas empresas estatais:",
        ["Dispensa licitação em qualquer contratação.",
         "Deve seguir a Lei 8.666/1993 exclusivamente.",
         "É precedida de licitação pública, ressalvadas as hipóteses legais, com regulamento próprio aprovado pelo conselho de administração.",
         "Pode ser substituída por pregão eletrônico em todos os casos.",
         "Deve ser dispensada para contratos de qualquer valor."],
        2,
        "Art. 28º (licitação obrigatória) e Art. 29º (regulamento próprio aprovado pelo conselho de administração).",
        "Legislação", ["13303"]
    ),
    _q(
        "Constitui princípio da administração pública expresso no caput do Art. 37 da CF/88:",
        ["Eficiência.",
         "Proporcionalidade.",
         "Razoabilidade.",
         "Supremacia do interesse público.",
         "Contraditório."],
        0,
        "O caput do Art. 37 traz: legalidade, impessoalidade, moralidade, publicidade e eficiência.",
        "Português", ["cf"]
    ),
    _q(
        "A Lei 9.478/1997 instituiu:",
        ["A Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP).",
         "A Petrobras como empresa pública.",
         "O monopólio da União sobre o petróleo.",
         "A obrigatoriedade de contratação direta pela Petrobras.",
         "O fim das concessões de exploração de petróleo."],
        0,
        "Art. 5º da Lei 9.478/1997 cria a ANP, autarquia sob regime especial.",
        "Legislação", ["9478"]
    ),
    _q(
        "Em 'Fazia anos que não via aquele amigo', a oração subordinada é:",
        ["Subordinada adverbial temporal.",
         "Subordinada substantiva subjetiva.",
         "Subordinada adjetiva explicativa.",
         "Subordinada adverbial causal.",
         "Coordenada sindética."],
        0,
        "'que não via aquele amigo' é oração subordinada adverbial temporal, pois exprime tempo.",
        "Português", ["sintaxe"]
    ),
    _q(
        "Assinale a alternativa em que a crase é obrigatória:",
        ["Entreguei o relatório à ele.",
         "Fui à casa de praia no fim de semana.",
         "Não me refiro àquela situação.",
         "Pagarei à vista o valor devido.",
         "Chegamos à noite do evento."],
        2,
        "Crase obrigatória antes de 'aquela' (a + aquela = àquela).",
        "Português", ["crase"]
    ),
    _q(
        "Uma proposição equivalente a 'Se Pedro é engenheiro, então passou no concurso' é:",
        ["Pedro não é engenheiro ou passou no concurso.",
         "Se Pedro passou no concurso, então é engenheiro.",
         "Pedro é engenheiro e passou no concurso.",
         "Se Pedro não passou no concurso, então é engenheiro.",
         "Pedro não é engenheiro e não passou no concurso."],
        0,
        "Equivalência lógica: p → q ≡ ¬p ∨ q (contrapositiva ou eliminação da condicional).",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Se todos os engenheiros da Petrobras são concursados e alguns concursados são da CESGRANRIO, podemos concluir que:",
        ["Todos os engenheiros da Petrobras são da CESGRANRIO.",
         "Nenhum engenheiro da Petrobras é da CESGRANRIO.",
         "É possível que algum engenheiro da Petrobras seja da CESGRANRIO.",
         "Todos os concursados são engenheiros da Petrobras.",
         "Nenhum concursado é engenheiro da Petrobras."],
        2,
        "Não há relação direta entre os conjuntos — apenas possibilidade, não certeza.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "O IC (Índice de Consistência) mede:",
        ["A quantidade de horas estudadas por dia.",
         "A regularidade dos estudos — proporção de dias com estudo na semana.",
         "O número de questões resolvidas por mês.",
         "A nota projetada para o concurso.",
         "O percentual de acertos nas questões."],
        1,
        "IC = nº de dias com sessão em uma semana / 7. Mede regularidade.",
        "Métricas", ["ic"]
    ),
    _q(
        "A transição energética para uma economia de baixo carbono inclui:",
        ["Aumento da exploração de carvão mineral.",
         "Substituição de fontes fósseis por renováveis como eólica, solar e hidrogênio verde.",
         "Redução da participação de biocombustíveis na matriz.",
         "Eliminação do petróleo como fonte de energia até 2030.",
         "Foco exclusivo em energia nuclear."],
        1,
        "Transição energética visa descarbonização através de renováveis, eficiência e novas tecnologias.",
        "Atualidades", ["energia"]
    ),
    _q(
        "O regime de contratação de pessoal pelas empresas estatais, segundo a Lei 13.303/2016, é:",
        ["CLT, com exigência de concurso público.",
         "Estatutário, sem necessidade de concurso.",
         "CLT, sem concurso, por livre nomeação.",
         "Estatutário, com concurso público obrigatório.",
         "Contrato temporário sem concurso."],
        0,
        "Art. 17 da Lei 13.303: as estatais contratam sob regime CLT, com concurso público obrigatório.",
        "Legislação", ["13303"]
    ),
    _q(
        "Em 'O gerente da Petrobras, que era muito competente, foi promovido', a vírgula é usada para:",
        ["Separar aposto explicativo.",
         "Isolar oração subordinada adjetiva explicativa.",
         "Marcar elipse do verbo.",
         "Separar adjunto adverbial deslocado.",
         "Indicar zeugma."],
        1,
        "'que era muito competente' é oração adjetiva explicativa, isolada por vírgulas.",
        "Português", ["pontuacao"]
    ),
    _q(
        "Qual das seguintes NÃO é uma fonte de energia renovável?",
        ["Solar",
         "Eólica",
         "Gás natural",
         "Biomassa",
         "Hidrelétrica"],
        2,
        "Gás natural é combustível fóssil não renovável.",
        "Atualidades", ["energia"]
    ),
    _q(
        "A Petrobras foi criada pela Lei 2.004/1953 sob o governo de:",
        ["Juscelino Kubitschek",
         "Getúlio Vargas",
         "João Goulart",
         "Castelo Branco",
         "Eurico Gaspar Dutra"],
        1,
        "Lei 2.004/1953, sancionada por Getúlio Vargas, criou a Petrobras.",
        "Legislação", ["petrobras"]
    ),
    _q(
        "A proposição 'p ∧ q' é verdadeira quando:",
        ["Apenas p é verdadeira.",
         "Apenas q é verdadeira.",
         "Ambas p e q são verdadeiras.",
         "Pelo menos uma é verdadeira.",
         "Nenhuma é verdadeira."],
        2,
        "Conjunção (∧) é verdadeira apenas quando ambos os operandos são verdadeiros.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "O Decreto 8.945/2016 regulamenta:",
        ["O regime de previdência dos empregados públicos.",
         "A Lei 13.303/2016, dispondo sobre procedimentos licitatórios e contratos das estatais.",
         "A exploração de petróleo no pré-sal.",
         "O Código de Ética da Administração Pública.",
         "A estrutura da ANP."],
        1,
        "Decreto 8.945/2016 regulamenta a Lei 13.303/2016 no âmbito da União.",
        "Legislação", ["8945"]
    ),
    _q(
        "A CESGRANRIO, banca organizadora dos concursos Petrobras, é:",
        ["Uma empresa privada de direito público.",
         "Uma fundação de direito privado sem fins lucrativos.",
         "Uma autarquia federal.",
         "Uma sociedade de economia mista.",
         "Uma empresa pública municipal."],
        1,
        "CESGRANRIO é fundação de direito privado, sem fins lucrativos.",
        "Legislação", ["banca"]
    ),
    _q(
        "A expressão 'haja vista' em 'Haja vista os resultados obtidos' é:",
        ["Verbo na 3ª pessoa do singular com sentido de 'veja'.",
         "Locução prepositiva invariável com sentido de 'devido a'.",
         "Substantivo composto.",
         "Advérbio de modo.",
         "Conjunção subordinativa causal."],
        1,
        "'Haja vista' é locução prepositiva invariável = 'devido a', 'considerando'.",
        "Português", ["expressoes"]
    ),
    _q(
        "Segundo a Lei 13.303/2016, a função de ouvidor nas estatais:",
        ["É facultativa e pode ser acumulada com a presidência.",
         "É obrigatória e o ouvidor tem mandato de 3 anos, vedada a recondução.",
         "É exercida pelo presidente do conselho de administração.",
         "Não está prevista na Lei 13.303.",
         "É temporária e nomeada pelo governador."],
        1,
        "Art. 14: a estatal deve ter ouvidor com mandato de 3 anos, vedada recondução.",
        "Legislação", ["13303"]
    ),
    _q(
        "O pré-sal brasileiro está localizado principalmente na bacia de:",
        ["Santos",
         "Campos",
         "Espírito Santo",
         "Potiguar",
         "Recôncavo"],
        0,
        "O pré-sal se estende do litoral de SC ao ES, com maior volume na Bacia de Santos.",
        "Atualidades", ["energia"]
    ),
    _q(
        "Em 'Precisa-se de engenheiros', o termo 'de engenheiros' é:",
        ["Objeto direto.",
         "Objeto indireto.",
         "Sujeito paciente.",
         "Complemento nominal.",
         "Adjunto adverbial."],
        1,
        "'Precisa-se' com partícula 'se' (índice de indeterminação do sujeito) exige objeto indireto com 'de'.",
        "Português", ["sintaxe"]
    ),
    _q(
        "O contrato de concessão para exploração de petróleo, segundo a Lei 9.478/1997, é precedido de:",
        ["Autorização do Congresso Nacional.",
         "Licitação na modalidade concorrência.",
         "Decreto presidencial sem licitação.",
         "Contrato direto com a Petrobras.",
         "Acordo internacional."],
        1,
        "Art. 26: a União contrata exploração e produção de petróleo mediante concessão precedida de licitação (concorrência).",
        "Legislação", ["9478"]
    ),
    _q(
        "A função social da empresa estatal, segundo a Lei 13.303/2016, inclui:",
        ["Maximização exclusiva do lucro dos acionistas.",
         "Geração de emprego como único objetivo.",
         "Alinhamento com políticas públicas e desenvolvimento sustentável, sem prejuízo da eficiência econômica.",
         "Distribuição de dividendos independentemente de resultados.",
         "Atuação exclusiva em monopólios naturais."],
        2,
        "Art. 27: a estatal deve alinhar-se a políticas públicas, com eficiência e sustentabilidade.",
        "Legislação", ["13303"]
    ),
    _q(
        "Se 3 engenheiros da Petrobras realizam uma inspeção em 8 horas, quanto tempo levariam 4 engenheiros para realizar a mesma inspeção (mesmo ritmo)?",
        ["6 horas",
         "10 horas",
         "4 horas",
         "8 horas",
         "12 horas"],
        0,
        "Grandezas inversamente proporcionais: 3×8 = 4×t → t = 6 horas.",
        "Raciocínio Lógico", ["rl"]
    ),
]


def carregar_simulados() -> list[dict]:
    if SIMULADOS_PATH.exists():
        import json
        try:
            return json.loads(SIMULADOS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def salvar_simulado(registro: dict) -> None:
    simulados = carregar_simulados()
    simulados.append(registro)
    DADOS.mkdir(parents=True, exist_ok=True)
    import json
    SIMULADOS_PATH.write_text(json.dumps(simulados, ensure_ascii=False, indent=2), encoding="utf-8")


def selecionar_questoes(n: int = 5, disciplina: str = "", tags: list[str] | None = None) -> list[QuestaoMC]:
    """Seleciona n questões do banco, filtradas por disciplina/tags."""
    pool = BANCO_QUESTOES
    if disciplina:
        pool = [q for q in pool if q.disciplina.lower() == disciplina.lower()]
    if tags:
        pool = [q for q in pool if any(t in q.tags for t in tags)]
    if len(pool) > n:
        pool = random.sample(pool, n)
    return pool


def iniciar_simulado(n_questoes: int = 5, cronometro: int = 0, disciplina: str = "") -> dict[str, Any]:
    """Executa um simulado interativo via terminal.

    Args:
        n_questoes: Número de questões.
        cronometro: Limite de minutos (0 = sem limite).
        disciplina: Filtrar por disciplina.

    Returns:
        Dict com resultados do simulado.
    """
    questoes = selecionar_questoes(n_questoes, disciplina=disciplina)
    if not questoes:
        return {"erro": "Nenhuma questão disponível para o filtro informado."}

    print("\n" + "═" * 64)
    print("  SIMULADO CESGRANRIO")
    if cronometro:
        print(f"  Tempo limite: {cronometro} minuto(s)")
    print("═" * 64)

    respostas: list[dict] = []
    acertos = 0
    tempo_inicio = time.time()
    tempo_limite = cronometro * 60 if cronometro > 0 else float("inf")

    for i, q in enumerate(questoes, 1):
        print(f"\n--- Questão {i}/{len(questoes)} ---")
        if q.disciplina:
            print(f"[{q.disciplina}]")
        print(q.pergunta)
        print()
        for j, op in enumerate(q.opcoes):
            print(f"  {j}) {op}")

        decorrido = time.time() - tempo_inicio
        restante = tempo_limite - decorrido
        if restante <= 0 and cronometro > 0:
            print("\n⏰ Tempo esgotado!")
            break

        while True:
            try:
                raw = input(f"\nSua resposta (0-{len(q.opcoes)-1}, Enter=0): ").strip()
                if not raw:
                    raw = "0"
                escolha = int(raw)
                if 0 <= escolha < len(q.opcoes):
                    break
                print(f"Digite um número entre 0 e {len(q.opcoes)-1}.")
            except ValueError:
                print("Digite um número válido.")

        correta = escolha == q.correta
        if correta:
            acertos += 1
            print("  ✅ Correto!")
        else:
            print(f"  ❌ Incorreto. Resposta correta: {q.correta}) {q.opcoes[q.correta]}")

        print(f"  📖 {q.explicacao}")
        respostas.append({
            "pergunta": q.pergunta,
            "opcoes": q.opcoes,
            "escolha": escolha,
            "correta_idx": q.correta,
            "acertou": correta,
            "explicacao": q.explicacao,
            "disciplina": q.disciplina,
        })

    tempo_total = round(time.time() - tempo_inicio, 1)
    pct = round(acertos / len(respostas) * 100, 1) if respostas else 0

    resultado = {
        "data": date.today().isoformat(),
        "questoes": len(respostas),
        "acertos": acertos,
        "pct": pct,
        "tempo_seg": tempo_total,
        "disciplina": disciplina or "geral",
        "respostas": respostas,
    }

    salvar_simulado(resultado)

    print("\n" + "═" * 64)
    print(f"  RESULTADO: {acertos}/{len(respostas)} ({pct}%) em {tempo_total}s")
    print("═" * 64)

    return resultado


def resumo_para_prompt(ultimos: int = 3) -> str:
    """Resumo dos últimos simulados para injetar no prompt do agente."""
    simulados = carregar_simulados()
    if not simulados:
        return ""
    recentes = simulados[-ultimos:]
    linhas = ["SIMULADOS RECENTES:"]
    for s in recentes:
        pct = s.get("pct", 0)
        face = "✅" if pct >= 70 else ("🟡" if pct >= 50 else "❌")
        linhas.append(
            f"  {face} {s['data']} — {s['disciplina']}: {s['acertos']}/{s['questoes']} ({pct}%)"
        )
    return "\n".join(linhas)


def desempenho_por_disciplina() -> dict[str, float]:
    """Média de acertos por disciplina."""
    simulados = carregar_simulados()
    disc: dict[str, list[float]] = {}
    for s in simulados:
        d = s.get("disciplina", "geral")
        disc.setdefault(d, []).append(s["pct"])
    return {d: round(sum(v) / len(v), 1) for d, v in disc.items()}
