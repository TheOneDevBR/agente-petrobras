import React, { useState } from 'react';
import { 
  Settings, 
  Trash2, 
  Key, 
  Check, 
  User,
  Info,
  RefreshCw
} from 'lucide-react';
import { PerfilCandidato, ConfigGlobal } from '../types';
import { limparTudo, obterConfigLocal, salvarConfigLocal } from '../utils/storage';

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
  const [apiKey, setApiKey] = useState(config.geminiApiKey);
  const [editingPerfil, setEditingPerfil] = useState<Partial<PerfilCandidato>>(perfil || {});

  const handleSaveConfig = (e: React.FormEvent) => {
    e.preventDefault();
    onSalvarConfig({
      ...config,
      geminiApiKey: apiKey
    });
    alert("Configurações salvas com sucesso!");
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
      
      {/* PAINEL DE INTEGRAÇÃO DE INTELIGÊNCIA */}
      <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h3 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
          <Key style={{ color: 'var(--color-primary)' }} />
          <span>Chave de API do Gemini (IA Opcional)</span>
        </h3>
        
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          Insira sua chave de API do Gemini para permitir discussões reais com o AgentePetrobras v4.0 no Coach Chat. A chave é salva apenas localmente no seu navegador.
        </p>

        <form onSubmit={handleSaveConfig} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">API Key do Google Gemini</label>
            <input 
              type="password" 
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="AIzaSy..." 
              className="form-input" 
            />
          </div>
          <button type="submit" className="btn btn-primary btn-sm" style={{ alignSelf: 'flex-start' }}>
            <Check size={14} /> Salvar Chave API
          </button>
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
