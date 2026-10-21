import { api, handleQuotaExceeded } from "./api.js";
import { initSettingsManager } from "./settingsManager.js";
import { bindSettingsButton } from "./settingsPopup.js";
import { bindLiveTranslations, t } from "./i18n.js";
import { setRenderedHtmlContent, extractMathSegments, restoreMathSegments } from "./mathrender.js";
import { initMentions } from "./chatbot-mentions.js";
import * as composer from "./chatbot-composer.js";
import { openPromptPopup, openConfirmPopup } from "./popup.js";
import { getStoredClassLevel } from "./curriculumSelector.js";
import { featureLabel } from "./features.js";
import { openReportTicketPopup } from "./supportTicket.js";
import { ICONS } from "./icons.js";
import { mountGuestLockOverlay } from "./guestLockOverlay.js";
import { registerUnsavedActivityCheck } from "./unsavedActivity.js";

initSettingsManager().then(() => bindLiveTranslations());
bindSettingsButton(document.getElementById("settings-btn"));

const $ = (id) => document.getElementById(id);
const convoList = $("chatbot-convo-list");
const messagesEl = $("chatbot-messages");
const emptyState = $("chatbot-empty-state");
const input = $("chatbot-input");

// Aucun brouillon persistant pour le composeur du chatbot (contrairement à
// une série d'exercices, voir store.js::saveInProgressSeries) — un message en
// cours de rédaction, non encore envoyé, serait donc perdu par n'importe quel
// rechargement de page. Enregistré auprès de unsavedActivity.js pour que
// analyticsBeacon.js puisse en tenir compte avant de recharger la page après
// un retrait de consentement aux cookies statistiques — jamais une
// sauvegarde parallèle du texte lui-même, seulement sa détection.
registerUnsavedActivityCheck("chatbot-draft", () => !!input && !composer.isEmpty(input));
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
const chatbotTopbar = document.querySelector(".chatbot-topbar");
const chatbotInputArea = document.querySelector(".chatbot-input-area");
const searchTrigger = $("chatbot-search-trigger");
const searchView = $("chatbot-search-view");
const searchViewInput = $("chatbot-search-view-input");
const searchViewClear = $("chatbot-search-view-clear");
const searchViewResults = $("chatbot-search-view-results");
const searchViewBack = $("chatbot-search-view-back");

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
  convosCollapseBtn.setAttribute(
    "aria-label",
    collapsed ? "Développer les conversations" : "Réduire les conversations",
  );
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
// extractMathSegments/restoreMathSegments (mathrender.js) : marked.parse()
// suit CommonMark, qui échappe tout antislash suivi de "(", ")", "[" ou "]"
// — une formule "\(x^2\)" perdait donc ses deux antislashs avant même
// d'atteindre KaTeX (chantier "rendu des formules", 2026-10-18). Chaque
// formule est donc extraite AVANT marked.parse() (remplacée par un jeton
// inerte qu'aucune règle Markdown ne peut altérer) puis restaurée tel quel
// juste après — KaTeX voit alors les délimiteurs intacts.
function renderMessageBody(el, rawText) {
  el.classList.remove("chatbot-msg-bubble--thinking");
  let html;
  if (window.marked) {
    const { text: protectedText, segments } = extractMathSegments(rawText || "");
    html = restoreMathSegments(window.marked.parse(protectedText), segments);
  } else {
    html = escapeHtml(rawText || "").replace(/\n/g, "<br>");
  }
  setRenderedHtmlContent(el, html);
}

