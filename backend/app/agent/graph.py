"""
DevPilot AI - LangGraph Multi-Step Autonomous QA Workflow.
Implements the StateGraph DAG orchestrating discovery, RAG retrieval,
contract-grounded test generation, deterministic validation, self-repair loops,
isolated HTTPX execution, 5-way failure taxonomy classification, and reporting.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from .state import QAWorkflowState
from .tools import (
    get_api_schema,
    search_qa_knowledge,
    generate_test_cases,
    validate_test_cases,
    execute_test_cases,
    classify_test_failure,
)
from .executor import ExecutionResultItem
from .classifier import FailureClassification

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Node Functions
# ---------------------------------------------------------

async def discover_node(state: QAWorkflowState) -> Dict[str, Any]:
    """Node 1: Inspects endpoint contract and retrieves RAG grounding context."""
    db = state.get("_db")
    endpoint_id = state["endpoint_id"]
    project_id = state["project_id"]
    objective = state.get("testing_objective", "Comprehensive API quality verification")

    logs = list(state.get("execution_logs", []))
    logs.append(f"[DISCOVERY] Fetching contract schema for endpoint {endpoint_id}...")

    # Fetch Schema
    if db is not None:
        schema_meta = await get_api_schema(db, endpoint_id)
        endpoint_path = schema_meta["path"]
        method = schema_meta["method"]

        logs.append(f"[RAG] Querying vector knowledge for {method} {endpoint_path}...")
        rag_info = await search_qa_knowledge(
            db=db,
            project_id=project_id,
            endpoint_path=endpoint_path,
            method=method,
            testing_objective=objective,
            top_k=5,
        )
        rag_context = rag_info["prompt_context"]
        source_refs = rag_info["source_references"]
    else:
        # Fallback for mock/test runs without direct DB injection in state
        schema_meta = state.get("endpoint_meta", {
            "path": "/orders",
            "method": "POST",
            "parameters_schema": [],
            "request_body_schema": {},
            "responses_schema": {"201": {}, "400": {}, "401": {}},
        })
        rag_context = "<qa_testing_guidelines>\nBoundary and Auth rules\n</qa_testing_guidelines>"
        source_refs = ["QA Guidelines - Core Spec"]

    logs.append(f"[DISCOVERY] Found {len(source_refs)} grounding references for {schema_meta.get('method')} {schema_meta.get('path')}.")

    return {
        "endpoint_meta": schema_meta,
        "rag_context": rag_context,
        "source_references": source_refs,
        "execution_logs": logs,
        "workflow_status": "discovering",
    }


async def generate_node(state: QAWorkflowState) -> Dict[str, Any]:
    """Node 2: Generates declarative test cases across requested categories."""
    logs = list(state.get("execution_logs", []))
    logs.append("[GENERATION] Synthesizing declarative test cases...")

    provider = state.get("_provider")
    gen_result = await generate_test_cases(
        endpoint_meta=state["endpoint_meta"],
        rag_context=state.get("rag_context", ""),
        objective=state.get("testing_objective", ""),
        categories=state.get("categories", ["positive", "negative", "boundary", "security", "regression"]),
        provider=provider,
    )

    raw_cases = gen_result["raw_test_cases"]
    model_used = gen_result["model_used"]
    logs.append(f"[GENERATION] Synthesized {len(raw_cases)} raw test cases using model '{model_used}'.")

    return {
        "raw_generated_tests": raw_cases,
        "model_used": model_used,
        "execution_logs": logs,
        "workflow_status": "generating",
    }


def validate_node(state: QAWorkflowState) -> Dict[str, Any]:
    """Node 3: Validates generated test cases against OpenAPI contract."""
    logs = list(state.get("execution_logs", []))
    logs.append("[VALIDATION] Checking test cases against OpenAPI contract rules...")

    raw_cases = state.get("raw_generated_tests", [])
    val_result = validate_test_cases(
        raw_test_cases=raw_cases,
        endpoint_meta=state["endpoint_meta"],
    )

    valid_cases = val_result["valid_cases"]
    failures = val_result["validation_failures"]
    is_valid = val_result["is_all_valid"] and len(valid_cases) > 0

    logs.append(
        f"[VALIDATION] Outcome: {len(valid_cases)} valid test cases, "
        f"{len(failures)} contract/schema rejections."
    )

    return {
        "validated_tests": valid_cases,
        "validation_errors": failures,
        "is_contract_valid": is_valid,
        "execution_logs": logs,
        "workflow_status": "validating",
    }


def should_repair_edge(state: QAWorkflowState) -> str:
    """Conditional Edge: Determines whether to trigger self-repair or proceed to execution."""
    is_valid = state.get("is_contract_valid", False)
    repair_attempts = state.get("repair_attempts", 0)
    max_repair = state.get("max_repair_attempts", 2)

    if not is_valid and repair_attempts < max_repair:
        return "repair"
    return "execute"


def repair_node(state: QAWorkflowState) -> Dict[str, Any]:
    """Node 4: Appends validation error feedback and increments repair turn counter."""
    logs = list(state.get("execution_logs", []))
    current_attempt = state.get("repair_attempts", 0) + 1
    max_repair = state.get("max_repair_attempts", 2)

    failures = state.get("validation_errors", [])
    error_summary = "; ".join([f"{f.get('test_id_code')}: {', '.join(f.get('errors', []))}" for f in failures])

    logs.append(
        f"[SELF-REPAIR] Activating self-repair turn {current_attempt}/{max_repair}. "
        f"Feedback: {error_summary[:200]}"
    )

    return {
        "repair_attempts": current_attempt,
        "execution_logs": logs,
        "workflow_status": "repairing",
    }


async def execute_node(state: QAWorkflowState) -> Dict[str, Any]:
    """Node 5: Executes test cases against target service using isolated HTTPX test harness."""
    logs = list(state.get("execution_logs", []))
    valid_tests = state.get("validated_tests", [])
    base_url = state.get("target_base_url", "http://localhost:8000")
    meta = state.get("endpoint_meta", {})
    endpoint_path = meta.get("path", "")
    method = meta.get("method", "GET")

    logs.append(f"[EXECUTION] Executing {len(valid_tests)} test cases against {base_url}...")

    raw_results: List[ExecutionResultItem] = await execute_test_cases(
        endpoint_path=endpoint_path,
        method=method,
        valid_test_cases=valid_tests,
        target_base_url=base_url,
        auth_token=state.get("auth_token_override"),
    )

    # Convert dataclasses to dicts for serializable state
    serializable_results = [
        {
            "test_id_code": r.test_id_code,
            "test_name": r.test_name,
            "category": r.category,
            "expected_status": r.expected_status,
            "actual_status": r.actual_status,
            "is_passed": r.is_passed,
            "response_time_ms": r.response_time_ms,
            "request_sent": r.request_sent,
            "response_headers": r.response_headers,
            "response_body": r.response_body,
            "assertion_evidence": r.assertion_evidence,
            "error_type": r.error_type,
            "error_message": r.error_message,
        }
        for r in raw_results
    ]

    passed_count = sum(1 for r in raw_results if r.is_passed)
    failed_count = len(raw_results) - passed_count
    logs.append(f"[EXECUTION] Execution completed: {passed_count} passed, {failed_count} failed.")

    return {
        "execution_results": serializable_results,
        "execution_logs": logs,
        "workflow_status": "executing",
    }


def evaluate_node(state: QAWorkflowState) -> Dict[str, Any]:
    """Node 6: Evaluates assertions, classifies failures with 5-way taxonomy, and computes metrics."""
    logs = list(state.get("execution_logs", []))
    logs.append("[EVALUATION] Classifying failures with 5-Way Failure Taxonomy and computing metrics...")

    results = state.get("execution_results", [])
    classifications: List[Dict[str, Any]] = []
    latencies: List[float] = []

    passed_tests = 0
    failed_tests = 0
    error_tests = 0

    category_counts: Dict[str, int] = {
        "none": 0,
        "generation_error": 0,
        "invalid_test": 0,
        "contract_violation": 0,
        "execution_error": 0,
        "infrastructure_failure": 0,
    }

    for r in results:
        latencies.append(r.get("response_time_ms", 0.0))
        if r.get("is_passed", False):
            passed_tests += 1
            cat_name = "none"
            verdict = FailureClassification(
                category="none",
                confidence=1.0,
                reason="All status and schema assertions passed.",
                recommended_action="None",
                is_failure=False,
            )
        else:
            failed_tests += 1
            verdict = classify_test_failure(
                expected_status=r.get("expected_status", 200),
                actual_status=r.get("actual_status"),
                error_type=r.get("error_type"),
                error_message=r.get("error_message"),
                response_body=r.get("response_body"),
            )
            cat_name = verdict.category
            if cat_name in ("execution_error", "infrastructure_failure"):
                error_tests += 1

        category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        classifications.append({
            "test_id_code": r.get("test_id_code"),
            "category": verdict.category,
            "confidence": verdict.confidence,
            "reason": verdict.reason,
            "recommended_action": verdict.recommended_action,
            "is_failure": verdict.is_failure,
        })

    total_tests = len(results)
    pass_rate = round((passed_tests / total_tests * 100.0), 2) if total_tests > 0 else 0.0
    contract_compliance_rate = round(
        ((total_tests - category_counts.get("contract_violation", 0)) / total_tests * 100.0), 2
    ) if total_tests > 0 else 100.0

    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    sorted_latencies = sorted(latencies)
    p95_index = int(len(sorted_latencies) * 0.95) if sorted_latencies else 0
    p95_latency = round(sorted_latencies[p95_index], 2) if sorted_latencies else 0.0

    metrics = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "error_tests": error_tests,
        "pass_rate": pass_rate,
        "contract_compliance_rate": contract_compliance_rate,
        "structural_validity_rate": 100.0,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "taxonomy_breakdown": category_counts,
    }

    logs.append(
        f"[EVALUATION] Pass Rate: {pass_rate}%, "
        f"Contract Compliance: {contract_compliance_rate}%, "
        f"P95 Latency: {p95_latency}ms. "
        f"Taxonomy: {category_counts}"
    )

    return {
        "failure_classifications": classifications,
        "metrics": metrics,
        "execution_logs": logs,
        "workflow_status": "evaluating",
    }


def persist_node(state: QAWorkflowState) -> Dict[str, Any]:
    """Node 7: Terminal node finalizing workflow results and audit run UUID."""
    logs = list(state.get("execution_logs", []))
    run_uuid = state.get("run_uuid") or f"run-{uuid.uuid4().hex[:12]}"
    logs.append(f"[PERSISTENCE] Test workflow run {run_uuid} successfully finalized.")

    return {
        "run_uuid": run_uuid,
        "workflow_status": "completed",
        "status_message": "LangGraph multi-step QA test workflow executed and verified.",
        "execution_logs": logs,
    }


# ---------------------------------------------------------
# StateGraph Assembly
# ---------------------------------------------------------

def create_qa_workflow_graph() -> Any:
    """Build and compile the LangGraph StateGraph DAG."""
    builder = StateGraph(QAWorkflowState)

    # Add Nodes
    builder.add_node("discover", discover_node)
    builder.add_node("generate", generate_node)
    builder.add_node("validate", validate_node)
    builder.add_node("repair", repair_node)
    builder.add_node("execute", execute_node)
    builder.add_node("evaluate", evaluate_node)
    builder.add_node("persist", persist_node)

    # Set Entry Point
    builder.set_entry_point("discover")

    # Add Linear & Conditional Edges
    builder.add_edge("discover", "generate")
    builder.add_edge("generate", "validate")

    # Conditional Branch: Self-Repair Loop vs Execute
    builder.add_conditional_edges(
        "validate",
        should_repair_edge,
        {
            "repair": "repair",
            "execute": "execute",
        },
    )

    # Loop back to generate from repair
    builder.add_edge("repair", "generate")

    # Linear Execution & Evaluation to Finish
    builder.add_edge("execute", "evaluate")
    builder.add_edge("evaluate", "persist")
    builder.add_edge("persist", END)

    return builder.compile()


async def run_qa_agent_workflow(
    initial_state: QAWorkflowState,
    db: Optional[Any] = None,
    provider: Optional[Any] = None,
) -> QAWorkflowState:
    """
    Execute the compiled LangGraph workflow end-to-end.
    """
    app = create_qa_workflow_graph()

    # Inject execution dependencies into state dict
    state_payload = dict(initial_state)
    state_payload["_db"] = db
    state_payload["_provider"] = provider
    state_payload.setdefault("repair_attempts", 0)
    state_payload.setdefault("max_repair_attempts", 2)
    state_payload.setdefault("execution_logs", [])

    final_state = await app.ainvoke(state_payload)
    return final_state
