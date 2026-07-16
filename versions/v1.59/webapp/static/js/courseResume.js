// ── Carte "Reprendre mon cours" — Dashboard, même esprit que resume.js ─────
import { api } from "./api.js";
import { icon } from "./icons.js";

/** Affiche (ou masque) la carte de reprise de lecture dans `container`.
 * Cherche, parmi toutes les notions en cours ("in_progress"), la plus
 * récemment mise à jour, et propose d'y retourner directement. */
export async function renderCourseResumeCard(container) {
  let progress, chaptersData;
  try {
    [progress, chaptersData] = await Promise.all([api.getCourseProgress(), api.chapters()]);
  } catch {
    container.hidden = true;
    return;
  }

  let best = null;
  for (const [chapterId, notions] of Object.entries(progress || {})) {
    for (const [notionId, entry] of Object.entries(notions || {})) {
      if (entry.status !== "in_progress") continue;
      if (!best || (entry.updatedAt || 0) > (best.entry.updatedAt || 0)) {
        best = { chapterId, notionId, entry };
      }
    }
  }

  if (!best) {
    container.hidden = true;
    return;
  }

  const chapterMeta = (chaptersData.chapters_meta || []).find((c) => c.id === best.chapterId);
  const chapterTitle = chapterMeta?.title || best.chapterId;

  container.hidden = false;
  container.innerHTML = `
    <div style="display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;">
      <div>
        <h3 style="font-size:1rem; margin-bottom:10px;">${icon("bookOpen")} Reprendre mon cours</h3>
        <div style="font-size:0.85rem; color:var(--text-muted);">
          <span>Chapitre : <strong style="color:var(--text);">${chapterTitle}</strong></span>
        </div>
      </div>
      <a href="cours.html?chapter=${encodeURIComponent(best.chapterId)}&notion=${encodeURIComponent(best.notionId)}" class="btn btn-primary">
        ${icon("play")} Continuer la lecture
      </a>
    </div>
  `;
}
