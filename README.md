# CineMatch: Universal AI Hybrid Movie Recommender System

A modern, full-stack movie recommendation platform powered by a **Dual-Engine Machine Learning Recommender** that dynamically unifies **Content-Based Filtering** (plot tags, keywords, cast, and director metadata) with **Collaborative Filtering** (MovieLens SVD latent matrix factorization).

Runs locally at **`http://localhost:5000`** with a modern **Netflix / Letterboxd-style dark interface**, featuring **13,906 movies**, guaranteed posters for **100% of films**, fuzzy typo-tolerant autocomplete, interactive catalog filtering, and on-the-fly universal vectorization.

---

## What's New: The Major Upgrade

### 1. Expanded Movie Catalog (13,906 Movies)
- **Massive Coverage**: Expanded from 4,803 to **13,906 unique films**, spanning all release eras (from early cinema classics through 2026 releases).
- **Multi-Source Data Fusion**: Cleans and merges TMDB 5,000, Extended TMDB 10,000+, modern 2016–2025/2026 blockbusters (*Oppenheimer, Barbie, Dune 1 & 2, Spider-Verse, Everything Everywhere All at Once, Avatar 2, Top Gun: Maverick, etc.*), curated international/Bollywood cinema, and MovieLens collaborative ratings.
- **Harmonized Schema**: Standardized columns (`tmdb_id`, `title`, `year`, `genres`, `overview`, `cast`, `director`, `keywords`, `rating`, `vote_count`, `popularity`, `poster_url`, `backdrop_url`, `language`, `has_collab`).
- **Catalog Update Pipeline**: Dedicated script `scripts/update_catalog.py` to seamlessly pull future releases from TMDB API and trigger automatic model retraining.

### 2. Posters for EVERY Movie (100% Guaranteed)
- **3-Tier Fallback Architecture**:
  1. **Tier 1 (TMDB High-Res Poster)**: Pre-cached URLs looked up via `tmdb_id` or `title` + `year`.
  2. **Tier 2 (Alternate Source)**: High-resolution Wikimedia / OMDb thumbnails.
  3. **Tier 3 (Dynamic High-Res SVG Placeholders)**: Beautiful, branded dark-themed SVG posters dynamically rendering the movie title, release year, and genre badge.
- **Pre-Cached Dataset**: Poster URLs are cached inside `data/movies_catalog.csv`, `model/movies.pkl`, and `data/poster_cache.json`.
- **Zero Broken Images**: Frontend `onerror` image handlers automatically fall back to `/api/placeholder?title=...`.
- **Verification Script (`scripts/verify_posters.py`)**:
  - Total catalog movies: **13,906**
  - Movies with real posters: **13,762 (99.0%)**
  - Movies on clean fallback: **144 (1.0%)**
  - Broken / missing posters: **0 (0.0%)**

### 3. Complete UI/UX Redesign (Netflix / Letterboxd Style)
- **Modern Dark Theme**: Deep obsidian surfaces (`#0b0e14`, `#161d2d`), vibrant crimson/gold gradients, frosted glass navigation (`backdrop-filter: blur(20px)`), and fluid card elevations.
- **Typo-Tolerant Fuzzy Search**: Prominent search bar with instant fuzzy matching (`difflib`) so typos like *"dark nite"*, *"interstelar"*, *"avaters"*, or *"shawshank"* instantly match the right movie.
- **Recommendation Showcase ("Because You Liked X")**: Hero banner of the seed movie, toggleable between **Horizontal Scrolling Row (Carousel)** and **Multi-Column Grid**, accompanied by intelligent *"Why Recommended"* explanation chips.
- **Interactive Movie Detail Modal**: High-res poster, backdrop image banner, plot overview, director, top cast chips, clickable genres, rating badge, and an integrated **"More Like This"** carousel.
- **Catalog Filtering & Sorting**: Filter by Genre pills (Action, Sci-Fi, Drama, Comedy, Horror, Romance, etc.), Era dropdown (2020s, 2010s, 2000s, 90s, Classics), Minimum Rating (8.0+, 7.0+, 6.0+), and Sort By (Popularity, Top Rated, Newest, Oldest, Title A-Z).
- **Performance & UX**: Native lazy loading (`loading="lazy"`), animated skeleton shimmers, keyboard shortcuts (`/` to search, `Esc` to close modal, Arrow keys in search dropdown).

---

## Architecture Overview

```text
                           +-------------------------------------------+
                           |               User Browser                |
                           |   (HTML5, Modern CSS, Modular Vanilla JS) |
                           +---------------------+---------------------+
                                                 |
                                                 v
                           +-------------------------------------------+
                           |           Flask Backend Server            |
                           |             (localhost:5000)              |
                           +----+--------------------+---------------+
                                |                    |               |
              +-----------------+                    |               +-----------------+
              v                                      v                                 v
   +----------------------+        +-----------------------------------+     +--------------------+
   |  Model Artifacts     |        |          Poster Service           |     |     TMDB API       |
   |  (Loaded into RAM)   |        |  (3-Tier Fallback Hierarchy:      |     |  (Edge CloudFront  |
   | - movies.pkl         |        |   TMDB -> Alt Source -> Dynamic   |     |   DNS Resolver     |
   | - vectors.pkl        |        |   SVG Title Placeholders)         |     |   + Rate-Limiter)  |
   | - collab_factors.pkl |        +-----------------------------------+     +--------------------+
   | - content_sim.pkl    |
   | - collab_sim.pkl     |
   | - vectorizer.pkl     |
   +----------------------+
              |
              v
   +-------------------------------------------------------------------+
   |                      Dynamic Hybrid Formula                       |
   |   score = alpha * content_score + (1.0 - alpha) * collab_score    |
   |   - Interactive slider: alpha in [0.0, 1.0] (Default = 0.6)       |
   |   - Fast sub-5ms cosine vector dot-product scoring                |
   |   - Cold-start safe fallback                                      |
   +-------------------------------------------------------------------+
```

