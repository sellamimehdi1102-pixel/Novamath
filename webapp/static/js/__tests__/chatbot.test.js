// ── chatbot.js : chat IA (conversations, envoi de message, quota, santé du
// fournisseur/reconnexion). Module purement piloté par le DOM (aucun export) —
// on charge donc le vrai corps de chatbot.html et on observe le DOM résultant.
// chatbot-composer.js (contenteditable <-> texte) est un utilitaire DOM pur
// sans appel réseau : jamais mocké, utilisé tel quel (comme en production).
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { loadPageBody, flushPromises, withMockedLocation } from "./testUtils.js";
import { extractMathSegments, restoreMathSegments, setRenderedHtmlContent } from "../mathrender.js"; // résolu vers le mock (vi.mock ci-dessous)

const __dirname = dirname(fileURLToPath(import.meta.url));

const mockApi = {
  chatbotConversations: vi.fn(),
  chatbotCreateConversation: vi.fn(),
  chatbotQuota: vi.fn(),
  getQuota: vi.fn(),
  chatbotGreeting: vi.fn(),
  chatbotHealth: vi.fn(),
  chatbotStream: vi.fn(),
  chatbotMessages: vi.fn(),
  chatbotFeedback: vi.fn(),
  handleQuotaExceeded: vi.fn(),
  getSettings: vi.fn(),
};

// ── Simule une réponse SSE (voir chatbot.js::consumeStream) sans dépendre
// d'un vrai réseau : un lecteur qui restitue chaque payload déjà encodé en
// "data: {...}\n\n", exactement le format que le backend produit.
function sseChunk(payload) {
  return `data: ${JSON.stringify(payload)}\n\n`;
}
// Le "machine à écrire" (chatbot.js::startTypewriter) tourne sur un vrai
// setInterval de 15ms : on attend en temps réel plutôt que d'utiliser des
// fake timers (qui feraient aussi patienter indéfiniment `flushPromises`,
// lequel repose lui-même sur un vrai `setTimeout`).
function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function makeStreamResponse(payloads) {
  const encoder = new TextEncoder();
  let i = 0;
  return {
    body: {
      getReader: () => ({
        read: () => {
          if (i >= payloads.length) return Promise.resolve({ done: true, value: undefined });
          const value = encoder.encode(sseChunk(payloads[i]));
          i += 1;
          return Promise.resolve({ done: false, value });
        },
      }),
    },
  };
}
vi.mock("../api.js", () => ({ api: mockApi, handleQuotaExceeded: mockApi.handleQuotaExceeded }));
vi.mock("../settingsManager.js", () => ({ initSettingsManager: () => Promise.resolve() }));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn(), t: (key, fallback) => fallback ?? key }));
// extractMathSegments/restoreMathSegments : stubs transparents (aucune
// protection réelle) pour les tests qui ne portent pas sur le rendu LaTeX —
// voir le describe dédié "rendu des formules mathématiques" plus bas, qui
// démonte ce mock pour exercer les VRAIES fonctions de mathrender.js.
vi.mock("../mathrender.js", () => ({
  setRenderedHtmlContent: vi.fn((el, text) => { el.textContent = text; }),
  extractMathSegments: vi.fn((text) => ({ text, segments: [] })),
  restoreMathSegments: vi.fn((html) => html),
}));
vi.mock("../chatbot-mentions.js", () => ({
  initMentions: vi.fn(() => ({ isOpen: () => false, dispose: vi.fn() })),
}));
vi.mock("../popup.js", () => ({ openPromptPopup: vi.fn(), openConfirmPopup: vi.fn() }));
vi.mock("../curriculumSelector.js", () => ({ getStoredClassLevel: () => "seconde" }));
vi.mock("../features.js", () => ({ featureLabel: (f) => f }));

function defaultMocks() {
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.chatbotConversations.mockResolvedValue({ conversations: [] });
  mockApi.getQuota.mockResolvedValue({ chat_messages: { unlimited: true } });
  mockApi.chatbotGreeting.mockResolvedValue({ greeting: "Bonjour !" });
  mockApi.chatbotHealth.mockResolvedValue({ ok: true });
  mockApi.chatbotCreateConversation.mockResolvedValue({ conversation: { id: 1 } });
  mockApi.chatbotMessages.mockResolvedValue({ messages: [] });
  mockApi.chatbotFeedback.mockResolvedValue({});
  // Réglage "Affichage progressif" (Paramètres → Chatbot, chatbot.js::
  // refreshChatbotStreamingSetting) : activé par défaut, comme la valeur par
  // défaut réelle (auth.DEFAULT_SETTINGS.chatbot.streaming = True) — voir le
  // describe dédié ci-dessous pour la valeur "false".
  mockApi.getSettings.mockResolvedValue({ chatbot: { streaming: true } });
}

async function mountChatbot() {
  document.body.innerHTML = loadPageBody("chatbot.html");
  defaultMocks();
  vi.resetModules();
  await import("../chatbot.js");
  await flushPromises();
}

const $ = (id) => document.getElementById(id);

describe("chatbot.js — état initial", () => {
  beforeEach(async () => {
    await mountChatbot();
  });

  it("affiche l'état vide (aucune conversation active)", () => {
    expect($("chatbot-empty-state").hidden).toBeFalsy();
  });

  it("le bouton d'envoi est désactivé tant que le composeur est vide", () => {
    expect($("chatbot-send-btn").disabled).toBe(true);
  });

  it("charge et affiche l'indicateur de quota illimité", () => {
    expect($("chatbot-quota-indicator").hidden).toBe(false);
    expect($("chatbot-quota-value").innerHTML).toContain("Illimité");
  });

  // Le panneau contextuel de droite ("Ton profil Mathadap") a été supprimé
  // (refonte UI/UX) : ces informations existent déjà dans le Dashboard.
  it("ne contient plus le panneau contextuel de droite", () => {
    expect($("chatbot-context-panel")).toBeNull();
  });

  it("affiche des suggestions de questions adaptées à la classe active", () => {
    const chips = document.querySelectorAll(".chatbot-suggestion-chip");
    expect(chips.length).toBeGreaterThan(0);
    // curriculumSelector.js est mocké sur "seconde" (ligne 29) : les chips
    // doivent correspondre au programme de Seconde, jamais à un autre niveau.
    const texts = Array.from(chips).map((c) => c.textContent);
    expect(texts.some((t) => /inéquation|vecteur|littérale/i.test(t))).toBe(true);
  });
});

describe("chatbot.js — composeur (contenteditable)", () => {
  beforeEach(async () => {
    await mountChatbot();
  });

  it("active le bouton d'envoi dès que du texte est saisi", () => {
    const input = $("chatbot-input");
    input.textContent = "Bonjour";
    input.dispatchEvent(new Event("input"));
    expect($("chatbot-send-btn").disabled).toBe(false);
  });

  it("redésactive le bouton d'envoi si le texte est vidé", () => {
    const input = $("chatbot-input");
    input.textContent = "x";
    input.dispatchEvent(new Event("input"));
    input.textContent = "";
    input.dispatchEvent(new Event("input"));
    expect($("chatbot-send-btn").disabled).toBe(true);
  });
});

describe("chatbot.js — liste des conversations", () => {
  it("affiche un message dédié si aucune conversation n'existe", async () => {
    await mountChatbot();
    expect($("chatbot-convo-list").innerHTML).toContain("Aucune conversation");
  });

  it("affiche chaque conversation avec son titre", async () => {
    document.body.innerHTML = loadPageBody("chatbot.html");
    defaultMocks();
    mockApi.chatbotConversations.mockResolvedValue({
      conversations: [{ id: 1, title: "Dérivées", pinned: false }, { id: 2, title: "Suites", pinned: true }],
    });
    vi.resetModules();
    await import("../chatbot.js");
    await flushPromises();
    expect($("chatbot-convo-list").textContent).toContain("Dérivées");
    expect($("chatbot-convo-list").textContent).toContain("Suites");
  });

  it("échappe le HTML du titre d'une conversation (anti-XSS)", async () => {
    document.body.innerHTML = loadPageBody("chatbot.html");
    defaultMocks();
    mockApi.chatbotConversations.mockResolvedValue({
      conversations: [{ id: 1, title: "<img src=x onerror=alert(1)>", pinned: false }],
    });
    vi.resetModules();
    await import("../chatbot.js");
    await flushPromises();
    expect($("chatbot-convo-list").innerHTML).not.toContain("<img src=x");
    expect($("chatbot-convo-list").innerHTML).toContain("&lt;img");
  });
});

