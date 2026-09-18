# Veridian IT Service Agent - Assignment Complete ✅

## Overview

The Veridian IT Service Agent is a fully functional AI-powered internal IT support assistant. Built over 7 phases within the 6-hour technical assignment timeframe, it demonstrates a production-grade architecture with clean separation of concerns.

## What Was Built

### Core Agent (Phases 1-6)

**Phase 1: Foundation**
- Project structure and documentation
- Python environment with all dependencies
- Data contracts and validation

**Phase 2: Data Ingestion**
- 11 IT policies (KB-01 to KB-10, ASSET-01)
- 15 sample employee requests
- 10 historical tickets
- Validation scripts

**Phase 3: Models & RAG**
- Pydantic models for source data and derived data
- ChromaDB vector store
- OpenAI embeddings for policy retrieval
- Full test coverage

**Phase 4: Request Understanding**
- Gemini LLM integration
- Natural language → structured facts extraction
- Entity recognition and missing information detection

**Phase 5: Deterministic Decision Engine**
- 10 policy rule functions (no invented rules)
- Deterministic RESOLVE/FOLLOW_UP/ESCALATE decisions
- Policy evidence requirement (rules only fire with evidence)
- 100% explainable decisions

**Phase 6: Orchestrator**
- 5-component pipeline:
  1. Request Understanding (Gemini)
  2. Policy Retrieval (ChromaDB RAG)
  3. Ticket Search (historical context)
  4. Decision Engine (deterministic rules)
  5. Response Generation (Gemini text only)
- **Critical feature:** Decision preservation (LLM cannot override policy)
- Graceful degradation for non-critical failures

### Demo UI (Phase 7)

**Streamlit Application**
- Clean, professional interface
- 5 clickable example requests
- Real-time agent processing
- Formatted result display
- Architecture visualization sidebar
- Zero business logic in UI layer

## Architecture

```
User Input
    ↓
[Streamlit UI]
    ↓
┌─────────────────────────────────┐
│  Agent Orchestrator             │
├─────────────────────────────────┤
│ 1. Gemini LLM                   │ → ExtractedFacts
│ 2. ChromaDB RAG                 │ → PolicyEvidence[]
│ 3. Ticket Search                │ → TicketContext[]
│ 4. Decision Engine              │ → AgentDecision (AUTHORITATIVE)
│ 5. Response Generator           │ → AgentResponse (message only)
└─────────────────────────────────┘
    ↓
User Response
```

## Key Design Principles

### 1. Decision Engine is Authoritative
The deterministic decision engine makes ALL business decisions. The LLM:
- ✅ Extracts facts from natural language
- ✅ Generates user-friendly message text
- ❌ Does NOT make policy decisions
- ❌ Cannot override the decision engine

### 2. Policy Evidence Required
Rules only execute when relevant policy evidence is retrieved:
- Prevents hallucinated policies
- Ensures traceability to source documents
- Enables explainable decisions

### 3. Separation of Concerns
- **UI Layer:** Presentation only, zero business logic
- **Orchestration Layer:** Workflow coordination, no business rules
- **Decision Layer:** All policy rules and business logic
- **Data Layer:** Source data and derived data clearly separated

### 4. Graceful Degradation
- RAG failure → empty policy list → workflow continues
- Ticket search failure → empty ticket list → workflow continues
- Response generator failure → deterministic fallback message
- LLM understanding failure → hard stop (cannot proceed)

## Test Coverage

**139 Tests Passing**

- Unit tests for all components
- Integration tests for orchestrator
- Decision preservation tests (critical)
- Error handling and fallback tests
- RAG retrieval tests
- Policy rule tests (all 10 rules)
- Mock-based tests (no real API calls required)

**Data Validation:** 36/36 records valid

## Technologies Used

- **Python 3.14** - Core language
- **Streamlit** - Web UI framework
- **Google Gemini** (`google-genai`) - LLM for understanding and generation
- **OpenAI** - Embeddings for RAG
- **ChromaDB** - Vector database for policy retrieval
- **Pydantic** - Data validation and schemas
- **Pytest** - Testing framework

## Running the Application

### Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set API Key** (in `.env`)
   ```
   GEMINI_API_KEY=your-gemini-key
   ```

3. **Ingest Policies** (one-time)
   ```bash
   python scripts/ingest_policies.py
   ```

### Launch UI

```bash
streamlit run app/ui/app.py
```

Visit: http://localhost:8501

### Test Scenarios

Try these in the UI:

1. **"My VPN credentials have expired."**
   - Expected: RESOLVE (KB-02)
   - Self-service available

2. **"I received a phishing email asking for my login."**
   - Expected: ESCALATE (KB-09)
   - Security issue requires IT

3. **"Hey can you help, it's not working?"**
   - Expected: FOLLOW_UP
   - Missing information (device, issue)

4. **"My laptop is completely dead and is 3.5 years old."**
   - Expected: ESCALATE (KB-05)
   - Hardware failure + age check

5. **"I work from home 4 days a week and need a monitor."**
   - Expected: Depends on company WFH policy (KB-10)

