"""
Policy ingestion script.

Loads supplied policy documents and ingests them into ChromaDB
for semantic retrieval.

This script is safe to run repeatedly - it will update existing
policies rather than creating duplicates.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.rag.policy_loader import load_policies
from app.rag.retriever import PolicyRetriever


def main():
    """Ingest policies into ChromaDB."""
    print("Veridian IT Service Agent - Policy Ingestion")
    print("=" * 60)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key in .env file")
        sys.exit(1)
    
    try:
        # Load policies
        print("\n1. Loading policies from data/policies.json...")
        policies = load_policies()
        print(f"   ✓ Loaded {len(policies)} policies")
        
        # Initialize retriever
        print("\n2. Initializing ChromaDB...")
        retriever = PolicyRetriever()
        print(f"   ✓ Collection: {retriever.collection_name}")
        print(f"   ✓ Location: {retriever.persist_directory}")
        
        # Ingest policies
        print("\n3. Ingesting policies...")
        count = retriever.ingest_policies(policies)
        print(f"   ✓ Ingested {count} policies")
        
        # Verify
        print("\n4. Verifying...")
        stored_count = retriever.get_collection_count()
        print(f"   ✓ Collection now contains {stored_count} policies")
        
        # Summary
        print("\n" + "=" * 60)
        print("Policy ingestion complete")
        print("-" * 60)
        print(f"Policies loaded: {len(policies)}")
        print(f"Policies stored: {stored_count}")
        print(f"Collection: {retriever.collection_name}")
        print(f"Location: {retriever.persist_directory}/")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
