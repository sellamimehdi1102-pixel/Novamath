// Shell SaaS de l'espace Administration — sidebar fixe + header + navigation
// interne (pushState, jamais de rechargement complet de page pour naviguer
// d'un module à l'autre). Aucune règle de permission ici : la liste des
// modules affichés vient déjà filtrée par le serveur (GET /api/admin/nav,
// voir webapp/admin_nav_service.py) — ce module se contente de l'afficher et
// de router entre les modules qu'elle contient.
import { loadDashboard } from "./admin-dashboard.js";
import { loadUsers } from "./admin-users.js";
import { loadUserProfile } from "./admin-user-profile.js";
import { loadAiOverview } from "./admin-ai.js";
import { loadAiProviderDetail } from "./admin-ai-provider.js";
import { loadJournal } from "./admin-journal.js";
import { loadSubscriptionsOverview } from "./admin-subscriptions.js";
import { loadSubscriptionDetail } from "./admin-subscription-detail.js";
import { loadSupport } from "./admin-support.js";
import { loadSupportTicketDetail } from "./admin-support-ticket.js";
import { loadHealth } from "./admin-health.js";
import { loadSettings } from "./admin-settings.js";
import { loadAnalytics } from "./admin-analytics.js";

// Sous-page /admin/users/:id — pas une entrée du menu (absente de
// /api/admin/nav), donc jamais dans moduleByPath : reconnue ici par motif,
// rattachée visuellement au module "Utilisateurs" (lien actif + fil
// d'Ariane) dont elle hérite la permission déjà validée côté serveur (la
// route Flask /admin/users/<id> exige le même rôle minimum, voir server.py).
const USER_PROFILE_PATH_RE = /^\/admin\/users\/(\d+)$/;

// Même principe pour /admin/ia/:id, rattachée au module "IA".
const AI_PROVIDER_PATH_RE = /^\/admin\/ia\/(\d+)$/;

// Même principe pour /admin/subscriptions/:plan, rattachée au module
// "Abonnements" — capture une chaîne (free/premium/ultra), jamais un entier
// (contrairement aux deux sous-routes ci-dessus, un plan n'a pas d'id
// numérique, voir plan_service.Plan.value).
const SUBSCRIPTION_DETAIL_PATH_RE = /^\/admin\/subscriptions\/([a-z]+)$/;

// Même principe pour /admin/support/:id, rattachée au module "Support".
const SUPPORT_TICKET_PATH_RE = /^\/admin\/support\/(\d+)$/;

const MOBILE_BREAKPOINT = 860;

