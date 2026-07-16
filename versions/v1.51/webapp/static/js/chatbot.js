import { api } from "./api.js";
import { initSettingsManager } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { bindLiveTranslations } from "./i18n.js";
import { setMathContent } from "./mathrender.js";
import { t } from "./i18n.js";
import { initMentions } from "./chatbot-mentions.js";
import * as composer from "./chatbot-composer.js";

initSettingsManager().then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));

const $ = (id) => document.getElementById(id);
const convoList = $("chatbot-convo-list");
const messagesEl = $("chatbot-messages");
const emptyState = $("chatbot-empty-state");
const input = $("chatbot-input");
const sendBtn = $("chatbot-send-btn");
const topbarTitle = $("chatbot-topbar-title");
const quotaBadge = $("chatbot-quota-badge");
const contextContent = $("chatbot-context-content");
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
function renderMessageBody(el, rawText) {
  const html = window.marked ? window.marked.parse(rawText || "") : (rawText || "");
  setMathContent(el, html);
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

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
      const title = window.prompt("Renommer la conversation :", conv.title);
      if (title && title.trim()) {
        await api.chatbotRenameConversation(id, title.trim());
        await loadConversations();
        if (id === activeConversationId) topbarTitle.textContent = title.trim();
      }
    });
    item.querySelector('[data-action="delete"]').addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!window.confirm("Supprimer définitivement cette conversation ?")) return;
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
  return `
    <div class="chatbot-msg-actions">
      <button data-action="copy" title="Copier"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2v14a2 2 0 0 0 2 2h14M18 22V8a2 2 0 0 0-2-2H2"/></svg></button>
      <button data-action="regenerate" title="Régénérer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 1 3 6.7"/><path d="M3 12V6M3 12h6"/></svg></button>
      <button data-action="continue" title="Continuer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
      <button data-action="like" title="J'aime" class="${msg.liked === 1 ? "active" : ""}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 22V11l5-8 1 1v6h6l-2 12H7Z"/></svg></button>
      <button data-action="dislike" title="Je n'aime pas" class="${msg.liked === 0 ? "active" : ""}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="transform:rotate(180deg)"><path d="M7 22V11l5-8 1 1v6h6l-2 12H7Z"/></svg></button>
      <button data-action="export-md" title="Exporter Markdown"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12m0 0 4-4m-4 4-4-4"/><path d="M4 19h16"/></svg></button>
      <button data-action="export-pdf" title="Exporter PDF"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"/><path d="M14 2v6h6"/></svg></button>
    </div>`;
}

