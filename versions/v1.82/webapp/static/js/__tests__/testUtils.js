// ── Utilitaires partagés par les tests d'intégration DOM ───────────────────
// `loadPageBody` charge le VRAI corps HTML d'une page de webapp/static/ (les
// modules comme auth.js/sidebar.js/abonnement.js/chatbot.js manipulent le DOM
// dès leur import et s'attendent à trouver des ids précis) — on teste donc
// contre le HTML réellement servi, jamais une approximation qui risquerait de
// diverger silencieusement de la vraie page.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const STATIC_DIR = resolve(__dirname, "..", "..");

export function loadPageBody(pageFileName) {
  const html = readFileSync(resolve(STATIC_DIR, pageFileName), "utf-8");
  const match = html.match(/<body[^>]*>([\s\S]*)<\/body>/i);
  if (!match) throw new Error(`Aucune balise <body> trouvée dans ${pageFileName}`);
  // Neutralise les <script> (chargés séparément via import() dans les tests,
  // jamais exécutés par la simple affectation à innerHTML).
  return match[1].replace(/<script[\s\S]*?<\/script>/gi, "");
}

export function mountPage(pageFileName) {
  document.body.innerHTML = loadPageBody(pageFileName);
}

/** Attend le prochain micro-tick — utile après un clic déclenchant une chaîne
 * de Promises (ex: api.me().then(...)) avant d'observer le DOM résultant. */
export function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

/** jsdom ne "navigue" jamais réellement (voir warning "Not implemented:
 * navigation") — pour tester un `window.location.href = ...`, on substitue
 * temporairement un objet simple, seul moyen fiable de lire la valeur écrite
 * sans dépendre du comportement de navigation de jsdom.
 * Toujours `async`/`await fn()` (jamais `return fn()` synchrone) : `fn` est
 * quasi systématiquement une fonction async qui `await flushPromises()` en
 * son sein — un simple `return fn()` déclencherait le `finally` (restauration
 * de window.location) avant même que le corps asynchrone de `fn` ait fini de
 * s'exécuter, annulant silencieusement le mock au moment précis où le code
 * testé écrit sur window.location.href. */
export async function withMockedLocation(fn) {
  const original = window.location;
  delete window.location;
  window.location = { ...original, href: "" };
  try {
    return await fn();
  } finally {
    window.location = original;
  }
}
