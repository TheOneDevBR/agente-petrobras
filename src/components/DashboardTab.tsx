import React, { useState, useEffect } from 'react';
import { 
  Flame, 
  Target, 
  TrendingUp, 
  ShieldCheck, 
  Play, 
  Pause, 
  SkipForward, 
  Clock, 
  AlertTriangle,
  Award,
  CheckCircle2,
  ListTodo
} from 'lucide-react';
import { PerfilCandidato, FaseEstudo } from '../types';

interface DashboardTabProps {
  perfil: PerfilCandidato;
  onSalvarPerfil: (novoPerfil: PerfilCandidato) => void;
}

interface StepProtocol {
  name: string;
  duration: number; // in minutes
  desc: string;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({
  perfil,
  onSalvarPerfil
}) => {
  // Timer State
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [timeLeft, setTimeLeft] = useState(5 * 60); // 5 minutes initial
  const [timerRunning, setTimerRunning] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);
  const [dailyGoal, setDailyGoal] = useState('');
  const [achievement, setAchievement] = useState('');
  const [sessionCompleted, setSessionCompleted] = useState(false);

  const protocolSteps: StepProtocol[] = [
    { name: 'ABERTURA', duration: 5, desc: 'Defina a meta da sessão em 1 frase com critério de sucesso. Anote seu foco.' },
    { name: 'AQUISIÇÃO', duration: 50, desc: 'Leitura ativa com anotação SQ3R. Questione e sintetize ativamente.' },
    { name: 'PAUSA ATIVA', duration: 10, desc: 'Sem telas! Caminhe, beba água ou respire profundamente.' },
    { name: 'RETRIEVAL PRACTICE', duration: 20, desc: 'Folha em branco! Escreva ou desenhe tudo que consolidou de memória.' },
    { name: 'ANKI', duration: 15, desc: 'Revise seus flashcards ativos e crie 5-10 novos cards sobre o tema de hoje.' },
    { name: 'QUESTÕES', duration: 30, desc: 'Resolva de 10 a 15 questões CESGRANRIO. Prática deliberada dos erros.' },
    { name: 'ENCERRAMENTO', duration: 5, desc: 'Avalie: meta atingida? Registre sua conquista e programe amanhã.' }
  ];

  // Sync initial timer duration when changing steps
  useEffect(() => {
    setTimeLeft(protocolSteps[currentStepIndex].duration * 60);
  }, [currentStepIndex]);

  // Timer Tick Hook
  useEffect(() => {
    let interval: any = null;
    if (timerRunning && timeLeft > 0) {
      interval = setInterval(() => {
        setTimeLeft(prev => prev - 1);
      }, 1000);
    } else if (timeLeft === 0 && timerRunning) {
      setTimerRunning(false);
      // Play a beep sound or notify
      alert(`Etapa ${protocolSteps[currentStepIndex].name} finalizada!`);
      handleNextStep();
    }
    return () => clearInterval(interval);
  }, [timerRunning, timeLeft]);

  const handleStartSession = () => {
    if (!dailyGoal.trim()) {
      alert("Escreva sua meta operacional antes de iniciar!");
      return;
    }
    setSessionActive(true);
    setCurrentStepIndex(0);
    setTimerRunning(true);
  };

  const handleNextStep = () => {
    if (currentStepIndex < protocolSteps.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
      setTimerRunning(true);
    } else {
      // Final da sessão
      setSessionRunningComplete();
    }
  };

  const setSessionRunningComplete = () => {
    setTimerRunning(false);
    setSessionActive(false);
    setSessionCompleted(true);
  };

