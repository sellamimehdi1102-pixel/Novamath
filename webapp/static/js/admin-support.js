// Module "Support" (/admin/support) — gestion des tickets envoyés par les
// utilisateurs (voir support_service.py). Recherche/filtres/tri/pagination
// délégués au backend (même architecture que admin-users.js/admin-journal.js,
// réutilise .admin-users-table) — jamais de tri/filtre en mémoire côté client.
import { debounce } from "./searchUtils.js";
import { fetchTeamMembers } from "./admin-team-roles.js";

const SEARCH_DEBOUNCE_MS = 300;

const STATUS_LABELS = { open: "Ouvert", in_progress: "En cours", closed: "Fermé" };
const CATEGORY_LABELS = {
  bug: "Bug", paiement: "Paiement", ia: "IA", compte: "Compte", technique: "Technique", autre: "Autre",
};
const PRIORITY_LABELS = { faible: "Faible", normale: "Normale", haute: "Haute", urgente: "Urgente" };

const COLUMNS = [
  { key: "id", label: "ID", sortable: false },
  { key: "user", label: "Utilisateur", sortable: false },
  { key: "email", label: "Email", sortable: false },
  { key: "subject", label: "Sujet", sortable: false },
  { key: "category", label: "Catégorie", sortable: true, sortKey: "category" },
  { key: "priority", label: "Priorité", sortable: true, sortKey: "priority" },
  { key: "status", label: "Statut", sortable: true, sortKey: "status" },
  { key: "assigned", label: "Assigné", sortable: false },
  { key: "created_at", label: "Créé le", sortable: true, sortKey: "created_at" },
  { key: "last_response_at", label: "Dernière réponse", sortable: true, sortKey: "last_response_at" },
];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function initialState() {
  return {
    search: "", status: "", category: "", priority: "", assigned_admin_id: "",
    sort_by: "created_at", sort_dir: "desc",
    page: 1, page_size: 25,
  };
}

function buildQuery(state) {
  const params = new URLSearchParams();
  if (state.search) params.set("search", state.search);
  if (state.status) params.set("status", state.status);
  if (state.category) params.set("category", state.category);
  if (state.priority) params.set("priority", state.priority);
  if (state.assigned_admin_id) params.set("assigned_admin_id", state.assigned_admin_id);
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

export function priorityBadge(priority) {
  const modifier = priority === "urgente" || priority === "haute" ? "error" : "muted";
  return el("span", `admin-badge admin-badge--${priority === "normale" || priority === "faible" ? "muted" : modifier}`, PRIORITY_LABELS[priority] || priority);
}

// Exportée pour réutilisation par admin-user-profile.js (onglet Support de
// la fiche utilisateur, Chantier Administrateur "Utilisateurs" Phase 2) —
// même wording/couleurs que ce module, jamais un second badge de statut.
export function statusBadge(status) {
  const modifier = status === "closed" ? "muted" : (status === "open" ? "error" : "ok");
  return el("span", `admin-badge admin-badge--${modifier}`, STATUS_LABELS[status] || status);
}

function renderRows(tbody, tickets, onRowClick) {
  tbody.innerHTML = "";
  tickets.forEach((ticket) => {
    const tr = el("tr", "admin-users-row");
    tr.tabIndex = 0;
    tr.setAttribute("role", "button");
    tr.addEventListener("click", () => onRowClick(ticket.id));
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onRowClick(ticket.id); }
    });

    tr.appendChild(el("td", "admin-users-td", `#${ticket.id}`));
    tr.appendChild(el("td", "admin-users-td", ticket.user_pseudo));
    tr.appendChild(el("td", "admin-users-td admin-users-td--muted admin-users-td--wrap", ticket.user_email));
    tr.appendChild(el("td", "admin-users-td admin-users-td--wrap", ticket.subject));
    tr.appendChild(el("td", "admin-users-td", ticket.category_label));

    const priorityTd = el("td", "admin-users-td");
    priorityTd.appendChild(priorityBadge(ticket.priority));
    tr.appendChild(priorityTd);

    const statusTd = el("td", "admin-users-td");
    statusTd.appendChild(statusBadge(ticket.status));
    tr.appendChild(statusTd);

    tr.appendChild(el("td", "admin-users-td", ticket.assigned_admin_name || "—"));
    tr.appendChild(el("td", "admin-users-td", formatDateTime(ticket.created_at)));
    tr.appendChild(el("td", "admin-users-td", formatDateTime(ticket.last_response_at)));

    tbody.appendChild(tr);
  });
}

function renderPagination(container, snapshot, onPageChange) {
  container.innerHTML = "";
  if (snapshot.total === 0) return;

  const info = el("span", "admin-users-pagination-info",
    `Page ${snapshot.page} / ${snapshot.total_pages} · ${new Intl.NumberFormat("fr-FR").format(snapshot.total)} ticket(s)`);
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

export async function loadSupport(onRowClick) {
  const searchInput = document.getElementById("admin-support-search-input");
  const statusSelect = document.getElementById("admin-support-filter-status");
  const categorySelect = document.getElementById("admin-support-filter-category");
  const prioritySelect = document.getElementById("admin-support-filter-priority");
  const assignedSelect = document.getElementById("admin-support-filter-assigned");
  const theadRow = document.getElementById("admin-support-thead-row");
  const tbody = document.getElementById("admin-support-tbody");
  const emptyEl = document.getElementById("admin-support-empty");
  const paginationEl = document.getElementById("admin-support-pagination");
  const errorEl = document.getElementById("admin-global-error");

  const state = initialState();

  populateSelect(statusSelect, Object.entries(STATUS_LABELS), "Tous les statuts");
  populateSelect(categorySelect, Object.entries(CATEGORY_LABELS), "Toutes les catégories");
  populateSelect(prioritySelect, Object.entries(PRIORITY_LABELS), "Toutes les priorités");

  // Liste des administrateurs assignables (rôles d'équipe) — factorisée dans
  // admin-team-roles.js (partagée avec admin-support-ticket.js).
  try {
    const admins = await fetchTeamMembers();
    populateSelect(assignedSelect, [...admins].map(([id, name]) => [String(id), name]), "Tous les assignataires");
  } catch {
    populateSelect(assignedSelect, [], "Tous les assignataires");
  }

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
      const res = await fetch(`/api/admin/support/tickets?${buildQuery(state)}`, { credentials: "same-origin" });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(payload.error || `Erreur API (${res.status})`);
      snapshot = payload;
    } catch {
      tbody.innerHTML = "";
      errorEl.textContent = "Impossible de charger la liste des tickets. Réessaie dans un instant.";
      errorEl.hidden = false;
      return;
    }

    tbody.innerHTML = "";
    if (snapshot.items.length === 0) {
      emptyEl.textContent = "Aucun ticket ne correspond à ces critères.";
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
  statusSelect.addEventListener("change", (e) => { state.status = e.target.value; state.page = 1; refresh(); });
  categorySelect.addEventListener("change", (e) => { state.category = e.target.value; state.page = 1; refresh(); });
  prioritySelect.addEventListener("change", (e) => { state.priority = e.target.value; state.page = 1; refresh(); });
  assignedSelect.addEventListener("change", (e) => { state.assigned_admin_id = e.target.value; state.page = 1; refresh(); });

  await refresh();
}
