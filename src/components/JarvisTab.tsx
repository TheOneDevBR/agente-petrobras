import React, { useState, useEffect, useCallback } from 'react';
import { Volume2 } from 'lucide-react';
import { PerfilCandidato } from '../types';
import {
  obterMaestria, obterPlanoHoje, obterProgresso, obterIntel,
  Maestria, PlanoHoje, Progresso, NotaIntel,
} from '../utils/api';

interface JarvisTabProps {
  perfil: PerfilCandidato | null;
  backendUrl: string;
  onIrPraticar: () => void;
}

const R = 80;
const CIRC = 2 * Math.PI * R;

const BOOT = [
  '> AGENTEPETROBRAS // núcleo tático',
  '> inicializando telemetria .......... ok',
  '> calibrando maestria (Elo) ......... ok',
  '> recuperando plano tático .......... ok',
  '> sistemas operacionais.',
];

function saudacao(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Bom dia';
  if (h < 18) return 'Boa tarde';
  return 'Boa noite';
}

export const JarvisTab: React.FC<JarvisTabProps> = ({ perfil, backendUrl, onIrPraticar }) => {
  const [maestria, setMaestria] = useState<Maestria | null>(null);
  const [plano, setPlano] = useState<PlanoHoje | null>(null);
  const [progresso, setProgresso] = useState<Progresso | null>(null);
  const [intel, setIntel] = useState<NotaIntel[]>([]);
  const [online, setOnline] = useState<boolean | null>(null);
  const [agora, setAgora] = useState(new Date());
  const [typed, setTyped] = useState('');
  const [bootN, setBootN] = useState(0);
  const [booting, setBooting] = useState(true);

  const carregar = useCallback(async () => {
    const [m, p, pr, it] = await Promise.allSettled([
      obterMaestria(backendUrl), obterPlanoHoje(backendUrl),
      obterProgresso(backendUrl, 14), obterIntel(backendUrl),
    ]);
    let ok = false;
    if (m.status === 'fulfilled') { setMaestria(m.value); ok = true; }
    if (p.status === 'fulfilled') { setPlano(p.value); ok = true; }
    if (pr.status === 'fulfilled') { setProgresso(pr.value); ok = true; }
    if (it.status === 'fulfilled') { setIntel(it.value); ok = true; }
    setOnline(ok);
  }, [backendUrl]);

  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => {
    const t = setInterval(() => setAgora(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  // Sequência de boot do núcleo (revela linhas e dissolve no HUD)
  useEffect(() => {
    if (!booting) return;
    if (bootN >= BOOT.length) {
      const t = setTimeout(() => setBooting(false), 450);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setBootN((n) => n + 1), 280);
    return () => clearTimeout(t);
  }, [bootN, booting]);

  const discs = maestria?.disciplinas ?? [];
  const prontidao = discs.length
    ? Math.round((discs.reduce((s, d) => s + (d.acerto_esperado ?? 0), 0) / discs.length) * 100)
    : 0;
  const streak = perfil?.estado_psicológico_e_motivacional?.streak_dias_consecutivos ?? 0;
  const foco = plano?.foco?.[0] ?? maestria?.foco?.[0] ?? '—';
  const alvo = perfil?.cargo_alvo || 'candidato';

  // Sequência de "boot" — digita a saudação ao calibrar
  useEffect(() => {
    if (online === null) return;
    const frase = `${saudacao()}, ${alvo}. ${online ? 'Todos os sistemas operacionais.' : 'Núcleo offline — reativando…'}`;
    setTyped('');
    let i = 0;
    const t = setInterval(() => {
      i += 1;
      setTyped(frase.slice(0, i));
      if (i >= frase.length) clearInterval(t);
    }, 28);
    return () => clearInterval(t);
  }, [online, alvo]);

  const briefing = () => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    const partes = [
      `${saudacao()}, ${alvo}.`,
      `Prontidão ${prontidao} por cento.`,
      plano?.revisoes_devidas ? `${plano.revisoes_devidas} revisões devidas.` : 'Sem revisões pendentes.',
      foco && foco !== '—' ? `Foco prioritário: ${foco}.` : '',
      progresso?.total_respondidas
        ? `${progresso.total_respondidas} questões resolvidas, ${progresso.pct_geral} por cento de acerto.`
        : '',
    ].filter(Boolean).join(' ');
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(partes);
      u.lang = 'pt-BR';
      window.speechSynthesis.speak(u);
    } catch { /* sem TTS */ }
  };

  const Stat = ({ k, v }: { k: string; v: React.ReactNode }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0', borderBottom: '1px solid var(--hud-faint)' }}>
      <span style={{ fontSize: '0.74rem', opacity: 0.8 }}>{k}</span>
      <span className="hud-glow" style={{ fontSize: '0.82rem', fontWeight: 700 }}>{v}</span>
    </div>
  );

  if (booting) {
    return (
      <div className="jarvis" style={{ minHeight: 340, display: 'flex', alignItems: 'center', cursor: 'pointer' }} onClick={() => setBooting(false)}>
        <div style={{ fontFamily: 'monospace', fontSize: '0.95rem', lineHeight: 1.9, paddingLeft: '1rem' }}>
          {BOOT.slice(0, bootN).map((l, i) => <div key={i} className="hud-glow">{l}</div>)}
          {bootN < BOOT.length && <span className="hud-cursor">▋</span>}
          <div style={{ fontSize: '0.7rem', opacity: 0.45, marginTop: '1rem' }}>clique para pular</div>
        </div>
      </div>
    );
  }

  return (
    <div className="jarvis">
      {/* Top bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <div className="hud-label" style={{ marginBottom: 2 }}>AgentePetrobras · Central Tática</div>
          <div style={{ fontSize: '0.9rem', minHeight: '1.2em' }}>
            {typed}<span className="hud-cursor">▋</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={briefing}
            title="Briefing por voz"
            className="btn btn-sm"
            style={{ background: 'transparent', border: '1px solid var(--hud-dim)', color: 'var(--hud)', padding: '0.3rem 0.5rem' }}
          >
            <Volume2 size={16} />
          </button>
          <div className="hud-glow" style={{ fontFamily: 'monospace', fontSize: '1.1rem' }}>
            {agora.toLocaleTimeString('pt-BR')}
          </div>
        </div>
      </div>

      {online === false && (
        <div className="hud-frame" style={{ textAlign: 'center', padding: '1.5rem' }}>
          <p style={{ fontSize: '0.85rem' }}>
            Sem telemetria. Inicie o núcleo: <code>python cli_python/api.py</code>.
          </p>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px,1fr) minmax(240px,1.1fr) minmax(220px,1fr)', gap: '1rem', alignItems: 'start' }}>
        {/* Esquerda: STATUS */}
        <div className="hud-frame">
          <div className="hud-label">Status do Candidato</div>
          <Stat k="Dias até a prova" v={plano?.dias_ate_prova ?? '—'} />
          <Stat k="Sequência" v={`${streak}d`} />
          <Stat k="Revisões devidas" v={plano?.revisoes_devidas ?? '—'} />
          <Stat k="Questões resolvidas" v={progresso?.total_respondidas ?? 0} />
          <Stat k="Acerto geral" v={`${progresso?.pct_geral ?? 0}%`} />
          <Stat k="Dias praticados" v={progresso?.dias_ativos ?? 0} />
        </div>

        {/* Centro: NÚCLEO / PRONTIDÃO */}
        <div className="hud-frame" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div className="hud-label">Prontidão</div>
          <svg viewBox="0 0 200 200" style={{ width: '100%', maxWidth: 230 }}>
            <circle cx="100" cy="100" r={R} fill="none" stroke="var(--hud-faint)" strokeWidth="10" />
            <circle
              cx="100" cy="100" r={R} fill="none" stroke="var(--hud)" strokeWidth="10" strokeLinecap="round"
              strokeDasharray={CIRC} strokeDashoffset={CIRC * (1 - prontidao / 100)}
              transform="rotate(-90 100 100)" style={{ filter: 'drop-shadow(0 0 6px var(--hud))', transition: 'stroke-dashoffset 0.8s' }}
            />
            <circle className="hud-ring" cx="100" cy="100" r="92" fill="none" stroke="var(--hud-dim)" strokeWidth="1" strokeDasharray="4 10" />
            <text x="100" y="96" textAnchor="middle" className="hud-glow" style={{ fontSize: '2.4rem', fontWeight: 800, fill: 'var(--hud)' }}>{prontidao}%</text>
            <text x="100" y="120" textAnchor="middle" style={{ fontSize: '0.6rem', letterSpacing: '0.2em', fill: '#9ad7e8' }}>MAESTRIA MÉDIA</text>
          </svg>
          <button onClick={onIrPraticar} className="btn btn-sm" style={{ marginTop: '0.75rem', background: 'transparent', border: '1px solid var(--hud)', color: 'var(--hud)', letterSpacing: '0.15em', boxShadow: '0 0 12px rgba(56,232,255,0.25)' }}>
            ▸ INICIAR PRÁTICA
          </button>
          <div style={{ fontSize: '0.72rem', marginTop: '0.6rem', opacity: 0.85 }}>
            Foco prioritário: <span className="hud-glow">{foco}</span>
          </div>
        </div>

        {/* Direita: RADAR */}
        <div className="hud-frame">
          <div className="hud-label">Radar de Inteligência</div>
          {intel.length === 0 ? (
            <p style={{ fontSize: '0.74rem', opacity: 0.7 }}>Sem sinais. Rode o coletor/radar.</p>
          ) : intel.slice(0, 4).map((n) => (
            <div key={n.arquivo} style={{ padding: '0.3rem 0', borderBottom: '1px solid var(--hud-faint)' }}>
              <div style={{ fontSize: '0.76rem', color: 'var(--hud)' }}>{n.titulo.slice(0, 40)}</div>
              <div style={{ fontSize: '0.68rem', opacity: 0.7 }}>{n.atualizado.slice(0, 10)}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Maestria por disciplina (largura total) */}
      <div className="hud-frame" style={{ marginTop: '1rem' }}>
        <div className="hud-label">Maestria por Disciplina (Elo)</div>
        {discs.length === 0 ? (
          <p style={{ fontSize: '0.76rem', opacity: 0.7 }}>Sem dados de prática — resolva questões para calibrar.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
            {discs.map((d) => {
              const pct = Math.round((d.acerto_esperado ?? 0) * 100);
              return (
                <div key={d.disciplina}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', marginBottom: 2 }}>
                    <span>{d.disciplina}</span><span className="hud-glow">{pct}% · {d.nivel}</span>
                  </div>
                  <div className="hud-bar"><span style={{ width: `${pct}%` }} /></div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
