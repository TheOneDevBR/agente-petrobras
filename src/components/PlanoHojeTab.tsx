import React, { useState, useEffect, useCallback } from 'react';
import { CalendarCheck, RefreshCw, XCircle, Flame, Target, RotateCcw, ChevronRight, Bell } from 'lucide-react';
import { PerfilCandidato } from '../types';
import { obterPlanoHoje, PlanoHoje } from '../utils/api';
import { pedirPermissaoNotificacao, notificar } from '../utils/notificacoes';

interface PlanoHojeTabProps {
  perfil: PerfilCandidato | null;
  backendUrl: string;
  onIrPraticar: () => void;
}

export const PlanoHojeTab: React.FC<PlanoHojeTabProps> = ({ perfil, backendUrl, onIrPraticar }) => {
  const [plano, setPlano] = useState<PlanoHoje | null>(null);
  const [status, setStatus] = useState<'loading' | 'ok' | 'erro'>('loading');
  const [erroMsg, setErroMsg] = useState('');

  const streak = perfil?.estado_psicológico_e_motivacional?.streak_dias_consecutivos ?? 0;
  const nome = perfil?.cargo_alvo ?? 'candidato';

  const carregar = useCallback(async () => {
    setStatus('loading');
    try {
      setPlano(await obterPlanoHoje(backendUrl));
      setStatus('ok');
    } catch (e) {
      setErroMsg(e instanceof Error ? e.message : 'falha');
      setStatus('erro');
    }
  }, [backendUrl]);

  useEffect(() => { carregar(); }, [carregar]);

  const ativarLembretes = async () => {
    const ok = await pedirPermissaoNotificacao();
    if (!ok) { alert('Ative as notificações do navegador para receber lembretes.'); return; }
    if (plano && plano.revisoes_devidas > 0) {
      notificar('AgentePetrobras', `Você tem ${plano.revisoes_devidas} revisão(ões) devida(s) hoje. Bora?`);
    } else {
      notificar('AgentePetrobras', 'Lembretes ativados! Sem revisões pendentes agora.');
    }
  };

  if (status === 'erro') {
    return (
      <div className="panel" style={{ textAlign: 'center', padding: '2rem' }}>
        <XCircle size={36} style={{ color: 'var(--color-error)', margin: '0 auto 1rem' }} />
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Não consegui montar o plano ({erroMsg}). Inicie a API: <code>python cli_python/api.py</code>.
        </p>
        <button onClick={carregar} className="btn btn-primary btn-sm" style={{ marginTop: '1rem' }}>
          <RefreshCw size={14} /> Tentar de novo
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 760, margin: '0 auto' }}>
      <div className="panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CalendarCheck style={{ color: 'var(--color-primary)' }} />
          <strong>Plano de Hoje</strong>
        </div>
        <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'center', fontSize: '0.85rem' }}>
          <span className="streak-counter" title="dias seguidos"><Flame size={15} /> {streak}d</span>
          {plano?.dias_ate_prova != null && (
            <span title="dias até a prova" style={{ color: 'var(--color-warning)' }}>
              ⏳ {plano.dias_ate_prova} dias p/ prova
            </span>
          )}
          <button onClick={ativarLembretes} className="btn btn-secondary btn-sm" title="ativar lembretes de revisão">
            <Bell size={14} />
          </button>
        </div>
      </div>

      <div className="panel">
        {status === 'loading' && (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
            <RefreshCw size={24} className="spin" /> <p>Montando seu plano...</p>
          </div>
        )}

        {status === 'ok' && plano && (
          <>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Bom estudo, <strong>{nome}</strong>. Seu plano para hoje, baseado no seu desempenho real:
            </p>

            {/* Ações rápidas */}
            <div className="grid-2" style={{ gap: '0.75rem', marginBottom: '1rem' }}>
              <button
                onClick={onIrPraticar}
                className={`panel ${plano.revisoes_devidas > 0 ? 'active-pulse' : ''}`}
                style={{ textAlign: 'left', cursor: 'pointer', border: plano.revisoes_devidas > 0 ? '1px solid var(--color-primary)' : '1px solid var(--border-color)' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-primary)' }}>
                  <RotateCcw size={18} /> <strong>{plano.revisoes_devidas} revisões devidas</strong>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '0.35rem 0 0' }}>
                  Recuperação espaçada — comece por aqui. <ChevronRight size={12} style={{ verticalAlign: 'middle' }} />
                </p>
              </button>

              <button
                onClick={onIrPraticar}
                className="panel"
                style={{ textAlign: 'left', cursor: 'pointer', border: '1px solid var(--border-color)' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-warning)' }}>
                  <Target size={18} /> <strong>Meta: {plano.meta_diaria} questões</strong>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '0.35rem 0 0' }}>
                  Foco: {plano.foco[0] ?? 'adaptativo'}. <ChevronRight size={12} style={{ verticalAlign: 'middle' }} />
                </p>
              </button>
            </div>

            {/* Passos (recomendação por evidência) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {plano.passos.map((p, i) => (
                <div key={i} style={{ fontSize: '0.85rem', display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                  <span style={{ color: 'var(--color-primary)' }}>▸</span>
                  <span>{p}</span>
                </div>
              ))}
            </div>

            <button onClick={onIrPraticar} className="btn btn-primary btn-sm active-pulse" style={{ marginTop: '1.25rem' }}>
              <Target size={16} /> Começar agora
            </button>
          </>
        )}
      </div>
    </div>
  );
};
