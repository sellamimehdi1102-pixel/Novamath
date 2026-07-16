// ── Composant Popup générique — réutilisé par tous les popups du site ──────
// Un seul mécanisme d'ouverture/fermeture (ESC, clic extérieur, animation,
// scroll interne, blocage du scroll de la page derrière) pour que chaque
// popup (Paramètres, confirmation, connexion, avatar, avis...) partage
// exactement les mêmes couleurs/marges/ombres/transitions — voir .popup-*
// dans css/base.css, qui généralise .modal-overlay/.modal-card existants.
import { icon } from "./icons.js";

let openCount = 0; // plusieurs popups peuvent théoriquement s'empiler (ex: confirmation par-dessus Paramètres)

function lockBodyScroll() {
  openCount += 1;
  document.body.style.overflow = "hidden";
}

function unlockBodyScroll() {
  openCount = Math.max(0, openCount - 1);
  if (openCount === 0) document.body.style.overflow = "";
}

/**
 * @param {Object} opts
 * @param {string} [opts.id] - id du conteneur overlay ; si un élément avec cet id existe déjà
 *   dans le DOM, il est réutilisé tel quel (permet la migration progressive de popups ad hoc).
 * @param {string} [opts.title] - titre affiché dans l'en-tête (ignoré si bodyEl fourni avec son propre en-tête).
 * @param {string} [opts.bodyHtml] - contenu HTML du corps du popup.
 * @param {HTMLElement} [opts.bodyEl] - contenu DOM déjà construit (prioritaire sur bodyHtml).
 * @param {"sm"|"md"|"lg"|"xl"} [opts.size="md"]
 * @param {boolean} [opts.closeOnEscape=true]
 * @param {boolean} [opts.closeOnOverlayClick=true]
 * @param {boolean} [opts.showCloseButton=true]
 * @param {(el: HTMLElement) => void} [opts.onOpen]
 * @param {() => void} [opts.onClose]
 * @returns {{ close: () => void, el: HTMLElement, bodyEl: HTMLElement }}
 */
export function openPopup({
  id,
  title,
  bodyHtml = "",
  bodyEl = null,
  size = "md",
  closeOnEscape = true,
  closeOnOverlayClick = true,
  showCloseButton = true,
  onOpen,
  onClose,
} = {}) {
  let overlay = id ? document.getElementById(id) : null;
  const reused = !!overlay;

  if (!overlay) {
    overlay = document.createElement("div");
    if (id) overlay.id = id;
  }
  overlay.className = "popup-overlay";
  overlay.hidden = false;

  const card = document.createElement("div");
  card.className = `popup-card popup-card--${size} card card--glass`;
  card.setAttribute("role", "dialog");
  card.setAttribute("aria-modal", "true");

  if (title || showCloseButton) {
    const header = document.createElement("div");
    header.className = "popup-header";
    header.innerHTML = `<h2 class="popup-title">${title || ""}</h2>`;
    if (showCloseButton) {
      const closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "popup-close";
      closeBtn.setAttribute("aria-label", "Fermer");
      closeBtn.innerHTML = icon("x");
      closeBtn.addEventListener("click", () => close());
      header.appendChild(closeBtn);
    }
    card.appendChild(header);
  }

  const body = document.createElement("div");
  body.className = "popup-body";
  if (bodyEl) body.appendChild(bodyEl);
  else body.innerHTML = bodyHtml;
  card.appendChild(body);

  overlay.innerHTML = "";
  overlay.appendChild(card);
  if (!reused) document.body.appendChild(overlay);

  lockBodyScroll();
  requestAnimationFrame(() => overlay.classList.add("is-open"));

  let closed = false;
  function close() {
    if (closed) return;
    closed = true;
    overlay.classList.remove("is-open");
    document.removeEventListener("keydown", onKeydown);
    unlockBodyScroll();
    const finish = () => {
      overlay.hidden = true;
      overlay.innerHTML = "";
      if (onClose) onClose();
    };
    // Laisse l'animation de fermeture (CSS) se jouer avant de vider le DOM —
    // durée alignée sur --transition-base (voir base.css), no-op si
    // data-animations="off" (transitionend se déclenche alors immédiatement).
    let done = false;
    const onEnd = () => { if (done) return; done = true; finish(); };
    overlay.addEventListener("transitionend", onEnd, { once: true });
    setTimeout(onEnd, 300);
  }

  function onKeydown(e) {
    if (e.key === "Escape" && closeOnEscape) close();
  }
  document.addEventListener("keydown", onKeydown);

  if (closeOnOverlayClick) {
    overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  }

  if (onOpen) onOpen(card);

  return { close, el: overlay, bodyEl: body };
}
