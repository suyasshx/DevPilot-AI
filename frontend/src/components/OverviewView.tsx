import React from 'react';
import {
  FileCode,
  BookOpen,
  PlayCircle,
  Activity,
  CheckCircle2,
  XCircle,
  ExternalLink,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import { Project, ApiSpecification, ApiEndpoint, KnowledgeDocument, TestRun } from '../types/api';

interface OverviewViewProps {
  project: Project;
  specs: ApiSpecification[];
  endpoints: ApiEndpoint[];
  documents: KnowledgeDocument[];
  runs: TestRun[];
  onNavigate: (tab: string) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  project,
  specs,
  endpoints,
  documents,
  runs,
  onNavigate,
}) => {
  const totalRuns = runs.length;
  const completedRuns = runs.filter((r) => r.status === 'completed');
  const avgPassRate =
    completedRuns.length > 0
      ? Math.round(completedRuns.reduce((acc, r) => acc + (r.pass_rate_pct || 0), 0) / completedRuns.length)
      : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Top Banner */}
      <div
        className="glass-panel"
        style={{
          padding: '28px 32px',
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.8) 100%)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '20px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Project Dashboard
            </span>
            <span style={{ width: '4px', height: '4px', borderRadius: '50%', background: 'var(--text-muted)' }} />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {project.slug}
            </span>
          </div>
          <h1 style={{ fontSize: '1.85rem', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
            {project.name}
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '650px' }}>
            {project.description ||
              'Universal autonomous testing suite. Ingest any OpenAPI contract, ground with QA documentation, and execute deterministic tests with 5-way failure taxonomy classification.'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            id="btn-overview-launch"
            onClick={() => onNavigate('workflow')}
            className="btn btn-primary"
            style={{ padding: '12px 20px', fontSize: '0.92rem' }}
          >
            <PlayCircle size={18} />
            <span>Launch QA Agent</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '16px' }}>
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              API Endpoints
            </span>
            <FileCode size={20} color="var(--accent-cyan)" />
          </div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#fff', lineHeight: 1 }}>{endpoints.length}</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
            Across {specs.length} uploaded specification{specs.length === 1 ? '' : 's'}
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              QA Documents
            </span>
            <BookOpen size={20} color="var(--accent-purple)" />
          </div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#fff', lineHeight: 1 }}>{documents.length}</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
            RAG vector search grounding docs
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Total Executions
            </span>
            <Activity size={20} color="var(--accent-blue)" />
          </div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#fff', lineHeight: 1 }}>{totalRuns}</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
            {completedRuns.length} completed sessions
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Average Pass Rate
            </span>
            <ShieldCheck size={20} color="var(--accent-green-bright)" />
          </div>
          <div
            style={{
              fontSize: '2.2rem',
              fontWeight: 800,
              color: avgPassRate >= 80 ? 'var(--accent-green-bright)' : avgPassRate >= 50 ? 'var(--accent-amber)' : 'var(--accent-red-bright)',
              lineHeight: 1,
            }}
          >
            {avgPassRate}%
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
            Across all test runs
          </div>
        </div>
      </div>

      {/* Quick Flow Guidance */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h2 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '16px' }}>Three-Step Testing Pipeline</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          <div
            className="glass-card"
            style={{ padding: '20px', cursor: 'pointer' }}
            onClick={() => onNavigate('specs')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-cyan)', marginBottom: '8px' }}>
              <span style={{ fontWeight: 800, fontSize: '0.9rem' }}>01.</span>
              <span style={{ fontWeight: 700 }}>Upload API Spec</span>
              <ArrowRight size={14} style={{ marginLeft: 'auto' }} />
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Add any OpenAPI / Swagger JSON or YAML specification. Automatically extracts endpoints, parameters, and contract schemas.
            </p>
          </div>

          <div
            className="glass-card"
            style={{ padding: '20px', cursor: 'pointer' }}
            onClick={() => onNavigate('knowledge')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-purple)', marginBottom: '8px' }}>
              <span style={{ fontWeight: 800, fontSize: '0.9rem' }}>02.</span>
              <span style={{ fontWeight: 700 }}>Add QA Guidelines</span>
              <ArrowRight size={14} style={{ marginLeft: 'auto' }} />
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Upload testing rules, bug reports, or defect notes. The agent uses RAG embeddings to ground test generation in your rules.
            </p>
          </div>

          <div
            className="glass-card"
            style={{ padding: '20px', cursor: 'pointer' }}
            onClick={() => onNavigate('workflow')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-green-bright)', marginBottom: '8px' }}>
              <span style={{ fontWeight: 800, fontSize: '0.9rem' }}>03.</span>
              <span style={{ fontWeight: 700 }}>Run Autonomous QA</span>
              <ArrowRight size={14} style={{ marginLeft: 'auto' }} />
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Select target endpoint and base URL. Watch the LangGraph agent generate, validate, execute, and classify defects live.
            </p>
          </div>
        </div>
      </div>

      {/* Recent Runs Glance */}
      {runs.length > 0 && (
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Recent Execution Runs</h2>
            <button
              onClick={() => onNavigate('runs')}
              className="btn btn-outline"
              style={{ padding: '6px 12px', fontSize: '0.8rem' }}
            >
              <span>View All</span>
              <ArrowRight size={14} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {runs.slice(0, 5).map((r) => (
              <div
                key={r.id}
                className="glass-card"
                style={{
                  padding: '14px 18px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.88rem' }}>
                      {r.run_uuid}
                    </span>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        background: r.status === 'completed' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: r.status === 'completed' ? 'var(--accent-green-bright)' : 'var(--accent-red-bright)',
                      }}
                    >
                      {r.status}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    Target: {r.target_base_url} &bull; {r.total_tests} Tests ({r.passed_tests} passed, {r.failed_tests} failed)
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 800, fontSize: '1.1rem', color: r.pass_rate_pct >= 80 ? 'var(--accent-green-bright)' : 'var(--accent-red-bright)' }}>
                      {r.pass_rate_pct}%
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Pass Rate</div>
                  </div>
                  <button
                    onClick={() => onNavigate('runs')}
                    className="btn btn-outline"
                    style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                  >
                    Inspect
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
