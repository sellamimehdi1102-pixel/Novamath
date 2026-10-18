// ── settings.js : centre de personnalisation (mountSettingsPanel) ──────────
// Utilise le VRAI settingsManager.js/theme.js/i18n.js (purement locaux, aucun
// réseau) ; seul api.js et curriculumSelector.js (réseau) sont mockés.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { withMockedLocation, flushPromises } from "./testUtils.js";

// Même forme que auth.DEFAULT_SETTINGS (backend) — mountSettingsPanel() lit
// les préférences déjà résolues par settingsManager.initSettingsManager()
// (appelé une fois au chargement de chaque page réelle, voir sidebar.js),
// jamais un nouvel appel réseau : sans ce mock réaliste, settings.training/
// learning/chatbot restent `undefined` dans ce harnais de test isolé — pas
// un bug de settings.js, juste l'absence du bootstrap réel reproduit ici.
const DEFAULT_SETTINGS = {
  appearance: { theme: "light", accent: "purple", fontSize: "normal", animations: true },
  training: { questionsPerSeries: 10, chrono: true, soundEffects: true, correctionDisplay: "fin" },
  learning: { dailyGoalExercises: 10, dailyGoalTimeMin: 15, spacedRepetition: true },
  language: "fr",
  favorites: [],
  favoriteNotions: [],
  chatbot: {
    explanationLevel: "auto", mode: "professeur", responseLength: "normal",
    memoryEnabled: true, historyEnabled: true, streaming: true,
  },
};

const mockApi = {
  me: vi.fn(),
  getCookieConsent: vi.fn().mockResolvedValue({ statistics: false, marketing: false, updated_at: null }),
  getSettings: vi.fn().mockResolvedValue(DEFAULT_SETTINGS),
  saveSettings: vi.fn((s) => Promise.resolve(s)),
};
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../curriculumSelector.js", () => ({ initClassBadge: vi.fn() }));

// Même gabarit que celui injecté par settingsPopup.js::PANEL_TEMPLATE — voir
// ce fichier pour la source de vérité (settings.js documente explicitement
// que mountSettingsPanel() attend ces ids précis).
const PANEL_TEMPLATE = `
  <nav class="settings-menu" id="settings-menu" aria-label="Catégories de paramètres"></nav>
  <div class="settings-panel" id="settings-panel"></div>
  <div class="modal-overlay" id="confirm-modal-overlay" hidden>
    <div class="modal-card card">
      <h3 id="confirm-modal-title">Confirmer l'action</h3>
      <p id="confirm-modal-text"></p>
      <div id="confirm-modal-extra"></div>
      <span class="form-error form-error--global" id="confirm-modal-error" hidden></span>
      <div class="verdict-row">
        <button type="button" id="confirm-modal-confirm">Confirmer</button>
        <button type="button" id="confirm-modal-cancel">Annuler</button>
      </div>
    </div>
  </div>
  <div class="toast" id="settings-toast" hidden></div>
`;

async function mountSettings(user = { id: 1, is_guest: false, plan: "free" }) {
  const container = document.createElement("div");
  container.innerHTML = PANEL_TEMPLATE;
  document.body.appendChild(container);
  Object.values(mockApi).forEach((fn) => fn.mockClear());
  mockApi.getSettings.mockResolvedValue(DEFAULT_SETTINGS);
  if (user) mockApi.me.mockResolvedValue({ user });
  else mockApi.me.mockRejectedValue(new Error("401"));
  vi.resetModules();
  const { initSettingsManager } = await import("../settingsManager.js");
  await initSettingsManager();
  const { mountSettingsPanel } = await import("../settings.js");
  await mountSettingsPanel(container);
  await flushPromises();
  return container;
}

// Retire chaque conteneur du document après son test : sans cela, les
// anciens conteneurs s'empilent dans document.body (id dupliqués) et les
// écouteurs onSettingsChange des anciennes instances du module (jamais
// désinscrits, voir settings.js) peuvent réagir à un "*" diffusé par un test
// suivant — reproductible uniquement dans ce harnais de tests qui monte le
// panneau plusieurs fois dans le même document.
afterEach(() => {
  document.body.innerHTML = "";
});

