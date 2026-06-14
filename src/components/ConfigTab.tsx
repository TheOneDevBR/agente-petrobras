import React, { useState } from 'react';
import {
  Trash2,
  Server,
  Check,
  User,
  Plug,
} from 'lucide-react';
import { PerfilCandidato, ConfigGlobal } from '../types';
import { limparTudo } from '../utils/storage';
import { pingBackend } from '../utils/api';

interface ConfigTabProps {
  perfil: PerfilCandidato | null;
  onSalvarPerfil: (novoPerfil: PerfilCandidato) => void;
  config: ConfigGlobal;
  onSalvarConfig: (novaConfig: ConfigGlobal) => void;
}

export const ConfigTab: React.FC<ConfigTabProps> = ({
  perfil,
  onSalvarPerfil,
  config,
  onSalvarConfig
}) => {
  const [backendUrl, setBackendUrl] = useState(config.backendUrl);
  const [editingPerfil, setEditingPerfil] = useState<Partial<PerfilCandidato>>(perfil || {});
  const [statusConexao, setStatusConexao] = useState<'idle' | 'testando' | 'ok' | 'erro'>('idle');
  const [statusDetalhe, setStatusDetalhe] = useState('');

  const handleSaveConfig = (e: React.FormEvent) => {
    e.preventDefault();
    onSalvarConfig({
      ...config,
      backendUrl: backendUrl.trim()
    });
    alert("Configurações salvas com sucesso!");
  };

  const handleTestarConexao = async () => {
    setStatusConexao('testando');
    setStatusDetalhe('');
    const r = await pingBackend(backendUrl.trim());
    setStatusConexao(r.ok ? 'ok' : 'erro');
    setStatusDetalhe(r.detalhe);
  };

  const handleReset = () => {
    if (window.confirm("ATENÇÃO: Isso irá apagar todo o seu histórico de questões, flashcards e dados do perfil de forma permanente! Deseja mesmo reiniciar seu treinamento?")) {
      limparTudo();
      window.location.reload();
    }
  };

  const handleUpdatePerfil = (e: React.FormEvent) => {
    e.preventDefault();
    if (!perfil) return;

    const atualizado: PerfilCandidato = {
      ...perfil,
      horas_dia_útil_reais: Number(editingPerfil.horas_dia_útil_reais || perfil.horas_dia_útil_reais),
      horas_sábado_reais: Number(editingPerfil.horas_sábado_reais || perfil.horas_sábado_reais),
      horas_domingo_reais: Number(editingPerfil.horas_domingo_reais || perfil.horas_domingo_reais),
      total_dias_até_prova: Number(editingPerfil.total_dias_até_prova || perfil.total_dias_até_prova),
    };

    onSalvarPerfil(atualizado);
    alert("Perfil de estudos ajustado com sucesso!");
  };

  return (
    <div className="grid-2">
      
      {/* PAINEL DE CONEXÃO COM O BACKEND (Ollama local) */}
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
          <Server style={{ color: 'var(--color-primary)' }} />
          <span>Conexão com o AgentePetrobras (IA Local)</span>
        </h3>

        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          O Coach Chat conversa com o backend FastAPI rodando o LLM local (Ollama).
          Deixe em branco para usar o proxy padrão <code>/api</code> (dev). Em produção,
          informe a URL da API (ex: <code>http://127.0.0.1:8000</code>).
          Inicie o backend com <code>python cli_python/api.py</code>.
        </p>

        <form onSubmit={handleSaveConfig} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">URL da API (opcional)</label>
            <input
              type="text"
              value={backendUrl}
              onChange={e => setBackendUrl(e.target.value)}
              placeholder="http://127.0.0.1:8000 (ou vazio = /api)"
              className="form-input"
            />
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <button type="submit" className="btn btn-primary btn-sm">
              <Check size={14} /> Salvar
            </button>
            <button
              type="button"
              onClick={handleTestarConexao}
              className="btn btn-secondary btn-sm"
              disabled={statusConexao === 'testando'}
            >
              <Plug size={14} /> {statusConexao === 'testando' ? 'Testando...' : 'Testar Conexão'}
            </button>
            {statusConexao === 'ok' && (
              <span className="badge badge-green" style={{ color: '#6ee7b7' }}>● Online — {statusDetalhe}</span>
            )}
            {statusConexao === 'erro' && (
              <span className="badge" style={{ color: '#fca5a5', background: 'rgba(239,68,68,0.15)' }}>● Offline — {statusDetalhe}</span>
            )}
          </div>
        </form>
      </div>

      {/* PAINEL DE CONTROLE DE PERFIL & DADOS */}
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
          <User style={{ color: 'var(--color-warning)' }} />
          <span>Ajustes Rápidos do Perfil</span>
        </h3>

        {perfil ? (
          <form onSubmit={handleUpdatePerfil} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">H. Dia Útil</label>
                <input 
                  type="number" 
                  value={editingPerfil.horas_dia_útil_reais ?? perfil.horas_dia_útil_reais}
                  onChange={e => setEditingPerfil(prev => ({ ...prev, horas_dia_útil_reais: Number(e.target.value) }))}
                  className="form-input" 
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">H. Sábados</label>
                <input 
                  type="number" 
                  value={editingPerfil.horas_sábado_reais ?? perfil.horas_sábado_reais}
                  onChange={e => setEditingPerfil(prev => ({ ...prev, horas_sábado_reais: Number(e.target.value) }))}
                  className="form-input" 
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">H. Domingos</label>
                <input 
                  type="number" 
                  value={editingPerfil.horas_domingo_reais ?? perfil.horas_domingo_reais}
                  onChange={e => setEditingPerfil(prev => ({ ...prev, horas_domingo_reais: Number(e.target.value) }))}
                  className="form-input" 
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label">Dias até Prova</label>
                <input 
                  type="number" 
                  value={editingPerfil.total_dias_até_prova ?? perfil.total_dias_até_prova}
                  onChange={e => setEditingPerfil(prev => ({ ...prev, total_dias_até_prova: Number(e.target.value) }))}
                  className="form-input" 
                />
              </div>
            </div>
            <button type="submit" className="btn btn-primary btn-sm" style={{ alignSelf: 'flex-start' }}>
              Ajustar Perfil
            </button>
          </form>
        ) : (
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Nenhum perfil ativo. Por favor, conclua o Onboarding no Coach Chat primeiro.</p>
        )}
      </div>

      {/* PAINEL DE PERIGO / RESET */}
      <div className="panel" style={{ gridColumn: 'span 2', display: 'flex', flexDirection: 'column', gap: '1rem', borderLeft: '4px solid var(--color-error)' }}>
        <h3 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-error)' }}>
          <Trash2 />
          <span>Zona de Perigo</span>
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Exclui todos os dados gerados de progresso acadêmico. Útil se você deseja iniciar uma preparação para outro cargo, recalcular baselines ou reiniciar o quiz de diagnóstico de viabilidade.
        </p>
        <button onClick={handleReset} className="btn btn-danger btn-sm" style={{ alignSelf: 'flex-start' }}>
          Reiniciar Todo o Treinamento
        </button>
      </div>

    </div>
  );
};