describe("chatbot.js — barre latérale des conversations (mobile/collapse)", () => {
  beforeEach(async () => {
    await mountChatbot();
  });

  it("le bouton de repli bascule la classe is-collapsed", () => {
    const btn = $("chatbot-convos-collapse-btn");
    btn.click();
    expect($("chatbot-convos").classList.contains("is-collapsed")).toBe(true);
  });

  it("le déclencheur mobile ouvre le tiroir des conversations", () => {
    $("chatbot-convos-mobile-trigger").click();
    expect($("chatbot-convos").classList.contains("is-open")).toBe(true);
  });

  it("Nouvelle conversation et Rechercher restent fonctionnels une fois la sidebar réduite", () => {
    $("chatbot-convos-collapse-btn").click();
    expect($("chatbot-convos").classList.contains("is-collapsed")).toBe(true);
    expect($("chatbot-search-trigger").disabled).toBeFalsy();
    expect($("chatbot-new-btn").disabled).toBeFalsy();
  });
});

// jsdom ne charge/applique jamais les feuilles de style externes (voir le
// même type de test déjà utilisé pour l'animation plus bas) : seul le
// fichier CSS source peut être vérifié ici. La vraie disparition visuelle
// (et l'absence de clic/focus clavier qui en découle, via display:none)
// reste à confirmer dans un navigateur réel — voir le rapport final.
describe("chatbot.css — sidebar réduite : conversations non interactives (source CSS)", () => {
  const css = readFileSync(resolve(__dirname, "..", "..", "css", "chatbot.css"), "utf-8");

  it("masque tout le conteneur de la liste (pas seulement le titre/les actions de chaque item)", () => {
    // Avant ce correctif, seuls le titre et les actions de CHAQUE conversation
    // étaient masqués en mode réduit : la ligne elle-même restait dans le
    // flux, cliquable et focusable (display:none ne s'appliquait jamais au
    // conteneur .chatbot-convo-list lui-même) — exactement le bug remonté.
    // Les deux sélecteurs partagent UNE seule règle (liste séparée par
    // virgules) : on isole ce groupe de sélecteurs + sa déclaration.
    const start = css.indexOf(".chatbot-convos.is-collapsed .chatbot-convo-list-label");
    expect(start).toBeGreaterThan(-1);
    const end = css.indexOf("}", start);
    const rule = css.slice(start, end + 1);
    expect(rule).toContain(".chatbot-convos.is-collapsed .chatbot-convo-list-label");
    expect(rule).toContain(".chatbot-convos.is-collapsed .chatbot-convo-list {");
    expect(rule).toMatch(/display:\s*none/);
  });
});

describe("chatbot.js — santé du fournisseur IA / reconnexion", () => {
  it("masque la bannière si le fournisseur est disponible", async () => {
    await mountChatbot();
    expect($("chatbot-provider-banner").hidden).toBe(true);
  });

  it("affiche une bannière d'indisponibilité avec le détail du serveur", async () => {
    document.body.innerHTML = loadPageBody("chatbot.html");
    defaultMocks();
    mockApi.chatbotHealth.mockResolvedValue({ ok: false, detail: "Fournisseur IA hors service." });
    vi.resetModules();
    await import("../chatbot.js");
    await flushPromises();
    expect($("chatbot-provider-banner").hidden).toBe(false);
    expect($("chatbot-provider-banner-msg").textContent).toBe("Fournisseur IA hors service.");
  });

  it("le bouton Réessayer relance la vérification et masque la bannière si rétablie", async () => {
    document.body.innerHTML = loadPageBody("chatbot.html");
    defaultMocks();
    mockApi.chatbotHealth.mockResolvedValueOnce({ ok: false, detail: "Indisponible." });
    vi.resetModules();
    await import("../chatbot.js");
    await flushPromises();
    expect($("chatbot-provider-banner").hidden).toBe(false);

    mockApi.chatbotHealth.mockResolvedValueOnce({ ok: true });
    $("chatbot-provider-retry").click();
    await flushPromises();
    expect($("chatbot-provider-banner").hidden).toBe(true);
  });

  it("le bouton 'Continuer sans le chatbot' masque simplement la bannière", async () => {
    document.body.innerHTML = loadPageBody("chatbot.html");
    defaultMocks();
    mockApi.chatbotHealth.mockResolvedValue({ ok: false, detail: "Indisponible." });
    vi.resetModules();
    await import("../chatbot.js");
    await flushPromises();
    $("chatbot-provider-dismiss").click();
    expect($("chatbot-provider-banner").hidden).toBe(true);
  });
});

// ── Chantier UX phase 1 : indicateur de réflexion ───────────────────────────
describe("chatbot.js — indicateur de réflexion", () => {
  beforeEach(async () => {
    await mountChatbot();
  });

  function sendUserMessage(text = "Salut") {
    const input = $("chatbot-input");
    input.textContent = text;
    input.dispatchEvent(new Event("input"));
    $("chatbot-send-btn").click();
  }

  it("apparaît immédiatement à l'envoi puis disparaît dès les premiers caractères affichés", async () => {
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ delta: "Bonjour" }, { done: true }]));
    sendUserMessage();
    await flushPromises();
    const bubble = document.querySelector(".chatbot-msg-bubble--assistant");
    expect(bubble.querySelector(".chatbot-thinking")).not.toBeNull();

    await wait(100);
    expect(bubble.querySelector(".chatbot-thinking")).toBeNull();
  });

  it("disparaît proprement en cas d'annulation (bouton stop) avant toute réponse", async () => {
    // startStream ne résout jamais avant l'abandon : simule une génération
    // interrompue avant même l'arrivée du premier delta (cf. correctif
    // chatbot.js::runAssistantTurn — avant lui, l'indicateur restait affiché
    // indéfiniment dans ce cas précis).
    mockApi.chatbotStream.mockImplementation((convId, text, mentions, { signal } = {}) => new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => {
        const err = new Error("aborted");
        err.name = "AbortError";
        reject(err);
      });
    }));

    sendUserMessage();
    await flushPromises();
    const bubble = document.querySelector(".chatbot-msg-bubble--assistant");
    expect(bubble.querySelector(".chatbot-thinking")).not.toBeNull();

    $("chatbot-send-btn").click(); // devenu le bouton "stop" pendant le streaming
    await flushPromises();

    expect(bubble.querySelector(".chatbot-thinking")).toBeNull();
    expect(bubble.classList.contains("is-streaming")).toBe(false);
  });

  it("disparaît en cas d'erreur serveur", async () => {
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ error: "Panne du fournisseur IA." }]));
    sendUserMessage();
    await flushPromises();
    const bubble = document.querySelector(".chatbot-msg-bubble--assistant");
    await wait(100);
    expect(bubble.querySelector(".chatbot-thinking")).toBeNull();
  });

  // ── Finalisation : plus de texte visible, bulle compacte ──────────────────
  it("n'affiche aucun texte visible, seul un libellé réservé aux lecteurs d'écran subsiste", async () => {
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ delta: "Bonjour" }, { done: true }]));
    sendUserMessage();
    await flushPromises();
    const bubble = document.querySelector(".chatbot-msg-bubble--assistant");
    const thinking = bubble.querySelector(".chatbot-thinking");
    expect(thinking.getAttribute("aria-label")).toBe("Mathadap réfléchit");
    const label = thinking.querySelector(".chatbot-thinking-label");
    expect(label.classList.contains("visually-hidden")).toBe(true);
    expect(bubble.querySelectorAll(".chatbot-thinking-dots > span").length).toBe(3);
  });

  it("porte un modificateur de bulle compacte pendant la réflexion, retiré dès l'affichage de la réponse", async () => {
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ delta: "Bonjour" }, { done: true }]));
    sendUserMessage();
    await flushPromises();
    const bubble = document.querySelector(".chatbot-msg-bubble--assistant");
    expect(bubble.classList.contains("chatbot-msg-bubble--thinking")).toBe(true);

    await wait(100);
    expect(bubble.classList.contains("chatbot-msg-bubble--thinking")).toBe(false);
  });

  it("retire le modificateur de bulle compacte même en cas d'annulation ou d'erreur", async () => {
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ error: "Panne du fournisseur IA." }]));
    sendUserMessage();
    await flushPromises();
    const bubble = document.querySelector(".chatbot-msg-bubble--assistant");
    await wait(100);
    expect(bubble.classList.contains("chatbot-msg-bubble--thinking")).toBe(false);
  });
});


