"""Complete LLM service tests with proper mocking"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.llm_service import llm_service, GroqProvider, OpenAIProvider, GeminiProvider


@pytest.mark.asyncio
async def test_groq_provider_generate_content():
    """Test Groq provider content generation"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test response"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch('app.services.llm_service.AsyncGroq', return_value=mock_client):
        provider = GroqProvider()
        result = await provider.generate_content("Test prompt")
        assert result == "Test response"


@pytest.mark.asyncio
async def test_groq_provider_handles_rate_limit():
    """Test Groq provider handles rate limits with fallback"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Fallback response"))]

    # First call fails with rate limit, second succeeds
    mock_client.chat.completions.create = AsyncMock(
        side_effect=[Exception("rate_limit_exceeded"), mock_response]
    )

    with patch('app.services.llm_service.AsyncGroq', return_value=mock_client):
        provider = GroqProvider()
        result = await provider.generate_content("Test prompt")
        assert result == "Fallback response"


@pytest.mark.asyncio
async def test_openai_provider_generate_content():
    """Test OpenAI provider content generation"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="OpenAI response"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch('app.services.llm_service.AsyncOpenAI', return_value=mock_client):
        provider = OpenAIProvider()
        result = await provider.generate_content("Test prompt")
        assert result == "OpenAI response"


@pytest.mark.asyncio
async def test_gemini_provider_generate_content():
    """Test Gemini provider content generation"""
    mock_model = Mock()
    mock_response = Mock(text="Gemini response")
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)

    with patch('app.services.llm_service.genai.GenerativeModel', return_value=mock_model):
        provider = GeminiProvider()
        result = await provider.generate_content("Test prompt")
        assert result == "Gemini response"


@pytest.mark.asyncio
async def test_llm_service_get_provider():
    """Test LLM service provider selection"""
    with patch('app.services.llm_service.settings') as mock_settings:
        mock_settings.DEFAULT_LLM = "groq"
        mock_settings.GROQ_API_KEY = "test_key"

        provider = llm_service.get_provider("groq")
        assert isinstance(provider, GroqProvider)


@pytest.mark.asyncio
async def test_llm_service_invalid_provider():
    """Test LLM service handles invalid provider"""
    with pytest.raises(ValueError):
        llm_service.get_provider("invalid_provider")


@pytest.mark.asyncio
async def test_llm_service_generate_content_with_cache():
    """Test LLM service uses cache"""
    with patch('app.services.llm_service.cache_service') as mock_cache, \
         patch('app.services.llm_service.settings') as mock_settings:

        mock_settings.DEFAULT_LLM = "groq"
        mock_cache.get = AsyncMock(return_value="Cached response")

        result = await llm_service.generate_content("Test prompt")
        assert result == "Cached response"


@pytest.mark.asyncio
async def test_llm_service_generate_content_no_cache():
    """Test LLM service generates new content when cache miss"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="New response"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch('app.services.llm_service.cache_service') as mock_cache, \
         patch('app.services.llm_service.settings') as mock_settings, \
         patch('app.services.llm_service.AsyncGroq', return_value=mock_client):

        mock_settings.DEFAULT_LLM = "groq"
        mock_settings.GROQ_API_KEY = "test_key"
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        result = await llm_service.generate_content("Test prompt")
        assert result == "New response"
        mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_llm_service_call_llm_sync():
    """Test synchronous LLM call wrapper"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Sync response"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch('app.services.llm_service.cache_service') as mock_cache, \
         patch('app.services.llm_service.settings') as mock_settings, \
         patch('app.services.llm_service.AsyncGroq', return_value=mock_client):

        mock_settings.DEFAULT_LLM = "groq"
        mock_settings.GROQ_API_KEY = "test_key"
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()

        result = llm_service.call_llm("Test prompt")
        assert result == "Sync response"


@pytest.mark.asyncio
async def test_groq_provider_truncates_long_prompts():
    """Test Groq provider truncates long prompts"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Truncated response"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch('app.services.llm_service.AsyncGroq', return_value=mock_client):
        provider = GroqProvider()
        long_prompt = "x" * 50000  # Exceeds max_chars
        result = await provider.generate_content(long_prompt)
        assert result == "Truncated response"

        # Verify truncation happened
        call_args = mock_client.chat.completions.create.call_args
        actual_prompt = call_args[1]['messages'][0]['content']
        assert len(actual_prompt) <= 30100  # max_chars + truncation message
