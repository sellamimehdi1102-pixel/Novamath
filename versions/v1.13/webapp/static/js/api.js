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
  if (!res.ok) {
    const err = new Error(payload.error || `Erreur API ${path}: ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return payload;
}

export const api = {
  chapters: () => request("/api/chapters"),
  getSiteStats: () => request("/api/site/stats"),
  start: (chapters) => request("/api/start", { method: "POST", body: { chapters } }),
  answer: (exerciseId, correct) => request("/api/answer", { method: "POST", body: { exercise_id: exerciseId, correct } }),
  practiceLoad: (exerciseId) => request("/api/practice/load", { method: "POST", body: { exercise_id: exerciseId } }),
  practiceResult: (exerciseId, correct) => request("/api/practice/result", { method: "POST", body: { exercise_id: exerciseId, correct } }),
  restart: () => request("/api/restart", { method: "POST" }),
  exercise: (id) => request(`/api/exercise/${id}`),
  getStats: () => request("/api/stats"),
  saveStats: (stats) => request("/api/stats", { method: "POST", body: stats }),

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
};
