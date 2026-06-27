import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  montarContextoCandidato, pingBackend, praticaProxima, simuladoMontar, avaliarRedacao,
} from './api';

function fakeResp(body: unknown, ok = true, statusCode = 200) {
  return { ok, status: statusCode, json: async () => body } as Response;
}

const perfil = {
  cargo_alvo: 'Engenheiro de Petróleo Júnior',
  fase_atual: 'FUNDAÇÃO',
  total_dias_até_prova: 90,
  projeção_de_nota_atual: 64,
  meta_e_calibração: { meta_operacional_de_acerto: 79, probabilidade_estimada_aprovação: 40 },
  estado_psicológico_e_motivacional: { streak_dias_consecutivos: 5 },
  histórico_acerto_por_disciplina: {
    'Língua Portuguesa': { acerto_semana: [55], baseline_diagnóstico: 50 },
  },
} as unknown as Parameters<typeof montarContextoCandidato>[0];

afterEach(() => vi.unstubAllGlobals());

describe('montarContextoCandidato', () => {
  it('retorna vazio sem perfil', () => {
    expect(montarContextoCandidato(null)).toBe('');
  });
  it('inclui cargo, fase e disciplinas fracas', () => {
    const ctx = montarContextoCandidato(perfil);
    expect(ctx).toContain('Engenheiro de Petróleo Júnior');
    expect(ctx).toContain('Fase atual');
    expect(ctx).toContain('Língua Portuguesa'); // < 60% → fraca
  });
});

describe('pingBackend', () => {
  it('online quando a API responde', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => fakeResp({ api: 'AgentePetrobras v4.0' })));
    const r = await pingBackend('');
    expect(r.ok).toBe(true);
    expect(r.detalhe).toContain('AgentePetrobras');
  });
  it('offline quando o fetch falha', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('sem conexão'); }));
    const r = await pingBackend('http://127.0.0.1:8000');
    expect(r.ok).toBe(false);
  });
});

describe('praticaProxima', () => {
  it('parseia a questão e usa a URL base', async () => {
    const spy = vi.fn(async () => fakeResp({ id: 'abc', pergunta: 'Q?', opcoes: ['a', 'b'], disciplina: 'RLM', tipo: 'nova', revisoes_pendentes: 0 }));
    vi.stubGlobal('fetch', spy);
    const q = await praticaProxima('', 'RLM');
    expect(q.id).toBe('abc');
    expect(spy).toHaveBeenCalledWith(expect.stringContaining('/api/pratica/proxima?disciplina=RLM'));
  });
});

describe('simuladoMontar', () => {
  it('retorna a lista de questões e a composição', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => fakeResp({ n: 1, basicas: 0, especificas: 1, questoes: [{ id: 'x', pergunta: 'P', opcoes: ['a'], disciplina: 'G' }] })));
    const m = await simuladoMontar('', 5);
    expect(m.questoes).toHaveLength(1);
    expect(m.questoes[0].id).toBe('x');
    expect(m.especificas).toBe(1);
  });
});

describe('avaliarRedacao', () => {
  it('envia texto e tema no corpo', async () => {
    const spy = vi.fn(async (_url: string, _init?: RequestInit) =>
      fakeResp({ avaliado_por: 'estrutural', metricas: { palavras: 3, paragrafos: 1 }, criterios: {}, nota_total: null, nota_maxima: 10, feedback: '', tema: 'X' }));
    vi.stubGlobal('fetch', spy);
    const r = await avaliarRedacao('', 'meu texto', 'Energia');
    expect(r.avaliado_por).toBe('estrutural');
    const body = JSON.parse(String(spy.mock.calls[0][1]?.body ?? '{}'));
    expect(body).toEqual({ texto: 'meu texto', tema: 'Energia' });
  });
});
