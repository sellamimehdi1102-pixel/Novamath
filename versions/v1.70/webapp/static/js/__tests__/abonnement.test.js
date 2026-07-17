// ── abonnement.js : cartes de tarification, toast, Checkout/Portail Stripe ──
import { describe, it, expect, vi } from "vitest";
import { loadPageBody, withMockedLocation, flushPromises } from "./testUtils.js";

const mockApi = {
  me: vi.fn(),
  checkoutCreateSession: vi.fn(),
  billingChangePlan: vi.fn(),
  billingCustomerPortal: vi.fn(),
  billingStatus: vi.fn(),
};
vi.mock("../api.js", () => ({ api: mockApi }));
vi.mock("../settingsManager.js", () => ({ initSettingsManager: () => Promise.resolve() }));
vi.mock("../settingsPopup.js", () => ({ bindSettingsButton: vi.fn() }));
vi.mock("../i18n.js", () => ({ bindLiveTranslations: vi.fn() }));

async function mountAbonnement(plan = "free", billingStatus = { customer_portal_available: false }, url = "/abonnement.html") {
  // Fixe l'URL AVANT l'import (handleCheckoutReturn/handleUpgradeParams la
  // lisent au chargement du module) : window.location/history persiste entre
  // tests d'un même fichier (un seul jsdom par fichier), donc toujours la
  // réassigner explicitement ici plutôt que de la modifier avant d'appeler
  // mountAbonnement — un ?required=/?checkout= resterait sinon collé aux
  // mounts suivants qui n'en veulent pas.
  window.history.pushState({}, "", url);
  document.body.innerHTML = loadPageBody("abonnement.html");
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.me.mockResolvedValue({ user: { plan } });
  mockApi.billingStatus.mockResolvedValue(billingStatus);
  vi.resetModules();
  await import("../abonnement.js");
  await flushPromises();
}

const $ = (id) => document.getElementById(id);

describe("abonnement.js — état des cartes selon le plan actuel", () => {
  it("plan free : le bouton Premium propose de passer à Premium", async () => {
    await mountAbonnement("free");
    const btn = document.querySelector('[data-plan-button="premium"]');
    expect(btn.disabled).toBe(false);
    expect(btn.textContent).toBe("Passer à Premium");
  });

  it("plan premium : la carte Premium est marquée comme actuelle et désactivée", async () => {
    await mountAbonnement("premium");
    const btn = document.querySelector('[data-plan-button="premium"]');
    expect(btn.disabled).toBe(true);
    expect(btn.textContent).toBe("Plan actuel");
    expect(document.querySelector('.pricing-card[data-plan="premium"]').hasAttribute("data-plan-current")).toBe(true);
  });

  it("plan premium : le bouton Ultra propose un changement de plan (pas un nouveau Checkout)", async () => {
    await mountAbonnement("premium");
    const btn = document.querySelector('[data-plan-button="ultra"]');
    expect(btn.textContent).toBe("Changer vers Ultra");
    expect(btn.dataset.changePlan).toBe("true");
  });
});

describe("abonnement.js — démarrage du Checkout", () => {
  it("redirige vers l'URL Stripe renvoyée par le serveur", async () => {
    await mountAbonnement("free");
    mockApi.checkoutCreateSession.mockResolvedValue({ checkout_url: "https://checkout.stripe.com/session/abc" });
    await withMockedLocation(async () => {
      document.querySelector('[data-plan-button="premium"]').click();
      await flushPromises();
      expect(mockApi.checkoutCreateSession).toHaveBeenCalledWith("premium");
      expect(window.location.href).toBe("https://checkout.stripe.com/session/abc");
    });
  });

  it("affiche un toast d'erreur si la réponse ne contient pas checkout_url", async () => {
    await mountAbonnement("free");
    mockApi.checkoutCreateSession.mockResolvedValue({});
    document.querySelector('[data-plan-button="premium"]').click();
    await flushPromises();
    expect($("abonnement-toast").hidden).toBe(false);
    expect($("abonnement-toast").className).toContain("toast--error");
  });

  it("réactive le bouton après une erreur", async () => {
    await mountAbonnement("free");
    mockApi.checkoutCreateSession.mockRejectedValue(new Error("Stripe indisponible."));
    const btn = document.querySelector('[data-plan-button="premium"]');
    btn.click();
    await flushPromises();
    expect(btn.disabled).toBe(false);
    expect($("abonnement-toast").textContent).toContain("Stripe indisponible.");
  });
});

