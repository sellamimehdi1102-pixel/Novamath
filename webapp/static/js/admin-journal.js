// Module "Journal" (/admin/journal) — historique en lecture seule de toutes
// les actions effectuées depuis le module Administration IA (voir
// admin_ai_log_service.py / GET /api/admin/journal). Recherche/filtres/tri
// sont tous délégués au backend (jamais filtré en mémoire, même politique
// que admin-users.js) — ce fichier réutilise volontairement le même
// composant table (.admin-users-table) et le même motif de pagination.
import { debounce } from "./searchUtils.js";

const EMPTY_LABEL = "Aucune donnée disponible";
const SEARCH_DEBOUNCE_MS = 300;

const RESULT_LABELS = { success: "Succès", error: "Échec" };

// Catégorisation des actions par préfixe/verbe — purement de l'affichage
// (couleur de badge), aucune influence sur les filtres/l'API. Réutilise les
// variantes déjà existantes de .admin-badge (voir admin.css) : une variante
// par grande famille d'action plutôt qu'une par valeur d'ACTIONS.
const ACTION_CATEGORIES = [
  { test: (a) => a.startsWith("create_"), label: "Création", variant: "premium" },
  { test: (a) => a.startsWith("delete_"), label: "Suppression", variant: "error" },
  { test: (a) => a.startsWith("enable_"), label: "Activation", variant: "ok" },
  { test: (a) => a.startsWith("disable_"), label: "Désactivation", variant: "muted" },
  { test: (a) => a.startsWith("test_") || a === "health_check", label: "Test", variant: "ultra" },
  { test: (a) => a.startsWith("analytics_"), label: "Analytics", variant: "free" },
  { test: () => true, label: "Modification", variant: "neutral" },
];

function actionCategory(action) {
  return ACTION_CATEGORIES.find((cat) => cat.test(action || "")) || ACTION_CATEGORIES[ACTION_CATEGORIES.length - 1];
}

const COLUMNS = [
  { key: "created_at", label: "Date / Heure" },
  { key: "admin", label: "Administrateur" },
  { key: "ip", label: "Adresse IP" },
  { key: "action", label: "Action" },
  { key: "provider", label: "Fournisseur" },
  { key: "result", label: "Résultat" },
  { key: "error", label: "Erreur" },
];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatDateTime(iso) {
  if (!iso) return EMPTY_LABEL;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// ── État du module (réinitialisé à chaque montage) ──────────────────────
function initialState() {
  return {
    search: "", admin_user_id: "", provider_id: "", action: "", result: "",
    date_from: "", date_to: "", page: 1, page_size: 25,
  };
}

function buildQuery(state) {
  const params = new URLSearchParams();
  if (state.search) params.set("search", state.search);
  if (state.admin_user_id) params.set("admin_user_id", state.admin_user_id);
  if (state.provider_id) params.set("provider_id", state.provider_id);
  if (state.action) params.set("action", state.action);
  if (state.result) params.set("result", state.result);
  if (state.date_from) params.set("date_from", state.date_from);
  if (state.date_to) params.set("date_to", state.date_to);
  params.set("page", String(state.page));
  params.set("page_size", String(state.page_size));
  return params.toString();
}

function renderTableHead(theadRow) {
  theadRow.innerHTML = "";
  COLUMNS.forEach((col) => theadRow.appendChild(el("th", "admin-users-th", col.label)));
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

// ── Regroupement visuel par jour ────────────────────────────────────────
function dayKey(date) {
  if (Number.isNaN(date.getTime())) return "unknown";
  // Format YYYY-MM-DD stable, basé sur le calendrier local (cohérent avec
  // formatDateTime qui affiche déjà les dates en heure locale).
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function dayLabel(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return EMPTY_LABEL;
  const key = dayKey(date);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (key === dayKey(today)) return "Aujourd'hui";
  if (key === dayKey(yesterday)) return "Hier";
  return date.toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });
}

function renderRows(tbody, entries, onRowClick, columnCount) {
  tbody.innerHTML = "";
  let lastGroupKey = null;
  entries.forEach((entry) => {
    const groupKey = dayKey(new Date(entry.created_at || ""));
    if (groupKey !== lastGroupKey) {
      lastGroupKey = groupKey;
      const headerTr = el("tr", "admin-journal-day-row");
      const headerTd = el("td", "admin-journal-day-td", dayLabel(entry.created_at));
      headerTd.colSpan = columnCount;
      headerTr.appendChild(headerTd);
      tbody.appendChild(headerTr);
    }

    const tr = el("tr", "admin-users-row");
    tr.tabIndex = 0;
    tr.setAttribute("role", "button");
    tr.addEventListener("click", () => onRowClick(entry));
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onRowClick(entry); }
    });

    tr.appendChild(el("td", "admin-users-td", formatDateTime(entry.created_at)));

    const adminTd = el("td", "admin-users-td");
    adminTd.appendChild(el("span", null, entry.admin.name));
    adminTd.appendChild(document.createElement("br"));
    adminTd.appendChild(el("span", "admin-card-sub", entry.admin.role));
    tr.appendChild(adminTd);

    tr.appendChild(el("td", "admin-users-td admin-users-td--muted", entry.ip || EMPTY_LABEL));

    const actionTd = el("td", "admin-users-td");
    const category = actionCategory(entry.action);
    actionTd.appendChild(el("span", `admin-badge admin-badge--${category.variant}`, category.label));
    actionTd.appendChild(document.createElement("br"));
    actionTd.appendChild(el("span", "admin-card-sub", entry.action_label));
    tr.appendChild(actionTd);

    tr.appendChild(el("td", "admin-users-td", entry.provider ? entry.provider.name : EMPTY_LABEL));

    const resultTd = el("td", "admin-users-td");
    resultTd.appendChild(el("span", `admin-status-dot admin-status-dot--${entry.result === "success" ? "ok" : "down"}`,
      RESULT_LABELS[entry.result] || entry.result));
    tr.appendChild(resultTd);

    tr.appendChild(el("td", "admin-users-td admin-users-td--muted", entry.error_message || EMPTY_LABEL));

    tbody.appendChild(tr);
  });
}

