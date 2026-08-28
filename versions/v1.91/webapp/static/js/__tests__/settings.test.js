// ── settings.js : centre de personnalisation (mountSettingsPanel) ──────────
// Utilise le VRAI settingsManager.js/theme.js/i18n.js (purement locaux, aucun
// réseau) ; seul api.js et curriculumSelector.js (réseau) sont mockés.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { withMockedLocation, flushPromises } from "./testUtils.js";

const mockApi = {
  me: vi.fn(),
  getCookieConsent: vi.fn().mockResolvedValue({ statistics: false, marketing: false, updated_at: null }),
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
  if (user) mockApi.me.mockResolvedValue({ user });
  else mockApi.me.mockRejectedValue(new Error("401"));
  vi.resetModules();
  const { mountSettingsPanel } = await import("../settings.js");
  await mountSettingsPanel(container);
  await flushPromises();
  return container;
}

describe("settings.js — mountSettingsPanel", () => {
  it("rend le menu des 8 catégories", async () => {
    const container = await mountSettings();
    expect(container.querySelectorAll(".settings-menu-item")).toHaveLength(8);
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
