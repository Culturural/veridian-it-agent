"""
Tests for LLM request understanding layer.

Tests use mocked Gemini API to avoid external dependencies
and API quota consumption.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.agent.request_understanding import understand_request
from app.agent.schemas import ExtractedFacts


# ============================================================================
# SUCCESSFUL EXTRACTION TESTS
# ============================================================================

def test_successful_extraction():
    """Test successful extraction with valid Gemini response."""
    with patch('google.genai.Client') as mock_client:
        # Mock Gemini response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "vpn_access",
            "entities": {"issue": "VPN credentials expired"},
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        # Test
        result = understand_request(
            "My VPN stopped working",
            api_key="test-key"
        )
        
        assert isinstance(result, ExtractedFacts)
        assert result.intent == "vpn_access"
        assert result.entities["issue"] == "VPN credentials expired"
        assert result.missing_information == []


def test_structured_pydantic_result():
    """Test that result is a properly validated Pydantic model."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "laptop_issue",
            "entities": {
                "device": "laptop",
                "age_years": 3.5,
                "issue": "won't turn on"
            },
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "My laptop won't turn on, had it 3.5 years",
            api_key="test-key"
        )
        
        # Verify it's a Pydantic model
        assert isinstance(result, ExtractedFacts)
        
        # Verify all fields
        assert result.intent == "laptop_issue"
        assert result.entities["device"] == "laptop"
        assert result.entities["age_years"] == 3.5
        assert result.entities["issue"] == "won't turn on"
        assert result.missing_information == []


# ============================================================================
# INPUT VALIDATION TESTS
# ============================================================================

def test_empty_input_rejected():
    """Test that empty input is rejected."""
    with pytest.raises(ValueError, match="Request text must be non-empty"):
        understand_request("", api_key="test-key")
    
    with pytest.raises(ValueError, match="Request text must be non-empty"):
        understand_request("   ", api_key="test-key")


def test_missing_api_key():
    """Test that missing API key is detected."""
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            understand_request("test request")


# ============================================================================
# API FAILURE HANDLING TESTS
# ============================================================================

def test_api_failure_handling():
    """Test handling of Gemini API failures."""
    with patch('google.genai.Client') as mock_client:
        mock_instance = MagicMock()
        mock_instance.models.generate_content.side_effect = Exception("API error")
        mock_client.return_value = mock_instance
        
        with pytest.raises(RuntimeError, match="Gemini API call failed"):
            understand_request("test request", api_key="test-key")


def test_empty_response_handling():
    """Test handling of empty Gemini response."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = None
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        with pytest.raises(RuntimeError, match="empty response"):
            understand_request("test request", api_key="test-key")


def test_invalid_json_response():
    """Test handling of invalid JSON from Gemini."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = "not valid json{"
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        with pytest.raises(RuntimeError, match="Failed to parse.*JSON"):
            understand_request("test request", api_key="test-key")


# ============================================================================
# AMBIGUOUS REQUEST HANDLING
# ============================================================================

def test_ambiguous_request_handling():
    """Test extraction from vague/ambiguous request."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "unknown",
            "entities": {},
            "missing_information": [
                "device or system affected",
                "description of the problem"
            ]
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "hey can you help, its not working",
            api_key="test-key"
        )
        
        assert result.intent == "unknown"
        assert result.entities == {}
        assert len(result.missing_information) > 0
        assert any("device" in info.lower() or "system" in info.lower() 
                   for info in result.missing_information)


# ============================================================================
# ENTITY EXTRACTION TESTS
# ============================================================================

def test_numeric_entity_extraction():
    """Test extraction of important numeric values."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "home_office_equipment",
            "entities": {
                "work_from_home_days_per_week": 4,
                "requested_equipment": "monitor"
            },
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "I work from home 4 days a week, need a monitor",
            api_key="test-key"
        )
        
        assert result.intent == "home_office_equipment"
        assert result.entities["work_from_home_days_per_week"] == 4
        assert result.entities["requested_equipment"] == "monitor"


