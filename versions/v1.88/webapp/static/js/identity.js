// ── Widget d'identité partagé (sidebar) ─────────────────────────────────────
// Depuis l'introduction des comptes, l'identité (pseudo/avatar) vient du
// compte connecté (/api/auth/me) et non plus uniquement de localStorage.
// Se met à jour en direct dans l'onglet courant via l'événement
// novamath:account-updated (déclenché par profil.js après une modification).
import { api } from "./api.js";
import { ICONS } from "./icons.js";

function initials(name) {
  const parts = String(name || "").trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() || "").join("") || "?";
}

const PLAN_LABELS = { free: "Free", premium: "Premium", ultra: "Ultra" };
function planLabel(plan) {
  return PLAN_LABELS[plan] || PLAN_LABELS.free;
}

// ── Badge "Mode invité", à côté du logo (dans l'en-tête, pas dans le widget
// de profil) — rappelle simplement que certaines fonctionnalités sont
// limitées, sans bloquer quoi que ce soit. ──────────────────────────────────
function paintGuestBadge(user) {
  const brand = document.querySelector(".brand");
  let badge = document.getElementById("guest-header-badge");
  if (!user.is_guest || !brand) {
    if (badge) badge.remove();
    return;
  }
  if (badge) return;
  badge = document.createElement("span");
  badge.id = "guest-header-badge";
  badge.className = "guest-badge";
  badge.textContent = "Mode invité";
  brand.insertAdjacentElement("afterend", badge);
}

// ── Widget "profil" de la sidebar : pour un compte invité, remplacé par une
// invitation à créer un compte plutôt qu'un accès à un profil qui n'a pas de
// vrai intérêt pour lui (nom "Invité", pas de personnalisation possible). ───
function paintSidebarUser(user) {
  const nameEl = document.getElementById("sidebar-user-name");
  const avatarEl = document.getElementById("sidebar-user-avatar");
  const userLink = document.getElementById("sidebar-user");
  const subEl = userLink?.querySelector(".sub");
  if (!nameEl || !avatarEl || !userLink) return;

  if (user.is_guest) {
    userLink.classList.remove("is-current");
    userLink.classList.add("js-open-signup", "sidebar-user--cta");
    userLink.removeAttribute("href");
    userLink.setAttribute("role", "button");
    userLink.setAttribute("tabindex", "0");
    nameEl.textContent = "Créer un compte";
    if (subEl) subEl.textContent = "Sauvegarder ma progression";
    avatarEl.innerHTML = ICONS.userPlus;
    return;
  }

  userLink.classList.remove("js-open-signup", "sidebar-user--cta");
  userLink.setAttribute("href", "profil.html");
  userLink.removeAttribute("role");
  userLink.removeAttribute("tabindex");
  if (subEl) subEl.textContent = planLabel(user.plan);
  const onProfilePage = /(^|\/)profil\.html$/.test(window.location.pathname);
  userLink.classList.toggle("is-current", onProfilePage);

  nameEl.textContent = user.pseudo || "Élève";
  avatarEl.innerHTML = "";
  if (user.avatar) {
    const img = document.createElement("img");
    img.src = user.avatar;
    img.alt = "";
    avatarEl.appendChild(img);
  } else {
    avatarEl.textContent = initials(user.pseudo);
  }
}

function paint(user) {
  if (!user) return;
  paintGuestBadge(user);
  paintSidebarUser(user);
}

async function render() {
  try {
    const { user } = await api.me();
    paint(user);
  } catch {
    // Page protégée normalement déjà gardée côté serveur ; si la session a
    // expiré entre-temps, on laisse le prochain rechargement rediriger vers
    // la connexion plutôt que de planter le widget.
  }
}

render();
window.addEventListener("novamath:account-updated", (e) => paint(e.detail));

// Sans `href`, un <a role="button"> n'est pas activable au clavier nativement
// (contrairement à un vrai lien) — on relaie Entrée/Espace vers un clic.
document.addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  const link = document.getElementById("sidebar-user");
  if (link && link.getAttribute("role") === "button" && document.activeElement === link) {
    e.preventDefault();
    link.click();
  }
});

export { render as renderIdentity };
