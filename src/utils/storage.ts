import { PerfilCandidato, FaseEstudo, ErroTipo, ConfigGlobal } from '../types';

export const CARGO_BENCHMARKS = {
  'Engenheiro Júnior': { corte: 64, meta: 79 },
  'Administrador Júnior': { corte: 61, meta: 76 },
  'Contador Júnior': { corte: 63, meta: 78 },
  'Analista de TI Júnior': { corte: 62, meta: 76 },
  'Geólogo / Geofísico Júnior': { corte: 66, meta: 81 },
  'Químico Júnior': { corte: 64, meta: 79 },
  'Advogado Júnior': { corte: 66, meta: 81 },
  'Técnico (nível médio)': { corte: 59, meta: 73 }
};

export const DISCIPLINAS_PADRAO = [
  'Língua Portuguesa',
  'Raciocínio Lógico / Matemática',
  'Conhecimentos Petrobras e Setor de O&G',
  'Legislação e Governança',
  'Conhecimentos Específicos'
];

export const PESOS_PADRAO: Record<string, number> = {
  'Língua Portuguesa': 20,
  'Raciocínio Lógico / Matemática': 15,
  'Conhecimentos Petrobras e Setor de O&G': 12,
  'Legislação e Governança': 11,
  'Conhecimentos Específicos': 42
};

export const ESTADO_INICIAL_PERFIL: PerfilCandidato = {
  cargo_alvo: '',
  área: '',
  nível_cargo: 'Superior',
  formação_acadêmica: '',
  domínios_de_expertise: [],
  data_prova_confirmada: '',
  total_dias_até_prova: 90,
  horas_dia_útil_reais: 3,
  horas_sábado_reais: 6,
  horas_domingo_reais: 4,
  restrições_estruturais: {
    trabalho_turno: false,
    filhos: false,
    saúde: false,
    outro: ''
  },
  fase_atual: 'FUNDAÇÃO',
  semana_atual: 1,
  semana_total: 12,
  ritmo_real_vs_planejado: 0,
  horas_estudadas_acumuladas: 0,
  horas_de_questões_acumuladas: 0,
  total_questões_resolvidas: 0,
  histórico_acerto_por_disciplina: {
    'Língua Portuguesa': { baseline_diagnóstico: 50, acerto_semana: [50], tendência: 'ESTÁVEL', total_questões_resolvidas: 0, velocidade_média_minutos_por_questão: 3.5 },
    'Raciocínio Lógico / Matemática': { baseline_diagnóstico: 50, acerto_semana: [50], tendência: 'ESTÁVEL', total_questões_resolvidas: 0, velocidade_média_minutos_por_questão: 3.5 },
    'Conhecimentos Petrobras e Setor de O&G': { baseline_diagnóstico: 50, acerto_semana: [50], tendência: 'ESTÁVEL', total_questões_resolvidas: 0, velocidade_média_minutos_por_questão: 3.5 },
    'Legislação e Governança': { baseline_diagnóstico: 50, acerto_semana: [50], tendência: 'ESTÁVEL', total_questões_resolvidas: 0, velocidade_média_minutos_por_questão: 3.5 },
    'Conhecimentos Específicos': { baseline_diagnóstico: 50, acerto_semana: [50], tendência: 'ESTÁVEL', total_questões_resolvidas: 0, velocidade_média_minutos_por_questão: 3.5 }
  },
  distribuição_de_erros: {
    'C': { porcentagem: 25, disciplinas_mais_afetadas: [] },
    'A': { porcentagem: 25, disciplinas_mais_afetadas: [] },
    'B': { porcentagem: 25, disciplinas_mais_afetadas: [] },
    'T': { porcentagem: 25, disciplinas_mais_afetadas: [] }
  },
  erro_dominante_histórico: 'NENHUM',
  simulados_realizados: [],
  projeção_de_nota_atual: 50,
  padrões_comportamentais_observados: {
    melhor_horário_produtivo_observado: 'Manhã',
    duração_foco_sustentável_real_minutos: 50,
    gatilhos_procrastinação_identificados: [],
    padrão_de_abandono_histórico: { tipo: 'Nenhum', momento_do_ciclo: 'Nenhum' },
    intervenções_que_funcionaram: [],
    intervenções_que_não_funcionaram: []
  },
  estado_psicológico_e_motivacional: {
    nível_ansiedade: 'MÉDIO',
    tipo_bloqueio_atual: 'NENHUM',
    streak_dias_consecutivos: 0,
    maior_streak_histórico: 0,
    última_vitória: null,
    semanas_consecutivas_de_queda: 0,
    narrativa_de_identidade_ativa: 'Você está construindo o profissional que a Petrobras aprova.'
  },
  meta_e_calibração: {
    nota_corte_estimada_do_cargo: 60,
    meta_operacional_de_acerto: 75,
    gap_atual_para_meta: -25,
    probabilidade_estimada_aprovação: 30
  }
};

