// ── Palette de commandes "@" du chatbot ──────────────────────────────────────
// Détecte "@" tapé dans la zone de saisie, propose des catégories réelles
// (Cours/Exercices/Notions cherchent vraiment dans /api/search — Phase A ;
// Dashboard/Quiz/Progression/Statistiques/Objectifs ouvrent la vraie page ou
// affichent les vraies données, jamais un résultat inventé). Isolé de
// chatbot.js (déjà volumineux) — importé comme module ES classique.
import { api } from "./api.js";
import { t } from "./i18n.js";

const CATEGORIES = [
  { key: "cours", label: "@Cours", scope: "cours", mode: "search" },
  { key: "exercices", label: "@Exercices", scope: "exercices", mode: "search" },
  { key: "notions", label: "@Notions", scope: "cours", mode: "search" },
  { key: "dashboard", label: "@Dashboard", mode: "nav", url: "dashboard.html" },
  { key: "quiz", label: "@Quiz", mode: "nav", url: "evaluation.html" },
  { key: "progression", label: "@Progression", mode: "nav", url: "dashboard.html" },
  { key: "statistiques", label: "@Statistiques", mode: "nav", url: "dashboard.html" },
  { key: "objectifs", label: "@Objectifs", mode: "goals" },
];

const ICONS = {
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
  nav: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  goals: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
};

function iconFor(cat) {
  return ICONS[cat.mode] || ICONS.search;
}

/** Trouve le token "@..." en cours de frappe juste avant le curseur, ou null. */
function currentMentionToken(text, caret) {
  const before = text.slice(0, caret);
  const match = before.match(/(?:^|\s)@([^\s@]*)$/);
  if (!match) return null;
  return { start: before.length - match[0].length + (match[0][0] === "@" ? 0 : 1), query: match[1] };
}

export function initMentions({ input, onNavigate }) {
  const menu = document.createElement("div");
  menu.className = "chatbot-mentions-menu";
  menu.hidden = true;
  const wrap = input.closest(".chatbot-input-wrap") || input.parentElement;
  wrap.style.position = wrap.style.position || "relative";
  wrap.appendChild(menu);

  let state = null; // { tokenStart, category: null|cat, searchTimer }

  function close() {
    state = null;
    menu.hidden = true;
    menu.innerHTML = "";
  }

  function renderCategories(filterText) {
    const items = CATEGORIES.filter((c) => c.key.startsWith((filterText || "").toLowerCase()));
    menu.innerHTML = items.length
      ? items.map((c) => `
        <button type="button" class="chatbot-mentions-item" data-key="${c.key}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${iconFor(c)}</svg>
          <span>${c.label}</span>
        </button>`).join("")
      : `<div class="chatbot-mentions-empty">Aucune commande</div>`;
    menu.hidden = false;
    menu.querySelectorAll("[data-key]").forEach((btn) => {
      btn.addEventListener("click", () => selectCategory(CATEGORIES.find((c) => c.key === btn.dataset.key)));
    });
  }

  function replaceToken(replacement) {
    const value = input.value;
    const tokenEnd = state.caret ?? state.tokenStart + 1;
    input.value = value.slice(0, state.tokenStart) + replacement + value.slice(tokenEnd);
    const pos = state.tokenStart + replacement.length;
    input.setSelectionRange(pos, pos);
    input.dispatchEvent(new Event("input"));
  }

  async function selectCategory(cat) {
    if (!cat) return;
    if (cat.mode === "nav") {
      renderSingleCard({ title: cat.label.slice(1), subtitle: "Ouvrir la page", url: cat.url });
      state = { ...state, category: cat };
      return;
    }
    if (cat.mode === "goals") {
      try {
        const goals = await api.dailyGoals();
        renderSingleCard({
          title: "Objectif du jour",
          subtitle: `${goals.done_exercises}/${goals.target_exercises} exercices${goals.reached ? " — atteint" : ""}`,
          url: "dashboard.html",
        });
      } catch {
        close();
      }
      state = { ...state, category: cat };
      return;
    }
    // mode "search" : bascule en mode recherche, la frappe suivante filtre.
    state.category = cat;
    state.queryText = "";
    renderResults([]);
  }

  function renderSingleCard(card) {
    menu.innerHTML = `
      <button type="button" class="chatbot-mentions-item chatbot-mentions-card" data-nav="${card.url}">
        <span class="title">${card.title}</span>
        <span class="subtitle">${card.subtitle}</span>
      </button>`;
    menu.hidden = false;
    menu.querySelector("[data-nav]").addEventListener("click", (e) => {
      replaceToken("");
      close();
      onNavigate ? onNavigate(e.currentTarget.dataset.nav) : (window.location.href = e.currentTarget.dataset.nav);
    });
  }

  function renderResults(results) {
    menu.innerHTML = results.length
      ? results.map((r, i) => `
        <button type="button" class="chatbot-mentions-item" data-index="${i}">
          <span class="title">${r.title}</span>
          <span class="subtitle">${(r.snippet || "").slice(0, 70)}</span>
        </button>`).join("")
      : `<div class="chatbot-mentions-empty">${t("chatbot_mentions_type_to_search", "Continue à écrire pour chercher…")}</div>`;
    menu.hidden = false;
    menu.querySelectorAll("[data-index]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const r = results[Number(btn.dataset.index)];
        replaceToken(`[${state.category.label.slice(1)}: ${r.title}] `);
        close();
      });
    });
  }

  async function runSearch(query) {
    if (!query || query.length < 2) return renderResults([]);
    try {
      const { results } = await api.search(query, state.category.scope, 6);
      if (state) renderResults(results);
    } catch {
      /* silencieux */
    }
  }

  input.addEventListener("input", () => {
    const caret = input.selectionStart;

    // Catégorie déjà choisie : on reste en mode recherche tant que le curseur
    // n'a pas quitté la zone du "@" (le texte peut contenir des espaces, ex.
    // "@Cours fonction affine" — la requête est tout ce qui suit le 1er mot).
    if (state && state.category && caret >= state.tokenStart) {
      state.caret = caret;
      const raw = input.value.slice(state.tokenStart, caret);
      if (!raw.startsWith("@")) return close();
      const spaceIdx = raw.indexOf(" ");
      state.queryText = spaceIdx === -1 ? "" : raw.slice(spaceIdx + 1);
      if (state.category.mode === "search") {
        clearTimeout(state.searchTimer);
        state.searchTimer = setTimeout(() => runSearch(state.queryText), 250);
      }
      return;
    }

    const token = currentMentionToken(input.value, caret);
    if (!token) return close();
    if (!state || state.tokenStart !== token.start) {
      state = { tokenStart: token.start, category: null, queryText: "" };
    }
    state.caret = caret;
    renderCategories(token.query);
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && state) close();
  });
  document.addEventListener("click", (e) => {
    if (state && !menu.hidden && !e.target.closest(".chatbot-mentions-menu") && e.target !== input) close();
  });
}
