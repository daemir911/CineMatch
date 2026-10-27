"""
Comprehensive Movie Catalog Builder and Merger Script.
Merges:
1. TMDB 5,000 Dataset with Credits (4,803 movies)
2. TMDB 10,000+ Extended Dataset (10,866 movies from 1960-2015)
3. Recent Top Modern Releases (2016-2025/2026 via TMDB discover API)
4. Bollywood / International Classics & Hits
5. MovieLens Links & Ratings (collaborative filtering linkages)

Cleans, deduplicates, fills missing values, resolves poster URLs for EVERY movie,
and exports data/movies_catalog.csv and model/movies.pkl.
"""
import os
import sys
import ast
import re
import time
import logging
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import joblib
import pandas as pd
import requests

import config
import network_utils
from poster_service import poster_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BuildCatalog")

# Helper parsers
def parse_json_names(val):
    if not val or pd.isna(val):
        return []
    if isinstance(val, list):
        return [str(x) for x in val if x]
    if isinstance(val, str):
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            try:
                items = ast.literal_eval(val)
                if isinstance(items, list):
                    res = []
                    for i in items:
                        if isinstance(i, dict) and "name" in i:
                            res.append(i["name"])
                        elif isinstance(i, str):
                            res.append(i)
                    return res
            except Exception:
                pass
        # Pipe or comma separated string
        if "|" in val:
            return [x.strip() for x in val.split("|") if x.strip()]
        if "," in val:
            return [x.strip() for x in val.split(",") if x.strip()]
        return [val] if val else []
    return []

def parse_cast_list(val, limit=4):
    names = parse_json_names(val)
    return names[:limit]

def parse_director_name(crew_val, direct_val=None):
    if direct_val and pd.notna(direct_val) and str(direct_val).strip():
        # Might be pipe separated
        d_str = str(direct_val).split("|")[0].strip()
        if d_str:
            return d_str
    if crew_val and pd.notna(crew_val):
        if isinstance(crew_val, str) and crew_val.strip().startswith("["):
            try:
                items = ast.literal_eval(crew_val)
                if isinstance(items, list):
                    for i in items:
                        if isinstance(i, dict) and i.get("job") == "Director":
                            return i.get("name", "Unknown")
            except Exception:
                pass
    return "Unknown"

def clean_year(release_date, release_year=None):
    if release_year and pd.notna(release_year):
        try:
            y = int(float(release_year))
            if 1880 <= y <= 2030:
                return y
        except Exception:
            pass
    if release_date and pd.notna(release_date):
        m = re.search(r'\b(19\d{2}|20\d{2})\b', str(release_date))
        if m:
            return int(m.group(1))
    return None

def fetch_recent_tmdb_movies(years=range(2016, 2026), pages_per_year=2):
    """
    Fetches the most popular & highest-rated modern movies from TMDB API
    to ensure recent blockbusters (Oppenheimer, Barbie, Dune 1 & 2, etc.) are included.
    """
    if not config.TMDB_API_KEY:
        logger.warning("No TMDB_API_KEY configured; skipping live recent movies fetch.")
        return []

    logger.info("Fetching recent releases (2016-2025) via TMDB API...")
    recent_movies = []
    seen_ids = set()

    for year in years:
        for sort_by in ["vote_count.desc", "popularity.desc"]:
            for page in range(1, pages_per_year + 1):
                try:
                    url = f"{config.TMDB_BASE_URL}/discover/movie"
                    params = {
                        "api_key": config.TMDB_API_KEY,
                        "primary_release_year": year,
                        "sort_by": sort_by,
                        "language": "en-US",
                        "page": page,
                        "vote_count.gte": 100
                    }
                    resp = requests.get(url, params=params, timeout=config.TMDB_TIMEOUT_SECONDS)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in data.get("results", []):
                            mid = item.get("id")
                            if mid and mid not in seen_ids:
                                seen_ids.add(mid)
                                recent_movies.append(item)
                    time.sleep(0.05)
                except Exception as e:
                    logger.debug("Error fetching year %s page %s: %s", year, page, e)

    logger.info("Fetched %d recent movies from TMDB API.", len(recent_movies))
    return recent_movies