const LOCAL_STORAGE_PERFIL_KEY = 'agente_petrobras_perfil_v4';
const LOCAL_STORAGE_CONFIG_KEY = 'agente_petrobras_config';
const LOCAL_STORAGE_FLASHCARDS_KEY = 'agente_petrobras_flashcards';

export function obterPerfilLocal(): PerfilCandidato | null {
  const data = localStorage.getItem(LOCAL_STORAGE_PERFIL_KEY);
  if (!data) return null;
  try {
    return JSON.parse(data) as PerfilCandidato;
  } catch (e) {
    console.error('Erro ao ler perfil do localStorage', e);
    return null;
  }
}

export function salvarPerfilLocal(perfil: PerfilCandidato): void {
  // Recalcular projeções e gaps dinamicamente antes de salvar
  const atualizado = calcularMetricasFinais(perfil);
  localStorage.setItem(LOCAL_STORAGE_PERFIL_KEY, JSON.stringify(atualizado));
}

export function obterConfigLocal(): ConfigGlobal {
  const data = localStorage.getItem(LOCAL_STORAGE_CONFIG_KEY);
  if (!data) return { backendUrl: '', onboarded: false };
  try {
    return JSON.parse(data) as ConfigGlobal;
  } catch {
    return { backendUrl: '', onboarded: false };
  }
}

export function salvarConfigLocal(config: ConfigGlobal): void {
  localStorage.setItem(LOCAL_STORAGE_CONFIG_KEY, JSON.stringify(config));
}

export function obterFlashcardsLocal(): import('../types').Flashcard[] {
  const data = localStorage.getItem(LOCAL_STORAGE_FLASHCARDS_KEY);
  if (!data) return [];
  try {
    return JSON.parse(data);
  } catch {
    return [];
  }
}

export function salvarFlashcardsLocal(cards: import('../types').Flashcard[]): void {
  localStorage.setItem(LOCAL_STORAGE_FLASHCARDS_KEY, JSON.stringify(cards));
}

export function limparTudo(): void {
  localStorage.removeItem(LOCAL_STORAGE_PERFIL_KEY);
  localStorage.removeItem(LOCAL_STORAGE_CONFIG_KEY);
  localStorage.removeItem(LOCAL_STORAGE_FLASHCARDS_KEY);
}

// CALCULATION FUNCTIONS (Scientist & Strategist logic)

export function calcularMetricasFinais(perfil: PerfilCandidato): PerfilCandidato {
  const cargo = perfil.cargo_alvo || 'Técnico (nível médio)';
  const benchmark = CARGO_BENCHMARKS[cargo as keyof typeof CARGO_BENCHMARKS] || { corte: 60, meta: 75 };

  // 1. Projeção de Nota Atual baseada nos acertos recentes de cada disciplina e pesos
  let totalPeso = 0;
  let somaPonderada = 0;

  DISCIPLINAS_PADRAO.forEach((disc) => {
    const perf = perfil.histórico_acerto_por_disciplina[disc];
    const acertos = perf?.acerto_semana || [];
    const notaAtual = acertos.length > 0 ? acertos[acertos.length - 1] : (perf?.baseline_diagnóstico ?? 50);
    const peso = PESOS_PADRAO[disc] ?? 10;

    somaPonderada += notaAtual * peso;
    totalPeso += peso;
  });

  const notaProjetada = totalPeso > 0 ? Math.round((somaPonderada / totalPeso) * 100) / 100 : 50;

  // 2. Determinar Erro Dominante
  let maxErroVal = -1;
  let erroDominante: ErroTipo = 'C';
  const erros = perfil.distribuição_de_erros;
  Object.keys(erros).forEach((key) => {
    const item = erros[key as ErroTipo];
    if (item.porcentagem > maxErroVal) {
      maxErroVal = item.porcentagem;
      erroDominante = key as ErroTipo;
    }
  });

  // 3. Gap para a meta operacional
  const gap = Math.round((notaProjetada - benchmark.meta) * 100) / 100;

  // 4. Calcular Probabilidade de Aprovação
  // A probabilidade leva em conta a nota projetada, a tendência, a consistência e o tempo restante
  const diasRestantes = perfil.total_dias_até_prova || 30;
  const difCorte = notaProjetada - benchmark.corte;
  
  let baseProb = 50;
  if (difCorte < -10) {
    baseProb = 15;
  } else if (difCorte < 0) {
    baseProb = 35 + (difCorte * 2); // 15 to 35%
  } else if (difCorte === 0) {
    baseProb = 50;
  } else if (difCorte < 10) {
    baseProb = 50 + (difCorte * 4); // 50 to 90%
  } else {
    baseProb = 90 + Math.min(8, difCorte - 10); // up to 98%
  }

  // Ajustes com base na consistência e dias restantes
  const streak = perfil.estado_psicológico_e_motivacional.streak_dias_consecutivos;
  const streakBonus = Math.min(5, streak * 0.5); // bonus de consistência
  
  // Se estiver caindo as últimas notas
  let dequedaPenalidade = 0;
  if (perfil.estado_psicológico_e_motivacional.semanas_consecutivas_de_queda > 1) {
    dequedaPenalidade = perfil.estado_psicológico_e_motivacional.semanas_consecutivas_de_queda * 5;
  }

  const probFinal = Math.max(5, Math.min(99, Math.round(baseProb + streakBonus - dequedaPenalidade)));

  // 5. Ajustar fase
  let fase: FaseEstudo = perfil.fase_atual;
  if (diasRestantes <= 7) {
    fase = 'SPRINT';
  } else if (diasRestantes <= 30 && gap < -5) {
    fase = 'EMERGÊNCIA';
  }

  return {
    ...perfil,
    fase_atual: fase,
    projeção_de_nota_atual: notaProjetada,
    erro_dominante_histórico: maxErroVal > 30 ? erroDominante : 'NENHUM',
    meta_e_calibração: {
      nota_corte_estimada_do_cargo: benchmark.corte,
      meta_operacional_de_acerto: benchmark.meta,
      gap_atual_para_meta: gap,
      probabilidade_estimada_aprovação: probFinal
    }
  };
}