function renderMessages() {
  emptyState.hidden = activeMessages.length > 0;
  messagesEl.innerHTML = "";
  if (!activeMessages.length) {
    messagesEl.appendChild(emptyState);
    return;
  }
  activeMessages.forEach((msg) => appendMessageEl(msg));
  scrollToBottom();
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

function appendMessageEl(msg) {
  const row = document.createElement("div");
  row.className = `chatbot-msg ${msg.role}`;
  row.dataset.id = msg.id || "";
  row.innerHTML = `
    <div class="chatbot-msg-avatar">${msg.role === "user" ? "Toi" : "NM"}</div>
    <div>
      <div class="chatbot-msg-bubble"></div>
      ${msg.role === "assistant" ? messageActionsHtml(msg) : ""}
      ${msg.role === "assistant" ? actionCardsHtml(msg.cards) : ""}
    </div>
  `;
  renderMessageBody(row.querySelector(".chatbot-msg-bubble"), msg.content);
  if (msg.role === "assistant") {
    bindMessageActions(row, msg);
    if (msg.cards?.length) bindActionCards(row, msg.cards);
  }
  messagesEl.appendChild(row);
  return row;
}

function bindMessageActions(row, msg) {
  row.querySelector('[data-action="copy"]')?.addEventListener("click", () => {
    navigator.clipboard.writeText(msg.content || "");
  });
  row.querySelector('[data-action="regenerate"]')?.addEventListener("click", () => regenerate());
  row.querySelector('[data-action="continue"]')?.addEventListener("click", () => sendMessage("Continue."));
  row.querySelector('[data-action="like"]')?.addEventListener("click", async (e) => {
    const newVal = msg.liked === 1 ? null : 1;
    msg.liked = newVal;
    await api.chatbotFeedback(msg.id, newVal);
    renderMessages();
  });
  row.querySelector('[data-action="dislike"]')?.addEventListener("click", async () => {
    const newVal = msg.liked === 0 ? null : 0;
    msg.liked = newVal;
    await api.chatbotFeedback(msg.id, newVal);
    renderMessages();
  });
  row.querySelector('[data-action="export-md"]')?.addEventListener("click", () => {
    const blob = new Blob([msg.content || ""], { type: "text/markdown" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "reponse-novamath.md";
    a.click();
  });
  row.querySelector('[data-action="export-pdf"]')?.addEventListener("click", () => window.print());
}

// ── Streaming ────────────────────────────────────────────────────────────────
function setStreamingUI(streaming) {
  isStreaming = streaming;
  sendBtn.classList.toggle("is-stop", streaming);
  sendBtn.disabled = !streaming && composer.isEmpty(input);
  sendBtn.innerHTML = streaming
    ? '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>'
    : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
}

// Affiche le texte progressivement (effet machine à écrire) plutôt que par
// à-coups au rythme des deltas SSE : les deltas remplissent un buffer, un
// intervalle local le "consomme" par petits groupes de caractères pour
// rester fluide même quand le réseau livre de gros blocs de texte d'un coup.
const TYPEWRITER_INTERVAL_MS = 15;
const TYPEWRITER_CHARS_PER_TICK = 2;

function startTypewriter(bubbleEl) {
  bubbleEl.classList.add("is-streaming");
  let shown = "";
  let target = "";
  let doneReceiving = false;
  let onFullyDone = null;

  const timer = setInterval(() => {
    if (shown.length < target.length) {
      shown = target.slice(0, shown.length + TYPEWRITER_CHARS_PER_TICK);
      renderMessageBody(bubbleEl, shown);
      scrollToBottom();
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
      try { payload = JSON.parse(line); } catch { continue; }
      if (payload.delta) {
        fullText += payload.delta;
        typewriter.push(payload.delta);
      } else if (payload.error) {
        fullText += `\n\n*⚠️ ${payload.error}*`;
        typewriter.push(`\n\n*⚠️ ${payload.error}*`);
        if (payload.provider_down) {
          providerBannerMsg.textContent = payload.error;
          providerBanner.hidden = false;
        }
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
  bubbleEl.innerHTML = '<div class="chatbot-thinking"><span class="chatbot-thinking-orb"></span><span class="chatbot-thinking-label">NovaMath réfléchit…</span></div>';
  scrollToBottom();

  abortController = new AbortController();
  setStreamingUI(true);
  try {
    const response = await api.chatbotStream(convId, text, mentions, { signal: abortController.signal });
    await consumeStream(response, bubbleEl, async () => {
      const { messages } = await api.chatbotMessages(convId);
      activeMessages = messages;
      renderMessages();
    });
  } catch (err) {
    if (err.name !== "AbortError") {
      renderMessageBody(bubbleEl, "*⚠️ La réponse a été interrompue ou le service est indisponible.*");
    }
  } finally {
    setStreamingUI(false);
    refreshQuota();
    loadConversations();
  }
}

async function regenerate() {
  if (!activeConversationId || isStreaming) return;
  activeMessages = activeMessages.slice(0, -1);
  renderMessages();
  const assistantRow = appendMessageEl({ role: "assistant", content: "" });
  const bubbleEl = assistantRow.querySelector(".chatbot-msg-bubble");
  bubbleEl.innerHTML = '<div class="chatbot-thinking"><span class="chatbot-thinking-orb"></span><span class="chatbot-thinking-label">NovaMath réfléchit…</span></div>';

  abortController = new AbortController();
  setStreamingUI(true);
  try {
    const response = await api.chatbotRegenerateStream(activeConversationId, { signal: abortController.signal });
    await consumeStream(response, bubbleEl, async () => {
      const { messages } = await api.chatbotMessages(activeConversationId);
      activeMessages = messages;
      renderMessages();
    });
  } catch (err) {
    if (err.name !== "AbortError") {
      renderMessageBody(bubbleEl, "*⚠️ Impossible de régénérer la réponse.*");
    }
  } finally {
    setStreamingUI(false);
  }
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
      const { results } = await api.search(text, null, 5);
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
    insertIntoInput(`[Impossible d'importer ce PDF : ${err.message}]`);
  } finally {
    btn.disabled = false;
  }
});
$("chatbot-attach-pdf").addEventListener("click", () => pdfFileInput.click());

// Image : NovaMath utilise par défaut un modèle local texte (Ollama/Mistral),
// sans capacité de vision, et aucun OCR n'est installé — on le dit clairement
// plutôt que de laisser croire à une analyse qui n'a pas lieu.
$("chatbot-attach-image").addEventListener("click", () => {
  insertIntoInput(
    "[Image jointe — NovaMath ne peut pas encore analyser automatiquement une image. Décris ce qu'elle contient (énoncé, figure...) pour que je puisse t'aider.]"
  );
});

$("chatbot-attach-exercise").addEventListener("click", () => {
  insertIntoInput("Voici l'exercice sur lequel je bloque :\n");
});

// ── Santé du fournisseur IA (Claude/Anthropic par défaut) ───────────────────
async function checkProviderHealth(providerOverride) {
  try {
    const health = await api.chatbotHealth(providerOverride);
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
window.checkChatbotProviderHealth = checkProviderHealth;
$("chatbot-provider-retry").addEventListener("click", checkProviderHealth);
$("chatbot-provider-dismiss").addEventListener("click", () => { providerBanner.hidden = true; });

// ── Quota + panneau contextuel ───────────────────────────────────────────────
async function refreshQuota() {
  try {
    const { used, limit } = await api.chatbotQuota();
    quotaBadge.textContent = `${used}/${limit} messages aujourd'hui`;
  } catch { /* silencieux */ }
}

async function loadContextPanel() {
  try {
    const summary = await api.chatbotContextPreview();
    const goals = summary.daily_goals;
    contextContent.innerHTML = `
      <div class="chatbot-context-item"><span class="label">Niveau</span><span class="value">${summary.level_label}</span></div>
      ${summary.accuracy_pct !== null ? `<div class="chatbot-context-item"><span class="label">Précision</span><span class="value">${summary.accuracy_pct}%</span></div>` : ""}
      <div class="chatbot-context-item"><span class="label">Exercices faits</span><span class="value">${summary.total_exercises}</span></div>
      ${goals ? `<div class="chatbot-context-item"><span class="label">Objectif du jour</span><span class="value">${goals.done_exercises}/${goals.target_exercises}${goals.reached ? " ✓" : ""}</span></div>` : ""}
      ${goals && goals.streak_days ? `<div class="chatbot-context-item"><span class="label">Série en cours</span><span class="value">${goals.streak_days} j</span></div>` : ""}
      ${summary.weak_notions.length ? `<div style="margin-top:14px;"><div class="chatbot-context-item" style="border:none; padding-bottom:2px;"><span class="label">Notions à renforcer</span></div><div class="chatbot-context-tags">${summary.weak_notions.map((n) => `<span class="chatbot-context-tag">${escapeHtml(n)}</span>`).join("")}</div></div>` : ""}
      ${summary.mastered_notions.length ? `<div style="margin-top:14px;"><div class="chatbot-context-item" style="border:none; padding-bottom:2px;"><span class="label">Notions maîtrisées</span></div><div class="chatbot-context-tags">${summary.mastered_notions.map((n) => `<span class="chatbot-context-tag">${escapeHtml(n)}</span>`).join("")}</div></div>` : ""}
    `;
  } catch {
    contextContent.innerHTML = `<p style="color:var(--text-faint); font-size:0.82rem;">Profil indisponible pour le moment.</p>`;
  }
}

// ── Accueil personnalisé (état vide, avant toute conversation) ──────────────
async function loadGreeting() {
  if (!emptyGreeting) return;
  try {
    const { greeting } = await api.chatbotGreeting();
    if (greeting) emptyGreeting.textContent = greeting;
  } catch {
    /* silencieux : le texte statique par défaut reste affiché */
  }
}

// ── Actions déclenchées par une catégorie de la palette "@" ─────────────────
// (Cours/Exercices/Notions insèrent un badge — géré dans chatbot-mentions.js.
// Les autres catégories déclenchent une vraie action immédiate, jamais une
// simple redirection décorative : Paramètres ouvre le vrai popup déjà présent
// sur la page, Chatbot démarre une vraie nouvelle conversation, Objectifs
// insère les vrais chiffres du jour.)
async function handleMentionAction(action) {
  if (action === "open-settings") {
    $("settings-btn")?.click();
    return;
  }
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
loadConversations();
refreshQuota();
loadContextPanel();
loadGreeting();
checkProviderHealth();
