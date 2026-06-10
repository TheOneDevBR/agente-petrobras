import React, { useState, useEffect, useRef } from 'react';
import { 
  Send, 
  Play, 
  Award, 
  AlertTriangle, 
  CheckCircle2, 
  HelpCircle, 
  RefreshCw,
  BookOpen,
  Calendar,
  Zap,
  Check,
  ChevronRight
} from 'lucide-react';
import { PerfilCandidato, MensagemChat, Questao, FaseEstudo, NivelAnsiedade, TipoBloqueio } from '../types';
import { bancoDeQuestoes } from '../data/questions';
import { 
  CARGO_BENCHMARKS, 
  ESTADO_INICIAL_PERFIL, 
  calcularViabilidade, 
  calcularMetricasFinais 
} from '../utils/storage';

interface OnboardingChatTabProps {
  perfil: PerfilCandidato | null;
  onSalvarPerfil: (novoPerfil: PerfilCandidato) => void;
  geminiApiKey: string;
}

type OnboardingStep = 
  | 'INTRO'
  | 'CARGO' 
  | 'ESTRUTURA' 
  | 'HORAS'
  | 'RESTRICOES'
  | 'HISTORICO'
  | 'AUTOAVALIACAO'
  | 'QUIZ_AVISO'
  | 'QUIZ'
  | 'SABOTADORES'
  | 'NARRATIVA'
  | 'RELATORIO';

