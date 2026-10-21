// ── analyticsBeacon.js : collecte Cloudflare Web Analytics (audit admin,
// Phase 1, 2026-10-2x) — gating par domaine de production ET par le
// consentement "Statistiques" déjà existant (cookieConsent.js). Aucun envoi
// réel à Cloudflare n'est jamais déclenché par cette suite : on vérifie
// uniquement la présence/absence de la balise <script> injectée par ce
// module, jamais une requête réseau réelle (beacon.min.js n'est jamais
// téléchargé en environnement de test, voir jsdom + absence de mock réseau).
import { describe, it, expect, vi, afterEach } from "vitest";

vi.mock("../api.js", () => ({ api: { setCookieConsent: vi.fn().mockResolvedValue({}) } }));

const STORAGE_KEY = "nm_cookie_consent";
const BEACON_SELECTOR = "#cf-web-analytics-beacon";
const CONSENT_CHANGED_EVENT = "mathadap:cookie-consent-changed";

function setConsent(statistics, marketing) {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ statistics, marketing, version: "1", decided_at: new Date().toISOString() }),
  );
}

function setHostname(hostname, { reload = vi.fn() } = {}) {
  const original = window.location;
  Object.defineProperty(window, "location", {
    value: { ...original, hostname, reload },
    writable: true,
    configurable: true,
  });
  return () => Object.defineProperty(window, "location", { value: original, writable: true, configurable: true });
}

async function mountAnalyticsBeacon() {
  document.head.innerHTML = "";
  vi.resetModules();
  return import("../analyticsBeacon.js");
}

// Monte analyticsBeacon.js ET récupère, en plus, les modules dont il dépend
// (cookieConsent.js pour déclencher un retrait "réaliste" via
// setCookieConsentChoice plutôt qu'un simple dispatchEvent qui contournerait
// la garde ; unsavedActivity.js pour simuler une activité non sauvegardée)
// — tous résolus vers les MÊMES instances (vi.resetModules() partagé, import
// par chemin résolu identique), jamais une copie séparée du module.
async function mountAnalyticsBeaconWithDeps() {
  document.head.innerHTML = "";
  vi.resetModules();
  const [analyticsBeacon, cookieConsent, unsavedActivity] = await Promise.all([
    import("../analyticsBeacon.js"),
    import("../cookieConsent.js"),
    import("../unsavedActivity.js"),
  ]);
  return { analyticsBeacon, cookieConsent, unsavedActivity };
}

afterEach(() => {
  localStorage.removeItem(STORAGE_KEY);
  document.head.innerHTML = "";
  // PAS vi.restoreAllMocks() ici : restaurerait aussi le vi.fn() de
  // api.setCookieConsent créé par le vi.mock("../api.js", ...) ci-dessus (sa
  // configuration mockResolvedValue({}) serait perdue dès le 2ᵉ test) —
  // chaque test qui espionne window.confirm le fait fraîchement via
  // vi.spyOn(...).mockReturnValue(...), qui remplace déjà entièrement le
  // comportement du test précédent sans qu'une restauration explicite soit
  // nécessaire ici.
});

describe("analyticsBeacon.js — chargement conditionné au domaine de production", () => {
  it("domaine de production + consentement accordé : le script est chargé", async () => {
    const restore = setHostname("mathadap.com");
    setConsent(true, false);
    await mountAnalyticsBeacon();
    const script = document.querySelector(BEACON_SELECTOR);
    expect(script).not.toBeNull();
    expect(script.src).toBe("https://static.cloudflareinsights.com/beacon.min.js");
    expect(script.type).toBe("module");
    expect(JSON.parse(script.getAttribute("data-cf-beacon")).token).toBe("0d93ead3b2ea4804a41fdff82b7087b8");
    restore();
  });

  it("localhost (développement) : jamais chargé, même avec consentement accordé", async () => {
    const restore = setHostname("localhost");
    setConsent(true, true);
    await mountAnalyticsBeacon();
    expect(document.querySelector(BEACON_SELECTOR)).toBeNull();
    restore();
  });

  it("environnement de test (jsdom) : jamais chargé par défaut", async () => {
    // Aucun setHostname ici : hostname par défaut de jsdom (ni mathadap.com).
    setConsent(true, true);
    await mountAnalyticsBeacon();
    expect(document.querySelector(BEACON_SELECTOR)).toBeNull();
  });

  it("sous-domaine ressemblant (ex. mathadap.com.evil.example) : jamais chargé — comparaison stricte", async () => {
    const restore = setHostname("mathadap.com.evil.example");
    setConsent(true, true);
    await mountAnalyticsBeacon();
    expect(document.querySelector(BEACON_SELECTOR)).toBeNull();
    restore();
  });
});

