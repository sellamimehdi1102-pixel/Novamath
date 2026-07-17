// ── api.js : wrapper fetch, CSRF, gestion d'erreurs, toasts quota/rate-limit ─
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api, handleQuotaExceeded, handleRateLimited } from "../api.js";
import { withMockedLocation } from "./testUtils.js";

function mockFetchOnce(status, payload, ok = status >= 200 && status < 300) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => payload,
  });
}

describe("api.js — request() / gestion d'erreurs", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("effectue un GET sans en-tête CSRF ni Content-Type", async () => {
    mockFetchOnce(200, { ok: true });
    await api.getStats();
    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.method).toBe("GET");
    expect(opts.headers["X-CSRF-Token"]).toBeUndefined();
    expect(opts.headers["Content-Type"]).toBeUndefined();
    expect(opts.credentials).toBe("same-origin");
  });

  it("ajoute le jeton CSRF depuis le cookie nm_csrf sur une requête mutante", async () => {
    document.cookie = "nm_csrf=abc123";
    mockFetchOnce(200, { ok: true });
    await api.saveStats({ xp: 1 });
    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.headers["X-CSRF-Token"]).toBe("abc123");
    expect(opts.headers["Content-Type"]).toBe("application/json");
  });

  it("n'ajoute aucun en-tête CSRF si le cookie nm_csrf est absent", async () => {
    mockFetchOnce(200, { ok: true });
    await api.saveStats({ xp: 1 });
    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.headers["X-CSRF-Token"]).toBeUndefined();
  });

  it("sérialise le body JSON pour une requête POST", async () => {
    mockFetchOnce(200, { ok: true });
    await api.start(["ch1"], "seconde");
    const [, opts] = global.fetch.mock.calls[0];
    expect(JSON.parse(opts.body)).toEqual({ chapters: ["ch1"], class_level: "seconde" });
  });

  it("retourne le JSON de la réponse en cas de succès", async () => {
    mockFetchOnce(200, { chapters: [1, 2, 3] });
    const result = await api.chapters();
    expect(result).toEqual({ chapters: [1, 2, 3] });
  });

  it("lève une Error avec le message serveur en cas d'échec générique", async () => {
    mockFetchOnce(400, { error: "Requête invalide." });
    await expect(api.getStats()).rejects.toThrow("Requête invalide.");
  });

  it("lève une Error avec un message par défaut si le payload est vide", async () => {
    mockFetchOnce(500, {});
    await expect(api.getStats()).rejects.toThrow(/Erreur API/);
  });

  it("marque isPremiumRequired + feature + requiredPlan sur une erreur 403 premium_required", async () => {
    mockFetchOnce(403, { error: "premium_required", feature: "advanced_ai", required_plan: "ultra" });
    try {
      await api.getStats();
      throw new Error("aurait dû lever");
    } catch (err) {
      expect(err.isPremiumRequired).toBe(true);
      expect(err.feature).toBe("advanced_ai");
      expect(err.requiredPlan).toBe("ultra");
    }
  });

  it("gère une réponse non-JSON sans planter (payload vide)", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => {
        throw new Error("not json");
      },
    });
    await expect(api.getStats()).rejects.toThrow(/Erreur API/);
  });

  it("chatbotAttachPdf envoie un FormData sans Content-Type manuel", async () => {
    mockFetchOnce(200, { ok: true });
    const file = new File(["contenu"], "doc.pdf", { type: "application/pdf" });
    await api.chatbotAttachPdf(file);
    const [path, opts] = global.fetch.mock.calls[0];
    expect(path).toBe("/api/chatbot/attachments/pdf");
    expect(opts.headers["Content-Type"]).toBeUndefined();
    expect(opts.body).toBeInstanceOf(FormData);
  });

  it("search() construit les query params (q/scope/limit/class_level)", async () => {
    mockFetchOnce(200, { results: [] });
    await api.search("dérivée", ["chapters", "notions"], 5, "premiere");
    const [path] = global.fetch.mock.calls[0];
    expect(path).toContain("q=d%C3%A9riv%C3%A9e");
    expect(path).toContain("scope=chapters%2Cnotions");
    expect(path).toContain("limit=5");
    expect(path).toContain("class_level=premiere");
  });

  it("chapters() encode class_level uniquement s'il est fourni", async () => {
    mockFetchOnce(200, {});
    await api.chapters();
    expect(global.fetch.mock.calls[0][0]).toBe("/api/chapters");
    await api.chapters("seconde");
    expect(global.fetch.mock.calls[1][0]).toBe("/api/chapters?class_level=seconde");
  });
});

