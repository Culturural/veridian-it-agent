"""
Decision Engine for Veridian IT Service Agent

This module implements deterministic policy enforcement logic.
NO LLM calls - pure business logic based on supplied policies.

The decision engine:
1. Takes ExtractedFacts + PolicyEvidence + TicketContext as input
2. Applies policy rule functions from policy_rules.py
3. Returns AgentDecision with outcome, reasoning, and actions

Key principles:
- ONLY use rules from the 11 supplied policies (KB-01 to KB-10, ASSET-01)
- NO invention of policies or company rules
- Historical tickets provide context but MUST NOT override policy
- Unknown/unsupported requests → FOLLOW_UP or ESCALATE (never fake approval)
"""

from typing import List, Optional, Tuple, Literal
from app.agent.schemas import (
    ExtractedFacts,
    PolicyEvidence,
    TicketContext,
    AgentDecision,
)
from app.agent.policy_rules import (
    password_reset_rule,
    vpn_rule,
    laptop_rule,
    software_rule,
    printer_rule,
    mailbox_rule,
    guest_wifi_rule,
    expense_rule,
    security_rule,
    wfh_rule,
)

# Type alias for decision outcomes
DecisionOutcome = Literal["RESOLVE", "FOLLOW_UP", "ESCALATE"]


def evaluate_decision(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> AgentDecision:
    """
    Deterministically evaluate a request against policies and ticket history.
    
    This is the core decision engine. It:
    1. Identifies which policy rule(s) apply based on intent
    2. Executes the matching rule function(s)
    3. Incorporates ticket history for precedent/context (not override)
    4. Returns a structured AgentDecision
    
    Args:
        facts: Extracted facts from the user's request (from LLM understanding)
        policies: Retrieved policy evidence from RAG (may be empty)
        tickets: Historical ticket context from similar requests
        
    Returns:
        AgentDecision with decision (RESOLVE/FOLLOW_UP/ESCALATE), reasoning, actions, sources
        
    Decision logic:
    - If a clear policy match exists and requirements are met → RESOLVE
    - If policy exists but info is missing → FOLLOW_UP
    - If no policy covers the request or complex approval needed → ESCALATE
    """
    
    # Try each policy rule to see which one applies
    # Rules return None if they don't apply to this intent or lack required policy evidence
    rule_functions = [
        security_rule,
        password_reset_rule,
        vpn_rule,
        laptop_rule,
        software_rule,
        printer_rule,
        mailbox_rule,
        guest_wifi_rule,
        expense_rule,
        wfh_rule,
    ]
    
    for rule_func in rule_functions:
        result = rule_func(facts, policies, tickets)
        if result is not None:
            # Unpack rule result
            decision_outcome, reasoning, recommended_actions, policy_sources = result
            
            # Calculate confidence based on missing information
            # Confidence is metadata only - does not determine business decision
            missing_info = facts.missing_information
            confidence = 1.0 if not missing_info else max(0.5, 1.0 - (len(missing_info) * 0.1))
            
            # Build the final AgentDecision
            decision = AgentDecision(
                decision=decision_outcome,
                intent=facts.intent,
                confidence=confidence,
                extracted_facts=facts,
                relevant_policies=policies,
                relevant_tickets=tickets,
                missing_information=missing_info,
                reason=reasoning,
                actions=recommended_actions,
                sources=policy_sources,
            )
            
            return decision
    
    # No rule matched - handle unsupported request
    return _handle_unsupported_request(facts, policies, tickets)


def _handle_unsupported_request(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> AgentDecision:
    """
    Handle requests that don't match any known policy rule.
    
    We NEVER invent policies or make up approvals.
    
    Decision logic:
    - If request is vague/unclear → FOLLOW_UP to gather more info
    - If policies retrieved but no rule matched → ESCALATE (related but not covered)
    - If no policies and clear intent → ESCALATE
    
    Args:
        facts: The extracted facts
        policies: Retrieved policies (may provide context)
        tickets: Historical tickets (may provide precedent)
        
    Returns:
        AgentDecision with FOLLOW_UP or ESCALATE decision
    """
    
    # Determine if request is vague/unclear
    has_missing_info = len(facts.missing_information) > 0
    intent_is_vague = "unclear" in facts.intent.lower() or "vague" in facts.intent.lower() or "unknown" in facts.intent.lower()
    
    if intent_is_vague or has_missing_info:
        # Request is unclear or has missing info → FOLLOW_UP to clarify
        reasoning = (
            f"Request intent '{facts.intent}' is unclear or incomplete. "
            f"Need to gather more information to determine applicable policy."
        )
        outcome = "FOLLOW_UP"
    elif policies:
        # We retrieved policies but no rule matched
        # This suggests the request is related but not directly covered
        reasoning = (
            f"Request intent '{facts.intent}' is not covered by standard policies. "
            f"Retrieved {len(policies)} related policy document(s), but no deterministic "
            f"rule applies. Human review required."
        )
        outcome = "ESCALATE"
    else:
        # No policies retrieved AND request seems clear
        # → likely unsupported → ESCALATE
        reasoning = (
            f"Request intent '{facts.intent}' does not match any known policy. "
            f"No applicable policy found. Human review required."
        )
        outcome = "ESCALATE"
    
    # Check ticket history for any precedent
    if tickets:
        reasoning += (
            f" Note: Found {len(tickets)} historical ticket(s) for context, "
            f"but they cannot override the lack of formal policy."
        )
    
    # Calculate low confidence since no rule matched
    confidence = 0.3
    
    return AgentDecision(
        decision=outcome,
        intent=facts.intent,
        confidence=confidence,
        extracted_facts=facts,
        relevant_policies=policies,
        relevant_tickets=tickets,
        missing_information=facts.missing_information,
        reason=reasoning,
        actions=[
            "Gather more information about the request" if outcome == "FOLLOW_UP" else "Escalate to human IT support agent",
            "Check if new policy documentation is available",
        ],
        sources=[p.policy_id for p in policies] if policies else [],
    )
