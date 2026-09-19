# Veridian IT Service Agent

An internal IT support agent for Veridian Corp that understands employee IT requests, retrieves relevant company policies, resolves simple requests, asks clarifying questions when needed, escalates complex or risky requests, creates structured tickets, cites sources, and maintains a complete audit trail.

## Assignment

Internal Service Agent — IT Support (Assignment 2).

## Objective

Build an agent that understands employee IT requests, retrieves relevant supplied policies, resolves simple requests, asks for missing information, escalates when necessary, creates structured tickets, cites sources, and maintains an audit trail.

## Tech Stack

- **Python 3.11+** - Core language
- **Streamlit** - Frontend interface
- **OpenAI API** - LLM capabilities for natural language understanding
- **Pydantic** - Structured data validation and LLM output parsing
- **ChromaDB** - Vector database for policy retrieval (RAG)
- **SQLite** - Ticket management and audit logging
- **python-dotenv** - Environment configuration

## Project Structure

- **app/** - Main application code
  - **agent/** - Agent orchestration, classification, decision logic, response generation
  - **rag/** - Policy retrieval and vector store management
  - **database/** - SQLite database and models
  - **policies/** - Policy enforcement engine
  - **ui/** - Streamlit dashboard
- **data/** - Supplied assignment data (policies, requests, tickets)
- **tests/** - Test suite
- **scripts/** - Utility scripts (policy ingestion, etc.)
- **docs/** - Project documentation

## Current Status

Project foundation initialized.

Agent implementation not started yet.

## Important Data Constraint

The supplied assignment material is the source of truth. Unsupported information must not be invented.

## Setup

1. Create a virtual environment: `python -m venv .venv`
2. Activate: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Unix)
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and add your OpenAI API key
5. Run: `streamlit run app/ui/app.py`

## Architecture Principle

The LLM handles natural language understanding and response generation. Deterministic Python logic handles policy enforcement, approval requirements, escalation conditions, and business rules.

Video Link - https://drive.google.com/file/d/1OegtpQSldKiSuD4L1x5-DnWfguM1kDXs/view?usp=sharing
