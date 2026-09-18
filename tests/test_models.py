"""
Tests for Pydantic data models.

Tests source models, derived agent models, and validation logic
without calling external services (OpenAI, ChromaDB, etc.).
"""

import pytest
from pydantic import ValidationError

from app.database.models import Policy, EmployeeRequest, Ticket, AuditEvent
from app.agent.schemas import (
    ExtractedFacts,
    PolicyEvidence,
    TicketContext,
    AgentDecision,
    AgentResponse,
)


# ============================================================================
# SOURCE MODEL TESTS
# ============================================================================

def test_valid_policy_creation():
    """Test creating a valid Policy from source data."""
    policy = Policy(
        id="KB-01",
        title="Password Reset",
        category="authentication",
        content="Employees can reset their own password via the self-service portal.",
        source_type="knowledge_base"
    )
    
    assert policy.id == "KB-01"
    assert policy.title == "Password Reset"
    assert policy.category == "authentication"
    assert policy.source_type == "knowledge_base"


def test_valid_employee_request_creation():
    """Test creating a valid EmployeeRequest from source data."""
    request = EmployeeRequest(
        request_id="REQ-01",
        employee="Aditi Sharma",
        email="aditi.sharma@veridian-corp.example",
        date_opened="Mon 21 Sep",
        request="My laptop won't turn on at all, it's completely dead, had it about 3.5 years now.",
        initial_action_taken="Not started"
    )
    
    assert request.request_id == "REQ-01"
    assert request.employee == "Aditi Sharma"
    assert request.email == "aditi.sharma@veridian-corp.example"
    assert request.initial_action_taken == "Not started"


def test_valid_ticket_creation():
    """Test creating a valid Ticket from source data."""
    ticket = Ticket(
        ticket_id="TK-1042",
        employee="R. Verma",
        issue_summary="VPN credential expired",
        status="Resolved (closed)"
    )
    
    assert ticket.ticket_id == "TK-1042"
    assert ticket.employee == "R. Verma"
    assert ticket.status == "Resolved (closed)"


def test_ticket_closed_semantics():
    """Test that closed ticket status is correctly identified."""
    # Closed tickets
    closed_statuses = [
        "Resolved (closed)",
        "Rejected — no business justification provided (closed)",
        "Approved at 35GB (closed)",
    ]
    
    for status in closed_statuses:
        ticket = Ticket(
            ticket_id="TK-TEST",
            employee="Test User",
            issue_summary="Test issue",
            status=status
        )
        context = TicketContext.from_ticket(ticket)
        assert context.is_active is False, f"Expected closed status for: {status}"


def test_ticket_active_semantics():
    """Test that active ticket status is correctly identified."""
    # Active tickets
    active_statuses = [
        "Approved — pending fulfillment (active)",
        "Pending Security review (active)",
        "Pending Finance (active)",
        "Escalated to Security — under investigation (active)",
    ]
    
    for status in active_statuses:
        ticket = Ticket(
            ticket_id="TK-TEST",
            employee="Test User",
            issue_summary="Test issue",
            status=status
        )
        context = TicketContext.from_ticket(ticket)
        assert context.is_active is True, f"Expected active status for: {status}"


# ============================================================================
# DERIVED AGENT MODEL TESTS
# ============================================================================

def test_valid_extracted_facts():
    """Test creating valid ExtractedFacts."""
    facts = ExtractedFacts(
        intent="laptop_issue",
        entities={
            "device": "laptop",
            "age_years": 3.5
        },
        missing_information=[]
    )
    
    assert facts.intent == "laptop_issue"
    assert facts.entities["device"] == "laptop"
    assert facts.entities["age_years"] == 3.5
    assert len(facts.missing_information) == 0


def test_extracted_facts_with_missing_info():
    """Test ExtractedFacts with missing information."""
    facts = ExtractedFacts(
        intent="unclear",
        entities={},
        missing_information=["device_type", "issue_description"]
    )
    
    assert facts.intent == "unclear"
    assert len(facts.entities) == 0
    assert len(facts.missing_information) == 2


def test_valid_policy_evidence():
    """Test creating valid PolicyEvidence."""
    evidence = PolicyEvidence(
        policy_id="KB-01",
        title="Password Reset",
        content="Employees can reset their own password via the self-service portal.",
        relevance=0.95
    )
    
    assert evidence.policy_id == "KB-01"
    assert evidence.relevance == 0.95


def test_policy_evidence_without_relevance():
    """Test PolicyEvidence without relevance score."""
    evidence = PolicyEvidence(
        policy_id="KB-01",
        title="Password Reset",
        content="Test content"
    )
    
    assert evidence.relevance is None


def test_invalid_policy_evidence_relevance():
    """Test that PolicyEvidence rejects invalid relevance scores."""
    with pytest.raises(ValidationError):
        PolicyEvidence(
            policy_id="KB-01",
            title="Password Reset",
            content="Test content",
            relevance=1.5  # Invalid: > 1.0
        )
    
    with pytest.raises(ValidationError):
        PolicyEvidence(
            policy_id="KB-01",
            title="Password Reset",
            content="Test content",
            relevance=-0.1  # Invalid: < 0.0
        )


# ============================================================================
# DECISION MODEL TESTS
# ============================================================================

