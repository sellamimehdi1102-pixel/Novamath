import { api, handleQuotaExceeded } from "./api.js";
import { initSettingsManager } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { bindLiveTranslations, t } from "./i18n.js";
import { setRenderedHtmlContent } from "./mathrender.js";
import { initMentions } from "./chatbot-mentions.js";
import * as composer from "./chatbot-composer.js";
import { openPromptPopup, openConfirmPopup } from "./popup.js";
import { getStoredClassLevel } from "./curriculumSelector.js";
import { featureLabel } from "./features.js";
import { openReportTicketPopup } from "./supportTicket.js";
import { ICONS } from "./icons.js";
import { mountGuestLockOverlay } from "./guestLockOverlay.js";

initSettingsManager().then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));

const $ = (id) => document.getElementById(id);
const convoList = $("chatbot-convo-list");
const messagesEl = $("chatbot-messages");
const emptyState = $("chatbot-empty-state");
const input = $("chatbot-input");
const sendBtn = $("chatbot-send-btn");
const topbarTitle = $("chatbot-topbar-title");
const quotaIndicator = $("chatbot-quota-indicator");
const quotaValue = $("chatbot-quota-value");
const emptyGreeting = $("chatbot-empty-greeting");
const liveSuggestions = $("chatbot-live-suggestions");
const providerBanner = $("chatbot-provider-banner");
const providerBannerMsg = $("chatbot-provider-banner-msg");
const convosAside = $("chatbot-convos");
const convosCollapseBtn = $("chatbot-convos-collapse-btn");
const convosMobileTrigger = $("chatbot-convos-mobile-trigger");
const convosOverlay = $("chatbot-convos-overlay");

let conversations = [];
let activeConversationId = null;
let activeMessages = [];
let abortController = null;
let isStreaming = false;
let mentionsController = null;

// Réglage "Streaming" (Paramètres → Chatbot) : jusqu'ici purement décoratif,
// jamais lu côté frontend — désormais désactive réellement l'effet machine
// à écrire (la réponse s'affiche d'un bloc dès qu'elle est complète).
let chatbotStreamingEnabled = true;
async function refreshChatbotStreamingSetting() {
  try {
    const settings = await api.getSettings();
    chatbotStreamingEnabled = settings?.chatbot?.streaming !== false;
  } catch {
    /* silencieux : garde la dernière valeur connue */
  }
}

// ── Sidebar conversations rétractable (desktop) + drawer (mobile) ───────────
const CONVOS_COLLAPSED_KEY = "novamath:chatbotConvosCollapsed";
const MOBILE_BREAKPOINT = 860;
const isMobile = () => window.innerWidth <= MOBILE_BREAKPOINT;

function setConvosCollapsed(collapsed) {
  convosAside.classList.toggle("is-collapsed", collapsed);
  convosCollapseBtn.setAttribute("aria-expanded", String(!collapsed));
  convosCollapseBtn.setAttribute("aria-label", collapsed ? "Développer les conversations" : "Réduire les conversations");
  localStorage.setItem(CONVOS_COLLAPSED_KEY, collapsed ? "1" : "0");
}

function openConvosDrawer() {
  convosAside.classList.add("is-open");
  convosOverlay.classList.add("is-visible");
}

function closeConvosDrawer() {
  convosAside.classList.remove("is-open");
  convosOverlay.classList.remove("is-visible");
}

if (!isMobile()) {
  setConvosCollapsed(localStorage.getItem(CONVOS_COLLAPSED_KEY) === "1");
}
convosCollapseBtn.addEventListener("click", () => {
  if (isMobile()) {
    if (convosAside.classList.contains("is-open")) closeConvosDrawer();
    else openConvosDrawer();
  } else {
    setConvosCollapsed(!convosAside.classList.contains("is-collapsed"));
  }
});
convosMobileTrigger.addEventListener("click", openConvosDrawer);
convosOverlay.addEventListener("click", closeConvosDrawer);
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeConvosDrawer();
});
window.addEventListener("resize", () => {
  if (!isMobile()) closeConvosDrawer();
});

// ── Rendu Markdown + KaTeX (réutilise mathrender.js, comme le reste du site) ─
// marked.parse() produit le HTML final (blocs de code, tableaux, listes,
// liens, citations) : on ne le modifie plus jamais après coup (cf. audit —
// l'ancien prettify() post-traitement corrompait les blocs <code>). Si le
// CDN marked venait à manquer, le texte est échappé (pas de risque d'injection
// HTML) puis les retours à la ligne sont conservés comme <br>.
// setRenderedHtmlContent neutralise le HTML dangereux (voir mathrender.js::
// sanitizeChatHtml) avant de l'injecter dans le DOM — nécessaire ici car
// marked ne le fait pas lui-même.
function renderMessageBody(el, rawText) {
  const html = window.marked
    ? window.marked.parse(rawText || "")
    : escapeHtml(rawText || "").replace(/\n/g, "<br>");
  setRenderedHtmlContent(el, html);
}

// ── Scroll intelligent (façon ChatGPT/Claude) ───────────────────────────────
// L'auto-scroll ne force la position que si l'utilisateur est déjà en bas ;
// sinon un bouton flottant apparaît plutôt que de le ramener de force pendant
// qu'il relit un message précédent (cf. audit chatbot, priorité n°1).
const SCROLL_BOTTOM_THRESHOLD = 80;
const scrollBottomBtn = $("chatbot-scroll-bottom-btn");

function isNearBottom() {
  return messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < SCROLL_BOTTOM_THRESHOLD;
}

