// ── SettingsManager — source de vérité unique des préférences Mathadap ─────
// Façade au-dessus de api.getSettings/saveSettings (backend) et du cache
// localStorage novamath:settings (déjà géré historiquement par theme.js pour
// la seule sous-clé "appearance" — ce module généralise à toutes les
// catégories : appearance, training, learning, language). Toute page qui
// veut lire ou changer une préférence passe par ici, plus jamais par un accès
// direct à localStorage/api.getSettings — c'est ce qui centralise ce qui
// était dupliqué dans chaque js de page (voir plan de refonte Paramètres).
import { api } from "./api.js";
import { initTheme, applyAppearance, getCachedAppearance, bindThemeToggle } from "./theme.js";
import { NOVAMATH_VERSION } from "./version.js";

const CACHE_KEY = "novamath:settings";

let current = null; // settings complets en mémoire, une fois chargés (source de lecture synchrone)
let saveTimer = null;
let saveChain = Promise.resolve();

function readCache() {
  try {
    return JSON.parse(localStorage.getItem(CACHE_KEY)) || {};
  } catch {
    return {};
  }
}

function writeCache(settings) {
  localStorage.setItem(CACHE_KEY, JSON.stringify(settings));
}

function dispatchChange(category, patch) {
  window.dispatchEvent(new CustomEvent("novamath:settings-changed", {
    detail: { category, patch, settings: current },
  }));
}

function applyCategorySideEffects(category) {
  if (category === "appearance") applyAppearance(current.appearance);
}

/** Charge les préférences (serveur si possible, sinon cache local hors-ligne),
 * applique tout de suite l'apparence pour éviter tout flash, et câble le
 * bouton de thème présent sur la page (une seule fois, centralisé ici). */
export async function initSettingsManager(themeToggleEl) {
  initTheme();
  const cached = readCache();
  current = { appearance: getCachedAppearance(), ...cached };
  applyAppearance(current.appearance);

  if (themeToggleEl) bindThemeToggle(themeToggleEl);
  else bindThemeToggle(document.getElementById("theme-toggle"));

  const versionEl = document.getElementById("sidebar-version");
  if (versionEl) versionEl.textContent = `Mathadap v${NOVAMATH_VERSION}`;

  try {
    const server = await api.getSettings();
    current = server;
    writeCache(current);
    applyAppearance(current.appearance);
    dispatchChange("*", current);
  } catch {
    // Hors-ligne / non authentifié : on reste sur le cache local déjà appliqué.
  }
  return current;
}

/** Lecture synchrone depuis l'état mémoire — jamais de parsing localStorage
 * dispersé dans les pages. */
export function getSettings() {
  return current || { appearance: getCachedAppearance() };
}

export function onSettingsChange(callback) {
  const handler = (e) => callback(e);
  window.addEventListener("novamath:settings-changed", handler);
  return () => window.removeEventListener("novamath:settings-changed", handler);
}

/** Mise à jour optimiste : appliquée immédiatement (mémoire+cache+DOM+event),
 * persistée côté serveur en arrière-plan avec un léger debounce (regroupe les
 * changements rapides, ex. slider), rollback silencieux si l'écriture échoue
 * (le prochain init()/refresh() resynchronisera avec le serveur). */
export function setSetting(category, key, value) {
  if (!current) current = { appearance: getCachedAppearance() };
  const previous = current[category];
  if (key === null) {
    current = { ...current, [category]: value };
  } else {
    current = { ...current, [category]: { ...current[category], [key]: value } };
  }
  writeCache(current);
  applyCategorySideEffects(category);
  dispatchChange(category, current[category]);

  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    saveChain = saveChain.then(() => api.saveSettings(current)).then((saved) => {
      current = saved;
      writeCache(current);
    }).catch(() => {
      // Rollback en mémoire uniquement — l'UI a déjà pu changer d'onglet entre
      // temps ; on ne réapplique pas de force pour éviter un flash intempestif.
      if (previous !== undefined) current = { ...current, [category]: previous };
    });
  }, 250);

  return current;
}

/** Force une resynchronisation depuis le serveur (ex. après connexion). */
export async function refreshSettings() {
  const server = await api.getSettings();
  current = server;
  writeCache(current);
  applyAppearance(current.appearance);
  dispatchChange("*", current);
  return current;
}