  const handleSalvarSessao = () => {
    // Adiciona as horas estudadas
    const totalHorasSessao = protocolSteps.reduce((acc, step) => acc + step.duration, 0) / 60; // 135 min = 2.25h
    const hoje = new Date().toISOString().split('T')[0];
    const ultimaVitoria = perfil.estado_psicológico_e_motivacional.última_vitória;
    const jaSessaoHoje = ultimaVitoria?.data === hoje;
    const novoStreak = jaSessaoHoje
      ? perfil.estado_psicológico_e_motivacional.streak_dias_consecutivos
      : perfil.estado_psicológico_e_motivacional.streak_dias_consecutivos + 1;

    const novoPerfil: PerfilCandidato = {
      ...perfil,
      horas_estudadas_acumuladas: Math.round((perfil.horas_estudadas_acumuladas + totalHorasSessao) * 10) / 10,
      estado_psicológico_e_motivacional: {
        ...perfil.estado_psicológico_e_motivacional,
        streak_dias_consecutivos: novoStreak,
        maior_streak_histórico: Math.max(
          perfil.estado_psicológico_e_motivacional.maior_streak_histórico,
          novoStreak
        ),
        última_vitória: {
          data: hoje,
          descrição: `Sessão Completa: ${dailyGoal}`
        }
      }
    };

    onSalvarPerfil(novoPerfil);
    setSessionCompleted(false);
    setDailyGoal('');
    setAchievement('');
    alert("Sessão registrada com sucesso no seu modelo de candidato! Streak atualizado.");
  };