function showScrollBottomBtn() {
  scrollBottomBtn.hidden = false;
  requestAnimationFrame(() => scrollBottomBtn.classList.add("is-visible"));
}

function hideScrollBottomBtn() {
  scrollBottomBtn.classList.remove("is-visible");
  scrollBottomBtn.hidden = true;
}

// Force la position en bas — réservé aux actions explicites de l'utilisateur
// (envoi d'un message, ouverture/changement de conversation).
function forceScrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
  hideScrollBottomBtn();
}

// À utiliser pendant le streaming : ne scrolle que si l'utilisateur était
// déjà en bas *avant* que le nouveau contenu n'agrandisse la zone.
function autoScrollIfNearBottom(wasNearBottom) {
  if (wasNearBottom) {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  } else {
    showScrollBottomBtn();
  }
}

messagesEl.addEventListener("scroll", () => {
  if (isNearBottom()) hideScrollBottomBtn();
});
scrollBottomBtn.addEventListener("click", () => forceScrollToBottom());

// ── Conversations (sidebar gauche) ──────────────────────────────────────────
async function loadConversations(search) {
  const { conversations: list } = await api.chatbotConversations(search);
  conversations = list;
  renderConvoList();
}

function renderConvoList() {
  if (!conversations.length) {
    convoList.innerHTML = `<div class="chatbot-convo-empty">Aucune conversation pour l'instant.</div>`;
    return;
  }
  convoList.innerHTML = conversations.map((c) => `
    <div class="chatbot-convo-item${c.id === activeConversationId ? " active" : ""}" data-id="${c.id}">
      ${c.pinned ? '<svg class="pin-icon" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1"><path d="M12 17v5M8 3h8l-1 6 3 3v2H6v-2l3-3-1-6Z"/></svg>' : ""}
      <span class="chatbot-convo-title">${escapeHtml(c.title)}</span>
      <div class="chatbot-convo-actions">
        <button data-action="pin" title="${c.pinned ? "Désépingler" : "Épingler"}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 17v5M8 3h8l-1 6 3 3v2H6v-2l3-3-1-6Z"/></svg></button>
        <button data-action="rename" title="Renommer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"/><path d="M18.4 2.6a2 2 0 1 1 2.8 2.8L12 14.6 8 15.6 9 11.6l9.4-9Z"/></svg></button>
        <button data-action="delete" title="Supprimer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6"/></svg></button>
      </div>
    </div>
  `).join("");

  convoList.querySelectorAll(".chatbot-convo-item").forEach((item) => {
    const id = Number(item.dataset.id);
    item.addEventListener("click", (e) => {
      if (e.target.closest("[data-action]")) return;
      selectConversation(id);
    });
    item.querySelector('[data-action="pin"]').addEventListener("click", async (e) => {
      e.stopPropagation();
      const conv = conversations.find((c) => c.id === id);
      await api.chatbotPinConversation(id, !conv.pinned);
      await loadConversations();
    });
    item.querySelector('[data-action="rename"]').addEventListener("click", async (e) => {
      e.stopPropagation();
      const conv = conversations.find((c) => c.id === id);
      const title = await openPromptPopup({
        title: "Renommer la conversation",
        label: "Nouveau titre",
        defaultValue: conv.title,
        confirmLabel: "Renommer",
      });
      if (title && title.trim()) {
        await api.chatbotRenameConversation(id, title.trim());
        await loadConversations();
        if (id === activeConversationId) topbarTitle.textContent = title.trim();
      }
    });
    item.querySelector('[data-action="delete"]').addEventListener("click", async (e) => {
      e.stopPropagation();
      const confirmed = await openConfirmPopup({
        title: "Supprimer la conversation",
        message: "Cette conversation sera définitivement supprimée. Cette action est irréversible.",
        confirmLabel: "Supprimer",
        danger: true,
      });
      if (!confirmed) return;
      await api.chatbotDeleteConversation(id);
      if (id === activeConversationId) {
        activeConversationId = null;
        activeMessages = [];
        renderMessages();
      }
      await loadConversations();
    });
  });
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

async function selectConversation(id) {
  activeConversationId = id;
  const conv = conversations.find((c) => c.id === id);
  topbarTitle.textContent = conv ? conv.title : "Nouvelle conversation";
  renderConvoList();
  closeConvosDrawer();
  messagesEl.classList.add("is-switching");
  const { messages } = await api.chatbotMessages(id);
  activeMessages = messages;
  renderMessages();
  requestAnimationFrame(() => messagesEl.classList.remove("is-switching"));
}

$("chatbot-new-btn").addEventListener("click", async () => {
  activeConversationId = null;
  activeMessages = [];
  topbarTitle.textContent = "Nouvelle conversation";
  renderMessages();
  renderConvoList();
  input.focus();
});

let searchTimer = null;
$("chatbot-search-input").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadConversations(e.target.value.trim() || undefined), 250);
});

