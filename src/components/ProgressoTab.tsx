import React, { useState, useEffect, useCallback } from 'react';
import { LineChart, RefreshCw, XCircle, CheckCircle2, CalendarDays } from 'lucide-react';
import { obterProgresso, Progresso } from '../utils/api';

interface ProgressoTabProps {
  backendUrl: string;
}

export const ProgressoTab: React.FC<ProgressoTabProps> = ({ backendUrl }) => {
  const [dados, setDados] = useState<Progresso | null>(null);
  const [status, setStatus] = useState<'loading' | 'ok' | 'erro'>('loading');
  const [erroMsg, setErroMsg] = useState('');

  const carregar = useCallback(async () => {
    setStatus('loading');
    try {
      setDados(await obterProgresso(backendUrl, 14));
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
          Não consegui carregar o progresso ({erroMsg}). Inicie a API: <code>python cli_python/api.py</code>.
        </p>
        <button onClick={carregar} className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }}>
          <RefreshCw size={14} /> Tentar de novo
        </button>
      </div>
    );
  }

  const serie = dados?.serie ?? [];
  const maxResp = Math.max(1, ...serie.map((d) => d.respondidas));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 820, margin: '0 auto' }}>
      <div className="panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <LineChart style={{ color: 'var(--color-primary)' }} />
          <strong>Progresso</strong>
        </div>
        <button onClick={carregar} className="btn btn-secondary btn-sm" title="atualizar"><RefreshCw size={14} /></button>
      </div>

      {status === 'loading' && (
        <div className="panel" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
          <RefreshCw size={24} className="spin" /> <p>Carregando histórico...</p>
        </div>
      )}

      {status === 'ok' && dados && (
        <>
          {/* Totais */}
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div className="panel" style={{ flex: '1 1 130px', minWidth: 130 }}>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--color-primary)' }}>{dados.total_respondidas}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>questões resolvidas</div>
            </div>
            <div className="panel" style={{ flex: '1 1 130px', minWidth: 130 }}>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: dados.pct_geral >= 60 ? 'var(--color-primary)' : 'var(--color-warning)' }}>{dados.pct_geral}%</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>acerto geral</div>
            </div>
            <div className="panel" style={{ flex: '1 1 130px', minWidth: 130 }}>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <CalendarDays size={18} style={{ color: 'var(--color-warning)' }} /> {dados.dias_ativos}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>dias praticados</div>
            </div>
          </div>

          {/* Gráfico: questões/dia (barra) + % acerto */}
          <div className="panel">
            <h4 style={{ fontSize: '0.9rem', marginBottom: '0.75rem' }}>Últimos 14 dias</h4>
            {dados.total_respondidas === 0 ? (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Sem prática registrada ainda. Resolva questões em <strong>Praticar</strong> ou <strong>Simulado</strong> para ver sua evolução.
              </p>
            ) : (
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: 160 }}>
                {serie.map((d) => {
                  const h = Math.round((d.respondidas / maxResp) * 130);
                  const cor = d.respondidas === 0 ? 'var(--bg-hover)' : d.pct >= 60 ? 'var(--color-primary)' : 'var(--color-warning)';
                  return (
                    <div key={d.data} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}
                         title={`${d.data}: ${d.respondidas} questões · ${d.pct}% acerto`}>
                      <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>{d.respondidas || ''}</span>
                      <div style={{ width: '100%', height: Math.max(2, h), background: cor, borderRadius: '3px 3px 0 0', transition: 'height 0.3s' }} />
                      <span style={{ fontSize: '0.58rem', color: 'var(--text-muted)' }}>{d.data.slice(8, 10)}/{d.data.slice(5, 7)}</span>
                    </div>
                  );
                })}
              </div>
            )}
            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.5rem', display: 'flex', gap: '1rem' }}>
              <span><CheckCircle2 size={11} style={{ color: 'var(--color-primary)', verticalAlign: 'middle' }} /> ≥60% acerto</span>
              <span>altura = nº de questões no dia</span>
            </p>
          </div>
        </>
      )}
    </div>
  );
};
