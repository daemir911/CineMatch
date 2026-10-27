"""
Update Script for Movie Catalog & Recommender Pipeline.
Allows pulling in newly released movies from TMDB API at any time in the future,
resolving their posters, and updating the model.

Usage:
    python scripts/update_catalog.py [--year 2026] [--pages 3] [--rebuild-model]
"""
import sys
import argparse
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
logger = logging.getLogger("UpdateCatalog")

GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
}

def fetch_new_movies(year: int, pages: int = 3):
    """Fetches popular movies for a specific release year from TMDB."""
    if not config.TMDB_API_KEY:
        logger.error("TMDB_API_KEY is required to fetch newly released movies.")
        return []

    logger.info("Fetching new movies for year %d (%d pages)...", year, pages)
    movies = []
    seen = set()

    for page in range(1, pages + 1):
        for sort_by in ["popularity.desc", "vote_count.desc"]:
            try:
                url = f"{config.TMDB_BASE_URL}/discover/movie"
                params = {
                    "api_key": config.TMDB_API_KEY,
                    "primary_release_year": year,
                    "sort_by": sort_by,
                    "language": "en-US",
                    "page": page
                }
                r = requests.get(url, params=params, timeout=config.TMDB_TIMEOUT_SECONDS)
                if r.status_code == 200:
                    for item in r.json().get("results", []):
                        mid = item.get("id")
                        if mid and mid not in seen:
                            seen.add(mid)
                            movies.append(item)
                time.sleep(0.1)
            except Exception as e:
                logger.warning("Error fetching year %s page %s: %s", year, page, e)

    logger.info("Retrieved %d candidate movies from TMDB API for year %d.", len(movies), year)
    return movies

def update_catalog(year: int = 2026, pages: int = 3, rebuild_model: bool = False):
    if not config.CATALOG_CSV.exists():
        logger.error("Existing catalog not found at %s. Please run build_catalog.py first.", config.CATALOG_CSV)
        return

    catalog_df = pd.read_csv(config.CATALOG_CSV)
    existing_ids = set(catalog_df['tmdb_id'].astype(int))
    logger.info("Current catalog size: %d movies", len(catalog_df))

    new_items = fetch_new_movies(year=year, pages=pages)
    new_rows = []

    for item in new_items:
        tid = int(item["id"])
        if tid in existing_ids:
            continue

        p_path = item.get("poster_path")
        b_path = item.get("backdrop_path")
        title = item.get("title", "").strip()
        y = year
        if item.get("release_date"):
            try:
                y = int(item["release_date"].split("-")[0])
            except Exception:
                pass

        genre_ids = item.get("genre_ids", [])
        genres = [GENRE_MAP[gid] for gid in genre_ids if gid in GENRE_MAP]
        overview = item.get("overview", "")
        rating = round(float(item.get("vote_average", 0.0) or 0.0), 1)
        vote_count = int(item.get("vote_count", 0) or 0)
        popularity = round(float(item.get("popularity", 0.0) or 0.0), 2)
        lang = item.get("original_language", "en")

        meta = poster_service.resolve_poster(
            tmdb_id=tid,
            title=title,
            year=y,
            known_poster_path=p_path,
            genre=genres[0] if genres else "Movie"
        )

        new_rows.append({
            "tmdb_id": tid,
            "id": tid,
            "title": title,
            "year": y,
            "genres": genres,
            "overview": overview,
            "cast": [],
            "director": "Various",
            "keywords": [],
            "rating": rating,
            "vote_average": rating,
            "vote_count": vote_count,
            "popularity": popularity,
            "poster_path": p_path,
            "poster_url": meta["poster_url"],
            "backdrop_url": f"{config.TMDB_IMAGE_BASE_URL}{b_path}" if b_path else None,
            "tagline": "",
            "language": lang,
            "has_collab": False
        })
        existing_ids.add(tid)

    if not new_rows:
        logger.info("Catalog is already up to date. No new movies added.")
        return

    logger.info("Appending %d new movies to catalog...", len(new_rows))
    new_df = pd.DataFrame(new_rows)
    updated_catalog = pd.concat([new_df, catalog_df], ignore_index=True)

    # Save
    updated_catalog.to_csv(config.CATALOG_CSV, index=False)
    joblib.dump(updated_catalog, config.MOVIES_PKL)
    logger.info("Catalog updated successfully! New total movies: %d", len(updated_catalog))

    if rebuild_model:
        logger.info("Triggering model retrain pipeline...")
        import train
        train.run_pipeline()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update movie catalog with newly released movies.")
    parser.add_argument("--year", type=int, default=2026, help="Target release year to pull")
    parser.add_argument("--pages", type=int, default=3, help="Pages of results to fetch (20 per page)")
    parser.add_argument("--rebuild-model", action="store_true", help="Rebuild ML similarity model after update")
    args = parser.parse_args()

    update_catalog(year=args.year, pages=args.pages, rebuild_model=args.rebuild_model)