// ── Rendu des messages ──────────────────────────────────────────────────────
function messageActionsHtml(msg) {
  // Tant que le message n'a pas d'id (placeholder en cours de génération,
  // ou tour en cours de réessai), aucune action n'a de sens : copier un
  // texte vide, régénérer/aimer un message pas encore persisté échoueraient
  // silencieusement (l'id n'existe pas encore côté serveur). On les
  // désactive dès le rendu plutôt que de laisser un clic sans effet visible.
  const dis = msg.id ? "" : "disabled";
  return `
    <div class="chatbot-msg-actions">
      <button data-action="copy" title="Copier" aria-label="Copier la réponse" ${dis}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2v14a2 2 0 0 0 2 2h14M18 22V8a2 2 0 0 0-2-2H2"/></svg></button>
      <button data-action="regenerate" title="Régénérer" aria-label="Régénérer la réponse" ${dis}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 1 3 6.7"/><path d="M3 12V6M3 12h6"/></svg></button>
      <button data-action="continue" title="Continuer" aria-label="Continuer la réponse" ${dis}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
      <button data-action="like" title="J'aime" aria-label="J'aime cette réponse" aria-pressed="${msg.liked === 1}" class="${msg.liked === 1 ? "active" : ""}" ${dis}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 22V11l5-8 1 1v6h6l-2 12H7Z"/></svg></button>
      <button data-action="dislike" title="Je n'aime pas" aria-label="Je n'aime pas cette réponse" aria-pressed="${msg.liked === 0}" class="${msg.liked === 0 ? "active" : ""}" ${dis}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="transform:rotate(180deg)"><path d="M7 22V11l5-8 1 1v6h6l-2 12H7Z"/></svg></button>
      <button data-action="export-md" title="Exporter Markdown" aria-label="Exporter la réponse en Markdown" ${dis}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12m0 0 4-4m-4 4-4-4"/><path d="M4 19h16"/></svg></button>
      <button data-action="export-pdf" title="Exporter PDF" aria-label="Exporter la réponse en PDF" ${dis}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"/><path d="M14 2v6h6"/></svg></button>
      <button data-action="report" title="Signaler un problème" aria-label="Signaler un problème avec cette réponse" ${dis}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="3"/></svg></button>
    </div>`;
}

// preserveScroll: true respecte la position de lecture de l'utilisateur
// (utilisé après la fin d'un streaming) ; false force le bas (nouvelle
// conversation, changement de conversation).
function renderMessages({ preserveScroll = false } = {}) {
  const wasNearBottom = preserveScroll ? isNearBottom() : true;
  emptyState.hidden = activeMessages.length > 0;
  messagesEl.innerHTML = "";
  if (!activeMessages.length) {
    messagesEl.appendChild(emptyState);
    return;
  }
  activeMessages.forEach((msg) => appendMessageEl(msg));
  autoScrollIfNearBottom(wasNearBottom);
}

// ── Cartes d'action (Phase C) : proposées par le backend en fin de réponse,
// jamais devinées côté frontend — voir chatbot/services/action_cards_service.py.
const ACTION_CARD_ICONS = {
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
};

function actionCardsHtml(cards) {
  if (!cards || !cards.length) return "";
  return `<div class="chatbot-action-cards">${cards.map((c, i) => `
    <button type="button" class="chatbot-action-card card card--interactive" data-card-index="${i}">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${ACTION_CARD_ICONS[c.icon] || ACTION_CARD_ICONS.book}</svg>
      <span>${escapeHtml(t(c.label_key, c.title || ""))}</span>
    </button>
  `).join("")}</div>`;
}

function navigateToCard(card) {
  if (card.type === "notion_series") {
    localStorage.setItem(
      "lumis:pending_series",
      JSON.stringify({
        mode: "notion",
        chapterId: card.chapter_id,
        notion: card.notion,
        notions: [card.notion],
        exerciseIds: card.exercise_ids,
      })
    );
    window.location.href = "exercice.html";
    return;
  }
  if (card.url) window.location.href = card.url;
}

function bindActionCards(row, cards) {
  row.querySelectorAll(".chatbot-action-card").forEach((btn) => {
    btn.addEventListener("click", () => navigateToCard(cards[Number(btn.dataset.cardIndex)]));
  });
}

// Deux structures DOM distinctes, pas une seule structure partagée
// re-coloriée en CSS : le message utilisateur est un simple conteneur
// `justify-content: flex-end` contenant SA bulle (aucun avatar dans le DOM,
// jamais seulement masqué), le message assistant est un conteneur
// `justify-content: flex-start` avec avatar + colonne (bulle, actions,
// cartes). Chaque rôle a sa propre classe de bulle (`--user`/`--assistant`)
// pour que la couleur/l'alignement ne dépendent d'aucun sélecteur composé
// fragile (ex. un `flex-direction: row-reverse` combiné à un
// `justify-content`, plus difficile à auditer qu'un `flex-end` direct).
function appendMessageEl(msg) {
  const row = document.createElement("div");
  row.dataset.id = msg.id || "";

  if (msg.role === "user") {
    row.className = "chatbot-msg-row chatbot-msg-row--user";
    row.innerHTML = `<div class="chatbot-msg-bubble chatbot-msg-bubble--user"></div>`;
  } else {
    row.className = "chatbot-msg-row chatbot-msg-row--assistant";
    row.innerHTML = `
      <div class="chatbot-msg-avatar" aria-hidden="true">NM</div>
      <div class="chatbot-msg-col">
        <div class="chatbot-msg-bubble chatbot-msg-bubble--assistant"></div>
        ${messageActionsHtml(msg)}
        ${actionCardsHtml(msg.cards)}
      </div>
    `;
  }

  renderMessageBody(row.querySelector(".chatbot-msg-bubble"), msg.content);
  if (msg.role === "assistant") {
    bindMessageActions(row, msg);
    if (msg.cards?.length) bindActionCards(row, msg.cards);
  }
  messagesEl.appendChild(row);
  return row;
}

const COPY_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2v14a2 2 0 0 0 2 2h14M18 22V8a2 2 0 0 0-2-2H2"/></svg>';
const COPIED_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>';
const COPY_FEEDBACK_MS = 1600;

