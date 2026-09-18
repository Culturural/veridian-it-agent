"""
Agent-specific data models for the Veridian IT Service Agent.

These models represent DERIVED DATA (extracted by the agent) and
decision structures that flow through the agent pipeline.

DERIVED DATA is information extracted or interpreted from source data
and should not be treated as authoritative business facts.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any, Dict, List, Literal, Optional


class ExtractedFacts(BaseModel):
    """
    Information derived from natural-language input through LLM analysis.
    
    This is DERIVED DATA - not authoritative source information.
    The model allows unknown information to remain unknown.
    """
    intent: str = Field(..., description="Classified intent of the request")
    entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities as key-value pairs"
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Information needed but not present in the request"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "intent": "laptop_issue",
                "entities": {
                    "device": "laptop",
                    "age_years": 3.5
                },
                "missing_information": []
            }
        }
    )


class PolicyEvidence(BaseModel):
    """
    Retrieved policy evidence from the knowledge base.
    
    This represents a policy that was retrieved as relevant to a request.
    Content is preserved from source - not modified.
    """
    policy_id: str = Field(..., description="Policy ID from source")
    title: str = Field(..., description="Policy title")
    content: str = Field(..., description="Policy content as supplied")
    relevance: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Optional relevance score from retrieval"
    )


class TicketContext(BaseModel):
    """
    Ticket information with derived active/closed status.
    
    Combines source ticket data with derived semantic information
    about whether the ticket is actionable.
    """
    ticket_id: str = Field(..., description="Ticket ID from source")
    employee: str = Field(..., description="Employee name")
    issue_summary: str = Field(..., description="Issue description")
    status: str = Field(..., description="Original status as supplied")
    is_active: bool = Field(..., description="Whether ticket is active (derived from status)")
    
    @staticmethod
    def from_ticket(ticket: "Ticket") -> "TicketContext":
        """
        Create TicketContext from a source Ticket.
        
        Applies ticket semantics:
        - Closed: status contains "Resolved (closed)", "Rejected ... (closed)", 
          or "Approved ... (closed)"
        - Active: all other statuses unless explicitly stated otherwise
        """
        from app.database.models import Ticket
        
        status_lower = ticket.status.lower()
        is_closed = (
            "resolved (closed)" in status_lower or
            "rejected" in status_lower and "(closed)" in status_lower or
            "approved" in status_lower and "(closed)" in status_lower
        )
        
        return TicketContext(
            ticket_id=ticket.ticket_id,
            employee=ticket.employee,
            issue_summary=ticket.issue_summary,
            status=ticket.status,
            is_active=not is_closed
        )


class AgentDecision(BaseModel):
    """
    Structured decision made by the agent.
    
    This combines extracted facts, retrieved evidence, and decision logic
    to produce an actionable recommendation.
    """
    decision: Literal["RESOLVE", "FOLLOW_UP", "ESCALATE"] = Field(
        ...,
        description="Agent decision: RESOLVE (can handle), FOLLOW_UP (needs info), ESCALATE (risky/unclear)"
    )
    intent: str = Field(..., description="Classified intent")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0 and 1"
    )
    extracted_facts: ExtractedFacts = Field(..., description="Facts extracted from request")
    relevant_policies: List[PolicyEvidence] = Field(
        default_factory=list,
        description="Policies retrieved as relevant"
    )
    relevant_tickets: List[TicketContext] = Field(
        default_factory=list,
        description="Historical/active tickets for context"
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Information needed to proceed"
    )
    reason: str = Field(..., description="Explanation for the decision")
    actions: List[str] = Field(
        default_factory=list,
        description="Recommended actions to take"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Policy IDs or other source references used"
    )
    
    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class AgentResponse(BaseModel):
    """
    User-facing response from the agent.
    
    This is what the employee sees - concise, clear, and actionable.
    Does not contain internal reasoning or chain-of-thought.
    """
    message: str = Field(..., description="User-facing response message")
    decision: Literal["RESOLVE", "FOLLOW_UP", "ESCALATE"] = Field(
        ...,
        description="Decision type"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Policy IDs or sources cited"
    )
    ticket_id: Optional[str] = Field(
        None,
        description="Generated ticket ID if a ticket was created"
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="Questions to ask if more information is needed"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "I can help you reset your password. You can use the self-service portal...",
                "decision": "RESOLVE",
                "sources": ["KB-01"],
                "ticket_id": None,
                "follow_up_questions": []
            }
        }
    )
