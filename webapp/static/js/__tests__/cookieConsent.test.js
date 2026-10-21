// ── cookieConsent.js : bandeau RGPD, réservation d'espace + correctif de
// défilement initial sur page "courte" (voir son commentaire de tête). ─────
// Non-régression du bug "sidebar collée en bas au premier login" (desktop,
// position:sticky) : sur une page plus haute que le viewport (dashboard.html
// typiquement), le correctif de défilement ne doit JAMAIS se déclencher —
// seul le cas page courte (contenu tenant déjà dans le viewport) le justifie.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("../api.js", () => ({ api: { setCookieConsent: vi.fn().mockResolvedValue({}) } }));

const STORAGE_KEY = "nm_cookie_consent";

function setViewportAndContent({ innerHeight, scrollHeight }) {
  Object.defineProperty(window, "innerHeight", { value: innerHeight, configurable: true });
  Object.defineProperty(document.documentElement, "scrollHeight", { value: scrollHeight, configurable: true });
}

async function mountCookieConsent() {
  localStorage.removeItem(STORAGE_KEY);
  document.body.innerHTML = "";
  vi.resetModules();
  return import("../cookieConsent.js");
}

describe("cookieConsent.js — correctif de défilement initial", () => {
  const ORIGINAL_INNER_HEIGHT = window.innerHeight;
  let scrollBySpy;

  beforeEach(() => {
    scrollBySpy = vi.spyOn(window, "scrollBy").mockImplementation(() => {});
  });

  afterEach(() => {
    scrollBySpy.mockRestore();
    Object.defineProperty(window, "innerHeight", { value: ORIGINAL_INNER_HEIGHT, configurable: true });
  });

  it("page longue (contenu > viewport, ex. dashboard.html) : aucun défilement forcé", async () => {
    setViewportAndContent({ innerHeight: 800, scrollHeight: 3000 });
    await mountCookieConsent();
    expect(document.getElementById("cookie-consent-banner")).not.toBeNull();
    expect(scrollBySpy).not.toHaveBeenCalled();
    // La réservation d'espace (padding-bottom), elle, reste appliquée sur
    // toutes les pages, longues ou courtes — seul le défilement forcé est
    // conditionné à la hauteur du contenu.
    expect(document.body.classList.contains("has-cookie-banner")).toBe(true);
  });

  it("page courte (contenu <= viewport) : le défilement correctif se déclenche toujours", async () => {
    setViewportAndContent({ innerHeight: 800, scrollHeight: 500 });
    await mountCookieConsent();
    expect(scrollBySpy).toHaveBeenCalled();
  });

  it("ne s'affiche jamais si un consentement est déjà enregistré", async () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ statistics: true, marketing: false, version: "1", decided_at: new Date().toISOString() }),
    );
    setViewportAndContent({ innerHeight: 800, scrollHeight: 3000 });
    document.body.innerHTML = "";
    vi.resetModules();
    await import("../cookieConsent.js");
    expect(document.getElementById("cookie-consent-banner")).toBeNull();
  });
});

// ── Garde avant tout retrait du consentement "statistiques" ────────────────
// Née du besoin de ne jamais faire perdre une activité non sauvegardée (ex.
// un message de chatbot en cours de rédaction) à cause du rechargement de
// page qu'analyticsBeacon.js déclenche après un retrait — voir
// analyticsBeacon.js::checkWithdrawalIsSafe pour l'utilisation réelle. Ici,
// on teste cookieConsent.js seul, avec une garde de test contrôlée
// directement (jamais le vrai analyticsBeacon.js), pour isoler le mécanisme
// générique (registerStatisticsWithdrawalGuard/storeConsent) de son seul
// consommateur actuel.
describe("cookieConsent.js — garde avant retrait du consentement statistiques", () => {
  it("une garde qui refuse (renvoie false) annule le retrait : localStorage inchangé, setCookieConsentChoice renvoie false", async () => {
    const mod = await mountCookieConsent();
    mod.setCookieConsentChoice(true, false); // consentement initial : accordé
    expect(localStorage.getItem(STORAGE_KEY)).not.toBeNull();

    mod.registerStatisticsWithdrawalGuard(() => false);
    const result = mod.setCookieConsentChoice(false, false);

    expect(result).toBe(false);
    expect(mod.getCookieConsentChoice().statistics).toBe(true); // jamais modifié
  });

  it("une garde qui accepte (renvoie true) laisse le retrait s'effectuer normalement", async () => {
    const mod = await mountCookieConsent();
    mod.setCookieConsentChoice(true, false);

    mod.registerStatisticsWithdrawalGuard(() => true);
    const result = mod.setCookieConsentChoice(false, false);

    expect(result).toBe(true);
    expect(mod.getCookieConsentChoice().statistics).toBe(false);
  });

  it("la garde n'est jamais appelée pour un octroi (statistics: true), même après un refus initial", async () => {
    const mod = await mountCookieConsent();
    const guard = vi.fn(() => false);
    mod.registerStatisticsWithdrawalGuard(guard);

    const result = mod.setCookieConsentChoice(true, true);

    expect(guard).not.toHaveBeenCalled();
    expect(result).toBe(true);
    expect(mod.getCookieConsentChoice().statistics).toBe(true);
  });

  it("sans garde enregistrée, un retrait s'effectue normalement (comportement par défaut inchangé)", async () => {
    const mod = await mountCookieConsent();
    mod.setCookieConsentChoice(true, false);

    const result = mod.setCookieConsentChoice(false, false);

    expect(result).toBe(true);
    expect(mod.getCookieConsentChoice().statistics).toBe(false);
  });

  it("bannière : un retrait annulé par la garde laisse le bandeau ouvert, le choix reste non enregistré", async () => {
    setViewportAndContent({ innerHeight: 800, scrollHeight: 3000 });
    const mod = await mountCookieConsent();
    mod.registerStatisticsWithdrawalGuard(() => false);

    document.getElementById("cookie-banner-reject-all").click();

    expect(document.getElementById("cookie-consent-banner")).not.toBeNull();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("bannière : un retrait confirmé par la garde ferme le bandeau et enregistre le choix", async () => {
    setViewportAndContent({ innerHeight: 800, scrollHeight: 3000 });
    const mod = await mountCookieConsent();
    mod.registerStatisticsWithdrawalGuard(() => true);

    document.getElementById("cookie-banner-reject-all").click();

    expect(document.getElementById("cookie-consent-banner")).toBeNull();
    expect(mod.getCookieConsentChoice().statistics).toBe(false);
  });
});
