"""
Tests for Ticket Search

Tests ticket search functionality including:
- Search by intent keywords
- Search by entity matches
- Active vs closed ticket context
- Edge cases
"""

import pytest
import json
from pathlib import Path

from app.agent.ticket_search import search_tickets, load_tickets
from app.agent.schemas import ExtractedFacts, TicketContext


@pytest.fixture
def sample_tickets_file(tmp_path):
    """Create a temporary tickets file for testing."""
    tickets = [
        {
            "ticket_id": "TK-1001",
            "title": "Password Reset Request",
            "description": "User cannot access their account",
            "requester_id": "alice_wonder",
            "status": "Resolved (closed)",
            "created_at": "2023-10-01 09:00:00",
            "resolved_at": "2023-10-05 10:00:00"
        },
        {
            "ticket_id": "TK-1002",
            "title": "Laptop Hardware Issue",
            "description": "Laptop screen flickering",
            "requester_id": "bob_thompson",
            "asset_id": "ASSET-001",
            "status": "Escalated to IT (active)",
            "created_at": "2023-10-02 14:00:00"
        },
        {
            "ticket_id": "TK-1003",
            "title": "Software Installation - Slack",
            "description": "Request to install Slack on work computer",
            "requester_id": "alice_wonder",
            "software_name": "Slack",
            "status": "Approved and installed (closed)",
            "created_at": "2023-10-03 11:00:00",
            "resolved_at": "2023-10-06 15:00:00"
        },
        {
            "ticket_id": "TK-1004",
            "title": "Password Reset",
            "description": "Forgot password again",
            "requester_id": "charlie_brown",
            "status": "Resolved (closed)",
            "created_at": "2023-10-04 08:00:00",
            "resolved_at": "2023-10-04 09:00:00"
        }
    ]
    
    tickets_file = tmp_path / "tickets.json"
    tickets_file.write_text(json.dumps(tickets, indent=2))
    return tickets_file


