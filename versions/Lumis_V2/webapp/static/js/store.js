// ── Store de gamification ───────────────────────────────────────────────────
// Source de vérité locale (localStorage), synchronisée vers /api/stats (fichier
// serveur additif) pour survivre aux redémarrages. Toutes les valeurs sont
// calculées à partir des vraies réponses de l'élève — jamais de données inventées.
import { api } from "./api.js";

const STORE_KEY = "lumis:stats";
const PROFILE_KEY = "lumis:profile";

const XP_MULT = { 1: 1, 2: 1.5, 3: 2 };
const LEVEL_THRESHOLDS = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200, 4000];

const BADGE_DEFS = [
  { id: "ex_10", label: "10 exercices", test: (s) => s.history.length >= 10 },
  { id: "ex_50", label: "50 exercices", test: (s) => s.history.length >= 50 },
  { id: "ex_100", label: "100 exercices", test: (s) => s.history.length >= 100 },
  { id: "streak_7", label: "Série de 7 jours", test: (s) => computeStreak(s.history) >= 7 },
  { id: "streak_30", label: "Série de 30 jours", test: (s) => computeStreak(s.history) >= 30 },
  {
    id: "chapter_mastered",
    label: "Un chapitre à 100%",
    test: (s) => Object.values(masteryByChapter(s.history)).some((m) => m.rate >= 1 && m.count >= 5),
  },
  { id: "exam_pass", label: "Premier examen blanc réussi", test: (s) => s.history.some((h) => h.mode === "examen" && h.correct) },
];

function emptyState() {
  return { xp: 0, history: [], badges: [], series: [] };
}

function load() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    return raw ? { ...emptyState(), ...JSON.parse(raw) } : emptyState();
  } catch {
    return emptyState();
  }
}

function persist(state) {
  localStorage.setItem(STORE_KEY, JSON.stringify(state));
  // Synchronisation best-effort vers le serveur — ne bloque jamais l'UI.
  api.saveStats(state).catch(() => {});
}

export function getProfile() {
  try {
    return JSON.parse(localStorage.getItem(PROFILE_KEY)) || { pseudo: "Élève" };
  } catch {
    return { pseudo: "Élève" };
  }
}

export function setProfile(profile) {
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
}

export function computeStreak(history) {
  if (!history.length) return 0;
  const days = [...new Set(history.map((h) => h.date))].sort().reverse();
  let streak = 0;
  let cursor = new Date();
  cursor.setHours(0, 0, 0, 0);
  for (const day of days) {
    const d = new Date(day);
    d.setHours(0, 0, 0, 0);
    const diffDays = Math.round((cursor - d) / 86400000);
    if (diffDays === 0 || diffDays === 1) {
      streak += 1;
      cursor = d;
    } else {
      break;
    }
  }
  return streak;
}

export function masteryByChapter(history) {
  const byChapter = {};
  for (const h of history) {
    const key = h.chapter || "?";
    byChapter[key] = byChapter[key] || { total: 0, correct: 0 };
    byChapter[key].total += 1;
    if (h.correct) byChapter[key].correct += 1;
  }
  const out = {};
  for (const [chapter, v] of Object.entries(byChapter)) {
    out[chapter] = { count: v.total, rate: v.total ? v.correct / v.total : 0 };
  }
  return out;
}

export function masteryByNotion(history) {
  const byNotion = {};
  for (const h of history) {
    const key = `${h.chapter}|${h.notion}`;
    byNotion[key] = byNotion[key] || { total: 0, correct: 0, last: null };
    byNotion[key].total += 1;
    if (h.correct) byNotion[key].correct += 1;
    if (!byNotion[key].last || h.ts > byNotion[key].last) byNotion[key].last = h.ts;
  }
  const out = {};
  for (const [key, v] of Object.entries(byNotion)) {
    out[key] = { count: v.total, rate: v.total ? v.correct / v.total : 0, last: v.last };
  }
  return out;
}

export function levelFromXp(xp) {
  let level = 1;
  for (let i = 0; i < LEVEL_THRESHOLDS.length; i++) {
    if (xp >= LEVEL_THRESHOLDS[i]) level = i + 1;
  }
  const floor = LEVEL_THRESHOLDS[level - 1] ?? 0;
  const ceilIdx = Math.min(level, LEVEL_THRESHOLDS.length - 1);
  const ceil = LEVEL_THRESHOLDS[ceilIdx] ?? floor + 800;
  const progress = ceil > floor ? Math.min(1, (xp - floor) / (ceil - floor)) : 1;
  return { level, floor, ceil, progress };
}

export function recordAnswer({ id, chapter, notion, difficulty, correct, usedHint, mode, duration_s }) {
  const state = load();
  const base = 10 * (XP_MULT[difficulty] || 1);
  const bonus = correct && !usedHint ? 5 : 0;
  const gained = correct ? Math.round(base + bonus) : 0;

  state.xp += gained;
  state.history.push({
    id,
    date: new Date().toISOString().slice(0, 10),
    ts: Date.now(),
    chapter,
    notion,
    difficulty,
    correct: !!correct,
    mode: mode || "revisions",
    duration_s: duration_s || 0,
  });

  const unlockedBefore = new Set(state.badges);
  state.badges = BADGE_DEFS.filter((b) => b.test(state)).map((b) => b.id);
  const newlyUnlocked = state.badges.filter((id) => !unlockedBefore.has(id));

  persist(state);
  return { gained, state, newlyUnlocked };
}

export function getState() {
  return load();
}

export function badgeDefs() {
  return BADGE_DEFS;
}

// ── Séries (regroupement de 10 questions d'entraînement, ou 7 pour l'évaluation) ─
export function createSeriesDraft({ mode, chapterId, notion, total }) {
  return { id: `s_${Date.now()}`, startedAt: Date.now(), mode, chapterId, notion, total, questions: [] };
}

export function addSeriesQuestion(draft, question) {
  draft.questions.push(question);
}

export function finalizeSeries(draft, extra = {}) {
  const state = load();
  const total = draft.questions.length;
  const score = draft.questions.filter((q) => q.correct).length;
  const durationTotal_s = draft.questions.reduce((sum, q) => sum + (q.duration_s || 0), 0);

  const record = {
    id: draft.id,
    date: new Date().toISOString().slice(0, 10),
    startedAt: draft.startedAt,
    endedAt: Date.now(),
    mode: draft.mode,
    chapterId: draft.chapterId,
    notion: draft.notion || null,
    questions: draft.questions,
    score,
    total,
    accuracy: total ? Math.round((score / total) * 100) : 0,
    durationTotal_s,
    levelAtTime: extra.levelAtTime || null,
  };

  state.series = state.series || [];
  state.series.push(record);
  persist(state);
  return record;
}

export function getSeries() {
  return load().series || [];
}

export function getSeriesById(id) {
  return getSeries().find((s) => s.id === id) || null;
}

/** Accuracy globale sur 20, arrondie au demi-point, à partir de tout l'historique. */
export function accuracyOutOf20(history) {
  if (!history.length) return 0;
  const correct = history.filter((h) => h.correct).length;
  return Math.round((correct / history.length) * 20 * 2) / 2;
}

export async function hydrateFromServer() {
  try {
    const remote = await api.getStats();
    if (remote && Array.isArray(remote.history) && remote.history.length) {
      const local = load();
      if (remote.history.length > local.history.length) {
        persist(remote);
        return remote;
      }
    }
  } catch {
    /* pas grave — on reste en local si le serveur est indisponible */
  }
  return load();
}
