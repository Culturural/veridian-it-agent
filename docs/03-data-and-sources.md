# Data & Sources

## 1. Source of Truth

The supplied Data Pack is the authoritative business source for this prototype.

**Assignment Constraint:** Unsupported information must not be invented. The agent must work exclusively with the supplied policies, employee requests, and ticket queue. Any information not present in these sources must be treated as unknown rather than hallucinated.

This constraint ensures:
- No fictional company policies
- No invented approval workflows
- No assumed employee attributes
- No fabricated business processes
- No guessed escalation procedures

## 2. Knowledge Base / Policies

The knowledge base contains IT support policies and procedures that guide resolution and decision-making.

### Policy Sources

**Knowledge Base Articles:**
- KB-01 through KB-10

**Policy Extracts:**
- Asset Management Policy (Extract)

### Policy Data Contract

Each policy record contains:

```json
{
  "id": "string",           // e.g., "KB-01" or "ASSET-01"
  "title": "string",        // Policy title
  "category": "string",     // Policy category
  "content": "string",      // Full policy text
  "source_type": "string"   // "knowledge_base" or "policy_extract"
}
```

**Example - Knowledge Base Article:**
```json
{
  "id": "KB-01",
  "title": "Password Reset",
  "category": "authentication",
  "content": "...",
  "source_type": "knowledge_base"
}
```

**Example - Policy Extract:**
```json
{
  "id": "ASSET-01",
  "title": "Asset Management Policy",
  "category": "hardware",
  "content": "...",
  "source_type": "policy_extract"
}
```

### Policy Categories

Categories are derived from the supplied content and are not invented. Common categories may include: authentication, hardware, software, network, access, etc. — but only as they appear in the source material.

## 3. Employee Requests

The dataset contains employee IT support requests that the agent must process.

### Request Coverage

**Request IDs:** REQ-01 through REQ-15

### Request Data Contract

Each request record contains:

```json
{
  "request_id": "string",           // e.g., "REQ-01"
  "employee": "string",             // Employee name
  "email": "string",                // Employee email
  "date_opened": "string",          // ISO date format (YYYY-MM-DD)
  "request": "string",              // Full request text
  "initial_action_taken": "string"  // Current status
}
```

**Example:**
```json
{
  "request_id": "REQ-01",
  "employee": "Aditi Sharma",
  "email": "aditi.sharma@veridian-corp.example",
  "date_opened": "2026-09-21",
  "request": "...",
  "initial_action_taken": "Not started"
}
```

### What Requests Do NOT Contain

The source request records do not include:
- Department
- Employee type
- Manager
- Priority level
- Severity
- Device age
- Intent classification
- Extracted entities

These may be **derived** by the agent through analysis, but they are not part of the source record.

## 4. Existing Ticket Queue

The ticket queue contains both active and historical tickets that provide context for agent decisions.

### Ticket Coverage

**Ticket IDs:** TK-1042 through TK-1051

### Ticket Data Contract

Each ticket record contains:

```json
{
  "ticket_id": "string",      // e.g., "TK-1042"
  "employee": "string",       // Employee name
  "issue_summary": "string",  // Brief description
  "status": "string"          // Ticket status
}
```

**Example:**
```json
{
  "ticket_id": "TK-1042",
  "employee": "R. Verma",
  "issue_summary": "VPN credential expired",
  "status": "Resolved (closed)"
}
```

### Ticket Status Values

Status values come from the supplied data and indicate whether a ticket is active or closed.

## 5. Ticket Semantics

### Closed (Historical) Tickets

A ticket is considered **CLOSED** and **historical** when its status indicates:
- `Resolved (closed)`
- `Rejected ... (closed)`
- `Approved ... (closed)`

**Characteristics:**
- Not actionable
- Cannot be modified
- May be used as historical context
- Provide precedent for similar cases
- Show prior resolution patterns
- Demonstrate consistency in decision-making

### Active Tickets

All other ticket statuses are considered **ACTIVE** unless the source explicitly states otherwise.

**Characteristics:**
- Actionable
- May require agent attention
- Can be updated
- Should be considered when processing new requests

