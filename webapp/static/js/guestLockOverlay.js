// ── Verrou invité — composant unique réutilisable ───────────────────────────
// Seule source de vérité (HTML + positionnement) pour TOUTE zone de contenu
// verrouillée pour un compte invité : le conteneur cible reste entièrement
// rendu derrière un léger flou, jamais assombri par un voile (voir
// guest.css::.guest-lock-target — repris tel quel du Dashboard), une popup
// flottante vient se poser au-dessus (voir guest.css::.guest-lock-overlay —
// reprise du Chatbot). Utilisé par dashboard.js (verrou dismissible : la
// popup peut être fermée SANS lever le flou, voir dismissGuestLockOverlay) et
// chatbot.js (verrou bloquant, jamais dismissible). Toute future page
// verrouillée doit réutiliser ce composant plutôt que recréer son propre
// overlay.
import { ICONS } from "./icons.js";

const instances = new Map(); // overlay id -> { sync }

// La popup est en `position: fixed` (toujours centrée dans le viewport
// visible, même si le conteneur est plus haut que l'écran — cas du
// Dashboard) mais bornée horizontalement au conteneur cible (jamais la
// sidebar/nav) : ces bornes ne peuvent être connues qu'après mise en page
// réelle, d'où cette resynchronisation JS plutôt qu'un simple CSS statique.
// rect.width vaut 0 tant qu'aucune mise en page réelle n'a eu lieu (jsdom en
// test) : on garde alors le repli CSS (largeur 100%) plutôt que d'écraser
// avec des valeurs nulles.
function syncOverlayBounds(container, overlay) {
  const rect = container.getBoundingClientRect();
  if (!rect.width) return;
  overlay.style.left = `${Math.round(rect.left)}px`;
  overlay.style.width = `${Math.round(rect.width)}px`;
}

/**
 * Monte (ou réutilise) l'overlay de verrou invité sur `container`, dont le
 * contenu passe en `.guest-lock-target` (flouté + inerte). `container` doit
 * envelopper tout le contenu à flouter — jamais la sidebar/nav.
 */
export function mountGuestLockOverlay(container, { id, icon: iconName = "lock", title, description, listItems = null, actionsHtml }) {
  container.classList.add("guest-lock-target");

  let overlay = document.getElementById(id);
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = id;
    overlay.className = "guest-lock-overlay";
    overlay.innerHTML = `
      <div class="guest-lock-card card">
        <div class="icon-wrap">${ICONS[iconName] || ""}</div>
        <h3>${title}</h3>
        <p>${description}</p>
        ${listItems ? `<ul class="guest-lock-card-list">${listItems.map((li) => `<li>${li}</li>`).join("")}</ul>` : ""}
        <div class="guest-lock-card-actions">${actionsHtml}</div>
      </div>`;
    container.appendChild(overlay);
  }

  const sync = () => syncOverlayBounds(container, overlay);
  sync();
  window.addEventListener("resize", sync);
  instances.set(id, { sync });

  return overlay;
}

/**
 * Referme la popup UNIQUEMENT (ex. "Continuer en mode invité" du Dashboard) :
 * le conteneur reste `.guest-lock-target` (flouté + inerte) pour le reste de
 * la session — jamais utilisé par le Chatbot, dont le verrou n'a pas de sortie.
 */
export function dismissGuestLockOverlay(id) {
  const overlay = document.getElementById(id);
  if (!overlay) return;
  const inst = instances.get(id);
  if (inst) {
    window.removeEventListener("resize", inst.sync);
    instances.delete(id);
  }
  overlay.remove();
}

/** Referme la popup ET lève le flou sur `container` (déverrouillage complet). */
export function unmountGuestLockOverlay(container, id) {
  dismissGuestLockOverlay(id);
  container.classList.remove("guest-lock-target");
}
