import React, { useState, useMemo } from 'react';
import { 
  Check, 
  X, 
  HelpCircle, 
  BookOpen, 
  AlertTriangle,
  Eye,
  EyeOff,
  Filter,
  ChevronLeft,
  ChevronRight,
  Search
} from 'lucide-react';
import { PerfilCandidato, Questao, ErroTipo } from '../types';
import { bancoDeQuestoes } from '../data/questions';

const ITENS_POR_PAGINA = 20;

interface QuestionBankTabProps {
  perfil: PerfilCandidato;
  onSalvarPerfil: (novoPerfil: PerfilCandidato) => void;
}

export const QuestionBankTab: React.FC<QuestionBankTabProps> = ({
  perfil,
  onSalvarPerfil
}) => {
  const [selectedDisciplina, setSelectedDisciplina] = useState<string>('Todas');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [pagina, setPagina] = useState(0);
  const [selectedQuestionId, setSelectedQuestionId] = useState<string>(bancoDeQuestoes[0]?.id ?? '');
  
  // Interactive Strike-through alternatives
  const [struckAlternatives, setStruckAlternatives] = useState<Record<string, boolean>>({});
  
  // Answer status
  const [userAnswer, setUserAnswer] = useState<'A'|'B'|'C'|'D'|'E' | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [isAnswered, setIsAnswered] = useState(false);
  const [errorClassified, setErrorClassified] = useState<boolean>(false);

  // Filter, search, pagination
  const filtradas = useMemo(() => {
    let qs = selectedDisciplina === 'Todas'
      ? bancoDeQuestoes
      : bancoDeQuestoes.filter(q => q.disciplina === selectedDisciplina);
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      qs = qs.filter(q => q.enunciado.toLowerCase().includes(term) || q.tema.toLowerCase().includes(term));
    }
    return qs;
  }, [selectedDisciplina, searchTerm]);

  const totalPaginas = Math.max(1, Math.ceil(filtradas.length / ITENS_POR_PAGINA));
  const paginaSegura = Math.min(pagina, totalPaginas - 1);
  const paginaAtual = pagina !== paginaSegura ? (setPagina(paginaSegura), paginaSegura) : pagina;
  const paginadas = filtradas.slice(paginaAtual * ITENS_POR_PAGINA, (paginaAtual + 1) * ITENS_POR_PAGINA);

  const activeQuestion = filtradas.find(q => q.id === selectedQuestionId) || filtradas[0] || bancoDeQuestoes[0];

  const handleSelectQuestion = (id: string) => {
    setSelectedQuestionId(id);
    setUserAnswer(null);
    setShowExplanation(false);
    setIsAnswered(false);
    setStruckAlternatives({});
    setErrorClassified(false);
  };

  const handleStrikeAlternative = (letra: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setStruckAlternatives(prev => ({
      ...prev,
      [letra]: !prev[letra]
    }));
  };

  const handleResponder = (letra: 'A'|'B'|'C'|'D'|'E') => {
    if (isAnswered) return;
    setUserAnswer(letra);
    setIsAnswered(true);
    setShowExplanation(true);
    
    // Se o usuário acertar, atualiza perfil imediatamente
    if (letra === activeQuestion.gabarito) {
      salvarQuestaoResolvida(true, null);
    }
  };

  const handleClassificarErro = (tipoErro: ErroTipo) => {
    salvarQuestaoResolvida(false, tipoErro);
    setErrorClassified(true);
    alert(`Erro categorizado como [${tipoErro}] com sucesso. Seu plano foi calibrado!`);
  };

  const salvarQuestaoResolvida = (acertou: boolean, tipoErro: ErroTipo | null) => {
    const disc = activeQuestion.disciplina;
    const discData = perfil.histórico_acerto_por_disciplina[disc] || {
      baseline_diagnóstico: 50,
      acerto_semana: [50],
      tendência: 'ESTÁVEL',
      total_questões_resolvidas: 0,
      velocidade_média_minutos_por_questão: 3.5
    };

    // Atualiza acertos
    const totalResolvidasDisc = discData.total_questões_resolvidas + 1;
    const acertosRecentes = [...discData.acerto_semana];
    
    // Adiciona o novo acerto como média móvel
    const ultimoAcerto = acertosRecentes[acertosRecentes.length - 1] || 50;
    const novoValor = acertou 
      ? Math.min(100, Math.round(((ultimoAcerto * 4) + 100) / 5)) 
      : Math.max(0, Math.round(((ultimoAcerto * 4) + 0) / 5));
    acertosRecentes.push(novoValor);

    // Limita histórico a 10 registros
    if (acertosRecentes.length > 10) acertosRecentes.shift();

    // Calcula tendência
    let tendencia = discData.tendência;
    if (acertosRecentes.length >= 3) {
      const penultimo = acertosRecentes[acertosRecentes.length - 2];
      const ultimo = acertosRecentes[acertosRecentes.length - 1];
      tendencia = ultimo > penultimo ? 'SUBINDO' : ultimo < penultimo ? 'CAINDO' : 'ESTÁVEL';
    }

    const historicoAtualizado = {
      ...perfil.histórico_acerto_por_disciplina,
      [disc]: {
        ...discData,
        total_questões_resolvidas: totalResolvidasDisc,
        acerto_semana: acertosRecentes,
        tendência: tendencia
      }
    };

    // Atualiza Distribuição de Erros se errou
    const distErros = { ...perfil.distribuição_de_erros };
    if (!acertou && tipoErro) {
      const err = distErros[tipoErro];
      // Incrementa e recalcula proporções
      const totaisErros: Record<ErroTipo, number> = { C: 0, A: 0, B: 0, T: 0 };
      
      // Conta proporcionalmente
      Object.keys(distErros).forEach(k => {
        const key = k as ErroTipo;
        totaisErros[key] = key === tipoErro ? (distErros[key].porcentagem + 10) : Math.max(2, distErros[key].porcentagem - 3.3);
      });

      // Normaliza para somar 100%
      const totalSoma = Object.values(totaisErros).reduce((a, b) => a + b, 0);
      Object.keys(distErros).forEach(k => {
        const key = k as ErroTipo;
        const discAfetadas = distErros[key].disciplinas_mais_afetadas;
        if (!discAfetadas.includes(disc)) discAfetadas.push(disc);
        distErros[key] = {
          porcentagem: Math.round((totaisErros[key] / totalSoma) * 100),
          disciplinas_mais_afetadas: discAfetadas.slice(-3) // mantém as últimas 3
        };
      });
    }

    // Salva perfil final
    const novoPerfil: PerfilCandidato = {
      ...perfil,
      total_questões_resolvidas: perfil.total_questões_resolvidas + 1,
      horas_de_questões_acumuladas: Math.round((perfil.horas_de_questões_acumuladas + 0.05) * 100) / 100, // +3 min
      histórico_acerto_por_disciplina: historicoAtualizado,
      distribuição_de_erros: distErros
    };

    onSalvarPerfil(novoPerfil);
  };

  const disciplinasUnicas = useMemo(
    () => ['Todas', ...Array.from(new Set(bancoDeQuestoes.map(q => q.disciplina)))],
    [],
  );

  return (
    <div className="grid-3" style={{ gridTemplateColumns: '300px 1fr' }}>
      
      {/* SIDEBAR DE SELEÇÃO DE QUESTÕES */}
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: 'fit-content' }}>
        <h3 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={18} />
          <span>Filtros & Navegação</span>
        </h3>

        {/* Busca textual */}
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">Buscar:</label>
          <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
            <Search size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setPagina(0); }}
              placeholder="Pergunta ou tema..."
              className="form-input"
              style={{ flex: 1 }}
            />
          </div>
        </div>

        {/* Filtro por disciplina */}
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">Filtrar por Disciplina:</label>
          <select 
            value={selectedDisciplina} 
            onChange={(e) => {
              setSelectedDisciplina(e.target.value);
              setPagina(0);
              setSearchTerm('');
              const filtered = e.target.value === 'Todas' 
                ? bancoDeQuestoes 
                : bancoDeQuestoes.filter(q => q.disciplina === e.target.value);
              if (filtered.length > 0) handleSelectQuestion(filtered[0].id);
            }} 
            className="form-input"
          >
            {disciplinasUnicas.map(d => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>

        {/* Paginação */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.3rem' }}>
          <button
            onClick={() => setPagina(p => Math.max(0, p - 1))}
            disabled={paginaAtual === 0}
            className="btn btn-secondary btn-sm"
            style={{ padding: '0.3rem 0.5rem' }}
          >
            <ChevronLeft size={14} />
          </button>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {paginaAtual * ITENS_POR_PAGINA + 1}–{Math.min((paginaAtual + 1) * ITENS_POR_PAGINA, filtradas.length)} de {filtradas.length}
          </span>
          <button
            onClick={() => setPagina(p => Math.min(totalPaginas - 1, p + 1))}
            disabled={paginaAtual >= totalPaginas - 1}
            className="btn btn-secondary btn-sm"
            style={{ padding: '0.3rem 0.5rem' }}
          >
            <ChevronRight size={14} />
          </button>
        </div>

        {/* Lista de Questões */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: '320px', overflowY: 'auto', marginTop: '0.3rem' }}>
          <label className="form-label">Lista de Questões:</label>
          {paginadas.map((q, idx) => (
            <button
              key={q.id}
              onClick={() => handleSelectQuestion(q.id)}
              className={`menu-item ${activeQuestion.id === q.id ? 'active' : ''}`}
              style={{ padding: '0.5rem 0.75rem', fontSize: '0.8rem', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '0.2rem' }}
            >
              <span style={{ fontWeight: 700 }}>Q{paginaAtual * ITENS_POR_PAGINA + idx + 1}: {q.tema}</span>
              <span style={{ fontSize: '0.7rem', opacity: 0.8, textOverflow: 'ellipsis', whiteSpace: 'nowrap', width: '100%', overflow: 'hidden' }}>
                {q.enunciado}
              </span>
            </button>
          ))}
          {paginadas.length === 0 && (
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1rem 0', textAlign: 'center' }}>
              Nenhuma questão encontrada.
            </span>
          )}
        </div>
      </div>

      {/* ÁREA DE EXIBIÇÃO DA QUESTÃO ATIVA */}
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* CABEÇALHO DA QUESTÃO */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
          <div>
            <span className="badge badge-green" style={{ marginRight: '0.5rem' }}>{activeQuestion.disciplina}</span>
            <span className="badge badge-yellow">{activeQuestion.tema}</span>
          </div>
          {activeQuestion.armadilhaCode && (
            <span className="badge badge-red" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <AlertTriangle size={12} /> {activeQuestion.armadilhaCode}
            </span>
          )}
        </div>

        {/* CONTEXTO */}
        {activeQuestion.contexto && (
          <div style={{ 
            padding: '1rem', 
            background: 'rgba(2,6,23,0.5)', 
            borderLeft: '4px solid var(--text-muted)', 
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.9rem',
            lineHeight: 1.6,
            color: 'var(--text-secondary)'
          }}>
            <p style={{ fontWeight: 600, fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Contexto Base:</p>
            {activeQuestion.contexto}
          </div>
        )}

        {/* ENUNCIADO */}
        <div style={{ fontSize: '1.05rem', fontWeight: 500, lineHeight: 1.6 }}>
          {activeQuestion.enunciado}
        </div>

        {/* INSTRUÇÃO PROTOCOLO LEITURA */}
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <HelpCircle size={14} />
          <span>Dica: Use o botão de riscar (✖) nas alternativas para exercitar a eliminação ativa.</span>
        </div>

        {/* ALTERNATIVAS */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {(['A', 'B', 'C', 'D', 'E'] as const).map((letra) => {
            const isStruck = struckAlternatives[letra];
            const isSelected = userAnswer === letra;
            const isGabarito = activeQuestion.gabarito === letra;
            
            // Definição de cores
            let btnClass = 'btn-secondary';
            let outlineStyle: React.CSSProperties = {};

            if (isAnswered) {
              if (isGabarito) {
                outlineStyle = { border: '2px solid var(--color-primary)', backgroundColor: 'var(--color-primary-glow)' };
              } else if (isSelected) {
                outlineStyle = { border: '2px solid var(--color-error)', backgroundColor: 'var(--color-error-glow)' };
              }
            }

            return (
              <div 
                key={letra} 
                className="btn"
                style={{ 
                  textAlign: 'left', 
                  display: 'flex', 
                  justifyContent: 'space-between',
                  alignItems: 'center', 
                  padding: '0.85rem 1rem', 
                  cursor: isAnswered ? 'default' : 'pointer',
                  opacity: isStruck && !isSelected ? 0.35 : 1,
                  textDecoration: isStruck ? 'line-through' : 'none',
                  backgroundColor: isSelected ? 'var(--bg-active)' : 'rgba(15, 23, 42, 0.4)',
                  borderColor: isSelected ? 'var(--color-primary)' : 'var(--border-color)',
                  ...outlineStyle
                }}
                onClick={() => !isAnswered && handleResponder(letra)}
              >
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', flex: 1 }}>
                  <strong style={{ color: 'var(--color-primary)', fontSize: '0.95rem' }}>{letra})</strong>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                    {activeQuestion.alternativas[letra]}
                  </span>
                </div>
                
                {/* AÇÕES (RISCAR OU FEEDBACK ICON) */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: '1rem' }} onClick={e => e.stopPropagation()}>
                  {!isAnswered && (
                    <button 
                      onClick={(e) => handleStrikeAlternative(letra, e)}
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '0.25rem 0.4rem', border: 'none', background: 'transparent' }}
                      title="Eliminar esta alternativa"
                    >
                      <X size={14} style={{ color: 'var(--text-muted)' }} />
                    </button>
                  )}
                  {isAnswered && isGabarito && <Check size={18} style={{ color: 'var(--color-primary)' }} />}
                  {isAnswered && isSelected && !isGabarito && <X size={18} style={{ color: 'var(--color-error)' }} />}
                </div>
              </div>
            );
          })}
        </div>

        {/* INTERACTION AREA ONCE ANSWERED */}
        {isAnswered && (
          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            
            {/* CORRECT / WRONG BANNER */}
            {userAnswer === activeQuestion.gabarito ? (
              <div className="alert alert-success" style={{ margin: 0 }}>
                <Check size={20} />
                <div>
                  <h4 style={{ color: 'inherit', fontWeight: 700, fontSize: '0.9rem' }}>RESPOSTA CORRETA</h4>
                  <p style={{ fontSize: '0.8rem', marginTop: '0.15rem' }}>Parabéns. Você neutralizou a armadilha da banca e registrou o acerto em seu modelo.</p>
                </div>
              </div>
            ) : (
              <div className="alert alert-error" style={{ margin: 0 }}>
                <X size={20} />
                <div style={{ width: '100%' }}>
                  <h4 style={{ color: 'inherit', fontWeight: 700, fontSize: '0.9rem' }}>RESPOSTA INCORRETA</h4>
                  <p style={{ fontSize: '0.8rem', marginTop: '0.15rem', marginBottom: '0.75rem' }}>Você errou esta questão. Classifique o seu erro para atualizar suas métricas de estudo:</p>
                  
                  {!errorClassified ? (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <button onClick={() => handleClassificarErro('C')} className="btn btn-secondary btn-sm" style={{ borderColor: 'var(--color-error)' }}>
                        <strong>[C]</strong> Conteúdo (Não sabia)
                      </button>
                      <button onClick={() => handleClassificarErro('A')} className="btn btn-secondary btn-sm" style={{ borderColor: 'var(--color-error)' }}>
                        <strong>[A]</strong> Atenção (Li errado)
                      </button>
                      <button onClick={() => handleClassificarErro('B')} className="btn btn-secondary btn-sm" style={{ borderColor: 'var(--color-error)' }}>
                        <strong>[B]</strong> Banca (Pegadinha)
                      </button>
                      <button onClick={() => handleClassificarErro('T')} className="btn btn-secondary btn-sm" style={{ borderColor: 'var(--color-error)' }}>
                        <strong>[T]</strong> Tempo (Falta de tempo)
                      </button>
                    </div>
                  ) : (
                    <span className="badge badge-green">Erro Categorizado e Salvo</span>
                  )}
                </div>
              </div>
            )}

            {/* EXPLICACAO */}
            <div className="panel" style={{ background: 'var(--bg-main)', border: '1px solid var(--border-color)', margin: '0.5rem 0 0 0', padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--color-primary)' }}>Explicação Analítica (Scientist Decoded)</h4>
                <button 
                  onClick={() => setShowExplanation(!showExplanation)}
                  className="btn btn-secondary btn-sm"
                  style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', padding: '0.25rem 0.5rem' }}
                >
                  {showExplanation ? <EyeOff size={14} /> : <Eye size={14} />}
                  <span>{showExplanation ? 'Ocultar' : 'Mostrar'}</span>
                </button>
              </div>
              
              {showExplanation && (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', whiteSpace: 'pre-line', lineHeight: 1.6 }}>
                  {activeQuestion.explicacao}
                </p>
              )}
            </div>

            <button 
              onClick={() => {
                const currentIndex = filtradas.findIndex(q => q.id === activeQuestion.id);
                if (currentIndex < filtradas.length - 1) {
                  handleSelectQuestion(filtradas[currentIndex + 1].id);
                } else {
                  handleSelectQuestion(filtradas[0].id);
                }
              }} 
              className="btn btn-primary"
              style={{ alignSelf: 'flex-end' }}
            >
              Avançar para Próxima Questão
            </button>

          </div>
        )}

      </div>

    </div>
  );
};
