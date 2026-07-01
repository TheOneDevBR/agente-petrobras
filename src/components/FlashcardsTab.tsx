import React, { useState, useEffect } from 'react';
import { 
  Brain, 
  Plus, 
  RotateCw, 
  Check, 
  FolderPlus,
  Trash2
} from 'lucide-react';
import { Flashcard } from '../types';
import { obterFlashcardsLocal, salvarFlashcardsLocal, DISCIPLINAS_PADRAO } from '../utils/storage';

const FLASHCARDS_INICIAIS: Flashcard[] = [
  {
    id: 'fc-1',
    disciplina: 'Conhecimentos Petrobras e Setor de O&G',
    tema: 'Cadeia de Valor',
    pergunta: 'Diferencie Upstream, Midstream e Downstream.',
    resposta: 'Upstream: Exploração e Produção (E&P) de óleo/gás bruto.\nMidstream: Logística, transporte (dutos, navios) e armazenamento.\nDownstream: Refino do petróleo, processamento do gás, distribuição e venda de derivados.',
    dataProximaRevisao: new Date().toISOString().split('T')[0],
    intervaloDias: 1,
    repeticoes: 0,
    facilidade: 2.5
  },
  {
    id: 'fc-2',
    disciplina: 'Legislação e Governança',
    tema: 'Lei das Estatais (Lei 13.303/2016)',
    pergunta: 'Em quais circunstâncias a licitação pode ser dispensada em uma estatal para obras/serviços comuns de engenharia?',
    resposta: 'Conforme art. 29, I: Licitação dispensável para valores de até R$ 100.000,00 (valor original atualizado por regulamentos vigentes, hoje em cerca de R$ 119k), desde que não se refira a parcelamento de uma mesma obra/serviço.',
    dataProximaRevisao: new Date().toISOString().split('T')[0],
    intervaloDias: 1,
    repeticoes: 0,
    facilidade: 2.5
  },
  {
    id: 'fc-3',
    disciplina: 'Raciocínio Lógico / Matemática',
    tema: 'Equivalências Lógicas',
    pergunta: 'Qual é a equivalência lógica clássica da condicional (P → Q)?',
    resposta: 'A condicional P → Q possui duas equivalências fundamentais:\n1. Disjunção equivalente: ~P ∨ Q (Nega a primeira OU mantém a segunda).\n2. Contrapositiva: ~Q → ~P (Inverte negando ambas).',
    dataProximaRevisao: new Date().toISOString().split('T')[0],
    intervaloDias: 1,
    repeticoes: 0,
    facilidade: 2.5
  },
  {
    id: 'fc-4',
    disciplina: 'Língua Portuguesa',
    tema: 'Regência Verbal',
    pergunta: 'Qual a regência correta de "aspirar" no sentido de desejar um cargo?',
    resposta: 'É transitivo indireto com preposição "a".\nExemplo: "Ele aspira AO cargo de engenheiro." (Aspirar o cargo significaria inalar fumaça/ar).',
    dataProximaRevisao: new Date().toISOString().split('T')[0],
    intervaloDias: 1,
    repeticoes: 0,
    facilidade: 2.5
  },
  {
    id: 'fc-6',
    disciplina: 'Conhecimentos Específicos',
    tema: 'Modelagem de Dados',
    pergunta: 'O que é normalização de banco de dados? Explique as três primeiras formas normais (1FN, 2FN e 3FN).',
    resposta: 'Normalização é o processo de organizar dados para reduzir redundância e dependências.\n1FN: Cada célula contém um valor atômico (não grupos repetitivos).\n2FN: Estar na 1FN e cada atributo não-chave depender COMPLETAMENTE da chave primária (dependência total).\n3FN: Estar na 2FN e não haver dependência transitiva (atributo não-chave depender de outro atributo não-chave).',
    dataProximaRevisao: new Date().toISOString().split('T')[0],
    intervaloDias: 1,
    repeticoes: 0,
    facilidade: 2.5
  },
  {
    id: 'fc-7',
    disciplina: 'Conhecimentos Petrobras e Setor de O&G',
    tema: 'Tipos de Plataformas',
    pergunta: 'Quais são os principais tipos de plataformas de produção offshore e suas aplicações?',
    resposta: '1. FPSO (Floating Production Storage and Offloading): Navio que produz, armazena e descarrega óleo. Ideal para águas profundas/ultraprofundas (Pré-Sal).\n2. Plataforma Fixa (Jacket): Estrutura de aço apoiada no leito marinho. Limitada a lâminas d\'água de até ~300m.\n3. Semi-submersível: Flutuante ancorada, usada em águas médias a profundas (até ~2000m).\n4. TLP (Tension Leg Platform): Plataforma estaiada com tendões tensionados, estável para poços de produção.',
    dataProximaRevisao: new Date().toISOString().split('T')[0],
    intervaloDias: 1,
    repeticoes: 0,
    facilidade: 2.5
  },
  {
    id: 'fc-8',
    disciplina: 'Língua Portuguesa',
    tema: 'Crase',
    pergunta: 'Em quais casos o uso da crase é obrigatório? Dê exemplos.',
    resposta: 'A crase (à) é a fusão da preposição "a" com o artigo feminino "a(s)". Casos obrigatórios:\n1. Antes de palavras femininas: "Vou à reunião".\n2. Na indicação de horas: "Chegarei às 14h".\n3. Em locuções adverbiais femininas: "à noite", "à vontade", "à esquerda".\n4. Antes de "aquele/aquela": "Refiro-me àquela proposta".\nNÃO se usa crase: antes de verbos, pronomes pessoais, palavras masculinas, ou "a" no singular diante de plural.',
    dataProximaRevisao: new Date().toISOString().split('T')[0],
    intervaloDias: 1,
    repeticoes: 0,
    facilidade: 2.5
  },
  {
    id: 'fc-9',
    disciplina: 'Raciocínio Lógico / Matemática',
    tema: 'Probabilidade - Eventos Independentes',
    pergunta: 'Como se calcula a probabilidade da UNIÃO de dois eventos (P(A ∪ B))?',
    resposta: 'P(A ∪ B) = P(A) + P(B) - P(A ∩ B).\nSe os eventos forem mutuamente exclusivos (A ∩ B = ∅), então P(A ∪ B) = P(A) + P(B).\nSe forem independentes, P(A ∩ B) = P(A) × P(B).\nExemplo: Em uma urna com 3 bolas azuis e 5 verdes, P(azul ∪ verde) = 3/8 + 5/8 = 1 (eventos complementares).',
    dataProximaRevisao: new Date().toISOString().split('T')[0],
    intervaloDias: 1,
    repeticoes: 0,
    facilidade: 2.5
  },
  {
    id: 'fc-10',
    disciplina: 'Legislação e Governança',
    tema: 'Licitações - Modalidades',
    pergunta: 'Quais são as modalidades de licitação previstas na Lei 14.133/2021 (Nova Lei de Licitações) e seus limites de valor?',
    resposta: 'A Lei 14.133/2021 prevê as seguintes modalidades:\n1. Pregão: Aquisição de bens e serviços comuns (qualquer valor).\n2. Concorrência: Qualquer valor, especialmente obras/serviços de engenharia.\n3. Concurso: Trabalho técnico, científico ou artístico.\n4. Leilão: Venda de bens.\n5. Diálogo Competitivo: Contratações complexas/inovadoras.\nLimites para dispensa (art. 75): Obras até R$ 111.564,36; demais até R$ 55.782,18 (valores do Dec. 11.871/2023).',
    dataProximaRevisao: new Date().toISOString().split('T')[0],
    intervaloDias: 1,
    repeticoes: 0,
    facilidade: 2.5
  },
  {
    id: 'fc-5',
    disciplina: 'Legislação e Governança',
    tema: 'LGPD (Lei 13.709/2018)',
    pergunta: 'Quais são os 3 principais papéis descritos na LGPD para o tratamento de dados pessoais?',
    resposta: '1. Controlador: Quem toma as decisões sobre o tratamento.\n2. Operador: Quem realiza o tratamento em nome do controlador.\n3. Encarregado (DPO): Canal de comunicação entre o controlador, os titulares e a ANPD.',
    dataProximaRevisao: new Date().toISOString().split('T')[0],
    intervaloDias: 1,
    repeticoes: 0,
    facilidade: 2.5
  }
];