// ── Chantier UX phase 1 : simplification des actions des messages ─────────
describe("chatbot.js — menu 'Plus' sous les messages", () => {
  beforeEach(async () => {
    await mountChatbot();
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ done: true }]));
    mockApi.chatbotMessages.mockResolvedValue({
      messages: [
        { id: 10, role: "user", content: "Salut" },
        { id: 11, role: "assistant", content: "Bonjour !", liked: null },
      ],
    });
    const input = $("chatbot-input");
    input.textContent = "Salut";
    input.dispatchEvent(new Event("input"));
    $("chatbot-send-btn").click();
    await flushPromises();
    await wait(100); // laisse le "machine à écrire" finir et la liste se recharger avec les ids persistés
  });

  // Certains tests ci-dessous redéfinissent innerWidth/innerHeight pour
  // simuler différentes largeurs d'écran (1440/768/390/320) — toujours
  // restaurés après coup pour ne jamais fuiter vers un autre test.
  const ORIGINAL_INNER_WIDTH = window.innerWidth;
  const ORIGINAL_INNER_HEIGHT = window.innerHeight;
  afterEach(() => {
    Object.defineProperty(window, "innerWidth", { value: ORIGINAL_INNER_WIDTH, configurable: true });
    Object.defineProperty(window, "innerHeight", { value: ORIGINAL_INNER_HEIGHT, configurable: true });
  });

  it("n'affiche directement que Copier et Régénérer, le reste étant dans 'Plus'", () => {
    // Sélecteur scopé à la ligne assistant : depuis le chantier Copier/Modifier,
    // les messages utilisateur portent eux aussi une ".chatbot-msg-actions"
    // (Copier/Modifier) — ce test ne concerne que les actions assistant.
    const actions = document.querySelector(".chatbot-msg-row--assistant .chatbot-msg-actions");
    const directButtons = Array.from(actions.children).filter((el) => el.tagName === "BUTTON");
    expect(directButtons.map((b) => b.dataset.action)).toEqual(["copy", "regenerate"]);

    // Chantier UX (2026-10-18) : "Continuer", "Exporter en Markdown" et
    // "Exporter en PDF" sont retirés de l'interface (aucun appel API, jamais
    // utilisés ailleurs — voir le commentaire au-dessus de messageActionsHtml
    // dans chatbot.js). Seules les 3 actions avec un vrai comportement
    // backend/fonctionnel restent, dans cet ordre.
    const menu = document.querySelector(".chatbot-msg-more-menu");
    const menuActions = Array.from(menu.querySelectorAll("button")).map((b) => b.dataset.action);
    expect(menuActions).toEqual(["like", "dislike", "report"]);
    expect(menu.textContent).toContain("Bonne réponse");
    expect(menu.textContent).toContain("Mauvaise réponse");
    // Séparateur visuel avant "Signaler un problème".
    expect(menu.querySelector(".chatbot-msg-more-sep")).not.toBeNull();
  });

  it("le menu 'Plus' s'ouvre au clic et se referme au clic extérieur", () => {
    const menu = document.querySelector(".chatbot-msg-more-menu");
    expect(menu.hidden).toBe(true);

    document.querySelector('[data-action="more-toggle"]').click();
    expect(menu.hidden).toBe(false);

    document.body.click();
    expect(menu.hidden).toBe(true);
  });

  it("le menu 'Plus' se referme avec Échap", () => {
    const menu = document.querySelector(".chatbot-msg-more-menu");
    document.querySelector('[data-action="more-toggle"]').click();
    expect(menu.hidden).toBe(false);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(menu.hidden).toBe(true);
  });

  it("le vote 'J'aime' depuis le menu reste fonctionnel et referme le menu", async () => {
    document.querySelector('[data-action="more-toggle"]').click();
    document.querySelector('[data-action="like"]').click();
    await flushPromises();
    expect(mockApi.chatbotFeedback).toHaveBeenCalledWith(11, 1);
  });

  // ── Chantier "menu Plus" (2026-10-18) : chevauchement signalé ("Bonne
  // réponse"/"Mauvaise réponse"/"Signaler un problème" superposés), fond
  // translucide, positionnement incohérent. Cause exacte : la règle icône
  // 28×28 (`.chatbot-msg-actions button:not(.btn)`), plus spécifique que
  // `.chatbot-msg-more-menu button`, s'appliquait AUSSI aux boutons du menu
  // déroulant (descendants de `.chatbot-msg-actions` sans classe `.btn`) —
  // voir describe "source CSS" ci-dessous pour la preuve directe.
  it("les boutons du menu déroulant ne reçoivent jamais la taille d'icône 28×28/44×44 (structure/classes)", () => {
    document.querySelector('[data-action="more-toggle"]').click();
    const menu = document.querySelector(".chatbot-msg-more-menu");
    const menuButtons = Array.from(menu.querySelectorAll("button"));
    expect(menuButtons).toHaveLength(3);
    for (const btn of menuButtons) {
      // Ni la classe `.btn` (système de boutons global), ni un style inline
      // de largeur/hauteur fixe — la taille vient uniquement de la règle
      // `.chatbot-msg-more-menu button` (source CSS, voir describe dédié).
      expect(btn.classList.contains("btn")).toBe(false);
      expect(btn.style.width).toBe("");
      expect(btn.style.height).toBe("");
      // Chaque action a bien son icône ET son texte (span), structure que la
      // boîte 28×28 (display:inline-flex, align-items:center sur un carré
      // minuscule) écrasait visuellement.
      expect(btn.querySelector("svg")).not.toBeNull();
      expect(btn.querySelector("span")).not.toBeNull();
    }
  });

  it("positionne le menu en 'fixed' avec des coordonnées calculées à l'ouverture (jamais 0,0 par défaut)", () => {
    const toggle = document.querySelector('[data-action="more-toggle"]');
    const menu = document.querySelector(".chatbot-msg-more-menu");
    toggle.getBoundingClientRect = () => ({ top: 300, bottom: 320, left: 100, right: 120, width: 20, height: 20 });
    menu.getBoundingClientRect = () => ({ top: 0, bottom: 0, left: 0, right: 0, width: 220, height: 120 });

    toggle.click();
    expect(menu.hidden).toBe(false);
    // Ouvre vers le BAS (assez de place en dessous, 300px de haut pour un
    // menu de 120px) : juste sous le bouton, pas la valeur par défaut (0).
    expect(menu.style.top).toBe("326px");
    expect(menu.style.left).toBe("100px");
  });

  it("bascule le menu vers le HAUT quand la place manque en dessous (bas d'écran)", () => {
    Object.defineProperty(window, "innerHeight", { value: 400, configurable: true });
    const toggle = document.querySelector('[data-action="more-toggle"]');
    const menu = document.querySelector(".chatbot-msg-more-menu");
    // Bouton très bas (ex: dernier message visible juste avant le bas de
    // l'écran) : 100px de marge en dessous, mais le menu mesure 120px.
    toggle.getBoundingClientRect = () => ({ top: 280, bottom: 300, left: 100, right: 120, width: 20, height: 20 });
    menu.getBoundingClientRect = () => ({ top: 0, bottom: 0, left: 0, right: 0, width: 220, height: 120 });

    toggle.click();
    expect(menu.hidden).toBe(false);
    // Ouvert au-dessus du bouton (280 - 120 - 6 = 154), jamais sous 300
    // (ce qui dépasserait l'écran de 400px).
    expect(menu.style.top).toBe("154px");
  });

  it("recale horizontalement pour rester entièrement visible près du bord droit (390px, 320px)", () => {
    for (const viewportWidth of [390, 320]) {
      document.body.click(); // referme un éventuel menu resté ouvert du tour précédent
      Object.defineProperty(window, "innerWidth", { value: viewportWidth, configurable: true });
      const toggle = document.querySelector('[data-action="more-toggle"]');
      const menu = document.querySelector(".chatbot-msg-more-menu");
      // Bouton "···" collé au bord droit de l'écran (cas réel : la barre
      // d'actions d'un message assistant est alignée à gauche, mais un petit
      // viewport laisse peu de marge) et un menu plus large que l'espace
      // restant à droite du bouton.
      toggle.getBoundingClientRect = () => ({
        top: 100, bottom: 120, left: viewportWidth - 40, right: viewportWidth - 20, width: 20, height: 20,
      });
      menu.getBoundingClientRect = () => ({ top: 0, bottom: 0, left: 0, right: 0, width: 220, height: 120 });

      toggle.click();
      expect(menu.hidden).toBe(false);
      const left = Number.parseFloat(menu.style.left);
      // Jamais négatif (toujours ≥ la marge de 8px) ET jamais hors écran à
      // droite (left + largeur du menu ≤ largeur de la fenêtre).
      expect(left).toBeGreaterThanOrEqual(8);
      expect(left + 220).toBeLessThanOrEqual(viewportWidth);
    }
  });
});

