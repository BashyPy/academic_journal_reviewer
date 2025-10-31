# LangGraph and LangChain Migration Guide

## Overview

The Academic Agentic Review Intelligence System (AARIS) has been successfully updated to use LangGraph and LangChain implementations instead of the previous custom agent system. This migration provides better orchestration, improved reliability, and enhanced AI capabilities.

## Key Changes Made

### 1. Dependencies Updated

**File**: `requirements.txt`
- Added LangChain ecosystem packages:
  - `langchain`
  - `langchain-openai`
  - `langchain-anthropic`
  - `langchain-google-genai`
  - `langchain-groq`
  - `langchain-community`
  - `langchain-core`
  - `langgraph`
  - `langsmith`

### 2. Configuration Enhanced

**File**: `app/core/config.py`
- Added `ANTHROPIC_API_KEY` configuration for Claude models

### 3. LangGraph Workflow Implementation

**File**: `app/services/langgraph_workflow.py`
- Implemented `EnhancedLangGraphWorkflow` class
- Uses StateGraph for orchestrating review process
- Parallel execution of specialist agents (methodology, literature, clarity, ethics)
- Integrated with existing domain detection and issue deduplication
- Memory management with MemorySaver

### 4. LangChain Service Integration

**File**: `app/services/langchain_service.py`
- Multi-LLM support (OpenAI, Anthropic, Google Gemini, Groq)
- Retrieval-Augmented Generation (RAG) capabilities
- Domain-aware review prompts
- Chain-of-thought analysis
- Multi-model consensus for critical decisions
- Vector embeddings for semantic search

### 5. Orchestrator Simplification

**File**: `app/agents/orchestrator.py`
- Removed complex agent task management
- Simplified to use only LangGraph workflow
- Improved error handling and logging
- Maintains document caching functionality

## Architecture Benefits

### Before (Custom Agents)
```
Orchestrator → Individual Agents → Task Management → Synthesis
```

### After (LangGraph + LangChain)
```
Orchestrator → LangGraph Workflow → Parallel LangChain Agents → Synthesis
```

## New Capabilities

1. **Parallel Processing**: All specialist agents run concurrently
2. **RAG Integration**: Semantic search and context retrieval
3. **Multi-Model Consensus**: Critical decisions use multiple AI models
4. **Chain-of-Thought**: Step-by-step reasoning for complex analysis
5. **Memory Management**: Conversation context and state persistence
6. **Domain Awareness**: Specialized prompts for different academic fields

## Workflow Process

1. **Initialize**: Detect domain and set up context
2. **Create Embeddings**: Generate vector embeddings for RAG
3. **Parallel Reviews**: Execute all specialist agents simultaneously
   - Methodology Agent (domain-aware review)
   - Literature Agent (domain-aware review)
   - Clarity Agent (chain-of-thought analysis)
   - Ethics Agent (multi-model consensus)
4. **Synthesize**: Compile final report with issue deduplication

## Testing

A test script has been provided to verify the integration:

```bash
python test_langgraph_integration.py
```

This script:
- Tests the complete LangGraph workflow
- Uses sample academic content
- Verifies all components work together
- Provides detailed output and error reporting

## Migration Impact

### Maintained Features
- ✅ Document upload and parsing
- ✅ Domain detection
- ✅ Issue deduplication
- ✅ PDF report generation
- ✅ Document caching
- ✅ API endpoints and responses
- ✅ Logging and monitoring

### Enhanced Features
- 🚀 Faster parallel processing
- 🧠 Improved AI reasoning with chain-of-thought
- 🔍 Better context understanding with RAG
- 🎯 More accurate reviews with multi-model consensus
- 📚 Domain-specific expertise
- 💾 Better memory management

### Removed Components
- ❌ Individual agent task tracking (replaced by LangGraph state)
- ❌ Custom agent orchestration (replaced by LangGraph workflow)
- ❌ Manual task polling (replaced by workflow execution)

## Environment Setup

Ensure your `.env` file includes all required API keys:

```env
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=aaris

# LLM API Keys (configure at least one)
DEFAULT_LLM=openai
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here

# Application
APP_ID=aaris-app
```

## Next Steps

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Tests**:
   ```bash
   python test_langgraph_integration.py
   ```

3. **Start Application**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Verify API**:
   - Visit http://localhost:8000/docs for interactive API documentation
   - Test manuscript upload and review process

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Ensure all required LLM API keys are configured
2. **MongoDB Connection**: Verify MongoDB is running and accessible
3. **Import Errors**: Run `pip install -r requirements.txt` to install new dependencies
4. **Memory Issues**: LangGraph uses memory checkpointing; ensure sufficient RAM

### Performance Optimization

- Configure `DEFAULT_LLM` to your preferred/fastest provider
- Use MongoDB Atlas for better vector search performance
- Consider GPU acceleration for local embeddings

## Conclusion

The migration to LangGraph and LangChain provides a more robust, scalable, and intelligent academic review system. The new architecture maintains all existing functionality while adding advanced AI capabilities and improved performance through parallel processing.