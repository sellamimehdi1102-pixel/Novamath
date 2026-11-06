import { bindThemeToggle } from "./theme.js";
import { api } from "./api.js";
import { resetGuestLocalState } from "./store.js";
import {
  fetchCurricula,
  getStoredClassLevel,
  setStoredClassLevel,
  setSessionClassLevel,
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
//
// Visiteur sans session (bouton « Commencer » de l'accueil) : session invité
// créée ici puis ouverture des chapitres de la classe choisie — même
// mécanisme que les liens ?classe= ci-dessous, au lieu d'un détour par la
// connexion. Un compte (ou invité) déjà connecté garde le comportement
// historique ; un échec réseau aussi.
async function ensureSession() {
  try {
    await api.me();
    return "existing";
  } catch {
    resetGuestLocalState();
    await api.enterGuest();
    return "guest";
  }
}

async function enterCurriculum(classLevel) {
  const next = resolveNextDestination();
  let session = null;
  try {
    session = await ensureSession();
  } catch {
    /* réseau indisponible : comportement historique ci-dessous */
  }
  setStoredClassLevel(classLevel);
  const fallback = session === "guest" ? "chapitres.html" : "dashboard.html";
  window.location.href = `/${next || fallback}`;
}

// Liens /maths-<classe> (redirigés ici par le serveur) : classe présélectionnée
// pour cet onglet, puis ouverture des questions — en mode invité si aucun
// compte n'est connecté. Une classe inconnue ou un échec réseau retombent sur
// le sélecteur habituel ci-dessous.
async function enterFromLink(curricula) {
  const requested = new URLSearchParams(window.location.search).get("classe");
  if (!requested || !curricula.some((c) => c.classLevel === requested)) return false;
  try {
    await ensureSession();
  } catch {
    return false;
  }
  setSessionClassLevel(requested);
  window.location.replace("/chapitres.html");
  return true;
}

fetchCurricula()
  .then(async (curricula) => {
    if (await enterFromLink(curricula)) return;
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
