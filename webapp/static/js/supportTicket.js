// ── Composant Support unique — réutilisé par TOUS les points d'entrée du site
// (chatbot, exercices, cours, Paramètres > Aide). Une seule popup de création
// (openReportTicketPopup), une seule popup "Mes tickets" (openSupportHubPopup),
// une seule popup de détail (openTicketDetailPopup) — jamais quatre formulaires
// différents. N'appelle QUE les routes déjà existantes de support_service.py
// (POST/GET /api/support/tickets, GET .../:id, POST .../:id/messages,
// POST .../:id/satisfaction) : aucune route, aucune logique métier ajoutée ici.
import { api } from "./api.js";
import { openPopup } from "./popup.js";
import { icon } from "./icons.js";

// Dupliqué volontairement depuis support_service.py (même convention que
// admin-support.js/admin-support-ticket.js, qui dupliquent déjà ces libellés
// côté admin) : aucune route n'expose la liste des catégories/statuts.
const CATEGORY_LABELS = {
  bug: "Bug", paiement: "Paiement", ia: "IA", compte: "Compte", technique: "Technique", autre: "Autre",
};
const STATUS_LABELS = { open: "Ouvert", in_progress: "En cours", closed: "Fermé" };
const STATUS_BADGE = { open: "badge--indigo", in_progress: "badge--warning", closed: "badge--neutral" };

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function formatDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

// Toast autonome (page-agnostique, voir api.js::handleQuotaExceeded pour le
// même principe) : ce module est importé depuis chatbot.html/exercice.html/
// cours.html/dashboard.html, aucun ne garantit un #settings-toast existant.
let toastTimer = null;
function toast(message, isError = false) {
  let el = document.getElementById("novamath-support-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "novamath-support-toast";
    document.body.appendChild(el);
  }
  clearTimeout(toastTimer);
  el.className = `toast${isError ? " toast--error" : ""}`;
  el.innerHTML = `${icon(isError ? "x" : "check")}<span>${escapeHtml(message)}</span>`;
  el.hidden = false;
  toastTimer = setTimeout(() => { el.hidden = true; }, 2600);
}

// Le contexte technique (conversation, exercice, cours...) est toujours
// ajouté automatiquement au corps du ticket — l'utilisateur ne saisit jamais
// ces informations lui-même (voir chaque appelant de openReportTicketPopup).
function buildBody(description, contextLines) {
  const lines = (contextLines || []).filter((l) => l.value !== null && l.value !== undefined && l.value !== "");
  let body = description.trim();
  if (lines.length) {
    body += "\n\n---\nContexte technique (ajouté automatiquement)\n";
    body += lines.map((l) => `${l.label} : ${l.value}`).join("\n");
  }
  return body;
}

/**
 * Popup de création — SEUL formulaire de création de ticket du site, ouvert
 * par tous les points d'entrée (chatbot, exercices, cours, Paramètres).
 * @param {Object} opts
 * @param {string} [opts.sourceLabel] - préfixe du sujet auto-généré (ex. "Chatbot", "Exercice").
 * @param {string} [opts.defaultCategory] - catégorie présélectionnée (voir CATEGORY_LABELS).
 * @param {{label: string, value: string}[]} [opts.contextLines] - contexte technique joint automatiquement.
 * @param {() => void} [opts.onCreated] - callback après création réussie (ex. rafraîchir "Mes tickets").
 */
