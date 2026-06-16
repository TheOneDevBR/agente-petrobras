import React, { useState, useEffect, useCallback } from 'react';
import { Activity, RotateCcw, Target, TrendingUp, Clock, Zap } from 'lucide-react';
import { obterMaestria, obterPlanoHoje, Maestria, PlanoHoje } from '../utils/api';

interface DashboardLivePanelProps {
  backendUrl: string;
  onIrPraticar: () => void;
}

/** Faixa de estatísticas reais (Elo/SM-2) no topo do Painel — não bloqueia o
 *  dashboard local se o backend estiver offline. */
export const DashboardLivePanel: React.FC<DashboardLivePanelProps> = ({ backendUrl, onIrPraticar }) => {
  const [maestria, setMaestria] = useState<Maestria | null>(null);
  const [plano, setPlano] = useState<PlanoHoje | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);

  const carregar = useCallback(async () => {
    try {
      const [m, p] = await Promise.all([obterMaestria(backendUrl), obterPlanoHoje(backendUrl)]);
      setMaestria(m);
      setPlano(p);
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, [backendUrl]);

  useEffect(() => { carregar(); }, [carregar]);

  if (online === false) {
    return (
      <div className="panel" style={{ marginBottom: '1rem', borderLeft: '3px solid var(--color-warning)' }}>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
          <Activity size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
          Estatísticas ao vivo offline — inicie a API (<code>python cli_python/api.py</code>) para ver
          maestria, revisões e foco reais. O painel abaixo segue funcionando com dados locais.
        </p>
      </div>
    );
  }

  const discs = maestria?.disciplinas ?? [];
  const projecao = discs.length
    ? Math.round((discs.reduce((s, d) => s + (d.acerto_esperado ?? 0), 0) / discs.length) * 100)
    : null;
  const foco = plano?.foco?.[0] ?? maestria?.foco?.[0] ?? null;

  const Card = ({ icon, valor, rotulo, cor }: { icon: React.ReactNode; valor: React.ReactNode; rotulo: string; cor?: string }) => (
    <div className="panel" style={{ flex: '1 1 140px', minWidth: 140, padding: '0.85rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: cor ?? 'var(--color-primary)' }}>
        {icon}
        <span style={{ fontSize: '1.25rem', fontWeight: 700 }}>{valor}</span>
      </div>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>{rotulo}</div>
    </div>
  );

  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'stretch' }}>
        <Card icon={<TrendingUp size={18} />} valor={projecao != null ? `${projecao}%` : '—'} rotulo="Maestria média (Elo)" />
        <Card icon={<RotateCcw size={18} />} valor={plano?.revisoes_devidas ?? '—'} rotulo="Revisões devidas" cor="var(--color-warning)" />
        <Card icon={<Target size={18} />} valor={foco ?? '—'} rotulo="Foco recomendado" cor="var(--color-warning)" />
        <Card icon={<Clock size={18} />} valor={plano?.dias_ate_prova ?? '—'} rotulo="Dias até a prova" />
        <button
          onClick={onIrPraticar}
          className="panel active-pulse"
          style={{ flex: '1 1 140px', minWidth: 140, cursor: 'pointer', border: '1px solid var(--color-primary)', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: '0.3rem', color: 'var(--color-primary)' }}
        >
          <Zap size={20} />
          <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>Praticar agora</span>
        </button>
      </div>
    </div>
  );
};
