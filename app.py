"""
Flask Backend Application for Universal Hybrid Movie Recommender System.
Supports 13,000+ movies in expanded catalog + universal on-the-fly ML recommendations:
1. Fast local hybrid filtering blending content similarity and collaborative SVD ratings.
2. Prominent fuzzy autocomplete title search that tolerates typos (e.g. 'dark nite' -> 'The Dark Knight').
3. Multi-attribute browsing and filtering by genre, release year range, minimum rating, and language.
4. Rich movie detail modal with 'More Like This' recommendations.
5. Dynamic high-resolution SVG poster placeholder generator for zero broken images.
6. Universal discovery for ANY movie in existence via live vectorization.
"""

import os
import sys
import difflib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import joblib
import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, render_template, request, Response
from flask_cors import CORS
from nltk.stem.porter import PorterStemmer
from sklearn.metrics.pairwise import cosine_similarity

import config
import network_utils
import poster_placeholder
from poster_service import poster_service

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MovieRecommenderApp")

app = Flask(
    __name__,
    static_folder=str(config.STATIC_DIR),
    template_folder=str(config.TEMPLATES_DIR)
)
CORS(app)

stemmer = PorterStemmer()

# -------------------------------------------------------------
# 1. Load Model Artifacts & Catalog
# -------------------------------------------------------------
logger.info("Loading model artifacts from %s ...", config.MODEL_DIR)

for artifact_path in [config.MOVIES_PKL, config.VECTORIZER_PKL, config.VECTORS_PKL]:
    if not os.path.exists(artifact_path):
        raise FileNotFoundError(
            f"Artifact '{artifact_path.name}' missing. "
            "Please run 'python scripts/build_catalog.py' and 'python train.py' to generate artifacts."
        )

movies_df = joblib.load(config.MOVIES_PKL)
vectorizer = joblib.load(config.VECTORIZER_PKL)
vectors = joblib.load(config.VECTORS_PKL)

# Optional precomputed matrices if available
content_sim = joblib.load(config.CONTENT_SIM_PKL) if os.path.exists(config.CONTENT_SIM_PKL) else None
collab_sim = joblib.load(config.COLLAB_SIM_PKL) if os.path.exists(config.COLLAB_SIM_PKL) else None
collab_factors = joblib.load(config.COLLAB_FACTORS_PKL) if os.path.exists(config.COLLAB_FACTORS_PKL) else None

# Helper to ensure list columns are python lists
import ast
def _ensure_list(v):
    if isinstance(v, list):
        return v
    if pd.isna(v) or v is None:
        return []
    if isinstance(v, str):
        v_str = v.strip()
        if v_str.startswith("[") and v_str.endswith("]"):
            try:
                res = ast.literal_eval(v_str)
                if isinstance(res, list):
                    return res
            except Exception:
                pass
        if "|" in v_str:
            return [x.strip() for x in v_str.split("|") if x.strip()]
        if "," in v_str:
            return [x.strip() for x in v_str.split(",") if x.strip()]
        return [v_str] if v_str else []
    return []

movies_df['genres'] = movies_df['genres'].apply(_ensure_list)
movies_df['cast'] = movies_df['cast'].apply(_ensure_list)
if 'keywords' in movies_df.columns:
    movies_df['keywords'] = movies_df['keywords'].apply(_ensure_list)

# Ensure consistent id and tmdb_id
if 'id' not in movies_df.columns and 'tmdb_id' in movies_df.columns:
    movies_df['id'] = movies_df['tmdb_id']
if 'rating' not in movies_df.columns and 'vote_average' in movies_df.columns:
    movies_df['rating'] = movies_df['vote_average']

# Fast lookup mappings
title_to_idx = {str(title).lower().strip(): idx for idx, title in enumerate(movies_df['title'])}
tmdb_to_idx = {int(tid): idx for idx, tid in enumerate(movies_df['id'])}
all_titles = [str(t) for t in movies_df['title'].tolist()]
all_titles_lower = [t.lower() for t in all_titles]
has_collab_mask = movies_df['has_collab'].values if 'has_collab' in movies_df.columns else np.zeros(len(movies_df), dtype=bool)

