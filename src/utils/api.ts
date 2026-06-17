import { PerfilCandidato, MensagemChat } from '../types';

// Cliente da API FastAPI do AgentePetrobras (LLM local via Ollama).
// Em dev, deixe backendUrl vazio para usar o proxy '/api' do Vite.

function base(backendUrl: string): string {
  const url = (backendUrl || '').trim().replace(/\/+$/, '');
  return url || '/api';
}

export interface RespostaCoach {
  pergunta: string;
  resposta: string;
}

// Monta um contexto compacto do candidato para o backend injetar no prompt,
// sem acoplar os dois esquemas de perfil.
export function montarContextoCandidato(perfil: PerfilCandidato | null): string {
  if (!perfil) return '';
  const m = perfil.meta_e_calibração;
  const fracas = Object.entries(perfil.histórico_acerto_por_disciplina || {})
    .map(([disc, perf]) => {
      const acertos = perf?.acerto_semana || [];
      const nota = acertos.length ? acertos[acertos.length - 1] : perf?.baseline_diagnóstico ?? 50;
      return { disc, nota };
    })
    .filter((d) => d.nota < 60)
    .map((d) => `${d.disc} (${d.nota}%)`);

  const linhas = [
    `Cargo alvo: ${perfil.cargo_alvo || '?'}`,
    `Fase atual: ${perfil.fase_atual}`,
    `Dias até a prova: ${perfil.total_dias_até_prova}`,
    `Projeção de nota: ${perfil.projeção_de_nota_atual}% (meta ${m?.meta_operacional_de_acerto ?? '?'}%)`,
    `Probabilidade estimada de aprovação: ${m?.probabilidade_estimada_aprovação ?? '?'}%`,
    `Streak: ${perfil.estado_psicológico_e_motivacional?.streak_dias_consecutivos ?? 0} dias`,
    fracas.length ? `Disciplinas fracas: ${fracas.join(', ')}` : 'Sem disciplinas abaixo de 60%.',
  ];
  return linhas.join('\n');
}

// Converte as mensagens do chat para o formato {role, content} do backend.
function historicoParaBackend(mensagens: MensagemChat[]): { role: string; content: string }[] {
  return mensagens.map((m) => ({
    role: m.remetente === 'user' ? 'user' : 'assistant',
    content: m.texto,
  }));
}

export async function perguntarCoach(
  backendUrl: string,
  mensagem: string,
  perfil: PerfilCandidato | null,
  mensagens: MensagemChat[],
): Promise<string> {
  const resp = await fetch(`${base(backendUrl)}/perguntar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mensagem,
      contexto_extra: montarContextoCandidato(perfil),
      historico: historicoParaBackend(mensagens),
    }),
  });

  if (!resp.ok) {
    let detalhe = `HTTP ${resp.status}`;
    try {
      const j = await resp.json();
      if (j?.detail) detalhe = j.detail;
    } catch {
      /* corpo não-JSON */
    }
    throw new Error(detalhe);
  }

  const data: RespostaCoach = await resp.json();
  return data.resposta;
}

// ── Loop de prática (recall espaçado) ──────────────────────────────────────

export interface QuestaoPratica {
  id: string;
  pergunta: string;
  opcoes: string[];
  disciplina: string;
  tipo: 'revisao' | 'nova';
  revisoes_pendentes: number;
}

export interface FeedbackPratica {
  correta: boolean;
  correta_idx: number;
  explicacao: string;
  fonte: string;
  disciplina: string;
  revisar_em: string;
}

export async function praticaProxima(backendUrl: string, disciplina = ''): Promise<QuestaoPratica> {
  const q = disciplina ? `?disciplina=${encodeURIComponent(disciplina)}` : '';
  const resp = await fetch(`${base(backendUrl)}/pratica/proxima${q}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

export async function praticaResponder(
  backendUrl: string, id: string, escolha: number, tempoSeg: number,
): Promise<FeedbackPratica> {
  const resp = await fetch(`${base(backendUrl)}/pratica/responder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, escolha, tempo_seg: tempoSeg }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

export async function praticaCoach(backendUrl: string, id: string, escolha: number): Promise<string> {
  try {
    const resp = await fetch(`${base(backendUrl)}/pratica/coach`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, escolha }),
    });
    if (!resp.ok) return '';
    return (await resp.json()).feedback || '';
  } catch {
    return '';
  }
}

export async function praticaClassificar(
  backendUrl: string, disciplina: string, categoria: string,
): Promise<void> {
  try {
    await fetch(`${base(backendUrl)}/pratica/classificar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ disciplina, categoria }),
    });
  } catch {
    /* best-effort */
  }
}

