// ── Sidebar rétractable + drawer mobile ─────────────────────────────────────
// Comportement partagé par toutes les pages avec .app-shell : bouton de
// réduction (icônes seules + tooltips) en desktop, menu coulissant en
// mobile. Injecté en JS plutôt que dupliqué en HTML dans les 5 pages, pour
// n'avoir qu'un seul endroit à maintenir. Préférence persistée dans
// localStorage (clé dédiée, lue en synchrone au chargement — pas d'attente
// réseau, pas de flash de mise en page).
import { ICONS } from "./icons.js";

const STORAGE_KEY = "novamath:sidebarCollapsed";
const MOBILE_BREAKPOINT = 860;

function isMobile() {
  return window.innerWidth <= MOBILE_BREAKPOINT;
}

function setCollapsed(sidebar, btn, collapsed) {
  sidebar.classList.toggle("is-collapsed", collapsed);
  btn.setAttribute("aria-expanded", String(!collapsed));
  btn.setAttribute("aria-label", collapsed ? "Développer la barre latérale" : "Réduire la barre latérale");
  localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
}

function buildCollapseBtn() {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "sidebar-collapse-btn";
  btn.className = "sidebar-collapse-btn";
  btn.setAttribute("aria-label", "Réduire la barre latérale");
  btn.innerHTML = ICONS.chevronsLeft;
  return btn;
}

function buildMobileTrigger() {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "sidebar-mobile-trigger";
  btn.className = "sidebar-mobile-trigger";
  btn.setAttribute("aria-label", "Ouvrir le menu");
  btn.innerHTML = ICONS.menu;
  return btn;
}

function buildOverlay() {
  const overlay = document.createElement("div");
  overlay.className = "sidebar-overlay";
  return overlay;
}

function openDrawer(sidebar) {
  sidebar.classList.add("is-open");
  document.body.classList.add("sidebar-drawer-open");
}

function closeDrawer(sidebar) {
  sidebar.classList.remove("is-open");
  document.body.classList.remove("sidebar-drawer-open");
}

// data-tooltip plutôt qu'un <span> texte séparé : reste correct même si le
// nom du compte se met à jour après coup (événement novamath:account-updated
// géré par identity.js), et sert de vrai composant tooltip (::after en CSS)
// au lieu du title="" natif du navigateur.
function wireTooltips(sidebar) {
  sidebar.querySelectorAll(".sidebar-link").forEach((a) => {
    const label = a.querySelector("span[data-i18n]")?.textContent?.trim();
    if (label) a.setAttribute("data-tooltip", label);
  });

  const userLink = sidebar.querySelector("#sidebar-user");
  const syncUserTooltip = () => {
    const name = document.getElementById("sidebar-user-name")?.textContent?.trim();
    if (userLink && name) userLink.setAttribute("data-tooltip", name);
  };
  syncUserTooltip();
  window.addEventListener("novamath:account-updated", syncUserTooltip);
}

function init() {
  const sidebar = document.querySelector(".sidebar");
  if (!sidebar) return;

  const brand = sidebar.querySelector(".brand");
  const collapseBtn = buildCollapseBtn();
  (brand || sidebar).insertAdjacentElement(brand ? "afterend" : "afterbegin", collapseBtn);

  if (!isMobile()) {
    setCollapsed(sidebar, collapseBtn, localStorage.getItem(STORAGE_KEY) === "1");
  }
  collapseBtn.addEventListener("click", () => {
    setCollapsed(sidebar, collapseBtn, !sidebar.classList.contains("is-collapsed"));
  });

  wireTooltips(sidebar);

  const mobileTrigger = buildMobileTrigger();
  const overlay = buildOverlay();
  document.body.append(mobileTrigger, overlay);
  mobileTrigger.addEventListener("click", () => openDrawer(sidebar));
  overlay.addEventListener("click", () => closeDrawer(sidebar));
  sidebar.querySelectorAll(".sidebar-link").forEach((a) => {
    a.addEventListener("click", () => closeDrawer(sidebar));
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDrawer(sidebar);
  });
  window.addEventListener("resize", () => {
    if (!isMobile()) closeDrawer(sidebar);
  });
}

init();
