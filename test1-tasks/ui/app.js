const API = "/api";

async function loadTasks() {
    const status = document.getElementById("filter-status").value;
    const priority = document.getElementById("filter-priority").value;
    const search = document.getElementById("filter-search").value;

    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (priority) params.set("priority", priority);
    if (search) params.set("search", search);

    const res = await fetch(`${API}/tasks?${params}`);
    const tasks = await res.json();
    render(tasks);
}

function render(tasks) {
    const list = document.getElementById("task-list");
    if (!tasks.length) {
        list.innerHTML = '<div class="empty">No tasks yet. Add one above.</div>';
        return;
    }
    list.innerHTML = tasks.map(t => `
        <div class="task-card" id="task-${t.id}">
            <div class="task-header">
                <span class="task-title" onclick="toggle(${t.id})">${esc(t.title)}</span>
                <div class="task-meta">
                    <span class="badge badge-${t.priority}">${t.priority}</span>
                    <span class="badge badge-${t.status}">${t.status.replace("_", " ")}</span>
                    <span>${timeAgo(t.created_at)}</span>
                </div>
            </div>
            <div class="task-detail" id="detail-${t.id}">
                <div class="detail-row">
                    <label>Title</label>
                    <input value="${esc(t.title)}" onchange="patch(${t.id}, 'title', this.value)">
                </div>
                <div class="detail-row">
                    <label>Description</label>
                    <textarea onchange="patch(${t.id}, 'description', this.value)">${esc(t.description || "")}</textarea>
                </div>
                <div class="detail-row">
                    <label>Status</label>
                    <select onchange="patch(${t.id}, 'status', this.value)">
                        <option value="pending" ${t.status === "pending" ? "selected" : ""}>Pending</option>
                        <option value="in_progress" ${t.status === "in_progress" ? "selected" : ""}>In Progress</option>
                        <option value="complete" ${t.status === "complete" ? "selected" : ""}>Complete</option>
                    </select>
                </div>
                <div class="detail-row">
                    <label>Priority</label>
                    <select onchange="patch(${t.id}, 'priority', this.value)">
                        <option value="low" ${t.priority === "low" ? "selected" : ""}>Low</option>
                        <option value="medium" ${t.priority === "medium" ? "selected" : ""}>Medium</option>
                        <option value="high" ${t.priority === "high" ? "selected" : ""}>High</option>
                    </select>
                </div>
                <button class="btn-delete" onclick="del(${t.id})">Delete</button>
            </div>
        </div>
    `).join("");
}

function toggle(id) {
    document.getElementById(`detail-${id}`).classList.toggle("open");
}

async function addTask() {
    const input = document.getElementById("new-title");
    const title = input.value.trim();
    if (!title) return;
    const priority = document.getElementById("new-priority").value;
    await fetch(`${API}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, priority }),
    });
    input.value = "";
    loadTasks();
}

async function patch(id, field, value) {
    await fetch(`${API}/tasks/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [field]: value }),
    });
    loadTasks();
}

async function del(id) {
    await fetch(`${API}/tasks/${id}`, { method: "DELETE" });
    loadTasks();
}

function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

function timeAgo(ts) {
    const diff = Date.now() - new Date(ts + "Z").getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
}

// Enter key submits
document.getElementById("new-title").addEventListener("keydown", e => {
    if (e.key === "Enter") addTask();
});

loadTasks();
