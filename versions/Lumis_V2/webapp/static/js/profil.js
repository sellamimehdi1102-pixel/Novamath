import { bindThemeToggle } from "./theme.js";
import {
  getProfile, setProfile, getState, hydrateFromServer, computeStreak,
  masteryByChapter, levelFromXp, badgeDefs,
} from "./store.js";
import { api } from "./api.js";

bindThemeToggle(document.getElementById("theme-toggle"));

const $ = (id) => document.getElementById(id);
const PAGE_SIZE = 10;
const BADGE_ICONS = {
  ex_10: "🔟", ex_50: "5️⃣0️⃣", ex_100: "💯",
  streak_7: "🔥", streak_30: "🌟",
  chapter_mastered: "🏆", exam_pass: "🎓",
};

let historyPage = 0;
const exerciseCache = new Map();

function formatDuration(seconds) {
  if (!seconds) return "0 min";
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.round(seconds / 60);
  return `${minutes} min`;
}

function render(state) {
  const profile = getProfile();
  $("profile-pseudo").textContent = profile.pseudo || "Élève";
  $("profile-avatar").textContent = (profile.pseudo || "É").charAt(0).toUpperCase();

  const { level, progress } = levelFromXp(state.xp);
  $("profile-level-label").textContent = `Niveau ${level}`;
  $("profile-xp-label").textContent = `${state.xp} XP`;
  $("profile-level-fill").style.width = `${Math.round(progress * 100)}%`;

  const total = state.history.length;
  const correct = state.history.filter((h) => h.correct).length;
  const totalSeconds = state.history.reduce((sum, h) => sum + (h.duration_s || 0), 0);
  $("stat-time").textContent = formatDuration(totalSeconds);
  $("stat-count").textContent = total;
  $("stat-rate").textContent = total ? `${Math.round((correct / total) * 100)}%` : "0%";
  $("stat-streak").textContent = computeStreak(state.history);

  renderRadar(state.history);
  renderBadges(state.badges);
  renderHeatmap(state.history);
  renderSeriesPage(state.series || []);
}