function bindMessageActions(row, msg) {
  row.querySelector('[data-action="copy"]')?.addEventListener("click", (e) => {
    const btn = e.currentTarget;
    if (btn.dataset.copying) return; // déjà en cours d'affichage du "Copié !"
    navigator.clipboard.writeText(msg.content || "");
    btn.dataset.copying = "1";
    btn.innerHTML = COPIED_ICON;
    btn.classList.add("is-copied");
    btn.setAttribute("aria-label", "Réponse copiée");
    btn.setAttribute("title", "Copié !");
    setTimeout(() => {
      btn.innerHTML = COPY_ICON;
      btn.classList.remove("is-copied");
      btn.setAttribute("aria-label", "Copier la réponse");
      btn.setAttribute("title", "Copier");
      delete btn.dataset.copying;
    }, COPY_FEEDBACK_MS);
  });
  row.querySelector('[data-action="regenerate"]')?.addEventListener("click", () => regenerate());
  row.querySelector('[data-action="continue"]')?.addEventListener("click", () => sendMessage("Continue."));
  row.querySelector('[data-action="like"]')?.addEventListener("click", async () => {
    const newVal = msg.liked === 1 ? null : 1;
    msg.liked = newVal;
    await api.chatbotFeedback(msg.id, newVal);
    renderMessages({ preserveScroll: true });
  });
  row.querySelector('[data-action="dislike"]')?.addEventListener("click", async () => {
    const newVal = msg.liked === 0 ? null : 0;
    msg.liked = newVal;
    await api.chatbotFeedback(msg.id, newVal);
    renderMessages({ preserveScroll: true });
  });
  row.querySelector('[data-action="export-md"]')?.addEventListener("click", () => {
    const blob = new Blob([msg.content || ""], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "reponse-mathadap.md";
    a.click();
  });
  row.querySelector('[data-action="export-pdf"]')?.addEventListener("click", () => window.print());
  row.querySelector('[data-action="report"]')?.addEventListener("click", () => {
    const index = activeMessages.indexOf(msg);
    let userMessage = "";
    for (let i = index - 1; i >= 0; i -= 1) {
      if (activeMessages[i].role === "user") { userMessage = activeMessages[i].content || ""; break; }
    }
    // Provider/modèle ne sont jamais transmis au frontend par design — le
    // contexte joint au ticket se limite donc à ce que ce module connaît
    // réellement côté client.
    openReportTicketPopup({
      sourceLabel: "Chatbot",
      defaultCategory: "ia",
      contextLines: [
        { label: "Conversation", value: activeConversationId },
        { label: "Message utilisateur", value: userMessage },
        { label: "Réponse IA", value: msg.content || "" },
        { label: "Horodatage", value: new Date().toISOString() },
      ],
    });
  });
}

// ── Streaming ────────────────────────────────────────────────────────────────
function setStreamingUI(streaming) {
  isStreaming = streaming;
  sendBtn.classList.toggle("is-stop", streaming);
  sendBtn.disabled = !streaming && composer.isEmpty(input);
  sendBtn.innerHTML = streaming
    ? '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>'
    : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
  // "Régénérer"/"Continuer" sur un message déjà persisté ne peuvent rien
  // faire tant qu'une génération est en cours ailleurs dans la conversation
  // (regenerate()/sendMessage() l'ignoreraient silencieusement) — le rendre
  // visuellement explicite plutôt que de laisser un clic sans effet.
  messagesEl.querySelectorAll('[data-action="regenerate"], [data-action="continue"]').forEach((btn) => {
    btn.disabled = streaming;
  });
}

// Affiche le texte progressivement (effet machine à écrire) plutôt que par
// à-coups au rythme des deltas SSE : les deltas remplissent un buffer, un
// intervalle local le "consomme" par petits groupes de caractères pour
// rester fluide même quand le réseau livre de gros blocs de texte d'un coup.
const TYPEWRITER_INTERVAL_MS = 15;
const TYPEWRITER_CHARS_PER_TICK = 2;

function startTypewriter(bubbleEl) {
  bubbleEl.classList.add("is-streaming");

  if (!chatbotStreamingEnabled) {
    // Streaming désactivé (Paramètres → Chatbot) : pas d'effet machine à
    // écrire, la réponse s'affiche d'un bloc une fois entièrement reçue.
    let target = "";
    return {
      push(text) { target += text; },
      finish(callback) {
        const wasNearBottom = isNearBottom();
        bubbleEl.classList.remove("is-streaming");
        renderMessageBody(bubbleEl, target);
        autoScrollIfNearBottom(wasNearBottom);
        callback(target);
      },
    };
  }

  let shown = "";
  let target = "";
  let doneReceiving = false;
  let onFullyDone = null;

  const timer = setInterval(() => {
    if (shown.length < target.length) {
      const wasNearBottom = isNearBottom();
      shown = target.slice(0, shown.length + TYPEWRITER_CHARS_PER_TICK);
      renderMessageBody(bubbleEl, shown);
      autoScrollIfNearBottom(wasNearBottom);
    } else if (doneReceiving) {
      clearInterval(timer);
      bubbleEl.classList.remove("is-streaming");
      onFullyDone?.(shown);
    }
  }, TYPEWRITER_INTERVAL_MS);

  return {
    push(text) { target += text; },
    finish(callback) { doneReceiving = true; onFullyDone = callback; },
  };
}

async function consumeStream(response, bubbleEl, onDone) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let fullText = "";
  const typewriter = startTypewriter(bubbleEl);
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    for (const part of parts) {
      const line = part.replace(/^data: /, "").trim();
      if (!line) continue;
      let payload;
      try {
        payload = JSON.parse(line);
      } catch (parseErr) {
        continue;
      }
      if (payload.delta) {
        fullText += payload.delta;
        typewriter.push(payload.delta);
      } else if (payload.quota_exceeded) {
        // Course concurrente résiduelle (voir server.py::peek_exceeded) : le
        // contrôle préalable était passé, mais la consommation réelle a
        // finalement échoué une fois le flux déjà ouvert (donc plus moyen de
        // répondre par un vrai 429 — en-têtes déjà envoyés). Jamais l'erreur
        // brute dans la bulle : même toast + redirection que le cas normal
        // (429 avant ouverture du flux, voir api.js::handleQuotaExceeded), et
        // le message utilisateur affiché n'est pas encore persisté côté
        // serveur (vérifié avant tout appel LLM) — pas de refetch, qui le
        // ferait disparaître à tort.
        handleQuotaExceeded(payload);
        const notice = "\n\n*Tu as atteint ta limite de messages aujourd'hui — redirection vers la page Abonnement…*";
        fullText += notice;
        typewriter.push(notice);
        typewriter.finish(() => {});
      } else if (payload.error) {
        // Erreur SSE "propre" (le serveur a répondu, pas une coupure réseau) :
        // aucun événement `done` ne suit jamais dans ce cas (cf. server.py),
        // donc il faut finaliser le typewriter ici, sinon son intervalle
        // tourne indéfiniment (curseur clignotant à vie).
        fullText += `\n\n*⚠️ ${payload.error}*`;
        typewriter.push(`\n\n*⚠️ ${payload.error}*`);
        if (payload.provider_down) {
          providerBannerMsg.textContent = payload.error;
          providerBanner.hidden = false;
        }
        typewriter.finish(() => onDone(fullText));
      } else if (payload.done) {
        typewriter.finish(() => onDone(fullText));
      }
    }
  }
}

