"""
Tests for Agent Orchestrator

Comprehensive tests covering:
- Happy path workflows
- Component failures and fallbacks
- Decision preservation
- Error handling
- Edge cases
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


@pytest.fixture
def sample_facts():
    """Sample extracted facts."""
    return ExtractedFacts(
        intent="password_reset",
        entities={"employee": "bob_thompson"},
        missing_information=[]
    )


@pytest.fixture
def sample_decision(sample_facts):
    """Sample agent decision."""
    return AgentDecision(
        decision="RESOLVE",
        intent="password_reset",
        confidence=0.90,
        extracted_facts=sample_facts,
        relevant_policies=[],
        relevant_tickets=[],
        missing_information=[],
        reason="Password reset available via KB-01",
        actions=["Use self-service portal"],
        sources=["KB-01"]
    )


@pytest.fixture
def sample_response():
    """Sample agent response."""
    return AgentResponse(
        decision="RESOLVE",
        message="I can help you reset your password via the self-service portal.",
        sources=["KB-01"],
        follow_up_questions=[]
    )


class TestOrchestratorHappyPath:
    """Test successful end-to-end workflows."""
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    @patch('app.agent.orchestrator.generate_response')
    def test_full_workflow_resolve(
        self,
        mock_generate,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever,
        sample_facts,
        sample_decision,
        sample_response
    ):
        """Test complete workflow resulting in RESOLVE."""
        # Setup mocks
        mock_understand.return_value = sample_facts
        mock_rag_retriever.retrieve_policies.return_value = []
        mock_search.return_value = []
        mock_evaluate.return_value = sample_decision
        mock_generate.return_value = sample_response
        
        # Execute
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        response = orchestrator.run_agent("I need to reset my password")
        
        # Verify all components called
        mock_understand.assert_called_once()
        mock_rag_retriever.retrieve_policies.assert_called_once()
        mock_search.assert_called_once()
        mock_evaluate.assert_called_once()
        mock_generate.assert_called_once()
        
        # Verify response
        assert response.decision == "RESOLVE"
        assert response.sources == ["KB-01"]
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    @patch('app.agent.orchestrator.generate_response')
    def test_full_workflow_escalate(
        self,
        mock_generate,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever
    ):
        """Test complete workflow resulting in ESCALATE."""
        # Setup mocks
        facts = ExtractedFacts(
            intent="hardware_failure",
            entities={"device": "laptop", "asset_id": "ASSET-001"},
            missing_information=[]
        )
        mock_understand.return_value = facts
        mock_rag_retriever.retrieve_policies.return_value = []
        mock_search.return_value = []
        
        decision = AgentDecision(
            decision="ESCALATE",
            intent="hardware_failure",
            confidence=0.85,
            extracted_facts=facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Hardware failure requires IT technician",
            actions=["Escalate to IT"],
            sources=["KB-05"]
        )
        mock_evaluate.return_value = decision
        
        response = AgentResponse(
            decision="ESCALATE",
            message="A technician will contact you shortly.",
            sources=["KB-05"],
            follow_up_questions=[]
        )
        mock_generate.return_value = response
        
        # Execute
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        result = orchestrator.run_agent("My laptop won't boot")
        
        # Verify ESCALATE decision preserved
        assert result.decision == "ESCALATE"
        assert result.sources == ["KB-05"]
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    @patch('app.agent.orchestrator.generate_response')
    def test_full_workflow_follow_up(
        self,
        mock_generate,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever
    ):
        """Test complete workflow resulting in FOLLOW_UP."""
        # Setup mocks
        facts = ExtractedFacts(
            intent="unclear_request",
            entities={},
            missing_information=["device_type", "issue_description"]
        )
        mock_understand.return_value = facts
        mock_rag_retriever.retrieve_policies.return_value = []
        mock_search.return_value = []
        
        decision = AgentDecision(
            decision="FOLLOW_UP",
            intent="unclear_request",
            confidence=0.50,
            extracted_facts=facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=["device_type", "issue_description"],
            reason="Need more information to determine policy",
            actions=["Ask for device type and issue details"],
            sources=[]
        )
        mock_evaluate.return_value = decision
        
        response = AgentResponse(
            decision="FOLLOW_UP",
            message="Could you provide more details about your device and the issue?",
            sources=[],
            follow_up_questions=["device_type", "issue_description"]
        )
        mock_generate.return_value = response
        
        # Execute
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        result = orchestrator.run_agent("Help")
        
        # Verify FOLLOW_UP decision preserved
        assert result.decision == "FOLLOW_UP"
        assert len(result.follow_up_questions) == 2


class TestOrchestratorErrorHandling:
    """Test error handling and fallbacks."""
    
    @patch('app.agent.orchestrator.understand_request')
    def test_understand_request_failure(self, mock_understand, mock_rag_retriever):
        """Test handling when request understanding fails."""
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
    def test_rag_retrieval_failure_graceful(
        self,
        mock_generate,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever,
        sample_facts,
        sample_decision,
        sample_response
    ):
        """Test that RAG failure doesn't stop workflow."""
        # RAG fails
        mock_rag_retriever.retrieve_policies.side_effect = Exception("ChromaDB error")
        
        # Other components succeed
        mock_understand.return_value = sample_facts
        mock_search.return_value = []
        mock_evaluate.return_value = sample_decision
        mock_generate.return_value = sample_response
        
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        # Should NOT raise - workflow continues with empty policies
        response = orchestrator.run_agent("Some request")
        
        assert response.decision == "RESOLVE"
        # Decision engine was called with empty policies list
        mock_evaluate.assert_called_once()
        call_args = mock_evaluate.call_args[0]
        assert call_args[1] == []  # policies list is empty
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    @patch('app.agent.orchestrator.generate_response')
    def test_ticket_search_failure_graceful(
        self,
        mock_generate,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever,
        sample_facts,
        sample_decision,
        sample_response
    ):
        """Test that ticket search failure doesn't stop workflow."""
        # Ticket search fails
        mock_search.side_effect = Exception("Database error")
        
        # Other components succeed
        mock_understand.return_value = sample_facts
        mock_rag_retriever.retrieve_policies.return_value = []
        mock_evaluate.return_value = sample_decision
        mock_generate.return_value = sample_response
        
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        # Should NOT raise - workflow continues with empty tickets
        response = orchestrator.run_agent("Some request")
        
        assert response.decision == "RESOLVE"
        # Decision engine was called with empty tickets list
        mock_evaluate.assert_called_once()
        call_args = mock_evaluate.call_args[0]
        assert call_args[2] == []  # tickets list is empty
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    def test_decision_engine_failure(
        self,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever,
        sample_facts
    ):
        """Test handling when decision engine fails."""
        mock_understand.return_value = sample_facts
        mock_rag_retriever.retrieve_policies.return_value = []
        mock_search.return_value = []
        mock_evaluate.side_effect = Exception("Rule evaluation error")
        
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        with pytest.raises(ValueError, match="Decision evaluation failed"):
            orchestrator.run_agent("Some request")


