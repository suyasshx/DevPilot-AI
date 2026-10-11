import React from 'react';
import {
  Layers,
  FileCode,
  BookOpen,
  PlayCircle,
  Activity,
  PlusCircle,
  CheckCircle2,
  FolderGit2,
} from 'lucide-react';
import { Project } from '../types/api';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  projects: Project[];
  selectedProject: Project | null;
  onSelectProject: (p: Project) => void;
  onOpenNewProjectModal: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  setCurrentTab,
  projects,
  selectedProject,
  onSelectProject,
  onOpenNewProjectModal,
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: Layers },
    { id: 'specs', label: 'Specs & Endpoints', icon: FileCode },
    { id: 'knowledge', label: 'Knowledge & Docs', icon: BookOpen },
    { id: 'workflow', label: 'Autonomous QA Agent', icon: PlayCircle },
    { id: 'runs', label: 'Execution Runs', icon: Activity },
  ];

  return (
    <aside className="sidebar" id="app-sidebar">
      {/* Brand Header */}
      <div style={{ padding: '24px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #0284c7 0%, #3b82f6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(56, 189, 248, 0.4)',
            }}
          >
            <FolderGit2 size={20} color="#fff" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.1rem', letterSpacing: '-0.3px', color: '#fff' }}>
              DevPilot <span style={{ color: 'var(--accent-cyan)' }}>AI</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Universal API QA Platform
            </div>
          </div>
        </div>
      </div>

      {/* Project Switcher */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)', fontWeight: 700 }}>
            Active Project
          </span>
          <button
            id="btn-new-project-open"
            onClick={onOpenNewProjectModal}
            className="btn btn-outline"
            style={{ padding: '3px 8px', fontSize: '0.75rem', gap: '4px' }}
            title="Create New Project"
          >
            <PlusCircle size={13} />
            <span>New</span>
          </button>
        </div>

        <select
          id="select-project-dropdown"
          className="select"
          style={{ fontSize: '0.82rem', padding: '8px 10px' }}
          value={selectedProject?.id || ''}
          onChange={(e) => {
            const p = projects.find((item) => item.id === e.target.value);
            if (p) onSelectProject(p);
          }}
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
          {projects.length === 0 && <option value="">No projects found</option>}
        </select>
      </div>

      {/* Navigation Links */}
      <nav style={{ padding: '16px 12px', flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              id={`nav-${item.id}`}
              onClick={() => setCurrentTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '10px 14px',
                borderRadius: '8px',
                border: 'none',
                background: isActive ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                color: isActive ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.88rem',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer Status */}
      <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-green-bright)' }} className="animate-pulse" />
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>System Operational</span>
        </div>
      </div>
    </aside>
  );
};
