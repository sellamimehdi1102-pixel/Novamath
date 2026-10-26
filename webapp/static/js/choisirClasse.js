import { bindThemeToggle } from "./theme.js";
import {
  fetchCurricula,
  getStoredClassLevel,
  setStoredClassLevel,
  renderCurriculumCard,
  ALLOWED_NEXT_PAGES,
} from "./curriculumSelector.js";
import { initScrollReveal } from "./scroll-reveal.js";

bindThemeToggle(document.getElementById("theme-toggle"));
initScrollReveal();

const grid = document.getElementById("cursus-grid");

// ── Phase 5 (onboarding) — ?next= optionnel, posé par
// auth.js::redirectAfterSignup quand cette page sert de détour après
// inscription. Même liste blanche que auth.js (ALLOWED_NEXT_PAGES,
// curriculumSelector.js) : une valeur absente/inconnue retombe sur le
// comportement historique de cette page (retour à index.html), jamais une
// redirection externe. ───────────────────────────────────────────────────
function resolveNextDestination() {
  const next = new URLSearchParams(window.location.search).get("next");
  return next && ALLOWED_NEXT_PAGES.includes(next) ? next : null;
}

// Sans ?next= (page ouverte directement, ou depuis un lien), « Entrer dans
// ce cursus » ouvre le tableau de bord de la classe choisie (2026-10-24 —
// auparavant retour à l'accueil, où la classe choisie n'était visible nulle
// part). Un visiteur non connecté y est redirigé vers la connexion par le
// serveur (server.py::_serve_protected, `/?next=dashboard.html`), puis
// ramené sur ce tableau de bord.
function enterCurriculum(classLevel) {
  setStoredClassLevel(classLevel);
  const next = resolveNextDestination();
  window.location.href = `/${next || "dashboard.html"}`;
}

fetchCurricula()
  .then((curricula) => {
    const current = getStoredClassLevel();
    grid.innerHTML = "";
    grid.setAttribute("aria-busy", "false");
    curricula.forEach((curriculum) => {
      grid.appendChild(
        renderCurriculumCard(curriculum, {
          isCurrent: curriculum.classLevel === current,
          onEnter: enterCurriculum,
        }),
      );
    });
  })
  .catch(() => {
    grid.innerHTML =
      '<p class="cursus-select-error">Impossible de charger les classes disponibles pour le moment. Réessaie dans un instant.</p>';
    grid.setAttribute("aria-busy", "false");
  });
