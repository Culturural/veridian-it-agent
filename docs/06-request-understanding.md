# Request Understanding

## Purpose

The request understanding layer converts an employee's natural-language IT support request into a structured `ExtractedFacts` object that can be processed by downstream components.

**This layer answers:** "What is the employee asking for, and what facts are present in their request?"

**This layer does NOT:**
- Retrieve policies
- Enforce policies
- Make RESOLVE/FOLLOW_UP/ESCALATE decisions
- Authorize requests
- Create tickets
- Apply business rules

## Why an LLM?

Employee IT requests arrive in natural language with wide variability:
- "My laptop won't turn on" vs "Laptop dead" vs "Computer not working"
- Vague descriptions: "it's not working"
- Implicit information: "I work from home 4 days a week"
- Multiple issues in one request

A large language model (LLM) excels at:
1. **Intent classification** - Understanding what category of request this is
2. **Entity extraction** - Pulling out key facts (device type, symptoms, numbers)
3. **Ambiguity detection** - Recognizing when information is missing
4. **Normalization** - Converting varied phrasing into consistent structure

## Gemini Integration

We use **Google Gemini API** via the official `google-genai` Python SDK.

### Why Gemini?
- High-quality structured output support
- Native Pydantic schema integration
- Reliable entity extraction
- Cost-effective for this use case
- Proven compatibility with the project environment

### Configuration

**Environment Variables:**
```bash
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-3.6-flash  # Optional, defaults to this
```

**Model Selection:**
- Default: `gemini-3.6-flash`
- Configurable via environment for flexibility
- No hard-coded model names in implementation

### API Client

The implementation uses the official `google.genai.Client`:

```python
from google import genai
client = genai.Client(api_key=api_key)
```

## Structured Output

Gemini's native structured output support ensures the LLM response matches our `ExtractedFacts` Pydantic schema.

### How It Works

1. **Schema Definition**: We pass the `ExtractedFacts` Pydantic model directly to Gemini
2. **Response Format**: Gemini returns JSON matching the schema structure
3. **Validation**: Pydantic validates the response before returning

```python
response = client.models.generate_content(
    model=model_name,
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ExtractedFacts,
    )
)
```

**Benefits:**
- No manual JSON parsing or error-prone regex
- Guaranteed structure matching our schema
- Type-safe throughout the pipeline
- Pydantic validation catches malformed output

## ExtractedFacts Contract

The structured output conforms to the existing `ExtractedFacts` model from `app/agent/schemas.py`:

```python
class ExtractedFacts(BaseModel):
    intent: str                     # Classified intent
    entities: Dict[str, Any]        # Extracted key-value facts
    missing_information: List[str]  # Information needed but absent
```

### Intent

A concise label describing what the user wants.

**Good intents:**
- `vpn_access` - User needs VPN-related help
- `laptop_issue` - Problem with laptop hardware
- `home_office_equipment` - Requesting home office items
- `security_phishing` - Suspected phishing/security incident
- `unknown` - Request is too vague to classify

**Avoid policy-decision intents:**
- ❌ `vpn_auto_approved` - This encodes policy logic
- ✅ `vpn_access` - This describes the request

### Entities

Key facts extracted from the request, stored as key-value pairs.

**Examples:**
```python
# "My laptop won't turn on, had it about 3.5 years"
entities = {
    "device": "laptop",
    "issue": "won't turn on",
    "age_years": 3.5
}

# "I work from home 4 days a week, need a monitor"
entities = {
    "work_from_home_days_per_week": 4,
    "requested_equipment": "monitor"
}

# "VPN credentials expired"
entities = {
    "issue": "VPN credentials expired"
}
```

**Guidelines:**
- Extract only facts explicitly stated or directly implied
- Preserve numbers, dates, symptoms, requested items
- Do NOT invent facts
- Do NOT apply policy interpretation
- Empty dict `{}` if no clear entities

### Missing Information

List of information genuinely needed to understand the request.

**Examples:**
```python
# "hey can you help, its not working"
missing_information = [
    "device or system affected",
    "description of the problem"
]

# "My VPN stopped working"
missing_information = []  # Sufficient information
```