async function ensureConversation() {
  if (activeConversationId) return activeConversationId;
  const { conversation } = await api.chatbotCreateConversation();
  activeConversationId = conversation.id;
  await loadConversations();
  return activeConversationId;
}

const THINKING_HTML = '<div class="chatbot-thinking"><span class="chatbot-thinking-orb"></span><span class="chatbot-thinking-label">Mathadap réfléchit…</span></div>';

// ── Robustesse réseau (façon ChatGPT/Claude) ────────────────────────────────
// Une erreur réseau réelle (fetch/lecture du flux qui lève, pas un payload
// d'erreur SSE propre déjà géré par consumeStream) ne doit jamais donner
// l'impression que la conversation est perdue : le message utilisateur est
// déjà persisté côté serveur avant tout traitement (conversation_manager.
// stream_reply), donc on ne le renvoie jamais. En cas d'échec, on consulte
// l'état RÉEL du serveur (jamais une supposition côté client) pour savoir
// si une réponse a déjà été persistée : si non, un bouton "Réessayer" relance
// uniquement la génération de la dernière réponse (retry_last, cf. backend) ;
// si oui (réponse partielle sauvée avant la coupure), on affiche simplement
// cette réponse — jamais de double envoi, jamais de duplication.
function renderErrorRetryState(bubbleEl, onRetry) {
  bubbleEl.innerHTML = `
    <div class="chatbot-error-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></svg>
      <span>La réponse n'a pas pu être générée. Vérifie ta connexion.</span>
      <button type="button" class="btn btn-ghost btn-sm chatbot-retry-btn">Réessayer</button>
    </div>`;
  const retryBtn = bubbleEl.querySelector(".chatbot-retry-btn");
  // { once: true } garantit déjà qu'un double-clic/double-tap ne déclenche
  // jamais deux générations (le listener est retiré dès le premier appel,
  // avant même que le second clic en file d'attente ne soit traité) ; on
  // désactive en plus le bouton de façon synchrone, en défense en profondeur,
  // pour un retour visuel immédiat même si l'échange de contenu du bubble
  // venait à être retardé par une future évolution (transition, etc.).
  retryBtn.addEventListener("click", () => {
    retryBtn.disabled = true;
    onRetry();
  }, { once: true });
}

// Exécute un tour (envoi initial, régénération ou réessai) contre l'un des
// trois endpoints SSE compatibles (stream/regenerate/retry) et gère l'échec
// de façon unifiée. `startStream(signal)` doit renvoyer la Response du fetch.
async function runAssistantTurn(convId, bubbleEl, startStream, onRetry) {
  abortController = new AbortController();
  setStreamingUI(true);
  try {
    const response = await startStream(abortController.signal);
    await consumeStream(response, bubbleEl, async () => {
      const { messages } = await api.chatbotMessages(convId);
      activeMessages = messages;
      renderMessages({ preserveScroll: true });
    });
  } catch (err) {
    if (err.name === "AbortError") return;
    if (err.isQuotaExceeded) {
      // 429 renvoyé avant même l'ouverture du flux (voir
      // server.py::peek_exceeded) : rien n'a été persisté côté serveur, donc
      // rien à recharger. Le toast + la redirection sont déjà déclenchés de
      // façon centralisée (voir api.js::buildApiError/handleQuotaExceeded) —
      // ici on finalise juste la bulle assistant avec un message explicite,
      // jamais l'erreur brute, jamais l'état "Réessayer" (retenter ne
      // débloquerait rien avant demain ou une mise à niveau).
      renderMessageBody(bubbleEl, "*Tu as atteint ta limite de messages aujourd'hui — redirection vers la page Abonnement…*");
      return;
    }
    let lastIsUser = true;
    try {
      const { messages } = await api.chatbotMessages(convId);
      activeMessages = messages;
      lastIsUser = !messages.length || messages[messages.length - 1].role === "user";
    } catch (getErr) {
      /* même le rechargement échoue (réseau totalement coupé) : on suppose
         le pire et on propose quand même un réessai plutôt qu'un blocage. */
    }
    if (lastIsUser) {
      // Point d'entrée unique de renderErrorRetryState (voir le graphe
      // d'appel en tête de fichier) : c'est ICI, et seulement ici, que
      // l'élève voit "La réponse n'a pas pu être générée."
      renderErrorRetryState(bubbleEl, onRetry);
    } else {
      // Une réponse (au moins partielle) a été persistée avant la coupure :
      // on l'affiche telle quelle, comme ChatGPT/Claude le font — la reprise
      // se fait alors via le bouton "Régénérer" standard du message.
      renderMessages({ preserveScroll: true });
    }
  } finally {
    setStreamingUI(false);
    refreshQuota();
    loadConversations();
  }
}