class TestTicketSearch:
    """Test ticket search functionality."""
    
    def test_search_by_intent_keywords(self, sample_tickets_file):
        """Test searching by intent keywords."""
        facts = ExtractedFacts(
            intent="password reset",
            entities={},
            missing_information=[]
        )
        
        results = search_tickets(facts, sample_tickets_file)
        
        # Should find password-related tickets
        assert len(results) >= 1
        ticket_ids = [t.ticket_id for t in results]
        assert any(tid in ["TK-1001", "TK-1004"] for tid in ticket_ids)
    
    def test_search_by_employee_entity(self, sample_tickets_file):
        """Test searching by employee entity."""
        facts = ExtractedFacts(
            intent="help",
            entities={"employee": "alice_wonder"},
            missing_information=[]
        )
        
        results = search_tickets(facts, sample_tickets_file)
        
        # Should find tickets for alice_wonder
        assert len(results) >= 1
        # Check that alice's tickets are in results
        alice_tickets = [t for t in results if t.employee == "alice_wonder"]
        assert len(alice_tickets) >= 1
    
    def test_search_by_asset_entity(self, sample_tickets_file):
        """Test searching by asset_id entity."""
        facts = ExtractedFacts(
            intent="hardware issue",
            entities={"asset_id": "ASSET-001"},
            missing_information=[]
        )
        
        results = search_tickets(facts, sample_tickets_file)
        
        # Should find ticket with matching asset_id
        assert len(results) >= 1
        assert "TK-1002" in [t.ticket_id for t in results]
    
    def test_search_by_software_entity(self, sample_tickets_file):
        """Test searching by software entity."""
        facts = ExtractedFacts(
            intent="install software",
            entities={"software": "Slack"},
            missing_information=[]
        )
        
        results = search_tickets(facts, sample_tickets_file)
        
        # Should find Slack installation ticket
        assert len(results) >= 1
        assert "TK-1003" in [t.ticket_id for t in results]
    
    def test_closed_ticket_context(self, sample_tickets_file):
        """Test that closed tickets are properly identified."""
        facts = ExtractedFacts(
            intent="password reset",
            entities={"employee": "alice_wonder"},  # Match alice to get her closed ticket
            missing_information=[]
        )
        
        results = search_tickets(facts, sample_tickets_file)
        
        # Should have tickets
        assert len(results) >= 1
        
        # Check if any are closed
        closed_tickets = [t for t in results if not t.is_active]
        
        # Verify that TK-1001 (alice's closed password reset) is marked as closed
        tk1001 = next((t for t in results if t.ticket_id == "TK-1001"), None)
        if tk1001:
            assert not tk1001.is_active, "TK-1001 should be closed"
            assert "closed" in tk1001.status.lower()
    
    def test_active_ticket_context(self, sample_tickets_file):
        """Test that active tickets are properly identified."""
        facts = ExtractedFacts(
            intent="hardware issue",
            entities={},
            missing_information=[]
        )
        
        results = search_tickets(facts, sample_tickets_file)
        
        # Should have active tickets
        active_tickets = [t for t in results if t.is_active]
        assert len(active_tickets) >= 1
        
        # Verify active ticket status
        for ticket in active_tickets:
            assert "closed" not in ticket.status.lower() or "escalated" in ticket.status.lower()
    
    def test_no_matching_tickets(self, sample_tickets_file):
        """Test when no tickets match the search."""
        facts = ExtractedFacts(
            intent="completely unrelated topic",
            entities={},
            missing_information=[]
        )
        
        results = search_tickets(facts, sample_tickets_file)
        
        # Should return empty list (no matches)
        assert len(results) == 0
    
    def test_max_five_results(self, tmp_path):
        """Test that only top 5 results are returned."""
        # Create many matching tickets
        tickets = []
        for i in range(10):
            tickets.append({
                "ticket_id": f"TK-100{i}",
                "title": "Password Reset",
                "description": "Password reset request",
                "requester_id": "test_user",
                "status": "Resolved (closed)",
                "created_at": f"2023-10-{i+1:02d} 10:00:00",
                "resolved_at": f"2023-10-{i+1:02d} 11:00:00"
            })
        
        tickets_file = tmp_path / "many_tickets.json"
        tickets_file.write_text(json.dumps(tickets, indent=2))
        
        facts = ExtractedFacts(
            intent="password reset",
            entities={},
            missing_information=[]
        )
        
        results = search_tickets(facts, tickets_file)
        
        # Should return max 5 results
        assert len(results) <= 5
    
    def test_empty_facts(self, sample_tickets_file):
        """Test with minimal facts."""
        facts = ExtractedFacts(
            intent="help",
            entities={},
            missing_information=[]
        )
        
        results = search_tickets(facts, sample_tickets_file)
        
        # May or may not match depending on "help" keyword
        assert isinstance(results, list)


class TestLoadTickets:
    """Test ticket loading functionality."""
    
    def test_load_default_tickets(self):
        """Test loading from default location."""
        # This will use the actual data/tickets.json file
        tickets = load_tickets()
        
        # Should load the 10 tickets from data pack
        assert isinstance(tickets, list)
        assert len(tickets) == 10
    
    def test_load_custom_tickets(self, tmp_path):
        """Test loading from custom path."""
        custom_tickets = [
            {
                "ticket_id": "TK-CUSTOM",
                "title": "Test Ticket",
                "description": "Custom test ticket",
                "requester_id": "test_user",
                "status": "Open"
            }
        ]
        
        tickets_file = tmp_path / "custom.json"
        tickets_file.write_text(json.dumps(custom_tickets, indent=2))
        
        tickets = load_tickets(tickets_file)
        
        assert len(tickets) == 1
        assert tickets[0]["ticket_id"] == "TK-CUSTOM"


class TestTicketContextCreation:
    """Test TicketContext object creation from search results."""
    
    def test_ticket_context_fields(self, sample_tickets_file):
        """Test that TicketContext is properly created."""
        facts = ExtractedFacts(
            intent="password reset",
            entities={},
            missing_information=[]
        )
        
        results = search_tickets(facts, sample_tickets_file)
        
        assert len(results) >= 1
        ticket = results[0]
        
        # Verify TicketContext structure
        assert isinstance(ticket, TicketContext)
        assert isinstance(ticket.ticket_id, str)
        assert isinstance(ticket.employee, str)
        assert isinstance(ticket.issue_summary, str)
        assert isinstance(ticket.status, str)
        assert isinstance(ticket.is_active, bool)
