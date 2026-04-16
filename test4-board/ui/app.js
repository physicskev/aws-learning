const basePath = window.location.pathname.replace(/\/$/, '');
const API = basePath + "/api";
let currentView = "list";
let showDone = false;
let filterData = {};

const TYPE_ICONS = { Bug: "\u{1F41B}", Feature: "\u2728", Task: "\u2611\uFE0F", Improvement: "\u{1F527}", Epic: "\u26A1" };
const COLUMN_ORDER = ["Backlog", "To Do", "In Progress", "In Review", "Done", "Cancelled"];

async function init() {
    const res = await fetch(`${API}/filters`);
    filterData = await res.json();
    populateSelect("f-status", filterData.statuses);
    populateSelect("f-type", filterData.types);
    populateSelect("f-priority", filterData.priorities);
    populateSelect("f-assignee", filterData.assignees);
    populateSelect("f-label", filterData.labels);
    loadTickets();
}

function populateSelect(id, items) {
    const el = document.getElementById(id);
    items.forEach(i => { const o = document.createElement("option"); o.value = i; o.textContent = i; el.appendChild(o); });
}

function switchView(view) {
    currentView = view;
    document.querySelectorAll(".view-tab").forEach((t, i) => {
        t.classList.toggle("active", (view === "list" && i === 0) || (view === "board" && i === 1));
    });
    document.getElementById("list-view").style.display = view === "list" ? "block" : "none";
    document.getElementById("board-view").style.display = view === "board" ? "block" : "none";
    if (view === "board") loadBoard();
    else loadTickets();
}

// --- List View ---
async function loadTickets() {
    const params = new URLSearchParams();
    const status = document.getElementById("f-status").value;
    const type = document.getElementById("f-type").value;
    const priority = document.getElementById("f-priority").value;
    const assignee = document.getElementById("f-assignee").value;
    const label = document.getElementById("f-label").value;
    const search = document.getElementById("f-search").value;
    if (status) params.set("status", status);
    if (type) params.set("type", type);
    if (priority) params.set("priority", priority);
    if (assignee) params.set("assignee", assignee);
    if (label) params.set("label", label);
    if (search) params.set("search", search);

    const res = await fetch(`${API}/tickets?${params}`);
    const tickets = await res.json();
    document.getElementById("stats").textContent = `${tickets.length} tickets`;
    renderList(tickets);
}

function renderList(tickets) {
    const el = document.getElementById("ticket-list");
    if (!tickets.length) { el.innerHTML = '<div style="text-align:center;color:#999;padding:40px">No tickets found.</div>'; return; }
    el.innerHTML = tickets.map(t => `
        <div class="ticket-row" onclick="openTicket(${t.id})">
            <span class="ticket-type-icon">${TYPE_ICONS[t.type] || ""}</span>
            <span class="ticket-key">${esc(t.key)}</span>
            <span class="ticket-summary">${esc(t.summary)}</span>
            <span class="badge badge-${t.priority}">${t.priority}</span>
            <span class="badge badge-${t.status.replace(/ /g,'')}">${t.status}</span>
            <span class="ticket-assignee">${esc(t.assignee)}</span>
        </div>
    `).join("");
}

// --- Board View ---
async function loadBoard() {
    const res = await fetch(`${API}/board`);
    const data = await res.json();
    const board = document.getElementById("board");
    const columns = COLUMN_ORDER.filter(s => {
        if (!showDone && (s === "Done" || s === "Cancelled")) return false;
        return true;
    });
    board.innerHTML = columns.map(status => {
        const tickets = data[status] || [];
        return `
            <div class="board-column">
                <div class="column-header">${status} <span class="count">${tickets.length}</span></div>
                ${tickets.map(t => `
                    <div class="board-card" onclick="openTicket(${t.id})">
                        <span class="ticket-key">${esc(t.key)}</span>
                        <div style="margin-top:4px">${esc(t.summary)}</div>
                        <div class="board-card-meta">
                            <span class="badge badge-${t.priority}" style="font-size:10px">${t.priority}</span>
                            <span style="font-size:11px;color:#888">${esc(t.assignee)}</span>
                        </div>
                    </div>
                `).join("")}
            </div>
        `;
    }).join("");
}

function toggleDone() {
    showDone = !showDone;
    document.getElementById("toggle-done").textContent = showDone ? "Hide Done/Cancelled" : "Show Done/Cancelled";
    loadBoard();
}