// Rendu "brut" utilisé UNIQUEMENT pendant les ticks intermédiaires du
// "machine à écrire" (voir startTypewriter) : jamais marked.parse() ni
// renderMathInElement ici. Deux raisons concrètes (chantier UX "animation de
// réflexion", audit du 2026-10-18) :
//  1. Performance — marked.parse() + DOMPurify.sanitize() + un balayage
//     KaTeX du DOM entier à CHAQUE tick (toutes les 15ms) sont coûteux, en
//     particulier sur une réponse longue/riche (listes, tableaux, blocs de
//     code) — c'était la cause probable des à-coups visuels rapportés
//     ("la réponse apparaît parfois entièrement d'un seul coup").
//  2. Correction visuelle — une formule KaTeX ($...$) révélée à moitié par
//     le défilement (délimiteur fermant pas encore tapé) se rend soit en
//     texte brut, soit en fragment vide (throwOnError:false), puis "saute"
//     à son rendu correct une fois le $ fermant arrivé — un vrai défaut
//     visuel, pas juste un détail de perf.
// Le rendu riche (markdown + KaTeX) n'intervient donc plus qu'UNE SEULE FOIS,
// sur le texte complet, à la toute fin du flux (voir startTypewriter).
function renderTypewriterTick(el, rawText) {
  el.classList.remove("chatbot-msg-bubble--thinking");
  el.innerHTML = escapeHtml(rawText || "").replace(/\n/g, "<br>");
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
  convoList.innerHTML = conversations
    .map(
      (c) => `
    <div class="chatbot-convo-item${c.id === activeConversationId ? " active" : ""}" data-id="${c.id}">
      ${c.pinned ? '<svg class="pin-icon" aria-hidden="true" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1"><path d="M12 17v5M8 3h8l-1 6 3 3v2H6v-2l3-3-1-6Z"/></svg>' : ""}
      <span class="chatbot-convo-title">${escapeHtml(c.title)}</span>
      <div class="chatbot-convo-actions">
        <button data-action="pin" title="${c.pinned ? "Désépingler" : "Épingler"}" aria-label="${c.pinned ? "Désépingler la conversation" : "Épingler la conversation"}">${ICONS.pin}</button>
        <button data-action="rename" title="Renommer" aria-label="Renommer la conversation">${ICONS.penSquare}</button>
        <button data-action="delete" title="Supprimer" aria-label="Supprimer la conversation">${ICONS.trash}</button>
      </div>
    </div>
  `,
    )
    .join("");

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

// `knownTitle` : utilisé par la vue de recherche (openSearchView ci-dessous),
// qui connaît déjà le titre exact de la conversation choisie SANS dépendre du
// tableau `conversations` de la sidebar — ce dernier peut très bien ne pas
// (encore) contenir ce résultat (liste non rafraîchie, pagination, filtre
// précédent) : sans ce paramètre, `conv` serait introuvable et le titre
// retomberait à tort sur "Nouvelle conversation".
async function selectConversation(id, knownTitle) {
  activeConversationId = id;
  const conv = conversations.find((c) => c.id === id);
  topbarTitle.textContent = conv ? conv.title : (knownTitle ?? "Nouvelle conversation");
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

// ── Vue "Rechercher une conversation" ───────────────────────────────────────
// Remplace l'ancien champ filtrant la liste en place par une vraie vue dans
// la zone principale (jamais un popover) — réutilise tels quels
// api.chatbotConversations(search) (recherche par titre déjà existante côté
// backend, voir db.list_conversations) et selectConversation() (même chemin
// que la sidebar, aucune logique dupliquée).
let searchViewTimer = null;
let searchViewOpen = false;

function formatConvoDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function renderSearchResults(items, query) {
  if (!items) {
    searchViewResults.innerHTML = `<div class="chatbot-search-view-status">Impossible de charger les conversations. Réessaie dans un instant.</div>`;
    return;
  }
  if (!items.length) {
    searchViewResults.innerHTML = query
      ? `<div class="chatbot-search-view-status">Aucune conversation ne correspond à « ${escapeHtml(query)} ».</div>`
      : `<div class="chatbot-search-view-status">Aucune conversation pour l'instant.</div>`;
    return;
  }
  searchViewResults.innerHTML = items
    .map(
      (c) => `
    <button type="button" class="chatbot-search-result" data-id="${c.id}">
      <span class="chatbot-search-result-title">${escapeHtml(c.title)}</span>
      <span class="chatbot-search-result-date">${escapeHtml(formatConvoDate(c.updated_at))}</span>
    </button>
  `,
    )
    .join("");
  searchViewResults.querySelectorAll(".chatbot-search-result").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.id);
      const found = items.find((c) => c.id === id);
      await selectConversation(id, found?.title);
      closeSearchView();
    });
  });
}

async function runSearchViewQuery(query) {
  searchViewResults.innerHTML = `<div class="chatbot-search-view-status">Recherche…</div>`;
  try {
    const { conversations: results } = await api.chatbotConversations(query || undefined);
    // Le champ a pu changer pendant l'aller-retour réseau (frappe rapide) :
    // n'affiche jamais une réponse devenue obsolète.
    if (searchViewInput.value.trim() === query) renderSearchResults(results, query);
  } catch {
    if (searchViewInput.value.trim() === query) renderSearchResults(null, query);
  }
}

function scheduleSearchViewQuery() {
  clearTimeout(searchViewTimer);
  // Espaces inutiles ignorés (recherche comme saisie) — jamais envoyés tels
  // quels à l'API, ni utilisés pour décider de l'état "vide".
  const query = searchViewInput.value.trim();
  searchViewClear.hidden = !query;
  searchViewTimer = setTimeout(() => runSearchViewQuery(query), 250);
}

function openSearchView() {
  searchViewOpen = true;
  searchView.hidden = false;
  chatbotTopbar.hidden = true;
  // Le bandeau "fournisseur indisponible" n'est jamais masqué ici (son état
  // est géré ailleurs, voir checkProviderHealth) : le cacher sans jamais le
  // restaurer explicitement à la fermeture le laisserait caché à tort même
  // si le service IA est réellement indisponible.
  messagesEl.hidden = true;
  chatbotInputArea.hidden = true;
  searchViewInput.value = "";
  searchViewClear.hidden = true;
  closeConvosDrawer();
  runSearchViewQuery("");
  searchViewInput.focus();
}

