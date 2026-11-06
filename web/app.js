// TaskFlow - frontend. Todas las peticiones van a /api, que Nginx reenvía al contenedor "api".
const API = "/api";
const STATUSES = ["todo", "in_progress", "done"];
const PRIORITY_LABEL = { low: "Baja", medium: "Media", high: "Alta" };

const state = { token: localStorage.getItem("tf_token"), user: null, projects: [], current: null, members: [], tasks: [], mode: "login" };
const $ = (sel) => document.querySelector(sel);

// ---------- Utilidades ----------
async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  let payload;
  if (form) { payload = new URLSearchParams(form); }
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  const res = await fetch(API + path, { method, headers, body: payload });
  if (res.status === 401 && state.token) { logout(); throw new Error("Sesión expirada"); }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map((e) => e.msg).join(", ") : d || `Error ${res.status}`);
  }
  return data;
}
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2500);
}
const initials = (name) => name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const todayISO = () => new Date().toISOString().slice(0, 10);

// ---------- Autenticación ----------
function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.mode === mode));
  document.querySelectorAll(".register-only").forEach((el) => el.classList.toggle("hidden", mode !== "register"));
  $("#auth-submit").textContent = mode === "login" ? "Entrar" : "Crear cuenta";
  $("#auth-error").textContent = "";
}
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => setMode(t.dataset.mode)));

$("#auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    if (state.mode === "register") {
      await api("/auth/register", { method: "POST", body: { email: f.get("email"), full_name: f.get("full_name"), password: f.get("password") } });
    }
    const { access_token } = await api("/auth/login", { method: "POST", form: { username: f.get("email"), password: f.get("password") } });
    state.token = access_token;
    localStorage.setItem("tf_token", access_token);
    await start();
  } catch (err) { $("#auth-error").textContent = err.message; }
});

function logout() {
  state.token = null; state.current = null;
  localStorage.removeItem("tf_token");
  $("#app-view").classList.add("hidden");
  $("#auth-view").classList.remove("hidden");
}
$("#logout").addEventListener("click", logout);

// ---------- Salud (API ↔ BD) ----------
async function checkHealth() {
  const el = $("#health");
  try {
    const h = await fetch(API + "/health").then((r) => r.json());
    const ok = h.database?.status === "ok";
    el.className = "health " + (ok ? "ok" : "bad");
    el.title = `API: ${h.container} · BD: ${h.database.engine}@${h.database.host} (${h.database.status})`;
  } catch { el.className = "health bad"; el.title = "API no disponible"; }
}

// ---------- Proyectos ----------
async function loadProjects() {
  state.projects = await api("/projects");
  const ul = $("#project-list");
  ul.innerHTML = state.projects.map((p) =>
    `<li data-id="${p.id}" class="${state.current?.id === p.id ? "active" : ""}">${esc(p.name)}<small>${p.my_role === "owner" ? "Dueño" : "Miembro"}</small></li>`).join("");
  ul.querySelectorAll("li").forEach((li) => li.addEventListener("click", () => openProject(Number(li.dataset.id))));
  if (!state.current && state.projects.length) await openProject(state.projects[0].id);
  $("#empty").classList.toggle("hidden", state.projects.length > 0);
}

$("#project-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const p = await api("/projects", { method: "POST", body: { name: new FormData(e.target).get("name") } });
    e.target.reset(); state.current = p; await loadProjects(); await openProject(p.id);
    toast("Proyecto creado");
  } catch (err) { toast(err.message); }
});

async function openProject(id) {
  state.current = state.projects.find((p) => p.id === id);
  document.querySelectorAll("#project-list li").forEach((li) => li.classList.toggle("active", Number(li.dataset.id) === id));
  $("#board-wrap").classList.remove("hidden");
  $("#project-name").textContent = state.current.name;
  $("#project-desc").textContent = state.current.description || "";
  document.querySelectorAll(".owner-only").forEach((el) => el.classList.toggle("hidden", state.current.my_role !== "owner"));
  await Promise.all([loadMembers(), loadTasks()]);
}

// ---------- Miembros ----------
async function loadMembers() {
  state.members = await api(`/projects/${state.current.id}/members`);
  $("#member-list").innerHTML = state.members.map((m) =>
    `<li><span class="avatar">${initials(m.user.full_name)}</span> ${esc(m.user.full_name)} · ${m.role === "owner" ? "dueño" : "miembro"}</li>`).join("");
  $("#assignee-select").innerHTML = `<option value="">Sin asignar</option>` +
    state.members.map((m) => `<option value="${m.user.id}">${esc(m.user.full_name)}</option>`).join("");
}
$("#toggle-members").addEventListener("click", () => $("#members-panel").classList.toggle("hidden"));
$("#member-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api(`/projects/${state.current.id}/members`, { method: "POST", body: { email: new FormData(e.target).get("email") } });
    e.target.reset(); await loadMembers(); toast("Miembro agregado");
  } catch (err) { toast(err.message); }
});

// ---------- Tareas ----------
async function loadTasks() {
  const priority = $("#filter-priority").value;
  const qs = priority ? `?priority=${priority}` : "";
  state.tasks = await api(`/projects/${state.current.id}/tasks${qs}`);
  renderBoard();
  loadStats();
}
$("#filter-priority").addEventListener("change", loadTasks);

