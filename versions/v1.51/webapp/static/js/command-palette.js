// ── Command Palette globale (Ctrl+K / Cmd+K), façon Cursor/Notion ──────────
// Chargée sur toutes les pages "app shell" (voir liste des <script> dans les
// pages HTML) : recherche unifiée sur le contenu réel (api.search, Phase A)
// mêlée à des raccourcis de navigation statiques. Réutilise popup.js pour la
// modale (aucun système de dialogue réinventé).
import { openPopup } from "./popup.js";
import { api } from "./api.js";
import { t } from "./i18n.js";

const STATIC_COMMANDS = [
  { title: "Dashboard", subtitle: "cmd_palette_dashboard", url: "dashboard.html" },
  { title: "Cours", subtitle: "cmd_palette_cours", url: "cours.html" },
  { title: "Chapitres", subtitle: "cmd_palette_chapitres", url: "chapitres.html" },
  { title: "Entraînement", subtitle: "cmd_palette_entrainement", url: "exercice.html" },
  { title: "Chatbot", subtitle: "cmd_palette_chatbot", url: "chatbot.html" },
  { title: "Profil", subtitle: "cmd_palette_profil", url: "profil.html" },
];

function staticCommandsTranslated() {
  return STATIC_COMMANDS.map((c) => ({ ...c, subtitle: t(c.subtitle, "") }));
}

function renderList(container, items, onPick) {
  container.innerHTML = items.length
    ? items.map((it, i) => `
      <button type="button" class="command-palette-item" data-index="${i}">
        <span class="title">${it.title}</span>
        <span class="subtitle">${it.subtitle || ""}</span>
      </button>`).join("")
    : `<div class="command-palette-empty">${t("cmd_palette_no_result", "Aucun résultat")}</div>`;
  container.querySelectorAll("[data-index]").forEach((btn) => {
    btn.addEventListener("click", () => onPick(items[Number(btn.dataset.index)]));
  });
}

function open() {
  const wrap = document.createElement("div");
  wrap.className = "command-palette";
  wrap.innerHTML = `
    <div class="command-palette-input-row">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input type="text" id="command-palette-input" placeholder="${t("cmd_palette_placeholder", "Rechercher ou naviguer…")}" autocomplete="off">
    </div>
    <div class="command-palette-results" id="command-palette-results"></div>
  `;
  const { close } = openPopup({ id: "command-palette-popup", bodyEl: wrap, size: "md", showCloseButton: false });
  const input = wrap.querySelector("#command-palette-input");
  const results = wrap.querySelector("#command-palette-results");

  const pick = (item) => {
    close();
    window.location.href = item.url;
  };
  renderList(results, staticCommandsTranslated(), pick);
  input.focus();

  let timer = null;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (!q) return renderList(results, staticCommandsTranslated(), pick);
    timer = setTimeout(async () => {
      try {
        const { results: hits } = await api.search(q, null, 8);
        const mapped = hits.map((r) => ({
          title: r.title,
          subtitle: (r.snippet || "").slice(0, 70),
          url: r.url || "chapitres.html",
        }));
        const matchingStatic = staticCommandsTranslated().filter((c) =>
          c.title.toLowerCase().includes(q.toLowerCase())
        );
        renderList(results, [...matchingStatic, ...mapped], pick);
      } catch {
        /* silencieux */
      }
    }, 250);
  });
}

export function initCommandPalette() {
  document.addEventListener("keydown", (e) => {
    const key = e.key.toLowerCase();
    if ((e.ctrlKey || e.metaKey) && key === "k") {
      e.preventDefault();
      open();
    }
  });
}

initCommandPalette();
