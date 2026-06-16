import React, { useState, useEffect, useRef } from 'react';
import { FileText, Clock, CheckCircle2, XCircle, RefreshCw, Award, Send } from 'lucide-react';
import { simuladoMontar, simuladoCorrigir, QuestaoSimulado, ResultadoSimulado } from '../utils/api';
import { DISCIPLINAS_PADRAO } from '../utils/storage';

interface SimuladoTabProps {
  backendUrl: string;
}

const LETRAS = ['A', 'B', 'C', 'D', 'E'];

export const SimuladoTab: React.FC<SimuladoTabProps> = ({ backendUrl }) => {
  const [fase, setFase] = useState<'config' | 'rodando' | 'resultado' | 'erro'>('config');
  const [erroMsg, setErroMsg] = useState('');
  const [n, setN] = useState(20);
  const [disciplina, setDisciplina] = useState('');
  const [questoes, setQuestoes] = useState<QuestaoSimulado[]>([]);
  const [respostas, setRespostas] = useState<Record<string, number>>({});
  const [resultado, setResultado] = useState<ResultadoSimulado | null>(null);
  const [tempo, setTempo] = useState(0);
  const inicioRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pararTimer = () => { if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; } };
  useEffect(() => pararTimer, []);

  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

  const iniciar = async () => {
    setFase('rodando');
    setRespostas({});
    setResultado(null);
    try {
      const qs = await simuladoMontar(backendUrl, n, disciplina);
      setQuestoes(qs);
      inicioRef.current = Date.now();
      setTempo(0);
      timerRef.current = setInterval(() => setTempo(Math.floor((Date.now() - inicioRef.current) / 1000)), 1000);
    } catch (e) {
      setErroMsg(e instanceof Error ? e.message : 'falha');
      setFase('erro');
    }
  };

  const enviar = async () => {
    pararTimer();
    const tempoSeg = (Date.now() - inicioRef.current) / 1000;
    try {
      const payload = Object.entries(respostas).map(([id, escolha]) => ({ id, escolha }));
      const r = await simuladoCorrigir(backendUrl, payload, tempoSeg);
      setResultado(r);
      setFase('resultado');
    } catch (e) {
      setErroMsg(e instanceof Error ? e.message : 'falha');
      setFase('erro');
    }
  };

  const respondidas = Object.keys(respostas).length;

  if (fase === 'erro') {
    return (
      <div className="panel" style={{ textAlign: 'center', padding: '2rem' }}>
        <XCircle size={36} style={{ color: 'var(--color-error)', margin: '0 auto 1rem' }} />
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          {erroMsg}. Inicie a API: <code>python cli_python/api.py</code>.
        </p>
        <button onClick={() => setFase('config')} className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }}>Voltar</button>
      </div>
    );
  }

  // ── Configuração ──
  if (fase === 'config') {
    return (
      <div className="panel" style={{ maxWidth: 560, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileText style={{ color: 'var(--color-primary)' }} /> <strong>Simulado completo</strong>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Prova cronometrada com correção e desempenho por disciplina. Alimenta sua maestria (Elo).
        </p>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">Número de questões: <strong>{n}</strong></label>
          <input type="range" min={5} max={70} step={5} value={n} onChange={(e) => setN(Number(e.target.value))} style={{ width: '100%', accentColor: 'var(--color-primary)' }} />
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">Disciplina (opcional)</label>
          <select value={disciplina} onChange={(e) => setDisciplina(e.target.value)} className="form-input">
            <option value="">Todas (mistas — como na prova)</option>
            {DISCIPLINAS_PADRAO.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <button onClick={iniciar} className="btn btn-primary active-pulse" style={{ alignSelf: 'flex-start' }}>
          Iniciar simulado
        </button>
      </div>
    );
  }

  // ── Resultado ──
  if (fase === 'resultado' && resultado) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 820, margin: '0 auto' }}>
        <div className="panel" style={{ textAlign: 'center' }}>
          <Award size={32} style={{ color: 'var(--color-primary)', margin: '0 auto 0.5rem' }} />
          <div style={{ fontSize: '2.2rem', fontWeight: 800, color: resultado.pct >= 60 ? 'var(--color-primary)' : 'var(--color-warning)' }}>
            {resultado.pct}%
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            {resultado.acertos}/{resultado.total} acertos · tempo {fmt(tempo)}
          </p>
        </div>

        <div className="panel">
          <h4 style={{ fontSize: '0.95rem', marginBottom: '0.75rem' }}>Desempenho por disciplina</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {Object.entries(resultado.por_disciplina).map(([disc, d]) => (
              <div key={disc}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.2rem' }}>
                  <span>{disc}</span><span style={{ color: 'var(--text-secondary)' }}>{d.acertos}/{d.total} · {d.pct}%</span>
                </div>
                <div style={{ height: 8, background: 'var(--bg-hover)', borderRadius: 5, overflow: 'hidden' }}>
                  <div style={{ width: `${d.pct}%`, height: '100%', background: d.pct >= 60 ? 'var(--color-primary)' : 'var(--color-warning)' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <h4 style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>Revisão dos erros</h4>
          {resultado.detalhes.filter((d) => !d.acertou).length === 0 ? (
            <p style={{ fontSize: '0.85rem', color: 'var(--color-primary)' }}>Gabaritou! 🎯</p>
          ) : resultado.detalhes.filter((d) => !d.acertou).map((d, i) => (
            <div key={i} style={{ borderBottom: '1px solid var(--border-color)', padding: '0.5rem 0' }}>
              <p style={{ fontSize: '0.82rem', fontWeight: 500, marginBottom: '0.25rem' }}>{d.pergunta.slice(0, 160)}</p>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                <XCircle size={12} style={{ color: 'var(--color-error)', verticalAlign: 'middle' }} /> Sua: {LETRAS[d.sua] ?? '—'} ·{' '}
                <CheckCircle2 size={12} style={{ color: 'var(--color-primary)', verticalAlign: 'middle' }} /> Certa: {LETRAS[d.correta_idx]}
              </p>
              {d.explicacao && <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>{d.explicacao}</p>}
            </div>
          ))}
        </div>

        <button onClick={() => setFase('config')} className="btn btn-primary btn-sm" style={{ alignSelf: 'center' }}>
          <RefreshCw size={14} /> Novo simulado
        </button>
      </div>
    );
  }

  // ── Rodando ──
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 820, margin: '0 auto' }}>
      <div className="panel" style={{ position: 'sticky', top: 0, zIndex: 5, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.85rem' }}>Respondidas: <strong>{respondidas}/{questoes.length}</strong></span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem' }}><Clock size={15} /> {fmt(tempo)}</span>
        <button onClick={enviar} className="btn btn-primary btn-sm" disabled={respondidas === 0}>
          <Send size={14} /> Entregar
        </button>
      </div>

      {questoes.map((q, qi) => (
        <div key={q.id} className="panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span className="badge badge-green">{q.disciplina}</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Q{qi + 1}</span>
          </div>
          <p style={{ fontSize: '0.9rem', fontWeight: 500, marginBottom: '0.75rem', whiteSpace: 'pre-line' }}>{q.pergunta}</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {q.opcoes.map((op, idx) => (
              <button
                key={idx}
                onClick={() => setRespostas((r) => ({ ...r, [q.id]: idx }))}
                className="btn btn-secondary btn-sm"
                style={{
                  textAlign: 'left', display: 'flex', gap: '0.5rem', padding: '0.55rem',
                  borderColor: respostas[q.id] === idx ? 'var(--color-primary)' : undefined,
                  background: respostas[q.id] === idx ? 'var(--color-primary-glow)' : undefined,
                }}
              >
                <strong style={{ color: 'var(--color-primary)' }}>{LETRAS[idx]})</strong>
                <span style={{ fontSize: '0.83rem' }}>{op}</span>
              </button>
            ))}
          </div>
        </div>
      ))}

      <button onClick={enviar} className="btn btn-primary active-pulse" disabled={respondidas === 0} style={{ alignSelf: 'center' }}>
        <Send size={16} /> Entregar simulado ({respondidas}/{questoes.length})
      </button>
    </div>
  );
};