// ── Radar de inteligência ────────────────────────────────────────────────

export interface NotaIntel {
  arquivo: string;
  titulo: string;
  resumo: string;
  atualizado: string;
}

export async function obterIntel(backendUrl: string): Promise<NotaIntel[]> {
  const resp = await fetch(`${base(backendUrl)}/intel`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()).notas ?? [];
}

// ── Plano de hoje ─────────────────────────────────────────────────────────

export interface PlanoHoje {
  revisoes_devidas: number;
  foco: string[];
  meta_diaria: number;
  dias_ate_prova: number | null;
  passos: string[];
}

export async function obterPlanoHoje(backendUrl: string): Promise<PlanoHoje> {
  const resp = await fetch(`${base(backendUrl)}/plano-hoje`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// ── Simulado completo ────────────────────────────────────────────────────

export interface QuestaoSimulado {
  id: string;
  pergunta: string;
  opcoes: string[];
  disciplina: string;
}

export interface ResultadoSimulado {
  total: number;
  acertos: number;
  pct: number;
  por_disciplina: Record<string, { total: number; acertos: number; pct: number }>;
  detalhes: {
    id: string; disciplina: string; sua: number; correta_idx: number;
    acertou: boolean; pergunta: string; opcoes: string[]; explicacao: string;
  }[];
}

export async function simuladoMontar(backendUrl: string, n: number, disciplina = ''): Promise<QuestaoSimulado[]> {
  const q = `?n=${n}${disciplina ? `&disciplina=${encodeURIComponent(disciplina)}` : ''}`;
  const resp = await fetch(`${base(backendUrl)}/simulado/montar${q}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()).questoes ?? [];
}

export async function simuladoCorrigir(
  backendUrl: string, respostas: { id: string; escolha: number }[], tempoSeg: number,
): Promise<ResultadoSimulado> {
  const resp = await fetch(`${base(backendUrl)}/simulado/corrigir`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ respostas, tempo_seg: tempoSeg }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// ── Redação ─────────────────────────────────────────────────────────────

export interface CriterioRedacao { rotulo: string; nota: number; max: number; comentario: string }
export interface AvaliacaoRedacao {
  tema: string;
  metricas: { palavras: number; paragrafos: number };
  criterios: Record<string, CriterioRedacao>;
  nota_total: number | null;
  nota_maxima: number;
  feedback: string;
  avaliado_por: string | null;
}

export async function avaliarRedacao(backendUrl: string, texto: string, tema: string): Promise<AvaliacaoRedacao> {
  const resp = await fetch(`${base(backendUrl)}/redacao/avaliar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texto, tema }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// ── Progresso ─────────────────────────────────────────────────────────────

export interface DiaProgresso {
  data: string;
  respondidas: number;
  acertos: number;
  pct: number;
}

export interface Progresso {
  serie: DiaProgresso[];
  total_respondidas: number;
  total_acertos: number;
  pct_geral: number;
  dias_ativos: number;
}

export async function obterProgresso(backendUrl: string, dias = 14): Promise<Progresso> {
  const resp = await fetch(`${base(backendUrl)}/progresso?dias=${dias}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// ── Painel de maestria ──────────────────────────────────────────────────────

export interface DisciplinaMaestria {
  disciplina: string;
  rating: number;
  nivel: string;
  respostas: number;
  acerto_esperado: number;
}

export interface Maestria {
  disciplinas: DisciplinaMaestria[];
  foco: string[];
  revisoes_hoje: number;
}

export async function obterMaestria(backendUrl: string): Promise<Maestria> {
  const resp = await fetch(`${base(backendUrl)}/maestria`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return resp.json();
}

// Verifica se o backend está no ar (usado no painel de configuração).
export async function pingBackend(backendUrl: string): Promise<{ ok: boolean; detalhe: string }> {
  try {
    const resp = await fetch(`${base(backendUrl)}/`, { method: 'GET' });
    if (!resp.ok) return { ok: false, detalhe: `HTTP ${resp.status}` };
    const data = await resp.json();
    return { ok: true, detalhe: data?.api || 'online' };
  } catch (e) {
    return { ok: false, detalhe: e instanceof Error ? e.message : 'sem conexão' };
  }
}
