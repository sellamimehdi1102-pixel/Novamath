// ── Wrapper fetch vers l'API Flask existante (contrat inchangé) ────────────
// Le cookie nm_csrf (non-HttpOnly, posé par le serveur à la connexion/inscription)
// doit être renvoyé en en-tête sur toute requête mutante — double-submit cookie,
// défense en profondeur contre le CSRF en complément de SameSite=Lax (voir
// webapp/auth.py::csrf_protect). Lecture directe du cookie : ce module n'a pas
// besoin de connaître la valeur autrement, elle n'est jamais exposée par l'API.
function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

const MUTATING_METHODS = new Set(["POST", "PUT", "DELETE", "PATCH"]);

// ── Toast centralisé "quota dépassé" ─────────────────────────────────────────
// Injecté à la volée (position: fixed, voir css/settings.css::.toast — chargé
// sur toutes les pages app-shell) plutôt que de dépendre d'un élément déjà
// présent dans le HTML de chaque page : ce module n'a aucune idée de quelle
// page l'appelle, donc aucun id de toast pré-existant à cibler. Réutilisée à
// la fois par request()/les fonctions de streaming ci-dessous ET par
// chatbot.js pour le cas résiduel d'un 429 reçu DANS un flux SSE déjà ouvert
// (voir son commentaire sur la course concurrente) — un seul comportement,
// jamais deux implémentations du même toast+redirection.
const PLAN_LABELS_FOR_TOAST = { premium: "Premium", ultra: "Ultra" };
let quotaToastTimer = null;

export function handleQuotaExceeded(payload) {
  const planLabel = PLAN_LABELS_FOR_TOAST[payload.required_plan] || "Premium";
  let el = document.getElementById("novamath-quota-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "novamath-quota-toast";
    document.body.appendChild(el);
  }
  clearTimeout(quotaToastTimer);
  el.className = "toast toast--error";
  el.innerHTML = `<span>Tu as utilisé tous tes messages d'aujourd'hui. Passe à ${planLabel} pour continuer.</span>`;
  el.hidden = false;
  quotaToastTimer = setTimeout(() => {
    window.location.href = `/abonnement.html?reason=quota&quota=${encodeURIComponent(payload.quota)}`;
  }, 1600);
}

// Construit l'Error levée pour toute réponse HTTP en échec, partagée par
// request() (JSON classique) et les fonctions de streaming ci-dessous (fetch
// brut, hors de request() car leur réponse réussie n'est pas du JSON) — un
// seul endroit qui sait traduire un payload d'erreur serveur en Error
// exploitable côté client, jamais dupliqué entre les deux styles d'appel.
function buildApiError(path, status, payload) {
  const err = new Error(payload.error || `Erreur API ${path}: ${status}`);
  err.status = status;
  // 403 "premium_required" (voir plan_service.requires_feature) : porte la
  // feature manquante et le plan minimal requis, pour que l'appelant
  // puisse afficher un message propre / rediriger vers la page Abonnement
  // au lieu d'exposer err.message ("premium_required") tel quel à l'écran.
  if (payload.error === "premium_required") {
    err.isPremiumRequired = true;
    err.feature = payload.feature;
    err.requiredPlan = payload.required_plan;
  }
  // 429 "quota_exceeded" (voir quota_service.py) : redirection + toast
  // déclenchés ici, centralement — l'appelant n'a qu'à arrêter proprement son
  // propre état de chargement, jamais à reconstruire ce comportement.
  if (payload.error === "quota_exceeded") {
    err.isQuotaExceeded = true;
    err.quota = payload.quota;
    err.remaining = payload.remaining;
    err.limit = payload.limit;
    err.requiredPlan = payload.required_plan;
    handleQuotaExceeded(payload);
  }
  return err;
}

async function request(path, { method = "GET", body, headers } = {}) {
  const csrfToken = MUTATING_METHODS.has(method) ? readCookie("nm_csrf") : null;
  const res = await fetch(path, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
      ...(headers || {}),
    },
    credentials: "same-origin",
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw buildApiError(path, res.status, payload);
  return payload;
}