describe("chatbot.css — menu 'Plus' (source CSS)", () => {
  const css = readFileSync(resolve(__dirname, "..", "..", "css", "chatbot.css"), "utf-8");

  it("le menu déroulant est en position fixed (jamais absolute, pour échapper à l'overflow de la liste de messages)", () => {
    const match = css.match(/\.chatbot-msg-more-menu\s*\{([^}]*)\}/);
    expect(match).not.toBeNull();
    expect(match[1]).toMatch(/position:\s*fixed/);
    expect(match[1]).not.toMatch(/position:\s*absolute/);
  });

  it("fond opaque (--surface-elevated), plus aucune transparence/backdrop-filter sur le menu", () => {
    const match = css.match(/\.chatbot-msg-more-menu\s*\{([^}]*)\}/);
    expect(match[1]).toMatch(/background:\s*var\(--surface-elevated\)/);
    expect(match[1]).not.toMatch(/--surface-glass/);
    expect(match[1]).not.toMatch(/backdrop-filter/);
  });

  it("aucune règle ambiguë ne cible les boutons du menu déroulant via .chatbot-msg-actions", () => {
    // La cause exacte du chevauchement signalé : cette règle (icône 28×28)
    // ne doit plus jamais matcher un descendant profond comme les boutons de
    // `.chatbot-msg-more-menu` — seul l'enfant direct (">") est ciblé.
    expect(css).toMatch(/\.chatbot-msg-actions > button:not\(\.btn\)/);
    expect(css).toMatch(/\.chatbot-msg-more-wrap > button:not\(\.btn\)/);
  });

  it("les boutons du menu ont une hauteur confortable, un espacement régulier et jamais de texte tronqué", () => {
    const match = css.match(/\.chatbot-msg-more-menu button\s*\{([^}]*)\}/);
    expect(match).not.toBeNull();
    expect(match[1]).toMatch(/min-height:\s*\d/);
    expect(match[1]).toMatch(/white-space:\s*nowrap/);
    expect(match[1]).not.toMatch(/width:\s*28px/);
    expect(match[1]).not.toMatch(/height:\s*28px/);
  });

  it("une ombre légère distingue le menu des éléments derrière, avec une bordure discrète", () => {
    const match = css.match(/\.chatbot-msg-more-menu\s*\{([^}]*)\}/);
    expect(match[1]).toMatch(/box-shadow:\s*var\(--shadow-md\)/);
    expect(match[1]).toMatch(/border:\s*1px solid var\(--border\)/);
  });
});

// ── Chantier "Copier/Modifier" sous les messages utilisateur ───────────────
describe("chatbot.js — actions Copier et Modifier sous les messages utilisateur", () => {
  beforeEach(async () => {
    await mountChatbot();
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ done: true }]));
    mockApi.chatbotMessages.mockResolvedValue({
      messages: [
        { id: 10, role: "user", content: "Salut" },
        { id: 11, role: "assistant", content: "Bonjour !", liked: null },
      ],
    });
    const input = $("chatbot-input");
    input.textContent = "Salut";
    input.dispatchEvent(new Event("input"));
    $("chatbot-send-btn").click();
    await flushPromises();
    await wait(100); // laisse le "machine à écrire" finir et la liste se recharger avec les ids persistés
  });

  function userRow() { return document.querySelector(".chatbot-msg-row--user"); }
  function assistantRow() { return document.querySelector(".chatbot-msg-row--assistant"); }

  it("affiche Copier et Modifier sous le message utilisateur", () => {
    const actions = userRow().querySelector(".chatbot-msg-actions--user");
    expect(actions).not.toBeNull();
    const buttons = Array.from(actions.querySelectorAll("button"));
    expect(buttons.map((b) => b.dataset.action)).toEqual(["copy-user", "edit-user"]);
    expect(buttons[0].getAttribute("aria-label")).toBe("Copier le message");
    expect(buttons[1].getAttribute("aria-label")).toBe("Modifier le message");
  });

  it("n'affiche aucun bouton Copier/Modifier sous les messages assistant", () => {
    expect(assistantRow().querySelector(".chatbot-msg-actions--user")).toBeNull();
  });

  it("copie exactement le texte du message (sans HTML) via le presse-papiers", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    userRow().querySelector('[data-action="copy-user"]').click();
    await flushPromises();

    expect(writeText).toHaveBeenCalledWith("Salut");
    const btn = userRow().querySelector('[data-action="copy-user"]');
    expect(btn.classList.contains("is-copied")).toBe(true);
    expect(btn.getAttribute("aria-label")).toBe("Message copié");
  });

  it("affiche un état d'erreur propre si le presse-papiers est inaccessible", async () => {
    Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });

    const btn = userRow().querySelector('[data-action="copy-user"]');
    btn.click();
    await flushPromises();

    expect(btn.classList.contains("is-copied")).toBe(false);
    expect(btn.getAttribute("title")).toBe("Copie impossible sur ce navigateur");
  });

  it("ouvre l'éditeur avec le texte original exact, au même emplacement", () => {
    userRow().querySelector('[data-action="edit-user"]').click();
    const textarea = userRow().querySelector(".chatbot-msg-edit-textarea");
    expect(textarea).not.toBeNull();
    expect(textarea.value).toBe("Salut");
    expect(userRow().classList.contains("is-editing")).toBe(true);
    expect(document.activeElement).toBe(textarea);
  });

  // Chantier "correction design édition" (2026-10-18) : Annuler/Envoyer
  // doivent porter les classes du système de boutons global (base.css),
  // seules capables de leur donner la bonne forme (pilule), le bon padding
  // et la bonne couleur — voir l'audit CSS ci-dessous pour la règle qui les
  // écrasait avant ce correctif.
  it("Annuler et Envoyer réutilisent le système de boutons global (secondaire discret / principal violet)", () => {
    userRow().querySelector('[data-action="edit-user"]').click();
    const cancelBtn = userRow().querySelector('[data-action="edit-cancel"]');
    const submitBtn = userRow().querySelector('[data-action="edit-submit"]');
    expect(cancelBtn.className).toContain("btn-ghost");
    expect(submitBtn.className).toContain("btn-primary");
    expect(cancelBtn.className).toContain("btn-sm");
    expect(submitBtn.className).toContain("btn-sm");
  });

  it("l'annulation referme l'éditeur, restaure le texte d'origine et ne modifie rien", () => {
    userRow().querySelector('[data-action="edit-user"]').click();
    const textarea = userRow().querySelector(".chatbot-msg-edit-textarea");
    textarea.value = "Texte modifié jamais envoyé";

    userRow().querySelector('[data-action="edit-cancel"]').click();

    expect(userRow().querySelector(".chatbot-msg-edit-textarea")).toBeNull();
    expect(userRow().classList.contains("is-editing")).toBe(false);
    expect(userRow().querySelector(".chatbot-msg-bubble").textContent).toContain("Salut");
    // L'historique réel (activeMessages, source de vérité) n'a pas bougé.
    expect(mockApi.chatbotStream).toHaveBeenCalledTimes(1);
  });

  it("refuse un message vide (espaces uniquement) sans effet", () => {
    userRow().querySelector('[data-action="edit-user"]').click();
    const textarea = userRow().querySelector(".chatbot-msg-edit-textarea");
    textarea.value = "   ";

    userRow().querySelector('[data-action="edit-submit"]').click();

    expect(textarea.classList.contains("is-invalid")).toBe(true);
    expect(userRow().querySelector(".chatbot-msg-edit-notice")).toBeNull();
    expect(userRow().classList.contains("is-editing")).toBe(true); // éditeur toujours ouvert
  });

  it("empêche les doubles soumissions (un seul message affiché pour deux clics successifs)", () => {
    userRow().querySelector('[data-action="edit-user"]').click();
    const textarea = userRow().querySelector(".chatbot-msg-edit-textarea");
    textarea.value = "Nouveau texte";

    const submitBtn = userRow().querySelector('[data-action="edit-submit"]');
    submitBtn.click();
    submitBtn.click();

    const notices = userRow().querySelectorAll(".chatbot-msg-edit-notice");
    expect(notices.length).toBe(1);
    expect(submitBtn.disabled).toBe(true);
  });

  it("n'altère jamais l'historique réel tant que le backend ne le permet pas (aucune mutation, aucun appel réseau)", () => {
    userRow().querySelector('[data-action="edit-user"]').click();
    const textarea = userRow().querySelector(".chatbot-msg-edit-textarea");
    textarea.value = "Nouvelle version";
    userRow().querySelector('[data-action="edit-submit"]').click();

    expect(userRow().querySelector(".chatbot-msg-edit-notice")).not.toBeNull();
    // Aucun appel réseau supplémentaire déclenché par la tentative de soumission.
    expect(mockApi.chatbotStream).toHaveBeenCalledTimes(1);
    expect(mockApi.chatbotMessages).toHaveBeenCalled();
  });

  it("désactive le bouton Modifier pendant qu'une génération est active (pas de conflit avec un envoi en cours)", async () => {
    mockApi.chatbotStream.mockImplementation((convId, text, mentions, { signal } = {}) => new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => {
        const err = new Error("aborted");
        err.name = "AbortError";
        reject(err);
      });
    }));
    const input = $("chatbot-input");
    input.textContent = "Autre message";
    input.dispatchEvent(new Event("input"));
    $("chatbot-send-btn").click();
    await flushPromises();

    const editBtn = userRow().querySelector('[data-action="edit-user"]');
    expect(editBtn.disabled).toBe(true);

    $("chatbot-send-btn").click(); // annule le tour en cours (bouton devenu "stop")
    await flushPromises();
  });

  it("est accessible au clavier : Échap referme l'éditeur comme le bouton Annuler", () => {
    userRow().querySelector('[data-action="edit-user"]').click();
    const textarea = userRow().querySelector(".chatbot-msg-edit-textarea");
    textarea.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
    expect(userRow().classList.contains("is-editing")).toBe(false);
  });
});

