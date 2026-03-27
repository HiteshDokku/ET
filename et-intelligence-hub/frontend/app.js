const API = "http://localhost:8000";

// ── Helpers ────────────────────────────────────────────────

function show(id) { document.getElementById(id).classList.remove("hidden"); }
function hide(id) { document.getElementById(id).classList.add("hidden"); }

function resetUI() {
    hide("loading-section");
    hide("navigator-results");
    hide("arc-results");
    hide("error-section");
    show("input-section");
    document.getElementById("topic-input").value = "";
}

function showError(msg) {
    hide("loading-section");
    hide("input-section");
    hide("navigator-results");
    hide("arc-results");
    show("error-section");
    document.getElementById("error-message").textContent = msg;
}

function startLoading(title) {
    hide("input-section");
    hide("navigator-results");
    hide("arc-results");
    hide("error-section");
    document.getElementById("loading-title").textContent = title;
    show("loading-section");
}

function renderSources(articles, containerId) {
    const container = document.getElementById(containerId);
    if (!articles || articles.length === 0) {
        container.innerHTML = "<p style='color:var(--text-muted)'>No sources available.</p>";
        return;
    }
    container.innerHTML = articles.map(a => `
        <div class="source-item">
            <a href="${a.url || '#'}" target="_blank">${a.title || 'Untitled'}</a>
            <div class="source-date">${a.date || ''} — ${a.source || 'Economic Times'}</div>
        </div>
    `).join("");
}

// ── News Navigator ─────────────────────────────────────────

async function runNavigator() {
    const topic = document.getElementById("topic-input").value.trim();
    if (!topic) return alert("Please enter a topic.");

    startLoading("🕵️ Agent is gathering articles for your briefing...");

    try {
        const res = await fetch(`${API}/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Server error ${res.status}`);
        }

        const data = await res.json();
        hide("loading-section");
        renderNavigatorResults(data);
        show("navigator-results");

    } catch (e) {
        showError(e.message);
    }
}

function renderNavigatorResults(data) {
    const briefing = data.briefing;
    const container = document.getElementById("briefing-content");

    if (typeof briefing === "string") {
        container.innerHTML = marked.parse(briefing);
    } else {
        let html = "";
        for (const key in briefing) {
            html += `<h2>${key}</h2>`;
            if (Array.isArray(briefing[key])) {
                html += "<ul>" + briefing[key].map(item => `<li>${item}</li>`).join("") + "</ul>";
            } else {
                html += `<p>${briefing[key]}</p>`;
            }
        }
        container.innerHTML = html;
    }

    // Followups
    const followups = data.followups || [];
    if (followups.length > 0) {
        show("followups-container");
        document.getElementById("followups-list").innerHTML = followups.map(q =>
            `<span class="followup-chip" onclick="fillAndAsk(this.textContent)">${q}</span>`
        ).join("");
    } else {
        hide("followups-container");
    }

    // Sources
    renderSources(data.articles, "nav-sources-list");
}

function fillAndAsk(question) {
    document.getElementById("qa-input").value = question;
    askQuestion();
}

async function askQuestion() {
    const question = document.getElementById("qa-input").value.trim();
    if (!question) return;

    const answerEl = document.getElementById("qa-answer");
    show("qa-answer");
    answerEl.innerHTML = "<p style='color:var(--text-muted)'>Thinking...</p>";

    try {
        const res = await fetch(`${API}/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });
        const data = await res.json();
        answerEl.innerHTML = marked.parse(data.answer || "No answer received.");
    } catch (e) {
        answerEl.innerHTML = `<p style="color:var(--accent-red)">Error: ${e.message}</p>`;
    }
}


// ── Story Arc ──────────────────────────────────────────────

async function runStoryArc() {
    const topic = document.getElementById("topic-input").value.trim();
    if (!topic) return alert("Please enter a topic.");

    startLoading("🧬 Agent is building a deep story arc...");

    try {
        const res = await fetch(`${API}/generate-arc`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Server error ${res.status}`);
        }

        const data = await res.json();
        hide("loading-section");
        renderArcResults(data);
        show("arc-results");

    } catch (e) {
        showError(e.message);
    }
}

