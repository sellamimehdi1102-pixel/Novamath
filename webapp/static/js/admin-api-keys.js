// Rendu partagé de la liste des clés API IA (haute disponibilité) — utilisé
// par /admin/ia (admin-ai.js) ET /admin/settings (admin-settings.js), qui
// affichaient auparavant la même donnée (/api/admin/ai/keys) via deux
// implémentations dupliquées (une en cartes, une en tableau). Ce module ne
// change ni la donnée, ni les endpoints appelés (toujours
// /api/admin/ai/keys/:id, /test, PATCH, DELETE), ni les permissions : la
// capacité "Modifier" (renommer/changer la priorité) reste réservée aux
// appelants qui la demandent explicitement via `allowEdit` — elle n'était
// disponible auparavant que sur /admin/settings (SUPER_ADMIN), jamais sur
// /admin/ia (ADMIN) ; ce module ne l'active donc QUE si l'appelant le
// demande, pour ne strictement rien changer aux droits existants.
//
// La création de clé (formulaire) reste hors de ce module : /admin/ia
// utilise une modale (admin-ai.js::openApiKeyModal), /admin/settings un
// formulaire en ligne — deux UX différentes et volontairement conservées
// telles quelles, seul l'AFFICHAGE de la liste existante est factorisé ici.

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatInt(value) {
  return new Intl.NumberFormat("fr-FR").format(value);
}