describe("abonnement.js — changement de plan (upgrade/downgrade d'un abonnement actif)", () => {
  it("appelle billingChangePlan puis recharge le plan courant", async () => {
    await mountAbonnement("premium");
    mockApi.billingChangePlan.mockResolvedValue({});
    mockApi.me.mockResolvedValue({ user: { plan: "ultra" } });
    document.querySelector('[data-plan-button="ultra"]').click();
    await flushPromises();
    expect(mockApi.billingChangePlan).toHaveBeenCalledWith("ultra");
    expect($("abonnement-toast").textContent).toContain("Ultra");
  });
});

describe("abonnement.js — retour depuis Stripe Checkout (?checkout=success|cancel)", () => {
  it("affiche un toast de succès et nettoie l'URL", async () => {
    await mountAbonnement("free", undefined, "/abonnement.html?checkout=success");
    expect($("abonnement-toast").hidden).toBe(false);
    expect($("abonnement-toast").className).not.toContain("toast--error");
    expect(window.location.search).toBe("");
  });

  it("affiche un toast d'erreur pour ?checkout=cancel", async () => {
    await mountAbonnement("free", undefined, "/abonnement.html?checkout=cancel");
    expect($("abonnement-toast").className).toContain("toast--error");
  });

  it("n'affiche aucun toast si le paramètre checkout est absent", async () => {
    await mountAbonnement("free", undefined, "/abonnement.html");
    expect($("abonnement-toast").hidden).toBe(true);
  });
});

describe("abonnement.js — bannière de mise à niveau (?required=feature / ?reason=quota)", () => {
  it("affiche la bannière pour une feature verrouillée avec le bon plan requis", async () => {
    await mountAbonnement("free", undefined, "/abonnement.html?required=advanced_ai");
    expect($("premium-required-banner").hidden).toBe(false);
    expect($("premium-required-cta").textContent).toBe("Passer à Ultra");
  });

  it("n'affiche rien si l'utilisateur a déjà le plan requis", async () => {
    await mountAbonnement("free", undefined, "/abonnement.html?required=chatbot");
    expect($("premium-required-banner").hidden).toBe(true);
  });

  it("affiche la bannière quota dépassé avec le palier suivant proposé", async () => {
    await mountAbonnement("free", undefined, "/abonnement.html?reason=quota&quota=chat_messages");
    expect($("premium-required-banner").hidden).toBe(false);
    expect($("premium-required-title").textContent).toContain("limite quotidienne");
  });
});

describe("abonnement.js — carte de statut d'abonnement (portail client)", () => {
  it("reste masquée pour un plan free", async () => {
    await mountAbonnement("free");
    expect($("billing-status-card").hidden).toBe(true);
  });

  it("s'affiche pour un abonné avec portail disponible", async () => {
    await mountAbonnement("premium", {
      plan: "premium",
      subscription_status: "active",
      customer_portal_available: true,
      renew_at: Math.floor(Date.now() / 1000) + 86400,
    });
    expect($("billing-status-card").hidden).toBe(false);
    expect($("billing-status-plan").textContent).toBe("Premium");
  });

  it("ouvre le portail client au clic sur 'Gérer mon abonnement'", async () => {
    await mountAbonnement("premium", {
      plan: "premium",
      subscription_status: "active",
      customer_portal_available: true,
    });
    mockApi.billingCustomerPortal.mockResolvedValue({ portal_url: "https://billing.stripe.com/session/xyz" });
    await withMockedLocation(async () => {
      $("billing-status-manage").click();
      await flushPromises();
      expect(window.location.href).toBe("https://billing.stripe.com/session/xyz");
    });
  });
});
