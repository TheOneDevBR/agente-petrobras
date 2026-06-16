import React, { useState, useEffect, useCallback } from 'react';
import { Award, RefreshCw, Target, XCircle, Flame } from 'lucide-react';
import { PerfilCandidato } from '../types';
import { obterMaestria, Maestria } from '../utils/api';

interface MaestriaTabProps {
  perfil: PerfilCandidato | null;
  backendUrl: string;
  onIrPraticar: () => void;
}

function corDaBarra(pct: number): string {
  if (pct >= 70) return 'var(--color-primary)';
  if (pct >= 50) return 'var(--color-warning)';
  return 'var(--color-error)';
}

export const MaestriaTab: React.FC<MaestriaTabProps> = ({ perfil, backendUrl, onIrPraticar }) => {
  const [dados, setDados] = useState<Maestria | null>(null);
  const [status, setStatus] = useState<'loading' | 'ok' | 'erro'>('loading');
  const [erroMsg, setErroMsg] = useState('');

  const streak = perfil?.estado_psicológico_e_motivacional?.streak_dias_consecutivos ?? 0;

  const carregar = useCallback(async () => {
    setStatus('loading');
    try {
      setDados(await obterMaestria(backendUrl));
      setStatus('ok');
    } catch (e) {
      setErroMsg(e instanceof Error ? e.message : 'falha');
      setStatus('erro');
    }
  }, [backendUrl]);

  useEffect(() => { carregar(); }, [carregar]);

  if (status === 'erro') {
    return (
      <div className="panel" style={{ textAlign: 'center', padding: '2rem' }}>
        <XCircle size={36} style={{ color: 'var(--color-error)', margin: '0 auto 1rem' }} />
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Não consegui carregar a maestria ({erroMsg}). Inicie a API: <code>python cli_python/api.py</code>.
        </p>
        <button onClick={carregar} className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }}>
          <RefreshCw size={14} /> Tentar de novo
        </button>
      </div>
    );
  }

  const disciplinas = dados?.disciplinas ?? [];
  const foco = dados?.foco ?? [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 820, margin: '0 auto' }}>
      <div className="panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Award style={{ color: 'var(--color-primary)' }} />
          <strong>Mapa de Maestria</strong>
        </div>
        <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'center', fontSize: '0.85rem' }}>
          <span className="streak-counter" title="dias seguidos"><Flame size={15} /> {streak}d</span>
          {dados && dados.revisoes_hoje > 0 && (
            <button onClick={onIrPraticar} className="btn btn-primary btn-sm active-pulse">
              ↻ {dados.revisoes_hoje} revisões hoje
            </button>
          )}
          <button onClick={carregar} className="btn btn-secondary btn-sm" title="atualizar">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      <div className="panel">
        {status === 'loading' && (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            <RefreshCw size={24} className="spin" /> <p>Carregando habilidade medida...</p>
          </div>
        )}

        {status === 'ok' && disciplinas.length === 0 && (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <Target size={32} style={{ color: 'var(--text-muted)', margin: '0 auto 0.75rem' }} />
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Ainda sem dados de prática. Responda questões para medir sua maestria (Elo).
            </p>
            <button onClick={onIrPraticar} className="btn btn-primary btn-sm active-pulse" style={{ marginTop: '1rem' }}>
              <Target size={14} /> Começar a praticar
            </button>
          </div>
        )}

        {status === 'ok' && disciplinas.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            {disciplinas.map((d) => {
              const pct = Math.round((d.acerto_esperado ?? 0) * 100);
              const ehFoco = foco.includes(d.disciplina);
              return (
                <div key={d.disciplina}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                      {d.disciplina}
                      {ehFoco && <span className="badge" style={{ marginLeft: '0.5rem', background: 'rgba(245,158,11,0.15)', color: '#fbbf24' }}>foco</span>}
                    </span>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      {pct}% · {d.nivel} · n={d.respostas}
                    </span>
                  </div>
                  <div style={{ height: 10, background: 'var(--bg-hover)', borderRadius: 6, overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: corDaBarra(pct), transition: 'width 0.4s' }} />
                  </div>
                </div>
              );
            })}
            <button onClick={onIrPraticar} className="btn btn-primary btn-sm" style={{ alignSelf: 'flex-start', marginTop: '0.5rem' }}>
              <Target size={14} /> Praticar o foco
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