// Restaure l'état normal du chatbot EXACTEMENT comme il était (sidebar
// ouverte/réduite jamais touchée par cette vue, voir openSearchView — aucune
// classe .is-collapsed/.is-open n'est modifiée ici).
function closeSearchView() {
  searchViewOpen = false;
  searchView.hidden = true;
  chatbotTopbar.hidden = false;
  messagesEl.hidden = false;
  chatbotInputArea.hidden = false;
}

searchTrigger.addEventListener("click", openSearchView);
searchViewBack.addEventListener("click", closeSearchView);
searchViewInput.addEventListener("input", scheduleSearchViewQuery);
searchViewClear.addEventListener("click", () => {
  searchViewInput.value = "";
  searchViewClear.hidden = true;
  searchViewInput.focus();
  runSearchViewQuery("");
});
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && searchViewOpen) closeSearchView();
});

// ── Rendu des messages ──────────────────────────────────────────────────────
// Seules les deux actions les plus utilisées (copier/régénérer) restent
// visibles directement ; le reste vit dans le menu "Plus". Chantier UX
// (2026-10-18) — audit des 6 actions historiques du menu :
//   - "Continuer"      : aucun appel API dédié, ré-envoie juste le texte
//     "Continue." via sendMessage() (même chemin qu'un message tapé à la
//     main) — jamais utilisé ailleurs dans le code. Retiré : l'élève peut
//     taper "continue" lui-même, ce raccourci n'était pas essentiel.
//   - "Exporter en Markdown"/"Exporter en PDF" : purement client (Blob +
//     window.print()), aucun appel backend, jamais réutilisés ailleurs
//     (window.print() d'admin-analytics.js est un bouton totalement séparé).
//     Retirés : fonctionnalités réellement secondaires pour un chatbot
//     pédagogique, sans dépendance à préserver.
//   - "J'aime"/"Je n'aime pas" (renommés "Bonne réponse"/"Mauvaise réponse")
//     et "Signaler un problème" : appels API réels (api.chatbotFeedback,
//     openReportTicketPopup) — conservés tels quels, avec leur comportement
//     exact (voir bindMessageActions).
function messageActionsHtml(msg) {
  // Tant que le message n'a pas d'id (placeholder en cours de génération,
  // ou tour en cours de réessai), aucune action n'a de sens : copier un
  // texte vide, régénérer/aimer un message pas encore persisté échoueraient
  // silencieusement (l'id n'existe pas encore côté serveur). On les
  // désactive dès le rendu plutôt que de laisser un clic sans effet visible.
  const dis = msg.id ? "" : "disabled";
  return `
    <div class="chatbot-msg-actions">
      <button data-action="copy" title="Copier" aria-label="Copier la réponse" ${dis}>${ICONS.copy}</button>
      <button data-action="regenerate" title="Régénérer" aria-label="Régénérer la réponse" ${dis}>${ICONS.rotate}</button>
      <div class="chatbot-msg-more-wrap">
        <button data-action="more-toggle" title="Plus d'actions" aria-label="Plus d'actions" aria-haspopup="true" aria-expanded="false" ${dis}>${ICONS.moreHorizontal}</button>
        <div class="chatbot-msg-more-menu" role="menu" hidden>
          <button data-action="like" role="menuitem" aria-pressed="${msg.liked === 1}" class="${msg.liked === 1 ? "active" : ""}" ${dis}>${ICONS.thumbsUp}<span>Bonne réponse</span></button>
          <button data-action="dislike" role="menuitem" aria-pressed="${msg.liked === 0}" class="${msg.liked === 0 ? "active" : ""}" ${dis}>${ICONS.thumbsDown}<span>Mauvaise réponse</span></button>
          <div class="chatbot-msg-more-sep" role="separator"></div>
          <button data-action="report" role="menuitem" ${dis}>${ICONS.flag}<span>Signaler un problème</span></button>
        </div>
      </div>
    </div>`;
}

// ── Actions sous un message UTILISATEUR (Copier/Modifier) ──────────────────
// Même logique de désactivation que messageActionsHtml ci-dessus (message
// pas encore persisté = aucune action utile).
function userMessageActionsButtonsHtml(msg) {
  const dis = msg.id ? "" : "disabled";
  return `
    <button data-action="copy-user" title="Copier" aria-label="Copier le message" ${dis}>${ICONS.copy}</button>
    <button data-action="edit-user" title="Modifier" aria-label="Modifier le message" ${dis}>${ICONS.penSquare}</button>`;
}

// ── Menu "Plus" (une seule rangée d'actions ouverte à la fois) ─────────────
function closeAllMoreMenus(except) {
  messagesEl.querySelectorAll(".chatbot-msg-more-menu").forEach((menu) => {
    if (menu === except) return;
    menu.hidden = true;
    menu
      .closest(".chatbot-msg-more-wrap")
      ?.querySelector('[data-action="more-toggle"]')
      ?.setAttribute("aria-expanded", "false");
  });
}
document.addEventListener("click", (e) => {
  if (!e.target.closest(".chatbot-msg-more-wrap")) closeAllMoreMenus();
});
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeAllMoreMenus();
});

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
// Icônes reprises de la bibliothèque centrale (icons.js), jamais redéfinies
// localement, pour rester visuellement cohérentes avec le reste du produit.
const ACTION_CARD_ICONS = {
  book: ICONS.bookOpen,
  target: ICONS.target,
};