describe("chatbot.css — design du mode édition (source CSS)", () => {
  const css = readFileSync(resolve(__dirname, "..", "..", "css", "chatbot.css"), "utf-8");

  // Régression du chevauchement signalé : la règle icône 28×28 pensée pour
  // Copier/Régénérer/Plus ne doit plus jamais s'appliquer à un bouton
  // `.btn` (Annuler/Envoyer) — c'est exactement cette collision qui écrasait
  // leur largeur/forme/bordure avant ce correctif.
  it("exclut les boutons .btn (Annuler/Envoyer) de la règle icône 28×28", () => {
    expect(css).toMatch(/\.chatbot-msg-actions > button:not\(\.btn\)/);
    // Aucune règle ne doit plus cibler ".chatbot-msg-actions button" SANS
    // l'exclusion ET sans le scoping ">" (qui recréerait le même conflit de
    // spécificité avec les boutons .btn — ou, depuis le chantier "menu
    // Plus", avec les boutons du menu déroulant, voir describe dédié).
    expect(css).not.toMatch(/\.chatbot-msg-actions button\s*\{/);
    expect(css).not.toMatch(/\.chatbot-msg-actions button:not\(\.btn\)\s*\{/);
  });

  it("espace Annuler/Envoyer d'un gap visible et les aligne à droite, sans position absolue", () => {
    const body = ruleBodyFor(".chatbot-msg-actions--user:has\\(.btn\\)", css);
    expect(body).not.toBeNull();
    expect(body).toMatch(/gap:\s*\d/);
    const wrapBody = ruleBodyFor(".chatbot-msg-actions--user", css);
    expect(wrapBody).toMatch(/justify-content:\s*flex-end/);
    expect(wrapBody).not.toMatch(/position:\s*absolute/);
  });

  it("donne à la bulle d'édition un fond neutre cohérent (pas de double superposition violette) et un seul bord", () => {
    const body = ruleBodyFor(".chatbot-msg-bubble--editing", css);
    expect(body).not.toBeNull();
    expect(body).toMatch(/background:\s*var\(--surface\)/);
    expect(body.match(/border:/g)?.length).toBe(1);
  });

  function ruleBodyFor(selector, source) {
    const match = source.match(new RegExp(`${selector}\\s*\\{([^}]*)\\}`));
    return match ? match[1] : null;
  }
});

// ── Chantier UX phase 2 : vrai affichage progressif (performance) ─────────
describe("chatbot.js — rendu Markdown/KaTeX pendant le streaming", () => {
  beforeEach(async () => {
    await mountChatbot();
  });

  function sendUserMessage(text = "Salut") {
    const input = $("chatbot-input");
    input.textContent = text;
    input.dispatchEvent(new Event("input"));
    $("chatbot-send-btn").click();
  }

  it("ne reconstruit le rendu riche (markdown + KaTeX) qu'une seule fois, jamais à chaque caractère révélé", async () => {
    // Avant ce correctif, renderMessageBody() (donc window.marked.parse())
    // tournait à CHAQUE tick du "machine à écrire" (toutes les 15ms) — coûteux,
    // et une formule KaTeX coupée en plein milieu du défilement se rendait
    // mal avant l'arrivée de son délimiteur fermant. Ce test échoue si cette
    // reconstruction redevient systématique.
    const longText = "Voici $x^2$ puis plusieurs ticks de défilement.";
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ delta: longText }, { done: true }]));
    const parseSpy = vi.fn((s) => `<p>${s}</p>`);
    window.marked = { parse: parseSpy };
    try {
      sendUserMessage();
      await flushPromises();
      // À ce stade, marked.parse() a déjà tourné deux fois pour l'affichage
      // initial (bulle utilisateur + bulle assistant vide) — avant même que
      // le "machine à écrire" ne démarre. C'est ce nombre de référence qui
      // compte, pas un 1 en dur.
      const callsBeforeTyping = parseSpy.mock.calls.length;

      // Le défilement révèle 2 caractères toutes les 15ms (voir
      // TYPEWRITER_CHARS_PER_TICK/TYPEWRITER_INTERVAL_MS dans chatbot.js) :
      // de quoi largement dépasser la durée réelle pour un texte de cette
      // longueur avant de vérifier qu'une seule reconstruction riche a eu lieu.
      await wait(800);

      // Une seule reconstruction riche supplémentaire doit avoir eu lieu (le
      // rendu final, à la toute fin du défilement) — jamais une par
      // caractère révélé pendant les ticks intermédiaires.
      expect(parseSpy).toHaveBeenCalledTimes(callsBeforeTyping + 1);
      expect(parseSpy).toHaveBeenLastCalledWith(longText);
    } finally {
      delete window.marked;
    }
  });

  // ── Chantier "rendu des formules mathématiques" (2026-10-18) : vérifie le
  // CÂBLAGE exact (extractMathSegments -> marked.parse -> restoreMathSegments)
  // — la justesse de la protection elle-même (regex, échappement Markdown
  // réellement défait) est testée indépendamment dans mathrender.test.js,
  // sans dépendre du DOM ni de ce mock.
  it("protège chaque formule AVANT marked.parse() puis la restaure APRÈS (câblage)", async () => {
    extractMathSegments.mockClear();
    restoreMathSegments.mockClear();
    extractMathSegments.mockImplementation((text) => ({ text: `PROTECTED(${text})`, segments: ["seg1"] }));
    restoreMathSegments.mockImplementation((html) => `RESTORED(${html})`);
    const parseSpy = vi.fn((s) => `<p>${s}</p>`);
    window.marked = { parse: parseSpy };
    try {
      mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ delta: "Texte avec \\(x^2\\)" }, { done: true }]));
      sendUserMessage();
      await flushPromises();
      await wait(300);

      // extractMathSegments a bien reçu le texte COMPLET reçu du flux.
      expect(extractMathSegments).toHaveBeenCalledWith("Texte avec \\(x^2\\)");
      // marked.parse() a reçu le texte PROTÉGÉ (jamais le texte brut
      // directement) — c'est ce qui empêche marked de manger les antislashs.
      expect(parseSpy).toHaveBeenLastCalledWith("PROTECTED(Texte avec \\(x^2\\))");
      // restoreMathSegments a reçu le HTML produit par marked ET les
      // segments extraits — jamais l'inverse, jamais sans les segments.
      expect(restoreMathSegments).toHaveBeenLastCalledWith("<p>PROTECTED(Texte avec \\(x^2\\))</p>", ["seg1"]);
      // setRenderedHtmlContent reçoit bien le résultat de restoreMathSegments
      // (jamais le html brut de marked directement) — le lien complet de la
      // chaîne, sans dépendre du nouveau rendu déclenché juste après par le
      // rechargement de l'historique (non mocké ici, hors-sujet pour ce test).
      expect(setRenderedHtmlContent).toHaveBeenCalledWith(
        expect.anything(), "RESTORED(<p>PROTECTED(Texte avec \\(x^2\\))</p>)",
      );
    } finally {
      delete window.marked;
      extractMathSegments.mockReset();
      restoreMathSegments.mockReset();
      extractMathSegments.mockImplementation((text) => ({ text, segments: [] }));
      restoreMathSegments.mockImplementation((html) => html);
    }
  });

  it("reconstitue correctement une formule répartie sur plusieurs chunks de streaming avant de la protéger", async () => {
    extractMathSegments.mockClear();
    const parseSpy = vi.fn((s) => `<p>${s}</p>`);
    window.marked = { parse: parseSpy };
    try {
      // La formule "\(x^2 + 1\)" arrive coupée en 3 deltas SSE distincts —
      // le texte complet ne doit être protégé/rendu qu'une fois réassemblé.
      mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([
        { delta: "Résultat : \\(x^2 " }, { delta: "+ 1" }, { delta: "\\)." }, { done: true },
      ]));
      sendUserMessage();
      await flushPromises();
      await wait(300);

      expect(extractMathSegments).toHaveBeenLastCalledWith("Résultat : \\(x^2 + 1\\).");
    } finally {
      delete window.marked;
    }
  });


  it("affiche quand même le texte progressivement pendant le défilement (pas d'attente artificielle)", async () => {
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ delta: "Une réponse assez longue pour voir la progression du défilement de caractères." }, { done: true }]));
    sendUserMessage();
    await flushPromises();
    const bubble = document.querySelector(".chatbot-msg-bubble--assistant");

    await wait(40); // quelques ticks seulement : pas encore fini
    const partial = bubble.textContent.length;
    expect(partial).toBeGreaterThan(0);

    await wait(200); // laisse le défilement se terminer
    expect(bubble.textContent.length).toBeGreaterThan(partial);
  });

  it("annulation en plein défilement : retire le curseur clignotant et garde le texte déjà révélé", async () => {
    // Un premier delta arrive puis plus rien (connexion ouverte, comme une
    // vraie génération en cours) jusqu'à ce que le signal d'abandon soit
    // déclenché par le clic sur "stop" — reproduit une vraie annulation
    // pendant le défilement, pas juste avant la première réponse.
    mockApi.chatbotStream.mockImplementation((convId, text, mentions, { signal } = {}) => {
      const encoder = new TextEncoder();
      const firstChunk = encoder.encode(sseChunk({ delta: "Une réponse assez longue pour que l'annulation arrive en plein défilement." }));
      let delivered = false;
      return Promise.resolve({
        body: {
          getReader: () => ({
            read: () => {
              if (!delivered) {
                delivered = true;
                return Promise.resolve({ done: false, value: firstChunk });
              }
              return new Promise((_resolve, reject) => {
                signal.addEventListener("abort", () => {
                  const err = new Error("aborted");
                  err.name = "AbortError";
                  reject(err);
                });
              });
            },
          }),
        },
      });
    });

    sendUserMessage();
    await flushPromises();
    const bubble = document.querySelector(".chatbot-msg-bubble--assistant");

    await wait(40); // laisse le défilement commencer à révéler du texte
    expect(bubble.classList.contains("is-streaming")).toBe(true);
    expect(bubble.textContent.length).toBeGreaterThan(0);

    $("chatbot-send-btn").click(); // devenu le bouton "stop" pendant le streaming
    await flushPromises();

    expect(bubble.classList.contains("is-streaming")).toBe(false);
    expect(bubble.querySelector(".chatbot-thinking")).toBeNull();
  });
});