def test_valid_agent_decision():
    """Test creating a valid AgentDecision."""
    facts = ExtractedFacts(
        intent="password_reset",
        entities={"issue": "locked_out"},
        missing_information=[]
    )
    
    evidence = PolicyEvidence(
        policy_id="KB-01",
        title="Password Reset",
        content="Test policy content"
    )
    
    decision = AgentDecision(
        decision="RESOLVE",
        intent="password_reset",
        confidence=0.95,
        extracted_facts=facts,
        relevant_policies=[evidence],
        relevant_tickets=[],
        missing_information=[],
        reason="Employee is locked out after failed login attempts.",
        actions=["Unlock account manually"],
        sources=["KB-01"]
    )
    
    assert decision.decision == "RESOLVE"
    assert decision.confidence == 0.95
    assert len(decision.relevant_policies) == 1
    assert decision.sources == ["KB-01"]


def test_invalid_agent_decision_value():
    """Test that AgentDecision rejects invalid decision values."""
    facts = ExtractedFacts(
        intent="test",
        entities={},
        missing_information=[]
    )
    
    with pytest.raises(ValidationError):
        AgentDecision(
            decision="APPROVE",  # Invalid: not in Literal types
            intent="test",
            confidence=0.8,
            extracted_facts=facts,
            reason="Test",
            actions=[],
            sources=[]
        )


def test_invalid_confidence_outside_range():
    """Test that AgentDecision rejects confidence outside 0-1 range."""
    facts = ExtractedFacts(
        intent="test",
        entities={},
        missing_information=[]
    )
    
    # Confidence > 1.0
    with pytest.raises(ValidationError):
        AgentDecision(
            decision="RESOLVE",
            intent="test",
            confidence=1.5,
            extracted_facts=facts,
            reason="Test",
            actions=[],
            sources=[]
        )
    
    # Confidence < 0.0
    with pytest.raises(ValidationError):
        AgentDecision(
            decision="RESOLVE",
            intent="test",
            confidence=-0.1,
            extracted_facts=facts,
            reason="Test",
            actions=[],
            sources=[]
        )


def test_agent_decision_with_follow_up():
    """Test AgentDecision for FOLLOW_UP case."""
    facts = ExtractedFacts(
        intent="unclear",
        entities={},
        missing_information=["device_type", "issue_description"]
    )
    
    decision = AgentDecision(
        decision="FOLLOW_UP",
        intent="unclear",
        confidence=0.3,
        extracted_facts=facts,
        missing_information=["device_type", "issue_description"],
        reason="Request is too vague to process.",
        actions=["Request clarification"],
        sources=[]
    )
    
    assert decision.decision == "FOLLOW_UP"
    assert len(decision.missing_information) == 2


def test_agent_decision_with_escalate():
    """Test AgentDecision for ESCALATE case."""
    facts = ExtractedFacts(
        intent="admin_access_request",
        entities={"system": "finance_reporting_server"},
        missing_information=[]
    )
    
    decision = AgentDecision(
        decision="ESCALATE",
        intent="admin_access_request",
        confidence=0.85,
        extracted_facts=facts,
        reason="Admin access requests require security review.",
        actions=["Escalate to Security team"],
        sources=[]
    )
    
    assert decision.decision == "ESCALATE"
    assert decision.confidence == 0.85


# ============================================================================
# RESPONSE MODEL TESTS
# ============================================================================

def test_valid_agent_response():
    """Test creating a valid AgentResponse."""
    response = AgentResponse(
        message="I can help you reset your password. You can use the self-service portal at any time.",
        decision="RESOLVE",
        sources=["KB-01"],
        ticket_id=None,
        follow_up_questions=[]
    )
    
    assert response.decision == "RESOLVE"
    assert response.sources == ["KB-01"]
    assert response.ticket_id is None
    assert len(response.follow_up_questions) == 0


def test_agent_response_with_follow_up_questions():
    """Test AgentResponse with follow-up questions."""
    response = AgentResponse(
        message="I need more information to help you.",
        decision="FOLLOW_UP",
        sources=[],
        ticket_id=None,
        follow_up_questions=[
            "What type of device are you having issues with?",
            "Can you describe the specific problem?"
        ]
    )
    
    assert response.decision == "FOLLOW_UP"
    assert len(response.follow_up_questions) == 2


def test_agent_response_with_ticket_id():
    """Test AgentResponse with generated ticket."""
    response = AgentResponse(
        message="Your request has been escalated to the Security team.",
        decision="ESCALATE",
        sources=["KB-09"],
        ticket_id="TK-1052",
        follow_up_questions=[]
    )
    
    assert response.decision == "ESCALATE"
    assert response.ticket_id == "TK-1052"


# ============================================================================
# SYSTEM MODEL TESTS
# ============================================================================

def test_valid_audit_event():
    """Test creating a valid AuditEvent."""
    event = AuditEvent(
        event_type="request_processed",
        timestamp="2026-09-18T10:30:00Z",
        request_id="REQ-01",
        details={"decision": "RESOLVE", "confidence": 0.95}
    )
    
    assert event.event_type == "request_processed"
    assert event.request_id == "REQ-01"
    assert event.details["decision"] == "RESOLVE"


def test_audit_event_without_request_id():
    """Test AuditEvent without request_id."""
    event = AuditEvent(
        event_type="system_startup",
        timestamp="2026-09-18T10:00:00Z",
        details={"version": "1.0.0"}
    )
    
    assert event.request_id is None
    assert event.details["version"] == "1.0.0"
