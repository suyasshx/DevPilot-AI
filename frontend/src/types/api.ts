export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string;
  created_at?: string;
}

export interface ApiSpecification {
  id: string;
  project_id: string;
  title: string;
  version: string;
  spec_format: string;
  checksum_sha256: string;
  created_at: string;
}

export interface ApiEndpoint {
  id: string;
  spec_id: string;
  path: string;
  method: string;
  summary?: string;
  description?: string;
  parameters_schema: any[];
  request_body_schema: Record<string, any>;
  responses_schema: Record<string, any>;
  auth_required: boolean;
  tags: string[];
}

export interface KnowledgeDocument {
  id: string;
  project_id: string;
  title: string;
  doc_type: string;
  chunk_count?: number;
  created_at?: string;
}

export interface TestEvaluation {
  id?: string;
  run_id?: string;
  structural_validity_rate: number;
  contract_compliance_rate: number;
  pass_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
}

export interface ExecutionLogItem {
  id?: string;
  log_level?: string;
  message: string;
  timestamp?: string;
}

export interface TestResult {
  id: string;
  run_id: string;
  test_case_id: string;
  test_id_code: string;
  test_name: string;
  category: string;
  status: 'passed' | 'failed' | 'error' | 'skipped';
  failure_category: 'none' | 'contract_violation' | 'execution_error' | 'invalid_test' | 'generation_error' | 'infrastructure_failure';
  request_sent_sanitized: Record<string, any>;
  response_status_code?: number;
  response_headers_sanitized: Record<string, string>;
  response_body_sanitized: any;
  response_time_ms: number;
  assertion_evidence: string[];
  error_message?: string;
  created_at?: string;
}

export interface TestRun {
  id: string;
  project_id: string;
  run_uuid: string;
  target_base_url: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  parent_run_id?: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  error_tests: number;
  pass_rate_pct: number;
  summary_metrics: Record<string, any>;
  created_at?: string;
  evaluation?: TestEvaluation;
  recent_logs?: ExecutionLogItem[];
}

export interface WorkflowLaunchPayload {
  endpoint_id: string;
  target_base_url: string;
  testing_objective: string;
  categories: string[];
  auth_token_override?: string;
  max_repair_attempts: number;
}