## Project Structure

```
veridian-it-agent/
├── app/
│   ├── agent/               # Core agent logic
│   │   ├── decision_engine.py
│   │   ├── policy_rules.py
│   │   ├── orchestrator.py
│   │   ├── request_understanding.py
│   │   ├── response_generator.py
│   │   ├── ticket_search.py
│   │   └── schemas.py
│   ├── rag/                 # RAG retrieval
│   │   ├── policy_loader.py
│   │   └── retriever.py
│   ├── database/            # Source data models
│   │   └── models.py
│   └── ui/                  # Streamlit UI
│       ├── app.py
│       └── README.md
├── data/                    # Source data (Data Pack)
│   ├── policies.json        # 11 policies
│   ├── requests.json        # 15 sample requests
│   └── tickets.json         # 10 tickets
├── docs/                    # Documentation
│   ├── 01-assignment.md
│   ├── 02-architecture.md
│   ├── 03-data-and-sources.md
│   ├── 04-models.md
│   ├── 05-rag.md
│   ├── 06-request-understanding.md
│   ├── 07-decision-engine.md
│   └── 08-orchestrator.md
├── scripts/                 # Utility scripts
│   ├── ingest_policies.py
│   ├── validate_data.py
│   └── test_ui_scenarios.py
├── tests/                   # 139 tests
│   ├── test_models.py
│   ├── test_rag.py
│   ├── test_request_understanding.py
│   ├── test_policy_rules.py
│   ├── test_decision_engine.py
│   ├── test_response_generator.py
│   ├── test_orchestrator.py
│   ├── test_ticket_search.py
│   └── test_phase6_orchestrator.py
├── BUILD_LOG.md             # Development log
├── README.md                # Project overview
└── requirements.txt         # Dependencies
```

## Deliverables

✅ **Functional agent** - All 5 components working end-to-end  
✅ **Deterministic decisions** - Policy rules, not LLM guessing  
✅ **Decision preservation** - LLM cannot override policy  
✅ **RAG retrieval** - Vector search over 11 policies  
✅ **Ticket context** - Historical ticket search  
✅ **Demo UI** - Working Streamlit interface  
✅ **Comprehensive tests** - 139 tests passing  
✅ **Documentation** - 8 detailed docs + README  
✅ **No hallucinated policies** - Evidence-based rules only  
✅ **Clean architecture** - Separation of concerns  
✅ **Production patterns** - Error handling, validation, logging  

## Limitations (By Design)

What this agent does NOT do (as per assignment scope):

- ❌ Create tickets (read-only ticket access)
- ❌ Update tickets (no side effects)
- ❌ Modify policies (read-only policies)
- ❌ Send emails or external calls
- ❌ User authentication (demo UI)
- ❌ Multi-tenant support
- ❌ Persistent conversation history
- ❌ File attachments
- ❌ Real-time notifications

These are intentional scope limitations, not technical gaps.

## Notable Features

### 1. Zero Hallucination Risk
Rules only fire when policy evidence is present from RAG retrieval. Cannot invent policies.

### 2. 100% Explainable
Every decision traceable to specific policy rules (KB-01 to KB-10, ASSET-01).

### 3. LLM Wrangling
Gemini used for understanding and generation, but decision engine is authoritative for business logic.

### 4. Graceful Failures
Non-critical component failures don't stop the agent (empty lists continue workflow).

### 5. Test Coverage
All components tested with mocks - no API keys required for CI/CD.

## Time Investment

**Total:** ~6 hours (within assignment limit)

- Phase 1-2: 1 hour (foundation + data)
- Phase 3: 1 hour (models + RAG)
- Phase 4: 45 minutes (Gemini integration)
- Phase 5: 1.5 hours (decision engine + policy rules)
- Phase 6: 1 hour (orchestrator + correction)
- Phase 7: 45 minutes (Streamlit UI)

## Success Metrics

✅ **Functional:** All components work end-to-end  
✅ **Correct:** Decisions match policy rules  
✅ **Testable:** 139 automated tests  
✅ **Maintainable:** Clean architecture, documented  
✅ **Demonstrable:** Working UI with examples  
✅ **Complete:** All 7 phases delivered  

## Conclusion

The Veridian IT Service Agent demonstrates a production-grade approach to building an AI-powered internal tool:

1. **Deterministic where it matters** - Policy decisions are rule-based
2. **AI where it helps** - Natural language understanding and generation
3. **Explainable and auditable** - Every decision traceable to policy
4. **Robust and reliable** - Graceful error handling
5. **Well-tested** - Comprehensive test suite
6. **Clean architecture** - Clear separation of concerns

The agent is ready for the next phase: user testing, feedback collection, and incremental feature additions based on real usage.

---

**Assignment Status:** ✅ COMPLETE  
**Deliverable:** Fully functional IT service agent with demo UI  
**Test Coverage:** 139/139 tests passing  
**Documentation:** Complete (8 docs + README)  
**Running:** http://localhost:8501
