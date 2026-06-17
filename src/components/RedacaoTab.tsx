import React, { useState } from 'react';
import { PenLine, Send, RefreshCw, Award, AlertTriangle } from 'lucide-react';
import { avaliarRedacao, AvaliacaoRedacao } from '../utils/api';

interface RedacaoTabProps {
  backendUrl: string;
}

export const RedacaoTab: React.FC<RedacaoTabProps> = ({ backendUrl }) => {
  const [tema, setTema] = useState('');
  const [texto, setTexto] = useState('');
  const [status, setStatus] = useState<'idle' | 'avaliando' | 'ok' | 'erro'>('idle');
  const [erroMsg, setErroMsg] = useState('');
  const [res, setRes] = useState<AvaliacaoRedacao | null>(null);

  const palavras = texto.trim() ? texto.trim().split(/\s+/).length : 0;

  const avaliar = async () => {
    if (!texto.trim()) return;
    setStatus('avaliando');
    try {
      setRes(await avaliarRedacao(backendUrl, texto, tema));
      setStatus('ok');
    } catch (e) {
      setErroMsg(e instanceof Error ? e.message : 'falha');
      setStatus('erro');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 820, margin: '0 auto' }}>
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <PenLine style={{ color: 'var(--color-primary)' }} /> <strong>Avaliador de Redação (CESGRANRIO)</strong>
        </div>
        <input
          className="form-input"
          placeholder="Tema (ex.: Transição energética e o papel da Petrobras)"
          value={tema}
          onChange={(e) => setTema(e.target.value)}
        />
        <textarea
          className="form-input"
          placeholder="Escreva sua redação/discursiva aqui…"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          rows={12}
          style={{ resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.5 }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button onClick={avaliar} className="btn btn-primary btn-sm" disabled={status === 'avaliando' || !texto.trim()}>
            {status === 'avaliando' ? <><RefreshCw size={14} className="spin" /> Avaliando…</> : <><Send size={14} /> Avaliar</>}
          </button>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{palavras} palavras</span>
        </div>
      </div>

      {status === 'erro' && (
        <div className="panel" style={{ borderLeft: '3px solid var(--color-error)' }}>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Falha ao avaliar ({erroMsg}). Inicie a API: <code>python cli_python/api.py</code>.
          </p>
        </div>
      )}

      {status === 'ok' && res && (
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {res.avaliado_por === 'estrutural' ? (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
              <AlertTriangle size={18} style={{ color: 'var(--color-warning)' }} />
              <p style={{ fontSize: '0.85rem' }}>{res.feedback}</p>
            </div>
          ) : (
            <>
              <div style={{ textAlign: 'center' }}>
                <Award size={26} style={{ color: 'var(--color-primary)', margin: '0 auto' }} />
                <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--color-primary)' }}>
                  {res.nota_total}<span style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>/{res.nota_maxima}</span>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {Object.entries(res.criterios).map(([k, c]) => {
                  const pct = c.max ? Math.round((c.nota / c.max) * 100) : 0;
                  return (
                    <div key={k}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 2 }}>
                        <span>{c.rotulo}</span>
                        <span style={{ color: 'var(--text-secondary)' }}>{c.nota}/{c.max}</span>
                      </div>
                      <div style={{ height: 7, background: 'var(--bg-hover)', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{ width: `${pct}%`, height: '100%', background: pct >= 60 ? 'var(--color-primary)' : 'var(--color-warning)' }} />
                      </div>
                      {c.comentario && <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', margin: '0.2rem 0 0' }}>{c.comentario}</p>}
                    </div>
                  );
                })}
              </div>
              {res.feedback && (
                <div style={{ background: 'var(--color-primary-glow)', borderRadius: 'var(--radius-sm)', padding: '0.6rem', fontSize: '0.82rem' }}>
                  <strong>Coach:</strong> {res.feedback}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};