export function openReportTicketPopup({ sourceLabel = "Support", defaultCategory = "autre", contextLines = [], onCreated } = {}) {
  const bodyEl = document.createElement("div");
  bodyEl.innerHTML = `
    <div class="form-field">
      <label for="support-ticket-category">Catégorie</label>
      <select id="support-ticket-category">
        ${Object.entries(CATEGORY_LABELS).map(([value, label]) =>
          `<option value="${value}" ${value === defaultCategory ? "selected" : ""}>${label}</option>`).join("")}
      </select>
    </div>
    <div class="form-field">
      <label for="support-ticket-description">Description</label>
      <textarea id="support-ticket-description" rows="5" placeholder="Décris précisément le problème rencontré..."></textarea>
      <span class="form-error" id="support-ticket-form-error" hidden></span>
    </div>
    ${contextLines.length ? `<p class="form-error form-error--info">Le contexte technique (page, contenu concerné, horodatage...) est joint automatiquement.</p>` : ""}
    <div class="verdict-row">
      <button type="button" class="btn btn-ghost" data-action="cancel">Annuler</button>
      <button type="button" class="btn btn-primary" data-action="submit">Envoyer</button>
    </div>
  `;

  const popup = openPopup({ title: "Signaler un problème", bodyEl, size: "sm" });
  const catEl = bodyEl.querySelector("#support-ticket-category");
  const descEl = bodyEl.querySelector("#support-ticket-description");
  const errEl = bodyEl.querySelector("#support-ticket-form-error");
  const submitBtn = bodyEl.querySelector('[data-action="submit"]');

  bodyEl.querySelector('[data-action="cancel"]').addEventListener("click", () => popup.close());
  submitBtn.addEventListener("click", async () => {
    const description = descEl.value.trim();
    if (!description) {
      errEl.textContent = "Merci de décrire le problème.";
      errEl.hidden = false;
      descEl.focus();
      return;
    }
    errEl.hidden = true;
    submitBtn.disabled = true;
    try {
      const category = catEl.value;
      const subject = `[${sourceLabel}] ${CATEGORY_LABELS[category] || category}`;
      const body = buildBody(description, contextLines);
      await api.supportTicketCreate(subject, category, body);
      popup.close();
      toast("Ticket envoyé — l'équipe support te répondra bientôt.");
      onCreated?.();
    } catch (err) {
      errEl.textContent = err.message || "Impossible d'envoyer le ticket.";
      errEl.hidden = false;
      submitBtn.disabled = false;
    }
  });

  requestAnimationFrame(() => descEl.focus());
  return popup;
}

function ticketRowHtml(ticket) {
  return `
    <button type="button" class="support-ticket-row" data-ticket-id="${ticket.id}">
      <div class="support-ticket-row-main">
        <span class="support-ticket-row-subject">${escapeHtml(ticket.subject)}</span>
        <span class="badge ${STATUS_BADGE[ticket.status] || "badge--neutral"}">${STATUS_LABELS[ticket.status] || ticket.status}</span>
      </div>
      <div class="support-ticket-row-meta">${CATEGORY_LABELS[ticket.category] || ticket.category} · ${formatDateTime(ticket.created_at)}</div>
    </button>
  `;
}

/**
 * Popup "Support" — Mes tickets + Créer un ticket, ouverte depuis Paramètres
 * > Aide (remplace l'ancien popup statique "Nous contacter").
 */
