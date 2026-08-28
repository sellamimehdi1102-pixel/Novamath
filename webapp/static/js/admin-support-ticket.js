// Fiche ticket (/admin/support/:id) — conversation complète, pièces
// jointes, notes internes, historique, changement de statut, assignation,
// réponse rapide (voir support_service.py). Une seule API par action
// (jamais un agrégat unique modifiable en un clic) — même philosophie que
// admin-ai.js pour les actions ponctuelles (test/health-check).
import { priorityBadge } from "./admin-support.js";
import { fetchTeamMembers } from "./admin-team-roles.js";

const STATUS_LABELS = { open: "Ouvert", in_progress: "En cours", closed: "Fermé" };

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

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

function readCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function apiJson(path, { method = "GET", body } = {}) {
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
  return { ok: res.ok, status: res.status, payload };
}

// Priorité (déjà visible dans la liste, ajoutée ici pour comprendre le
// ticket sans revenir en arrière), note de satisfaction et délai de première
// réponse (produits mais jamais affichés avant ce chantier — voir
// support_service.get_ticket_detail). `closed_at` n'est volontairement pas
// répété ici : déjà visible dans l'Historique ("Statut changé → Fermé").
function renderHead(container, ticket) {
  container.innerHTML = "";
  container.appendChild(el("h1", null, `#${ticket.id} — ${ticket.subject}`));
  const sub = el("p", "admin-page-lead",
    `${ticket.user_pseudo} (${ticket.user_email}) — ${ticket.category_label} — créé le ${formatDateTime(ticket.created_at)}`);
  container.appendChild(sub);

  const meta = el("div", "admin-user-profile-badges");
  meta.appendChild(priorityBadge(ticket.priority));
  if (ticket.first_admin_response_at) {
    meta.appendChild(el("span", "admin-badge admin-badge--neutral", `1ère réponse : ${formatDateTime(ticket.first_admin_response_at)}`));
  }
  if (ticket.satisfaction_rating) {
    meta.appendChild(el("span", "admin-badge admin-badge--ok", `Satisfaction : ${ticket.satisfaction_rating}/5`));
  }
  container.appendChild(meta);
}

function renderMessages(container, messages) {
  container.innerHTML = "";
  if (!messages.length) {
    container.appendChild(el("p", "admin-empty", "Aucun message dans cette conversation."));
    return;
  }
  messages.forEach((msg) => {
    const block = el("div", `admin-support-message admin-support-message--${msg.author_type}`);
    const meta = el("div", "admin-support-message-meta",
      `${msg.author_type === "admin" ? "Administrateur" : "Utilisateur"} — ${formatDateTime(msg.created_at)}`);
    block.appendChild(meta);
    block.appendChild(el("p", "admin-support-message-body", msg.body));
    if (msg.attachments.length) {
      const list = el("ul", "admin-unavailable-list");
      msg.attachments.forEach((att) => {
        const li = el("li", "admin-unavailable-item");
        const link = document.createElement("a");
        link.href = `/api/admin/support/attachments/${att.id}`;
        link.textContent = `📎 ${att.filename} (${formatSize(att.size_bytes)})`;
        li.appendChild(link);
        list.appendChild(li);
      });
      block.appendChild(list);
    }
    container.appendChild(block);
  });
}

function renderNotes(container, notes) {
  container.innerHTML = "";
  if (!notes.length) {
    container.appendChild(el("li", "admin-unavailable-item", "Aucune note interne pour ce ticket."));
    return;
  }
  notes.forEach((note) => {
    container.appendChild(el("li", "admin-unavailable-item", `${formatDateTime(note.created_at)} — ${note.body}`));
  });
}

const HISTORY_EVENT_LABELS = {
  status_changed: (h) => `Statut changé : ${STATUS_LABELS[h.from_value] || h.from_value} → ${STATUS_LABELS[h.to_value] || h.to_value}`,
  assigned: (h) => (h.to_value ? `Ticket assigné (administrateur #${h.to_value})` : "Ticket désassigné"),
};

function renderHistory(container, history) {
  container.innerHTML = "";
  if (!history.length) {
    container.appendChild(el("li", "admin-unavailable-item", "Aucun changement enregistré pour ce ticket."));
    return;
  }
  history.forEach((h) => {
    const describe = HISTORY_EVENT_LABELS[h.event_type] || ((x) => x.event_type);
    container.appendChild(el("li", "admin-unavailable-item", `${formatDateTime(h.created_at)} — ${describe(h)}`));
  });
}