# Collaborative rating confidence scaling
# Uses a smooth logarithmic scale so movies with authentic co-ratings have high confidence,
# avoiding low-vote outlier noise while accurately distinguishing audience preferences.
vote_counts = movies_df['vote_count'].fillna(0).values.astype(np.float32) if 'vote_count' in movies_df.columns else np.zeros(len(movies_df), dtype=np.float32)
collab_confidence = np.log1p(vote_counts) / (np.log1p(vote_counts) + 1.5)

logger.info("Loaded %d catalog movies and text vectorizer into RAM.", len(movies_df))

# -------------------------------------------------------------
# 2. Universal Movie Metadata & Poster Fetchers (TMDB + Wikipedia)
# -------------------------------------------------------------
external_cache = {}
WIKI_HEADERS = {"User-Agent": "CineMatchRecommender/2.0 (Movie Recommender System)"}

def fetch_external_movie_info(query):
    """Finds ANY movie outside the catalog via TMDB or Wikipedia."""
    cache_key = query.lower().strip()
    if cache_key in external_cache:
        return external_cache[cache_key]

    # Strategy 1: TMDB Search
    if config.TMDB_API_KEY:
        try:
            url = f"{config.TMDB_BASE_URL}/search/movie"
            params = {"api_key": config.TMDB_API_KEY, "query": query, "language": "en-US"}
            r = requests.get(url, params=params, timeout=config.TMDB_TIMEOUT_SECONDS)
            if r.status_code == 200:
                results = r.json().get("results", [])
                if results:
                    top = results[0]
                    year = None
                    if top.get("release_date"):
                        try:
                            year = int(top["release_date"].split("-")[0])
                        except Exception:
                            pass
                    p_path = top.get("poster_path")
                    b_path = top.get("backdrop_path")
                    poster_url = f"{config.TMDB_IMAGE_BASE_URL}{p_path}" if p_path else f"/api/placeholder?title={query}&year={year or ''}"
                    backdrop_url = f"{config.TMDB_IMAGE_BASE_URL}{b_path}" if b_path else None

                    info = {
                        "tmdb_id": top.get("id"),
                        "id": top.get("id"),
                        "title": top.get("title", query),
                        "year": year,
                        "overview": top.get("overview", ""),
                        "rating": round(float(top.get("vote_average", 0.0)), 1),
                        "vote_count": int(top.get("vote_count", 0)),
                        "genres": ["Feature Film"],
                        "director": "Various",
                        "cast": [],
                        "poster_url": poster_url,
                        "backdrop_url": backdrop_url,
                        "is_external": True,
                        "source": "TMDB"
                    }
                    external_cache[cache_key] = info
                    return info
        except Exception as e:
            logger.debug("TMDB live search error for '%s': %s", query, e)

    # Strategy 2: Wikipedia Search
    try:
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": f"{query} film",
            "format": "json",
            "utf8": 1
        }
        res = requests.get("https://en.wikipedia.org/w/api.php", params=search_params, headers=WIKI_HEADERS, timeout=3.0)
        if res.status_code == 200:
            search_items = res.json().get("query", {}).get("search", [])
            if search_items:
                page_title = search_items[0]["title"]
                sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page_title}"
                res_sum = requests.get(sum_url, headers=WIKI_HEADERS, timeout=3.0)
                if res_sum.status_code == 200:
                    data = res_sum.json()
                    clean_t = data.get("title", query).replace(" (film)", "").replace(" (2023 film)", "").replace(" (2024 film)", "")
                    extract = data.get("extract", "")
                    thumb_url = data.get("thumbnail", {}).get("source")
                    info = {
                        "tmdb_id": None,
                        "id": None,
                        "title": clean_t,
                        "year": None,
                        "overview": extract,
                        "rating": 7.5,
                        "vote_count": 500,
                        "genres": ["Drama", "Feature Film"],
                        "director": "Various",
                        "cast": [],
                        "poster_url": thumb_url if thumb_url else f"/api/placeholder?title={clean_t}",
                        "backdrop_url": None,
                        "is_external": True,
                        "source": "Wikipedia"
                    }
                    external_cache[cache_key] = info
                    return info
    except Exception as e:
        logger.debug("Wikipedia live search error for '%s': %s", query, e)

    return None

