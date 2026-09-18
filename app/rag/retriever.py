"""
Policy retriever using ChromaDB and OpenAI embeddings.

Performs semantic search over the policy corpus and returns
PolicyEvidence objects.

IMPORTANT: This module retrieves evidence only. It does NOT:
- Make RESOLVE/FOLLOW_UP/ESCALATE decisions
- Authorize requests
- Enforce policy rules
- Create tickets
"""

import os
from typing import List, Optional

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

from app.database.models import Policy
from app.agent.schemas import PolicyEvidence


# Configuration
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
CHROMA_PERSIST_DIR = "data/chroma"
COLLECTION_NAME = "veridian_policies"


class PolicyRetriever:
    """
    Retrieves relevant policies using semantic similarity search.
    
    RAG retrieves evidence; the policy engine enforces decisions.
    """
    
    def __init__(
        self,
        persist_directory: str = CHROMA_PERSIST_DIR,
        collection_name: str = COLLECTION_NAME,
        embedding_model: Optional[str] = None
    ):
        """
        Initialize the policy retriever.
        
        Args:
            persist_directory: Path to ChromaDB persistent storage
            collection_name: Name of the policy collection
            embedding_model: OpenAI embedding model (defaults to env or constant)
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Get embedding model from env or use default
        self.embedding_model = (
            embedding_model or
            os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        )
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Initialize OpenAI embedding function
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name=self.embedding_model
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
    
    def retrieve_policies(
        self,
        query: str,
        top_k: int = 3
    ) -> List[PolicyEvidence]:
        """
        Retrieve relevant policies using semantic similarity.
        
        Args:
            query: User's request or query text
            top_k: Number of policies to retrieve
            
        Returns:
            List of PolicyEvidence objects with relevance scores
            
        Raises:
            ValueError: If query is empty or top_k is invalid
        """
        if not query or not query.strip():
            raise ValueError("Query must be non-empty")
        
        if top_k < 1:
            raise ValueError("top_k must be positive")
        
        # Query ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count())
        )
        
        # Convert to PolicyEvidence
        evidence_list = []
        
        if results['ids'] and results['ids'][0]:
            for i, policy_id in enumerate(results['ids'][0]):
                # Extract metadata and document
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                document = results['documents'][0][i] if results['documents'] else ""
                
                # Get distance and convert to relevance score
                distance = results['distances'][0][i] if results['distances'] else None
                relevance = self._distance_to_relevance(distance)
                
                # Create PolicyEvidence
                evidence = PolicyEvidence(
                    policy_id=policy_id,
                    title=metadata.get('title', ''),
                    content=document,
                    relevance=relevance
                )
                evidence_list.append(evidence)
        
        return evidence_list
    
    def _distance_to_relevance(self, distance: Optional[float]) -> Optional[float]:
        """
        Convert ChromaDB distance to relevance score.
        
        ChromaDB returns L2 (Euclidean) distance by default for OpenAI embeddings.
        Lower distance = more similar.
        
        We convert to a relevance score where:
        - 1.0 = most relevant (distance ≈ 0)
        - 0.0 = least relevant (large distance)
        
        This uses a simple exponential decay: relevance = e^(-distance)
        
        IMPORTANT: This score is a retrieval signal only, NOT:
        - Probability of correctness
        - LLM confidence
        - Authorization confidence
        
        Args:
            distance: L2 distance from ChromaDB
            
        Returns:
            Relevance score between 0.0 and 1.0, or None if distance is None
        """
        if distance is None:
            return None
        
        import math
        # Exponential decay: e^(-distance)
        # Distance of 0 -> relevance 1.0
        # Distance increases -> relevance approaches 0
        relevance = math.exp(-distance)
        
        # Ensure within bounds
        return max(0.0, min(1.0, relevance))
    
    def ingest_policies(self, policies: List[Policy]) -> int:
        """
        Ingest policies into ChromaDB.
        
        This operation is idempotent - running it multiple times with the
        same policies will update existing records rather than creating duplicates.
        
        Args:
            policies: List of Policy objects to ingest
            
        Returns:
            Number of policies ingested
        """
        if not policies:
            return 0
        
        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for policy in policies:
            ids.append(policy.id)
            documents.append(policy.content)
            metadatas.append({
                "policy_id": policy.id,
                "title": policy.title,
                "category": policy.category,
                "source_type": policy.source_type
            })
        
        # Upsert into collection (idempotent)
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        return len(policies)
    
    def get_collection_count(self) -> int:
        """Get the number of policies in the collection."""
        return self.collection.count()