function renderPagination(container, snapshot, onPageChange) {
  container.innerHTML = "";
  if (snapshot.total === 0) return;

  const info = el("span", "admin-users-pagination-info",
    `Page ${snapshot.page} / ${snapshot.total_pages} · ${new Intl.NumberFormat("fr-FR").format(snapshot.total)} événement(s)`);
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

// ── Chips de filtres actifs (voir .admin-filter-chips dans admin.css) ───
function selectedLabel(select) {
  const opt = select.selectedOptions[0];
  return opt ? opt.text : "";
}

function renderFilterChips(container, state, inputs, onRemove, onReset) {
  container.innerHTML = "";
  const chips = [];

  if (state.search) chips.push({ label: `Recherche : "${state.search}"`, remove: () => onRemove("search") });
  if (state.admin_user_id) chips.push({ label: `Administrateur : ${selectedLabel(inputs.adminSelect)}`, remove: () => onRemove("admin_user_id") });
  if (state.provider_id) chips.push({ label: `Fournisseur : ${selectedLabel(inputs.providerSelect)}`, remove: () => onRemove("provider_id") });
  if (state.action) chips.push({ label: `Action : ${selectedLabel(inputs.actionSelect)}`, remove: () => onRemove("action") });
  if (state.result) chips.push({ label: `Résultat : ${RESULT_LABELS[state.result] || state.result}`, remove: () => onRemove("result") });
  if (state.date_from) chips.push({ label: `Depuis le ${state.date_from}`, remove: () => onRemove("date_from") });
  if (state.date_to) chips.push({ label: `Jusqu'au ${state.date_to}`, remove: () => onRemove("date_to") });

  if (chips.length === 0) {
    container.hidden = true;
    return;
  }

  container.hidden = false;
  chips.forEach(({ label, remove }) => {
    const chip = el("span", "admin-filter-chip");
    chip.appendChild(el("span", null, label));
    const removeBtn = el("button", "admin-filter-chip-remove", "✕");
    removeBtn.type = "button";
    removeBtn.setAttribute("aria-label", `Retirer le filtre : ${label}`);
    removeBtn.addEventListener("click", remove);
    chip.appendChild(removeBtn);
    container.appendChild(chip);
  });

  const resetBtn = el("button", "admin-filter-chips-reset", "Réinitialiser tous les filtres");
  resetBtn.type = "button";
  resetBtn.addEventListener("click", onReset);
  container.appendChild(resetBtn);
}

// ── Modale de détail (anciennes/nouvelles valeurs) ──────────────────────
function openDetailModal(entry) {
  const overlay = document.getElementById("admin-journal-detail-modal");
  const body = document.getElementById("admin-journal-detail-modal-body");
  const closeBtn = document.getElementById("admin-journal-detail-modal-close");
  body.innerHTML = "";

  const summary = el("div", "admin-fields-grid");
  summary.appendChild(el("div", "admin-field")).append(
    el("span", "admin-field-label", "Date / heure"), el("span", "admin-field-value", formatDateTime(entry.created_at)),
  );
  summary.appendChild(el("div", "admin-field")).append(
    el("span", "admin-field-label", "Administrateur"), el("span", "admin-field-value", `${entry.admin.name} (${entry.admin.role})`),
  );
  summary.appendChild(el("div", "admin-field")).append(
    el("span", "admin-field-label", "Adresse IP"), el("span", "admin-field-value", entry.ip || EMPTY_LABEL),
  );
  summary.appendChild(el("div", "admin-field")).append(
    el("span", "admin-field-label", "Action"), el("span", "admin-field-value", entry.action_label),
  );
  summary.appendChild(el("div", "admin-field")).append(
    el("span", "admin-field-label", "Fournisseur"), el("span", "admin-field-value", entry.provider ? entry.provider.name : EMPTY_LABEL),
  );
  summary.appendChild(el("div", "admin-field")).append(
    el("span", "admin-field-label", "Résultat"), el("span", "admin-field-value", RESULT_LABELS[entry.result] || entry.result),
  );
  if (entry.error_message) {
    summary.appendChild(el("div", "admin-field admin-form-field--full")).append(
      el("span", "admin-field-label", "Message d'erreur"), el("span", "admin-field-value", entry.error_message),
    );
  }
  body.appendChild(summary);

  const diff = el("div", "admin-journal-diff");
  const oldCol = el("div", "admin-journal-diff-col");
  oldCol.appendChild(el("h3", null, "Anciennes valeurs"));
  const oldPre = document.createElement("pre");
  oldPre.textContent = entry.old_values ? JSON.stringify(entry.old_values, null, 2) : EMPTY_LABEL;
  oldCol.appendChild(oldPre);
  diff.appendChild(oldCol);

  const newCol = el("div", "admin-journal-diff-col");
  newCol.appendChild(el("h3", null, "Nouvelles valeurs"));
  const newPre = document.createElement("pre");
  newPre.textContent = entry.new_values ? JSON.stringify(entry.new_values, null, 2) : EMPTY_LABEL;
  newCol.appendChild(newPre);
  diff.appendChild(newCol);

  body.appendChild(diff);

  function close() { overlay.hidden = true; }
  closeBtn.onclick = close;
  overlay.onclick = (e) => { if (e.target === overlay) close(); };
  overlay.hidden = false;
}

export async function loadJournal() {
  const searchInput = document.getElementById("admin-journal-search-input");
  const adminSelect = document.getElementById("admin-journal-filter-admin");
  const providerSelect = document.getElementById("admin-journal-filter-provider");
  const actionSelect = document.getElementById("admin-journal-filter-action");
  const resultSelect = document.getElementById("admin-journal-filter-result");
  const dateFromInput = document.getElementById("admin-journal-filter-date-from");
  const dateToInput = document.getElementById("admin-journal-filter-date-to");
  const theadRow = document.getElementById("admin-journal-thead-row");
  const tbody = document.getElementById("admin-journal-tbody");
  const emptyEl = document.getElementById("admin-journal-empty");
  const paginationEl = document.getElementById("admin-journal-pagination");
  const errorEl = document.getElementById("admin-global-error");
  const exportCsvBtn = document.getElementById("admin-journal-export-csv");
  const exportJsonBtn = document.getElementById("admin-journal-export-json");
  const filterChipsEl = document.getElementById("admin-journal-filter-chips");

  const state = initialState();
  renderTableHead(theadRow);

  const filterInputs = { adminSelect, providerSelect, actionSelect };

  function clearFilter(key) {
    state[key] = "";
    if (key === "search") searchInput.value = "";
    if (key === "admin_user_id") adminSelect.value = "";
    if (key === "provider_id") providerSelect.value = "";
    if (key === "action") actionSelect.value = "";
    if (key === "result") resultSelect.value = "";
    if (key === "date_from") dateFromInput.value = "";
    if (key === "date_to") dateToInput.value = "";
    state.page = 1;
    refresh();
  }

  function resetAllFilters() {
    searchInput.value = "";
    adminSelect.value = "";
    providerSelect.value = "";
    actionSelect.value = "";
    resultSelect.value = "";
    dateFromInput.value = "";
    dateToInput.value = "";
    Object.assign(state, initialState());
    refresh();
  }

  try {
    const res = await fetch("/api/admin/journal/filters", { credentials: "same-origin" });
    const filters = await res.json().catch(() => ({ admins: [], providers: [], actions: [] }));
    populateSelect(adminSelect, filters.admins.map((a) => [String(a.id), a.name]), "Tous les administrateurs");
    populateSelect(providerSelect, filters.providers.map((p) => [String(p.id), p.name]), "Tous les fournisseurs");
    populateSelect(actionSelect, filters.actions.map((a) => [a.value, a.label]), "Toutes les actions");
  } catch {
    // Filtres non critiques : la liste principale reste consultable sans eux.
  }
  populateSelect(resultSelect, [["success", "Succès"], ["error", "Échec"]], "Tous les résultats");

  async function refresh() {
    renderSkeletonRows(tbody);
    emptyEl.hidden = true;
    paginationEl.innerHTML = "";
    errorEl.hidden = true;
    renderFilterChips(filterChipsEl, state, filterInputs, clearFilter, resetAllFilters);

    let snapshot;
    try {
      const res = await fetch(`/api/admin/journal?${buildQuery(state)}`, { credentials: "same-origin" });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(payload.error || `Erreur API (${res.status})`);
      snapshot = payload;
    } catch {
      tbody.innerHTML = "";
      errorEl.textContent = "Impossible de charger le journal. Réessaie dans un instant.";
      errorEl.hidden = false;
      return;
    }

    tbody.innerHTML = "";
    if (snapshot.items.length === 0) {
      emptyEl.textContent = EMPTY_LABEL;
      emptyEl.hidden = false;
      return;
    }
    renderRows(tbody, snapshot.items, openDetailModal, COLUMNS.length);
    renderPagination(paginationEl, snapshot, (page) => { state.page = page; refresh(); });
  }

  const debouncedSearch = debounce((value) => { state.search = value; state.page = 1; refresh(); }, SEARCH_DEBOUNCE_MS);
  searchInput.addEventListener("input", (e) => debouncedSearch(e.target.value));
  adminSelect.addEventListener("change", (e) => { state.admin_user_id = e.target.value; state.page = 1; refresh(); });
  providerSelect.addEventListener("change", (e) => { state.provider_id = e.target.value; state.page = 1; refresh(); });
  actionSelect.addEventListener("change", (e) => { state.action = e.target.value; state.page = 1; refresh(); });
  resultSelect.addEventListener("change", (e) => { state.result = e.target.value; state.page = 1; refresh(); });
  dateFromInput.addEventListener("change", (e) => { state.date_from = e.target.value; state.page = 1; refresh(); });
  dateToInput.addEventListener("change", (e) => { state.date_to = e.target.value; state.page = 1; refresh(); });

  exportCsvBtn.addEventListener("click", () => {
    window.location.href = `/api/admin/journal/export.csv?${buildQuery(state)}`;
  });
  exportJsonBtn.addEventListener("click", async () => {
    exportJsonBtn.disabled = true;
    const originalLabel = exportJsonBtn.textContent;
    exportJsonBtn.textContent = "Export en cours…";
    try {
      const res = await fetch(`/api/admin/journal/export.json?${buildQuery(state)}`, { credentials: "same-origin" });
      const payload = await res.json().catch(() => []);
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "journal-ia.json";
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      exportJsonBtn.disabled = false;
      exportJsonBtn.textContent = originalLabel;
    }
  });

  await refresh();
}
