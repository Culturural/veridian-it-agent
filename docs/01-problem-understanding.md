# Problem Understanding

## Context

Veridian Corp needs an internal IT support agent that can understand employee requests and determine the appropriate next step using the provided company information.

## Core Problem

Employees may describe IT issues in natural language. The system needs to determine what the employee needs, identify relevant supplied information, and decide whether the request can be resolved, requires more information, or must be escalated.

## Key Constraint

The supplied policies and data are the source of truth. The system must not invent unsupported company information.

## Intended Agent Behavior

The agent should be able to:

- **Understand the issue** - Parse natural language requests and extract key information
- **Retrieve relevant policy information** - Find applicable policies from supplied data
- **Ask necessary follow-up questions** - Identify missing information needed for resolution
- **Resolve simple requests** - Handle straightforward cases automatically
- **Escalate risky or unclear requests** - Route complex cases appropriately
- **Create structured tickets** - Generate properly formatted ticket records
- **Show supporting sources** - Cite the specific policies or data used
- **Maintain an audit trail** - Log all interactions and decisions

## Initial Architecture Principle

Use the LLM for language understanding and response generation, while deterministic application logic enforces business rules and policy decisions.

The LLM should handle:
- Natural language understanding
- Intent classification
- Entity and fact extraction
- Follow-up question generation
- Natural language response generation

Deterministic Python logic should handle:
- Policy enforcement
- Approval requirements
- Limits and thresholds
- Escalation conditions
- Routing decisions
- Ticket state management
- Audit logging

This separation ensures explainability and prevents the LLM from making uncontrolled business decisions.

## What We Don't Know Yet

The following will be provided in the supplied assignment data:
- Specific company policies
- Approval workflows
- SLAs
- Employee attributes
- Permission structures
- Ticket rules
- Business processes
- Escalation contacts
- System capabilities

We must not invent these elements.
