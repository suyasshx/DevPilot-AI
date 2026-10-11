"""
DevPilot AI - Unit Tests for LangGraph Multi-Step StateGraph Workflow.
"""

import pytest
from app.agent.graph import create_qa_workflow_graph, run_qa_agent_workflow
from app.agent.state import QAWorkflowState
from app.llm.mock_provider import MockLLMProvider


def test_create_qa_workflow_graph_compilation() -> None:
    """Verify that the LangGraph DAG compiles with valid edges and nodes."""
    graph = create_qa_workflow_graph()
    assert graph is not None


@pytest.mark.asyncio
async def test_run_qa_agent_workflow_offline() -> None:
    """Verify full LangGraph DAG execution cycle without external network dependencies."""
    initial_state: QAWorkflowState = {
        "project_id": "proj-unit-test",
        "endpoint_id": "ep-unit-test",
        "target_base_url": "http://localhost:8000",
        "testing_objective": "Test order processing contract",
        "categories": ["positive", "negative", "security"],
        "endpoint_meta": {
            "path": "/orders",
            "method": "POST",
            "parameters_schema": [],
            "request_body_schema": {
                "required": True,
                "schema": {"type": "object", "required": ["customer_id"]},
            },
            "responses_schema": {"201": {}, "400": {}, "401": {}},
            "auth_required": True,
        },
        "max_repair_attempts": 2,
    }

    mock_provider = MockLLMProvider()
    final_state = await run_qa_agent_workflow(
        initial_state=initial_state,
        provider=mock_provider,
    )

    # Assertions on final state
    assert final_state["workflow_status"] == "completed"
    assert len(final_state["raw_generated_tests"]) > 0
    assert len(final_state["validated_tests"]) > 0
    assert len(final_state["execution_results"]) > 0
    assert len(final_state["failure_classifications"]) > 0
    assert len(final_state["execution_logs"]) > 0

    metrics = final_state["metrics"]
    assert "total_tests" in metrics
    assert "taxonomy_breakdown" in metrics
    assert metrics["structural_validity_rate"] == 100.0


@pytest.mark.asyncio
async def test_workflow_self_repair_loop_trigger() -> None:
    """Verify that if validation detects failures, LangGraph cycles through repair_node."""
    # Custom provider that produces an invalid test case on attempt 1, then valid on attempt 2
    invalid_cases_json = '{"test_cases": [{"test_id_code": "TC-BAD", "name": "Bad", "description": "desc", "category": "positive", "expected_status": 999}]}'
    valid_cases_json = '{"test_cases": [{"test_id_code": "TC-GOOD", "name": "Good", "description": "desc", "category": "positive", "expected_status": 201}]}'

    custom_provider = MockLLMProvider(custom_responses=[invalid_cases_json, valid_cases_json])

    initial_state: QAWorkflowState = {
        "project_id": "proj-repair-test",
        "endpoint_id": "ep-repair-test",
        "target_base_url": "http://localhost:8000",
        "testing_objective": "Test self-repair loop",
        "categories": ["positive"],
        "endpoint_meta": {
            "path": "/orders",
            "method": "POST",
            "parameters_schema": [],
            "request_body_schema": {},
            "responses_schema": {"201": {}},
            "auth_required": False,
        },
        "max_repair_attempts": 2,
    }

    final_state = await run_qa_agent_workflow(
        initial_state=initial_state,
        provider=custom_provider,
    )

    assert final_state["workflow_status"] == "completed"
    assert final_state["repair_attempts"] >= 1
    # Check that execution logs record the repair turn
    assert any("[SELF-REPAIR]" in log for log in final_state["execution_logs"])
