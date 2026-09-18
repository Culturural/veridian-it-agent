"""
Policy loader for RAG system.

Loads policies from the source JSON file and validates them
using Pydantic models.
"""

import json
from pathlib import Path
from typing import List

from app.database.models import Policy


def load_policies(file_path: str = "data/policies.json") -> List[Policy]:
    """
    Load policies from JSON file and validate using Pydantic.
    
    Args:
        file_path: Path to policies.json file
        
    Returns:
        List of validated Policy objects
        
    Raises:
        FileNotFoundError: If the policies file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
        ValueError: If policy validation fails
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Policies file not found: {file_path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in policies file: {e.msg}",
            e.doc,
            e.pos
        )
    
    if not isinstance(data, list):
        raise ValueError(f"Expected list of policies, got {type(data).__name__}")
    
    policies = []
    for i, record in enumerate(data):
        try:
            policy = Policy(**record)
            policies.append(policy)
        except Exception as e:
            raise ValueError(f"Policy validation failed at index {i}: {e}")
    
    return policies