// Chantier "routage réel" (2026-10-17, test D) : t() ne fait jamais
// d'interpolation (voir i18n.js::t — `fallback` n'est utilisé QUE si la clé
// est absente du dictionnaire) — deux cartes "notion_series" sur des notions
// différentes affichaient donc un texte strictement identique. `c.title`
// (déjà transmis par le backend, voir action_cards_service.py) nomme le
// sujet réel de la carte ; on l'ajoute ici au libellé générique plutôt que
// de dupliquer les clés i18n par notion.
function actionCardLabel(c) {
  const base = t(c.label_key, "");
  return c.title ? `${base} — ${c.title}` : base;
}

function actionCardsHtml(cards) {
  if (!cards || !cards.length) return "";
  return `<div class="chatbot-action-cards">${cards
    .map(
      (c, i) => `
    <button type="button" class="chatbot-action-card card card--interactive" data-card-index="${i}">
      <span class="chatbot-action-card-icon">${ACTION_CARD_ICONS[c.icon] || ACTION_CARD_ICONS.book}</span>
      <span>${escapeHtml(actionCardLabel(c))}</span>
    </button>
  `,
    )
    .join("")}</div>`;
}

/** `card.exercise_ids` ne porte parfois qu'UN SEUL id (voir resultToCard
 * ci-dessous : les suggestions live pendant la frappe ne connaissent qu'un
 * résultat de recherche ponctuel, pas un pool) — exercice.js::buildSeriesPool
 * ne doit alors jamais répéter silencieusement ce même exercice pour remplir
 * la série (bug "10 questions identiques" du chantier routage réel). On
 * complète ici le pool via le même mécanisme que le backend utilise déjà
 * pour les cartes générées sous une réponse du chatbot (voir
 * action_cards_service.py::build_cards -> search_service.exercises_by_notion),
 * avant d'écrire lumis:pending_series — jamais après coup côté exercice.js,
 * qui n'a aucun moyen d'élargir un pool déjà trop restreint. */
