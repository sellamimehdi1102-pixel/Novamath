// ── Carte "Série en cours" — partagée entre dashboard.html et chapitres.html ─
import { getInProgressSeries } from "./store.js";
import { icon } from "./icons.js";

const SERIES_TOTAL = 10;

function formatElapsed(seconds) {
  if (seconds < 60) return `${seconds} s`;
  return `${Math.round(seconds / 60)} min`;
}

/** Affiche (ou masque) la carte "Série en cours" dans `container`.
 * Retourne true si une série en cours a été affichée. */
export function renderResumeCard(container) {
  const s = getInProgressSeries();
  if (!s) {
    container.hidden = true;
    return false;
  }

  const elapsed = (s.draftQuestions || []).reduce((sum, q) => sum + (q.duration_s || 0), 0);
  const label = s.seriesConfig?.notion
    ? `${s.seriesConfig.chapterId || ""} · ${s.seriesConfig.notion}`
    : s.seriesConfig?.chapterId || "Entraînement mixte";

  container.hidden = false;
  container.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;">
      <div>
        <div class="badge badge--indigo" style="margin-bottom:8px;">Série en cours</div>
        <h3 style="font-size:1rem; margin-bottom:4px;">${label}</h3>
        <p style="color:var(--text-muted); font-size:0.85rem;">
          Question ${s.seriesIndex + 1}/${SERIES_TOTAL} · Temps écoulé : ${formatElapsed(elapsed)}
        </p>
        <div class="progress-track" style="margin-top:10px; max-width:260px;">
          <div class="progress-fill" style="width:${(s.seriesIndex / SERIES_TOTAL) * 100}%"></div>
        </div>
      </div>
      <a href="exercice.html" class="btn btn-primary">${icon("play")} Reprendre la série</a>
    </div>
  `;
  return true;
}