describe("api.js — handleQuotaExceeded (toast quota)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("crée le toast novamath-quota-toast avec le libellé du plan requis", () => {
    handleQuotaExceeded({ required_plan: "ultra", quota: "chat_messages" });
    const el = document.getElementById("novamath-quota-toast");
    expect(el).not.toBeNull();
    expect(el.hidden).toBe(false);
    expect(el.textContent).toContain("Ultra");
  });

  it("retombe sur Premium si required_plan est inconnu", () => {
    handleQuotaExceeded({ required_plan: "inconnu", quota: "chat_messages" });
    expect(document.getElementById("novamath-quota-toast").textContent).toContain("Premium");
  });

  it("redirige vers abonnement.html après 1600ms", () => {
    withMockedLocation(() => {
      handleQuotaExceeded({ required_plan: "premium", quota: "chat_messages" });
      vi.advanceTimersByTime(1600);
      expect(window.location.href).toContain("/abonnement.html?reason=quota&quota=chat_messages");
    });
  });

  it("réutilise le même élément toast à un second appel (jamais de doublon)", () => {
    handleQuotaExceeded({ required_plan: "premium", quota: "a" });
    handleQuotaExceeded({ required_plan: "ultra", quota: "b" });
    expect(document.querySelectorAll("#novamath-quota-toast").length).toBe(1);
  });
});

describe("api.js — handleRateLimited (toast 429)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("affiche le nombre de secondes d'attente (singulier)", () => {
    handleRateLimited({ retry_after: 1 });
    expect(document.getElementById("novamath-quota-toast").textContent).toContain("1 seconde.");
  });

  it("affiche le nombre de secondes d'attente (pluriel)", () => {
    handleRateLimited({ retry_after: 5 });
    expect(document.getElementById("novamath-quota-toast").textContent).toContain("5 secondes.");
  });

  it("arrondit au moins à 1 seconde même pour une valeur nulle/négative", () => {
    handleRateLimited({ retry_after: 0 });
    expect(document.getElementById("novamath-quota-toast").textContent).toContain("1 seconde.");
  });

  it("masque le toast après le délai d'attente (plafonné à 8s)", () => {
    handleRateLimited({ retry_after: 3 });
    const el = document.getElementById("novamath-quota-toast");
    expect(el.hidden).toBe(false);
    vi.advanceTimersByTime(3000);
    expect(el.hidden).toBe(true);
  });

  it("ne redirige jamais (contrairement au toast quota)", () => {
    withMockedLocation(() => {
      window.location.href = "";
      handleRateLimited({ retry_after: 1 });
      vi.advanceTimersByTime(8000);
      expect(window.location.href).toBe("");
    });
  });
});

describe("api.js — 429 rate_limited via request()", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("marque isRateLimited + retryAfter et déclenche le toast", async () => {
    mockFetchOnce(429, { error: "rate_limited", retry_after: 4 });
    try {
      await api.login({ email: "a@gmail.com", password: "x" });
      throw new Error("aurait dû lever");
    } catch (err) {
      expect(err.isRateLimited).toBe(true);
      expect(err.retryAfter).toBe(4);
    }
    expect(document.getElementById("novamath-quota-toast")).not.toBeNull();
  });
});
