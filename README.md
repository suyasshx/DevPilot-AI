# DevPilot AI — Universal Autonomous API QA & Testing Platform

[![CI/CD Pipeline](https://github.com/your-username/devpilot-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/devpilot-ai/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-StateGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**DevPilot AI** is an enterprise-grade, autonomous API quality assurance platform designed to generate, validate, execute, and classify API tests for **any application, website, or backend service**.

Unlike basic LLM wrappers that blindly generate code snippets, DevPilot AI operates as a **deterministic software engineering agent**:
1. Grounded strictly in formal **OpenAPI contracts** and **RAG domain knowledge**.
2. Guarded by a **Pydantic schema validator** with an autonomous **self-repair loop**.
3. Executed via an **isolated HTTP test harness** with SSRF protection.
4. Categorized using an industry-standard **5-Way Failure Taxonomy** that separates true API contract defects from generator or infrastructure faults.
5. Observed in real-time through **Server-Sent Events (SSE)** and exported into **self-contained offline HTML reports**.

---

## Architecture Overview

```
                          ┌───────────────────────────┐
                          │   Any OpenAPI / Swagger   │
                          │   Specification (.json/.yaml)│
                          └─────────────┬─────────────┘
                                        │
                                        ▼
┌─────────────────────────┐   ┌───────────────────────────┐   ┌─────────────────────────┐
│ Custom QA Guidelines &  │   │  OpenAPI Recursive Parser │   │ Target Web Application  │
│ Defect Bug Reports (RAG)│   │  & SHA-256 Deduplication  │   │   or Live Backend API   │
└────────────┬────────────┘   └─────────────┬─────────────┘   └────────────▲────────────┘
             │                              │                              │
             ▼                              ▼                              │
┌─────────────────────────┐   ┌───────────────────────────┐                │
│ ChromaDB Vector Store   │──▶│ Multi-Step LangGraph DAG  │                │
│ (all-MiniLM-L6-v2)     │   │ Autonomous QA Workflow    │                │
└─────────────────────────┘   └─────────────┬─────────────┘                │
                                            │                              │
                   ┌────────────────────────┴────────────────────────┐     │
                   ▼                                                 ▼     │
     ┌───────────────────────────┐                     ┌───────────────────┴─────┐
     │  Pydantic Contract Guard  │                     │ Isolated HTTPX Executor │
     │  & Agent Self-Repair Loop │                     │ & SSRF Host Allowlist   │
     └───────────────────────────┘                     └─────────────┬───────────┘
                                                                     │
                                                                     ▼
                                                       ┌───────────────────────────┐
                                                       │  5-Way Failure Taxonomy   │
                                                       │    Classification Engine  │
                                                       └─────────────┬─────────────┘
                                                                     │
                                        ┌────────────────────────────┴────────────────────────────┐
                                        ▼                                                         ▼
                         ┌─────────────────────────────┐                           ┌─────────────────────────────┐
                         │  Real-Time Telemetry (SSE)  │                           │ Offline Interactive Report  │
                         │  & React/TS Web Dashboard   │                           │ Single-File HTML Visualizer │
                         └─────────────────────────────┘                           └─────────────────────────────┘
```

---

## Core Capabilities

### 1. Test Any Website or Application
DevPilot AI is fully generic:
- **Create Any Project:** Test e-commerce apps, fintech APIs, gaming microservices, or public SaaS endpoints.
- **Ingest Contracts:** Upload any OpenAPI 3.0/3.1 or Swagger 2.0 specification. The engine recursively resolves all `$ref` pointers (including nested and cyclic schemas) and computes SHA-256 checksums to eliminate redundant processing.
- **Add Custom Docs:** Ingest Markdown QA guidelines, edge-case notes, or bug reports. The built-in RAG retriever benchmarks at **MRR = 0.90** and **Recall@3 = 100%**.

### 2. Multi-Step LangGraph Orchestration
Rather than a single prompt-completion call, DevPilot AI executes a stateful directed acyclic graph (DAG):
1. **Endpoint Discovery:** Extracts parameters, request body schemas, and response status constraints.
2. **RAG Grounding:** Retrieves top-$K$ historical defect patterns and boundary rules relevant to the endpoint.
3. **LLM Test Synthesis:** Generates declarative test cases across 5 distinct categories (`positive`, `negative`, `boundary`, `security`, `regression`).
4. **Contract Validation:** Deterministically audits every test against status codes, missing path parameters, and request body types.
5. **Self-Repair Edge:** If schema violations occur, the agent passes the compiler error back to the LLM to self-correct (up to $N$ iterations).
6. **Execution Harness:** Safely fires HTTP requests against the live target server with configurable timeouts and SSRF host allowlists.
7. **5-Way Failure Classification:** Classifies every test result deterministically.

### 3. The 5-Way Failure Taxonomy
A key flaw in traditional AI testing is grouping all non-200 responses as "test failures." DevPilot AI classifies every outcome:

| Category | Description | Root Cause |
|---|---|---|
| **`none`** | All status and schema assertions passed | Working as expected |
| **`contract_violation`** | Target API returned a status code or body schema contrary to contract | **Real API Bug** |
| **`execution_error`** | Target API returned an unhandled 500 or defect crash | **Real API Bug** |
| **`invalid_test`** | Test was structurally rejected before execution | AI generation invalidity |
| **`generation_error`** | LLM synthesized malformed JSON or invalid schema | AI prompt/format issue |
| **`infrastructure_failure`**| Target server offline, connection refused, or SSRF blocked | Network/Infra outage |

### 4. Interactive Offline HTML Reports
- Self-contained, single-file HTML reports viewable completely offline with zero external CDN dependencies.
- Features executive KPI metric cards, 5-way taxonomy distribution bar, expandable request/response inspection, assertion evidence checklists, and complete audit logs.
- Available at `GET /projects/{id}/runs/{run_id}/report.html` and downloadable for CI/CD artifacts.

### 5. React + TypeScript Web Dashboard
- Sleek modern dark mode interface built with React 19, TypeScript, and Vite.
- Real-time Server-Sent Events (SSE) telemetry log streamer.
- Dynamic project switcher, endpoint explorer, RAG vector search console, and one-click regression rerun engine.

---

## Defect Injection Showcase

To demonstrate DevPilot AI's defect discovery power, an included sample target API (`sample-api/`) features 4 toggleable defect injection hooks:

1. **`negative_quantity_allowed`:** Accepts negative item quantities in checkout without 422 rejection.
2. **`unhandled_500_on_user_not_found`:** Throws an unhandled runtime error instead of 404 when querying missing users.
3. **`broken_schema_on_products`:** Returns string fields as integers, triggering contract schema rejections.
4. **`auth_bypass_on_orders`:** Fails to enforce authentication headers on checkout routes.

DevPilot AI automatically surfaces each defect, captures the raw payload evidence, and flags them under `contract_violation` or `execution_error`.

---

## Quick Start Guide

### Prerequisites
- Python 3.11+
- Node.js 20+
- (Optional) Groq API Key for live LLM inference (`MockLLMProvider` is active by default for deterministic offline execution).

### Option 1: Running with Docker Compose

```bash
docker-compose up --build
```
- **Web Dashboard:** `http://localhost:3000`
- **DevPilot AI Backend:** `http://localhost:8000/docs`
- **Sample Target API:** `http://localhost:8001/docs`

---

### Option 2: Running Locally

#### 1. Setup Backend & Target API
```bash
# Clone the repository
git clone https://github.com/your-username/devpilot-ai.git
cd devpilot-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
pip install -r sample-api/requirements.txt
```

#### 2. Run the Test Suites
```bash
# Run all 81 platform unit and integration tests
python scripts/run_tests.py
```

#### 3. Start the Backend Services
```bash
# Terminal 1: DevPilot AI Backend
uvicorn backend.app.main:app --port 8000 --reload

# Terminal 2: Sample Target API (or point to your own app)
uvicorn sample-api.app.main:app --port 8001 --reload
```

#### 4. Start the Web Dashboard
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:3000` to launch the platform.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agent/             # LangGraph StateGraph DAG, tools, isolated executor, taxonomy classifier
│   │   ├── api/routes/        # REST endpoints (projects, specs, knowledge, generation, workflow, execution)
│   │   ├── db/                # SQLAlchemy async session & database models
│   │   ├── ingestion/         # OpenAPI recursive parser & SHA256 checksum deduplication
│   │   ├── llm/               # Groq provider & deterministic MockLLMProvider with self-repair
│   │   ├── models/            # SQLAlchemy 2.0 ORM models
│   │   ├── rag/               # ChromaDB vector store, sentence embeddings & benchmark evaluator
│   │   ├── schemas/           # Pydantic v2 declarative schemas
│   │   ├── services/          # Business logic: generation, execution, reporting, telemetry broadcaster
│   │   ├── templates/         # Offline standalone HTML report Jinja2 template
│   │   └── validation/        # Deterministic contract validator & signature deduplicator
│   └── tests/                 # Unit & integration test suites (50 tests, 83% coverage)
├── frontend/                  # React 19 + TypeScript + Vite modern dashboard
│   ├── src/
│   │   ├── components/        # Overview, SpecsView, KnowledgeView, WorkflowLaunch, RunsView
│   │   ├── services/          # Typed API client
│   │   └── types/             # TypeScript contract definitions
├── sample-api/                # Target e-commerce API with toggleable defect injection hooks
│   └── tests/                 # Target API test suite (31 tests, 97% coverage)
├── sample-data/               # Sample OpenAPI specs, QA guidelines, and historical bug reports
├── scripts/
│   └── run_tests.py           # Unified test runner across backend and target API
└── docker-compose.yml         # Containerized multi-service deployment
```

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
