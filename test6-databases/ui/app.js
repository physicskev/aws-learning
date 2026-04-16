// Detect base path: works both locally (/) and behind Nginx (/test6/)
const basePath = window.location.pathname.replace(/\/$/, '');
const API = basePath + "/api";

// --- Status ---
async function checkHealth() {
    try {
        const res = await fetch(`${API}/health`);
        const data = await res.json();
        const bar = document.getElementById("status-bar");
        const pgStatus = data.postgres === "connected";
        const dyStatus = data.dynamodb === "connected";
        bar.innerHTML = `
            <span><span class="status-dot ${pgStatus ? 'ok' : 'err'}"></span>Postgres: ${data.postgres}</span>
            <span><span class="status-dot ${dyStatus ? 'ok' : 'err'}"></span>DynamoDB: ${data.dynamodb}</span>
        `;
    } catch (e) {
        document.getElementById("status-bar").innerHTML = `<span class="status-dot err"></span>API unreachable`;
    }
}

// --- Tabs ---
function switchTab(tab) {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
    document.querySelector(`.tab.${tab}`).classList.add("active");
    document.getElementById(`${tab}-section`).classList.add("active");
    if (tab === "dynamo") dynamoLoad();
    else pgLoad();
}

// --- Postgres: Contacts ---
async function pgLoad() {
    const search = document.getElementById("pg-search").value;
    const params = search ? `?search=${encodeURIComponent(search)}` : "";
    const res = await fetch(`${API}/pg/contacts${params}`);
    const contacts = await res.json();
    const el = document.getElementById("pg-list");
    if (!contacts.length) { el.innerHTML = '<div class="empty">No contacts. Add one above.</div>'; return; }
    el.innerHTML = contacts.map(c => `
        <div class="card">
            <div class="card-header">
                <span class="card-title">${esc(c.name)}</span>
                <span class="badge badge-pg">Postgres</span>
            </div>
            <div class="card-detail">
                ${c.email ? `<span>${esc(c.email)}</span>` : ""}
                ${c.company ? ` &middot; ${esc(c.company)}` : ""}
                ${c.notes ? `<br><em>${esc(c.notes)}</em>` : ""}
            </div>
            <div class="card-meta">${new Date(c.created_at).toLocaleDateString()}</div>
            <div class="card-actions">
                <button class="btn btn-danger btn-sm" onclick="pgDelete(${c.id})">Delete</button>
            </div>
        </div>
    `).join("");
}

async function pgCreate() {
    const name = document.getElementById("pg-name").value.trim();
    if (!name) return;
    await fetch(`${API}/pg/contacts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name,
            email: document.getElementById("pg-email").value.trim() || null,
            company: document.getElementById("pg-company").value.trim() || null,
        }),
    });
    document.getElementById("pg-name").value = "";
    document.getElementById("pg-email").value = "";
    document.getElementById("pg-company").value = "";
    pgLoad();
}

async function pgDelete(id) {
    await fetch(`${API}/pg/contacts/${id}`, { method: "DELETE" });
    pgLoad();
}

// --- DynamoDB: Bookmarks ---
async function dynamoLoad() {
    const cat = document.getElementById("dynamo-filter").value;
    const params = cat ? `?category=${encodeURIComponent(cat)}` : "";
    const res = await fetch(`${API}/dynamo/bookmarks${params}`);
    const items = await res.json();

    // Update category filter
    const catRes = await fetch(`${API}/dynamo/categories`);
    const cats = await catRes.json();
    const filter = document.getElementById("dynamo-filter");
    const current = filter.value;
    filter.innerHTML = '<option value="">All Categories</option>';
    cats.forEach(c => { const o = document.createElement("option"); o.value = c; o.textContent = c; filter.appendChild(o); });
    filter.value = current;

    const el = document.getElementById("dynamo-list");
    if (!items.length) { el.innerHTML = '<div class="empty">No bookmarks. Add one above.</div>'; return; }
    el.innerHTML = items.map(b => {
        const cat = b.pk.replace("BOOKMARK#", "");
        return `
        <div class="card">
            <div class="card-header">
                <span class="card-title"><a href="${esc(b.url)}" target="_blank">${esc(b.title)}</a></span>
                <span class="badge badge-dynamo">${esc(cat)}</span>
            </div>
            <div class="card-detail">${esc(b.url)}${b.notes ? `<br><em>${esc(b.notes)}</em>` : ""}</div>
            <div class="card-meta">${b.created_at || ""}</div>
            <div class="card-actions">
                <button class="btn btn-danger btn-sm" onclick="dynamoDelete('${esc(cat)}','${esc(b.sk)}')">Delete</button>
            </div>
        </div>
    `}).join("");
}

async function dynamoCreate() {
    const title = document.getElementById("dynamo-title").value.trim();
    const url = document.getElementById("dynamo-url").value.trim();
    if (!title || !url) return;
    await fetch(`${API}/dynamo/bookmarks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            category: document.getElementById("dynamo-cat-input").value,
            title,
            url,
            notes: document.getElementById("dynamo-notes").value.trim() || null,
        }),
    });
    document.getElementById("dynamo-title").value = "";
    document.getElementById("dynamo-url").value = "";
    document.getElementById("dynamo-notes").value = "";
    dynamoLoad();
}

async function dynamoDelete(category, id) {
    await fetch(`${API}/dynamo/bookmarks/${encodeURIComponent(category)}/${encodeURIComponent(id)}`, { method: "DELETE" });
    dynamoLoad();
}

function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

// Init
checkHealth();
pgLoad();
