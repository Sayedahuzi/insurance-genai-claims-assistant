from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
# Load local secrets from .env; existing environment variables take precedence.
load_dotenv(ROOT / ".env", override=False)

DATA_ZIP = Path(os.getenv("INSURANCE_DATA_ZIP", ROOT / "data.zip"))
DB_PATH = Path(os.getenv("INSURANCE_DB_PATH", ROOT / "data" / "insurance.db"))
# OpenRouter exposes an OpenAI-compatible chat-completions endpoint.
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
# Backwards-compatible aliases for the existing assistant module.
OPENAI_API_KEY = OPENROUTER_API_KEY
OPENAI_BASE_URL = OPENROUTER_BASE_URL
OPENAI_MODEL = OPENROUTER_MODEL
