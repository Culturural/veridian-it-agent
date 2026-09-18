"""
Tests for RAG (policy retrieval) system.

Tests policy loading, metadata construction, and retrieval logic
without requiring OpenAI API or network access (using mocks).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path

from app.rag.policy_loader import load_policies
from app.rag.retriever import PolicyRetriever
from app.database.models import Policy
from app.agent.schemas import PolicyEvidence


# ============================================================================
# POLICY LOADER TESTS
# ============================================================================

def test_policy_loader_loads_all_policies():
    """Test that policy loader loads all 11 policies."""
    policies = load_policies("data/policies.json")
    
    assert len(policies) == 11
    assert all(isinstance(p, Policy) for p in policies)


def test_policy_loader_validates_through_pydantic():
    """Test that policy loader validates records through Pydantic."""
    policies = load_policies("data/policies.json")
    
    # Check that all required fields are present
    for policy in policies:
        assert policy.id
        assert policy.title
        assert policy.category
        assert policy.content
        assert policy.source_type


def test_policy_loader_file_not_found():
    """Test that policy loader fails clearly if file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_policies("nonexistent.json")


def test_policy_loader_invalid_json(tmp_path):
    """Test that policy loader fails on invalid JSON."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("not valid json{")
    
    with pytest.raises(json.JSONDecodeError):
        load_policies(str(invalid_file))


def test_policy_loader_invalid_structure(tmp_path):
    """Test that policy loader fails on invalid structure."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text('{"not": "a list"}')
    
    with pytest.raises(ValueError, match="Expected list"):
        load_policies(str(invalid_file))


# ============================================================================
# METADATA CONSTRUCTION TESTS
# ============================================================================

def test_metadata_construction():
    """Test that metadata is constructed correctly."""
    policies = load_policies("data/policies.json")
    
    # Find KB-02 as an example
    kb02 = next(p for p in policies if p.id == "KB-02")
    
    # Construct metadata as retriever would
    metadata = {
        "policy_id": kb02.id,
        "title": kb02.title,
        "category": kb02.category,
        "source_type": kb02.source_type
    }
    
    assert metadata["policy_id"] == "KB-02"
    assert metadata["title"] == "VPN Access"
    assert metadata["category"] == "vpn"
    assert metadata["source_type"] == "knowledge_base"


def test_policy_content_preserved():
    """Test that policy content is preserved exactly."""
    policies = load_policies("data/policies.json")
    
    # Check that content matches source (spot check KB-01)
    kb01 = next(p for p in policies if p.id == "KB-01")
    
    assert "self-service portal" in kb01.content
    assert "5 failed attempts" in kb01.content
    assert "No approval required" in kb01.content


# ============================================================================
# RETRIEVER VALIDATION TESTS
# ============================================================================

def test_empty_query_rejected():
    """Test that empty query is rejected."""
    with patch('chromadb.PersistentClient'):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            retriever = PolicyRetriever()
            
            with pytest.raises(ValueError, match="Query must be non-empty"):
                retriever.retrieve_policies("")
            
            with pytest.raises(ValueError, match="Query must be non-empty"):
                retriever.retrieve_policies("   ")


def test_invalid_top_k_rejected():
    """Test that invalid top_k is rejected."""
    with patch('chromadb.PersistentClient'):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            retriever = PolicyRetriever()
            
            with pytest.raises(ValueError, match="top_k must be positive"):
                retriever.retrieve_policies("test query", top_k=0)
            
            with pytest.raises(ValueError, match="top_k must be positive"):
                retriever.retrieve_policies("test query", top_k=-1)


def test_missing_api_key():
    """Test that retriever fails without API key."""
    with patch('chromadb.PersistentClient'):
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                PolicyRetriever()


# ============================================================================
# CONVERSION TESTS
# ============================================================================

def test_retrieval_converts_to_policy_evidence():
    """Test that retrieval results are converted to PolicyEvidence."""
    with patch('chromadb.PersistentClient') as mock_client:
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            # Mock collection
            mock_collection = MagicMock()
            mock_collection.count.return_value = 3
            mock_collection.query.return_value = {
                'ids': [['KB-01', 'KB-02']],
                'documents': [['Content 1', 'Content 2']],
                'metadatas': [[
                    {'policy_id': 'KB-01', 'title': 'Title 1', 'category': 'cat1', 'source_type': 'kb'},
                    {'policy_id': 'KB-02', 'title': 'Title 2', 'category': 'cat2', 'source_type': 'kb'}
                ]],
                'distances': [[0.1, 0.3]]
            }
            
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            retriever = PolicyRetriever()
            results = retriever.retrieve_policies("test query", top_k=2)
            
            assert len(results) == 2
            assert all(isinstance(r, PolicyEvidence) for r in results)
            assert results[0].policy_id == 'KB-01'
            assert results[0].title == 'Title 1'
            assert results[0].content == 'Content 1'