# -------------------------------------------------------------
# 3. Recommendation Scoring & Explanations
# -------------------------------------------------------------
def compute_scores_for_index(target_idx, alpha):
    """
    Computes hybrid similarity scores for a movie index in the catalog.
    1. content_score: cosine similarity from plot, cast, director, genres, keywords
    2. collab_score: latent collaborative factor similarity weighted by confidence
    3. Normalizes both component scores to [0, 1] across candidate films
    4. Blends: final_score = alpha * content_norm + (1 - alpha) * collab_norm
    Returns: (final_score, content_norm, collab_norm)
    """
    # 1. Content similarity
    if content_sim is not None:
        c_raw = content_sim[target_idx].astype(np.float32).copy()
    else:
        c_raw = vectors[target_idx].dot(vectors.T).toarray()[0].astype(np.float32)

    # 2. Collaborative similarity
    if collab_factors is not None:
        target_f = collab_factors[target_idx]
        cl_raw = (collab_factors.dot(target_f) * collab_confidence).astype(np.float32)
    elif collab_sim is not None:
        cl_raw = (collab_sim[target_idx].astype(np.float32) * collab_confidence).copy()
    else:
        cl_raw = np.zeros_like(c_raw, dtype=np.float32)

    # Exclude target movie itself
    c_raw[target_idx] = -1.0
    cl_raw[target_idx] = -1.0

    # Min-Max Normalization to [0, 1] range across candidates
    c_valid = c_raw[c_raw >= 0]
    if len(c_valid) > 0:
        c_min, c_max = float(c_valid.min()), float(c_valid.max())
        c_norm = np.clip((c_raw - c_min) / (c_max - c_min + 1e-8), 0.0, 1.0)
    else:
        c_norm = np.zeros_like(c_raw, dtype=np.float32)

    cl_valid = cl_raw[cl_raw >= 0]
    if len(cl_valid) > 0:
        cl_min, cl_max = float(cl_valid.min()), float(cl_valid.max())
        cl_norm = np.clip((cl_raw - cl_min) / (cl_max - cl_min + 1e-8), 0.0, 1.0)
    else:
        cl_norm = np.zeros_like(cl_raw, dtype=np.float32)

    # Hybrid dynamic balance: alpha * Content + (1 - alpha) * Collab
    final_score = (alpha * c_norm) + ((1.0 - alpha) * cl_norm)
    final_score[target_idx] = -1.0

    return final_score, c_norm, cl_norm

def generate_why_recommended(target_movie, rec_row, content_score=None, collab_score=None):
    """Generates an intuitive explanation for why a movie is recommended."""
    reasons = []

    # Check shared director
    t_director = target_movie.get('director')
    r_director = rec_row.get('director')
    if t_director and r_director and t_director not in ("Unknown", "Various") and t_director == r_director:
        reasons.append(f"Directed by {r_director}")

    # Check shared cast
    t_cast = set(target_movie.get('cast', []) if isinstance(target_movie.get('cast'), list) else [])
    r_cast = set(rec_row.get('cast', []) if isinstance(rec_row.get('cast'), list) else [])
    shared_cast = list(t_cast.intersection(r_cast))
    if shared_cast:
        if len(shared_cast) == 1:
            reasons.append(f"Stars {shared_cast[0]}")
        else:
            reasons.append(f"Stars {', '.join(shared_cast[:2])}")

    # Check shared genres
    t_genres = set(target_movie.get('genres', []) if isinstance(target_movie.get('genres'), list) else [])
    r_genres = set(rec_row.get('genres', []) if isinstance(rec_row.get('genres'), list) else [])
    shared_genres = list(t_genres.intersection(r_genres))

    if reasons:
        if shared_genres:
            return f"{'; '.join(reasons)}; shared {', '.join(shared_genres[:2])}."
        return f"{'; '.join(reasons)}."
    elif shared_genres:
        if collab_score is not None and content_score is not None and collab_score > content_score:
            return f"Strong audience preference overlap; shared {', '.join(shared_genres[:2])}."
        return f"Shared {', '.join(shared_genres[:3])} genres with matching viewer preferences."
    else:
        return "Frequently enjoyed together by audiences with similar taste profiles."