  // Time formatter
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Calculations for graphs and status colors
  const gap = perfil.meta_e_calibração.gap_atual_para_meta;
  const statusColor = gap >= 0 ? 'var(--color-primary)' : gap >= -10 ? 'var(--color-warning)' : 'var(--color-error)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* SECTION HEADER CARDS */}
      <div className="grid-4">
        {/* PROJEÇÃO DE NOTA */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>PROJEÇÃO DE NOTA</span>
            <TrendingUp size={16} />
          </div>
          <div>
            <h2 style={{ fontSize: '2rem', fontWeight: 800 }}>{perfil.projeção_de_nota_atual}%</h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Meta Operacional: <strong>{perfil.meta_e_calibração.meta_operacional_de_acerto}%</strong>
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem', color: statusColor, marginTop: '0.25rem' }}>
            <span style={{ fontWeight: 700 }}>
              {gap >= 0 ? `+${gap}pp` : `${gap}pp`}
            </span>
            <span>em relação à meta de aprovação</span>
          </div>
        </div>

        {/* PROBABILIDADE DE APROVAÇÃO */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>PROBABILIDADE DE APROVAÇÃO</span>
            <ShieldCheck size={16} />
          </div>
          <div>
            <h2 style={{ fontSize: '2rem', fontWeight: 800 }}>
              {perfil.meta_e_calibração.probabilidade_estimada_aprovação}%
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Baseado no corte histórico e consistência
            </p>
          </div>
          <div style={{ marginTop: '0.25rem' }}>
            <span className="badge" style={{
              backgroundColor: perfil.meta_e_calibração.probabilidade_estimada_aprovação >= 70 ? 'rgba(16, 185, 129, 0.15)' : perfil.meta_e_calibração.probabilidade_estimada_aprovação >= 40 ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              color: perfil.meta_e_calibração.probabilidade_estimada_aprovação >= 70 ? '#6ee7b7' : perfil.meta_e_calibração.probabilidade_estimada_aprovação >= 40 ? '#fde047' : '#fca5a5'
            }}>
              {perfil.meta_e_calibração.probabilidade_estimada_aprovação >= 70 ? 'ALTA PROJEÇÃO' : perfil.meta_e_calibração.probabilidade_estimada_aprovação >= 40 ? 'MÉDIA PROJEÇÃO' : 'CRÍTICO / REVISAR'}
            </span>
          </div>
        </div>

        {/* DIAS ATÉ A PROVA */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>DIAS ATÉ A PROVA</span>
            <Clock size={16} />
          </div>
          <div>
            <h2 style={{ fontSize: '2rem', fontWeight: 800 }}>{perfil.total_dias_até_prova} dias</h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Data estimada: <strong>{perfil.data_prova_confirmada}</strong>
            </p>
          </div>
          <div style={{ marginTop: '0.25rem' }}>
            <span className="badge badge-yellow">Fase: {perfil.fase_atual}</span>
          </div>
        </div>

        {/* STREAK ATIVO */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>DIAS CONSECUTIVOS (STREAK)</span>
            <Flame size={16} />
          </div>
          <div>
            <h2 style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--color-warning)' }}>
              {perfil.estado_psicológico_e_motivacional.streak_dias_consecutivos} dias
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Maior streak histórico: <strong>{perfil.estado_psicológico_e_motivacional.maior_streak_histórico} dias</strong>
            </p>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Horas Acumuladas: <strong>{perfil.horas_estudadas_acumuladas}h</strong>
          </div>
        </div>
      </div>

      {/* CORE WORKSPACE: TIMER & INTERACTIVE PROTOCOLS */}
      <div className="grid-2">
        {/* TIMER DE SESSÃO DIÁRIA */}
        <div className="panel" style={{ borderLeft: '4px solid var(--color-primary)' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Target style={{ color: 'var(--color-primary)' }} />
            <span>Sessão de Estudo Diária — Protocolo de Elite</span>
          </h3>

          {!sessionActive && !sessionCompleted && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Fase de estudos ativa: <strong>{perfil.fase_atual}</strong>.
                Inicie uma sessão estruturada de alta intensidade (<strong>2h15 de foco planejado</strong>) seguindo o protocolo cognitivo ideal.
              </p>
              
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Qual é a sua meta operacional de hoje?</label>
                <input 
                  type="text" 
                  value={dailyGoal}
                  onChange={(e) => setDailyGoal(e.target.value)}
                  placeholder="Ex: Dominar Regência Verbal e fazer 10 questões." 
                  className="form-input" 
                />
              </div>

              <button onClick={handleStartSession} className="btn btn-primary active-pulse" style={{ alignSelf: 'flex-start' }}>
                <Play size={16} /> Iniciar Sessão Diária
              </button>
            </div>
          )}

          {sessionActive && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', alignItems: 'center', textAlign: 'center', padding: '1rem 0' }}>
              <div>
                <span className="badge badge-green" style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}>
                  {protocolSteps[currentStepIndex].name}
                </span>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                  Etapa {currentStepIndex + 1} de {protocolSteps.length}
                </p>
              </div>

              <div style={{ fontSize: '4.5rem', fontWeight: 800, fontFamily: 'monospace', color: 'var(--text-primary)', lineHeight: 1 }}>
                {formatTime(timeLeft)}
              </div>

              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', maxWidth: '400px', minHeight: '48px' }}>
                {protocolSteps[currentStepIndex].desc}
              </p>

              {/* CONTROLS */}
              <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
                <button 
                  onClick={() => setTimerRunning(!timerRunning)} 
                  className="btn btn-secondary"
                  title={timerRunning ? 'Pausar Timer' : 'Retomar Timer'}
                >
                  {timerRunning ? <Pause size={18} /> : <Play size={18} />}
                </button>
                <button 
                  onClick={handleNextStep} 
                  className="btn btn-secondary"
                  title="Pular para Próxima Etapa"
                >
                  <SkipForward size={18} />
                </button>
                <button 
                  onClick={setSessionRunningComplete} 
                  className="btn btn-danger btn-sm"
                  style={{ alignSelf: 'center' }}
                >
                  Encerrar Sessão
                </button>
              </div>

              {/* PROTOCOL STEPS PIPES */}
              <div style={{ display: 'flex', width: '100%', gap: '0.25rem', marginTop: '1rem' }}>
                {protocolSteps.map((step, idx) => (
                  <div 
                    key={step.name} 
                    style={{ 
                      flex: 1, 
                      height: '4px', 
                      backgroundColor: idx === currentStepIndex ? 'var(--color-primary)' : idx < currentStepIndex ? 'var(--bg-active)' : 'var(--border-color)',
                      borderRadius: '2px',
                      boxShadow: idx === currentStepIndex ? '0 0 8px var(--color-primary)' : 'none'
                    }} 
                  />
                ))}
              </div>
            </div>
          )}

          {sessionCompleted && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary)' }}>
                <CheckCircle2 size={24} />
                <h4 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Parabéns, Sessão Concluída!</h4>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Você concluiu o protocolo diário planejado. Registre seu desempenho no modelo do candidato.
              </p>
              
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">O que você conseguiu consolidar/conquistar hoje?</label>
                <textarea 
                  value={achievement}
                  onChange={(e) => setAchievement(e.target.value)}
                  placeholder="Ex: Acertei 80% das questões de crase, mas errei uma por desatenção." 
                  className="form-input"
                  style={{ minHeight: '80px', resize: 'vertical' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button onClick={handleSalvarSessao} className="btn btn-primary">
                  Registrar Sessão (+2.25h estudadas)
                </button>
                <button onClick={() => setSessionCompleted(false)} className="btn btn-secondary">
                  Descartar / Cancelar
                </button>
              </div>
            </div>
          )}
        </div>

        {/* RECOMENDAÇÕES DO COACH & CIENTISTA */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Award style={{ color: 'var(--color-warning)' }} />
            <span>Prescrição Clínica & Padrões</span>
          </h3>

          <div style={{ background: 'var(--bg-hover)', padding: '1rem', borderRadius: 'var(--radius-md)', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>NARRATIVA DE IDENTIDADE ATIVA</p>
            <p style={{ fontStyle: 'italic', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
              "{perfil.estado_psicológico_e_motivacional.narrativa_de_identidade_ativa}"
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600 }}>STATUS DE SAÚDE COMPORTAMENTAL:</h4>
            
            {/* Erro Dominante Alerta */}
            {perfil.erro_dominante_histórico !== 'NENHUM' ? (
              <div className="alert alert-warning" style={{ margin: 0, padding: '0.75rem' }}>
                <AlertTriangle size={18} style={{ flexShrink: 0 }} />
                <div>
                  <h5 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'inherit' }}>Padrão de Erro Detectado: {perfil.erro_dominante_histórico}</h5>
                  <p style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: 'inherit' }}>
                    {perfil.erro_dominante_histórico === 'C' && 'Seus erros são majoritariamente por falta de Conteúdo. Ação: Revise a teoria e crie mais flashcards.'}
                    {perfil.erro_dominante_histórico === 'A' && 'Erros dominados por falta de Atenção. Ação: Use o protocolo de leitura e sublinhe palavras-chave no enunciado.'}
                    {perfil.erro_dominante_histórico === 'B' && 'Erros por pegadinhas da Banca. Ação: Aumente a resolução de provas anteriores sem focar em novas teorias.'}
                    {perfil.erro_dominante_histórico === 'T' && 'Erros por estresse de Tempo. Ação: Pratique simulados cronometrados pulando questões complexas de imediato.'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="alert alert-success" style={{ margin: 0, padding: '0.75rem' }}>
                <CheckCircle2 size={18} style={{ flexShrink: 0 }} />
                <div>
                  <h5 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'inherit' }}>Distribuição de Erros Equilibrada</h5>
                  <p style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: 'inherit' }}>
                    Nenhum erro supera 30% de dominância. Continue resolvendo questões de forma balanceada.
                  </p>
                </div>
              </div>
            )}

            {/* Ansiedade alerta */}
            {perfil.estado_psicológico_e_motivacional.nível_ansiedade === 'ALTO' || perfil.estado_psicológico_e_motivacional.nível_ansiedade === 'CRÍTICO' ? (
              <div className="alert alert-error" style={{ margin: 0, padding: '0.75rem' }}>
                <AlertTriangle size={18} style={{ flexShrink: 0 }} />
                <div>
                  <h5 style={{ fontSize: '0.8rem', fontWeight: 700, color: 'inherit' }}>Nível de Ansiedade {perfil.estado_psicológico_e_motivacional.nível_ansiedade}</h5>
                  <p style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: 'inherit' }}>
                    [COACH] Ansiedade elevada bloqueia o raciocínio matemático. Protocolo: Insira 20min de exercício aeróbico antes da sessão e durma pelo menos 7.5h.
                  </p>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};