describe("analyticsBeacon.js — respect du consentement", () => {
  it("consentement non encore décidé (aucune valeur stockée) : jamais chargé par défaut", async () => {
    const restore = setHostname("mathadap.com");
    await mountAnalyticsBeacon();
    expect(document.querySelector(BEACON_SELECTOR)).toBeNull();
    restore();
  });

  it("consentement refusé explicitement (statistics: false) : jamais chargé", async () => {
    const restore = setHostname("mathadap.com");
    setConsent(false, false);
    await mountAnalyticsBeacon();
    expect(document.querySelector(BEACON_SELECTOR)).toBeNull();
    restore();
  });

  it("retrait du consentement après chargement : la balise est retirée ET un rechargement contrôlé est déclenché", async () => {
    // Retirer la balise <script> ne défait pas les écouteurs déjà enregistrés
    // par le script Cloudflare (visibilitychange/pagehide/surcharge de
    // history.pushState pour le tracking SPA) — Cloudflare ne documente
    // aucune API d'arrêt. Seul un rechargement garantit qu'aucun nouvel
    // évènement n'est plus envoyé après un retrait de consentement.
    const reload = vi.fn();
    const restore = setHostname("mathadap.com", { reload });
    setConsent(true, false);
    await mountAnalyticsBeacon();
    expect(document.querySelector(BEACON_SELECTOR)).not.toBeNull();

    window.dispatchEvent(new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { statistics: false, marketing: false } }));
    expect(document.querySelector(BEACON_SELECTOR)).toBeNull();
    expect(reload).toHaveBeenCalledTimes(1);
    restore();
  });

  it("le choix retiré est déjà persisté en localStorage AVANT le rechargement (jamais perdu)", async () => {
    const reload = vi.fn();
    const restore = setHostname("mathadap.com", { reload });
    setConsent(true, false);
    await mountAnalyticsBeacon();

    // Simule exactement ce que fait cookieConsent.js::storeConsent : écrire
    // en localStorage AVANT de diffuser l'évènement lu par ce module.
    setConsent(false, false);
    window.dispatchEvent(new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { statistics: false, marketing: false } }));

    expect(reload).toHaveBeenCalledTimes(1);
    expect(JSON.parse(localStorage.getItem(STORAGE_KEY)).statistics).toBe(false);
    restore();
  });

  it("après le rechargement contrôlé (remontage avec le consentement refusé déjà stocké) : le script reste absent et aucun rechargement supplémentaire n'est déclenché", async () => {
    // Reproduit l'état "après reload" : un nouveau contexte JS (vi.resetModules
    // dans mountAnalyticsBeacon) qui relit un consentement déjà refusé.
    const reload = vi.fn();
    const restore = setHostname("mathadap.com", { reload });
    setConsent(false, false);
    await mountAnalyticsBeacon();

    expect(document.querySelector(BEACON_SELECTOR)).toBeNull();
    expect(reload).not.toHaveBeenCalled(); // jamais de boucle de rechargement
    restore();
  });

  it("retrait de consentement alors que le script n'avait jamais été chargé (déjà refusé) : aucun rechargement", async () => {
    const reload = vi.fn();
    const restore = setHostname("mathadap.com", { reload });
    setConsent(false, false);
    await mountAnalyticsBeacon();

    window.dispatchEvent(new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { statistics: false, marketing: false } }));
    expect(reload).not.toHaveBeenCalled();
    restore();
  });

  it("un octroi de consentement ne déclenche jamais de rechargement", async () => {
    const reload = vi.fn();
    const restore = setHostname("mathadap.com", { reload });
    setConsent(false, false);
    await mountAnalyticsBeacon();

    window.dispatchEvent(new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { statistics: true, marketing: false } }));
    expect(document.querySelector(BEACON_SELECTOR)).not.toBeNull();
    expect(reload).not.toHaveBeenCalled();
    restore();
  });

  it("consentement accordé APRÈS coup (événement, sans rechargement de page) : le script se charge", async () => {
    const restore = setHostname("mathadap.com");
    setConsent(false, false);
    await mountAnalyticsBeacon();
    expect(document.querySelector(BEACON_SELECTOR)).toBeNull();

    window.dispatchEvent(new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { statistics: true, marketing: false } }));
    expect(document.querySelector(BEACON_SELECTOR)).not.toBeNull();
    restore();
  });
});

