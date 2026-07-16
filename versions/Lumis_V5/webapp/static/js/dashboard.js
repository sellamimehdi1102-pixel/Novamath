import { bindThemeToggle } from "./theme.js";
import {
  getProfile, getState, hydrateFromServer, computeStreak, masteryByChapter,
  coverageByChapter, levelFromXp, badgeDefs, accuracyOutOf20,
} from "./store.js";
import { renderResumeCard } from "./resume.js";
import { getChaptersMeta, buildSeriesRow } from "./seriesview.js";
import { icon } from "./icons.js";

bindThemeToggle(document.getElementById("theme-toggle"));
renderResumeCard(document.getElementById("resume-card"));

const $ = (id) => document.getElementById(id);
const RING_CIRCUMFERENCE = 2 * Math.PI * 18;

const BADGE_ICONS = {
  ex_10: "🔟", ex_50: "5️⃣0️⃣", ex_100: "💯",
  streak_7: "🔥", streak_30: "🌟",
  chapter_mastered: "🏆", exam_pass: "🎓",
};

let chartWindow = 20;
let chaptersMeta = [];

function render(state) {
  const profile = getProfile();
  $("greeting").textContent = `Bonjour ${profile.pseudo || "Élève"} 👋`;

  const streak = computeStreak(state.history);
  $("streak-value").textContent = streak;

  const { level, progress } = levelFromXp(state.xp);
  $("xp-level").textContent = `Niveau ${level}`;
  $("xp-value").textContent = `${state.xp} XP`;
  const offset = RING_CIRCUMFERENCE * (1 - progress);
  $("xp-ring-fill").setAttribute("stroke-dasharray", RING_CIRCUMFERENCE.toFixed(1));
  $("xp-ring-fill").setAttribute("stroke-dashoffset", offset.toFixed(1));

  renderRealTime(state.history);
  renderAccuracy(state.history);
  renderWeekGrid(state.history);
  renderProgressChart(state.series || []);
  renderMasteryLists(state.history);
  renderSuggestions(state.history);
  renderSeriesTable(state.series || []);
  renderBadges(state.badges);
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function renderRealTime(history) {
  const today = todayStr();
  const now = Date.now();
  const weekMs = 7 * 86400000;

  const sumDuration = (predicate) =>
    history.filter(predicate).reduce((sum, h) => sum + (h.duration_s || 0), 0);

  const todaySeconds = sumDuration((h) => h.date === today);
  const weekSeconds = sumDuration((h) => now - h.ts < weekMs);
  const totalSeconds = sumDuration(() => true);

  $("time-today").textContent = formatDuration(todaySeconds);
  $("time-week").textContent = `Cette semaine : ${formatDuration(weekSeconds)}`;
  $("time-total").textContent = `Depuis le début : ${formatDuration(totalSeconds)}`;
}

function formatDuration(seconds) {
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `${hours} h ${rest.toString().padStart(2, "0")}`;
}

function renderAccuracy(history) {
  const acc = accuracyOutOf20(history);
  $("accuracy-value").textContent = `${acc} / 20`;
  const badge = $("accuracy-badge");
  badge.classList.remove("badge--success", "badge--warning", "badge--danger", "badge--neutral");
  if (!history.length) {
    badge.classList.add("badge--neutral");
    badge.textContent = "Pas encore de données";
  } else if (acc >= 16) {
    badge.classList.add("badge--success");
    badge.textContent = "Excellent";
  } else if (acc >= 10) {
    badge.classList.add("badge--warning");
    badge.textContent = "Correct";
  } else {
    badge.classList.add("badge--danger");
    badge.textContent = "À renforcer";
  }
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

function renderProgressChart(series) {
  const svg = $("progress-chart");
  const tooltip = $("chart-tooltip");
  if (!series.length) {
    svg.innerHTML = `<text x="300" y="90" text-anchor="middle" fill="var(--text-faint)" font-size="14">Termine une série pour voir ta progression</text>`;
    return;
  }
  const windowed = chartWindow === "all" ? series : series.slice(-chartWindow);
  const points = windowed.map((s, i) => {
    const x = windowed.length > 1 ? (i / (windowed.length - 1)) * 580 + 10 : 300;
    const y = 160 - (s.accuracy / 100) * 140;
    return { x, y, s };
  });

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const dots = points
    .map((p, i) => `<circle data-idx="${i}" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4" fill="#a855f7" class="chart-dot"/>`)
    .join("");
  const hitAreas = points
    .map((p, i) => `<circle data-idx="${i}" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="12" fill="transparent" class="chart-hit"/>`)
    .join("");

  svg.innerHTML = `
    <line x1="10" y1="160" x2="590" y2="160" stroke="var(--border)" stroke-width="1"/>
    <path d="${path}" fill="none" stroke="url(#linegrad)" stroke-width="3" stroke-linecap="round" style="transition: d 300ms ease;"/>
    ${dots}
    ${hitAreas}
    <defs><linearGradient id="linegrad" x1="0" y1="0" x2="600" y2="0"><stop offset="0" stop-color="#6366f1"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs>
  `;

  svg.querySelectorAll(".chart-hit").forEach((hit) => {
    hit.addEventListener("mousemove", (e) => {
      const idx = Number(hit.dataset.idx);
      const point = points[idx];
      const rect = svg.getBoundingClientRect();
      const scaleX = rect.width / 600;
      const scaleY = rect.height / 180;
      tooltip.style.display = "block";
      tooltip.style.left = `${point.x * scaleX + 12}px`;
      tooltip.style.top = `${point.y * scaleY - 10}px`;
      const d = point.s;
      const label = d.notion ? `${d.chapterId || ""} · ${d.notion}` : d.chapterId || "Mixte";
      tooltip.innerHTML = `<strong>${d.accuracy}%</strong> (${d.score}/${d.total})<br>${label}<br>${d.date}`;
    });
    hit.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
  });
}

document.querySelectorAll(".chart-zoom-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".chart-zoom-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    chartWindow = btn.dataset.window === "all" ? "all" : Number(btn.dataset.window);
    renderProgressChart(getState().series || []);
  });
});

