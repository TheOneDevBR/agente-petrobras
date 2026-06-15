import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Target, Flame, Clock, CheckCircle2, XCircle, ChevronRight, RefreshCw, BookOpen, Sparkles } from 'lucide-react';
import { PerfilCandidato } from '../types';
import {
  praticaProxima, praticaResponder, praticaCoach, praticaClassificar,
  QuestaoPratica, FeedbackPratica,
} from '../utils/api';
import { DISCIPLINAS_PADRAO } from '../utils/storage';

interface PraticaTabProps {
  perfil: PerfilCandidato | null;
  backendUrl: string;
}

const LETRAS = ['A', 'B', 'C', 'D', 'E'];
const META_DIARIA = 12;

const ERROS = [
  { cat: 'C', label: 'Conteúdo', desc: 'não sabia a matéria' },
  { cat: 'A', label: 'Atenção', desc: 'li errado / desatenção' },
  { cat: 'B', label: 'Branco', desc: 'sabia mas travei' },
  { cat: 'T', label: 'Tempo', desc: 'faltou tempo' },
];

export const PraticaTab: React.FC<PraticaTabProps> = ({ perfil, backendUrl }) => {
  const [status, setStatus] = useState<'loading' | 'answering' | 'answered' | 'erro'>('loading');
  const [erroMsg, setErroMsg] = useState('');
  const [questao, setQuestao] = useState<QuestaoPratica | null>(null);
  const [escolha, setEscolha] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<FeedbackPratica | null>(null);
  const [coachTexto, setCoachTexto] = useState('');
  const [coachLoading, setCoachLoading] = useState(false);
  const [disciplina, setDisciplina] = useState('');
  const [tempo, setTempo] = useState(0);
  const [respondidas, setRespondidas] = useState(0);
  const [acertos, setAcertos] = useState(0);

  const inicioRef = useRef<number>(Date.now());
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const streak = perfil?.estado_psicológico_e_motivacional?.streak_dias_consecutivos ?? 0;

  const pararTimer = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  };

  const carregar = useCallback(async () => {
    pararTimer();
    setStatus('loading');
    setEscolha(null); setFeedback(null); setCoachTexto('');
    try {
      const q = await praticaProxima(backendUrl, disciplina);
      setQuestao(q);
      setTempo(0);
      inicioRef.current = Date.now();
      setStatus('answering');
    } catch (e) {
      setErroMsg(e instanceof Error ? e.message : 'falha');
      setStatus('erro');
    }
  }, [backendUrl, disciplina]);

  useEffect(() => { carregar(); }, [carregar]);

  // Timer enquanto responde
  useEffect(() => {
    if (status === 'answering') {
      timerRef.current = setInterval(() => {
        setTempo(Math.floor((Date.now() - inicioRef.current) / 1000));
      }, 1000);
      return pararTimer;
    }
  }, [status]);

  const responder = async (idx: number) => {
    if (!questao || status !== 'answering') return;
    pararTimer();
    setEscolha(idx);
    const tempoSeg = (Date.now() - inicioRef.current) / 1000;
    try {
      const fb = await praticaResponder(backendUrl, questao.id, idx, tempoSeg);
      setFeedback(fb);
      setRespondidas((n) => n + 1);
      if (fb.correta) setAcertos((n) => n + 1);
      setStatus('answered');
      // coach socrático (assíncrono, não bloqueia)
      setCoachLoading(true);
      praticaCoach(backendUrl, questao.id, idx)
        .then((t) => setCoachTexto(t))
        .finally(() => setCoachLoading(false));
    } catch (e) {
      setErroMsg(e instanceof Error ? e.message : 'falha ao responder');
      setStatus('erro');
    }
  };

  const classificarErro = async (cat: string) => {
    if (feedback) await praticaClassificar(backendUrl, feedback.disciplina, cat);
    carregar();
  };

  const fmtTempo = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  const pctSessao = respondidas > 0 ? Math.round((acertos / respondidas) * 100) : 0;

  // ── Estados de erro/carregamento ──
  if (status === 'erro') {
    return (
      <div className="panel" style={{ textAlign: 'center', padding: '2rem' }}>
        <XCircle size={40} style={{ color: 'var(--color-error)', margin: '0 auto 1rem' }} />
        <h3>Não consegui falar com o backend</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '0.5rem 0 1rem' }}>
          {erroMsg}. Inicie a API: <code>python cli_python/api.py</code> (e o Ollama).
          Configure a URL na aba Configurações.
        </p>
        <button onClick={carregar} className="btn btn-primary btn-sm">
          <RefreshCw size={14} /> Tentar de novo
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 820, margin: '0 auto' }}>
      {/* HEADER: hoje · streak · meta */}
      <div className="panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Target style={{ color: 'var(--color-primary)' }} />
          <strong>Recall espaçado</strong>
        </div>
        <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'center', fontSize: '0.85rem', flexWrap: 'wrap' }}>
          <span title="respondidas nesta sessão">HOJE: <strong>{respondidas}</strong> · {pctSessao}%</span>
          <span className="streak-counter" title="dias seguidos"><Flame size={15} /> {streak}d</span>
          <span title="meta diária">meta {Math.min(respondidas, META_DIARIA)}/{META_DIARIA}</span>
          {questao && questao.revisoes_pendentes > 0 && (
            <span title="revisões espaçadas devidas" style={{ color: 'var(--color-warning)' }}>
              ↻ {questao.revisoes_pendentes} revisões
            </span>
          )}
        </div>
      </div>

      {/* Filtro de disciplina */}
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Foco:</span>
        <select
          value={disciplina}
          onChange={(e) => setDisciplina(e.target.value)}
          className="form-input"
          style={{ maxWidth: 320, padding: '0.35rem 0.6rem', fontSize: '0.82rem' }}
        >
          <option value="">Todas as disciplinas (adaptativo)</option>
          {DISCIPLINAS_PADRAO.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      {/* CARD DA QUESTÃO */}
      <div className="panel" style={{ minHeight: 240 }}>
        {status === 'loading' && (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
            <RefreshCw size={28} className="spin" style={{ marginBottom: '0.5rem' }} />
            <p>Selecionando a melhor questão para você...</p>
          </div>
        )}

        {questao && status !== 'loading' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem', marginBottom: '0.75rem' }}>
              <span style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                <span className="badge badge-green">{questao.disciplina}</span>
                {questao.tipo === 'revisao' && (
                  <span className="badge" style={{ background: 'rgba(245,158,11,0.15)', color: '#fbbf24' }} title="revisão espaçada agendada">
                    ↻ REVISÃO
                  </span>
                )}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', color: status === 'answering' ? 'var(--text-secondary)' : 'var(--text-muted)' }}>
                <Clock size={14} /> {fmtTempo(tempo)}
              </span>
            </div>

            <p style={{ fontSize: '0.95rem', fontWeight: 500, marginBottom: '1rem', whiteSpace: 'pre-line', lineHeight: 1.5 }}>
              {questao.pergunta}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {questao.opcoes.map((op, idx) => {
                const ehCorreta = feedback && idx === feedback.correta_idx;
                const ehEscolhida = escolha === idx;
                let estilo: React.CSSProperties = { textAlign: 'left', display: 'flex', gap: '0.6rem', alignItems: 'flex-start', padding: '0.65rem' };
                if (status === 'answered') {
                  if (ehCorreta) estilo = { ...estilo, borderColor: 'var(--color-primary)', background: 'rgba(16,185,129,0.12)' };
                  else if (ehEscolhida) estilo = { ...estilo, borderColor: 'var(--color-error)', background: 'rgba(239,68,68,0.12)' };
                }
                return (
                  <button
                    key={idx}
                    onClick={() => responder(idx)}
                    disabled={status === 'answered'}
                    className="btn btn-secondary btn-sm"
                    style={estilo}
                  >
                    <strong style={{ color: 'var(--color-primary)' }}>{LETRAS[idx]})</strong>
                    <span style={{ fontSize: '0.85rem' }}>{op}</span>
                    {status === 'answered' && ehCorreta && <CheckCircle2 size={16} style={{ color: 'var(--color-primary)', marginLeft: 'auto' }} />}
                    {status === 'answered' && ehEscolhida && !ehCorreta && <XCircle size={16} style={{ color: 'var(--color-error)', marginLeft: 'auto' }} />}
                  </button>
                );
              })}
            </div>

            {status === 'answering' && (
              <button onClick={carregar} className="btn btn-secondary btn-sm" style={{ marginTop: '0.75rem', color: 'var(--text-muted)' }}>
                pular questão
              </button>
            )}
          </>
        )}
      </div>

      {/* FEEDBACK */}
      {status === 'answered' && feedback && (
        <div className="panel" style={{ borderLeft: `4px solid ${feedback.correta ? 'var(--color-primary)' : 'var(--color-error)'}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            {feedback.correta
              ? <><CheckCircle2 style={{ color: 'var(--color-primary)' }} /> <strong>Correto!</strong></>
              : <><XCircle style={{ color: 'var(--color-error)' }} /> <strong>Resposta: {LETRAS[feedback.correta_idx]}</strong></>}
            {feedback.revisar_em && (
              <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                ↻ revisar em {feedback.revisar_em}
              </span>
            )}
          </div>

          {feedback.explicacao && (
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              {feedback.explicacao}
            </p>
          )}

          {/* Coach socrático (assíncrono) */}
          {(coachLoading || coachTexto) && (
            <div style={{ background: 'var(--color-primary-glow)', borderRadius: 'var(--radius-sm)', padding: '0.6rem', margin: '0.5rem 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.7rem', color: 'var(--color-primary)', marginBottom: '0.25rem' }}>
                <Sparkles size={13} /> COACH {coachLoading && '· pensando...'}
              </div>
              {coachTexto && <p style={{ fontSize: '0.82rem', whiteSpace: 'pre-line' }}>{coachTexto}</p>}
            </div>
          )}

          {/* Trecho da apostila (RAG) */}
          {feedback.fonte && (
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', borderTop: '1px dashed var(--border-color)', paddingTop: '0.5rem', marginTop: '0.5rem' }}>
              <BookOpen size={13} style={{ verticalAlign: 'middle', marginRight: 4 }} />
              Da sua apostila: <em>{feedback.fonte}…</em>
            </div>
          )}

          {/* Classificação de erro (só se errou) */}
          {!feedback.correta ? (
            <div style={{ marginTop: '0.75rem' }}>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                Por que você errou? (ajuda o coach a te direcionar)
              </p>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                {ERROS.map((e) => (
                  <button key={e.cat} onClick={() => classificarErro(e.cat)} className="btn btn-secondary btn-sm" title={e.desc}>
                    {e.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <button onClick={carregar} className="btn btn-primary btn-sm active-pulse" style={{ marginTop: '0.75rem' }}>
              Próxima <ChevronRight size={16} />
            </button>
          )}
        </div>
      )}
    </div>
  );
};
