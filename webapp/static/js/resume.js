// ── Carte "Série en cours" — partagée entre dashboard.html et chapitres.html ─
import { getInProgressSeries } from "./store.js";
import { icon } from "./icons.js";

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
  const chapter = s.seriesConfig?.chapterId || "Entraînement mixte";
  const notion = s.seriesConfig?.notion || "—";
  const total = s.total || 10;
  const progressPct = s.progressPct ?? Math.round((s.seriesIndex / total) * 100);

  container.hidden = false;
  container.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;">
      <div>
        <h3 style="font-size:1rem; margin-bottom:10px; display:flex; align-items:center; gap:8px;">${icon("bookOpen")} Série en cours</h3>
        <div style="display:flex; gap:18px; flex-wrap:wrap; font-size:0.85rem; color:var(--text-muted); margin-bottom:8px;">
          <span>Chapitre : <strong style="color:var(--text);">${chapter}</strong></span>
          <span>Notion : <strong style="color:var(--text);">${notion}</strong></span>
          <span>Question <strong style="color:var(--text);">${s.seriesIndex + 1} / ${total}</strong></span>
          <span>Temps écoulé : <strong style="color:var(--text);">${formatElapsed(elapsed)}</strong></span>
        </div>
        <div class="progress-track" style="max-width:260px;">
          <div class="progress-fill" style="width:${progressPct}%"></div>
        </div>
      </div>
      <a href="exercice.html?resume=1" class="btn btn-primary">${icon("play")} Reprendre la série</a>
    </div>
  `;
  return true;
}
