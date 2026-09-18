# Decision Engine Architecture

**Last Updated:** 2026-09-18  
**Phase:** 5 - Deterministic Policy Decision Engine (CORRECTED)

---

## Overview

The Decision Engine is the **deterministic policy enforcement layer** of the Veridian IT Service Agent. It takes structured input from the LLM understanding layer and RAG retriever, then applies pure business logic to produce a decision.

**Critical Principles:**
1. The decision engine **NEVER** calls an LLM
2. The decision engine **NEVER** invents policies
3. The decision engine **ONLY** enforces rules from the 11 supplied policies (KB-01 to KB-10, ASSET-01)
4. **Policy evidence is authoritative** - rules execute ONLY when corresponding PolicyEvidence is present

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Decision Engine                          │
│                                                              │
│  Input:                                                      │
│    - ExtractedFacts  (from LLM understanding)               │
│    - PolicyEvidence  (from RAG retriever) ← AUTHORITATIVE   │
│    - TicketContext   (from ticket database)                 │
│                                                              │
│  Processing:                                                 │
│    1. For each policy rule function:                         │
│       - Check if required PolicyEvidence is present          │
│       - If not present, rule returns None (skipped)          │
│       - If present, evaluate deterministic rule logic        │
│    2. First matching rule returns decision                   │
│    3. If no rule matches → handle unsupported request        │
│                                                              │
│  Output:                                                     │
│    - AgentDecision (RESOLVE/FOLLOW_UP/ESCALATE)            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Policy Evidence Requirement (NEW):**
- Password request WITHOUT KB-01 in policies list → unsupported
- Laptop request WITHOUT KB-03 in policies list → unsupported
- RAG is not decorative - presence of policy evidence determines rule applicability

---

## Core Components

### 1. Decision Engine (`app/agent/decision_engine.py`)

**Main Function:** `evaluate_decision(facts, policies, tickets) → AgentDecision`

The orchestrator that:
1. Passes structured models to each policy rule function
2. Executes rules in sequence until one matches
3. Handles unsupported request types gracefully
4. Calculates confidence (as metadata only, not for business decisions)

**Decision Outcomes:**
- `RESOLVE`: Request can be fulfilled automatically per policy
- `FOLLOW_UP`: Need more information before deciding
- `ESCALATE`: Request requires human intervention

### 2. Policy Rules (`app/agent/policy_rules.py`)

**Structure:** Each policy rule is a separate function with structured interface

```python
def <policy>_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext]
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    1. Check if required policy evidence is present
    2. Check if intent matches
    3. Evaluate policy logic
    
    Returns:
        (decision, reasoning, actions, policy_sources) or None
    """
```

**Implemented Rules:**
1. `password_reset_rule` (KB-01)
2. `vpn_rule` (KB-02)
3. `laptop_rule` (KB-03 + ASSET-01)
4. `software_rule` (KB-04)
5. `printer_rule` (KB-05)
6. `mailbox_rule` (KB-06)
7. `guest_wifi_rule` (KB-07)
8. `expense_rule` (KB-08)
9. `security_rule` (KB-09)
10. `wfh_rule` (KB-10)

---

## Policy Rule Logic (Corrected)

### KB-01: Password Reset

**Policy Evidence Required:** KB-01 must be in policies list

**Auto-resolve conditions:**
- Normal password reset
- Employee ID provided

**Escalate conditions:**
- Account locked after >5 failed attempts (requires manual IT unlock)

**Key business rule:**
> "Employees can reset their own password via the self-service portal at any time. If locked out after 5 failed attempts, contact IT to unlock the account manually. No approval required."

---

### KB-02: VPN Access

**Policy Evidence Required:** KB-02 must be in policies list

**Auto-resolve conditions:**
- Full-time employee (automatic provisioning)
- Expired credentials (renewal instructions)

**Escalate conditions:**
- Contractor (requires manager approval via access request form)

**Follow-up conditions:**
- Employee type unknown

**Key business rule:**
> "VPN access is granted automatically to all full-time employees. Contractors require manager approval submitted via the access request form. VPN credentials expire every 90 days and must be renewed by the employee."

---

### KB-03 + ASSET-01: Laptop Replacement (CORRECTED)

**Policy Evidence Required:** KB-03 must be in policies list; ASSET-01 optional but affects logic

**KB-03:** "Laptops are eligible for replacement after 3 years of service, or earlier in case of verified hardware failure. Requests must be raised at least 2 weeks in advance of intended replacement."

**ASSET-01:** "All company-issued hardware, including laptops and monitors, follows a standard 4-year refresh cycle from date of issue. Early replacement outside this cycle requires Finance sign-off in addition to IT approval."

**Corrected Logic:**

**A. Laptop >= 4 years:**
- Normal refresh cycle case
- → RESOLVE with 2-week advance requirement
- Sources: KB-03, ASSET-01