// ── Chantier "audit fonctionnel des paramètres" (2026-10-18) : démontre que
// "Affichage progressif" (Paramètres → Chatbot → streaming) produit bien un
// comportement DIFFÉRENT selon sa valeur — comparaison à un seul paramètre
// varié, sur le même flux SSE (voir consigne, section 3).
describe("chatbot.js — réglage 'Affichage progressif' (streaming)", () => {
  function sendUserMessage(text = "Salut") {
    const input = $("chatbot-input");
    input.textContent = text;
    input.dispatchEvent(new Event("input"));
    $("chatbot-send-btn").click();
  }

  it("activé (valeur par défaut) : le texte apparaît progressivement, pas d'un bloc", async () => {
    await mountChatbot(); // getSettings() -> streaming:true, voir defaultMocks()
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([
      { delta: "Une réponse assez longue pour observer une révélation progressive du texte." }, { done: true },
    ]));
    sendUserMessage();
    await flushPromises();
    const bubble = document.querySelector(".chatbot-msg-bubble--assistant");

    await wait(40); // quelques ticks seulement
    const partialLength = bubble.textContent.length;
    expect(partialLength).toBeGreaterThan(0);
    await wait(250);
    expect(bubble.textContent.length).toBeGreaterThan(partialLength);
  });

  it("désactivé : le texte apparaît d'un seul bloc dès réception complète, jamais progressivement", async () => {
    document.body.innerHTML = loadPageBody("chatbot.html");
    defaultMocks();
    mockApi.getSettings.mockResolvedValue({ chatbot: { streaming: false } });
    vi.resetModules();
    await import("../chatbot.js");
    await flushPromises();

    const fullText = "Une réponse assez longue pour observer une révélation progressive du texte.";
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ delta: fullText }, { done: true }]));
    // Une fois le tour terminé, chatbot.js recharge l'historique réel (voir
    // runAssistantTurn::onDone) — lui donner une réponse cohérente avec ce
    // qui vient d'être envoyé évite la course "contenu vidé puis rechargé"
    // déjà documentée (chantier "rendu des formules", 2026-10-18) et permet
    // de vérifier l'état final sans dépendre d'un instant précis.
    mockApi.chatbotMessages.mockResolvedValue({
      messages: [
        { id: 20, role: "user", content: "Salut" },
        { id: 21, role: "assistant", content: fullText, liked: null },
      ],
    });
    sendUserMessage();

    // Sondage répété (jamais un minuteur simulé, voir mémoire de session) :
    // tant que la bulle n'existe pas encore, vide, ou en cours de
    // rechargement d'historique, c'est un état transitoire valide — ce qui
    // est interdit, c'est un texte PARTIEL (ni vide, ni complet), signe d'une
    // révélation progressive comme en mode "activé".
    const observed = [];
    let settledBubble = null;
    for (let i = 0; i < 60 && !settledBubble; i += 1) {
      await flushPromises();
      await wait(10);
      const bubble = document.querySelector(".chatbot-msg-bubble--assistant");
      if (bubble && bubble.textContent) observed.push(bubble.textContent);
      if (bubble && bubble.textContent === fullText && !bubble.classList.contains("is-streaming")) {
        settledBubble = bubble;
      }
    }

    expect(observed.length).toBeGreaterThan(0);
    for (const text of observed) expect(text).toBe(fullText);
    expect(settledBubble).not.toBeNull();
    expect(settledBubble.classList.contains("is-streaming")).toBe(false);
  });
});

