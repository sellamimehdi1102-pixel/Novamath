// ── auth.js : mode invité — fichier séparé de auth.test.js ─────────────────
// Isolé exprès (voir le commentaire laissé dans auth.test.js) : Vitest donne
// à chaque fichier de test son propre jsdom/document, ce qui garantit ici
// qu'aucun listener .js-start-guest périmé d'un autre test ne persiste
// sur `document` au moment du clic. Le test à assertion négative
// ("ne recrée pas d'invité...") est volontairement le PREMIER de ce fichier :
// c'est le seul moyen de garantir zéro import précédent de auth.js (donc zéro
// listener résiduel) au moment où il s'exécute.
import { describe, it, expect, vi } from "vitest";
import { loadPageBody, withMockedLocation, flushPromises } from "./testUtils.js";

const mockApi = { me: vi.fn(), enterGuest: vi.fn() };
vi.mock("../api.js", () => ({ api: mockApi }));

async function mountAuth({ meResolves = null } = {}) {
  document.body.innerHTML = loadPageBody("index.html");
  Object.values(mockApi).forEach((fn) => fn.mockReset());
  mockApi.me.mockImplementation(() =>
    meResolves ? Promise.resolve({ user: meResolves }) : Promise.reject(new Error("401")),
  );
  vi.resetModules();
  await import("../auth.js");
  await flushPromises();
}

describe("auth.js — mode invité", () => {
  it("ne recrée pas d'invité si un compte réel est déjà connecté (currentAccount résolu)", async () => {
    await mountAuth({ meResolves: { id: 1, is_guest: false } });
    await withMockedLocation(async () => {
      document.querySelector(".js-start-guest").click();
      await flushPromises();
      expect(mockApi.enterGuest).not.toHaveBeenCalled();
      expect(window.location.href).toBe("/chapitres.html");
    });
  });

  it("démarre une session invité puis redirige vers /chapitres.html", async () => {
    await mountAuth();
    mockApi.enterGuest.mockResolvedValue({});
    await withMockedLocation(async () => {
      document.querySelector(".js-start-guest").click();
      await flushPromises();
      expect(mockApi.enterGuest).toHaveBeenCalled();
      expect(window.location.href).toBe("/chapitres.html");
    });
  });
});
