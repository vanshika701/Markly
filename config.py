import os

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
FUZZY_MATCH_THRESHOLD = int(os.getenv("FUZZY_MATCH_THRESHOLD", "85"))
RELIABILITY_THRESHOLD = int(os.getenv("RELIABILITY_THRESHOLD", "60"))

VALID_LLM_PROVIDERS = {"gemini", "groq", "ollama"}

if LLM_PROVIDER not in VALID_LLM_PROVIDERS:
    raise RuntimeError(
        f"Invalid LLM_PROVIDER '{LLM_PROVIDER}' in .env — must be one of {VALID_LLM_PROVIDERS}"
    )