def test_issue_description_extraction():
    """Test extraction of issue descriptions."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "vpn_access",
            "entities": {
                "issue": "VPN credentials expired",
                "timeframe": "this morning"
            },
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "My VPN stopped working this morning, says credentials expired",
            api_key="test-key"
        )
        
        assert result.intent == "vpn_access"
        assert "expired" in result.entities["issue"].lower()


# ============================================================================
# POLICY DECISION LEAKAGE TESTS
# ============================================================================

def test_no_policy_decision_in_intent():
    """Test that intent doesn't contain policy decisions."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "home_office_equipment",  # Not "monitor_approved"
            "entities": {
                "work_from_home_days_per_week": 4,
                "requested_equipment": "monitor"
            },
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "I work from home 4 days a week, how do I get a monitor?",
            api_key="test-key"
        )
        
        # Should NOT contain approval/rejection in intent
        assert "approved" not in result.intent.lower()
        assert "rejected" not in result.intent.lower()
        assert "authorized" not in result.intent.lower()


def test_security_incident_no_prescription():
    """Test that security incidents extract facts without prescribing action."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "security_phishing",
            "entities": {
                "issue": "suspected phishing email",
                "planned_action": "forwarding to teammates"
            },
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "I think I got a phishing email — forwarding it to teammates to check",
            api_key="test-key"
        )
        
        # Should extract what user said, not what they should do
        assert result.intent == "security_phishing"
        assert "planned_action" in result.entities or "issue" in result.entities
        
        # Should NOT contain prescriptive instructions in entities
        entity_values = str(result.entities).lower()
        assert "do not forward" not in entity_values
        assert "must report" not in entity_values
        assert "should contact" not in entity_values


# ============================================================================
# EXAMPLE-BASED TESTS
# ============================================================================

def test_example_vpn_credentials_expired():
    """Test example: VPN credentials expired."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "vpn_access",
            "entities": {"issue": "VPN credentials expired"},
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "My VPN credentials expired",
            api_key="test-key"
        )
        
        assert result.intent == "vpn_access"
        assert "credentials" in result.entities["issue"].lower()
        assert result.missing_information == []


def test_example_wfh_monitor():
    """Test example: Work from home 4 days, need monitor."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "home_office_equipment",
            "entities": {
                "work_from_home_days_per_week": 4,
                "requested_equipment": "monitor"
            },
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "I've started working from home 4 days a week, how do I get a monitor?",
            api_key="test-key"
        )
        
        assert result.intent == "home_office_equipment"
        assert result.entities["work_from_home_days_per_week"] == 4
        assert "monitor" in result.entities["requested_equipment"].lower()


def test_example_phishing_email():
    """Test example: Suspected phishing email."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "security_phishing",
            "entities": {
                "issue": "suspected phishing email",
                "planned_action": "forwarding to teammates"
            },
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "I think I got a phishing email asking for my login — forwarding it to a few teammates to check",
            api_key="test-key"
        )
        
        assert result.intent == "security_phishing"
        assert "phishing" in result.entities["issue"].lower()


def test_example_vague_request():
    """Test example: Vague 'it's not working' request."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "unknown",
            "entities": {},
            "missing_information": [
                "device or system that is not working",
                "description of the problem"
            ]
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "hey can you help, its not working",
            api_key="test-key"
        )
        
        assert result.intent == "unknown"
        assert result.entities == {}
        assert len(result.missing_information) > 0


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

def test_api_key_from_parameter():
    """Test that API key can be passed as parameter."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "test",
            "entities": {},
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "test request",
            api_key="explicit-key"
        )
        
        # Verify client was initialized with explicit key
        mock_client.assert_called_once_with(api_key="explicit-key")


def test_model_from_parameter():
    """Test that model can be passed as parameter."""
    with patch('google.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "intent": "test",
            "entities": {},
            "missing_information": []
        })
        
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        
        result = understand_request(
            "test request",
            api_key="test-key",
            model="custom-model"
        )
        
        # Verify generate_content was called with custom model
        call_args = mock_instance.models.generate_content.call_args
        assert call_args[1]['model'] == "custom-model"
