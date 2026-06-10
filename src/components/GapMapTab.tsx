import React from 'react';
import { 
  BarChart3, 
  HelpCircle, 
  AlertCircle, 
  TrendingUp, 
  Clock, 
  Calendar,
  AlertTriangle,
  FileSpreadsheet
} from 'lucide-react';
import { PerfilCandidato } from '../types';
import { DISCIPLINAS_PADRAO, calcularViabilidade } from '../utils/storage';

interface GapMapTabProps {
  perfil: PerfilCandidato;
}

export const GapMapTab: React.FC<GapMapTabProps> = ({ perfil }) => {
  const cargo = perfil.cargo_alvo || 'Técnico (nível médio)';
  const totalQuestoes = perfil.total_questões_resolvidas || 0;

  // Calculo de viabilidade
  const viabilidade = calcularViabilidade(
    perfil.total_dias_até_prova || 90,
    perfil.horas_dia_útil_reais || 3,
    perfil.horas_sábado_reais || 6,
    perfil.horas_domingo_reais || 4,
    totalQuestoes > 0 ? 'base_parcial' : 'base_zero'
  );

  // Geração de cronograma dinâmico baseado na data atual e dias restantes
  const diasTotais = perfil.total_dias_até_prova || 90;
  const hoje = new Date();
  
  const f1Dias = Math.round(diasTotais * 0.25);
  const f2Dias = Math.round(diasTotais * 0.40);
  const f3Dias = Math.round(diasTotais * 0.25);
  const f4Dias = diasTotais - (f1Dias + f2Dias + f3Dias); // restante (~10%)

  const addDays = (date: Date, days: number): string => {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  };

  const cronograma = [
    { 
      fase: 'FUNDAÇÃO (Fase 1)', 
      datas: `${addDays(hoje, 0)} → ${addDays(hoje, f1Dias)}`,
      foco: 'Conceitos base de alto impacto, português regência e lógica proposicional.',
      status: perfil.fase_atual === 'FUNDAÇÃO' ? 'Ativo' : 'Concluído'
    },
    { 
      fase: 'DOMÍNIO (Fase 2)', 
      datas: `${addDays(hoje, f1Dias + 1)} → ${addDays(hoje, f1Dias + f2Dias)}`,
      foco: 'Resolução intensiva por tema, transição para camadas mistas (§7).',
      status: perfil.fase_atual === 'DOMÍNIO' ? 'Ativo' : perfil.fase_atual === 'FUNDAÇÃO' ? 'Pendente' : 'Concluído'
    },
    { 
      fase: 'CONSOLIDAÇÃO (Fase 3)', 
      datas: `${addDays(hoje, f1Dias + f2Dias + 1)} → ${addDays(hoje, f1Dias + f2Dias + f3Dias)}`,
      foco: 'Fechamento de lacunas criticas, simulados de 4h cronometrados.',
      status: perfil.fase_atual === 'CONSOLIDAÇÃO' ? 'Ativo' : (perfil.fase_atual === 'FUNDAÇÃO' || perfil.fase_atual === 'DOMÍNIO') ? 'Pendente' : 'Concluído'
    },
    { 
      fase: 'SPRINT FINAL (Fase 4)', 
      datas: `${addDays(hoje, f1Dias + f2Dias + f3Dias + 1)} → Prova (${perfil.data_prova_confirmada})`,
      foco: 'Revisão Anki exclusiva, sono de 8h, zero teoria nova, alinhamento psicológico.',
      status: perfil.fase_atual === 'SPRINT' || perfil.fase_atual === 'EMERGÊNCIA' ? 'Ativo' : 'Pendente'
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      
      {/* SEÇÃO 1: MAPA DE LACUNAS */}
      <div className="panel" style={{ borderLeft: '4px solid var(--color-primary)' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <BarChart3 style={{ color: 'var(--color-primary)' }} />
          <span>Mapa de Lacunas Calibrado (Autoavaliação vs. Performance Real)</span>
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
          Este mapa cruza sua percepção de conhecimento (Auto) com seus dados reais de questões (Real). Gaps negativos (🔴) indicam prioridade cirúrgica imediata de estudo.
        </p>

        <div className="table-wrapper">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Disciplina</th>
                <th style={{ textAlign: 'center' }}>Auto (0-10)</th>
                <th style={{ textAlign: 'center' }}>Real (%)</th>
                <th style={{ textAlign: 'center' }}>Gap</th>
                <th style={{ textAlign: 'center' }}>Prioridade</th>
              </tr>
            </thead>
            <tbody>
              {DISCIPLINAS_PADRAO.map(disc => {
                const perf = perfil.histórico_acerto_por_disciplina[disc];
                const auto = (perf?.baseline_diagnóstico || 50) / 10; // converte de baseline %
                
                // Média real de acertos das semanas recentes ou baseline
                const acertos = perf?.acerto_semana || [];
                const real = acertos.length > 0 ? acertos[acertos.length - 1] : (perf?.baseline_diagnóstico ?? 50);
                
                // O gap compara a performance real com a meta operacional do cargo
                const targetMeta = perfil.meta_e_calibração.meta_operacional_de_acerto;
                const gapVal = Math.round(real - targetMeta);

                let prioBadge = <span className="badge badge-green">🟢 Domínio</span>;
                if (gapVal < -15) {
                  prioBadge = <span className="badge badge-red">🔴 Crítico</span>;
                } else if (gapVal < 0) {
                  prioBadge = <span className="badge badge-yellow">🟡 Atenção</span>;
                }

                return (
                  <tr key={disc}>
                    <td style={{ fontWeight: 600 }}>{disc}</td>
                    <td style={{ textAlign: 'center', fontWeight: 700, color: 'var(--text-secondary)' }}>{auto.toFixed(1)}</td>
                    <td style={{ textAlign: 'center', fontWeight: 700 }}>{real}%</td>
                    <td style={{ 
                      textAlign: 'center', 
                      fontWeight: 700, 
                      color: gapVal >= 0 ? 'var(--color-primary)' : 'var(--color-error)'
                    }}>
                      {gapVal >= 0 ? `+${gapVal}%` : `${gapVal}%`}
                    </td>
                    <td style={{ textAlign: 'center' }}>{prioBadge}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* SEÇÃO 2: EQUAÇÃO DE VIABILIDADE E CRONOGRAMA */}
      <div className="grid-2">
        {/* EQUAÇÃO DE VIABILIDADE */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileSpreadsheet style={{ color: 'var(--color-warning)' }} />
            <span>Equação de Viabilidade Horária</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem', fontSize: '0.9rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Horas Líquidas Disponíveis:</span>
              <strong style={{ color: 'var(--text-primary)' }}>{viabilidade.horasDisponiveis} horas</strong>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem', fontSize: '0.9rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Horas Necessárias Estimadas:</span>
              <strong style={{ color: 'var(--text-primary)' }}>{viabilidade.horasNecessarias} horas</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.4rem', fontSize: '0.9rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Saldo Operacional:</span>
              <strong style={{ color: viabilidade.saldo >= 0 ? 'var(--color-primary)' : 'var(--color-error)' }}>
                {viabilidade.saldo >= 0 ? `+${viabilidade.saldo} horas` : `${viabilidade.saldo} horas`}
              </strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.4rem', fontSize: '0.9rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Veredicto Clínico:</span>
              <span className="badge" style={{
                backgroundColor: viabilidade.veredicto === 'CONFORTÁVEL' ? 'rgba(16,185,129,0.15)' : viabilidade.veredicto === 'AJUSTADO' ? 'rgba(59,130,246,0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: viabilidade.veredicto === 'CONFORTÁVEL' ? '#6ee7b7' : viabilidade.veredicto === 'AJUSTADO' ? '#93c5fd' : '#fca5a5'
              }}>{viabilidade.veredicto}</span>
            </div>
          </div>

          {viabilidade.saldo < 0 && (
            <div className="alert alert-warning" style={{ margin: 0, display: 'flex', gap: '0.5rem', padding: '0.75rem' }}>
              <AlertTriangle size={18} style={{ flexShrink: 0 }} />
              <div style={{ fontSize: '0.75rem', lineHeight: 1.4 }}>
                <strong>DÉFICIT DETECTADO:</strong> Você tem menos horas disponíveis do que o recomendado para fechar o edital base zero. O sistema ativou o modo <strong>{viabilidade.modoAtivado}</strong> (Curta Duração). Cortaremos tópicos com menor relevância histórica nas questões (Pareto §6).
              </div>
            </div>
          )}
        </div>

        {/* CRONOGRAMA MACRO */}
        <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Calendar style={{ color: 'var(--color-info)' }} />
            <span>Cronograma Macro Baseado em Datas Reais</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {cronograma.map((item, idx) => (
              <div 
                key={idx} 
                style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  gap: '0.2rem',
                  padding: '0.65rem 0.85rem',
                  background: item.status === 'Ativo' ? 'var(--color-primary-glow)' : 'rgba(15,23,42,0.3)',
                  border: item.status === 'Ativo' ? '1px solid rgba(16,185,129,0.3)' : '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 700, color: item.status === 'Ativo' ? 'var(--color-primary)' : 'var(--text-primary)' }}>
                    {item.fase}
                  </span>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                    {item.datas}
                  </span>
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>
                  Foco: {item.foco}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

    </div>
  );
};
