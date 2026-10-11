"""
DevPilot AI - Workflow Execution Pydantic Schemas.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class WorkflowExecutionRequest(BaseModel):
    """Payload to trigger autonomous LangGraph QA workflow for an endpoint."""
    __test__ = False

    endpoint_id: str = Field(..., description="Target endpoint database UUID")
    target_base_url: str = Field(default="http://localhost:8000", description="Live or test server base URL")
    testing_objective: str = Field(
        default="Perform full autonomous QA validation, boundary check, and defect evaluation.",
        description="Natural language instruction guiding test generation",
    )
    categories: List[str] = Field(
        default=["positive", "negative", "boundary", "security", "regression"],
        description="Test categories to generate and execute",
    )
    auth_token_override: Optional[str] = None
    max_repair_attempts: int = Field(default=2, ge=0, le=5)


class WorkflowExecutionResponse(BaseModel):
    """Result of an autonomous LangGraph workflow execution run."""
    run_uuid: str
    project_id: str
    endpoint_id: str
    workflow_status: str
    status_message: str
    total_tests_generated: int
    total_tests_executed: int
    metrics: Dict[str, Any]
    taxonomy_breakdown: Dict[str, int]
    execution_logs: List[str]
    execution_results: List[Dict[str, Any]]
