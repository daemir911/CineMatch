/**
 * ============================================================================
 * CINEMATCH UI RENDERERS (ui.js)
 * ============================================================================
 * Modular, clean DOM rendering functions for cards, carousels, modals,
 * skeleton shimmers, and empty/error states.
 */

const UI = {
  /**
   * Escapes special characters to prevent XSS vulnerabilities.
   */
  escapeHTML(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },

  /**
   * Renders a modern Netflix / Letterboxd style movie card.
   * @param {Object} movie
   * @param {boolean} isRecommendation
   */
  renderMovieCard(movie, isRecommendation = false) {
    const id = movie.tmdb_id || movie.id;
    const title = UI.escapeHTML(movie.title || "Untitled");
    const yearText = movie.year ? movie.year : "N/A";
    const ratingVal = typeof movie.rating === "number" ? movie.rating.toFixed(1) : (typeof movie.vote_average === "number" ? movie.vote_average.toFixed(1) : "—");
    
    // Poster URL with guaranteed fallback
    const rawPoster = movie.poster_url;
    const fallbackPoster = `/api/placeholder?title=${encodeURIComponent(movie.title || 'Movie')}&year=${movie.year || ''}`;
    const posterSrc = (rawPoster && rawPoster.trim() && rawPoster !== "nan") ? rawPoster : fallbackPoster;

    // Badges
    let scoreTooltip = "";
    if (typeof movie.content_score === "number" && typeof movie.collab_score === "number") {
      scoreTooltip = `title="Plot & Cast: ${Math.round(movie.content_score * 100)}% · Viewer Ratings: ${Math.round(movie.collab_score * 100)}%"`;
    }
    const scoreBadge = (isRecommendation && typeof movie.score === "number")
      ? `<span class="card-score-badge" ${scoreTooltip}>${Math.round(movie.score * 100)}% Match</span>`
      : "";

    // Genres (first 2)
    const genreBadges = (movie.genres || [])
      .slice(0, 2)
      .map(g => `<span class="card-genre-tag">${UI.escapeHTML(g)}</span>`)
      .join("");

    // "Why recommended" tag
    const whySnippet = movie.why_recommended
      ? `<div class="card-why-wrapper">
           <p class="card-why-text" title="${UI.escapeHTML(movie.why_recommended)}">
             💡 ${UI.escapeHTML(movie.why_recommended)}
           </p>
         </div>`
      : "";

    return `
      <article class="movie-card" data-id="${id}" data-title="${title}" tabindex="0" role="button" aria-label="${title}">
        <div class="card-poster-wrapper">
          <img 
            class="card-poster" 
            src="${posterSrc}" 
            alt="${title} Poster" 
            loading="lazy" 
            onerror="this.onerror=null; this.src='${fallbackPoster}';"
          />
          <div class="card-rating-badge" title="Audience Rating: ${ratingVal} / 10">
            ★ ${ratingVal}
          </div>
          ${scoreBadge}
          
          <div class="card-hover-actions">
            <button class="card-action-btn btn-details" data-id="${id}" title="View details">Details</button>
            <button class="card-action-btn btn-recommend-seed" data-title="${title}" title="Find recommendations like this">Similar</button>
          </div>
        </div>
        
        <div class="card-content">
          <h3 class="card-title" title="${title}">${title}</h3>
          <div class="card-meta">
            <span>${yearText}</span>
            ${movie.director && movie.director !== "Unknown" ? `<span>• ${UI.escapeHTML(movie.director)}</span>` : ""}
          </div>
          <div class="card-genres">
            ${genreBadges}
          </div>
          ${whySnippet}
        </div>
      </article>
    `;
  },

  /**
   * Renders the Seed Movie Hero Banner for the recommendations section.
   * @param {Object} movie
   */
  renderSeedMovieBanner(movie) {
    const title = UI.escapeHTML(movie.title || "Selected Movie");
    const yearText = movie.year ? `(${movie.year})` : "";
    const posterSrc = movie.poster_url || `/api/placeholder?title=${encodeURIComponent(movie.title)}&year=${movie.year || ''}`;
    const backdropStyle = movie.backdrop_url ? `style="background-image: url('${movie.backdrop_url}')"` : "";
    const genresList = (movie.genres || []).join(", ") || "General";
    const dirText = movie.director && movie.director !== "Unknown" ? `Directed by ${UI.escapeHTML(movie.director)}` : "";
    const isLive = movie.is_external ? `<span class="autocomplete-badge live">✨ Live Discovery</span>` : "";

    return `
      <div class="seed-backdrop" ${backdropStyle}></div>
      <img class="seed-poster" src="${posterSrc}" alt="${title} Poster" onerror="this.onerror=null; this.src='/api/placeholder?title=${encodeURIComponent(movie.title)}';" />
      <div class="seed-details">
        <span class="seed-badge">BECAUSE YOU LIKED ${isLive}</span>
        <h3 class="seed-title">${title} ${yearText}</h3>
        <div class="seed-meta">
          ${dirText ? `<span>${dirText}</span>` : ""}
          <span>Genres: ${UI.escapeHTML(genresList)}</span>
          ${movie.rating ? `<span>★ ${movie.rating.toFixed(1)} / 10</span>` : ""}
        </div>
      </div>
    `;
  },

  /**
   * Shimmer skeleton placeholders while data loads.
   * @param {number} count
   */
  renderSkeletonCards(count = 8) {
    let html = "";
    for (let i = 0; i < count; i++) {
      html += `
        <div class="skeleton-card" aria-hidden="true">
          <div class="skeleton-poster"></div>
          <div class="skeleton-body">
            <div class="skeleton-line medium"></div>
            <div class="skeleton-line short"></div>
          </div>
        </div>
      `;
    }
    return html;
  },

  /**
   * Renders Movie Detail Modal body content including 'More Like This' carousel.
   * @param {Object} movie
   */
  renderModalContent(movie) {
    const title = UI.escapeHTML(movie.title || "Untitled");
    const yearText = movie.year || "N/A";
    const ratingVal = typeof movie.rating === "number" ? movie.rating.toFixed(1) : (movie.vote_average ? movie.vote_average.toFixed(1) : "—");
    const voteCount = movie.vote_count ? `${movie.vote_count.toLocaleString()} votes` : "";
    const runtime = movie.runtime ? `${movie.runtime} min` : "";
    const fallbackPoster = `/api/placeholder?title=${encodeURIComponent(movie.title || 'Movie')}&year=${movie.year || ''}`;
    const posterSrc = movie.poster_url || fallbackPoster;
    const backdropStyle = movie.backdrop_url ? `style="background-image: url('${movie.backdrop_url}')"` : "";

    const genresHtml = (movie.genres || []).map(g => `<span class="modal-chip">${UI.escapeHTML(g)}</span>`).join("");
    const castHtml = (movie.cast || []).map(a => `<span class="modal-chip">${UI.escapeHTML(a)}</span>`).join("") || `<span class="modal-chip">Cast details available online</span>`;

    // Similar movies cards
    const similarHtml = (movie.similar_movies || []).map(sim => {
      const simTitle = UI.escapeHTML(sim.title);
      const simPoster = sim.poster_url || `/api/placeholder?title=${encodeURIComponent(sim.title)}`;
      return `
        <div class="modal-similar-card" data-id="${sim.tmdb_id || sim.id}" data-title="${simTitle}" title="${simTitle}">
          <img class="modal-similar-poster" src="${simPoster}" alt="${simTitle}" loading="lazy" onerror="this.onerror=null; this.src='/api/placeholder?title=${encodeURIComponent(sim.title)}';" />
          <div class="modal-similar-title">${simTitle}</div>
        </div>
      `;
    }).join("");

    return `
      <div class="modal-backdrop-banner" ${backdropStyle}></div>
      
      <div class="modal-header-content">
        <img class="modal-poster" src="${posterSrc}" alt="${title} Poster" onerror="this.onerror=null; this.src='${fallbackPoster}';" />
        <div class="modal-title-group">
          <h2 class="modal-title">${title}</h2>
          ${movie.tagline ? `<p class="modal-tagline">"${UI.escapeHTML(movie.tagline)}"</p>` : ""}
          <div class="modal-meta-row">
            <span>${yearText}</span>
            ${runtime ? `<span>• ${runtime}</span>` : ""}
            ${movie.language ? `<span>• ${UI.escapeHTML(movie.language.toUpperCase())}</span>` : ""}
            <span class="modal-rating-badge">★ ${ratingVal} ${voteCount ? `<span style="color: var(--text-muted); font-size: 11px;">(${voteCount})</span>` : ""}</span>
          </div>
        </div>
      </div>

      <div class="modal-body-content">
        <div class="modal-actions">
          <button class="modal-cta-btn modal-rec-btn" data-title="${title}">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
            </svg>
            <span>Get Recommendations Based on This</span>
          </button>
        </div>

        <div class="modal-section-title">Overview</div>
        <p class="modal-overview">${UI.escapeHTML(movie.overview || "No overview plot available.")}</p>

        <div class="modal-section-title">Genres</div>
        <div class="modal-chips-row">${genresHtml}</div>

        <div class="modal-section-title">Director</div>
        <div class="modal-chips-row">
          <span class="modal-chip" style="background: rgba(229, 9, 20, 0.15); border-color: rgba(229, 9, 20, 0.3); color: #fff;">
            🎬 ${UI.escapeHTML(movie.director || "Unknown")}
          </span>
        </div>

        <div class="modal-section-title">Top Cast</div>
        <div class="modal-chips-row">${castHtml}</div>

        ${similarHtml ? `
          <div class="modal-section-title">More Like This</div>
          <div class="modal-similar-grid">${similarHtml}</div>
        ` : ""}
      </div>
    `;
  },

  /**
   * Renders friendly empty state when search or filter yields no results.
   */
  renderEmptyState(message = "No movies found.", suggestions = []) {
    let suggHtml = "";
    if (suggestions && suggestions.length > 0) {
      suggHtml = `
        <div class="suggestions-cloud">
          ${suggestions.map(s => `<button class="suggestion-chip" data-title="${UI.escapeHTML(s)}">${UI.escapeHTML(s)}</button>`).join("")}
        </div>
      `;
    }

    return `
      <div class="empty-state">
        <div class="empty-icon">🍿</div>
        <h3 class="empty-title">No Movies Found</h3>
        <p class="empty-desc">${UI.escapeHTML(message)}</p>
        ${suggHtml}
      </div>
    `;
  },

  /**
   * Renders error state.
   */
  renderErrorState(message, suggestions = []) {
    return UI.renderEmptyState(`Error: ${message}`, suggestions);
  }
};