async function retryReply(convId, bubbleEl) {
  bubbleEl.innerHTML = THINKING_HTML;
  refreshChatbotStreamingSetting();
  await runAssistantTurn(
    convId,
    bubbleEl,
    (signal) => api.chatbotRetryStream(convId, { signal, classLevel: getStoredClassLevel() }),
    () => retryReply(convId, bubbleEl)
  );
}

async function sendMessage(overrideText) {
  const text = (overrideText ?? composer.getText(input)).trim();
  if (!text || isStreaming) return;
  const mentions = overrideText ? [] : composer.getMentions(input);
  composer.clear(input);
  sendBtn.disabled = true;
  hideLiveSuggestions();

  const convId = await ensureConversation();

  emptyState.hidden = true;
  appendMessageEl({ role: "user", content: text });

  const assistantRow = appendMessageEl({ role: "assistant", content: "" });
  const bubbleEl = assistantRow.querySelector(".chatbot-msg-bubble");
  bubbleEl.innerHTML = THINKING_HTML;
  forceScrollToBottom();

  refreshChatbotStreamingSetting();
  await runAssistantTurn(
    convId,
    bubbleEl,
    (signal) => api.chatbotStream(convId, text, mentions, { signal, classLevel: getStoredClassLevel() }),
    () => retryReply(convId, bubbleEl)
  );
}

async function regenerate() {
  if (!activeConversationId || isStreaming) return;
  const convId = activeConversationId;
  activeMessages = activeMessages.slice(0, -1);
  renderMessages();
  const assistantRow = appendMessageEl({ role: "assistant", content: "" });
  const bubbleEl = assistantRow.querySelector(".chatbot-msg-bubble");
  bubbleEl.innerHTML = THINKING_HTML;

  await runAssistantTurn(
    convId,
    bubbleEl,
    (signal) => api.chatbotRegenerateStream(convId, { signal, classLevel: getStoredClassLevel() }),
    () => retryReply(convId, bubbleEl)
  );
}

sendBtn.addEventListener("click", () => {
  if (isStreaming) {
    abortController?.abort();
    return;
  }
  sendMessage();
});

input.addEventListener("input", () => {
  sendBtn.disabled = isStreaming ? false : composer.isEmpty(input);
  scheduleLiveSuggestions();
});
input.addEventListener("keydown", (e) => {
  // La palette "@" (chatbot-mentions.js) intercepte Enter/flèches/Échap
  // pendant qu'elle est ouverte — ne jamais envoyer le message dans ce cas.
  if (mentionsController?.isOpen()) return;
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// ── Suggestions en temps réel pendant la frappe (Phase F) ──────────────────
// Débounce sur le texte principal (distinct de la recherche de conversations
// et de la palette "@", cf. chatbot-mentions.js) : propose jusqu'à 4 vraies
// correspondances (cours/exercices) via /api/search, jamais devinées.
const LIVE_SUGGESTIONS_DELAY_MS = 350;
let liveSuggestionsTimer = null;

function hideLiveSuggestions() {
  liveSuggestions.hidden = true;
  liveSuggestions.innerHTML = "";
}

function resultToCard(r) {
  if (r.type === "cours") return { type: "course", url: r.url, title: r.title };
  return { type: "notion_series", chapter_id: r.chapter_id, notion: r.notion, exercise_ids: [r.exercise_id] };
}

function renderLiveSuggestions(results) {
  if (!results.length) return hideLiveSuggestions();
  liveSuggestions.innerHTML = results.slice(0, 4).map((r, i) => `
    <button type="button" class="chatbot-suggestion-chip" data-index="${i}">${escapeHtml(r.title)}</button>
  `).join("");
  liveSuggestions.hidden = false;
  liveSuggestions.querySelectorAll("[data-index]").forEach((btn) => {
    btn.addEventListener("click", () => navigateToCard(resultToCard(results[Number(btn.dataset.index)])));
  });
}

function scheduleLiveSuggestions() {
  clearTimeout(liveSuggestionsTimer);
  if (mentionsController?.isOpen()) return hideLiveSuggestions();
  const text = composer.getText(input).trim();
  if (!text || text.length <= 3) return hideLiveSuggestions();
  liveSuggestionsTimer = setTimeout(async () => {
    try {
      const { results } = await api.search(text, null, 5, getStoredClassLevel());
      if (composer.getText(input).trim() === text) renderLiveSuggestions(results);
    } catch {
      /* silencieux */
    }
  }, LIVE_SUGGESTIONS_DELAY_MS);
}

// ── Suggestions avant le premier message ────────────────────────────────────
$("chatbot-suggestions")?.addEventListener("click", (e) => {
  const chip = e.target.closest(".chatbot-suggestion-chip");
  if (!chip) return;
  sendMessage(chip.textContent.trim());
});

// ── Menu "+" (pièces jointes) ────────────────────────────────────────────────
const attachToggle = $("chatbot-attach-toggle");
const attachMenu = $("chatbot-attach-menu");

function closeAttachMenu() {
  attachMenu.hidden = true;
  attachToggle.setAttribute("aria-expanded", "false");
}
attachToggle.addEventListener("click", (e) => {
  e.stopPropagation();
  const willOpen = attachMenu.hidden;
  attachMenu.hidden = !willOpen;
  attachToggle.setAttribute("aria-expanded", String(willOpen));
});
attachMenu.addEventListener("click", (e) => {
  if (e.target.closest("button")) closeAttachMenu();
});
document.addEventListener("click", (e) => {
  if (!attachMenu.hidden && !e.target.closest(".chatbot-attach-wrap")) closeAttachMenu();
});
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeAttachMenu();
});

