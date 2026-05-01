"""
Configuration module — reads secrets from env vars, defines constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

# ── API Keys (never hardcoded) ──────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Paths ───────────────────────────────────────────────────────────────
DATA_DIR = _project_root / "data"
SUPPORT_TICKETS_DIR = _project_root / "support_tickets"
INPUT_CSV = SUPPORT_TICKETS_DIR / "support_tickets.csv"
SAMPLE_CSV = SUPPORT_TICKETS_DIR / "sample_support_tickets.csv"
OUTPUT_CSV = SUPPORT_TICKETS_DIR / "output.csv"

# ── Corpus domains ──────────────────────────────────────────────────────
DOMAINS = ["hackerrank", "claude", "visa"]

# ── Retrieval settings ──────────────────────────────────────────────────
CHUNK_SIZE = 500          # tokens per chunk
CHUNK_OVERLAP = 50        # overlap tokens between chunks
TOP_K_RETRIEVAL = 10      # candidates from semantic search
TOP_K_CONTEXT = 5         # docs passed to LLM after re-ranking

# ── LLM settings ────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # "gemini" or "openai"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = 0.1     # low temp for deterministic output
LLM_SEED = 42             # seed for reproducibility

# ── ChromaDB ────────────────────────────────────────────────────────────
CHROMA_COLLECTION = "support_corpus"
