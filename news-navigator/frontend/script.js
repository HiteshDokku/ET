const API = "http://localhost:8000";

async function generate() {

    const topic = document.getElementById("topic").value;
    document.getElementById("briefing").innerHTML = "Generating Intelligence Briefing...";
    const res = await fetch(`${API}/generate`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ topic })
    });

    const data = await res.json();

    // Format briefing
    const briefing = data.briefing;

    let formatted = "";

    for (const key in briefing) {

        formatted += `<h2>${key}</h2>`;

        if (Array.isArray(briefing[key])) {

            formatted += "<ul>";

            briefing[key].forEach(item => {
                formatted += `<li>${item}</li>`;
            });

            formatted += "</ul>";

        } else {

            formatted += `<p>${briefing[key]}</p>`;

        }
    }

    document.getElementById("briefing").innerHTML = formatted;


    // Followups
    let followups = "";

    data.followups.forEach(q => {
        followups += `<div class="follow">${q}</div>`;
    });

    document.getElementById("followups").innerHTML = followups;


    // Sources
    let sources = "";

    data.articles.forEach(article => {
        sources += `
            <div class="source">
                <a href="${article.url}" target="_blank">
                    ${article.title}
                </a>
                <div class="date">${article.date || ""}</div>
            </div>
        `;
    });

    document.getElementById("sources").innerHTML = sources;

}


async function ask() {

    const question = document.getElementById("question").value;

    const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
    });

    const data = await res.json();

    // Markdown formatting
    document.getElementById("answer").innerHTML = marked.parse(data.answer);

}