export const FlashcardsTab: React.FC = () => {
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [flipped, setFlipped] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  
  // Active review session state
  const [dueCards, setDueCards] = useState<Flashcard[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Form State
  const [newDisc, setNewDisc] = useState(DISCIPLINAS_PADRAO[0]);
  const [newTema, setNewTema] = useState('');
  const [newPreg, setNewPreg] = useState('');
  const [newResp, setNewResp] = useState('');

  // Load cards on mount
  useEffect(() => {
    let localCards = obterFlashcardsLocal();
    if (localCards.length === 0) {
      localCards = FLASHCARDS_INICIAIS;
      salvarFlashcardsLocal(localCards);
    }
    setCards(localCards);
    filterDueCards(localCards);
  }, []);

  const filterDueCards = (allCards: Flashcard[]) => {
    const hoje = new Date().toISOString().split('T')[0];
    const due = allCards.filter(c => c.dataProximaRevisao <= hoje);
    setDueCards(due);
    setCurrentIndex(0);
    setFlipped(false);
  };

  const handleCreateCard = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTema.trim() || !newPreg.trim() || !newResp.trim()) return;

    const newCard: Flashcard = {
      id: 'fc-' + Date.now(),
      disciplina: newDisc,
      tema: newTema,
      pergunta: newPreg,
      resposta: newResp,
      dataProximaRevisao: new Date().toISOString().split('T')[0],
      intervaloDias: 1,
      repeticoes: 0,
      facilidade: 2.5
    };

    const updated = [...cards, newCard];
    setCards(updated);
    salvarFlashcardsLocal(updated);
    filterDueCards(updated);
    
    // Reset form
    setNewTema('');
    setNewPreg('');
    setNewResp('');
    setShowAddForm(false);
    alert("Card criado com sucesso no seu baralho!");
  };

  const handleReview = (grau: 'facil' | 'medio' | 'dificil') => {
    if (dueCards.length === 0) return;
    const activeCard = dueCards[currentIndex];

    // Simulação do algoritmo SM-2 simplificado para agendamento
    let novoIntervalo = activeCard.intervaloDias;
    let novaFacilidade = activeCard.facilidade;
    let novasRep = activeCard.repeticoes + 1;

    if (grau === 'facil') {
      novoIntervalo = activeCard.repeticoes === 0 ? 1 : activeCard.repeticoes === 1 ? 4 : Math.round(activeCard.intervaloDias * activeCard.facilidade * 1.5);
      novaFacilidade = Math.min(3.0, activeCard.facilidade + 0.15);
    } else if (grau === 'medio') {
      novoIntervalo = activeCard.repeticoes === 0 ? 1 : activeCard.repeticoes === 1 ? 2 : Math.round(activeCard.intervaloDias * activeCard.facilidade);
    } else {
      // Dificil / errou
      novoIntervalo = 1;
      novasRep = 0;
      novaFacilidade = Math.max(1.3, activeCard.facilidade - 0.2);
    }

    const proximaData = new Date();
    proximaData.setDate(proximaData.getDate() + novoIntervalo);
    const dataString = proximaData.toISOString().split('T')[0];

    // Atualiza a lista geral
    const updatedCards = cards.map(c => {
      if (c.id === activeCard.id) {
        return {
          ...c,
          intervaloDias: novoIntervalo,
          facilidade: novaFacilidade,
          repeticoes: novasRep,
          dataProximaRevisao: dataString
        };
      }
      return c;
    });

    setCards(updatedCards);
    salvarFlashcardsLocal(updatedCards);

    // Avança na sessão
    setFlipped(false);
    if (currentIndex < dueCards.length - 1) {
      setCurrentIndex(prev => prev + 1);
    } else {
      // Fim da sessão
      filterDueCards(updatedCards);
      alert("Você revisou todos os flashcards programados para hoje!");
    }
  };

  const handleDeleteCard = (id: string) => {
    if (!window.confirm("Deseja mesmo excluir este card?")) return;
    const updated = cards.filter(c => c.id !== id);
    setCards(updated);
    salvarFlashcardsLocal(updated);
    filterDueCards(updated);
  };

  return (
    <div className="grid-3" style={{ gridTemplateColumns: '1fr 320px' }}>
      
      {/* SEÇÃO PRINCIPAL: REVISÃO DE CARDS */}
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', minHeight: '400px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Brain style={{ color: 'var(--color-primary)' }} />
            <span>Repetição Espaçada (Micro-Anki)</span>
          </h3>
          <span className="badge badge-yellow">
            {dueCards.length} cards para hoje
          </span>
        </div>

        {dueCards.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', alignItems: 'center', width: '100%' }}>
            
            {/* CARROUSEL / CONTADOR */}
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Revisando card {currentIndex + 1} de {dueCards.length}
            </span>

            {/* CARD INTERATIVO */}
            <div 
              onClick={() => setFlipped(!flipped)}
              style={{
                width: '100%',
                maxWidth: '500px',
                minHeight: '220px',
                perspective: '1000px',
                cursor: 'pointer'
              }}
            >
              <div 
                style={{
                  width: '100%',
                  height: '100%',
                  position: 'relative',
                  transformStyle: 'preserve-3d',
                  transition: 'transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
                  transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
                }}
              >
                {/* FRENTE */}
                <div style={{
                  position: 'absolute',
                  width: '100%',
                  height: '100%',
                  backfaceVisibility: 'hidden',
                  backgroundColor: 'rgba(15,23,42,0.9)',
                  border: '2px solid var(--border-color)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '1.5rem',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  boxShadow: 'var(--shadow-lg)'
                }}>
                  <div>
                    <span className="badge badge-green" style={{ fontSize: '0.75rem' }}>
                      {dueCards[currentIndex].disciplina}
                    </span>
                    <span className="badge badge-yellow" style={{ marginLeft: '0.5rem', fontSize: '0.75rem' }}>
                      {dueCards[currentIndex].tema}
                    </span>
                  </div>
                  
                  <p style={{ fontSize: '1.1rem', textAlign: 'center', fontWeight: 600, margin: '1rem 0' }}>
                    {dueCards[currentIndex].pergunta}
                  </p>

                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    <RotateCw size={12} /> Clique para revelar resposta
                  </div>
                </div>

                {/* VERSO */}
                <div style={{
                  position: 'absolute',
                  width: '100%',
                  height: '100%',
                  backfaceVisibility: 'hidden',
                  backgroundColor: 'rgba(15,23,42,0.9)',
                  border: '2px dashed var(--color-primary)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '1.5rem',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  transform: 'rotateY(180deg)',
                  boxShadow: 'var(--shadow-glow)'
                }}>
                  <div>
                    <span className="badge badge-green" style={{ fontSize: '0.75rem' }}>Gabarito / Resposta</span>
                  </div>
                  
                  <p style={{ fontSize: '0.95rem', textAlign: 'center', color: 'var(--text-primary)', whiteSpace: 'pre-line', margin: '1rem 0', lineHeight: 1.5 }}>
                    {dueCards[currentIndex].resposta}
                  </p>

                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: 'var(--color-primary)' }}>
                    Como foi responder a este card?
                  </div>
                </div>

              </div>
            </div>

            {/* AVALIAÇÃO DE RESPOSTAS */}
            {flipped && (
              <div style={{ display: 'flex', gap: '0.75rem', width: '100%', maxWidth: '500px', justifyContent: 'center' }}>
                <button onClick={() => handleReview('dificil')} className="btn btn-danger btn-sm" style={{ flex: 1 }}>
                  🔴 Errei / Difícil
                </button>
                <button onClick={() => handleReview('medio')} className="btn btn-secondary btn-sm" style={{ flex: 1 }}>
                  🟡 Médio / Razoável
                </button>
                <button onClick={() => handleReview('facil')} className="btn btn-primary btn-sm" style={{ flex: 1 }}>
                  🟢 Acertei / Fácil
                </button>
              </div>
            )}

          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem 0', textAlign: 'center', gap: '0.5rem' }}>
            <Check size={40} style={{ color: 'var(--color-primary)' }} />
            <h4 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Zero Cards Pendentes!</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '360px' }}>
              Seu baralho está em dia. Adicione novos flashcards a partir dos seus resumos na barra lateral.
            </p>
          </div>
        )}
      </div>

      {/* PAINEL LATERAL: ADICIONAR CARD */}
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: 'fit-content' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FolderPlus size={16} />
            <span>Criar Flashcard</span>
          </h3>
          <button 
            onClick={() => setShowAddForm(!showAddForm)}
            className="btn btn-secondary btn-sm"
            style={{ padding: '0.25rem 0.5rem' }}
          >
            {showAddForm ? 'Fechar' : <Plus size={14} />}
          </button>
        </div>

        {showAddForm ? (
          <form onSubmit={handleCreateCard} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Disciplina</label>
              <select 
                value={newDisc}
                onChange={e => setNewDisc(e.target.value)}
                className="form-input"
              >
                {DISCIPLINAS_PADRAO.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
            
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Tema / Conteúdo</label>
              <input 
                required 
                value={newTema}
                onChange={e => setNewTema(e.target.value)}
                placeholder="Ex: Artigo 13" 
                className="form-input" 
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Pergunta (Frente)</label>
              <textarea 
                required 
                value={newPreg}
                onChange={e => setNewPreg(e.target.value)}
                placeholder="Qual o critério de..." 
                className="form-input"
                style={{ minHeight: '60px', resize: 'vertical' }}
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Resposta (Verso)</label>
              <textarea 
                required 
                value={newResp}
                onChange={e => setNewResp(e.target.value)}
                placeholder="O critério define que..." 
                className="form-input"
                style={{ minHeight: '80px', resize: 'vertical' }}
              />
            </div>

            <button type="submit" className="btn btn-primary btn-sm">Criar Card</button>
          </form>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '350px', overflowY: 'auto' }}>
            <label className="form-label">Cards Ativos no Baralho ({cards.length}):</label>
            {cards.map((card) => (
              <div 
                key={card.id} 
                style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  padding: '0.5rem', 
                  background: 'rgba(15,23,42,0.3)', 
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)'
                }}
              >
                <div style={{ overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis', maxWidth: '200px' }}>
                  <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0, textOverflow: 'ellipsis', overflow: 'hidden' }}>
                    Q: {card.pergunta}
                  </p>
                  <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)' }}>
                    {card.tema}
                  </span>
                </div>
                <button 
                  onClick={() => handleDeleteCard(card.id)}
                  className="btn btn-secondary btn-sm"
                  style={{ border: 'none', background: 'transparent', padding: '0.25rem' }}
                  title="Deletar card"
                >
                  <Trash2 size={12} style={{ color: 'var(--color-error)' }} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
};
