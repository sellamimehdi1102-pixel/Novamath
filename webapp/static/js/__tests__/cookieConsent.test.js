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