class TestOrchestratorDecisionPreservation:
    """Critical tests: verify orchestrator preserves decisions."""
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    @patch('app.agent.orchestrator.generate_response')
    def test_decision_preserved_through_workflow(
        self,
        mock_generate,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever,
        sample_facts
    ):
        """Test that decision from engine is preserved in final response."""
        mock_understand.return_value = sample_facts
        mock_rag_retriever.retrieve_policies.return_value = []
        mock_search.return_value = []
        
        # Decision engine says ESCALATE
        engine_decision = AgentDecision(
            decision="ESCALATE",
            intent="complex_issue",
            confidence=0.80,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Requires expert review",
            actions=["Escalate to senior IT"],
            sources=[]
        )
        mock_evaluate.return_value = engine_decision
        
        # Response generator preserves ESCALATE
        final_response = AgentResponse(
            decision="ESCALATE",
            message="This will be escalated.",
            sources=[],
            follow_up_questions=[]
        )
        mock_generate.return_value = final_response
        
        orchestrator = AgentOrchestrator(
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        result = orchestrator.run_agent("Complex issue")
        
        # Verify decision preserved
        assert result.decision == "ESCALATE"


class TestConvenienceFunction:
    """Test run_agent convenience function."""
    
    @patch('app.agent.orchestrator.understand_request')
    @patch('app.agent.orchestrator.search_tickets')
    @patch('app.agent.orchestrator.evaluate_decision')
    @patch('app.agent.orchestrator.generate_response')
    def test_run_agent_function(
        self,
        mock_generate,
        mock_evaluate,
        mock_search,
        mock_understand,
        mock_rag_retriever,
        sample_facts,
        sample_decision,
        sample_response
    ):
        """Test convenience function creates orchestrator and runs workflow."""
        mock_understand.return_value = sample_facts
        mock_rag_retriever.retrieve_policies.return_value = []
        mock_search.return_value = []
        mock_evaluate.return_value = sample_decision
        mock_generate.return_value = sample_response
        
        response = run_agent(
            user_request="Test request",
            gemini_api_key="fake-key",
            rag_retriever=mock_rag_retriever
        )
        
        assert response.decision == "RESOLVE"
        assert response.sources == ["KB-01"]
