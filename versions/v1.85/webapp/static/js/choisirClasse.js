import { bindThemeToggle } from "./theme.js";
import {
  fetchCurricula, getStoredClassLevel, setStoredClassLevel, renderCurriculumCard,
} from "./curriculumSelector.js";
import { initScrollReveal } from "./scroll-reveal.js";

bindThemeToggle(document.getElementById("theme-toggle"));
initScrollReveal();

const grid = document.getElementById("cursus-grid");

function enterCurriculum(classLevel) {
  setStoredClassLevel(classLevel);
  window.location.href = "index.html";
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
