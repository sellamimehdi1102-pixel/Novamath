// ── Page de diagnostic temporaire (dev only, voir server.py::_serve_debug_runtime
// gardé par config.DEBUG) — aucune logique métier, uniquement de la lecture
// d'état pour comparer un environnement qui bloque avec un environnement qui
// fonctionne. Volontairement indépendant d'api.js : on veut voir le status
// HTTP et le JSON bruts, sans que la couche d'erreurs applicative (voir
// api.js::buildApiError) ne les reformate ou les masque.

const $ = (id) => document.getElementById(id);

// ── JS : erreurs capturées dès le chargement de CETTE page ─────────────────
const capturedErrors = [];
function pushError(label, detail) {
  capturedErrors.push({ label, detail, at: new Date().toISOString() });
  renderErrors();
}
window.addEventListener("error", (e) => {
  pushError("window.onerror", `${e.message} @ ${e.filename}:${e.lineno}:${e.colno}`);
});
window.addEventListener("unhandledrejection", (e) => {
  pushError("unhandledrejection", e.reason?.stack || String(e.reason));
});
const _origConsoleError = console.error.bind(console);
console.error = (...args) => {
  pushError("console.error", args.map((a) => (a instanceof Error ? a.stack : String(a))).join(" "));
  _origConsoleError(...args);
};

