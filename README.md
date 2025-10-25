# Academic Journal Reviewer (AARIS)

An Agentic AI system for academic journal/paper review using multi-agent architecture.

## Architecture

- **Frontend**: React-based UI for manuscript upload and review display
- **Backend**: FastAPI with agent orchestration
- **Database**: Firebase Firestore for state management
- **Agents**: Specialized LLM agents for different review aspects

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Configure Firebase credentials
3. Set up environment variables
4. Run: `uvicorn app.main:app --reload`

## Components

- **Orchestrator Agent**: Plans and coordinates review process
- **Specialist Agents**: Methodology, Literature, Clarity, Ethics
- **Synthesis Agent**: Compiles final review report