// --- Ticket Detail Modal ---
async function openTicket(id) {
    const res = await fetch(`${API}/tickets/${id}`);
    const t = await res.json();
    const modal = document.getElementById("modal");
    document.getElementById("modal-content").innerHTML = `
        <h2>${TYPE_ICONS[t.type] || ""} ${esc(t.key)} — ${esc(t.summary)}</h2>
        <div class="modal-row">
            <label>Summary</label>
            <input value="${esc(t.summary)}" onchange="patchTicket(${t.id},'summary',this.value)">
        </div>
        <div class="modal-row">
            <label>Status</label>
            <select onchange="patchTicket(${t.id},'status',this.value)">
                ${COLUMN_ORDER.map(s => `<option value="${s}" ${t.status===s?"selected":""}>${s}</option>`).join("")}
            </select>
        </div>
        <div class="modal-row">
            <label>Type</label>
            <select onchange="patchTicket(${t.id},'type',this.value)">
                ${(filterData.types||[]).map(ty => `<option value="${ty}" ${t.type===ty?"selected":""}>${ty}</option>`).join("")}
            </select>
        </div>
        <div class="modal-row">
            <label>Priority</label>
            <select onchange="patchTicket(${t.id},'priority',this.value)">
                ${["Critical","High","Medium","Low"].map(p => `<option value="${p}" ${t.priority===p?"selected":""}>${p}</option>`).join("")}
            </select>
        </div>
        <div class="modal-row">
            <label>Assignee</label>
            <select onchange="patchTicket(${t.id},'assignee',this.value)">
                <option value="">Unassigned</option>
                ${(filterData.assignees||[]).map(a => `<option value="${a}" ${t.assignee===a?"selected":""}>${a}</option>`).join("")}
            </select>
        </div>
        <div class="modal-row">
            <label>Labels</label>
            <input value="${esc(t.labels)}" onchange="patchTicket(${t.id},'labels',this.value)">
        </div>
        <div class="modal-row">
            <label>Description</label>
            <textarea onchange="patchTicket(${t.id},'description',this.value)">${esc(t.description||"")}</textarea>
        </div>
        <div class="comments-section">
            <h3>Comments (${(t.comments||[]).length})</h3>
            ${(t.comments||[]).map(c => `
                <div class="comment">
                    <div class="comment-meta">${esc(c.author)} &middot; ${c.created_at}</div>
                    ${esc(c.text)}
                </div>
            `).join("")}
            <div class="comment-add">
                <input id="comment-text" placeholder="Add a comment...">
                <button class="btn btn-primary" onclick="addComment(${t.id})">Add</button>
            </div>
        </div>
        <div class="modal-actions">
            <button class="btn btn-danger" onclick="deleteTicket(${t.id})">Delete</button>
            <button class="btn btn-secondary" onclick="closeModal()">Close</button>
        </div>
    `;
    modal.classList.add("open");
}

function closeModal() {
    document.getElementById("modal").classList.remove("open");
    if (currentView === "board") loadBoard(); else loadTickets();
}

async function patchTicket(id, field, value) {
    await fetch(`${API}/tickets/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [field]: value }),
    });
}

async function deleteTicket(id) {
    await fetch(`${API}/tickets/${id}`, { method: "DELETE" });
    closeModal();
}

async function addComment(ticketId) {
    const input = document.getElementById("comment-text");
    const text = input.value.trim();
    if (!text) return;
    await fetch(`${API}/tickets/${ticketId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ author: "Kev", text }),
    });
    openTicket(ticketId);
}

// --- Create Modal ---
function showCreateModal() {
    const modal = document.getElementById("modal");
    document.getElementById("modal-content").innerHTML = `
        <h2>New Ticket</h2>
        <div class="modal-row"><label>Summary</label><input id="new-summary"></div>
        <div class="modal-row"><label>Type</label>
            <select id="new-type">${(filterData.types||[]).map(t => `<option value="${t}">${t}</option>`).join("")}</select>
        </div>
        <div class="modal-row"><label>Priority</label>
            <select id="new-priority">${["Critical","High","Medium","Low"].map(p => `<option value="${p}" ${p==="Medium"?"selected":""}>${p}</option>`).join("")}</select>
        </div>
        <div class="modal-row"><label>Assignee</label>
            <select id="new-assignee"><option value="">Unassigned</option>${(filterData.assignees||[]).map(a => `<option value="${a}">${a}</option>`).join("")}</select>
        </div>
        <div class="modal-row"><label>Description</label><textarea id="new-desc"></textarea></div>
        <div class="modal-actions">
            <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
            <button class="btn btn-primary" onclick="createTicket()">Create</button>
        </div>
    `;
    modal.classList.add("open");
}

async function createTicket() {
    const summary = document.getElementById("new-summary").value.trim();
    if (!summary) return;
    await fetch(`${API}/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            summary,
            type: document.getElementById("new-type").value,
            priority: document.getElementById("new-priority").value,
            assignee: document.getElementById("new-assignee").value,
            description: document.getElementById("new-desc").value,
        }),
    });
    closeModal();
}

function esc(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

init();