function renderErrors() {
  const list = $("errors-list");
  const empty = $("errors-empty");
  list.innerHTML = capturedErrors.map((e) => `<li><strong>[${e.at}] ${e.label}</strong><br>${escapeHtml(e.detail)}</li>`).join("");
  empty.style.display = capturedErrors.length ? "none" : "block";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function prettyJson(raw) {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

function kvTable(pairs) {
  if (!pairs.length) return '<p class="muted">Aucune entrée.</p>';
  return `<table>${pairs.map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td>${v}</td></tr>`).join("")}</table>`;
}

// ── Authentification ─────────────────────────────────────────────────────
async function renderAuth() {
  const el = $("sec-auth");
  try {
    const res = await fetch("/api/auth/me", { credentials: "same-origin" });
    const json = await res.json().catch(() => null);
    if (!res.ok) {
      el.innerHTML = `<span class="fail">Non connecté</span> — status ${res.status}<pre>${escapeHtml(JSON.stringify(json, null, 2))}</pre>`;
      return { user: null };
    }
    const u = json.user || {};
    el.innerHTML = kvTable([
      ["connecté", `<span class="ok">oui</span>`],
      ["guest", String(!!u.is_guest)],
      ["user id", String(u.id ?? "—")],
      ["username", escapeHtml(u.username ?? "—")],
      ["rôle", escapeHtml(u.role ?? "—")],
      ["can_access_admin", String(!!u.can_access_admin)],
      ["plan", escapeHtml(u.plan ?? "—")],
      ["classe (localStorage novamath:class_level)", escapeHtml(localStorage.getItem("novamath:class_level") ?? "—")],
    ]);
    return { user: u };
  } catch (err) {
    el.innerHTML = `<span class="fail">Requête échouée</span><pre>${escapeHtml(err.stack || String(err))}</pre>`;
    return { user: null };
  }
}

// ── Local / Session Storage ─────────────────────────────────────────────
function renderStorage(storage, elId, filterFn) {
  const el = $(elId);
  const pairs = [];
  for (let i = 0; i < storage.length; i++) {
    const key = storage.key(i);
    if (filterFn && !filterFn(key)) continue;
    const raw = storage.getItem(key);
    pairs.push([key, `<pre>${escapeHtml(prettyJson(raw))}</pre>`]);
  }
  el.innerHTML = kvTable(pairs);
  return pairs;
}

// ── Cookies ──────────────────────────────────────────────────────────────
function renderCookies() {
  const el = $("sec-cookies");
  const pairs = document.cookie
    .split(";")
    .map((c) => c.trim())
    .filter(Boolean)
    .map((c) => {
      const idx = c.indexOf("=");
      return [c.slice(0, idx), escapeHtml(decodeURIComponent(c.slice(idx + 1)))];
    });
  el.innerHTML = kvTable(pairs);
  return pairs;
}

// ── Pending / Current series ─────────────────────────────────────────────
function renderPendingSeries() {
  // Lecture pure (getItem), jamais consumePendingSeries() : cette page ne
  // doit JAMAIS modifier l'état qu'elle observe.
  const raw = localStorage.getItem("lumis:pending_series");
  $("sec-pending").innerHTML = raw ? `<pre>${escapeHtml(prettyJson(raw))}</pre>` : '<p class="muted">Aucune série en attente.</p>';
  return raw;
}

function renderCurrentSeries() {
  const raw = localStorage.getItem("lumis:series_in_progress");
  $("sec-current-series").innerHTML = raw ? `<pre>${escapeHtml(prettyJson(raw))}</pre>` : '<p class="muted">Aucune série en cours.</p>';
  return raw;
}

function renderCurrentExercise(currentSeriesRaw) {
  const el = $("sec-current-exercise");
  if (!currentSeriesRaw) {
    el.innerHTML = '<p class="muted">Pas de série en cours — aucun exercice courant.</p>';
    return;
  }
  try {
    const snap = JSON.parse(currentSeriesRaw);
    const questions = snap.draftQuestions || [];
    const last = questions[questions.length - 1];
    el.innerHTML = kvTable([
      ["mode", escapeHtml(snap.mode ?? "—")],
      ["chapterId (seriesConfig)", escapeHtml(snap.seriesConfig?.chapterId ?? "—")],
      ["notion (seriesConfig)", escapeHtml(snap.seriesConfig?.notion ?? "—")],
      ["seriesIndex / total", `${snap.seriesIndex ?? "—"} / ${snap.total ?? "—"}`],
      ["dernière question connue", last ? `<pre>${escapeHtml(JSON.stringify(last, null, 2))}</pre>` : '<span class="muted">aucune (série pas encore commencée)</span>'],
    ]);
  } catch (err) {
    el.innerHTML = `<span class="fail">Impossible de parser lumis:series_in_progress</span><pre>${escapeHtml(err.stack || String(err))}</pre>`;
  }
}

// ── API : tests en direct ────────────────────────────────────────────────
function apiBlockHtml(label, method, url, status, ok, body) {
  const cls = status === "réseau" ? "status-err" : status >= 500 ? "status-5xx" : status >= 400 ? "status-4xx" : "status-2xx";
  return `
    <div class="api-block">
      <strong>${escapeHtml(label)}</strong> — <span class="muted">${method} ${escapeHtml(url)}</span>
      — <span class="status-badge ${cls}">${status}</span>
      <pre>${escapeHtml(typeof body === "string" ? body : JSON.stringify(body, null, 2))}</pre>
    </div>`;
}

async function testEndpoint(label, method, url, body) {
  try {
    const res = await fetch(url, {
      method,
      credentials: "same-origin",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const json = await res.json().catch(() => "(réponse non-JSON)");
    return apiBlockHtml(label, method, url, res.status, res.ok, json);
  } catch (err) {
    return apiBlockHtml(label, method, url, "réseau", false, err.stack || String(err));
  }
}

async function renderApiTests(classLevel, pendingRaw) {
  const el = $("sec-api");
  el.innerHTML = '<p class="muted">Tests en cours…</p>';

  const blocks = [];
  blocks.push(await testEndpoint("GET /api/auth/me", "GET", "/api/auth/me"));

  const chaptersUrl = `/api/chapters?class_level=${encodeURIComponent(classLevel || "seconde")}`;
  const chaptersHtml = await testEndpoint("GET /api/chapters", "GET", chaptersUrl);
  blocks.push(chaptersHtml);

  // Détermine un exercise_id réel pour tester /api/practice/load : priorité
  // à la série en attente (c'est justement ce que exercice.js consommerait),
  // sinon le premier id trouvé dans la réponse /api/chapters ci-dessus.
  let exerciseId = null;
  try {
    if (pendingRaw) {
      const pending = JSON.parse(pendingRaw);
      exerciseId = (pending.exerciseIds || [])[0] ?? null;
    }
  } catch { /* ignore */ }
  if (exerciseId == null) {
    try {
      const res = await fetch(chaptersUrl, { credentials: "same-origin" });
      const json = await res.json();
      for (const ch of json.chapters_meta || []) {
        for (const n of ch.notions_detail || []) {
          if (n.exercise_ids?.length) { exerciseId = n.exercise_ids[0]; break; }
        }
        if (exerciseId != null) break;
      }
    } catch { /* ignore */ }
  }

  if (exerciseId != null) {
    blocks.push(await testEndpoint(
      `POST /api/practice/load (exercise_id=${exerciseId})`,
      "POST",
      "/api/practice/load",
      { exercise_id: exerciseId, class_level: classLevel || "seconde" },
    ));
  } else {
    blocks.push(`<div class="api-block"><strong>POST /api/practice/load</strong> — <span class="fail">aucun exercise_id trouvé pour tester (ni dans pending_series, ni dans /api/chapters)</span></div>`);
  }

  el.innerHTML = blocks.join("");
}

// ── Navigation ───────────────────────────────────────────────────────────
function renderNav() {
  $("sec-nav").innerHTML = kvTable([
    ["window.location.href", escapeHtml(window.location.href)],
    ["history.length", String(history.length)],
    ["document.referrer", escapeHtml(document.referrer || "(vide)")],
  ]);
}

// ── Environnement ────────────────────────────────────────────────────────
function renderEnv() {
  let tz = "—";
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone; } catch { /* ignore */ }
  $("sec-env").innerHTML = kvTable([
    ["navigator.userAgent", escapeHtml(navigator.userAgent)],
    ["navigator.language", escapeHtml(navigator.language)],
    ["navigator.languages", escapeHtml((navigator.languages || []).join(", "))],
    ["timezone", escapeHtml(tz)],
    ["écran", `${screen.width}×${screen.height}`],
    ["viewport", `${window.innerWidth}×${window.innerHeight}`],
  ]);
}

// ── Orchestration ─────────────────────────────────────────────────────────
let lastSnapshot = {};

async function refreshAll() {
  const authInfo = await renderAuth();
  const localPairs = renderStorage(localStorage, "sec-localstorage", (k) => k.startsWith("novamath:") || k.startsWith("lumis:"));
  const sessionPairs = renderStorage(sessionStorage, "sec-sessionstorage", () => true);
  const cookiePairs = renderCookies();
  const pendingRaw = renderPendingSeries();
  const currentSeriesRaw = renderCurrentSeries();
  renderCurrentExercise(currentSeriesRaw);
  renderNav();
  renderEnv();

  const classLevel = localStorage.getItem("novamath:class_level");
  await renderApiTests(classLevel, pendingRaw);

  lastSnapshot = {
    capturedAt: new Date().toISOString(),
    auth: authInfo.user,
    localStorage: Object.fromEntries(localPairs.map(([k], i) => [k, localStorage.getItem(k)])),
    sessionStorage: Object.fromEntries(sessionPairs.map(([k]) => [k, sessionStorage.getItem(k)])),
    cookies: Object.fromEntries(cookiePairs.map(([k, v]) => [k, v])),
    pendingSeries: pendingRaw,
    currentSeries: currentSeriesRaw,
    navigation: { href: window.location.href, historyLength: history.length, referrer: document.referrer },
    environment: {
      userAgent: navigator.userAgent,
      language: navigator.language,
      languages: navigator.languages,
      timezone: (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone; } catch { return null; } })(),
    },
    jsErrors: capturedErrors,
  };
}

$("btn-refresh").addEventListener("click", refreshAll);
$("btn-copy").addEventListener("click", async () => {
  await navigator.clipboard.writeText(JSON.stringify(lastSnapshot, null, 2));
  $("copy-feedback").textContent = "Copié !";
  setTimeout(() => { $("copy-feedback").textContent = ""; }, 2000);
});

refreshAll();