def format_movie_payload(row, score=None, content_score=None, collab_score=None, why_text=None):
    """Helper to convert a pandas row/dict into a JSON-friendly movie card object."""
    genres = row.get("genres")
    if not isinstance(genres, list):
        genres = []
    cast = row.get("cast")
    if not isinstance(cast, list):
        cast = []

    poster_url = row.get("poster_url")
    title = row.get("title", "")
    year = int(row["year"]) if pd.notna(row.get("year")) and row.get("year") else None

    if not poster_url or pd.isna(poster_url) or not str(poster_url).strip():
        poster_url = f"/api/placeholder?title={title}&year={year or ''}"

    payload = {
        "tmdb_id": int(row.get("tmdb_id") or row.get("id")),
        "id": int(row.get("tmdb_id") or row.get("id")),
        "title": title,
        "year": year,
        "rating": round(float(row.get("rating") or row.get("vote_average") or 0.0), 1),
        "vote_count": int(row.get("vote_count", 0)),
        "genres": genres,
        "overview": str(row.get("overview", "") or "") if pd.notna(row.get("overview")) else "",
        "director": str(row.get("director", "Unknown")),
        "cast": cast[:4],
        "poster_url": poster_url,
        "backdrop_url": row.get("backdrop_url") if pd.notna(row.get("backdrop_url")) else None,
        "tagline": str(row.get("tagline", "") or "") if pd.notna(row.get("tagline")) else "",
        "language": str(row.get("language", "en") or "en")
    }
    if score is not None:
        payload["score"] = round(float(score), 3)
    if content_score is not None:
        payload["content_score"] = round(float(content_score), 3)
    if collab_score is not None:
        payload["collab_score"] = round(float(collab_score), 3)
    if why_text:
        payload["why_recommended"] = why_text
    return payload

# -------------------------------------------------------------
# 4. REST API Routes
# -------------------------------------------------------------
@app.route("/")
@app.route("/api/index")
@app.route("/api/index.py")
def index():
    return render_template("index.html")

@app.route("/api/placeholder", methods=["GET"])
def get_svg_placeholder():
    """Generates a standalone crisp SVG poster for any movie title."""
    title = request.args.get("title", "Movie Title")
    year_val = request.args.get("year")
    year = int(year_val) if year_val and year_val.isdigit() else None
    genre = request.args.get("genre", "Feature Film")

    svg_content = poster_placeholder.generate_svg_poster(title=title, year=year, genre=genre)
    return Response(
        svg_content,
        mimetype="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"}
    )

@app.route("/api/genres", methods=["GET"])
def get_genres():
    """Returns list of distinct genres with counts in the catalog."""
    genre_counts = {}
    for g_list in movies_df['genres']:
        if isinstance(g_list, list):
            for g in g_list:
                g_clean = g.strip()
                if g_clean:
                    genre_counts[g_clean] = genre_counts.get(g_clean, 0) + 1

    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    return jsonify([{"name": g, "count": c} for g, c in sorted_genres if c >= 10])

@app.route("/api/movies", methods=["GET"])
def get_all_movies():
    """Returns lightweight list of movies for search autocomplete."""
    global _cached_movies_list
    if "_cached_movies_list" not in globals():
        movies_list = []
        for _, row in movies_df.iterrows():
            movies_list.append({
                "id": int(row["id"]),
                "title": row["title"],
                "year": int(row["year"]) if row["year"] else None,
                "rating": round(float(row.get("rating", 0.0) or 0.0), 1),
                "poster_url": row.get("poster_url")
            })
        _cached_movies_list = movies_list
    return jsonify(_cached_movies_list)