function chapterBubbleHtml(chapterId, m, badgeClass, weakestNotion) {
  const meta = chaptersMeta.find((c) => c.id === chapterId);
  const num = chapterId.replace("Chapitre_", "");
  const title = meta?.title || chapterId;
  const coveragePct = meta?.n_exercises ? Math.round((m.covered / meta.n_exercises) * 100) : 0;
  const accuracyPct = Math.round(m.rate * 100);

  return `
    <div class="mini-row" style="align-items:center;">
      <div>
        <div style="font-weight:600; font-size:0.88rem;">Chapitre ${num} — ${title}</div>
        <div style="color:var(--text-muted); font-size:0.78rem; margin-top:2px;">
          Progression ${coveragePct}% · Accuracy
          <span class="badge ${badgeClass}" style="margin-left:2px;">${accuracyPct}%</span>
        </div>
      </div>
      <button class="btn btn-ghost btn-sm btn-goto-chapter" data-chapter="${chapterId}" data-notion="${weakestNotion || ""}">
        ${icon("arrowRight")} Aller au chapitre
      </button>
    </div>`;
}

function weakestNotionOf(history, chapterId) {
  const byNotion = {};
  history.filter((h) => h.chapter === chapterId).forEach((h) => {
    byNotion[h.notion] = byNotion[h.notion] || { total: 0, correct: 0 };
    byNotion[h.notion].total += 1;
    if (h.correct) byNotion[h.notion].correct += 1;
  });
  const entries = Object.entries(byNotion).map(([n, v]) => ({ n, rate: v.correct / v.total }));
  entries.sort((a, b) => a.rate - b.rate);
  return entries[0]?.n || "";
}

function bindGotoChapterButtons(container) {
  container.querySelectorAll(".btn-goto-chapter").forEach((btn) => {
    btn.addEventListener("click", () => {
      localStorage.setItem(
        "lumis:open_chapter",
        JSON.stringify({ chapterId: btn.dataset.chapter, notion: btn.dataset.notion || null })
      );
      window.location.href = "chapitres.html";
    });
  });
}

function renderMasteryLists(history) {
  const mastery = masteryByChapter(history);
  const coverage = coverageByChapter(history);
  const enriched = Object.entries(mastery).map(([ch, m]) => ({ ch, ...m, covered: (coverage[ch] || new Set()).size }));

  const mastered = enriched.filter((m) => m.rate >= 0.8 && m.count >= 3);
  const toReview = enriched.filter((m) => m.rate < 0.6 && m.count >= 1);

  const masteredEl = $("chapters-mastered");
  const reviewEl = $("chapters-to-review");
  masteredEl.innerHTML = mastered.length
    ? mastered.map((m) => chapterBubbleHtml(m.ch, m, "badge--success")).join("")
    : `<p style="color:var(--text-muted); font-size:0.85rem;">Aucun chapitre maîtrisé pour l'instant.</p>`;
  reviewEl.innerHTML = toReview.length
    ? toReview.map((m) => chapterBubbleHtml(m.ch, m, "badge--danger", weakestNotionOf(history, m.ch))).join("")
    : `<p style="color:var(--text-muted); font-size:0.85rem;">Rien à signaler — continue comme ça !</p>`;

  bindGotoChapterButtons(masteredEl);
  bindGotoChapterButtons(reviewEl);
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
    : `<div class="suggestion-card">Belle régularité ! Continue l'entraînement pour progresser encore.</div>`;
}

function renderSeriesTable(series) {
  const body = $("history-body");
  body.innerHTML = "";
  const recent = [...series].reverse().slice(0, 8);
  if (!recent.length) {
    body.innerHTML = `<tr><td colspan="11" style="color:var(--text-muted);">Aucune série terminée pour l'instant.</td></tr>`;
    return;
  }
  const titles = {};
  chaptersMeta.forEach((ch) => { titles[ch.id] = ch.title; });
  recent.forEach((s) => body.appendChild(buildSeriesRow(s, titles)));
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
  chaptersMeta = await getChaptersMeta();
  render(getState());
  const fresh = await hydrateFromServer();
  render(fresh);
}

init();