export const OnboardingChatTab: React.FC<OnboardingChatTabProps> = ({
  perfil,
  onSalvarPerfil,
  geminiApiKey
}) => {
  const [step, setStep] = useState<OnboardingStep>('INTRO');
  const [messages, setMessages] = useState<MensagemChat[]>([]);
  const [inputValue, setInputValue] = useState('');
  
  // Form State for Onboarding
  const [formData, setFormData] = useState<Partial<PerfilCandidato>>({
    ...ESTADO_INICIAL_PERFIL
  });

  // Self-assessment temp storage
  const [autoScores, setAutoScores] = useState<Record<string, number>>({
    'Língua Portuguesa': 5,
    'Raciocínio Lógico / Matemática': 5,
    'Legislação e Governança': 5,
    'Conhecimentos Petrobras e Setor de O&G': 5,
    'Conhecimentos Específicos': 5,
  });

  // Quiz State
  const [quizQuestions, setQuizQuestions] = useState<Questao[]>([]);
  const [currentQuizIndex, setCurrentQuizIndex] = useState(0);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, 'A'|'B'|'C'|'D'|'E'>>({});
  const [quizStartTime, setQuizStartTime] = useState<number>(0);
  const [quizDurations, setQuizDurations] = useState<number[]>([]);

  // Blocker & Narrative details
  const [sabotador, setSabotador] = useState('procrastinação');
  const [narrativaInput, setNarrativaInput] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initial welcome message
  useEffect(() => {
    if (perfil && perfil.cargo_alvo) {
      setStep('RELATORIO');
      setFormData(perfil);
      addAgentMessage(`╔══════════════════════════════════════════════════════════════════════╗
║              AGENTE PETROBRAS — SISTEMA PROMPT v4.0                  ║
║   Preparador Autônomo de Máximo Desempenho · CESGRANRIO · 2025–2026  ║
║           Arquitetura: Estrategista + Coach + Cientista              ║
╚══════════════════════════════════════════════════════════════════════╝

Bem-vindo de volta ao centro de operações táticas. Seu diagnóstico está ativo. Você pode rodar análises preditivas, rever suas lacunas ou consultar estratégias de estudo.`);
    } else {
      setStep('INTRO');
      const introMsg = `╔══════════════════════════════════════════════════════════════════════╗
║              AGENTE PETROBRAS — SISTEMA PROMPT v4.0                  ║
║   Preparador Autônomo de Máximo Desempenho · CESGRANRIO · 2025–2026  ║
║           Arquitetura: Estrategista + Coach + Cientista              ║
╚══════════════════════════════════════════════════════════════════════╝

Candidato, sou o **AgentePetrobras v4.0**.

Não sou um chatbot passivo ou um assistente de conversas vazias. Sou seu treinador de alto desempenho. Meu papel é diagnosticar seus bloqueios, planejar seus estudos com base em dados de provas e ajustar sua rota antes que o atraso vire fracasso.

Vamos iniciar o seu **Diagnóstico Inicial de Viabilidade e Nivelamento**. Responda com honestidade clínica.

Clique no botão abaixo para escolher o seu **cargo alvo**.`;
      addAgentMessage(introMsg);
    }
  }, [perfil]);

  const addAgentMessage = (text: string) => {
    setMessages(prev => [
      ...prev,
      {
        id: Date.now().toString() + Math.random().toString(),
        remetente: 'agent',
        texto: text,
        dataHora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  const addUserMessage = (text: string) => {
    setMessages(prev => [
      ...prev,
      {
        id: Date.now().toString() + Math.random().toString(),
        remetente: 'user',
        texto: text,
        dataHora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  // Onboarding flow steps
  const handleSelectCargo = (cargo: string) => {
    addUserMessage(`Quero estudar para o cargo de ${cargo}`);
    setFormData(prev => ({
      ...prev,
      cargo_alvo: cargo,
      nível_cargo: cargo === 'Técnico (nível médio)' ? 'Médio' : 'Superior'
    }));

    addAgentMessage(`[ESTRATEGISTA] Excelente escolha. O cargo de **${cargo}** possui nota de corte média histórica de **${CARGO_BENCHMARKS[cargo as keyof typeof CARGO_BENCHMARKS]?.corte}%** e nossa meta de segurança operacional é de **${CARGO_BENCHMARKS[cargo as keyof typeof CARGO_BENCHMARKS]?.meta}%**.

Qual é a sua **área de especialidade / engenharia** e sua **formação acadêmica**?`);
    setStep('ESTRUTURA');
  };

  const handleStructureSubmit = (area: string, formacao: string) => {
    if (!area.trim() || !formacao.trim()) return;
    addUserMessage(`Minha área é ${area} e minha formação é ${formacao}.`);
    setFormData(prev => ({
      ...prev,
      área: area,
      formação_acadêmica: formacao,
      domínios_de_expertise: [area]
    }));

    addAgentMessage(`[CIENTISTA] Registrado. Agora, vamos quantificar sua **disponibilidade real de horas líquidas**. Não use médias inflacionadas. Seja realista, descontando deslocamento, cansaço acumulado, refeições e família.

Quantas horas diárias reais você pode dedicar nos:
- Dias úteis (Segunda a Sexta)
- Sábados
- Domingos`);
    setStep('HORAS');
  };

  const handleHorasSubmit = (hUtil: number, hSab: number, hDom: number, diasProva: number) => {
    addUserMessage(`Posso estudar: ${hUtil}h/dia útil, ${hSab}h aos sábados, ${hDom}h aos domingos. Faltam aproximadamente ${diasProva} dias para a prova.`);
    
    // Calculo da data da prova
    const dataProva = new Date();
    dataProva.setDate(dataProva.getDate() + diasProva);
    const dataString = dataProva.toISOString().split('T')[0];

    setFormData(prev => ({
      ...prev,
      horas_dia_útil_reais: hUtil,
      horas_sábado_reais: hSab,
      horas_domingo_reais: hDom,
      total_dias_até_prova: diasProva,
      data_prova_confirmada: dataString
    }));

    addAgentMessage(`[COACH] Compreendido. A vida real impõe amarras. Você possui alguma **restrição estrutural** crítica?
- Trabalho em turno de revezamento?
- Filhos ou dependentes sob seus cuidados?
- Problemas de saúde ativos?
- Outro impedimento não negociável?`);
    setStep('RESTRICOES');
  };

  const handleRestricoesSubmit = (turno: boolean, filhos: boolean, saude: boolean, outro: string) => {
    addUserMessage(`Restrições: ${turno ? 'Trabalho por turnos. ' : ''}${filhos ? 'Tenho filhos sob meus cuidados. ' : ''}${saude ? 'Cuidados com saúde. ' : ''}${outro ? `Outros: ${outro}` : 'Nenhuma'}`);
    setFormData(prev => ({
      ...prev,
      restrições_estruturais: {
        trabalho_turno: turno,
        filhos,
        saúde: saude,
        outro
      }
    }));

    addAgentMessage(`[CIENTISTA] Gravado no modelo. Qual é o seu **histórico em concursos**?
1. Já fez provas da Petrobras anteriormente? (Se sim, qual ano, cargo e desempenho aproximado)
2. Já fez provas CESGRANRIO de outras estatais (BNDES, Transpetro, Liquigás, etc.)?
3. Quanto tempo estuda para concursos no total? O que funcionou e o que faturou você no passado?`);
    setStep('HISTORICO');
  };

  const handleHistoricoSubmit = (historicoText: string) => {
    addUserMessage(historicoText);
    
    addAgentMessage(`[ESTRATEGISTA] Perfeito. Agora faremos uma **autoavaliação de confiança**.
Para cada disciplina universal do edital abaixo, atribua uma nota de **0 a 10** sobre o quanto você se sente confiante para resolver uma prova hoje (0 = nulo, 10 = domínio completo).

1. Língua Portuguesa
2. Raciocínio Lógico / Matemática
3. Legislação e Governança (ex: Lei 13.303, Estatuto, Código de Conduta, LGPD)
4. Conhecimentos Petrobras e Setor de O&G
5. Conhecimentos Específicos do Cargo`);
    setStep('AUTOAVALIACAO');
  };

  const handleAutoavaliacaoSubmit = () => {
    addUserMessage(`Notas de Confiança:
- Português: ${autoScores['Língua Portuguesa']}/10
- Raciocínio Lógico: ${autoScores['Raciocínio Lógico / Matemática']}/10
- Legislação: ${autoScores['Legislação e Governança']}/10
- Petrobras: ${autoScores['Conhecimentos Petrobras e Setor de O&G']}/10
- Específicos: ${autoScores['Conhecimentos Específicos']}/10`);

    addAgentMessage(`⚠️ [CIENTISTA] **ALERTA DE VIÉS COGNITIVO**
Nossas estatísticas de preparação indicam que candidatos superestimam Português em média 2,5 pontos e subestimam RL/Matemática em cerca de 1,5 pontos. 

Para calibrar o seu mapa de lacunas com evidência real, **você iniciará agora um Quiz de Calibração com 5 questões reais/estilizadas CESGRANRIO** (1 de cada disciplina).

Prepare papel e caneta. Você terá cerca de 3,5 minutos por questão (conforme padrão de prova). 
Clique no botão abaixo para iniciar a calibração.`);
    setStep('QUIZ_AVISO');
  };

  const handleStartQuiz = () => {
    // Escolhe 5 questões: 1 de cada disciplina
    const selected: Questao[] = [];
    const disciplinas = [
      'Língua Portuguesa',
      'Raciocínio Lógico / Matemática',
      'Legislação e Governança',
      'Conhecimentos Petrobras e Setor de O&G',
      'Conhecimentos Específicos'
    ];

    disciplinas.forEach(d => {
      const q = bancoDeQuestoes.find(q => q.disciplina === d);
      if (q) selected.push(q);
    });

    setQuizQuestions(selected);
    setCurrentQuizIndex(0);
    setQuizAnswers({});
    setQuizStartTime(Date.now());
    setQuizDurations([]);
    
    addUserMessage("Iniciar Calibração de Prova.");
    addAgentMessage(`🚀 **Calibração Iniciada**. Responda às questões na tela. O tempo está sendo cronometrado.`);
    setStep('QUIZ');
  };

  const handleAnswerQuiz = (alternativa: 'A'|'B'|'C'|'D'|'E') => {
    const timeSpent = (Date.now() - quizStartTime) / 1000 / 60; // in minutes
    setQuizDurations(prev => [...prev, timeSpent]);
    
    const currentQuestion = quizQuestions[currentQuizIndex];
    setQuizAnswers(prev => ({
      ...prev,
      [currentQuestion.id]: alternativa
    }));

    if (currentQuizIndex < quizQuestions.length - 1) {
      setCurrentQuizIndex(prev => prev + 1);
      setQuizStartTime(Date.now());
    } else {
      // Final do Quiz
      addUserMessage("Quiz de calibração finalizado.");
      
      // Calcular acertos
      const todasRespostas = { ...quizAnswers, [currentQuestion.id]: alternativa };
      const novoHistorico: Record<string, any> = {};
      let totalAcertos = 0;

      quizQuestions.forEach((q, idx) => {
        const respostaDada = todasRespostas[q.id];
        const acertou = respostaDada === q.gabarito;
        if (acertou) totalAcertos++;

        const duracao = quizDurations[idx] || timeSpent;
        const acertoPct = acertou ? 100 : 0;
        
        novoHistorico[q.disciplina] = {
          baseline_diagnóstico: acertoPct,
          acerto_semana: [acertoPct],
          tendência: 'ESTÁVEL' as const,
          total_questões_resolvidas: 1,
          velocidade_média_minutos_por_questão: Math.round(duracao * 10) / 10
        };
      });

      // Se alguma disciplina não foi testada, joga o baseline
      Object.keys(autoScores).forEach(d => {
        if (!novoHistorico[d]) {
          const baseline = autoScores[d] * 10; // converte de 0-10 para %
          novoHistorico[d] = {
            baseline_diagnóstico: baseline,
            acerto_semana: [baseline],
            tendência: 'ESTÁVEL' as const,
            total_questões_resolvidas: 0,
            velocidade_média_minutos_por_questão: 3.5
          };
        }
      });

      setFormData(prev => ({
        ...prev,
        histórico_acerto_por_disciplina: novoHistorico,
        total_questões_resolvidas: 5
      }));

      addAgentMessage(`[CIENTISTA] Quiz de calibração concluído! Você acertou **${totalAcertos}/5** questões. 

Para fechar o diagnóstico, me informe:
1. Qual é o seu **maior sabotador atual** de estudos (procrastinação, perda de foco, ansiedade, falta de método)?
2. Descreva em uma frase qual a sua **narrativa pessoal** como candidato (ex: "tenho pouco tempo", "não consigo reter fórmulas", "estudo mas travo na hora da prova").`);
      setStep('SABOTADORES');
    }
  };

  const handleSabotadoresSubmit = (sab: string, narrativa: string) => {
    if (!narrativa.trim()) return;
    addUserMessage(`Meu maior sabotador é a ${sab}. Minha narrativa: "${narrativa}"`);
    
    // Configura os dados psicológicos
    const estadoPsi = {
      nível_ansiedade: (sab === 'ansiedade' ? 'ALTO' : 'MÉDIO') as NivelAnsiedade,
      tipo_bloqueio_atual: (sab === 'procrastinação' ? 'PROCRASTINAÇÃO' : sab === 'burnout' ? 'BURNOUT' : 'NENHUM') as TipoBloqueio,
      streak_dias_consecutivos: 1,
      maior_streak_histórico: 1,
      última_vitória: { data: new Date().toISOString().split('T')[0], descrição: 'Concluiu o Diagnóstico de Entrada' },
      semanas_consecutivas_de_queda: 0,
      narrativa_de_identidade_ativa: `Você não está tentando passar. Você está construindo, hoje, o profissional que a Petrobras aprova. Esta sessão é evidência disso.`
    };

    // Montando o perfil final provisório para cálculo
    let perfilTemp: PerfilCandidato = {
      ...ESTADO_INICIAL_PERFIL,
      ...formData,
      padrões_comportamentais_observados: {
        melhor_horário_produtivo_observado: 'Manhã',
        duração_foco_sustentável_real_minutos: 45,
        gatilhos_procrastinação_identificados: [sab],
        padrão_de_abandono_histórico: { tipo: sab, momento_do_ciclo: 'Fase 1' },
        intervenções_que_funcionaram: ['Timer de 45min', 'Retrieval Practice'],
        intervenções_que_não_funcionaram: ['Estudos de 3h seguidas']
      },
      estado_psicológico_e_motivacional: estadoPsi
    } as PerfilCandidato;

    // Calcular via utilitários
    perfilTemp = calcularMetricasFinais(perfilTemp);

    setFormData(perfilTemp);
    
    addAgentMessage(`[COACH] Perfil calibrado e salvo! A sua Âncora de Identidade é: 
*"${perfilTemp.estado_psicológico_e_motivacional.narrativa_de_identidade_ativa}"*

O seu plano tático estratégico está gerado. Clique abaixo para ver o relatório completo e ativar seu painel.`);
    setStep('RELATORIO');
  };

  const handleAtivarPlano = () => {
    onSalvarPerfil(formData as PerfilCandidato);
    addAgentMessage(`[ESTRATEGISTA] Painel de Controle de Alto Desempenho ativado com sucesso! Navegue pelas abas na barra lateral para ver suas lacunas, banco de questões e iniciar sua sessão diária.`);
  };

  // RENDER INTERACTION AREA
  const renderInteractiveArea = () => {
    switch (step) {
      case 'INTRO':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%' }}>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Selecione seu cargo alvo:</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.5rem' }}>
              {Object.keys(CARGO_BENCHMARKS).map((cargo) => (
                <button
                  key={cargo}
                  onClick={() => handleSelectCargo(cargo)}
                  className="btn btn-secondary btn-sm"
                  style={{ textAlign: 'left', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <span>{cargo}</span>
                  <ChevronRight size={14} />
                </button>
              ))}
            </div>
          </div>
        );

      case 'ESTRUTURA':
        return (
          <form 
            onSubmit={(e) => {
              e.preventDefault();
              const area = (e.currentTarget.elements.namedItem('area') as HTMLInputElement).value;
              const formacao = (e.currentTarget.elements.namedItem('formacao') as HTMLInputElement).value;
              handleStructureSubmit(area, formacao);
            }}
            style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}
          >
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Área / Especialidade (ex: Petróleo, Elétrica, TI)</label>
                <input required name="area" placeholder="Ex: Software, Mecânica" className="form-input" />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Sua Formação Acadêmica</label>
                <input required name="formacao" placeholder="Ex: Engenheiro de Controle, Analista" className="form-input" />
              </div>
            </div>
            <button type="submit" className="btn btn-primary btn-sm align-self-end">Prosseguir</button>
          </form>
        );

      case 'HORAS':
        return (
          <form 
            onSubmit={(e) => {
              e.preventDefault();
              const hUtil = parseFloat((e.currentTarget.elements.namedItem('hUtil') as HTMLInputElement).value);
              const hSab = parseFloat((e.currentTarget.elements.namedItem('hSab') as HTMLInputElement).value);
              const hDom = parseFloat((e.currentTarget.elements.namedItem('hDom') as HTMLInputElement).value);
              const dias = parseInt((e.currentTarget.elements.namedItem('dias') as HTMLInputElement).value);
              handleHorasSubmit(hUtil, hSab, hDom, dias);
            }}
            style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}
          >
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">H. Dia Útil</label>
                <input type="number" step="0.5" defaultValue="3" required name="hUtil" className="form-input" />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">H. Sábados</label>
                <input type="number" step="0.5" defaultValue="6" required name="hSab" className="form-input" />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">H. Domingos</label>
                <input type="number" step="0.5" defaultValue="4" required name="hDom" className="form-input" />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Dias até Prova</label>
                <input type="number" defaultValue="90" required name="dias" className="form-input" />
              </div>
            </div>
            <button type="submit" className="btn btn-primary btn-sm">Prosseguir</button>
          </form>
        );

      case 'RESTRICOES':
        return (
          <form 
            onSubmit={(e) => {
              e.preventDefault();
              const target = e.currentTarget;
              const turno = (target.elements.namedItem('turno') as HTMLInputElement).checked;
              const filhos = (target.elements.namedItem('filhos') as HTMLInputElement).checked;
              const saude = (target.elements.namedItem('saude') as HTMLInputElement).checked;
              const outro = (target.elements.namedItem('outro') as HTMLInputElement).value;
              handleRestricoesSubmit(turno, filhos, saude, outro);
            }}
            style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}
          >
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', margin: '0.5rem 0' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="checkbox" name="turno" style={{ accentColor: 'var(--color-primary)' }} />
                <span>Trabalho em turnos</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="checkbox" name="filhos" style={{ accentColor: 'var(--color-primary)' }} />
                <span>Filhos / Cuidados Familiares</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input type="checkbox" name="saude" style={{ accentColor: 'var(--color-primary)' }} />
                <span>Cuidados de Saúde</span>
              </label>
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Outras restrições / Notas</label>
              <input name="outro" placeholder="Ex: Viagens constantes a trabalho..." className="form-input" />
            </div>
            <button type="submit" className="btn btn-primary btn-sm">Confirmar Restrições</button>
          </form>
        );

      case 'HISTORICO':
        return (
          <div style={{ display: 'flex', gap: '0.5rem', width: '100%' }}>
            <input 
              type="text" 
              placeholder="Descreva seu histórico de estudos..." 
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              className="chat-input"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleHistoricoSubmit(inputValue);
                  setInputValue('');
                }
              }}
            />
            <button 
              onClick={() => {
                handleHistoricoSubmit(inputValue);
                setInputValue('');
              }} 
              className="btn btn-primary btn-sm"
              disabled={!inputValue.trim()}
            >
              <Send size={16} />
            </button>
          </div>
        );

      case 'AUTOAVALIACAO':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%', padding: '0.5rem', background: 'var(--bg-hover)', borderRadius: 'var(--radius-md)' }}>
            <p style={{ fontSize: '0.85rem', fontWeight: 600 }}>De 0 a 10, qual sua confiança em:</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '0.5rem' }}>
              {Object.keys(autoScores).map((disc) => (
                <div key={disc} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{disc}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input 
                      type="range" 
                      min="0" 
                      max="10" 
                      value={autoScores[disc]}
                      onChange={(e) => setAutoScores(prev => ({ ...prev, [disc]: parseInt(e.target.value) }))}
                      style={{ accentColor: 'var(--color-primary)', width: '120px' }}
                    />
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, width: '20px' }}>{autoScores[disc]}</span>
                  </div>
                </div>
              ))}
            </div>
            <button onClick={handleAutoavaliacaoSubmit} className="btn btn-primary btn-sm">Confirmar Autoavaliação</button>
          </div>
        );

      case 'QUIZ_AVISO':
        return (
          <button onClick={handleStartQuiz} className="btn btn-primary active-pulse" style={{ width: '100%' }}>
            <Play size={18} /> Iniciar Quiz de Calibração (5 Questões)
          </button>
        );

      case 'QUIZ':
        const currentQuestion = quizQuestions[currentQuizIndex];
        if (!currentQuestion) return null;
        return (
          <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1rem', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              <span className="badge badge-green">{currentQuestion.disciplina}</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Questão {currentQuizIndex + 1} de 5</span>
            </div>
            {currentQuestion.contexto && (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', background: 'var(--bg-main)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--text-muted)' }}>
                {currentQuestion.contexto}
              </p>
            )}
            <p style={{ fontSize: '0.9rem', fontWeight: 500 }}>{currentQuestion.enunciado}</p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {(['A','B','C','D','E'] as const).map((letra) => (
                <button
                  key={letra}
                  onClick={() => handleAnswerQuiz(letra)}
                  className="btn btn-secondary btn-sm"
                  style={{ textAlign: 'left', display: 'flex', gap: '0.5rem', alignItems: 'flex-start', padding: '0.65rem' }}
                >
                  <strong style={{ color: 'var(--color-primary)' }}>{letra})</strong>
                  <span style={{ fontSize: '0.85rem' }}>{currentQuestion.alternativas[letra]}</span>
                </button>
              ))}
            </div>
          </div>
        );

      case 'SABOTADORES':
        return (
          <form 
            onSubmit={(e) => {
              e.preventDefault();
              handleSabotadoresSubmit(sabotador, narrativaInput);
            }}
            style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}
          >
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Selecione seu maior sabotador atual:</label>
              <select 
                value={sabotador}
                onChange={(e) => setSabotador(e.target.value)}
                className="form-input"
              >
                <option value="procrastinação">Procrastinação (deixar para amanhã)</option>
                <option value="perda_foco">Perda de foco e distração com redes/materiais</option>
                <option value="ansiedade">Ansiedade exagerada que trava a resolução</option>
                <option value="burnout">Fadiga extrema por excesso de carga</option>
                <option value="falta_metodo">Estudo passivo (apenas ler sem praticar)</option>
              </select>
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Sua narrativa mental de candidato:</label>
              <input 
                required 
                value={narrativaInput}
                onChange={(e) => setNarrativaInput(e.target.value)}
                placeholder="Ex: Não tenho tempo suficiente por causa do trabalho." 
                className="form-input" 
              />
            </div>
            <button type="submit" className="btn btn-primary btn-sm">Gerar Diagnóstico Final</button>
          </form>
        );

      case 'RELATORIO':
        if (!formData.meta_e_calibração) return null;
        
        // Cálculo local de viabilidade
        const viabil = calcularViabilidade(
          formData.total_dias_até_prova ?? 90,
          formData.horas_dia_útil_reais ?? 3,
          formData.horas_sábado_reais ?? 6,
          formData.horas_domingo_reais ?? 4,
          (formData.total_questões_resolvidas ?? 0) > 0 ? 'base_parcial' : 'base_zero'
        );

        return (
          <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="panel" style={{ border: '1px solid var(--color-primary)' }}>
              <h3 style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Award /> DIAGNÓSTICO ESTRATÉGICO FINAL
              </h3>
              
              <div className="grid-2" style={{ margin: '1rem 0' }}>
                <div>
                  <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>① Equação de Viabilidade</h4>
                  <p style={{ fontSize: '0.85rem', margin: '0.25rem 0' }}>
                    Horas Disponíveis: <strong>{viabil.horasDisponiveis}h</strong> | Requeridas: <strong>{viabil.horasNecessarias}h</strong>
                  </p>
                  <p style={{ fontSize: '0.85rem', margin: '0.25rem 0' }}>
                    Saldo de Horas: <strong style={{ color: viabil.saldo >= 0 ? 'var(--color-primary)' : 'var(--color-error)' }}>{viabil.saldo >= 0 ? `+${viabil.saldo}h` : `${viabil.saldo}h`}</strong>
                  </p>
                  <p style={{ fontSize: '0.85rem' }}>
                    Veredicto: <span className="badge badge-green" style={{
                      backgroundColor: viabil.veredicto === 'CONFORTÁVEL' ? 'rgba(16,185,129,0.15)' : viabil.veredicto === 'AJUSTADO' ? 'rgba(59,130,246,0.15)' : 'rgba(239,68,68,0.15)',
                      color: viabil.veredicto === 'CONFORTÁVEL' ? '#6ee7b7' : viabil.veredicto === 'AJUSTADO' ? '#93c5fd' : '#fca5a5'
                    }}>{viabil.veredicto}</span>
                  </p>
                </div>

                <div>
                  <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>② Projeção de Nota Operacional</h4>
                  <p style={{ fontSize: '0.85rem', margin: '0.25rem 0' }}>
                    Nota Projetada: <strong>{formData.projeção_de_nota_atual}%</strong>
                  </p>
                  <p style={{ fontSize: '0.85rem', margin: '0.25rem 0' }}>
                    Corte de Segurança: <strong>{formData.meta_e_calibração.meta_operacional_de_acerto}%</strong>
                  </p>
                  <p style={{ fontSize: '0.85rem' }}>
                    Probabilidade Estimada: <strong style={{ color: 'var(--color-warning)' }}>{formData.meta_e_calibração.probabilidade_estimada_aprovação}%</strong>
                  </p>
                </div>
              </div>

              <div style={{ margin: '1rem 0' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>③ Âncora de Identidade Ativa</h4>
                <p style={{ fontStyle: 'italic', fontSize: '0.85rem', color: 'var(--color-primary-light)', background: 'var(--color-primary-glow)', padding: '0.5rem', borderRadius: 'var(--radius-sm)' }}>
                  "{formData.estado_psicológico_e_motivacional?.narrativa_de_identidade_ativa}"
                </p>
              </div>

              <button onClick={handleAtivarPlano} className="btn btn-primary active-pulse" style={{ width: '100%' }}>
                <Check /> ATIVAR PLANO DE ESTUDOS AGORA
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: '500px' }}>
      <div className="section-title" style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
        <Zap style={{ color: 'var(--color-primary)' }} />
        <span>AgentePetrobras Coach Chat v4.0</span>
      </div>

      <div className="chat-messages" style={{ overflowY: 'auto', padding: '1rem', height: '350px' }}>
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={`chat-message-row ${msg.remetente}`}
            style={{ marginBottom: '1rem' }}
          >
            <div className={`chat-bubble ${msg.remetente}`}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginBottom: '0.25rem', textAlign: msg.remetente === 'user' ? 'right' : 'left' }}>
                {msg.remetente === 'user' ? 'Candidato' : 'AgentePetrobras'} • {msg.dataHora}
              </div>
              <div style={{ whiteSpace: 'pre-line' }}>{msg.texto}</div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area" style={{ background: 'transparent', border: 'none', borderTop: '1px solid var(--border-color)', padding: '1rem 0 0 0' }}>
        {renderInteractiveArea()}
      </div>
    </div>
  );
};
