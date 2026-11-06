// ── Menus déroulants « Classes » de la page d'accueil ──────────────────────
// Un même composant pour le menu de navigation, le bouton « Commencer » du
// Hero et le bouton « Choisir ma classe » : bouton de divulgation
// (aria-expanded/aria-controls) + liste de liens. Les liens pointent vers
// /choisir-classe.html?classe=<id> (cible des anciennes URL /maths-<classe>) :
// la classe est présélectionnée puis les questions s'ouvrent, en mode invité
// si aucun compte n'est connecté (voir choisirClasse.js::enterFromLink).
// Fonctionne à la souris, au toucher et au clavier (Entrée/Espace, flèches,
// Début/Fin, Échap, Tab). Un seul menu ouvert à la fois.

const OPEN_CLASS = "is-open";
const menus = [];

function links(menu) {
  return [...menu.list.querySelectorAll("a")];
}

function close(menu, { focusToggle = false } = {}) {
  if (menu.list.hidden) return;
  menu.list.hidden = true;
  menu.toggle.setAttribute("aria-expanded", "false");
  menu.root.classList.remove(OPEN_CLASS);
  if (focusToggle) menu.toggle.focus();
}

function open(menu, { focus = null } = {}) {
  menus.forEach((other) => other !== menu && close(other));
  menu.list.hidden = false;
  menu.toggle.setAttribute("aria-expanded", "true");
  menu.root.classList.add(OPEN_CLASS);
  const items = links(menu);
  if (focus === "first") items[0]?.focus();
  if (focus === "last") items[items.length - 1]?.focus();
}

function moveFocus(menu, delta) {
  const items = links(menu);
  const index = items.indexOf(document.activeElement);
  const next = index === -1 ? 0 : (index + delta + items.length) % items.length;
  items[next]?.focus();
}

function bind(root) {
  const toggle = root.querySelector(".class-menu-toggle");
  const list = root.querySelector(".class-menu-list");
  if (!toggle || !list) return;
  const menu = { root, toggle, list };
  menus.push(menu);

  toggle.addEventListener("click", () => {
    if (list.hidden) open(menu);
    else close(menu);
  });

  // stopPropagation : sans lui, la même touche remonterait jusqu'au gestionnaire
  // du menu ci-dessous et déplacerait aussitôt le focus d'un cran de plus.
  toggle.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      e.stopPropagation();
      open(menu, { focus: e.key === "ArrowDown" ? "first" : "last" });
    }
  });

  root.addEventListener("keydown", (e) => {
    if (list.hidden) return;
    if (e.key === "Escape") {
      e.preventDefault();
      close(menu, { focusToggle: true });
    } else if (list.contains(document.activeElement)) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        moveFocus(menu, 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        moveFocus(menu, -1);
      } else if (e.key === "Home") {
        e.preventDefault();
        links(menu)[0]?.focus();
      } else if (e.key === "End") {
        e.preventDefault();
        const items = links(menu);
        items[items.length - 1]?.focus();
      }
    }
  });

  // Tab hors du menu : il se referme (le focus ne reste jamais dans une liste masquée).
  root.addEventListener("focusout", (e) => {
    if (e.relatedTarget && !root.contains(e.relatedTarget)) close(menu);
  });
}

/** Câble tous les menus `[data-class-menu]` présents dans `scope`. */
export function initClassMenus(scope = document) {
  scope.querySelectorAll("[data-class-menu]").forEach(bind);
  if (!menus.length) return;
  // Clic/toucher en dehors : fermeture (pointerdown couvre souris et toucher).
  document.addEventListener("pointerdown", (e) => {
    menus.forEach((menu) => {
      if (!menu.root.contains(e.target)) close(menu);
    });
  });
}
