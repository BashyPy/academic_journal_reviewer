from abc import ABC, abstractmethod

from app.core.config import settings
from app.services.cache_service import cache_service


class LLMProvider(ABC):
    @abstractmethod
    async def generate_content(self, prompt: str) -> str:
        pass


class GroqProvider(LLMProvider):
    def __init__(self):
        from groq import AsyncGroq

        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.primary_model = "llama-3.3-70b-versatile"
        self.fallback_model = "llama3-8b-8192"

    async def generate_content(self, prompt: str) -> str:
        # Truncate prompt to stay within Groq's token limits
        # Groq llama-3.3-70b-versatile has 12k token limit
        max_chars = 30000  # ~7.5k tokens, leaving room for response
        if len(prompt) > max_chars:
            prompt = prompt[:max_chars] + "\n\n[Content truncated due to token limits]"

        try:
            # Try the larger model first
            response = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=4000,
            )
        except Exception as e:
            if "rate_limit_exceeded" in str(e) or "413" in str(e):
                # Fallback to smaller model with further truncated prompt
                if len(prompt) > 20000:
                    prompt = prompt[:20000] + "\n\n[Content further truncated for smaller model]"

                response = await self.client.chat.completions.create(
                    model="llama3-8b-8192",  # Smaller model with better token limits
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=3000,
                )
            else:
                raise e
        return response.choices[0].message.content


class OpenAIProvider(LLMProvider):
    def __init__(self):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_content(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return response.choices[0].message.content


class GeminiProvider(LLMProvider):
    def __init__(self):
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    async def generate_content(self, prompt: str) -> str:
        response = await self.model.generate_content_async(prompt)
        return response.text


class LLMService:
    def __init__(self):
        self.providers = {
            "groq": GroqProvider,
            "openai": OpenAIProvider,
            "gemini": GeminiProvider,
        }
        self.default_provider = settings.DEFAULT_LLM

    def get_provider(self, provider_name: str = None) -> LLMProvider:
        provider_name = provider_name or self.default_provider
        if provider_name not in self.providers:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")
        return self.providers[provider_name]()

    def call_llm(self, prompt: str, provider: str = None) -> str:
        """Synchronous wrapper for LLM calls (for test compatibility)."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.generate_content(prompt, provider))

    async def generate_content(self, prompt: str, provider: str = None) -> str:
        provider = provider or self.default_provider

        # Check cache first
        cached_response = await cache_service.get(prompt, provider)
        if cached_response:
            return cached_response

        # Generate new response
        llm_provider = self.get_provider(provider)
        response = await llm_provider.generate_content(prompt)

        # Cache the response
        await cache_service.set(prompt, provider, response)

        return response


llm_service = LLMService()
