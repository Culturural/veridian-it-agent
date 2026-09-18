# Requirements

## Functional Requirements

| ID | Assignment Requirement | Planned Implementation | Status |
|----|------------------------|------------------------|--------|
| R1 | Understand employee issue | LLM-based intent and entity extraction | Planned |
| R2 | Find relevant policy/resolution | Policy retrieval using ChromaDB RAG | Planned |
| R3 | Ask sensible follow-up questions | Missing-information detection logic | Planned |
| R4 | Resolve simple requests | Decision engine + response generator | Planned |
| R5 | Escalate risky or unclear requests | Deterministic escalation logic | Planned |
| R6 | Create structured ticket | SQLite ticket manager with Pydantic models | Planned |
| R7 | Show source used | Policy references and citations in UI | Planned |
| R8 | Maintain audit trail | SQLite audit log with full interaction history | Planned |

## Non-Functional Requirements

### Explainability
- All agent decisions must be traceable
- Source attribution must be explicit
- Business logic must be deterministic and auditable

### Reliability
- No hallucination of company policies
- No invention of unsupported workflows
- Graceful handling of missing information

### Source Integrity
- Only supplied data may be used as source of truth
- Clear distinction between known and unknown information
- Explicit citation of policy sources

### Development Constraints
- Simple local setup
- Demonstrable within 6-hour assignment window
- Maintainable project structure
- Standard Python tooling

### Technical Quality
- Type hints and Pydantic validation
- Modular architecture
- Clear separation of concerns
- Testable components

## Out of Scope

The following are explicitly NOT part of this assignment:
- Agent frameworks (LangChain, CrewAI, AutoGen)
- Production deployment infrastructure
- Advanced authentication/authorization
- Real-time notifications
- Multi-tenancy
- External integrations beyond OpenAI API

## Success Criteria

The agent will be considered successful if it can:
1. Parse natural language IT requests
2. Retrieve relevant policies from supplied data
3. Identify when information is missing
4. Generate appropriate follow-up questions
5. Make correct escalation decisions based on rules
6. Create well-structured tickets
7. Cite sources for all recommendations
8. Maintain complete audit logs
9. Handle the supplied test cases correctly
10. Demonstrate explainable decision-making