function isMobile() {
  return window.innerWidth <= MOBILE_BREAKPOINT;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// ── Identité (header) ───────────────────────────────────────────────────
function renderIdentity(identity) {
  const container = document.getElementById("admin-identity");
  container.innerHTML = "";

  const avatarWrap = el("span", "admin-avatar");
  if (identity.avatar) {
    const img = document.createElement("img");
    img.src = identity.avatar;
    img.alt = "";
    avatarWrap.appendChild(img);
  } else {
    avatarWrap.textContent = (identity.name || "?").trim().charAt(0).toUpperCase();
  }

  const meta = el("span", "admin-identity-meta");
  meta.appendChild(el("span", "admin-identity-name", identity.name));
  meta.appendChild(el("span", "admin-identity-role", identity.role));

  container.append(avatarWrap, meta);
}

async function loadIdentity() {
  try {
    const res = await fetch("/api/admin/me", { credentials: "same-origin" });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(payload.error || `Erreur API /api/admin/me: ${res.status}`);
    renderIdentity(payload);
    return payload;
  } catch {
    document.getElementById("admin-identity").textContent = "Identité indisponible.";
    return null;
  }
}

// ── Navigation (sidebar + routeur) ───────────────────────────────────────
const COMING_SOON_MESSAGE = "Cette fonctionnalité sera disponible prochainement.";

function renderSidebar(modules, onNavigate) {
  const nav = document.getElementById("admin-sidebar-nav");
  nav.innerHTML = "";
  modules.forEach((module) => {
    const link = document.createElement("a");
    link.href = module.path;
    link.className = "admin-sidebar-link";
    link.dataset.path = module.path;
    link.innerHTML = `<span class="admin-sidebar-icon" aria-hidden="true">${module.icon}</span><span>${module.label}</span>`;
    link.addEventListener("click", (e) => {
      e.preventDefault();
      onNavigate(module.path, { pushState: true });
    });
    nav.appendChild(link);
  });
}

function setActiveLink(path) {
  document.querySelectorAll(".admin-sidebar-link").forEach((link) => {
    link.classList.toggle("is-active", link.dataset.path === path);
  });
}

function renderBreadcrumb(module, extraLabel) {
  const crumb = document.getElementById("admin-breadcrumb");
  crumb.innerHTML = "";
  crumb.appendChild(el("span", "admin-breadcrumb-item", "Administration"));
  if (module) {
    crumb.appendChild(el("span", "admin-breadcrumb-sep", "›"));
    const moduleLabel = extraLabel ? "admin-breadcrumb-item" : "admin-breadcrumb-item admin-breadcrumb-item--current";
    crumb.appendChild(el("span", moduleLabel, module.label));
  }
  if (extraLabel) {
    crumb.appendChild(el("span", "admin-breadcrumb-sep", "›"));
    crumb.appendChild(el("span", "admin-breadcrumb-item admin-breadcrumb-item--current", extraLabel));
  }
}

async function renderModuleContent(module, navigateTo) {
  const body = document.getElementById("admin-content-body");
  body.innerHTML = "";

  if (module.id === "dashboard") {
    const template = document.getElementById("admin-dashboard-template");
    body.appendChild(template.content.cloneNode(true));
    await loadDashboard(navigateTo);
    return;
  }

  if (module.id === "users") {
    const template = document.getElementById("admin-users-template");
    body.appendChild(template.content.cloneNode(true));
    await loadUsers((userId) => navigateTo(`/admin/users/${userId}`, { pushState: true }));
    return;
  }

  if (module.id === "ai") {
    const template = document.getElementById("admin-ai-template");
    body.appendChild(template.content.cloneNode(true));
    await loadAiOverview((providerId) => navigateTo(`/admin/ia/${providerId}`, { pushState: true }));
    return;
  }

  if (module.id === "journal") {
    const template = document.getElementById("admin-journal-template");
    body.appendChild(template.content.cloneNode(true));
    await loadJournal();
    return;
  }

  if (module.id === "health") {
    const template = document.getElementById("admin-health-template");
    body.appendChild(template.content.cloneNode(true));
    await loadHealth(navigateTo);
    return;
  }

  if (module.id === "settings") {
    const template = document.getElementById("admin-settings-template");
    body.appendChild(template.content.cloneNode(true));
    await loadSettings();
    return;
  }

  if (module.id === "analytics") {
    const template = document.getElementById("admin-analytics-template");
    body.appendChild(template.content.cloneNode(true));
    await loadAnalytics();
    return;
  }

  if (module.id === "subscriptions") {
    const template = document.getElementById("admin-subscriptions-template");
    body.appendChild(template.content.cloneNode(true));
    await loadSubscriptionsOverview((plan) => navigateTo(`/admin/subscriptions/${plan}`, { pushState: true }));
    return;
  }

  if (module.id === "support") {
    const template = document.getElementById("admin-support-template");
    body.appendChild(template.content.cloneNode(true));
    await loadSupport((ticketId) => navigateTo(`/admin/support/${ticketId}`, { pushState: true }));
    return;
  }

  const placeholder = el("div", "admin-coming-soon");
  placeholder.appendChild(el("div", "admin-coming-soon-icon", module.icon));
  placeholder.appendChild(el("h2", "admin-coming-soon-title", module.label));
  placeholder.appendChild(el("p", "admin-coming-soon-text", COMING_SOON_MESSAGE));
  body.appendChild(placeholder);
}

// Contenu de /admin/users/:id — fiche complète en lecture seule (voir
// admin-user-profile.js pour la logique des 8 onglets à chargement paresseux).
async function renderUserProfileContent(userId) {
  const body = document.getElementById("admin-content-body");
  body.innerHTML = "";
  const template = document.getElementById("admin-user-profile-template");
  body.appendChild(template.content.cloneNode(true));
  await loadUserProfile(userId);
}

// Contenu de /admin/ia/:id — fiche détaillée d'un fournisseur IA (voir
// admin-ai-provider.js pour la logique des 4 onglets à chargement paresseux).
async function renderAiProviderContent(providerId) {
  const body = document.getElementById("admin-content-body");
  body.innerHTML = "";
  const template = document.getElementById("admin-ai-provider-template");
  body.appendChild(template.content.cloneNode(true));
  await loadAiProviderDetail(providerId);
}

// Contenu de /admin/subscriptions/:plan — fiche détaillée d'un abonnement
// (voir admin-subscription-detail.js pour la logique des 6 onglets à
// chargement paresseux).
async function renderSubscriptionDetailContent(plan) {
  const body = document.getElementById("admin-content-body");
  body.innerHTML = "";
  const template = document.getElementById("admin-subscription-detail-template");
  body.appendChild(template.content.cloneNode(true));
  await loadSubscriptionDetail(plan);
}

// Contenu de /admin/support/:id — fiche ticket complète (voir
// admin-support-ticket.js).
async function renderSupportTicketContent(ticketId) {
  const body = document.getElementById("admin-content-body");
  body.innerHTML = "";
  const template = document.getElementById("admin-support-ticket-template");
  body.appendChild(template.content.cloneNode(true));
  await loadSupportTicketDetail(ticketId);
}

function closeMobileDrawer() {
  document.getElementById("admin-sidebar").classList.remove("is-open");
  document.getElementById("admin-sidebar-overlay").hidden = true;
  document.body.classList.remove("admin-drawer-open");
}

export async function initAdminShell() {
  document.getElementById("admin-sidebar-toggle").addEventListener("click", () => {
    const sidebar = document.getElementById("admin-sidebar");
    const overlay = document.getElementById("admin-sidebar-overlay");
    const opening = !sidebar.classList.contains("is-open");
    sidebar.classList.toggle("is-open", opening);
    overlay.hidden = !opening;
    document.body.classList.toggle("admin-drawer-open", opening);
  });
  document.getElementById("admin-sidebar-overlay").addEventListener("click", closeMobileDrawer);

  loadIdentity();

  let modules = [];
  try {
    const res = await fetch("/api/admin/nav", { credentials: "same-origin" });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(payload.error || `Erreur API /api/admin/nav: ${res.status}`);
    modules = payload.modules || [];
  } catch {
    document.getElementById("admin-global-error").hidden = false;
    document.getElementById("admin-global-error").textContent =
      "Impossible de charger le menu d'administration. Réessaie dans un instant.";
    document.getElementById("admin-sidebar-nav").innerHTML = "";
    return;
  }

  const moduleByPath = new Map(modules.map((m) => [m.path, m]));

  // Sous-pages de détail (/admin/<module>/:id) — pas des entrées du menu,
  // rattachées visuellement au module parent (lien actif + fil d'Ariane).
  // Un seul endroit à étendre pour une future fiche détaillée (ex: Analytics).
  const DETAIL_SUBROUTES = [
    { re: USER_PROFILE_PATH_RE, parentPath: "/admin/users", extraLabel: "Profil utilisateur", render: renderUserProfileContent },
    { re: AI_PROVIDER_PATH_RE, parentPath: "/admin/ia", extraLabel: "Fiche fournisseur", render: renderAiProviderContent },
    // param textuel (plan free/premium/ultra), jamais un id numérique —
    // voir SUBSCRIPTION_DETAIL_PATH_RE.
    { re: SUBSCRIPTION_DETAIL_PATH_RE, parentPath: "/admin/subscriptions", extraLabel: "Fiche abonnement", render: renderSubscriptionDetailContent, textParam: true },
    { re: SUPPORT_TICKET_PATH_RE, parentPath: "/admin/support", extraLabel: "Fiche ticket", render: renderSupportTicketContent },
  ];

  async function navigateTo(path, { pushState }) {
    for (const sub of DETAIL_SUBROUTES) {
      const match = path.match(sub.re);
      const parentModule = moduleByPath.get(sub.parentPath);
      if (!match || !parentModule) continue;
      if (pushState && window.location.pathname !== path) {
        window.history.pushState({ path }, "", path);
      }
      setActiveLink(sub.parentPath);
      renderBreadcrumb(parentModule, sub.extraLabel);
      document.title = `${sub.extraLabel} — Administration Mathadap`;
      if (isMobile()) closeMobileDrawer();
      await sub.render(sub.textParam ? match[1] : Number(match[1]));
      return;
    }

    const module = moduleByPath.get(path);
    if (!module) return; // chemin inconnu du menu autorisé — jamais de rendu, jamais de 404 côté client non plus
    if (pushState && window.location.pathname !== path) {
      window.history.pushState({ path }, "", path);
    }
    setActiveLink(path);
    renderBreadcrumb(module);
    document.title = `${module.label} — Administration Mathadap`;
    if (isMobile()) closeMobileDrawer();
    await renderModuleContent(module, navigateTo);
  }

  renderSidebar(modules, navigateTo);

  window.addEventListener("popstate", () => {
    navigateTo(window.location.pathname, { pushState: false });
  });

  // Chemin courant au chargement — direct (rechargement/URL tapée) ou après
  // clic sur un lien sidebar/breadcrumb d'une AUTRE page : toujours un module
  // valide, car chaque chemin sidebar correspond à une route Flask réellement
  // enregistrée (voir server.py) et jamais un 404.
  await navigateTo(window.location.pathname, { pushState: false });
}