// ── Chantier UX phase 3 : harmonisation des icônes ─────────────────────────
describe("chatbot.js — bouton Envoyer/Arrêter : icône et nom accessible", () => {
  beforeEach(async () => {
    await mountChatbot();
  });

  it("bascule l'icône et le nom accessible selon l'état de streaming", async () => {
    // Avant ce correctif, aria-label restait bloqué sur "Envoyer" même une
    // fois le bouton transformé en "Arrêter la génération" (icône carrée
    // rouge) — un vrai défaut d'accessibilité, pas qu'un détail visuel.
    mockApi.chatbotStream.mockImplementation((convId, text, mentions, { signal } = {}) => new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => {
        const err = new Error("aborted");
        err.name = "AbortError";
        reject(err);
      });
    }));

    const sendBtn = $("chatbot-send-btn");
    expect(sendBtn.getAttribute("aria-label")).toBe("Envoyer");

    const input = $("chatbot-input");
    input.textContent = "Salut";
    input.dispatchEvent(new Event("input"));
    sendBtn.click();
    await flushPromises();

    expect(sendBtn.getAttribute("aria-label")).toBe("Arrêter la génération");
    expect(sendBtn.classList.contains("is-stop")).toBe(true);

    sendBtn.click(); // annulation
    await flushPromises();

    expect(sendBtn.getAttribute("aria-label")).toBe("Envoyer");
    expect(sendBtn.classList.contains("is-stop")).toBe(false);
  });
});

// ── Chantier UX phase 3 : cartes de suggestion compactes ──────────────────
describe("chatbot.js — carte de suggestion (entraînement)", () => {
  beforeEach(async () => {
    await mountChatbot();
    mockApi.chatbotStream.mockResolvedValue(makeStreamResponse([{ done: true }]));
    mockApi.chatbotMessages.mockResolvedValue({
      messages: [
        { id: 20, role: "user", content: "Je ne comprends pas les suites" },
        {
          id: 21,
          role: "assistant",
          content: "Voici une explication.",
          cards: [{ type: "notion_series", icon: "target", label_key: "chatbot.card.practice", chapter_id: 3, notion: "suites", exercise_ids: [101, 102] }],
        },
      ],
    });
    const input = $("chatbot-input");
    input.textContent = "Je ne comprends pas les suites";
    input.dispatchEvent(new Event("input"));
    $("chatbot-send-btn").click();
    await flushPromises();
    await wait(100);
  });

  it("affiche la carte avec une structure compacte (icône + libellé + chevron CSS)", () => {
    const card = document.querySelector(".chatbot-action-card");
    expect(card).not.toBeNull();
    expect(card.querySelector(".chatbot-action-card-icon")).not.toBeNull();
    // Le chevron est un pseudo-élément CSS (::after), jamais un élément du DOM.
    expect(card.querySelector("svg")).not.toBeNull();
  });

  it("conserve la destination et les paramètres de l'entraînement au clic (chapitre/notion/exercices)", async () => {
    await withMockedLocation(async () => {
      document.querySelector(".chatbot-action-card").click();
      await flushPromises();
      const stored = JSON.parse(localStorage.getItem("lumis:pending_series"));
      expect(stored).toEqual({
        mode: "notion",
        chapterId: 3,
        notion: "suites",
        notions: ["suites"],
        exerciseIds: [101, 102],
      });
      expect(window.location.href).toBe("exercice.html");
    });
  });
});

// ── Chantier UX phase 4 : correction du bug "trois points immobiles" ───────
// jsdom ne charge ni n'applique jamais les feuilles de style externes (les
// tests DOM ci-dessus mockent tout le rendu) — impossible donc de vérifier
// un VRAI mouvement rendu depuis ce fichier. Ces tests vérifient les deux
// choses qu'on PEUT garantir depuis Node : (1) le DOM généré contient bien
// 3 <span> enfants de .chatbot-thinking-dots (structure attendue par les
// sélecteurs CSS), et (2) le fichier CSS source définit une vraie animation
// (durée non nulle, @keyframes avec au moins deux états visuellement
// différents, délais distincts par point) — pas une règle neutralisée par
// erreur. La confirmation du mouvement RENDU reste à faire dans un vrai
// navigateur (voir le rapport final).
describe("chatbot.js — structure DOM de l'indicateur à trois points", () => {
  it("insère exactement 3 <span> enfants dans .chatbot-thinking-dots", async () => {
    await mountChatbot();
    mockApi.chatbotStream.mockImplementation((convId, text, mentions, { signal } = {}) => new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => {
        const err = new Error("aborted");
        err.name = "AbortError";
        reject(err);
      });
    }));
    const input = $("chatbot-input");
    input.textContent = "Salut";
    input.dispatchEvent(new Event("input"));
    $("chatbot-send-btn").click();
    await flushPromises();

    const dots = document.querySelectorAll(".chatbot-thinking-dots > span");
    expect(dots.length).toBe(3);
  });
});

