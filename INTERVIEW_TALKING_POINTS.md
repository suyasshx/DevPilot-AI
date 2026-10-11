# DevPilot AI — Technical Architecture & Interview Talking Points Guide

This guide is designed to help you explain the architectural principles, engineering trade-offs, and design decisions behind **DevPilot AI** during senior software engineering, AI engineering, or QA automation interviews.

---

## 1. Executive Summary & Core Pitch

> **The Problem:** Most AI test generation tools are simple prompt wrappers that blindly produce static test code. They hallucinate invalid query parameters, generate tests that fail due to prompt errors rather than real bugs, and fail to distinguish between API defects, infrastructure downtime, and bad test syntax.
> 
> **The DevPilot AI Solution:** DevPilot AI is a deterministic, contract-grounded autonomous QA platform. It treats the OpenAPI contract as the single source of truth, grounds test synthesis in vector-embedded domain guidelines, validates generated tests before execution using a Pydantic compiler with a self-repair loop, executes tests through a secure harness with SSRF guards, and classifies every failure into a 5-Way Taxonomy to pinpoint real contract violations versus AI hallucinations.

---

## 2. Key Architecture Pillars & Discussion Questions

### Q1: "Why not just ask ChatGPT or Claude to write pytest files directly?"

**Your Answer:**
- **Hallucination Risk:** LLMs routinely invent endpoints, hallucinate non-existent path parameters, or assume arbitrary data types that crash immediately upon execution.
- **Unvalidated Code Execution:** Direct code generation creates an execution security hazard (arbitrary Python execution, SSRF).
- **No Self-Correction:** When an LLM generates a broken test, a static script fails once and abandons the run.
- **DevPilot AI Approach:**
  - Tests are synthesized as **declarative Pydantic data schemas** (`GeneratedTestCaseItem`), not raw executable scripts.
  - Every test is strictly audited against the OpenAPI specification before a single network byte is sent.
  - If a schema discrepancy is detected, our **LangGraph conditional self-repair loop** feeds compiler feedback back into the LLM to fix the test.

---

### Q2: "How did you design the RAG pipeline and measure its retrieval quality?"

**Your Answer:**
- **Chunking Strategy:** Structured documents (such as QA guidelines and bug reports) are normalized and chunked with token overlap to preserve contextual boundaries.
- **Dense Embeddings:** Indexed using `sentence-transformers` (`all-MiniLM-L6-v2`) in an embedded vector store.
- **Quantitative Evaluation:** Rather than guessing whether retrieval works, we implemented a quantitative benchmark evaluator (`backend/app/rag/evaluation.py`):
  - Evaluated on 10 realistic QA retrieval queries across auth, order boundaries, defect patterns, and rate limits.
  - Measured across **Mean Reciprocal Rank (MRR)** and **Recall@K**:
    - **MRR:** `0.9000`
    - **Recall@1:** `80.0%`
    - **Recall@3:** `100.0%`
    - **Recall@5:** `100.0%`
  - This guarantees that when synthesizing negative or boundary tests, the agent is grounded in actual historical bug reports.

---

### Q3: "Why did you choose LangGraph instead of a standard linear sequence or LangChain chain?"

**Your Answer:**
- **Stateful Cyclic Workflows:** A traditional linear chain cannot handle cyclic recovery loops cleanly. Testing requires a **generate $\rightarrow$ validate $\rightarrow$ self-repair $\rightarrow$ re-validate** cycle.
- **Typed State Management:** `QAWorkflowState` maintains an immutable audit trail of execution logs, validation errors, and raw outputs across nodes.
- **Conditional Edge Routing:** `should_repair_edge` checks `is_contract_valid` and `repair_attempts < max_repair_attempts`. If invalid, it routes to `repair_node`; once valid (or repairs exhausted), it transitions to `execute_node`.
- **Telemetry Streaming:** The DAG node transitions emit real-time Server-Sent Events (SSE) so users can observe stage progression live in the dashboard.

---

### Q4: "What is your 5-Way Failure Taxonomy and why is it important?"

**Your Answer:**
In traditional test automation, everything that fails is labeled as a "FAIL". This wastes hours of developer time diagnosing tests that were flawed to begin with. DevPilot AI categorizes failures into 5 distinct buckets:

1. **`none`:** Test executed and all assertions passed.
2. **`contract_violation` (Real Bug):** The target API returned a status code or body schema that directly violated its OpenAPI contract (e.g. returning 200 on negative quantity or 500 on missing user).
3. **`execution_error` (Real Bug):** Target API crashed with an unhandled 5xx or defect crash.
4. **`invalid_test` (AI Defect):** Test had missing required path parameters or unparsable types that were rejected during pre-execution validation.
5. **`generation_error` (AI Defect):** LLM synthesized malformed JSON or invalid schema that could not be parsed.
6. **`infrastructure_failure` (Environment Defect):** Connection refused, gateway timeout, or target server offline.

**Impact:** When an engineering team views the report, they can immediately filter for `contract_violation` to file high-priority JIRA tickets without chasing false positives.

---

### Q5: "How did you prevent security vulnerabilities like SSRF?"

**Your Answer:**
- Because the platform allows users to enter arbitrary target base URLs, an attacker could attempt to target cloud metadata services (`http://169.254.169.254`) or internal microservices.
- We implemented an **SSRF Host Allowlist Guard** in `TestHarnessExecutor._validate_host_security`:
  - Every URL is parsed into its hostname and validated against `settings.ALLOWED_TARGET_HOSTS`.
  - External remote `$ref` pointers in OpenAPI specifications are blocked from remote resolution to prevent blind server-side request forgery during contract parsing.

---

### Q6: "How does regression testing work in DevPilot AI?"

**Your Answer:**
- When an engineer fixes a bug, they shouldn't have to regenerate an entire test suite from scratch.
- Our **Regression Rerun Engine** (`POST /projects/{id}/runs/{run_id}/rerun`):
  - Fetches previous test runs.
  - Supports `failed_only=True`, which queries only tests with `status != 'passed'`.
  - Re-executes the tests through the harness, re-classifies the outcomes, and creates a new `TestRun` record linked via `parent_run_id` for historical lineage tracking.

---

### Q7: "How is the reporting architected for offline or CI/CD usage?"

**Your Answer:**
- Many enterprise environments or CI pipelines run in airgapped environments without public internet access.
- We built an offline-capable Jinja2 template (`backend/app/templates/report_template.html`):
  - Zero external CDN dependencies (embedded CSS, inline SVG bar visualizers, vanilla JS interactive filtering).
  - Can be downloaded as a standalone `.html` file that opens anywhere, or inspected live in the browser via `GET /report.html`.

---

## 3. Key Metrics to Highlight

- **Total Test Suite:** 81 automated tests with 100% pass rate.
  - 50 Backend unit & integration tests (83% coverage).
  - 31 Sample Target API tests (97% coverage).
- **RAG Retrieval Quality:** MRR = 0.90, Recall@3 = 100%.
- **Defects Captured in Target API:** 4/4 synthetic defects caught and classified as contract violations.
- **Frontend:** React 19 + TypeScript + Vite, zero build errors, production bundle built in 1.32s.
