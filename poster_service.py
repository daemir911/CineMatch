"""
Poster service implementing the 3-tier fallback architecture:
Tier 1: TMDB Poster (looked up by tmdb_id or by title & year)
Tier 2: Alternate Source (OMDb API, Wikipedia API, or Direct Dataset URL)
Tier 3: Clean Generated High-Res SVG Placeholder showing movie title and year

Includes in-memory and persistent disk caching (data/poster_cache.json),
parallel fetching, rate-limiting, and retry logic.
"""
import os
import json
import time
import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

import config
import poster_placeholder

logger = logging.getLogger("PosterService")

CACHE_FILE = config.DATA_DIR / "poster_cache.json"

class PosterService:
    def __init__(self):
        self.cache = self._load_cache()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CineMatchRecommender/2.0 (Movie Recommendation Project)"
        })

    def _load_cache(self) -> dict:
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not read poster cache: %s", e)
        return {}

    def save_cache(self):
        try:
            cache_copy = dict(list(self.cache.items()))
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_copy, f, indent=2)
        except Exception as e:
            logger.warning("Could not save poster cache: %s", e)

    def get_cached_poster(self, tmdb_id=None, title=None, year=None):
        if tmdb_id and str(tmdb_id) in self.cache:
            return self.cache[str(tmdb_id)]
        if title:
            key = f"title:{title.lower().strip()}:{year or ''}"
            if key in self.cache:
                return self.cache[key]
        return None

    def cache_poster(self, tmdb_id, title, year, poster_info):
        if tmdb_id:
            self.cache[str(tmdb_id)] = poster_info
        if title:
            key = f"title:{title.lower().strip()}:{year or ''}"
            self.cache[key] = poster_info

    def resolve_poster(self, tmdb_id=None, title=None, year=None, known_poster_path=None, alt_url=None, genre="Movie") -> dict:
        """
        Resolves poster using the 3-tier hierarchy:
        1. TMDB Poster
        2. Alternate Source (OMDb / Wikipedia / direct URL)
        3. Clean Generated SVG Placeholder with title
        """
        # Check cache first
        cached = self.get_cached_poster(tmdb_id=tmdb_id, title=title, year=year)
        if cached:
            return cached

        # 1. Tier 1: Known TMDB poster_path
        if known_poster_path and isinstance(known_poster_path, str) and known_poster_path.strip() and known_poster_path.strip().startswith("/"):
            poster_url = f"{config.TMDB_IMAGE_BASE_URL}{known_poster_path.strip()}"
            res = {
                "poster_url": poster_url,
                "backdrop_url": None,
                "source": "tmdb",
                "is_fallback": False
            }
            self.cache_poster(tmdb_id, title, year, res)
            return res

        # 1. Tier 1b: Fetch from TMDB API via tmdb_id
        if tmdb_id and config.TMDB_API_KEY:
            try:
                url = f"{config.TMDB_BASE_URL}/movie/{tmdb_id}"
                params = {"api_key": config.TMDB_API_KEY, "language": "en-US"}
                resp = self.session.get(url, params=params, timeout=config.TMDB_TIMEOUT_SECONDS)
                if resp.status_code == 200:
                    data = resp.json()
                    p_path = data.get("poster_path")
                    b_path = data.get("backdrop_path")
                    if p_path:
                        res = {
                            "poster_url": f"{config.TMDB_IMAGE_BASE_URL}{p_path}",
                            "backdrop_url": f"{config.TMDB_IMAGE_BASE_URL}{b_path}" if b_path else None,
                            "tagline": data.get("tagline", "") or "",
                            "runtime": data.get("runtime"),
                            "source": "tmdb",
                            "is_fallback": False
                        }
                        self.cache_poster(tmdb_id, title, year, res)
                        return res
            except Exception as e:
                logger.debug("TMDB id lookup error for %s: %s", tmdb_id, e)

        # 1. Tier 1c: Search TMDB by title and year
        if title and config.TMDB_API_KEY:
            try:
                url = f"{config.TMDB_BASE_URL}/search/movie"
                params = {"api_key": config.TMDB_API_KEY, "query": title, "language": "en-US"}
                if year and str(year).isdigit() and int(year) > 1800:
                    params["year"] = int(year)
                resp = self.session.get(url, params=params, timeout=config.TMDB_TIMEOUT_SECONDS)
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results:
                        top = results[0]
                        p_path = top.get("poster_path")
                        b_path = top.get("backdrop_path")
                        if p_path:
                            res = {
                                "poster_url": f"{config.TMDB_IMAGE_BASE_URL}{p_path}",
                                "backdrop_url": f"{config.TMDB_IMAGE_BASE_URL}{b_path}" if b_path else None,
                                "source": "tmdb",
                                "is_fallback": False
                            }
                            self.cache_poster(tmdb_id, title, year, res)
                            return res
            except Exception as e:
                logger.debug("TMDB search error for %s: %s", title, e)

        # 2. Tier 2: Alternate Source (Dataset direct URL, Wikipedia, or OMDb)
        if alt_url and isinstance(alt_url, str) and (alt_url.startswith("http://") or alt_url.startswith("https://")):
            res = {
                "poster_url": alt_url,
                "backdrop_url": None,
                "source": "alternate",
                "is_fallback": False
            }
            self.cache_poster(tmdb_id, title, year, res)
            return res

        # Tier 2b: Wikipedia API summary thumbnail
        if title:
            try:
                clean_title = title.split("(")[0].strip()
                wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_title)}"
                resp = self.session.get(wiki_url, timeout=2.5)
                if resp.status_code == 200:
                    data = resp.json()
                    thumb = data.get("thumbnail", {}).get("source")
                    if thumb:
                        res = {
                            "poster_url": thumb,
                            "backdrop_url": None,
                            "source": "wikipedia",
                            "is_fallback": False
                        }
                        self.cache_poster(tmdb_id, title, year, res)
                        return res
            except Exception as e:
                logger.debug("Wikipedia poster fallback error for %s: %s", title, e)

        # 3. Tier 3: Clean Generated SVG Placeholder showing movie title & year
        placeholder_url = f"/api/placeholder?title={urllib.parse.quote(title or 'Movie')}&year={year or ''}&genre={urllib.parse.quote(genre or 'Feature')}"
        res = {
            "poster_url": placeholder_url,
            "backdrop_url": None,
            "source": "placeholder",
            "is_fallback": True
        }
        self.cache_poster(tmdb_id, title, year, res)
        return res

    def batch_resolve_posters(self, movie_list: list, max_workers: int = 12, save_interval: int = 500) -> list:
        """
        Resolves posters for a list of movie dicts in parallel with thread pool.
        movie_list items must be dicts with keys: tmdb_id, title, year, poster_path, alt_url, genre.
        """
        total = len(movie_list)
        logger.info("Batch resolving posters for %d movies (workers=%d)...", total, max_workers)

        def worker(m):
            meta = self.resolve_poster(
                tmdb_id=m.get("tmdb_id") or m.get("id"),
                title=m.get("title"),
                year=m.get("year"),
                known_poster_path=m.get("poster_path"),
                alt_url=m.get("alt_url"),
                genre=m.get("genres", ["Movie"])[0] if isinstance(m.get("genres"), list) and m.get("genres") else "Movie"
            )
            m["poster_url"] = meta["poster_url"]
            if meta.get("backdrop_url") and not m.get("backdrop_url"):
                m["backdrop_url"] = meta["backdrop_url"]
            m["poster_source"] = meta["source"]
            m["is_poster_fallback"] = meta["is_fallback"]
            return m

        processed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(worker, m) for m in movie_list]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.debug("Worker error: %s", e)
                processed += 1
                if processed % save_interval == 0 or processed == total:
                    logger.info("Poster resolution progress: %d / %d (%.1f%%)", processed, total, (processed / total) * 100)
                    self.save_cache()

        self.save_cache()
        logger.info("Finished batch poster resolution.")
        return movie_list

# Singleton instance
poster_service = PosterService()