def test_relevance_scores_within_bounds():
    """Test that relevance scores remain within 0-1."""
    with patch('chromadb.PersistentClient') as mock_client:
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            # Mock collection with various distances
            mock_collection = MagicMock()
            mock_collection.count.return_value = 3
            mock_collection.query.return_value = {
                'ids': [['KB-01', 'KB-02', 'KB-03']],
                'documents': [['Content 1', 'Content 2', 'Content 3']],
                'metadatas': [[
                    {'policy_id': 'KB-01', 'title': 'T1', 'category': 'c1', 'source_type': 'kb'},
                    {'policy_id': 'KB-02', 'title': 'T2', 'category': 'c2', 'source_type': 'kb'},
                    {'policy_id': 'KB-03', 'title': 'T3', 'category': 'c3', 'source_type': 'kb'}
                ]],
                'distances': [[0.0, 0.5, 2.0]]  # Various distances
            }
            
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            retriever = PolicyRetriever()
            results = retriever.retrieve_policies("test query", top_k=3)
            
            for result in results:
                assert result.relevance is not None
                assert 0.0 <= result.relevance <= 1.0


def test_distance_to_relevance_conversion():
    """Test distance to relevance conversion logic."""
    with patch('chromadb.PersistentClient'):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            retriever = PolicyRetriever()
            
            # Distance 0 should give relevance close to 1.0
            rel_0 = retriever._distance_to_relevance(0.0)
            assert rel_0 == pytest.approx(1.0, abs=0.01)
            
            # Distance increases, relevance decreases
            rel_1 = retriever._distance_to_relevance(1.0)
            rel_2 = retriever._distance_to_relevance(2.0)
            assert rel_1 > rel_2
            
            # All values within bounds
            assert 0.0 <= rel_0 <= 1.0
            assert 0.0 <= rel_1 <= 1.0
            assert 0.0 <= rel_2 <= 1.0
            
            # None distance returns None
            assert retriever._distance_to_relevance(None) is None


# ============================================================================
# ID PRESERVATION TESTS
# ============================================================================

def test_stable_policy_ids_preserved():
    """Test that stable policy IDs are preserved."""
    policies = load_policies("data/policies.json")
    
    # Check expected IDs
    expected_ids = [
        "KB-01", "KB-02", "KB-03", "KB-04", "KB-05",
        "KB-06", "KB-07", "KB-08", "KB-09", "KB-10",
        "ASSET-01"
    ]
    
    actual_ids = [p.id for p in policies]
    
    for expected_id in expected_ids:
        assert expected_id in actual_ids


# ============================================================================
# INGESTION TESTS
# ============================================================================

def test_duplicate_ingestion_safe():
    """Test that duplicate ingestion is safe/idempotent."""
    with patch('chromadb.PersistentClient') as mock_client:
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_collection = MagicMock()
            mock_collection.count.return_value = 11
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            retriever = PolicyRetriever()
            
            # Create test policies
            test_policies = [
                Policy(
                    id="TEST-01",
                    title="Test Policy",
                    category="test",
                    content="Test content",
                    source_type="knowledge_base"
                )
            ]
            
            # Ingest twice
            count1 = retriever.ingest_policies(test_policies)
            count2 = retriever.ingest_policies(test_policies)
            
            # Both should succeed
            assert count1 == 1
            assert count2 == 1
            
            # Upsert should be called (not insert)
            assert mock_collection.upsert.call_count == 2


def test_ingest_preserves_metadata():
    """Test that ingestion preserves all metadata."""
    with patch('chromadb.PersistentClient') as mock_client:
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            mock_collection = MagicMock()
            mock_client.return_value.get_or_create_collection.return_value = mock_collection
            
            retriever = PolicyRetriever()
            
            test_policy = Policy(
                id="KB-02",
                title="VPN Access",
                category="vpn",
                content="VPN access is granted...",
                source_type="knowledge_base"
            )
            
            retriever.ingest_policies([test_policy])
            
            # Check upsert was called with correct data
            call_args = mock_collection.upsert.call_args
            assert call_args[1]['ids'] == ['KB-02']
            assert call_args[1]['documents'] == ['VPN access is granted...']
            assert call_args[1]['metadatas'][0]['policy_id'] == 'KB-02'
            assert call_args[1]['metadatas'][0]['title'] == 'VPN Access'
            assert call_args[1]['metadatas'][0]['category'] == 'vpn'
            assert call_args[1]['metadatas'][0]['source_type'] == 'knowledge_base'


def test_empty_ingestion():
    """Test that ingesting empty list is handled gracefully."""
    with patch('chromadb.PersistentClient'):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            retriever = PolicyRetriever()
            count = retriever.ingest_policies([])
            assert count == 0
