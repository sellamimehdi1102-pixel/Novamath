// ── Sidebar rétractable + drawer mobile ─────────────────────────────────────
// Comportement partagé par toutes les pages avec .app-shell : bouton de
// réduction (icônes seules + tooltips) en desktop, menu coulissant en
// mobile. Injecté en JS plutôt que dupliqué en HTML dans les 5 pages, pour
// n'avoir qu'un seul endroit à maintenir. Préférence persistée dans
// localStorage (clé dédiée, lue en synchrone au chargement — pas d'attente
// réseau, pas de flash de mise en page).
import { ICONS } from "./icons.js";
import { initClassBadge } from "./curriculumSelector.js";
import { initScrollReveal } from "./scroll-reveal.js";
import { api } from "./api.js";
import { PAGE_FEATURE_REQUIREMENTS, featureLabel, requiredPlanFor, planMeetsRequirement } from "./features.js";

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

// Badge "classe actuelle", injecté ici plutôt que dupliqué dans le HTML des 6
// pages à sidebar (même logique que le bouton de réduction ci-dessus) —
// même composant que index.html, câblé via curriculumSelector.js::initClassBadge.
function buildClassBadge() {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.id = "class-badge-btn";
  btn.className = "class-badge sidebar-class-badge";
  btn.setAttribute("aria-label", "Changer de classe");
  btn.setAttribute("data-tooltip", "Changer de classe");
  btn.innerHTML = `
    <span class="class-badge-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></svg></span>
    <span class="class-badge-label" id="class-badge-label">Seconde</span>
    <span class="class-badge-chevron" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg></span>
  `;
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

// ── Cadenas sur les liens verrouillés ────────────────────────────────────────
// Générique et piloté par PAGE_FEATURE_REQUIREMENTS (features.js, miroir de
// server.py::PAGE_FEATURE_REQUIREMENTS) : aujourd'hui vide (aucune page
// n'excède le plan Free), donc aucun lien n'est verrouillé en pratique — mais
// le mécanisme est complet et s'active automatiquement dès qu'une entrée y
// est ajoutée, sans toucher à sidebar.js. Un lien verrouillé n'est jamais
// masqué (UX façon Notion AI/Copilot/Linear) : cadenas visible, légèrement
// grisé, reste cliquable, ouvre la page Abonnement avec le bon message.
function pageFromHref(href) {
  return (href || "").split("/").pop();
}

function lockLink(link, featureValue) {
  link.classList.add("is-locked");
  const label = link.querySelector("span[data-i18n]")?.textContent?.trim() || "";
  link.setAttribute("data-tooltip", `${label} — ${featureLabel(featureValue)} requis`);

  const lockBadge = document.createElement("span");
  lockBadge.className = "sidebar-link-lock";
  lockBadge.setAttribute("aria-hidden", "true");
  lockBadge.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>';
  link.appendChild(lockBadge);

  const targetPage = pageFromHref(link.getAttribute("href"));
  link.addEventListener("click", (e) => {
    e.preventDefault();
    window.location.href = `abonnement.html?required=${featureValue}${targetPage ? `&from=${targetPage}` : ""}`;
  });
}

// Piloté par PAGE_FEATURE_REQUIREMENTS : { "page.html": "feature_value" }.
async function applyFeatureLocks(sidebar) {
  if (!Object.keys(PAGE_FEATURE_REQUIREMENTS).length) return;
  let user;
  try {
    ({ user } = await api.me());
  } catch {
    return; // Session expirée ou invité non résolu : pas de verrouillage à l'aveugle.
  }
  const plan = user?.plan || "free";

  sidebar.querySelectorAll(".sidebar-link[href]").forEach((link) => {
    const page = pageFromHref(link.getAttribute("href"));
    const featureValue = PAGE_FEATURE_REQUIREMENTS[page];
    if (!featureValue) return;
    if (planMeetsRequirement(plan, requiredPlanFor(featureValue))) return;
    lockLink(link, featureValue);
  });
}

function init() {
  const sidebar = document.querySelector(".sidebar");
  if (!sidebar) return;

  const brand = sidebar.querySelector(".brand");
  const collapseBtn = buildCollapseBtn();
  (brand || sidebar).insertAdjacentElement(brand ? "afterend" : "afterbegin", collapseBtn);

  const classBadge = buildClassBadge();
  (brand || sidebar).insertAdjacentElement(brand ? "afterend" : "afterbegin", classBadge);
  initClassBadge(classBadge);

  if (!isMobile()) {
    setCollapsed(sidebar, collapseBtn, localStorage.getItem(STORAGE_KEY) === "1");
  }
  collapseBtn.addEventListener("click", () => {
    setCollapsed(sidebar, collapseBtn, !sidebar.classList.contains("is-collapsed"));
  });

  wireTooltips(sidebar);
  applyFeatureLocks(sidebar);

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
initScrollReveal();