**Guidelines:**
- Only include information truly needed for understanding
- Do NOT list information needed for policy decisions (that's later)
- Empty list `[]` if request is sufficiently clear

## Prompt Responsibilities

The extraction prompt explicitly defines boundaries:

### LLM IS Responsible For:
1. ✅ Understanding natural language
2. ✅ Classifying intent
3. ✅ Extracting entities from the request
4. ✅ Identifying missing information
5. ✅ Returning structured data

### LLM is NOT Responsible For:
1. ❌ Retrieving company policies
2. ❌ Enforcing policies
3. ❌ Determining approval
4. ❌ Making RESOLVE/FOLLOW_UP/ESCALATE decisions
5. ❌ Creating tickets
6. ❌ Inventing facts
7. ❌ Applying business rules

### Prompt Design

The prompt explicitly instructs the model:

```
You are the request-understanding component of an internal IT service agent.

Your job is to extract facts from the employee's request.

CRITICAL RULES:
- Extract ONLY information explicitly stated or directly implied
- Do NOT invent facts
- Do NOT apply company policy
- Do NOT determine whether the request should be approved
- ...
```

This prevents the LLM from overstepping into policy enforcement or decision-making.

## Examples

### Example 1: Home Office Equipment

**Input:**
```
I've started working from home 4 days a week, how do I get a monitor?
```

**Output:**
```python
ExtractedFacts(
    intent="home_office_equipment",
    entities={
        "work_from_home_days_per_week": 4,
        "requested_equipment": "monitor"
    },
    missing_information=[]
)
```

**Why:** Request is clear, contains specific number and item. The LLM does NOT determine if the monitor is approved (that's policy engine's job).

### Example 2: VPN Issue

**Input:**
```
My VPN stopped working this morning, says credentials expired.
```

**Output:**
```python
ExtractedFacts(
    intent="vpn_access",
    entities={
        "issue": "VPN credentials expired",
        "timeframe": "this morning"
    },
    missing_information=[]
)
```

**Why:** Clear issue description. The LLM does NOT apply KB-02 policy (that's RAG's job).

### Example 3: Security Incident

**Input:**
```
I think I got a phishing email asking for my login — forwarding it to a few teammates to check.
```

**Output:**
```python
ExtractedFacts(
    intent="security_phishing",
    entities={
        "issue": "suspected phishing email",
        "planned_action": "forwarding to teammates"
    },
    missing_information=[]
)
```

**Why:** The LLM extracts what the employee said, including their planned action. It does NOT tell them what to do (that's the decision engine's job after retrieving KB-09).

### Example 4: Vague Request

**Input:**
```
hey can you help, its not working
```

**Output:**
```python
ExtractedFacts(
    intent="unknown",
    entities={},
    missing_information=[
        "device or system affected",
        "description of the problem"
    ]
)
```

**Why:** Request is too vague. The LLM recognizes this and identifies what's missing, enabling the system to ask follow-up questions.

## Error Handling

The implementation handles multiple failure modes:

### Input Validation
```python
if not text or not text.strip():
    raise ValueError("Request text must be non-empty")
```

### Configuration Validation
```python
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is required")
```

### API Failures
```python
try:
    response = client.models.generate_content(...)
except Exception as e:
    raise RuntimeError(f"Gemini API call failed: {e}")
```

### Response Validation
```python
if not response or not response.text:
    raise RuntimeError("Gemini returned empty response")

data = json.loads(response.text)  # May raise JSONDecodeError
facts = ExtractedFacts(**data)     # Pydantic validates structure
```

**Error Philosophy:**
- Fail explicitly, never silently
- Do NOT fabricate fallback facts
- Raise meaningful exceptions
- Let the caller decide how to handle failures

## Testing Strategy

Tests use mocked Gemini API responses to avoid:
- External API dependencies
- API quota consumption
- Non-deterministic behavior
- Test execution delays

### Mock Approach

```python
with patch('google.genai.Client') as mock_client:
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "intent": "vpn_access",
        "entities": {"issue": "VPN credentials expired"},
        "missing_information": []
    })
    mock_client.return_value.models.generate_content.return_value = mock_response
    
    result = understand_request("My VPN stopped working")
    assert result.intent == "vpn_access"
```

### Test Coverage

1. ✅ Successful extraction with valid output
2. ✅ Structured Pydantic result validation
3. ✅ Empty input rejection
4. ✅ Missing API key handling
5. ✅ API failure handling
6. ✅ Invalid JSON response handling
7. ✅ Ambiguous request handling
8. ✅ Numeric/entity extraction
9. ✅ No policy decision leakage

All tests verify the returned `ExtractedFacts`, not just that the API was called.

## Architectural Boundary

The request understanding layer is ONE component in the agent pipeline:

```
User Request (natural language)
    ↓
LLM Request Understanding ← YOU ARE HERE
    ↓
ExtractedFacts
    ↓
Policy Retrieval (RAG)
    ↓
PolicyEvidence
    ↓
Decision Engine
    ↓
AgentDecision
    ↓
Response Generator
    ↓
AgentResponse
```

**This phase stops after producing `ExtractedFacts`.**

### What Comes Next (Not This Phase)

- **Policy Retrieval**: Takes `ExtractedFacts.intent` and uses RAG to find relevant policies
- **Decision Engine**: Combines `ExtractedFacts` + `PolicyEvidence` + business rules → `AgentDecision`
- **Response Generator**: Converts `AgentDecision` → `AgentResponse`

### Clear Separation

By isolating request understanding:
1. **Testing** is simpler (mock one API, validate one output)
2. **Swapping** LLM providers is easier
3. **Debugging** is clearer (each component has one job)
4. **Reasoning** is explicit (facts separated from policy)

## Limitations

### Context Window
The LLM sees only the current request, not:
- Previous conversation history
- Employee's role or department
- Historical tickets
- Company policies

These are added by later stages.

### Extraction Accuracy
The LLM may:
- Misclassify ambiguous intents
- Extract entities with slight variations
- Miss subtle implications

The decision engine compensates by validating facts against policy requirements.

### Policy Blind
This layer intentionally does NOT see policies. This prevents:
- Policy hallucination
- Authorization bypass
- Inconsistent policy application

Policies are retrieved deterministically after extraction.

## Security Considerations

### API Key Management
- ✅ API key read from environment
- ✅ No hard-coded keys in source
- ✅ `.env` is gitignored
- ✅ `.env.example` contains only placeholder
- ✅ Tests use mocks, not real keys

### Input Validation
- Request text is validated (non-empty)
- No arbitrary code execution
- No prompt injection protection needed (extraction task is safe)

### Output Validation
- All output validated by Pydantic
- No raw LLM text passed downstream
- Invalid structure raises exception

## Performance

**Typical Latency:**
- Gemini API call: 500-2000ms
- JSON parsing: <1ms
- Pydantic validation: <1ms
- **Total: ~0.5-2 seconds per request**

**Optimization Opportunities (Future):**
- Batch processing for multiple requests
- Caching for duplicate/similar requests
- Async API calls for parallel processing

## Summary

The request understanding layer provides a clean, tested interface for converting natural-language IT requests into structured facts. By using Gemini's native structured output support and maintaining strict boundaries, it ensures reliable, maintainable, and explainable request processing.

**Key Principle:** Extract facts, don't make decisions.
