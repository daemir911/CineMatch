/**
 * ============================================================================
 * CINEMATCH API CLIENT (api.js)
 * ============================================================================
 * Handles all asynchronous HTTP communication with the Flask backend.
 * Provides caching, query string building, and graceful error handling.
 */

const API = {
  /**
   * Fetches lightweight movie catalog for autocomplete.
   */
  async fetchMoviesList() {
    try {
      const response = await fetch("/api/movies");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (error) {
      console.warn("[API] fetchMoviesList failed:", error);
      return [];
    }
  },

  /**
   * Queries autocomplete search with fuzzy matching and live fallback.
   * @param {string} query
   */
  async searchTitles(query) {
    if (!query || query.trim().length < 2) return [];
    try {
      const response = await fetch(`/api/search_titles?q=${encodeURIComponent(query.trim())}`);
      if (!response.ok) return [];
      return await response.json();
    } catch (e) {
      return [];
    }
  },

  /**
   * Fetches hybrid recommendations for a movie title or ID.
   * @param {string} movieTitleOrId
   * @param {number} count
   * @param {number} alpha
   */
  async fetchRecommendations(movieTitleOrId, count = 12, alpha = 0.6) {
    const encoded = encodeURIComponent(String(movieTitleOrId).trim());
    const url = `/api/recommend?movie=${encoded}&n=${count}&alpha=${alpha}`;
    const response = await fetch(url);
    const data = await response.json();

    if (!response.ok) {
      const err = new Error(data.error || `HTTP error ${response.status}`);
      err.status = response.status;
      err.suggestions = data.suggestions || [];
      throw err;
    }
    return data;
  },

  /**
   * Fetches full movie details including 'More Like This' similar movies.
   * @param {string|number} identifier
   */
  async fetchMovieDetails(identifier) {
    const encoded = encodeURIComponent(String(identifier).trim());
    const response = await fetch(`/api/movie/${encoded}`);
    if (!response.ok) {
      throw new Error(`Movie not found (HTTP ${response.status})`);
    }
    return await response.json();
  },

  /**
   * Fetches popular/trending movies for home shelf.
   */
  async fetchPopularMovies(limit = 16) {
    try {
      const response = await fetch(`/api/popular?limit=${limit}`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.movies || [];
    } catch (e) {
      console.error("[API] fetchPopularMovies error:", e);
      return [];
    }
  },

  /**
   * Fetches top rated movies for home shelf.
   */
  async fetchTopRatedMovies(limit = 16) {
    try {
      const response = await fetch(`/api/top_rated?limit=${limit}`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.movies || [];
    } catch (e) {
      console.error("[API] fetchTopRatedMovies error:", e);
      return [];
    }
  },

  /**
   * Catalog browsing endpoint with filters & sorting.
   * @param {Object} params {genre, year_min, year_max, min_rating, sort, page, limit}
   */
  async browseCatalog(params = {}) {
    const qs = new URLSearchParams();
    if (params.genre && params.genre !== "all") qs.append("genre", params.genre);
    if (params.year_min) qs.append("year_min", params.year_min);
    if (params.year_max) qs.append("year_max", params.year_max);
    if (params.min_rating && params.min_rating > 0) qs.append("min_rating", params.min_rating);
    if (params.sort) qs.append("sort", params.sort);
    if (params.page) qs.append("page", params.page);
    if (params.limit) qs.append("limit", params.limit);

    const response = await fetch(`/api/browse?${qs.toString()}`);
    if (!response.ok) {
      throw new Error(`Browse failed with HTTP ${response.status}`);
    }
    return await response.json();
  },

  /**
   * Fetches all available genres with movie counts.
   */
  async fetchGenres() {
    try {
      const response = await fetch("/api/genres");
      if (!response.ok) return [];
      return await response.json();
    } catch (e) {
      return [];
    }
  }
};
