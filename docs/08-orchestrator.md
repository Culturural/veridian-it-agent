# Phase 6: Agent Orchestrator

## Overview

The orchestrator is a **thin coordination layer** that connects the 5 agent components into an end-to-end workflow:

1. **Request Understanding** (LLM) → Extract structured facts from natural language
2. **Policy Retrieval** (RAG) → Find relevant policies from knowledge base  
3. **Ticket Search** (Database) → Find historical/active tickets for context
4. **Decision Engine** (Deterministic) → Apply policy rules and make decision
5. **Response Generation** (LLM) → Generate user-friendly message text

The orchestrator contains **NO business logic**. All policy rules and decision logic reside in the deterministic decision engine (`policy_rules.py` + `decision_engine.py`).

## Architecture

```
User Request (natural language)
    ↓
┌───────────────────────────────────────┐
│  1. Request Understanding (LLM)       │  ExtractedFacts
│     app/agent/request_understanding.py│  - intent
├───────────────────────────────────────┤  - entities
│  2. Policy Retrieval (RAG)            │  - missing_information
│     app/rag/retriever.py              │
├───────────────────────────────────────┤  PolicyEvidence[]
│  3. Ticket Search (Database)          │  - policy_id, title, content
│     app/agent/ticket_search.py        │  - relevance score
├───────────────────────────────────────┤
│  4. Decision Engine (Deterministic)   │  TicketContext[]
│     app/agent/decision_engine.py      │  - ticket_id, employee
├───────────────────────────────────────┤  - issue_summary, status
│  5. Response Generator (LLM)          │  - is_active
│     app/agent/response_generator.py   │
└───────────────────────────────────────┘
    ↓
AgentResponse (to user)
```

## Component Responsibilities

### 1. Request Understanding (`understand_request`)
**Input:** Natural language string  
**Output:** `ExtractedFacts`  
**Role:** Use Gemini LLM to extract intent, entities, and identify missing information  
**Failure Mode:** Raise ValueError → workflow stops

### 2. Policy Retrieval (`PolicyRetriever.retrieve_policies`)
**Input:** Query string (built from ExtractedFacts)  
**Output:** `List[PolicyEvidence]`  
**Role:** Use ChromaDB + embeddings to find relevant policies  
**Failure Mode:** Return empty list → workflow continues (decision engine handles)

### 3. Ticket Search (`search_tickets`)
**Input:** `ExtractedFacts`  
**Output:** `List[TicketContext]`  
**Role:** Search `data/tickets.json` for related historical/active tickets  
**Failure Mode:** Return empty list → workflow continues

### 4. Decision Engine (`evaluate_decision`)
**Input:** ExtractedFacts + PolicyEvidence[] + TicketContext[]  
**Output:** `AgentDecision`  
**Role:** Apply deterministic policy rules to make RESOLVE/FOLLOW_UP/ESCALATE decision  
**Failure Mode:** Raise ValueError → workflow stops  
**CRITICAL:** This component is authoritative for the business decision

### 5. Response Generator (`generate_response`)
**Input:** `AgentDecision`  
**Output:** `AgentResponse`  
**Role:** Use Gemini LLM to generate natural language message text  
**Failure Mode:** Use deterministic fallback message  
**CRITICAL:** This component ONLY generates message text. It CANNOT change the decision.

## Decision Preservation

**The most critical aspect of Phase 6 is decision preservation:**

1. The **Decision Engine** makes the business decision (RESOLVE/FOLLOW_UP/ESCALATE)
2. The **Response Generator** receives this decision and generates ONLY the message text
3. The final **AgentResponse** preserves the decision value exactly as determined by the engine

### Why This Matters

- **Correctness:** Business rules must be enforced by deterministic code, not LLMs
- **Explainability:** Decisions are traceable to specific policy rules
- **Compliance:** Policy violations cannot be masked by friendly message text
- **Auditability:** The decision value is the authoritative record

### Example

```python
# Decision Engine determines: ESCALATE
decision = AgentDecision(
    decision="ESCALATE",  # AUTHORITATIVE
    intent="software_install",
    reason="Software not on approved list (KB-03)",
    ...
)

# Response Generator receives decision
# LLM generates friendly message but CANNOT change decision
response = generate_response(decision, api_key)

# Final response preserves decision
assert response.decision == "ESCALATE"  # MUST be true
assert "Software not on approved list" in response.message  # Explanation in message
```

Even if the LLM tried to generate "I can help you install that software!" (suggesting RESOLVE), the response.decision field would still be "ESCALATE" because it's set from the AgentDecision object.

## Error Handling

The orchestrator implements different error handling strategies based on component criticality:

### Critical Components (Hard Failures)
- **Request Understanding:** If LLM fails, raise ValueError → stop workflow
- **Decision Engine:** If rule evaluation fails, raise ValueError → stop workflow
- **Response Generation:** If LLM fails, use deterministic fallback → continue workflow

### Non-Critical Components (Soft Failures)
- **Policy Retrieval:** If RAG fails, use empty policy list → continue workflow
- **Ticket Search:** If database fails, use empty ticket list → continue workflow

This ensures that missing context data doesn't stop the agent, but missing core functionality does.

## Usage

### Basic Usage

```python
from app.agent.orchestrator import run_agent
from app.rag.retriever import PolicyRetriever

# Initialize RAG retriever (uses local embeddings, no API key needed)
retriever = PolicyRetriever(
    collection_name="veridian_policies"
)

# Run the agent
response = run_agent(
    user_request="I need to reset my password",
    gemini_api_key="your-gemini-key",
    rag_retriever=retriever
)

print(f"Decision: {response.decision}")
print(f"Message: {response.message}")
print(f"Sources: {response.sources}")
```

### Advanced Usage (Class-Based)

```python
from app.agent.orchestrator import AgentOrchestrator

# Create orchestrator instance
orchestrator = AgentOrchestrator(
    gemini_api_key="your-gemini-key",
    rag_retriever=retriever,
    gemini_model="gemini-1.5-flash",
    tickets_path=Path("custom/tickets.json")  # Optional
)

# Run multiple requests
for request in user_requests:
    try:
        response = orchestrator.run_agent(request)
        # Handle response
    except ValueError as e:
        # Handle failure
        log_error(e)
```

## Testing Strategy

Phase 6 tests use **mocks for all external dependencies** (LLM, RAG, database):

1. **Component Integration Tests:** Verify orchestrator calls all 5 components in order
2. **Error Handling Tests:** Verify graceful degradation when non-critical components fail
3. **Decision Preservation Tests:** Verify decision from engine is preserved in response
4. **Fallback Tests:** Verify deterministic fallback when response generation fails

All tests run WITHOUT real API keys. Real integration testing happens in Phase 7 (UI).

## Files

- `app/agent/orchestrator.py` - Main orchestration logic
- `app/agent/ticket_search.py` - Ticket search from data/tickets.json
- `app/agent/response_generator.py` - LLM response generation with decision preservation
- `tests/test_phase6_orchestrator.py` - Orchestrator tests (6 scenarios)

## Limitations (By Design)

Phase 6 does NOT:
- Create tickets (read-only access to ticket history)
- Update tickets (no side effects)
- Modify policies (read-only policy retrieval)
- Send emails or call external systems (no I/O beyond LLM/RAG)
- Implement business logic (all rules in decision_engine.py)

These are features for future phases or outside the agent's scope.

## Next Steps

Phase 7 will add the Streamlit UI to connect user input → orchestrator → user output.