async function loadStats() {
  const s = await api(`/projects/${state.current.id}/stats`);
  $("#progress-bar").style.width = s.progress_pct + "%";
  $("#progress-text").textContent = `${s.progress_pct}% completado`;
  $("#stat-total").textContent = `${s.total} tareas`;
  $("#stat-overdue").textContent = `${s.overdue} vencidas`;
  $("#stat-overdue").classList.toggle("hidden", s.overdue === 0);
}

function renderBoard() {
  for (const status of STATUSES) {
    const col = document.querySelector(`.column[data-status="${status}"]`);
    const tasks = state.tasks.filter((t) => t.status === status);
    col.querySelector(".count").textContent = tasks.length;
    col.querySelector(".cards").innerHTML = tasks.map(cardHTML).join("");
  }
  document.querySelectorAll(".card").forEach((card) => {
    card.addEventListener("dragstart", (e) => e.dataTransfer.setData("text/plain", card.dataset.id));
    card.addEventListener("click", (e) => { if (!e.target.closest(".moves")) openTask(Number(card.dataset.id)); });
  });
  document.querySelectorAll(".moves button").forEach((b) =>
    b.addEventListener("click", () => moveTask(Number(b.dataset.id), b.dataset.to)));
}

function cardHTML(t) {
  const idx = STATUSES.indexOf(t.status);
  const overdue = t.due_date && t.due_date < todayISO() && t.status !== "done";
  const prev = idx > 0 ? `<button data-id="${t.id}" data-to="${STATUSES[idx - 1]}" title="Mover a la izquierda">◀</button>` : "";
  const next = idx < 2 ? `<button data-id="${t.id}" data-to="${STATUSES[idx + 1]}" title="Mover a la derecha">▶</button>` : "";
  return `<article class="card ${t.priority}" draggable="true" data-id="${t.id}">
    <h4>${esc(t.title)}</h4>
    <div class="meta">
      <span>${PRIORITY_LABEL[t.priority]}${t.due_date ? ` · <span class="${overdue ? "overdue" : ""}">${t.due_date}</span>` : ""}${t.comment_count ? ` · 💬 ${t.comment_count}` : ""}</span>
      <span class="moves">${prev}${next}${t.assignee ? `<span class="avatar" title="${esc(t.assignee.full_name)}">${initials(t.assignee.full_name)}</span>` : ""}</span>
    </div>
  </article>`;
}

async function moveTask(id, status) {
  try { await api(`/tasks/${id}`, { method: "PATCH", body: { status } }); await loadTasks(); }
  catch (err) { toast(err.message); }
}

document.querySelectorAll(".column").forEach((col) => {
  col.addEventListener("dragover", (e) => { e.preventDefault(); col.classList.add("drag-over"); });
  col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
  col.addEventListener("drop", (e) => {
    e.preventDefault(); col.classList.remove("drag-over");
    moveTask(Number(e.dataTransfer.getData("text/plain")), col.dataset.status);
  });
});

$("#task-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const body = { title: f.get("title"), priority: f.get("priority") };
  if (f.get("due_date")) body.due_date = f.get("due_date");
  if (f.get("assignee_id")) body.assignee_id = Number(f.get("assignee_id"));
  try {
    await api(`/projects/${state.current.id}/tasks`, { method: "POST", body });
    e.target.reset(); await loadTasks(); toast("Tarea creada");
  } catch (err) { toast(err.message); }
});

// ---------- Detalle y comentarios ----------
let openTaskId = null;
async function openTask(id) {
  openTaskId = id;
  const t = state.tasks.find((x) => x.id === id);
  $("#dlg-title").textContent = t.title;
  $("#dlg-meta").textContent = `Prioridad ${PRIORITY_LABEL[t.priority]} · ${t.assignee ? "Asignada a " + t.assignee.full_name : "Sin asignar"}${t.due_date ? " · Vence " + t.due_date : ""}`;
  $("#dlg-desc").textContent = t.description || "";
  await loadComments();
  $("#task-dialog").showModal();
}
async function loadComments() {
  const comments = await api(`/tasks/${openTaskId}/comments`);
  $("#dlg-comments").innerHTML = comments.length
    ? comments.map((c) => `<li><small>${esc(c.author.full_name)} · ${new Date(c.created_at).toLocaleString("es-CO")}</small>${esc(c.content)}</li>`).join("")
    : `<li class="muted">Sin comentarios aún.</li>`;
}
$("#comment-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api(`/tasks/${openTaskId}/comments`, { method: "POST", body: { content: new FormData(e.target).get("content") } });
    e.target.reset(); await loadComments(); await loadTasks();
  } catch (err) { toast(err.message); }
});
$("#dlg-delete").addEventListener("click", async () => {
  if (!confirm("¿Eliminar esta tarea?")) return;
  await api(`/tasks/${openTaskId}`, { method: "DELETE" });
  $("#task-dialog").close(); await loadTasks(); toast("Tarea eliminada");
});

// ---------- Inicio ----------
async function start() {
  try {
    state.user = await api("/auth/me");
  } catch { logout(); return; }
  $("#user-name").textContent = state.user.full_name;
  $("#auth-view").classList.add("hidden");
  $("#app-view").classList.remove("hidden");
  checkHealth();
  setInterval(checkHealth, 15000);
  await loadProjects();
}

if (state.token) start(); else logout();
