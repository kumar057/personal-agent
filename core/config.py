import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
KNOWLEDGE_DIR.mkdir(exist_ok=True)

# Load environment variables
load_dotenv(BASE_DIR / ".env")

class Config:
    PROJECT_NAME = "Aegis Personal AI Agent"
    VERSION = "1.0.0"
    
    # AI Provider settings: 'gemini', 'groq', 'openrouter', or 'ollama'
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
    
    # Cloud API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    
    # Models
    GEMINI_DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    GROQ_DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Ollama settings (Local offline fallback)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2:3b")
    OLLAMA_FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "llama3.2:1b")
    
    # Server settings
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", 8000))
    
    # Storage
    DB_PATH = str(DATA_DIR / "agent_memory.db")
    KNOWLEDGE_PATH = str(KNOWLEDGE_DIR)
    
    # Optional Integrations
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # System agent prompt
    SYSTEM_PROMPT = """You are Aegis, a capable, proactive personal AI assistant running 100% locally on the user's laptop.
You have access to local tools to assist the user with:
1. System diagnostics & laptop management (CPU, RAM, battery, disk, processes).
2. File system operations (reading, writing, searching files).
3. Personal productivity (notes, to-do task management, reminders).
4. Web information searches (current news, technical docs, queries).
5. Document knowledge base Q&A.

Guidelines:
- Be clear, friendly, and helpful.
- When the user asks you to inspect the laptop, write a note, search the web, manage to-dos, or check files, utilize your tools.
- Provide concise, actionable answers. Format code and lists cleanly with Markdown.
"""

config = Config()