@app.route("/api/search_titles", methods=["GET"])
def search_titles():
    """
    Prominent search bar autocomplete with fuzzy typo matching:
    1. Exact substring matches
    2. Fuzzy matching (difflib) so typos (e.g. 'dark nite', 'interstelar', 'avater') match
    3. Universal live search if fewer than 4 local matches found
    """
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify([])

    q_lower = q.lower()
    matches = []
    seen_ids = set()

    # 1. Substring matching in catalog
    for idx, row in movies_df.iterrows():
        t = row["title"]
        t_low = t.lower()
        if q_lower in t_low:
            seen_ids.add(int(row["id"]))
            matches.append({
                "id": int(row["id"]),
                "title": t,
                "year": int(row["year"]) if row["year"] else None,
                "rating": round(float(row.get("rating", 0.0) or 0.0), 1),
                "poster_url": row.get("poster_url"),
                "source": "catalog"
            })
            if len(matches) >= 6:
                break

    # 2. Fuzzy typo matching if few matches
    if len(matches) < 6:
        close_titles = difflib.get_close_matches(q_lower, all_titles_lower, n=6, cutoff=0.5)
        for ct in close_titles:
            idx = title_to_idx.get(ct)
            if idx is not None:
                row = movies_df.iloc[idx]
                mid = int(row["id"])
                if mid not in seen_ids:
                    seen_ids.add(mid)
                    matches.append({
                        "id": mid,
                        "title": row["title"],
                        "year": int(row["year"]) if row["year"] else None,
                        "rating": round(float(row.get("rating", 0.0) or 0.0), 1),
                        "poster_url": row.get("poster_url"),
                        "source": "fuzzy"
                    })
                    if len(matches) >= 8:
                        break

    # 3. Universal live discovery if still few matches
    if len(matches) < 4 and config.TMDB_API_KEY:
        try:
            url = f"{config.TMDB_BASE_URL}/search/movie"
            params = {"api_key": config.TMDB_API_KEY, "query": q, "language": "en-US"}
            r = requests.get(url, params=params, timeout=2.0)
            if r.status_code == 200:
                for item in r.json().get("results", [])[:4]:
                    item_id = item.get("id")
                    if item_id not in seen_ids:
                        seen_ids.add(item_id)
                        p_path = item.get("poster_path")
                        p_url = f"{config.TMDB_IMAGE_BASE_URL}{p_path}" if p_path else f"/api/placeholder?title={item.get('title')}"
                        matches.append({
                            "id": item_id,
                            "title": item.get("title"),
                            "year": int(item["release_date"].split("-")[0]) if item.get("release_date") else None,
                            "rating": round(float(item.get("vote_average", 0.0)), 1),
                            "poster_url": p_url,
                            "source": "universal"
                        })
        except Exception:
            pass

    return jsonify(matches[:10])

