// Module "Utilisateurs" (/admin/users) — CRM en lecture seule : aucune
// action de modification (pas de bouton supprimer/modifier/suspendre/
// réinitialiser/changer d'abonnement ou de rôle). Recherche/filtres/tri/
// pagination sont tous délégués au backend (voir GET /api/admin/users,
// admin_users_service.py) — ce module ne trie/filtre jamais en mémoire, pour
// rester performant quel que soit le nombre de comptes.
import { debounce } from "./searchUtils.js";

const EMPTY_LABEL = "Aucune donnée disponible";
const SEARCH_DEBOUNCE_MS = 300;

const PLAN_LABELS = { free: "Gratuit", premium: "Premium", ultra: "Ultra" };
const ROLE_LABELS = {
  user: "Utilisateur", support: "Support", moderator: "Modérateur",
  admin: "Admin", super_admin: "Super admin",
};
// 3 valeurs réelles de users.account_status (Chantier Administrateur
// "Utilisateurs", Phase 2 — remplace l'ancien bucket "Suspendu" qui les
// confondait toutes les deux). Même wording que admin-user-profile.js::
// ACCOUNT_STATUS_LABELS, jamais un second libellé pour la même donnée.
const ACCOUNT_STATUS_LABELS = {
  active: "Actif",
  pending_parental_consent: "En attente de consentement",
  parental_consent_refused: "Consentement refusé",
};
// Réutilise .admin-status-dot--{ok,warning,down} (déjà utilisé par le
// Dashboard/Santé/Support pour exactement cette sémantique à 3 tons) plutôt
// que d'inventer une nouvelle métaphore visuelle.
const ACCOUNT_STATUS_DOT_CLASS = {
  active: "ok",
  pending_parental_consent: "warning",
  parental_consent_refused: "down",
};
const PAYMENT_STATUS_LABELS = { failed: "Paiement en échec" };

const COLUMNS = [
  { key: "avatar", label: "Avatar", sortable: false },
  { key: "name", label: "Nom", sortable: true, sortKey: "pseudo" },
  { key: "email", label: "Email", sortable: true, sortKey: "email" },
  { key: "plan", label: "Abonnement", sortable: true, sortKey: "plan" },
  { key: "account_status", label: "Statut", sortable: false },
  { key: "role", label: "Rôle", sortable: true, sortKey: "role" },
  { key: "last_login_at", label: "Dernière connexion", sortable: true, sortKey: "last_login_at" },
  { key: "created_at", label: "Date de création", sortable: true, sortKey: "created_at" },
  { key: "total_time_s", label: "Temps passé", sortable: true, sortKey: "total_time_s" },
];

