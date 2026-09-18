"""
Phase 6 Orchestrator Tests

Tests for the thin orchestration layer connecting all agent components.
Uses mocks for LLM/RAG calls - NO real API keys required.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from app.agent.orchestrator import AgentOrchestrator, run_agent
from app.agent.schemas import ExtractedFacts, PolicyEvidence, TicketContext, AgentDecision, AgentResponse


@pytest.fixture
def mock_rag_retriever():
    """Mock RAG retriever."""
    retriever = Mock()
    retriever.retrieve_policies = Mock(return_value=[])
    return retriever


class TestOrchestratorComponents:
    """Test that orchestrator correctly connects all components."""
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    @patch('app.agent.orchestrator.generate_response')
    def test_orchestrator_calls_all_components(
        self,
        mock_generate,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever
    ):
        """Test that orchestrator calls all 5 components in order."""
        # Setup mocks
        facts = ExtractedFacts(
            intent="password_reset",
            entities={"employee": "bob_thompson"},
            missing_information=[]
        )
        mock_understand.return_value = facts
        
        mock_rag_retriever.retrieve_policies.return_value = []
        mock_search.return_value = []
        
        decision = AgentDecision(
            decision="RESOLVE",
            intent="password_reset",
            confidence=0.90,
            extracted_facts=facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Can reset via self-service",
            actions=["Use self-service portal"],
            sources=["KB-01"]
        )
        mock_evaluate.return_value = decision
        
        response = AgentResponse(
            decision="RESOLVE",
            message="I can help you reset your password.",
            sources=["KB-01"],
            follow_up_questions=[]
        )
        mock_generate.return_value = response
        
        # Execute orchestrator
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        result = orchestrator.run_agent("I need to reset my password")
        
        # Verify all components called
        mock_understand.assert_called_once()
        mock_rag_retriever.retrieve_policies.assert_called_once()
        mock_search.assert_called_once()
        mock_evaluate.assert_called_once()
        mock_generate.assert_called_once()
        
        # Verify response
        assert result.decision == "RESOLVE"
        assert "password" in result.message.lower()
    
    @patch('app.agent.orchestrator.understand_request')
    def test_orchestrator_handles_understand_failure(self, mock_understand, mock_rag_retriever):
        """Test that orchestrator handles LLM understanding failures."""
        mock_understand.side_effect = Exception("LLM API error")
        
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        with pytest.raises(ValueError, match="Failed to understand request"):
            orchestrator.run_agent("Some request")
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    @patch('app.agent.orchestrator.generate_response')
    def test_orchestrator_continues_when_rag_fails(
        self,
        mock_generate,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever
    ):
        """Test that orchestrator continues when RAG fails (graceful degradation)."""
        facts = ExtractedFacts(
            intent="laptop_issue",
            entities={},
            missing_information=[]
        )
        mock_understand.return_value = facts
        
        # RAG fails
        mock_rag_retriever.retrieve_policies.side_effect = Exception("ChromaDB error")
        
        mock_search.return_value = []
        
        decision = AgentDecision(
            decision="ESCALATE",
            intent="laptop_issue",
            confidence=0.50,
            extracted_facts=facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="No policy found",
            actions=["Escalate to IT"],
            sources=[]
        )
        mock_evaluate.return_value = decision
        
        response = AgentResponse(
            decision="ESCALATE",
            message="This will be escalated to IT support.",
            sources=[],
            follow_up_questions=[]
        )
        mock_generate.return_value = response
        
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        # Should NOT raise - workflow continues
        result = orchestrator.run_agent("My laptop is broken")
        
        assert result.decision == "ESCALATE"
        # Decision engine was called with empty policies list
        mock_evaluate.assert_called_once()
        call_args = mock_evaluate.call_args[0]
        assert call_args[1] == []  # policies list is empty


class TestResponseGeneration:
    """Test response generation with decision preservation."""
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    @patch('app.agent.response_generator.genai')
    def test_decision_preserved_in_response(
        self,
        mock_genai,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever
    ):
        """CRITICAL: Test that decision from engine is preserved in final response."""
        facts = ExtractedFacts(
            intent="software_install",
            entities={"software": "Slack"},
            missing_information=[]
        )
        mock_understand.return_value = facts
        
        mock_rag_retriever.retrieve_policies.return_value = []
        mock_search.return_value = []
        
        # Decision engine says ESCALATE
        decision = AgentDecision(
            decision="ESCALATE",
            intent="software_install",
            confidence=0.85,
            extracted_facts=facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Software approval requires manager review",
            actions=["Submit for approval"],
            sources=["KB-03"]
        )
        mock_evaluate.return_value = decision
        
        # Mock Gemini response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Your software request will be reviewed by management."
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        result = orchestrator.run_agent("Can I install Slack?")
        
        # Decision MUST be preserved as ESCALATE
        assert result.decision == "ESCALATE", "Decision was not preserved from engine to response"
        assert result.sources == ["KB-03"]


class TestTicketSearch:
    """Test ticket search functionality."""
    
    def test_ticket_search_with_real_data(self):
        """Test ticket search with actual tickets.json data."""
        from app.agent.ticket_search import search_tickets
        
        facts = ExtractedFacts(
            intent="password reset",
            entities={"employee": "alice_wonder"},
            missing_information=[]
        )
        
        # Search using real data/tickets.json
        tickets = search_tickets(facts)
        
        # Should return TicketContext objects
        assert isinstance(tickets, list)
        for ticket in tickets:
            assert isinstance(ticket, TicketContext)
            assert hasattr(ticket, 'ticket_id')
            assert hasattr(ticket, 'is_active')


class TestConvenienceFunction:
    """Test the run_agent convenience function."""
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    @patch('app.agent.orchestrator.generate_response')
    def test_run_agent_convenience_function(
        self,
        mock_generate,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever
    ):
        """Test convenience function creates orchestrator and runs workflow."""
        facts = ExtractedFacts(
            intent="vpn_access",
            entities={},
            missing_information=[]
        )
        mock_understand.return_value = facts
        mock_rag_retriever.retrieve_policies.return_value = []
        mock_search.return_value = []
        
        decision = AgentDecision(
            decision="RESOLVE",
            intent="vpn_access",
            confidence=0.92,
            extracted_facts=facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="VPN available via KB-02",
            actions=["Download VPN client"],
            sources=["KB-02"]
        )
        mock_evaluate.return_value = decision
        
        response = AgentResponse(
            decision="RESOLVE",
            message="You can access VPN by downloading the client.",
            sources=["KB-02"],
            follow_up_questions=[]
        )
        mock_generate.return_value = response
        
        result = run_agent(
            user_request="How do I get VPN?",
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        assert result.decision == "RESOLVE"
        assert result.sources == ["KB-02"]