@app.route("/api/recommend", methods=["GET"])
def recommend():
    """
    GET /api/recommend?movie=<title_or_id>&n=12&alpha=0.6
    Universal Recommender blending content and collaborative filtering.
    """
    query_param = request.args.get("movie", "").strip()
    if not query_param:
        return jsonify({"error": "Query parameter 'movie' is required."}), 400

    try:
        n = int(request.args.get("n", config.DEFAULT_RECOMMEND_COUNT))
        n = max(1, min(n, 48))
    except ValueError:
        n = config.DEFAULT_RECOMMEND_COUNT

    try:
        alpha = float(request.args.get("alpha", config.DEFAULT_ALPHA))
        alpha = max(0.0, min(alpha, 1.0))
    except ValueError:
        alpha = config.DEFAULT_ALPHA

    # 1. Lookup target in local catalog
    target_idx = title_to_idx.get(query_param.lower())
    if target_idx is None and query_param.isdigit():
        target_idx = tmdb_to_idx.get(int(query_param))

    is_external = False
    external_movie = None

    if target_idx is not None:
        target_movie = movies_df.iloc[target_idx]
        final_scores, c_scores, cl_scores = compute_scores_for_index(target_idx, alpha)
        top_indices = np.argsort(final_scores)[::-1][:n]
    else:
        # Check fuzzy match in catalog first before falling back to external
        close_titles = difflib.get_close_matches(query_param.lower(), all_titles_lower, n=1, cutoff=0.6)
        if close_titles:
            target_idx = title_to_idx.get(close_titles[0])
            target_movie = movies_df.iloc[target_idx]
            final_scores, c_scores, cl_scores = compute_scores_for_index(target_idx, alpha)
            top_indices = np.argsort(final_scores)[::-1][:n]
        else:
            # 2. Universal Live Discovery
            external_movie = fetch_external_movie_info(query_param)
            if external_movie:
                is_external = True
                logger.info("Universal Recommender: Vectorizing live movie '%s'", external_movie['title'])
                text_tokens = (str(external_movie.get('overview', '')) + ' ' + str(external_movie.get('title', ''))).split()
                stemmed_words = [stemmer.stem(w.lower()) for w in text_tokens]
                query_vec = vectorizer.transform([' '.join(stemmed_words)])
                c_raw = cosine_similarity(query_vec, vectors)[0].astype(np.float32)
                c_val = c_raw[c_raw >= 0]
                c_norm = np.clip((c_raw - c_val.min()) / (c_val.max() - c_val.min() + 1e-8), 0.0, 1.0) if len(c_val) > 0 else np.zeros_like(c_raw)
                final_scores = c_norm
                c_scores = c_norm
                cl_scores = np.zeros_like(c_norm)
                top_indices = np.argsort(final_scores)[::-1][:n]
                target_movie = external_movie
            else:
                suggestions = difflib.get_close_matches(query_param, all_titles, n=5, cutoff=0.35)
                return jsonify({
                    "error": f"Movie '{query_param}' was not found.",
                    "suggestions": suggestions
                }), 404

    # Build recommendations payload
    recommendations = []
    for idx in top_indices:
        rec_row = movies_df.iloc[idx]
        why_text = generate_why_recommended(target_movie, rec_row, content_score=c_scores[idx], collab_score=cl_scores[idx])
        recommendations.append(format_movie_payload(
            rec_row, 
            score=final_scores[idx], 
            content_score=c_scores[idx], 
            collab_score=cl_scores[idx], 
            why_text=why_text
        ))

    # Format seed movie info
    if is_external:
        q_meta = {
            "tmdb_id": external_movie.get("tmdb_id"),
            "id": external_movie.get("tmdb_id"),
            "title": external_movie["title"],
            "year": external_movie.get("year"),
            "genres": external_movie.get("genres", []),
            "director": external_movie.get("director", "Unknown"),
            "poster_url": external_movie.get("poster_url"),
            "backdrop_url": external_movie.get("backdrop_url"),
            "overview": external_movie.get("overview", ""),
            "is_external": True,
            "source": external_movie.get("source", "Live Search")
        }
    else:
        q_meta = format_movie_payload(target_movie)
        q_meta["is_external"] = False

    return jsonify({
        "query_movie": q_meta,
        "alpha": alpha,
        "count": len(recommendations),
        "recommendations": recommendations
    })

@app.route("/api/movie/<path:identifier>", methods=["GET"])
def get_movie_details(identifier):
    """
    Returns rich details for a movie by TMDB ID or Title,
    including top 6 similar movies for the 'More Like This' section.
    """
    idx = None
    if identifier.isdigit():
        idx = tmdb_to_idx.get(int(identifier))
    if idx is None:
        idx = title_to_idx.get(identifier.lower().strip())
    if idx is None:
        # Fuzzy match attempt
        close = difflib.get_close_matches(identifier.lower().strip(), all_titles_lower, n=1, cutoff=0.7)
        if close:
            idx = title_to_idx.get(close[0])

    if idx is not None:
        row = movies_df.iloc[idx]
        payload = format_movie_payload(row)

        # Compute top 6 similar movies for the detail modal
        scores, c_sc, cl_sc = compute_scores_for_index(idx, alpha=config.DEFAULT_ALPHA)
        similar_indices = np.argsort(scores)[::-1][:6]
        similar_movies = [
            format_movie_payload(movies_df.iloc[i], score=scores[i], content_score=c_sc[i], collab_score=cl_sc[i]) 
            for i in similar_indices
        ]

        payload["similar_movies"] = similar_movies
        payload["has_collab"] = bool(row.get("has_collab", False))
        payload["is_external"] = False
        return jsonify(payload)

    # External fallback
    external = fetch_external_movie_info(identifier)
    if external:
        return jsonify(external)

    return jsonify({"error": f"Movie '{identifier}' not found."}), 404