function renderArcResults(data) {
    // Summary
    document.getElementById("arc-summary").innerHTML = `<p>${data.story_summary || ''}</p>`;

    // Timeline
    const timelineEl = document.getElementById("arc-timeline");
    if (data.timeline && data.timeline.length > 0) {
        timelineEl.innerHTML = data.timeline.map(evt => `
            <div class="timeline-item">
                <div class="timeline-date">${evt.date || 'Unknown'}</div>
                <div class="timeline-title">${evt.title}</div>
                <div class="timeline-summary">${evt.summary}</div>
                <span class="timeline-sentiment sentiment-${evt.sentiment || 'neutral'}">${evt.sentiment || 'neutral'}</span>
            </div>
        `).join("");
    } else {
        timelineEl.innerHTML = "<p style='color:var(--text-muted)'>No timeline events extracted.</p>";
    }

    // Key Players
    const playersEl = document.getElementById("arc-players");
    if (data.key_players && data.key_players.length > 0) {
        playersEl.innerHTML = data.key_players.map(p =>
            `<span class="player-chip" title="${p.role}">${p.name}</span>`
        ).join("");
    } else {
        playersEl.innerHTML = "<p style='color:var(--text-muted)'>No key players identified.</p>";
    }

    // Sentiment
    const sentimentEl = document.getElementById("arc-sentiment");
    if (data.sentiment_overview) {
        const s = data.sentiment_overview;
        const trend = s.trend || [];
        const pos = trend.filter(t => t === "positive").length;
        const neg = trend.filter(t => t === "negative").length;
        const neu = trend.filter(t => t === "neutral").length;
        const total = trend.length || 1;

        let badgeClass = "sentiment-neutral";
        if (s.overall === "positive") badgeClass = "sentiment-positive";
        else if (s.overall === "negative") badgeClass = "sentiment-negative";

        sentimentEl.innerHTML = `
            <div class="sentiment-bar">
                ${pos > 0 ? `<div class="bar-positive" style="width:${(pos/total*100).toFixed(0)}%">${pos}</div>` : ''}
                ${neu > 0 ? `<div class="bar-neutral" style="width:${(neu/total*100).toFixed(0)}%">${neu}</div>` : ''}
                ${neg > 0 ? `<div class="bar-negative" style="width:${(neg/total*100).toFixed(0)}%">${neg}</div>` : ''}
            </div>
            <span class="overall-badge ${badgeClass}">Overall: ${s.overall || 'neutral'}</span>
        `;
    }

    // Contrarian
    const contrarianEl = document.getElementById("arc-contrarian");
    if (data.contrarian_insights) {
        const c = data.contrarian_insights;
        let html = `<div class="contrarian-mainstream"><strong>Mainstream:</strong> ${c.mainstream || 'N/A'}</div>`;
        if (c.contrarian && c.contrarian.length > 0) {
            html += c.contrarian.map(item => `<div class="contrarian-item">${item}</div>`).join("");
        }
        contrarianEl.innerHTML = html;
    }

    // Predictions
    const predictionsEl = document.getElementById("arc-predictions");
    if (data.what_to_watch && data.what_to_watch.length > 0) {
        predictionsEl.innerHTML = data.what_to_watch.map(item =>
            `<div class="prediction-item">${item}</div>`
        ).join("");
    } else {
        predictionsEl.innerHTML = "<p style='color:var(--text-muted)'>No predictions available.</p>";
    }

    // Sources
    renderSources(data.articles, "arc-sources-list");
}

async function askQuestionArc() {
    const question = document.getElementById("qa-input-arc").value.trim();
    if (!question) return;

    const answerEl = document.getElementById("qa-answer-arc");
    show("qa-answer-arc");
    answerEl.innerHTML = "<p style='color:var(--text-muted)'>Thinking...</p>";

    try {
        const res = await fetch(`${API}/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });
        const data = await res.json();
        answerEl.innerHTML = marked.parse(data.answer || "No answer received.");
    } catch (e) {
        answerEl.innerHTML = `<p style="color:var(--accent-red)">Error: ${e.message}</p>`;
    }
}
