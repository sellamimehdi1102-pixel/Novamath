// ── Thème clair/sombre — CLAIR par défaut (V4), persisté en localStorage ───
// V2/V3 étaient dark-first ; ce chantier inverse la référence (palette issue
// de l'image de vagues violet/lavande, pensée pour un fond clair) — le sombre
// devient l'option explicite ([data-theme="dark"] sur <html>, jamais posé
// tant que l'utilisateur n'a pas basculé ou n'a pas ce choix en cache).
const THEME_KEY = "lumis:theme";

export function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark") {
    document.documentElement.setAttribute("data-theme", saved);
  }
}

export function currentTheme() {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

export function setTheme(next) {
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem(THEME_KEY, next);
  _patchAppearanceCache({ theme: next });
  return next;
}

export function toggleTheme() {
  return setTheme(currentTheme() === "dark" ? "light" : "dark");
}

export function bindThemeToggle(buttonEl) {
  if (!buttonEl) return;
  buttonEl.addEventListener("click", () => toggleTheme());
}

// ── Apparence (Paramètres → Apparence) ──────────────────────────────────────
// Appliquée immédiatement au chargement de CHAQUE page (ce module est déjà
// importé partout via bindThemeToggle), pour éviter tout flash de contenu non
// stylé. Source rapide : cache localStorage (lecture synchrone, aucune
// requête réseau) — la synchronisation avec le serveur (multi-appareils) est
// gérée par webapp/static/js/settings.js, qui réécrit ce même cache.
export const APPEARANCE_KEY = "novamath:settings";

const APPEARANCE_DEFAULTS = {
  theme: "light",
  accent: "purple",
  fontSize: "normal",
  radius: "normal",
  animations: true,
  transparency: true,
};

function _readAppearanceCache() {
  try {
    const raw = JSON.parse(localStorage.getItem(APPEARANCE_KEY));
    return { ...APPEARANCE_DEFAULTS, ...(raw?.appearance || {}) };
  } catch {
    return { ...APPEARANCE_DEFAULTS };
  }
}

/** Fusionne un patch partiel dans le cache local d'apparence sans écraser les
 * autres catégories de préférences (training/learning/...) déjà en cache. */
function _patchAppearanceCache(patch) {
  let full;
  try {
    full = JSON.parse(localStorage.getItem(APPEARANCE_KEY)) || {};
  } catch {
    full = {};
  }
  full.appearance = { ..._readAppearanceCache(), ...patch };
  localStorage.setItem(APPEARANCE_KEY, JSON.stringify(full));
  return full.appearance;
}

const ACCENT_VALUES = new Set(["purple", "blue", "green", "red", "orange"]);
const FONT_SIZE_VALUES = new Set(["small", "normal", "large"]);
const RADIUS_VALUES = new Set(["normal", "rounded"]);

/** Couleur d'accent active, lue en direct depuis les variables CSS calculées —
 * jamais mise en cache statique, pour que tout rendu canvas/SVG dynamique
 * (graphes, confettis, avatar) reflète immédiatement un changement de couleur
 * sans recharger la page (voir animations.js, dashboard.js, profil.js). */
export function getAccentColor() {
  return getComputedStyle(document.documentElement).getPropertyValue("--brand-indigo").trim() || "#5b57d6";
}
export function getAccentColorSecondary() {
  return getComputedStyle(document.documentElement).getPropertyValue("--brand-violet").trim() || "#8f63e0";
}
/** ex: accentRgba(0.28) -> "rgba(117, 67, 223, 0.28)", pour les canvas/SVG où
 * une variable CSS ne peut pas être injectée directement dans un attribut fill. */
export function accentRgba(alpha = 1) {
  const rgb = getComputedStyle(document.documentElement).getPropertyValue("--accent-rgb").trim() || "117, 67, 223";
  return `rgba(${rgb}, ${alpha})`;
}

/** <meta name="theme-color"> ne peut pas lire une variable CSS nativement —
 * on la resynchronise en JS à chaque changement d'accent (barre d'adresse
 * mobile, PWA). */
function syncThemeColorMeta() {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", getAccentColor());
}

export function applyAppearance(appearance) {
  const a = { ...APPEARANCE_DEFAULTS, ...(appearance || {}) };
  const root = document.documentElement;

  if (a.theme === "light" || a.theme === "dark") root.setAttribute("data-theme", a.theme);
  root.setAttribute("data-accent", ACCENT_VALUES.has(a.accent) ? a.accent : "purple");
  root.setAttribute("data-font-size", FONT_SIZE_VALUES.has(a.fontSize) ? a.fontSize : "normal");
  root.setAttribute("data-radius", RADIUS_VALUES.has(a.radius) ? a.radius : "normal");
  root.setAttribute("data-animations", a.animations === false ? "off" : "on");
  root.setAttribute("data-glass", a.transparency === false ? "off" : "on");
  syncThemeColorMeta();
}

export function initAppearance() {
  // initTheme() a déjà tourné juste avant (voir bas de fichier) et fait
  // autorité pour le thème (clé historique THEME_KEY) : on ne laisse jamais
  // le cache d'apparence (par défaut "light" si l'utilisateur n'a encore
  // jamais ouvert Paramètres) écraser un choix clair/sombre déjà appliqué.
  const a = _readAppearanceCache();
  a.theme = currentTheme();
  applyAppearance(a);
}

export function getCachedAppearance() {
  return _readAppearanceCache();
}

/** Appelé par settings.js après une sauvegarde réussie côté serveur : applique
 * immédiatement (aucun rechargement de page) et met à jour le cache local. */
export function setAppearance(partial) {
  const merged = _patchAppearanceCache(partial);
  applyAppearance(merged);
  return merged;
}

initTheme();
initAppearance();
