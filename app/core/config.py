import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "aaris")

    DEFAULT_LLM = os.getenv("DEFAULT_LLM", "groq")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    APP_ID = os.getenv("APP_ID", "default-app-id")


settings = Settings()