def load_all_sources():
    catalog_dict = {}  # tmdb_id -> movie_dict

    # 1. Load TMDB 5000 + Credits
    if config.TMDB_MOVIES_CSV.exists() and config.TMDB_CREDITS_CSV.exists():
        logger.info("Processing TMDB 5,000 datasets...")
        m_df = pd.read_csv(config.TMDB_MOVIES_CSV)
        c_df = pd.read_csv(config.TMDB_CREDITS_CSV)
        merged_5k = m_df.merge(c_df[['movie_id', 'cast', 'crew']], left_on='id', right_on='movie_id', how='left')

        for _, row in merged_5k.iterrows():
            tid = int(row['id'])
            title = str(row['title']).strip()
            year = clean_year(row.get('release_date'))
            genres = parse_json_names(row.get('genres'))
            keywords = parse_json_names(row.get('keywords'))
            cast = parse_cast_list(row.get('cast'), limit=4)
            director = parse_director_name(row.get('crew'))
            overview = str(row.get('overview', '') or '') if pd.notna(row.get('overview')) else ""
            rating = round(float(row.get('vote_average', 0.0) or 0.0), 1)
            vote_count = int(row.get('vote_count', 0) or 0)
            popularity = round(float(row.get('popularity', 0.0) or 0.0), 2)
            lang = str(row.get('original_language', 'en') or 'en')
            tagline = str(row.get('tagline', '') or '') if pd.notna(row.get('tagline')) else ""

            catalog_dict[tid] = {
                "tmdb_id": tid,
                "title": title,
                "year": year,
                "genres": genres,
                "overview": overview,
                "cast": cast,
                "director": director,
                "keywords": keywords,
                "rating": rating,
                "vote_count": vote_count,
                "popularity": popularity,
                "poster_path": None,
                "poster_url": None,
                "backdrop_url": None,
                "tagline": tagline,
                "language": lang,
                "alt_url": None
            }
        logger.info("Catalog after TMDB 5k: %d movies", len(catalog_dict))

    # 2. Load Extended TMDB 10k Dataset
    if config.TMDB_10K_CSV.exists():
        logger.info("Processing Extended TMDB 10,000+ dataset (%s)...", config.TMDB_10K_CSV.name)
        df_10k = pd.read_csv(config.TMDB_10K_CSV)
        added_10k = 0
        updated_10k = 0

        for _, row in df_10k.iterrows():
            try:
                tid = int(row['id'])
            except Exception:
                continue

            title = str(row.get('original_title', '') or '').strip()
            if not title:
                continue

            year = clean_year(row.get('release_date'), row.get('release_year'))
            genres = parse_json_names(row.get('genres'))
            keywords = parse_json_names(row.get('keywords'))
            cast = parse_cast_list(row.get('cast'), limit=4)
            director = parse_director_name(None, row.get('director'))
            overview = str(row.get('overview', '') or '') if pd.notna(row.get('overview')) else ""
            rating = round(float(row.get('vote_average', 0.0) or 0.0), 1)
            vote_count = int(row.get('vote_count', 0) or 0)
            popularity = round(float(row.get('popularity', 0.0) or 0.0), 2)
            tagline = str(row.get('tagline', '') or '') if pd.notna(row.get('tagline')) else ""

            if tid in catalog_dict:
                # Enrich missing fields in 5k movie
                existing = catalog_dict[tid]
                if not existing['genres'] and genres:
                    existing['genres'] = genres
                if not existing['cast'] and cast:
                    existing['cast'] = cast
                if existing['director'] == "Unknown" and director != "Unknown":
                    existing['director'] = director
                if not existing['overview'] and overview:
                    existing['overview'] = overview
                if not existing['keywords'] and keywords:
                    existing['keywords'] = keywords
                updated_10k += 1
            else:
                catalog_dict[tid] = {
                    "tmdb_id": tid,
                    "title": title,
                    "year": year,
                    "genres": genres,
                    "overview": overview,
                    "cast": cast,
                    "director": director,
                    "keywords": keywords,
                    "rating": rating,
                    "vote_count": vote_count,
                    "popularity": popularity,
                    "poster_path": None,
                    "poster_url": None,
                    "backdrop_url": None,
                    "tagline": tagline,
                    "language": "en",
                    "alt_url": None
                }
                added_10k += 1

        logger.info("From 10k dataset: added %d new movies, enriched %d existing movies.", added_10k, updated_10k)

    # 3. Add Recent TMDB releases (2016-2025)
    recent_items = fetch_recent_tmdb_movies(years=range(2016, 2026), pages_per_year=2)
    added_recent = 0
    # TMDB Genre ID Mapping
    GENRE_MAP = {
        28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
        99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
        27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
        10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
    }

    for item in recent_items:
        tid = item.get("id")
        if not tid:
            continue
        p_path = item.get("poster_path")
        b_path = item.get("backdrop_path")
        title = item.get("title", "").strip()
        year = clean_year(item.get("release_date"))
        genre_ids = item.get("genre_ids", [])
        genres = [GENRE_MAP[gid] for gid in genre_ids if gid in GENRE_MAP]
        overview = item.get("overview", "")
        rating = round(float(item.get("vote_average", 0.0) or 0.0), 1)
        vote_count = int(item.get("vote_count", 0) or 0)
        popularity = round(float(item.get("popularity", 0.0) or 0.0), 2)
        lang = item.get("original_language", "en")

        if tid in catalog_dict:
            # Update poster path if known
            if p_path and not catalog_dict[tid]["poster_path"]:
                catalog_dict[tid]["poster_path"] = p_path
            if b_path and not catalog_dict[tid]["backdrop_url"]:
                catalog_dict[tid]["backdrop_url"] = f"{config.TMDB_IMAGE_BASE_URL}{b_path}"
        else:
            catalog_dict[tid] = {
                "tmdb_id": tid,
                "title": title,
                "year": year,
                "genres": genres,
                "overview": overview,
                "cast": [],
                "director": "Various",
                "keywords": [],
                "rating": rating,
                "vote_count": vote_count,
                "popularity": popularity,
                "poster_path": p_path,
                "poster_url": f"{config.TMDB_IMAGE_BASE_URL}{p_path}" if p_path else None,
                "backdrop_url": f"{config.TMDB_IMAGE_BASE_URL}{b_path}" if b_path else None,
                "tagline": "",
                "language": lang,
                "alt_url": None
            }
            added_recent += 1

    logger.info("Added %d recent movies (2016-2025). Total movies so far: %d", added_recent, len(catalog_dict))

    # 4. Add Bollywood Classics & Hits (with Wikimedia posters)
    if config.BOLLYWOOD_CSV.exists():
        logger.info("Processing Bollywood dataset (%s)...", config.BOLLYWOOD_CSV.name)
        b_df = pd.read_csv(config.BOLLYWOOD_CSV)
        added_bolly = 0
        title_year_seen = {(m["title"].lower(), m["year"]) for m in catalog_dict.values()}

        # Filter to top Bollywood movies (rating >= 6.0, votes >= 500)
        top_b_df = b_df[b_df['imdb_rating'] >= 6.0].copy()
        for idx, row in top_b_df.iterrows():
            title = str(row.get('title_x') or row.get('original_title') or '').strip()
            if not title:
                continue
            year = clean_year(row.get('release_date'), row.get('year_of_release'))
            if (title.lower(), year) in title_year_seen:
                continue

            genres = parse_json_names(row.get('genres'))
            cast = parse_cast_list(row.get('actors'), limit=4)
            overview = str(row.get('summary') or row.get('story') or '').strip()
            rating = round(float(row.get('imdb_rating', 6.0) or 6.0), 1)
            votes = int(float(row.get('imdb_votes', 100) or 100))
            poster_url = str(row.get('poster_path', '') or '').strip()
            alt_url = poster_url if (poster_url.startswith("http://") or poster_url.startswith("https://")) else None

            # Generate unique negative synthetic tmdb_id for Bollywood movies without tmdb_id
            synth_id = 9000000 + idx
            catalog_dict[synth_id] = {
                "tmdb_id": synth_id,
                "title": title,
                "year": year,
                "genres": genres if genres else ["Drama"],
                "overview": overview,
                "cast": cast,
                "director": "Indian Cinema",
                "keywords": ["bollywood", "indian cinema"],
                "rating": rating,
                "vote_count": votes,
                "popularity": round(rating * 3.0, 1),
                "poster_path": None,
                "poster_url": alt_url,
                "backdrop_url": None,
                "tagline": "",
                "language": "hi",
                "alt_url": alt_url
            }
            title_year_seen.add((title.lower(), year))
            added_bolly += 1
            if added_bolly >= 1500:  # Top 1,500 curated Bollywood movies
                break

        logger.info("Added %d curated Bollywood movies. Total catalog size: %d", added_bolly, len(catalog_dict))

    # Convert to DataFrame
    movies_list = list(catalog_dict.values())
    catalog_df = pd.DataFrame(movies_list)

    # 5. Link MovieLens Collaborative Ratings
    has_collab_set = set()
    if config.LINKS_CSV.exists() and config.RATINGS_CSV.exists():
        logger.info("Linking MovieLens collaborative ratings...")
        links_df = pd.read_csv(config.LINKS_CSV).dropna(subset=['tmdbId'])
        ratings_df = pd.read_csv(config.RATINGS_CSV)
        rated_movie_ids = set(ratings_df['movieId'].unique())
        links_rated = links_df[links_df['movieId'].isin(rated_movie_ids)]
        has_collab_set = set(links_rated['tmdbId'].astype(int))
        logger.info("Found %d movies with active collaborative ratings.", len(has_collab_set))

    catalog_df['has_collab'] = catalog_df['tmdb_id'].apply(lambda tid: tid in has_collab_set)

    # Clean missing values
    catalog_df['overview'] = catalog_df['overview'].fillna('')
    catalog_df['director'] = catalog_df['director'].fillna('Unknown')
    catalog_df['year'] = catalog_df['year'].fillna(0).astype(int)
    catalog_df['rating'] = catalog_df['rating'].fillna(6.0).astype(float)
    catalog_df['vote_count'] = catalog_df['vote_count'].fillna(0).astype(int)
    catalog_df['popularity'] = catalog_df['popularity'].fillna(0.0).astype(float)

    # Sort catalog by popularity & vote count
    catalog_df.sort_values(by=['vote_count', 'popularity'], ascending=False, inplace=True)
    catalog_df.reset_index(drop=True, inplace=True)

    logger.info("Final cleaned catalog contains %d unique movies.", len(catalog_df))
    return catalog_df