### Use of Historical Tickets

Closed tickets serve important purposes:
- Precedent for handling similar requests
- Historical resolution patterns
- Consistency checking
- Context for policy interpretation
- Evidence of past decisions

The agent may reference closed tickets to inform current decisions but cannot modify or reopen them.

## 6. Source Data vs Derived Data

Understanding the distinction between source data, derived data, and system data is critical for maintaining integrity.

### Source Data

**Definition:** Information directly supplied by the assignment Data Pack.

**Examples:**
- Policy text from KB-01 through KB-10
- Employee request text from REQ-01 through REQ-15
- Ticket status from TK-1042 through TK-1051
- Employee names and emails

**Characteristics:**
- Authoritative
- Must not be modified
- Must be preserved exactly as supplied
- Cannot be fabricated

### Derived Data

**Definition:** Information extracted or inferred by the agent from source data through analysis.

**Examples:**
- Intent classification (e.g., "password_reset", "hardware_request")
- Extracted entities (e.g., device type, software name)
- Identified missing information
- Confidence scores
- Relevance assessments

**Characteristics:**
- Generated by LLM or application logic
- Not authoritative
- Should be traceable to source
- May require validation

### System Data

**Definition:** Information generated by the application itself to support operations.

**Examples:**
- New ticket IDs
- Timestamps
- Audit log entries
- Session identifiers
- User interactions
- Agent decisions and reasoning

**Characteristics:**
- Generated at runtime
- Not from assignment source
- Required for application function
- Should be logged and traceable

## 7. Data Integrity Rules

The following rules govern how data must be handled throughout the application:

### Rule 1: Never Invent Policies
Do not create, modify, or extrapolate policies beyond what is supplied. If a policy does not exist for a scenario, the agent must acknowledge the gap.

### Rule 2: Never Invent Approval Workflows
Approval processes, authorization rules, and escalation procedures must come from the supplied policies. Do not assume standard corporate workflows.

### Rule 3: Never Invent Employee Attributes
Do not assign departments, roles, seniority, permissions, or other attributes unless explicitly stated in the source data.

### Rule 4: Never Treat LLM Inference as Source Data
Intent classification, entity extraction, and other LLM outputs are derived data, not source data. Always maintain the distinction.

### Rule 5: Preserve Supplied Source Wording
Policy text, request text, and ticket descriptions must be stored exactly as supplied. Do not paraphrase or summarize source documents.

### Rule 6: Every Policy-Based Decision Must Be Traceable
When the agent makes a decision based on a policy, it must cite the specific policy ID and relevant content.

### Rule 7: Closed Tickets Are Historical Context Only
Tickets with closed status cannot be modified or reopened. They provide precedent but are not actionable.

### Rule 8: Active Tickets Are Actionable
Tickets without closed status should be considered in the agent's decision-making and may require attention.

## 8. Ground Truth Record Counts

The Veridian Corp Data Pack contains the following source records:

- **Policies:** 11 (KB-01 through KB-10, plus ASSET-01)
- **Employee Requests:** 15 (REQ-01 through REQ-15)
- **Existing Tickets:** 10 (TK-1042 through TK-1051)

**Total source records:** 36

## 9. Data Validation

The source data has been structured into JSON files without adding unsupported business information. All policy content, request text, and ticket information has been preserved exactly as supplied.

### Validation Checks

The validation script (`scripts/validate_data.py`) performs the following checks:

1. **Record Counts** - Verifies expected number of policies (11), requests (15), and tickets (10)
2. **IDs** - Confirms all expected IDs are present and no unexpected IDs exist
3. **Required Fields** - Ensures all records contain required fields per the data contract
4. **Duplicates** - Detects duplicate IDs within each dataset
5. **JSON Validity** - Confirms all files are valid JSON

### What Is NOT Validated

The validation script does NOT enforce business rules such as:
- Policy applicability logic
- Approval workflows
- Escalation conditions
- Priority assignments
- SLA compliance

These business rules will be implemented in the decision engine based on the policy content, not as data validation constraints.
