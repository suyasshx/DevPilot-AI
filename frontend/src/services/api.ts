import {
  Project,
  ApiSpecification,
  ApiEndpoint,
  KnowledgeDocument,
  TestRun,
  TestResult,
  WorkflowLaunchPayload,
} from '../types/api';

const BASE_URL = '/api/v1';

export const api = {
  // Projects
  async getProjects(): Promise<Project[]> {
    const res = await fetch(`${BASE_URL}/projects`);
    if (!res.ok) throw new Error('Failed to fetch projects');
    return res.json();
  },

  async createProject(name: string, description?: string): Promise<Project> {
    const res = await fetch(`${BASE_URL}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    });
    if (!res.ok) throw new Error('Failed to create project');
    return res.json();
  },

  // Specifications
  async getSpecs(projectId: string): Promise<ApiSpecification[]> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/specs`);
    if (!res.ok) throw new Error('Failed to fetch specifications');
    return res.json();
  },

  async uploadSpec(projectId: string, file: File): Promise<ApiSpecification> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE_URL}/projects/${projectId}/specs/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to upload specification');
    }
    return res.json();
  },

  // Endpoints
  async getEndpoints(projectId: string, method?: string, tag?: string): Promise<ApiEndpoint[]> {
    const params = new URLSearchParams();
    if (method) params.append('method', method);
    if (tag) params.append('tag', tag);
    const res = await fetch(`${BASE_URL}/projects/${projectId}/endpoints?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch endpoints');
    return res.json();
  },

  // Knowledge Documents
  async getDocuments(projectId: string): Promise<KnowledgeDocument[]> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/knowledge/documents`);
    if (!res.ok) throw new Error('Failed to fetch knowledge documents');
    return res.json();
  },

  async uploadDocument(projectId: string, file: File, docType: string = 'qa_guideline'): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE_URL}/projects/${projectId}/knowledge/upload?doc_type=${encodeURIComponent(docType)}`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to upload document');
    }
    return res.json();
  },

  async searchKnowledge(projectId: string, query: string, topK: number = 3): Promise<any[]> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/knowledge/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: topK }),
    });
    if (!res.ok) throw new Error('Knowledge search failed');
    return res.json();
  },

  // Autonomous QA Workflow
  async launchWorkflow(projectId: string, payload: WorkflowLaunchPayload): Promise<any> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/workflows/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Workflow execution failed');
    }
    return res.json();
  },

  // Test Runs
  async getRuns(projectId: string, status?: string): Promise<{ total: number; items: TestRun[] }> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    const res = await fetch(`${BASE_URL}/projects/${projectId}/runs?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch runs');
    return res.json();
  },

  async getRunDetail(projectId: string, runId: string): Promise<TestRun> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/runs/${runId}`);
    if (!res.ok) throw new Error('Failed to fetch run detail');
    return res.json();
  },

  async getRunResults(projectId: string, runId: string, status?: string, taxonomy?: string): Promise<{ total: number; items: TestResult[] }> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (taxonomy) params.append('failure_category', taxonomy);
    const res = await fetch(`${BASE_URL}/projects/${projectId}/runs/${runId}/results?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch test results');
    return res.json();
  },

  async rerunRun(projectId: string, runId: string, failedOnly: boolean = false, targetBaseUrl?: string): Promise<TestRun> {
    const res = await fetch(`${BASE_URL}/projects/${projectId}/runs/${runId}/rerun`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ failed_only: failedOnly, target_base_url: targetBaseUrl }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Rerun execution failed');
    }
    return res.json();
  },

  // Standalone Report URLs
  getReportHtmlUrl(projectId: string, runId: string): string {
    return `${BASE_URL}/projects/${projectId}/runs/${runId}/report.html`;
  },

  getReportDownloadUrl(projectId: string, runId: string): string {
    return `${BASE_URL}/projects/${projectId}/runs/${runId}/report/download`;
  },
};