async function navigateToCard(card) {
  if (card.type === "notion_series") {
    let exerciseIds = card.exercise_ids;
    if (exerciseIds.length <= 1 && card.chapter_id && card.notion) {
      try {
        const { results } = await api.exercisesByNotion(card.chapter_id, card.notion, 10, getStoredClassLevel());
        if (results.length > 1) exerciseIds = results.map((r) => r.exercise_id);
      } catch {
        /* repli silencieux sur le pool d'origine (mieux qu'un blocage total) */
      }
    }
    localStorage.setItem(
      "lumis:pending_series",
      JSON.stringify({
        mode: "notion",
        chapterId: card.chapter_id,
        notion: card.notion,
        notions: [card.notion],
        exerciseIds,
      }),
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
    row.innerHTML = `
      <div class="chatbot-msg-bubble chatbot-msg-bubble--user"></div>
      <div class="chatbot-msg-actions chatbot-msg-actions--user">${userMessageActionsButtonsHtml(msg)}</div>
    `;
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
  } else {
    bindUserMessageActions(row, msg);
  }
  messagesEl.appendChild(row);
  return row;
}

const COPY_FEEDBACK_MS = 1600;

// Positionnement dynamique du menu "Plus" (chantier "menu Plus", 2026-10-18) :
// `.chatbot-msg-more-menu` est en `position: fixed` (chatbot.css) pour
// échapper à l'`overflow` de `.chatbot-messages` — ses coordonnées ne
// peuvent donc plus être fixées en CSS, il faut les calculer ici, à CHAQUE
// ouverture (jamais mémorisé : fenêtre redimensionnée/liste défilée entre
// deux ouvertures). Bascule vers le haut si la place manque en dessous, et
// recale horizontalement pour ne jamais sortir de la fenêtre (y compris
// tout près des bords de l'écran, ex. 320px).
function positionMoreMenu(toggleEl, menuEl) {
  const MARGIN = 8;
  const toggleRect = toggleEl.getBoundingClientRect();
  const menuRect = menuEl.getBoundingClientRect(); // menu déjà visible (hidden=false) à cet instant
  const spaceBelow = window.innerHeight - toggleRect.bottom;
  const openUpward = spaceBelow < menuRect.height + MARGIN && toggleRect.top > menuRect.height + MARGIN;
  menuEl.style.top = openUpward
    ? `${Math.max(MARGIN, toggleRect.top - menuRect.height - 6)}px`
    : `${Math.min(toggleRect.bottom + 6, window.innerHeight - menuRect.height - MARGIN)}px`;
  const left = Math.min(toggleRect.left, window.innerWidth - menuRect.width - MARGIN);
  menuEl.style.left = `${Math.max(MARGIN, left)}px`;
}

function bindMessageActions(row, msg) {
  const moreToggle = row.querySelector('[data-action="more-toggle"]');
  const moreMenu = row.querySelector(".chatbot-msg-more-menu");
  moreToggle?.addEventListener("click", (e) => {
    e.stopPropagation();
    const willOpen = moreMenu.hidden;
    closeAllMoreMenus();
    moreMenu.hidden = !willOpen;
    moreToggle.setAttribute("aria-expanded", String(willOpen));
    if (willOpen) positionMoreMenu(moreToggle, moreMenu);
  });
  // Toute sélection dans le menu referme celui-ci (sauf J'aime/Je n'aime pas,
  // dont l'utilisateur peut vouloir voir l'état "actif" se mettre à jour
  // avant de refermer — comportement courant des menus de vote).
  moreMenu?.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      moreMenu.hidden = true;
      moreToggle?.setAttribute("aria-expanded", "false");
    });
  });

  row.querySelector('[data-action="copy"]')?.addEventListener("click", (e) => {
    const btn = e.currentTarget;
    if (btn.dataset.copying) return; // déjà en cours d'affichage du "Copié !"
    navigator.clipboard.writeText(msg.content || "");
    btn.dataset.copying = "1";
    btn.innerHTML = ICONS.check;
    btn.classList.add("is-copied");
    btn.setAttribute("aria-label", "Réponse copiée");
    btn.setAttribute("title", "Copié !");
    setTimeout(() => {
      btn.innerHTML = ICONS.copy;
      btn.classList.remove("is-copied");
      btn.setAttribute("aria-label", "Copier la réponse");
      btn.setAttribute("title", "Copier");
      delete btn.dataset.copying;
    }, COPY_FEEDBACK_MS);
  });
  row.querySelector('[data-action="regenerate"]')?.addEventListener("click", () => regenerate());
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
  row.querySelector('[data-action="report"]')?.addEventListener("click", () => {
    const index = activeMessages.indexOf(msg);
    let userMessage = "";
    for (let i = index - 1; i >= 0; i -= 1) {
      if (activeMessages[i].role === "user") {
        userMessage = activeMessages[i].content || "";
        break;
      }
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

// ── Actions sous un message UTILISATEUR (Copier/Modifier) ──────────────────
// Écrit via navigator.clipboard.writeText comme le bouton copier de
// l'assistant (ligne ~584) — jamais touché ici, voir la contrainte "ne pas
// modifier les actions assistant". Erreur gérée explicitement (presse-papiers
// indisponible : contexte non sécurisé, permission refusée, API absente),
// contrairement au bouton assistant qui n'a jamais eu ce cas géré — on ne
// corrige pas son code existant, seul le nouveau bouton a ce traitement.
async function copyPlainText(text) {
  if (!navigator.clipboard?.writeText) throw new Error("Presse-papiers indisponible");
  await navigator.clipboard.writeText(text);
}

function autosizeEditTextarea(el) {
  el.style.height = "auto";
  el.style.height = `${el.scrollHeight}px`;
}

// Un seul éditeur de message ouvert à la fois (comme ChatGPT) — en ouvrir un
// second annule proprement le premier plutôt que de laisser deux brouillons
// actifs simultanément.
let activeMessageEditor = null;

function bindUserMessageActions(row, msg) {
  const bubbleEl = row.querySelector(".chatbot-msg-bubble");
  const actionsEl = row.querySelector(".chatbot-msg-actions--user");

  actionsEl.querySelector('[data-action="copy-user"]')?.addEventListener("click", (e) => {
    const btn = e.currentTarget;
    if (btn.dataset.copying) return;
    copyPlainText(msg.content || "")
      .then(() => {
        btn.dataset.copying = "1";
        btn.innerHTML = ICONS.check;
        btn.classList.add("is-copied");
        btn.setAttribute("aria-label", "Message copié");
        btn.setAttribute("title", "Copié !");
        setTimeout(() => {
          btn.innerHTML = ICONS.copy;
          btn.classList.remove("is-copied");
          btn.setAttribute("aria-label", "Copier le message");
          btn.setAttribute("title", "Copier");
          delete btn.dataset.copying;
        }, COPY_FEEDBACK_MS);
      })
      .catch(() => {
        btn.setAttribute("title", "Copie impossible sur ce navigateur");
        btn.setAttribute("aria-label", "Copie impossible sur ce navigateur");
        setTimeout(() => {
          btn.setAttribute("title", "Copier");
          btn.setAttribute("aria-label", "Copier le message");
        }, COPY_FEEDBACK_MS);
      });
  });

  actionsEl.querySelector('[data-action="edit-user"]')?.addEventListener("click", () => {
    openMessageEditor(row, bubbleEl, actionsEl, msg);
  });
}

function closeMessageEditor(row, bubbleEl, actionsEl, msg, { restoreFocus = true } = {}) {
  row.classList.remove("is-editing");
  bubbleEl.classList.remove("chatbot-msg-bubble--editing");
  renderMessageBody(bubbleEl, msg.content || "");
  actionsEl.innerHTML = userMessageActionsButtonsHtml(msg);
  bindUserMessageActions(row, msg);
  if (activeMessageEditor?.row === row) activeMessageEditor = null;
  if (restoreFocus) actionsEl.querySelector('[data-action="edit-user"]')?.focus();
}

function openMessageEditor(row, bubbleEl, actionsEl, msg) {
  if (isStreaming) return; // section 5 : jamais d'édition pendant une génération active
  if (row.classList.contains("is-editing")) return;
  // Un brouillon déjà ouvert ailleurs est annulé sans confirmation (aucune
  // donnée n'y est jamais persistée, voir openMessageEditor/closeMessageEditor
  // — rien à perdre qui ait une valeur au-delà de cette session d'édition).
  if (activeMessageEditor) {
    closeMessageEditor(
      activeMessageEditor.row,
      activeMessageEditor.bubbleEl,
      activeMessageEditor.actionsEl,
      activeMessageEditor.msg,
      { restoreFocus: false },
    );
  }

  const originalContent = msg.content || "";
  row.classList.add("is-editing");
  bubbleEl.classList.add("chatbot-msg-bubble--editing");
  bubbleEl.innerHTML = `<textarea class="chatbot-msg-edit-textarea" aria-label="Modifier le message"></textarea>`;
  const textarea = bubbleEl.querySelector("textarea");
  textarea.value = originalContent; // valeur posée en JS, jamais interpolée dans le HTML (texte arbitraire de l'élève)

  actionsEl.innerHTML = `
    <button type="button" class="btn btn-ghost btn-sm" data-action="edit-cancel">Annuler</button>
    <button type="button" class="btn btn-primary btn-sm" data-action="edit-submit">Envoyer</button>`;
  const cancelBtn = actionsEl.querySelector('[data-action="edit-cancel"]');
  const submitBtn = actionsEl.querySelector('[data-action="edit-submit"]');

  activeMessageEditor = { row, bubbleEl, actionsEl, msg };

  autosizeEditTextarea(textarea);
  textarea.addEventListener("input", () => {
    textarea.classList.remove("is-invalid");
    autosizeEditTextarea(textarea);
    // Un nouvel essai n'a de sens qu'après un changement réel du texte —
    // tant que rien n'a bougé, le bouton reste désactivé (voir plus bas :
    // on ne le réactive JAMAIS juste après l'avoir désactivé, sinon deux
    // clics synchrones contourneraient la garde anti-double-soumission).
    submitBtn.disabled = false;
    actionsEl.querySelector(".chatbot-msg-edit-notice")?.remove();
  });
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      closeMessageEditor(row, bubbleEl, actionsEl, msg);
    }
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      submitBtn.click();
    }
  });
  textarea.focus();
  textarea.setSelectionRange(textarea.value.length, textarea.value.length);

  cancelBtn.addEventListener("click", () => closeMessageEditor(row, bubbleEl, actionsEl, msg));

  submitBtn.addEventListener("click", () => {
    if (submitBtn.disabled) return; // anti double-soumission : reste désactivé jusqu'à une vraie modification du texte (voir l'écouteur "input" ci-dessus)
    const newText = textarea.value.trim();
    if (!newText) {
      textarea.classList.add("is-invalid");
      textarea.focus();
      return;
    }
    submitBtn.disabled = true;
    // ── Pas de régénération réelle ici, volontairement ──────────────────
    // Auditer db.py/server.py (chantier "Copier/Modifier", 2026-10-18) a
    // confirmé qu'aucune route n'existe pour mettre à jour le contenu d'un
    // message existant ni pour supprimer plusieurs messages à la suite —
    // seules add_message (ajout en fin d'historique) et delete_message
    // (suppression PAR id, usage interne de regenerate_last/retry_last) sont
    // disponibles. Réutiliser ces primitives depuis le frontend produirait
    // soit un doublon visible dans l'historique (ancien message jamais
    // retiré), soit une suppression de messages réels sans confirmation
    // explicite de l'utilisateur — les deux sont explicitement interdits.
    // Tant qu'un contrat d'API dédié n'est pas approuvé (voir le rapport),
    // on ne simule pas un faux succès : aucune mutation de activeMessages,
    // aucun appel réseau, un message explicite à la place.
    const notice = document.createElement("p");
    notice.className = "chatbot-msg-edit-notice";
    notice.setAttribute("role", "status");
    notice.textContent =
      "Cette fonctionnalité nécessite une évolution du backend, pas encore approuvée — rien n'a été modifié.";
    actionsEl.appendChild(notice);
  });
}

