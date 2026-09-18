"""
Agent Orchestrator

Thin coordination layer connecting all agent components into an end-to-end workflow.
This module contains NO business logic - only coordination and error handling.

Workflow:
1. Understand request (LLM extracts facts)
2. Retrieve policies (RAG finds relevant policies)
3. Search tickets (find related ticket context)
4. Evaluate decision (deterministic rules engine)
5. Generate response (LLM generates message text, preserves decision)
"""

from typing import Optional
from pathlib import Path

from app.agent.schemas import AgentResponse, ExtractedFacts
from app.agent.request_understanding import understand_request
from app.rag.retriever import PolicyRetriever
from app.agent.ticket_search import search_tickets
from app.agent.decision_engine import evaluate_decision
from app.agent.response_generator import generate_response


class AgentOrchestrator:
    """
    Orchestrates the agent workflow by connecting all components.
    
    This is a thin coordination layer with NO business logic.
    All business rules are in the decision engine (policy_rules.py).
    """
    
    def __init__(
        self,
        gemini_api_key: str,
        rag_retriever: PolicyRetriever,
        gemini_model: Optional[str] = None,
        tickets_path: Optional[Path] = None
    ):
        """
        Initialize orchestrator with required dependencies.
        
        Args:
            gemini_api_key: Google API key for Gemini LLM
            rag_retriever: Initialized PolicyRetriever for RAG
            gemini_model: Gemini model name (optional, uses env var or default)
            tickets_path: Optional path to tickets.json (for testing)
        """
        self.gemini_api_key = gemini_api_key
        self.rag_retriever = rag_retriever
        self.gemini_model = gemini_model
        self.tickets_path = tickets_path
    
    def run_agent(self, user_request: str) -> AgentResponse:
        """
        Execute the full agent workflow for a user request.
        
        This is the main entry point. It coordinates:
        - Request understanding (LLM)
        - Policy retrieval (RAG)
        - Ticket search (database)
        - Decision evaluation (deterministic rules)
        - Response generation (LLM for message text only)
        
        Args:
            user_request: Natural language request from user
        
        Returns:
            AgentResponse with decision and message
        
        Raises:
            ValueError: If request understanding or core workflow fails
        """
        try:
            # Step 1: Understand request using LLM
            facts = self._understand_request(user_request)
            
            # Step 2: Retrieve relevant policies using RAG
            policies = self._retrieve_policies(facts)
            
            # Step 3: Search for relevant tickets
            tickets = self._search_tickets(facts)
            
            # Step 4: Evaluate decision using deterministic rules
            decision = self._evaluate_decision(facts, policies, tickets)
            
            # Step 5: Generate response message (preserving decision)
            response = self._generate_response(decision)
            
            return response
        
        except ValueError as e:
            # Re-raise ValueError for critical failures
            raise
        except Exception as e:
            # Catch-all for unexpected errors
            raise ValueError(f"Agent workflow failed: {str(e)}") from e
    
    def _understand_request(self, user_request: str) -> ExtractedFacts:
        """Step 1: Use LLM to extract structured facts from request."""
        try:
            facts = understand_request(
                user_request,
                self.gemini_api_key,
                self.gemini_model
            )
            return facts
        except Exception as e:
            raise ValueError(f"Failed to understand request: {str(e)}") from e
    
    def _retrieve_policies(self, facts: ExtractedFacts) -> list:
        """Step 2: Use RAG to retrieve relevant policies."""
        try:
            # Build query from facts
            query = self._build_policy_query(facts)
            
            # Retrieve policies
            policies = self.rag_retriever.retrieve_policies(query, top_k=5)
            
            return policies
        except Exception as e:
            # If RAG fails, return empty list (decision engine will handle)
            return []
    
    def _search_tickets(self, facts: ExtractedFacts) -> list:
        """Step 3: Search for relevant tickets."""
        try:
            tickets = search_tickets(facts, self.tickets_path)
            return tickets
        except Exception as e:
            # If ticket search fails, return empty list
            return []
    
    def _evaluate_decision(self, facts, policies, tickets):
        """Step 4: Evaluate decision using deterministic rules engine."""
        try:
            decision = evaluate_decision(facts, policies, tickets)
            return decision
        except Exception as e:
            raise ValueError(f"Decision evaluation failed: {str(e)}") from e
    
    def _generate_response(self, decision):
        """Step 5: Generate natural language response (preserving decision)."""
        try:
            response = generate_response(
                decision,
                self.gemini_api_key,
                self.gemini_model
            )
            return response
        except Exception as e:
            # Response generator has built-in fallback, but catch any edge cases
            raise ValueError(f"Response generation failed: {str(e)}") from e
    
    def _build_policy_query(self, facts: ExtractedFacts) -> str:
        """Build a search query for policy retrieval based on extracted facts."""
        query_parts = []
        
        if facts.intent:
            query_parts.append(facts.intent)
        
        # Add entity values to query
        for key, value in facts.entities.items():
            if value:
                query_parts.append(f"{key} {value}")
        
        # Join with spaces
        query = " ".join(query_parts)
        
        # Fallback if no query parts
        if not query:
            query = "IT support policy"
        
        return query


def run_agent(
    user_request: str,
    gemini_api_key: str,
    rag_retriever: PolicyRetriever,
    gemini_model: Optional[str] = None,
    tickets_path: Optional[Path] = None
) -> AgentResponse:
    """
    Convenience function to run the agent workflow.
    
    Creates an orchestrator instance and executes the workflow.
    
    Args:
        user_request: Natural language request from user
        gemini_api_key: Google API key for Gemini
        rag_retriever: Initialized PolicyRetriever
        gemini_model: Gemini model name
        tickets_path: Optional path to tickets.json (for testing)
    
    Returns:
        AgentResponse with decision and message
    """
    orchestrator = AgentOrchestrator(
        gemini_api_key=gemini_api_key,
        rag_retriever=rag_retriever,
        gemini_model=gemini_model,
        tickets_path=tickets_path
    )
    
    return orchestrator.run_agent(user_request)
