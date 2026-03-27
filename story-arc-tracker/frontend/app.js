/* ═══════════════════════════════════════════════════════════
   Story Arc Tracker — Frontend Application Logic
   ═══════════════════════════════════════════════════════════ */

const API_URL = "http://localhost:8001";

let currentData = null;

// ── Analyze Handler ──────────────────────────────────────────

async function handleAnalyze() {
    const topic = document.getElementById("topic-input").value.trim();
    const articlesRaw = document.getElementById("articles-input").value.trim();

    if (!topic) {
        showToast("Please enter a topic.");
        return;
    }
    if (!articlesRaw) {
        showToast("Please provide articles in JSON format.");
        return;
    }

    let articles;
    try {
        articles = JSON.parse(articlesRaw);
        if (!Array.isArray(articles) || articles.length === 0) {
            throw new Error("Articles must be a non-empty array.");
        }
    } catch (e) {
        showToast("Invalid JSON: " + e.message);
        return;
    }

    const btn = document.getElementById("analyze-btn");
    btn.disabled = true;
    showLoading(true);

    try {
        const response = await fetch(`${API_URL}/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic, articles }),
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Analysis failed");
        }

        currentData = await response.json();
        renderResults(currentData);
    } catch (e) {
        showToast("Error: " + e.message);
    } finally {
        btn.disabled = false;
        showLoading(false);
    }
}

// ── Render All Results ───────────────────────────────────────

function renderResults(data) {
    const container = document.getElementById("results-container");
    container.classList.remove("hidden");

    renderSummary(data.story_summary);
    renderTimeline(data.timeline);
    renderPlayers(data.key_players);
    renderSentiment(data.sentiment_overview);
    renderContrarian(data.contrarian_insights);
    renderPredictions(data.what_to_watch);

    // Smooth scroll to results
    container.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ── Story Summary ────────────────────────────────────────────

function renderSummary(summary) {
    document.getElementById("story-summary").textContent = summary;
}

// ── Timeline ─────────────────────────────────────────────────

function renderTimeline(events) {
    const container = document.getElementById("timeline-container");
    container.innerHTML = "";

    events.forEach((event, index) => {
        const node = document.createElement("div");
        node.className = "timeline-node";
        node.setAttribute("data-sentiment", event.sentiment);
        node.setAttribute("data-event-id", event.event_id);
        node.style.animationDelay = `${index * 0.1}s`;

        node.innerHTML = `
            <div class="node-header">
                <span class="node-title">${escapeHtml(event.title)}</span>
                <span class="node-date">${escapeHtml(event.date)}</span>
            </div>
            <span class="node-sentiment ${event.sentiment}">${event.sentiment}</span>
        `;

        node.addEventListener("click", () => showEventDetail(event, node));
        container.appendChild(node);
    });
}

// ── Event Detail Panel ───────────────────────────────────────

function showEventDetail(event, clickedNode) {
    const panel = document.getElementById("event-detail-panel");
    panel.classList.remove("hidden");

    // Highlight active node
    document.querySelectorAll(".timeline-node").forEach(n => n.classList.remove("active"));
    clickedNode.classList.add("active");

    document.getElementById("detail-title").textContent = event.title;
    document.getElementById("detail-date").textContent = event.date;

    const badge = document.getElementById("detail-sentiment");
    badge.textContent = event.sentiment;
    badge.className = `sentiment-badge ${event.sentiment}`;

    document.getElementById("detail-summary").textContent = event.summary;

    // Entities
    const entitiesDiv = document.getElementById("detail-entities");
    entitiesDiv.innerHTML = event.entities
        .map(e => `<span class="entity-tag">${escapeHtml(e)}</span>`)
        .join("");

    // Sources
    const sourcesDiv = document.getElementById("detail-sources");
    sourcesDiv.textContent = event.source_articles.length
        ? `Sources: ${event.source_articles.join(", ")}`
        : "";

    // Scroll to panel
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function closeDetail() {
    document.getElementById("event-detail-panel").classList.add("hidden");
    document.querySelectorAll(".timeline-node").forEach(n => n.classList.remove("active"));
}

// ── Key Players ──────────────────────────────────────────────

function renderPlayers(players) {
    const grid = document.getElementById("players-grid");
    grid.innerHTML = "";

    if (!players.length) {
        grid.innerHTML = '<p style="color:var(--text-muted)">No key players identified.</p>';
        return;
    }

    players.forEach(player => {
        const card = document.createElement("div");
        card.className = "player-card";
        card.innerHTML = `
            <div class="player-name">${escapeHtml(player.name)}</div>
            <div class="player-role">${escapeHtml(player.role)}</div>
        `;
        grid.appendChild(card);
    });
}

// ── Sentiment Overview ───────────────────────────────────────

function renderSentiment(overview) {
    // Overall badge
    const badge = document.getElementById("overall-sentiment");
    badge.textContent = overview.overall;
    badge.className = `overall-badge sentiment-badge ${overview.overall}`;

    // Trend bar
    const trendBar = document.getElementById("sentiment-trend");
    trendBar.innerHTML = "";

    if (overview.trend.length === 0) {
        trendBar.innerHTML = '<p style="color:var(--text-muted)">No trend data.</p>';
        return;
    }

    overview.trend.forEach(sentiment => {
        const seg = document.createElement("div");
        seg.className = `trend-segment ${sentiment}`;
        seg.title = sentiment;
        trendBar.appendChild(seg);
    });
}

// ── Contrarian Insights ──────────────────────────────────────

function renderContrarian(insights) {
    const mainBox = document.getElementById("mainstream-view");
    mainBox.innerHTML = `
        <h4>Mainstream Narrative</h4>
        <p>${escapeHtml(insights.mainstream)}</p>
    `;

    const list = document.getElementById("contrarian-views");
    list.innerHTML = "";

    if (!insights.contrarian || insights.contrarian.length === 0) {
        list.innerHTML = '<p style="color:var(--text-muted); padding: 12px;">No contrarian perspectives detected.</p>';
        return;
    }

    insights.contrarian.forEach(view => {
        const item = document.createElement("div");
        item.className = "contrarian-item";
        item.textContent = view;
        list.appendChild(item);
    });
}

// ── Predictions ──────────────────────────────────────────────

function renderPredictions(predictions) {
    const grid = document.getElementById("predictions-list");
    grid.innerHTML = "";

    if (!predictions.length) {
        grid.innerHTML = '<p style="color:var(--text-muted)">No predictions generated.</p>';
        return;
    }

    predictions.forEach((pred, i) => {
        const card = document.createElement("div");
        card.className = "prediction-card";
        card.innerHTML = `
            <span class="prediction-num">${i + 1}</span>
            <span>${escapeHtml(pred)}</span>
        `;
        grid.appendChild(card);
    });
}

// ── Utilities ────────────────────────────────────────────────

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function showLoading(show) {
    document.getElementById("loading-overlay").classList.toggle("hidden", !show);
}

function showToast(message) {
    // Simple alert fallback — can be upgraded to a proper toast
    alert(message);
}
