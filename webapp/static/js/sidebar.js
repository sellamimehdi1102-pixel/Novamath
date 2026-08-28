// ── Rail de navigation + drawer mobile ──────────────────────────────────────
// Comportement partagé par toutes les pages avec .app-shell : bande fixe
// icônes + légende (V3 "Carnet" — un seul état, plus de bascule réduit/
// déplié) en desktop, menu coulissant plein en mobile. Injecté en JS plutôt
// que dupliqué en HTML dans les 7 pages, pour n'avoir qu'un seul endroit à
// maintenir.
import { ICONS } from "./icons.js";
import { initClassBadge } from "./curriculumSelector.js";
import { initScrollReveal } from "./scroll-reveal.js";
import { api } from "./api.js";
import { PAGE_FEATURE_REQUIREMENTS, featureLabel, hasFeature } from "./features.js";
import { initOwnerTestPanel } from "./owner-test-panel.js";

const MOBILE_BREAKPOINT = 860;

function isMobile() {
  return window.innerWidth <= MOBILE_BREAKPOINT;
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

// Badge "classe actuelle", injecté ici plutôt que dupliqué dans le HTML des 7
// pages à sidebar — même composant que index.html, câblé via
// curriculumSelector.js::initClassBadge.
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

// Entrée "Administration" du menu utilisateur (sidebar-bottom) — masquée par
// défaut, révélée uniquement si /api/auth/me::can_access_admin est vrai (voir
// applyAdminMenuEntry ci-dessous). Jamais de comparaison de rôle ici : le
// backend (auth.py::_public_user) est la seule source de vérité, et chaque
// route /admin reste de toute façon protégée par @requires_role côté serveur.
function buildAdminLink() {
  const link = document.createElement("a");
  link.href = "/admin";
  link.id = "sidebar-admin-link";
  link.className = "sidebar-settings-btn";
  link.setAttribute("aria-label", "Administration");
  link.setAttribute("data-tooltip", "Administration");
  link.hidden = true;
  link.innerHTML = `${ICONS.shield}<span>Administrateur</span>`;
  return link;
}

async function applyAdminMenuEntry(sidebar) {
  const adminLink = sidebar.querySelector("#sidebar-admin-link");
  if (!adminLink) return;
  let user;
  try {
    ({ user } = await api.me());
  } catch {
    return; // Session expirée ou invité non résolu : reste masqué par défaut.
  }
  adminLink.hidden = !user?.can_access_admin;
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
  sidebar.querySelectorAll(".sidebar-link[href]").forEach((link) => {
    const page = pageFromHref(link.getAttribute("href"));
    const featureValue = PAGE_FEATURE_REQUIREMENTS[page];
    if (!featureValue) return;
    if (hasFeature(user, featureValue)) return;
    lockLink(link, featureValue);
  });
}

function init() {
  const sidebar = document.querySelector(".sidebar");
  if (!sidebar) return;

  const brand = sidebar.querySelector(".brand");
  const classBadge = buildClassBadge();
  (brand || sidebar).insertAdjacentElement(brand ? "afterend" : "afterbegin", classBadge);
  initClassBadge(classBadge);

  const settingsBtn = sidebar.querySelector("#settings-btn");
  const sidebarBottom = settingsBtn?.closest(".sidebar-bottom");
  if (sidebarBottom && settingsBtn) {
    const adminLink = buildAdminLink();
    sidebarBottom.insertBefore(adminLink, settingsBtn);
    applyAdminMenuEntry(sidebar);
  }

  wireTooltips(sidebar);
  applyFeatureLocks(sidebar);
  initOwnerTestPanel();

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
