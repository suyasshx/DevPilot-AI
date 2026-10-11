import React, { useState, useEffect } from 'react';
import {
  Activity,
  RotateCcw,
  ExternalLink,
  Download,
  Search,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Layers,
  ChevronRight,
  ChevronDown,
  X,
  FileText,
} from 'lucide-react';
import { Project, TestRun, TestResult } from '../types/api';
import { api } from '../services/api';

interface RunsViewProps {
  project: Project;
  runs: TestRun[];
  initialRunId?: string | null;
  onRefreshRuns: () => void;
}

export const RunsView: React.FC<RunsViewProps> = ({
  project,
  runs,
  initialRunId,
  onRefreshRuns,
}) => {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(
    initialRunId || (runs.length > 0 ? runs[0].id : null)
  );
  const [runDetail, setRunDetail] = useState<TestRun | null>(null);
  const [results, setResults] = useState<TestResult[]>([]);
  const [loadingResults, setLoadingResults] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Inspect Modal
  const [inspectModalResult, setInspectModalResult] = useState<TestResult | null>(null);

  // Rerun State
  const [rerunning, setRerunning] = useState(false);
  const [rerunFailedOnly, setRerunFailedOnly] = useState(false);
  const [rerunError, setRerunError] = useState<string | null>(null);

  // Load run details whenever selectedRunId changes
  useEffect(() => {
    if (!selectedRunId) return;
    loadRunDetails(selectedRunId);
  }, [selectedRunId, project.id]);

  const loadRunDetails = async (runId: string) => {
    setLoadingResults(true);
    try {
      const detail = await api.getRunDetail(project.id, runId);
      setRunDetail(detail);

      const res = await api.getRunResults(project.id, runId);
      setResults(res.items || []);
    } catch (err: any) {
      console.error('Failed to load run details:', err);
    } finally {
      setLoadingResults(false);
    }
  };

  const handleRerun = async () => {
    if (!selectedRunId) return;
    setRerunning(true);
    setRerunError(null);
    try {
      const newRun = await api.rerunRun(project.id, selectedRunId, rerunFailedOnly);
      onRefreshRuns();
      setSelectedRunId(newRun.id);
    } catch (err: any) {
      setRerunError(err.message || 'Failed to trigger rerun');
    } finally {
      setRerunning(false);
    }
  };

  const filteredResults = results.filter((r) => {
    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'passed' && r.status === 'passed') ||
      (statusFilter === 'failed' && r.status === 'failed') ||
      (statusFilter === 'error' && r.status === 'error') ||
      (statusFilter === 'contract_violation' && r.failure_category === 'contract_violation');

    const matchesSearch =
      r.test_id_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.test_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.failure_category.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesStatus && matchesSearch;
  });

  // Calculate taxonomy breakdown percentages
  const taxonomy = runDetail?.summary_metrics?.taxonomy_breakdown || {};
  const totalInTax = runDetail?.total_tests || 1;
  const taxPct = (cat: string) => Math.round(((taxonomy[cat] || 0) / totalInTax) * 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header and Controls */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={22} color="var(--accent-blue)" />
              <span>Execution Runs & Telemetry Explorer</span>
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem' }}>
              Inspect past test sessions, 5-way failure taxonomy classifications, latency percentiles, and evidentiary assertions.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {selectedRunId && (
              <>
                <a
                  id="btn-view-report-html"
                  href={api.getReportHtmlUrl(project.id, selectedRunId)}
                  target="_blank"
                  rel="noreferrer"
                  className="btn btn-outline"
                  style={{ fontSize: '0.82rem' }}
                >
                  <ExternalLink size={15} />
                  <span>View HTML Report</span>
                </a>

                <a
                  id="btn-download-report-html"
                  href={api.getReportDownloadUrl(project.id, selectedRunId)}
                  className="btn btn-outline"
                  style={{ fontSize: '0.82rem' }}
                >
                  <Download size={15} />
                  <span>Download Report</span>
                </a>

                <button
                  id="btn-trigger-rerun"
                  onClick={handleRerun}
                  disabled={rerunning}
                  className="btn btn-primary"
                  style={{ fontSize: '0.82rem' }}
                >
                  <RotateCcw size={15} className={rerunning ? 'animate-spin' : ''} />
                  <span>{rerunning ? 'Rerunning...' : 'Rerun Session'}</span>
                </button>
              </>
            )}
          </div>
        </div>

        {rerunError && (
          <div
            style={{
              marginTop: '16px',
              padding: '10px 14px',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid var(--accent-red)',
              color: 'var(--accent-red-bright)',
              fontSize: '0.82rem',
            }}
          >
            {rerunError}
          </div>
        )}
      </div>

      {/* Main Grid: Run Selector Sidebar vs Run Detail Explorer */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px' }}>
        {/* Runs List Sidebar */}
        <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '780px', overflowY: 'auto' }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', padding: '6px 8px' }}>
            Execution History ({runs.length})
          </div>

          {runs.map((r) => {
            const isSelected = r.id === selectedRunId || r.run_uuid === selectedRunId;
            return (
              <div
                key={r.id}
                id={`run-item-${r.id}`}
                onClick={() => setSelectedRunId(r.id)}
                style={{
                  padding: '12px 14px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  border: isSelected ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                  background: isSelected ? 'rgba(56, 189, 248, 0.1)' : 'var(--bg-elevated)',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.84rem', color: isSelected ? 'var(--accent-cyan)' : '#fff' }}>
                    {r.run_uuid}
                  </span>
                  <span
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                      background: r.status === 'completed' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      color: r.status === 'completed' ? 'var(--accent-green-bright)' : 'var(--accent-red-bright)',
                    }}
                  >
                    {r.status}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  <span>{r.total_tests} Tests &bull; {r.pass_rate_pct}% Pass</span>
                  <span>{r.duration_seconds ? `${r.duration_seconds.toFixed(1)}s` : ''}</span>
                </div>
                {r.parent_run_id && (
                  <div style={{ fontSize: '0.7rem', color: 'var(--accent-purple)', marginTop: '4px' }}>
                    &bull; Regression Rerun
                  </div>
                )}
              </div>
            );
          })}

          {runs.length === 0 && (
            <div style={{ padding: '24px 8px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
              No execution runs yet. Launch a workflow to see history here.
            </div>
          )}
        </div>

        {/* Selected Run Details */}
        {runDetail ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '14px' }}>
              <div className="glass-card" style={{ padding: '16px' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>
                  Pass Rate
                </div>
                <div
                  style={{
                    fontSize: '1.8rem',
                    fontWeight: 800,
                    color: runDetail.pass_rate_pct >= 80 ? 'var(--accent-green-bright)' : runDetail.pass_rate_pct >= 50 ? 'var(--accent-amber)' : 'var(--accent-red-bright)',
                  }}
                >
                  {runDetail.pass_rate_pct}%
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  {runDetail.passed_tests} / {runDetail.total_tests} passed
                </div>
              </div>

              <div className="glass-card" style={{ padding: '16px' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>
                  Avg Latency
                </div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-cyan)' }}>
                  {runDetail.evaluation?.avg_latency_ms ? `${runDetail.evaluation.avg_latency_ms.toFixed(1)}` : '0'}
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}> ms</span>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  P95: {runDetail.evaluation?.p95_latency_ms?.toFixed(1) || '0'} ms
                </div>
              </div>

              <div className="glass-card" style={{ padding: '16px' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>
                  Contract Score
                </div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-green-bright)' }}>
                  {runDetail.evaluation?.contract_compliance_rate || 100}%
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  OpenAPI compliance
                </div>
              </div>

              <div className="glass-card" style={{ padding: '16px' }}>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '6px' }}>
                  Failures & Errors
                </div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: runDetail.failed_tests > 0 ? 'var(--accent-red-bright)' : 'var(--accent-green-bright)' }}>
                  {runDetail.failed_tests + runDetail.error_tests}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  {runDetail.failed_tests} failed, {runDetail.error_tests} error
                </div>
              </div>
            </div>

            {/* 5-Way Failure Taxonomy Breakdown Bar */}
            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ fontSize: '0.92rem', fontWeight: 700, marginBottom: '12px' }}>
                5-Way Failure Taxonomy Distribution
              </div>

              <div style={{ display: 'flex', height: '16px', borderRadius: '8px', overflow: 'hidden', background: 'var(--bg-elevated)', marginBottom: '14px' }}>
                {taxonomy.none > 0 && (
                  <div style={{ width: `${taxPct('none')}%`, background: 'var(--accent-green-bright)' }} title={`None (Passed): ${taxonomy.none}`} />
                )}
                {taxonomy.contract_violation > 0 && (
                  <div style={{ width: `${taxPct('contract_violation')}%`, background: 'var(--accent-red-bright)' }} title={`Contract Violation: ${taxonomy.contract_violation}`} />
                )}
                {taxonomy.execution_error > 0 && (
                  <div style={{ width: `${taxPct('execution_error')}%`, background: 'var(--accent-amber)' }} title={`Execution Error: ${taxonomy.execution_error}`} />
                )}
                {taxonomy.invalid_test > 0 && (
                  <div style={{ width: `${taxPct('invalid_test')}%`, background: 'var(--accent-purple)' }} title={`Invalid Test: ${taxonomy.invalid_test}`} />
                )}
                {taxonomy.generation_error > 0 && (
                  <div style={{ width: `${taxPct('generation_error')}%`, background: 'var(--accent-orange)' }} title={`Generation Error: ${taxonomy.generation_error}`} />
                )}
                {taxonomy.infrastructure_failure > 0 && (
                  <div style={{ width: `${taxPct('infrastructure_failure')}%`, background: 'var(--text-muted)' }} title={`Infrastructure Failure: ${taxonomy.infrastructure_failure}`} />
                )}
              </div>

              {/* Taxonomy pills */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent-green-bright)', background: 'rgba(52, 211, 153, 0.1)', padding: '4px 8px', borderRadius: '4px' }}>
                  Passed: {taxonomy.none || 0}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent-red-bright)', background: 'rgba(239, 68, 68, 0.1)', padding: '4px 8px', borderRadius: '4px' }}>
                  Contract Violation: {taxonomy.contract_violation || 0}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent-amber)', background: 'rgba(245, 158, 11, 0.1)', padding: '4px 8px', borderRadius: '4px' }}>
                  Execution Error: {taxonomy.execution_error || 0}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent-purple)', background: 'rgba(168, 85, 247, 0.1)', padding: '4px 8px', borderRadius: '4px' }}>
                  Invalid Test: {taxonomy.invalid_test || 0}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent-orange)', background: 'rgba(249, 115, 22, 0.1)', padding: '4px 8px', borderRadius: '4px' }}>
                  Generation Error: {taxonomy.generation_error || 0}
                </span>
              </div>
            </div>

            {/* Test Results Table with Filter Controls */}
            <div className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
                {/* Filter Pills */}
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {['all', 'passed', 'failed', 'error', 'contract_violation'].map((st) => (
                    <button
                      key={st}
                      id={`btn-filter-${st}`}
                      onClick={() => setStatusFilter(st)}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '16px',
                        border: '1px solid',
                        borderColor: statusFilter === st ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                        background: statusFilter === st ? 'rgba(56, 189, 248, 0.15)' : 'var(--bg-elevated)',
                        color: statusFilter === st ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        textTransform: 'capitalize',
                      }}
                    >
                      {st.replace('_', ' ')}
                    </button>
                  ))}
                </div>

                {/* Search */}
                <div style={{ position: 'relative' }}>
                  <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '10px' }} />
                  <input
                    id="input-search-results"
                    type="text"
                    className="input"
                    style={{ paddingLeft: '30px', width: '220px', fontSize: '0.8rem', padding: '6px 10px 6px 30px' }}
                    placeholder="Search test results..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </div>

              {/* Table */}
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                      <th style={{ padding: '10px 12px' }}>Test Code</th>
                      <th style={{ padding: '10px 12px' }}>Scenario Name</th>
                      <th style={{ padding: '10px 12px' }}>Category</th>
                      <th style={{ padding: '10px 12px' }}>Status</th>
                      <th style={{ padding: '10px 12px' }}>Taxonomy</th>
                      <th style={{ padding: '10px 12px' }}>Latency</th>
                      <th style={{ padding: '10px 12px', textAlign: 'right' }}>Telemetry</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredResults.map((r) => (
                      <tr key={r.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                          {r.test_id_code}
                        </td>
                        <td style={{ padding: '10px 12px', fontWeight: 500, color: '#fff' }}>{r.test_name}</td>
                        <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                          {r.category}
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <span
                            style={{
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '0.72rem',
                              fontWeight: 700,
                              textTransform: 'uppercase',
                              background: r.status === 'passed' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                              color: r.status === 'passed' ? 'var(--accent-green-bright)' : 'var(--accent-red-bright)',
                            }}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px' }}>
                          <span
                            style={{
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              background: 'rgba(255, 255, 255, 0.06)',
                              color: r.failure_category === 'none' ? 'var(--accent-green-bright)' : 'var(--accent-amber)',
                            }}
                          >
                            {r.failure_category}
                          </span>
                        </td>
                        <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)' }}>
                          {r.response_time_ms.toFixed(1)} ms
                        </td>
                        <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                          <button
                            id={`btn-inspect-result-${r.id}`}
                            onClick={() => setInspectModalResult(r)}
                            className="btn btn-outline"
                            style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                    {filteredResults.length === 0 && (
                      <tr>
                        <td colSpan={7} style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                          No test results matched the active filters.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Select a test run from the sidebar to inspect execution details and telemetry.
          </div>
        )}
      </div>

      {/* Evidentiary Telemetry Inspection Modal */}
      {inspectModalResult && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '20px',
          }}
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '850px',
              maxHeight: '90vh',
              overflowY: 'auto',
              padding: '28px',
              display: 'flex',
              flexDirection: 'column',
              gap: '18px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 800, fontSize: '1rem', color: 'var(--accent-cyan)' }}>
                    {inspectModalResult.test_id_code}
                  </span>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                      background: inspectModalResult.status === 'passed' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      color: inspectModalResult.status === 'passed' ? 'var(--accent-green-bright)' : 'var(--accent-red-bright)',
                    }}
                  >
                    {inspectModalResult.status}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--accent-amber)', background: 'rgba(245, 158, 11, 0.15)', padding: '2px 8px', borderRadius: '4px' }}>
                    Taxonomy: {inspectModalResult.failure_category}
                  </span>
                </div>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#fff' }}>{inspectModalResult.test_name}</h3>
              </div>
              <button
                id="btn-close-inspect-modal"
                onClick={() => setInspectModalResult(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={22} />
              </button>
            </div>

            {inspectModalResult.error_message && (
              <div
                style={{
                  padding: '12px 16px',
                  borderRadius: '8px',
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid var(--accent-red)',
                  color: 'var(--accent-red-bright)',
                  fontSize: '0.84rem',
                }}
              >
                <strong>Diagnosis / Error Message:</strong> {inspectModalResult.error_message}
              </div>
            )}

            {/* Request vs Response Payloads */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Sanitized Request Sent
                </div>
                <pre
                  style={{
                    background: '#04060a',
                    padding: '12px',
                    borderRadius: '8px',
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    color: '#94a3b8',
                    maxHeight: '220px',
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  {JSON.stringify(inspectModalResult.request_sent_sanitized || {}, null, 2)}
                </pre>
              </div>

              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Response Telemetry ({inspectModalResult.response_status_code || 'N/A'}, {inspectModalResult.response_time_ms.toFixed(1)} ms)
                </div>
                <pre
                  style={{
                    background: '#04060a',
                    padding: '12px',
                    borderRadius: '8px',
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    color: '#94a3b8',
                    maxHeight: '220px',
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  {JSON.stringify(
                    {
                      status: inspectModalResult.response_status_code,
                      headers: inspectModalResult.response_headers_sanitized,
                      body: inspectModalResult.response_body_sanitized,
                    },
                    null,
                    2
                  )}
                </pre>
              </div>
            </div>

            {/* Assertion Evidence */}
            <div>
              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Evidentiary Assertion Verification
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {inspectModalResult.assertion_evidence?.map((ev, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '8px 12px',
                      borderRadius: '6px',
                      background: 'rgba(255, 255, 255, 0.04)',
                      fontSize: '0.78rem',
                      fontFamily: 'var(--font-mono)',
                      color: ev.toLowerCase().includes('failed') || ev.toLowerCase().includes('not match') ? 'var(--accent-red-bright)' : 'var(--accent-green-bright)',
                    }}
                  >
                    {ev}
                  </div>
                ))}
                {(!inspectModalResult.assertion_evidence || inspectModalResult.assertion_evidence.length === 0) && (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontStyle: 'italic' }}>
                    No assertions recorded.
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '10px' }}>
              <button className="btn btn-outline" onClick={() => setInspectModalResult(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