export async function loadSupportTicketDetail(ticketId) {
  const headEl = document.getElementById("admin-support-ticket-head");
  const messagesEl = document.getElementById("admin-support-ticket-messages");
  const notesEl = document.getElementById("admin-support-ticket-notes-list");
  const historyEl = document.getElementById("admin-support-ticket-history-list");
  const statusSelect = document.getElementById("admin-support-ticket-status-select");
  const assignSelect = document.getElementById("admin-support-ticket-assign-select");
  const replyForm = document.getElementById("admin-support-ticket-reply-form");
  const replyBody = document.getElementById("admin-support-ticket-reply-body");
  const replyFiles = document.getElementById("admin-support-ticket-reply-files");
  const noteForm = document.getElementById("admin-support-ticket-note-form");
  const noteBody = document.getElementById("admin-support-ticket-note-body");
  const errorEl = document.getElementById("admin-global-error");

  errorEl.hidden = true;

  async function refresh() {
    const res = await fetch(`/api/admin/support/tickets/${ticketId}`, { credentials: "same-origin" });
    if (!res.ok) {
      errorEl.hidden = false;
      errorEl.textContent = "Impossible de charger ce ticket. Réessaie dans un instant.";
      return null;
    }
    const ticket = await res.json();
    renderHead(headEl, ticket);
    renderMessages(messagesEl, ticket.messages);
    renderNotes(notesEl, ticket.notes);
    renderHistory(historyEl, ticket.history);

    statusSelect.innerHTML = "";
    Object.entries(STATUS_LABELS).forEach(([value, label]) => statusSelect.appendChild(new Option(label, value)));
    statusSelect.value = ticket.status;

    assignSelect.value = ticket.assigned_admin_id ? String(ticket.assigned_admin_id) : "";
    return ticket;
  }

  // Liste des administrateurs assignables (rôles d'équipe) — factorisée dans
  // admin-team-roles.js (partagée avec admin-support.js).
  try {
    const admins = await fetchTeamMembers();
    assignSelect.innerHTML = "";
    assignSelect.appendChild(new Option("Non assigné", ""));
    admins.forEach((name, id) => assignSelect.appendChild(new Option(name, String(id))));
  } catch {
    assignSelect.innerHTML = "";
    assignSelect.appendChild(new Option("Liste indisponible", ""));
  }

  await refresh();

  statusSelect.addEventListener("change", async (e) => {
    const { ok, payload } = await apiJson(`/api/admin/support/tickets/${ticketId}/status`, {
      method: "PATCH", body: { status: e.target.value },
    });
    if (!ok) alert(payload.error || "Impossible de changer le statut.");
    await refresh();
  });

  assignSelect.addEventListener("change", async (e) => {
    const { ok, payload } = await apiJson(`/api/admin/support/tickets/${ticketId}/assign`, {
      method: "PATCH", body: { admin_id: e.target.value || null },
    });
    if (!ok) alert(payload.error || "Impossible de changer l'assignation.");
    await refresh();
  });

  replyForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = replyBody.value.trim();
    if (!body) return;
    const formData = new FormData();
    formData.set("body", body);
    Array.from(replyFiles.files || []).forEach((file) => formData.append("attachments", file));
    const csrfToken = readCookie("nm_csrf");
    const res = await fetch(`/api/admin/support/tickets/${ticketId}/messages`, {
      method: "POST",
      headers: csrfToken ? { "X-CSRF-Token": csrfToken } : {},
      credentials: "same-origin",
      body: formData,
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      alert(payload.error || "Impossible d'envoyer la réponse.");
      return;
    }
    replyBody.value = "";
    replyFiles.value = "";
    await refresh();
  });

  noteForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = noteBody.value.trim();
    if (!body) return;
    const { ok, payload } = await apiJson(`/api/admin/support/tickets/${ticketId}/notes`, {
      method: "POST", body: { body },
    });
    if (!ok) {
      alert(payload.error || "Impossible d'ajouter la note.");
      return;
    }
    noteBody.value = "";
    await refresh();
  });
}
