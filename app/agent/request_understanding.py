"""
LLM request understanding layer using Google Gemini.

This module is responsible ONLY for:
- Understanding natural-language requests
- Identifying user intent
- Extracting entities explicitly present in the request
- Identifying missing information

This module does NOT:
- Retrieve policies
- Enforce policies
- Make RESOLVE/FOLLOW_UP/ESCALATE decisions
- Authorize requests
- Create tickets
- Search tickets
- Invent facts not present in the request
"""

import json
import os
from typing import Optional

from google import genai
from google.genai import types

from app.agent.schemas import ExtractedFacts


# Default model configuration
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

# Extraction prompt
EXTRACTION_PROMPT = """You are the request-understanding component of an internal IT service agent.

Your job is to extract facts from the employee's request.

CRITICAL RULES:
- Extract ONLY information explicitly stated or directly implied by the request
- Do NOT invent facts
- Do NOT apply company policy
- Do NOT determine whether the request should be approved
- Do NOT decide whether a ticket should be created
- Do NOT retrieve or infer policy
- Do NOT make RESOLVE/FOLLOW_UP/ESCALATE decisions
- If the request is ambiguous, use a broad/unknown intent and list missing information
- Preserve important numerical values, requested items, symptoms, and conditions
- Missing information should contain only information genuinely required to understand the request
- Do NOT ask questions inside the entities field
- Return only the structured schema

INTENT GUIDELINES:
- Use concise intent names that describe what the user wants (e.g., "vpn_access", "laptop_issue", "home_office_equipment")
- Do NOT create policy decision intents (avoid "vpn_auto_approved", use "vpn_access")
- Use "unknown" for unclear or vague requests

ENTITIES:
- Extract key facts: device types, issues, symptoms, timeframes, numbers, requested items
- Store as key-value pairs (e.g., {"device": "laptop", "age_years": 3.5})
- Leave empty if no clear entities

MISSING INFORMATION:
- List ONLY information that is genuinely needed to understand the request
- Examples: "device type", "issue description", "specific problem"
- Leave empty if the request is clear enough

Now extract facts from the following employee request:"""


def understand_request(
    text: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> ExtractedFacts:
    """
    Extract structured facts from a natural-language IT request using Gemini.
    
    This function uses Google Gemini API with structured output to parse
    the employee's request into the ExtractedFacts schema.
    
    Args:
        text: The employee's request text
        api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        model: Gemini model name (defaults to GEMINI_MODEL env var or constant)
        
    Returns:
        ExtractedFacts object with intent, entities, and missing_information
        
    Raises:
        ValueError: If input is empty or API key is missing
        RuntimeError: If Gemini API call fails
    """
    # Validate input
    if not text or not text.strip():
        raise ValueError("Request text must be non-empty")
    
    # Get API key
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    # Get model name
    model_name = model or os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    
    try:
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Create prompt
        prompt = f"{EXTRACTION_PROMPT}\n\n{text}"
        
        # Call Gemini with structured output
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ExtractedFacts,
            )
        )
        
        # Parse response
        if not response or not response.text:
            raise RuntimeError("Gemini returned empty response")
        
        # Parse JSON and validate with Pydantic
        data = json.loads(response.text)
        facts = ExtractedFacts(**data)
        
        return facts
        
    except (ValueError, json.JSONDecodeError) as e:
        # Re-raise validation and JSON decode errors with context
        if isinstance(e, json.JSONDecodeError):
            raise RuntimeError(f"Failed to parse Gemini response as JSON: {e}")
        raise
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {e}")
