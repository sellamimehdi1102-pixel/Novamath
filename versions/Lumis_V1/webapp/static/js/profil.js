import { bindThemeToggle } from "./theme.js";
import { getProfile, setProfile, getState, hydrateFromServer, computeStreak, masteryByChapter, levelFromXp, badgeDefs } from "./store.js";

bindThemeToggle(document.getElementById("theme-toggle"));

const $ = (id) => document.getElementById(id);
const MIN_PER_EXERCISE = 3;
const PAGE_SIZE = 10;
const BADGE_ICONS = {
  ex_10: "🔟", ex_50: "5️⃣0️⃣", ex_100: "💯",
  streak_7: "🔥", streak_30: "🌟",
  chapter_mastered: "🏆", exam_pass: "🎓",
};

let historyPage = 0;

function render(state) {
  const profile = getProfile();
  $("profile-pseudo").textContent = profile.pseudo || "Élève";
  $("profile-avatar").textContent = (profile.pseudo || "É").charAt(0).toUpperCase();

  const { level, floor, ceil, progress } = levelFromXp(state.xp);
  $("profile-level-label").textContent = `Niveau ${level}`;
  $("profile-xp-label").textContent = `${state.xp} XP`;
  $("profile-level-fill").style.width = `${Math.round(progress * 100)}%`;

  const total = state.history.length;
  const correct = state.history.filter((h) => h.correct).length;
  $("stat-time").textContent = `${total * MIN_PER_EXERCISE} min`;
  $("stat-count").textContent = total;
  $("stat-rate").textContent = total ? `${Math.round((correct / total) * 100)}%` : "0%";
  $("stat-streak").textContent = computeStreak(state.history);

  renderRadar(state.history);
  renderBadges(state.badges);
  renderHeatmap(state.history);
  renderHistoryPage(state.history);
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

function renderHistoryPage(history) {
  const sorted = [...history].reverse();
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  historyPage = Math.min(historyPage, totalPages - 1);
  const slice = sorted.slice(historyPage * PAGE_SIZE, (historyPage + 1) * PAGE_SIZE);

  $("full-history-body").innerHTML = slice.length
    ? slice.map((h) => `
        <tr>
          <td>${h.date}</td>
          <td>${h.chapter || "—"}</td>
          <td>${h.notion || "—"}</td>
          <td>${h.mode || "libre"}</td>
          <td>${h.correct ? '<span class="badge badge--success">Réussi</span>' : '<span class="badge badge--danger">Échoué</span>'}</td>
        </tr>`).join("")
    : `<tr><td colspan="5" style="color:var(--text-muted);">Aucun exercice pour l'instant.</td></tr>`;

  $("btn-prev-page").disabled = historyPage === 0;
  $("btn-next-page").disabled = historyPage >= totalPages - 1;
}

$("btn-prev-page").addEventListener("click", () => {
  historyPage = Math.max(0, historyPage - 1);
  renderHistoryPage(getState().history);
});
$("btn-next-page").addEventListener("click", () => {
  historyPage += 1;
  renderHistoryPage(getState().history);
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
