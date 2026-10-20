"""All settings in one place. Change values here, not inside the code."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"            # your documents (.pdf, .docx, .md, .txt)
INDEX_DIR = BASE_DIR / "index"          # generated search index
# Downloaded search models. On Vercel the project folder is read-only and size-limited, so the
# model is downloaded to /tmp when the app starts instead of being bundled with the code.
ON_VERCEL = bool(os.getenv("VERCEL"))
MODEL_DIR = Path("/tmp/fastembed_models") if ON_VERCEL else BASE_DIR / "models"
LOG_DIR = BASE_DIR / "logs"             # question log
PROMPT_FILE = BASE_DIR / "prompts" / "system_prompt.txt"

# ── Owner info (shown in the website and used in fallback replies) ──────
OWNER_NAME = "M Faizan"
OWNER_FIRST_NAME = "Faizan"
OWNER_ROLE = "AI Engineer at Business Analytics, Islamabad"
OWNER_LINKS = {
    "LinkedIn": "https://www.linkedin.com/in/muhammad-faizan-a28882278",
    "GitHub": "https://github.com/fazich21",
}
CONTACT_HINT = "by email or on LinkedIn (linkedin.com/in/muhammad-faizan-a28882278)"
# Shown as tiles on the welcome screen (phones show the first 4). "topic" is the small label.
SUGGESTED_QUESTIONS = [
    {"topic": "Life", "question": "What are his interests?"},
    {"topic": "Projects", "question": "Tell me about the multilingual RAG system"},
    {"topic": "Work", "question": "What does he do at Business Analytics?"},
    {"topic": "Skills", "question": "What are his strongest skills?"},
    {"topic": "Mobile apps", "question": "Which Flutter apps has he built?"},
    {"topic": "Contact", "question": "How can I reach him?"},
]
# Words visitors use for the owner in questions; rewritten to "I/my" before searching,
# because the documents are written in the first person.
OWNER_ALIASES = ["muhammad faizan", "m faizan", "faizan"]

# ── LLM (Groq) ───────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "low")  # gpt-oss models only; "" to disable
TEMPERATURE = 0.4
MAX_TOKENS = 1200

# ── Models for search ────────────────────────────────────────────────────
EMBED_MODEL = "BAAI/bge-small-en-v1.5"  # small, fast, 512-token window, runs on free CPU
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
USE_RERANKER = os.getenv("USE_RERANKER", "true").lower() == "true"
MODEL_THREADS = int(os.getenv("MODEL_THREADS", "0")) or None   # None = use all CPU cores
RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"  # reads question + chunk together (~80 MB)
RERANK_MIN_SCORE = 0.01   # 0..1 relevance; chunks below this are dropped...
RERANK_MIN_KEEP = 3       # ...but the best few are always kept

# ── Chunking ─────────────────────────────────────────────────────────────
MAX_CHUNK_CHARS = 1200   # sections longer than this are split on paragraphs/sentences
MIN_CHUNK_CHARS = 40     # tiny leftovers are dropped

# ── Retrieval ────────────────────────────────────────────────────────────
CANDIDATES = 20          # chunks found by hybrid search, then re-ranked
TOP_K = 7                # best chunks sent to the LLM per question
MIN_DENSE_SCORE = 0.35   # without reranker: below this (and no keyword match) = irrelevant
RRF_K = 60               # reciprocal-rank-fusion constant for hybrid search

# ── Conversation ─────────────────────────────────────────────────────────
HISTORY_TURNS = 4        # past question/answer pairs sent for follow-up questions

# ── Guard rails ──────────────────────────────────────────────────────────
MAX_QUESTION_CHARS = 500
MAX_HISTORY_MESSAGE_CHARS = 4000
RATE_LIMIT_MESSAGES = 10          # per visitor...
RATE_LIMIT_WINDOW_SECONDS = 60    # ...per this many seconds

# ── Web server ───────────────────────────────────────────────────────────
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"   # built React app served by FastAPI
CORS_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o]
PORT = int(os.getenv("PORT", "7860"))

# ── Logging ──────────────────────────────────────────────────────────────
LOG_QUESTIONS = os.getenv("LOG_QUESTIONS", "true").lower() == "true"