function renderRadar(history) {
  const svg = $("radar-chart");
  const mastery = masteryByChapter(history);
  const chapters = Object.keys(mastery).sort();
  if (!chapters.length) {
    svg.innerHTML = `<text x="150" y="130" text-anchor="middle" fill="var(--text-faint)" font-size="13">Fais des exercices pour voir ton radar</text>`;
    return;
  }
  const cx = 150, cy = 130, maxR = 100;
  const n = chapters.length;
  const angleFor = (i) => (Math.PI * 2 * i) / n - Math.PI / 2;

  let rings = "";
  [0.25, 0.5, 0.75, 1].forEach((f) => {
    const pts = chapters.map((_, i) => {
      const a = angleFor(i);
      return `${(cx + Math.cos(a) * maxR * f).toFixed(1)},${(cy + Math.sin(a) * maxR * f).toFixed(1)}`;
    });
    rings += `<polygon points="${pts.join(" ")}" fill="none" stroke="var(--border)" stroke-width="1"/>`;
  });

  const dataPts = chapters.map((ch, i) => {
    const a = angleFor(i);
    const r = mastery[ch].rate * maxR;
    return `${(cx + Math.cos(a) * r).toFixed(1)},${(cy + Math.sin(a) * r).toFixed(1)}`;
  });

  const labels = chapters.map((ch, i) => {
    const a = angleFor(i);
    const lx = cx + Math.cos(a) * (maxR + 18);
    const ly = cy + Math.sin(a) * (maxR + 18);
    return `<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="middle" font-size="9" fill="var(--text-muted)">${ch.replace("Chapitre_", "C")}</text>`;
  });

  svg.innerHTML = `
    ${rings}
    <polygon points="${dataPts.join(" ")}" fill="rgba(99,102,241,0.28)" stroke="#a855f7" stroke-width="2"/>
    ${labels.join("")}
  `;
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

function renderHeatmap(history) {
  const grid = $("heatmap-grid");
  const counts = {};
  history.forEach((h) => { counts[h.date] = (counts[h.date] || 0) + 1; });

  const days = [];
  for (let i = 181; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }
  grid.innerHTML = days.map((day) => {
    const c = counts[day] || 0;
    const level = c === 0 ? 0 : c === 1 ? 1 : c <= 3 ? 2 : c <= 5 ? 3 : 4;
    return `<div class="heatmap-cell" data-level="${level}" title="${day} : ${c} exercice(s)"></div>`;
  }).join("");
}

function renderSeriesPage(series) {
  const sorted = [...series].reverse();
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  historyPage = Math.min(historyPage, totalPages - 1);
  const slice = sorted.slice(historyPage * PAGE_SIZE, (historyPage + 1) * PAGE_SIZE);

  const body = $("full-history-body");
  body.innerHTML = "";

  if (!slice.length) {
    body.innerHTML = `<tr><td colspan="11" style="color:var(--text-muted);">Aucune série terminée pour l'instant.</td></tr>`;
  } else {
    slice.forEach((s) => {
      const bad = s.total - s.score;
      const dt = new Date(s.endedAt || Date.now());
      const heure = dt.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${s.date}</td>
        <td>${heure}</td>
        <td>${s.chapterId || "Mixte"}</td>
        <td>${s.notion || "—"}</td>
        <td>${s.score}/${s.total}</td>
        <td>${s.accuracy}%</td>
        <td>${formatDuration(s.durationTotal_s || 0)}</td>
        <td>${s.score}</td>
        <td>${bad}</td>
        <td>${s.levelAtTime || "—"}</td>
        <td style="white-space:nowrap;">
          <button class="btn btn-ghost btn-sm btn-review" data-id="${s.id}">👁 Revoir</button>
          <button class="btn btn-ghost btn-sm btn-restart-series" data-id="${s.id}">🔄 Recommencer</button>
          <a href="chapitres.html" class="btn btn-ghost btn-sm">📚 Chapitres</a>
        </td>
      `;
      body.appendChild(row);

      row.querySelector(".btn-review").addEventListener("click", () => toggleReview(row, s));
      row.querySelector(".btn-restart-series").addEventListener("click", () => restartSeries(s));
    });
  }

  $("btn-prev-page").disabled = historyPage === 0;
  $("btn-next-page").disabled = historyPage >= totalPages - 1;
}

async function toggleReview(row, series) {
  const existing = row.nextElementSibling;
  if (existing && existing.classList.contains("series-review-row")) {
    existing.remove();
    return;
  }

  const reviewRow = document.createElement("tr");
  reviewRow.className = "series-review-row";
  const cell = document.createElement("td");
  cell.colSpan = 11;
  cell.textContent = "Chargement du détail...";
  reviewRow.appendChild(cell);
  row.after(reviewRow);

  const details = await Promise.all(
    series.questions.map(async (q) => {
      if (!exerciseCache.has(q.exercise_id)) {
        try {
          const data = await api.exercise(q.exercise_id);
          exerciseCache.set(q.exercise_id, data.exercise);
        } catch {
          exerciseCache.set(q.exercise_id, null);
        }
      }
      return { q, ex: exerciseCache.get(q.exercise_id) };
    })
  );

  cell.innerHTML = details.map(({ q, ex }) => `
    <div class="series-review-item">
      <span>${ex ? ex.enonce : "(exercice indisponible)"}</span>
      <span class="badge ${q.correct ? "badge--success" : "badge--danger"}">${q.correct ? "Réussi" : "Échoué"}</span>
    </div>
  `).join("");
}

function restartSeries(series) {
  const exerciseIds = [...new Set(series.questions.map((q) => q.exercise_id))];
  localStorage.setItem(
    "lumis:pending_series",
    JSON.stringify({ mode: series.mode, chapterId: series.chapterId, notion: series.notion, exerciseIds })
  );
  window.location.href = "exercice.html";
}

$("btn-prev-page").addEventListener("click", () => {
  historyPage = Math.max(0, historyPage - 1);
  renderSeriesPage(getState().series || []);
});
$("btn-next-page").addEventListener("click", () => {
  historyPage += 1;
  renderSeriesPage(getState().series || []);
});

$("btn-edit-pseudo").addEventListener("click", () => {
  const current = getProfile();
  const next = prompt("Ton pseudo :", current.pseudo || "Élève");
  if (next && next.trim()) {
    setProfile({ ...current, pseudo: next.trim() });
    render(getState());
  }
});

async function init() {
  render(getState());
  const fresh = await hydrateFromServer();
  render(fresh);
}

init();
