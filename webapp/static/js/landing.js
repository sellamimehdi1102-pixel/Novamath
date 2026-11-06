import { bindThemeToggle } from "./theme.js";
import { initClassMenus } from "./classMenu.js";
import { initScrollReveal } from "./scroll-reveal.js";

bindThemeToggle(document.getElementById("theme-toggle"));
initClassMenus();
initScrollReveal();

// ── FAQ : accordéons fermés par défaut ─────────────────────────────────────
// Le bouton porte l'état (aria-expanded) ; la classe .open pilote l'animation
// et masque la réponse aux technologies d'assistance tant qu'elle est fermée
// (visibility, voir landing.css).
document.querySelectorAll(".faq-question").forEach((q) => {
  q.addEventListener("click", () => {
    const item = q.closest(".faq-item");
    const isOpen = item.classList.toggle("open");
    q.setAttribute("aria-expanded", String(isOpen));
  });
});
