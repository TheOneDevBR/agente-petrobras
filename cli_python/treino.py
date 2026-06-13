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
    # ── Novas questões ────────────────────────────────────────────────────────
    _q(
        "Em uma planilha do Excel, a fórmula =SOMA(A1:A4) equivale a:",
        ["A1+A2+A3+A4",
         "A1*A2*A3*A4",
         "MÉDIA(A1:A4)",
         "CONT.VALORES(A1:A4)",
         "MÁXIMO(A1:A4)"],
        0,
        "SOMA(A1:A4) retorna a soma dos valores no intervalo de A1 a A4.",
        "Informática", ["excel"]
    ),
    _q(
        "No Windows 10, o atalho para abrir o Gerenciador de Tarefas é:",
        ["Ctrl+Shift+Esc",
         "Ctrl+Alt+Del",
         "Alt+F4",
         "Win+R",
         "Ctrl+Esc"],
        0,
        "Ctrl+Shift+Esc abre diretamente o Gerenciador de Tarefas; Ctrl+Alt+Del abre a tela de segurança.",
        "Informática", ["windows"]
    ),
    _q(
        "Qual equipamento de rede é responsável por interligar redes diferentes e encaminhar pacotes com base no endereço IP?",
        ["Switch",
         "Roteador",
         "Hub",
         "Modem",
         "Access Point"],
        1,
        "O roteador opera na camada 3 (rede) e encaminha pacotes IP entre redes distintas.",
        "Informática", ["redes"]
    ),
    _q(
        "No Word, a formatação que aplica efeito de relevo ao texto é:",
        ["Negrito",
         "Itálico",
         "Sublinhado",
         "Tachado",
         "Sombra"],
        4,
        "Sombra é um efeito de formatação de fonte que adiciona profundidade ao texto.",
        "Informática", ["word"]
    ),
    _q(
        "Assinale a alternativa que apresenta um software de navegação na web:",
        ["Microsoft Edge",
         "Microsoft Word",
         "Windows Explorer",
         "Outlook Express",
         "PowerPoint"],
        0,
        "Microsoft Edge é um navegador web; os demais são editor de texto, gerenciador de arquivos, e-mail e apresentações.",
        "Informática", ["navegador"]
    ),
    _q(
        "No Excel, a função que retorna o maior valor de um intervalo é:",
        ["MÁXIMO",
         "MAIOR",
         "MÍNIMO",
         "SOMA",
         "MÉDIA"],
        0,
        "MÁXIMO(intervalo) retorna o maior valor numérico do intervalo.",
        "Informática", ["excel"]
    ),
    _q(
        "O protocolo utilizado para transferência de hipertexto na web é:",
        ["HTTP",
         "FTP",
         "SMTP",
         "DNS",
         "DHCP"],
        0,
        "HTTP (Hypertext Transfer Protocol) é o protocolo base da web para transferência de hipertexto.",
        "Informática", ["redes"]
    ),
    _q(
        "No Windows, o comando executado no Prompt para verificar a configuração de IP é:",
        ["ipconfig",
         "ping",
         "tracert",
         "netstat",
         "nslookup"],
        0,
        "ipconfig exibe as configurações de IP da máquina; ping testa conectividade; tracert mostra a rota.",
        "Informática", ["windows"]
    ),
    # ── Legislação ────────────────────────────────────────────────────────────
    _q(
        "Segundo a Lei 9.478/1997, a ANP tem por finalidade:",
        ["Promover a exploração de petróleo exclusivamente pela Petrobras.",
         "Regular e fiscalizar as atividades econômicas da indústria do petróleo, gás natural e biocombustíveis.",
         "Definir o preço dos combustíveis no mercado interno.",
         "Coordenar a política energética nacional.",
         "Administrar os royalties do petróleo."],
        1,
        "Art. 7º: a ANP regula e fiscaliza as atividades da indústria do petróleo, gás natural e biocombustíveis.",
        "Legislação", ["9478"]
    ),
    _q(
        "O Conselho Nacional de Política Energética (CNPE) é vinculado:",
        ["Ao Ministério de Minas e Energia",
         "À Presidência da República",
         "À ANP",
         "À Petrobras",
         "Ao Congresso Nacional"],
        1,
        "Lei 9.478/1997, Art. 2º: CNPE é órgão de assessoramento da Presidência da República.",
        "Legislação", ["9478"]
    ),
    _q(
        "O regime de partilha de produção, instituído pela Lei 12.351/2010, aplica-se:",
        ["A qualquer bloco exploratório em terra.",
         "Exclusivamente às áreas do pré-sal e áreas estratégicas.",
         "A poços de petróleo já em produção.",
         "A refinarias da Petrobras.",
         "A contratos de gás natural liquefeito."],
        1,
        "Lei 12.351/2010 institui o regime de partilha para áreas do pré-sal e demais áreas estratégicas.",
        "Legislação", ["12351"]
    ),
    _q(
        "De acordo com a CF/88, compete à União explorar diretamente ou mediante concessão:",
        ["Serviços de saúde pública.",
         "Os serviços e instalações de energia elétrica e o aproveitamento energético dos cursos d'água.",
         "O transporte coletivo municipal.",
         "A educação básica.",
         "A segurança pública."],
        1,
        "Art. 21, XII, b: compete à União explorar serviços e instalações de energia elétrica e aproveitamento hidrelétrico.",
        "Legislação", ["cf"]
    ),
    # ── Português ────────────────────────────────────────────────────────────
    _q(
        "Assinale a frase em que a concordância verbal está correta:",
        ["Fazem cinco anos que trabalho na empresa.",
         "Houveram muitas dúvidas durante a prova.",
         "Existem questões de múltipla escolha no concurso.",
         "Devem haver engenheiros capacitados.",
         "Faltam pouco para a prova."],
        2,
        "'Existem' concorda com 'questões' (plural). As demais violam a regra: 'faz' (tempo), 'houve' (impessoal), 'deve haver' (impessoal), 'falta' (pouco é singular).",
        "Português", ["concordancia"]
    ),
    _q(
        "A regência verbal está correta em:",
        ["Prefiro estudar matemática do que português.",
         "Assistimos o filme na semana passada.",
         "O candidato aspirava ao cargo de engenheiro.",
         "Paguei o fornecedor ontem.",
         "Lembrei do compromisso marcado."],
        2,
        "'Aspirar' no sentido de almejar exige preposição 'a'. Correção: prefiro X a Y; assistir a (ver); pagar a; lembrar-se de.",
        "Português", ["regencia"]
    ),
    _q(
        "A palavra 'estratégia' é acentuada pela mesma regra que:",
        ["Saúde",
         "Pônei",
         "Água",
         "Médico",
         "Café"],
        2,
        "Paroxítona terminada em ditongo crescente: estratégia, água, história. Saúde (hiato), pônei (oxítona), médico (proparoxítona), café (oxítona).",
        "Português", ["acentuacao"]
    ),
    _q(
        "Em 'Entregaram o relatório para mim avaliar', há erro de:",
        ["Pontuação",
         "Regência nominal",
         "Colocação pronominal",
         "Emprego do pronome pessoal",
         "Concordância nominal"],
        3,
        "'Mim' não pode ser sujeito de verbo no infinitivo. O correto é 'para eu avaliar'.",
        "Português", ["pronomes"]
    ),
    # ── Raciocínio Lógico ────────────────────────────────────────────────────
    _q(
        "Em uma sequência lógica, o próximo termo de 2, 6, 18, 54, ... é:",
        ["108",
         "162",
         "72",
         "216",
         "90"],
        1,
        "Sequência geométrica de razão 3: 54 × 3 = 162.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Considerando o diagrama: 'Todo engenheiro é concursado. Alguns concursados são da CESGRANRIO. Maria é engenheira.' Pode-se concluir que:",
        ["Maria é concursada.",
         "Maria é da CESGRANRIO.",
         "Maria não é concursada.",
         "Nenhum concursado é engenheiro.",
         "Todos os concursados são engenheiros."],
        0,
        "Todo engenheiro é concursado → Maria (engenheira) é concursada. Mas não se sabe se é da CESGRANRIO.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Um dado honesto é lançado. Qual a probabilidade de sair um número maior que 4?",
        ["1/6",
         "1/3",
         "1/2",
         "2/3",
         "5/6"],
        1,
        "Números maiores que 4: 5 e 6 → 2/6 = 1/3.",
        "Raciocínio Lógico", ["rl"]
    ),
    # ── Matemática ───────────────────────────────────────────────────────────
    _q(
        "Um produto custava R$ 200,00 e sofreu dois aumentos sucessivos de 10% e 20%. O preço final é:",
        ["R$ 230,00",
         "R$ 260,00",
         "R$ 264,00",
         "R$ 240,00",
         "R$ 250,00"],
        2,
        "Aumento de 10%: 200 × 1,10 = 220. Aumento de 20%: 220 × 1,20 = 264.",
        "Matemática", ["porcentagem"]
    ),
    _q(
        "Uma torneira enche um tanque em 4 horas. Outra o esvazia em 6 horas. Estando ambas abertas, o tanque encherá em:",
        ["10 horas",
         "12 horas",
         "2 horas",
         "8 horas",
         "5 horas"],
        1,
        "Vazão líquida: 1/4 − 1/6 = 1/12 do tanque por hora → 12 horas.",
        "Matemática", ["raciocinio"]
    ),
    _q(
        "João aplicou R$ 5.000,00 a juros simples de 2% ao mês durante 6 meses. O montante é:",
        ["R$ 5.600,00",
         "R$ 5.800,00",
         "R$ 6.000,00",
         "R$ 6.200,00",
         "R$ 6.500,00"],
        0,
        "J = C×i×t = 5000×0,02×6 = 600. M = C+J = 5600.",
        "Matemática", ["juros"]
    ),
    _q(
        "Em uma proporção a/b = c/d, se a = 6, b = 9 e c = 10, então d vale:",
        ["12",
         "15",
         "18",
         "20",
         "24"],
        1,
        "6/9 = 10/d → 6d = 90 → d = 15.",
        "Matemática", ["proporcao"]
    ),
    # ── Atualidades ──────────────────────────────────────────────────────────
    _q(
        "O gás natural é classificado como:",
        ["Fonte renovável de energia.",
         "Combustível fóssil não renovável.",
         "Fonte limpa sem emissão de CO₂.",
         "Biocombustível de segunda geração.",
         "Fonte de energia nuclear."],
        1,
        "Gás natural é combustível fóssil, formado pela decomposição de matéria orgânica ao longo de milhões de anos.",
        "Atualidades", ["energia"]
    ),
    _q(
        "O Brasil é um dos maiores produtores mundiais de petróleo devido principalmente:",
        ["Às reservas de xisto betuminoso.",
         "À produção em águas profundas e ultraprofundas do pré-sal.",
         "À exploração de carvão mineral.",
         "Às refinarias do Nordeste.",
         "Ao gás de xisto (shale gas)."],
        1,
        "O pré-sal (Bacia de Santos, Campos, Espírito Santo) elevou o Brasil ao ranking dos maiores produtores mundiais.",
        "Atualidades", ["energia"]
    ),
    _q(
        "O biodiesel é um biocombustível produzido a partir de:",
        ["Óleos vegetais e gorduras animais, através de transesterificação.",
         "Petróleo bruto, através de craqueamento catalítico.",
         "Carvão mineral, através de gaseificação.",
         "Gás natural, através de reforma a vapor.",
         "Resíduos nucleares, através de fissão."],
        0,
        "Biodiesel é produzido por transesterificação de óleos vegetais (soja, palma) ou gorduras animais.",
        "Atualidades", ["energia"]
    ),
    # ── Engenharia questions ───────────────────────────────────────────────────
    _q(
        "O ângulo de atrito interno e a coesão de um solo são parâmetros de resistência ao cisalhamento obtidos principalmente no ensaio de:",
        ["Compressão simples.",
         "Cisalhamento direto ou triaxial.",
         "Adensamento edométrico.",
         "Granulometria por peneiramento.",
         "Limite de liquidez."],
        1,
        "Os ensaios de cisalhamento direto e triaxial determinam a envoltória de ruptura de Mohr-Coulomb, fornecendo coesão e ângulo de atrito.",
        "Engenharia Civil", ["civil", "solos"]
    ),
    _q(
        "A teoria do adensamento de Terzaghi é unidimensional e permite prever:",
        ["A velocidade de percolação da água no solo.",
         "A evolução do recalque ao longo do tempo em solos saturados.",
         "A resistência ao cisalhamento de solos não saturados.",
         "A curva granulométrica do solo.",
         "O índice de vazio crítico do solo."],
        1,
        "A teoria do adensamento de Terzaghi modela a dissipação das poropressões e a evolução dos recalques ao longo do tempo em solos argilosos saturados.",
        "Engenharia Civil", ["civil", "solos"]
    ),
    _q(
        "Um traço de concreto 1:2:3 (cimento:areia:brita) em massa significa que, para cada saco de cimento de 50 kg, as quantidades de areia e brita são, respectivamente:",
        ["50 kg e 100 kg.",
         "100 kg e 150 kg.",
         "50 kg e 150 kg.",
         "150 kg e 100 kg.",
         "100 kg e 50 kg."],
        1,
        "No traço 1:2:3, para cada parte de cimento (50 kg), usam-se 2 partes de areia (100 kg) e 3 partes de brita (150 kg).",
        "Engenharia Civil", ["civil", "concreto"]
    ),
    _q(
        "O fck do concreto é definido como:",
        ["A resistência média do concreto aos 28 dias.",
         "A resistência característica à compressão, para a qual 95% dos corpos de prova têm resistência superior.",
         "A resistência à tração na flexão do concreto.",
         "A resistência do concreto aos 7 dias de cura.",
         "A tensão de escoamento do aço da armadura."],
        1,
        "O fck é a resistência característica à compressão, definida como o valor que tem 95% de probabilidade de ser superado (fck = fm − 1,65·s).",
        "Engenharia Civil", ["civil", "concreto"]
    ),
    _q(
        "A principal diferença entre fundação rasa (direta) e fundação profunda é:",
        ["O custo: rasa é sempre mais cara que profunda.",
         "A profundidade: rasa transmite carga a camadas superficiais (até 3 m); profunda transmite a camadas mais profundas (> 3 m).",
         "O material: rasa é sempre de concreto; profunda é sempre metálica.",
         "A forma: rasa é circular; profunda é retangular.",
         "O tipo de solo: rasa só pode ser usada em rocha."],
        1,
        "Fundações rasas (sapatas, radiers) transmitem carga a profundidades até ~3 m; fundações profundas (estacas, tubulões) atingem camadas mais profundas.",
        "Engenharia Civil", ["civil", "fundacoes"]
    ),
    _q(
        "Nas instalações prediais de água fria, o barrilete é:",
        ["O reservatório inferior de água.",
         "A tubulação que deriva da rede pública até o cavalete.",
         "O conjunto de tubulações que se origina no reservatório e do qual partem as colunas de distribuição.",
         "A válvula de descarga do vaso sanitário.",
         "O dispositivo de aquecimento de água."],
        2,
        "O barrilete é a tubulação mestra logo após o reservatório superior, de onde partem as colunas de distribuição para os pavimentos.",
        "Engenharia Civil", ["civil", "instalacoes"]
    ),
    _q(
        "A NR-18 estabelece condições de segurança e saúde no trabalho na indústria da construção. Entre suas exigências está:",
        ["Uso obrigatório de equipamentos de proteção individual apenas para serviços em altura.",
         "Elaboração obrigatória do PCMAT (Programa de Condições e Meio Ambiente de Trabalho na Indústria da Construção) para obras com 20 ou mais trabalhadores.",
         "Jornada de trabalho máxima de 6 horas para todos os operários.",
         "Proibição total do uso de madeira em andaimes.",
         "Obrigatoriedade de engenheiro civil em todas as obras."],
        1,
        "A NR-18 exige PCMAT para obras com ≥ 20 trabalhadores, contemplando riscos, medidas preventivas e cronograma de ações.",
        "Engenharia Civil", ["civil", "nr18"]
    ),
    _q(
        "Em topografia, o método de levantamento por coordenadas polares consiste em:",
        ["Medir apenas ângulos horizontais entre pontos.",
         "Medir ângulos horizontais e distâncias a partir de uma estação, calculando coordenadas relativas.",
         "Medir apenas distâncias entre pontos consecutivos.",
         "Utilizar coordenadas geográficas obtidas por GPS.",
         "Fotografar o terreno e extrair medidas da imagem."],
        1,
        "No método polar, medem-se ângulos horizontais e distâncias de uma estação a cada ponto visado, obtendo coordenadas polares convertidas em cartesianas.",
        "Engenharia Civil", ["civil", "topografia"]
    ),
    _q(
        "O aço CA-50 utilizado em concreto armado tem limite de escoamento característico de:",
        ["250 MPa.",
         "500 MPa.",
         "600 MPa.",
         "350 MPa.",
         "750 MPa."],
        1,
        "CA significa Concreto Armado e o número 50 indica a resistência característica ao escoamento em kgf/mm² (500 MPa).",
        "Engenharia Civil", ["civil", "aco"]
    ),
    _q(
        "A massa específica real do cimento Portland é determinada em laboratório utilizando:",
        ["O frasco de Chapman (ou Le Chatelier).",
         "O ensaio de consistência normal.",
         "O ensaio de finura por peneiramento.",
         "O ensaio de tração na flexão.",
         "O ensaio de compressão diametral."],
        0,
        "O frasco de Le Chatelier (ou de Chapman) mede o volume deslocado por uma massa conhecida de cimento, permitindo calcular sua massa específica real.",
        "Engenharia Civil", ["civil", "materiais"]
    ),
    # ── Engenharia Mecânica ────────────────────────────────────────────────────
    _q(
        "A primeira lei da termodinâmica para um sistema fechado é uma formulação do princípio de:",
        ["Conservação da massa.",
         "Conservação da energia.",
         "Aumento da entropia.",
         "Conservação da quantidade de movimento.",
         "Equilíbrio térmico."],
        1,
        "A 1ª lei estabelece que a variação de energia interna de um sistema fechado é igual ao calor adicionado menos o trabalho realizado (ΔU = Q − W).",
        "Engenharia Mecânica", ["mec", "termo"]
    ),
    _q(
        "O ciclo Rankine é o ciclo termodinâmico utilizado principalmente em:",
        ["Motores de combustão interna.",
         "Usinas termelétricas a vapor.",
         "Turbinas a gás (ciclo Brayton).",
         "Refrigeradores domésticos.",
         "Ciclo Otto de motores a gasolina."],
        1,
        "O ciclo Rankine (bomba, caldeira, turbina, condensador) é o ciclo padrão das usinas termelétricas a vapor.",
        "Engenharia Mecânica", ["mec", "termo"]
    ),
    _q(
        "A equação de Bernoulli para escoamento de fluidos é válida sob a hipótese de:",
        ["Escoamento viscoso e compressível.",
         "Escoamento incompressível, invíscido, permanente e ao longo de uma linha de corrente.",
         "Escoamento turbulento com perda de carga.",
         "Escoamento bifásico (líquido e gás).",
         "Escoamento não permanente com atrito."],
        1,
        "Bernoulli: p/γ + v²/2g + z = cte, válida para fluido incompressível, sem atrito, regime permanente ao longo de uma linha de corrente.",
        "Engenharia Mecânica", ["mec", "fluidos"]
    ),
    _q(
        "O número de Reynolds é definido pela relação entre forças:",
        ["De pressão e viscosas.",
         "De inércia e viscosas.",
         "Gravitacionais e de inércia.",
         "De tensão superficial e de inércia.",
         "Elásticas e viscosas."],
        1,
        "Re = ρ·v·D/μ, representando a razão entre forças de inércia e forças viscosas, determinando o regime de escoamento (laminar ou turbulento).",
        "Engenharia Mecânica", ["mec", "fluidos"]
    ),
    _q(
        "Na resistência dos materiais, a tensão normal de flexão em uma viga submetida a momento fletor M é dada pela expressão:",
        ["τ = V·Q/(I·t).",
         "σ = M·y/I.",
         "σ = P/A.",
         "τ = G·γ.",
         "σ = E·ε."],
        1,
        "A fórmula da flexão (σ = M·y/I) relaciona a tensão normal ao momento fletor M, distância y da linha neutra e momento de inércia I.",
        "Engenharia Mecânica", ["mec", "resistencia"]
    ),
    _q(
        "A lei de Fourier para condução de calor unidimensional em regime permanente estabelece que:",
        ["q = h·A·ΔT.",
         "q = σ·ε·A·(T₁⁴ − T₂⁴).",
         "q = −k·A·dT/dx.",
         "q = m·cp·ΔT.",
         "q = U·A·ΔTₘₗ."],
        2,
        "A lei de Fourier: q = −k·A·dT/dx, onde k é a condutividade térmica e dT/dx é o gradiente de temperatura.",
        "Engenharia Mecânica", ["mec", "transcal"]
    ),
    _q(
        "Segundo a NR-13, as caldeiras a vapor são classificadas em categorias com base em:",
        ["Apenas na pressão de operação.",
         "Apenas no volume interno.",
         "Na pressão de operação e no volume interno, definindo 3 categorias (A, B, C).",
         "No tipo de combustível utilizado.",
         "Na temperatura de operação."],
        2,
        "NR-13 classifica caldeiras em categorias A, B e C conforme pressão de operação (P) e volume interno (V), com requisitos de segurança específicos.",
        "Engenharia Mecânica", ["mec", "nr13"]
    ),
    _q(
        "Em sistemas de bombeamento, o NPSH disponível (NPSHd) deve ser:",
        ["Igual ao NPSH requerido pela bomba.",
         "Maior ou igual ao NPSH requerido (NPSHr) para evitar cavitação.",
         "Menor que o NPSH requerido para garantir eficiência.",
         "Indiferente ao funcionamento da bomba.",
         "Sempre igual à pressão atmosférica local."],
        1,
        "NPSHd ≥ NPSHr é condição necessária para evitar cavitação, que ocorre quando a pressão do líquido atinge a pressão de vapor.",
        "Engenharia Mecânica", ["mec", "maquinasfluxo"]
    ),
    _q(
        "No processo de soldagem SMAW (Shielded Metal Arc Welding), também conhecido como soldagem a eletrodo revestido:",
        ["O arco elétrico é estabelecido entre o eletrodo de tungstênio e a peça, com gás de proteção.",
         "O calor é gerado por resistência elétrica entre as peças.",
         "O eletrodo revestido funde-se e o revestimento forma escória e gases de proteção.",
         "O metal de adição é alimentado automaticamente por um arame contínuo.",
         "Não há fusão do metal base, apenas pressão e calor."],
        2,
        "No SMAW, o eletrodo revestido é consumível; o revestimento queima gerando escória e gases que protegem a poça de fusão.",
        "Engenharia Mecânica", ["mec", "soldagem"]
    ),
    _q(
        "O módulo de uma engrenagem cilíndrica de dentes retos é definido como:",
        ["A relação entre o diâmetro primitivo e o número de dentes (m = d/z).",
         "A relação entre o número de dentes e o diâmetro externo.",
         "A altura total do dente.",
         "O ângulo de pressão do perfil do dente.",
         "A largura da engrenagem dividida pelo módulo."],
        0,
        "O módulo m = d/z (mm) é o parâmetro fundamental das engrenagens: determina o tamanho dos dentes e padroniza o intertravamento.",
        "Engenharia Mecânica", ["mec", "elementosmaquinas"]
    ),
    # ── Engenharia Elétrica ────────────────────────────────────────────────────
    _q(
        "A resistência equivalente de dois resistores R₁ e R₂ ligados em paralelo é dada por:",
        ["Req = R₁ + R₂.",
         "Req = (R₁·R₂)/(R₁ + R₂).",
         "Req = R₁·R₂.",
         "Req = (R₁ + R₂)/(R₁·R₂).",
         "Req = R₁ − R₂."],
        1,
        "Em paralelo, 1/Req = 1/R₁ + 1/R₂ → Req = (R₁·R₂)/(R₁ + R₂), sempre menor que o menor dos resistores.",
        "Engenharia Elétrica", ["ele", "circuitos"]
    ),
    _q(
        "O teorema de Thevenin estabelece que qualquer circuito linear bilateral entre dois terminais pode ser substituído por:",
        ["Uma fonte de corrente em paralelo com uma resistência.",
         "Uma fonte de tensão em série com uma resistência equivalente.",
         "Uma fonte de tensão ideal apenas.",
         "Uma resistência equivalente apenas.",
         "Um indutor e um capacitor em série."],
        1,
        "O equivalente Thevenin é uma fonte de tensão Vth (tensão de circuito aberto) em série com Rth (resistência equivalente vista dos terminais).",
        "Engenharia Elétrica", ["ele", "circuitos"]
    ),
    _q(
        "O escorregamento de um motor de indução trifásico é definido como:",
        ["s = (Ns − N)/Ns, onde Ns é a velocidade síncrona e N a velocidade do rotor.",
         "s = N/Ns.",
         "s = (N − Ns)/N.",
         "s = 1 − Ns/N.",
         "s = Ns·N."],
        0,
        "O escorregamento s = (Ns − N)/Ns representa a diferença percentual entre a velocidade do campo girante e a do rotor.",
        "Engenharia Elétrica", ["ele", "maquinas"]
    ),
    _q(
        "Em um transformador ideal, a relação entre tensão primária (V₁) e secundária (V₂) é:",
        ["V₁/V₂ = N₂/N₁.",
         "V₁/V₂ = N₁/N₂, onde N₁ e N₂ são os números de espiras.",
         "V₁ = V₂ independentemente das espiras.",
         "V₁/V₂ = (N₁/N₂)².",
         "V₁·V₂ = N₁·N₂."],
        1,
        "Em transformador ideal, V₁/V₂ = N₁/N₂ e I₁/I₂ = N₂/N₁, mantendo potência constante (V₁·I₁ = V₂·I₂).",
        "Engenharia Elétrica", ["ele", "transformadores"]
    ),
    _q(
        "A frequência nominal do sistema elétrico interligado brasileiro é de:",
        ["50 Hz.",
         "60 Hz.",
         "100 Hz.",
         "400 Hz.",
         "30 Hz."],
        1,
        "O Brasil adota 60 Hz como frequência nominal (SIN). Alguns países adotam 50 Hz (Europa, Ásia).",
        "Engenharia Elétrica", ["ele", "potencia"]
    ),
    _q(
        "Um relé de sobrecorrente temporizado tem a função de:",
        ["Proteger contra curtos-circuitos apenas, com atuação instantânea.",
         "Proteger contra sobrecargas, atuando após um tempo inversamente proporcional à corrente.",
         "Medir o fator de potência da instalação.",
         "Religar automaticamente o disjuntor após falta.",
         "Monitorar a frequência do sistema."],
        1,
        "Relés de sobrecorrente temporizados (curva inversa) atuam com tempo inversamente proporcional à corrente, protegendo contra sobrecargas.",
        "Engenharia Elétrica", ["ele", "protecao"]
    ),
    _q(
        "A NR-10 estabelece requisitos de segurança em instalações elétricas. Entre eles, determina que:",
        ["Apenas engenheiros eletricistas podem trabalhar com eletricidade.",
         "Toda instalação elétrica deve ser desenergizada antes de qualquer intervenção, salvo exceções justificadas com procedimentos específicos.",
         "O aterramento elétrico é opcional em instalações prediais.",
         "Não é obrigatório o uso de EPI em baixa tensão.",
         "A medição de resistividade do solo é dispensável."],
        1,
        "NR-10: sempre que possível, trabalhar com instalações desenergizadas; quando não for, procedimentos específicos e EPIs adequados são obrigatórios.",
        "Engenharia Elétrica", ["ele", "nr10"]
    ),
    _q(
        "Um diodo semicondutor em polarização direta conduz corrente quando:",
        ["A tensão catodo-anodo é positiva e maior que a tensão de ruptura.",
         "A tensão anodo-catodo é positiva e superior à tensão de joelho (≈0,7 V para silício).",
         "A tensão aplicada é alternada.",
         "A temperatura do dispositivo ultrapassa 100 °C.",
         "O catodo está em potencial mais positivo que o anodo."],
        1,
        "Em polarização direta (anodo > catodo), o diodo de silício conduz quando Vak > ~0,7 V, superando a barreira de potencial da junção PN.",
        "Engenharia Elétrica", ["ele", "eletronica"]
    ),
    _q(
        "Na instrumentação industrial, o sinal padrão de corrente mais utilizado para transmitir medidas é:",
        ["0 a 10 VCC.",
         "4 a 20 mA.",
         "0 a 20 mA.",
         "−10 a +10 VCC.",
         "10 a 50 mA."],
        1,
        "O padrão 4-20 mA é o mais utilizado: 4 mA representa o zero vivo (permite detectar falha/fio rompido) e 20 mA o fundo de escala.",
        "Engenharia Elétrica", ["ele", "instrumentacao"]
    ),
    _q(
        "Os harmônicos em sistemas elétricos de potência são distorções nas formas de onda de tensão e corrente causadas principalmente por:",
        ["Cargas lineares como resistores e aquecedores.",
         "Cargas não lineares como fontes chaveadas, conversores e inversores.",
         "Desbalanceamento entre fases.",
         "Aterramento inadequado.",
         "Cabos subterrâneos de longa extensão."],
        1,
        "Cargas não lineares (fontes chaveadas, inversores, retificadores) geram correntes harmônicas que distorcem a forma de onda senoidal.",
        "Engenharia Elétrica", ["ele", "qualidade"]
    ),
    # ── Engenharia Química ────────────────────────────────────────────────────
    _q(
        "Em uma coluna de destilação contínua, o produto retirado no topo é rico em:",
        ["Componente menos volátil.",
         "Componente mais volátil.",
         "Líquido de fundo.",
         "Resíduo pesado.",
         "Água de arraste."],
        1,
        "Na destilação, o componente mais volátil (menor ponto de ebulição) concentra-se no vapor que sai pelo topo e é condensado.",
        "Engenharia Química", ["quim", "operacoes"]
    ),
    _q(
        "A lei de Darcy aplicada à filtração estabelece que a vazão de filtrado é:",
        ["Diretamente proporcional à área filtrante e à diferença de pressão, e inversamente proporcional à viscosidade e à resistência da torta.",
         "Independente da área do filtro.",
         "Diretamente proporcional à viscosidade do fluido.",
         "Inversamente proporcional à diferença de pressão aplicada.",
         "Igual para todos os tipos de partículas."],
        0,
        "Darcy: Q = (k·A·ΔP)/(μ·L). A vazão aumenta com área e ΔP, e diminui com maior viscosidade e espessura da torta.",
        "Engenharia Química", ["quim", "operacoes"]
    ),
    _q(
        "A regra das fases de Gibbs para um sistema em equilíbrio com C componentes e F fases é expressa como:",
        ["G = C + F − P.",
         "G = C − F + 2.",
         "G = C + F.",
         "G = C·F.",
         "G = 2 − C − F."],
        1,
        "A regra de Gibbs: G = C − F + 2, onde G é o número de graus de liberdade (variáveis intensivas independentes) do sistema.",
        "Engenharia Química", ["quim", "termo"]
    ),
    _q(
        "O ponto de bolha de uma mistura líquida binária é definido como:",
        ["A temperatura na qual a última gota de líquido vaporiza.",
         "A temperatura na qual se forma a primeira bolha de vapor ao aquecer o líquido, a uma dada pressão.",
         "A temperatura de congelamento da mistura.",
         "A pressão na qual o líquido solidifica.",
         "A temperatura na qual os componentes se separam."],
        1,
        "Ponto de bolha: para uma dada pressão, é a temperatura em que surge a primeira bolha de vapor ao aquecer uma mistura líquida.",
        "Engenharia Química", ["quim", "termo"]
    ),
    _q(
        "Em um reator CSTR (Continuous Stirred Tank Reactor) operando em estado estacionário, a concentração do reagente na saída é:",
        ["Igual à concentração na entrada.",
         "Uniforme em todo o reator e igual à concentração de saída.",
         "Máxima no centro e mínima nas paredes.",
         "Decrescente exponencialmente ao longo do comprimento.",
         "Independente da vazão de alimentação."],
        1,
        "O CSTR opera com mistura perfeita: as propriedades são uniformes em todo o volume e a concentração de saída é igual à do interior.",
        "Engenharia Química", ["quim", "reatores"]
    ),
    _q(
        "O reator PFR (Plug Flow Reactor) é caracterizado por:",
        ["Mistura perfeita do conteúdo.",
         "Escoamento tipo pistão, sem mistura axial, com gradiente de concentração ao longo do comprimento.",
         "Operação apenas em batelada.",
         "Ausência de reação química.",
         "Perfil de temperatura uniforme independente da reação."],
        1,
        "No PFR, o fluido escoa como pistão (sem mistura axial) e a concentração varia continuamente ao longo do reator.",
        "Engenharia Química", ["quim", "reatores"]
    ),
    _q(
        "O número de Nusselt (Nu) em fenômenos de transporte é definido como a razão entre:",
        ["A transferência de calor por convecção e por condução.",
         "A transferência de massa por difusão e por convecção.",
         "As forças de inércia e viscosas.",
         "A quantidade de movimento e a difusividade térmica.",
         "A energia cinética e a entalpia."],
        0,
        "Nu = h·L/k, relacionando o coeficiente convectivo h com a condutividade k. Nu = 1 significa condução pura.",
        "Engenharia Química", ["quim", "transporte"]
    ),
    _q(
        "O craqueamento catalítico (FCC) em refinarias de petróleo tem como principal objetivo:",
        ["Remover enxofre dos derivados de petróleo.",
         "Converter frações pesadas de hidrocarbonetos em frações mais leves (GLP, gasolina, diesel) usando catalisador.",
         "Separar o petróleo em frações por ponto de ebulição.",
         "Produzir lubrificantes a partir do resíduo de vácuo.",
         "Remover água do petróleo bruto."],
        1,
        "O FCC (Fluid Catalytic Cracking) quebra moléculas grandes de gasóleo em moléculas menores de gasolina, GLP e diesel, usando catalisador zeolítico.",
        "Engenharia Química", ["quim", "petroquimica"]
    ),
    _q(
        "A corrosão por pite (pitting) é caracterizada por:",
        ["Ataque uniforme em toda a superfície metálica.",
         "Formação de cavidades localizadas e profundas, geralmente causada por íons cloreto em metais passivados.",
         "Dissolução preferencial de um dos componentes de uma liga.",
         "Fragilização por hidrogênio.",
         "Corrosão acelerada por contato entre metais diferentes."],
        1,
        "O pite é uma corrosão localizada que forma pequenas cavidades profundas, comum em aços inoxidáveis na presença de cloretos.",
        "Engenharia Química", ["quim", "corrosao"]
    ),
    _q(
        "A sigla HAZOP (Hazard and Operability Study) é uma técnica de análise de risco que:",
        ["Calcula a probabilidade estatística de falhas.",
         "Identifica desvios de processo, suas causas e consequências, usando palavras-guia em sessões sistemáticas.",
         "Lista todos os equipamentos com suas especificações técnicas.",
         "Determina o custo de manutenção de uma planta.",
         "Substitui a APR (Análise Preliminar de Riscos)."],
        1,
        "HAZOP é uma técnica estruturada que usa palavras-guia (nenhum, mais, menos, etc.) para identificar desvios operacionais e seus riscos.",
        "Engenharia Química", ["quim", "seguranca"]
    ),
    # ── Engenharia de Produção ─────────────────────────────────────────────────
    _q(
        "O MRP (Material Requirements Planning) é uma ferramenta de PCP cuja função principal é:",
        ["Controlar a qualidade dos produtos acabados.",
         "Calcular as necessidades de materiais e componentes para atender ao plano mestre de produção.",
         "Definir o layout fabril da planta.",
         "Gerenciar o fluxo de caixa da empresa.",
         "Avaliar o desempenho dos fornecedores."],
        1,
        "MRP explode a demanda do plano mestre em necessidades de componentes e matérias-primas, considerando lead times e estoques.",
        "Engenharia de Produção", ["prod", "pcp"]
    ),
    _q(
        "O sistema Just-in-Time (JIT) tem como objetivo principal:",
        ["Manter grandes estoques de segurança.",
         "Eliminar desperdícios, produzir somente o necessário, no momento certo e na quantidade certa.",
         "Maximizar a produção em massa independentemente da demanda.",
         "Centralizar todas as decisões de produção.",
         "Reduzir o número de fornecedores a um único."],
        1,
        "JIT é uma filosofia de produção enxuta que busca estoque zero, eliminação de desperdícios e produção puxada pela demanda.",
        "Engenharia de Produção", ["prod", "jit"]
    ),
    _q(
        "Em programação linear, o método simplex encontra a solução ótima percorrendo:",
        ["Todos os pontos possíveis do espaço de soluções.",
         "Os vértices da região factível, melhorando a função objetivo a cada iteração.",
         "Apenas o interior da região factível.",
         "Soluções aleatórias até encontrar a melhor.",
         "O gradiente negativo da função objetivo."],
        1,
        "O simplex percorre vértices adjacentes da região factível (politopo) reduzindo o custo ou aumentando o lucro até o ótimo.",
        "Engenharia de Produção", ["prod", "po"]
    ),
    _q(
        "Em teoria das filas, para um sistema M/M/1, a taxa de ocupação ρ (rho) é definida como:",
        ["ρ = λ − μ, onde λ é a taxa de chegada e μ a taxa de serviço.",
         "ρ = λ/μ, representando a fração de tempo em que o servidor está ocupado.",
         "ρ = μ/λ.",
         "ρ = λ·μ.",
         "ρ = (λ + μ)/λ."],
        1,
        "Em M/M/1, ρ = λ/μ. Para estabilidade, ρ < 1 (a taxa de chegada deve ser menor que a taxa de serviço).",
        "Engenharia de Produção", ["prod", "po"]
    ),
    _q(
        "O ciclo PDCA (Plan-Do-Check-Act) é uma ferramenta de gestão da qualidade que:",
        ["Estabelece metas, executa, verifica resultados e atua corretivamente de forma contínua.",
         "Substitui o método 5W2H na análise de problemas.",
         "É utilizado exclusivamente em auditorias ISO.",
         "Aplica-se apenas a processos produtivos industriais.",
         "Elimina a necessidade de indicadores de desempenho."],
        0,
        "PDCA: Plan (planejar), Do (executar), Check (verificar), Act (agir corretivamente). É a base da melhoria contínua.",
        "Engenharia de Produção", ["prod", "qualidade"]
    ),
    _q(
        "A norma ISO 9001:2015 estabelece requisitos para:",
        ["Produtos específicos da indústria automotiva.",
         "Sistemas de gestão da qualidade, aplicáveis a qualquer organização, independentemente do porte ou setor.",
         "Gestão ambiental nas empresas.",
         "Segurança da informação corporativa.",
         "Responsabilidade social das organizações."],
        1,
        "ISO 9001 especifica requisitos para um SGQ (Sistema de Gestão da Qualidade) focado em processos e satisfação do cliente.",
        "Engenharia de Produção", ["prod", "qualidade"]
    ),
    _q(
        "Na engenharia econômica, um Valor Presente Líquido (VPL) positivo significa que:",
        ["O investimento é inviável economicamente.",
         "O retorno do projeto supera a taxa mínima de atratividade (TMA), gerando riqueza.",
         "A Taxa Interna de Retorno é negativa.",
         "O payback é maior que a vida útil do projeto.",
         "O custo do projeto é maior que o benefício."],
        1,
        "VPL > 0 indica que os fluxos de caixa descontados pela TMA superam o investimento inicial, agregando valor ao projeto.",
        "Engenharia de Produção", ["prod", "economica"]
    ),
    _q(
        "A Taxa Interna de Retorno (TIR) de um projeto de investimento é definida como:",
        ["A taxa de desconto que torna o VPL igual a zero.",
         "A taxa de juros do mercado financeiro.",
         "O período de retorno do investimento inicial.",
         "A relação benefício/custo do projeto.",
         "A taxa de inflação projetada para o período."],
        0,
        "TIR é a taxa de desconto que iguala o valor presente das entradas ao valor presente das saídas (VPL = 0).",
        "Engenharia de Produção", ["prod", "economica"]
    ),
    _q(
        "A NR-17 estabelece parâmetros de ergonomia no trabalho, entre os quais:",
        ["A obrigatoriedade de ginástica laboral diária.",
         "O levantamento, transporte e descarga de cargas individuais, adaptação do mobiliário e condições de conforto no ambiente de trabalho.",
         "A jornada máxima de 6 horas para trabalho repetitivo.",
         "A proibição do uso de telas de computador.",
         "A medição obrigatória de ruído a cada hora."],
        1,
        "NR-17 trata de levantamento de cargas, mobiliário, equipamentos, condições ambientais e organização do trabalho para conforto e segurança.",
        "Engenharia de Produção", ["prod", "ergonomia"]
    ),
    _q(
        "Na gestão de projetos segundo o PMBOK, a EAP (Estrutura Analítica do Projeto) é:",
        ["Um gráfico de Gantt detalhado com as datas do projeto.",
         "Uma decomposição hierárquica do trabalho total a ser executado, orientada a entregas.",
         "A lista de recursos financeiros alocados ao projeto.",
         "O cronograma de marcos (milestones) do projeto.",
         "A matriz de responsabilidade (RACI) da equipe."],
        1,
        "A EAP (WBS em inglês) é a decomposição hierárquica do escopo do projeto em pacotes de trabalho menores e gerenciáveis.",
        "Engenharia de Produção", ["prod", "projetos"]
    ),
    # ── NOVAS QUESTÕES ────────────────────────────────────────────────────
    #
    # Legislação (14)
    #
    _q(
        "Segundo a Lei 13.303/2016, o conselho de administração das empresas públicas e sociedades de economia mista deve ter, no mínimo:",
        ["3 membros.",
         "5 membros.",
         "7 membros.",
         "9 membros.",
         "11 membros."],
        2,
        "Art. 13, §1º da Lei 13.303/2016: o conselho de administração deve ter, no mínimo, 7 membros, todos nomeados pela assembleia geral ou pelo poder competente.",
        "Legislação", ["13303"]
    ),
    _q(
        "De acordo com a Lei 13.303/2016, a empresa pública e a sociedade de economia mista deverão observar, em suas licitações, os princípios da:",
        ["Legalidade, moralidade e eficiência apenas.",
          "Impessoalidade, moralidade, publicidade e eficiência, entre outros.",
          "Apenas legalidade e impessoalidade.",
          "Sigilo e competitividade.",
          "Discricionariedade e conveniência."],
        1,
        "Art. 31 da Lei 13.303/2016: as licitações devem observar os princípios da impessoalidade, moralidade, publicidade, eficiência, dentre outros previstos no caput.",
        "Legislação", ["13303"]
    ),
    _q(
        "Nos termos da Lei 13.303/2016, a vedação à participação de servidores públicos no conselho de administração das estatais alcança:",
        ["Apenas ocupantes de cargo em comissão.",
         "Apenas ministros de Estado.",
         "Apenas ocupantes de cargo público na administração direta.",
         "Agentes públicos, incluindo empregados públicos e ocupantes de cargo em comissão.",
         "Apenas membros do Poder Legislativo."],
        3,
        "Art. 17, §3º da Lei 13.303/2016 veda a participação de agentes públicos (servidores, empregados públicos e ocupantes de cargo em comissão) no conselho de administração das estatais.",
        "Legislação", ["13303"]
    ),
    _q(
        "A Lei 9.478/1997, em seu art. 1º, estabelece que as políticas nacionais para o setor energético devem observar, entre outros:",
        ["O monopólio estatal do refino de petróleo.",
         "A proteção dos interesses do consumidor quanto a preço, qualidade e oferta dos produtos.",
         "A exclusividade de atuação da Petrobras na distribuição de derivados.",
         "A proibição de participação estrangeira na exploração de petróleo.",
         "A centralização das decisões no Ministério de Minas e Energia."],
        1,
        "Art. 1º, II da Lei 9.478/1997: proteção do consumidor quanto a preço, qualidade e oferta dos produtos é um dos objetivos da política energética nacional.",
        "Legislação", ["9478"]
    ),
    _q(
        "Compete ao Conselho Nacional de Política Energética (CNPE), instituído pela Lei 9.478/1997:",
        ["Fiscalizar as atividades da ANP.",
         "Propor ao Presidente da República a aplicação dos regimes de licitação nos blocos exploratórios.",
         "Aprovar os contratos de concessão de petróleo.",
         "Definir o preço dos combustíveis ao consumidor final.",
         "Nomear os diretores da Petrobras."],
        1,
        "Art. 2º, §1º, I, a da Lei 9.478/1997: ao CNPE compete propor ao Presidente da República a aplicação dos regimes de licitação nos blocos exploratórios.",
        "Legislação", ["9478"]
    ),
    _q(
        "A Lei 12.351/2010, que instituiu o regime de partilha de produção, criou também:",
        ["A Agência Nacional do Petróleo (ANP).",
         "O Fundo Social (FS) e o Pré-Sal Petróleo S.A. (PPSA).",
         "A Petrobras como operadora única.",
         "O Conselho Nacional de Política Energética (CNPE).",
         "O Ministério de Minas e Energia."],
        1,
        "Art. 46 e 47 da Lei 12.351/2010: criam o Fundo Social (FS) e autorizam a criação do Pré-Sal Petróleo S.A. (PPSA) para gerir os contratos de partilha.",
        "Legislação", ["12351"]
    ),
    _q(
        "Segundo a Constituição Federal de 1988, a exploração direta de atividade econômica pelo Estado só será permitida:",
        ["Em qualquer setor da economia.",
         "Quando necessária aos imperativos da segurança nacional ou a relevante interesse coletivo, conforme definidos em lei.",
         "Apenas em monopólios naturais.",
         "Exclusivamente no setor de petróleo e gás.",
         "Apenas em regime de concessão a empresas privadas."],
        1,
        "Art. 173 da CF/88: a exploração direta de atividade econômica pelo Estado é permitida quando necessária aos imperativos de segurança nacional ou relevante interesse coletivo.",
        "Legislação", ["cf"]
    ),
    _q(
        "De acordo com a Lei 13.303/2016, a remuneração dos administradores das empresas estatais deve ser:",
        ["Definida livremente pelo presidente da empresa.",
         "Aprovada pela assembleia geral ou conselho de administração, com base em política de remuneração que considere mercado e função social.",
         "Vinculada ao teto constitucional do funcionalismo público.",
         "Equivalente ao salário mínimo vigente.",
         "Proporcional ao faturamento da empresa."],
        1,
        "Art. 13, §4º c/c §3º da Lei 13.303/2016: a remuneração é aprovada pela assembleia geral ou conselho de administração, observando política de remuneração e limites de mercado.",
        "Legislação", ["13303"]
    ),
    _q(
        "A área do pré-sal, conforme definido pela Lei 12.351/2010, é considerada:",
        ["Área de exploração exclusiva da Petrobras.",
         "Área estratégica nacional, sob regime de partilha de produção.",
         "Área de livre exploração por qualquer empresa.",
         "Área de preservação ambiental permanente.",
         "Área sob regime de concessão tradicional."],
        1,
        "Art. 1º e 2º da Lei 12.351/2010: o pré-sal e áreas estratégicas são submetidos ao regime de partilha de produção, com a União como contratante.",
        "Legislação", ["12351"]
    ),
    _q(
        "O regime de concessão para exploração de petróleo e gás natural, nos termos da Lei 9.478/1997, é outorgado pela ANP mediante:",
        ["Contrato direto com a Petrobras.",
         "Licitação na modalidade concorrência ou leilão de blocos exploratórios.",
         "Autorização legislativa específica.",
         "Decreto presidencial sem licitação.",
         "Acordo internacional bilateral."],
        1,
        "Art. 36 da Lei 9.478/1997: a ANP realiza licitação na modalidade concorrência ou leilão para outorga de contratos de concessão de exploração e produção.",
        "Legislação", ["9478"]
    ),
    _q(
        "A Lei 13.303/2016 exige que as empresas estatais publiquem anualmente:",
        ["Apenas o balanço patrimonial.",
         "A Carta Anual de Governança Corporativa e o Relatório Integrado de Gestão.",
         "A declaração de Imposto de Renda.",
         "O plano de cargos e salários detalhado.",
         "A lista de todos os fornecedores contratados."],
        1,
        "Art. 8º, VIII e IX da Lei 13.303/2016: a Carta Anual de Governança e o Relatório Integrado de Gestão são instrumentos obrigatórios de transparência.",
        "Legislação", ["13303"]
    ),
    _q(
        "Conforme a Lei 13.303/2016, o comitê de auditoria estatutário das estatais deve ser composto, em sua maioria, por:",
        ["Diretores da empresa.",
         "Membros independentes do conselho de administração.",
         "Funcionários concursados da empresa.",
         "Representantes do Ministério Público.",
         "Auditores externos contratados."],
        1,
        "Art. 15, §2º da Lei 13.303/2016: o comitê de auditoria deve ter maioria de membros independentes do conselho de administração.",
        "Legislação", ["13303"]
    ),
    _q(
        "As participações governamentais devidas pela exploração de petróleo e gás natural, conforme a Lei 9.478/1997, incluem:",
        ["Imposto de renda e CSLL.",
         "Bônus de assinatura, royalties, participação especial e pagamento pela ocupação ou retenção de área.",
         "Apenas royalties de 5% sobre a receita bruta.",
         "Taxa de fiscalização da ANP e ICMS.",
         "Contribuição ao FGTS e INSS."],
        1,
        "Arts. 45 a 50 da Lei 9.478/1997: as participações governamentais são bônus de assinatura, royalties, participação especial e pagamento pela ocupação ou retenção de área.",
        "Legislação", ["9478"]
    ),
    _q(
        "De acordo com a Constituição Federal de 1988, a lei disciplinará a participação do Estado na atividade econômica, devendo a empresa pública e a sociedade de economia mista:",
        ["Atuar sem qualquer finalidade lucrativa.",
         "Submeter-se ao regime jurídico de direito público exclusivamente.",
         "Não se submeter a controle externo.",
         "Ter sua função social definida em lei e reger-se pelas regras de licitação e contratação previstas em lei específica.",
         "Atuar exclusivamente em regime de monopólio."],
        3,
        "Art. 173, §1º da CF/88: a lei estabelecerá o estatuto jurídico da empresa pública e da sociedade de economia mista, abrangendo licitação, contratação e função social.",
        "Legislação", ["cf"]
    ),
    #
    # Raciocínio Lógico (8)
    #
    _q(
        "A negação da proposição 'Todo engenheiro da Petrobras é concursado' é:",
        ["Nenhum engenheiro da Petrobras é concursado.",
         "Algum engenheiro da Petrobras não é concursado.",
         "Todo concursado é engenheiro da Petrobras.",
         "Algum engenheiro da Petrobras é concursado.",
         "Existe engenheiro que não é da Petrobras."],
        1,
        "A negação de 'Todo A é B' é 'Algum A não é B' (ou 'Existe A que não é B').",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Quantos anagramas distintos podem ser formados com a palavra 'PETROBRAS'?",
        ["9!",
         "9! / 2!",
         "9! / 3!",
         "9! / 2!·2!",
         "8!"],
        1,
        "'PETROBRAS' tem 9 letras, com repetição de 'R' (2 vezes). Logo: 9! / 2!.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Em um grupo de 12 engenheiros, de quantas maneiras podemos formar uma comissão de 3 membros?",
        ["36",
         "220",
         "1320",
         "1728",
         "12"],
        1,
        "Combinação de 12, escolhe 3: C(12,3) = 12!/(3!·9!) = (12·11·10)/(3·2·1) = 220.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Se 'Se estudo, então passo no concurso' é verdadeira, qual das seguintes proposições é necessariamente verdadeira?",
        ["Se passei no concurso, então estudei.",
         "Se não passei no concurso, então não estudei.",
         "Se não estudo, então não passo no concurso.",
         "Estudo e passo no concurso.",
         "Não estudo ou não passo no concurso."],
        1,
        "Contrapositiva é logicamente equivalente à condicional: (p → q) ≡ (¬q → ¬p). 'Se não passei, então não estudei' é a contrapositiva.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Em uma urna há 5 bolas vermelhas e 3 bolas azuis. Retirando-se duas bolas sem reposição, a probabilidade de ambas serem vermelhas é:",
        ["5/8",
         "25/64",
         "5/14",
         "20/56",
         "1/2"],
        2,
        "P = (5/8) × (4/7) = 20/56 = 5/14.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Considere a sequência: 1, 4, 9, 16, 25, ... O próximo termo é:",
        ["30",
         "35",
         "36",
         "49",
         "64"],
        2,
        "Sequência dos quadrados perfeitos: 1²=1, 2²=4, 3²=9, 4²=16, 5²=25, 6²=36.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Em uma afirmação 'p ∧ q → r', se p é verdadeiro, q é falso e r é verdadeiro, a afirmação é:",
        ["Verdadeira.",
         "Falsa.",
         "Verdadeira apenas se r for falso.",
         "Indeterminada.",
         "Falsa apenas se p for falso."],
        0,
        "p ∧ q é falso (pois q é falso). Falso → Verdadeiro é verdadeiro (a condicional é verdadeira quando a antecedente é falsa).",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Três amigos — Ana, Bruno e Carlos — são engenheiros. Sabe-se que Ana é mais velha que Bruno, e Carlos é mais novo que Bruno. Logo:",
        ["Ana é a mais nova.",
         "Bruno é o mais novo.",
         "Carlos é o mais velho.",
         "Ana é a mais velha.",
         "Carlos é mais velho que Ana."],
        3,
        "Relações: Ana > Bruno e Bruno > Carlos. Logo Ana > Bruno > Carlos. Ana é a mais velha e Carlos o mais novo.",
        "Raciocínio Lógico", ["rl"]
    ),
    #
    # Engenharia de Produção (13)
    #
    _q(
        "O sistema Toyota de Produção, que originou a produção enxuta (Lean Manufacturing), baseia-se principalmente em dois pilares:",
        ["Produção em massa e estoque regulador.",
         "Just-in-Time (JIT) e Autonomação (Jidoka).",
         "Especialização do trabalho e hierarquia rígida.",
         "Produção contínua e manutenção corretiva.",
         "Automação total e grandes lotes de produção."],
        1,
        "O STP tem como pilares o JIT (produzir no momento certo) e o Jidoka (autonomação com toque humano para detectar anormalidades).",
        "Engenharia de Produção", ["prod", "lean"]
    ),
    _q(
        "A curva ABC (ou curva de Pareto) na gestão de estoques classifica os itens com base:",
        ["No prazo de validade dos produtos.",
         "No valor de consumo ou importância relativa, concentrando esforços nos itens classe A.",
         "No peso físico dos materiais armazenados.",
         "Na ordem alfabética dos fornecedores.",
         "Na data de aquisição do estoque."],
        1,
        "Curva ABC (80/20): classe A (alto valor, poucos itens), B (médio), C (baixo valor, muitos itens). Foco na gestão dos itens A.",
        "Engenharia de Produção", ["prod", "estoques"]
    ),
    _q(
        "O método 5S é uma ferramenta da qualidade que visa:",
        ["Aumentar a velocidade das máquinas produtivas.",
         "Organizar o ambiente de trabalho através de sensos de utilização, ordenação, limpeza, saúde e autodisciplina.",
         "Reduzir o número de funcionários no setor produtivo.",
         "Eliminar completamente os estoques intermediários.",
         "Automatizar os processos de inspeção de qualidade."],
        1,
        "5S: Seiri (senso de utilização), Seiton (ordenação), Seisō (limpeza), Seiketsu (padronização/saúde), Shitsuke (autodisciplina).",
        "Engenharia de Produção", ["prod", "qualidade"]
    ),
    _q(
        "No MRP II (Manufacturing Resource Planning), além dos materiais, o sistema integra também:",
        ["Apenas o controle de qualidade.",
         "Recursos de capacidade, mão de obra, máquinas e finanças, integrando todo o planejamento empresarial.",
         "Exclusivamente o fluxo de caixa da empresa.",
         "Somente a programação de entregas dos fornecedores.",
         "Apenas a manutenção preditiva dos equipamentos."],
        1,
        "MRP II evolui do MRP integrando planejamento de capacidade, recursos produtivos, finanças e demais áreas, formando o ERP.",
        "Engenharia de Produção", ["prod", "pcp"]
    ),
    _q(
        "Na teoria das filas, o modelo M/M/c é caracterizado por:",
        ["Chegadas exponenciais, serviço exponencial e c servidores em paralelo.",
         "Chegadas determinísticas, serviço exponencial e um servidor.",
         "Chegadas exponenciais, serviço constante e c servidores em série.",
         "Chegadas Poisson, serviço geral e servidor único.",
         "Chegadas exponenciais, serviço exponencial e fila infinita com um servidor."],
        0,
        "M/M/c: M = Markovian (chegadas Poisson), M = Markovian (serviço exponencial), c = número de servidores em paralelo.",
        "Engenharia de Produção", ["prod", "po"]
    ),
    _q(
        "O índice OEE (Overall Equipment Effectiveness) na manufatura enxuta mede:",
        ["Apenas a produtividade da mão de obra.",
         "A disponibilidade, o desempenho e a qualidade dos equipamentos, indicando a eficiência global.",
         "Somente o tempo de setup das máquinas.",
         "Exclusivamente o consumo de energia por peça produzida.",
         "A taxa de refugo dividida pela produção total."],
        1,
        "OEE = Disponibilidade × Desempenho × Qualidade. É o principal indicador da eficiência global de equipamentos no TPM.",
        "Engenharia de Produção", ["prod", "qualidade"]
    ),
    _q(
        "Na gestão de projetos, o método do caminho crítico (CPM) é utilizado para:",
        ["Calcular o orçamento detalhado do projeto.",
         "Identificar a sequência de atividades que determina a duração mínima do projeto, sem folgas.",
         "Alocar recursos humanos de forma otimizada.",
         "Gerenciar os riscos do projeto.",
         "Definir a matriz de responsabilidades da equipe."],
        1,
        "O caminho crítico é a sequência de atividades com folga zero, determinando o menor prazo possível para conclusão do projeto.",
        "Engenharia de Produção", ["prod", "projetos"]
    ),
    _q(
        "A folga (ou tolerância) no PERT/CPM de uma atividade é calculada como:",
        ["Término mais tarde − Término mais cedo.",
         "Término mais cedo − Início mais cedo.",
         "Duração da atividade dividida pelo número de recursos.",
         "Término mais tarde − Início mais tarde.",
         "Diferença entre o caminho crítico e o caminho não crítico."],
        0,
        "Folga total = TMT − TMC (ou IMT − INC). Indica quanto uma atividade pode atrasar sem comprometer o prazo final do projeto.",
        "Engenharia de Produção", ["prod", "projetos"]
    ),
    _q(
        "O conceito de 'Gargalo' (bottleneck) na teoria das restrições (TOC) de Goldratt refere-se a:",
        ["Qualquer máquina que apresente defeitos frequentes.",
         "O recurso cuja capacidade é menor ou igual à demanda, limitando a capacidade do sistema como um todo.",
         "O setor com maior número de funcionários.",
         "O processo com maior valor agregado.",
         "A atividade que consome mais energia na fábrica."],
        1,
        "Na TOC, o gargalo determina o throughput do sistema. Melhorias fora do gargalo não aumentam a produção total.",
        "Engenharia de Produção", ["prod", "toc"]
    ),
    _q(
        "O método de precificação conhecido como 'Mark-up' consiste em:",
        ["Definir o preço com base exclusivamente na concorrência.",
         "Adicionar ao custo unitário uma margem percentual para cobrir despesas e gerar lucro.",
         "Fixar o preço abaixo do custo para ganhar market share.",
         "Negociar o preço diretamente com cada cliente.",
         "Utilizar o valor percebido pelo cliente como base de preço."],
        1,
        "Mark-up = 100 / (100 − %Despesas − %Lucro). Aplica-se o fator ao custo unitário para obter o preço de venda.",
        "Engenharia de Produção", ["prod", "economica"]
    ),
    _q(
        "O diagrama de Ishikawa (ou espinha de peixe) é uma ferramenta da qualidade usada para:",
        ["Calcular a capacidade produtiva da fábrica.",
         "Identificar as causas-raiz de um problema, organizando-as em categorias como método, mão de obra, material, máquina, meio e medição.",
         "Elaborar o cronograma de produção semanal.",
         "Desenhar o layout fabril da planta industrial.",
         "Registrar a frequência de não conformidades ao longo do tempo."],
        1,
        "Diagrama de Ishikawa (causa e efeito) agrupa causas potenciais nas categorias 6M: método, mão de obra, material, máquina, meio, medição.",
        "Engenharia de Produção", ["prod", "qualidade"]
    ),
    _q(
        "O lote econômico de compra (LEC) no modelo de Wilson é calculado como:",
        ["√(2·D·Cp/Ce), onde D é a demanda, Cp o custo de pedir e Ce o custo de estocar.",
         "D·Cp/Ce.",
         "D·Ce/Cp.",
         "Cp·Ce/D².",
         "2·D·Cp·Ce."],
        0,
        "LEC = √(2·D·Cp/Ce). É o lote que minimiza a soma dos custos de pedir e estocar, equilíbrio entre frequência e volume de compras.",
        "Engenharia de Produção", ["prod", "estoques"]
    ),
    _q(
        "O balanceamento de linha de produção tem como objetivo principal:",
        ["Reduzir o número de operadores ao mínimo possível.",
         "Distribuir as tarefas entre as estações de trabalho de modo a minimizar o tempo ocioso e aproximar os tempos de ciclo ao takt time.",
         "Aumentar a velocidade das máquinas de produção.",
         "Eliminar os estoques entre as estações de trabalho.",
         "Automatizar completamente o processo produtivo."],
        1,
        "Balanceamento de linha busca igualar os tempos de cada estação ao takt time (ritmo da demanda), minimizando ociosidade e gargalos.",
        "Engenharia de Produção", ["prod", "pcp"]
    ),
    #
    # Engenharia Civil (3)
    #
    _q(
        "No dimensionamento de vigas de concreto armado, a altura útil (d) é definida como:",
        ["A altura total da viga.",
         "A distância do centro de gravidade da armadura tracionada até a fibra mais comprimida de concreto.",
         "A espessura do cobrimento de concreto.",
         "A distância entre o centro das armaduras tracionada e comprimida.",
         "A altura da linha neutra da seção."],
        1,
        "Altura útil d = h − c − φ/2, onde h é altura total, c o cobrimento e φ o diâmetro da armadura. É usada no cálculo de Momento Resistente (NBR 6118).",
        "Engenharia Civil", ["civil", "concreto"]
    ),
    _q(
        "No ensaio de compactação de solos (Proctor Normal), a energia de compactação aplicada é de aproximadamente:",
        ["6.000 kJ/m³.",
         "12.000 kJ/m³.",
         "600 kJ/m³.",
         "25.000 kJ/m³.",
         "2.500 kJ/m³."],
        2,
        "Energia Proctor Normal: 3 camadas × 26 golpes × 2,49 kg × 0,305 m / volume do molde ≈ 600 kJ/m³ (NBR 7182).",
        "Engenharia Civil", ["civil", "solos"]
    ),
    _q(
        "A NBR 9050 estabelece critérios de acessibilidade. A largura mínima para circulação de uma pessoa em cadeira de rodas em linha reta é de:",
        ["0,60 m.",
         "0,80 m.",
         "0,90 m.",
         "1,00 m.",
         "1,20 m."],
        2,
        "NBR 9050: largura mínima para deslocamento linear de cadeira de rodas é 0,90 m. Para rotação de 90°, mínimo de 1,20 m.",
        "Engenharia Civil", ["civil", "normas"]
    ),
    #
    # Engenharia Mecânica (3)
    #
    _q(
        "O fator de segurança em projetos de elementos mecânicos é definido como a razão entre:",
        ["A tensão admissível e a tensão de escoamento.",
         "A tensão de ruptura e a tensão admissível, ou entre a resistência do material e a tensão atuante.",
         "O módulo de Young e a tensão de escoamento.",
         "A deformação plástica e a deformação elástica.",
         "A carga estática e a carga dinâmica aplicada."],
        1,
        "Fator de segurança (FS) = Resistência do material / Tensão atuante. Valores típicos: 1,5 a 3,0 para cargas estáticas (NBR 8400, ASME).",
        "Engenharia Mecânica", ["mec", "resistencia"]
    ),
    _q(
        "No diagrama tensão-deformação de um aço carbono, o patamar de escoamento caracteriza-se por:",
        ["Grande aumento de tensão com pequena deformação.",
         "Deformação significativa sem aumento de tensão (escoamento definido).",
         "Ruptura imediata após o limite de proporcionalidade.",
         "Comportamento perfeitamente elástico até a ruptura.",
         "Ausência de deformação plástica antes da ruptura."],
        1,
        "Aços carbono (como CA-25 e CA-50) apresentam patamar de escoamento bem definido, com deformação plástica a tensão constante (NBR 6118, NBR 7480).",
        "Engenharia Mecânica", ["mec", "materiais"]
    ),
    _q(
        "A eficiência de uma máquina térmica operando entre dois reservatórios térmicos, segundo Carnot, é máxima quando:",
        ["O ciclo é reversível e opera entre as temperaturas T₁ (quente) e T₂ (fria), com η = 1 − T₂/T₁.",
         "A máquina opera em ciclo aberto com combustão interna.",
         "O fluido de trabalho é o vapor d'água.",
         "A temperatura do reservatório frio é igual à temperatura do reservatório quente.",
         "A máquina opera com regeneração de calor."],
        0,
        "Ciclo de Carnot: η_máx = 1 − T_fria/T_quente (em Kelvin). Nenhuma máquina térmica pode ter eficiência maior que a de Carnot (2ª Lei).",
        "Engenharia Mecânica", ["mec", "termo"]
    ),
    #
    # Engenharia Elétrica (3)
    #
    _q(
        "Em circuitos trifásicos equilibrados ligados em estrela (Y), a relação entre tensão de linha (V_L) e tensão de fase (V_F) é:",
        ["V_L = V_F.",
         "V_L = √3 · V_F.",
         "V_L = V_F / √3.",
         "V_L = 3 · V_F.",
         "V_L = 2 · V_F."],
        1,
        "Na ligação estrela equilibrada, V_L = √3 × V_F e I_L = I_F. Exemplo: 380 V de linha corresponde a 220 V de fase.",
        "Engenharia Elétrica", ["ele", "circuitos"]
    ),
    _q(
        "A grandeza elétrica medida em volts-ampères reativos (VAr) é:",
        ["Potência ativa.",
         "Potência aparente.",
         "Potência reativa.",
         "Fator de potência.",
         "Energia elétrica consumida."],
        2,
        "Potência reativa (Q) é medida em VAr. Potência ativa (P) em W, potência aparente (S) em VA. Q = S·sen φ, P = S·cos φ.",
        "Engenharia Elétrica", ["ele", "potencia"]
    ),
    _q(
        "No sistema elétrico de potência, a função do disjuntor é:",
        ["Medir o consumo de energia elétrica.",
         "Transformar níveis de tensão entre circuitos.",
         "Interromper correntes de falta (curto-circuito) e manobrar circuitos sob carga de forma segura.",
         "Corrigir o fator de potência da instalação.",
         "Proteger contra sobretensões atmosféricas."],
        2,
        "Disjuntor é um dispositivo de manobra e proteção que interrompe correntes de falta e de carga, ao contrário da chave seccionadora (sem carga).",
        "Engenharia Elétrica", ["ele", "protecao"]
    ),
    #
    # Engenharia Química (4)
    #
    _q(
        "Em um trocador de calor de casco e tubos, o aumento do número de passes nos tubos tem como efeito:",
        ["Reduzir a área de troca térmica.",
         "Aumentar a velocidade do fluido nos tubos e o coeficiente global de transferência de calor.",
         "Diminuir a perda de carga do sistema.",
         "Eliminar a necessidade de chicanas no casco.",
         "Reduzir a temperatura de saída do fluido quente."],
        1,
        "Múltiplos passes nos tubos aumentam a velocidade do fluido, elevando o coeficiente de película (h) e melhorando a troca térmica, mas aumentam a perda de carga.",
        "Engenharia Química", ["quim", "transporte"]
    ),
    _q(
        "A equação de Antoine é utilizada para estimar:",
        ["A viscosidade de líquidos puros em função da temperatura.",
         "A pressão de vapor de substâncias puras em função da temperatura.",
         "A condutividade térmica de gases.",
         "A difusividade mássica em meios porosos.",
         "A velocidade de reação em catalisadores sólidos."],
        1,
        "Equação de Antoine: log₁₀(P_vap) = A − B/(C + T), onde A, B, C são constantes específicas. Amplamente usada para estimar pressão de vapor.",
        "Engenharia Química", ["quim", "termo"]
    ),
    _q(
        "Na destilação flash (equilíbrio), a separação ocorre quando:",
        ["O líquido é aquecido em batelada até a ebulição total.",
         "A alimentação é parcialmente vaporizada em um único estágio de equilíbrio, separando vapor e líquido em equilíbrio.",
         "O vapor é condensado fracionadamente em vários estágios.",
         "A alimentação é resfriada abaixo do ponto de congelamento.",
         "O líquido é centrifugado para separação de fases."],
        1,
        "Destilação flash: a alimentação passa por uma válvula de expansão ou aquecedor, gerando duas fases (vapor e líquido) em equilíbrio em um vaso de separação.",
        "Engenharia Química", ["quim", "operacoes"]
    ),
    _q(
        "O catalisador utilizado no processo de reforma catalítica em refinarias é normalmente:",
        ["Carbono ativado.",
         "Zeólita ácida.",
         "Platina suportada em alumina.",
         "Óxido de ferro.",
         "Sílica gel."],
        2,
        "A reforma catalítica usa catalisador bimetálico de platina e rênio suportado em alumina, promovendo a aromatização e reforma de naftas para produção de gasolina de alta octanagem.",
        "Engenharia Química", ["quim", "petroquimica"]
    ),
    #
    # Direito Administrativo (20) — Lei 14.133/2021, atos, poderes, servidores, improbidade, concessões
    #
    _q(
        "A nova Lei de Licitações e Contratos Administrativos (Lei 14.133/2021) estabelece como um de seus princípios:",
        ["Discricionariedade absoluta do gestor público.",
         "Planejamento e desenvolvimento nacional sustentável.",
         "Prevalência do interesse privado sobre o interesse público.",
         "Sigilo absoluto dos processos licitatórios.",
         "Contratação direta como regra geral."],
        1,
        "Art. 5º da Lei 14.133/2021: o planejamento e o desenvolvimento nacional sustentável são princípios expressos, ao lado da legalidade, impessoalidade, moralidade, publicidade e eficiência.",
        "Direito Administrativo", ["14133"]
    ),
    _q(
        "Segundo a Lei 14.133/2021, o modo de disputa 'diálogo competitivo' é cabível quando:",
        ["O valor da licitação for inferior a R$ 100.000,00.",
         "A administração pública não dispuser de meios suficientes para definir os melhores meios técnicos para atender suas necessidades.",
         "A contratação for de baixa complexidade técnica.",
         "O objeto da licitação for padronizado e de prateleira.",
         "O certame for exclusivo para micro e pequenas empresas."],
        1,
        "Art. 6º, XLI e Art. 32 da Lei 14.133/2021: o diálogo competitivo é aplicável quando a administração não tem meios de definir a melhor solução técnica, cabendo aos licitantes apresentar propostas após diálogo.",
        "Direito Administrativo", ["14133"]
    ),
    _q(
        "Os requisitos mínimos para a caracterização do ato administrativo são:",
        ["Competência, finalidade, forma, motivo e objeto.",
         "Capacidade, legitimidade, oportunidade e conveniência.",
         "Razoabilidade, proporcionalidade, eficiência e moralidade.",
         "Autorização, permissão, concessão e licença.",
         "Amplitude, duração, executoriedade e tipicidade."],
        0,
        "Ato administrativo tem 5 requisitos: competência (sujeito), finalidade (interesse público), forma (prevista em lei), motivo (fundamento fático/jurídico), objeto (conteúdo).",
        "Direito Administrativo", ["atosadm"]
    ),
    _q(
        "O atributo da autoexecutoriedade dos atos administrativos significa que:",
        ["O ato pode ser anulado pelo Judiciário a qualquer tempo.",
         "A administração pode executar direta e imediatamente o ato, sem necessidade de intervenção judicial prévia.",
         "O ato deve ser previamente aprovado pelo Legislativo.",
         "O beneficiário do ato pode executá-lo por conta própria.",
         "O ato não pode ser revogado pela administração."],
        1,
        "Autoexecutoriedade: a administ pública pode impor suas decisões independentemente de ordem judicial. Ex: multa de trânsito, interdição de estabelecimento (dentro dos limites legais).",
        "Direito Administrativo", ["atosadm"]
    ),
    _q(
        "O poder de polícia da administração pública, segundo o Código Tributário Nacional (Art. 78), caracteriza-se por:",
        ["Atividade exclusiva do Poder Judiciário.",
         "Atividade da administração pública que, limitando ou disciplinando direito, interesse ou liberdade, regula a prática de ato em razão do interesse público.",
         "Poder ilimitado do Estado sobre a propriedade privada.",
         "Poder exclusivo para criar tributos.",
         "Atividade legislativa de criar leis penais."],
        1,
        "CTN Art. 78: poder de polícia é a atividade da administração que, no exercício de sua competência, condiciona o exercício de direitos em benefício do interesse público.",
        "Direito Administrativo", ["poderes"]
    ),
    _q(
        "O poder hierárquico no âmbito da administração pública autoriza o superior a:",
        ["Punir diretamente os administrados por infrações de trânsito.",
         "Delegar e avocar competências, editar atos de organização e supervisionar a atividade dos subordinados.",
         "Criar tributos por decreto.",
         "Legislar sobre matéria de competência privativa da União.",
         "Anular atos do Poder Judiciário."],
        1,
        "Poder hierárquico: relação de subordinação entre órgãos e agentes. Permite delegar, avocar, coordenar, fiscalizar, dar ordens (não se confunde com poder disciplinar).",
        "Direito Administrativo", ["poderes"]
    ),
    _q(
        "A investidura em cargo público, de acordo com a CF/88, depende de aprovação prévia em concurso público, ressalvadas:",
        ["As nomeações para cargo em comissão declarado em lei de livre nomeação e exoneração.",
         "Apenas os cargos de ministro do STF.",
         "Todos os cargos do Poder Legislativo.",
         "Os cargos de presidente da República e governadores.",
         "As funções de confiança de qualquer natureza."],
        0,
        "Art. 37, II da CF/88: a investidura em cargo ou emprego público depende de concurso público, exceto para cargos em comissão de livre nomeação e exoneração.",
        "Direito Administrativo", ["servidores"]
    ),
    _q(
        "A Lei 8.429/1992 (Lei de Improbidade Administrativa), com as alterações da Lei 14.230/2021, considera ato de improbidade que atenta contra os princípios da administração pública:",
        ["Deixar de prestar contas quando obrigatório.",
         "Qualquer ação ou omissão que viole os deveres de honestidade, imparcialidade, legalidade e lealdade às instituições.",
         "Apenas o enriquecimento ilícito do agente público.",
         "Apenas a lesão ao erário.",
         "A contratação de parentes para cargos comissionados."],
        1,
        "Art. 11 da Lei 8.429/1992: violação aos princípios da administração pública (honestidade, imparcialidade, legalidade, lealdade) constitui ato de improbidade, independentemente de dano ao erário.",
        "Direito Administrativo", ["improbidade"]
    ),
    _q(
        "Na concessão de serviço público, a transferência da prestação do serviço ao concessionário é feita mediante:",
        ["Contrato administrativo precedido de licitação, com prazo determinado e riscos assumidos pelo concessionário.",
         "Decreto presidencial sem licitação.",
         "Autorização legislativa específica e contrato de trabalho temporário.",
         "Permissão unilateral e precária do poder concedente.",
         "Acordo internacional entre Estados."],
        0,
        "Lei 8.987/1995, Art. 2º, II c/c Art. 14: concessão de serviço público é precedida de licitação, com contrato administrativo de prazo determinado, riscos do concessionário.",
        "Direito Administrativo", ["concessoes"]
    ),
    _q(
        "A modalidade de licitação 'pregão', prevista na Lei 14.133/2021, destina-se à contratação de:",
        ["Obras de engenharia de grande porte.",
         "Bens e serviços comuns, cujos padrões de desempenho e qualidade possam ser objetivamente definidos pelo edital.",
         "Serviços técnicos especializados de natureza predominantemente intelectual.",
         "Concessão de serviços públicos.",
         "Contratação de obras de arte e restauro."],
        1,
        "Art. 6º, XLI e Art. 28 da Lei 14.133/2021: pregão é a modalidade para aquisição de bens e serviços comuns, com disputa por lances em sessão pública.",
        "Direito Administrativo", ["14133"]
    ),
    _q(
        "Os contratos administrativos, segundo a Lei 14.133/2021, podem ser alterados unilateralmente pela administração quando:",
        ["Houver acordo entre as partes para reduzir o valor contratual.",
         "Ocorrer modificação do projeto ou das especificações técnicas, para melhor adequação técnica aos interesses da administração.",
         "O contratante solicitar aumento do valor em até 50%.",
         "A administração decidir suspender o contrato por tempo indeterminado.",
         "O contrato for de fornecimento de bens de prateleira."],
        1,
        "Art. 124, I da Lei 14.133/2021: a administração pode alterar unilateralmente o contrato quando houver modificação do projeto ou especificações para melhor adequação técnica.",
        "Direito Administrativo", ["14133"]
    ),
    _q(
        "O servidor público estável, segundo a CF/88, perderá o cargo:",
        ["A qualquer tempo, por decisão discricionária do chefe do executivo.",
         "Em virtude de sentença judicial transitada em julgado ou mediante processo administrativo disciplinar com ampla defesa, ou por avaliação periódica de desempenho na forma de lei complementar.",
         "Apenas por vontade própria mediante pedido de exoneração.",
         "Exclusivamente por condenação criminal irrecorrível.",
         "Por decreto do chefe do executivo sem necessidade de processo."],
        1,
        "Art. 41, §1º da CF/88: o servidor estável perde o cargo por sentença judicial transitada em julgado, PAD com ampla defesa, ou avaliação periódica de desempenho na forma de lei complementar.",
        "Direito Administrativo", ["servidores"]
    ),
    _q(
        "Classificam-se como atos administrativos vinculados aqueles em que:",
        ["A administração tem liberdade de escolha quanto à conveniência e oportunidade.",
         "Todos os elementos do ato são predeterminados em lei, não havendo margem de escolha ao administrador.",
         "O ato depende de autorização legislativa prévia.",
         "O administrador pode decidir com base em critérios de mérito administrativo.",
         "O ato é praticado exclusivamente pelo chefe do executivo."],
        1,
        "Ato vinculado: lei define todos os requisitos (competência, forma, motivo, objeto, finalidade). Ex: licença para dirigir. Ato discricionário: margem de escolha (juízo de conveniência e oportunidade).",
        "Direito Administrativo", ["atosadm"]
    ),
    _q(
        "A responsabilidade civil do Estado por danos causados por seus agentes é, no Brasil:",
        ["Subjetiva, exigindo comprovação de dolo ou culpa do agente.",
         "Objetiva, com base na teoria do risco administrativo, independentemente de culpa do agente, assegurado o direito de regresso contra o agente causador.",
         "Inexistente, pois o Estado não responde por atos de seus agentes.",
         "Limitada a danos materiais, excluídos danos morais.",
         "Exclusiva do agente público, não alcançando a pessoa jurídica."],
        1,
        "Art. 37, §6º da CF/88: responsabilidade objetiva do Estado (teoria do risco administrativo). O Estado responde independentemente de culpa, com direito de regresso contra o agente em caso de dolo ou culpa.",
        "Direito Administrativo", ["responsabilidade"]
    ),
    _q(
        "O princípio da publicidade na administração pública admite exceções quando:",
        ["O ato for praticado por autoridade de alto escalão.",
         "A imprensa solicitar sigilo sobre determinada informação.",
         "A defesa da intimidade ou o interesse social assim o exigirem, nas hipóteses previstas em lei.",
         "O administrador público considerar inconveniente a divulgação.",
         "O ato for praticado em período eleitoral."],
        2,
        "Art. 5º, X e XXXIII da CF/88: a publicidade é regra, mas admite exceções para proteção da intimidade, vida privada, honra e imagem, ou quando exigido pelo interesse público.",
        "Direito Administrativo", ["principios"]
    ),
    _q(
        "A desapropriação por utilidade pública é ato administrativo pelo qual o Estado:",
        ["Toma temporariamente a posse de bem particular.",
         "Transfere a titularidade de bem particular para o poder público, mediante indenização prévia e justa, em dinheiro, salvo exceções constitucionais.",
         "Aluga imóvel particular para uso público.",
         "Requisita bens particulares em caso de iminente perigo público.",
         "Confisca bens de criminosos condenados."],
        1,
        "Decreto-Lei 3.365/1941 e CF/88 Art. 5º, XXIV: desapropriação é a transferência compulsória da propriedade particular ao poder público, mediante indenização prévia e justa.",
        "Direito Administrativo", ["desapropriacao"]
    ),
    _q(
        "O controle da administração pública pelo Tribunal de Contas é classificado como:",
        ["Controle político exclusivo.",
         "Controle externo, de natureza técnica e financeira, auxiliando o Poder Legislativo na fiscalização contábil, financeira e orçamentária.",
         "Controle interno da própria administração.",
         "Controle judicial privativo do Supremo Tribunal Federal.",
         "Controle social exercido pelo Ministério Público."],
        1,
        "CF/88 Art. 70: o controle externo é exercido pelo Congresso Nacional com auxílio do TCU, abrangendo aspectos contábeis, financeiros, orçamentários, operacionais e patrimoniais.",
        "Direito Administrativo", ["controle"]
    ),
    _q(
        "O regime jurídico dos servidores públicos civis da União (Lei 8.112/1990) estabelece como requisito básico para ingresso no serviço público:",
        ["Ter no mínimo 25 anos de idade.",
         "Aprovação em concurso público de provas ou de provas e títulos.",
         "Indicação política para cargo comissionado.",
         "Ter cursado universidade pública.",
         "Residir no Distrito Federal."],
        1,
        "Lei 8.112/1990, Art. 5º: são requisitos básicos para investidura em cargo público, entre outros, a aprovação em concurso público de provas ou de provas e títulos.",
        "Direito Administrativo", ["servidores"]
    ),
    _q(
        "Na licitação da modalidade 'concorrência', segundo a Lei 14.133/2021, é obrigatória:",
        ["A participação exclusiva de micro e pequenas empresas.",
         "A fase de julgamento de propostas técnicas antes da fase de lances, quando o critério de julgamento for técnica e preço.",
         "A dispensa de publicação de edital no Diário Oficial.",
         "A realização do certame exclusivamente na modalidade eletrônica.",
         "A contratação direta sem licitação prévia."],
        1,
        "Art. 31 da Lei 14.133/2021: a concorrência pode adotar o critério de técnica e preço, com fase de julgamento técnico antes da fase competitiva de lances.",
        "Direito Administrativo", ["14133"]
    ),
    _q(
        "A anulação do ato administrativo, quando ilegal, pode ser realizada:",
        ["Exclusivamente pelo Poder Judiciário.",
         "Pela administração pública, de ofício, ou pelo Poder Judiciário, com efeitos retroativos (ex tunc).",
         "Apenas pelo Congresso Nacional.",
         "Somente pelo chefe do Poder Executivo, sem possibilidade de controle judicial.",
         "Exclusivamente pelo Tribunal de Contas da União."],
        1,
        "Súmula 473 do STF: a administração pode anular seus próprios atos, quando eivados de vícios ilegais, ou revogá-los por motivo de conveniência ou oportunidade, respeitados direitos adquiridos.",
        "Direito Administrativo", ["atosadm"]
    ),
    #
    # Meio Ambiente (12) — PNMA, CONAMA, licenciamento, EIA/RIMA, recursos hídricos
    #
    _q(
        "A Política Nacional do Meio Ambiente (Lei 6.938/1981) tem como um de seus instrumentos:",
        ["A criação de impostos ambientais municipais.",
         "O licenciamento ambiental e a avaliação de impactos ambientais.",
         "A privatização de unidades de conservação.",
         "A proibição total de atividades industriais.",
         "O confisco de propriedades rurais produtivas."],
        1,
        "Art. 9º da Lei 6.938/1981: são instrumentos da PNMA o licenciamento ambiental, a avaliação de impactos ambientais, o zoneamento ambiental, entre outros.",
        "Meio Ambiente", ["pnma"]
    ),
    _q(
        "O Conselho Nacional do Meio Ambiente (CONAMA), criado pela Lei 6.938/1981, é:",
        ["Um órgão executor da política ambiental.",
         "Um órgão consultivo e deliberativo com participação de setores públicos e da sociedade civil, que estabelece normas e padrões ambientais.",
         "Uma autarquia federal com poder de polícia ambiental.",
         "Um fundo financeiro para projetos ambientais.",
         "Uma entidade privada de certificação ambiental."],
        1,
        "Lei 6.938/1981, Art. 6º, II: CONAMA é órgão consultivo e deliberativo, com representação de órgãos federais, estaduais, municipais e sociedade civil, que expede resoluções ambientais.",
        "Meio Ambiente", ["conama"]
    ),
    _q(
        "O licenciamento ambiental de empreendimentos de significativo impacto ambiental exige a elaboração de:",
        ["Apenas um relatório fotográfico da área.",
         "Estudo Prévio de Viabilidade Econômica.",
         "Estudo de Impacto Ambiental (EIA) e seu respectivo Relatório de Impacto Ambiental (RIMA).",
         "Apenas uma declaração do empreendedor sobre os impactos.",
         "Um laudo técnico de segurança do trabalho."],
        2,
        "Resolução CONAMA 01/86 e CF/88 Art. 225, §1º, IV: o EIA/RIMA é exigido para atividades de significativo impacto ambiental, com publicidade e participação social.",
        "Meio Ambiente", ["eia"]
    ),
    _q(
        "A Política Nacional de Recursos Hídricos (Lei 9.433/1997) fundamenta-se no princípio de que:",
        ["A água é um bem de domínio público e recurso natural limitado, dotado de valor econômico.",
         "A água é um bem infinito e gratuito.",
         "A água pertence exclusivamente aos Estados.",
         "O uso da água independe de outorga do poder público.",
         "As águas subterrâneas são de propriedade do proprietário do solo."],
        0,
        "Art. 1º, I e II da Lei 9.433/1997: a água é bem de domínio público, recurso natural limitado e dotado de valor econômico.",
        "Meio Ambiente", ["recursoshidricos"]
    ),
    _q(
        "O Sistema Nacional do Meio Ambiente (SISNAMA), instituído pela Lei 6.938/1981, é composto:",
        ["Exclusivamente pelo IBAMA e ICMBio.",
         "Por órgãos e entidades da União, Estados, DF e Municípios responsáveis pela proteção e melhoria da qualidade ambiental.",
         "Apenas por organizações não governamentais ambientais.",
         "Exclusivamente pelo Ministério do Meio Ambiente.",
         "Por empresas privadas do setor de consultoria ambiental."],
        1,
        "Art. 6º da Lei 6.938/1981: SISNAMA é a estrutura de órgãos e entidades da União, Estados, DF e Municípios, com o CONAMA como órgão consultivo e deliberativo.",
        "Meio Ambiente", ["sisnama"]
    ),
    _q(
        "As unidades de conservação de uso sustentável, segundo a Lei 9.985/2000 (SNUC), permitem:",
        ["Apenas visitação científica autorizada.",
         "A exploração do ambiente de forma compatível com a conservação dos recursos naturais renováveis.",
         "A ocupação humana permanente com atividades industriais.",
         "A exploração mineral ilimitada.",
         "Apenas pesquisa científica sem qualquer uso econômico."],
        1,
        "Lei 9.985/2000, Art. 7º, II: unidades de uso sustentável visam compatibilizar a conservação da natureza com o uso sustentável de parcela dos recursos naturais.",
        "Meio Ambiente", ["snuc"]
    ),
    _q(
        "A Resolução CONAMA 237/1997 estabelece que o licenciamento ambiental é composto por:",
        ["Apenas a Licença Prévia (LP).",
         "Três fases: Licença Prévia (LP), Licença de Instalação (LI) e Licença de Operação (LO).",
         "Duas fases: Licença Ambiental Simplificada e Licença de Instalação.",
         "Apenas a Licença de Operação (LO), renovável anualmente.",
         "Cinco fases: LP, LI, LO, LA e LC."],
        1,
        "Res. CONAMA 237/97, Art. 8º: LP (viabilidade), LI (instalação), LO (operação). Cada licença tem prazo de validade e condicionantes específicos.",
        "Meio Ambiente", ["licenciamento"]
    ),
    _q(
        "Segundo a Lei 9.433/1997, a outorga de direito de uso de recursos hídricos é:",
        ["Dispensável para qualquer tipo de uso.",
         "Ato administrativo mediante o qual o poder público concede ao usuário o direito de utilizar recursos hídricos, por prazo determinado.",
         "Uma autorização verbal do órgão ambiental.",
         "Um contrato de concessão de serviço público.",
         "Um título de propriedade sobre o corpo d'água."],
        1,
        "Art. 12 e 14 da Lei 9.433/1997: outorga é ato administrativo de autorização para uso de recursos hídricos, com prazo determinado, sujeito a prioridades de uso.",
        "Meio Ambiente", ["recursoshidricos"]
    ),
    _q(
        "O princípio do poluidor-pagador, reconhecido no direito ambiental brasileiro, significa que:",
        ["O poluidor pode poluir desde que pague uma multa.",
         "O causador de degradação ambiental deve arcar com os custos de prevenção, reparação e compensação dos danos causados.",
         "Apenas empresas de grande porte são responsáveis por danos ambientais.",
         "O pagamento de taxa ambiental autoriza a poluição ilimitada.",
         "O Estado é o único responsável pela reparação de danos ambientais."],
        1,
        "Lei 6.938/1981, Art. 4º, VII e Art. 14, §1º: responsabilidade objetiva do poluidor, que deve indenizar ou reparar os danos causados ao meio ambiente, independentemente de culpa.",
        "Meio Ambiente", ["principios"]
    ),
    _q(
        "A avaliação de impacto ambiental (AIA) é definida como:",
        ["Um parecer técnico sobre a viabilidade econômica de um projeto.",
         "Um instrumento de política ambiental que identifica, prevê, interpreta e comunica os impactos de um projeto sobre o meio ambiente.",
         "Uma vistoria fiscal para aplicação de multas.",
         "Um relatório contábil de custos ambientais.",
         "Uma auditoria de conformidade legal das empresas."],
        1,
        "Res. CONAMA 01/86: AIA é o processo que estuda os impactos ambientais de um empreendimento, culminando no EIA/RIMA e subsidiando o licenciamento.",
        "Meio Ambiente", ["eia"]
    ),
    _q(
        "As florestas na Amazônia Legal, segundo a CF/88, são consideradas:",
        ["Propriedade privada disponível para exploração ilimitada.",
         "Bem de uso comum do povo, e sua exploração depende de autorização do poder público, com preservação da vegetação nativa em percentual mínimo.",
         "Áreas de proteção integral onde qualquer atividade é proibida.",
         "Bens da União intransferíveis e inexploráveis.",
         "Áreas de domínio exclusivo dos Estados da Amazônia Legal."],
        1,
        "Art. 225 da CF/88 e Código Florestal (Lei 12.651/2012): a Floresta Amazônica é bem de interesse comum, com exploração condicionada à preservação de reserva legal (80% na Amazônia).",
        "Meio Ambiente", ["florestal"]
    ),
    _q(
        "A compensação ambiental, prevista na Lei 9.985/2000 (SNUC), é devida por empreendimentos de significativo impacto ambiental e consiste em:",
        ["Pagamento de multa administrativa ao IBAMA.",
         "Apoiar a implantação e manutenção de unidade de conservação do Grupo de Proteção Integral, no mínimo 0,5% dos custos do empreendimento.",
         "Doação voluntária de mudas para reflorestamento urbano.",
         "Contratação de seguro ambiental privado.",
         "Investimento em marketing verde pela empresa empreendedora."],
        1,
        "Art. 36 da Lei 9.985/2000: o empreendedor deve apoiar a implantação e manutenção de UC de proteção integral, com valor mínimo de 0,5% dos custos do empreendimento.",
        "Meio Ambiente", ["snuc"]
    ),

    _q(
        "O hidrogênio verde é produzido a partir de fontes renováveis por meio do processo de:",
        ["Eletrólise da água utilizando energia solar ou eólica.",
         "Craqueamento térmico do gás natural.",
         "Gaseificação do carvão mineral.",
         "Reforma a vapor do metano sem captura de carbono.",
         "Destilação fracionada do petróleo."],
        0,
        "O hidrogênio verde é obtido por eletrólise da água usando energia de fontes renováveis (solar, eólica), sem emissão de CO₂ no processo.",
        "Atualidades", ["hidrogenio", "energia"]
    ),
    _q(
        "A matriz elétrica brasileira caracteriza-se por ter predominantemente:",
        ["Fontes térmicas a carvão.",
         "Fontes hidrelétricas, complementadas por eólica, solar e biomassa.",
         "Energia nuclear como principal fonte.",
         "Geração distribuída por painéis solares em todas as residências.",
         "Usinas termelétricas a óleo combustível."],
        1,
        "O Brasil possui uma das matrizes elétricas mais renováveis do mundo, com cerca de 60-65% de energia hidrelétrica, complementada por eólica, solar e biomassa.",
        "Atualidades", ["matriz", "energia"]
    ),
    _q(
        "A geração de energia eólica offshore (no mar) no Brasil:",
        ["Já é a principal fonte de energia do país.",
         "Está em fase de desenvolvimento regulatório e projetos-piloto, com grande potencial na costa brasileira.",
         "É proibida por lei federal.",
         "Não apresenta viabilidade técnica devido à plataforma continental rasa.",
         "Depende exclusivamente de investimento estatal."],
        1,
        "O Brasil tem enorme potencial eólico offshore (costa extensa, ventos fortes), com o Decreto 10.946/2022 e projetos em licenciamento pelo IBAMA, mas a fonte ainda não é comercial em larga escala.",
        "Atualidades", ["eolica", "energia"]
    ),
    _q(
        "O Brasil é membro fundador da Agência Internacional de Energia (IEA):",
        ["Verdadeiro, desde 1974.",
         "Falso, o Brasil é membro associado da IEA desde 2017, mas não membro pleno da OCDE.",
         "Verdadeiro, o Brasil participa como membro pleno desde 2015.",
         "Falso, o Brasil não tem nenhum vínculo com a IEA.",
         "Verdadeiro, pois a IEA foi criada pela Petrobras."],
        1,
        "O Brasil tornou-se membro associado da IEA em 2017 (país de transição), buscando a adesão plena à OCDE, condição para membro pleno da Agência Internacional de Energia.",
        "Atualidades", ["iea", "energia"]
    ),
    _q(
        "A política de preços dos combustíveis adotada pela Petrobras a partir de 2016 era conhecida como:",
        ["Paridade de Preços de Importação (PPI), alinhando os preços internos ao mercado internacional.",
         "Congelamento de preços por decreto presidencial.",
         "Preço único nacional definido pela ANP.",
         "Subsídio integral do diesel pelo Tesouro Nacional.",
         "Cálculo baseado exclusivamente no custo de produção interno."],
        0,
        "O PPI (Paridade de Preços de Importação), praticado de 2016 a 2023, alinhava os preços internos de diesel, gasolina e GLP às cotações internacionais do petróleo e câmbio.",
        "Atualidades", ["petrobras", "precos"]
    ),
    _q(
        "O mercado de carbono regulado no Brasil foi instituído pela:",
        ["Lei 12.187/2009 (Política Nacional sobre Mudança do Clima), que criou o Sistema Brasileiro de Comércio de Emissões (SBCE).",
         "Lei 9.478/1997, no âmbito da ANP.",
         "Resolução CONAMA 237/1997.",
         "Decreto 10.946/2022 sobre energia eólica offshore.",
         "Lei 13.303/2016, artigo sobre sustentabilidade."],
        0,
        "A PNMC (Lei 12.187/2009) instituiu o SBCE como instrumento, mas o mercado regulado foi efetivamente operacionalizado pelo Decreto 11.075/2022 e Lei 14.120/2021.",
        "Atualidades", ["carbono", "clima"]
    ),
    _q(
        "A refinaria REPAR (Refinaria Presidente Getúlio Vargas) está localizada em:",
        ["Canoas (RS).",
         "São José dos Campos (SP).",
         "Duque de Caxias (RJ).",
         "Mataripe (BA).",
         "Paulínia (SP)."],
        0,
        "A REPAR está em Canoas/RS, com capacidade de processamento de cerca de 200 mil barris/dia, abastecendo a região Sul do Brasil.",
        "Atualidades", ["petrobras", "refino"]
    ),
    _q(
        "O BNDES financia projetos de inovação e infraestrutura no setor de petróleo e gás por meio de programas como:",
        ["FUNTEC, BNDES Automático e BNDES Finem, com linhas específicas para o setor de O&G.",
         "Apenas por meio de doações diretas a empresas estatais.",
         "Financiamento exclusivo de projetos de energia solar.",
         "Crédito rotativo para capital de giro sem análise técnica.",
         "Convênios com universidades sem contrapartida financeira."],
        0,
        "O BNDES apoia o setor de O&G com financiamentos de longo prazo via BNDES Finem (projetos de investimento), BNDES Automático (máquinas) e FUNTEC (inovação tecnológica).",
        "Atualidades", ["bndes", "financiamento"]
    ),
    _q(
        "O gás natural veicular (GNV) é composto predominantemente por:",
        ["Propano e butano.",
         "Metano (CH₄), com pequenas frações de etano e outros hidrocarbonetos leves.",
         "Hidrogênio puro.",
         "Monóxido de carbono e hidrogênio.",
         "Nitrogênio e oxigênio."],
        1,
        "O GNV é basicamente metano (CH₄), o hidrocarboneto mais leve, com pequenas quantidades de etano, propano e inertes, dependendo da origem do gás natural.",
        "Atualidades", ["gnv", "gas"]
    ),
    _q(
        "A participação da Petrobras no mercado brasileiro de derivados de petróleo, após a abertura do mercado em 2023-2024:",
        ["Permaneceu como monopolista em toda a cadeia.",
         "Reduziu sua participação no refino e na distribuição, com novos agentes privados atuando na importação e refino.",
         "Manteve monopólio exclusivo da distribuição de combustíveis.",
         "Foi estatizada com capital 100% público.",
         "Encerrou todas as atividades de refino no Brasil."],
        1,
        "Com a abertura do mercado, a Petrobras reduziu sua participação no refino (venda de refinarias como RLAM, REPAR, REGAP) e novos agentes passaram a importar e comercializar derivados, embora a empresa ainda lidere o setor.",
        "Atualidades", ["petrobras", "mercado"]
    ),
    _q(
        "O Pré-Sal foi descoberto em 2006 pela Petrobras na Bacia de Santos, no bloco conhecido como:",
        ["Tupi (hoje Campo de Mero).",
         "Búzios.",
         "Lula (antigo Tupi).",
         "Sépia.",
         "Atapu."],
        2,
        "A descoberta do pré-sal ocorreu em 2006 no bloco BM-S-11, com o poço 1-RJS-628 (Lula), então denominado Tupi, na Bacia de Santos, um dos maiores campos de petróleo do mundo.",
        "Atualidades", ["presal", "petrobras"]
    ),
    _q(
        "A transição energética justa (just transition) no contexto brasileiro busca:",
        ["Eliminar totalmente o petróleo da matriz até 2030.",
         "Conciliar a descarbonização com a geração de empregos, inclusão social e desenvolvimento regional, especialmente nos estados produtores de petróleo.",
         "Substituir todos os empregos do setor de O&G por empregos em energia solar.",
         "Manter inalterada a matriz energética atual.",
         "Privatizar todas as empresas do setor elétrico."],
        1,
        "A transição justa (OIT) envolve políticas que compatibilizam a descarbonização com proteção social, requalificação profissional e desenvolvimento de novas cadeias produtivas nas regiões dependentes de O&G.",
        "Atualidades", ["transicao", "energia"]
    ),
    _q(
        "O Leilão de Energia Nova (LEN) promovido pelo governo brasileiro tem como objetivo:",
        ["Contratar energia de novos empreendimentos de geração para garantir o atendimento futuro ao mercado regulado.",
         "Privatizar usinas hidrelétricas existentes.",
         "Definir o preço da gasolina nas refinarias.",
         "Contratar energia apenas de termelétricas a carvão.",
         "Distribuir subsídios para consumidores de baixa renda."],
        0,
        "O LEN (Leilão de Energia Nova) é promovido pela CCEE e ANEEL para contratar energia de novos empreendimentos (eólicas, solares, térmicas, hidrelétricas) com entrega futura, atendendo às distribuidoras do Ambiente Regulado.",
        "Atualidades", ["energia", "leiloes"]
    ),
    _q(
        "O etanol de cana-de-açúcar brasileiro é classificado internacionalmente como:",
        ["Combustível fóssil de baixa qualidade.",
         "Biocombustível de primeira geração com balanço energético positivo e baixa pegada de carbono.",
         "Derivado do petróleo processado nas usinas de açúcar.",
         "Combustível sintético produzido a partir de carvão mineral.",
         "Resíduo industrial sem valor energético."],
        1,
        "O etanol de cana é um biocombustível renovável de 1ª geração, com balanço energético de até 9:1 (energia gerada/energia fóssil consumida) e redução de até 90% nas emissões de CO₂ comparado à gasolina.",
        "Atualidades", ["etanol", "biocombustivel"]
    ),
    _q(
        "No Microsoft Excel, a função PROCV procura um valor:",
        ["Na primeira coluna de uma tabela e retorna um valor na mesma linha de outra coluna especificada.",
         "Em qualquer coluna à esquerda e retorna o valor à direita.",
         "Apenas em planilhas abertas simultaneamente.",
         "Em células formatadas como moeda exclusivamente.",
         "Considerando apenas valores numéricos inteiros."],
        0,
        "PROCV (procurar verticalmente) busca o valor na primeira coluna de uma matriz tabela e retorna o valor na mesma linha de uma coluna índice especificada, exigindo que o critério esteja na primeira coluna.",
        "Informática", ["excel"]
    ),
    _q(
        "No Windows, a ferramenta 'Desfragmentador de Disco' tem a função de:",
        ["Aumentar a capacidade total do disco rígido.",
         "Reorganizar os dados fragmentados no disco para melhorar o desempenho de leitura/gravação.",
         "Remover arquivos temporários e liberar espaço.",
         "Verificar a integridade física do disco rígido.",
         "Criptografar os dados armazenados no disco."],
        1,
        "A desfragmentação reorganiza os clusters de arquivos que foram fragmentados (espalhados fisicamente) ao longo do tempo, reduzindo o tempo de seek do cabeçote e melhorando o desempenho em HDs mecânicos.",
        "Informática", ["windows"]
    ),
    _q(
        "O protocolo SMTP (Simple Mail Transfer Protocol) é utilizado para:",
        ["Transferir arquivos entre computadores em uma rede.",
         "Enviar mensagens de e-mail entre servidores de correio eletrônico.",
         "Navegar em páginas web de forma segura.",
         "Atribuir endereços IP dinâmicos a dispositivos na rede.",
         "Resolver nomes de domínio em endereços IP."],
        1,
        "SMTP é o protocolo padrão para envio de e-mails na internet, operando na porta 25 (ou 587 com autenticação), transferindo mensagens entre servidores de correio.",
        "Informática", ["redes"]
    ),
    _q(
        "No Microsoft Word, a combinação de teclas Ctrl+Enter insere:",
        ["Uma quebra de página no local do cursor.",
         "Um novo parágrafo com espaçamento duplo.",
         "Uma nota de rodapé.",
         "Um hiperlink para um site externo.",
         "Uma tabela com 3 colunas e 3 linhas."],
        0,
        "Ctrl+Enter insere uma quebra de página manual, forçando o conteúdo seguinte a iniciar em uma nova página, independentemente da formatação automática de margens.",
        "Informática", ["word"]
    ),
    _q(
        "Em redes de computadores, o endereço IP 127.0.0.1 é conhecido como:",
        ["Gateway padrão da rede local.",
         "Loopback (localhost), referindo-se ao próprio computador.",
         "Servidor DNS primário da internet.",
         "Broadcast da sub-rede local.",
         "Endereço de multicast reservado para roteadores."],
        1,
        "127.0.0.1 é o endereço de loopback IPv4, usado para testar a pilha de protocolos TCP/IP localmente, sem tráfego na rede externa (localhost).",
        "Informática", ["redes"]
    ),
    _q(
        "No modelo OSI da ISO, a camada responsável pelo roteamento e definição do caminho dos pacotes entre redes é a camada de:",
        ["Física (camada 1).",
         "Enlace (camada 2).",
         "Rede (camada 3).",
         "Transporte (camada 4).",
         "Sessão (camada 5)."],
        2,
        "A camada de Rede (camada 3 do OSI) é responsável pelo endereçamento lógico (IP) e roteamento, determinando o melhor caminho para os pacotes entre origem e destino em redes distintas.",
        "Informática", ["redes"]
    ),
    _q(
        "No Linux, o comando 'chmod 755 arquivo' atribui à permissão:",
        ["Leitura, escrita e execução para o dono; leitura e execução para grupo e outros.",
         "Apenas leitura para todos os usuários.",
         "Leitura e execução para o dono; apenas execução para grupo e outros.",
         "Leitura e escrita para o dono; apenas leitura para grupo e outros.",
         "Todas as permissões para todos os usuários."],
        0,
        "755 em octal = dono (7 = rwx), grupo (5 = r-x), outros (5 = r-x). O dono tem permissão total; grupo e outros podem ler e executar, mas não escrever.",
        "Informática", ["linux"]
    ),
    _q(
        "O ataque cibernético do tipo ransomware caracteriza-se por:",
        ["Roubar senhas de redes sociais por engenharia social.",
         "Criptografar arquivos da vítima e exigir resgate (pagamento) para liberar o acesso.",
         "Sobrecarregar um servidor com tráfego para torná-lo indisponível (DDoS).",
         "Instalar spyware para monitorar as teclas digitadas (keylogger).",
         "Falsificar o remetente de e-mails para obter informações confidenciais (phishing)."],
        1,
        "Ransomware é um malware que criptografa os arquivos da vítima usando criptografia forte (ex: AES, RSA) e exige pagamento de resgate (em criptomoedas) pela chave de descriptografia.",
        "Informática", ["seguranca"]
    ),
    _q(
        "No Microsoft Outlook, a funcionalidade 'Regras' permite:",
        ["Aplicar formatação condicional em células de e-mail.",
         "Automatizar ações como mover, marcar ou excluir mensagens com base em critérios predefinidos (remetente, assunto, etc.).",
         "Criar macros VBA para controle de caixa postal.",
         "Sincronizar automaticamente com servidores Linux.",
         "Compactar a caixa de entrada para economizar espaço."],
        1,
        "As Regras do Outlook automatizam o gerenciamento de mensagens: movem e-mails para pastas específicas, marcam como lidos, encaminham ou excluem com base em critérios como remetente, palavras-chave no assunto, destinatários, etc.",
        "Informática", ["outlook"]
    ),
    _q(
        "O SharePoint é uma plataforma da Microsoft que permite:",
        ["Editar vídeos profissionais com efeitos especiais.",
         "Criar sites colaborativos, gerenciar documentos, intranets e fluxos de trabalho corporativos.",
         "Desenvolver aplicativos mobile nativos para iOS e Android.",
         "Hospedar máquinas virtuais na nuvem da Microsoft.",
         "Realizar chamadas de vídeo com até 1000 participantes simultâneos."],
        1,
        "SharePoint é uma plataforma colaborativa da Microsoft para gerenciamento de conteúdo corporativo, criação de sites de equipe, portais de intranet, bibliotecas de documentos e workflows colaborativos.",
        "Informática", ["sharepoint"]
    ),
    _q(
        "O formato de arquivo CSV (Comma-Separated Values) é caracterizado por:",
        ["Armazenar dados em formato binário compactado com perdas.",
         "Armazenar dados tabulares em texto simples, onde cada linha é um registro e os campos são separados por delimitadores como vírgula ou ponto e vírgula.",
         "Ser um formato proprietário do Microsoft Excel não compatível com outros softwares.",
         "Permitir apenas uma coluna de dados por arquivo.",
         "Ser utilizado exclusivamente para imagens e gráficos vetoriais."],
        1,
        "CSV é um formato de texto simples e aberto para dados tabulares, amplamente utilizado para importação/exportação entre sistemas, bancos de dados e planilhas, com campos separados por delimitadores.",
        "Informática", ["formatos"]
    ),
    _q(
        "A tecnologia NVMe (Non-Volatile Memory Express) é um protocolo de comunicação utilizado por:",
        ["Monitores de vídeo de alta resolução.",
         "Unidades de estado sólido (SSD) conectadas via PCI Express, oferecendo alta velocidade de transferência.",
         "Impressoras multifuncionais em redes corporativas.",
         "Placas de som para áudio profissional.",
         "Modems de conexão discada à internet."],
        1,
        "NVMe é um protocolo otimizado para SSDs conectados ao barramento PCIe, oferecendo latência muito menor e maior throughput que o protocolo AHCI (SATA), aproveitando o paralelismo das memórias flash NAND.",
        "Informática", ["hardware"]
    ),
    _q(
        "Conforme a Lei 13.303/2016, o conselho de administração das empresas estatais deve ser composto por, no mínimo:",
        ["3 membros.",
         "5 membros.",
         "7 membros.",
         "10 membros.",
         "15 membros."],
        2,
        "Art. 13, §1º: O conselho de administração das estatais deve ter, no mínimo, 7 membros, sendo no máximo 25% de representantes dos empregados, com mandato unificado de até 2 anos, permitida até 3 reconduções consecutivas.",
        "Legislação", ["13303"]
    ),
    _q(
        "De acordo com a Lei 13.303/2016, a política de transação (acordo) para solução consensual de controvérsias nas estatais:",
        ["É vedada em qualquer hipótese.",
         "É permitida para dirimir controvérsias relativas a direitos patrimoniais disponíveis, observada a aprovação do conselho de administração.",
         "Depende exclusivamente de autorização judicial.",
         "Pode ser celebrada pelo presidente da estatal sem aprovação do conselho.",
         "Exige homologação do Tribunal de Contas da União."],
        1,
        "Art. 32, §5º e Art. 66-A da Lei 13.303/2016 preveem a transação para resolução consensual de controvérsias sobre direitos patrimoniais disponíveis no âmbito das estatais, com aprovação do conselho de administração.",
        "Legislação", ["13303"]
    ),
    _q(
        "A Lei 13.303/2016 exige que as empresas estatais constituam comitê estatutário de:",
        ["Auditoria estatutário, obrigatório para todas as estatais, e comitê de remuneração e elegibilidade, entre outros.",
         "Apenas comitê de ética, sendo os demais facultativos.",
         "Marketing e comunicação corporativa, com mandato vitalício.",
         "Relações internacionais para empresas com operações no exterior.",
         "Desenvolvimento tecnológico exclusivamente."],
        0,
        "Art. 14: as estatais devem ter comitê de auditoria estatutário (obrigatório), e podem ter comitê de remuneração e elegibilidade e comitê de riscos, compliance e sustentabilidade, conforme seu estatuto social.",
        "Legislação", ["13303"]
    ),
    _q(
        "Segundo a Lei 14.133/2021 (Nova Lei de Licitações), o critério de desempate entre licitantes inclui preferência para:",
        ["Empresas estrangeiras com maior faturamento global.",
         "Empresas brasileiras, empresas que invistam em pesquisa e desenvolvimento de tecnologia no país, e empresas que comprovem boas práticas de sustentabilidade.",
         "Empresas com maior tempo de mercado.",
         "Empresas que tenham contratado ex-servidores públicos.",
         "Empresas de capital aberto com ações negociadas em bolsa."],
        1,
        "Art. 60 da Lei 14.133/2021: como critério de desempate, prefere-se: I - bens e serviços produzidos no país; II - empresas que invistam em P&D; III - que comprovem boas práticas de sustentabilidade; IV - que tenham menor preço; V - MF maior.",
        "Legislação", ["14133"]
    ),
    _q(
        "A modalidade de licitação 'diálogo competitivo', prevista na Lei 14.133/2021, é:",
        ["Utilizada para compras de baixo valor com dispensa de licitação.",
         "Modalidade para contratação de obras, serviços e compras em que a Administração realiza diálogos com licitantes pré-selecionados para desenvolver alternativas para atender às suas necessidades.",
         "Equivalente ao convite da Lei 8.666/1993.",
         "Aplicável exclusivamente a contratos de TI de pequeno porte.",
         "Uma fase interna de planejamento sem participação de licitantes."],
        1,
        "Art. 6º, XLII e Art. 32 da Lei 14.133/2021: o diálogo competitivo é uma modalidade para contratações complexas em que a Administração dialoga com licitantes para definir a solução mais adequada antes da apresentação de propostas.",
        "Legislação", ["14133"]
    ),
    _q(
        "O agente público que pratica ato de improbidade que causa lesão ao erário está sujeito, conforme a Lei 8.429/1992:",
        ["Apenas a advertência verbal.",
         "À perda dos bens ou valores acrescidos ilicitamente, ressarcimento integral do dano, perda da função pública e suspensão dos direitos políticos de 5 a 8 anos.",
         "Exclusivamente a multa civil de até 2 vezes o valor do dano.",
         "A detenção de 1 a 3 anos sem perda da função pública.",
         "Apenas à proibição de contratar com o poder público por 2 anos."],
        1,
        "Lei 8.429/92, Art. 10: improbidade por lesão ao erário sujeita o agente a ressarcimento integral, perda dos bens, perda da função pública, suspensão dos direitos políticos por 5 a 8 anos, multa de até 2× o dano e proibição de contratar com o poder público por 5 anos.",
        "Legislação", ["8429"]
    ),
    _q(
        "O art. 37, §6º da CF/88 estabelece a responsabilidade civil objetiva das pessoas jurídicas de direito público e as de direito privado prestadoras de serviços públicos, que se baseia na teoria:",
        ["Da culpa administrativa (faute du service).",
         "Do risco administrativo, com direito de regresso contra o agente causador do dano em caso de dolo ou culpa.",
         "Da culpa presumida do Estado.",
         "Do risco integral, sem qualquer excludente de responsabilidade.",
         "Da culpa subjetiva do agente público exclusivamente."],
        1,
        "O §6º do Art. 37 adota a responsabilidade objetiva do Estado (teoria do risco administrativo), exigindo nexo causal e dano, mas o ente público pode alegar excludentes (culpa exclusiva da vítima, força maior) e tem direito de regresso contra o agente culpado.",
        "Legislação", ["cf"]
    ),
    _q(
        "O contrato de partilha de produção do pré-sal (Lei 12.351/2010) prevê que o excedente em óleo (profit oil) é dividido entre:",
        ["União e contratante com base em percentuais definidos na proposta vencedora da licitação.",
         "União detém 100% e o contratante recebe apenas reembolso de custos.",
         "Contratante detém 100% e paga royalties apenas.",
         "Estados e municípios produtores dividem igualmente.",
         "Petrobras e ANP sem participação da União."],
        0,
        "Lei 12.351/2010, Art. 2º, III: o excedente em óleo (profit oil) é a parcela da produção a ser repartida entre a União e o contratante conforme critérios definidos no edital e contrato de partilha.",
        "Legislação", ["12351"]
    ),
    _q(
        "O Conselho Nacional de Política Energética (CNPE) tem como competência, entre outras:",
        ["Executar a política tributária do setor energético.",
         "Propor ao Presidente da República políticas nacionais de energia, assegurar o suprimento de insumos e revisar a matriz energética.",
         "Fiscalizar a qualidade dos combustíveis vendidos nos postos.",
         "Autorizar a importação de derivados de petróleo por agentes privados.",
         "Definir a taxa de câmbio para contratos de petróleo."],
        1,
        "Art. 2º da Lei 9.478/1997: o CNPE é órgão de assessoramento da Presidência da República para formulação de políticas e diretrizes de energia, assegurando suprimento, revisando a matriz e promovendo o aproveitamento racional dos recursos energéticos.",
        "Legislação", ["9478"]
    ),
    _q(
        "A Lei 9.478/1997, em seu Art. 26, estabelece que as concessões de exploração e produção de petróleo serão contratadas por meio de:",
        ["Contrato direto com a Petrobras, independentemente de licitação.",
         "Licitação na modalidade de concorrência ou leilão público, sob o regime de concessão ou partilha de produção.",
         "Autorização simples da ANP sem contrato.",
         "Decreto presidencial após aprovação do Congresso Nacional.",
         "Acordo internacional entre o Brasil e o país de origem da empresa contratada."],
        1,
        "Art. 26, caput: a União contratará a E&P de petróleo sob os regimes de concessão e partilha de produção (Lei 12.351/2010), precedidos de licitação na modalidade concorrência ou leilão público promovido pela ANP.",
        "Legislação", ["9478"]
    ),
    _q(
        "O regime de afretamento de navios para a indústria offshore brasileira é disciplinado pela:",
        ["Lei 9.432/1997 (Lei de Afretamento), que regula o transporte aquaviário e o afretamento de embarcações na navegação de cabotagem e apoio marítimo.",
         "Lei 13.303/2016, que trata das estatais.",
         "Lei 8.630/1993 (Lei dos Portos), revogada posteriormente.",
         "Resolução ANP 50/2013 exclusivamente.",
         "Lei 9.478/1997, artigo sobre outorga de exploração."],
        0,
        "Lei 9.432/1997 regula o afretamento de embarcações (por tempo, por viagem, casco nu) e estabelece regras para a navegação de cabotagem, apoio marítimo e apoio portuário, essencial para a logística offshore.",
        "Legislação", ["9432"]
    ),
    _q(
        "De acordo com a Lei Complementar 182/2021 (Marco Legal das Startups), o governo pode contratar soluções inovadoras por meio de:",
        ["Licitação exclusiva para empresas estatais.",
         "Contrato público para solução inovadora, permitindo à Administração testar protótipos antes da contratação definitiva.",
         "Doação direta com dispensa de licitação para qualquer empresa.",
         "Compra por pregão eletrônico com prazo reduzido para 5 dias.",
         "Contratação emergencial sem justificativa."],
        1,
        "Art. 5º da LC 182/2021: a Administração pode contratar soluções inovadoras por meio de contrato público para solução inovadora (CPSI), com fases de desenvolvimento, validação e eventual contratação, com dispensa de licitação (Art. 13).",
        "Legislação", ["lc182"]
    ),
    _q(
        "A Medida Provisória que perdeu eficácia por decurso de prazo sem conversão em lei:",
        ["Produz efeitos jurídicos permanentes como se fosse lei.",
         "Perde a eficácia desde a edição, mas o Congresso deve disciplinar as relações jurídicas constituídas no período.",
         "É automaticamente reeditada com novo prazo.",
         "Torna-se lei por decurso de prazo.",
         "É revogada pelo Presidente da República sem necessidade de deliberação."],
        1,
        "Art. 62, §3º da CF/88: a MP perde eficácia desde a edição se não for convertida em lei no prazo de 60 dias (prorrogável por +60). O Congresso deve disciplinar as relações jurídicas constituídas durante a vigência por decreto legislativo.",
        "Legislação", ["cf"]
    ),
    _q(
        "O contrato de concessão comum de serviço público (Lei 8.987/1995) caracteriza-se por:",
        ["Transferir a titularidade do serviço público ao concessionário.",
         "Manter o poder concedente como titular do serviço, transferindo ao concessionário apenas a execução, com riscos do negócio assumidos pelo concessionário.",
         "Não exigir licitação prévia para sua celebração.",
         "Atribuir ao poder concedente todos os riscos operacionais.",
         "Ser celebrado por prazo indeterminado."],
        1,
        "Arts. 1º e 2º da Lei 8.987/1995: concessão é a delegação da prestação de serviço público (não da titularidade) ao particular, que assume os riscos do negócio, mediante licitação, por prazo determinado e tarifa paga pelo usuário.",
        "Legislação", ["8987"]
    ),
    _q(
        "Os contratos de integração entre refinarias e postos de combustíveis devem ser registrados na ANP conforme:",
        ["Lei 9.478/1997 e Portaria ANP específica sobre integração vertical, visando garantir livre concorrência e transparência de preços.",
         "Lei 13.303/2016 referente à governança das estatais.",
         "Decreto 8.945/2016 sobre licitações de estatais.",
         "Código de Defesa do Consumidor, sem participação da ANP.",
         "Legislação municipal de cada cidade onde os postos estão localizados."],
        0,
        "A ANP regula e fiscaliza a integração vertical na distribuição e revenda de combustíveis, exigindo registro de contratos de exclusividade e bandeira branca para garantir a concorrência e o livre mercado.",
        "Legislação", ["9478"]
    ),
    _q(
        "Uma aplicação de R$ 10.000,00 a juros compostos de 2% ao mês durante 3 meses gera um montante de:",
        ["R$ 10.600,00.",
         "R$ 10.612,08.",
         "R$ 10.609,00.",
         "R$ 11.000,00.",
         "R$ 10.508,00."],
        1,
        "M = C × (1 + i)^t = 10000 × (1,02)³ = 10000 × 1,061208 = R$ 10.612,08.",
        "Matemática", ["juros"]
    ),
    _q(
        "A equação do 2º grau x² − 5x + 6 = 0 tem raízes:",
        ["2 e 3.",
         "1 e 6.",
         "−2 e −3.",
         "5 e 0.",
         "3 e 4."],
        0,
        "Δ = b² − 4ac = 25 − 24 = 1. x = (5 ± 1)/2 → x₁ = 3, x₂ = 2.",
        "Matemática", ["equacao"]
    ),
    _q(
        "Em uma progressão aritmética (PA), o primeiro termo é 5 e a razão é 3. O 10º termo vale:",
        ["30.",
         "32.",
         "35.",
         "28.",
         "33."],
        1,
        "an = a₁ + (n−1)·r → a₁₀ = 5 + 9·3 = 5 + 27 = 32.",
        "Matemática", ["pa"]
    ),
    _q(
        "O domínio da função real f(x) = √(x − 3) é:",
        ["x ≥ 3.",
         "x > 3.",
         "x ≤ 3.",
         "x < 3.",
         "Todos os reais."],
        0,
        "A raiz quadrada de índice par exige radicando ≥ 0: x − 3 ≥ 0 → x ≥ 3.",
        "Matemática", ["funcao"]
    ),
    _q(
        "Uma pesquisa mostrou que 60% dos engenheiros da Petrobras falam inglês e 40% falam espanhol. Se 20% falam ambos, qual a porcentagem que fala pelo menos um dos dois idiomas?",
        ["60%.",
         "80%.",
         "100%.",
         "70%.",
         "90%."],
        1,
        "P(A∪B) = P(A) + P(B) − P(A∩B) = 60% + 40% − 20% = 80%.",
        "Matemática", ["conjuntos"]
    ),
    _q(
        "O determinante da matriz [[2, 3], [4, 5]] é igual a:",
        ["−2.",
         "2.",
         "10.",
         "−10.",
         "7."],
        0,
        "det = 2×5 − 3×4 = 10 − 12 = −2.",
        "Matemática", ["matriz"]
    ),
    _q(
        "Um título de R$ 1.500,00 foi descontado 2 meses antes do vencimento à taxa de desconto simples de 3% ao mês. Pelo desconto comercial simples, o valor recebido é:",
        ["R$ 1.410,00.",
         "R$ 1.500,00.",
         "R$ 1.440,00.",
         "R$ 1.380,00.",
         "R$ 1.350,00."],
        0,
        "Desconto comercial simples: Dc = N × i × t = 1500 × 0,03 × 2 = 90. Valor atual A = N − Dc = 1500 − 90 = R$ 1.410,00.",
        "Matemática", ["desconto"]
    ),
    _q(
        "Quantos anagramas distintos podem ser formados com as letras da palavra CONCURSO?",
        ["5.040.",
         "10.080.",
         "20.160.",
         "40.320.",
         "2.520."],
        1,
        "CONCURSO tem 8 letras com repetições: C (2×), O (2×). Anagramas = 8!/(2!·2!) = 40320/4 = 10.080.",
        "Matemática", ["combinatoria"]
    ),
    _q(
        "A reta que passa pelos pontos A(1,2) e B(3,6) tem coeficiente angular igual a:",
        ["1.",
         "2.",
         "3.",
         "4.",
         "5."],
        1,
        "m = (y₂ − y₁)/(x₂ − x₁) = (6 − 2)/(3 − 1) = 4/2 = 2.",
        "Matemática", ["geometria"]
    ),
    _q(
        "O volume de um cilindro circular reto de raio 3 cm e altura 10 cm é (considere π = 3,14):",
        ["94,2 cm³.",
         "282,6 cm³.",
         "188,4 cm³.",
         "314,0 cm³.",
         "141,3 cm³."],
        1,
        "V = π·r²·h = 3,14 × 9 × 10 = 3,14 × 90 = 282,6 cm³.",
        "Matemática", ["geometria"]
    ),
    _q(
        "Em um sistema de equações lineares, se o determinante da matriz dos coeficientes é zero, pode-se afirmar que:",
        ["O sistema tem solução única.",
         "O sistema é impossível ou possui infinitas soluções (SPI ou SI).",
         "O sistema é sempre possível e determinado.",
         "O sistema tem exatamente duas soluções.",
         "A matriz é inversível."],
        1,
        "Se det = 0, a matriz é singular (não inversível). O sistema pode ser SPI (infinitas soluções) ou SI (sem solução), dependendo dos termos independentes.",
        "Matemática", ["sistemas"]
    ),
    _q(
        "O logaritmo de 243 na base 3 é igual a:",
        ["3.",
         "4.",
         "5.",
         "6.",
         "7."],
        2,
        "log₃ 243 = x → 3^x = 243 → 3⁵ = 243 → x = 5.",
        "Matemática", ["logaritmo"]
    ),
    _q(
        "Uma progressão geométrica (PG) tem primeiro termo 2 e razão 3. O 5º termo vale:",
        ["48.",
         "162.",
         "54.",
         "72.",
         "486."],
        1,
        "an = a₁ × q^(n−1) → a₅ = 2 × 3⁴ = 2 × 81 = 162.",
        "Matemática", ["pg"]
    ),
    _q(
        "A distância entre os pontos P(2,3) e Q(5,7) no plano cartesiano é:",
        ["4.",
         "5.",
         "6.",
         "7.",
         "8."],
        1,
        "d = √[(5−2)² + (7−3)²] = √[9 + 16] = √25 = 5.",
        "Matemática", ["geometria"]
    ),
    _q(
        "O Índice de Consistência (IC) é calculado dividindo-se:",
        ["O número de dias com estudo na semana por 7.",
         "O total de horas estudadas no mês pelo número de semanas.",
         "A média de acertos pelo total de questões.",
         "O número de matérias estudadas por dia.",
         "As horas líquidas de estudo pelas horas brutas registradas."],
        0,
        "IC = (dias com sessão de estudo na semana) / 7. Mede a regularidade do hábito de estudos, independentemente da quantidade de horas.",
        "Métricas", ["ic"]
    ),
    _q(
        "O Índice de Gestão (IG) do método graphify/RTK mede:",
        ["O tempo de tela gasto em redes sociais.",
         "A proporção de meta de questões cumprida em relação à meta planejada (questões respondidas / meta do dia).",
         "A quantidade de páginas lidas de livros técnicos.",
         "A velocidade de leitura em palavras por minuto.",
         "A nota projetada para o próximo simulado."],
        1,
        "IG = questões respondidas no dia / meta diária de questões. Reflete o cumprimento da meta quantitativa de treino por questões.",
        "Métricas", ["ig"]
    ),
    _q(
        "O Tempo de Revisão (TR) representa:",
        ["O tempo total acumulado de estudo no mês.",
         "O tempo dedicado exclusivamente à revisão de ciclos anteriores, medido em minutos ou horas.",
         "A velocidade com que o usuário lê questões de múltipla escolha.",
         "O intervalo entre simulados em dias.",
         "A duração média de cada sessão de estudos."],
        1,
        "TR é o tempo investido em revisar conteúdos já estudados (ciclos anteriores), essencial para a consolidação da memória de longo prazo e para a fixação do conhecimento.",
        "Métricas", ["tr"]
    ),
    _q(
        "A meta semanal de questões no método RTK deve ser definida com base:",
        ["Apenas na disponibilidade de tempo livre nos fins de semana.",
         "Na quantidade de questões disponíveis no banco, no tempo disponível por dia e no IC do usuário, buscando progressividade.",
         "Na média de questões que os amigos estão resolvendo.",
         "No número de matérias que caem no edital do concurso.",
         "No valor pago pelo curso preparatório."],
        1,
        "A meta semanal deve ser personalizada conforme o tempo disponível, o IC e o banco de questões disponível, aumentando progressivamente para gerar adaptação sem sobrecarga.",
        "Métricas", ["meta"]
    ),
    _q(
        "O Índice de Aprendizado por Ciclo (IAC) é calculado como:",
        ["Soma de acertos em todas as tentativas dividida pelo total de tentativas.",
         "Média ponderada do desempenho nas questões de um mesmo tópico ao longo dos ciclos de revisão, indicando retenção.",
         "Número de matérias estudadas no dia vezes o tempo de estudo.",
         "Diferença entre acertos e erros no último simulado.",
         "Percentual de questões em branco no simulado completo."],
        1,
        "O IAC avalia a evolução do aprendizado ao longo dos ciclos: compara o desempenho nas questões de um mesmo tópico entre a primeira exposição e as revisões subsequentes.",
        "Métricas", ["iac"]
    ),
    _q(
        "O objetivo principal do método de estudo baseado em questões (Question-Based Learning) é:",
        ["Ler toda a teoria antes de resolver qualquer questão.",
         "Identificar lacunas de conhecimento por meio da resolução ativa de questões, direcionando o estudo teórico para os pontos fracos.",
         "Responder questões apenas na véspera da prova para testar o conhecimento.",
         "Estudar exclusivamente por videoaulas sem resolver questões.",
         "Criar resumos de toda a matéria antes de praticar."],
        1,
        "O QBL (aprendizagem baseada em questões) inverte a ordem tradicional: o aluno resolve questões e, a partir dos erros, identifica e preenche as lacunas teóricas específicas, otimizando o tempo de estudo.",
        "Métricas", ["metodo"]
    ),
    _q(
        "O indicador LI (Líquido de Imersão) mede:",
        ["O número de horas brutas de estudo no mês.",
         "O tempo de estudo livre de distrações (celular, redes sociais, pausas não programadas) em uma sessão.",
         "A quantidade de matérias diferentes estudadas no mesmo dia.",
         "O percentual de tempo gasto com revisão versus conteúdo novo.",
         "A quantidade de café consumido durante o estudo."],
        1,
        "LI = tempo de foco total − tempo de distrações. Um LI alto indica alta concentração, correlacionando-se com melhor retenção e aprendizado mais eficiente.",
        "Métricas", ["li"]
    ),
    _q(
        "A 'curva do esquecimento' de Ebbinghaus sugere que, sem revisão, o cérebro:",
        ["Lembra 100% do conteúdo aprendido por meses.",
         "Esquece cerca de 50% do conteúdo em uma hora e até 80% em 24 horas, sendo a revisão espaçada essencial para reverter esse processo.",
         "Esquece apenas detalhes irrelevantes.",
         "Retém melhor informações lidas em voz alta.",
         "Não perde informações se o estudo foi feito em grupo."],
        1,
        "A curva do esquecimento mostra que a retenção cai exponencialmente: ~50% em 1 hora, ~70% em 24h. A revisão espaçada (spaced repetition) em intervalos crescentes reverte esse declínio e consolida a memória de longo prazo.",
        "Métricas", ["curva"]
    ),
    _q(
        "O gabarito de redação de 07/11/2019 enfatiza que a função da vírgula na frase 'O concurso, disse o presidente, será mantido' é:",
        ["Separar o sujeito do predicado.",
         "Isolar o discurso direto.",
         "Separar oração intercalada (intercalação), que traz a fala de terceiro entre o sujeito e o verbo.",
         "Indicar aposto explicativo.",
         "Marcar a elipse do verbo."],
        2,
        "Em 'O concurso, disse o presidente, será mantido', a expressão 'disse o presidente' é uma oração intercalada, que interrompe a oração principal para indicar a fonte da informação, sendo isolada por vírgulas.",
        "Português", ["pontuacao"]
    ),
    _q(
        "A palavra 'enjoo' perdeu o acento com o Novo Acordo Ortográfico porque:",
        ["É paroxítona terminada em 'oo', que não mais são acentuadas.",
         "É oxítona terminada em 'o'.",
         "É proparoxítona aparente.",
         "O acento diferencial de timbre foi abolido.",
         "É monossílaba tônica."],
        0,
        "Pelo Novo Acordo, as paroxítonas terminadas em 'oo' (enjoo, voo, magoo) perderam o acento circunflexo. A regra anterior acentuava essas palavras.",
        "Português", ["acentuacao"]
    ),
    _q(
        "A colocação pronominal está correta em:",
        ["Me entregue o relatório amanhã.",
         "Nunca te disse isso.",
         "Far-lhe-ia um favor se pudesse.",
         "Em se tratando de prazos, não podemos atrasar.",
         "Todos me ajudaram a concluir o projeto."],
        3,
        "Em 'Em se tratando de prazos', a ênclise é correta após preposição (em) + verbo no gerúndio. Nas demais: 'entregue-me' (início de frase), 'nunca te disse' (advérbio atrai próclise), 'faria-lhe' ou 'lhe faria' (locução verbal com particípio exige próclise ou ênclise no infinitivo).",
        "Português", ["pronomes"]
    ),
    _q(
        "Assinale a alternativa em que o termo sublinhado exerce função de complemento nominal:",
        ["A confiança do povo no governo foi abalada.",
         "A confiança venceu o medo.",
         "O governante confia na equipe.",
         "A equipe confiante apresentou o projeto.",
         "O presidente foi confiante ao falar."],
        0,
        "Complemento nominal completa o sentido de um nome (substantivo, adjetivo ou advérbio) com preposição. 'confiança no governo': 'no governo' é complemento nominal de 'confiança' (substantivo abstrato), pois 'confiança' exige 'em'.",
        "Português", ["sintaxe"]
    ),
    _q(
        "A regência do verbo 'aspirar' está correta em:",
        ["Aspiramos o cargo de diretor com dedicação.",
         "Aspiramos ao cargo de diretor com dedicação.",
         "Aspiramos pelo cargo de diretor com dedicação.",
         "Aspiramos para o cargo de diretor com dedicação.",
         "Aspiramos no cargo de diretor com dedicação."],
        1,
        "'Aspirar' no sentido de 'desejar, almejar' é transitivo indireto, exigindo preposição 'a': aspirar ao cargo. No sentido de 'inspirar, sorver' é transitivo direto: aspirar o ar.",
        "Português", ["regencia"]
    ),
    _q(
        "Assinale a alternativa em que há ERRO de concordância verbal:",
        ["Faz dez anos que ingressei na empresa.",
         "Havia muitas pessoas na reunião.",
         "Devem haver soluções viáveis para o problema.",
         "Choveu pedras no final da tarde.",
         "Bastam dois dias para concluir o trabalho."],
        2,
        "'Haver' como impessoal (sentido de 'existir') é invariável. 'Haver' em locução verbal com verbo auxiliar também fica invariável: 'deve haver' (não 'devem haver'). O correto é 'Deve haver soluções viáveis'.",
        "Português", ["concordancia"]
    ),
    _q(
        "'O gerente pediu para mim organizar a planilha.' A frase apresenta:",
        ["Erro de colocação pronominal.",
         "Erro de emprego do caso oblíquo (mim) como sujeito de verbo no infinitivo. O correto é 'para eu organizar'.",
         "Erro de crase.",
         "Erro de concordância nominal.",
         "Erro de pontuação."],
        1,
        "'Mim' é pronome oblíquo tônico e não pode exercer função de sujeito. Quando o pronome antecede um verbo no infinitivo, deve-se usar o caso reto 'eu': 'para eu organizar'.",
        "Português", ["pronomes"]
    ),
    _q(
        "Assinale a alternativa em que a palavra 'que' é pronome relativo:",
        ["Que surpresa boa encontrar você aqui!",
         "Não sei que caminho seguir.",
         "O livro que li é muito interessante.",
         "Que venham os resultados do concurso!",
         "Ele estava tão feliz que chorou."],
        2,
        "Em 'O livro que li', o 'que' retoma o antecedente 'livro' e exerce função sintática (objeto direto de 'li'), caracterizando-se como pronome relativo. Substitui 'o qual'.",
        "Português", ["que"]
    ),
    _q(
        "Assinale a alternativa que apresenta uma oração subordinada substantiva subjetiva:",
        ["É importante que todos participem da reunião.",
         "O gerente disse que a reunião foi produtiva.",
         "O funcionário que chegou atrasado justificou-se.",
         "Fique tranquilo, pois a reunião foi adiada.",
         "Chegando o gerente, iniciaremos a reunião."],
        0,
        "'que todos participem' exerce função de sujeito do verbo 'É' (importante = predicativo). Oração subordinada substantiva subjetiva funciona como sujeito da oração principal.",
        "Português", ["sintaxe"]
    ),
    _q(
        "'O engenheiro foi informado do resultado.' A voz verbal é:",
        ["Ativa, pois o sujeito pratica a ação.",
         "Passiva analítica (sujeito paciente sofre a ação: 'foi informado').",
         "Reflexiva, com ação que recai sobre o próprio sujeito.",
         "Passiva sintética com partícula 'se'.",
         "Recíproca, com ação mútua entre os agentes."],
        1,
        "Na voz passiva analítica, o sujeito ('O engenheiro') sofre/recebe a ação verbal. Formada por verbo 'ser' + particípio do verbo principal ('informado').",
        "Português", ["vozes"]
    ),
    _q(
        "A crase é facultativa antes de:",
        ["Palavra masculina.",
         "Pronome possessivo feminino singular (minha, tua, sua, nossa, sua), quando o substantivo feminino está subentendido.",
         "Verbo no infinitivo.",
         "Pronome de tratamento como Vossa Senhoria e equivalentes.",
         "Palavra feminina que exige preposição 'a' e admite artigo."],
        1,
        "É facultativo o uso da crase antes de pronome possessivo feminino singular (ex: 'entreguei a' ou 'à minha secretária'), mas obrigatório antes de 'senhora', 'dona' e 'mesma'.",
        "Português", ["crase"]
    ),
    _q(
        "Em 'Precisamos discutir acerca do orçamento', a expressão 'acerca de' significa:",
        ["Ao redor de, aproximadamente.",
         "Sobre, a respeito de.",
         "Há cerca de, aproximadamente no tempo.",
         "Próximo de, perto de.",
         "Contrário a, oposto de."],
        1,
        "'Acerca de' (= sobre, a respeito de) deve ser grafado separadamente e com 'c'. 'Cerca de' (= aproximadamente) e 'há cerca de' (= existe aproximadamente há) são expressões distintas.",
        "Português", ["ortografia"]
    ),
    _q(
        "Assinale a alternativa em que o emprego do sinal indicativo de crase é OBRIGATÓRIO:",
        ["Refiro-me àquele senhor alto.",
         "Entreguei o documento à Vossa Senhoria.",
         "Chegamos à noite, mas ainda era cedo.",
         "Fomos à casa de praia passar o feriado.",
         "Ele fez uma pintura à óleo."],
        0,
        "A + aquele = àquele. Crase obrigatória diante de pronomes demonstrativos 'aquele(s)', 'aquela(s)', 'aquilo'. 'A Vossa Senhoria' não admite artigo; 'à noite' é locução feminina com hora; 'casa' sem especificador; 'à óleo' é locução com palavra masculina (casos especiais regrados).",
        "Português", ["crase"]
    ),
    _q(
        "A função de linguagem predominante em 'Atenção, senhores passageiros: o voo 2045 com destino a São Paulo acaba de ser cancelado' é:",
        ["Função emotiva (expressão de emoções do emissor).",
         "Função conativa ou apelativa (chamar a atenção do receptor), combinada com função referencial (informar).",
         "Função metalinguística (explicar o próprio código).",
         "Função fática (testar o canal de comunicação).",
         "Função poética (estética da mensagem)."],
        1,
        "Há função conativa ('Atenção') — verbo no imperativo para chamar o receptor — e função referencial (informação objetiva sobre o voo cancelado).",
        "Português", ["funcoes"]
    ),
    _q(
        "Na frase 'Ele não só organizou a equipe, mas também liderou o projeto', a expressão 'não só... mas também' estabelece relação de:",
        ["Adição (soma de ideias).",
         "Oposição (contraste de ideias).",
         "Alternância (ideias que se excluem).",
         "Causa e consequência.",
         "Condição e conclusão."],
        0,
        "'Não só... mas também' é uma conjunção coordenativa aditiva que enfatiza a adição de dois elementos ou ações, equivalendo a 'tanto... quanto' ou 'e ainda'.",
        "Português", ["conjuncoes"]
    ),
    _q(
        "'Os engenheiros concluíram o projeto, embora houvessem enfrentado desafios técnicos.' A oração iniciada por 'embora' classifica-se como:",
        ["Oração coordenada sindética adversativa.",
         "Oração subordinada adverbial concessiva.",
         "Oração subordinada substantiva objetiva direta.",
         "Oração subordinada adjetiva explicativa.",
         "Oração coordenada assindética."],
        1,
        "'Embora' é conjunção subordinativa concessiva, indicando um fato que se admite (concessão) mas que não impede a realização do fato da oração principal. Equivale a 'apesar de que', 'conquanto'.",
        "Português", ["sintaxe"]
    ),
    _q(
        "Assinale a alternativa em que a palavra 'se' é partícula apassivadora:",
        ["Precisa-se de engenheiros experientes.",
         "Alugam-se salas comerciais.",
         "Ele se machucou durante o trabalho.",
         "Os candidatos se cumprimentaram no auditório.",
         "Ela se queixou do calor excessivo."],
        1,
        "Em 'Alugam-se salas comerciais', o 'se' é partícula apassivadora (voz passiva sintética): 'salas comerciais' é sujeito paciente concorda com o verbo. 'Precisa-se' é índice de indeterminação do sujeito. Os demais são pronomes reflexivos/recíprocos.",
        "Português", ["se"]
    ),
    _q(
        "Assinale a alternativa em que a palavra destacada é um adjetivo:",
        ["O engenheiro trabalha feliz.",
         "O engenheiro feliz concluiu o projeto.",
         "Ele trabalha felizmente.",
         "O engenheiro tem felicidade na profissão.",
         "Felizmente, o projeto foi aprovado."],
        1,
        "'Feliz' em 'O engenheiro feliz' é adjetivo, caracterizando o substantivo 'engenheiro'. Em 'trabalha feliz' é predicativo do sujeito. 'Felizmente' é advérbio. 'Felicidade' é substantivo.",
        "Português", ["morfologia"]
    ),
    _q(
        "Na lógica proposicional, a frase 'Não é verdade que Pedro passou no concurso e Maria não estudou' é logicamente equivalente a:",
        ["Pedro não passou no concurso ou Maria estudou.",
         "Pedro passou no concurso e Maria estudou.",
         "Pedro não passou no concurso e Maria não estudou.",
         "Se Pedro não passou, então Maria não estudou.",
         "Pedro passou no concurso ou Maria estudou."],
        0,
        "¬(p ∧ ¬q) ≡ ¬p ∨ q (negação da conjunção: ~(A e B) = ~A ou ~B). Aplicando: ~(Pedro passou ∧ Maria não estudou) = Pedro não passou ∨ Maria estudou.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Em um grupo de 50 engenheiros, 30 são de produção e 25 são ambientais. Sabendo que 10 são de ambas, quantos não são de nenhuma das duas?",
        ["5.",
         "10.",
         "15.",
         "20.",
         "25."],
        0,
        "n(A∪B) = n(A) + n(B) − n(A∩B) = 30 + 25 − 10 = 45. Total = 50, então n(nenhuma) = 50 − 45 = 5.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Em uma sequência definida por an = 2n² − 3n + 1, o valor do 5º termo é:",
        ["30.",
         "36.",
         "42.",
         "48.",
         "54."],
        1,
        "a₅ = 2·(5²) − 3·5 + 1 = 2·25 − 15 + 1 = 50 − 15 + 1 = 36.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Em uma urna há 5 bolas azuis, 3 verdes e 2 amarelas. Retirando-se duas bolas sem reposição, a probabilidade de ambas serem azuis é:",
        ["1/5.",
         "2/9.",
         "5/18.",
         "1/4.",
         "2/5."],
        1,
        "P(azul,azul) = (5/10) × (4/9) = 20/90 = 2/9 ≈ 22,2%.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "A negação de 'Todo engenheiro da Petrobras é concursado' é:",
        ["Nenhum engenheiro da Petrobras é concursado.",
         "Existe engenheiro da Petrobras que não é concursado.",
         "Todo engenheiro concursado trabalha na Petrobras.",
         "Algum engenheiro concursado não é da Petrobras.",
         "Todo engenheiro da Petrobras é terceirizado."],
        1,
        "A negação de 'Todo A é B' é 'Algum A não é B' (ou 'Existe A que não é B'). O quantificador universal é negado pelo existencial, e a qualidade invertida.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Se 'alguns engenheiros são concursados' e 'todos os concursados estudaram para a prova', podemos concluir que:",
        ["Todos os engenheiros estudaram para a prova.",
         "Alguns engenheiros estudaram para a prova.",
         "Nenhum engenheiro estudou para a prova.",
         "Alguns concursados não são engenheiros.",
         "Todos os que estudaram são engenheiros."],
        1,
        "A interseção dos conjuntos 'engenheiros' e 'concursados' existe (alguns). Como todos os 'concursados' são 'estudaram', essa interseção também está contida em 'estudaram'. Logo, alguns engenheiros (os que são concursados) estudaram.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Em uma fila de banco, 5 pessoas estão na frente de Carlos e 3 pessoas estão atrás de Maria. Se há 12 pessoas na fila, quantas pessoas estão entre Carlos e Maria?",
        ["2.",
         "3.",
         "4.",
         "5.",
         "6."],
        0,
        "Carlos é a 6ª pessoa (5 na frente). Maria é a 9ª (3 atrás = 10ª posição, mas são 12 pessoas, então Maria é a 10ª). Entre a 6ª e 10ª posições há as posições 7, 8, 9 = 3 pessoas. Verificando: posições 1-5, Carlos(6), 7,8,9, Maria(10), 11,12 = 12 pessoas. Entre Carlos e Maria: posições 7,8,9 = 3 pessoas.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Assinale a alternativa que representa uma tautologia:",
        ["p ∧ q.",
         "p ∨ ¬p.",
         "p ∧ ¬p.",
         "p → ¬p.",
         "p ↔ ¬p."],
        1,
        "p ∨ ¬p (princípio do terceiro excluído) é sempre verdadeira, independentemente do valor de p. Uma tautologia é uma proposição sempre verdadeira.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Quantos números de 3 algarismos distintos podem ser formados com os dígitos 1, 2, 3, 4, 5 e 6?",
        ["60.",
         "120.",
         "180.",
         "216.",
         "240."],
        1,
        "Arranjo: 6 × 5 × 4 = 120 números. Primeiro algarismo: 6 opções; segundo: 5 (não pode repetir); terceiro: 4.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Se p é verdadeiro e q é falso, o valor lógico de (p → q) ∧ (q → p) é:",
        ["Verdadeiro.",
         "Falso.",
         "Verdadeiro apenas se r também for verdadeiro.",
         "Inconclusivo.",
         "Verdadeiro quando q for verdadeiro."],
        1,
        "p → q: V → F = F. q → p: F → V = V. (F) ∧ (V) = Falso.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Uma herança de R$ 240.000,00 foi dividida entre 3 herdeiros em partes diretamente proporcionais a 2, 3 e 5. O herdeiro que recebeu a maior parte recebeu:",
        ["R$ 48.000,00.",
         "R$ 72.000,00.",
         "R$ 96.000,00.",
         "R$ 120.000,00.",
         "R$ 140.000,00."],
        3,
        "Soma das proporções = 2+3+5 = 10. Parte maior = 5/10 × 240.000 = R$ 120.000,00.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Em um silogismo válido, 'Todo A é B' e 'Todo B é C' permite concluir que:",
        ["Todo A é C.",
         "Todo C é A.",
         "Nenhum A é C.",
         "Algum A não é C.",
         "Algum C é A e B."],
        0,
        "Silogismo categórico: se A ⊆ B e B ⊆ C, por transitividade A ⊆ C. Portanto, 'Todo A é C' é uma conclusão válida.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "O ensaio de compactação de solos (Proctor) tem como objetivo determinar:",
        ["A resistência ao cisalhamento do solo.",
         "A umidade ótima e o peso específico seco máximo do solo para um dado esforço de compactação.",
         "A permeabilidade do solo saturado.",
         "O coeficiente de adensamento do solo.",
         "A granulometria do solo."],
        1,
        "O ensaio de Proctor (NBR 7182) determina a curva de compactação: varia-se a umidade e mede-se o peso específico seco, obtendo a umidade ótima (wót) e o peso específico seco máximo (γd,máx).",
        "Engenharia Civil", ["civil", "solos"]
    ),
    _q(
        "De acordo com a NBR 6118 (Projeto de Estruturas de Concreto), o cobrimento nominal mínimo para lajes em ambientes de classe de agressividade ambiental II (urbano) é de:",
        ["15 mm.",
         "20 mm.",
         "25 mm.",
         "30 mm.",
         "35 mm."],
        2,
        "NBR 6118, Tabela 7.2: para CAA II (urbano), cobrimento nominal mínimo: laje = 25 mm, viga/pilar = 30 mm, fundação = 40 mm. O cobrimento é essencial para proteção contra corrosão das armaduras.",
        "Engenharia Civil", ["civil", "concreto"]
    ),
    _q(
        "O limite de liquidez (LL) de um solo é o teor de umidade no qual o solo passa do estado:",
        ["Sólido para semissólido.",
         "Semissólido para plástico.",
         "Plástico para líquido.",
         "Líquido para gasoso.",
         "Semissólido para líquido."],
        2,
        "LL é a umidade de transição entre os estados plástico e líquido, determinado pelo aparelho de Casagrande (NBR 6459). O limite de plasticidade (LP) separa o plástico do semissólido.",
        "Engenharia Civil", ["civil", "solos"]
    ),
    _q(
        "Nas instalações prediais de esgoto sanitário, o desconector que impede o retorno de gases e odores do esgoto para o ambiente é:",
        ["A caixa sifonada.",
         "O tubo de queda.",
         "A coluna de ventilação.",
         "O ralo seco.",
         "O barrilete."],
        0,
        "A caixa sifonada contém um fecho hídrico (selo d'água) que bloqueia a passagem de gases do esgoto para o ambiente, sendo obrigatória em instalações sanitárias conforme NBR 8160.",
        "Engenharia Civil", ["civil", "instalacoes"]
    ),
    _q(
        "Na NBR 9050 (Acessibilidade), a largura mínima para passagem de uma pessoa em cadeira de rodas é:",
        ["0,70 m.",
         "0,80 m.",
         "0,90 m.",
         "1,00 m.",
         "1,20 m."],
        2,
        "NBR 9050: para deslocamento linear de uma pessoa em cadeira de rodas, a largura mínima é 0,90 m. Para duas cadeiras de rodas cruzarem, 1,50 m.",
        "Engenharia Civil", ["civil", "acessibilidade"]
    ),
    _q(
        "O diagrama de momento fletor de uma viga biapoiada com carga uniformemente distribuída ao longo de todo o vão tem a forma de:",
        ["Uma reta linear crescente.",
         "Uma parábola do 2º grau com concavidade para baixo e valor máximo no centro do vão.",
         "Uma linha reta horizontal.",
         "Um triângulo com vértice no apoio esquerdo.",
         "Uma curva exponencial decrescente."],
        1,
        "Para viga biapoiada com carga distribuída q, o momento fletor M(x) = q·x·(L−x)/2, que é uma parábola, com valor máximo Mmax = q·L²/8 no meio do vão (x = L/2).",
        "Engenharia Civil", ["civil", "estruturas"]
    ),
    _q(
        "Na pavimentação asfáltica, o Concreto Betuminoso Usinado a Quente (CBUQ) é aplicado na camada de:",
        ["Base, abaixo do subleito.",
         "Revestimento (capa de rolamento), sobre a base ou binder.",
         "Sub-base, entre o subleito e a base.",
         "Reforço do subleito.",
         "Drenagem vertical do pavimento."],
        1,
        "O CBUQ (ou concreto asfáltico) é o revestimento flexível do pavimento, camada superior que recebe diretamente as cargas do tráfego, composta por agregados e ligante asfáltico (CAP).",
        "Engenharia Civil", ["civil", "pavimentacao"]
    ),
    _q(
        "A NR-18 estabelece que, em canteiros de obras com 20 ou mais trabalhadores, é obrigatória a elaboração do:",
        ["PPRA (Programa de Prevenção de Riscos Ambientais), hoje substituído pelo PGR.",
         "PCMAT (Programa de Condições e Meio Ambiente de Trabalho na Indústria da Construção).",
         "LTCAT (Laudo Técnico das Condições Ambientais de Trabalho).",
         "PCMSO (Programa de Controle Médico de Saúde Ocupacional).",
         "PCC (Plano de Cargos e Carreiras)."],
        1,
        "NR-18, item 18.4.1: para obras com 20 ou mais trabalhadores, é obrigatório elaborar o PCMAT, contemplando memorial sobre condições e meio ambiente, incluindo riscos, medidas preventivas e cronograma.",
        "Engenharia Civil", ["civil", "nr18"]
    ),
    _q(
        "O ensaio SPT (Standard Penetration Test) é utilizado na engenharia civil para:",
        ["Determinar a resistência à compressão do concreto endurecido.",
         "Medir a resistência à penetração do solo (N-SPT) e coletar amostras deformadas a cada metro de sondagem.",
         "Calcular o módulo de elasticidade do aço.",
         "Medir a condutividade hidráulica do solo saturado.",
         "Avaliar a resistência ao cisalhamento de rochas intactas."],
        1,
        "O SPT (NBR 6484) mede o número N de golpes necessários para penetrar 45 cm (15+30+30) com um amostrador padrão, indicando a compacidade/consistência do solo e orientando o projeto de fundações.",
        "Engenharia Civil", ["civil", "solos"]
    ),
    _q(
        "A impermeabilização de lajes de cobertura em concreto armado deve ser feita:",
        ["Apenas com pintura acrílica simples.",
         "Com sistemas de impermeabilização flexíveis (mantas asfálticas, membranas acrílicas, etc.), incluindo camada de proteção mecânica.",
         "Com argamassa de cimento e areia sem aditivos.",
         "Apenas com calafetação das juntas de dilatação.",
         "Não é necessária, pois o concreto é naturalmente impermeável."],
        1,
        "Lajes de cobertura exigem impermeabilização adequada com sistemas como mantas asfálticas (APP) ou membranas acrílicas, com camada de proteção (argamassa, concreto) para evitar danos mecânicos, conforme NBR 9574 e 9575.",
        "Engenharia Civil", ["civil", "impermeabilizacao"]
    ),
    _q(
        "Na NR-35 (Trabalho em Altura), é obrigatório que o trabalhador:",
        ["Tenha idade mínima de 25 anos.",
         "Realize exame médico ocupacional específico para trabalho em altura e treinamento periódico com carga horária mínima de 8 horas.",
         "Trabalhe com supervisão direta de engenheiro civil.",
         "Use equipamentos de proteção individual (EPI) apenas acima de 5 metros.",
         "Possua certificado de curso superior em engenharia."],
        1,
        "NR-35: treinamento inicial e periódico (reciclagem) de no mínimo 8 horas, exame médico ocupacional (ASO), e uso de sistema de proteção contra quedas (cinto tipo paraquedista, talabarte, pontos de ancoragem).",
        "Engenharia Civil", ["civil", "nr35"]
    ),
    _q(
        "O método de execução de estacas do tipo hélice contínua monitorada consiste em:",
        ["Cravar estacas pré-fabricadas de concreto com bate-estacas.",
         "Perfurar o solo com trado helicoidal contínuo e injetar concreto sob pressão, introduzindo a armadura após a concretagem.",
         "Escavar manualmente e concretar in loco em pequenas profundidades.",
         "Cravagem de perfil metálico por vibração.",
         "Injetar calda de cimento (grouting) em solo granular."],
        1,
        "A hélice contínua (NBR 6122) perfura o solo com um trado helicoidal; ao atingir a profundidade, bombeia concreto pelo centro do trado enquanto o retira, e depois insere a armadura. É monitorada por equipamento eletrônico que registra torque, profundidade e volume de concreto.",
        "Engenharia Civil", ["civil", "fundacoes"]
    ),
    _q(
        "Segundo a NBR 15575 (Edificações Habitacionais — Desempenho), o tempo mínimo de garantia recomendado para a estrutura da edificação (vigas, pilares, lajes) é de:",
        ["2 anos.",
         "5 anos.",
         "10 anos.",
         "20 anos.",
         "50 anos."],
        4,
        "NBR 15575, Tabela 5.5.1: a vida útil de projeto (VUP) mínima para a estrutura principal da edificação é de 50 anos, desde que cumpridos os requisitos de manutenção preventiva previstos no manual do proprietário.",
        "Engenharia Civil", ["civil", "nbr15575"]
    ),
    _q(
        "No projeto de estruturas metálicas (NBR 8800), o estado-limite último de flambagem local da alma (FLA) em vigas é verificado para evitar:",
        ["O escoamento do aço por tração excessiva.",
         "A deformação excessiva da alma por compressão ou cisalhamento localizados, com possibilidade de enrugamento.",
         "A ruptura dos parafusos da ligação.",
         "O deslizamento das ligações parafusadas.",
         "A corrosão da superfície metálica."],
        1,
        "A FLA (flambagem local da alma) é um estado-limite que ocorre quando a alma esbelta de uma viga sofre flambagem sob tensões de compressão (momento fletor) ou cisalhamento, sendo verificada conforme os limites de esbeltez λ da NBR 8800.",
        "Engenharia Civil", ["civil", "estruturas"]
    ),
    _q(
        "Em alvenaria estrutural, o bloco de concreto utilizado deve ter resistência característica à compressão (fbk) mínima definida pela NBR 6136, sendo comum em edificações de até 4 pavimentos o valor de:",
        ["2,0 MPa.",
         "4,5 MPa.",
         "6,0 MPa.",
         "10,0 MPa.",
         "15,0 MPa."],
        2,
        "NBR 6136: blocos de concreto para alvenaria estrutural têm classes de resistência. Para paredes externas e internas de edifícios de até 4 pavimentos, utiliza-se comumente blocos com fbk ≥ 6,0 MPa (classe B), variando conforme o projeto estrutural.",
        "Engenharia Civil", ["civil", "estruturas"]
    ),
    _q(
        "A vazão de projeto de um sistema de drenagem urbana é calculada pelo método racional, que considera:",
        ["A intensidade da chuva, a área da bacia contribuinte e o coeficiente de escoamento superficial (runoff).",
         "Apenas a declividade do terreno e o tipo de pavimento.",
         "A permeabilidade do solo e a profundidade do lençol freático.",
         "A vazão efluente de estações de tratamento de esgoto.",
         "A capacidade de infiltração do solo exclusivamente."],
        0,
        "Método racional: Q = C × I × A / 360, onde Q = vazão (m³/s), C = coeficiente de runoff, I = intensidade pluviométrica (mm/h), A = área da bacia (ha). Válido para pequenas bacias (≤ 2 km²).",
        "Engenharia Civil", ["civil", "drenagem"]
    ),
    _q(
        "O cimento Portland CP III é classificado como cimento:",
        ["Comum (sem adições).",
         "Composto com pozolana.",
         "De alto-forno, contendo escória granulada de alto-forno (entre 35% e 70% em massa).",
         "Composto com filler calcário.",
         "Resistente a sulfatos (RS)."],
        2,
        "CP III (cimento Portland de Alto-Forno) contém escória granulada de alto-forno (35-70%) em sua composição, conferindo maior durabilidade e resistência a sulfatos, com menor calor de hidratação. NBR 5735.",
        "Engenharia Civil", ["civil", "materiais"]
    ),
    _q(
        "A segunda lei da termodinâmica para um ciclo estabelece que:",
        ["A energia total é conservada.",
         "A entropia de um sistema isolado nunca diminui (ΔS ≥ 0), definindo a irreversibilidade dos processos naturais.",
         "O calor sempre flui do corpo frio para o quente espontaneamente.",
         "A eficiência térmica de uma máquina térmica pode ser 100%.",
         "A pressão é inversamente proporcional ao volume a temperatura constante."],
        1,
        "A 2ª lei (enunciado de Clausius/Kelvin-Planck) estabelece que a entropia de um sistema isolado aumenta em processos irreversíveis e permanece constante em processos reversíveis, nunca diminuindo.",
        "Engenharia Mecânica", ["mec", "termo"]
    ),
    _q(
        "Em um processo isoentrópico (reversível e adiabático) para um gás ideal, a relação entre temperatura e pressão é dada por:",
        ["T₂/T₁ = (P₂/P₁)^((k−1)/k), onde k = cp/cv.",
         "T₂/T₁ = P₂/P₁.",
         "T₂/T₁ = (P₂/P₁)^k.",
         "T₂/T₁ = (P₂/P₁)^(1/k).",
         "T₂/T₁ = (P₂/P₁)^((k+1)/k)."],
        0,
        "Para um gás ideal em processo isentrópico, T₂/T₁ = (P₂/P₁)^((k−1)/k), onde k = cp/cv é a razão de calores específicos. Para o ar, k ≈ 1,4.",
        "Engenharia Mecânica", ["mec", "termo"]
    ),
    _q(
        "Em mecânica dos fluidos, a perda de carga distribuída em uma tubulação é calculada pela equação de Darcy-Weisbach:",
        ["hf = f × (L/D) × (v²/2g).",
         "hf = (P₁ − P₂)/ρ.",
         "hf = K × v²/2g.",
         "hf = Δz (diferença de cota).",
         "hf = (v₁² − v₂²)/2g."],
        0,
        "hf = f × (L/D) × (v²/2g), onde f = fator de atrito (função de Re e rugosidade relativa), L = comprimento, D = diâmetro, v = velocidade média, g = gravidade. Perdas localizadas usam K (coeficiente de perda singular).",
        "Engenharia Mecânica", ["mec", "fluidos"]
    ),
    _q(
        "O fator de atrito f para escoamento turbulento em tubulações lisas pode ser calculado pela equação de Blasius, que é válida para:",
        ["Re < 2000 (escoamento laminar).",
         "4000 < Re < 10⁵, sendo f = 0,316/Re^(1/4).",
         "Qualquer regime de escoamento.",
         "Re > 10⁶ exclusivamente.",
         "Escoamento compressível apenas."],
        1,
        "A equação de Blasius (f = 0,316/Re^0,25) é válida para tubos lisos em regime turbulento com 4000 < Re < 10⁵. Para Re maiores, usa-se a equação de Colebrook-White (implícita).",
        "Engenharia Mecânica", ["mec", "fluidos"]
    ),
    _q(
        "O fenômeno de cavitação em uma bomba hidráulica ocorre quando:",
        ["A vazão é muito baixa e a bomba superaquece.",
         "A pressão absoluta do líquido na sucção atinge a pressão de vapor, formando bolhas que colapsam na região de alta pressão do rotor.",
         "O motor elétrico que aciona a bomba entra em sobrecarga.",
         "A rotação da bomba excede a velocidade crítica do eixo.",
         "O fluido é viscoso demais para ser bombeado."],
        1,
        "Cavitação: quando a pressão na sucção cai abaixo da pressão de vapor do líquido, formam-se bolhas de vapor que colapsam violentamente ao atingir regiões de alta pressão no rotor, causando erosão, vibração e perda de desempenho.",
        "Engenharia Mecânica", ["mec", "maquinasfluxo"]
    ),
    _q(
        "No ciclo de Brayton (turbina a gás), os processos termodinâmicos são:",
        ["Compressão isentrópica, aquecimento a volume constante, expansão isentrópica e rejeição de calor a volume constante.",
         "Compressão isentrópica, aquecimento a pressão constante (combustão), expansão isentrópica e rejeição de calor a pressão constante.",
         "Compressão isotérmica, aquecimento isobárico, expansão isotérmica e resfriamento isobárico.",
         "Admissão, compressão, explosão e exaustão em 4 tempos.",
         "Compressão isobárica, combustão isocórica e expansão isentrópica."],
        1,
        "O ciclo Brayton ideal (turbina a gás) consiste em: 1-2 compressão isentrópica, 2-3 combustão isobárica, 3-4 expansão isentrópica na turbina, 4-1 rejeição de calor isobárica (atmosfera).",
        "Engenharia Mecânica", ["mec", "termo"]
    ),
    _q(
        "Em resistência dos materiais, a tensão de cisalhamento máxima em uma viga de seção retangular submetida à flexão ocorre:",
        ["Na fibra superior (maior distância da linha neutra).",
         "Na linha neutra (centro da seção transversal).",
         "Na fibra inferior.",
         "Uniformemente distribuída em toda a seção.",
         "Nos pontos de aplicação das cargas concentradas."],
        1,
        "Para seção retangular, a tensão cisalhante máxima τmax = (3/2) × V/A, ocorrendo na linha neutra (y = 0). Nas fibras extremas (superior e inferior), a tensão cisalhante é nula.",
        "Engenharia Mecânica", ["mec", "resistencia"]
    ),
    _q(
        "Na transmissão de calor por convecção, o coeficiente de transferência de calor h depende de:",
        ["Apenas da condutividade térmica do material.",
         "Das propriedades do fluido (viscosidade, condutividade térmica, cp, densidade), da velocidade do escoamento e da geometria da superfície.",
         "Exclusivamente da diferença de temperatura entre a superfície e o fluido.",
         "Apenas da emissividade da superfície.",
         "Da cor e rugosidade superficial do material."],
        1,
        "O coeficiente convectivo h é determinado por correlações empíricas adimensionais (Nu = h·L/k = f(Re, Pr)) que dependem das propriedades do fluido, regime de escoamento (Re), propriedades térmicas (Pr) e geometria.",
        "Engenharia Mecânica", ["mec", "transcal"]
    ),
    _q(
        "A soldagem TIG (Tungsten Inert Gas) caracteriza-se por:",
        ["Usar eletrodo consumível revestido e corrente alternada.",
         "Usar eletrodo de tungstênio não consumível e gás de proteção inerte (argônio/hélio), com ou sem metal de adição.",
         "Ser um processo de soldagem a gás (oxiacetilênico).",
         "Utilizar arco submerso em fluxo granular.",
         "Gerar calor por resistência elétrica entre duas peças metálicas."],
        1,
        "TIG (GTAW) usa eletrodo de tungstênio (não consumível) para estabelecer o arco elétrico, protegido por gás inerte (argônio ou hélio). Pode usar ou não metal de adição. Produz soldas de alta qualidade e acabamento.",
        "Engenharia Mecânica", ["mec", "soldagem"]
    ),
    _q(
        "O mancal de rolamento rígido de esferas (deep groove ball bearing) é adequado para:",
        ["Cargas axiais exclusivamente.",
         "Cargas radiais combinadas com cargas axiais moderadas, sendo o tipo mais comum de rolamento.",
         "Apenas cargas combinadas muito elevadas.",
         "Velocidades extremamente baixas com lubrificação a graxa.",
         "Movimento linear ao longo de um eixo."],
        1,
        "O rolamento rígido de esferas (single row deep groove) é o mais versátil: suporta cargas radiais e axiais moderadas em ambas as direções, opera em altas velocidades e é de baixo custo, sendo amplamente utilizado em máquinas industriais.",
        "Engenharia Mecânica", ["mec", "elementosmaquinas"]
    ),
    _q(
        "A figura de mérito de um trocador de calor (efetividade ε) é definida como:",
        ["A razão entre a taxa de calor real transferida e a taxa de calor máxima possível em um trocador de calor contracorrente de área infinita.",
         "A diferença de temperatura entre os fluidos quente e frio na entrada.",
         "A soma das resistências térmicas de condução e convecção.",
         "A relação entre a área superficial e o volume do trocador.",
         "O coeficiente global de transferência de calor U."],
        0,
        "ε = Qreal/Qmax. A efetividade depende do método NTU (Número de Unidades de Transferência) e da configuração do trocador (paralelo, contracorrente, fluxo cruzado, etc.), variando de 0 a 1.",
        "Engenharia Mecânica", ["mec", "transcal"]
    ),
    _q(
        "O processo de usinagem por torneamento caracteriza-se por:",
        ["Ferramenta rotativa de múltiplos cortes avançando contra a peça estacionária.",
         "Peça em movimento de rotação e ferramenta monocortante com movimento de avanço linear, removendo cavacos.",
         "Ferramenta abrasiva rotativa desgastando a superfície da peça.",
         "Erosão do material por descargas elétricas entre eletrodo e peça.",
         "Corte por jato d'água em alta pressão."],
        1,
        "Torneamento: a peça gira (movimento de corte) enquanto a ferramenta monocortante se desloca longitudinal ou transversalmente (movimento de avanço), gerando superfícies cilíndricas, cônicas ou de contorno.",
        "Engenharia Mecânica", ["mec", "usinagem"]
    ),
    _q(
        "Em um circuito trifásico equilibrado ligado em estrela (Y), a relação entre tensão de linha (VL) e tensão de fase (Vf) é:",
        ["VL = Vf.",
         "VL = √2 × Vf.",
         "VL = √3 × Vf.",
         "VL = 3 × Vf.",
         "VL = Vf/√3."],
        2,
        "Na ligação estrela, VL = √3 × Vf ≈ 1,732 × Vf, e a corrente de linha é igual à corrente de fase (IL = If). Na ligação triângulo, VL = Vf e IL = √3 × If.",
        "Engenharia Elétrica", ["ele", "circuitos"]
    ),
    _q(
        "O fator de potência de uma instalação elétrica é definido como:",
        ["A relação entre a energia ativa e a energia reativa.",
         "O cosseno do ângulo de defasagem entre a tensão e a corrente (cos φ), representando a fração da potência aparente que é convertida em trabalho útil.",
         "A relação entre a corrente e a tensão do sistema.",
         "A potência aparente dividida pela potência ativa.",
         "O inverso da impedância do circuito."],
        1,
        "FP = cos φ = P/S (potência ativa / potência aparente). Um FP baixo (cargas indutivas) aumenta a corrente para dada potência útil, gerando perdas e sendo penalizado pelas concessionárias (RES 1000/2021 ANEEL).",
        "Engenharia Elétrica", ["ele", "potencia"]
    ),
    _q(
        "A lei de Kirchhoff das tensões (LKT) estabelece que:",
        ["A soma das correntes que entram em um nó é igual à soma das correntes que saem.",
         "A soma algébrica das tensões ao longo de qualquer caminho fechado (malha) é igual a zero.",
         "A potência total gerada é igual à potência total consumida.",
         "A tensão em um resistor é igual ao produto da corrente pela resistência.",
         "A resistência equivalente de resistores em série é a soma das resistências."],
        1,
        "LKT (2ª lei de Kirchhoff): a soma algébrica das diferenças de potencial (ddp) em uma malha fechada é zero, resultado da conservação da energia no circuito: ∑V = 0.",
        "Engenharia Elétrica", ["ele", "circuitos"]
    ),
    _q(
        "O motor síncrono trifásico opera com velocidade:",
        ["Variável com a carga aplicada ao eixo.",
         "Constante e igual à velocidade síncrona (Ns = 120·f/P), independentemente da carga, desde que dentro do conjugado máximo.",
         "Sempre inferior à velocidade síncrona, com escorregamento.",
         "Apenas em velocidades subsíncronas.",
         "Controlada exclusivamente por inversor de frequência."],
        1,
        "O motor síncrono gira exatamente à velocidade síncrona Ns = 120·f/P (rpm), determinada pela frequência f (Hz) e número de polos P. Não há escorregamento. O conjugado é desenvolvido até o conjugado máximo (pull-out torque).",
        "Engenharia Elétrica", ["ele", "maquinas"]
    ),
    _q(
        "Em uma subestação elétrica, o disjuntor de alta tensão tem a função de:",
        ["Apenas isolar o circuito sem carga para manutenção.",
         "Interromper correntes de carga e de curto-circuito, extinguindo o arco elétrico de forma segura.",
         "Medir a corrente que passa pelo circuito.",
         "Transformar níveis de tensão entre os circuitos primário e secundário.",
         "Compensar o fator de potência da instalação."],
        1,
        "O disjuntor é o equipamento de proteção que interrompe o fluxo de corrente em condições normais (manobra) e de falta (curto-circuito), utilizando meios de extinção do arco como SF₆, óleo, vácuo ou ar comprimido.",
        "Engenharia Elétrica", ["ele", "potencia"]
    ),
    _q(
        "A proteção diferencial (relé 87) é utilizada para proteger:",
        ["Linhas de transmissão contra sobretensões atmosféricas.",
         "Transformadores de potência, geradores e barras contra faltas internas, comparando as correntes de entrada e saída do equipamento.",
         "Motores contra sobrecarga térmica.",
         "Banco de capacitores contra harmônicos.",
         "Sistemas de aterramento contra correntes de fuga."],
        1,
        "O relé diferencial (87) aplica o princípio de Kirchhoff: em condições normais, a corrente que entra é igual à que sai. Se houver diferença (corrente diferencial), indica falta interna e o relé atua comandando a abertura dos disjuntores.",
        "Engenharia Elétrica", ["ele", "protecao"]
    ),
    _q(
        "No chaveamento de indutor em corrente contínua (CC), a tensão induzida no momento da abertura da chave pode ser muito elevada, sendo necessário utilizar:",
        ["Um resistor em série para limitar a corrente.",
         "Um diodo de roda livre (flyback diode) em antiparalelo com a carga indutiva para circular a corrente de extinção.",
         "Um capacitor em série para filtrar a tensão.",
         "Um transformador de isolamento.",
         "Um varistor para proteção contra surtos."],
        1,
        "O diodo de roda livre (também chamado de diodo flyback) é colocado em antiparalelo com a carga indutiva: quando a chave abre, o diodo conduz a corrente de extinção do indutor, evitando a sobretensão que poderia danificar a chave ou o circuito.",
        "Engenharia Elétrica", ["ele", "eletronica"]
    ),
    _q(
        "Em sistemas de potência, a capacidade de curto-circuito em um barramento é medida em MVA e depende:",
        ["Apenas da tensão nominal do barramento.",
         "Da tensão nominal e da impedância equivalente de Thévenin vista do barramento até as fontes de geração.",
         "Exclusivamente do tipo de disjuntor instalado.",
         "Da corrente nominal do transformador da subestação.",
         "Da distância física até a subestação mais próxima."],
        1,
        "Scc (MVA) = √3 × Vn (kV) × Icc (kA). A corrente de curto-circuito Icc depende da impedância equivalente de Thévenin (Zth), que considera a contribuição de geradores, transformadores e linhas de transmissão até o ponto de falta.",
        "Engenharia Elétrica", ["ele", "potencia"]
    ),
    _q(
        "O controle PID (Proporcional-Integral-Derivativo) em instrumentação industrial combina três ações:",
        ["Ação proporcional ao erro, ação integral para eliminar o erro em regime permanente e ação derivativa para antecipar a tendência do erro.",
         "Apenas ação liga-desliga (on-off).",
         "Controle de malha aberta sem realimentação.",
         "Ação proporcional e derivativa apenas, sem ação integral.",
         "Compensação de perturbações por feedforward exclusivamente."],
        0,
        "PID: P (proporcional) responde ao erro atual; I (integral) elimina o offset acumulando o erro ao longo do tempo; D (derivativo) antecipa o erro futuro pela taxa de variação. Sintonia adequada é essencial para estabilidade e desempenho.",
        "Engenharia Elétrica", ["ele", "instrumentacao"]
    ),
    _q(
        "As linhas de transmissão de energia elétrica em corrente alternada (CA) apresentam o efeito Ferranti, que consiste em:",
        ["Elevação da tensão no final da linha em relação ao início, devido à corrente capacitiva em linhas longas e pouco carregadas.",
         "Redução da tensão proporcional ao comprimento da linha.",
         "Aquecimento excessivo dos cabos condutores.",
         "Perda de potência por efeito corona.",
         "Ressonância série entre indutância e capacitância da linha."],
        0,
        "Efeito Ferranti: em linhas longas de transmissão em CA, a corrente capacitiva (gerada pela capacitância natural da linha) circula pela indutância série, causando elevação da tensão no terminal receptor quando a linha está em vazio ou com baixa carga.",
        "Engenharia Elétrica", ["ele", "potencia"]
    ),
    _q(
        "A transformação de coordenadas ABC para αβ0 (transformada de Clarke) em sistemas trifásicos é utilizada para:",
        ["Simplificar o cálculo de faltas simétricas.",
         "Separar o sistema trifásico em componentes de sequência zero e dois eixos ortogonais α e β, simplificando a análise de máquinas elétricas.",
         "Converter tensões trifásicas em tensões CC.",
         "Calcular a impedância de sequência zero de transformadores.",
         "Analisar harmônicos em sistemas de distribuição."],
        1,
        "A transformada de Clarke (ABC → αβ0) projeta as grandezas trifásicas em um referencial bifásico estacionário (α, β), mantendo a magnitude. É base para a transformada de Park (dq0) usada em controle de motores e geradores.",
        "Engenharia Elétrica", ["ele", "maquinas"]
    ),
    _q(
        "O aterramento elétrico do tipo TN-S (NF C 15-100) caracteriza-se por:",
        ["Neutro aterrado na origem, condutor de proteção (PE) separado do neutro em todo o circuito, garantindo baixa impedância de falta.",
         "Aterramento apenas do condutor neutro em carga.",
         "Condutor de proteção ausente, utilizando o neutro como proteção.",
         "Aterramento independente das massas sem vínculo com o neutro.",
         "Condutor PEN combinando neutro e proteção em todo o circuito."],
        0,
        "TN-S: neutro aterrado na fonte (transformador) e condutor PE (proteção) separado do N (neutro) ao longo de toda a instalação. Garante alta segurança e é obrigatório para circuitos com dispositivos DR e equipamentos sensíveis.",
        "Engenharia Elétrica", ["ele", "nr10"]
    ),
    _q(
        "Em uma coluna de destilação, o refluxo tem a função de:",
        ["Aquecer o fundo da coluna para vaporizar os componentes pesados.",
         "Retornar parte do condensado do topo para a coluna, aumentando a pureza do produto de topo por meio de maior contato líquido-vapor.",
         "Separar os componentes por densidade.",
         "Retirar o produto de fundo continuamente.",
         "Alimentar a coluna com a mistura a ser separada."],
        1,
        "Refluxo (razão R = L/D) retorna líquido condensado do topo à coluna, aumentando a eficiência da separação: o líquido descendente absorve os componentes menos voláteis do vapor ascendente, enriquecendo o vapor nos componentes mais leves.",
        "Engenharia Química", ["quim", "operacoes"]
    ),
    _q(
        "A equação de Antoine é utilizada para estimar:",
        ["A viscosidade de líquidos em função da temperatura.",
         "A pressão de vapor de uma substância pura em função da temperatura, utilizando três parâmetros empíricos.",
         "O coeficiente de difusão binária em gases.",
         "A condutividade térmica de fluidos.",
         "O calor específico de soluções diluídas."],
        1,
        "Equação de Antoine: log₁₀ Pvap = A − B/(C + T), onde Pvap é a pressão de vapor (mmHg ou bar), T a temperatura (°C ou K), e A, B, C são parâmetros específicos da substância. Essencial para cálculos de equilíbrio líquido-vapor (ELV).",
        "Engenharia Química", ["quim", "termo"]
    ),
    _q(
        "No balanço de massa de um processo em estado estacionário, a equação geral é:",
        ["Acúmulo = Entrada + Saída − Geração.",
         "Entrada + Geração = Saída + Consumo (para regime permanente, acúmulo = 0).",
         "Entrada = Geração × Saída.",
         "Acúmulo = Entrada × Consumo.",
         "Saída = Geração / Entrada."],
        1,
        "Balanço de massa em regime permanente: massa que entra + massa gerada (por reação) = massa que sai + massa consumida (por reação). O termo de acúmulo é zero em estado estacionário. Balanço global sem reação: entrada = saída.",
        "Engenharia Química", ["quim", "processos"]
    ),
    _q(
        "A extração líquido-líquido é uma operação unitária que separa componentes com base:",
        ["Nas diferenças de ponto de ebulição entre os componentes.",
         "Na diferença de solubilidade dos componentes entre duas fases líquidas imiscíveis (solvente e alimentação).",
         "No tamanho das partículas dos componentes.",
         "Na densidade dos componentes sólidos em suspensão.",
         "Na carga elétrica dos íons em solução aquosa."],
        1,
        "Na extração líquido-líquido (ELL), um solvente seletivo extrai um ou mais componentes de uma mistura líquida, formando duas fases: extrato (solvente + soluto) e refinado (alimentação residual). Aplicada quando a destilação é inviável (ex: azeótropos, termosensíveis).",
        "Engenharia Química", ["quim", "operacoes"]
    ),
    _q(
        "Em cinética química, a ordem de uma reação é determinada:",
        ["Apenas pela estequiometria da reação química balanceada.",
         "Experimentalmente, pela relação entre a velocidade da reação e a concentração dos reagentes, podendo ser fracionária ou negativa.",
         "Pela temperatura de operação do reator.",
         "Pelo tipo de catalisador utilizado.",
         "Pela pressão de operação do sistema."],
        1,
        "A ordem de reação (n) é obtida experimentalmente (método das velocidades iniciais, meia-vida, etc.) e não coincide necessariamente com os coeficientes estequiométricos. Por exemplo, decomposição do N₂O₅ é 1ª ordem, apesar da estequiometria 2N₂O₅ → 4NO₂ + O₂.",
        "Engenharia Química", ["quim", "cinetica"]
    ),
    _q(
        "A membrana de osmose inversa é aplicada no tratamento de água para:",
        ["Remover apenas sólidos grosseiros em suspensão.",
         "Remover sais dissolvidos, íons e moléculas pequenas, aplicando pressão superior à pressão osmótica da solução.",
         "Esterilizar a água por radiação ultravioleta.",
         "Ajustar o pH da água por troca iônica.",
         "Remover micro-organismos por filtração em profundidade."],
        1,
        "Osmose inversa (RO) utiliza membranas semipermeáveis que retêm sais dissolvidos (rejeição > 99% para NaCl) e impurezas moleculares, operando com pressões de 15-70 bar, sendo amplamente usada em dessalinização e produção de água ultrapura.",
        "Engenharia Química", ["quim", "processos"]
    ),
    _q(
        "O fator de compressibilidade Z de um gás real é definido como:",
        ["Z = P × V / (n × R × T). Para gás ideal, Z = 1. Desvios indicam comportamento não ideal.",
         "Z = (∂P/∂V)T, indicando a compressibilidade do gás.",
         "Z = P × V / T, medindo a energia interna do gás.",
         "Z = n × R × T / (P × V).",
         "Z = (P × V²)/(n × T), para correção de volume."],
        0,
        "Z = Pv/(RT). Fator de compressibilidade: Z = 1 para gás ideal; Z < 1 indica forças atrativas predominantes (gás mais compressível); Z > 1 indica forças repulsivas (menos compressível). Correlações (Peng-Robinson, SRK) estimam Z para projetos.",
        "Engenharia Química", ["quim", "termo"]
    ),
    _q(
        "A reforma a vapor do metano (steam methane reforming - SMR) é o principal processo industrial para produção de:",
        ["Hidrogênio (H₂) a partir de metano (CH₄) e vapor d'água (H₂O), com catalisador de níquel e altas temperaturas.",
         "Etanol a partir de cana-de-açúcar.",
         "Gasolina sintética a partir de gás natural.",
         "Amônia a partir de nitrogênio e hidrogênio.",
         "Metanol a partir de monóxido de carbono e hidrogênio."],
        0,
        "SMR: CH₄ + H₂O → CO + 3H₂ (reação endotérmica, ~800-1000°C, catalisador Ni), seguida de shift: CO + H₂O → CO₂ + H₂. Produz cerca de 95% do H₂ mundial. O CO₂ gerado é o principal desafio ambiental (hidrogênio cinza vs. azul/verde).",
        "Engenharia Química", ["quim", "petroquimica"]
    ),
    _q(
        "No balanço de energia de um reator químico, o calor de reação ΔHr é considerado:",
        ["Positivo (ΔHr > 0) para reações exotérmicas, liberando calor.",
         "Negativo (ΔHr < 0) para reações exotérmicas, liberando calor para o meio; ΔHr > 0 para endotérmicas.",
         "Sempre igual a zero, pois a energia se conserva.",
         "Independente da temperatura de operação.",
         "Igual à energia de ativação da reação."],
        1,
        "Convenção termodinâmica: ΔHr < 0 (exotérmica, calor liberado) e ΔHr > 0 (endotérmica, calor absorvido). O sinal depende da definição (entalpia dos produtos menos entalpia dos reagentes). O calor de reação varia com a temperatura pela lei de Kirchhoff.",
        "Engenharia Química", ["quim", "termo"]
    ),
    _q(
        "O fenômeno de fluidização ocorre quando:",
        ["Um fluido passa através de um leito de partículas sólidas a uma velocidade suficiente para suspender as partículas, fazendo o leito comportar-se como um fluido.",
         "Um líquido se mistura completamente com um gás formando uma emulsão estável.",
         "Sólidos dissolvem-se completamente em um solvente líquido.",
         "Partículas sólidas sedimentam-se no fundo de um tanque por ação da gravidade.",
         "Um gás se liquefaz por aumento de pressão."],
        0,
        "Fluidização: quando a velocidade superficial do fluido atinge a velocidade mínima de fluidização (Umf), a força de arrasto equilibra o peso das partículas, expandindo o leito. Aplicações: FCC (craqueamento catalítico fluidizado), secadores, reatores de leito fluidizado.",
        "Engenharia Química", ["quim", "operacoes"]
    ),
    _q(
        "A Técnica de Incidentes Críticos (TIC) e a Análise Preliminar de Riscos (APR) são ferramentas de segurança de processo que se diferenciam por:",
        ["APR identifica riscos na fase de projeto (antes da operação), enquanto TIC analisa eventos indesejados ocorridos para prevenir recorrências.",
         "APR é quantitativa e TIC é qualitativa.",
         "APR substitui completamente a necessidade de HAZOP.",
         "TIC é aplicada apenas após acidentes fatais.",
         "APR não requer equipe multidisciplinar."],
        0,
        "APR (Análise Preliminar de Riscos) é uma técnica qualitativa aplicada na fase de concepção/projeto para identificar perigos e estimar riscos iniciais. TIC (Técnica de Incidentes Críticos) analisa incidentes passados (quase-acidentes) para identificar causas raízes e implementar ações corretivas preventivas.",
        "Engenharia Química", ["quim", "seguranca"]
    ),
    _q(
        "O planejamento agregado da produção (PAP) tem como horizonte de tempo típico:",
        ["Curto prazo (dias a semanas).",
         "Médio prazo (3 a 18 meses), equilibrando capacidade produtiva e demanda agregada.",
         "Longo prazo (5 a 10 anos) para definição de estratégia corporativa.",
         "Apenas o próximo mês, revisado diariamente.",
         "O ciclo de vida completo do produto (10 a 20 anos)."],
        1,
        "O PAP (S&OP) é um plano tático de médio prazo (3-18 meses) que define níveis de produção, estoques, força de trabalho e subcontratação para atender à demanda agregada prevista, dentro das restrições de capacidade instalada.",
        "Engenharia de Produção", ["prod", "pcp"]
    ),
    _q(
        "No método 5S, a etapa 'Seiton' (ordenação) consiste em:",
        ["Separar o útil do inútil e descartar o desnecessário.",
         "Organizar os materiais e ferramentas de forma que estejam sempre disponíveis e fáceis de encontrar, cada coisa em seu lugar.",
         "Padronizar as melhores práticas de limpeza e organização.",
         "Manter e melhorar continuamente os padrões estabelecidos.",
         "Disciplinar os colaboradores para seguir os procedimentos."],
        1,
        "5S: Seiri (utilização/senso de descarte), Seiton (ordenação, cada coisa em seu lugar), Seiso (limpeza), Seiketsu (padronização/saúde), Shitsuke (disciplina/manutenção). Seiton é a fase de organizar e identificar locais de guarda.",
                 "Engenharia de Produção", ["prod", "qualidade"]
    ),
    # ── Segurança do Trabalho (25) ── NR-4, NR-5, NR-6, NR-7, NR-9, NR-10, NR-12, NR-15, NR-17, NR-33, NR-35 ──
    #
    _q(
        "A NR-4 estabelece que o Serviço Especializado em Engenharia de Segurança e em Medicina do Trabalho (SESMT) deve ser dimensionado em função do(a):",
        ["Número de empregados e grau de risco da atividade principal da empresa.",
         "Faturamento anual da empresa.",
         "Localização geográfica do estabelecimento.",
         "Tempo de funcionamento da empresa no mercado.",
         "Nível de escolaridade dos empregados."],
        0,
        "NR-4, item 4.2: o SESMT é dimensionado conforme o grau de risco (GR) da atividade principal e o número de empregados do estabelecimento, conforme Tabela I da NR-4.",
        "Segurança do Trabalho", ["nr4"]
    ),
    _q(
        "De acordo com a NR-5, a Comissão Interna de Prevenção de Acidentes (CIPA) tem como objetivo principal:",
        ["Aplicar multas e penalidades aos trabalhadores que descumprirem normas de segurança.",
         "Observar e relatar condições de risco nos ambientes de trabalho, solicitar medidas para eliminar perigos e promover a prevenção de acidentes.",
         "Substituir integralmente o SESMT na gestão de segurança do trabalho.",
         "Elaborar o laudo técnico de insalubridade e periculosidade da empresa.",
         "Gerenciar o plano de saúde ocupacional dos funcionários terceirizados."],
        1,
        "NR-5, item 5.1: a CIPA tem como atribuição a prevenção de acidentes e doenças decorrentes do trabalho, observando condições de risco, promovendo campanhas e sugerindo medidas preventivas.",
        "Segurança do Trabalho", ["nr5"]
    ),
    _q(
        "Segundo a NR-6, considera-se Equipamento de Proteção Individual (EPI) o dispositivo de uso individual utilizado pelo trabalhador destinado à proteção de riscos suscetíveis de ameaçar a segurança e a saúde no trabalho. O EPI deve ser:",
        ["Adquirido e custeado integralmente pelo trabalhador.",
         "Fornecido gratuitamente pelo empregador, mediante registro de entrega (CA válido), sendo de responsabilidade do trabalhador a conservação e higienização.",
         "Opcional, cabendo ao trabalhador decidir quando utilizá-lo.",
         "Fornecido apenas para trabalhadores com mais de 5 anos de empresa.",
         "Substituído anualmente, independentemente do estado de conservação."],
        1,
        "NR-6, item 6.3: o empregador deve fornecer o EPI adequado ao risco, com Certificado de Aprovação (CA), gratuitamente, e o trabalhador deve utilizá-lo e conservá-lo.",
        "Segurança do Trabalho", ["nr6"]
    ),
    _q(
        "O Programa de Controle Médico de Saúde Ocupacional (PCMSO), previsto na NR-7, tem como diretriz principal:",
        ["Realizar exames médicos admissionais, periódicos, de retorno ao trabalho, de mudança de função e demissionais, visando à promoção e preservação da saúde dos trabalhadores.",
         "Substituir integralmente o PPRA/PGR na gestão de riscos ocupacionais.",
         "Exigir que todos os trabalhadores realizem exames genéticos para mapeamento de doenças hereditárias.",
         "Definir o grau de insalubridade das atividades da empresa.",
         "Estabelecer o plano de carreira e remuneração dos profissionais de saúde ocupacional."],
        0,
        "NR-7, item 7.1.1: o PCMSO deve ser elaborado e implantado com base nos riscos ocupacionais identificados, incluindo exames médicos obrigatórios e emissão do ASO (Atestado de Saúde Ocupacional).",
        "Segurança do Trabalho", ["nr7"]
    ),
    _q(
        "A NR-9 (Programa de Prevenção de Riscos Ambientais — PPRA, substituído pelo PGR/GRO) estabelece que os riscos ambientais são classificados como:",
        ["Físicos, químicos e biológicos.",
         "Apenas riscos de acidentes mecânicos.",
         "Riscos ergonômicos e psicossociais exclusivamente.",
         "Riscos financeiros e econômicos.",
         "Apenas riscos de incêndio e explosão."],
        0,
        "NR-9 (vigente até a entrada do novo GRO): os riscos ambientais incluem agentes físicos (ruído, vibração, calor, frio, pressão, radiação), químicos (poeiras, fumos, gases, vapores) e biológicos (bactérias, fungos, vírus, parasitas). A nova NR-1 (GRO) amplia a abordagem para riscos ocupacionais.",
        "Segurança do Trabalho", ["nr9"]
    ),
    _q(
        "De acordo com a NR-10 (Segurança em Instalações e Serviços em Eletricidade), é obrigatório que os serviços em instalações elétricas sejam realizados somente por:",
        ["Qualquer trabalhador maior de 18 anos.",
         "Trabalhador qualificado, capacitado ou autorizado, com treinamento específico conforme Anexo II da NR-10 e reciclagem bienal.",
         "Engenheiro eletricista exclusivamente.",
         "Técnico em eletrônica formado por instituição reconhecida pelo MEC.",
         "Profissional com mais de 10 anos de experiência em eletricidade."],
        1,
        "NR-10, item 10.8.1: os serviços em instalações elétricas só podem ser realizados por trabalhador autorizado, que atenda às condições de qualificação, capacitação e autorização definidas na NR-10, com treinamento específico de 40h.",
        "Segurança do Trabalho", ["nr10"]
    ),
    _q(
        "A NR-12 (Segurança no Trabalho em Máquinas e Equipamentos) estabelece que as máquinas devem possuir dispositivos de segurança, como:",
        ["Sistemas de proteção fixa, móvel e dispositivos de intertravamento, sensores de segurança e botões de parada de emergência.",
         "Apenas um manual de instruções em inglês.",
         "Sistema de alerta visual com luzes piscantes em todas as máquinas.",
         "Extintor de incêndio fixado na estrutura da máquina.",
         "Sensor de presença para desligamento em caso de aproximação de qualquer pessoa."],
        0,
        "NR-12, itens 12.30 a 12.38: as máquinas devem ter proteções fixas e móveis com intertravamento, dispositivos de segurança (sensores, cortinas de luz), parada de emergência e sistema de partida segura, conforme Anexos da NR-12.",
        "Segurança do Trabalho", ["nr12"]
    ),
    _q(
        "A NR-15 (Atividades e Operações Insalubres) define insalubridade como:",
        ["A exposição a agentes nocivos à saúde acima dos limites de tolerância estabelecidos, gerando direito ao adicional de insalubridade em graus mínimo (10%), médio (20%) e máximo (40%).",
         "Qualquer atividade executada em altura superior a 2 metros.",
         "Toda atividade realizada em ambiente com ruído acima de 50 dB(A).",
         "A execução de horas extras habituais acima de 2 horas diárias.",
         "O trabalho noturno em qualquer atividade econômica."],
        0,
        "NR-15: insalubridade é caracterizada quando a exposição ao agente nocivo ultrapassa os limites de tolerância. Graus: máximo (40% do salário mínimo), médio (20%) e mínimo (10%), conforme Anexos da NR-15.",
        "Segurança do Trabalho", ["nr15"]
    ),
    _q(
        "A NR-17 (Ergonomia) estabelece que, no trabalho sentado, devem ser observados critérios como:",
        ["Altura do assento ajustável, apoio para os pés, encosto adaptável e bordas arredondadas, garantindo boa postura e circulação.",
         "Cadeira fixa sem regulagem, com encosto reto e assento plano.",
         "Banco tipo tamborete com altura única padronizada.",
         "Assento giratório sem encosto, permitindo livre movimentação.",
         "Cadeira reclinável para descanso dos trabalhadores durante o expediente."],
        0,
        "NR-17, item 17.3.2: o assento deve ter altura ajustável à estatura do trabalhador, apoio para os pés quando necessário, encosto adaptável à curvatura lombar e bordas arredondadas.",
        "Segurança do Trabalho", ["nr17"]
    ),
    _q(
        "A NR-33 (Segurança e Saúde nos Trabalhos em Espaços Confinados) define como espaço confinado:",
        ["Qualquer área ao ar livre com presença de gases tóxicos.",
         "Área não projetada para ocupação humana contínua, com meios limitados de entrada e saída, ventilação insuficiente e risco de atmosfera perigosa.",
         "Todo ambiente subterrâneo como túneis e galerias independentemente do tamanho.",
         "Apenas tanques e vasos de pressão com diâmetro superior a 2 metros.",
         "Salas com ventilação mecânica e portas de emergência."],
        1,
        "NR-33, item 33.1.1: espaço confinado é qualquer área não projetada para ocupação contínua, com meios limitados de entrada e saída, ventilação deficiente e que pode conter atmosfera perigosa (deficiente ou enriquecida de oxigênio, inflamável, tóxica).",
        "Segurança do Trabalho", ["nr33"]
    ),
    _q(
        "De acordo com a NR-35 (Trabalho em Altura), considera-se trabalho em altura toda atividade executada acima de:",
        ["1,00 m.",
         "1,50 m.",
         "2,00 m.",
         "2,50 m.",
         "3,00 m."],
        2,
        "NR-35, item 35.1.1: considera-se trabalho em altura toda atividade executada acima de 2,00 m do nível inferior, com risco de queda. Exige treinamento específico de 8h, ASO, sistema de proteção contra quedas e análise de risco.",
        "Segurança do Trabalho", ["nr35"]
    ),
    _q(
        "O Perfil Profissiográfico Previdenciário (PPP), instituído pela Lei 8.213/1991 e regulamentado pelo INSS, é um documento que:",
        ["Substitui a carteira de trabalho para fins de aposentadoria.",
         "Registra as condições ambientais de trabalho, exposição a agentes nocivos e informações sobre o fator previdenciário, sendo obrigatório para aposentadoria especial.",
         "É um atestado médico que comprova a aptidão do trabalhador para trabalho em altura.",
         "Define o grau de risco da empresa para fins de dimensionamento do SESMT.",
         "Certifica a qualidade dos equipamentos de proteção individual utilizados na empresa."],
        1,
        "Lei 8.213/1991, Art. 58 e IN INSS 77/2015: o PPP é o documento histórico-laboral que comprova as condições de exposição a agentes nocivos para concessão de aposentadoria especial e outros benefícios previdenciários.",
        "Segurança do Trabalho", ["ppp"]
    ),
    _q(
        "A Comunicação de Acidente de Trabalho (CAT) deve ser emitida pelo empregador à Previdência Social até:",
        ["O primeiro dia útil seguinte ao da ocorrência, em caso de acidente típico ou de trajeto, ou imediatamente em caso de morte.",
         "30 dias corridos após a data do acidente.",
         "15 dias úteis para acidentes sem afastamento.",
         "Apenas quando houver afastamento superior a 15 dias.",
         "No momento da rescisão contratual do empregado acidentado."],
        0,
        "Lei 8.213/1991, Art. 22: a CAT deve ser emitida até o 1º dia útil seguinte ao acidente (típico ou trajeto) e imediatamente em caso de óbito. O empregador é obrigado a emitir a CAT sob pena de multa.",
        "Segurança do Trabalho", ["cat"]
    ),
    _q(
        "O Mapa de Riscos Ambientais, previsto na NR-5 (CIPA), é uma representação gráfica do local de trabalho que:",
        ["Substitui o PPRA/PGR na identificação de riscos.",
         "Identifica os riscos físicos, químicos, biológicos, ergonômicos e de acidentes por meio de círculos de cores e tamanhos, conforme intensidade.",
         "Serve exclusivamente como documento contábil para auditoria fiscal.",
         "É facultativo para empresas com até 50 empregados.",
         "Deve ser elaborado exclusivamente pelo SESMT."],
        1,
        "NR-5, item 5.13 e alíneas: a CIPA deve elaborar o Mapa de Riscos com a participação dos trabalhadores. Cores: verde (físico), vermelho (químico), marrom (biológico), azul (ergonômico), amarelo (acidente). Tamanho do círculo indica grau do risco.",
        "Segurança do Trabalho", ["mapaderiscos"]
    ),
    _q(
        "Segundo a NR-10, o Prontuário de Instalações Elétricas (PIE) deve conter, entre outros documentos:",
        ["O conjunto de diagramas unifilares, descrição das instalações, procedimentos de segurança e certificações de equipamentos elétricos.",
         "Apenas a relação de todos os equipamentos de proteção individual adquiridos no último ano.",
         "O balanço financeiro anual do departamento elétrico.",
         "O plano de carreira dos profissionais eletricistas.",
         "O histórico de multas recebidas por infrações elétricas."],
        0,
        "NR-10, item 10.2.3: o PIE deve conter diagramas unifilares atualizados, memorial descritivo, especificação dos dispositivos de proteção, procedimentos de segurança e certificações dos equipamentos elétricos, sob responsabilidade de profissional habilitado.",
        "Segurança do Trabalho", ["nr10"]
    ),
    _q(
        "A NR-12 determina que as máquinas e equipamentos devem ser submetidos à inspeção periódica conforme:",
        ["A norma técnica nacional ABNT NBR aplicável ou, na ausência, recomendações do fabricante, com periodicidade definida em procedimento documentado.",
         "A inspeção diária visual realizada pelo operador, sem necessidade de registro documental.",
         "Inspeção anual obrigatória realizada exclusivamente pelo fabricante original.",
         "Apenas no momento da instalação e após 10 anos de uso.",
         "Inspeção fiscal realizada pelo Ministério do Trabalho a cada 5 anos."],
        0,
        "NR-12, item 12.126: as máquinas devem ser submetidas a inspeções de acordo com normas técnicas nacionais (ABNT) ou internacionais aplicáveis, com periodicidade definida em procedimentos documentados, garantindo condições seguras de operação.",
        "Segurança do Trabalho", ["nr12"]
    ),
    _q(
        "No contexto da NR-15, o adicional de periculosidade é devido ao trabalhador que exerce atividade em contato com:",
        ["Inflamáveis, explosivos, eletricidade em alta tensão (acima de 250V) e radiações ionizantes, conforme regulamentação específica.",
         "Produtos de limpeza e higienização de uso comum.",
         "Equipamentos de escritório como computadores e impressoras.",
         "Veículos automotores leves em área interna da empresa.",
         "Máquinas de corte e solda a frio."],
        0,
        "NR-16 e CLT Art. 193: o adicional de periculosidade (30%) é devido para exposição a inflamáveis, explosivos, energia elétrica (NR-16 Anexo IV), radiações ionizantes e substâncias radioativas, caracterizado por perícia técnica.",
        "Segurança do Trabalho", ["nr16"]
    ),
    _q(
        "O Programa de Gerenciamento de Riscos (PGR), instituído pela nova NR-1 (2021), substitui qual programa anterior?",
        ["O PPRA (Programa de Prevenção de Riscos Ambientais), que foi incorporado ao PGR como parte do gerenciamento de riscos ocupacionais.",
         "O PCMSO, que passou a ser facultativo.",
         "A CIPA, que teve suas atribuições extintas.",
         "O PCMAT, que perdeu a obrigatoriedade.",
         "O Programa de Proteção Respiratória (PPR), que foi descontinuado."],
        0,
        "NR-1 (vigente a partir de 2021): o PGR substitui o PPRA, integrando a identificação, avaliação e controle dos riscos ocupacionais (físicos, químicos, biológicos, ergonômicos e de acidentes) ao invés de apenas riscos ambientais.",
        "Segurança do Trabalho", ["nr1"]
    ),
    _q(
        "De acordo com a NR-17, para trabalho que exija digitação ou uso de teclado, recomenda-se, além dos critérios de mobiliário:",
        ["Pausas de 10 minutos a cada 50 minutos trabalhados para descanso dos músculos e visão, sem prejuízo da remuneração.",
         "Obrigatoriedade de luvas anti-vibração para todos os digitadores.",
         "Uso exclusivo de teclados ergonômicos importados.",
         "Exame de visão obrigatório a cada 3 meses.",
         "Alternância obrigatória entre digitação e trabalho braçal a cada 2 horas."],
        0,
        "NR-17, item 17.6.3: a organização do trabalho deve prever pausas de 10 minutos a cada 50 minutos de digitação ou processamento de dados, sem prejuízo da remuneração, para prevenir LER/DORT.",
        "Segurança do Trabalho", ["nr17"]
    ),
    _q(
        "Na elaboração do Mapa de Riscos pela CIPA, a cor azul representa riscos:",
        ["Físicos (ruído, calor, radiação).",
         "Ergonômicos (postura inadequada, repetitividade, levantamento de peso).",
         "Químicos (gases, vapores, poeiras).",
         "Biológicos (bactérias, fungos, vírus).",
         "De acidentes (máquinas sem proteção, iluminação inadequada)."],
        1,
        "NR-5, Mapa de Riscos: verde (físico), vermelho (químico), marrom (biológico), azul (ergonômico), amarelo (acidente). O tamanho do círculo (pequeno, médio, grande) indica a intensidade do risco.",
        "Segurança do Trabalho", ["mapaderiscos"]
    ),
    _q(
        "Quanto à classificação dos agentes insalubres na NR-15, o Benzeno é classificado no Anexo 13-A como:",
        ["Agente de baixa toxicidade com tolerância de 8 ppm.",
         "Agente cancerígeno de uso proibido em operações industriais, com exceções específicas e controle rigoroso.",
         "Agente asfixiante simples sem limites de tolerância estabelecidos.",
         "Agente de alta toxicidade com tolerância de 0,5 ppm.",
         "Agente inerte sem classificação de insalubridade."],
        1,
        "NR-15, Anexo 13-A: o Benzeno é cancerígeno (leucemia), proibido em processos industriais, exceto em laboratórios de análise e na indústria petroquímica para produção de benzeno e derivados, com limites de tolerância rigorosos e monitoramento biológico obrigatório.",
        "Segurança do Trabalho", ["nr15"]
    ),
    _q(
        "A NR-33 exige que o trabalho em espaço confinado seja precedido de:",
        ["Autorização verbal do supervisor da área, sem necessidade de documentação.",
         "Permissão de Entrada e Trabalho (PET) formal, emitida pelo supervisor de entrada, com identificação dos riscos, procedimentos e equipe.",
         "Aprovação do engenheiro de segurança do trabalho com Anotação de Responsabilidade Técnica (ART).",
         "Alvará da prefeitura municipal autorizando o acesso ao local.",
         "Comunicação prévia ao corpo de bombeiros com 48 horas de antecedência."],
        1,
        "NR-33, item 33.3.3: a Permissão de Entrada e Trabalho (PET) é o documento formal que autoriza a entrada em espaço confinado, contendo os riscos, procedimentos, equipe (supervisor, vigia, trabalhador autorizado) e medidas de emergência.",
        "Segurança do Trabalho", ["nr33"]
    ),
    _q(
        "Em relação aos Equipamentos de Proteção Coletiva (EPC), a NR-12 determina que as zonas de perigo em máquinas devem ser protegidas por:",
        ["Barreiras físicas (fixas ou móveis com intertravamento), cortinas de luz, sensores de presença e dispositivos de retenção.",
         "Apenas sinalização visual adesivada com pictogramas de alerta.",
         "Isolamento acústico e térmico de toda a área de operação.",
         "Ventilação forçada e exaustão de gases.",
         "Sistemas de combate a incêndio automáticos sobre a máquina."],
        0,
        "NR-12, itens 12.30-12.40: a proteção coletiva deve ser priorizada sobre a individual. Inclui enclausuramento de máquinas, dispositivos de intertravamento, cortinas de luz, sensores capacitivos e zonas de detecção de presença.",
        "Segurança do Trabalho", ["nr12"]
    ),
    _q(
        "O adicional de periculosidade devido ao trabalhador exposto a inflamáveis, segundo a NR-16, é de:",
        ["20% sobre o salário base.",
         "30% sobre o salário base, sem os acréscimos de gratificações e prêmios.",
         "40% sobre o salário mínimo.",
         "50% sobre a remuneração total.",
         "15% sobre o salário contratual."],
        1,
        "NR-16, item 16.2 e Súmula 364 TST: o adicional de periculosidade é de 30% sobre o salário base (sem gratificações), devido para exposição permanente a inflamáveis, explosivos e energia elétrica, caracterizado por perícia técnica.",
        "Segurança do Trabalho", ["nr16"]
    ),
    _q(
        "A NR-10 estabelece que as instalações elétricas, antes de serem consideradas desenergizadas e liberadas para serviços, devem ser submetidas a procedimentos na seguinte sequência:",
        ["Seccionamento, impedimento de reenergização, constatação de ausência de tensão, instalação de aterramento temporário, proteção de elementos energizados e sinalização.",
         "Desligamento do disjuntor geral, remoção da sinalização e início imediato do serviço.",
         "Comunicação ao centro de controle, espera de 30 minutos e início dos trabalhos.",
         "Abertura da chave geral, colocação de placa de advertência e início do reparo.",
         "Isolamento visual, desligamento do nobreak e religamento após o serviço."],
        0,
        "NR-10, item 10.5.1: a sequência obrigatória para desenergização é: seccionar (abrir fontes), impedir reenergização (travamento/etiqueta), constatar ausência de tensão, aterrar temporariamente, proteger elementos energizados residuais e sinalizar a área.",
        "Segurança do Trabalho", ["nr10"]
    ),
    # ── Contabilidade/Custos (15) ──
    #
    _q(
        "Na contabilidade de custos, os custos fixos são aqueles que:",
        ["Variam proporcionalmente ao volume de produção.",
         "Independem do volume de produção, como aluguel da fábrica e salários da administração da produção, dentro de determinada capacidade instalada.",
         "São exclusivamente os materiais diretos aplicados no produto.",
         "São apropriados apenas no final do exercício fiscal.",
         "Dependem do preço de venda do produto no mercado."],
        1,
        "Custos fixos (aluguel, depreciação linear, seguros) não variam com o volume produzido no curto prazo, dentro da capacidade instalada.",
        "Contabilidade/Custos", ["custos"]
    ),
    _q(
        "Na Demonstração do Resultado do Exercício (DRE), o Lucro Bruto é calculado como:",
        ["Receita Líquida − Custos dos Produtos Vendidos (CPV).",
         "Receita Bruta − Impostos − Despesas Operacionais.",
         "Lucro Operacional − Despesas Financeiras.",
         "Receita Líquida − Despesas Administrativas.",
         "Lucro Líquido + Imposto de Renda."],
        0,
        "DRE: Receita Bruta (− deduções) = Receita Líquida (− CPV) = Lucro Bruto (− Desp. Operacionais) = Resultado Operacional (± resultado financeiro) = LAIR (− IR/CSLL) = Lucro Líquido.",
        "Contabilidade/Custos", ["dre"]
    ),
    _q(
        "O Método de Custeio por Absorção, aceito pela legislação fiscal brasileira, consiste em:",
        ["Apropriar todos os custos (fixos e variáveis) aos produtos, enquanto as despesas são lançadas diretamente no resultado do período.",
         "Apropriar apenas os custos variáveis aos produtos, tratando os custos fixos como despesas do período.",
         "Ratear todos os gastos (custos e despesas) aos produtos fabricados.",
         "Ignorar os custos indiretos de fabricação na apuração do custo do produto.",
         "Apropriar apenas a matéria-prima como custo do produto."],
        0,
        "Custeio por absorção: todos os custos de produção (diretos/indiretos, fixos/variáveis) são apropriados aos produtos. Despesas comerciais, administrativas e financeiras vão diretamente ao resultado.",
        "Contabilidade/Custos", ["custos"]
    ),
    _q(
        "O Ponto de Equilíbrio Contábil (PEC) é atingido quando:",
        ["A receita total se iguala à soma dos custos e despesas totais (fixos e variáveis), resultando em lucro zero.",
         "O lucro líquido iguala o patrimônio líquido da empresa.",
         "A margem de contribuição total se iguala ao capital social.",
         "O fluxo de caixa operacional se iguala ao investimento inicial.",
         "O ativo circulante se iguala ao passivo circulante."],
        0,
        "PEC = Custos Fixos Totais / Margem de Contribuição Unitária. Neste volume, a receita total cobre todos os gastos, gerando lucro contábil zero.",
        "Contabilidade/Custos", ["custos"]
    ),
    _q(
        "Na análise de balanço patrimonial, o Índice de Liquidez Corrente é calculado como:",
        ["Ativo Circulante / Passivo Circulante, medindo a capacidade de pagamento de curto prazo.",
         "Ativo Total / Passivo Total.",
         "Ativo Circulante / Passivo Total.",
         "Ativo Não Circulante / Passivo Circulante.",
         "Caixa e Equivalentes / Passivo Circulante."],
        0,
        "ILC = AC/PC. Indica quanto a empresa possui de ativos de curto prazo para cada R$ 1,00 de dívidas de curto prazo.",
        "Contabilidade/Custos", ["balanco"]
    ),
    _q(
        "A Margem de Contribuição Unitária (MCu) é calculada como:",
        ["Preço de venda − Custos e despesas variáveis unitários.",
         "Preço de venda − Custo fixo unitário.",
         "Receita total / Quantidade vendida.",
         "Custo total / Quantidade produzida.",
         "Lucro líquido / Quantidade vendida."],
        0,
        "MCu = PV − (CVu + DVu). Representa o valor que cada unidade vendida contribui para cobrir custos fixos e gerar lucro (análise CVL).",
        "Contabilidade/Custos", ["custos"]
    ),
    _q(
        "O regime de tributação do Lucro Real, utilizado pela Petrobras, caracteriza-se por:",
        ["Tributar IRPJ e CSLL com base no lucro contábil ajustado (adições e exclusões fiscais), apurado ao final de cada período.",
         "Tributar com base em percentual fixo da receita bruta (presunção).",
         "Isentar a empresa de pagar CSLL.",
         "Pagar imposto apenas sobre o faturamento mensal.",
         "Substituir o PIS e COFINS por um tributo único."],
        0,
        "Lucro Real: IRPJ (15% + adicional 10% sobre lucro > R$ 240.000/ano) e CSLL (9%) sobre o lucro contábil ajustado (RIR/2018).",
        "Contabilidade/Custos", ["tributacao"]
    ),
    _q(
        "Na classificação dos custos industriais, os Custos Indiretos de Fabricação (CIF) incluem:",
        ["Matéria-prima e mão de obra direta aplicados no produto.",
         "Materiais auxiliares, mão de obra indireta, depreciação de máquinas, energia elétrica da fábrica e manutenção industrial.",
         "Apenas os salários dos diretores da empresa.",
         "Comissões de vendedores e frete de entregas.",
         "Despesas bancárias e juros de financiamentos."],
        1,
        "CIF são os gastos fabris não identificáveis diretamente ao produto: lubrificantes, supervisão fabril, depreciação, aluguel da fábrica, energia elétrica industrial.",
        "Contabilidade/Custos", ["custos"]
    ),
    _q(
        "O ciclo operacional de uma empresa industrial compreende o período entre:",
        ["A compra da matéria-prima e o recebimento da venda do produto acabado.",
         "O início da produção e o fim do exercício fiscal.",
         "A assinatura do contrato social e a emissão da primeira nota fiscal.",
         "A contratação de funcionários e a primeira produção.",
         "O pagamento de dividendos e a recompra de ações."],
        0,
        "Ciclo operacional = PME + PMF + PMV + PMR. Tempo entre aquisição de insumos e recebimento das vendas.",
        "Contabilidade/Custos", ["custos"]
    ),
    _q(
        "No Balanço Patrimonial, o Ativo Não Circulante é composto por:",
        ["Disponibilidades, contas a receber, estoques e despesas antecipadas.",
         "Realizável a Longo Prazo, Investimentos, Imobilizado e Intangível.",
         "Fornecedores, salários a pagar e impostos a recolher.",
         "Capital Social, Reservas de Lucro e Ações em Tesouraria.",
         "Financiamentos de curto prazo, dividendos a pagar e provisões."],
        1,
        "Lei 6.404/1976: ANC = Realizável a LP + Investimentos + Imobilizado + Intangível. AC inclui caixa, contas a receber, estoques.",
        "Contabilidade/Custos", ["balanco"]
    ),
    _q(
        "O método de depreciação linear para um ativo de R$ 100.000,00, vida útil de 10 anos e valor residual de R$ 10.000,00 resulta em depreciação anual de:",
        ["R$ 9.000,00.",
         "R$ 10.000,00.",
         "R$ 5.000,00.",
         "R$ 15.000,00.",
         "R$ 12.000,00."],
        0,
        "Depreciação linear = (Custo − Valor Residual) / Vida Útil = (100.000 − 10.000) / 10 = R$ 9.000,00/ano.",
        "Contabilidade/Custos", ["custos"]
    ),
    _q(
        "A COFINS no regime não cumulativo tem alíquota de:",
        ["3,0% sobre o faturamento.",
         "7,6% sobre a receita bruta, com direito a créditos sobre insumos, energia elétrica, aluguéis e depreciação.",
         "9,25% sobre a receita líquida.",
         "4,0% sobre o lucro operacional.",
         "1,65% sobre o valor agregado."],
        1,
        "Lei 10.833/2003: COFINS não cumulativa = 7,6% (créditos sobre insumos). PIS não cumulativo = 1,65%. Regime cumulativo: COFINS 3% e PIS 0,65%.",
        "Contabilidade/Custos", ["tributacao"]
    ),
    _q(
        "No custeio baseado em atividades (ABC), os custos indiretos são alocados por:",
        ["Rateio proporcional à mão de obra direta de cada produto.",
         "Direcionadores de custos (cost drivers) que refletem como cada atividade consome recursos e como cada produto consome atividades.",
         "Divisão igualitária dos CIF entre todos os produtos.",
         "Apropriação exclusiva com base no volume de produção.",
         "Percentual fixo definido pela contabilidade fiscal."],
        1,
        "ABC: identifica atividades, atribui custos por direcionadores de recursos, depois aos produtos por direcionadores de atividades. Reduz distorções no rateio de CIF.",
        "Contabilidade/Custos", ["custos"]
    ),
    _q(
        "O EBITDA (Earnings Before Interest, Taxes, Depreciation and Amortization) representa:",
        ["O lucro líquido do período após dedução de juros e impostos.",
         "O lucro operacional antes dos juros, impostos, depreciação e amortização, indicando a geração operacional de caixa aproximada.",
         "O fluxo de caixa livre disponível para os acionistas.",
         "A receita bruta menos todos os custos e despesas, incluindo investimentos.",
         "O lucro após imposto de renda e contribuição social."],
        1,
        "EBITDA = LAJIR + Depreciação + Amortização. Mede a geração de caixa operacional, desconsiderando efeitos financeiros, fiscais e contábeis.",
        "Contabilidade/Custos", ["ebitda"]
    ),
    _q(
        "A CIDE (Contribuição de Intervenção no Domínio Econômico) sobre combustíveis incide sobre:",
        ["A importação e comercialização de gasolina, diesel, querosene de aviação, óleos combustíveis e GLP, com alíquotas por unidade de medida.",
         "Apenas a gasolina vendida em postos.",
         "O faturamento das distribuidoras de combustíveis.",
         "O lucro da Petrobras na exploração de petróleo.",
         "A exportação de petróleo bruto e derivados."],
        0,
        "Lei 10.336/2001: CIDE-combustíveis com alíquotas específicas (R$/unidade). Parte da arrecadação destina-se a subsídios ao transporte.",
        "Contabilidade/Custos", ["cide"]
    ),
    # ── Administração (15) ──
    #
    _q(
        "No processo administrativo, a função Planejamento consiste em:",
        ["Coordenar a execução das atividades operacionais do dia a dia.",
         "Definir objetivos, metas e estratégias, estabelecendo os meios para alcançá-los.",
         "Alocar recursos humanos e materiais para a execução das tarefas.",
         "Monitorar resultados e corrigir desvios em relação ao planejado.",
         "Liderar equipes e motivar colaboradores."],
        1,
        "Planejamento (1ª função adm.): define onde se quer chegar e como. Desdobra-se em estratégico (LP), tático (MP) e operacional (CP).",
        "Administração", ["planejamento"]
    ),
    _q(
        "O organograma de uma organização representa graficamente:",
        ["O fluxo de processos e atividades produtivas.",
         "A estrutura hierárquica, relações de autoridade, responsabilidade e unidades organizacionais.",
         "O cronograma de execução de projetos e prazos.",
         "A distribuição geográfica das unidades da empresa.",
         "O orçamento anual e alocação de recursos financeiros."],
        1,
        "Organograma: representação gráfica da estrutura formal, mostrando hierarquia, departamentalização, níveis hierárquicos e linhas de autoridade.",
        "Administração", ["organograma"]
    ),
    _q(
        "A Teoria da Burocracia, sistematizada por Max Weber, caracteriza-se por:",
        ["Informalidade, ausência de regras e flexibilidade total.",
         "Hierarquia definida, divisão do trabalho, regras formais, impessoalidade e meritocracia.",
         "Gestão participativa com autogestão dos trabalhadores.",
         "Foco exclusivo na satisfação dos funcionários.",
         "Decisões baseadas na intuição dos gestores, sem normas escritas."],
        1,
        "Weber: burocracia = autoridade racional-legal, normas formais, impessoalidade, hierarquia, competência técnica, separação propriedade/administração.",
        "Administração", ["teorias"]
    ),
    _q(
        "Na função Direção, o estilo de liderança democrático caracteriza-se por:",
        ["O líder toma decisões unilateralmente e determina tarefas.",
         "O líder consulta a equipe, estimula participação e delega responsabilidades.",
         "O líder se abstém de intervir, deixando o grupo livre.",
         "O líder usa exclusivamente recompensas financeiras.",
         "O líder centraliza decisões e comunica ordens verticalmente."],
        1,
        "Liderança democrática (Lewin): líder orienta e estimula participação. Autocrático: centraliza. Laissez-faire: liberdade total ao grupo.",
        "Administração", ["direcao"]
    ),
    _q(
        "O controle administrativo consiste em:",
        ["Estabelecer padrões, medir resultados, comparar com padrões e tomar ações corretivas.",
         "Apenas punir funcionários que não atingem metas.",
         "Eliminar completamente erros operacionais sem padrões.",
         "Definir a missão e visão da empresa.",
         "Contratar e demitir conforme necessidade da produção."],
        0,
        "Controle (Chiavenato): 1) padrões, 2) medir, 3) comparar, 4) corrigir desvios. Pode ser estratégico, tático ou operacional.",
        "Administração", ["controle"]
    ),
    _q(
        "A Abordagem Contingencial sustenta que:",
        ["Existe uma única forma correta de administrar.",
         "A estrutura e práticas gerenciais dependem das circunstâncias (ambiente, tecnologia, tamanho, estratégia).",
         "A administração deve focar exclusivamente na eficiência interna.",
         "Todas as organizações devem ser burocracias.",
         "O comportamento humano é o único fator do sucesso organizacional."],
        1,
        "Teoria da Contingência (Burns & Stalker, Lawrence & Lorsch): não há one best way. A estrutura depende das contingências ambientais e tecnológicas.",
        "Administração", ["teorias"]
    ),
    _q(
        "Na Administração da Produção, o Just-in-Time (JIT) tem como princípio fundamental:",
        ["Produzir grandes lotes para economias de escala.",
         "Produzir somente o necessário, no momento e quantidade necessários, eliminando desperdícios.",
         "Manter estoques elevados de segurança.",
         "Centralizar a produção em uma única planta global.",
         "Terceirizar toda a produção para países de mão de obra barata."],
        1,
        "JIT (Toyota Production System): estoque mínimo, fluxo contínuo, kanban, setup rápido, qualidade na fonte (jidoka), kaizen. Elimina desperdícios (muda).",
        "Administração", ["producao"]
    ),
    _q(
        "O Balanced Scorecard (BSC) avalia o desempenho organizacional sob:",
        ["Perspectivas Financeira, Clientes, Processos Internos e Aprendizado/Crescimento.",
         "Produção, Marketing, Finanças e RH.",
         "Estratégica, Tática, Operacional e Contábil.",
         "Qualidade, Produtividade, Custos e Satisfação.",
         "Ambiental, Social, Econômica e Governança."],
        0,
        "BSC (Kaplan & Norton, 1992): converte estratégia em indicadores nas 4 perspectivas, alinhando objetivos de curto e longo prazo.",
        "Administração", ["bsc"]
    ),
    _q(
        "O Desenvolvimento Organizacional (DO) é uma abordagem de mudança planejada baseada em:",
        ["Intervenções comportamentais e estruturais focadas em cultura, clima e relações interpessoais.",
         "Implementação forçada de novas tecnologias sem preparação.",
         "Reengenharia radical com demissões em massa.",
         "Aquisição de empresas para crescimento vertical.",
         "Redução de custos exclusivamente por cortes de pessoal."],
        0,
        "DO (French & Bell, Schein): mudança planejada focada em cultura e processos humanos. Técnicas: feedback de dados, team building, consultoria de processos.",
        "Administração", ["do"]
    ),
    _q(
        "Na departamentalização funcional, os departamentos são agrupados por:",
        ["Funções organizacionais: produção, marketing, finanças, RH, buscando especialização.",
         "Produtos ou serviços distintos oferecidos ao mercado.",
         "Regiões geográficas onde a empresa atua.",
         "Tipos de clientes atendidos.",
         "Processos específicos da cadeia produtiva."],
        0,
        "Departamentalização funcional: agrupa atividades similares por função. Vantagens: especialização. Desvantagens: comunicação horizontal limitada.",
        "Administração", ["departamentalizacao"]
    ),
    _q(
        "A Teoria das Relações Humanas (Elton Mayo) enfatiza:",
        ["A importância da estrutura formal e regras burocráticas.",
         "O impacto dos fatores sociais e psicológicos, o grupo informal e a liderança.",
         "A maximização do lucro como único objetivo empresarial.",
         "A mecanização total para eliminar a subjetividade humana.",
         "O pagamento por produção como único fator de motivação."],
        1,
        "Experiência de Hawthorne (Mayo): fatores sociais e relacionamentos informais afetam mais a produtividade que condições físicas ou incentivos financeiros.",
        "Administração", ["teorias"]
    ),
    _q(
        "Decisões programadas na administração:",
        ["Usam regras pré-definidas para situações repetitivas, como reposição de estoque.",
         "Usam intuição e criatividade para situações complexas e inovadoras.",
         "Exigem modelos matemáticos sofisticados.",
         "Utilizam votação democrática de todos os funcionários.",
         "Delegam todas as decisões aos níveis operacionais."],
        0,
        "Decisões programadas (Simon): repetitivas, rotineiras, com regras claras. Ex: pedido de compra, aprovação de férias.",
        "Administração", ["tomada-decisao"]
    ),
    _q(
        "Empowerment na gestão contemporânea significa:",
        ["Centralizar decisões na alta direção para maior controle.",
         "Delegar poder, autoridade e autonomia aos colaboradores, responsabilizando-os por resultados.",
         "Reduzir o quadro de funcionários para cortar custos.",
         "Implementar sistemas de vigilância eletrônica.",
         "Aumentar níveis hierárquicos para melhorar supervisão."],
        1,
        "Empowerment: transferência de poder de decisão aos níveis mais próximos da ação, com autonomia, recursos e informações.",
        "Administração", ["gestao"]
    ),
    _q(
        "A Análise SWOT (FOFA) analisa:",
        ["Forças e Fraquezas internas, Oportunidades e Ameaças externas.",
         "Apenas os concorrentes diretos da empresa.",
         "Exclusivamente fraquezas internas.",
         "Somente oportunidades e ameaças do macroambiente.",
         "A estrutura de capital e fluxo de caixa."],
        0,
        "SWOT: diagnóstico estratégico que cruza variáveis internas (forças/fraquezas) com externas (oportunidades/ameaças).",
        "Administração", ["swot"]
    ),
    _q(
        "Os princípios da Administração Científica de Taylor incluem:",
        ["Estudo de tempos e movimentos, padronização, seleção científica e divisão gerência/operário.",
         "Autogestão, cooperação voluntária e ausência de hierarquia.",
         "Foco exclusivo na satisfação emocional dos trabalhadores.",
         "Participação dos funcionários nas decisões estratégicas.",
         "Eliminação total da supervisão e controle hierárquico."],
        0,
        "Taylor (1911): observação científica, seleção e treinamento, cooperação gerência/trabalhadores, divisão de responsabilidades.",
        "Administração", ["teorias"]
    ),
    # ── Direito Constitucional (15) ──
    #
    _q(
        "O controle de constitucionalidade difuso caracteriza-se por:",
        ["Ser realizado exclusivamente pelo STF.",
         "Permitir que qualquer juiz ou tribunal, no caso concreto, declare a inconstitucionalidade com efeitos inter partes.",
         "Ser um controle abstrato sem caso concreto.",
         "Ter sempre efeito vinculante e erga omnes.",
         "Ser exercido apenas pelo Poder Legislativo."],
        1,
        "Controle difuso: qualquer juiz pode deixar de aplicar lei inconstitucional no caso concreto. O STF julga RE e o Senado pode suspender a lei (Art. 52, X).",
        "Direito Constitucional", ["controle-constitucionalidade"]
    ),
    _q(
        "A Ação Direta de Inconstitucionalidade (ADI) por omissão é cabível quando:",
        ["Uma lei é contrária à Constituição Federal.",
         "Houver omissão do Poder Público em tornar efetiva norma constitucional, dando ciência ao poder competente.",
         "Um particular tiver direito fundamental violado.",
         "O governo federal deixar de pagar precatórios.",
         "Houver conflito de competência União/Estados."],
        1,
        "ADI por omissão (Art. 103, §2º CF e Lei 9.868/1999): o STF dá ciência ao poder omisso para adotar as providências necessárias.",
        "Direito Constitucional", ["adi"]
    ),
    _q(
        "A Ação Declaratória de Constitucionalidade (ADC) tem como objetivo:",
        ["Declarar a inconstitucionalidade de lei federal.",
         "Preservar a presunção de constitucionalidade de lei/ato normativo federal, com efeito vinculante e erga omnes, quando houver controvérsia judicial relevante.",
         "Impugnar ato concreto que viola direito líquido e certo.",
         "Questionar omissão do Legislativo.",
         "Suspender liminarmente lei estadual."],
        1,
        "ADC (Art. 102, I, 'a' e Lei 9.868/1999): busca afirmar a constitucionalidade diante de controvérsia judicial. Eficácia erga omnes e vinculante.",
        "Direito Constitucional", ["adc"]
    ),
    _q(
        "A Arguição de Descumprimento de Preceito Fundamental (ADPF) é cabível quando:",
        ["Houver lei municipal contrária à CF.",
         "Ato do poder público violar preceito fundamental e não houver outro meio processual eficaz, sendo subsidiária.",
         "Um particular impugnar ato administrativo federal.",
         "O governo estadual questionar lei federal.",
         "Houver conflito entre dois Estados."],
        1,
        "ADPF (Lei 9.882/1999): instrumento subsidiário para lesão a preceito fundamental quando não houver ADI/ADC cabível.",
        "Direito Constitucional", ["adpf"]
    ),
    _q(
        "Compete ao Supremo Tribunal Federal (STF), precipuamente:",
        ["A guarda da CF: julgar ADI, ADC, ADPF e recursos extraordinários.",
         "Julgar causas entre Estados estrangeiros e a União.",
         "Apreciar todos os recursos cíveis e criminais do país.",
         "Executar decisões do TCU.",
         "Processar e julgar governadores por crimes comuns."],
        0,
        "Art. 102 CF: STF é guardião da CF. Competências: ADI, ADC, ADPF, RE, conflitos federativos, extradição, crimes de Presidente e Ministros.",
        "Direito Constitucional", ["stf"]
    ),
    _q(
        "São competências privativas da União (Art. 22 CF):",
        ["Legislar sobre direito civil, penal, processual, eleitoral, agrário, marítimo, aeronáutico e do trabalho.",
         "Legislar sobre educação, saúde e assistência social.",
         "Legislar sobre transporte intermunicipal.",
         "Legislar sobre proteção ao meio ambiente.",
         "Legislar sobre florestas, caça, pesca e fauna."],
        0,
        "Art. 22 CF: 29 matérias de competência privativa da União, incluindo todos os ramos do direito, telecomunicações, energia, comércio exterior e defesa.",
        "Direito Constitucional", ["competencias"]
    ),
    _q(
        "A competência comum (Art. 23 CF) inclui:",
        ["Cuidar da saúde, proteger o meio ambiente, fomentar produção agropecuária e promover habitação.",
         "Legislar sobre direito penal.",
         "Explorar serviços de telecomunicações.",
         "Autorizar produção de material bélico.",
         "Organizar o sistema nacional de emprego."],
        0,
        "Art. 23 CF: competência administrativa comum (União, Estados, DF, Municípios) para saúde, meio ambiente, educação, habitação, combate à pobreza.",
        "Direito Constitucional", ["competencias"]
    ),
    _q(
        "A cláusula pétrea (Art. 60, §4º CF) impede emenda tendente a abolir:",
        ["Forma federativa, voto direto/universal/periódico, separação dos Poderes e direitos e garantias individuais.",
         "Qualquer dispositivo do ADCT.",
         "O direito de greve dos servidores.",
         "A competência do STF para ADI.",
         "As imunidades tributárias recíprocas."],
        0,
        "Art. 60, §4º CF: limite material ao poder reformador. Não pode ser objeto de deliberação proposta de emenda tendente a abolir essas cláusulas pétreas.",
        "Direito Constitucional", ["clausulas-petreas"]
    ),
    _q(
        "O controle concentrado de constitucionalidade estadual é exercido pelo:",
        ["STF, em qualquer caso.",
         "TJ do respectivo Estado, por Representação de Inconstitucionalidade de leis estaduais/municipais em face da Constituição Estadual.",
         "STJ, exclusivamente.",
         "TRF da respectiva região.",
         "Governador do Estado, mediante veto jurídico."],
        1,
        "Art. 125, §2º CF: TJS julgam Representação de Inconstitucionalidade de leis/atos estaduais e municipais em face da CE (simetria ao modelo federal).",
        "Direito Constitucional", ["controle-constitucionalidade"]
    ),
    _q(
        "Os efeitos da declaração de inconstitucionalidade em ADI, em regra, são:",
        ["Ex nunc, desde o trânsito em julgado, podendo modular.",
         "Ex tunc (retroativos), erga omnes e vinculante, podendo o STF modular por 2/3 dos votos.",
         "Inter partes, afetando apenas as partes do processo.",
         "Apenas suspensivos, dependendo do Senado.",
         "Irretroativos, sem eficácia vinculante."],
        1,
        "Lei 9.868/1999, Art. 27: em regra nulidade ex tunc, mas o STF pode modular efeitos (ex nunc) por 2/3 dos votos, por segurança jurídica.",
        "Direito Constitucional", ["adi"]
    ),
    _q(
        "O Art. 37 da CF/88 estabelece os princípios da administração pública:",
        ["Legalidade, impessoalidade, moralidade, publicidade e eficiência.",
         "Igualdade, liberdade, fraternidade e justiça social.",
         "Hierarquia, disciplina, unidade e coordenação.",
         "Centralização, descentralização, concentração.",
         "Supremacia, continuidade, autotutela e motivação."],
        0,
        "Art. 37, caput CF: legalidade, impessoalidade, moralidade, publicidade e eficiência (LIMPSE, incluído pela EC 19/1998).",
        "Direito Constitucional", ["administracao-publica"]
    ),
    _q(
        "O mandado de segurança coletivo pode ser impetrado por:",
        ["Qualquer cidadão no gozo de direitos políticos.",
         "Partido político com representação no CN, sindicato, entidade de classe ou associação constituída há pelo menos 1 ano.",
         "Apenas pelo Ministério Público Federal.",
         "Qualquer empresa privada com CNPJ ativo.",
         "Exclusivamente por pessoa física maior de 18 anos."],
        1,
        "Lei 12.016/2009, Art. 21: MS coletivo em defesa de membros/associados.",
        "Direito Constitucional", ["mandado-seguranca"]
    ),
    _q(
        "Segundo a CF/88, o Ministério Público é instituição permanente, incumbindo-lhe:",
        ["A defesa da ordem jurídica, regime democrático e interesses sociais e individuais indisponíveis.",
         "A representação judicial da União, Estados e Municípios.",
         "A consultoria jurídica do Executivo.",
         "O julgamento de causas cíveis de pequeno valor.",
         "A execução da política de segurança pública."],
        0,
        "Art. 127 CF: MP autônomo. Art. 129: funções como ação penal pública, inquérito civil, ação civil pública, defesa do patrimônio público e meio ambiente.",
        "Direito Constitucional", ["mp"]
    ),
    _q(
        "As contribuições sociais de intervenção no domínio econômico (Art. 149 CF) são instituídas por:",
        ["Aprovação por lei complementar.",
         "Lei ordinária específica, competência exclusiva da União.",
         "Autorização prévia do Senado.",
         "Aprovação por maioria absoluta do CN em sessão conjunta.",
         "Decreto do Presidente sem participação do Legislativo."],
        1,
        "Art. 149 CF: compete exclusivamente à União instituir contribuições sociais, de intervenção e de interesse das categorias, por lei ordinária.",
        "Direito Constitucional", ["tributacao"]
    ),
    _q(
        "O Art. 5º, XI da CF estabelece que a casa é asilo inviolável, salvo:",
        ["Flagrante delito, desastre, socorro ou, durante o dia, por determinação judicial.",
         "Qualquer suspeita de crime a qualquer hora.",
         "Ordem verbal do delegado durante a noite.",
         "Suspeita de sonegação fiscal pela Receita Federal.",
         "Vistoria de bombeiros sem mandado a qualquer hora."],
        0,
        "Art. 5º, XI CF: exceções à inviolabilidade do domicílio: flagrante, desastre, socorro (qualquer hora) ou determinação judicial (somente durante o dia).",
        "Direito Constitucional", ["direitos-fundamentais"]
    ),
    # ── Direito Tributário (10) ──
    #
    _q(
        "O Imposto sobre a Renda (IR) é um tributo federal que incide sobre:",
        ["O patrimônio das pessoas jurídicas exclusivamente.",
         "Renda e proventos de qualquer natureza, com generalidade, universalidade e progressividade.",
         "Apenas salários de pessoas físicas.",
         "Circulação de mercadorias e serviços.",
         "Propriedade territorial rural."],
        1,
        "Art. 153, III CF: IRPJ/IRPF. Princípios: generalidade, universalidade, progressividade. Regulado pelo RIR/2018 (Decreto 9.580/2018).",
        "Direito Tributário", ["ir"]
    ),
    _q(
        "O IOF é um tributo federal com função predominantemente:",
        ["Arrecadatória, com alíquotas fixas.",
         "Extra fiscal, como instrumento de política monetária e cambial, com alíquotas alteráveis por decreto.",
         "Finalística para financiamento da seguridade social.",
         "Distributiva de renda entre entes federativos.",
         "Compensatória de desequilíbrios regionais."],
        1,
        "Art. 153, V CF: IOF (crédito, câmbio, seguro, títulos). Função extrafiscal: Presidente altera alíquotas por decreto (Art. 153, §1º).",
        "Direito Tributário", ["iof"]
    ),
    _q(
        "Os royalties da exploração de petróleo são devidos com base:",
        ["No volume de produção mensal de petróleo e gás, com alíquotas diferenciadas por regime (concessão/partilha) e localização.",
         "No lucro líquido da empresa concessionária.",
         "No valor de mercado das ações da Petrobras.",
         "Na receita bruta da refinaria.",
         "No número de empregados da empresa petrolífera."],
        0,
        "Lei 9.478/1997 Art. 45-48: royalties = 10% da receita bruta (alíquota básica), distribuídos a Estados, Municípios, União e Comando da Marinha.",
        "Direito Tributário", ["royalties"]
    ),
    _q(
        "O ICMS é de competência:",
        ["Da União, com alíquotas uniformes em todo o país.",
         "Dos Estados e DF: circulação de mercadorias, transporte interestadual/intermunicipal e comunicação.",
         "Dos Municípios, para serviços.",
         "Exclusiva do DF.",
         "Compartilhada União/Estados com alíquotas do Senado."],
        1,
        "Art. 155, II CF: ICMS estadual. Não cumulativo, seletivo. Alíquotas internas por Estado; interestaduais pelo Senado (Res. 22/1989).",
        "Direito Tributário", ["icms"]
    ),
    _q(
        "O ISS é de competência dos Municípios e DF, e sua base de cálculo é:",
        ["O valor do serviço prestado, conforme lista anexa à LC 116/2003.",
         "O valor do serviço acrescido do ICMS.",
         "O faturamento anual da empresa.",
         "O lucro operacional da atividade.",
         "O patrimônio líquido da empresa."],
        0,
        "LC 116/2003: ISS sobre preço do serviço, alíquotas 2% a 5%, conforme lista de serviços anexa.",
        "Direito Tributário", ["iss"]
    ),
    _q(
        "A CIDE exige vinculação do produto da arrecadação:",
        ["À finalidade que a justificou: infraestrutura rodoviária, subsídios ao transporte e projetos ambientais.",
         "Repartição integral com Estados e Municípios.",
         "Alíquotas definidas pelo Congresso com vigência imediata.",
         "Aprovação do CNPE.",
         "Autorização do Banco Central."],
        0,
        "Art. 149 CF e Lei 10.336/2001: CIDE-combustíveis vinculada a infraestrutura de transportes, subsídios e projetos ambientais.",
        "Direito Tributário", ["cide"]
    ),
    _q(
        "A CSLL tem alíquota geral de:",
        ["9% sobre o lucro líquido do período-base, antes da provisão para IR.",
         "15% sobre o lucro operacional.",
         "25% sobre a receita bruta.",
         "10% sobre o faturamento mensal.",
         "4% sobre o patrimônio líquido ajustado."],
        0,
        "Lei 7.689/1988: CSLL 9% (geral). Instituições financeiras: 15% (20% desde 2022). Base = LAIR ajustado.",
        "Direito Tributário", ["csll"]
    ),
    _q(
        "O IPI segue os princípios da:",
        ["Seletividade (alíquotas conforme essencialidade) e não cumulatividade (compensação do imposto pago nas etapas anteriores).",
         "Progressividade e cumulatividade.",
         "Generalidade e uniformidade.",
         "Regressividade e neutralidade fiscal.",
         "Simplicidade e alíquota única."],
        0,
        "Art. 153, IV CF e CTN: IPI é seletivo e não cumulativo. Incide sobre produtos industrializados nacionais e importados.",
        "Direito Tributário", ["ipi"]
    ),
    _q(
        "O ITR pode ser fiscalizado e arrecadado pelos Municípios mediante convênio, desde que:",
        ["O Município assuma integralmente a administração do imposto em seu território, ficando com 100% da arrecadação.",
         "A União perca competência para alterar alíquotas.",
         "O Município renuncie ao produto da arrecadação.",
         "O convênio seja aprovado por lei complementar.",
         "O ITR seja substituído pelo IPTU."],
        0,
        "Art. 153, §4º CF e Lei 11.250/2005: delegação da fiscalização/arrecadação do ITR aos Municípios, que ficam com 100%.",
        "Direito Tributário", ["itr"]
    ),
    _q(
        "O princípio da anterioridade nonagesimal (noventena) estabelece que:",
        ["A lei que institui ou aumenta tributo só produz efeitos após 90 dias da publicação.",
         "O tributo só pode ser cobrado no exercício seguinte.",
         "A lei tributária retroage em benefício do contribuinte.",
         "O tributo deve ser cobrado pelo valor venal do imóvel.",
         "As alíquotas do IPI podem ser alteradas sem prazo mínimo."],
        0,
        "Art. 150, III, 'c' CF: vedado cobrar tributo antes de 90 dias da lei que o instituiu ou aumentou. Exceções: IR, IOF, II, IE.",
        "Direito Tributário", ["principios"]
    ),
    # ── Matemática (+12) ──
    #
    _q(
        "O valor de x na equação 2^(x+1) = 32 é:",
        ["3.", "4.", "5.", "6.", "7."],
        1,
        "2^(x+1) = 32 → 2^(x+1) = 2^5 → x+1 = 5 → x = 4.",
        "Matemática", ["exponencial"]
    ),
    _q(
        "Em uma PA, o 1º termo é 10 e o 6º termo é 30. A razão é:",
        ["2.", "3.", "4.", "5.", "6."],
        2,
        "a₆ = a₁ + 5r → 30 = 10 + 5r → r = 4.",
        "Matemática", ["pa"]
    ),
    _q(
        "O valor de (2³ × 2⁴) / 2⁵ é:",
        ["2.", "4.", "8.", "16.", "32."],
        1,
        "2³ × 2⁴ / 2⁵ = 2^(3+4-5) = 2² = 4.",
        "Matemática", ["potencia"]
    ),
    _q(
        "A área de um círculo de raio 5 cm (π = 3,14) é:",
        ["15,70 cm².", "31,40 cm².", "78,50 cm².", "157,00 cm².", "314,00 cm²."],
        2,
        "A = π·r² = 3,14 × 25 = 78,50 cm².",
        "Matemática", ["geometria"]
    ),
    _q(
        "A média aritmética de 8, 12, 15, 20 e 25 é:",
        ["14.", "15.", "16.", "17.", "18."],
        2,
        "Média = (8+12+15+20+25)/5 = 80/5 = 16.",
        "Matemática", ["estatistica"]
    ),
    _q(
        "Em uma PG, o 1º termo é 3 e a razão é 2. O 4º termo vale:",
        ["12.", "18.", "24.", "30.", "48."],
        2,
        "a₄ = a₁ × q³ = 3 × 2³ = 24.",
        "Matemática", ["pg"]
    ),
    _q(
        "A soma dos ângulos internos de um pentágono regular é:",
        ["360°.", "480°.", "540°.", "600°.", "720°."],
        2,
        "S = (n−2)×180° = (5−2)×180° = 540°.",
        "Matemática", ["geometria"]
    ),
    _q(
        "O valor de log₁₀ 1000 + log₁₀ 0,01 é:",
        ["0.", "1.", "2.", "3.", "4."],
        1,
        "log₁₀ 1000 = 3; log₁₀ 0,01 = −2; 3 + (−2) = 1.",
        "Matemática", ["logaritmo"]
    ),
    _q(
        "A função f(x) = x² − 4x + 3 tem vértice em:",
        ["(2, −1).", "(−2, 15).", "(4, 3).", "(1, 0).", "(3, 0)."],
        0,
        "xᵥ = −b/2a = 2; yᵥ = f(2) = 4 − 8 + 3 = −1.",
        "Matemática", ["funcao"]
    ),
    _q(
        "Quantos metros de arame são necessários para cercar terreno 30m × 20m com 4 voltas?",
        ["200 m.", "300 m.", "400 m.", "500 m.", "600 m."],
        2,
        "Perímetro = 2×(30+20) = 100 m. 4 voltas = 400 m.",
        "Matemática", ["geometria"]
    ),
    _q(
        "0,222... + 0,333... na forma fracionária é:",
        ["1/2.", "3/5.", "5/9.", "2/3.", "7/9."],
        2,
        "2/9 + 3/9 = 5/9.",
        "Matemática", ["fracao"]
    ),
    _q(
        "Um investimento de R$ 5.000,00 a juros simples de 1,5% a.m. por 6 meses gera montante de:",
        ["R$ 5.300,00.", "R$ 5.450,00.", "R$ 5.500,00.", "R$ 5.600,00.", "R$ 5.750,00."],
        1,
        "J = 5000×0,015×6 = R$ 450,00. M = 5000+450 = R$ 5.450,00.",
        "Matemática", ["juros"]
    ),
    # ── Métricas (+11) ──
    #
    _q(
        "O Índice de Aproveitamento (IA) mede:",
        ["Horas líquidas de estudo por dia.",
         "Percentual de acertos nas questões respondidas.",
         "Número de matérias estudadas por semana.",
         "Velocidade de leitura em páginas/hora.",
         "Quantidade de revisões no mês."],
        1,
        "IA = (acertos / total de questões) × 100. Indica compreensão do conteúdo naquele momento.",
        "Métricas", ["ia"]
    ),
    _q(
        "O Tempo Líquido de Estudo (TLE) é:",
        ["Tempo total registrado no cronômetro.",
         "Tempo de foco subtraindo distrações e pausas não programadas.",
         "Soma do tempo de estudo de todas as disciplinas no mês.",
         "Tempo gasto apenas com videoaulas.",
         "Tempo dedicado ao lazer entre sessões."],
        1,
        "TLE = tempo total − distrações. Correlacionado com maior retenção e eficiência.",
        "Métricas", ["tle"]
    ),
    _q(
        "Segundo a curva de Ebbinghaus, o padrão ideal de revisão é:",
        ["Apenas na véspera da prova.",
         "Intervalos crescentes: 1 dia, 1 semana, 1 mês, 3 meses.",
         "Revisão diária do mesmo conteúdo até a exaustão.",
         "Uma única revisão intensiva 24h após o estudo.",
         "Revisão semanal com intervalo fixo para todo conteúdo."],
        1,
        "Curva do esquecimento: perda ~50% em 1h. Spaced repetition com intervalos crescentes consolida a memória de longo prazo.",
        "Métricas", ["revisao"]
    ),
    _q(
        "A Carga Semanal de Treino (CST) recomendada para um candidato com 4h/dia é:",
        ["10-15 questões/dia.",
         "20-30 questões/dia, ajustando conforme tempo e IC.",
         "50-60 questões/dia independentemente do tempo.",
         "5-10 questões/dia.",
         "100+ questões só nos fins de semana."],
        1,
        "CST calculada com base no tempo disponível e IC, buscando volume progressivo. 20-30 questões/dia é factível para 3-4h diárias.",
        "Métricas", ["cst"]
    ),
    _q(
        "A Matriz de Prioridades de Estudo (MPE) cruza:",
        ["Dificuldade e Importância do tópico para o concurso.",
         "Quantidade de questões e tempo médio de resposta.",
         "Tempo gasto e nota no último simulado.",
         "Número de acertos e erros acumulados.",
         "Preferência pessoal e disponibilidade do professor."],
        0,
        "MPE: tópicos difíceis e importantes (prioridade máxima) merecem mais tempo; fáceis e pouco importantes podem ser revistos superficialmente.",
        "Métricas", ["mpe"]
    ),
    _q(
        "O Ciclo de Revisão (CR) representa:",
        ["Período entre exposições ao mesmo conteúdo, progressivamente maior.",
         "Número máximo de questões de um tópico resolvidas num dia.",
         "Sequência de disciplinas estudadas em uma semana.",
         "Horário reservado exclusivamente para revisão.",
         "Quantidade de ciclos até a data da prova."],
        0,
        "CR gerencia a spaced repetition: o conteúdo é revisitado em intervalos crescentes antes do esquecimento completo.",
        "Métricas", ["cr"]
    ),
    _q(
        "O Percentual de Ciclo Completo (PCC) indica:",
        ["Percentual de disciplinas concluídas do edital.",
         "Proporção do ciclo de revisão já cumprida.",
         "Percentual de questões certas no último simulado.",
         "Fração do tempo decorrido até a prova.",
         "Percentual da meta diária de questões."],
        1,
        "PCC = (dias estudados no ciclo atual / duração total do ciclo) × 100. Ajuda a visualizar o progresso.",
        "Métricas", ["pcc"]
    ),
    _q(
        "A evolução do IC ao longo do tempo serve para:",
        ["Medir horas de estudo acumuladas no mês.",
         "Avaliar se a regularidade está aumentando ou diminuindo.",
         "Mostrar quais disciplinas têm mais questões.",
         "Comparar desempenho entre candidatos.",
         "Prever a nota final no concurso."],
        1,
        "IC crescente = consolidação do hábito. Queda = risco de procrastinação e necessidade de ajuste na rotina.",
        "Métricas", ["ic"]
    ),
    _q(
        "A Técnica Pomodoro recomenda:",
        ["50 min de estudo + 10 de descanso.",
         "25 min de foco + 5 min de pausa, com pausa maior a cada 4 ciclos.",
         "2 horas contínuas sem pausas.",
         "1h de estudo + 30 min de descanso.",
         "Estudar apenas nos intervalos do trabalho."],
        1,
        "Pomodoro (Cirillo): 25 min (pomodoro) + 5 min pausa. A cada 4, pausa de 15-30 min.",
        "Métricas", ["pomodoro"]
    ),
    _q(
        "O DPR (Déficit de Performance Relativa) mede:",
        ["Diferença entre meta e questões respondidas no dia.",
         "Diferença entre % acertos esperado e real em um tópico.",
         "Tempo perdido com distrações.",
         "Quantidade de tópicos não estudados.",
         "Desvio padrão das notas dos simulados."],
        1,
        "DPR = % esperado − % real. DPR alto indica necessidade de revisar teoria antes de novas questões.",
        "Métricas", ["dpr"]
    ),
    _q(
        "A Meta Mínima de Engajamento (MME) é:",
        ["Número mínimo de questões por dia para manter o hábito, mesmo em dias corridos.",
         "Horas mínimas de sono para bom rendimento.",
         "Máximo de dias consecutivos sem estudar.",
         "Menor nota aceitável em simulado.",
         "Tempo mínimo de revisão por disciplina por semana."],
        0,
        "MME (ex: 5 questões/dia) garante que a regularidade (IC) não seja interrompida em dias de baixa disponibilidade.",
        "Métricas", ["mme"]
    ),
    # ── Meio Ambiente (+13) ──
    #
    _q(
        "A Res. CONAMA 357/2005 classifica corpos d'água. Para classe especial:",
        ["Abastecimento doméstico sem tratamento.",
         "Abastecimento após tratamento simplificado.",
         "Preservação do equilíbrio natural, vedado lançamento de efluentes.",
         "Navegação e harmonia paisagística.",
         "Recreação de contato primário."],
        2,
        "Res. CONAMA 357/2005, Art. 4º: classe especial = preservação dos ecossistemas, vedado lançamento de efluentes.",
        "Meio Ambiente", ["conama"]
    ),
    _q(
        "A Lei 12.651/2012 (Código Florestal) define APP como:",
        ["Área com cobertura florestal para exploração de madeira.",
         "Área protegida com função ambiental de preservar recursos hídricos, estabilidade geológica e biodiversidade.",
         "Área urbana para parques públicos.",
         "Área rural com potencial agrícola mecanizado.",
         "Propriedade privada com direito de desmatamento integral."],
        1,
        "Lei 12.651/2012, Art. 3º, II: APP protege recursos hídricos, paisagem, estabilidade geológica, biodiversidade, solo e bem-estar humano.",
        "Meio Ambiente", ["florestal"]
    ),
    _q(
        "O licenciamento ambiental de atividades offshore de O&G é competência:",
        ["Do IBAMA (federal), devido ao impacto em âmbito nacional ou marinho.",
         "Do órgão estadual do litoral onde a plataforma está.",
         "Do município sede da operadora.",
         "Da ANP.",
         "Do MME."],
        0,
        "LC 140/2011, Art. 7º, XIV: IBAMA licencia atividades offshore e exploração de petróleo na plataforma continental e mar territorial.",
        "Meio Ambiente", ["licenciamento"]
    ),
    _q(
        "O EIA deve conter, entre outros:",
        ["Diagnóstico ambiental, análise de impactos, medidas mitigadoras e monitoramento.",
         "Apenas levantamento topográfico e viabilidade financeira.",
         "Plano de carreira dos funcionários.",
         "Relação de EPIs.",
         "Cronograma de implantação sem avaliação de impactos."],
        0,
        "Res. CONAMA 01/86, Art. 6º: diagnóstico (meios físico, biológico, socioeconômico), análise de impactos, medidas mitigadoras/compensatórias e monitoramento.",
        "Meio Ambiente", ["eia"]
    ),
    _q(
        "A logística reversa (Lei 12.305/2010) é obrigatória para:",
        ["Agrotóxicos, pilhas, pneus, óleos lubrificantes e eletroeletrônicos.",
         "Apenas embalagens de alimentos.",
         "Todos os resíduos domiciliares.",
         "Resíduos de serviços de saúde exclusivamente.",
         "Entulho da construção civil."],
        0,
        "Lei 12.305/2010, Art. 33: logística reversa obrigatória para agrotóxicos, pilhas/baterias, pneus, óleos lubrificantes, lâmpadas e eletroeletrônicos.",
        "Meio Ambiente", ["residuos"]
    ),
    _q(
        "O PRONAR (Res. CONAMA 05/1989) estabelece:",
        ["Padrões de qualidade do ar e limites de emissão para fontes fixas e móveis.",
         "Proibição total da queima de combustíveis fósseis.",
         "Limite máximo de veículos nas capitais.",
         "Obrigatoriedade de filtros biológicos em todas as chaminés.",
         "Substituição integral da frota por elétricos."],
        0,
        "Res. CONAMA 05/1989: padrões primários (saúde) e secundários (meio ambiente) de qualidade do ar, limites de emissão e monitoramento.",
        "Meio Ambiente", ["qualidade-ar"]
    ),
    _q(
        "A Res. CONAMA 430/2011 estabelece para lançamento de efluentes:",
        ["pH 5-9, temperatura < 40°C, óleos e graxas ≤ 20 mg/L.",
         "Proibição total de lançamento de efluentes.",
         "Obrigatoriedade de diluição em água doce.",
         "Reuso integral obrigatório.",
         "Descarte no mar sem licenciamento."],
        0,
        "Res. CONAMA 430/2011: pH 5-9, T < 40°C, materiais sedimentáveis ≤ 1 mL/L, óleos/graxas ≤ 20 mg/L, DBO ≤ 130 mg/L.",
        "Meio Ambiente", ["efluentes"]
    ),
    _q(
        "A Avaliação Ambiental Estratégica (AAE) avalia impactos:",
        ["Em nível de políticas, planos e programas, antes dos projetos individuais.",
         "Substitui o EIA/RIMA para todos os empreendimentos.",
         "Equivale ao Relatório de Sustentabilidade GRI.",
         "Apenas a viabilidade econômica.",
         "Realizada exclusivamente após implantação."],
        0,
        "AAE: instrumento de planejamento que integra considerações ambientais em PPP governamentais. Prevista na PNMC (Lei 12.187/2009).",
        "Meio Ambiente", ["aae"]
    ),
    _q(
        "A PNMC (Lei 12.187/2009) estabelece como instrumento:",
        ["Plano Nacional sobre Mudança do Clima e SBCE (mercado de carbono).",
         "Proibição total de emissões de GEE pela indústria.",
         "Eliminação de combustíveis fósseis até 2030.",
         "Imposto sobre carbono com alíquota de 10%.",
         "Fechamento de todas as termelétricas a carvão."],
        0,
        "Lei 12.187/2009, Art. 6º: Plano Nacional, Fundo Clima, SBCE, comunicações ao UNFCCC e planos setoriais de mitigação.",
        "Meio Ambiente", ["clima"]
    ),
    _q(
        "A Res. CONAMA 420/2009 para áreas contaminadas estabelece:",
        ["Valores orientadores (prevenção, intervenção) e critérios para investigação e remediação.",
         "Que toda área industrial é contaminada.",
         "Proibição total de atividades industriais em áreas urbanas.",
         "Apenas o IBAMA declara área contaminada.",
         "Isenção do proprietário após venda do imóvel."],
        0,
        "Res. CONAMA 420/2009: VRQ, Valor de Prevenção, Valor de Intervenção. Fases: investigação preliminar, confirmatória, detalhada e plano de intervenção.",
        "Meio Ambiente", ["areas-contaminadas"]
    ),
    _q(
        "O desenvolvimento sustentável (Rio-92) fundamenta-se em:",
        ["Conciliar desenvolvimento econômico, preservação ambiental e justiça social.",
         "Crescimento econômico a qualquer custo.",
         "Industrialização acelerada com máxima exploração de recursos.",
         "Manter intactos todos os ecossistemas sem atividade econômica.",
         "Substituir todas as fontes fósseis por renováveis em 5 anos."],
        0,
        "Relatório Brundtland (1987): atender necessidades presentes sem comprometer gerações futuras. Tripé: ambiental, social, econômico.",
        "Meio Ambiente", ["principios"]
    ),
    _q(
        "A Res. CONAMA 462/2014 estabelece licenciamento de:",
        ["Geração eólica em superfície terrestre.",
         "Exploração de petróleo offshore.",
         "Usinas hidrelétricas > 30 MW.",
         "Aterros sanitários.",
         "Mineração em APP."],
        0,
        "Res. CONAMA 462/2014: parques eólicos em terra, critérios para instalação, operação, impacto em aves e audiências públicas.",
        "Meio Ambiente", ["licenciamento"]
    ),
    _q(
        "O Cadastro Ambiental Rural (CAR) é:",
        ["Registro público eletrônico obrigatório para todos os imóveis rurais, para planejamento ambiental.",
         "Certificado voluntário de sustentabilidade.",
         "Imposto territorial rural com alíquotas por bioma.",
         "Programa de pagamento por serviços ambientais.",
         "Sistema de licenciamento agropecuário."],
        0,
        "Lei 12.651/2012, Art. 29: CAR obrigatório, via SICAR, com dados de APP, reserva legal e vegetação nativa.",
        "Meio Ambiente", ["car"]
    ),
    # ── Atualidades (+10) ──
    #
    _q(
        "A Refinaria Abreu e Lima (RNEST) tem capacidade aproximada de:",
        ["100 mil bpd.", "130 mil bpd.", "200 mil bpd.", "250 mil bpd.", "300 mil bpd."],
        1,
        "RNEST (Ipojuca/PE): capacidade nominal de 130.000 bpd. Produz diesel S-10, GLP e nafta.",
        "Atualidades", ["petrobras", "refino"]
    ),
    _q(
        "A produção brasileira de petróleo em 2024-2025 é de aproximadamente:",
        ["2,0 milhões bpd.", "3,0 milhões bpd.", "3,5 milhões bpd.", "4,3 milhões bpd.", "5,5 milhões bpd."],
        2,
        "~3,4-3,5 milhões bpd (incluindo gás). Pré-sal responde por ~75% da produção total.",
        "Atualidades", ["petrobras", "producao"]
    ),
    _q(
        "A Margem Equatorial brasileira abrange:",
        ["RS até SC.",
         "Amapá até RN (Foz do Amazonas, Pará-Maranhão, Barreirinhas, Ceará, Potiguar).",
         "ES até SC (Santos e Campos).",
         "Bacia de Pelotas até Santos.",
         "Apenas o Pré-Sal da Bacia de Santos."],
        1,
        "Margem Equatorial: nova fronteira exploratória, do AP ao RN. Potencial similar à margem equatorial da África (Guiana, Suriname).",
        "Atualidades", ["petrobras", "exploracao"]
    ),
    _q(
        "A nova Política de Preços de Combustíveis da Petrobras (2023) baseia-se em:",
        ["PPI (Paridade de Preços de Importação).",
         "Estratégia que considera alternativas de abastecimento, sem repasse automático da volatilidade internacional.",
         "Congelamento total por decreto.",
         "Preço único definido pelo CNPE.",
         "Subsídio integral com recursos do Tesouro."],
        1,
        "Maio/2023: Petrobras abandonou o PPI. Nova estratégia: flexibilidade de prazos e frequência de reajustes, sem repasse automático diário.",
        "Atualidades", ["petrobras", "precos"]
    ),
    _q(
        "O Combustível do Futuro (Lei 14.993/2024) instituiu:",
        ["ProBioQAV, PNDV e aumento do teor de etanol anidro na gasolina para até 35%.",
         "Proibição total da gasolina no transporte urbano.",
         "Obrigatoriedade de veículos elétricos até 2035.",
         "Imposto sobre emissões de carbono.",
         "Fim dos subsídios ao etanol."],
        0,
        "Lei 14.993/2024: SAF obrigatório na aviação, diesel verde, etanol anidro até 35% na gasolina e marco de CCS.",
        "Atualidades", ["combustivel-futuro"]
    ),
    _q(
        "O Fundo Social do Pré-Sal (Lei 12.351/2010) destina recursos para:",
        ["Educação (50%), saúde, CT&I, combate à pobreza e meio ambiente.",
         "Apenas o IRPJ pago pelas petrolíferas.",
         "Totalidade dos royalties.",
         "Dividendos da Petrobras ao Tesouro.",
         "Arrecadação integral da CIDE."],
        0,
        "Lei 12.351/2010, Art. 47 e Lei 13.885/2019: Fundo Social com 50% para educação, além de saúde, ciência, combate à pobreza e meio ambiente.",
        "Atualidades", ["fundo-social"]
    ),
    _q(
        "A transição energética brasileira para hidrogênio verde tem vantagem:",
        ["Grande oferta de energia renovável para eletrólise e infraestrutura portuária.",
         "Abundância de carvão mineral para H₂ cinza.",
         "Experiência consolidada em energia nuclear.",
         "Disponibilidade de gás de xisto.",
         "Frota de veículos a H₂ em larga escala."],
        0,
        "Matriz elétrica ~85% renovável, ventos excepcionais e alto potencial solar permitem H₂ verde de baixo custo para exportação.",
        "Atualidades", ["hidrogenio"]
    ),
    _q(
        "O Mercado Livre de Gás (Lei 14.134/2021) promoveu:",
        ["Manutenção do monopólio da Petrobras.",
         "Acesso de terceiros a gasodutos e terminais de GNL, unbundling e saída da Petrobras do transporte.",
         "Proibição de comercialização por empresas privadas.",
         "Preço único nacional para o gás.",
         "Eliminação da participação da Petrobras."],
        1,
        "Lei 14.134/2021: livre mercado de gás, acesso não discriminatório, carregador, unbundling, venda da TAG e NTS pela Petrobras.",
        "Atualidades", ["gas"]
    ),
    _q(
        "O leilão de blocos da ANP em 2024-2025 teve como destaque:",
        ["Blocos na Margem Equatorial sem licenciamento do IBAMA.",
         "Blocos terrestres e marítimos, com ênfase na Margem Equatorial e áreas maduras, com controvérsias ambientais.",
         "Venda integral de todos os blocos ofertados.",
         "Ausência da Petrobras nos leilões.",
         "Proibição de empresas estrangeiras."],
        1,
        "Leilões ANP: blocos na Margem Equatorial (aguardando licenciamento), áreas terrestres em bacias maduras e blocos marítimos em SE-AL e Potiguar.",
        "Atualidades", ["anp"]
    ),
    _q(
        "A produção mundial de petróleo em 2025 é liderada por:",
        ["Brasil como maior produtor global.",
         "Estados Unidos (maior produtor), seguido por Arábia Saudita e Rússia, com o Brasil entre os 10 maiores.",
         "Apenas países da OPEP.",
         "China como maior produtor e consumidor.",
         "Venezuela como maior reserva e produtora."],
        1,
        "EIA/OPEP 2025: EUA lideram produção mundial (~13 milhões bpd). Brasil (~3,5 milhões bpd) está entre os 10 maiores produtores globais.",
        "Atualidades", ["petrobras"]
    ),

    # ── Informática (+10) ──
    #
    _q(
        "No Excel, =CONT.SE(A1:A10;\">5\") conta:",
        ["Células > 5.", "Soma dos valores > 5.", "Células com texto.", "Média > 5.", "Células em branco."],
        0,
        "CONT.SE (COUNTIF) conta células que atendem ao critério > 5 no intervalo.",
        "Informática", ["excel"]
    ),
    _q(
        "Ctrl+Z no Windows executa:",
        ["Salvar.", "Desfazer (undo).", "Refazer (redo).", "Copiar.", "Recortar."],
        1,
        "Ctrl+Z = desfazer. Ctrl+Y = refazer. Ctrl+C copia, Ctrl+X recorta, Ctrl+S salva.",
        "Informática", ["windows"]
    ),
    _q(
        "O sistema de arquivos NTFS oferece:",
        ["Permissões de segurança, EFS, compressão, cotas de disco e journaling.",
         "Suporte apenas a nomes de 8 caracteres.",
         "Compatibilidade exclusiva com Linux.",
         "Nenhum recurso de segurança.",
         "Criptografia obrigatória em todos os arquivos."],
        0,
        "NTFS: ACLs, EFS (criptografia), compressão, cotas, journaling ($LogFile), suporte a arquivos > 4 GB e links simbólicos.",
        "Informática", ["windows"]
    ),
    _q(
        "Phishing é:",
        ["Ataque DDoS.",
         "Engenharia social: atacante se passa por entidade confiável para obter dados sensíveis.",
         "Malware de autopropagação.",
         "Vulnerabilidade de execução remota.",
         "Roubo físico de equipamentos."],
        1,
        "Phishing: mensagens simulando instituições legítimas para induzir vítima a fornecer dados pessoais/financeiros.",
        "Informática", ["seguranca"]
    ),
    _q(
        "No Excel, $B$5 é referência:",
        ["Relativa.", "Absoluta (coluna B e linha 5 fixas).", "Mista de linha.", "Mista de coluna.", "3D."],
        1,
        "$B$5 = absoluta. B5 = relativa. B$5 = mista (linha fixa). $B5 = mista (coluna fixa).",
        "Informática", ["excel"]
    ),
    _q(
        "F5 no PowerPoint inicia:",
        ["Janela de propriedades.", "Apresentação desde o 1º slide.", "Novo slide.", "Impressão.", "Salvar."],
        1,
        "F5 = slideshow do início. Shift+F5 = do slide atual. Esc = encerra.",
        "Informática", ["powerpoint"]
    ),
    _q(
        "HTTPS utiliza criptografia baseada em:",
        ["SSL/TLS com certificados X.509 para autenticação e criptografia.",
         "Apenas autenticação básica sem criptografia.",
         "Chave simétrica pré-compartilhada.",
         "SSH para tunelamento.",
         "Criptografia ponta a ponta sem certificados."],
        0,
        "HTTPS: TLS na camada de transporte, certificado X.509 assinado por AC. Porta 443. Handshake assimétrico RSA/ECDHE.",
        "Informática", ["redes"]
    ),
    _q(
        "BitLocker no Windows:",
        ["Gerencia permissões de rede.",
         "Criptografa unidades inteiras para proteger dados em caso de perda/roubo.",
         "Otimiza disco via desfragmentação.",
         "Gerencia atualizações automáticas.",
         "Faz backup para OneDrive."],
        1,
        "BitLocker (Pro/Enterprise): criptografia AES 128/256 com TPM. Protege contra acesso físico não autorizado ao disco.",
        "Informática", ["windows"]
    ),
    _q(
        "As 4 camadas do modelo TCP/IP são:",
        ["Aplicação, Transporte, Internet, Interface de Rede.",
         "Apresentação, Sessão, Transporte, Física.",
         "Aplicação, Apresentação, Sessão, Transporte.",
         "Aplicação, Transporte, Rede, Enlace.",
         "Sessão, Transporte, Internet, Acesso."],
        0,
        "TCP/IP (RFC 1122): Aplicação (HTTP,FTP,SMTP), Transporte (TCP,UDP), Internet (IP,ICMP), Interface de Rede (Ethernet,Wi-Fi).",
        "Informática", ["redes"]
    ),
    _q(
        "No Teams, 'Canais' servem para:",
        ["Organizar comunicação por tópicos com conversas e arquivos por assunto/projeto.",
         "Chamadas de vídeo individuais.",
         "Enviar e-mails em massa.",
         "Criar site público da equipe.",
         "Gerenciar permissões de convidados."],
        0,
        "Teams: canais são subseções para organizar discussões por temas, com abas de Postagens, Arquivos e Wiki.",
        "Informática", ["teams"]
    ),
    # ── Raciocínio Lógico (+8) ──
    #
    _q(
        "Em uma turma de 60, 35 estudam matemática, 28 português e 12 ambas. Quantos não estudam nenhuma?",
        ["7.", "8.", "9.", "10.", "11."],
        2,
        "n(M∪P) = 35+28−12 = 51. Nenhuma = 60−51 = 9.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "O próximo número da sequência 2, 6, 12, 20, 30, ? é:",
        ["36.", "38.", "40.", "42.", "44."],
        2,
        "Diferenças: +4, +6, +8, +10, +12. Próximo = 30+12 = 42. Sequência: n×(n+1).",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Se Maria > João > Pedro, então:",
        ["Maria > Pedro, Pedro é o mais baixo.",
         "Pedro > Maria.",
         "Não é possível comparar Maria e Pedro.",
         "João é o mais alto.",
         "Maria e Pedro têm a mesma altura."],
        0,
        "Transitividade: Maria > João > Pedro. Maria é a mais alta, Pedro o mais baixo.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Sequência ○, △, □, ○, △, □, ○, △, ?. O próximo é:",
        ["○.", "△.", "□.", "○△.", "○□."],
        2,
        "Padrão ○-△-□ se repete a cada 3. Posição 9 = 9 mod 3 = 0 → terceiro elemento = □.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "A negação de 'Todos os técnicos são competentes e dedicados' é:",
        ["Nenhum é competente ou dedicado.",
         "Existe técnico que não é competente ou não é dedicado.",
         "Todos são incompetentes e não dedicados.",
         "Nenhum é competente e dedicado.",
         "Existe técnico competente e não dedicado."],
        1,
        "Negação de 'Todo A é B': 'Algum A não é B'. Negação de conjunção: ¬(p∧q) = ¬p ∨ ¬q.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Probabilidade de sortear número par ou > 4 em dado de 1 a 6:",
        ["1/2.", "2/3.", "5/6.", "1/6.", "1/3."],
        1,
        "P(par) = 3/6, P(>4) = 2/6, P(par ∩ >4) = 1/6. P(par ∪ >4) = 3/6+2/6−1/6 = 4/6 = 2/3.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "Se todo A é B e nenhum B é C, conclui-se que:",
        ["Nenhum A é C.", "Todo A é C.", "Algum A é C.", "Nenhum C é A ou B.", "Todo B é A."],
        0,
        "A ⊆ B e B ∩ C = ∅ → A ∩ C = ∅. Nenhum A é C.",
        "Raciocínio Lógico", ["rl"]
    ),
    _q(
        "André na 4ª posição, Beatriz na 9ª, fila de 15 pessoas. Quantos entre eles?",
        ["3.", "4.", "5.", "6.", "7."],
        1,
        "Posições 1,2,3,André(4),5,6,7,8,Beatriz(9),...,15. Entre: 4 pessoas (posições 5,6,7,8).",
        "Raciocínio Lógico", ["rl"]
    ),
    # ── Português (+7) ──
    #
    _q(
        "Assinale a grafia correta segundo o Novo Acordo:",
        ["Micro-ondas, anti-inflamatório, autoescola, paraquedas.",
         "Microondas, antiinflamatório, auto-escola, pára-quedas.",
         "Micro-ondas, anti-inflamatório, autoescola, para-quedas.",
         "Microondas, anti-inflamatório, auto-escola, para-quedas.",
         "Micro-ondas, antiinflamatório, autoescola, para-quedas."],
        0,
        "Novo Acordo: micro-ondas (hífen com o/a), anti-inflamatório (vogal igual), autoescola (prefixo + consoante), paraquedas (perdeu hífen e acento).",
        "Português", ["ortografia"]
    ),
    _q(
        "Em 'Entregaram o prêmio aos candidatos cujo desempenho foi exemplar', 'cujo' é:",
        ["Pronome indefinido.",
         "Pronome relativo possessivo que retoma 'candidatos'.",
         "Conjunção consecutiva.",
         "Advérbio de intensidade.",
         "Preposição acidental."],
        1,
        "'Cujo' é pronome relativo que retoma 'candidatos' e indica posse (desempenho dos candidatos). Concorda com a coisa possuída.",
        "Português", ["pronomes"]
    ),
    _q(
        "'Fazem cinco anos que trabalho na Petrobras' apresenta:",
        ["Erro de concordância (fazer impessoal: 'Faz cinco anos').",
         "Erro de regência nominal.",
         "Erro de colocação pronominal.",
         "Erro de crase.",
         "Erro de pontuação."],
        0,
        "'Fazer' com tempo decorrido é impessoal (sem sujeito) e invariável na 3ª pessoa do singular. Correto: 'Faz cinco anos'.",
        "Português", ["concordancia"]
    ),
    _q(
        "Em 'O diretor informou ao funcionário de que o projeto foi aprovado', há:",
        ["Crase facultativa.",
         "Erro de regência verbal. 'Informar' é VTDI. O correto é 'informou o funcionário de que' ou 'informou ao funcionário que' (sem 'de').",
         "Erro de concordância nominal.",
         "Oração sem sujeito.",
         "Pleonasmo vicioso."],
        1,
        "'Informar' admite VTDI: informar alguém de algo. 'de que' exige objeto indireto com 'a' antes de 'funcionário' ou suprime-se o 'de'.",
        "Português", ["regencia"]
    ),
    _q(
        "Em 'Mas que bela surpresa!', 'mas' é:",
        ["Conjunção adversativa.",
         "Interjeição (surpresa/espanto).",
         "Substantivo.",
         "Advérbio de modo.",
         "Pronome indefinido."],
        1,
        "'Mas' interjeição exprime surpresa/admiração. 'Mas' conjunção adversativa = porém. 'Mas' substantivo = defeito.",
        "Português", ["morfologia"]
    ),
    _q(
        "Em 'Chegando o gerente, a reunião começou', a oração reduzida é:",
        ["Subordinada adverbial temporal reduzida de gerúndio.",
         "Coordenada assindética.",
         "Subordinada substantiva subjetiva.",
         "Subordinada adjetiva explicativa.",
         "Oração principal."],
        0,
        "'Chegando o gerente' (= quando o gerente chegou) é oração subordinada adverbial temporal reduzida de gerúndio.",
        "Português", ["sintaxe"]
    ),
    _q(
        "'Porquê' (acentuado) é correto em:",
        ["Não fui ao trabalho porque estava doente.",
         "Explique o porquê da sua ausência.",
         "Por que você não respondeu?",
         "Estude bastante, porquê a prova é difícil.",
         "O caminho por que passei estava interditado."],
        1,
        "'Porquê' substantivo = motivo/razão (antepor artigo). 'Porque' = pois. 'Por que' = pelo qual/por qual motivo.",
        "Português", ["ortografia"]
    ),
    # ── Engenharia Civil (+5) ──
    #
    _q(
        "A NBR 6118 estabelece que o módulo de elasticidade secante (Ecs) do concreto depende:",
        ["Da resistência fck e do tipo de agregado graúdo (basalto, granito, calcário, arenito).",
         "Apenas da idade do concreto.",
         "Exclusivamente do tipo de cimento.",
         "Da relação água/cimento.",
         "Do tipo de forma metálica utilizada."],
        0,
        "NBR 6118, item 8.2.8: Ecs = αi × 5600 × fck^0,5, onde αi depende do tipo de agregado graúdo.",
        "Engenharia Civil", ["civil", "concreto"]
    ),
    _q(
        "No dimensionamento de vigas de concreto armado à flexão simples, a posição da linha neutra (x) é limitada para garantir:",
        ["A ductilidade da peça, evitando ruptura frágil por esmagamento do concreto antes do escoamento do aço.",
         "A estanqueidade da estrutura.",
         "A redução do peso próprio da viga.",
         "O aumento da flecha máxima admissível.",
         "A simplificação do cálculo do momento fletor."],
        0,
        "NBR 6118: x/d ≤ 0,45 (concreto até C50) para garantir domínio 2 ou 3 (seção subarmada), com escoamento do aço antes da ruptura do concreto.",
        "Engenharia Civil", ["civil", "concreto"]
    ),
    _q(
        "No cálculo de fundações profundas, a capacidade de carga de uma estaca é determinada por métodos como:",
        ["Decourt-Quaresma, Aoki-Velloso e Décourt, baseados no SPT e nos parâmetros do solo.",
         "Apenas pela resistência de ponta do solo.",
         "Pelo método de Terzaghi para capacidade de carga de sapatas.",
         "Pela fórmula de Manning para escoamento em tubulações.",
         "Pela equação de Bernoulli para fluxo de fluidos."],
        0,
        "Métodos semi-empíricos (Decourt-Quaresma, Aoki-Velloso) estimam a capacidade de carga de estacas a partir do NSPT, considerando resistência lateral e de ponta.",
        "Engenharia Civil", ["civil", "fundacoes"]
    ),
    _q(
        "Na hidráulica de condutos livres, a equação de Manning é expressa por:",
        ["V = (1/n) × R^(2/3) × I^(1/2), onde n é o coeficiente de rugosidade de Manning.",
         "V = C × (R × I)^0,5 (Fórmula de Chézy).",
         "V = (g × R × I)^0,5.",
         "V = (2 × g × h)^0,5.",
         "V = Q / A."],
        0,
        "Manning: V = (1/n) × R^(2/3) × I^(1/2) (m/s), onde n é rugosidade, R = raio hidráulico (m), I = declividade (m/m). Essencial para cálculo de canais e galerias.",
        "Engenharia Civil", ["civil", "hidraulica"]
    ),
    _q(
        "No aço CA-50, o número 50 indica:",
        ["O diâmetro máximo da barra em mm.",
         "A resistência característica ao escoamento de 500 MPa (50 kgf/mm²).",
         "O módulo de elasticidade do aço em GPa.",
         "A resistência à tração última em kN.",
         "O alongamento mínimo na ruptura em %."],
        1,
        "CA-50 (NBR 7480): aço com resistência característica ao escoamento (fyk) de 500 MPa. CA-60 tem fyk = 600 MPa. CA-25 tem fyk = 250 MPa.",
        "Engenharia Civil", ["civil", "estruturas"]
    ),
    # ── Engenharia Mecânica (+5) ──
    #
    _q(
        "No ciclo Rankine (vapor), a bomba de alimentação eleva a pressão do líquido:",
        ["De forma isentrópica (ideal), da pressão do condensador para a pressão da caldeira.",
         "De forma isotérmica, mantendo a temperatura constante.",
         "De forma isobárica, mantendo a pressão constante.",
         "De forma isocórica, a volume constante.",
         "Apenas por gravidade, sem consumo de energia."],
        0,
        "Ciclo Rankine ideal: 1-2 compressão isentrópica na bomba (líquido), 2-3 aquecimento isobárico na caldeira, 3-4 expansão isentrópica na turbina, 4-1 condensação isobárica no condensador.",
        "Engenharia Mecânica", ["mec", "termo"]
    ),
    _q(
        "O número de Reynolds (Re) é um parâmetro adimensional que:",
        ["Mede a relação entre forças inerciais e forças viscosas, determinando o regime de escoamento (laminar, transição ou turbulento).",
         "Mede a relação entre forças de pressão e forças viscosas.",
         "Indica o grau de compressibilidade do fluido.",
         "Representa a relação entre velocidade do som e velocidade do fluido.",
         "Mede a transferência de calor por convecção."],
        0,
        "Re = ρ·v·D/μ. Laminar: Re < 2000. Turbulento: Re > 4000. Transição: 2000 < Re < 4000. Essencial para cálculo de perda de carga.",
        "Engenharia Mecânica", ["mec", "fluidos"]
    ),
    _q(
        "A Lei de Fourier para condução de calor unidimensional em regime permanente é:",
        ["q = −k × A × (dT/dx), onde k é a condutividade térmica do material.",
         "q = h × A × (Ts − T∞), onde h é o coeficiente convectivo.",
         "q = σ × ε × A × (T1⁴ − T2⁴), onde σ é a constante de Stefan-Boltzmann.",
         "q = m × cp × ΔT, onde cp é o calor específico.",
         "q = U × A × ΔTlm, onde U é o coeficiente global."],
        0,
        "Lei de Fourier: o fluxo de calor por condução é proporcional ao gradiente de temperatura e à condutividade térmica do material (k). Convecção: Lei de Newton do resfriamento.",
        "Engenharia Mecânica", ["mec", "transcal"]
    ),
    _q(
        "Em um sistema hidráulico com dois pistões interligados, aplicando-se uma força de 100 N no pistão menor (área 2 cm²), a força no pistão maior (área 50 cm²) será de:",
        ["250 N.",
         "500 N.",
         "1.000 N.",
         "2.500 N.",
         "5.000 N."],
        3,
        "Princípio de Pascal: P₁ = P₂ → F₁/A₁ = F₂/A₂ → 100/2 = F₂/50 → F₂ = 100 × 50/2 = 2.500 N.",
        "Engenharia Mecânica", ["mec", "fluidos"]
    ),
    _q(
        "O fenômeno de fadiga em materiais metálicos ocorre quando:",
        ["O material é submetido a cargas estáticas acima do limite de escoamento.",
         "O material é submetido a cargas cíclicas (alternadas), com tensões abaixo do limite de escoamento, gerando falha por propagação de trinca.",
         "A temperatura de operação excede a temperatura de fusão do material.",
         "Ocorre deformação plástica excessiva em um único ciclo de carga.",
         "O material sofre corrosão generalizada em ambiente ácido."],
        1,
        "Fadiga: falha sob tensões cíclicas com valores abaixo do limite de escoamento. A curva S-N (Wöhler) descreve a vida em fadiga. Fatores: concentração de tensão, acabamento superficial e temperatura.",
        "Engenharia Mecânica", ["mec", "resistencia"]
    ),
    # ── Engenharia Elétrica (+5) ──
    #
    _q(
        "No teorema de Thévenin, qualquer circuito linear pode ser substituído por:",
        ["Uma fonte de corrente em paralelo com uma impedância.",
         "Uma fonte de tensão equivalente Vth em série com uma impedância Zth.",
         "Uma resistência equivalente sem fonte.",
         "Uma fonte de tensão ideal sem impedância.",
         "Uma fonte de corrente ideal sem admitância."],
        1,
        "Teorema de Thévenin: qualquer circuito linear entre dois terminais equivale a uma fonte de tensão Vth (tensão de circuito aberto) em série com Zth (impedância equivalente com fontes anuladas).",
        "Engenharia Elétrica", ["ele", "circuitos"]
    ),
    _q(
        "Em um gerador síncrono, a regulação de tensão é controlada ajustando-se:",
        ["A velocidade da máquina primária.",
         "A corrente de campo do rotor, que controla o fluxo magnético e a tensão induzida no estator.",
         "A carga conectada aos terminais do gerador.",
         "O ângulo de carga do rotor.",
         "A frequência da rede elétrica."],
        1,
        "A tensão terminal de um gerador síncrono é controlada pela corrente de campo (excitação). Maior corrente de campo → maior fluxo → maior tensão induzida. O regulador automático de tensão (AVR) ajusta a excitação.",
        "Engenharia Elétrica", ["ele", "maquinas"]
    ),
    _q(
        "O fator de potência de uma instalação pode ser corrigido com a instalação de:",
        ["Indutores em série com a carga.",
         "Capacitores em paralelo com a carga, compensando a potência reativa indutiva.",
         "Resistores em paralelo com a carga.",
         "Transformadores de isolamento.",
         "Disjuntores diferenciais residuais (DR)."],
        1,
        "Correção do FP: capacitores em paralelo (banco de capacitores) fornecem potência reativa capacitiva para compensar a reativa indutiva de motores e transformadores. A ANEEL (RES 1000/2021) exige FP ≥ 0,92.",
        "Engenharia Elétrica", ["ele", "potencia"]
    ),
    _q(
        "O relé de proteção de sobrecorrente temporizado (51) é utilizado para:",
        ["Proteção diferencial de transformadores.",
         "Proteção contra curtos-circuitos e sobrecargas, com curva tempo x corrente inversa (IEC ou ANSI).",
         "Religamento automático de linhas de transmissão.",
         "Proteção de sobretensão em barras.",
         "Sincronismo de geradores com a rede."],
        1,
        "Relé 51 (ANSI/IEEE): sobrecorrente temporizado de fase, com curvas inversas (IEC: normal, muito inversa, extremamente inversa) ou curva de tempo definido. Protege contra curto e sobrecarga.",
        "Engenharia Elétrica", ["ele", "protecao"]
    ),
    _q(
        "Em sistemas de potência, o fator de potência unitário (FP = 1) significa que:",
        ["A potência reativa é máxima.",
         "A potência ativa é igual à potência aparente (P = S), sem circulação de potência reativa.",
         "A tensão está em quadratura com a corrente.",
         "A corrente é máxima para a potência transmitida.",
         "O sistema está em ressonância série."],
        1,
        "FP = P/S = cos φ. FP = 1 → φ = 0° → tensão e corrente em fase → apenas potência ativa (P = S). Não há potência reativa circulante, minimizando as perdas por corrente reativa.",
        "Engenharia Elétrica", ["ele", "potencia"]
    ),
    # ── Engenharia Química (+5) ──
    #
    _q(
        "O número de pratos teóricos em uma coluna de destilação pode ser determinado pelo método de:",
        ["McCabe-Thiele, que utiliza o diagrama xy de equilíbrio e as retas de operação das seções de retificação e esgotamento.",
         "Ponchon-Savarit, que requer dados de entalpia.",
         "Fenske-Underwood para destilação multicomponente.",
         "Método de Lewis para absorção gasosa.",
         "Equação de Antoine para pressão de vapor."],
        0,
        "Método de McCabe-Thiele: constrói-se o diagrama xy (equilíbrio), traça-se a reta de alimentação (q-line) e os degraus entre as retas de operação para determinar o número de estágios teóricos.",
        "Engenharia Química", ["quim", "operacoes"]
    ),
    _q(
        "A Lei de Raoult para uma solução ideal estabelece que:",
        ["A pressão parcial de um componente na fase vapor é igual à sua fração molar na fase líquida multiplicada pela pressão de vapor do componente puro.",
         "A pressão total do sistema é a soma das pressões parciais.",
         "A solubilidade de um gás em um líquido é proporcional à pressão parcial.",
         "A velocidade de uma reação é proporcional ao produto das concentrações dos reagentes.",
         "O fluxo difusivo é proporcional ao gradiente de concentração."],
        0,
        "Lei de Raoult: Pi = xi × Pvap,i. Válida para soluções ideais (forças intermoleculares semelhantes). Excesso ou desvio da idealidade requer modelos como Wilson, NRTL ou UNIQUAC.",
        "Engenharia Química", ["quim", "termo"]
    ),
    _q(
        "A Equação de Ergun é utilizada para calcular:",
        ["A perda de carga em leitos porosos (fixos) para escoamento de fluidos, combinando os regimes laminar e turbulento.",
         "A velocidade terminal de sedimentação de partículas.",
         "O coeficiente de transferência de massa em colunas de parede molhada.",
         "A eficiência de separação em ciclones.",
         "A queda de pressão em tubulações lisas."],
        0,
        "Equação de Ergun: ΔP/L = 150×μ×(1−ε)²×v/(Dp²×ε³) + 1,75×ρ×(1−ε)×v²/(Dp×ε³). Amplamente usada em reatores de leito fixo e filtração.",
        "Engenharia Química", ["quim", "operacoes"]
    ),
    _q(
        "A Lei de Fick para difusão molecular em regime permanente estabelece que:",
        ["JA = −DAB × (dCA/dz), onde DAB é o coeficiente de difusão do componente A em B.",
         "JA = kc × (CA,s − CA,∞), onde kc é o coeficiente convectivo de massa.",
         "NA = Kp × (PA − PA*), onde Kp é o coeficiente global de transferência de massa.",
         "JA = hD × (ρA,s − ρA,∞), onde hD é o coeficiente de transferência de massa.",
         "Sh = 2 + 0,6 × Re^(1/2) × Sc^(1/3)."],
        0,
        "1ª Lei de Fick: o fluxo difusivo molar é proporcional ao gradiente de concentração. DAB depende do par soluto-solvente, temperatura e pressão. Análoga à Lei de Fourier (calor) e Newton (momentum).",
        "Engenharia Química", ["quim", "transporte"]
    ),
    _q(
        "O craqueamento catalítico fluidizado (FCC) é um processo da indústria petroquímica que:",
        ["Converte frações pesadas do petróleo (gasóleo) em produtos mais leves (GLP, gasolina, diesel) usando catalisador zeolítico em leito fluidizado.",
         "Separa o petróleo bruto em frações por destilação atmosférica.",
         "Remove enxofre dos derivados de petróleo por hidrogenação catalítica.",
         "Produz hidrogênio a partir de gás natural por reforma a vapor.",
         "Polimeriza etileno e propileno para produção de plásticos."],
        0,
        "FCC (Fluid Catalytic Cracking): o catalisador (zeólita) fluidizado craqueia moléculas grandes de gasóleo em moléculas menores de alto valor. O catalisador é regenerado continuamente queimando coque. Produz cerca de 30-40% da gasolina brasileira.",
        "Engenharia Química", ["quim", "petroquimica"]
    ),
    # ── Engenharia de Produção (+5) ──
    #
    _q(
        "O fluxo de caixa descontado (DCF) é um método de avaliação de investimentos que:",
        ["Calcula o prazo de retorno do investimento sem considerar o valor do dinheiro no tempo.",
         "Desconta os fluxos de caixa futuros a valor presente usando uma taxa de desconto (TMA ou WACC), determinando o VPL e a TIR.",
         "Calcula apenas o lucro contábil do projeto.",
         "Considera exclusivamente o investimento inicial ignorando fluxos futuros.",
         "Avalia a liquidez corrente da empresa."],
        1,
        "DCF: VPL = Σ FCt/(1+i)^t − Investimento Inicial. TIR = taxa que zera o VPL. Payback descontado considera o tempo de retorno com fluxos descontados. WACC é a taxa mínima de atratividade.",
        "Engenharia de Produção", ["prod", "economica"]
    ),
    _q(
        "A curva ABC (Curva de Pareto ou 80/20) é utilizada na gestão de estoques para:",
        ["Classificar itens conforme seu valor de consumo: Classe A (80% do valor, 20% dos itens), B (15%), C (5%).",
         "Determinar o lote econômico de compra (LEC).",
         "Calcular o ponto de pedido (ROP) de cada material.",
         "Definir o estoque de segurança baseado no lead time.",
         "Controlar a validade dos produtos perecíveis."],
        0,
        "Curva ABC (Pareto): itens classe A (maior valor) requerem gestão rigorosa, B (intermediário) e C (menor valor) com controle simplificado. Base para o sistema de classificação XYZ.",
        "Engenharia de Produção", ["prod", "qualidade"]
    ),
    _q(
        "Na Teoria das Filas (M/M/1), a utilização do sistema (ρ) é dada por:",
        ["ρ = λ/μ, onde λ é a taxa média de chegada e μ a taxa média de serviço.",
         "ρ = 1 − (λ/μ).",
         "ρ = (λ × μ)^0,5.",
         "ρ = λ/(λ+μ).",
         "ρ = μ/(μ−λ)."],
        0,
        "M/M/1 (chegadas Poisson, serviço exponencial, 1 servidor): ρ = λ/μ. ρ < 1 para estabilidade. Número médio no sistema: L = ρ/(1−ρ). Tempo médio: W = 1/(μ−λ).",
        "Engenharia de Produção", ["prod", "po"]
    ),
    _q(
        "O MASP (Método de Análise e Solução de Problemas) segue o ciclo PDCA e é estruturado em 8 etapas, sendo a primeira:",
        ["Identificação do problema (definição clara do problema, histórico e metas).",
         "Implementação de ações corretivas.",
         "Análise estatística de processos.",
         "Treinamento da equipe de melhoria contínua.",
         "Padronização dos resultados obtidos."],
        0,
        "MASP: 1) Identificação do problema, 2) Observação, 3) Análise, 4) Plano de Ação (5W2H), 5) Execução, 6) Verificação, 7) Padronização, 8) Conclusão. Baseado no ciclo PDCA de Deming.",
        "Engenharia de Produção", ["prod", "qualidade"]
    ),
    _q(
        "No MRP (Material Requirements Planning), a explosão de materiais parte:",
        ["Do plano mestre de produção (MPS), calculando as necessidades brutas e líquidas de materiais, considerando estoques, lead times e estrutura do produto.",
         "Da previsão de vendas anual, sem considerar a estrutura do produto.",
         "Do orçamento financeiro da empresa, alocando recursos por centro de custo.",
         "Da capacidade produtiva instalada, independentemente da demanda.",
         "Do histórico de compras do último exercício fiscal."],
        0,
        "MRP: a partir do MPS (Plano Mestre de Produção), exploda a estrutura do produto (BOM) para calcular necessidades de materiais, ordens de compra e produção, respeitando lead times e estoques disponíveis.",
        "Engenharia de Produção", ["prod", "pcp"]
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


def _extraidas() -> list[QuestaoMC]:
    """Questões reais extraídas de PDFs (dados/questoes_extraidas.json)."""
    try:
        from importar_questoes import carregar_extraidas
        out: list[QuestaoMC] = []
        for q in carregar_extraidas():
            opcoes = q.get("opcoes", [])
            correta = q.get("correta")
            if len(opcoes) >= 2 and isinstance(correta, int) and 0 <= correta < len(opcoes):
                out.append(QuestaoMC(
                    pergunta=q["pergunta"], opcoes=opcoes, correta=correta,
                    explicacao=q.get("explicacao", ""), disciplina=q.get("disciplina", ""),
                    tags=q.get("tags", []),
                ))
        return out
    except Exception:
        return []


def banco() -> list[QuestaoMC]:
    """Banco completo: curado (BANCO_QUESTOES) + questões extraídas de PDFs."""
    return BANCO_QUESTOES + _extraidas()


def selecionar_questoes(n: int = 5, disciplina: str = "", tags: list[str] | None = None) -> list[QuestaoMC]:
    """Seleciona n questões do banco completo, filtradas por disciplina/tags."""
    pool = banco()
    if disciplina:
        pool = [q for q in pool if q.disciplina.lower() == disciplina.lower()]
    if tags:
        pool = [q for q in pool if any(t in q.tags for t in tags)]
    if len(pool) > n:
        pool = random.sample(pool, n)
    return pool


def _feedback_llm(cliente, questao: QuestaoMC, escolha: int) -> str:
    """Gera feedback do LLM sobre a resposta do usuário."""
    if cliente is None:
        return ""
    certo = escolha == questao.correta
    system = "Você é um tutor de concurso CESGRANRIO. Dê um feedback curto (máx 4 linhas) sobre a resposta."
    prompt = (
        f"Pergunta: {questao.pergunta}\n"
        f"Opções: {', '.join(f'{i}) {o}' for i, o in enumerate(questao.opcoes))}\n"
        f"Resposta correta: {questao.correta}) {questao.opcoes[questao.correta]}\n"
        f"O candidato {'acertou' if certo else f'errou (escolheu {escolha})'}.\n"
        f"Explique por que a resposta {'está' if certo else 'não está'} correta."
    )
    try:
        return cliente.chat(system=system, messages=[{"role": "user", "content": prompt}], max_tokens=256)
    except Exception:
        return ""


def iniciar_simulado(n_questoes: int = 5, cronometro: int = 0, disciplina: str = "",
                     cliente=None, adaptativo: bool = False) -> dict[str, Any]:
    """Executa um simulado interativo via terminal.

    Args:
        n_questoes: Número de questões.
        cronometro: Limite de minutos (0 = sem limite).
        disciplina: Filtrar por disciplina.
        cliente: Instância de LocalLLM para feedback opcional.
        adaptativo: Se True, escolhe questões na dificuldade certa (coaching Elo).

    Returns:
        Dict com resultados do simulado.
    """
    if adaptativo:
        try:
            from coaching import selecionar_adaptativo
            questoes = selecionar_adaptativo(n_questoes, disciplina=disciplina)
        except Exception:
            questoes = selecionar_questoes(n_questoes, disciplina=disciplina)
    else:
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

        q_inicio = time.time()
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
        if cliente:
            feedback = _feedback_llm(cliente, q, escolha)
            if feedback:
                print(f"  🤖 {feedback.strip()}")

        # SM-2: registra qualidade da resposta
        try:
            qualidade = 4 if correta else 1
            from sm2 import registrar_revisao, carregar
            cartoes = carregar()
            q_idx = next(
                (idx for idx, bq in enumerate(BANCO_QUESTOES)
                 if bq.pergunta == q.pergunta and bq.disciplina == q.disciplina),
                -1
            )
            if q_idx >= 0:
                registrar_revisao(q_idx, q.disciplina, q.pergunta[:80], qualidade, cartoes)
        except Exception:
            pass

        # Coaching adaptativo: calibra habilidade do candidato × dificuldade do item
        try:
            from coaching import registrar_resposta as _coach_registrar
            _coach_registrar(q.disciplina, q, correta)
        except Exception:
            pass

        # Erros C/A/B/T: classifica o erro por heurística de tempo (sem novo input)
        if not correta:
            try:
                from erros import classificar as _clf, registrar_erro as _reg
                cat, _motivo = _clf(tempo_seg=time.time() - q_inicio)
                _reg(q.disciplina, cat)
            except Exception:
                pass

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


def iniciar_prova_completa() -> dict[str, Any]:
    """Simula uma prova completa CESGRANRIO (70 questões, 4h).

    Seleciona questões de todas as disciplinas proporcionalmente.
    O candidato responde todas, depois vê o resultado consolidado.

    Returns:
        Dict com resultados completos da prova.
    """
    n_total = min(70, len(BANCO_QUESTOES))

    questoes = random.sample(BANCO_QUESTOES, n_total)
    tempo_limite = 240 * 60  # 4 horas em segundos

    print("\n" + "═" * 64)
    print("  PROVA COMPLETA CESGRANRIO")
    print(f"  {n_total} questões · 4 horas")
    print("═" * 64)

    respostas_por_disciplina: dict[str, list[dict]] = {}
    tempo_inicio = time.time()

    for i, q in enumerate(questoes, 1):
        print(f"\n--- Questão {i}/{n_total} ---")
        disc = q.disciplina or "Geral"
        print(f"[{disc}]")
        print(q.pergunta)
        print()
        for j, op in enumerate(q.opcoes):
            print(f"  {j}) {op}")

        decorrido = time.time() - tempo_inicio
        restante = tempo_limite - decorrido
        if restante <= 0:
            print("\n⏰ Tempo esgotado!")
            break

        while True:
            try:
                raw = input(f"\nResposta (0-{len(q.opcoes)-1}): ").strip()
                if not raw:
                    raw = "0"
                escolha = int(raw)
                if 0 <= escolha < len(q.opcoes):
                    break
            except ValueError:
                pass

        correta = escolha == q.correta
        resp_data = {
            "pergunta": q.pergunta,
            "opcoes": q.opcoes,
            "escolha": escolha,
            "correta_idx": q.correta,
            "acertou": correta,
            "explicacao": q.explicacao,
            "disciplina": disc,
        }
        respostas_por_disciplina.setdefault(disc, []).append(resp_data)

    tempo_total = round(time.time() - tempo_inicio, 1)

    acertos_geral = sum(
        1 for r in [rd for rds in respostas_por_disciplina.values() for rd in rds]
        if r["acertou"]
    )
    total_respondidas = sum(len(rds) for rds in respostas_por_disciplina.values())

    resultado = {
        "data": time.strftime("%Y-%m-%d"),
        "questoes": total_respondidas,
        "acertos": acertos_geral,
        "pct": round(acertos_geral / total_respondidas * 100, 1) if total_respondidas else 0,
        "tempo_seg": tempo_total,
        "disciplina": "prova-completa",
        "tipo": "prova-completa",
        "respostas": [rd for rds in respostas_por_disciplina.values() for rd in rds],
        "disciplinas": {},
    }

    for disc, rds in respostas_por_disciplina.items():
        acertos_disc = sum(1 for rd in rds if rd["acertou"])
        resultado["disciplinas"][disc] = {
            "total": len(rds),
            "acertos": acertos_disc,
            "pct": round(acertos_disc / len(rds) * 100, 1),
        }

    salvar_simulado(resultado)

    print("\n" + "═" * 64)
    print("  RESULTADO DA PROVA COMPLETA")
    print("═" * 64)
    print(f"  Total: {acertos_geral}/{total_respondidas} ({resultado['pct']}%)")
    print(f"  Tempo: {tempo_total // 60}min {tempo_total % 60}s")
    print()
    for disc, info in sorted(resultado["disciplinas"].items()):
        barra = "█" * int(info["pct"] / 10) + "░" * (10 - int(info["pct"] / 10))
        print(f"  {disc:20s} {barra} {info['acertos']:2d}/{info['total']:2d} ({info['pct']:5.1f}%)")
    print("═" * 64)

    return resultado




