"""
Veridian IT Service Agent - Streamlit Demo UI

A minimal demo frontend for the Veridian IT Service Agent.
Connects to the existing orchestrator - NO business logic in UI.
"""

import os
import streamlit as st
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add project root to path for imports
import sys
project_root = Path(__file__).parents[2]
sys.path.insert(0, str(project_root))

from app.agent.orchestrator import run_agent
from app.rag.retriever import PolicyRetriever


# Page configuration
st.set_page_config(
    page_title="Veridian IT Service Agent",
    page_icon="🔧",
    layout="wide"
)

# Example requests
EXAMPLE_REQUESTS = [
    "My VPN credentials have expired.",
    "My laptop is completely dead and is 3.5 years old.",
    "I received a phishing email asking for my login.",
    "I work from home 4 days a week and need a monitor.",
    "Hey can you help, it's not working?"
]


def initialize_agent():
    """Initialize the agent components (RAG retriever)."""
    if 'rag_retriever' not in st.session_state:
        # Get API key from environment
        gemini_key = os.getenv("GEMINI_API_KEY")
        
        if not gemini_key:
            st.error("❌ GEMINI_API_KEY environment variable not set")
            st.stop()
        
        # Initialize RAG retriever
        try:
            st.session_state.rag_retriever = PolicyRetriever(
                collection_name="veridian_policies"
            )
            st.session_state.gemini_key = gemini_key
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"❌ Failed to initialize agent: {e}")
            st.info("Make sure policies are ingested. Run: python scripts/ingest_policies.py")
            st.stop()


def render_sidebar():
    """Render the sidebar with architecture information."""
    with st.sidebar:
        st.header("🏗️ Architecture")
        
        st.markdown("""
        **Agent Pipeline:**
        
        1. 🧠 **Gemini LLM**  
           Understands request
        
        2. 📚 **Policy RAG**  
           ChromaDB + Local embeddings
        
        3. 🎫 **Ticket Context**  
           Historical ticket search
        
        4. ⚖️ **Decision Engine**  
           Deterministic policy rules
        
        5. 💬 **Response Generator**  
           Gemini generates message
        """)
        
        st.divider()
        
        st.markdown("""
        **Decision Types:**
        - 🟢 **RESOLVE** - Agent can handle
        - 🟡 **FOLLOW_UP** - Needs more info
        - 🔴 **ESCALATE** - Requires human IT
        """)
        
        st.divider()
        
        st.caption("Veridian IT Service Agent Demo")
        st.caption("Built with Streamlit")


def render_result(response):
    """Render the agent response in a formatted way."""
    
    # Decision badge
    decision = response.decision
    if decision == "RESOLVE":
        st.success(f"✅ Decision: **{decision}**")
    elif decision == "FOLLOW_UP":
        st.warning(f"❓ Decision: **{decision}**")
    elif decision == "ESCALATE":
        st.error(f"🚨 Decision: **{decision}**")
    
    # Agent response message
    st.subheader("Agent Response")
    st.markdown(response.message)
    
    # Follow-up questions if any
    if response.follow_up_questions:
        st.subheader("ℹ️ Information Needed")
        for question in response.follow_up_questions:
            st.markdown(f"- {question}")
    
    # Policy sources
    if response.sources:
        st.subheader("📋 Policy Sources")
        st.markdown(", ".join(response.sources))
    
    # Ticket context (if we want to show it)
    # Note: The current AgentResponse doesn't include ticket info
    # but we could add it if needed


def main():
    """Main Streamlit application."""
    
    # Title
    st.title("🔧 Veridian IT Service Agent")
    st.subheader("AI-Powered Internal IT Support Assistant")
    
    # Initialize agent
    initialize_agent()
    
    # Render sidebar
    render_sidebar()
    
    # Main content
    st.markdown("---")
    
    # Example requests as buttons
    st.markdown("**Quick Examples:**")
    cols = st.columns(5)
    
    for idx, example in enumerate(EXAMPLE_REQUESTS):
        with cols[idx % 5]:
            if st.button(
                example[:30] + "..." if len(example) > 30 else example,
                key=f"example_{idx}",
                use_container_width=True
            ):
                st.session_state.user_input = example
    
    st.markdown("---")
    
    # User input
    user_request = st.text_area(
        "Describe your IT issue",
        height=100,
        placeholder="Example: My laptop won't turn on and it's 4 years old...",
        value=st.session_state.get('user_input', ''),
        key='request_input'
    )
    
    # Submit button
    col1, col2, col3 = st.columns([1, 1, 4])
    
    with col1:
        submit_button = st.button("Submit Request", type="primary", use_container_width=True)
    
    with col2:
        if st.button("Clear", use_container_width=True):
            st.session_state.user_input = ""
            st.rerun()
    
    # Process request
    if submit_button and user_request.strip():
        with st.spinner("🤖 Agent processing your request..."):
            try:
                # Call the orchestrator
                response = run_agent(
                    user_request=user_request,
                    gemini_api_key=st.session_state.gemini_key,
                    rag_retriever=st.session_state.rag_retriever
                )
                
                # Display results
                st.markdown("---")
                st.header("Results")
                render_result(response)
                
            except Exception as e:
                st.error(f"❌ Error processing request: {e}")
                st.exception(e)
    
    elif submit_button:
        st.warning("⚠️ Please enter a request description")
    
    # Footer
    st.markdown("---")
    st.caption("Demo UI - Veridian IT Service Agent Technical Assignment")


if __name__ == "__main__":
    main()