// Calcula o Índice de Consistência (IC)
export function calcularIndiceConsistencia(diasEstudados: number, questoesFeitas: number, questoesPlanejadas: number): number {
  const fatorDias = diasEstudados / 7;
  const fatorQuestoes = questoesPlanejadas > 0 ? Math.min(1.2, questoesFeitas / questoesPlanejadas) : 1;
  return Math.round((fatorDias * fatorQuestoes) * 100) / 100;
}

// Calcula a equação de viabilidade de horas de estudo
export interface EquacaoViabilidadeResult {
  horasDisponiveis: number;
  horasNecessarias: number;
  saldo: number;
  veredicto: 'CONFORTÁVEL' | 'AJUSTADO' | 'CRÍTICO' | 'EMERGÊNCIA';
  modoAtivado: string;
}

export function calcularViabilidade(
  diasAteProva: number,
  hUtil: number,
  hSab: number,
  hDom: number,
  nivelEstudo: 'base_zero' | 'base_parcial' | 'revisao'
): EquacaoViabilidadeResult {
  // Estimativa de semanas restantes
  const semanas = diasAteProva / 7;
  const diasUteis = semanas * 5;
  const sabados = semanas;
  const domingos = semanas;

  const horasDisponiveis = Math.round(hUtil * diasUteis + hSab * sabados + hDom * domingos);

  // Horas estimadas necessárias por disciplina no total de acordo com a tabela do §7
  const horasNecessariasTabela = {
    base_zero: 100 + 70 + 50 + 60 + 250, // média dos intervalos (80-120 PT, 60-80 RL, 40-60 PB, 50-70 LG, 200-300 ESP) = 530h
    base_parcial: 50 + 35 + 25 + 30 + 125, // 265h
    revisao: 25 + 18 + 12 + 15 + 65 // 135h
  };

  const horasNecessarias = horasNecessariasTabela[nivelEstudo];
  const saldo = horasDisponiveis - horasNecessarias;
  const ratio = horasDisponiveis / horasNecessarias;

  let veredicto: 'CONFORTÁVEL' | 'AJUSTADO' | 'CRÍTICO' | 'EMERGÊNCIA' = 'AJUSTADO';
  let modoAtivado = 'PADRÃO';

  if (ratio >= 1.2) {
    veredicto = 'CONFORTÁVEL';
    modoAtivado = 'PADRÃO';
  } else if (ratio >= 0.9) {
    veredicto = 'AJUSTADO';
    modoAtivado = 'PADRÃO';
  } else if (ratio >= 0.7) {
    veredicto = 'CRÍTICO';
    modoAtivado = diasAteProva <= 60 ? '60d' : '90d';
  } else {
    veredicto = 'EMERGÊNCIA';
    modoAtivado = diasAteProva <= 15 ? '15d' : diasAteProva <= 30 ? '30d' : 'EMERGÊNCIA';
  }

  return {
    horasDisponiveis,
    horasNecessarias,
    saldo,
    veredicto,
    modoAtivado
  };
}
