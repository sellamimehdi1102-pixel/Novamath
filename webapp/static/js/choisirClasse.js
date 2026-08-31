import { bindThemeToggle } from "./theme.js";
import {
  fetchCurricula, getStoredClassLevel, setStoredClassLevel, renderCurriculumCard, ALLOWED_NEXT_PAGES,
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

function enterCurriculum(classLevel) {
  setStoredClassLevel(classLevel);
  const next = resolveNextDestination();
  window.location.href = next ? `/${next}` : "index.html";
}

fetchCurricula()
  .then((curricula) => {
    const current = getStoredClassLevel();
    grid.innerHTML = "";
    grid.setAttribute("aria-busy", "false");
    curricula.forEach((curriculum) => {
      grid.appendChild(renderCurriculumCard(curriculum, {
        isCurrent: curriculum.classLevel === current,
        onEnter: enterCurriculum,
      }));
    });
  })
  .catch(() => {
    grid.innerHTML = '<p class="cursus-select-error">Impossible de charger les classes disponibles pour le moment. Réessaie dans un instant.</p>';
    grid.setAttribute("aria-busy", "false");
  });
