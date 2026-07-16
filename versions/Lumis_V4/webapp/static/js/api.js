// ── Wrapper fetch vers l'API Flask existante (contrat inchangé) ────────────
async function request(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    credentials: "same-origin",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`Erreur API ${path}: ${res.status}`);
  return res.json();
}

export const api = {
  chapters: () => request("/api/chapters"),
  start: (chapters) => request("/api/start", { method: "POST", body: { chapters } }),
  answer: (exerciseId, correct) => request("/api/answer", { method: "POST", body: { exercise_id: exerciseId, correct } }),
  practiceLoad: (exerciseId) => request("/api/practice/load", { method: "POST", body: { exercise_id: exerciseId } }),
  practiceResult: (exerciseId, correct) => request("/api/practice/result", { method: "POST", body: { exercise_id: exerciseId, correct } }),
  restart: () => request("/api/restart", { method: "POST" }),
  exercise: (id) => request(`/api/exercise/${id}`),
  getStats: () => request("/api/stats"),
  saveStats: (stats) => request("/api/stats", { method: "POST", body: stats }),
};
