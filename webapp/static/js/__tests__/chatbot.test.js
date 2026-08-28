// ── chatbot.js : chat IA (conversations, envoi de message, quota, santé du
// fournisseur/reconnexion). Module purement piloté par le DOM (aucun export) —
// on charge donc le vrai corps de chatbot.html et on observe le DOM résultant.
// chatbot-composer.js (contenteditable <-> texte) est un utilitaire DOM pur
// sans appel réseau : jamais mocké, utilisé tel quel (comme en production).
import { describe, it, expect, vi, beforeEach } from "vitest";
import { loadPageBody, flushPromises } from "./testUtils.js";

const mockApi = {
  chatbotConversations: vi.fn(),
  chatbotCreateConversation: vi.fn(),
  chatbotQuota: vi.fn(),
  getQuota: vi.fn(),
  chatbotGreeting: vi.fn(),
  chatbotHealth: vi.fn(),
  chatbotStream: vi.fn(),
  handleQuotaExceeded: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi, handleQuotaExceeded: mockApi.handleQuotaExceeded }));
vi.mock("../settingsManager.js", () => ({ initSettingsManager: () => Promise.resolve() }));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn(), t: (key, fallback) => fallback ?? key }));
vi.mock("../mathrender.js", () => ({ setRenderedHtmlContent: (el, text) => { el.textContent = text; } }));
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

  // Le panneau contextuel de droite ("Ton profil NovaMath") a été supprimé
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
