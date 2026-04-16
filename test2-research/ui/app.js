const basePath = window.location.pathname.replace(/\/$/, '');
const API = basePath + "/api";

async function runResearch() {
    const topics = document.getElementById("topics").value.trim();
    if (!topics) return;

    const btn = document.getElementById("btn-run");
    const status = document.getElementById("status");
    btn.disabled = true;
    status.textContent = "Running research... this may take 1-2 minutes";

    try {
        const res = await fetch(`${API}/research`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                topics,
                prompt_extra: document.getElementById("extra").value.trim(),
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Research failed");
        }

        const data = await res.json();
        document.getElementById("raw").textContent = data.markdown;
        document.getElementById("rendered").innerHTML = renderMarkdown(data.markdown);
        document.getElementById("results-meta").textContent = `Completed in ${data.duration_seconds}s`;
        document.getElementById("results").classList.add("visible");
        status.textContent = "";
    } catch (e) {
        status.textContent = `Error: ${e.message}`;
    } finally {
        btn.disabled = false;
    }
}

function showTab(tab) {
    document.querySelectorAll(".tab").forEach((t, i) => {
        t.classList.toggle("active", (tab === "rendered" && i === 0) || (tab === "raw" && i === 1));
    });
    document.getElementById("rendered").style.display = tab === "rendered" ? "block" : "none";
    document.getElementById("raw").style.display = tab === "raw" ? "block" : "none";
}

function renderMarkdown(md) {
    // Simple markdown to HTML — same regex approach as work's test2-fda
    let html = md
        // Code blocks (must be before other replacements)
        .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
            `<pre><code>${esc(code.trim())}</code></pre>`)
        // Headers
        .replace(/^#### (.+)$/gm, "<h4>$1</h4>")
        .replace(/^### (.+)$/gm, "<h3>$1</h3>")
        .replace(/^## (.+)$/gm, "<h2>$1</h2>")
        .replace(/^# (.+)$/gm, "<h1>$1</h1>")
        // Bold and italic
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        // Inline code
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
        // Blockquotes
        .replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>")
        // Unordered lists
        .replace(/^- (.+)$/gm, "<li>$1</li>")
        // Paragraphs (double newline)
        .replace(/\n\n/g, "</p><p>")
        // Single newlines in non-list context
        .replace(/\n/g, "<br>");

    // Wrap list items
    html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");
    // Clean up nested ul tags
    html = html.replace(/<\/ul><br><ul>/g, "");
    html = html.replace(/<\/ul><\/p><p><ul>/g, "");

    return `<p>${html}</p>`;
}

function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}