export const api = {
  chapters: (classLevel) =>
    request(`/api/chapters${classLevel ? `?class_level=${encodeURIComponent(classLevel)}` : ""}`),
  getSiteStats: (classLevel) =>
    request(`/api/site/stats${classLevel ? `?class_level=${encodeURIComponent(classLevel)}` : ""}`),
  getCurricula: () => request("/api/curricula"),
  start: (chapters, classLevel) => request("/api/start", { method: "POST", body: { chapters, class_level: classLevel } }),
  answer: (exerciseId, correct) => request("/api/answer", { method: "POST", body: { exercise_id: exerciseId, correct } }),
  practiceLoad: (exerciseId, classLevel) =>
    request("/api/practice/load", { method: "POST", body: { exercise_id: exerciseId, class_level: classLevel } }),
  practiceResult: (exerciseId, correct, classLevel) =>
    request("/api/practice/result", { method: "POST", body: { exercise_id: exerciseId, correct, class_level: classLevel } }),
  restart: () => request("/api/restart", { method: "POST" }),
  exercise: (id, classLevel) =>
    request(`/api/exercise/${id}${classLevel ? `?class_level=${encodeURIComponent(classLevel)}` : ""}`),
  getStats: () => request("/api/stats"),
  saveStats: (stats) => request("/api/stats", { method: "POST", body: stats }),

  getCourseProgress: (classLevel) =>
    request(`/api/course-progress${classLevel ? `?class_level=${encodeURIComponent(classLevel)}` : ""}`),
  saveCourseProgress: (chapterId, notionId, patch, classLevel) =>
    request("/api/course-progress", { method: "POST", body: { chapterId, notionId, patch, class_level: classLevel } }),

  getSettings: () => request("/api/settings"),
  saveSettings: (settings) => request("/api/settings", { method: "POST", body: settings }),
  getDataSummary: () => request("/api/data/summary"),
  exportData: () => request("/api/data/export"),
  resetProgress: () => request("/api/data/reset", { method: "POST" }),

  getReviews: (adminKey) => request("/api/reviews", { headers: adminKey ? { "X-Admin-Key": adminKey } : undefined }),
  createReview: (payload) => request("/api/reviews", { method: "POST", body: payload }),
  updateReview: (id, payload, adminKey) =>
    request(`/api/reviews/${id}`, { method: "PUT", body: payload, headers: adminKey ? { "X-Admin-Key": adminKey } : undefined }),
  deleteReview: (id, ownerToken, adminKey) =>
    request(`/api/reviews/${id}`, {
      method: "DELETE",
      body: { owner_token: ownerToken || undefined },
      headers: adminKey ? { "X-Admin-Key": adminKey } : undefined,
    }),
  pinReview: (id, adminKey) => request(`/api/reviews/${id}/pin`, { method: "POST", headers: { "X-Admin-Key": adminKey } }),
  hideReview: (id, adminKey) => request(`/api/reviews/${id}/hide`, { method: "POST", headers: { "X-Admin-Key": adminKey } }),

  register: (payload) => request("/api/auth/register", { method: "POST", body: payload }),
  login: (payload) => request("/api/auth/login", { method: "POST", body: payload }),
  enterGuest: () => request("/api/auth/guest", { method: "POST" }),
  guestDashboardSeen: () => request("/api/auth/guest/dashboard-seen", { method: "POST" }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request("/api/auth/me"),
  updateMe: (payload) => request("/api/auth/me", { method: "PUT", body: payload }),
  deleteMe: (payload) => request("/api/auth/me", { method: "DELETE", body: payload }),
  forgotPassword: (email) => request("/api/auth/forgot-password", { method: "POST", body: { email } }),
  resetPassword: (payload) => request("/api/auth/reset-password", { method: "POST", body: payload }),
  changePassword: (payload) => request("/api/auth/change-password", { method: "POST", body: payload }),
  getSessions: () => request("/api/auth/sessions"),
  logoutOtherSessions: () => request("/api/auth/sessions/logout-others", { method: "POST" }),
  enable2FA: () => request("/api/auth/2fa/enable", { method: "POST" }),

  // ── Abonnements (Stripe Billing) ─────────────────────────────────────────
  checkoutCreateSession: (plan) => request("/api/checkout/create-session", { method: "POST", body: { plan } }),

  // ── Chatbot ────────────────────────────────────────────────────────────
  chatbotConversations: (q) => request(`/api/chatbot/conversations${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  chatbotCreateConversation: () => request("/api/chatbot/conversations", { method: "POST" }),
  chatbotRenameConversation: (id, title) => request(`/api/chatbot/conversations/${id}`, { method: "PATCH", body: { title } }),
  chatbotPinConversation: (id, pinned) => request(`/api/chatbot/conversations/${id}`, { method: "PATCH", body: { pinned } }),
  chatbotDeleteConversation: (id) => request(`/api/chatbot/conversations/${id}`, { method: "DELETE" }),
  chatbotMessages: (id) => request(`/api/chatbot/conversations/${id}/messages`),
  chatbotFeedback: (messageId, liked) => request(`/api/chatbot/messages/${messageId}/feedback`, { method: "POST", body: { liked } }),
  chatbotQuota: () => request("/api/chatbot/quota"),
  getQuota: () => request("/api/quota"),
  chatbotContextPreview: (classLevel) =>
    request(`/api/chatbot/context-preview${classLevel ? `?class_level=${encodeURIComponent(classLevel)}` : ""}`),
  chatbotGreeting: (classLevel) =>
    request(`/api/chatbot/greeting${classLevel ? `?class_level=${encodeURIComponent(classLevel)}` : ""}`),
  chatbotHealth: (provider) => request(`/api/chatbot/health${provider ? `?provider=${encodeURIComponent(provider)}` : ""}`),
  chatbotModels: () => request("/api/chatbot/models"),
  chatbotMentions: (q, limit, classLevel) => request(`/api/chatbot/mentions?q=${encodeURIComponent(q || "")}${limit ? `&limit=${limit}` : ""}${classLevel ? `&class_level=${encodeURIComponent(classLevel)}` : ""}`),

  // ── Recherche unifiée + objectifs quotidiens ────────────────────────────
  search: (q, scope, limit, classLevel) => {
    const params = new URLSearchParams({ q: q || "" });
    if (scope) params.set("scope", Array.isArray(scope) ? scope.join(",") : scope);
    if (limit) params.set("limit", limit);
    if (classLevel) params.set("class_level", classLevel);
    return request(`/api/search?${params.toString()}`);
  },
  dailyGoals: () => request("/api/goals/daily"),

  // Streaming SSE : pas de JSON de retour classique côté succès (le corps est
  // le flux `data: {...}\n\n` lui-même, lu par chatbot.js), donc ces trois
  // fonctions ne passent pas par request() — mais un échec AVANT l'ouverture
  // du flux (ex: 429 quota_exceeded renvoyé par server.py avant de streamer,
  // voir son commentaire) est un vrai JSON classique : vérifié et traduit en
  // Error via buildApiError() comme n'importe quel autre appel, jamais laissé
  // remonter tel quel à consumeStream() qui ne saurait pas le lire. Le CSRF
  // est requis (route mutante), même logique que request().
  chatbotStream: async (conversationId, message, mentions, { signal, classLevel } = {}) => {
    const path = `/api/chatbot/conversations/${conversationId}/messages`;
    const csrfToken = readCookie("nm_csrf");
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
      credentials: "same-origin",
      body: JSON.stringify({
        message, mentions: mentions && mentions.length ? mentions : undefined, class_level: classLevel,
      }),
      signal,
    });
    if (!res.ok) throw buildApiError(path, res.status, await res.json().catch(() => ({})));
    return res;
  },
  chatbotRegenerateStream: async (conversationId, { signal, classLevel } = {}) => {
    const path = `/api/chatbot/conversations/${conversationId}/regenerate`;
    const csrfToken = readCookie("nm_csrf");
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
      credentials: "same-origin",
      body: JSON.stringify({ class_level: classLevel }),
      signal,
    });
    if (!res.ok) throw buildApiError(path, res.status, await res.json().catch(() => ({})));
    return res;
  },
  // Réessai après une erreur réseau réelle : régénère une réponse pour le
  // dernier message utilisateur SANS le renvoyer (déjà persisté côté
  // serveur) — ne coûte pas de quota supplémentaire, voir retry_last().
  chatbotRetryStream: async (conversationId, { signal, classLevel } = {}) => {
    const path = `/api/chatbot/conversations/${conversationId}/retry`;
    const csrfToken = readCookie("nm_csrf");
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
      credentials: "same-origin",
      body: JSON.stringify({ class_level: classLevel }),
      signal,
    });
    if (!res.ok) throw buildApiError(path, res.status, await res.json().catch(() => ({})));
    return res;
  },
  // Upload de fichier (FormData) : pas de Content-Type manuel, le navigateur
  // doit fixer lui-même la frontière multipart — seul le jeton CSRF est ajouté.
  chatbotAttachPdf: async (file) => {
    const csrfToken = readCookie("nm_csrf");
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/chatbot/attachments/pdf", {
      method: "POST",
      headers: { ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}) },
      credentials: "same-origin",
      body: form,
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw buildApiError("/api/chatbot/attachments/pdf", res.status, payload);
    return payload;
  },
};
