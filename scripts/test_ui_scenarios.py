"""
Test script for UI scenarios

This script tests the orchestrator with the 4 required scenarios
to verify the logic works before running the full UI.

Usage:
  python scripts/test_ui_scenarios.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

from app.agent.orchestrator import run_agent
from app.rag.retriever import PolicyRetriever


def run_scenario_test(name: str, request: str, rag_retriever, gemini_key):
    """Test a single scenario and print results."""
    print(f"\n{'='*70}")
    print(f"SCENARIO: {name}")
    print(f"{'='*70}")
    print(f"Request: {request}")
    print()
    
    try:
        response = run_agent(
            user_request=request,
            gemini_api_key=gemini_key,
            rag_retriever=rag_retriever
        )
        
        print(f"[DECISION] {response.decision}")
        print(f"\n[RESPONSE]")
        print(response.message)
        
        if response.sources:
            print(f"\n[SOURCES] {', '.join(response.sources)}")
        
        if response.follow_up_questions:
            print(f"\n[INFO NEEDED]")
            for q in response.follow_up_questions:
                print(f"  - {q}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run test scenarios."""
    print("Veridian IT Service Agent - UI Scenario Tests")
    print("="*70)
    
    # Check API key
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_key:
        print("[ERROR] GEMINI_API_KEY not set")
        print("Please set in .env file")
        return False
    
    # Initialize RAG
    print("\n[INIT] Initializing RAG retriever...")
    try:
        rag_retriever = PolicyRetriever(
            collection_name="veridian_policies"
        )
        print("[OK] RAG retriever initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize RAG: {e}")
        print("Run: python scripts/ingest_policies.py")
        return False
    
    # Test scenarios
    scenarios = [
        ("VPN Expired", "My VPN credentials have expired."),
        ("Phishing Email", "I received a phishing email asking for my login."),
        ("Vague Request", "Hey can you help, it's not working?"),
        ("Laptop 3.5 years + failure", "My laptop is completely dead and is 3.5 years old."),
    ]
    
    results = []
    for name, request in scenarios:
        success = run_scenario_test(name, request, rag_retriever, gemini_key)
        results.append((name, success))
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    print(f"\nTotal: {passed}/{total} scenarios passed")
    
    return all(s for _, s in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
