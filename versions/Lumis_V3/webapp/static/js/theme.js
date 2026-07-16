// ── Thème clair/sombre — dark par défaut, persisté en localStorage ─────────
const THEME_KEY = "lumis:theme";

export function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "light" || saved === "dark") {
    document.documentElement.setAttribute("data-theme", saved);
  }
}

export function currentTheme() {
  return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
}

export function toggleTheme() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem(THEME_KEY, next);
  return next;
}

export function bindThemeToggle(buttonEl) {
  if (!buttonEl) return;
  buttonEl.addEventListener("click", () => toggleTheme());
}

initTheme();