describe("settings.js — mountSettingsPanel", () => {
  // Chantier "simplification page Paramètres" (2026-10-18) : catégorie
  // "Langue" retirée (traduction partielle et trompeuse, voir settings.js) —
  // 7 catégories restantes, plus aucune trace de "language"/"Langue" dans le
  // menu.
  it("rend le menu des 7 catégories restantes (Langue retirée)", async () => {
    const container = await mountSettings();
    const items = container.querySelectorAll(".settings-menu-item");
    expect(items).toHaveLength(7);
    expect([...items].some((el) => el.dataset.cat === "language")).toBe(false);
    expect(container.querySelector("#settings-menu").textContent).not.toContain("Langue");
  });

  it("affiche la catégorie Compte par défaut", async () => {
    const container = await mountSettings();
    expect(container.querySelector(".settings-menu-item.active").dataset.cat).toBe("account");
  });

  it("redirige vers / si la session est invalide (api.me échoue)", async () => {
    await withMockedLocation(async () => {
      await mountSettings(null);
      expect(window.location.href).toBe("/");
    });
  });

  it("charge le consentement cookies pour un compte non-invité", async () => {
    await mountSettings({ id: 1, is_guest: false });
    expect(mockApi.getCookieConsent).toHaveBeenCalled();
  });

  it("ne charge pas le consentement cookies pour un compte invité", async () => {
    await mountSettings({ id: 1, is_guest: true });
    expect(mockApi.getCookieConsent).not.toHaveBeenCalled();
  });
});

describe("settings.js — navigation entre catégories", () => {
  let container;
  beforeEach(async () => {
    container = await mountSettings();
  });

  it("change de catégorie active au clic sur un item du menu", () => {
    container.querySelector('[data-cat="appearance"]').click();
    expect(container.querySelector(".settings-menu-item.active").dataset.cat).toBe("appearance");
  });

  it("persiste l'onglet actif en localStorage", () => {
    container.querySelector('[data-cat="security"]').click();
    expect(localStorage.getItem("novamath:settings_tab")).toBe("security");
  });

  it("affiche le panneau Apparence avec les sections attendues", () => {
    container.querySelector('[data-cat="appearance"]').click();
    const panel = container.querySelector("#settings-panel");
    expect(panel.innerHTML).toContain("Thème");
    expect(panel.innerHTML).toContain("Couleur principale");
  });
});

