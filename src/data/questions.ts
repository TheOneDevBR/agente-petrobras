import { Questao } from '../types';

export const bancoDeQuestoes: Questao[] = [
  // LÍNGUA PORTUGUESA
  {
    id: 'lp-01',
    disciplina: 'Língua Portuguesa',
    tema: 'Regência Verbal',
    contexto: 'No fragmento "Muitos analistas de energia visam ao aumento da eficiência nos poços maduros de petróleo, enquanto outros assistem passivamente às flutuações do mercado de Brent."',
    enunciado: 'Considerando as normas de regência verbal recomendadas pelo padrão culto da Língua Portuguesa, avalie a correção gramatical e semântica do período e assinale a opção correta.',
    alternativas: {
      A: 'O verbo "visar" exige a preposição "a" no sentido de "mirar/desejar", e o verbo "assistir" no sentido de "presenciar/ver" também exige a preposição "a", tornando o período gramaticalmente correto.',
      B: 'O verbo "visar" deveria ser empregado sem preposição ("visam o aumento"), visto que expressa uma ação transitiva direta comum em textos corporativos.',
      C: 'A expressão "assistem passivamente" devera prescindir da crase antes de "flutuações", visto que "assistir" expressa regência sem preposição quando indica prestar auxílio técnico.',
      D: 'Ambos os verbos exigem regência direta ("visam o aumento" e "assistem as flutuações"), de modo que a presença da preposição é considerada um desvio de hipercorreção típica de enunciados oficiais.',
      E: 'O uso de crase em "às flutuações" está incorreto porque o verbo "assistir", no sentido de presenciar acontecimentos, é transitivo indireto com regência da preposição "de".'
    },
    gabarito: 'A',
    explicacao: 'ALT-A (Gabarito): O verbo "visar" no sentido de ter por objetivo é transitivo indireto e rege a preposição "a" ("visar ao..."). O verbo "assistir" no sentido de ver/presenciar é transitivo indireto e rege a preposição "a" ("assistir às flutuações", com crase devido ao artigo plural). \nALT-B (Armadilha de Estudo Superficial): O candidato costuma ver a regência informal "visar o cargo" e acha correta. \nALT-C (Conteúdo Invertido): Inverte o sentido de "assistir" (socorrer vs presenciar) para confundir. \nALT-D (Quase certa): Apresenta o argumento falso de hipercorreção. \nALT-E (Totalmente incorreta): Afirma que a regência do assistir seria com a preposição "de", o que é gramaticalmente inexistente nesse contexto.',
    armadilhaCode: 'ARM-LP2'
  },
  {
    id: 'lp-02',
    disciplina: 'Língua Portuguesa',
    tema: 'Conectivos e Coesão',
    contexto: 'Considere o seguinte trecho: "A transição energética para fontes limpas avança em ritmo constante; conquanto, o gás natural continuará a desempenhar papel relevante na segurança do sistema elétrico nacional por pelo menos mais duas décadas."',
    enunciado: 'O conectivo "conquanto" foi utilizado no trecho acima. Com base no valor semântico dos conectivos e na correção gramatical, assinale a opção correta.',
    alternativas: {
      A: 'O conectivo "conquanto" expressa ideia de consequência lógica, e sua substituição por "portanto" mantém o sentido original do período sem necessidade de alteração verbal.',
      B: 'O uso de "conquanto" está incorreto, pois este conectivo possui valor concessivo (embora) e exige verbo no subjuntivo. Para expressar a oposição pretendida entre as orações coordenadas, deveria ser utilizado um conectivo adversativo como "contudo" ou "entretanto".',
      C: 'O conectivo "conquanto" está correto e equivale a "por conseguinte", expressando a justificativa técnica para o uso do gás natural.',
      D: 'Sua substituição por "visto que" mantém a correção gramatical e a coerência argumentativa do período, mantendo a relação de oposição original intacta.',
      E: 'O conectivo expressa uma condição absoluta e poderia ser perfeitamente substituído por "caso" sem afetar a flexão dos verbos subsequentes.'
    },
    gabarito: 'B',
    explicacao: 'ALT-A (Claramente errada): Afirma que "conquanto" é conclusivo. \nALT-B (Gabarito): "Conquanto" é conjunção subordinativa concessiva (equivale a "embora") e rege o modo subjuntivo. O texto pretendia introduzir uma oposição/contraste coordenado (adversativo), portanto, "contudo" ou "entretanto" são os adequados. \nALT-C (Armadilha): Tenta convencer que o conectivo equivale a "por conseguinte", o que é falso. \nALT-D (Quase certa): Troca o conectivo por um explicativo/causal e alega que mantém a oposição original. \nALT-E (Totalmente incorreta): Alega valor condicional que "conquanto" não possui.',
    armadilhaCode: 'ARM-LP1'
  },
  {
    id: 'lp-03',
    disciplina: 'Língua Portuguesa',
    tema: 'Interpretação e Inferência',
    contexto: '"A exploração de petróleo na Margem Equatorial brasileira desperta debates complexos. De um lado, ambientalistas apontam os riscos de derramamento em uma área de altíssima biodiversidade e correntes marinhas dispersivas. De outro, setores governamentais e petroleiros apontam que a autossuficiência de petróleo do país começará a declinar na próxima década se novas reservas não forem incorporadas, o que comprometeria os royalties que financiam a saúde e a educação pública. A estatal defende que sua tecnologia de contenção e histórico de segurança em águas ultraprofundas atenuam significativamente os riscos ambientais."',
    enunciado: 'Com base no texto, infere-se de forma logicamente sustentada que:',
    alternativas: {
      A: 'A Petrobras tem autorização legal imediata para explorar a Margem Equatorial devido à sua capacidade comprovada em contenção de derramamentos.',
      B: 'Os royalties obtidos com a exploração de petróleo no Brasil são integralmente aplicados no desenvolvimento da Margem Equatorial.',
      C: 'O declínio da autossuficiência energética nacional é uma certeza matemática aceita por ambientalistas e governantes de forma unânime.',
      D: 'O debate sobre a Margem Equatorial envolve um dilema ético-econômico entre a preservação ambiental preventiva e a segurança fiscal/social de longo prazo financiada pelo setor de óleo e gás.',
      E: 'A estatal desconsidera totalmente as correntes marinhas dispersivas em seus relatórios de impacto para acelerar a emissão de licenças operacionais.'
    },
    gabarito: 'D',
    explicacao: 'ALT-A (Quase Certa / Sem embasamento textual): Embora a Petrobras defenda sua tecnologia, o texto não afirma que ela tem "autorização legal imediata". \nALT-B (Claramente errada): O texto diz que os royalties financiam "saúde e educação pública", não o desenvolvimento da Margem Equatorial. \nALT-C (Armadilha de Generalização): O texto coloca o declínio da autossuficiência como argumento de "setores governamentais e petroleiros", não unanimidade de certeza. \nALT-D (Gabarito): O texto expõe o conflito entre riscos de biodiversidade (ambiental) e sustentação dos royalties para saúde/educação (econômico-social). \nALT-E (Totalmente incorreta): Afirma que a empresa desconsidera as correntes, o que contraria a afirmação de que a empresa atesta que sua tecnologia atenua os riscos.',
    armadilhaCode: 'ARM-LP3'
  },

  // RACIOCÍNIO LÓGICO / MATEMÁTICA
  {
    id: 'rl-01',
    disciplina: 'Raciocínio Lógico / Matemática',
    tema: 'Lógica Proposicional',
    contexto: 'Um engenheiro de segurança emitiu a seguinte declaração em um relatório técnico: "Se a pressão do reator subir ou a válvula de alívio falhar, então o alarme de segurança dispara."',
    enunciado: 'Considerando as leis da lógica proposicional clássica, assinale a opção que apresenta uma negação logicamente equivalente para a declaração do engenheiro.',
    alternativas: {
      A: 'A pressão do reator não sobe, a válvula de alívio não falha e o alarme de segurança não dispara.',
      B: 'Se o alarme de segurança não dispara, então a pressão do reator não subiu e a válvula de alívio não falhou.',
      C: 'A pressão do reator sobe ou a válvula de alívio falha, e o alarme de segurança não dispara.',
      D: 'A pressão do reator sobe e a válvula de alívio falha, e o alarme de segurança não dispara.',
      E: 'Se a pressão do reator não subir ou a válvula de alívio não falhar, então o alarme de segurança não dispara.'
    },
    gabarito: 'C',
    explicacao: 'A proposição é da forma (P ∨ Q) → R. A negação de uma condicional A → B é equivalente a A ∧ ~B. \nPortanto, a negação é (P ∨ Q) ∧ ~R, o que equivale a: "A pressão do reator sobe ou a válvula de alívio falha, e o alarme de segurança não dispara" (ALT-C). \nALT-B é a contrapositiva (~R → ~(P ∨ Q)), que é uma equivalência lógica, não a negação. \nALT-A, D e E trazem fórmulas logicamente inválidas como negação.',
    armadilhaCode: 'ARM-RL2'
  },
  {
    id: 'rl-02',
    disciplina: 'Raciocínio Lógico / Matemática',
    tema: 'Matemática Financeira',
    contexto: 'Uma subsidiária da Petrobras estuda investir R$ 100.000 em um projeto de otimização de fluxo de dutos. O projeto promete gerar um retorno de R$ 60.000 ao final do ano 1 e R$ 60.000 ao final do ano 2. A taxa de atratividade mínima (TMA) da companhia é de 10% ao ano.',
    enunciado: 'Desconsiderando efeitos inflacionários e impostos, calcule o Valor Presente Líquido (VPL) desse projeto ao final do segundo ano e assinale a alternativa correta.',
    alternativas: {
      A: 'VPL = R$ 20.000. O projeto é viável pois o retorno absoluto (R$ 120.000) supera o investimento original.',
      B: 'VPL ≈ R$ 4.132. O projeto é economicamente viável porque o VPL é maior do que zero.',
      C: 'VPL ≈ -R$ 4.132. O projeto é inviável pois gera prejuízo financeiro sob a taxa de atratividade de 10%.',
      D: 'VPL ≈ R$ 9.090. O cálculo desconsidera a taxa de desconto no segundo ano por se tratar de capital capitalizado de forma simples.',
      E: 'VPL ≈ R$ 12.430. O projeto é viável visto que a taxa interna de retorno (TIR) atinge exatamente 20% ao ano.'
    },
    gabarito: 'B',
    explicacao: 'VPL = -Investimento + Retorno1/(1+i)^1 + Retorno2/(1+i)^2 \nVPL = -100.000 + 60.000/(1,1) + 60.000/(1,21) \nVPL = -100.000 + 54.545,45 + 49.586,77 = +4.132,22. \nComo o VPL é positivo (~R$ 4.132), o projeto é viável (ALT-B). \nALT-A é a armadilha clássica que ignora o valor do dinheiro no tempo (soma simples 60k+60k - 100k = 20k). \nALT-C inverte o sinal do VPL. \nALT-D e E contêm cálculos incorretos de desconto e TIR.',
    armadilhaCode: 'ARM-RL1'
  },
  {
    id: 'rl-03',
    disciplina: 'Raciocínio Lógico / Matemática',
    tema: 'Probabilidade',
    contexto: 'Em um terminal de distribuição da Petrobras, 3 bombas operam de forma independente. A probabilidade de falha operacional de cada bomba em um dia de pico é de 10% para a Bomba A, 20% para a Bomba B e 30% para a Bomba C.',
    enunciado: 'Se as bombas operam de forma independente, qual é a probabilidade de que pelo menos uma bomba apresente falha operacional durante um dia de pico?',
    alternativas: {
      A: '60,0%. Obtido através da soma simples das probabilidades individuais de falha (10% + 20% + 30%).',
      B: '0,6%. Calculado multiplicando as três probabilidades de falha direta, representando o cenário de acoplamento.',
      C: '49,6%. Calculado usando o complementar da probabilidade de que nenhuma bomba falhe no mesmo dia.',
      D: '50,4%. Representando a média ponderada com foco na bomba de maior probabilidade de interrupção.',
      E: '30,0%. A probabilidade do evento de união é limitada pela taxa de falha da bomba mais instável.'
    },
    gabarito: 'C',
    explicacao: 'Para calcular "pelo menos uma falha", o caminho mais rápido é 1 - P(nenhuma falha). \nP(não falha A) = 0,9. P(não falha B) = 0,8. P(não falha C) = 0,7. \nP(nenhuma falhar) = 0,9 * 0,8 * 0,7 = 0,504 (50,4%). \nP(pelo menos uma falhar) = 1 - 0,504 = 0,496, ou seja, 49,6% (ALT-C). \nALT-A é o erro clássico de somar probabilidades diretas (10+20+30 = 60%). \nALT-B é a multiplicação direta das falhas (0,1 * 0,2 * 0,3 = 0,006 = 0,6%). \nALT-D é a probabilidade complementar de nenhuma falha, mas apresentada como sendo a de falhas.',
    armadilhaCode: 'ARM-RL3'
  },

  // LEGISLAÇÃO E GOVERNANÇA
  {
    id: 'lg-01',
    disciplina: 'Legislação e Governança',
    tema: 'Lei das Estatais (Lei 13.303/2016)',
    contexto: 'Uma sociedade de economia mista, como a Petrobras, deseja celebrar um contrato de prestação de serviços técnicos especializados. A administração interna discute a aplicação das regras de licitação e dispensa conforme a Lei Federal 13.303/2016.',
    enunciado: 'Segundo as normas vigentes na Lei 13.303/2016, a licitação nas empresas estatais:',
    alternativas: {
      A: 'É sempre dispensável para contratação de qualquer obra ou serviço técnico, desde que autorizado pelo Ministério de Minas e Energia.',
      B: 'Pode ser dispensada para contratação de serviços técnicos especializados cujos valores estimados sejam inferiores a R$ 100.000,00, conforme atualização monetária e limites previstos em lei.',
      C: 'Segue integralmente e de forma subsidiária a Lei 14.133/2021 (Nova Lei de Licitações) em todas as suas modalidades, invalidando os regulamentos próprios de licitações das empresas.',
      D: 'Pode ter seu regime de contratação semi-integrada adotado, hipótese na qual o contratado é responsável pela elaboração do projeto básico e do projeto executivo, além da execução física da obra.',
      E: 'Não admite sob qualquer hipótese o critério de julgamento por melhor técnica ou combinação de técnica e preço, privilegiando exclusivamente o menor preço nas estatais.'
    },
    gabarito: 'D',
    explicacao: 'ALT-D (Gabarito): Conforme o art. 42 da Lei 13.303/2016, na contratação semi-integrada, o contratado elabora o projeto básico e o executivo e executa a obra (no regime integrado, o contratado faz até o anteprojeto). \nALT-B (Armadilha de limite): O valor de dispensa para serviços e compras comuns foi atualizado por decreto mas não segue limites puros estáticos de R$ 100.000 fixados de forma genérica sem menção aos incisos da Lei. \nALT-C (Conflito de Leis): A Lei 13.303 possui regime próprio de licitações e contratos, não sendo subordinada diretamente à Lei 14.133 para as atividades finalísticas. \nALT-E (Incorreta): O art. 54 da Lei 13.303 admite sim critérios de melhor técnica ou técnica e preço.',
    armadilhaCode: 'ARM-RL1'
  },
  {
    id: 'lg-02',
    disciplina: 'Legislação e Governança',
    tema: 'Lei Anticorrupção (Lei 12.846/2013)',
    contexto: 'No contexto de compliance e governança da Petrobras, analistas avaliam a aplicação da Lei Anticorrupção (Lei 12.846/2013) sobre atos lesivos praticados por terceiros contratados em benefício da empresa.',
    enunciado: 'A respeito da responsabilidade prevista na Lei 12.846/2013, assinale a opção que reflete corretamente a disciplina legal.',
    alternativas: {
      A: 'A lei estabelece a responsabilidade civil e administrativa objetiva das pessoas jurídicas pela prática de atos lesivos que sejam cometidos em seu interesse ou benefício.',
      B: 'A responsabilidade da pessoa jurídica depende necessariamente da comprovação de dolo ou culpa individual dos seus dirigentes, sob pena de extinção da punibilidade.',
      C: 'A existência de um programa interno de integridade (compliance) isenta a empresa de responder por qualquer multa administrativa decorrente de atos de corrupção.',
      D: 'As sanções administrativas aplicáveis às empresas incluem exclusivamente a advertência verbal e a suspensão da inscrição no cadastro geral de contribuintes.',
      E: 'A celebração de acordo de leniência afasta a obrigatoriedade de reparação integral do dano causado, restando apenas a punição administrativa simplificada.'
    },
    gabarito: 'A',
    explicacao: 'ALT-A (Gabarito): A Lei 12.846 prevê a responsabilidade administrativa e civil OBJETIVA da pessoa jurídica (art. 2º), significando que independe de comprovação de dolo ou culpa. \nALT-B (Incorreta/Armadilha): Exige dolo ou culpa, o que seria responsabilidade subjetiva. \nALT-C (Incorreta): O programa de compliance não isenta, mas serve de atenuante no cálculo das sanções (art. 7º, VIII). \nALT-D (Incorreta): As sanções administrativas incluem multas de até 20% do faturamento bruto e publicação extraordinária da decisão. \nALT-E (Incorreta): O acordo de leniência NÃO exime a pessoa jurídica da obrigação de reparar integralmente o dano (art. 16, § 3º).',
    armadilhaCode: 'ARM-LP1'
  },

  // CONHECIMENTOS PETROBRAS E SETOR DE O&G
  {
    id: 'pb-01',
    disciplina: 'Conhecimentos Petrobras e Setor de O&G',
    tema: 'Cadeia de Valor e Pré-Sal',
    contexto: 'A Petrobras tem focado estrategicamente suas atividades de exploração e produção (E&P) na província do Pré-Sal da Bacia de Santos, em campos de águas ultraprofundas, visando a eficiência de custos.',
    enunciado: 'Em relação ao marco regulatório do Pré-sal e às características geológicas da produção nesta camada, assinale a opção correta.',
    alternativas: {
      A: 'O regime de partilha de produção, regulado pela Lei 12.351/2010, estabelece que a Petrobras é obrigatoriamente a operadora única de todos os blocos licitados sob este modelo, com participação mínima de 50%.',
      B: 'Os reservatórios do pré-sal são compostos majoritariamente por rochas areníticas continentais de alta porosidade, que facilitam a drenagem sem necessidade de poços injetores.',
      C: 'No regime de partilha de produção, o consórcio vencedor é remunerado com o chamado "óleo-custo", que corresponde à parcela da produção de petróleo e gás natural destinada a ressarcir os custos de exploração e desenvolvimento.',
      D: 'O pré-sal brasileiro caracteriza-se pelo acúmulo de óleo leve de alta qualidade em rochas ígneas vulcânicas formadas durante a separação dos continentes Africano e Sul-Americano.',
      E: 'A Lei 12.351/2010 aboliu o pagamento de royalties para exploração no pré-sal, concentrando as compensações fiscais unicamente na partilha do excedente em óleo com a União.'
    },
    gabarito: 'C',
    explicacao: 'ALT-C (Gabarito): Na partilha de produção, o contratado recupera seus custos de desenvolvimento através do "óleo-custo" (limite definido no edital), e o restante ("óleo-lucro") é partilhado entre o consórcio e a União. \nALT-A (Armadilha histórica): A Petrobras não é mais operadora única obrigatória em todos os blocos após a lei 13.365/2016, embora tenha o direito de preferência e participação mínima de 30% quando exercer a opção. \nALT-B (Erro Geológico): Os reservatórios do pré-sal são carbonáticos (calcários formados por estromatólitos), e não areníticos. \nALT-D (Erro de rocha): As rochas geradoras e reservatórios são sedimentares carbonáticas, não vulcânicas. \nALT-E (Erro fiscal): Os royalties continuam sendo cobrados (art. 42 da Lei 12.351).',
    armadilhaCode: 'ARM-RL1'
  },
  {
    id: 'pb-02',
    disciplina: 'Conhecimentos Petrobras e Setor de O&G',
    tema: 'Processos de Refino',
    contexto: 'O parque de refino da Petrobras é responsável por converter o petróleo cru extraído de nossas bacias em derivados como gasolina, diesel, QAV e GLP de alta qualidade para o mercado nacional.',
    enunciado: 'Sobre as unidades de refino e os processos empregados pela Petrobras nas suas refinarias (como REPLAN ou REDUC), avalie as seguintes afirmações e assinale a correta.',
    alternativas: {
      A: 'O craqueamento catalítico fluido (FCC) é um processo puramente físico que separa as frações do petróleo com base em seus diferentes pontos de ebulição, sem alterar a estrutura das moléculas de hidrocarboneto.',
      B: 'A destilação atmosférica é a primeira etapa de separação física nas refinarias e extrai frações leves como o GLP e nafta, enviando o resíduo atmosférico direto para a queima direta em caldeiras sem processamentos adicionais.',
      C: 'O coqueamento retardado é um processo de craqueamento térmico severo que converte frações pesadas de baixo valor comercial (resíduos de vácuo) em derivados mais leves e em coque verde de petróleo.',
      D: 'A reforma catalítica visa reduzir o número de octanas da nafta para tornar a gasolina menos volátil e mais segura para o transporte intermunicipal.',
      E: 'O processo de hidrotratamento (HDT) é empregado para injetar compostos sulfurosos na corrente de diesel S-10, garantindo o poder lubrificante necessário exigido pela ANP.'
    },
    gabarito: 'C',
    explicacao: 'ALT-C (Gabarito): O coqueamento retardado é de fato um craqueamento térmico que trata resíduos pesados e gera derivados médios/leves e coque de petróleo. \nALT-A (Erro conceitual): O craqueamento é um processo QUÍMICO de quebra de moléculas longas (craqueamento). A separação física por ebulição é a destilação. \nALT-B (Incorreta): O resíduo de destilação atmosférica vai para a destilação a vácuo ou coqueamento, não para queima direta. \nALT-D (Incorreta): A reforma catalítica AUMENTA a octanagem da nafta petroquímica para produzir gasolina de alta octanagem. \nALT-E (Incorreta): O HDT remove enxofre (dessulfurização) e nitrogênio, gerando o diesel limpo (S-10, com 10 ppm de enxofre), não injeta enxofre.',
    armadilhaCode: 'ARM-RL2'
  },

  // CONHECIMENTOS ESPECÍFICOS (TI / SISTEMAS - exemplo universal)
  {
    id: 'esp-ti-01',
    disciplina: 'Conhecimentos Específicos',
    tema: 'Bancos de Dados - SQL',
    contexto: 'Considere a existência de uma tabela em um banco de dados relacional da Petrobras denominada `PRODUCAO_DIARIA` com as colunas: `id_poco` (int), `data_registro` (date), `barris_oleo` (decimal) e `status_poco` (varchar). A gerência técnica solicita um relatório que exiba apenas os poços com produção média acumulada superior a 5.000 barris nos poços com status "Ativo".',
    enunciado: 'Assinale a alternativa que apresenta a consulta SQL que atende perfeitamente ao requisito técnico descrito utilizando a sintaxe padrão ANSI SQL.',
    alternativas: {
      A: 'SELECT id_poco, AVG(barris_oleo) FROM PRODUCAO_DIARIA WHERE status_poco = \'Ativo\' AND AVG(barris_oleo) > 5000 GROUP BY id_poco;',
      B: 'SELECT id_poco, AVG(barris_oleo) FROM PRODUCAO_DIARIA WHERE status_poco = \'Ativo\' GROUP BY id_poco HAVING AVG(barris_oleo) > 5000;',
      C: 'SELECT id_poco, SUM(barris_oleo) FROM PRODUCAO_DIARIA WHERE status_poco = \'Ativo\' HAVING AVG(barris_oleo) > 5000 GROUP BY id_poco;',
      D: 'SELECT id_poco, AVG(barris_oleo) FROM PRODUCAO_DIARIA GROUP BY id_poco HAVING status_poco = \'Ativo\' AND AVG(barris_oleo) > 5000;',
      E: 'SELECT id_poco, PRODUCAO_MEDIA = AVG(barris_oleo) FROM PRODUCAO_DIARIA WHERE status_poco = \'Ativo\' AND WHERE PRODUCAO_MEDIA > 5000 GROUP BY id_poco;'
    },
    gabarito: 'B',
    explicacao: 'ALT-B (Gabarito): O filtro individual das linhas deve ser feito na cláusula WHERE (`status_poco = \'Ativo\'`). O agrupamento é feito por `id_poco` com `GROUP BY`. O filtro da função agregada (`AVG(barris_oleo) > 5000`) deve ser posicionado obrigatoriamente na cláusula `HAVING` após o `GROUP BY`. \nALT-A (Erro clássico): Tenta usar a função agregada `AVG` na cláusula `WHERE`, o que causa erro de sintaxe. \nALT-C (Erro de sintaxe): Posiciona o `HAVING` antes do `GROUP BY`. \nALT-D (Erro de sintaxe/lógica): Coloca o filtro de linha `status_poco = \'Ativo\'` no `HAVING` sem agrupá-lo na coluna do GROUP BY. \nALT-E (Erro de sintaxe): Utiliza cláusulas duplicadas `AND WHERE` e sintaxe proprietária inválida.',
    armadilhaCode: 'ARM-RL2'
  },
  // LÍNGUA PORTUGUESA
  {
    id: 'lp-04',
    disciplina: 'Língua Portuguesa',
    tema: 'Colocação Pronominal',
    contexto: 'No relatório técnico da unidade de refino, lê-se: "Os operadores ________ comunicaram sobre o desvio de pressão. Não ___________ informados sobre a parada programada."',
    enunciado: 'Assinale a alternativa que preenche corretamente as lacunas, de acordo com a norma-padrão da língua portuguesa quanto à colocação pronominal.',
    alternativas: {
      A: 'tinham-nos / lhes foram',
      B: 'nos tinham / foram-lhes',
      C: 'tinham nos / foram eles',
      D: 'tinham-nos / foram-nos',
      E: 'nos tinham / lhes foram'
    },
    gabarito: 'A',
    explicacao: 'ALT-A (Gabarito): "Tinham-nos comunicado" — próclise facultativa em locuções verbais com verbo principal no particípio, mas a ênclise é preferível ("tinham-nos"). "Não lhes foram informados" — a palavra negativa "não" atrai o pronome "lhes" para antes da locução verbal "foram informados". \nALT-B: "Não foram-lhes" quebra a regra de próclise obrigatória com advérbio negativo. \nALT-C: "foram eles" altera o sentido original. \nALT-D: "Não foram-nos" mesma violação da próclise. \nALT-E: "Nos tinham" está correto, mas "lhes foram" na segunda lacuna quebra a próclise.',
    armadilhaCode: 'ARM-LP1'
  },
  {
    id: 'rl-04',
    disciplina: 'Raciocínio Lógico / Matemática',
    tema: 'Estruturas Lógicas',
    contexto: 'Em um processo seletivo da Petrobras, os candidatos devem atender aos seguintes critérios para a vaga de Engenheiro de Segurança:\n- Ter curso de Engenharia (E) E especialização em Segurança do Trabalho (S).\n- OU ter mais de 10 anos de experiência na área (X) E curso técnico em Segurança (T).\n- E, em qualquer caso, não ter restrições médicas (R).',
    enunciado: 'Assinale a alternativa que representa corretamente a expressão lógica que descreve os critérios de elegibilidade, onde o resultado deve ser VERDADEIRO para candidatos aptos.',
    alternativas: {
      A: '(E ∨ S) ∧ (X ∨ T) ∧ ¬R',
      B: '((E ∧ S) ∨ (X ∧ T)) ∧ ¬R',
      C: '(E ∧ S) ∨ (X ∧ T ∧ ¬R)',
      D: '((E ∧ S) ∨ X) ∧ T ∧ ¬R',
      E: '(E ∨ X) ∧ (S ∨ T) ∧ ¬R'
    },
    gabarito: 'B',
    explicacao: 'A estruturação correta é: (E ∧ S) ∨ (X ∧ T) são os dois caminhos alternativos de qualificação, e em AMBOS os casos exige-se ¬R (sem restrições médicas). Portanto: ((E ∧ S) ∨ (X ∧ T)) ∧ ¬R. \nALT-B (Gabarito): Expressão correta. \nALT-A: Troca os "E" por "OU" nos pré-requisitos, tornando muito permissivo. \nALT-C: Coloca ¬R apenas no segundo caminho, mas o texto diz "em qualquer caso". \nALT-D: Mistura os operadores incorretamente. \nALT-E: Similar a A, com conectivos incorretos.',
    armadilhaCode: 'ARM-RL2'
  },
  {
    id: 'lg-03',
    disciplina: 'Legislação e Governança',
    tema: 'Regulamento do Petróleo (Lei 9.478/97)',
    contexto: 'A Lei do Petróleo (Lei 9.478/1997) estabelece as bases institucionais para as atividades de exploração, produção, refino e distribuição de petróleo e gás natural no Brasil.',
    enunciado: 'Com base na Lei 9.478/1997 e suas alterações, assinale a alternativa correta acerca das competências e instituições do setor de petróleo e gás natural no Brasil.',
    alternativas: {
      A: 'O Conselho Nacional de Política Energética (CNPE) é o órgão executivo máximo do setor, responsável por fiscalizar as atividades de exploração e produção de petróleo.',
      B: 'A Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP) tem competência para contratar diretamente a exploração e produção, podendo ela própria explorar blocos não concessionados.',
      C: 'O CNPE é um órgão de assessoramento do Presidente da República para formulação de políticas e diretrizes de energia, enquanto a ANP é o ente regulador e fiscalizador das atividades.',
      D: 'A Petrobras, como empresa estatal, está dispensada de obter autorização da ANP para realizar atividades de produção e refino, em razão do seu caráter estratégico previsto na Lei 9.478.',
      E: 'A Lei 9.478/1997 extinguiu o monopólio da União sobre o petróleo e gás natural, transferindo integralmente a titularidade das jazidas para os estados produtores.'
    },
    gabarito: 'C',
    explicacao: 'ALT-C (Gabarito): O CNPE é órgão consultivo de assessoramento à Presidência (art. 2º), e a ANP é a autarquia reguladora e fiscalizadora (art. 7º). \nALT-A (Erro): CNPE não é executivo nem fiscalizador — é consultivo. \nALT-B (Erro): ANP regula e fiscaliza, mas não explora diretamente. \nALT-D (Erro): A Petrobras submete-se à regulação da ANP como qualquer concessionária. \nALT-E (Erro): A titularidade das jazidas permanece da União (art. 20, CF); a Lei 9.478 quebrou o monopólio da Petrobras, não da União.',
    armadilhaCode: 'ARM-LP2'
  },
  {
    id: 'pb-03',
    disciplina: 'Conhecimentos Petrobras e Setor de O&G',
    tema: 'Impacto Ambiental e Sustentabilidade',
    contexto: 'A Petrobras anunciou investimentos de US$ 11,5 bilhões em projetos de descarbonização e energias renováveis no seu Plano Estratégico 2025-2029, incluindo eólicas offshore, captura de carbono (CCUS) e produção de hidrogênio verde.',
    enunciado: 'Considerando o posicionamento estratégico da Petrobras na transição energética e as características técnicas das iniciativas citadas, assinale a alternativa correta.',
    alternativas: {
      A: 'A captura e estocagem de carbono (CCUS) consiste em injetar CO2 em aquíferos subterrâneos para reações químicas espontâneas que convertem o gás em carbonato de sódio sólido.',
      B: 'A energia eólica offshore no Brasil não apresenta viabilidade técnica para a Petrobras devido à profundidade média da plataforma continental brasileira, que excede 500 metros em toda a costa.',
      C: 'O hidrogênio verde, produzido por eletrólise da água utilizando energia renovável, pode ser utilizado em refinarias para substituir parte do hidrogênio cinza oriundo de reforma a vapor do gás natural.',
      D: 'A Petrobras descartou totalmente qualquer investimento em renováveis e foca exclusivamente em aumentar a produção de petróleo na Margem Equatorial sem limites ambientais.',
      E: 'A captura de carbono é uma tecnologia madura que remove 100% do CO2 emitido pelas chaminés das refinarias, tornando neutras as emissões do refino.'
    },
    gabarito: 'C',
    explicacao: 'ALT-C (Gabarito): O H2 verde pode sim substituir parcialmente o H2 cinza nos processos de hidrotratamento (HDT) e hidrocraqueamento das refinarias. \nALT-A (Erro técnico): CCUS injeta CO2 em reservatórios geológicos (não necessariamente aquíferos) e não há conversão espontânea em carbonato de sódio. \nALT-B (Erro): O Brasil tem grande potencial offshore em águas rasas (<50m) no Nordeste e Sul. \nALT-D (Erro): Contradiz o plano estratégico público da companhia. \nALT-E (Erro): Nenhuma tecnologia remove 100% do CO2; a eficiência típica é de 85-95%.',
    armadilhaCode: 'ARM-RL1'
  },
  {
    id: 'esp-ti-03',
    disciplina: 'Conhecimentos Específicos',
    tema: 'Arquitetura de Software - Microsserviços',
    contexto: 'A equipe de arquitetura de TI da Petrobras está modernizando o sistema de gestão de contratos, migrando de uma arquitetura monolítica para microsserviços, visando maior escalabilidade e resiliência.',
    enunciado: 'Sobre os padrões de projeto e práticas recomendadas para arquitetura de microsserviços, assinale a alternativa correta.',
    alternativas: {
      A: 'Em microsserviços, recomenda-se o compartilhamento direto de bancos de dados entre os serviços para garantir consistência transacional ACID em toda a aplicação.',
      B: 'O padrão API Gateway atua como ponto único de entrada, centralizando autenticação, rate limiting e roteamento, mas introduz um ponto potencial de falha que deve ser mitigado com redundância.',
      C: 'Microsserviços devem sempre ser implantados em máquinas virtuais separadas, pois contêineres não oferecem isolamento adequado entre processos concorrentes.',
      D: 'A comunicação síncrona via REST é sempre preferível à comunicação assíncrona por filas de mensagens, pois elimina a complexidade de consistência eventual.',
      E: 'No padrão Saga coreografado, um orquestrador central controla cada transação entre os microsserviços, garantindo rollback automático em caso de falha.'
    },
    gabarito: 'B',
    explicacao: 'ALT-B (Gabarito): O API Gateway é um padrão consolidado que unifica o ponto de entrada, abstrai a complexidade dos serviços internos e centraliza cross-cutting concerns, devendo ser implantado com balanceamento e redundância. \nALT-A (Erro): Microsserviços prezam pelo "database per service" (bases separadas), não compartilhadas. \nALT-C (Erro): Contêineres oferecem isolamento adequado e são o padrão de facto. \nALT-D (Erro): Comunicação assíncrona é frequentemente necessária para resiliência e desacoplamento. \nALT-E (Erro): O padrão coreografado não tem orquestrador central; é o orquestrado que usa um coordenador.',
    armadilhaCode: 'ARM-RL2'
  },
  {
    id: 'esp-ti-02',
    disciplina: 'Conhecimentos Específicos',
    tema: 'Segurança da Informação',
    contexto: 'No desenvolvimento de sistemas corporativos da Petrobras sob o princípio da LGPD, arquitetos de segurança de TI avaliam a aplicação de controles criptográficos para tráfego seguro de dados sensíveis na rede corporativa.',
    enunciado: 'Em relação ao funcionamento de criptografia simétrica e assimétrica em protocolos de comunicação segura como HTTPS (SSL/TLS), assinale a opção correta.',
    alternativas: {
      A: 'A criptografia assimétrica utiliza chaves diferentes para cifrar e decifrar os dados (chave pública e privada) e é empregada na fase inicial de handshake para autenticar o servidor e trocar de forma segura a chave de sessão simétrica.',
      B: 'A criptografia simétrica utiliza uma chave pública para encriptar e uma chave privada para decifrar, sendo ideal para a transmissão contínua de grandes volumes de dados devido ao baixo custo computacional.',
      C: 'O protocolo TLS 1.3 utiliza criptografia assimétrica baseada em algoritmo AES-256 para cifrar todo o conteúdo útil das mensagens trafegadas, dispensando o handshake.',
      D: 'As chaves privadas digitais do servidor HTTPS de uma estatal devem ser públicas e armazenadas em servidores de DNS abertos para auditoria por qualquer órgão de fiscalização.',
      E: 'A criptografia assimétrica é mais rápida que a simétrica, sendo utilizada de ponta a ponta durante toda a conexão para encriptar os pacotes de dados.'
    },
    gabarito: 'A',
    explicacao: 'ALT-A (Gabarito): Correto. O TLS combina ambos: a criptografia assimétrica (chaves pública e privada) é usada no início para autenticação e troca segura de chaves (geralmente via Diffie-Hellman ou RSA). Depois, a criptografia simétrica (chave única compartilhada) assume para encriptar os dados do tráfego real. \nALT-B (Conceito trocado): Descreve a criptografia assimétrica alegando que é a simétrica. \nALT-C (Erro técnico): O AES é um algoritmo de chave simétrica, e não assimétrica. \nALT-D (Erro de segurança): A chave privada nunca deve ser pública nem exposta no DNS. \nALT-E (Conceito trocado): A criptografia assimétrica é muito mais lenta do que a simétrica devido à matemática complexa de grandes números primos, não sendo usada de ponta a ponta para pacotes úteis.',
    armadilhaCode: 'ARM-RL1'
  }
];
