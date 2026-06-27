import React, { useState, useEffect } from 'react';
import { 
  Flame, 
  Target, 
  HelpCircle, 
  AlertCircle,
  Menu,
  Sparkles,
  BookOpen
} from 'lucide-react';
import { Sidebar } from './components/Sidebar';
import { DashboardTab } from './components/DashboardTab';
import { OnboardingChatTab } from './components/OnboardingChatTab';
import { QuestionBankTab } from './components/QuestionBankTab';
import { PraticaTab } from './components/PraticaTab';
import { MaestriaTab } from './components/MaestriaTab';
import { PlanoHojeTab } from './components/PlanoHojeTab';
import { RadarTab } from './components/RadarTab';
import { DashboardLivePanel } from './components/DashboardLivePanel';
import { SimuladoTab } from './components/SimuladoTab';
import { ProgressoTab } from './components/ProgressoTab';
import { JarvisTab } from './components/JarvisTab';
import { RedacaoTab } from './components/RedacaoTab';
import { GapMapTab } from './components/GapMapTab';
import { FlashcardsTab } from './components/FlashcardsTab';
import { ConfigTab } from './components/ConfigTab';
import { PerfilCandidato, ConfigGlobal } from './types';
import { obterPerfilLocal, salvarPerfilLocal, obterConfigLocal, salvarConfigLocal } from './utils/storage';
import { obterPerfilApi, salvarPerfilApi } from './utils/api';

