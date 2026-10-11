import React, { useState } from 'react';
import { X, FolderPlus } from 'lucide-react';
import { api } from '../services/api';
import { Project } from '../types/api';

interface ProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (p: Project) => void;
}

export const ProjectModal: React.FC<ProjectModalProps> = ({ isOpen, onClose, onProjectCreated }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const p = await api.createProject(name.trim(), description.trim() || undefined);
      onProjectCreated(p);
      setName('');
      setDescription('');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '480px',
          padding: '28px',
          boxShadow: '0 20px 50px rgba(0,0,0,0.8)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FolderPlus size={22} color="var(--accent-cyan)" />
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Create New Project</h2>
          </div>
          <button
            id="btn-close-project-modal"
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid var(--accent-red)',
              color: 'var(--accent-red-bright)',
              fontSize: '0.85rem',
              marginBottom: '16px',
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Project / Website Name *
            </label>
            <input
              id="input-project-name"
              type="text"
              className="input"
              placeholder="e.g. Acme Cloud Store, Stripe Billing API, My App"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Description (Optional)
            </label>
            <textarea
              id="input-project-description"
              className="textarea"
              rows={3}
              placeholder="Brief description of the application, architecture, or testing scope..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button id="btn-submit-create-project" type="submit" className="btn btn-primary" disabled={loading || !name.trim()}>
              {loading ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