describe("chatbot.css — règles d'animation des trois points (source CSS)", () => {
  const css = readFileSync(resolve(__dirname, "..", "..", "css", "chatbot.css"), "utf-8");

  function ruleBodyFor(selector, source) {
    const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`));
    return match ? match[1] : null;
  }

  it("applique une animation réelle (durée non nulle, répétée) aux points", () => {
    const body = ruleBodyFor(".chatbot-thinking-dots span", css);
    expect(body).not.toBeNull();
    expect(body).toMatch(/animation:\s*chatbot-thinking-dot\s+[\d.]+s/);
    expect(body).toContain("infinite");
    expect(body).not.toMatch(/animation:\s*none/);
  });

  it("donne un animation-delay DIFFÉRENT à chacun des 3 points (effet de cascade)", () => {
    const delay2 = css.match(/\.chatbot-thinking-dots span:nth-child\(2\)\s*\{\s*animation-delay:\s*([\d.]+)s/);
    const delay3 = css.match(/\.chatbot-thinking-dots span:nth-child\(3\)\s*\{\s*animation-delay:\s*([\d.]+)s/);
    expect(delay2).not.toBeNull();
    expect(delay3).not.toBeNull();
    const d2 = Number(delay2[1]);
    const d3 = Number(delay3[1]);
    expect(d2).toBeGreaterThan(0);
    expect(d3).toBeGreaterThan(d2);
  });

  it("définit un @keyframes chatbot-thinking-dot avec un vrai mouvement (positions différentes)", () => {
    // Découpe par index plutôt qu'une regex à accolades imbriquées (fragile
    // avec plusieurs étapes de keyframes) : isole le texte entre l'ouverture
    // de CE bloc @keyframes et le prochain sélecteur top-level connu.
    const start = css.indexOf("@keyframes chatbot-thinking-dot");
    expect(start).toBeGreaterThan(-1);
    const end = css.indexOf(".chatbot-thinking-label", start);
    expect(end).toBeGreaterThan(start);
    const body = css.slice(start, end);

    // Au moins deux valeurs de translateY distinctes (sinon aucun mouvement
    // réel, quelle que soit la durée de l'animation).
    // "translateY(0)" n'a pas d'unité en CSS (contrairement à "-4px") — le
    // suffixe "px" doit donc être optionnel dans le motif.
    const translateYValues = [...body.matchAll(/translateY\(([-\d.]+)(?:px)?\)/g)].map((m) => Number(m[1]));
    expect(new Set(translateYValues).size).toBeGreaterThan(1);
    // Au moins deux valeurs d'opacité distinctes.
    const opacityValues = [...body.matchAll(/opacity:\s*([\d.]+)/g)].map((m) => Number(m[1]));
    expect(new Set(opacityValues).size).toBeGreaterThan(1);
  });

  // ── Chantier "fluidité" (2026-10-18) ──────────────────────────────────────
  it("dure entre 1,6 et 2 secondes (plage demandée) et ne dépasse pas 2px de mouvement vertical", () => {
    const body = ruleBodyFor(".chatbot-thinking-dots span", css);
    const duration = Number(body.match(/animation:\s*chatbot-thinking-dot\s+([\d.]+)s/)[1]);
    expect(duration).toBeGreaterThanOrEqual(1.6);
    expect(duration).toBeLessThanOrEqual(2);

    const start = css.indexOf("@keyframes chatbot-thinking-dot");
    const end = css.indexOf(".chatbot-thinking-label", start);
    const keyframesBody = css.slice(start, end);
    const translateYValues = [...keyframesBody.matchAll(/translateY\(([-\d.]+)(?:px)?\)/g)].map((m) => Math.abs(Number(m[1])));
    expect(Math.max(...translateYValues)).toBeLessThan(2);
  });

  it("boucle sans rupture visible : l'état à 0% est identique à l'état à 100% (même étape de keyframe)", () => {
    // Condition nécessaire pour qu'une boucle `infinite` paraisse continue :
    // si le point d'arrivée d'un cycle diffère de son point de départ, un
    // saut est visible à chaque répétition. Avant ce correctif, l'ancienne
    // version avait aussi 0%=100% mais un plateau immobile de 40% du cycle
    // entre les deux (60%→100%) — ce test vérifie la continuité, pas
    // l'absence de plateau (couvert par le test de durée/amplitude ci-dessus
    // + la revue de code : le nouveau cycle n'a que 2 étapes, 0% et 50%).
    const start = css.indexOf("@keyframes chatbot-thinking-dot");
    const end = css.indexOf(".chatbot-thinking-label", start);
    const body = css.slice(start, end);
    const stepZero = body.match(/0%[^{]*\{([^}]*)\}/);
    const stepHundred = body.match(/100%[^{]*\{([^}]*)\}/);
    expect(stepZero).not.toBeNull();
    expect(stepHundred).not.toBeNull();
    // "0%, 100% { ... }" : les deux pourcentages partagent la MÊME règle
    // (donc le même bloc capturé) plutôt que deux déclarations séparées
    // pouvant diverger accidentellement.
    expect(stepZero[1].trim()).toBe(stepHundred[1].trim());
  });

  it("fait épouser la largeur du contenu à .chatbot-msg-bubble--thinking, sans toucher à .chatbot-msg-bubble de base", () => {
    const body = ruleBodyFor(".chatbot-msg-bubble--thinking", css);
    expect(body).not.toBeNull();
    expect(body).toMatch(/width:\s*fit-content/);
    expect(body).toMatch(/max-width:\s*fit-content/);
    // La règle de base garde son plafond de 70% pour les réponses réelles.
    const baseBody = ruleBodyFor(".chatbot-msg-bubble", css);
    expect(baseBody).toMatch(/max-width:\s*70%/);
  });
});

// ── Chantier UX : vraie page de recherche de conversations ─────────────────
describe("chatbot.js — vue de recherche de conversations", () => {
  beforeEach(async () => {
    await mountChatbot();
    mockApi.chatbotConversations.mockResolvedValue({
      conversations: [
        { id: 1, title: "Dérivées et tangentes", pinned: false, updated_at: "2026-10-10T12:00:00Z" },
        { id: 2, title: "Suites numériques", pinned: true, updated_at: "2026-10-12T09:30:00Z" },
      ],
    });
  });

  it("s'ouvre au clic sur Rechercher, met le focus dans le champ et masque la zone de conversation", async () => {
    $("chatbot-search-trigger").click();
    await flushPromises();
    expect($("chatbot-search-view").hidden).toBe(false);
    expect($("chatbot-messages").hidden).toBe(true);
    expect(document.querySelector(".chatbot-input-area").hidden).toBe(true);
    expect(document.activeElement).toBe($("chatbot-search-view-input"));
  });

  it("s'ouvre aussi depuis la sidebar réduite", async () => {
    $("chatbot-convos-collapse-btn").click();
    expect($("chatbot-convos").classList.contains("is-collapsed")).toBe(true);
    $("chatbot-search-trigger").click();
    await flushPromises();
    expect($("chatbot-search-view").hidden).toBe(false);
  });

  it("affiche la liste complète à l'ouverture puis la filtre pendant la saisie", async () => {
    $("chatbot-search-trigger").click();
    await flushPromises();
    expect($("chatbot-search-view-results").textContent).toContain("Dérivées et tangentes");
    expect($("chatbot-search-view-results").textContent).toContain("Suites numériques");

    mockApi.chatbotConversations.mockResolvedValue({
      conversations: [{ id: 2, title: "Suites numériques", pinned: true, updated_at: "2026-10-12T09:30:00Z" }],
    });
    const searchInput = $("chatbot-search-view-input");
    searchInput.value = "suites";
    searchInput.dispatchEvent(new Event("input"));
    await wait(300);

    expect(mockApi.chatbotConversations).toHaveBeenCalledWith("suites");
    expect($("chatbot-search-view-results").textContent).toContain("Suites numériques");
    expect($("chatbot-search-view-results").textContent).not.toContain("Dérivées et tangentes");
  });

  it("ignore les espaces inutiles autour de la saisie", async () => {
    $("chatbot-search-trigger").click();
    await flushPromises();
    const searchInput = $("chatbot-search-view-input");
    searchInput.value = "  suites  ";
    searchInput.dispatchEvent(new Event("input"));
    await wait(300);
    expect(mockApi.chatbotConversations).toHaveBeenCalledWith("suites");
  });

  it("affiche un état explicite sans résultat", async () => {
    $("chatbot-search-trigger").click();
    await flushPromises();
    mockApi.chatbotConversations.mockResolvedValue({ conversations: [] });
    const searchInput = $("chatbot-search-view-input");
    searchInput.value = "zzz";
    searchInput.dispatchEvent(new Event("input"));
    await wait(300);
    expect($("chatbot-search-view-results").textContent).toContain("Aucune conversation ne correspond");
  });

  it("affiche un état d'erreur si la récupération échoue", async () => {
    $("chatbot-search-trigger").click();
    await flushPromises();
    mockApi.chatbotConversations.mockRejectedValue(new Error("réseau coupé"));
    const searchInput = $("chatbot-search-view-input");
    searchInput.value = "suites";
    searchInput.dispatchEvent(new Event("input"));
    await wait(300);
    expect($("chatbot-search-view-results").textContent).toContain("Impossible de charger");
  });

  it("le bouton effacer vide le champ et recharge la liste complète", async () => {
    $("chatbot-search-trigger").click();
    await flushPromises();
    const searchInput = $("chatbot-search-view-input");
    searchInput.value = "suites";
    searchInput.dispatchEvent(new Event("input"));
    await wait(300);
    expect($("chatbot-search-view-clear").hidden).toBe(false);

    $("chatbot-search-view-clear").click();
    expect(searchInput.value).toBe("");
    await wait(300);
    expect(mockApi.chatbotConversations).toHaveBeenLastCalledWith(undefined);
  });

  it("ouvre la bonne conversation au clic sur un résultat, sans doublon ni génération IA", async () => {
    mockApi.chatbotMessages.mockResolvedValue({
      messages: [{ id: 10, role: "user", content: "Salut" }, { id: 11, role: "assistant", content: "Bonjour !" }],
    });
    $("chatbot-search-trigger").click();
    await flushPromises();

    $("chatbot-search-view-results").querySelector('[data-id="2"]').click();
    await flushPromises();

    expect(mockApi.chatbotMessages).toHaveBeenCalledWith(2);
    expect(mockApi.chatbotMessages).toHaveBeenCalledTimes(1);
    expect(mockApi.chatbotStream).not.toHaveBeenCalled();
    expect($("chatbot-search-view").hidden).toBe(true);
    expect($("chatbot-messages").hidden).toBe(false);
    expect($("chatbot-topbar-title").textContent).toBe("Suites numériques");
  });

  it("le bouton retour referme la vue et restaure l'affichage normal", async () => {
    $("chatbot-search-trigger").click();
    await flushPromises();
    $("chatbot-search-view-back").click();
    expect($("chatbot-search-view").hidden).toBe(true);
    expect($("chatbot-messages").hidden).toBe(false);
  });

  // ── Chantier "rendu des formules mathématiques" (2026-10-18) ─────────────
  it("recharge une conversation contenant une formule LaTeX sans planter, via le même pipeline de rendu", async () => {
    mockApi.chatbotMessages.mockResolvedValue({
      messages: [
        { id: 20, role: "user", content: "Calcule AB" },
        { id: 21, role: "assistant", content: "\\(AB=\\sqrt{3^2+4^2}=5\\)", liked: null },
      ],
    });
    $("chatbot-search-trigger").click();
    await flushPromises();
    $("chatbot-search-view-results").querySelector('[data-id="2"]').click();
    await flushPromises();

    const bubble = document.querySelector(".chatbot-msg-bubble--assistant");
    expect(bubble).not.toBeNull();
    expect(bubble.textContent).toBe("\\(AB=\\sqrt{3^2+4^2}=5\\)");
  });

  it("Échap referme la vue de recherche", async () => {
    $("chatbot-search-trigger").click();
    await flushPromises();
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect($("chatbot-search-view").hidden).toBe(true);
  });

  it("conserve l'état réduit de la sidebar après fermeture de la recherche", async () => {
    $("chatbot-convos-collapse-btn").click();
    $("chatbot-search-trigger").click();
    await flushPromises();
    $("chatbot-search-view-back").click();
    expect($("chatbot-convos").classList.contains("is-collapsed")).toBe(true);
  });
});
