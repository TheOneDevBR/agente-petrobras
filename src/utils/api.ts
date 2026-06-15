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
