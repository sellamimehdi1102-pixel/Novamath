import { bindThemeToggle } from "./theme.js";
import { getProfile, getState, hydrateFromServer, computeStreak, masteryByChapter, levelFromXp, badgeDefs } from "./store.js";

bindThemeToggle(document.getElementById("theme-toggle"));

const $ = (id) => document.getElementById(id);
const RING_CIRCUMFERENCE = 2 * Math.PI * 18;
const WEEKLY_GOAL = 20;
const MIN_PER_EXERCISE = 3;

const BADGE_ICONS = {
  ex_10: "🔟", ex_50: "5️⃣0️⃣", ex_100: "💯",
  streak_7: "🔥", streak_30: "🌟",
  chapter_mastered: "🏆", exam_pass: "🎓",
};

function render(state) {
  const profile = getProfile();
  $("greeting").textContent = `Bonjour ${profile.pseudo || "Élève"} 👋`;

  const streak = computeStreak(state.history);
  $("streak-value").textContent = streak;

  const { level, floor, ceil, progress } = levelFromXp(state.xp);
  $("xp-level").textContent = `Niveau ${level}`;
  $("xp-value").textContent = `${state.xp} XP`;
  const offset = RING_CIRCUMFERENCE * (1 - progress);
  $("xp-ring-fill").setAttribute("stroke-dasharray", RING_CIRCUMFERENCE.toFixed(1));
  $("xp-ring-fill").setAttribute("stroke-dashoffset", offset.toFixed(1));

  const now = Date.now();
  const weekMs = 7 * 86400000;
  const thisWeek = state.history.filter((h) => now - h.ts < weekMs);
  $("time-week").textContent = `${thisWeek.length * MIN_PER_EXERCISE} min`;
  $("goal-value").textContent = `${thisWeek.length} / ${WEEKLY_GOAL}`;
  $("goal-fill").style.width = `${Math.min(100, (thisWeek.length / WEEKLY_GOAL) * 100)}%`;

  renderWeekGrid(state.history);
  renderProgressChart(state.history);
  renderMasteryLists(state.history);
  renderSuggestions(state.history);
  renderHistoryTable(state.history);
  renderBadges(state.badges);
}

function renderWeekGrid(history) {
  const grid = $("week-grid");
  grid.innerHTML = "";
  const days = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }
  const activeDays = new Set(history.map((h) => h.date));
  days.forEach((day) => {
    const cell = document.createElement("div");
    cell.className = `week-day${activeDays.has(day) ? " active" : ""}`;
    cell.title = day;
    grid.appendChild(cell);
  });
}

function renderProgressChart(history) {
  const svg = $("progress-chart");
  if (!history.length) {
    svg.innerHTML = `<text x="300" y="90" text-anchor="middle" fill="var(--text-faint)" font-size="14">Pas encore d'historique</text>`;
    return;
  }
  const byDay = {};
  history.forEach((h) => {
    byDay[h.date] = byDay[h.date] || { total: 0, correct: 0 };
    byDay[h.date].total += 1;
    if (h.correct) byDay[h.date].correct += 1;
  });
  const days = Object.keys(byDay).sort().slice(-14);
  const points = days.map((day, i) => {
    const rate = byDay[day].correct / byDay[day].total;
    const x = days.length > 1 ? (i / (days.length - 1)) * 580 + 10 : 300;
    const y = 160 - rate * 140;
    return [x, y];
  });
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
  const dots = points.map((p) => `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="3.5" fill="#a855f7"/>`).join("");
  svg.innerHTML = `
    <line x1="10" y1="160" x2="590" y2="160" stroke="var(--border)" stroke-width="1"/>
    <path d="${path}" fill="none" stroke="url(#linegrad)" stroke-width="3" stroke-linecap="round"/>
    ${dots}
    <defs><linearGradient id="linegrad" x1="0" y1="0" x2="600" y2="0"><stop offset="0" stop-color="#6366f1"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs>
  `;
}

function renderMasteryLists(history) {
  const mastery = masteryByChapter(history);
  const mastered = Object.entries(mastery).filter(([, m]) => m.rate >= 0.8 && m.count >= 3);
  const toReview = Object.entries(mastery).filter(([, m]) => m.rate < 0.6 && m.count >= 1);

  const masteredEl = $("chapters-mastered");
  const reviewEl = $("chapters-to-review");
  masteredEl.innerHTML = mastered.length
    ? mastered.map(([ch, m]) => `<div class="mini-row"><span>${ch}</span><span class="badge badge--success">${Math.round(m.rate * 100)}%</span></div>`).join("")
    : `<p style="color:var(--text-muted); font-size:0.85rem;">Aucun chapitre maîtrisé pour l'instant.</p>`;
  reviewEl.innerHTML = toReview.length
    ? toReview.map(([ch, m]) => `<div class="mini-row"><span>${ch}</span><span class="badge badge--danger">${Math.round(m.rate * 100)}%</span></div>`).join("")
    : `<p style="color:var(--text-muted); font-size:0.85rem;">Rien à signaler — continue comme ça !</p>`;
}

function renderSuggestions(history) {
  const el = $("suggestions");
  if (!history.length) {
    el.innerHTML = `<div class="suggestion-card">Fais ta première évaluation pour recevoir des suggestions personnalisées.</div>`;
    return;
  }
  const byNotion = {};
  history.forEach((h) => {
    const key = `${h.chapter} : ${h.notion}`;
    byNotion[key] = byNotion[key] || { total: 0, correct: 0 };
    byNotion[key].total += 1;
    if (h.correct) byNotion[key].correct += 1;
  });
  const weak = Object.entries(byNotion)
    .map(([k, v]) => ({ key: k, rate: v.correct / v.total }))
    .filter((x) => x.rate < 0.6)
    .sort((a, b) => a.rate - b.rate)
    .slice(0, 3);

  el.innerHTML = weak.length
    ? weak.map((w) => `<div class="suggestion-card">Reprends <strong>${w.key}</strong> — ${Math.round(w.rate * 100)}% de réussite.</div>`).join("")
    : `<div class="suggestion-card">Belle régularité ! Continue l'entraînement libre pour progresser encore.</div>`;
}

function renderHistoryTable(history) {
  const body = $("history-body");
  const recent = [...history].reverse().slice(0, 8);
  body.innerHTML = recent.length
    ? recent.map((h) => `
        <tr>
          <td>${h.date}</td>
          <td>${h.chapter || "—"}</td>
          <td>${h.notion || "—"}</td>
          <td>${h.correct ? '<span class="badge badge--success">Réussi</span>' : '<span class="badge badge--danger">Échoué</span>'}</td>
        </tr>`).join("")
    : `<tr><td colspan="4" style="color:var(--text-muted);">Aucun exercice pour l'instant.</td></tr>`;
}

function renderBadges(unlocked) {
  const grid = $("badges-grid");
  const unlockedSet = new Set(unlocked);
  grid.innerHTML = badgeDefs().map((b) => `
    <div class="badge-tile${unlockedSet.has(b.id) ? " unlocked" : ""}">
      <div class="icon">${BADGE_ICONS[b.id] || "🏅"}</div>
      <div class="name">${b.label}</div>
    </div>
  `).join("");
}

async function init() {
  render(getState());
  const fresh = await hydrateFromServer();
  render(fresh);
}

init();
