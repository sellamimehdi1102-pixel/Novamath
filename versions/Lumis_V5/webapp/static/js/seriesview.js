// ── Rendu partagé de l'historique des séries (Dashboard + Profil) ──────────
// Centralise le format de date FR, le calcul du temps, et le détail "Revoir",
// pour éviter de dupliquer cette logique entre dashboard.js et profil.js.
import { api } from "./api.js";
import { icon } from "./icons.js";

let chaptersMetaCache = null;
const exerciseCache = new Map();

/** Récupère (et met en cache) chapters_meta une seule fois par page. */
export async function getChaptersMeta() {
  if (chaptersMetaCache) return chaptersMetaCache;
  try {
    const data = await api.chapters();
    chaptersMetaCache = data.chapters_meta || [];
  } catch {
    chaptersMetaCache = [];
  }
  return chaptersMetaCache;
}

export async function getChapterTitles() {
  const meta = await getChaptersMeta();
  const titles = {};
  meta.forEach((ch) => { titles[ch.id] = ch.title; });
  return titles;
}

export function formatDateFR(isoDate) {
  if (!isoDate) return "—";
  const [y, m, d] = isoDate.split("-");
  return `${d}/${m}/${y}`;
}

export function formatDuration(seconds) {
  if (!seconds) return "0 min";
  if (seconds < 60) return `${seconds} s`;
  return `${Math.round(seconds / 60)} min`;
}

export function chapterLabel(chapterId, chapterTitles) {
  if (!chapterId) return "Mixte";
  const num = chapterId.replace("Chapitre_", "");
  const title = chapterTitles[chapterId];
  return title ? `Chapitre ${num} · ${title}` : chapterId;
}

/** Construit une ligne de tableau pour une série, avec bouton Revoir (détail
 * question par question) et, optionnellement, Recommencer. */
export function buildSeriesRow(series, chapterTitles, { withRestart = false } = {}) {
  const bad = series.total - series.score;
  const dt = new Date(series.endedAt || Date.now());
  const heure = dt.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });

  const row = document.createElement("tr");
  row.innerHTML = `
    <td>${formatDateFR(series.date)}</td>
    <td>${heure}</td>
    <td>${chapterLabel(series.chapterId, chapterTitles)}</td>
    <td>${series.notion || "—"}</td>
    <td>${series.score}/${series.total}</td>
    <td>${series.accuracy}%</td>
    <td>${formatDuration(series.durationTotal_s || 0)}</td>
    <td>${series.score}</td>
    <td>${bad}</td>
    <td>${series.levelAtTime || "—"}</td>
    <td style="white-space:nowrap;">
      <button class="btn btn-ghost btn-sm btn-review">${icon("eye")} Revoir</button>
      ${withRestart ? `<button class="btn btn-ghost btn-sm btn-restart-series">${icon("rotate")} Recommencer</button>` : ""}
    </td>
  `;

  row.querySelector(".btn-review").addEventListener("click", () => toggleReview(row, series));
  if (withRestart) {
    row.querySelector(".btn-restart-series").addEventListener("click", () => restartSeries(series));
  }
  return row;
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

export function restartSeries(series) {
  const exerciseIds = [...new Set(series.questions.map((q) => q.exercise_id))];
  localStorage.setItem(
    "lumis:pending_series",
    JSON.stringify({ mode: series.mode, chapterId: series.chapterId, notion: series.notion, exerciseIds })
  );
  window.location.href = "exercice.html";
}