// ── Streaming ────────────────────────────────────────────────────────────────
function setStreamingUI(streaming) {
  isStreaming = streaming;
  sendBtn.classList.toggle("is-stop", streaming);
  sendBtn.disabled = !streaming && composer.isEmpty(input);
  sendBtn.innerHTML = streaming ? ICONS.square : ICONS.arrowRight;
  // Le nom accessible doit refléter l'action RÉELLE du bouton, pas rester
  // bloqué sur "Envoyer" une fois son icône/rôle basculés sur "Arrêter".
  sendBtn.setAttribute("aria-label", streaming ? "Arrêter la génération" : "Envoyer");
  // "Régénérer" sur un message déjà persisté ne peut rien faire tant qu'une
  // génération est en cours ailleurs dans la conversation (regenerate()
  // l'ignorerait silencieusement) — le rendre visuellement explicite plutôt
  // que de laisser un clic sans effet.
  messagesEl.querySelectorAll('[data-action="regenerate"]').forEach((btn) => {
    btn.disabled = streaming;
  });
  // Section 5 (chantier Copier/Modifier) : une édition ne doit jamais entrer
  // en conflit avec une génération déjà active — même garde que "Régénérer".
  messagesEl.querySelectorAll('[data-action="edit-user"]').forEach((btn) => {
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
    const controller = {
      push(text) {
        target += text;
      },
      finish(callback) {
        const wasNearBottom = isNearBottom();
        bubbleEl.classList.remove("is-streaming");
        renderMessageBody(bubbleEl, target);
        autoScrollIfNearBottom(wasNearBottom);
        callback(target);
      },
      // Annulation (bouton stop) : avant ce correctif, rien ne retirait
      // jamais l'indicateur "Mathadap réfléchit…" dans ce cas (seul `finish`
      // le faisait) — il restait affiché indéfiniment. On rend visible le
      // texte déjà reçu, s'il y en a.
      cancel() {
        bubbleEl.classList.remove("is-streaming");
        renderMessageBody(bubbleEl, target || "*Réponse interrompue.*");
      },
    };
    bubbleEl._chatbotTypewriter = controller;
    return controller;
  }

  let shown = "";
  let target = "";
  let doneReceiving = false;
  let onFullyDone = null;
  let settled = false; // garantit un unique rendu riche (markdown+KaTeX), à la toute fin

  const timer = setInterval(() => {
    if (shown.length < target.length) {
      const wasNearBottom = isNearBottom();
      shown = target.slice(0, shown.length + TYPEWRITER_CHARS_PER_TICK);
      renderTypewriterTick(bubbleEl, shown);
      autoScrollIfNearBottom(wasNearBottom);
    }
    // Vérifié à CHAQUE tick (pas seulement dans un `else`) : que le
    // rattrapage vienne de se terminer à l'instant ou qu'il ait déjà fini un
    // tick plus tôt (le flux s'est terminé entre deux tops d'horloge), ce
    // test unique couvre les deux cas sans jamais déclencher le rendu riche
    // deux fois.
    if (doneReceiving && shown.length >= target.length && !settled) {
      settled = true;
      clearInterval(timer);
      bubbleEl.classList.remove("is-streaming");
      renderMessageBody(bubbleEl, shown);
      onFullyDone?.(shown);
    }
  }, TYPEWRITER_INTERVAL_MS);

  const controller = {
    push(text) {
      target += text;
    },
    finish(callback) {
      doneReceiving = true;
      onFullyDone = callback;
    },
    // Même correctif que ci-dessus pour le cas "machine à écrire" : sans
    // ceci, l'intervalle continuait de tourner indéfiniment après un stop
    // (plus aucun `push` ne vient jamais l'arrêter) et le curseur clignotant
    // (`.is-streaming`) restait affiché pour toujours.
    cancel() {
      if (settled) return;
      settled = true;
      clearInterval(timer);
      bubbleEl.classList.remove("is-streaming");
      renderMessageBody(bubbleEl, shown || "*Réponse interrompue.*");
    },
  };
  bubbleEl._chatbotTypewriter = controller;
  return controller;
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
      } catch {
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

// role="status" + aria-live="polite" : annoncé une seule fois par un lecteur
// d'écran dès son insertion, puis silencieux (le noeud est entièrement
// remplacé — jamais mis à jour en place — dès l'arrivée du premier contenu,
// donc aucune annonce répétée pendant le streaming).
// Trois points violets animés en cascade (pattern "en train d'écrire"
// classique), remplace l'ancienne pastille unique — plus proche de ce
// qu'on attend d'un indicateur de réflexion et plus clairement animé.
// prefers-reduced-motion/Paramètres→Animations="off" sont déjà gérés
// globalement (voir tokens.css) : aucune logique spécifique nécessaire ici.
const THINKING_HTML =
  '<div class="chatbot-thinking" role="status" aria-live="polite" aria-label="Mathadap réfléchit"><span class="chatbot-thinking-dots" aria-hidden="true"><span></span><span></span><span></span></span><span class="chatbot-thinking-label visually-hidden">Mathadap réfléchit…</span></div>';

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
  bubbleEl.classList.remove("chatbot-msg-bubble--thinking");
  bubbleEl.innerHTML = `
    <div class="chatbot-error-state">
      <span aria-hidden="true">${ICONS.alertTriangle}</span>
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
  retryBtn.addEventListener(
    "click",
    () => {
      retryBtn.disabled = true;
      onRetry();
    },
    { once: true },
  );
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
    if (err.name === "AbortError") {
      // L'annulation peut survenir avant même que le flux SSE ne soit ouvert
      // (abort pendant le fetch initial) : dans ce cas startTypewriter n'a
      // jamais tourné, donc pas de typewriter à annuler — la bulle contient
      // encore THINKING_HTML qu'il faut retirer directement.
      if (bubbleEl._chatbotTypewriter) bubbleEl._chatbotTypewriter.cancel();
      else renderMessageBody(bubbleEl, "*Réponse interrompue.*");
      return;
    }
    if (err.isQuotaExceeded) {
      // 429 renvoyé avant même l'ouverture du flux (voir
      // server.py::peek_exceeded) : rien n'a été persisté côté serveur, donc
      // rien à recharger. Le toast + la redirection sont déjà déclenchés de
      // façon centralisée (voir api.js::buildApiError/handleQuotaExceeded) —
      // ici on finalise juste la bulle assistant avec un message explicite,
      // jamais l'erreur brute, jamais l'état "Réessayer" (retenter ne
      // débloquerait rien avant demain ou une mise à niveau).
      renderMessageBody(
        bubbleEl,
        "*Tu as atteint ta limite de messages aujourd'hui — redirection vers la page Abonnement…*",
      );
      return;
    }
    let lastIsUser = true;
    try {
      const { messages } = await api.chatbotMessages(convId);
      activeMessages = messages;
      lastIsUser = !messages.length || messages[messages.length - 1].role === "user";
    } catch {
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
  bubbleEl.classList.add("chatbot-msg-bubble--thinking");
  refreshChatbotStreamingSetting();
  await runAssistantTurn(
    convId,
    bubbleEl,
    (signal) => api.chatbotRetryStream(convId, { signal, classLevel: getStoredClassLevel() }),
    () => retryReply(convId, bubbleEl),
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
  bubbleEl.classList.add("chatbot-msg-bubble--thinking");
  forceScrollToBottom();

  refreshChatbotStreamingSetting();
  await runAssistantTurn(
    convId,
    bubbleEl,
    (signal) => api.chatbotStream(convId, text, mentions, { signal, classLevel: getStoredClassLevel() }),
    () => retryReply(convId, bubbleEl),
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
  bubbleEl.classList.add("chatbot-msg-bubble--thinking");

  await runAssistantTurn(
    convId,
    bubbleEl,
    (signal) => api.chatbotRegenerateStream(convId, { signal, classLevel: getStoredClassLevel() }),
    () => retryReply(convId, bubbleEl),
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
  liveSuggestions.innerHTML = results
    .slice(0, 4)
    .map(
      (r, i) => `
    <button type="button" class="chatbot-suggestion-chip" data-index="${i}">${escapeHtml(r.title)}</button>
  `,
    )
    .join("");
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
    insertIntoInput(`[Extrait de "${filename}"${truncated ? " (tronqué, document long)" : ""}]\n${text}`);
  } catch (err) {
    // 403 "premium_required" (analyse de PDF réservée à Ultra, voir
    // plan_service.Feature.ADVANCED_AI) : jamais afficher err.message brut
    // ("premium_required") — un message explicite + un lien direct vers
    // l'offre correspondante, jamais une erreur technique à l'écran.
    if (err.isPremiumRequired) {
      const planLabel = err.requiredPlan === "ultra" ? "Ultra" : "Premium";
      insertIntoInput(
        `[${featureLabel(err.feature)} fait partie de la formule ${planLabel}. ` +
          `Découvre l'offre ${planLabel} sur la page Abonnement pour débloquer l'analyse de documents joints.]`,
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
    "[Image jointe — Mathadap ne peut pas encore analyser automatiquement une image. Décris ce qu'elle contient (énoncé, figure...) pour que je puisse t'aider.]",
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
      providerBannerMsg.textContent =
        health.detail || "Le service d'intelligence artificielle n'est pas disponible pour le moment.";
      providerBanner.hidden = false;
    }
  } catch {
    /* silencieux : ne bloque jamais le reste de la page */
  }
}
$("chatbot-provider-retry").addEventListener("click", checkProviderHealth);
$("chatbot-provider-dismiss").addEventListener("click", () => {
  providerBanner.hidden = true;
});

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
    quotaIndicator.classList.toggle(
      "is-low",
      !chat.unlimited && chat.remaining > 0 && chat.remaining <= Math.ceil(chat.limit * 0.15),
    );
    quotaValue.innerHTML = chat.unlimited
      ? 'Illimité <span aria-hidden="true">∞</span>'
      : `${chat.used} / ${chat.limit} messages`;
  } catch {
    /* silencieux : l'indicateur reste dans son dernier état connu */
  }
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
  chips.innerHTML = questions
    .map((q) => `<button class="chatbot-suggestion-chip" type="button">${escapeHtml(q)}</button>`)
    .join("");
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
        `Mon objectif du jour : ${goals.done_exercises}/${goals.target_exercises} exercices${goals.reached ? " (atteint)" : ""}. `,
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
