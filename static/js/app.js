"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

// Build DOM with textContent only, so user-written memories can never inject HTML.
function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (v === true) n.setAttribute(k, "");
    else if (v !== false && v != null) n.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null) n.append(kid.nodeType ? kid : document.createTextNode(kid));
  return n;
}

function errorMessage(data, status) {
  const d = data && data.detail;
  if (typeof d === "string") return d;
  if (d && d.message) return d.message;
  if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).slice(1).join(".")}: ${e.msg}`).join("; ");
  return `Request failed (${status}).`;
}

async function api(path, { method = "GET", body } = {}) {
  const init = { method, headers: {} };
  if (body !== undefined) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
  let res;
  try { res = await fetch("/api" + path, init); }
  catch { throw new Error("Cannot reach the local server. Is it still running?"); }
  let data = null;
  try { data = await res.json(); } catch { /* no body */ }
  if (!res.ok) throw new Error(errorMessage(data, res.status));
  return data;
}

function notify(msg, kind = "ok") {
  const t = $("#toast");
  t.textContent = msg; t.dataset.kind = kind;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => { t.textContent = ""; }, 8000);
}

async function busy(button, label, fn) {
  const original = button.textContent;
  button.disabled = true; button.textContent = label;
  try { return await fn(); }
  catch (e) { notify(e.message, "error"); }
  finally { button.disabled = false; button.textContent = original; refreshStatus(); }
}

// ---- tabs ---------------------------------------------------------------
function show(name) {
  $$(".panel").forEach((p) => { p.hidden = p.id !== "panel-" + name; });
  $$("nav button").forEach((b) => b.setAttribute("aria-current", b.dataset.tab === name ? "page" : "false"));
  if (name === "ofrenda") { refreshSubjects(); loadOfrendas(); }
  if (name === "seance") refreshSubjects();
  if (name === "settings") loadSettings();
}
$$("nav button").forEach((b) => b.addEventListener("click", () => show(b.dataset.tab)));

// ---- status -------------------------------------------------------------
async function refreshStatus() {
  const s = $("#status");
  try {
    const h = await api("/health");
    const ok = h.ollama && h.model_installed;
    s.dataset.ok = String(ok);
    s.textContent = ok ? `Ollama ready, model ${h.model}` : (h.message || "Ollama is not ready.");
  } catch (e) { s.dataset.ok = "false"; s.textContent = e.message; }
}

// ---- memories -----------------------------------------------------------
function resetMemoryForm() {
  $("#memory-form").reset(); $("#memory-id").value = "";
  $("#form-title").textContent = "Add a memory"; $("#m-cancel").hidden = true;
}

async function loadMemories() {
  const list = await api("/memories");
  $("#memory-empty").hidden = list.length > 0;
  $("#memory-list").replaceChildren(...list.map((m) => el("li", {},
    el("article", { class: "card" },
      el("h3", {}, m.title),
      el("p", { class: "meta" }, [m.subject, m.date, m.tags].filter(Boolean).join(", ")),
      el("p", { class: "memory-text" }, m.text),
      el("div", { class: "actions" },
        el("button", { type: "button", onclick: () => editMemory(m), "aria-label": `Edit ${m.title}` }, "Edit"),
        el("button", { type: "button", class: "warn", onclick: () => removeMemory(m), "aria-label": `Delete ${m.title}` }, "Delete"))))));
  $("#subject-list").replaceChildren(...[...new Set(list.map((m) => m.subject))].map((s) => el("option", { value: s })));
}

function editMemory(m) {
  $("#memory-id").value = m.id; $("#m-title").value = m.title; $("#m-subject").value = m.subject;
  $("#m-text").value = m.text; $("#m-tags").value = m.tags; $("#m-date").value = m.date;
  $("#form-title").textContent = "Edit memory"; $("#m-cancel").hidden = false;
  $("#m-title").focus(); window.scrollTo({ top: 0 });
}

async function removeMemory(m) {
  if (!confirm(`Delete "${m.title}"? This cannot be undone.`)) return;
  try { await api(`/memories/${m.id}`, { method: "DELETE" }); notify("Memory deleted."); await loadMemories(); }
  catch (e) { notify(e.message, "error"); }
}

$("#m-cancel").addEventListener("click", resetMemoryForm);
$("#memory-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const id = $("#memory-id").value;
  const body = { title: $("#m-title").value, subject: $("#m-subject").value, text: $("#m-text").value,
                 tags: $("#m-tags").value, date: $("#m-date").value };
  await busy($("#m-save"), "Saving…", async () => {
    await api(id ? `/memories/${id}` : "/memories", { method: id ? "PUT" : "POST", body });
    notify(id ? "Memory updated." : "Memory saved.");
    resetMemoryForm(); await loadMemories();
  });
});

// ---- subjects -----------------------------------------------------------
async function refreshSubjects() {
  const subjects = await api("/subjects").catch(() => []);
  const o = $("#o-subject"), s = $("#s-subject");
  const keepO = o.value, keepS = s.value;
  o.replaceChildren(...(subjects.length ? subjects.map((x) => el("option", { value: x.subject }, `${x.subject} (${x.count})`))
                                         : [el("option", { value: "" }, "Add a memory first")]));
  s.replaceChildren(el("option", { value: "" }, "Everything"), ...subjects.map((x) => el("option", { value: x.subject }, x.subject)));
  if (keepO) o.value = keepO; if (keepS) s.value = keepS;
}

// ---- ofrenda ------------------------------------------------------------
function renderOfrenda(o) {
  return el("article", { class: "card ofrenda" },
    el("h3", {}, `Ofrenda for ${o.subject}`),
    el("p", {}, o.remembrance),
    el("ul", {}, o.remembered.map((x) => el("li", {}, x))),
    el("p", { class: "closing" }, o.closing),
    el("p", { class: "meta" }, `Written by ${o.model} from ${o.source_ids.length} saved memories on ${o.created_at}.`));
}

async function loadOfrendas() {
  const list = await api("/ofrendas");
  $("#ofrenda-empty").hidden = list.length > 0;
  $("#ofrenda-list").replaceChildren(...list.map((o) => el("li", {}, renderOfrenda(o),
    el("button", { type: "button", class: "warn", onclick: async () => {
      if (!confirm("Delete this saved ofrenda?")) return;
      await api(`/ofrendas/${o.id}`, { method: "DELETE" }); loadOfrendas();
    } }, "Delete ofrenda"))));
}

$("#ofrenda-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const subject = $("#o-subject").value;
  if (!subject) { notify("Add a memory first, then choose who to remember.", "error"); return; }
  await busy($("#o-go"), "Writing… (a small model can take a minute)", async () => {
    const o = await api("/ofrenda", { method: "POST", body: { subject } });
    $("#ofrenda-result").replaceChildren(renderOfrenda(o)); notify("Ofrenda saved on this computer.");
    await loadOfrendas();
  });
});

// ---- séance -------------------------------------------------------------
$("#seance-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const question = $("#s-question").value.trim();
  const subject = $("#s-subject").value || null;
  if (question.length < 2) return;
  const log = $("#chat-log");
  log.append(el("div", { class: "msg q" }, el("strong", {}, "You: "), question));
  $("#s-question").value = "";
  await busy($("#s-go"), "Listening…", async () => {
    const r = await api("/seance", { method: "POST", body: { question, subject } });
    const msg = el("div", { class: "msg a" + (r.answered ? "" : " none") },
      el("strong", {}, "Narrator: "), r.answer);
    if (r.sources.length) {
      msg.append(el("details", {}, el("summary", {}, `Memories used (${r.sources.length})`),
        el("ul", {}, r.sources.map((s) => el("li", {}, el("strong", {}, `${s.title} (${s.subject}${s.date ? ", " + s.date : ""}): `), s.text)))));
    }
    msg.append(el("p", { class: "meta" }, r.answered ? "Fictional narration generated from the memories above." : "No answer was invented."));
    log.append(msg); msg.scrollIntoView({ block: "nearest" });
  });
});

// ---- settings -----------------------------------------------------------
async function loadSettings() {
  const s = await api("/settings");
  let installed = [];
  try { installed = (await api("/health")).installed_models; } catch { /* offline is fine */ }
  const names = [...new Set([...s.supported_models, s.model, ...installed])];
  $("#set-model").replaceChildren(...names.map((n) => el("option", { value: n }, n)));
  $("#set-model").value = s.model; $("#set-url").value = s.ollama_url;
}

$("#settings-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  try {
    await api("/settings", { method: "PUT", body: { model: $("#set-model").value, ollama_url: $("#set-url").value } });
    notify("Settings saved."); refreshStatus();
  } catch (e) { notify(e.message, "error"); }
});
$("#set-test").addEventListener("click", async () => {
  await refreshStatus(); notify($("#status").textContent, $("#status").dataset.ok === "true" ? "ok" : "error");
});
$("#delete-all").addEventListener("click", async () => {
  if (!confirm("Delete ALL memories and saved ofrendas from this computer? This cannot be undone.")) return;
  try {
    await api("/data?confirm=yes", { method: "DELETE" });
    notify("Everything was deleted from the local database."); await loadMemories(); await refreshSubjects(); await loadOfrendas();
    $("#chat-log").replaceChildren(); $("#ofrenda-result").replaceChildren();
  } catch (e) { notify(e.message, "error"); }
});

// ---- start --------------------------------------------------------------
loadMemories().catch((e) => notify(e.message, "error"));
refreshStatus();
