// ── abonnement.js : cartes de tarification, toast, Checkout/Portail Stripe ──
import { describe, it, expect, vi } from "vitest";
import { loadPageBody, withMockedLocation, flushPromises } from "./testUtils.js";

const mockApi = {
  me: vi.fn(),
  checkoutCreateSession: vi.fn(),
  billingChangePlan: vi.fn(),
  billingCustomerPortal: vi.fn(),
  billingStatus: vi.fn(),
  ownerTestPlanStatus: vi.fn(),
  ownerTestPlanUpdate: vi.fn(),
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

async function mountAbonnementOwner(status, url = "/abonnement.html") {
  window.history.pushState({}, "", url);
  document.body.innerHTML = loadPageBody("abonnement.html");
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.me.mockResolvedValue({ user: { plan: "free", is_owner: true } });
  mockApi.ownerTestPlanStatus.mockResolvedValue(status);
  mockApi.ownerTestPlanUpdate.mockResolvedValue(status);
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

  // Régression : un changement de plan en place (sans rechargement de page)
  // doit notifier les autres widgets (sidebar/identity.js, carte compte du
  // dashboard, page profil) — sinon ils continuent d'afficher l'ancien plan
  // jusqu'au prochain rechargement complet de la page.
  it("notifie novamath:account-updated avec le nouveau plan après changement", async () => {
    await mountAbonnement("premium");
    mockApi.billingChangePlan.mockResolvedValue({});
    mockApi.me.mockResolvedValue({ user: { plan: "ultra" } });
    const onUpdate = vi.fn();
    window.addEventListener("novamath:account-updated", onUpdate);
    document.querySelector('[data-plan-button="ultra"]').click();
    await flushPromises();
    window.removeEventListener("novamath:account-updated", onUpdate);
    expect(onUpdate).toHaveBeenCalled();
    expect(onUpdate.mock.calls.at(-1)[0].detail).toEqual({ plan: "ultra" });
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

  // Chantier 10 (centralisation du feature gating) : la décision d'accès de
  // cette bannière doit passer par hasFeature(user, ...) — donc par
  // user.features quand il est présent — jamais par un recalcul local à
  // partir du seul nom du plan réel (user.plan). Avant ce chantier,
  // showRequiredFeatureBanner comparait uniquement `user.plan` : un cas où
  // user.features contredit user.plan (Owner en mode test, ou toute
  // divergence future) aurait affiché à tort la bannière de mise à niveau
  // alors que le backend a déjà tranché que l'accès est autorisé.
  it("n'affiche rien si user.features autorise déjà l'accès, même si user.plan dit le contraire", async () => {
    window.history.pushState({}, "", "/abonnement.html?required=advanced_ai");
    document.body.innerHTML = loadPageBody("abonnement.html");
    Object.values(mockApi).forEach((fn) => fn.mockReset());
    mockApi.me.mockResolvedValue({
      user: { plan: "free", features: { advanced_ai: true } },
    });
    mockApi.billingStatus.mockResolvedValue({ customer_portal_available: false });
    vi.resetModules();
    await import("../abonnement.js");
    await flushPromises();

    expect($("premium-required-banner").hidden).toBe(true);
  });
});

describe("abonnement.js — mode test Owner (Chantier 6)", () => {
  const statusFree = { is_owner: true, real_plan: "free", test_plan: null, effective_plan: "free", provider: "gemini", model: "gemini-3-flash-preview" };
  const statusPremium = { is_owner: true, real_plan: "free", test_plan: "premium", effective_plan: "premium", provider: "gemini", model: "gemini-3.1-pro-preview" };

  it("affiche la bannière mode test et jamais le parcours Stripe", async () => {
    await mountAbonnementOwner(statusFree);
    expect($("owner-mode-banner").hidden).toBe(false);
    expect($("pricing-footnote").hidden).toBe(true);
    expect(mockApi.billingChangePlan).not.toHaveBeenCalled();
    expect(mockApi.checkoutCreateSession).not.toHaveBeenCalled();
  });

  it("les boutons deviennent des boutons de test, jamais désactivés pour free", async () => {
    await mountAbonnementOwner(statusFree);
    const freeBtn = document.querySelector('[data-plan-button="free"]');
    const premiumBtn = document.querySelector('[data-plan-button="premium"]');
    expect(freeBtn.disabled).toBe(true); // plan effectif courant
    expect(freeBtn.textContent).toBe("Mode testé");
    expect(premiumBtn.disabled).toBe(false);
    expect(premiumBtn.textContent).toBe("Tester Premium");
  });

  it("cliquer sur Premium appelle /api/owner/test-plan, jamais Stripe", async () => {
    await mountAbonnementOwner(statusFree);
    mockApi.ownerTestPlanUpdate.mockResolvedValue(statusPremium);
    document.querySelector('[data-plan-button="premium"]').click();
    await flushPromises();
    // unlimited_quotas: false envoyé dans le même appel — sinon les quotas
    // resteraient illimités quel que soit le plan "testé" (voir
    // owner_test_plan_service.get_unlimited_quotas, True par défaut pour
    // l'Owner), ce qui viderait "Tester Premium/Ultra" de son intérêt.
    expect(mockApi.ownerTestPlanUpdate).toHaveBeenCalledWith({ plan: "premium", unlimited_quotas: false });
    expect(mockApi.checkoutCreateSession).not.toHaveBeenCalled();
    expect(mockApi.billingChangePlan).not.toHaveBeenCalled();
    const premiumBtn = document.querySelector('[data-plan-button="premium"]');
    expect(premiumBtn.textContent).toBe("Mode testé");
  });

  it("un utilisateur normal ne voit jamais la bannière mode test", async () => {
    await mountAbonnement("free");
    expect($("owner-mode-banner").hidden).toBe(true);
    expect($("pricing-footnote").hidden).toBe(false);
  });

  // Même régression que pour startChangePlan (voir describe "changement de
  // plan" plus haut) : startOwnerTest() doit aussi notifier les autres
  // widgets de la page.
  it("cliquer sur Tester Premium notifie aussi novamath:account-updated", async () => {
    await mountAbonnementOwner(statusFree);
    mockApi.ownerTestPlanUpdate.mockResolvedValue(statusPremium);
    const onUpdate = vi.fn();
    window.addEventListener("novamath:account-updated", onUpdate);
    document.querySelector('[data-plan-button="premium"]').click();
    await flushPromises();
    window.removeEventListener("novamath:account-updated", onUpdate);
    expect(onUpdate).toHaveBeenCalled();
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

// Chantier "Alignement final de l'offre des abonnements" (2026-08-27) :
// la page ne doit plus promettre AUCUNE fonctionnalité qui n'existe pas
// réellement dans le produit (support prioritaire, badges exclusifs,
// statistiques avancées, accès anticipé, exercices personnalisés, export
// PDF différencié par plan — tous confirmés non implémentés par l'audit).
// Les valeurs numériques affichées doivent rester cohérentes avec les
// sources de vérité backend (quota_service.QUOTA_MATRIX,
// server.py::_SUGGESTIONS_LIMIT_BY_PLAN) — un seul test suffit puisque
// abonnement.html est un fragment 100% statique (aucun rendu dynamique des
// <li>, voir abonnement.js) : pas besoin de mounter la page pour chaque cas.
describe("abonnement.html — plus aucune promesse marketing non tenue", () => {
  const html = loadPageBody("abonnement.html");

  it("ne contient plus aucune des promesses non implémentées", () => {
    const forbidden = [
      "Statistiques avancées et badges exclusifs",
      "Support prioritaire par email",
      "Support prioritaire dédié",
      "Accès anticipé aux nouvelles fonctionnalités",
      "Génération d'exercices sur mesure illimitée",
      "1 export PDF par mois",
      "Exports PDF illimités",
      "Recommandations personnalisées",
      "Tout Gratuit, en illimité",
    ];
    forbidden.forEach((text) => expect(html).not.toContain(text));
  });

  it("affiche les vraies limites de chaque plan (quotas)", () => {
    expect(html).toContain("20 exercices/jour");
    expect(html).toContain("Chatbot : 15 messages/jour");
    expect(html).toContain("60 exercices/jour");
    expect(html).toContain("Chatbot : 25 messages/jour");
    expect(html).toContain("Exercices illimités");
    expect(html).toContain("Chatbot : 40 messages/jour");
  });

  it("n'affiche plus le nombre d'appels IA/jour (masqué volontairement)", () => {
    expect(html).not.toContain("appels IA/jour");
  });

  it("affiche les 3 volumes de suggestions réels (3/5/8)", () => {
    expect(html).toContain("3 suggestions de révision personnalisées");
    expect(html).toContain("5 suggestions de révision personnalisées");
    expect(html).toContain("8 suggestions de révision personnalisées");
  });

  it("mentionne le contenu de cours réellement différencié par plan", () => {
    expect(html).toMatch(/essentiel du cours/);
    expect(html).toContain("Cours complet, toutes les notions et exemples");
    expect(html).toContain("Cours complet, avec les démonstrations");
  });

  it("mentionne les explications avancées uniquement pour Premium/Ultra (réellement implémenté)", () => {
    expect(html).toContain("Explications avancées du chatbot");
  });

  it("mentionne l'analyse de PDF uniquement pour Ultra (réellement implémenté, Feature.ADVANCED_AI)", () => {
    const occurrences = html.split("Analyse de PDF par l'IA du chatbot").length - 1;
    expect(occurrences).toBe(1); // une seule carte (Ultra) la mentionne
  });

  it("prix inchangés (0€ / 6,99€ / 12,99€)", () => {
    expect(html).toContain(">0€<");
    expect(html).toContain(">6,99€<");
    expect(html).toContain(">12,99€<");
  });
});