// ── Pièces jointes ───────────────────────────────────────────────────────────
function insertIntoInput(text) {
  composer.prependParagraphIfNotEmpty(input);
  composer.insertText(input, text);
  sendBtn.disabled = isStreaming ? false : composer.isEmpty(input);
}

// PDF : extraction réelle du texte côté serveur (PyMuPDF), inséré tel quel —
// l'élève peut ensuite poser sa question sur ce contenu.
const pdfFileInput = document.createElement("input");
pdfFileInput.type = "file";
pdfFileInput.accept = "application/pdf";
pdfFileInput.hidden = true;
document.body.appendChild(pdfFileInput);
pdfFileInput.addEventListener("change", async () => {
  const file = pdfFileInput.files[0];
  pdfFileInput.value = "";
  if (!file) return;
  const btn = $("chatbot-attach-pdf");
  btn.disabled = true;
  try {
    const { text, truncated, filename } = await api.chatbotAttachPdf(file);
    insertIntoInput(
      `[Extrait de "${filename}"${truncated ? " (tronqué, document long)" : ""}]\n${text}`
    );
  } catch (err) {
    // 403 "premium_required" (analyse de PDF réservée à Ultra, voir
    // plan_service.Feature.ADVANCED_AI) : jamais afficher err.message brut
    // ("premium_required") — un message explicite + un lien direct vers
    // l'offre correspondante, jamais une erreur technique à l'écran.
    if (err.isPremiumRequired) {
      const planLabel = err.requiredPlan === "ultra" ? "Ultra" : "Premium";
      insertIntoInput(
        `[${featureLabel(err.feature)} fait partie de la formule ${planLabel}. ` +
        `Découvre l'offre ${planLabel} sur la page Abonnement pour débloquer l'analyse de documents joints.]`
      );
    } else {
      insertIntoInput(`[Impossible d'importer ce PDF : ${err.message}]`);
    }
  } finally {
    btn.disabled = false;
  }
});
$("chatbot-attach-pdf").addEventListener("click", () => pdfFileInput.click());

// Image : Mathadap utilise par défaut un modèle local texte (Ollama/Mistral),
// sans capacité de vision, et aucun OCR n'est installé — on le dit clairement
// plutôt que de laisser croire à une analyse qui n'a pas lieu.
$("chatbot-attach-image").addEventListener("click", () => {
  insertIntoInput(
    "[Image jointe — Mathadap ne peut pas encore analyser automatiquement une image. Décris ce qu'elle contient (énoncé, figure...) pour que je puisse t'aider.]"
  );
});

$("chatbot-attach-exercise").addEventListener("click", () => {
  insertIntoInput("Voici l'exercice sur lequel je bloque :\n");
});

// ── Santé du fournisseur IA (décidé en interne, jamais exposé côté client) ──
async function checkProviderHealth() {
  try {
    const health = await api.chatbotHealth();
    if (health.ok) {
      providerBanner.hidden = true;
    } else {
      providerBannerMsg.textContent = health.detail || "Le service d'intelligence artificielle n'est pas disponible pour le moment.";
      providerBanner.hidden = false;
    }
  } catch {
    /* silencieux : ne bloque jamais le reste de la page */
  }
}
$("chatbot-provider-retry").addEventListener("click", checkProviderHealth);
$("chatbot-provider-dismiss").addEventListener("click", () => { providerBanner.hidden = true; });

// ── Quota ────────────────────────────────────────────────────────────────────
// Source unique : GET /api/quota (quota_service.py) — appelé au chargement de
// la page et après chaque réponse (voir runAssistantTurn), jamais recalculé
// côté client (le serveur reste la seule source de vérité de l'usage réel).
async function refreshQuota() {
  try {
    const { chat_messages: chat } = await api.getQuota();
    quotaIndicator.hidden = false;
    quotaIndicator.classList.toggle("is-unlimited", chat.unlimited);
    quotaIndicator.classList.toggle("is-exhausted", !chat.unlimited && chat.remaining === 0);
    quotaIndicator.classList.toggle("is-low", !chat.unlimited && chat.remaining > 0 && chat.remaining <= Math.ceil(chat.limit * 0.15));
    quotaValue.innerHTML = chat.unlimited
      ? "Illimité <span aria-hidden=\"true\">∞</span>"
      : `${chat.used} / ${chat.limit} messages`;
  } catch { /* silencieux : l'indicateur reste dans son dernier état connu */ }
}