function statusDot(accountStatus) {
  const cls = ACCOUNT_STATUS_DOT_CLASS[accountStatus] || "unknown";
  const label = ACCOUNT_STATUS_LABELS[accountStatus] || accountStatus;
  return el("span", `admin-status-dot admin-status-dot--${cls}`, label);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatDateTime(iso) {
  if (!iso) return "Jamais connecté";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatDate(iso) {
  if (!iso) return EMPTY_LABEL;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function formatDuration(seconds) {
  const s = Math.round(seconds || 0);
  if (s < 60) return `${s} s`;
  const minutes = Math.floor(s / 60);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remMinutes = minutes % 60;
  return remMinutes ? `${hours} h ${remMinutes} min` : `${hours} h`;
}

function avatarNode(user) {
  const wrap = el("span", "admin-avatar admin-avatar--sm");
  if (user.avatar) {
    const img = document.createElement("img");
    img.src = user.avatar;
    img.alt = "";
    wrap.appendChild(img);
  } else {
    wrap.textContent = (user.name || "?").trim().charAt(0).toUpperCase();
  }
  return wrap;
}

// ── État du module (réinitialisé à chaque montage du module Utilisateurs) ──
function initialState() {
  return {
    search: "", role: "", plan: "", account_status: "", payment_status: "",
    sort_by: "created_at", sort_dir: "desc",
    page: 1, page_size: 25,
  };
}

function buildQuery(state) {
  const params = new URLSearchParams();
  if (state.search) params.set("search", state.search);
  if (state.role) params.set("role", state.role);
  if (state.plan) params.set("plan", state.plan);
  if (state.account_status) params.set("account_status", state.account_status);
  if (state.payment_status) params.set("payment_status", state.payment_status);
  params.set("sort_by", state.sort_by);
  params.set("sort_dir", state.sort_dir);
  params.set("page", String(state.page));
  params.set("page_size", String(state.page_size));
  return params.toString();
}

function renderTableHead(theadRow, state, onSort) {
  theadRow.innerHTML = "";
  COLUMNS.forEach((col) => {
    const th = el("th", "admin-users-th", col.label);
    if (col.sortable) {
      th.classList.add("is-sortable");
      if (state.sort_by === col.sortKey) {
        th.classList.add(state.sort_dir === "asc" ? "is-sorted-asc" : "is-sorted-desc");
      }
      th.addEventListener("click", () => onSort(col.sortKey));
    }
    theadRow.appendChild(th);
  });
}

function renderSkeletonRows(tbody, count = 8) {
  tbody.innerHTML = "";
  for (let i = 0; i < count; i += 1) {
    const tr = el("tr", "admin-users-row admin-users-row--skeleton");
    COLUMNS.forEach(() => {
      const td = el("td", "admin-users-td");
      td.appendChild(el("span", "admin-skeleton admin-users-skeleton-cell", " "));
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
}

function renderRows(tbody, users, onRowClick) {
  tbody.innerHTML = "";
  users.forEach((user) => {
    const tr = el("tr", "admin-users-row");
    tr.tabIndex = 0;
    tr.setAttribute("role", "button");
    tr.addEventListener("click", () => onRowClick(user.id));
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onRowClick(user.id); }
    });

    const avatarTd = el("td", "admin-users-td");
    avatarTd.appendChild(avatarNode(user));
    tr.appendChild(avatarTd);

    tr.appendChild(el("td", "admin-users-td", user.name));
    tr.appendChild(el("td", "admin-users-td admin-users-td--muted admin-users-td--wrap", user.email));

    tr.appendChild(el("td", "admin-users-td", PLAN_LABELS[user.plan] || user.plan));
    const statusTd = el("td", "admin-users-td");
    statusTd.appendChild(statusDot(user.account_status));
    tr.appendChild(statusTd);
    tr.appendChild(el("td", "admin-users-td", ROLE_LABELS[user.role] || user.role));
    tr.appendChild(el("td", "admin-users-td", formatDateTime(user.last_login_at)));
    tr.appendChild(el("td", "admin-users-td", formatDate(user.created_at)));
    tr.appendChild(el("td", "admin-users-td", formatDuration(user.total_time_s)));

    tbody.appendChild(tr);
  });
}

function renderPagination(container, snapshot, onPageChange) {
  container.innerHTML = "";
  if (snapshot.total === 0) return;

  const info = el("span", "admin-users-pagination-info",
    `Page ${snapshot.page} / ${snapshot.total_pages} · ${new Intl.NumberFormat("fr-FR").format(snapshot.total)} utilisateur(s)`);
  container.appendChild(info);

  const prev = el("button", "admin-icon-btn admin-users-page-btn", "‹");
  prev.type = "button";
  prev.disabled = snapshot.page <= 1;
  prev.setAttribute("aria-label", "Page précédente");
  prev.addEventListener("click", () => onPageChange(snapshot.page - 1));
  container.appendChild(prev);

  const next = el("button", "admin-icon-btn admin-users-page-btn", "›");
  next.type = "button";
  next.disabled = snapshot.page >= snapshot.total_pages;
  next.setAttribute("aria-label", "Page suivante");
  next.addEventListener("click", () => onPageChange(snapshot.page + 1));
  container.appendChild(next);
}

function populateSelect(select, options, placeholder) {
  select.innerHTML = "";
  select.appendChild(new Option(placeholder, ""));
  options.forEach(([value, label]) => select.appendChild(new Option(label, value)));
}

export async function loadUsers(onRowClick) {
  const searchInput = document.getElementById("admin-users-search-input");
  const planSelect = document.getElementById("admin-users-filter-plan");
  const roleSelect = document.getElementById("admin-users-filter-role");
  const statusSelect = document.getElementById("admin-users-filter-status");
  const paymentSelect = document.getElementById("admin-users-filter-payment");
  const theadRow = document.getElementById("admin-users-thead-row");
  const tbody = document.getElementById("admin-users-tbody");
  const emptyEl = document.getElementById("admin-users-empty");
  const paginationEl = document.getElementById("admin-users-pagination");
  const errorEl = document.getElementById("admin-global-error");

  const state = initialState();

  populateSelect(planSelect, Object.entries(PLAN_LABELS), "Tous les abonnements");
  populateSelect(roleSelect, Object.entries(ROLE_LABELS), "Tous les rôles");
  populateSelect(statusSelect, Object.entries(ACCOUNT_STATUS_LABELS), "Tous les statuts");
  populateSelect(paymentSelect, Object.entries(PAYMENT_STATUS_LABELS), "Tous les paiements");

  async function refresh() {
    renderTableHead(theadRow, state, (sortKey) => {
      if (state.sort_by === sortKey) {
        state.sort_dir = state.sort_dir === "asc" ? "desc" : "asc";
      } else {
        state.sort_by = sortKey;
        state.sort_dir = "asc";
      }
      state.page = 1;
      refresh();
    });
    renderSkeletonRows(tbody);
    emptyEl.hidden = true;
    paginationEl.innerHTML = "";
    errorEl.hidden = true;

    let snapshot;
    try {
      const res = await fetch(`/api/admin/users?${buildQuery(state)}`, { credentials: "same-origin" });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(payload.error || `Erreur API (${res.status})`);
      snapshot = payload;
    } catch {
      tbody.innerHTML = "";
      errorEl.textContent = "Impossible de charger la liste des utilisateurs. Réessaie dans un instant.";
      errorEl.hidden = false;
      return;
    }

    tbody.innerHTML = "";
    if (snapshot.items.length === 0) {
      emptyEl.textContent = EMPTY_LABEL;
      emptyEl.hidden = false;
      return;
    }
    renderRows(tbody, snapshot.items, onRowClick);
    renderPagination(paginationEl, snapshot, (page) => { state.page = page; refresh(); });
  }

  const debouncedSearch = debounce((value) => {
    state.search = value;
    state.page = 1;
    refresh();
  }, SEARCH_DEBOUNCE_MS);

  searchInput.addEventListener("input", (e) => debouncedSearch(e.target.value));
  planSelect.addEventListener("change", (e) => { state.plan = e.target.value; state.page = 1; refresh(); });
  roleSelect.addEventListener("change", (e) => { state.role = e.target.value; state.page = 1; refresh(); });
  statusSelect.addEventListener("change", (e) => { state.account_status = e.target.value; state.page = 1; refresh(); });
  paymentSelect.addEventListener("change", (e) => { state.payment_status = e.target.value; state.page = 1; refresh(); });

  await refresh();
}