describe("settings.js — catégorie Apparence (application immédiate)", () => {
  let container;
  beforeEach(async () => {
    container = await mountSettings();
    container.querySelector('[data-cat="appearance"]').click();
  });

  it("sélectionner une couleur d'accent l'applique immédiatement au document", () => {
    const blueSwatch = container.querySelector('.color-swatch[data-accent="blue"]');
    blueSwatch.click();
    expect(document.documentElement.getAttribute("data-accent")).toBe("blue");
    expect(blueSwatch.classList.contains("active")).toBe(true);
  });

  it("basculer le pill 'Mode clair' change le thème du document", () => {
    container.querySelector('[data-group="theme"] [data-value="light"]').click();
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("désactiver le toggle Animations met data-animations=off", () => {
    const toggle = container.querySelector("#toggle-animations");
    toggle.checked = false;
    toggle.dispatchEvent(new Event("change"));
    expect(document.documentElement.getAttribute("data-animations")).toBe("off");
  });
});

// Chantier "simplification page Paramètres" (2026-10-18) : vérifie l'absence
// des contrôles retirés (sans effet réel ou sans valeur pédagogique vérifiée,
// voir settings.js) et la présence de ceux conservés (effet réel confirmé).
describe("settings.js — catégorie Chatbot (nettoyage)", () => {
  let container;
  beforeEach(async () => {
    container = await mountSettings();
    container.querySelector('[data-cat="chatbot"]').click();
  });

  it("conserve les réglages ayant un effet réel vérifié", () => {
    const panel = container.querySelector("#settings-panel").innerHTML;
    expect(panel).toContain("Niveau d'explication");
    expect(panel).toContain("Mode");
    expect(panel).toContain("Longueur des réponses");
    expect(panel).toContain("Mémoire");
    expect(panel).toContain("Historique");
    expect(panel).toContain("Affichage progressif");
  });

  // Chantier "audit fonctionnel des paramètres du chatbot" (2026-10-18) :
  // "Historique" avait été retiré par un chantier précédent au motif qu'il
  // serait redondant/sans valeur pédagogique — son effet réel étant démontré
  // (chatbot/conversation_manager.py::stream_reply), il est restauré. Un
  // réglage fonctionnel n'est jamais retiré au seul motif qu'il est
  // redondant ou peu utile.
  it("propose bien le toggle Historique (effet réel démontré, restauré)", () => {
    const panel = container.querySelector("#settings-panel");
    expect(panel.querySelector("#toggle-chatbot-history")).not.toBeNull();
  });

  it("le mode pas-à-pas reste un choix proposé (pertinent, effet réel sur le prompt système)", () => {
    const panel = container.querySelector("#settings-panel").innerHTML;
    expect(panel).toContain("Pas-à-pas");
  });
});

describe("settings.js — catégorie Entraînement (nettoyage)", () => {
  it("ne propose plus 'Mode de correction' (correctionDisplay, aucun effet réel)", async () => {
    const container = await mountSettings();
    container.querySelector('[data-cat="training"]').click();
    const panel = container.querySelector("#settings-panel");
    expect(panel.innerHTML).not.toContain("Mode de correction");
    expect(panel.querySelector('[data-group="correctionDisplay"]')).toBeNull();
  });

  it("conserve Chronomètre et Effets sonores (effet réel confirmé)", async () => {
    const container = await mountSettings();
    container.querySelector('[data-cat="training"]').click();
    const panel = container.querySelector("#settings-panel").innerHTML;
    expect(panel).toContain("Chronomètre");
    expect(panel).toContain("Effets sonores");
  });
});

describe("settings.js — catégorie Apprentissage (nettoyage)", () => {
  it("ne propose plus 'Temps quotidien' ni 'Révision espacée' (aucun consommateur)", async () => {
    const container = await mountSettings();
    container.querySelector('[data-cat="learning"]').click();
    const panel = container.querySelector("#settings-panel");
    expect(panel.innerHTML).not.toContain("Temps quotidien");
    expect(panel.innerHTML).not.toContain("Révision espacée");
    expect(panel.querySelector("#input-daily-time")).toBeNull();
    expect(panel.querySelector("#toggle-spaced")).toBeNull();
  });

  it("conserve l'objectif quotidien d'exercices (réellement utilisé par le Dashboard)", async () => {
    const container = await mountSettings();
    container.querySelector('[data-cat="learning"]').click();
    const panel = container.querySelector("#settings-panel");
    expect(panel.innerHTML).toContain("Nombre d'exercices souhaités");
    expect(panel.querySelector("#input-daily-exercises")).not.toBeNull();
  });
});

describe("settings.js — sauvegarde et compatibilité des préférences", () => {
  it("une préférence conservée modifiée est bien envoyée au serveur (sauvegarde)", async () => {
    const container = await mountSettings();
    container.querySelector('[data-cat="chatbot"]').click();
    container.querySelector("#toggle-chatbot-memory").dispatchEvent(new Event("change"));
    const toggle = container.querySelector("#toggle-chatbot-memory");
    toggle.checked = false;
    toggle.dispatchEvent(new Event("change"));
    // Sauvegarde debouncée (250ms, voir settingsManager.js::setSetting) —
    // attente réelle, jamais de minuteur simulé (casse flushPromises()
    // ailleurs dans le projet, voir mémoire de session).
    await new Promise((resolve) => setTimeout(resolve, 350));
    expect(mockApi.saveSettings).toHaveBeenCalled();
    const sent = mockApi.saveSettings.mock.calls.at(-1)[0];
    expect(sent.chatbot.memoryEnabled).toBe(false);
  });

  it("le toggle Historique est bien sauvegardé (sélection -> enregistrement)", async () => {
    const container = await mountSettings();
    container.querySelector('[data-cat="chatbot"]').click();
    const toggle = container.querySelector("#toggle-chatbot-history");
    toggle.checked = false;
    toggle.dispatchEvent(new Event("change"));
    await new Promise((resolve) => setTimeout(resolve, 350));
    expect(mockApi.saveSettings).toHaveBeenCalled();
    const sent = mockApi.saveSettings.mock.calls.at(-1)[0];
    expect(sent.chatbot.historyEnabled).toBe(false);
  });

  it("ne plante pas si une ancienne préférence retirée de l'interface est encore présente côté serveur", async () => {
    // Compatibilité avec les anciennes préférences enregistrées (section 7) :
    // un compte ayant déjà changé de langue ou désactivé l'historique avant
    // un chantier de nettoyage doit continuer à charger la page sans erreur —
    // ces clés restent dans la réponse serveur (backend inchangé) même si un
    // contrôle a pu disparaître de l'interface pour certaines d'entre elles
    // (ex: "language", "correctionDisplay" — voir settings.js).
    mockApi.getSettings.mockResolvedValueOnce({
      ...DEFAULT_SETTINGS,
      language: "en",
      chatbot: { ...DEFAULT_SETTINGS.chatbot, historyEnabled: false },
      training: { ...DEFAULT_SETTINGS.training, correctionDisplay: "chaque_question" },
      learning: { ...DEFAULT_SETTINGS.learning, dailyGoalTimeMin: 45, spacedRepetition: false },
    });
    const container = await mountSettings();
    for (const cat of ["chatbot", "training", "learning"]) {
      expect(() => container.querySelector(`[data-cat="${cat}"]`).click()).not.toThrow();
    }
    expect(container.querySelector("#settings-panel").innerHTML.trim()).not.toBe("");
  });
});