describe("analyticsBeacon.js — absence de double comptage", () => {
  it("plusieurs changements de consentement successifs vers 'accordé' n'injectent jamais deux balises", async () => {
    const restore = setHostname("mathadap.com", { reload: vi.fn() });
    setConsent(true, false);
    await mountAnalyticsBeacon();
    expect(document.querySelectorAll(BEACON_SELECTOR).length).toBe(1);

    window.dispatchEvent(new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { statistics: true, marketing: true } }));
    window.dispatchEvent(new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { statistics: true, marketing: false } }));
    expect(document.querySelectorAll(BEACON_SELECTOR).length).toBe(1);
    restore();
  });

  it("un retrait suivi d'un nouvel octroi ne laisse jamais deux balises simultanées", async () => {
    // Le retrait déclenche désormais un rechargement contrôlé (stubbé ici,
    // jsdom ne navigue pas réellement) : le reste du scénario — un octroi
    // dispatché juste après sur la même page, sans attendre ce rechargement —
    // doit rester sans danger (jamais deux balises).
    const restore = setHostname("mathadap.com", { reload: vi.fn() });
    setConsent(true, false);
    await mountAnalyticsBeacon();

    window.dispatchEvent(new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { statistics: false, marketing: false } }));
    window.dispatchEvent(new CustomEvent(CONSENT_CHANGED_EVENT, { detail: { statistics: true, marketing: false } }));
    expect(document.querySelectorAll(BEACON_SELECTOR).length).toBe(1);
    restore();
  });
});

