"""
Ticket Search Module

Searches existing tickets from data/tickets.json based on intent and entities.
Provides context to the decision engine but never overrides policy decisions.
"""

import json
from pathlib import Path
from typing import List, Optional
from app.agent.schemas import ExtractedFacts, TicketContext


def load_tickets(tickets_path: Optional[Path] = None) -> List[dict]:
    """Load tickets from JSON file."""
    if tickets_path is None:
        tickets_path = Path(__file__).parents[2] / "data" / "tickets.json"
    
    with open(tickets_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def search_tickets(facts: ExtractedFacts, tickets_path: Optional[Path] = None) -> List[TicketContext]:
    """
    Search for relevant tickets based on extracted facts.
    
    Returns tickets that match:
    - Similar intent keywords
    - Related entities (asset, software, etc.)
    
    Args:
        facts: ExtractedFacts containing user request information
        tickets_path: Optional path to tickets.json (for testing)
    
    Returns:
        List of TicketContext objects, most recent first
    """
    tickets = load_tickets(tickets_path)
    relevant_tickets = []
    
    # Extract search terms from facts
    intent_lower = facts.intent.lower() if facts.intent else ""
    entities = facts.entities
    
    # Keywords for matching
    intent_keywords = set(intent_lower.split())
    
    for ticket in tickets:
        relevance_score = 0
        
        # Match by intent keywords in description or title
        description_lower = ticket.get("description", "").lower()
        title_lower = ticket.get("title", "").lower()
        
        for keyword in intent_keywords:
            if keyword in description_lower or keyword in title_lower:
                relevance_score += 2
        
        # Match by entities
        # Check if ticket has matching employee ID
        if "employee" in entities and ticket.get("requester_id") == entities.get("employee"):
            relevance_score += 10
        
        # Check for asset_id match
        if "asset_id" in entities and ticket.get("asset_id") == entities.get("asset_id"):
            relevance_score += 5
        
        # Check for software match
        if "software" in entities:
            software_lower = str(entities["software"]).lower()
            if software_lower in description_lower or software_lower in title_lower:
                relevance_score += 3
        
        # If any relevance, add to results
        if relevance_score > 0:
            # Convert ticket dict to Ticket-like object for from_ticket
            from app.database.models import Ticket
            ticket_obj = Ticket(
                ticket_id=ticket["ticket_id"],
                employee=ticket["requester_id"],
                issue_summary=ticket.get("description", ticket.get("title", "")),
                status=ticket["status"],
                created_at=ticket.get("created_at", ""),
                resolved_at=ticket.get("resolved_at")
            )
            ticket_context = TicketContext.from_ticket(ticket_obj)
            relevant_tickets.append((relevance_score, ticket_context))
    
    # Sort by relevance score (descending), then by ticket_id (descending for recency)
    relevant_tickets.sort(key=lambda x: (x[0], x[1].ticket_id), reverse=True)
    
    # Return top 5 most relevant tickets
    return [tc for score, tc in relevant_tickets[:5]]