@app.route("/api/browse", methods=["GET"])
def browse_movies():
    """
    Catalog browsing endpoint with multi-criteria filtering and sorting:
    - genre: string (e.g. Action, Comedy, Drama, Sci-Fi)
    - year_min, year_max: int
    - min_rating: float
    - lang: string
    - sort: 'popularity' | 'rating' | 'year_desc' | 'year_asc' | 'title'
    - page: int (1-indexed)
    - limit: int (default: 24)
    """
    genre_filter = request.args.get("genre", "").strip().lower()
    year_min = request.args.get("year_min", type=int)
    year_max = request.args.get("year_max", type=int)
    min_rating = request.args.get("min_rating", type=float)
    lang_filter = request.args.get("lang", "").strip().lower()
    sort_by = request.args.get("sort", "popularity").strip().lower()
    page = max(1, request.args.get("page", 1, type=int))
    limit = max(1, min(request.args.get("limit", 24, type=int), 60))

    filtered_df = movies_df

    # Genre filter
    if genre_filter and genre_filter != "all":
        filtered_df = filtered_df[filtered_df['genres'].apply(
            lambda glist: any(genre_filter in str(g).lower() for g in glist) if isinstance(glist, list) else False
        )]

    # Year filters
    if year_min is not None:
        filtered_df = filtered_df[filtered_df['year'] >= year_min]
    if year_max is not None:
        filtered_df = filtered_df[filtered_df['year'] <= year_max]

    # Rating filter
    if min_rating is not None:
        filtered_df = filtered_df[filtered_df['rating'] >= min_rating]

    # Language filter
    if lang_filter and lang_filter != "all":
        filtered_df = filtered_df[filtered_df['language'].str.lower() == lang_filter]

    # Sorting
    if sort_by == "rating":
        filtered_df = filtered_df.sort_values(by=["rating", "vote_count"], ascending=[False, False])
    elif sort_by == "year_desc":
        filtered_df = filtered_df.sort_values(by=["year", "popularity"], ascending=[False, False])
    elif sort_by == "year_asc":
        filtered_df = filtered_df[filtered_df['year'] > 1880].sort_values(by=["year", "popularity"], ascending=[True, False])
    elif sort_by == "title":
        filtered_df = filtered_df.sort_values(by="title", ascending=True)
    else:  # Popularity default
        filtered_df = filtered_df.sort_values(by=["vote_count", "popularity"], ascending=[False, False])

    total_count = len(filtered_df)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_df = filtered_df.iloc[start_idx:end_idx]

    movies_payload = [format_movie_payload(row) for _, row in page_df.iterrows()]

    return jsonify({
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit,
        "movies": movies_payload
    })

@app.route("/api/popular", methods=["GET"])
def get_popular():
    """Returns top popular movies for the home page showcase row."""
    limit = request.args.get("limit", 16, type=int)
    top_df = movies_df.sort_values(by=["vote_count", "popularity"], ascending=[False, False]).head(limit)
    return jsonify({
        "count": len(top_df),
        "movies": [format_movie_payload(r) for _, r in top_df.iterrows()]
    })

@app.route("/api/top_rated", methods=["GET"])
def get_top_rated():
    """Returns top critically acclaimed movies (high rating & substantial votes)."""
    limit = request.args.get("limit", 16, type=int)
    top_rated_df = movies_df[movies_df['vote_count'] >= 500].sort_values(by=["rating", "vote_count"], ascending=[False, False]).head(limit)
    return jsonify({
        "count": len(top_rated_df),
        "movies": [format_movie_payload(r) for _, r in top_rated_df.iterrows()]
    })

@app.errorhandler(404)
def not_found(e):
    if request.path in ["/api/index", "/api/index.py"]:
        return render_template("index.html")
    if request.path.startswith("/api/"):
        return jsonify({"error": "Resource not found", "path": request.path}), 404
    return render_template("index.html"), 404

if __name__ == "__main__":
    logger.info("Starting CineMatch Universal Recommender on http://%s:%s", config.HOST, config.PORT)
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, use_reloader=False)
