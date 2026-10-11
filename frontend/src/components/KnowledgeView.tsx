import React, { useState } from 'react';
import {
  BookOpen,
  Upload,
  PlusCircle,
  Search,
  FileText,
  Bug,
  ShieldAlert,
  CheckCircle2,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import { Project, KnowledgeDocument } from '../types/api';
import { api } from '../services/api';

interface KnowledgeViewProps {
  project: Project;
  documents: KnowledgeDocument[];
  onDocumentAdded: () => void;
}

export const KnowledgeView: React.FC<KnowledgeViewProps> = ({
  project,
  documents,
  onDocumentAdded,
}) => {
  const [activeTab, setActiveTab] = useState<'docs' | 'search'>('docs');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // New Doc Form
  const [showAddForm, setShowAddForm] = useState(false);
  const [docTitle, setDocTitle] = useState('');
  const [docType, setDocType] = useState('qa_guideline');
  const [docContent, setDocContent] = useState('');

  // RAG Search Console
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      await api.uploadDocument(project.id, file, docType);
      setSuccess(`Uploaded and indexed "${file.name}" into RAG vector store.`);
      onDocumentAdded();
    } catch (err: any) {
      setError(err.message || 'Failed to upload document');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!docTitle.trim() || !docContent.trim()) return;
    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const blob = new Blob([docContent], { type: 'text/markdown' });
      const file = new File([blob], `${docTitle.toLowerCase().replace(/\s+/g, '_')}.md`);
      await api.uploadDocument(project.id, file, docType);
      setSuccess(`Indexed "${docTitle}" successfully into vector memory.`);
      setDocTitle('');
      setDocContent('');
      setShowAddForm(false);
      onDocumentAdded();
    } catch (err: any) {
      setError(err.message || 'Failed to save document');
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const results = await api.searchKnowledge(project.id, searchQuery, 4);
      setSearchResults(results);
    } catch (err: any) {
      setError('Search failed: ' + err.message);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Banner */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BookOpen size={22} color="var(--accent-purple)" />
              <span>QA Knowledge Base & RAG Retrieval</span>
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', maxWidth: '650px' }}>
              Upload test plans, defect history, or domain rules for <strong>{project.name}</strong>. The autonomous agent retrieves relevant chunks to ground negative, boundary, and regression tests.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              id="btn-toggle-add-doc"
              className="btn btn-outline"
              onClick={() => setShowAddForm(!showAddForm)}
            >
              <PlusCircle size={16} />
              <span>Write Guideline</span>
            </button>

            <label
              htmlFor="doc-file-input"
              className={`btn btn-primary ${uploading ? 'animate-pulse' : ''}`}
              style={{ cursor: uploading ? 'wait' : 'pointer' }}
            >
              <Upload size={16} />
              <span>{uploading ? 'Chunking & Embedding...' : 'Upload Doc (.md/.txt)'}</span>
            </label>
            <input
              id="doc-file-input"
              type="file"
              accept=".md,.txt,.json"
              style={{ display: 'none' }}
              onChange={handleFileUpload}
              disabled={uploading}
            />
          </div>
        </div>

        {error && (
          <div
            style={{
              marginTop: '16px',
              padding: '12px 16px',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid var(--accent-red)',
              color: 'var(--accent-red-bright)',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div
            style={{
              marginTop: '16px',
              padding: '12px 16px',
              borderRadius: '8px',
              background: 'rgba(52, 211, 153, 0.15)',
              border: '1px solid var(--accent-green-bright)',
              color: 'var(--accent-green-bright)',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <CheckCircle2 size={18} />
            <span>{success}</span>
          </div>
        )}

        {/* Add Document Inline Form */}
        {showAddForm && (
          <form
            onSubmit={handleManualSubmit}
            style={{
              marginTop: '20px',
              paddingTop: '20px',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Add Custom Documentation / Test Rule</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Document Title *
                </label>
                <input
                  id="input-doc-title"
                  type="text"
                  className="input"
                  placeholder="e.g. Rate Limiting Rules, Order Payment Defects"
                  value={docTitle}
                  onChange={(e) => setDocTitle(e.target.value)}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  Type
                </label>
                <select
                  id="select-doc-type"
                  className="select"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                >
                  <option value="qa_guideline">QA Guideline</option>
                  <option value="bug_report">Bug Report / Defect</option>
                  <option value="auth_rule">Security & Auth Rule</option>
                </select>
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                Content (Markdown or Plain Text) *
              </label>
              <textarea
                id="textarea-doc-content"
                className="textarea"
                rows={5}
                placeholder="Describe business logic, known edge-cases, validation rules, or past bug reproduction steps..."
                value={docContent}
                onChange={(e) => setDocContent(e.target.value)}
                required
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button type="button" className="btn btn-outline" onClick={() => setShowAddForm(false)}>
                Cancel
              </button>
              <button id="btn-save-doc" type="submit" className="btn btn-primary" disabled={uploading}>
                {uploading ? 'Indexing Chunks...' : 'Save & Index Document'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Tabs: Documents List vs Semantic Search Console */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', gap: '12px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px', marginBottom: '20px' }}>
          <button
            id="tab-btn-docs"
            onClick={() => setActiveTab('docs')}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: 'pointer',
              color: activeTab === 'docs' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              borderBottom: activeTab === 'docs' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
            }}
          >
            Ingested Documents ({documents.length})
          </button>

          <button
            id="tab-btn-search"
            onClick={() => setActiveTab('search')}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              color: activeTab === 'search' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              borderBottom: activeTab === 'search' ? '2px solid var(--accent-cyan)' : '2px solid transparent',
            }}
          >
            <Sparkles size={15} />
            <span>RAG Vector Search Console</span>
          </button>
        </div>

        {activeTab === 'docs' ? (
          <div>
            {documents.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                No documents found for this project. Upload markdown files or write guidelines above to power RAG retrieval.
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
                {documents.map((doc) => (
                  <div key={doc.id} className="glass-card" style={{ padding: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {doc.doc_type === 'bug_report' ? (
                          <Bug size={18} color="var(--accent-red-bright)" />
                        ) : (
                          <FileText size={18} color="var(--accent-cyan)" />
                        )}
                        <span style={{ fontWeight: 700, fontSize: '0.92rem' }}>{doc.title}</span>
                      </div>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: 'rgba(255,255,255,0.06)',
                          color: 'var(--text-secondary)',
                          textTransform: 'uppercase',
                        }}
                      >
                        {doc.doc_type}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {doc.chunk_count ? `${doc.chunk_count} vector chunks indexed` : 'Embedded in vector database'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          /* Semantic Vector Search Test Console */
          <div>
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
              <input
                id="input-rag-search"
                type="text"
                className="input"
                placeholder="Ask a question or enter a test scenario to inspect retrieved context..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <button id="btn-submit-rag-search" type="submit" className="btn btn-primary" disabled={searching || !searchQuery.trim()}>
                <Search size={16} />
                <span>{searching ? 'Querying...' : 'Search Vector Store'}</span>
              </button>
            </form>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {searchResults.map((item, idx) => (
                <div key={idx} className="glass-card" style={{ padding: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--accent-cyan)' }}>
                      Retrieved Chunk #{idx + 1}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Relevance Distance: {item.distance ? item.distance.toFixed(4) : 'N/A'}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                    {item.content}
                  </p>
                </div>
              ))}
              {searchResults.length === 0 && !searching && (
                <div style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Enter a test scenario query above to test RAG retrieval relevance against this project's documentation.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
