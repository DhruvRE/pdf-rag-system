"""
Centralized Configuration Loader Module.
Loads environment variables from .env using python-dotenv and provides
configuration constants for paths, local & cloud model parameters, API endpoints, and credentials.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve root directory of the project
_THIS_DIR = Path(__file__).resolve().parent
_DEFAULT_ROOT = _THIS_DIR.parent

# Load .env file from project root
env_file_path = _DEFAULT_ROOT / ".env"
load_dotenv(dotenv_path=env_file_path, override=False)

# Project Root Directory
PROJECT_ROOT = os.getenv("PROJECT_ROOT", str(_DEFAULT_ROOT))

# Data & Relative Directory Paths
DATA_DIR_NAME = os.getenv("DATA_DIR", "data")
DATA_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, DATA_DIR_NAME))

RAW_PDFS_DIR_NAME = os.getenv("RAW_PDFS_DIR", "data/raw_pdfs")
RAW_PDFS_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, RAW_PDFS_DIR_NAME))

PARSED_DIR_NAME = os.getenv("PARSED_DIR", "data/parsed")
PARSED_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, PARSED_DIR_NAME))

VECTOR_STORE_DIR_NAME = os.getenv("VECTOR_STORE_DIR", "data/vector_store")
VECTOR_STORE_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, VECTOR_STORE_DIR_NAME))

VECTOR_DB_NAME = os.getenv("VECTOR_DB_NAME", "vector_index.db")
VECTOR_DB_PATH = os.path.join(VECTOR_STORE_DIR, VECTOR_DB_NAME)

CONTEXT_FILE_NAME = os.getenv("CONTEXT_FILE", ".agent/context.json")
CONTEXT_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, CONTEXT_FILE_NAME))

WEB_DIR_NAME = os.getenv("WEB_DIR", "web")
WEB_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, WEB_DIR_NAME))

# ------------------------------------------------------------------------------
# LLM Model Provider Selection (local | cloud)
# ------------------------------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local").lower()
CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "google").lower()

# Local LLM Configuration (Ollama)
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "qwen3.5:latest")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

# Cloud LLM Credentials (Google Gemini & Mistral)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_MODEL_NAME = os.getenv("MISTRAL_MODEL_NAME", "mistral-small-latest")

# Embedding Configuration
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

# API Server Settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "dev_secret_key_change_in_prod")

# Deduplication & Retrieval Thresholds
DEDUP_SIMILARITY_THRESHOLD = float(os.getenv("DEDUP_SIMILARITY_THRESHOLD", "0.85"))
DEFAULT_SEARCH_TOP_K = int(os.getenv("DEFAULT_SEARCH_TOP_K", "5"))
