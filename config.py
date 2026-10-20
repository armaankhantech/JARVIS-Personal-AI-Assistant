import os

from dotenv import load_dotenv


# Load variables from .env
load_dotenv()


# =========================
# API KEYS
# =========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


# =========================
# MODEL NAMES
# =========================

GROQ_MODEL = "openai/gpt-oss-120b"


GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_VISION_MODEL = "gemini-3.8-flash"

OPENROUTER_MODEL = "openrouter/free"

OLLAMA_VISION_MODEL = "qwen3-vl:4b"
OLLAMA_MODEL = "llama3.2:3b"

# =========================
# JARVIS WORKSPACE
# =========================

from pathlib import Path

WORKSPACE_ROOT = Path(
    os.getenv("JARVIS_WORKSPACE", r"D:\Jarvis")
).resolve()

FILES_DIR = WORKSPACE_ROOT / "Files"
NOTES_DIR = WORKSPACE_ROOT / "Notes"
PROJECTS_DIR = WORKSPACE_ROOT / "Projects"
TEMP_DIR = WORKSPACE_ROOT / "Temp"