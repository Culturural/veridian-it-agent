# Veridian IT Service Agent - Streamlit UI

## Setup

1. **Set API Keys**

   Create/update `.env` file in project root:
   ```
   GEMINI_API_KEY=your-gemini-key-here
   ```

2. **Ingest Policies** (one-time setup)

   ```bash
   python scripts/ingest_policies.py
   ```

   This loads the 11 policies into ChromaDB for RAG retrieval.

3. **Run the UI**

   ```bash
   streamlit run app/ui/app.py
   ```

   The app will open in your browser at http://localhost:8501

## Usage

### Quick Examples

Click any of the 5 example buttons:
- VPN credentials expired
- Laptop dead (3.5 years old)
- Phishing email report
- Work from home monitor request
- Vague request ("it's not working")

### Custom Request

Type your IT issue in the text area and click "Submit Request"

### Understanding Results

**Decision Types:**
- ✅ **RESOLVE** - Agent can handle via self-service
- ❓ **FOLLOW_UP** - Needs more information
- 🚨 **ESCALATE** - Requires human IT support

**Display Sections:**
- **Agent Response** - Natural language explanation
- **Information Needed** - Missing details (for FOLLOW_UP)
- **Policy Sources** - Which policies were used (KB-01, KB-02, etc.)

## Architecture

The UI is a thin layer that calls:

```
User Input → run_agent() → AgentResponse
```

The `run_agent()` function orchestrates:
1. Request Understanding (Gemini)
2. Policy Retrieval (ChromaDB + Local Embeddings)
3. Ticket Search (JSON search)
4. Decision Engine (Deterministic rules)
5. Response Generation (Gemini)

**No business logic in the UI** - all decisions are made by the decision engine.

## Test Scenarios

Recommended tests:

1. **VPN Expired** → Should RESOLVE (KB-02)
2. **Phishing Email** → Should ESCALATE (KB-09)
3. **Vague Request** → Should FOLLOW_UP (missing info)
4. **Laptop 3.5 years + failure** → Should FOLLOW_UP (KB-03, reported ≠ verified)
5. **Work from home monitor** → Should depend on WFH days (KB-10)

## Troubleshooting

**"GEMINI_API_KEY not set"**
- Add your Gemini API key to `.env`

**"Failed to initialize agent"**
- Run `python scripts/ingest_policies.py` first
- Make sure ChromaDB is not corrupted

**"No policies found"**
- Delete `data/chroma/` directory and re-run ingestion

## Notes

- This is a **demo UI**, not production-ready
- No authentication or user management
- No persistent session history
- No ticket creation (read-only)
- No policy modification