// ── Suggestions personnalisées par classe (état vide, avant toute
// conversation) ─────────────────────────────────────────────────────────────
// Questions d'exemple réellement rattachées au programme officiel de chaque
// classe (voir les vrais chapitres de webapp/static/data/cours_*/) — jamais
// les mêmes quel que soit le niveau sélectionné. Purement client (pas
// d'appel réseau) : mis à jour au chargement de la page, la classe active ne
// changeant qu'après un rechargement complet (voir curriculumSelector.js).
const CLASS_SUGGESTIONS = {
  troisieme: [
    "Explique-moi le théorème de Pythagore",
    "Comment reconnaître une situation de Thalès ?",
    "Comment calculer un angle avec la trigonométrie ?",
    "Aide-moi à calculer une moyenne ou une médiane",
    "Comment calculer une probabilité simple ?",
    "Qu'est-ce qu'une fonction affine ?",
  ],
  seconde: [
    "Aide-moi à développer une expression littérale",
    "Comment étudier les variations d'une fonction ?",
    "Comment résoudre une inéquation ?",
    "Qu'est-ce qu'un vecteur directeur ?",
    "Comment trouver l'équation d'une droite ?",
    "Explique-moi les statistiques descriptives",
  ],
  premiere: [
    "Comment calculer les termes d'une suite arithmétique ou géométrique ?",
    "Explique-moi le nombre dérivé",
    "Comment étudier un trinôme du second degré ?",
    "Qu'est-ce que le produit scalaire ?",
    "Comment utiliser un arbre de probabilités ?",
    "Explique-moi la fonction exponentielle",
  ],
};
const DEFAULT_SUGGESTIONS = [
  "Explique-moi cette notion",
  "Je n'ai pas compris cet exercice",
  "Fais-moi réviser",
  "Donne-moi un exercice",
  "Prépare-moi pour mon contrôle",
];

function renderSuggestions() {
  const chips = $("chatbot-suggestions");
  if (!chips) return;
  const questions = CLASS_SUGGESTIONS[getStoredClassLevel()] || DEFAULT_SUGGESTIONS;
  chips.innerHTML = questions.map((q) => `<button class="chatbot-suggestion-chip" type="button">${escapeHtml(q)}</button>`).join("");
}

// ── Accueil personnalisé (état vide, avant toute conversation) ──────────────
async function loadGreeting() {
  if (!emptyGreeting) return;
  try {
    const { greeting } = await api.chatbotGreeting(getStoredClassLevel());
    if (greeting) emptyGreeting.textContent = greeting;
  } catch {
    /* silencieux : le texte statique par défaut reste affiché */
  }
}

// ── Blocage total pour un compte invité ──────────────────────────────────────
// Contrairement au verrou du dashboard (dismissible), l'accès est ici
// totalement refusé (aussi côté serveur par auth.py::require_non_guest sur
// toutes les routes /api/chatbot/*) : le même composant guestLockOverlay
// couvre TOUTE la zone chatbot (conversations + messages + saisie, voir
// .chatbot-shell) — jamais deux zones floutées séparément, pour qu'aucun
// message/bouton/champ ne reste distinguable ni cliquable/scrollable/
// sélectionnable derrière. Seul élément interactif : "Se connecter" (pas de
// bouton pour lever le verrou, contrairement au dashboard.js).
function applyGuestChatbotLock() {
  const shell = document.querySelector(".chatbot-shell");
  if (!shell) return;
  input.setAttribute("contenteditable", "false");
  sendBtn.disabled = true;

  mountGuestLockOverlay(shell, {
    id: "chatbot-guest-lock-overlay",
    icon: "lock",
    title: "Connexion requise",
    description: "Connecte-toi pour utiliser le professeur IA.",
    actionsHtml: `<button type="button" class="btn btn-primary js-open-login">Se connecter</button>`,
  });
}

async function guardAgainstGuestAccess() {
  let user;
  try {
    ({ user } = await api.me());
  } catch {
    return; // Session expirée : login_required redirigera de toute façon.
  }
  if (user.is_guest) applyGuestChatbotLock();
}

// ── Actions déclenchées par une catégorie de la palette "@" ─────────────────
// (Cours/Exercices/Notions/Progression/Statistiques/Dashboard/Profil/
// Paramètres/Séries insèrent un badge de donnée résolue côté backend — géré
// dans chatbot-mentions.js. Seules les catégories qui déclenchent une
// vraie action immédiate passent par ici : Chatbot démarre une nouvelle
// conversation, Objectifs insère les vrais chiffres du jour.)
async function handleMentionAction(action) {
  if (action === "new-conversation") {
    $("chatbot-new-btn")?.click();
    return;
  }
  if (action === "goals") {
    try {
      const goals = await api.dailyGoals();
      composer.prependParagraphIfNotEmpty(input);
      composer.insertText(
        input,
        `Mon objectif du jour : ${goals.done_exercises}/${goals.target_exercises} exercices${goals.reached ? " (atteint)" : ""}. `
      );
      sendBtn.disabled = isStreaming ? false : composer.isEmpty(input);
    } catch {
      /* silencieux */
    }
  }
}

mentionsController = initMentions({ input, onAction: handleMentionAction });

// ── Démarrage ────────────────────────────────────────────────────────────────
guardAgainstGuestAccess();
loadConversations();
refreshQuota();
renderSuggestions();
loadGreeting();
checkProviderHealth();
refreshChatbotStreamingSetting();
