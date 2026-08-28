import { bindThemeToggle } from "./theme.js";
import { api } from "./api.js";
import { getStoredClassLevel, initClassBadge, fetchCurricula } from "./curriculumSelector.js";
import { initScrollReveal } from "./scroll-reveal.js";

bindThemeToggle(document.getElementById("theme-toggle"));
initClassBadge(document.getElementById("class-badge-btn"));
initScrollReveal();

document.querySelectorAll(".faq-question").forEach((q) => {
  q.addEventListener("click", () => {
    q.closest(".faq-item").classList.toggle("open");
  });
});

// ── Statistiques (bandeau + FAQ) : source unique /api/site/stats ───────────
// Aucune valeur codée en dur : tout est recalculé depuis les banques
// d'exercices côté serveur (voir webapp/server.py::api_site_stats), pour la
// classe actuellement choisie (voir curriculumSelector.js) — "seconde" par
// défaut tant qu'aucun choix n'a été fait, comportement strictement
// identique à avant l'introduction du sélecteur de classe.
function animateCount(el, target, duration = 1200) {
  const start = performance.now();
  function frame(now) {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
    el.textContent = Math.round(target * eased).toLocaleString("fr-FR");
    if (progress < 1) requestAnimationFrame(frame);
    else el.textContent = target.toLocaleString("fr-FR");
  }
  requestAnimationFrame(frame);
}

function roundedMarketingLabel(value) {
  const floor50 = Math.floor(value / 50) * 50;
  return floor50 >= 50 ? `Plus de ${floor50.toLocaleString("fr-FR")}` : `${value}`;
}

const activeClassLevel = getStoredClassLevel();

fetchCurricula().then((curricula) => {
  const current = curricula.find((c) => c.classLevel === activeClassLevel);
  if (!current) return;
  document.querySelectorAll("#stats-class-label, #faq-class-label").forEach((el) => {
    el.textContent = current.label;
  });
}).catch(() => {});

api.getSiteStats(activeClassLevel).then((stats) => {
  const faqEl = document.getElementById("faq-chapter-count");
  if (faqEl && stats.chapters) faqEl.textContent = stats.chapters;

  document.querySelectorAll(".stat-item[data-stat]").forEach((item) => {
    const key = item.dataset.stat;
    const value = stats[key];
    if (typeof value !== "number") return;

    const valueEl = item.querySelector(".stat-value");
    const labelEl = item.querySelector(".stat-label");

    if (item.dataset.format === "exercises") {
      labelEl.textContent = "exercices";
      valueEl.dataset.prefix = "Plus de ";
    }

    animateCount(valueEl, value);
    if (item.dataset.format === "exercises") {
      // Ré-habille le compteur en formulation marketing une fois l'animation
      // terminée (évite un texte qui "saute" pendant le comptage).
      setTimeout(() => { valueEl.textContent = roundedMarketingLabel(value); }, 1250);
    }
  });
}).catch(() => {});
