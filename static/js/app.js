/**
 * ============================================================================
 * CINEMATCH APPLICATION CONTROLLER (app.js)
 * ============================================================================
 * Coordinates API requests, UI rendering, real-time fuzzy search autocomplete,
 * dynamic filtering, catalog pagination, carousels, and movie detail modals.
 */

document.addEventListener("DOMContentLoaded", () => {
  // --------------------------------------------------------------------------
  // DOM Elements
  // --------------------------------------------------------------------------
  const searchInput = document.getElementById("searchInput");
  const searchSubmitBtn = document.getElementById("searchSubmitBtn");
  const searchClearBtn = document.getElementById("searchClearBtn");
  const autocompleteList = document.getElementById("autocompleteList");
  const navSearchTrigger = document.getElementById("navSearchTrigger");

  const weightSlider = document.getElementById("weightSlider");
  const sliderBadge = document.getElementById("sliderBadge");
  const presetButtons = document.querySelectorAll(".preset-btn");

  const recommendationsSection = document.getElementById("recommendationsSection");
  const seedMovieBanner = document.getElementById("seedMovieBanner");
  const resultsTitle = document.getElementById("resultsTitle");
  const resultsMeta = document.getElementById("resultsMeta");
  const resultsGrid = document.getElementById("resultsGrid");
  const viewCarouselBtn = document.getElementById("viewCarouselBtn");
  const viewGridBtn = document.getElementById("viewGridBtn");
  const recScrollLeft = document.getElementById("recScrollLeft");
  const recScrollRight = document.getElementById("recScrollRight");

  const popularGrid = document.getElementById("popularGrid");
  const popularScrollLeft = document.getElementById("popularScrollLeft");
  const popularScrollRight = document.getElementById("popularScrollRight");

  const topRatedGrid = document.getElementById("topRatedGrid");
  const topRatedScrollLeft = document.getElementById("topRatedScrollLeft");
  const topRatedScrollRight = document.getElementById("topRatedScrollRight");

  const browseGrid = document.getElementById("browseGrid");
  const browseCountMeta = document.getElementById("browseCountMeta");
  const genrePills = document.querySelectorAll(".genre-pill");
  const filterYear = document.getElementById("filterYear");
  const filterRating = document.getElementById("filterRating");
  const filterSort = document.getElementById("filterSort");
  const resetFiltersBtn = document.getElementById("resetFiltersBtn");
  const loadMoreBtn = document.getElementById("loadMoreBtn");

  const movieModal = document.getElementById("movieModal");
  const modalContent = document.getElementById("modalContent");
  const modalCloseBtn = document.getElementById("modalCloseBtn");

  // --------------------------------------------------------------------------
  // Application State
  // --------------------------------------------------------------------------
  let catalogSummary = [];       // Cached lightweight movie list
  let currentAlpha = 0.6;
  let activeRecommendationQuery = null;
  let sliderDebounceTimer = null;
  let autocompleteIndex = -1;
  let activeGenre = "all";
  let browsePage = 1;
  let browseLimit = 24;
  let totalBrowsePages = 1;
  let currentRecommendationsView = "carousel";

  // --------------------------------------------------------------------------
  // 1. Initialization
  // --------------------------------------------------------------------------
  initApp();

  async function initApp() {
    loadPreloadCatalog();
    loadPopularShowcase();
    loadTopRatedShowcase();
    loadBrowseCatalog(true);
    setupEventListeners();
  }

  async function loadPreloadCatalog() {
    try {
      catalogSummary = await API.fetchMoviesList();
      console.log(`[CineMatch] Cached ${catalogSummary.length} movies for instant search.`);
    } catch (e) {
      console.warn("[CineMatch] Could not preload catalog summary:", e);
    }
  }

  async function loadPopularShowcase() {
    if (!popularGrid) return;
    popularGrid.innerHTML = UI.renderSkeletonCards(6);
    try {
      const movies = await API.fetchPopularMovies(16);
      popularGrid.innerHTML = movies.map(m => UI.renderMovieCard(m, false)).join("");
    } catch (e) {
      popularGrid.innerHTML = UI.renderEmptyState("Popular movies unavailable.");
    }
  }

  async function loadTopRatedShowcase() {
    if (!topRatedGrid) return;
    topRatedGrid.innerHTML = UI.renderSkeletonCards(6);
    try {
      const movies = await API.fetchTopRatedMovies(16);
      topRatedGrid.innerHTML = movies.map(m => UI.renderMovieCard(m, false)).join("");
    } catch (e) {
      topRatedGrid.innerHTML = UI.renderEmptyState("Top rated movies unavailable.");
    }
  }

  // --------------------------------------------------------------------------
  // 2. Catalog Browsing & Multi-Filtering
  // --------------------------------------------------------------------------
  async function loadBrowseCatalog(reset = false) {
    if (!browseGrid) return;

    if (reset) {
      browsePage = 1;
      browseGrid.innerHTML = UI.renderSkeletonCards(12);
      if (loadMoreBtn) loadMoreBtn.style.display = "none";
    }

    // Build filter parameters
    const params = {
      genre: activeGenre,
      sort: filterSort ? filterSort.value : "popularity",
      min_rating: filterRating && parseFloat(filterRating.value) > 0 ? parseFloat(filterRating.value) : null,
      page: browsePage,
      limit: browseLimit
    };

    // Era parse
    if (filterYear && filterYear.value !== "all") {
      const parts = filterYear.value.split("-");
      if (parts.length === 2) {
        params.year_min = parseInt(parts[0]);
        params.year_max = parseInt(parts[1]);
      }
    }

    try {
      const data = await API.browseCatalog(params);
      totalBrowsePages = data.total_pages || 1;

      if (browseCountMeta) {
        browseCountMeta.textContent = `Showing ${Math.min(browsePage * browseLimit, data.total).toLocaleString()} of ${data.total.toLocaleString()} movies in catalog`;
      }

      const cardsHtml = (data.movies || []).map(m => UI.renderMovieCard(m, false)).join("");

      if (reset) {
        browseGrid.innerHTML = cardsHtml || UI.renderEmptyState("No movies matched your filter criteria.");
      } else {
        browseGrid.insertAdjacentHTML("beforeend", cardsHtml);
      }

      // Handle Load More button visibility
      if (loadMoreBtn) {
        loadMoreBtn.style.display = (browsePage < totalBrowsePages) ? "inline-flex" : "none";
      }

    } catch (err) {
      console.error("[Browse Error]", err);
      if (reset) browseGrid.innerHTML = UI.renderErrorState("Could not load catalog movies.");
    }
  }

  // --------------------------------------------------------------------------
  // 3. Recommendation Engine
  // --------------------------------------------------------------------------
  async function performRecommendation(movieTitleOrId, shouldScroll = true) {
    if (!movieTitleOrId || !String(movieTitleOrId).trim()) return;

    const query = String(movieTitleOrId).trim();
    activeRecommendationQuery = query;
    searchInput.value = query;
    searchClearBtn.style.display = "block";
    closeAutocomplete();

    // Reveal recommendations section
    recommendationsSection.style.display = "block";
    if (shouldScroll) {
      recommendationsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    // Loading state
    const contentPct = Math.round(currentAlpha * 100);
    const collabPct = Math.round((1 - currentAlpha) * 100);
    resultsTitle.textContent = `Finding AI recommendations for "${query}"...`;
    resultsMeta.textContent = `Applying ${contentPct}% plot & cast / ${collabPct}% collaborative balance`;
    if (shouldScroll) {
      seedMovieBanner.innerHTML = "";
    }
    resultsGrid.innerHTML = UI.renderSkeletonCards(8);

    try {
      const data = await API.fetchRecommendations(query, 16, currentAlpha);
      const target = data.query_movie;
      const recs = data.recommendations || [];

      // Update active query to canonical title so subsequent slider tweaks use the exact movie
      activeRecommendationQuery = target.title || query;

      // Render seed banner
      seedMovieBanner.innerHTML = UI.renderSeedMovieBanner(target);

      // Section header
      resultsTitle.innerHTML = `Recommended Because You Liked <span style="color: var(--accent-red);">${UI.escapeHTML(target.title)}</span>`;
      resultsMeta.textContent = `${recs.length} matches generated using ${contentPct}% plot & cast / ${collabPct}% collaborative rating balance`;

      if (recs.length === 0) {
        resultsGrid.innerHTML = UI.renderEmptyState("No strong recommendations found for this title.");
        return;
      }

      // Render recommendation cards
      resultsGrid.innerHTML = recs.map(m => UI.renderMovieCard(m, true)).join("");

    } catch (err) {
      console.error("[Recommendation Failed]", err);
      resultsTitle.textContent = "Search Notice";
      resultsMeta.textContent = "";
      seedMovieBanner.innerHTML = "";
      resultsGrid.innerHTML = UI.renderErrorState(err.message || "Failed to find movie", err.suggestions || []);

      // Attach click events on suggestion chips
      resultsGrid.querySelectorAll(".suggestion-chip").forEach(chip => {
        chip.addEventListener("click", () => {
          const title = chip.getAttribute("data-title");
          if (title) performRecommendation(title);
        });
      });
    }
  }

  // --------------------------------------------------------------------------
  // 4. Autocomplete Search with Debounce & Typo Handling
  // --------------------------------------------------------------------------
  let searchDebounceTimer = null;

  function handleSearchInput(e) {
    const q = e.target.value.trim();
    searchClearBtn.style.display = q ? "block" : "none";

    if (!q || q.length < 2) {
      closeAutocomplete();
      return;
    }

    // 1. Instant local filter against preloaded catalog summary
    const qLower = q.toLowerCase();
    const localMatches = catalogSummary
      .filter(m => m.title && m.title.toLowerCase().includes(qLower))
      .slice(0, 6)
      .map(m => ({ ...m, source: "catalog" }));

    if (localMatches.length > 0) {
      renderAutocomplete(localMatches);
    }

    // 2. Debounced query to backend for fuzzy typo matching and universal live search
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(async () => {
      try {
        const backendMatches = await API.searchTitles(q);
        if (backendMatches && backendMatches.length > 0 && searchInput.value.trim() === q) {
          // Merge avoiding duplicates
          const seenIds = new Set();
          const merged = [];
          for (const item of [...backendMatches, ...localMatches]) {
            const key = item.title.toLowerCase();
            if (!seenIds.has(key)) {
              seenIds.add(key);
              merged.push(item);
            }
          }
          renderAutocomplete(merged.slice(0, 8));
        }
      } catch (err) {
        // Fallback silently to local matches
      }
    }, 200);
  }

  function renderAutocomplete(items) {
    autocompleteIndex = -1;
    autocompleteList.innerHTML = items.map((m, idx) => {
      let badgeClass = "catalog";
      let badgeLabel = m.year ? `${m.year}` : "Catalog";

      if (m.source === "fuzzy") {
        badgeClass = "fuzzy";
        badgeLabel = "Typo Match";
      } else if (m.source === "universal") {
        badgeClass = "live";
        badgeLabel = "✨ Live";
      }

      const thumbUrl = m.poster_url || `/api/placeholder?title=${encodeURIComponent(m.title)}&year=${m.year || ''}`;

      return `
        <div class="autocomplete-item" data-index="${idx}" data-title="${UI.escapeHTML(m.title)}">
          <img class="autocomplete-thumb" src="${thumbUrl}" alt="" loading="lazy" onerror="this.onerror=null; this.src='/api/placeholder?title=${encodeURIComponent(m.title)}';" />
          <div class="autocomplete-info">
            <div class="autocomplete-title">${UI.escapeHTML(m.title)}</div>
            <div class="autocomplete-meta">
              <span class="autocomplete-badge ${badgeClass}">${badgeLabel}</span>
              ${m.rating ? `<span>★ ${m.rating.toFixed(1)}</span>` : ""}
            </div>
          </div>
        </div>
      `;
    }).join("");

    autocompleteList.classList.add("active");

    // Click on autocomplete item
    autocompleteList.querySelectorAll(".autocomplete-item").forEach(item => {
      item.addEventListener("click", () => {
        const title = item.getAttribute("data-title");
        if (title) performRecommendation(title);
      });
    });
  }

  function closeAutocomplete() {
    autocompleteList.classList.remove("active");
    autocompleteList.innerHTML = "";
    autocompleteIndex = -1;
  }

  function handleKeydown(e) {
    const items = autocompleteList.querySelectorAll(".autocomplete-item");
    if (!autocompleteList.classList.contains("active") || items.length === 0) {
      if (e.key === "Enter") {
        e.preventDefault();
        performRecommendation(searchInput.value);
      }
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      autocompleteIndex = (autocompleteIndex + 1) % items.length;
      updateAutocompleteHighlight(items);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      autocompleteIndex = (autocompleteIndex - 1 + items.length) % items.length;
      updateAutocompleteHighlight(items);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (autocompleteIndex >= 0 && autocompleteIndex < items.length) {
        items[autocompleteIndex].click();
      } else {
        performRecommendation(searchInput.value);
      }
    } else if (e.key === "Escape") {
      closeAutocomplete();
    }
  }

  function updateAutocompleteHighlight(items) {
    items.forEach((item, idx) => {
      item.classList.toggle("highlighted", idx === autocompleteIndex);
      if (idx === autocompleteIndex) {
        item.scrollIntoView({ block: "nearest" });
      }
    });
  }

  // --------------------------------------------------------------------------
  // 5. Modal Detail Controller
  // --------------------------------------------------------------------------
  async function openMovieDetails(identifier) {
    if (!identifier) return;
    movieModal.classList.add("active");
    movieModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden"; // Lock background scroll

    modalContent.innerHTML = `
      <div style="padding: 60px 20px; text-align: center;">
        <div class="empty-icon">⏳</div>
        <h3 class="empty-title">Loading movie details...</h3>
      </div>
    `;

    try {
      const data = await API.fetchMovieDetails(identifier);
      modalContent.innerHTML = UI.renderModalContent(data);

      // Attach click to modal CTA recommendation button
      const ctaBtn = modalContent.querySelector(".modal-rec-btn");
      if (ctaBtn) {
        ctaBtn.addEventListener("click", () => {
          closeModal();
          performRecommendation(ctaBtn.getAttribute("data-title"));
        });
      }

      // Attach click to similar movie cards inside modal
      modalContent.querySelectorAll(".modal-similar-card").forEach(card => {
        card.addEventListener("click", () => {
          const simId = card.getAttribute("data-id");
          if (simId) openMovieDetails(simId);
        });
      });

    } catch (err) {
      modalContent.innerHTML = `
        <div style="padding: 40px; text-align: center;">
          <h3 class="empty-title">Could not load details</h3>
          <p class="empty-desc">${UI.escapeHTML(err.message)}</p>
        </div>
      `;
    }
  }

  function closeModal() {
    movieModal.classList.remove("active");
    movieModal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  // --------------------------------------------------------------------------
  // 6. Event Listeners Setup
  // --------------------------------------------------------------------------
  function setupEventListeners() {
    // Search inputs
    searchInput.addEventListener("input", handleSearchInput);
    searchInput.addEventListener("keydown", handleKeydown);

    searchSubmitBtn.addEventListener("click", () => {
      performRecommendation(searchInput.value);
    });

    searchClearBtn.addEventListener("click", () => {
      searchInput.value = "";
      searchClearBtn.style.display = "none";
      closeAutocomplete();
      searchInput.focus();
    });

    // Close autocomplete on click outside
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".search-container")) {
        closeAutocomplete();
      }
    });

    // Global keyboard shortcut '/' to focus search
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement !== searchInput && !e.target.matches("input, textarea, select")) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      } else if (e.key === "Escape" && movieModal.classList.contains("active")) {
        closeModal();
      }
    });

    if (navSearchTrigger) {
      navSearchTrigger.addEventListener("click", () => {
        searchInput.focus();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    // Hybrid Slider Weighting
    weightSlider.addEventListener("input", (e) => {
      currentAlpha = parseFloat(e.target.value);
      updateSliderUI();
    });

    presetButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        const targetAlpha = parseFloat(btn.getAttribute("data-alpha"));
        currentAlpha = targetAlpha;
        weightSlider.value = targetAlpha;
        updateSliderUI();
      });
    });

    function updateSliderUI() {
      const contentPct = Math.round(currentAlpha * 100);
      const collabPct = Math.round((1 - currentAlpha) * 100);
      sliderBadge.textContent = `${contentPct}% Content / ${collabPct}% Collab`;

      // Highlight preset ONLY when the slider is exactly at its value, and highlight none otherwise
      presetButtons.forEach(btn => {
        const pAlpha = parseFloat(btn.getAttribute("data-alpha"));
        if (Math.abs(currentAlpha - pAlpha) < 0.01) {
          btn.classList.add("active");
        } else {
          btn.classList.remove("active");
        }
      });

      // If recommendation results are currently shown, show loading skeleton and re-query with debounce
      if (activeRecommendationQuery && recommendationsSection.style.display === "block") {
        resultsGrid.innerHTML = UI.renderSkeletonCards(8);
        resultsMeta.textContent = `Applying ${contentPct}% plot & cast / ${collabPct}% collaborative balance...`;

        clearTimeout(sliderDebounceTimer);
        sliderDebounceTimer = setTimeout(() => {
          performRecommendation(activeRecommendationQuery, false);
        }, 300);
      }
    }

    // Initialize slider UI state to match default
    updateSliderUI();

    // Recommendation View Switcher (Carousel vs Grid)
    if (viewCarouselBtn && viewGridBtn) {
      viewCarouselBtn.addEventListener("click", () => {
        viewCarouselBtn.classList.add("active");
        viewGridBtn.classList.remove("active");
        resultsGrid.className = "movies-row carousel-mode";
        currentRecommendationsView = "carousel";
      });

      viewGridBtn.addEventListener("click", () => {
        viewGridBtn.classList.add("active");
        viewCarouselBtn.classList.remove("active");
        resultsGrid.className = "movies-grid";
        currentRecommendationsView = "grid";
      });
    }

    // Carousel Navigation Arrows
    setupCarouselScroll(recScrollLeft, recScrollRight, resultsGrid);
    setupCarouselScroll(popularScrollLeft, popularScrollRight, popularGrid);
    setupCarouselScroll(topRatedScrollLeft, topRatedScrollRight, topRatedGrid);

    function setupCarouselScroll(leftBtn, rightBtn, container) {
      if (!leftBtn || !rightBtn || !container) return;
      leftBtn.addEventListener("click", () => {
        container.scrollBy({ left: -600, behavior: "smooth" });
      });
      rightBtn.addEventListener("click", () => {
        container.scrollBy({ left: 600, behavior: "smooth" });
      });
    }

    // Catalog Filter Pills
    genrePills.forEach(pill => {
      pill.addEventListener("click", () => {
        genrePills.forEach(p => p.classList.remove("active"));
        pill.classList.add("active");
        activeGenre = pill.getAttribute("data-genre");
        loadBrowseCatalog(true);
      });
    });

    // Secondary Filter Dropdowns
    if (filterYear) filterYear.addEventListener("change", () => loadBrowseCatalog(true));
    if (filterRating) filterRating.addEventListener("change", () => loadBrowseCatalog(true));
    if (filterSort) filterSort.addEventListener("change", () => loadBrowseCatalog(true));

    if (resetFiltersBtn) {
      resetFiltersBtn.addEventListener("click", () => {
        activeGenre = "all";
        genrePills.forEach(p => p.classList.toggle("active", p.getAttribute("data-genre") === "all"));
        if (filterYear) filterYear.value = "all";
        if (filterRating) filterRating.value = "0";
        if (filterSort) filterSort.value = "popularity";
        loadBrowseCatalog(true);
      });
    }

    // Load More Pagination
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener("click", () => {
        if (browsePage < totalBrowsePages) {
          browsePage++;
          loadBrowseCatalog(false);
        }
      });
    }

    // Delegated Clicks on Movie Cards (Opening Details or Recommending)
    document.addEventListener("click", (e) => {
      // 1. "Similar" button click
      const recBtn = e.target.closest(".btn-recommend-seed");
      if (recBtn) {
        e.stopPropagation();
        const title = recBtn.getAttribute("data-title");
        if (title) performRecommendation(title);
        return;
      }

      // 2. "Details" button or Card Body click
      const card = e.target.closest(".movie-card");
      if (card && !e.target.closest(".card-action-btn")) {
        const id = card.getAttribute("data-id") || card.getAttribute("data-title");
        if (id) openMovieDetails(id);
        return;
      }

      const detailsBtn = e.target.closest(".btn-details");
      if (detailsBtn) {
        e.stopPropagation();
        const id = detailsBtn.getAttribute("data-id");
        if (id) openMovieDetails(id);
        return;
      }
    });

    // Modal close events
    if (modalCloseBtn) modalCloseBtn.addEventListener("click", closeModal);
    if (movieModal) {
      movieModal.addEventListener("click", (e) => {
        if (e.target === movieModal) closeModal();
      });
    }
  }
});