**B. Laptop 3 to <4 years:**
- Eligible per KB-03 (>3 years)
- BUT early replacement per ASSET-01 (<4 years)
- → ESCALATE (requires Finance sign-off + IT approval)
- Sources: KB-03, ASSET-01

**C. Laptop <3 years:**
- Not eligible under normal KB-03 age criterion
- → ESCALATE (requires Finance sign-off + IT approval if approved)
- Sources: KB-03, ASSET-01

**D. Verified hardware failure at ANY age:**
- Eligible per KB-03 regardless of age
- **BUT** if <4 years with ASSET-01 present → still requires Finance sign-off
- → ESCALATE if <4 years, RESOLVE if >=4 years
- Sources: KB-03, ASSET-01 (if applicable)

**E. Reported vs Verified:**
- Reported failure ≠ verified failure
- Reported but not verified → FOLLOW_UP for verification
- REQ-01 (3.5 years, dead, unverified) → FOLLOW_UP

**IMPORTANT:** Do NOT equate employee tenure with laptop age. Use laptop_age_years entity.

---

### KB-04: Software Installation

**Policy Evidence Required:** KB-04 must be in policies list

**Auto-resolve conditions:**
- Software in approved catalog (`in_catalog=True`)

**Escalate conditions:**
- Software NOT in approved catalog (`in_catalog=False`)
- Requires IT Security review (3-5 business days)

**Follow-up conditions:**
- Catalog status unknown (`in_catalog=None`)
- NEVER assume software is approved

**Key business rule:**
> "Standard software (listed in the approved catalog) can be self-installed. Non-catalog software requires IT Security review, which takes 3–5 business days."

---

### KB-05: Printer Troubleshooting

**Policy Evidence Required:** KB-05 must be in policies list

**Auto-resolve conditions:**
- Troubleshooting not yet attempted
- Provide instructions: check queue, restart spooler

**Escalate conditions:**
- Troubleshooting attempted, issue persists, asset tag available
- Log ticket with asset tag

**Follow-up conditions:**
- Troubleshooting attempted, issue persists, asset tag missing

**Key business rule:**
> "For printer issues, first check the printer queue and restart the print spooler. If the issue persists after restart, log a ticket with the printer's asset tag."

**IMPORTANT:** NO floor-based authorization rules exist in supplied policy.

---

### KB-06: Email Mailbox Quota

**Policy Evidence Required:** KB-06 must be in policies list

**Auto-resolve conditions:**
- Mailbox full/nearing full → archive old mail
- Requested quota ≤25GB (within default)

**Escalate conditions:**
- Quota increase 26-50GB (requires manager approval)
- Quota increase >50GB (exceeds maximum cap)

**Key business rule:**
> "Default mailbox quota is 25GB. Employees nearing quota should archive old mail. Quota increases beyond 25GB require manager approval and are capped at 50GB."

**IMPORTANT:** 
- 50GB is the MAXIMUM (hard cap)
- Historical ticket TK-1045 showing 100GB MUST NOT override this cap
- Policy is explicit: "capped at 50GB"

---

### KB-07: Guest Wi-Fi Access

**Policy Evidence Required:** KB-07 must be in policies list

**Auto-resolve conditions:**
- Duration ≤24 hours
- Generated from front-desk kiosk
- No IT ticket required

**Escalate conditions:**
- Duration >24 hours
- Extended access not covered by supplied policy
- Do NOT invent extension procedure

**Key business rule:**
> "Guest Wi-Fi credentials are valid for 24 hours and can be generated by any employee from the front-desk kiosk. No IT ticket required."

**IMPORTANT:** NO 7-day extension policy exists in Data Pack.

---

### KB-08: Expense Software Access

**Policy Evidence Required:** KB-08 must be in policies list

**This is EXPENSE SOFTWARE ACCESS, not reimbursement.**

**Auto-resolve conditions:**
- Login/technical issue with existing account (`account_exists=True`)

**Escalate conditions:**
- Access request for new account (`account_exists=False`)
- Finance grants access, not IT

**Follow-up conditions:**
- Account existence unknown (`account_exists=None`)
- Need to verify first

**Key business rule:**
> "Access to the expense management tool is granted by Finance, not IT. IT can only assist with login/technical issues once an account already exists."

**IMPORTANT:** NO receipt requirements, NO reimbursement approval thresholds (not in policy).

---

### KB-09: Security Incident Reporting

**Policy Evidence Required:** KB-09 must be in policies list

**Applies ONLY to supplied categories:**
- Suspected phishing email
- Malware
- Unauthorized access attempt

**All applicable incidents:**
- → ESCALATE to security@veridian-corp.example immediately
- Should NOT be forwarded to other employees

**Key business rule:**
> "Any suspected phishing email, malware, or unauthorized access attempt must be reported to security@veridian-corp.example immediately and should not be forwarded to other employees."

**IMPORTANT:** NOT a generic "all security incidents" rule. Only applies to the three supplied categories.

---