export function openSupportHubPopup() {
  const bodyEl = document.createElement("div");
  const popup = openPopup({ title: "Support", bodyEl, size: "md" });

  async function render() {
    bodyEl.innerHTML = `<p class="support-hub-loading">Chargement de tes tickets…</p>`;
    let tickets;
    try {
      tickets = await api.supportTickets();
    } catch {
      bodyEl.innerHTML = `<p class="form-error">Impossible de charger tes tickets. Réessaie dans un instant.</p>`;
      return;
    }
    bodyEl.innerHTML = `
      <div class="support-hub-header">
        <span class="support-hub-title">Mes tickets</span>
        <button type="button" class="btn btn-primary btn-sm" data-action="new-ticket">${icon("flag")} Créer un ticket</button>
      </div>
      ${tickets.length
        ? `<div class="support-ticket-list">${tickets.map(ticketRowHtml).join("")}</div>`
        : `<p class="support-hub-empty">Tu n'as encore créé aucun ticket.</p>`}
    `;
    bodyEl.querySelector('[data-action="new-ticket"]').addEventListener("click", () => {
      openReportTicketPopup({ sourceLabel: "Paramètres", onCreated: render });
    });
    bodyEl.querySelectorAll("[data-ticket-id]").forEach((row) => {
      row.addEventListener("click", () => openTicketDetailPopup(Number(row.dataset.ticketId), render));
    });
  }

  render();
  return popup;
}

function renderThread(container, messages) {
  container.innerHTML = messages.map((m) => `
    <div class="support-ticket-msg support-ticket-msg--${m.author_type}">
      <div class="support-ticket-msg-meta">${m.author_type === "admin" ? "Équipe NovaMath" : "Toi"} · ${formatDateTime(m.created_at)}</div>
      <p class="support-ticket-msg-body">${escapeHtml(m.body)}</p>
      ${m.attachments.length ? `<div class="support-ticket-msg-attachments">${m.attachments.map((a) =>
        `<a href="/api/support/attachments/${a.id}" target="_blank" rel="noopener">${icon("paperclip")} ${escapeHtml(a.filename)}</a>`).join("")}</div>` : ""}
    </div>
  `).join("");
}

function satisfactionHtml() {
  return `
    <div class="support-ticket-satisfaction">
      <p>Ce ticket est résolu — comment évalues-tu la réponse ?</p>
      <div class="support-ticket-stars">
        ${[1, 2, 3, 4, 5].map((n) => `<button type="button" class="support-ticket-star-btn" data-rating="${n}" aria-label="${n}/5">${icon("star")}</button>`).join("")}
      </div>
    </div>
  `;
}

/**
 * Popup de détail — fil de conversation, réponse (+ pièces jointes), note de
 * satisfaction si le ticket est fermé. Réutilise exactement les routes déjà
 * exposées par support_service.py côté utilisateur.
 */
export function openTicketDetailPopup(ticketId, onChange) {
  const bodyEl = document.createElement("div");
  bodyEl.innerHTML = `<p class="support-hub-loading">Chargement…</p>`;
  const popup = openPopup({ title: `Ticket #${ticketId}`, bodyEl, size: "md" });

  async function refresh() {
    let ticket;
    try {
      ticket = await api.supportTicketDetail(ticketId);
    } catch {
      bodyEl.innerHTML = `<p class="form-error">Ce ticket est introuvable.</p>`;
      return;
    }
    bodyEl.innerHTML = `
      <p class="support-ticket-detail-meta">
        <span class="badge ${STATUS_BADGE[ticket.status] || "badge--neutral"}">${STATUS_LABELS[ticket.status] || ticket.status}</span>
        ${CATEGORY_LABELS[ticket.category] || ticket.category} · créé le ${formatDateTime(ticket.created_at)}
      </p>
      <div class="support-ticket-thread" id="support-ticket-thread"></div>
      ${ticket.status !== "closed" ? `
        <form class="support-ticket-reply-form" id="support-ticket-reply-form">
          <div class="form-field">
            <label for="support-ticket-reply-body">Répondre</label>
            <textarea id="support-ticket-reply-body" rows="3" placeholder="Écris ta réponse..."></textarea>
          </div>
          <div class="verdict-row">
            <label class="btn btn-ghost btn-sm support-ticket-attach-btn">
              ${icon("paperclip")} Joindre un fichier
              <input type="file" id="support-ticket-reply-files" multiple hidden>
            </label>
            <button type="submit" class="btn btn-primary btn-sm">Envoyer</button>
          </div>
        </form>
      ` : ticket.satisfaction_rating
        ? `<p class="support-ticket-satisfaction-done">${icon("starFilled")} Tu as noté ce ticket ${ticket.satisfaction_rating}/5.</p>`
        : satisfactionHtml()}
    `;
    renderThread(bodyEl.querySelector("#support-ticket-thread"), ticket.messages);

    const form = bodyEl.querySelector("#support-ticket-reply-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const textarea = form.querySelector("#support-ticket-reply-body");
        const body = textarea.value.trim();
        if (!body) return;
        const filesInput = form.querySelector("#support-ticket-reply-files");
        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        try {
          await api.supportTicketAddMessage(ticketId, body, Array.from(filesInput.files || []));
          onChange?.();
          await refresh();
        } catch (err) {
          submitBtn.disabled = false;
          toast(err.message || "Impossible d'envoyer la réponse.", true);
        }
      });
    }
    bodyEl.querySelectorAll("[data-rating]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await api.supportTicketSatisfaction(ticketId, Number(btn.dataset.rating));
          onChange?.();
          await refresh();
        } catch (err) {
          toast(err.message || "Impossible d'enregistrer la note.", true);
        }
      });
    });
  }

  refresh();
  return popup;
}
