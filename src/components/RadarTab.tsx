import React, { useState, useEffect, useCallback } from 'react';
import { Radar, RefreshCw, XCircle, Newspaper, AtSign } from 'lucide-react';
import { obterIntel, NotaIntel } from '../utils/api';

interface RadarTabProps {
  backendUrl: string;
}

function iconeNota(arquivo: string) {
  if (arquivo.toLowerCase().includes('instagram')) return <AtSign size={16} style={{ color: 'var(--color-warning)' }} />;
  return <Newspaper size={16} style={{ color: 'var(--color-primary)' }} />;
}

export const RadarTab: React.FC<RadarTabProps> = ({ backendUrl }) => {
  const [notas, setNotas] = useState<NotaIntel[]>([]);
  const [status, setStatus] = useState<'loading' | 'ok' | 'erro'>('loading');
  const [erroMsg, setErroMsg] = useState('');

  const carregar = useCallback(async () => {
    setStatus('loading');
    try {
      setNotas(await obterIntel(backendUrl));
      setStatus('ok');
    } catch (e) {
      setErroMsg(e instanceof Error ? e.message : 'falha');
      setStatus('erro');
    }
  }, [backendUrl]);

  useEffect(() => { carregar(); }, [carregar]);

  const fmtData = (iso: string) => {
    try { return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }); }
    catch { return iso.slice(0, 10); }
  };

  if (status === 'erro') {
    return (
      <div className="panel" style={{ textAlign: 'center', padding: '2rem' }}>
        <XCircle size={36} style={{ color: 'var(--color-error)', margin: '0 auto 1rem' }} />
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Não consegui carregar o radar ({erroMsg}). Inicie a API: <code>python cli_python/api.py</code>.
        </p>
        <button onClick={carregar} className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }}>
          <RefreshCw size={14} /> Tentar de novo
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 820, margin: '0 auto' }}>
      <div className="panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Radar style={{ color: 'var(--color-primary)' }} />
          <strong>Radar de Inteligência</strong>
        </div>
        <button onClick={carregar} className="btn btn-secondary btn-sm" title="atualizar">
          <RefreshCw size={14} />
        </button>
      </div>

      <div className="panel">
        {status === 'loading' && (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            <RefreshCw size={24} className="spin" /> <p>Buscando novidades...</p>
          </div>
        )}

        {status === 'ok' && notas.length === 0 && (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <Radar size={32} style={{ color: 'var(--text-muted)', margin: '0 auto 0.75rem' }} />
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Nenhuma novidade ainda. Rode o coletor (<code>coletor.py --all</code>) ou o radar do
              Instagram (<code>instagram.py</code>) para captar editais e materiais.
            </p>
          </div>
        )}

        {status === 'ok' && notas.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {notas.map((n) => (
              <div key={n.arquivo} style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '0.6rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                  {iconeNota(n.arquivo)}
                  <strong style={{ fontSize: '0.88rem' }}>{n.titulo}</strong>
                  <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: 'var(--text-muted)' }}>{fmtData(n.atualizado)}</span>
                </div>
                {n.resumo && (
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>{n.resumo}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
