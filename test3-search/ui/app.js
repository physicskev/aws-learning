const API = "/api";
let searchTimer = null;

// --- Init ---
async function init() {
    const res = await fetch(`${API}/filters`);
    const data = await res.json();

    const genreSelect = document.getElementById("filter-genre");
    data.genres.forEach(g => {
        const opt = document.createElement("option");
        opt.value = g; opt.textContent = g;
        genreSelect.appendChild(opt);
    });

    const dirSelect = document.getElementById("filter-director");
    data.directors.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d; opt.textContent = d;
        dirSelect.appendChild(opt);
    });

    loadMovies();
}

// --- Tabs ---
function switchTab(tab) {
    document.querySelectorAll(".tab").forEach((t, i) => {
        t.classList.toggle("active", (tab === "browse" && i === 0) || (tab === "search" && i === 1));
    });
    document.getElementById("browse-view").style.display = tab === "browse" ? "block" : "none";
    document.getElementById("search-view").style.display = tab === "search" ? "block" : "none";
    if (tab === "search") document.getElementById("search-input").focus();
}

// --- Browse ---
async function loadMovies() {
    const genre = document.getElementById("filter-genre").value;
    const director = document.getElementById("filter-director").value;
    const sort = document.getElementById("filter-sort").value;

    const params = new URLSearchParams({ sort, limit: 50, offset: 0 });
    if (genre) params.set("genre", genre);
    if (director) params.set("director", director);

    const res = await fetch(`${API}/movies?${params}`);
    const data = await res.json();

    document.getElementById("browse-stats").textContent = `${data.total} movies`;
    renderMovies("browse-list", data.movies, false);
}

// --- Search ---
function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(doSearch, 200);
}

async function doSearch() {
    const q = document.getElementById("search-input").value.trim();
    const mode = document.getElementById("search-mode").value;

    if (!q) {
        document.getElementById("search-stats").textContent = "";
        document.getElementById("search-list").innerHTML = '<div class="empty">Type to search...</div>';
        return;
    }

    const res = await fetch(`${API}/search?q=${encodeURIComponent(q)}&mode=${mode}`);
    const data = await res.json();

    document.getElementById("search-stats").textContent = `${data.count} result${data.count !== 1 ? "s" : ""}`;
    renderMovies("search-list", data.results, mode === "review");
}

// --- Render ---
function renderMovies(containerId, movies, showReviews) {
    const container = document.getElementById(containerId);
    if (!movies.length) {
        container.innerHTML = '<div class="empty">No movies found.</div>';
        return;
    }
    container.innerHTML = movies.map(m => `
        <div class="movie-card" onclick="toggleDetail(${m.id})">
            <div class="movie-header">
                <span class="movie-title">${m.title_snippet || esc(m.title)}</span>
                <span class="movie-rating">${m.rating}</span>
            </div>
            <div class="movie-meta">
                <span class="badge badge-genre">${esc(m.genre)}</span>
                <span>${m.year}</span>
                <span>${esc(m.director)}</span>
                <span>${m.runtime_minutes}min</span>
                <span>$${m.budget_millions}M</span>
            </div>
            <div class="movie-synopsis">${m.synopsis_snippet || esc(m.synopsis)}</div>
            ${showReviews && m.matched_reviews ? m.matched_reviews.map(r =>
                `<div class="movie-reviews"><div class="review-snippet">"${r.snippet}"</div></div>`
            ).join("") : ""}
            <div class="movie-detail" id="detail-${m.id}">
                <div class="detail-section"><strong>Cast</strong><p>${esc(m.cast_list)}</p></div>
                <div class="detail-section"><strong>Synopsis</strong><p>${esc(m.synopsis)}</p></div>
            </div>
        </div>
    `).join("");
}

function toggleDetail(id) {
    document.getElementById(`detail-${id}`).classList.toggle("open");
}

function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

init();