### KB-10: Work-From-Home Equipment

**Policy Evidence Required:** KB-10 must be in policies list

**Escalate conditions (eligible):**
- Remote work >3 days/week
- Eligible for one-time allowance (chair, monitor)
- Requires manager sign-off + Finance processing
- IT handles shipping AFTER approval

**Escalate conditions (not eligible):**
- Remote work ≤3 days/week
- Not eligible under supplied policy

**Follow-up conditions:**
- Remote days per week unknown

**Key business rule:**
> "Employees working remotely more than 3 days/week are eligible for a one-time home office equipment allowance (chair, monitor). Requires manager sign-off and Finance processing — IT only handles the equipment shipping request once approved."

**IMPORTANT:** Do NOT introduce permanent WFH status, keyboard, mouse, or other requirements not present in KB-10.

---

## Ticket History Integration

**Principle:** Historical tickets provide **context and precedent**, but **NEVER override policy**.

**How tickets are used:**
1. Provide precedent examples
2. Show common resolution patterns
3. Give context for similar requests

**What tickets DON'T do:**
- Override explicit policy rules
- Create new implicit policies
- Allow/deny requests that policy doesn't cover

**Example:**
- TK-1045 shows mailbox increased to 100GB (historical)
- KB-06 caps quota at 50GB
- Decision: 40GB request → ESCALATE (manager approval), respecting 50GB cap
- Historical ticket does NOT override 50GB policy cap

---

## Unsupported Requests

**Decision logic:**
- Vague/unclear with missing info → FOLLOW_UP to clarify
- Policies retrieved but no rule matched → ESCALATE (related but not covered)
- No policies and clear intent → ESCALATE (unsupported)

**Examples:**
- REQ-10 (admin access): No general admin-access policy → ESCALATE, NO invented authorization rules
- REQ-15 ("it's not working"): Vague/unclear → FOLLOW_UP

**Never:**
- Invent policies
- Guess at authorization rules
- Make up approval workflows

---

## Confidence

**Purpose:** Metadata for visibility, NOT for business decisions

**Calculation:**
- Full information: 1.0
- Some missing info: 0.5-0.9 (reduces by 0.1 per missing item)
- Unsupported request: 0.3

**IMPORTANT:** 
- NO "confidence < X => escalate" logic
- Decision outcomes come from policy rules, not confidence thresholds
- Confidence is informational only

---

## Testing Strategy

### Test Coverage (47 tests)

1. **Per-policy tests** (30+ tests)
   - Valid auto-resolve case
   - Follow-up case (missing info)
   - Escalate case (policy restriction)
   - Edge cases

2. **Policy evidence tests** (10 new tests)
   - Password request without KB-01 → unsupported
   - Password request with wrong policy → unsupported
   - Laptop without KB-03 → unsupported
   - Verified failure <4 years → ESCALATE (Finance)
   - Expense with account_exists variations
   - Admin access (no invented rules)
   - Vague request → FOLLOW_UP

3. **Integration tests** (7 tests)
   - Full context (facts + policies + tickets)
   - Ticket history doesn't override policy
   - Active vs closed ticket semantics
   - Confidence calculation

---

## Implementation Notes

### Design Principles

1. **Policy Evidence is Authoritative**
   - Rules check for required PolicyEvidence at start
   - Without evidence, rule returns None
   - RAG determines which rules can execute

2. **Structured Interfaces**
   - Rules receive ExtractedFacts, PolicyEvidence list, TicketContext list
   - No Dict[str, Any] conversions
   - Type-safe and maintainable

3. **Explainability**
   - Every decision includes detailed reasoning
   - Policy sources are always cited
   - Recommended actions are explicit

4. **Safety**
   - Conservative decision-making (when in doubt, escalate)
   - No invented policies or "creative" interpretations
   - Tickets provide context but never override policy

### Code Organization

```
app/agent/
├── decision_engine.py      # Orchestrator (evaluate_decision)
├── policy_rules.py         # Individual rule functions with policy evidence checks
└── schemas.py              # Pydantic models

tests/
└── test_decision_engine.py # 47 comprehensive tests

docs/
└── 07-decision-engine.md   # This document
```

---

## Summary

The Decision Engine is where **policy meets execution**. It's:
- **Deterministic**: Same input → same output (no LLM randomness)
- **Traceable**: Every decision cites its policy sources
- **Evidence-based**: Rules execute only with required PolicyEvidence
- **Safe**: Conservative, with escalation when needed
- **Maintainable**: Clear structure, comprehensive tests
- **Accurate**: Implements ONLY what the Data Pack explicitly states

**Key constraints:**
1. The ONLY authoritative business rules are the 11 supplied policies
2. Policy evidence must be present for rules to execute
3. Tickets provide context but never override policy
4. Confidence is metadata, not a business decision factor

**Test Status:** All 47 decision engine tests passing. All 102 total project tests passing. Phase 5 architecturally correct and ready for Phase 6 integration.
