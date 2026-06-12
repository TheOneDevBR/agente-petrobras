# Benchmark de Qualidade — Automatizado
**Data:** 2026-06-12
**Perguntas:** 7
**Total de keywords:** 48

## Sumário

- **qwen2.5:1.5b sem RAG**: `60%` acerto keywords · 80.7s · 9723 chars (120.5 char/s)
- **qwen2.5:1.5b +RAG**: `79%` acerto keywords · 134.4s · 16181 chars (120.4 char/s)

## Detalhes por configuração

### qwen2.5:1.5b sem RAG
- **Score:** 60% (29/48 keywords)
- **Tempo total:** 80.7s
- **Chars:** 9723

**P:** O que é a Lei 13.303/2016 e qual seu principal objeto?
**Score:** 50% (3/6 kw) · 3.5s
**R:** Lei 13.303/2016 é o Estatuto Jurídico das Estatais (empresas públicas e sociedades de economia mista). Seu principal objeto é regulamentar a exploração de atividade econômica pelo Estado, estabelecendo regras de governança, licitações e contratos.

**P:** Qual o regime de licitação aplicável às empresas estatais segundo a Lei 13.303/2016?
**Score:** 50% (3/6 kw) · 5.6s
**R:** De acordo com a Lei 13.303/2016, o regime de licitação aplicável às empresas estatais é o do "Concorrência Aberta". Este regime prevê:

- Licitações públicas abertas para contratação direta ou por meio de convênio.
- Inclusão da concorrência em todas as fases do processo licitatório, desde a elabora

**P:** Cite três princípios da administração pública previstos no caput do Art. 37 da CF.
**Score:** 100% (5/5 kw) · 12.7s
**R:** Princípios da administração pública previstos no caput do Art. 37 da Constituição Federal:

1. Legalidade: A administração deve seguir normas estabelecidas por lei, evitando arbitrariedades ou ilegalidades.

2. Impessoalidade: O servidor público não pode ter interesses pessoais que possam influencia

**P:** O que é a transição energética e quais os principais desafios para o Brasil?
**Score:** 57% (4/7 kw) · 22.0s
**R:** A transição energética é um processo que visa mudar a estrutura do sistema elétrico brasileiro para reduzir o uso de energia fóssil (carvão, petróleo e gás natural) e substituí-lo por fontes renováveis como solar, hidroeletricidade, biomassa e eólica. Este processo é essencial para enfrentar os desa

**P:** Qual a diferença entre empresa pública e sociedade de economia mista?
**Score:** 100% (7/7 kw) · 6.2s
**R:** A diferença entre uma empresa pública e uma sociedade de economia mista é a composição do capital:

1. **Empresa Pública**: Tem seu capital integralmente constituído por recursos do Estado (100% público). O controle sobre as ações é exercido pelo governo, que pode adquirir ou vender ações.

2. **Soc

**P:** Explique o que é a Lei 9.478/1997 (Lei do Petróleo) e sua importância.
**Score:** 44% (4/9 kw) · 13.4s
**R:** A Lei 9.478/1997 é o principal instrumento legal que regula a exploração, produção, comercialização e transporte do petróleo no Brasil. Ela estabelece regras para as empresas públicas e sociedades de economia mista que operam na área petrolífera.

O principal objeto da Lei 9.478/1997 é a regulamenta

**P:** O que é o IC (Índice de Consistência) nos estudos?
**Score:** 38% (3/8 kw) · 17.3s
**R:** O Índice de Consistência (IC) é um indicador utilizado em estudos econômicos para medir a consistência das informações apresentadas sobre uma determinada empresa ou setor. Este índice serve como uma ferramenta para avaliar o nível de confiabilidade e precisão dos dados disponíveis.

O IC é calculado

### qwen2.5:1.5b +RAG
- **Score:** 79% (38/48 keywords)
- **Tempo total:** 134.4s
- **Chars:** 16181

**P:** O que é a Lei 13.303/2016 e qual seu principal objeto?
**Score:** 50% (3/6 kw) · 3.2s
**R:** Lei 13.303/2016 é o Estatuto Jurídico das Estatais (empresas públicas e sociedades de economia mista). Seu principal objeto é regulamentar a exploração de atividade econômica pelo Estado, estabelecendo regras de governança, licitações e contratos.

**P:** Qual o regime de licitação aplicável às empresas estatais segundo a Lei 13.303/2016?
**Score:** 67% (4/6 kw) · 8.6s
**R:** O regime de licitação aplicável às empresas estatais, conforme a Lei 13.303/2016, é o seguinte:

- As estatais devem realizar LICITAÇÃO PÚBLICA para contratos com terceiros (Art. 28).
- Elas próprias elaboram REGULAMENTO PRÓPRIO de licitações, aprovado pelo conselho de administração (Art. 29), obser

**P:** Cite três princípios da administração pública previstos no caput do Art. 37 da CF.
**Score:** 100% (5/5 kw) · 50.5s
**R:** Princípios da administração pública previstos no caput do Art. 37 da CF são:

1. Legalidade: Diretriz que implica a observância das normas legais, regulamentadas e estabelecidas pelo Poder Público.

2. Impessoalidade: Princípio que garante o exercício da função pública sem influência pessoal ou inte

**P:** O que é a transição energética e quais os principais desafios para o Brasil?
**Score:** 57% (4/7 kw) · 50.7s
**R:** A transição energética é um processo que visa mudar a matriz energética do país para reduzir o uso de combustíveis fósseis e aumentar a dependência de fontes renováveis como energia solar, hidroeletricidade, biomassa e eólica. Este processo tem como objetivo principal:

1. **Redução das emissões de 

**P:** Qual a diferença entre empresa pública e sociedade de economia mista?
**Score:** 100% (7/7 kw) · 3.5s
**R:** EMPRESA PÚBLICA: capital INTEGRALMENTE PÚBLICO (100% do Estado).
SOCIEDADE DE ECONOMIA MISTA: capital com MAIORIA de ações com direito a voto sob CONTROLE PÚBLICO (admite capital PRIVADO minoritário). Ambas têm personalidade jurídica de direito privado e criação autorizada por lei.

**P:** Explique o que é a Lei 9.478/1997 (Lei do Petróleo) e sua importância.
**Score:** 100% (9/9 kw) · 9.3s
**R:** A Lei 9.478/1997 (Lei do Petróleo) é uma legislação brasileira que instituiu a Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP), autarquia reguladora da indústria petrolífera no país. Fundada em 1997, a ANP tem como principal objetivo garantir o controle e fiscalização das atividade

**P:** O que é o IC (Índice de Consistência) nos estudos?
**Score:** 75% (6/8 kw) · 8.7s
**R:** O Índice de Consistência (IC) é um método utilizado para medir a regularidade e consistência dos estudos realizados por uma pessoa em relação à semana inteira. Este índice é calculado através da fórmula: 

\[ \text{IC} = \frac{\text{dias com estudo na semana}}{7} \]

O IC é um indicador que mede a r

## Metodologia

- 7 perguntas sobre legislação Petrobras, CF, transição energética
- Cada pergunta tem keywords esperadas (n-gramas)
- Score = proporção de keywords encontradas na resposta (case-insensitive)
- RAG injeta `[TEXTO_DA_LEI]` com artigos reais no prompt
- Modelo: timeout 180s, max_tokens 1024
