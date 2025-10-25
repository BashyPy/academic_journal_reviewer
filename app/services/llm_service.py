from abc import ABC, abstractmethod

from app.core.config import settings


class LLMProvider(ABC):
    @abstractmethod
    async def generate_content(self, prompt: str) -> str:
        pass


class GroqProvider(LLMProvider):
    def __init__(self):
        from groq import AsyncGroq

        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def generate_content(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
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

    async def generate_content(self, prompt: str, provider: str = None) -> str:
        llm_provider = self.get_provider(provider)
        return await llm_provider.generate_content(prompt)


llm_service = LLMService()
