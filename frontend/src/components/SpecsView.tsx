import React, { useState } from 'react';
import {
  Upload,
  FileCode,
  Search,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Play,
  FileText,
  AlertCircle,
  Tag,
} from 'lucide-react';
import { Project, ApiSpecification, ApiEndpoint } from '../types/api';
import { api } from '../services/api';

interface SpecsViewProps {
  project: Project;
  specs: ApiSpecification[];
  endpoints: ApiEndpoint[];
  onSpecUploaded: () => void;
  onSelectEndpointForTest: (ep: ApiEndpoint) => void;
}

export const SpecsView: React.FC<SpecsViewProps> = ({
  project,
  specs,
  endpoints,
  onSpecUploaded,
  onSelectEndpointForTest,
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [selectedMethod, setSelectedMethod] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedEndpointId, setExpandedEndpointId] = useState<string | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const res = await api.uploadSpec(project.id, file);
      setUploadSuccess(`Successfully ingested specification: "${res.title}" (v${res.version})`);
      onSpecUploaded();
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload specification');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const filteredEndpoints = endpoints.filter((ep) => {
    const matchesMethod = selectedMethod === 'ALL' || ep.method.toUpperCase() === selectedMethod;
    const matchesSearch =
      ep.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (ep.summary || '').toLowerCase().includes(searchQuery.toLowerCase());
    return matchesMethod && matchesSearch;
  });

  const methods = ['ALL', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Upload Specification Banner */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileCode size={22} color="var(--accent-cyan)" />
              <span>OpenAPI Specification Ingestion</span>
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', maxWidth: '650px' }}>
              Upload any OpenAPI 3.0/3.1 or Swagger 2.0 specification (<code style={{ color: 'var(--accent-cyan)' }}>.json</code> or <code style={{ color: 'var(--accent-cyan)' }}>.yaml</code>) to extract all routes, contract schemas, and parameter constraints for this project.
            </p>
          </div>

          <div>
            <label
              htmlFor="spec-file-input"
              className={`btn btn-primary ${uploading ? 'animate-pulse' : ''}`}
              style={{ cursor: uploading ? 'wait' : 'pointer' }}
            >
              <Upload size={16} />
              <span>{uploading ? 'Ingesting Contract...' : 'Upload OpenAPI Spec'}</span>
            </label>
            <input
              id="spec-file-input"
              type="file"
              accept=".json,.yaml,.yml"
              style={{ display: 'none' }}
              onChange={handleFileUpload}
              disabled={uploading}
            />
          </div>
        </div>

        {uploadError && (
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
            <span>{uploadError}</span>
          </div>
        )}

        {uploadSuccess && (
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
            <span>{uploadSuccess}</span>
          </div>
        )}

        {/* Existing Specs Tags */}
        {specs.length > 0 && (
          <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 600 }}>
              Active Specifications for {project.name}:
            </div>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              {specs.map((s) => (
                <div
                  key={s.id}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  <FileText size={14} color="var(--accent-cyan)" />
                  <span style={{ fontWeight: 600 }}>{s.title}</span>
                  <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>v{s.version}</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    ({s.checksum_sha256.substring(0, 8)}...)
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Discovered Endpoints Explorer */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Discovered Endpoints ({filteredEndpoints.length})</h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Select an endpoint to inspect its request/response schemas or launch autonomous test generation.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Method filter pills */}
            <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-elevated)', padding: '3px', borderRadius: '8px' }}>
              {methods.map((m) => (
                <button
                  key={m}
                  id={`filter-method-${m}`}
                  onClick={() => setSelectedMethod(m)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: 'none',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    background: selectedMethod === m ? 'var(--accent-cyan)' : 'transparent',
                    color: selectedMethod === m ? '#090d16' : 'var(--text-secondary)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {m}
                </button>
              ))}
            </div>

            {/* Search */}
            <div style={{ position: 'relative' }}>
              <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '12px' }} />
              <input
                id="input-search-endpoints"
                type="text"
                className="input"
                style={{ paddingLeft: '32px', width: '220px', fontSize: '0.82rem' }}
                placeholder="Search endpoints..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Endpoints List */}
        {filteredEndpoints.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No endpoints found. Upload an OpenAPI specification above to populate endpoints.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {filteredEndpoints.map((ep) => {
              const isExpanded = expandedEndpointId === ep.id;
              const methodLower = ep.method.toLowerCase();
              return (
                <div key={ep.id} className="glass-card" style={{ overflow: 'hidden' }}>
                  <div
                    style={{
                      padding: '12px 18px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      userSelect: 'none',
                    }}
                    onClick={() => setExpandedEndpointId(isExpanded ? null : ep.id)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
                      <span className={`badge badge-method-${methodLower}`} style={{ width: '60px', justifyContent: 'center' }}>
                        {ep.method}
                      </span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.9rem', color: '#fff' }}>
                        {ep.path}
                      </span>
                      {ep.summary && (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          &bull; {ep.summary}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <button
                        id={`btn-test-endpoint-${ep.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectEndpointForTest(ep);
                        }}
                        className="btn btn-primary"
                        style={{ padding: '5px 12px', fontSize: '0.78rem' }}
                      >
                        <Play size={12} fill="#fff" />
                        <span>Test Endpoint</span>
                      </button>

                      {isExpanded ? <ChevronDown size={18} color="var(--text-muted)" /> : <ChevronRight size={18} color="var(--text-muted)" />}
                    </div>
                  </div>

                  {/* Expanded Contract Schemas */}
                  {isExpanded && (
                    <div
                      style={{
                        padding: '16px 18px',
                        background: 'rgba(0, 0, 0, 0.25)',
                        borderTop: '1px solid var(--border-subtle)',
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                        gap: '16px',
                      }}
                    >
                      {/* Parameters Schema */}
                      <div>
                        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                          Parameters (Path / Query / Header)
                        </div>
                        <pre
                          style={{
                            background: 'var(--bg-base)',
                            padding: '10px',
                            borderRadius: '6px',
                            fontSize: '0.74rem',
                            fontFamily: 'var(--font-mono)',
                            maxHeight: '180px',
                            overflowY: 'auto',
                            color: '#94a3b8',
                          }}
                        >
                          {JSON.stringify(ep.parameters_schema || [], null, 2)}
                        </pre>
                      </div>

                      {/* Request Body Schema */}
                      <div>
                        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                          Request Body Schema
                        </div>
                        <pre
                          style={{
                            background: 'var(--bg-base)',
                            padding: '10px',
                            borderRadius: '6px',
                            fontSize: '0.74rem',
                            fontFamily: 'var(--font-mono)',
                            maxHeight: '180px',
                            overflowY: 'auto',
                            color: '#94a3b8',
                          }}
                        >
                          {JSON.stringify(ep.request_body_schema || {}, null, 2)}
                        </pre>
                      </div>

                      {/* Responses Schema */}
                      <div>
                        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                          Contract Response Statuses
                        </div>
                        <pre
                          style={{
                            background: 'var(--bg-base)',
                            padding: '10px',
                            borderRadius: '6px',
                            fontSize: '0.74rem',
                            fontFamily: 'var(--font-mono)',
                            maxHeight: '180px',
                            overflowY: 'auto',
                            color: '#94a3b8',
                          }}
                        >
                          {JSON.stringify(ep.responses_schema || {}, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
