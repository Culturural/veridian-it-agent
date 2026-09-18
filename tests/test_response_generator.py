"""
Tests for Response Generator

Critical tests verifying that Gemini CANNOT change the decision value.
The LLM only generates message text - the decision is preserved.
"""

import pytest
from unittest.mock import Mock, patch

from app.agent.response_generator import generate_response, _generate_fallback_message
from app.agent.schemas import AgentDecision, AgentResponse, ExtractedFacts


@pytest.fixture
def sample_facts():
    """Sample extracted facts."""
    return ExtractedFacts(
        intent="password_reset",
        entities={"employee": "bob_thompson"},
        missing_information=[]
    )


class TestResponseGenerator:
    """Test response generation with decision preservation."""
    
    @patch('app.agent.response_generator.genai')
    def test_generate_response_resolve_decision(self, mock_genai, sample_facts):
        """Test that RESOLVE decision is preserved."""
        decision = AgentDecision(
            decision="RESOLVE",
            intent="password_reset",
            confidence=0.95,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Password can be reset via self-service portal (KB-01)",
            actions=["Use self-service portal"],
            sources=["KB-01"]
        )
        
        # Mock Gemini response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "I can help you reset your password. Please visit the self-service portal."
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        response = generate_response(decision, "fake-api-key")
        
        # Decision MUST be preserved
        assert response.decision == "RESOLVE"
        assert response.sources == ["KB-01"]
        assert "password" in response.message.lower()
    
    @patch('app.agent.response_generator.genai')
    def test_generate_response_escalate_decision(self, mock_genai, sample_facts):
        """Test that ESCALATE decision is preserved."""
        decision = AgentDecision(
            decision="ESCALATE",
            intent="hardware_failure",
            confidence=0.88,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Hardware failure requires IT technician (KB-05)",
            actions=["Escalate to IT"],
            sources=["KB-05"]
        )
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "This issue requires assistance from our IT team. A technician will contact you."
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        response = generate_response(decision, "fake-api-key")
        
        # Decision MUST be preserved
        assert response.decision == "ESCALATE"
        assert response.sources == ["KB-05"]
    
    @patch('app.agent.response_generator.genai')
    def test_llm_cannot_override_decision(self, mock_genai, sample_facts):
        """
        CRITICAL TEST: Verify LLM cannot change decision.
        
        Even if the LLM response suggests a different decision,
        the original decision MUST be preserved.
        """
        decision = AgentDecision(
            decision="ESCALATE",
            intent="complex_issue",
            confidence=0.85,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Complex issue requires expert review",
            actions=["Escalate to senior IT"],
            sources=[]
        )
        
        # LLM tries to suggest RESOLVE (this should be ignored)
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "Actually, I can resolve this for you right away! RESOLVE"
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        response = generate_response(decision, "fake-api-key")
        
        # Original ESCALATE decision MUST be preserved
        assert response.decision == "ESCALATE", "LLM changed the decision - CRITICAL FAILURE"
    
    @patch('app.agent.response_generator.genai')
    def test_fallback_when_llm_fails(self, mock_genai, sample_facts):
        """Test fallback message generation when LLM fails."""
        decision = AgentDecision(
            decision="RESOLVE",
            intent="vpn_access",
            confidence=0.90,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Can be handled via self-service",
            actions=["Download VPN client"],
            sources=["KB-02"]
        )
        
        # LLM raises exception
        mock_client = Mock()
        mock_client.models.generate_content.side_effect = Exception("API error")
        mock_genai.Client.return_value = mock_client
        
        response = generate_response(decision, "fake-api-key")
        
        # Decision MUST still be preserved
        assert response.decision == "RESOLVE"
        assert response.sources == ["KB-02"]
        # Fallback message should still communicate the decision
        assert "resolve" in response.message.lower() or "handled" in response.message.lower()
    
    @patch('app.agent.response_generator.genai')
    def test_fallback_when_llm_returns_empty(self, mock_genai, sample_facts):
        """Test fallback when LLM returns empty response."""
        decision = AgentDecision(
            decision="ESCALATE",
            intent="unclear_request",
            confidence=0.80,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=["device_type"],
            reason="Needs human review",
            actions=["Escalate to IT"],
            sources=[]
        )
        
        # LLM returns empty string
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = ""
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        response = generate_response(decision, "fake-api-key")
        
        # Decision preserved, fallback message used
        assert response.decision == "ESCALATE"
        assert "escalate" in response.message.lower() or "escalation" in response.message.lower()
    
    def test_fallback_message_resolve(self, sample_facts):
        """Test fallback message generation for RESOLVE."""
        decision = AgentDecision(
            decision="RESOLVE",
            intent="password_reset",
            confidence=0.90,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Self-service available",
            actions=["Use portal"],
            sources=["KB-01"]
        )
        
        message = _generate_fallback_message(decision)
        
        assert "resolve" in message.lower()
        assert "Self-service available" in message
    
    def test_fallback_message_escalate(self, sample_facts):
        """Test fallback message generation for ESCALATE."""
        decision = AgentDecision(
            decision="ESCALATE",
            intent="hardware_issue",
            confidence=0.85,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="IT support required",
            actions=["Create ticket"],
            sources=[]
        )
        
        message = _generate_fallback_message(decision)
        
        assert "escalate" in message.lower() or "escalation" in message.lower()
        assert "IT support required" in message
    
    def test_fallback_message_follow_up(self, sample_facts):
        """Test fallback message generation for FOLLOW_UP."""
        decision = AgentDecision(
            decision="FOLLOW_UP",
            intent="unclear_request",
            confidence=0.60,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=["device_type", "issue_description"],
            reason="Need more information",
            actions=["Ask for details"],
            sources=[]
        )
        
        message = _generate_fallback_message(decision)
        
        assert "information" in message.lower() or "follow" in message.lower()
        assert "Need more information" in message
    
    @patch('app.agent.response_generator.genai')
    def test_response_schema_valid(self, mock_genai, sample_facts):
        """Test that generated response matches AgentResponse schema."""
        decision = AgentDecision(
            decision="RESOLVE",
            intent="vpn_access",
            confidence=0.88,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Standard procedure",
            actions=["Download client"],
            sources=["KB-02"]
        )
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "I can help you with this request."
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client
        
        response = generate_response(decision, "fake-api-key")
        
        # Should be valid AgentResponse
        assert isinstance(response, AgentResponse)
        assert isinstance(response.decision, str)
        assert isinstance(response.message, str)
        assert isinstance(response.sources, list)
        assert isinstance(response.follow_up_questions, list)
    
    def test_missing_api_key_uses_fallback(self, sample_facts):
        """Test that missing API key uses fallback response (graceful degradation)."""
        decision = AgentDecision(
            decision="RESOLVE",
            intent="test",
            confidence=0.90,
            extracted_facts=sample_facts,
            relevant_policies=[],
            relevant_tickets=[],
            missing_information=[],
            reason="Test",
            actions=[],
            sources=[]
        )
        
        # Should not raise - should return fallback response
        response = generate_response(decision, api_key=None)
        
        assert response.decision == "RESOLVE"
        assert "resolved" in response.message.lower() or "resolve" in response.message.lower()
        assert response.sources == []
