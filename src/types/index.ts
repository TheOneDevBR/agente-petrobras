export type FaseEstudo = 'FUNDAÇÃO' | 'DOMÍNIO' | 'CONSOLIDAÇÃO' | 'SPRINT' | 'EMERGÊNCIA';

export type TendenciaAcerto = 'SUBINDO' | 'ESTÁVEL' | 'CAINDO';

export type NivelAnsiedade = 'BAIXO' | 'MÉDIO' | 'ALTO' | 'CRÍTICO';

export type TipoBloqueio = 'PROCRASTINAÇÃO' | 'BURNOUT' | 'MEDO' | 'NENHUM';

export interface DisciplinaPerf {
  baseline_diagnóstico: number; // baseline % from quiz or input
  acerto_semana: number[]; // history of weekly averages (%)
  tendência: TendenciaAcerto;
  total_questões_resolvidas: number;
  velocidade_média_minutos_por_questão: number;
}

export type ErroTipo = 'C' | 'A' | 'B' | 'T'; // Content, Attention, Bank, Time

export interface ErroDist {
  porcentagem: number;
  disciplinas_mais_afetadas: string[];
}

export interface Simulado {
  id: string;
  data: string;
  acerto: number; // percentage
  disciplinas: string[];
  tempo_total_minutos: number;
}

export interface PadroesComportamentais {
  melhor_horário_produtivo_observado: string;
  duração_foco_sustentável_real_minutos: number;
  gatilhos_procrastinação_identificados: string[];
  padrão_de_abandono_histórico: {
    tipo: string;
    momento_do_ciclo: string;
  };
  intervenções_que_funcionaram: string[];
  intervenções_que_não_funcionaram: string[];
}

export interface EstadoPsicologico {
  nível_ansiedade: NivelAnsiedade;
  tipo_bloqueio_atual: TipoBloqueio;
  streak_dias_consecutivos: number;
  maior_streak_histórico: number;
  última_vitória: {
    data: string;
    descrição: string;
  } | null;
  semanas_consecutivas_de_queda: number;
  narrativa_de_identidade_ativa: string;
}

export interface MetaCalibracao {
  nota_corte_estimada_do_cargo: number;
  meta_operacional_de_acerto: number;
  gap_atual_para_meta: number; // percentage points
  probabilidade_estimada_aprovação: number; // percentage 0-100
}

export interface PerfilCandidato {
  // Dados Estruturais
  cargo_alvo: string;
  área: string;
  nível_cargo: 'Médio' | 'Superior';
  formação_acadêmica: string;
  domínios_de_expertise: string[];
  data_prova_confirmada: string; // YYYY-MM-DD
  total_dias_até_prova: number;
  horas_dia_útil_reais: number;
  horas_sábado_reais: number;
  horas_domingo_reais: number;
  restrições_estruturais: {
    trabalho_turno: boolean;
    filhos: boolean;
    saúde: boolean;
    outro: string;
  };

  // Estado Dinâmico do Plano
  fase_atual: FaseEstudo;
  semana_atual: number;
  semana_total: number;
  ritmo_real_vs_planejado: number; // ±N days
  horas_estudadas_acumuladas: number;
  horas_de_questões_acumuladas: number;
  total_questões_resolvidas: number;

  // Performance Técnica
  histórico_acerto_por_disciplina: Record<string, DisciplinaPerf>;
  distribuição_de_erros: Record<ErroTipo, ErroDist>;
  erro_dominante_histórico: ErroTipo | 'NENHUM';
  simulados_realizados: Simulado[];
  projeção_de_nota_atual: number; // score project 0-100

  // Padrões Comportamentais
  padrões_comportamentais_observados: PadroesComportamentais;

  // Estado Psicológico e Motivacional
  estado_psicológico_e_motivacional: EstadoPsicologico;

  // Meta e Calibração
  meta_e_calibração: MetaCalibracao;
}

// Question interface for the Quiz and simulation bank
export interface Questao {
  id: string;
  disciplina: string;
  tema: string;
  contexto: string;
  enunciado: string;
  alternativas: {
    A: string;
    B: string;
    C: string;
    D: string;
    E: string;
  };
  gabarito: 'A' | 'B' | 'C' | 'D' | 'E';
  explicacao: string; // Explanations detailing ALT-A, B, C, D, E roles
  armadilhaCode?: string; // e.g. 'ARM-LP1'
}

// Flashcard interface
export interface Flashcard {
  id: string;
  disciplina: string;
  tema: string;
  pergunta: string;
  resposta: string;
  dataProximaRevisao: string; // YYYY-MM-DD
  intervaloDias: number;
  repeticoes: number;
  facilidade: number; // SM-2 parameter
}

// Chat message interface
export interface MensagemChat {
  id: string;
  remetente: 'agent' | 'user';
  texto: string;
  dataHora: string;
}

// Global configuration (backend AgentePetrobras / Ollama local)
export interface ConfigGlobal {
  // URL base da API FastAPI. Vazio = usa o proxy '/api' do Vite (dev).
  backendUrl: string;
  onboarded: boolean;
}
