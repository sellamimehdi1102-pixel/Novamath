// ── Palette de commandes "@" du chatbot ──────────────────────────────────────
// Une seule source de vérité pour les correspondances : GET /api/chatbot/mentions
// (chatbot/services/mentions_service.py) — catégories de page réelles +
// ressources (cours/exercices, avec repli flou pour les fautes de frappe côté
// backend). Ce module ne fait AUCUNE correspondance lui-même : il affiche,
// débounce, gère le clavier/la souris et délègue la résolution au backend.
import { api } from "./api.js";
import { t } from "./i18n.js";
import * as composer from "./chatbot-composer.js";

const DEBOUNCE_MS = 200;

const CATEGORY_ICONS = {
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
  nav: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  goals: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  action: '<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>',
};

function iconFor(item) {
  return CATEGORY_ICONS[item.kind] || CATEGORY_ICONS.search;
}

/** Trouve, dans le nœud texte contenant le curseur, la position du dernier
 * "@" ouvrant une mention en cours de frappe (pas de retour arrière dans
 * l'historique du texte : seul un "@" fraîchement tapé ouvre le menu). */
function findTriggerStart(node, caretOffset) {
  const text = node.data.slice(0, caretOffset);
  const at = text.lastIndexOf("@");
  if (at === -1) return -1;
  // Doit être en début de champ ou précédé d'un espace/retour à la ligne.
  if (at > 0 && !/\s/.test(text[at - 1])) return -1;
  return at;
}

export function initMentions({ input, onNavigate, onAction }) {
  const menu = document.createElement("div");
  menu.className = "chatbot-mentions-menu";
  menu.hidden = true;
  const wrap = input.closest(".chatbot-input-wrap") || input.parentElement;
  wrap.style.position = wrap.style.position || "relative";
  wrap.appendChild(menu);

  // state : { node, atOffset, items, activeIndex, didYouMean } | null
  let state = null;
  let debounceTimer = null;

  function isOpen() {
    return !!state;
  }

  function close() {
    state = null;
    clearTimeout(debounceTimer);
    menu.hidden = true;
    menu.innerHTML = "";
  }

  function currentCaret() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || !sel.isCollapsed) return null;
    const range = sel.getRangeAt(0);
    if (range.startContainer.nodeType !== Node.TEXT_NODE) return null;
    if (!input.contains(range.startContainer)) return null;
    return { node: range.startContainer, offset: range.startOffset };
  }

  function renderLoading() {
    menu.innerHTML = `<div class="chatbot-mentions-empty">${t("chatbot_mentions_searching", "Recherche…")}</div>`;
    menu.hidden = false;
  }

  function renderEmpty(didYouMean) {
    if (didYouMean) {
      menu.innerHTML = `
        <button type="button" class="chatbot-mentions-item" data-suggest="1">
          <span class="title">${t("chatbot_mentions_did_you_mean", "Voulez-vous dire")} : ${didYouMean.title} ?</span>
        </button>`;
      menu.querySelector("[data-suggest]").addEventListener("click", () => selectItem(didYouMean));
    } else {
      menu.innerHTML = `<div class="chatbot-mentions-empty">${t("chatbot_mentions_no_result", "Aucune ressource trouvée.")}</div>`;
    }
    menu.hidden = false;
  }

  function renderItems(items) {
    state.items = items;
    state.activeIndex = items.length ? 0 : -1;
    menu.innerHTML = items.map((it, i) => `
      <button type="button" class="chatbot-mentions-item${i === 0 ? " is-active" : ""}" data-index="${i}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${iconFor(it)}</svg>
        <span class="chatbot-mentions-item-text">
          <span class="title">${it.item_kind === "category" ? "@" + it.label : it.title}</span>
          ${it.snippet ? `<span class="subtitle">${it.snippet.slice(0, 70)}</span>` : ""}
        </span>
      </button>`).join("");
    menu.hidden = false;
    menu.querySelectorAll("[data-index]").forEach((btn) => {
      btn.addEventListener("click", () => selectItem(items[Number(btn.dataset.index)]));
      btn.addEventListener("mouseenter", () => setActive(Number(btn.dataset.index)));
    });
  }

  function setActive(index) {
    if (!state || !state.items.length) return;
    state.activeIndex = index;
    menu.querySelectorAll(".chatbot-mentions-item").forEach((el, i) => {
      el.classList.toggle("is-active", i === index);
    });
    menu.querySelector(".is-active")?.scrollIntoView({ block: "nearest" });
  }

  async function runQuery(query) {
    renderLoading();
    try {
      const { items, did_you_mean } = await api.chatbotMentions(query, 8);
      if (!state) return; // fermé entre-temps
      if (!items.length) return renderEmpty(did_you_mean);
      renderItems(items);
    } catch {
      if (state) renderEmpty(null);
    }
  }

  function scheduleQuery(query) {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => runQuery(query), DEBOUNCE_MS);
  }

  function selectItem(item) {
    if (!state) return;
    const { node, atOffset, caretOffset } = state;
    if (item.item_kind === "category") {
      composer.removeRange(node, atOffset, caretOffset);
      close();
      if (item.kind === "nav") {
        (onNavigate || ((url) => { window.location.href = url; }))(item.url);
      } else if (item.kind === "goals") {
        onAction ? onAction("goals") : null;
      } else if (item.kind === "action") {
        onAction ? onAction(item.action, item.url) : null;
      }
      return;
    }
    // Ressource (cours/exercice) : insertion d'un badge, on reste dans la conversation.
    const chip = composer.createMentionChip({
      type: item.type,
      chapter_id: item.chapter_id,
      notion_id: item.notion_id,
      exercise_id: item.exercise_id,
      label: item.title,
    });
    composer.replaceRangeWithNode(node, atOffset, caretOffset, chip);
    close();
    input.dispatchEvent(new Event("input"));
  }

  input.addEventListener("input", () => {
    const caret = currentCaret();
    if (!caret) return close();

    if (state && state.node === caret.node && caret.offset >= state.atOffset) {
      const raw = caret.node.data.slice(state.atOffset, caret.offset);
      if (!raw.startsWith("@") || raw.includes("\n")) return close();
      state.caretOffset = caret.offset;
      scheduleQuery(raw.slice(1));
      return;
    }

    const atOffset = findTriggerStart(caret.node, caret.offset);
    if (atOffset === -1) return close();
    state = { node: caret.node, atOffset, caretOffset: caret.offset, items: [], activeIndex: -1 };
    scheduleQuery(caret.node.data.slice(atOffset + 1, caret.offset));
  });

  input.addEventListener("keydown", (e) => {
    if (!isOpen()) return;
    if (e.key === "Escape") {
      close();
      e.preventDefault();
      return;
    }
    if (e.key === "ArrowDown") {
      if (state.items.length) setActive((state.activeIndex + 1) % state.items.length);
      e.preventDefault();
      return;
    }
    if (e.key === "ArrowUp") {
      if (state.items.length) setActive((state.activeIndex - 1 + state.items.length) % state.items.length);
      e.preventDefault();
      return;
    }
    if (e.key === "Enter" || e.key === "Tab") {
      if (state.items.length && state.activeIndex >= 0) {
        selectItem(state.items[state.activeIndex]);
      } else {
        close();
      }
      e.preventDefault();
    }
  });

  document.addEventListener("click", (e) => {
    if (state && !menu.hidden && !e.target.closest(".chatbot-mentions-menu") && e.target !== input) close();
  });

  return { isOpen };
}