// ── Confirmation avant rechargement si une activité non sauvegardée existe ─
// Ces tests passent par cookieConsent.js::setCookieConsentChoice (jamais un
// simple dispatchEvent) pour exercer le VRAI chemin emprunté par la bannière
// et par Paramètres — dispatchEvent seul contournerait la garde enregistrée
// par analyticsBeacon.js (voir checkWithdrawalIsSafe), qui s'exécute AVANT
// la diffusion de l'évènement.
describe("analyticsBeacon.js — confirmation avant rechargement si activité non sauvegardée", () => {
  it("aucune activité non sauvegardée : rechargement immédiat, jamais de window.confirm", async () => {
    const reload = vi.fn();
    const restore = setHostname("mathadap.com", { reload });
    setConsent(true, false);
    const { cookieConsent, unsavedActivity } = await mountAnalyticsBeaconWithDeps();
    unsavedActivity.registerUnsavedActivityCheck("test", () => false);
    const confirmSpy = vi.spyOn(window, "confirm");

    const result = cookieConsent.setCookieConsentChoice(false, false);

    expect(confirmSpy).not.toHaveBeenCalled();
    expect(result).toBe(true);
    expect(reload).toHaveBeenCalledTimes(1);
    expect(document.querySelector(BEACON_SELECTOR)).toBeNull();
    restore();
  });

  it("activité non sauvegardée détectée + confirmation acceptée : le retrait a lieu, puis rechargement", async () => {
    const reload = vi.fn();
    const restore = setHostname("mathadap.com", { reload });
    setConsent(true, false);
    const { cookieConsent, unsavedActivity } = await mountAnalyticsBeaconWithDeps();
    unsavedActivity.registerUnsavedActivityCheck("test", () => true);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    const result = cookieConsent.setCookieConsentChoice(false, false);

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(result).toBe(true);
    expect(cookieConsent.getCookieConsentChoice().statistics).toBe(false);
    expect(reload).toHaveBeenCalledTimes(1);
    expect(document.querySelector(BEACON_SELECTOR)).toBeNull();
    restore();
  });

  it("activité non sauvegardée détectée + confirmation refusée : consentement INCHANGÉ, aucun rechargement", async () => {
    const reload = vi.fn();
    const restore = setHostname("mathadap.com", { reload });
    setConsent(true, false);
    const { cookieConsent, unsavedActivity } = await mountAnalyticsBeaconWithDeps();
    unsavedActivity.registerUnsavedActivityCheck("test", () => true);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    const result = cookieConsent.setCookieConsentChoice(false, false);

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(result).toBe(false);
    // Jamais modifié : ni localStorage, ni le script encore chargé, ni reload.
    expect(cookieConsent.getCookieConsentChoice().statistics).toBe(true);
    expect(reload).not.toHaveBeenCalled();
    expect(document.querySelector(BEACON_SELECTOR)).not.toBeNull();
    restore();
  });

  it("consentement jamais encore accordé sur cette page (balise jamais chargée) : aucune confirmation, même avec une activité en cours", async () => {
    const reload = vi.fn();
    const restore = setHostname("mathadap.com", { reload });
    setConsent(false, false); // jamais chargé sur cette page
    const { cookieConsent, unsavedActivity } = await mountAnalyticsBeaconWithDeps();
    unsavedActivity.registerUnsavedActivityCheck("test", () => true);
    const confirmSpy = vi.spyOn(window, "confirm");

    const result = cookieConsent.setCookieConsentChoice(false, false);

    expect(confirmSpy).not.toHaveBeenCalled();
    expect(result).toBe(true);
    expect(reload).not.toHaveBeenCalled();
    restore();
  });

  it("hors production : aucune confirmation même avec une activité en cours (rien à perdre, le beacon n'y tourne jamais)", async () => {
    const reload = vi.fn();
    const restore = setHostname("localhost", { reload });
    setConsent(true, false);
    const { cookieConsent, unsavedActivity } = await mountAnalyticsBeaconWithDeps();
    unsavedActivity.registerUnsavedActivityCheck("test", () => true);
    const confirmSpy = vi.spyOn(window, "confirm");

    const result = cookieConsent.setCookieConsentChoice(false, false);

    expect(confirmSpy).not.toHaveBeenCalled();
    expect(result).toBe(true);
    expect(reload).not.toHaveBeenCalled();
    restore();
  });

  it("un octroi de consentement ne consulte jamais la garde ni window.confirm", async () => {
    const reload = vi.fn();
    const restore = setHostname("mathadap.com", { reload });
    setConsent(false, false);
    const { cookieConsent, unsavedActivity } = await mountAnalyticsBeaconWithDeps();
    unsavedActivity.registerUnsavedActivityCheck("test", () => true);
    const confirmSpy = vi.spyOn(window, "confirm");

    const result = cookieConsent.setCookieConsentChoice(true, false);

    expect(confirmSpy).not.toHaveBeenCalled();
    expect(result).toBe(true);
    expect(document.querySelector(BEACON_SELECTOR)).not.toBeNull();
    restore();
  });
});
