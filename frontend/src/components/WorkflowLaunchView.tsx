import React, { useState } from 'react';
import {
  PlayCircle,
  Cpu,
  Layers,
  Terminal,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  RotateCcw,
  Sparkles,
} from 'lucide-react';
import { Project, ApiEndpoint } from '../types/api';
import { api } from '../services/api';

interface WorkflowLaunchViewProps {
  project: Project;
  endpoints: ApiEndpoint[];
  selectedEndpoint: ApiEndpoint | null;
  onSelectEndpoint: (ep: ApiEndpoint) => void;
  onRunFinished: (runId: string) => void;
}

export const WorkflowLaunchView: React.FC<WorkflowLaunchViewProps> = ({
  project,
  endpoints,
  selectedEndpoint,
  onSelectEndpoint,
  onRunFinished,
}) => {
  const [targetBaseUrl, setTargetBaseUrl] = useState('http://localhost:8000');
  const [objective, setObjective] = useState(
    'Perform comprehensive boundary testing, negative schema validation, and defect detection.'
  );
  const [selectedCategories, setSelectedCategories] = useState<string[]>([
    'positive',
    'negative',
    'boundary',
    'security',
    'regression',
  ]);
  const [authToken, setAuthToken] = useState('');
  const [maxRepairs, setMaxRepairs] = useState(2);

  // Execution State
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeStage, setActiveStage] = useState<string>('idle');
  const [liveLogs, setLiveLogs] = useState<string[]>([]);
  const [executionResult, setExecutionResult] = useState<any | null>(null);

  const toggleCategory = (cat: string) => {
    if (selectedCategories.includes(cat)) {
      if (selectedCategories.length > 1) {
        setSelectedCategories(selectedCategories.filter((c) => c !== cat));
      }
    } else {
      setSelectedCategories([...selectedCategories, cat]);
    }
  };

  const handleLaunch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEndpoint) return;

    setExecuting(true);
    setError(null);
    setExecutionResult(null);
    setLiveLogs([
      `[LAUNCH] Initializing autonomous QA workflow for ${selectedEndpoint.method} ${selectedEndpoint.path}...`,
      `[CONFIG] Target Server: ${targetBaseUrl}`,
      `[CONFIG] Objective: "${objective}"`,
    ]);
    setActiveStage('discovery');

    try {
      // Launch workflow
      const result = await api.launchWorkflow(project.id, {
        endpoint_id: selectedEndpoint.id,
        target_base_url: targetBaseUrl,
        testing_objective: objective,
        categories: selectedCategories,
        auth_token_override: authToken.trim() || undefined,
        max_repair_attempts: maxRepairs,
      });

      setExecutionResult(result);
      setActiveStage('completed');
      setLiveLogs(result.execution_logs || []);
    } catch (err: any) {
      setError(err.message || 'Workflow execution failed');
      setActiveStage('failed');
      setLiveLogs((prev) => [...prev, `[ERROR] Workflow aborted: ${err.message}`]);
    } finally {
      setExecuting(false);
    }
  };

  const stages = [
    { id: 'discovery', label: '1. Discovery' },
    { id: 'rag', label: '2. RAG Grounding' },
    { id: 'synthesis', label: '3. Test Synthesis' },
    { id: 'validation', label: '4. Contract Check' },
    { id: 'execution', label: '5. Execution Harness' },
    { id: 'evaluation', label: '6. 5-Way Taxonomy' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <PlayCircle size={22} color="var(--accent-cyan)" />
          <span>Autonomous LangGraph QA Agent</span>
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', maxWidth: '700px' }}>
          Launches a multi-step LangGraph DAG workflow that discovers contract rules, retrieves RAG domain context, synthesizes declarative tests, enforces strict Pydantic validation with a self-repair loop, executes via isolated HTTP harness, and classifies outcomes with the 5-way failure taxonomy.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(350px, 1fr) minmax(400px, 1.2fr)', gap: '24px' }}>
        {/* Workflow Configuration Form */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '16px' }}>Configure Execution</h3>

          <form onSubmit={handleLaunch} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Target Endpoint Picker */}
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Target Endpoint *
              </label>
              <select
                id="select-target-endpoint"
                className="select"
                value={selectedEndpoint?.id || ''}
                onChange={(e) => {
                  const ep = endpoints.find((item) => item.id === e.target.value);
                  if (ep) onSelectEndpoint(ep);
                }}
                required
                disabled={executing}
              >
                <option value="">-- Choose an endpoint from specification --</option>
                {endpoints.map((ep) => (
                  <option key={ep.id} value={ep.id}>
                    [{ep.method}] {ep.path} {ep.summary ? `- ${ep.summary}` : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Target Base URL */}
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Target Server Base URL *
              </label>
              <input
                id="input-target-base-url"
                type="text"
                className="input"
                style={{ fontFamily: 'var(--font-mono)' }}
                placeholder="http://localhost:8000 or https://api.mywebsite.com"
                value={targetBaseUrl}
                onChange={(e) => setTargetBaseUrl(e.target.value)}
                required
                disabled={executing}
              />
            </div>

            {/* Testing Objective */}
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Testing Objective / QA Persona Prompt
              </label>
              <textarea
                id="textarea-testing-objective"
                className="textarea"
                rows={3}
                placeholder="Guide the AI test generator with specific scenarios, security boundaries, or regression goals..."
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                disabled={executing}
              />
            </div>

            {/* Categories */}
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                Test Categories to Synthesize
              </label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {['positive', 'negative', 'boundary', 'security', 'regression'].map((cat) => {
                  const checked = selectedCategories.includes(cat);
                  return (
                    <button
                      type="button"
                      key={cat}
                      id={`btn-cat-${cat}`}
                      onClick={() => toggleCategory(cat)}
                      disabled={executing}
                      style={{
                        padding: '6px 12px',
                        borderRadius: '20px',
                        border: '1px solid',
                        borderColor: checked ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                        background: checked ? 'rgba(56, 189, 248, 0.15)' : 'var(--bg-elevated)',
                        color: checked ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        textTransform: 'capitalize',
                      }}
                    >
                      {cat}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Auth Token Override */}
            <div>
              <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Authorization Bearer Token (Optional)
              </label>
              <input
                id="input-auth-token"
                type="password"
                className="input"
                style={{ fontFamily: 'var(--font-mono)' }}
                placeholder="Bearer token for protected endpoints"
                value={authToken}
                onChange={(e) => setAuthToken(e.target.value)}
                disabled={executing}
              />
            </div>

            {/* Launch Button */}
            <button
              id="btn-trigger-workflow"
              type="submit"
              className="btn btn-primary"
              style={{ marginTop: '8px', padding: '12px' }}
              disabled={executing || !selectedEndpoint}
            >
              {executing ? (
                <>
                  <Cpu size={18} className="animate-spin" />
                  <span>Agent Executing Workflow...</span>
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  <span>Launch Autonomous QA Workflow</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Live Execution & Telemetry Output */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Stepper */}
          <div className="glass-panel" style={{ padding: '16px 20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
              {stages.map((st, idx) => (
                <div
                  key={st.id}
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: executing ? 'var(--accent-cyan)' : executionResult ? 'var(--accent-green-bright)' : 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <span>{st.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Terminal Console */}
          <div
            className="glass-panel"
            style={{
              flex: 1,
              padding: '0',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              background: '#04060a',
              minHeight: '360px',
            }}
          >
            <div
              style={{
                padding: '10px 16px',
                background: 'rgba(255, 255, 255, 0.04)',
                borderBottom: '1px solid var(--border-subtle)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: '0.78rem',
                color: 'var(--text-secondary)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Terminal size={15} color="var(--accent-cyan)" />
                <span style={{ fontWeight: 600 }}>Autonomous Agent Telemetry Log</span>
              </div>
              <span style={{ fontFamily: 'var(--font-mono)' }}>{liveLogs.length} events</span>
            </div>

            <div
              id="terminal-log-output"
              style={{
                flex: 1,
                padding: '16px',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.75rem',
                lineHeight: 1.6,
                overflowY: 'auto',
                maxHeight: '320px',
                color: '#cbd5e1',
              }}
            >
              {liveLogs.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  Awaiting execution launch. Click "Launch Autonomous QA Workflow" to begin.
                </div>
              ) : (
                liveLogs.map((line, idx) => (
                  <div key={idx} style={{ marginBottom: '3px' }}>
                    {line.startsWith('[ERROR]') ? (
                      <span style={{ color: 'var(--accent-red-bright)' }}>{line}</span>
                    ) : line.startsWith('[LAUNCH]') || line.startsWith('[STAGE]') ? (
                      <span style={{ color: 'var(--accent-cyan)' }}>{line}</span>
                    ) : line.startsWith('[EXECUTION]') ? (
                      <span style={{ color: 'var(--accent-amber)' }}>{line}</span>
                    ) : line.startsWith('[EVALUATION]') ? (
                      <span style={{ color: 'var(--accent-purple)' }}>{line}</span>
                    ) : (
                      <span>{line}</span>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Outcome Card when finished */}
          {executionResult && (
            <div
              className="glass-panel"
              style={{
                padding: '18px 24px',
                borderLeft: '4px solid var(--accent-green-bright)',
                background: 'rgba(15, 23, 42, 0.95)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <CheckCircle2 size={18} color="var(--accent-green-bright)" />
                    <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Run Completed Successfully</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      ({executionResult.run_uuid})
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Generated: {executionResult.total_tests_generated} &bull; Executed: {executionResult.total_tests_executed} &bull; Pass Rate: {executionResult.metrics?.pass_rate}%
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <a
                    href={api.getReportHtmlUrl(project.id, executionResult.run_uuid)}
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-outline"
                    style={{ fontSize: '0.8rem', padding: '6px 12px' }}
                  >
                    <ExternalLink size={14} />
                    <span>View HTML Report</span>
                  </a>
                  <button
                    onClick={() => onRunFinished(executionResult.run_uuid)}
                    className="btn btn-primary"
                    style={{ fontSize: '0.8rem', padding: '6px 14px' }}
                  >
                    <span>Inspect Results &rarr;</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
