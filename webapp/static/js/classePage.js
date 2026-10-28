// ── Pages publiques par classe (/maths-quatrieme, ...) ─────────────────────
// Contenu entièrement rendu côté serveur (voir webapp/seo_pages.py) : ce
// module ne fait qu'ajouter le thème, les modales Connexion/Inscription
// (auth.js, mêmes fenêtres que partout ailleurs) et mémoriser la classe de
// la page quand l'élève clique sur un bouton d'inscription ou « Continuer ».
import { bindThemeToggle } from "./theme.js";
import { setStoredClassLevel } from "./curriculumSelector.js";
import "./auth.js";

bindThemeToggle(document.getElementById("theme-toggle"));

// Phase de capture : la classe est enregistrée avant que auth.js n'ouvre la
// modale. Geste explicite de l'élève, comme sur choisir-classe.html — après
// inscription, il arrive donc directement dans la classe de la page.
document.addEventListener(
  "click",
  (e) => {
    const trigger = e.target.closest("[data-set-class]");
    if (trigger) setStoredClassLevel(trigger.dataset.setClass);
  },
  true,
);
