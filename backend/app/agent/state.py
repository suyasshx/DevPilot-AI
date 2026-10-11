"""
DevPilot AI - LangGraph Agent State Definition.
Defines immutable workflow state threaded across LangGraph StateGraph nodes.
"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict


class QAWorkflowState(TypedDict, total=False):
    """Execution state passed through the LangGraph multi-step DAG."""

    # Input parameters
    project_id: str
    endpoint_id: str
    target_base_url: str
    testing_objective: str
    categories: List[str]
    auth_token_override: Optional[str]

    # Discovery & RAG outputs
    endpoint_meta: Dict[str, Any]
    rag_context: str
    source_references: List[str]

    # Test generation outputs
    raw_generated_tests: List[Dict[str, Any]]
    model_used: str

    # Contract validation & self-repair outputs
    validated_tests: List[Dict[str, Any]]
    validation_errors: List[Dict[str, Any]]
    repair_attempts: int
    max_repair_attempts: int
    is_contract_valid: bool

    # Execution telemetry
    execution_results: List[Dict[str, Any]]

    # Evaluation & 5-way failure classification
    failure_classifications: List[Dict[str, Any]]
    metrics: Dict[str, Any]

    # Database persistence & audit
    test_run_id: Optional[str]
    run_uuid: Optional[str]
    workflow_status: str  # "discovering", "generating", "validating", "repairing", "executing", "evaluating", "completed", "failed"
    status_message: str
    execution_logs: List[str]
