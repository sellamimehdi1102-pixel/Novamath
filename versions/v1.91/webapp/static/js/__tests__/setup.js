// ── Configuration globale Vitest (jsdom) ────────────────────────────────────
// Chargé une fois avant chaque fichier de test (voir vite.config.js::test.setupFiles).
// N'importe AUCUN module applicatif : reste neutre, les fixtures/mocks
// spécifiques à un module vivent dans son propre fichier de test.
import { afterEach, beforeEach } from "vitest";

// jsdom implémente requestAnimationFrame nativement depuis longtemps, mais le
// planifie via setTimeout(0) — on le force en synchrone-ish (setTimeout(fn, 0))
// uniquement s'il est absent, pour ne jamais dépendre d'une version précise.
if (typeof globalThis.requestAnimationFrame !== "function") {
  globalThis.requestAnimationFrame = (cb) => setTimeout(() => cb(performance.now()), 0);
}

// jsdom n'implémente PAS window.matchMedia (lève "Not implemented") — utilisé
// par scroll-reveal.js (prefers-reduced-motion). Stub minimal : jamais "reduced"
// par défaut, pour laisser IntersectionObserver (absent en jsdom → fallback
// "tout visible immédiatement") piloter le comportement testé.
// jsdom n'implémente pas Element.scrollIntoView (lève un TypeError) — utilisé
// par abonnement.js pour amener à l'écran la carte de plan recommandée.
if (typeof Element.prototype.scrollIntoView !== "function") {
  Element.prototype.scrollIntoView = () => {};
}

if (typeof window.matchMedia !== "function") {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  // document.cookie ne fournit aucune méthode "clear" — un cookie posé par un
  // test (ex: api.test.js::nm_csrf) survivrait sinon à tous les tests suivants
  // du même fichier (jsdom ne réinitialise jamais document.cookie entre tests).
  document.cookie.split(";").forEach((c) => {
    const name = c.split("=")[0].trim();
    if (name) document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`;
  });
  document.documentElement.removeAttribute("data-theme");
  document.documentElement.removeAttribute("data-accent");
  document.documentElement.removeAttribute("lang");
  document.body.innerHTML = "";
  window.__NOVAMATH_USER_ID__ = undefined;
});

afterEach(() => {
  document.body.innerHTML = "";
});