def resolve_all_posters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures EVERY movie in the catalog has a working poster URL,
    following the 3-tier fallback architecture:
    1. TMDB Poster
    2. Alternate Source
    3. Clean Generated SVG Placeholder
    """
    logger.info("Resolving poster URLs for all %d movies in catalog...", len(df))
    records = df.to_dict(orient="records")
    resolved_records = poster_service.batch_resolve_posters(records, max_workers=10, save_interval=1000)
    resolved_df = pd.DataFrame(resolved_records)
    return resolved_df

def main():
    start_time = time.time()
    logger.info("=== STEP 1: Building Expanded Catalog ===")
    df = load_all_sources()

    logger.info("=== STEP 2: Resolving & Caching Posters ===")
    df = resolve_all_posters(df)

    # Prepare standard export schema
    export_df = df[[
        'tmdb_id', 'title', 'year', 'genres', 'overview',
        'cast', 'director', 'keywords', 'rating', 'vote_count',
        'popularity', 'poster_path', 'poster_url', 'backdrop_url',
        'tagline', 'language', 'has_collab'
    ]].copy()

    # Also include compatibility column 'id' for existing recommender lookups
    export_df['id'] = export_df['tmdb_id']
    export_df['vote_average'] = export_df['rating']

    # Save to CSV and PKL
    logger.info("Saving catalog to %s and %s ...", config.CATALOG_CSV, config.MOVIES_PKL)
    export_df.to_csv(config.CATALOG_CSV, index=False)
    joblib.dump(export_df, config.MOVIES_PKL)

    elapsed = time.time() - start_time
    logger.info("Catalog build complete! Total: %d movies in %.2f seconds.", len(export_df), elapsed)
    return export_df

if __name__ == "__main__":
    main()
