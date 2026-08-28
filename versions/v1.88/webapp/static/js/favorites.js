// ── Favoris (chapitres + notions) — Cours ET Exercices ──────────────────────
// Persistés comme n'importe quelle autre préférence (SettingsManager →
// /api/settings), sans nouveau point d'API. "favorites" (chapitres) est
// partagé entre Cours et Exercices : un chapitre enregistré l'est partout,
// même convention historique que chapitres.js. "favoriteNotions" est propre
// aux notions de la page Cours (voir auth.py::DEFAULT_SETTINGS).
// Même namespacing par classe que le reste du projet (ex. évaluation) : sans
// préfixe, un favori Seconde apparaîtrait aussi en Première. Les entrées
// historiques (sans préfixe) restent des favoris Seconde par convention.
import { getSettings, setSetting } from "./settingsManager.js";

function _key(id, classLevel) {
  return classLevel === "seconde" ? id : `${classLevel}:${id}`;
}

function _getSet(settingsKey, classLevel) {
  const raw = getSettings()[settingsKey] || [];
  const ids = raw
    .filter((f) => {
      const sepIdx = f.indexOf(":");
      return sepIdx === -1 ? classLevel === "seconde" : f.slice(0, sepIdx) === classLevel;
    })
    .map((f) => {
      const sepIdx = f.indexOf(":");
      return sepIdx === -1 ? f : f.slice(sepIdx + 1);
    });
  return new Set(ids);
}

function _toggle(settingsKey, id, classLevel) {
  const raw = getSettings()[settingsKey] || [];
  const key = _key(id, classLevel);
  const isFav = raw.includes(key);
  const next = isFav ? raw.filter((f) => f !== key) : [...raw, key];
  setSetting(settingsKey, null, next);
  return !isFav;
}

export function getFavoriteChapters(classLevel) {
  return _getSet("favorites", classLevel);
}
export function toggleFavoriteChapter(chapterId, classLevel) {
  return _toggle("favorites", chapterId, classLevel);
}

/** Clés au format "chapterId|notionId" — une notion favorite est indépendante
 * du favori de son chapitre (on peut aimer une notion sans enregistrer tout
 * le chapitre). */
export function getFavoriteNotions(classLevel) {
  return _getSet("favoriteNotions", classLevel);
}
export function toggleFavoriteNotion(chapterId, notionId, classLevel) {
  return _toggle("favoriteNotions", `${chapterId}|${notionId}`, classLevel);
}

export function favoriteIconSvg() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12 2.5 3 6.6 7 .8-5.2 4.8 1.4 7-6.2-3.6-6.2 3.6 1.4-7L2 9.9l7-.8 3-6.6Z" stroke-linejoin="round"/></svg>`;
}