export default function App() {
  const [perfil, setPerfil] = useState<PerfilCandidato | null>(null);
  const [config, setConfig] = useState<ConfigGlobal>({ backendUrl: '', onboarded: false });
  const [activeTab, setActiveTab] = useState<string>('chat');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Load local state on mount, try API sync if backend available
  useEffect(() => {
    const localPerfil = obterPerfilLocal();
    const localConfig = obterConfigLocal();

    setPerfil(localPerfil);
    setConfig(localConfig);

    // Try loading profile from backend (async)
    (async () => {
      const url = localConfig.backendUrl;
      if (!url) return;
      const apiPerfil = await obterPerfilApi(url);
      if (apiPerfil && apiPerfil.cargo_alvo) {
        setPerfil(apiPerfil);
        salvarPerfilLocal(apiPerfil);
      }
    })();

    if (localPerfil && localPerfil.cargo_alvo) {
      setActiveTab('central');
    } else {
      setActiveTab('chat');
    }
  }, []);

  const handleSalvarPerfil = async (novoPerfil: PerfilCandidato) => {
    salvarPerfilLocal(novoPerfil);
    setPerfil(novoPerfil);
    // Persist to backend if configured
    const url = config?.backendUrl;
    if (url) {
      await salvarPerfilApi(url, novoPerfil);
    }
  };

  const handleSalvarConfig = (novaConfig: ConfigGlobal) => {
    salvarConfigLocal(novaConfig);
    setConfig(novaConfig);
  };

  const handleSetActiveTab = (tab: string) => {
    const onboarded = perfil && perfil.cargo_alvo;
    if (!onboarded && tab !== 'chat' && tab !== 'config') {
      alert("⚠️ Diagnóstico Requerido: Conclua o seu Diagnóstico de Entrada no Coach Chat para desbloquear todas as abas operacionais do sistema!");
      return;
    }
    setActiveTab(tab);
  };

  // Render content according to tab
  const renderTabContent = () => {
    if (!perfil || !perfil.cargo_alvo) {
      if (activeTab === 'config') {
        return (
          <ConfigTab 
            perfil={perfil} 
            onSalvarPerfil={handleSalvarPerfil} 
            config={config} 
            onSalvarConfig={handleSalvarConfig} 
          />
        );
      }
      return (
        <OnboardingChatTab
          perfil={perfil}
          onSalvarPerfil={handleSalvarPerfil}
          backendUrl={config.backendUrl}
        />
      );
    }

    switch (activeTab) {
      case 'dashboard':
        return (
          <>
            <DashboardLivePanel backendUrl={config.backendUrl} onIrPraticar={() => handleSetActiveTab('praticar')} />
            <DashboardTab perfil={perfil} onSalvarPerfil={handleSalvarPerfil} />
          </>
        );
      case 'central':
        return <JarvisTab perfil={perfil} backendUrl={config.backendUrl} onIrPraticar={() => handleSetActiveTab('praticar')} />;
      case 'hoje':
        return <PlanoHojeTab perfil={perfil} backendUrl={config.backendUrl} onIrPraticar={() => handleSetActiveTab('praticar')} />;
      case 'praticar':
        return <PraticaTab perfil={perfil} backendUrl={config.backendUrl} />;
      case 'simulado':
        return <SimuladoTab backendUrl={config.backendUrl} />;
      case 'redacao':
        return <RedacaoTab backendUrl={config.backendUrl} />;
      case 'maestria':
        return <MaestriaTab perfil={perfil} backendUrl={config.backendUrl} onIrPraticar={() => handleSetActiveTab('praticar')} />;
      case 'progresso':
        return <ProgressoTab backendUrl={config.backendUrl} />;
      case 'radar':
        return <RadarTab backendUrl={config.backendUrl} />;
      case 'chat':
        return (
          <OnboardingChatTab
            perfil={perfil}
            onSalvarPerfil={handleSalvarPerfil}
            backendUrl={config.backendUrl}
          />
        );
      case 'lacunas':
        return <GapMapTab perfil={perfil} />;
      case 'questoes':
        return <QuestionBankTab perfil={perfil} onSalvarPerfil={handleSalvarPerfil} />;
      case 'flashcards':
        return <FlashcardsTab />;
      case 'config':
        return (
          <ConfigTab 
            perfil={perfil} 
            onSalvarPerfil={handleSalvarPerfil} 
            config={config} 
            onSalvarConfig={handleSalvarConfig} 
          />
        );
      default:
        return <DashboardTab perfil={perfil} onSalvarPerfil={handleSalvarPerfil} />;
    }
  };

  const hasActiveProfile = perfil && perfil.cargo_alvo;

  return (
    <div className="app-container">
      
      {/* SIDEBAR NAVIGATION */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={handleSetActiveTab} 
        perfil={perfil} 
        collapsed={sidebarCollapsed} 
        setCollapsed={setSidebarCollapsed} 
      />

      {/* MAIN CONTAINER */}
      <div className="main-content">
        
        {/* HEADER BAR */}
        <header className="app-header">
          <div className="header-title-section">
            <h1 style={{ fontSize: '1.2rem', fontWeight: 700 }}>
              {activeTab === 'central' && 'Central Tática'}
              {activeTab === 'hoje' && 'Plano de Hoje'}
              {activeTab === 'dashboard' && 'Painel Tático Geral'}
              {activeTab === 'praticar' && 'Prática — Recall Espaçado'}
              {activeTab === 'simulado' && 'Simulado Completo'}
              {activeTab === 'redacao' && 'Avaliador de Redação'}
              {activeTab === 'maestria' && 'Mapa de Maestria'}
              {activeTab === 'progresso' && 'Progresso'}
              {activeTab === 'radar' && 'Radar de Inteligência'}
              {activeTab === 'chat' && 'AgentePetrobras Coach Chat'}
              {activeTab === 'lacunas' && 'Mapa de Lacunas & Cronograma'}
              {activeTab === 'questoes' && 'Banco de Questões CESGRANRIO'}
              {activeTab === 'flashcards' && 'Baralho de Flashcards (Anki)'}
              {activeTab === 'config' && 'Configurações do Sistema'}
            </h1>
            
            {hasActiveProfile && (
              <div className="status-badge" title="Fase de preparação atual">
                Fase {perfil.fase_atual}
              </div>
            )}
          </div>

          <div className="header-user-section">
            {hasActiveProfile && (
              <>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Meta: <strong style={{ color: 'var(--color-primary)' }}>{perfil.meta_e_calibração.meta_operacional_de_acerto}%</strong>
                </div>
                
                <div className="streak-counter" title="Dias seguidos de estudo">
                  <Flame size={16} />
                  <span>{perfil.estado_psicológico_e_motivacional.streak_dias_consecutivos}d Streak</span>
                </div>
              </>
            )}
            
            {!hasActiveProfile && (
              <div className="status-badge" style={{ color: 'var(--color-warning)', borderColor: 'rgba(245,158,11,0.2)' }}>
                DIAGNÓSTICO INICIAL PENDENTE
              </div>
            )}
          </div>
        </header>

        {/* WORKSPACE */}
        <main className="workspace">
          {renderTabContent()}
        </main>

      </div>

    </div>
  );
}
