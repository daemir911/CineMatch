"""
Configuration settings for the Movie Recommendation System.
Centralizes all file paths, ML hyper-parameters, TMDB API settings, and server configs.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure network utilities and DNS patch are active
try:
    import network_utils
except ImportError:
    pass

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

# Directories
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "model"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
NOTEBOOK_DIR = BASE_DIR / "notebook"
SCRIPTS_DIR = BASE_DIR / "scripts"

# Dataset Files (expected inside data/)
TMDB_MOVIES_CSV = DATA_DIR / "tmdb_5000_movies.csv"
TMDB_CREDITS_CSV = DATA_DIR / "tmdb_5000_credits.csv"
TMDB_10K_CSV = DATA_DIR / "tmdb_10k_movies.csv"
BOLLYWOOD_CSV = DATA_DIR / "bollywood_movies.csv"
CATALOG_CSV = DATA_DIR / "movies_catalog.csv"
RATINGS_CSV = DATA_DIR / "ratings.csv"
LINKS_CSV = DATA_DIR / "links.csv"

# Saved Model Artifacts (inside model/)
MOVIES_PKL = MODEL_DIR / "movies.pkl"
CONTENT_SIM_PKL = MODEL_DIR / "content_sim.pkl"
COLLAB_SIM_PKL = MODEL_DIR / "collab_sim.pkl"
VECTORIZER_PKL = MODEL_DIR / "vectorizer.pkl"
VECTORS_PKL = MODEL_DIR / "vectors.pkl"
COLLAB_FACTORS_PKL = MODEL_DIR / "collab_factors.pkl"

# Recommender Parameters
DEFAULT_ALPHA = 0.6  # Default weight for content similarity (1 - alpha for collaborative similarity)
DEFAULT_RECOMMEND_COUNT = 12
MAX_FEATURES = 6000  # Vocabulary size for Content-based Vectorizer
SVD_FACTORS = 20    # Number of latent dimensions for collaborative SVD
RANDOM_STATE = 42

# TMDB API Settings
# If the user provides TMDB_API_KEY in .env, it takes highest precedence.
# Otherwise, we use a reliable fallback key so features work seamlessly out of the box.
_ENV_KEY = os.getenv("TMDB_API_KEY", "").strip()
DEFAULT_DEMO_KEY = "8265bd1679663a7ea12ac168da84d2e8"
TMDB_API_KEY = _ENV_KEY if _ENV_KEY and _ENV_KEY != "your_tmdb_api_key_here" else DEFAULT_DEMO_KEY

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_TIMEOUT_SECONDS = 3.5  # Responsive timeout
TMDB_MAX_WORKERS = 8       # ThreadPoolExecutor parallel poster fetching
PLACEHOLDER_IMAGE_URL = "/static/images/poster_placeholder.svg"

# Server Settings
HOST = "127.0.0.1"
PORT = 5000
DEBUG = True
