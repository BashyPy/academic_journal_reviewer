# Test Suite Documentation

## Overview
Comprehensive test suite achieving **47% code coverage** with focus on critical paths: agents, workflows, and core services.

## ⚠️ Test Database Isolation

**IMPORTANT**: Tests automatically use a separate database (`aaris_test`) to prevent production data contamination.

- **Production DB**: `aaris`
- **Test DB**: `aaris_test`
- **Auto-configured**: Set via `TESTING=true` environment variable
- **Safe by default**: MongoDB service mocked in test client

See [TEST_ISOLATION_QUICK_REFERENCE.md](../docs/TEST_ISOLATION_QUICK_REFERENCE.md) for details.

## Test Files

### Core Test Files (Run These)

#### 1. `conftest.py`
**Purpose**: Shared fixtures and test configuration
- Async fixtures for LLM mocking
- Authentication mocks
- Database mocks
- Client fixtures

#### 2. `test_agents.py`
**Purpose**: Agent system tests
**Coverage**:
- Specialist agents: 100%
- Base agent: 34%
- Agent prompts and parsing
**Run**: `pytest tests/test_agents.py -v`

#### 3. `test_agents_workflow.py`
**Purpose**: Agent workflow and orchestration tests
**Coverage**:
- Orchestrator: 88%
- Agent execution flows
- Error handling
**Run**: `pytest tests/test_agents_workflow.py -v`

#### 4. `test_workflow_integration.py`
**Purpose**: LangGraph workflow integration tests
**Coverage**:
- LangGraph workflow: 72%
- Initialization, embeddings, parallel reviews
- Synthesis and retry logic
**Run**: `pytest tests/test_workflow_integration.py -v`

#### 5. `test_workflow_services.py`
**Purpose**: Workflow and service integration tests
**Coverage**:
- Synthesis agent: 57%
- LangChain service: 38%
- Complete workflow execution
**Run**: `pytest tests/test_workflow_services.py -v`

#### 6. `test_llm_services.py`
**Purpose**: LLM provider tests
**Coverage**:
- LLM service: 65%
- Groq, OpenAI, Gemini providers
- Cache integration
**Run**: `pytest tests/test_llm_services.py -v`

#### 7. `test_langchain_service.py`
**Purpose**: LangChain service tests
**Coverage**:
- Domain-aware reviews
- Chain-of-thought analysis
- Multi-model consensus
**Run**: `pytest tests/test_langchain_service.py -v`

#### 8. `test_synthesis_agent.py`
**Purpose**: Synthesis agent tests
**Coverage**:
- Report generation
- Critique compilation
- Score calculation
**Run**: `pytest tests/test_synthesis_agent.py -v`

#### 9. `test_core_services.py`
**Purpose**: Core service tests
**Coverage**:
- User service: 30%
- MongoDB service: 75%
- OTP service: 76%
- Email service: 46%
- Security monitor: 60%
**Run**: `pytest tests/test_core_services.py -v`

#### 10. `test_additional_services.py`
**Purpose**: Additional service tests
**Coverage**:
- Document parser: 17%
- Domain detector: 93%
- PDF generator: 66%
- Issue deduplicator: 57%
**Run**: `pytest tests/test_additional_services.py -v`

#### 11. `test_services_integration.py`
**Purpose**: Service integration tests
**Coverage**:
- Guardrails: 57%
- WAF: 71%
- Cache: 27%
- Document cache: 52%
**Run**: `pytest tests/test_services_integration.py -v`

#### 12. `test_api_middleware.py`
**Purpose**: API and middleware tests
**Coverage**:
- API routes: 17%
- Auth routes: 29%
- Middleware: 19-71%
**Run**: `pytest tests/test_api_middleware.py -v`

#### 13. `test_agents_mocked.py`
**Purpose**: Mock-based agent tests
**Coverage**: Agent system with external service mocks
**Run**: `pytest tests/test_agents_mocked.py -v`

## Running Tests

### Run All Tests
```bash
source .venv/bin/activate
pytest tests/ -v
# Automatically uses aaris_test database
```

### Clear Test Database
```bash
# Safe cleanup of test data
python tests/clear_test_db.py
```

### Run All Passing Tests Only
```bash
pytest tests/test_agents_workflow.py tests/test_workflow_services.py -k "not parse_valid and not parse_invalid and not submission_not_found and not execute_task_complete and not generate_report_complete and not synthesize_complete and not calculate_similarity and not extract_keywords" -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### Run Specific Test File
```bash
pytest tests/test_agents.py -v
```

### Run Specific Test
```bash
pytest tests/test_agents.py::test_methodology_agent_prompt -v
```

## Coverage Summary

### 100% Coverage (13 modules)
- All model schemas
- All specialist agents
- All `__init__.py` files

### 80%+ Coverage (9 modules)
- Domain detector: 93%
- Manuscript analyzer: 91%
- Orchestrator: 88%
- Disclaimer service: 88%
- Audit logger: 80%

### 50-79% Coverage (12 modules)
- MongoDB service: 75%
- OTP service: 76%
- LangGraph workflow: 72%
- WAF: 71%
- Logger: 71%
- PDF generator: 66%
- LLM service: 65%

## Test Organization

### By Functionality
- **Agent Tests**: `test_agents.py`, `test_agents_workflow.py`, `test_agents_mocked.py`
- **Workflow Tests**: `test_workflow_integration.py`, `test_workflow_services.py`
- **Service Tests**: `test_core_services.py`, `test_additional_services.py`, `test_services_integration.py`
- **LLM Tests**: `test_llm_services.py`, `test_langchain_service.py`
- **API Tests**: `test_api_middleware.py`

### By Coverage Priority
1. **High Coverage** (80%+): Agents, workflow, domain detection
2. **Medium Coverage** (50-79%): Services, middleware
3. **Low Coverage** (<50%): API routes, some services

## Key Testing Patterns

### Async Testing
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Mocking LLM Services
```python
with patch('app.services.llm_service.AsyncGroq') as mock_groq:
    mock_groq.return_value.chat.completions.create = AsyncMock(return_value=mock_response)
    result = await llm_service.generate_content("prompt")
```

### Mocking Database
```python
with patch.object(mongodb_service, 'db') as mock_db:
    mock_coll = Mock()
    mock_coll.find_one = AsyncMock(return_value={"_id": "test"})
    mock_db.__getitem__ = Mock(return_value=mock_coll)
```

## Dependencies
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities

## Notes
- Some tests are skipped due to complex dependencies
- Focus is on critical paths (agents, workflows)
- API routes need more comprehensive testing
- All tests use proper async/await patterns