---

## Project Structure

```text
movie/
├── data/
│   ├── movies_catalog.csv             # Full expanded 13,906 movie catalog
│   ├── poster_cache.json              # Persistent poster URL cache
│   ├── tmdb_5000_movies.csv           # Original TMDB 5k movies
│   ├── tmdb_5000_credits.csv          # Original TMDB 5k credits
│   ├── tmdb_10k_movies.csv            # Extended 10,866 TMDB dataset
│   ├── bollywood_movies.csv           # Curated international/Bollywood films
│   ├── ratings.csv                    # MovieLens ratings (100,000+ ratings)
│   └── links.csv                      # MovieLens to TMDB ID cross-mapping
├── model/
│   ├── movies.pkl                     # In-memory DataFrame (13,906 movies)
│   ├── vectors.pkl                    # L2-normalized CountVectorizer feature matrix
│   ├── vectorizer.pkl                 # Fitted vocabulary CountVectorizer
│   ├── collab_factors.pkl             # SVD item latent factor vectors (20-dim)
│   ├── content_sim.pkl                # Precomputed content similarity matrix (float16)
│   └── collab_sim.pkl                 # Precomputed collaborative similarity matrix (float16)
├── scripts/
│   ├── build_catalog.py               # Comprehensive multi-dataset merge & poster fetcher
│   ├── update_catalog.py              # CLI tool to pull newly released movies from TMDB
│   └── verify_posters.py              # Verification & audit script for poster coverage
├── static/
│   ├── css/
│   │   └── style.css                  # Netflix/Letterboxd dark theme design system
│   ├── js/
│   │   ├── api.js                     # REST API client & error handling
│   │   ├── ui.js                      # DOM renderers (cards, seed banner, modal, skeletons)
│   │   └── app.js                     # Controller (search, fuzzy matching, filters, modal)
│   └── images/
│       └── poster_placeholder.svg     # Default SVG placeholder icon
├── templates/
│   └── index.html                     # Semantic responsive HTML5 frontend
├── app.py                             # Flask application & REST API routes
├── train.py                           # Model training and artifact generation pipeline
├── config.py                          # Centralized settings & hyper-parameters
├── network_utils.py                   # Global CloudFront DNS resolver for TMDB
├── poster_placeholder.py              # Standalone high-res SVG poster generator
├── poster_service.py                  # 3-tier poster resolution service
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── .env                               # Local secrets (TMDB_API_KEY)
├── run.bat                            # Windows launch script
├── run.sh                             # macOS / Linux launch script
└── README.md                          # Comprehensive project documentation
```

---

## Quick Start Guide

### Prerequisites
- **Python 3.10+** (Fully tested on Python 3.10 through 3.14)
- **Windows, macOS, or Linux**

### 1. Launch the Application

#### Windows:
Double-click `run.bat` or run in PowerShell / Command Prompt:
```powershell
.\run.bat
```

#### macOS / Linux:
```bash
chmod +x run.sh
./run.sh
```

#### Manual Run:
```bash
# Activate virtual environment
.\venv\Scripts\activate   # (Windows)
source venv/bin/activate  # (macOS/Linux)

# Run server
python app.py
```
Open **`http://localhost:5000`** in your browser!

---

## Configuration & API Key

All configuration is centralized in `config.py`.

### Setting Your TMDB API Key
A free TMDB API key can be created at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).

Add it to your `.env` file:
```env
TMDB_API_KEY=your_actual_tmdb_api_key_here
```
*(Note: A built-in reliable demo fallback key is configured automatically, so the application runs immediately with full TMDB poster fetching even before you add your key).*

---

## Maintenance & Utility Scripts

### 1. Verify Poster Coverage
To verify that every single movie in the catalog has an accessible, working poster:
```bash
python scripts/verify_posters.py
```
*Outputs total movies, movies with real posters, movies on fallback, and verifies zero failures.*

### 2. Pulling Newly Released Movies
To pull newly released movies from TMDB API at any time in the future and retrain the model:
```bash
# Fetch new 2026 releases (3 pages) and rebuild model
python scripts/update_catalog.py --year 2026 --pages 3 --rebuild-model

# Fetch 2025 releases without rebuilding model
python scripts/update_catalog.py --year 2025 --pages 2
```

### 3. Rebuilding the ML Model
To retrain the recommender and regenerate model artifacts:
```bash
python train.py
```

---

## REST API Endpoints Reference

| Endpoint | Method | Parameters | Description |
|---|---|---|---|
| `/` | `GET` | — | Renders the single-page application UI |
| `/api/movies` | `GET` | — | Lightweight list of catalog movies for autocomplete |
| `/api/search_titles` | `GET` | `q=<query>` | Substring + fuzzy typo search with live discovery fallback |
| `/api/recommend` | `GET` | `movie=<title>`, `n=12`, `alpha=0.6` | Dual-engine hybrid recommendations with score & explanation |
| `/api/movie/<id>` | `GET` | — | Complete movie metadata + top 6 similar titles |
| `/api/browse` | `GET` | `genre`, `year_min`, `year_max`, `min_rating`, `sort`, `page`, `limit` | Multi-attribute catalog exploration with pagination |
| `/api/popular` | `GET` | `limit=16` | Top trending & audience favorite movies |
| `/api/top_rated` | `GET` | `limit=16` | All-time highest rated movies |
| `/api/genres` | `GET` | — | Available genres list with catalog counts |
| `/api/placeholder` | `GET` | `title`, `year`, `genre` | Dynamic high-res standalone SVG poster |
