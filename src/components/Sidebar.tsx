import React from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  BarChart3,
  Brain,
  Settings,
  User,
  Target,
  FileText,
  Award,
  CalendarCheck,
  Radar,
  LineChart,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { PerfilCandidato } from '../types';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  perfil: PerfilCandidato | null;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  perfil,
  collapsed,
  setCollapsed
}) => {
  const menuItems = [
    { id: 'hoje', label: 'Plano de Hoje', icon: CalendarCheck },
    { id: 'dashboard', label: 'Painel Geral', icon: LayoutDashboard },
    { id: 'praticar', label: 'Praticar (Recall)', icon: Target },
    { id: 'simulado', label: 'Simulado', icon: FileText },
    { id: 'maestria', label: 'Maestria', icon: Award },
    { id: 'progresso', label: 'Progresso', icon: LineChart },
    { id: 'radar', label: 'Radar (Novidades)', icon: Radar },
    { id: 'chat', label: 'Coach Chat', icon: MessageSquare },
    { id: 'lacunas', label: 'Diagnóstico & Lacunas', icon: BarChart3 },
    { id: 'questoes', label: 'Banco de Questões', icon: BookOpen },
    { id: 'flashcards', label: 'Micro-Anki', icon: Brain },
    { id: 'config', label: 'Configurações', icon: Settings },
  ];

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="logo-icon">P4</div>
        {!collapsed && <span className="logo-text">AgentePetrobras</span>}
      </div>

      <nav className="sidebar-menu">
        {menuItems.map((item) => {
          const IconComponent = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`menu-item ${activeTab === item.id ? 'active' : ''}`}
              title={collapsed ? item.label : undefined}
            >
              <IconComponent size={20} className="menu-item-icon" />
              {!collapsed && <span>{item.label}</span>}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <button 
          onClick={() => setCollapsed(!collapsed)} 
          className="menu-item"
          style={{ justifyContent: collapsed ? 'center' : 'space-between', padding: '0.5rem' }}
          title={collapsed ? 'Expandir Menu' : 'Recolher Menu'}
        >
          {collapsed ? <ChevronRight size={20} /> : (
            <>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Recolher</span>
              <ChevronLeft size={20} />
            </>
          )}
        </button>
        
        {perfil && perfil.cargo_alvo && !collapsed && (
          <div style={{ marginTop: '1rem', padding: '0.5rem', background: 'var(--bg-hover)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '32px', height: '32px', background: 'var(--color-primary-glow)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <User size={16} style={{ color: 'var(--color-primary)' }} />
            </div>
            <div style={{ overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
              <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0, textOverflow: 'ellipsis', overflow: 'hidden' }}>
                {perfil.cargo_alvo}
              </p>
              <p style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', margin: 0 }}>
                Fase: {perfil.fase_atual}
              </p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