function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function formatMs(ms) {
  if (ms === null || ms === undefined) return "—";
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function apiCall(path, { method = "GET", body } = {}) {
  const csrfToken = method !== "GET" ? readCookie("nm_csrf") : null;
  const res = await fetch(path, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    },
    credentials: "same-origin",
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await res.json().catch(() => ({}));
  return { ok: res.ok, payload };
}

// État à 4 valeurs (repris de l'ancienne version /admin/settings, la plus
// précise des deux implémentations d'origine) : une clé active mais dont le
// dernier appel a échoué plus récemment que son dernier succès affiche
// "Erreur" plutôt qu'"Active" — même donnée (last_success_at/last_failure_at),
// juste dérivée plus finement.
export function keyState(row) {
  if (row.in_cooldown) return { label: "Quota atteint (cooldown)", cls: "admin-badge--error" };
  if (!row.enabled) return { label: "Désactivée", cls: "admin-badge--muted" };
  if (row.last_error && (!row.last_success_at || row.last_failure_at > row.last_success_at)) {
    return { label: "Erreur", cls: "admin-badge--error" };
  }
  return { label: "Active", cls: "admin-badge--ok" };
}

function renderRow(tbody, key, { onChanged, allowEdit }) {
  const state = keyState(key);
  const tr = document.createElement("tr");

  tr.appendChild(el("td", "admin-users-td admin-users-td--wrap", key.label));
  tr.appendChild(el("td", "admin-users-td", key.provider_key));
  tr.appendChild(el("td", "admin-users-td admin-users-td--wrap", key.model_name || "—"));

  const stateTd = document.createElement("td");
  stateTd.className = "admin-users-td";
  stateTd.appendChild(el("span", `admin-badge ${state.cls}`, state.label));
  tr.appendChild(stateTd);

  tr.appendChild(el("td", "admin-users-td", String(key.priority)));
  tr.appendChild(el("td", "admin-users-td", formatDateTime(key.last_used_at)));
  tr.appendChild(el("td", "admin-users-td", formatInt(key.request_count)));
  tr.appendChild(el("td", "admin-users-td", formatInt(key.request_count - key.failure_count)));
  tr.appendChild(el("td", "admin-users-td", formatInt(key.failure_count)));
  tr.appendChild(el("td", "admin-users-td", formatInt(key.fallback_count || 0)));
  tr.appendChild(el("td", "admin-users-td", formatMs(key.avg_response_time_ms)));

  const actionsTd = document.createElement("td");
  actionsTd.className = "admin-users-td";
  const actions = el("div", "admin-actions-right");

  const testBtn = el("button", "admin-btn admin-btn--sm", "Tester");
  testBtn.type = "button";
  testBtn.addEventListener("click", async () => {
    testBtn.disabled = true;
    testBtn.textContent = "Test en cours…";
    const { ok, payload } = await apiCall(`/api/admin/ai/keys/${key.id}/test`, { method: "POST" });
    testBtn.disabled = false;
    testBtn.textContent = "Tester";
    if (!ok) { alert(payload.error || "Test impossible."); return; }
    onChanged();
  });
  actions.appendChild(testBtn);

  const toggleBtn = el("button", "admin-btn admin-btn--sm", key.enabled ? "Désactiver" : "Activer");
  toggleBtn.type = "button";
  toggleBtn.addEventListener("click", async () => {
    if (key.enabled && !confirm(`Désactiver la clé « ${key.label} » ?`)) return;
    toggleBtn.disabled = true;
    const { ok, payload } = await apiCall(`/api/admin/ai/keys/${key.id}`, { method: "PATCH", body: { enabled: !key.enabled } });
    toggleBtn.disabled = false;
    if (!ok) { alert(payload.error || "Action impossible."); return; }
    onChanged();
  });
  actions.appendChild(toggleBtn);

  if (allowEdit) {
    const editBtn = el("button", "admin-btn admin-btn--sm", "Modifier");
    editBtn.type = "button";
    editBtn.addEventListener("click", async () => {
      const newLabel = prompt("Nom de la clé :", key.label);
      if (newLabel === null) return;
      const newPriority = prompt("Priorité (0 = la plus haute) :", String(key.priority));
      if (newPriority === null) return;
      editBtn.disabled = true;
      const { ok, payload } = await apiCall(`/api/admin/ai/keys/${key.id}`, {
        method: "PATCH", body: { label: newLabel, priority: Number(newPriority) || 0 },
      });
      editBtn.disabled = false;
      if (!ok) { alert(payload.error || "Modification impossible."); return; }
      onChanged();
    });
    actions.appendChild(editBtn);
  }

  const deleteBtn = el("button", "admin-btn admin-btn--sm admin-btn--danger", "Supprimer");
  deleteBtn.type = "button";
  deleteBtn.addEventListener("click", async () => {
    if (!confirm(`Supprimer la clé « ${key.label} » ? Cette action est irréversible.`)) return;
    deleteBtn.disabled = true;
    const { ok, payload } = await apiCall(`/api/admin/ai/keys/${key.id}`, { method: "DELETE" });
    deleteBtn.disabled = false;
    if (!ok) { alert(payload.error || "Suppression impossible."); return; }
    onChanged();
  });
  actions.appendChild(deleteBtn);

  actionsTd.appendChild(actions);
  tr.appendChild(actionsTd);
  tbody.appendChild(tr);

  if (key.last_error) {
    const errorRow = document.createElement("tr");
    const errorTd = el("td", "admin-users-td admin-users-td--muted admin-users-td--wrap", `Dernière erreur : ${key.last_error}`);
    errorTd.colSpan = COLUMNS.length;
    errorRow.appendChild(errorTd);
    tbody.appendChild(errorRow);
  }
}

const COLUMNS = ["Nom", "Fournisseur", "Modèle principal", "État", "Priorité", "Dernière utilisation", "Requêtes", "Succès", "Échecs", "Bascules", "Latence", "Actions"];

/** Construit (ou réutilise) un tableau complet à l'intérieur de `container`
 * et le peuple avec `keys`. `allowEdit` doit rester exactement ce que
 * l'appelant avait avant ce chantier (voir docstring en tête de fichier). */
export function renderApiKeysTable(container, keys, { onChanged, allowEdit = false, emptyMessage = "Aucune clé API configurée." } = {}) {
  container.innerHTML = "";
  if (!keys.length) {
    container.appendChild(el("p", "admin-empty", emptyMessage));
    return;
  }
  const wrap = el("div", "admin-users-table-wrap");
  const table = document.createElement("table");
  table.className = "admin-users-table";
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  COLUMNS.forEach((label) => headRow.appendChild(el("th", "admin-users-th", label)));
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  keys.forEach((key) => renderRow(tbody, key, { onChanged, allowEdit }));
  table.appendChild(tbody);
  wrap.appendChild(table);
  container.appendChild(wrap);
}
